"""
Unit and integration tests for modular src.builders package and src.builder facade.
Consolidated Logical Invariant Suite:
Tests theme engine, client bundle, readme builder, html builder, and orchestrator.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

import src.builder as legacy_builder
import src.builders as builders_pkg
from src.builders.theme_engine import (
    THEMES,
    DEFAULT_THEME,
    get_theme_by_id,
    generate_css_variables,
    generate_zero_foit_script,
    generate_theme_dropdown_options,
    get_theme_json,
)
from src.builders.client_bundle import generate_client_bundle
from src.builders.readme_builder import (
    generate_readme,
    format_4_timezones,
    STATUS_BADGES,
    load_offers,
    load_news,
)
from src.builders.html_builder import generate_web_dashboard


# ==============================================================================
# 1. Theme Engine Tests
# ==============================================================================

class TestThemeEngine:
    def test_theme_engine_palettes_and_composition_invariants(self):
        """Theme engine must export exactly 10 themes, unique IDs, light/dark balance, and required tokens."""
        assert len(THEMES) == 10
        assert DEFAULT_THEME == "catppuccin-latte"
        theme_ids = [t["id"] for t in THEMES]
        assert len(set(theme_ids)) == 10, "Theme IDs must be strictly unique"
        assert DEFAULT_THEME in theme_ids

        light_themes = [t for t in THEMES if t["type"] == "light"]
        dark_themes = [t for t in THEMES if t["type"] == "dark"]
        assert len(light_themes) >= 3, "Must have at least 3 light themes"
        assert len(dark_themes) >= 5, "Must have at least 5 dark themes"

        required_keys = {"id", "name", "type", "dot", "meta", "css_vars"}
        required_css_tokens = {
            "--bg-primary", "--bg-card", "--text-primary", "--text-muted",
            "--border-color", "--accent-color", "--accent-bg"
        }
        for theme in THEMES:
            assert required_keys.issubset(theme.keys()), f"Missing keys in theme {theme['id']}"
            assert theme["type"] in ("light", "dark")
            assert theme["dot"].startswith("#") or theme["dot"].startswith("rgb")
            css_keys = set(theme["css_vars"].keys())
            assert required_css_tokens.issubset(css_keys), f"Missing CSS tokens in theme {theme['id']}"

        # get_theme_by_id and fallback
        assert get_theme_by_id("catppuccin-mocha")["type"] == "dark"
        assert get_theme_by_id("non-existent-theme-xyz")["id"] == DEFAULT_THEME

    def test_theme_engine_code_generation_invariants(self):
        """CSS variables, zero-FOIT script, dropdown HTML, and JSON representations must be valid."""
        css = generate_css_variables()
        assert ":root" in css
        assert f'[data-theme="{DEFAULT_THEME}"]' in css
        assert '[data-theme="light"]' in css and '[data-theme="dark"]' in css
        for theme in THEMES:
            assert f'[data-theme="{theme["id"]}"]' in css

        script = generate_zero_foit_script()
        assert "<script>" in script and "</script>" in script and "certpulse_theme" in script
        assert "document.documentElement.setAttribute('data-theme'" in script

        dropdown_html = generate_theme_dropdown_options()
        assert '<option value="catppuccin-latte" selected>' in dropdown_html
        for theme in THEMES:
            assert f'value="{theme["id"]}"' in dropdown_html

        parsed = json.loads(get_theme_json())
        assert len(parsed) == 10 and parsed[0]["id"] == THEMES[0]["id"]


# ==============================================================================
# 2. Client Bundle Tests
# ==============================================================================

class TestClientBundle:
    def test_client_bundle_rendering_and_injection_invariants(self):
        """Bundle must define all 5 core render routines, modal controllers, and inject datasets."""
        js = generate_client_bundle()
        assert isinstance(js, str) and len(js) > 1000

        required_functions = [
            "function renderGridView", "function renderTableView",
            "function renderTimelineView", "function renderMatrixView", "function renderRedemption",
            "function openProofModal", "function closeProofModal", "function handleProofModalBackdrop",
        ]
        for fn in required_functions:
            assert fn in js, f"Missing routine: {fn}"

        for dom_id in ["proofModal", "proofModalTitle", "proofModalPlatform", "proofModalImage", "closeProofModalBtn"]:
            assert dom_id in js, f"Missing modal DOM ID reference: {dom_id}"

        # Test dataset injection
        sample_offers = json.dumps([{"id": "test-cert", "title": "Test Certification"}])
        sample_news = json.dumps([{"id": "test-news", "title": "Test News"}])
        injected = generate_client_bundle(
            offers_json_str=sample_offers, news_json_str=sample_news, last_sync_iso_js="2026-10-23T12:00:00Z"
        )
        assert "Test Certification" in injected
        assert "Test News" in injected
        assert "2026-10-23T12:00:00Z" in injected


# ==============================================================================
# 3. Readme Builder Tests
# ==============================================================================

class TestReadmeBuilder:
    def test_readme_timezone_formatting_invariants(self):
        """format_4_timezones must format UTC, EST/EDT, IST, and CET/CEST gracefully."""
        res = format_4_timezones("2026-10-23T12:00:00Z")
        assert "UTC" in res["utc"] and "IST" in res["ist"] and "ticker" in res

        for invalid in ["", None, "not-a-valid-iso-date"]:
            fallback = format_4_timezones(invalid)
            assert isinstance(fallback, dict) and "utc" in fallback

    def test_readme_builder_generation_and_escaping_invariants(self):
        """generate_readme must produce valid Markdown, handle empty datasets, and escape pipes."""
        offers = [{
            "id": "ms-ai-900", "title": "Microsoft AI-900 Free Voucher",
            "provider": "Microsoft", "credential_tier": "proctored_exam",
            "offer_type": "free_voucher", "value_usd": 99.0, "verified": True,
            "status": "Active", "valid_until": "2026-12-31T23:59:59Z",
            "proctoring_type": "pearson_vue", "exam_code": "AI-900",
            "url": "https://learn.microsoft.com", "proof_url": "docs/screenshots/ms-ai-900.png",
            "requirements": "Complete Cloud Skills Challenge", "tags": ["AI", "Cloud"],
            "steps_to_claim": ["Sign up", "Complete challenge"],
        }]
        news = [{
            "id": "news-1", "title": "Microsoft launches new AI challenge",
            "date": "2026-10-23", "source": "Microsoft Learn", "summary": "Free vouchers",
            "url": "https://learn.microsoft.com",
        }]
        md = generate_readme(offers, news, "2026-10-23T12:00:00Z")
        assert "CertPulse" in md and "Microsoft AI-900 Free Voucher" in md and "$99" in md

        # Empty datasets
        assert "$0" in generate_readme([], [], "")

        # Pipe escaping
        pipe_offer = [{
            "id": "sparse-offer", "title": "Sparse Offer | With Pipes",
            "provider": "Unknown", "credential_tier": "skill_badge_lab",
            "offer_type": "free_tier", "value_usd": None, "verified": False,
            "status": "Expired", "valid_until": None, "proctoring_type": "unproctored_assessment",
            "exam_code": None, "url": "https://example.com", "proof_url": None,
            "requirements": None, "tags": None, "steps_to_claim": None,
        }]
        pipe_md = generate_readme(pipe_offer, [], "2026-10-23T12:00:00Z")
        assert "Sparse Offer &#124; With Pipes" in pipe_md or "Sparse Offer \\| With Pipes" in pipe_md


# ==============================================================================
# 4. HTML Builder Tests
# ==============================================================================

class TestHtmlBuilder:
    def test_html_builder_structure_and_xss_protection_invariants(self):
        """generate_web_dashboard must render required containers and neutralize XSS payloads."""
        html = generate_web_dashboard([], [], "2026-10-23T12:00:00Z")
        assert "<!DOCTYPE html>" in html and '<html lang="en"' in html
        for container in ["proofModal", "cardsViewContainer", "listViewContainer", "timelineViewContainer", "matrixViewContainer"]:
            assert f'id="{container}"' in html

        # XSS protection
        malicious = [{
            "id": "xss-test", "title": "<script>alert('XSS')</script>",
            "provider": "Hacker", "credential_tier": "proctored_exam",
            "offer_type": "free_voucher", "value_usd": 100.0, "verified": True,
            "status": "active", "valid_until": "2026-12-31T23:59:59Z",
            "proctoring_type": "pearson_vue", "url": "https://example.com",
        }]
        xss_html = generate_web_dashboard(malicious, [], "2026-10-23T12:00:00Z")
        assert "<script>alert('XSS')</script>" not in xss_html


# ==============================================================================
# 5. Package and Facade Backward-Compatibility Tests
# ==============================================================================

class TestPackageAndFacade:
    def test_package_and_facade_parity_invariants(self):
        """src.builders and src.builder must export matching core symbols and calculation strings."""
        core_symbols = [
            "build_all", "generate_readme", "generate_web_dashboard", "THEMES",
            "DEFAULT_THEME", "generate_css_variables", "generate_zero_foit_script",
            "generate_theme_dropdown_options", "generate_client_bundle", "format_4_timezones",
            "load_offers", "load_news",
        ]
        for sym in core_symbols:
            assert hasattr(builders_pkg, sym), f"src.builders missing {sym}"
            assert hasattr(legacy_builder, sym), f"src.builder missing {sym}"

        content = Path("src/builder.py").read_text(encoding="utf-8")
        assert "len(active_offers)" in content or "len(offers)" in content
        assert "len(active_proctored)" in content

    def test_build_all_execution_and_custom_paths_invariants(self):
        """build_all must write valid README and index.html to specified paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_readme = Path(tmpdir) / "README_TEST.md"
            tmp_html = Path(tmpdir) / "index_test.html"
            res = builders_pkg.build_all(readme_path=tmp_readme, html_path=tmp_html)
            assert res is True
            assert tmp_readme.exists() and tmp_html.exists()
            assert len(tmp_readme.read_text(encoding="utf-8")) > 500
            assert len(tmp_html.read_text(encoding="utf-8")) > 1000

    def test_cli_execution_parity_invariants(self):
        """CLI invocations for src.builder and src.builders must both return 0."""
        for mod in ["src.builder", "src.builders"]:
            result = subprocess.run([sys.executable, "-m", mod], capture_output=True, text=True, check=False)
            assert result.returncode == 0
            assert "[OK] Successfully built" in result.stdout
