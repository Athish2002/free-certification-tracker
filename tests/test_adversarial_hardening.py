"""
Tier 5 Adversarial Coverage Hardening Test Suite for CertPulse (Milestone M5).

Comprehensive cross-module adversarial and boundary stress tests validating:
1. Schema validation invariants across all 39 offers and 75 news articles.
2. Dynamic truth oracle derivation consistency and HTTPS policy compliance.
3. Builder theme palette variables, CSS class generation, and zero-FOIT script.
4. Visual delta-skipping invariant boundaries (Hamming <= 3 bits skips, >= 4 bits forces write, status change forces write).
5. Async concurrency semaphore bounding and task isolation under simulated network chaos.
6. Backward-compatibility facade integrity (src/builder.py and src/inspector.py).
"""

from __future__ import annotations

import asyncio
import io
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import jsonschema
import numpy as np
from PIL import Image
import pytest
import httpx

from src.models import Offer, OffersDatabase
from src.io_utils import validate_payload, atomic_write_json
from src.truth_oracle import (
    derive_truth_policy,
    build_dynamic_policy_registry,
    get_truth_policy,
    POLICY_VERIFIED_100PCT_FREE,
    POLICY_STUDENT_VERIFIED_ONLY,
    POLICY_PARTIAL_DISCOUNT_COPAY,
    POLICY_ANNUAL_WINDOW_CLOSED,
    POLICY_HISTORICAL_EVENT_WAVE,
    POLICY_PROMOTIONAL_SWEEPSTAKES,
    POLICY_CE_RECERTIFICATION_CREDITS,
    POLICY_FREE_UNPROCTORED_BADGE,
)
from src.builders.theme_engine import (
    THEMES,
    DEFAULT_THEME,
    generate_css_variables,
    generate_zero_foit_script,
    get_theme_by_id,
    get_theme_json,
    generate_theme_dropdown_options,
)
from src.visual_hasher import (
    PerceptualHashEngine,
    should_skip_screenshot_write,
)
from src.inspector import (
    InspectionResult,
    run_inspection,
    run_inspection_async,
    inspect_offer,
)
import src.builder as builder_facade
import src.inspector as inspector_facade

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
OFFERS_FILE = DATA_DIR / "offers.json"
NEWS_FILE = DATA_DIR / "news.json"
OFFERS_SCHEMA_FILE = DATA_DIR / "schema.json"
NEWS_SCHEMA_FILE = DATA_DIR / "news_schema.json"


# ==============================================================================
# Helper Utilities & Fixtures
# ==============================================================================

def _generate_synthetic_png(seed: int = 42, size: tuple = (200, 200)) -> bytes:
    """Generates pseudo-random PNG bytes >= 4096 bytes with valid PNG magic bytes."""
    rng = np.random.default_rng(seed)
    arr = rng.integers(50, 200, (size[1], size[0], 3), dtype=np.uint8)
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    val = buf.getvalue()
    assert len(val) >= 4096, f"Generated PNG must be >= 4096 bytes, got {len(val)}"
    assert val[:8] == b"\x89PNG\r\n\x1a\n", "Generated payload must have PNG magic bytes"
    return val


# ==============================================================================
# 1. Schema Validation Invariants (Offers & News)
# ==============================================================================

class TestSchemaValidationInvariants:
    """Adversarial stress testing of schema enforcement across offers and news datasets."""

    def test_news_dataset_conforms_to_schema(self):
        """Verify all 75 articles in data/news.json strictly conform to data/news_schema.json."""
        assert NEWS_FILE.exists()
        assert NEWS_SCHEMA_FILE.exists()
        with open(NEWS_FILE, "r", encoding="utf-8") as f:
            news_data = json.load(f)
        with open(NEWS_SCHEMA_FILE, "r", encoding="utf-8") as f:
            news_schema = json.load(f)

        validate_payload(news_data, news_schema)
        articles = news_data.get("news", [])
        assert len(articles) >= 75, f"Expected at least 75 news articles, found {len(articles)}"

        # Verify dual-date invariants across all 75 articles
        for idx, item in enumerate(articles):
            assert "date" in item, f"Article {idx} missing 'date'"
            assert "published_date" in item, f"Article {idx} missing 'published_date'"
            assert item["date"], f"Article {idx} has empty 'date'"
            assert item["published_date"], f"Article {idx} has empty 'published_date'"
            # Check ISO date format
            clean_date = item["date"].replace("Z", "+00:00")
            assert datetime.fromisoformat(clean_date), f"Invalid ISO date in article {idx}: {item['date']}"

    def test_all_39_offers_instantiate_pydantic_model(self):
        """Verify all 39 offers in data/offers.json cleanly instantiate Pydantic Offer model."""
        assert OFFERS_FILE.exists()
        with open(OFFERS_FILE, "r", encoding="utf-8") as f:
            offers_data = json.load(f)

        offers = offers_data.get("offers", [])
        assert len(offers) == 39, f"Expected 39 offers, found {len(offers)}"

        instantiated_models = []
        for idx, raw_offer in enumerate(offers):
            model = Offer(**raw_offer)
            assert model.id == raw_offer["id"], f"Offer {idx} ID mismatch"
            assert isinstance(model.authenticity_details, dict), f"Offer {idx} authenticity_details not dict"
            assert model.authenticity_score is not None and 0 <= model.authenticity_score <= 100
            assert model.url.startswith("https://") or model.url.startswith("http://")
            instantiated_models.append(model)

        assert len(instantiated_models) == 39

    def test_schema_preflight_rejection_of_invalid_payloads(self):
        """Ensure validate_payload strictly rejects invalid schemas, bad types, and missing fields."""
        with open(NEWS_SCHEMA_FILE, "r", encoding="utf-8") as f:
            news_schema = json.load(f)

        # 1. Missing required field
        bad_payload_missing = {
            "last_updated": "2026-10-23T00:00:00Z",
            "news": [{"title": "Missing fields item"}]
        }
        with pytest.raises(jsonschema.ValidationError):
            validate_payload(bad_payload_missing, news_schema)

        # 2. Invalid field type
        bad_payload_type = {
            "last_updated": 1234567,  # Should be string
            "news": []
        }
        with pytest.raises(jsonschema.ValidationError):
            validate_payload(bad_payload_type, news_schema)

    def test_atomic_write_protects_existing_file_on_validation_failure(self, tmp_path: Path):
        """Verify that atomic_write_json does not overwrite existing file when schema validation fails."""
        target_file = tmp_path / "protected_store.json"
        original_content = {"$schema": "./schema.json", "valid": True, "marker": "CANARY_INTACT"}
        target_file.write_text(json.dumps(original_content), encoding="utf-8")

        # Attempt to overwrite with invalid payload against news schema
        invalid_payload = {"malformed": "data", "corrupt": 999}
        with pytest.raises(jsonschema.ValidationError):
            atomic_write_json(target_file, invalid_payload, schema_path=NEWS_SCHEMA_FILE)

        # Verify target file content remained 100% untouched
        reloaded = json.loads(target_file.read_text(encoding="utf-8"))
        assert reloaded.get("marker") == "CANARY_INTACT"
        assert reloaded.get("valid") is True


# ==============================================================================
# 2. Dynamic Truth Oracle Derivation Consistency & HTTPS Policy Compliance
# ==============================================================================

class TestTruthOracleAdversarialConsistency:
    """Stress testing dynamic truth policy derivation, policy registry, and HTTPS enforcement."""

    def test_all_39_offers_derive_truth_policies(self):
        """Assert that every tracked offer derives a valid policy with HTTPS and cost boundaries."""
        with open(OFFERS_FILE, "r", encoding="utf-8") as f:
            offers_data = json.load(f)

        for offer in offers_data.get("offers", []):
            policy = derive_truth_policy(offer)
            assert isinstance(policy, dict), f"Policy for {offer['id']} must be a dict"
            assert "policy_type" in policy
            assert "real_exam_cost_usd" in policy
            assert "verified_discount_pct" in policy
            assert "truth_source_name" in policy
            assert "truth_source_url" in policy
            assert "authority_rules" in policy

            # HTTPS compliance invariants
            assert policy["authority_rules"]["requires_https"] is True
            truth_url = policy["truth_source_url"]
            assert truth_url.startswith("https://"), f"Truth source URL must be HTTPS: {truth_url}"

            # Numeric cost and discount boundaries
            assert policy["real_exam_cost_usd"] >= 0.0
            assert 0 <= policy["verified_discount_pct"] <= 100

    def test_dynamic_policy_registry_builds_and_resolves(self):
        """Assert build_dynamic_policy_registry indexes all offers and get_truth_policy resolves."""
        registry = build_dynamic_policy_registry(OFFERS_FILE)
        assert len(registry) == 39

        with open(OFFERS_FILE, "r", encoding="utf-8") as f:
            offers = json.load(f)["offers"]

        for offer in offers:
            oid = offer["id"]
            policy = get_truth_policy(oid, offer)
            assert policy["policy_type"] == registry[oid]["policy_type"]

    def test_adversarial_offer_derivation_edge_cases(self):
        """Verify dynamic derivation handles edge cases: copay, closed windows, and empty inputs."""
        # 1. Copay indicator in cart balance
        copay_offer = {
            "id": "synthetic-copay-test",
            "title": "Vendor Copay Challenge",
            "platform": "Juniper",
            "cart_balance_verified": "$50.00 Pearson VUE Co-Pay required",
            "url": "https://learningportal.juniper.net/test"
        }
        copay_policy = derive_truth_policy(copay_offer)
        assert copay_policy["policy_type"] == POLICY_PARTIAL_DISCOUNT_COPAY
        assert copay_policy["real_exam_cost_usd"] == 50.0
        assert copay_policy["verified_discount_pct"] == 75

        # 2. Registrations closed status
        closed_offer = {
            "id": "synthetic-closed-test",
            "title": "Concluded Scholarship Wave",
            "platform": "Linux Foundation",
            "status": "Registrations Closed",
            "url": "https://www.linuxfoundation.org/test"
        }
        closed_policy = derive_truth_policy(closed_offer)
        assert closed_policy["policy_type"] == POLICY_ANNUAL_WINDOW_CLOSED

        # 3. Empty offer fallback
        fallback_policy = derive_truth_policy({})
        assert isinstance(fallback_policy, dict)
        assert fallback_policy["authority_rules"]["requires_https"] is True


# ==============================================================================
# 3. Builder Theme Palette Variables, CSS Generation & Zero-FOIT Script
# ==============================================================================

class TestBuilderThemeEngineAdversarial:
    """Stress testing 10 developer color palettes, CSS token completeness, and Zero-FOIT script."""

    def test_theme_catalog_exactness(self):
        """Verify exactly 10 canonical developer color palettes are defined with Catppuccin Latte default."""
        assert len(THEMES) == 10
        assert DEFAULT_THEME == "catppuccin-latte"

        theme_ids = [t["id"] for t in THEMES]
        expected_ids = [
            "catppuccin-latte", "catppuccin-mocha", "github-dark", "github-light",
            "dracula", "nord", "tokyo-night", "one-dark", "gruvbox-dark", "solarized-light"
        ]
        assert sorted(theme_ids) == sorted(expected_ids)

    def test_theme_tokens_contract(self):
        """Assert all 10 themes define the complete set of required CSS variables."""
        required_tokens = {
            "--canvas-default", "--canvas-subtle", "--canvas-inset",
            "--border-default", "--border-muted",
            "--fg-default", "--fg-muted", "--fg-subtle",
            "--accent-fg", "--accent-emphasis", "--accent-subtle",
            "--success-fg", "--success-emphasis", "--success-subtle",
            "--attention-fg", "--attention-subtle",
            "--danger-fg", "--danger-subtle",
            "--btn-default-bg", "--btn-default-hover",
            "--btn-primary-bg", "--btn-primary-hover",
            "--card-shadow", "--card-shadow-hover", "--specular-rim"
        }

        for theme in THEMES:
            tokens = set(theme.get("tokens", {}).keys())
            missing = required_tokens - tokens
            assert not missing, f"Theme {theme['id']} missing tokens: {missing}"
            assert theme["type"] in ("light", "dark")
            assert theme["dot"].startswith("#")

    def test_css_variables_and_zero_foit_generation(self):
        """Verify CSS generation and Zero-FOIT inline initialization script."""
        css = generate_css_variables()
        assert ":root" in css
        assert "[data-theme=\"catppuccin-latte\"]" in css
        assert ".theme-item" in css

        script = generate_zero_foit_script()
        assert "<script>" in script and "</script>" in script
        assert "certpulse_theme_v2" in script or "certpulse_theme" in script
        assert "catppuccin-latte" in script
        assert "data-theme" in script

    def test_theme_helpers_and_fallback(self):
        """Verify get_theme_by_id fallback, get_theme_json serialization, and dropdown HTML."""
        # Known theme
        nord = get_theme_by_id("nord")
        assert nord["id"] == "nord"

        # Unknown theme falls back to default
        unknown = get_theme_by_id("non-existent-matrix-theme")
        assert unknown["id"] == DEFAULT_THEME

        # JSON serialization roundtrip
        parsed = json.loads(get_theme_json())
        assert len(parsed) == 10

        # Dropdown options
        opts = generate_theme_dropdown_options()
        assert "value=\"catppuccin-latte\"" in opts
        assert "selected" in opts


# ==============================================================================
# 4. Visual Delta-Skipping Invariant Boundaries
# ==============================================================================

class TestVisualDeltaSkippingBoundaries:
    """Stress testing pHash Hamming distance boundaries and skip-write logic."""

    def test_identical_image_same_status_skips_write(self, tmp_path: Path):
        """Hamming distance = 0 (delta = 0.0 < 0.05) with same status must skip write."""
        img_bytes = _generate_synthetic_png(seed=101)
        sc_file = tmp_path / "existing_screenshot.png"
        sc_file.write_bytes(img_bytes)

        should_skip, delta, dist = should_skip_screenshot_write(
            new_image=img_bytes,
            existing_screenshot_path=sc_file,
            old_status="Active",
            new_status="Active",
            delta_threshold=0.05
        )
        assert should_skip is True
        assert dist == 0
        assert delta == 0.0

    def test_hamming_distance_boundary_thresholds(self, tmp_path: Path):
        """Verify Hamming distance boundary: <= 3 bits skips, >= 4 bits forces write."""
        img_bytes = _generate_synthetic_png(seed=202)
        sc_file = tmp_path / "existing_screenshot.png"
        sc_file.write_bytes(img_bytes)

        # Baseline hash: compute real pHash of img_bytes
        real_phash = PerceptualHashEngine.compute_phash(img_bytes)
        base_val = int(real_phash, 16)

        # 1. Flip 3 bits: Hamming distance = 3 -> delta = 3/64 = 0.046875 < 0.05 (SKIPS)
        val_3_bits = base_val ^ 0b111
        hash_3_bits = f"{val_3_bits:016x}"

        with patch.object(PerceptualHashEngine, "compute_phash", side_effect=[hash_3_bits, real_phash]):
            skip, delta, dist = should_skip_screenshot_write(
                new_image=img_bytes,
                existing_screenshot_path=sc_file,
                old_status="Active",
                new_status="Active",
                delta_threshold=0.05
            )
            assert dist == 3
            assert delta == 3 / 64.0
            assert skip is True, f"Distance 3 must skip write, got skip={skip}"

        # 2. Flip 4 bits: Hamming distance = 4 -> delta = 4/64 = 0.0625 >= 0.05 (FORCES WRITE)
        val_4_bits = base_val ^ 0b1111
        hash_4_bits = f"{val_4_bits:016x}"

        with patch.object(PerceptualHashEngine, "compute_phash", side_effect=[hash_4_bits, real_phash]):
            skip, delta, dist = should_skip_screenshot_write(
                new_image=img_bytes,
                existing_screenshot_path=sc_file,
                old_status="Active",
                new_status="Active",
                delta_threshold=0.05
            )
            assert dist == 4
            assert delta == 4 / 64.0
            assert skip is False, f"Distance 4 must force write, got skip={skip}"

    def test_status_change_strictly_forces_screenshot_write(self, tmp_path: Path):
        """Any change in status must force screenshot write, regardless of visual similarity."""
        img_bytes = _generate_synthetic_png(seed=303)
        sc_file = tmp_path / "existing_screenshot.png"
        sc_file.write_bytes(img_bytes)

        # Even with identical bytes (0 bits changed), status change forces write
        should_skip, delta, dist = should_skip_screenshot_write(
            new_image=img_bytes,
            existing_screenshot_path=sc_file,
            old_status="Active",
            new_status="Registrations Closed",
            delta_threshold=0.05
        )
        assert should_skip is False
        assert delta == 1.0
        assert dist == 64

    def test_corrupted_or_missing_target_forces_write(self, tmp_path: Path):
        """Missing file, file size < 4096 bytes, or non-PNG header must force write."""
        img_bytes = _generate_synthetic_png(seed=404)

        # 1. Non-existent file
        missing_file = tmp_path / "does_not_exist.png"
        skip, delta, dist = should_skip_screenshot_write(img_bytes, missing_file, "Active", "Active")
        assert skip is False
        assert delta == 1.0
        assert dist == 64

        # 2. File too small (< 4096 bytes)
        small_file = tmp_path / "small.png"
        small_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        skip, delta, dist = should_skip_screenshot_write(img_bytes, small_file, "Active", "Active")
        assert skip is False
        assert delta == 1.0

        # 3. Invalid magic bytes
        corrupt_header = tmp_path / "corrupt.png"
        corrupt_header.write_bytes(b"GIF89a" + b"\x00" * 5000)
        skip, delta, dist = should_skip_screenshot_write(img_bytes, corrupt_header, "Active", "Active")
        assert skip is False
        assert delta == 1.0


# ==============================================================================
# 5. Async Concurrency Semaphore Bounding & Task Isolation Under Chaos
# ==============================================================================

@pytest.mark.asyncio
class TestAsyncConcurrencyAndChaosIsolation:
    """Stress testing concurrency semaphore bounds and error resilience under network chaos."""

    async def test_semaphore_bounds_concurrent_tasks(self, tmp_path: Path):
        """Assert asyncio.Semaphore(concurrency=3) strictly limits active in-flight tasks to <= 3."""
        offers_file = tmp_path / "offers.json"
        synthetic_offers = [
            {
                "id": f"syn-concurrency-{i}",
                "title": f"Concurrent Exam {i}",
                "platform": "Microsoft Azure",
                "category": "Cloud Architecture",
                "certification_name": f"AZ-{i}",
                "credential_tier": "certification_exam",
                "url": f"https://learn.microsoft.com/credentials/{i}",
                "status": "Active",
                "expiry_date": "2026-12-31"
            }
            for i in range(10)
        ]
        offers_data = {
            "$schema": "./schema.json",
            "last_updated": "2026-10-23T00:00:00Z",
            "offers": synthetic_offers
        }
        offers_file.write_text(json.dumps(offers_data, indent=2), encoding="utf-8")

        max_in_flight = 0
        current_in_flight = 0
        lock = asyncio.Lock()

        def mock_sync_inspector(url, offer=None, max_retries=3):
            auth_mock = {"is_authentic_vendor": True, "authenticity_score": 95, "verdict": "VERIFIED_AUTHENTIC", "summary": "OK", "warning_flags": []}
            return "Active", "HTTP 200 OK", url, auth_mock

        async def tracked_to_thread(fn, *args, **kwargs):
            nonlocal current_in_flight, max_in_flight
            async with lock:
                current_in_flight += 1
                if current_in_flight > max_in_flight:
                    max_in_flight = current_in_flight
            try:
                await asyncio.sleep(0.03)  # Overlap window
                return fn(*args, **kwargs)
            finally:
                async with lock:
                    current_in_flight -= 1

        with patch("src.inspector.DATA_FILE", offers_file), \
             patch("src.inspector.inspect_url_with_retry", side_effect=mock_sync_inspector), \
             patch("asyncio.to_thread", side_effect=tracked_to_thread):

            result = await run_inspection_async(use_headless=False, concurrency=3)

        assert len(result) == 10
        assert max_in_flight <= 3, f"Semaphore violated: peak concurrency was {max_in_flight} > 3"

    async def test_network_chaos_task_isolation(self, tmp_path: Path):
        """Simulate network chaos (timeouts, socket errors, DNS failures) on alternating offers."""
        offers_file = tmp_path / "offers.json"
        synthetic_offers = [
            {
                "id": f"chaos-offer-{i}",
                "title": f"Chaos Exam {i}",
                "platform": "AWS",
                "category": "Cloud Architecture",
                "certification_name": f"AWS-{i}",
                "credential_tier": "certification_exam",
                "url": f"https://aws.amazon.com/certification/{i}",
                "status": "Active",
                "expiry_date": "2026-12-31"
            }
            for i in range(8)
        ]
        offers_data = {
            "$schema": "./schema.json",
            "last_updated": "2026-10-23T00:00:00Z",
            "offers": synthetic_offers
        }
        offers_file.write_text(json.dumps(offers_data, indent=2), encoding="utf-8")

        def mock_chaos_inspector(url, offer=None, max_retries=3):
            # Alternating chaos: even indices succeed, odd indices throw diverse network errors
            idx = int(url.split("/")[-1])
            if idx % 4 == 1:
                raise httpx.ConnectTimeout(f"Simulated ConnectTimeout on {url}")
            elif idx % 4 == 2:
                raise httpx.ConnectError(f"Simulated DNS/ConnectError on {url}")
            elif idx % 4 == 3:
                raise ConnectionResetError(f"Simulated ConnectionReset on {url}")
            else:
                auth_mock = {"is_authentic_vendor": True, "authenticity_score": 90, "verdict": "VERIFIED_AUTHENTIC", "summary": "OK", "warning_flags": []}
                return "Active", "HTTP 200 OK", url, auth_mock

        with patch("src.inspector.DATA_FILE", offers_file), \
             patch("src.inspector.inspect_url_with_retry", side_effect=mock_chaos_inspector):

            # Entire async batch must succeed without aborting
            result = await run_inspection_async(use_headless=False, concurrency=4)

        assert len(result) == 8, f"Expected 8 offers returned despite chaos, got {len(result)}"
        # Verify valid offers (0 and 4) succeeded
        assert result[0]["status"] == "Active"
        assert result[4]["status"] == "Active"


# ==============================================================================
# 6. Backward-Compatibility Facade Integrity (builder.py & inspector.py)
# ==============================================================================

class TestBackwardCompatibilityFacades:
    """Verifies that src/builder.py and src/inspector.py preserve all legacy imports and signatures."""

    def test_builder_facade_exports(self):
        """Assert builder facade re-exports all required functions, paths, and constants."""
        required_callables = [
            "build_all", "generate_readme", "generate_web_dashboard",
            "format_4_timezones", "load_offers", "load_news", "compute_kpis",
            "generate_css_variables", "generate_zero_foit_script",
            "get_theme_by_id", "get_theme_json", "generate_theme_dropdown_options",
            "generate_client_bundle"
        ]
        for name in required_callables:
            attr = getattr(builder_facade, name, None)
            assert callable(attr), f"src.builder facade missing callable: {name}"

        # Invariant paths
        assert hasattr(builder_facade, "DATA_FILE")
        assert hasattr(builder_facade, "NEWS_FILE")
        assert hasattr(builder_facade, "README_FILE")
        assert hasattr(builder_facade, "DOCS_HTML")
        assert hasattr(builder_facade, "THEMES")
        assert hasattr(builder_facade, "DEFAULT_THEME")

    def test_builder_compute_kpis_calculation(self):
        """Verify compute_kpis calculates correct metrics and financial savings."""
        synthetic_offers = [
            {"id": "o1", "status": "Active", "credential_tier": "proctored_exam", "value_usd": 200},
            {"id": "o2", "status": "Active", "credential_tier": "skill_badge_lab", "value_usd": 0},
            {"id": "o3", "status": "Registrations Closed", "credential_tier": "proctored_exam", "value_usd": 150},
            {"id": "o4", "status": "Active", "credential_tier": "proctored_exam", "value_usd": 100},
        ]
        kpis = builder_facade.compute_kpis(synthetic_offers)
        assert kpis["total_offers_count"] == 4
        assert kpis["active_offers_count"] == 3
        assert kpis["active_proctored_count"] == 2
        assert kpis["active_badges_count"] == 1
        assert kpis["total_savings_usd"] == 300

    def test_builder_text_inspection_invariants(self):
        """Assert src/builder.py source code retains required text-inspection token substrings."""
        source_code = Path(builder_facade.__file__).read_text(encoding="utf-8")
        required_substrings = [
            "len(active_offers)",
            "len(offers)",
            "len(active_proctored)",
            "len(active_badges)",
            "total_savings = sum(",
        ]
        for token in required_substrings:
            assert token in source_code, f"Required invariant substring '{token}' missing from src/builder.py"

    def test_inspector_facade_exports_and_result_container(self):
        """Assert inspector facade exports run_inspection, run_inspection_async, inspect_offer."""
        assert callable(getattr(inspector_facade, "run_inspection", None))
        assert callable(getattr(inspector_facade, "run_inspection_async", None))
        assert callable(getattr(inspector_facade, "inspect_offer", None))
        assert callable(getattr(inspector_facade, "should_skip_screenshot_write", None))

        # Test InspectionResult container dual behavior (list + dict access)
        sample_offers = [{"id": "item1", "status": "Active"}, {"id": "item2", "status": "Active"}]
        metrics = {"total_offers": 2, "active_count": 2}
        result = InspectionResult(sample_offers, summary=metrics)

        # List interface
        assert len(result) == 2
        assert result[0]["id"] == "item1"
        assert list(result) == sample_offers

        # Dict interface
        assert result.get("summary") == metrics
        assert result["summary"] == metrics
        assert result.get("offers") == sample_offers
        assert "summary" in result
        assert "offers" in result
        assert set(result.keys()) == {"summary", "results", "offers"}
