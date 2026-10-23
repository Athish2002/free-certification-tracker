"""
Unit and integration tests for modular src.builders package and src.builder facade.
Tests theme engine, client bundle, readme builder, html builder, and orchestrator.
"""

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
    def test_themes_count_and_default(self):
        """Theme engine must export exactly 10 themes and default to catppuccin-latte."""
        assert len(THEMES) == 10
        assert DEFAULT_THEME == "catppuccin-latte"
        theme_ids = [t["id"] for t in THEMES]
        assert len(set(theme_ids)) == 10, "Theme IDs must be strictly unique"
        assert DEFAULT_THEME in theme_ids

    def test_theme_composition_invariants(self):
        """Theme definitions must satisfy light/dark balance and required tokens."""
        light_themes = [t for t in THEMES if t["type"] == "light"]
        dark_themes = [t for t in THEMES if t["type"] == "dark"]
        assert len(light_themes) >= 3, "Must have at least 3 light themes"
        assert len(dark_themes) >= 5, "Must have at least 5 dark themes"

        required_keys = {"id", "name", "type", "dot", "meta", "css_vars"}
        required_css_tokens = {
            "--bg-primary",
            "--bg-card",
            "--text-primary",
            "--text-muted",
            "--border-color",
            "--accent-color",
            "--accent-bg",
        }

        expected_theme_ids = {
            "catppuccin-latte",
            "catppuccin-mocha",
            "github-dark",
            "github-light",
            "dracula",
            "nord",
            "tokyo-night",
            "one-dark",
            "gruvbox-dark",
            "solarized-light",
        }
        actual_theme_ids = {t["id"] for t in THEMES}
        assert expected_theme_ids == actual_theme_ids

        for theme in THEMES:
            assert required_keys.issubset(theme.keys()), f"Missing keys in theme {theme['id']}"
            assert theme["type"] in ("light", "dark")
            assert theme["dot"].startswith("#") or theme["dot"].startswith("rgb")
            assert theme["meta"].startswith("#") or theme["meta"].startswith("rgb")
            css_keys = set(theme["css_vars"].keys())
            assert required_css_tokens.issubset(css_keys), f"Missing CSS tokens in theme {theme['id']}"

    def test_get_theme_by_id(self):
        """get_theme_by_id must return the correct theme or default theme for unknown IDs."""
        mocha = get_theme_by_id("catppuccin-mocha")
        assert mocha["name"] == "Catppuccin Mocha"
        assert mocha["type"] == "dark"

        # Unknown ID fallback
        fallback = get_theme_by_id("non-existent-theme-xyz")
        assert fallback["id"] == DEFAULT_THEME

    def test_generate_css_variables(self):
        """CSS variables generator must render :root and selectors for all 10 themes."""
        css = generate_css_variables()
        assert ":root" in css
        assert f'[data-theme="{DEFAULT_THEME}"]' in css
        for theme in THEMES:
            assert f'[data-theme="{theme["id"]}"]' in css
            assert theme["css_vars"]["--bg-primary"] in css

        # Legacy alias backward compatibility
        assert '[data-theme="light"]' in css
        assert '[data-theme="dark"]' in css

    def test_generate_zero_foit_script(self):
        """Zero-FOIT script must handle localStorage, catppuccin-latte fallback, and meta theme-color."""
        script = generate_zero_foit_script()
        assert "<script>" in script
        assert "</script>" in script
        assert "certpulse_theme" in script
        assert "catppuccin-latte" in script
        assert "document.documentElement.setAttribute('data-theme'" in script
        assert "meta[name=\"theme-color\"]" in script

    def test_generate_theme_dropdown_options(self):
        """Theme dropdown options must produce HTML option tags with catppuccin-latte selected."""
        dropdown_html = generate_theme_dropdown_options()
        assert '<option value="catppuccin-latte" selected>' in dropdown_html
        for theme in THEMES:
            assert f'value="{theme["id"]}"' in dropdown_html
            assert theme["name"] in dropdown_html

    def test_get_theme_json(self):
        """get_theme_json must return valid JSON matching THEMES."""
        json_str = get_theme_json()
        parsed = json.loads(json_str)
        assert len(parsed) == 10
        assert parsed[0]["id"] == THEMES[0]["id"]


# ==============================================================================
# 2. Client Bundle Tests
# ==============================================================================

class TestClientBundle:
    def test_generate_client_bundle_zero_args(self):
        """generate_client_bundle must work with zero arguments."""
        js = generate_client_bundle()
        assert isinstance(js, str)
        assert len(js) > 1000

    def test_client_bundle_view_routines_present(self):
        """Bundle must define all 5 core render routines."""
        js = generate_client_bundle()
        required_functions = [
            "function renderGridView",
            "function renderTableView",
            "function renderTimelineView",
            "function renderMatrixView",
            "function renderRedemption",
        ]
        for fn in required_functions:
            assert fn in js, f"Missing view routine: {fn}"

    def test_client_bundle_modal_controllers_and_dom_ids(self):
        """Bundle must define modal controllers and reference all modal DOM IDs."""
        js = generate_client_bundle()
        required_modal_functions = [
            "function openProofModal",
            "function closeProofModal",
            "function handleProofModalBackdrop",
        ]
        for fn in required_modal_functions:
            assert fn in js, f"Missing modal function: {fn}"

        required_modal_dom_ids = [
            "proofModal",
            "proofModalTitle",
            "proofModalPlatform",
            "proofModalImage",
            "closeProofModalBtn",
        ]
        for dom_id in required_modal_dom_ids:
            assert dom_id in js, f"Missing modal DOM ID reference: {dom_id}"

    def test_client_bundle_theme_and_data_injection(self):
        """Bundle must inject provided JSON and handle theme switching."""
        sample_offers = json.dumps([{"id": "test-cert", "title": "Test Certification"}])
        sample_news = json.dumps([{"id": "test-news", "title": "Test News"}])
        js = generate_client_bundle(
            offers_json_str=sample_offers,
            news_json_str=sample_news,
            last_sync_iso_js="2026-10-23T12:00:00Z",
        )
        assert "Test Certification" in js
        assert "Test News" in js
        assert "2026-10-23T12:00:00Z" in js
        assert "switchTheme" in js or "applyTheme" in js
        assert "catppuccin-latte" in js


# ==============================================================================
# 3. Readme Builder Tests
# ==============================================================================

class TestReadmeBuilder:
    def test_format_4_timezones_valid(self):
        """format_4_timezones must format UTC, EST/EDT, IST, and CET/CEST."""
        iso_str = "2026-10-23T12:00:00Z"
        res = format_4_timezones(iso_str)
        assert isinstance(res, dict)
        assert "UTC" in res["utc"]
        assert "IST" in res["ist"]
        assert "EDT" in res["et"] or "EST" in res["et"]
        assert "CET" in res["cet"] or "CEST" in res["cet"]
        assert "ticker" in res

    def test_format_4_timezones_empty_and_invalid(self):
        """format_4_timezones must handle empty or invalid timestamps gracefully without crashing."""
        res_empty = format_4_timezones("")
        assert isinstance(res_empty, dict)
        assert "utc" in res_empty

        res_none = format_4_timezones(None)
        assert isinstance(res_none, dict)
        assert "utc" in res_none

        res_invalid = format_4_timezones("not-a-valid-iso-date")
        assert isinstance(res_invalid, dict)
        assert "utc" in res_invalid

    def test_generate_readme_with_data(self):
        """generate_readme must produce valid Markdown with headers, KPIs, and offers."""
        offers = [
            {
                "id": "ms-ai-900",
                "title": "Microsoft AI-900 Free Voucher",
                "provider": "Microsoft",
                "credential_tier": "proctored_exam",
                "offer_type": "free_voucher",
                "value_usd": 99.0,
                "verified": True,
                "status": "Active",
                "valid_until": "2026-12-31T23:59:59Z",
                "proctoring_type": "pearson_vue",
                "exam_code": "AI-900",
                "url": "https://learn.microsoft.com",
                "proof_url": "docs/screenshots/ms-ai-900.png",
                "requirements": "Complete Cloud Skills Challenge",
                "tags": ["AI", "Cloud"],
                "steps_to_claim": ["Sign up", "Complete challenge"],
            }
        ]
        news = [
            {
                "id": "news-1",
                "title": "Microsoft launches new AI challenge",
                "date": "2026-10-23",
                "source": "Microsoft Learn",
                "summary": "Free vouchers for top performers.",
                "url": "https://learn.microsoft.com",
            }
        ]
        md = generate_readme(offers, news, "2026-10-23T12:00:00Z")
        assert "CertPulse" in md
        assert "Microsoft AI-900 Free Voucher" in md
        assert "$99" in md
        assert "Microsoft launches new AI challenge" in md

    def test_generate_readme_empty_datasets(self):
        """generate_readme must not crash on empty lists."""
        md = generate_readme([], [], "")
        assert "CertPulse" in md
        assert "$0" in md

    def test_generate_readme_null_and_boundary_fields(self):
        """generate_readme must tolerate missing or null fields in offers."""
        offers = [
            {
                "id": "sparse-offer",
                "title": "Sparse Offer | With Pipes",
                "provider": "Unknown",
                "credential_tier": "skill_badge_lab",
                "offer_type": "free_tier",
                "value_usd": None,
                "verified": False,
                "status": "Expired",
                "valid_until": None,
                "proctoring_type": "unproctored_assessment",
                "exam_code": None,
                "url": "https://example.com",
                "proof_url": None,
                "requirements": None,
                "tags": None,
                "steps_to_claim": None,
            }
        ]
        md = generate_readme(offers, [], "2026-10-23T12:00:00Z")
        assert "Sparse Offer &#124; With Pipes" in md or "Sparse Offer \\| With Pipes" in md
        assert "$0" in md


# ==============================================================================
# 4. HTML Builder Tests
# ==============================================================================

class TestHtmlBuilder:
    def test_generate_web_dashboard_structure(self):
        """generate_web_dashboard must render complete HTML with required containers."""
        html = generate_web_dashboard([], [], "2026-10-23T12:00:00Z")
        assert "<!DOCTYPE html>" in html
        assert '<html lang="en"' in html
        assert 'id="proofModal"' in html
        assert 'role="dialog"' in html
        assert 'aria-modal="true"' in html
        assert 'id="cardsViewContainer"' in html
        assert 'id="listViewContainer"' in html
        assert 'id="timelineViewContainer"' in html
        assert 'id="matrixViewContainer"' in html
        assert "catppuccin-latte" in html

    def test_xss_protection_in_html_script_injection(self):
        """HTML builder must neutralize <script> injection in offer titles."""
        malicious_offers = [
            {
                "id": "xss-test",
                "title": "<script>alert('XSS')</script>",
                "provider": "Hacker",
                "credential_tier": "proctored_exam",
                "offer_type": "free_voucher",
                "value_usd": 100.0,
                "verified": True,
                "status": "active",
                "valid_until": "2026-12-31T23:59:59Z",
                "proctoring_type": "pearson_vue",
                "url": "https://example.com",
            }
        ]
        html = generate_web_dashboard(malicious_offers, [], "2026-10-23T12:00:00Z")
        assert "<script>alert('XSS')</script>" not in html


# ==============================================================================
# 5. Package and Facade Backward-Compatibility Tests
# ==============================================================================

class TestPackageAndFacade:
    def test_package_exports_parity(self):
        """src.builders and src.builder must export matching core symbols."""
        core_symbols = [
            "build_all",
            "generate_readme",
            "generate_web_dashboard",
            "THEMES",
            "DEFAULT_THEME",
            "generate_css_variables",
            "generate_zero_foit_script",
            "generate_theme_dropdown_options",
            "generate_client_bundle",
            "format_4_timezones",
            "load_offers",
            "load_news",
        ]
        for sym in core_symbols:
            assert hasattr(builders_pkg, sym), f"src.builders missing {sym}"
            assert hasattr(legacy_builder, sym), f"src.builder missing {sym}"

    def test_legacy_builder_kpi_text_invariants(self):
        """src/builder.py must contain required calculation strings for adversarial tests."""
        builder_file = Path("src/builder.py")
        content = builder_file.read_text(encoding="utf-8")
        assert "len(active_offers)" in content or "len(offers)" in content
        assert "len(active_proctored)" in content
        assert "len(active_badges)" in content
        assert "total_savings = sum(" in content or "sum((o.get(" in content

    def test_build_all_execution_to_custom_paths(self):
        """build_all must write valid README and index.html to specified paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_readme = Path(tmpdir) / "README_TEST.md"
            tmp_html = Path(tmpdir) / "index_test.html"
            res = builders_pkg.build_all(readme_path=tmp_readme, html_path=tmp_html)
            assert res is True
            assert tmp_readme.exists()
            assert tmp_html.exists()
            assert len(tmp_readme.read_text(encoding="utf-8")) > 500
            assert len(tmp_html.read_text(encoding="utf-8")) > 1000

    def test_cli_execution_python_m_src_builder(self):
        """CLI invocation `python -m src.builder` must return code 0."""
        result = subprocess.run(
            [sys.executable, "-m", "src.builder"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        assert "[OK] Successfully built" in result.stdout

    def test_cli_execution_python_m_src_builders(self):
        """CLI invocation `python -m src.builders` must return code 0."""
        result = subprocess.run(
            [sys.executable, "-m", "src.builders"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        assert "[OK] Successfully built" in result.stdout
