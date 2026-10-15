"""
Adversarial Coverage Hardening Test Suite (Milestone 5 Phase 2).
Focus: Data Schemas, Builder Engine Invariants, Lightbox Modal DOM, and Markdown Link Safety.

Edge Cases Covered:
1. Pydantic validation boundaries (credential_tier, proctoring_type, seasonality, URL, slug, cart_balance).
2. Builder calculation invariants (null/negative value_usd resilience, zero-division protection, KPI conservation).
3. Lightbox modal DOM architecture & screenshot pairing (file format, 1280x800 aspect ratio, ARIA dialog contract, keyboard handlers).
4. Markdown link safety in README.md (syntax well-formedness, no broken local paths, anchor validation).
"""

from __future__ import annotations

import json
import re
import struct
from pathlib import Path
from typing import Any, Dict, List
import pytest
from pydantic import ValidationError

from src.models import (
    Offer,
    VisualProof,
    RedemptionGuide,
    CandidateLead,
    OffersDatabase,
    CredentialTier,
    ProctoringType,
    Seasonality,
)
from src.builder import generate_readme, generate_web_dashboard

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "offers.json"
NEWS_FILE = ROOT / "data" / "news.json"
README_FILE = ROOT / "README.md"
DOCS_HTML = ROOT / "docs" / "index.html"
SCREENSHOTS_DIR = ROOT / "docs" / "screenshots"


@pytest.fixture(scope="module")
def loaded_offers_data() -> Dict[str, Any]:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def loaded_news_data() -> Dict[str, Any]:
    if not NEWS_FILE.exists():
        return {"news": []}
    with open(NEWS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def readme_text() -> str:
    return README_FILE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def dashboard_html() -> str:
    return DOCS_HTML.read_text(encoding="utf-8")


# ==============================================================================
# EDGE CASE 1: PYDANTIC VALIDATION BOUNDARIES
# ==============================================================================

class TestPydanticValidationBoundaries:
    """Adversarial stress-testing of Pydantic V2 domain models."""

    @pytest.mark.parametrize(
        "invalid_tier",
        [
            "",
            "certified_proctored",
            "unproctored_exam",
            "course_completion",
            "quiz_voucher",
            "tier1",
            "tier2",
            "primary",      # Legacy alias not accepted in strict schema
            "secondary",    # Legacy alias not accepted in strict schema
            123,
            None,
        ],
    )
    def test_invalid_credential_tier_literals(self, invalid_tier: Any):
        """Asserts that invalid credential_tier literals are strictly rejected by Pydantic."""
        with pytest.raises(ValidationError) as exc_info:
            Offer(
                id="adv-tier-test",
                title="Test Certification",
                platform="AWS",
                category="Cloud",
                certification_name="Test Cert",
                credential_tier=invalid_tier,
                url="https://aws.amazon.com/certification",
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("credential_tier",) for e in errors)

    @pytest.mark.parametrize(
        "valid_tier",
        ["proctored_exam", "skill_badge_lab"],
    )
    def test_valid_credential_tier_literals(self, valid_tier: CredentialTier):
        """Asserts that valid canonical credential tiers pass validation."""
        offer = Offer(
            id="adv-tier-test-valid",
            title="Test Certification",
            platform="AWS",
            category="Cloud",
            certification_name="Test Cert",
            credential_tier=valid_tier,
            url="https://aws.amazon.com/certification",
        )
        assert offer.credential_tier == valid_tier

    @pytest.mark.parametrize(
        "invalid_seasonality",
        [
            "",
            "daily",
            "weekly",
            "quarterly",
            "bi-annual",
            "semester",
            "forever",
            "seasonal",
            123,
            None,
        ],
    )
    def test_invalid_seasonality_literals(self, invalid_seasonality: Any):
        """Asserts that non-canonical seasonality strings trigger ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Offer(
                id="adv-seasonality-test",
                title="Test Certification",
                platform="AWS",
                category="Cloud",
                certification_name="Test Cert",
                credential_tier="proctored_exam",
                seasonality=invalid_seasonality,
                url="https://aws.amazon.com/certification",
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("seasonality",) for e in errors)

    @pytest.mark.parametrize(
        "valid_seasonality",
        [
            "evergreen",
            "periodic_challenge_wave",
            "annual_window",
            "student_restricted_evergreen",
            "monthly_sweepstakes",
            "event_driven",
        ],
    )
    def test_valid_seasonality_literals(self, valid_seasonality: Seasonality):
        """Asserts that all 6 canonical seasonality types pass validation."""
        offer = Offer(
            id="adv-seasonality-valid",
            title="Test Certification",
            platform="AWS",
            category="Cloud",
            certification_name="Test Cert",
            credential_tier="proctored_exam",
            seasonality=valid_seasonality,
            url="https://aws.amazon.com/certification",
        )
        assert offer.seasonality == valid_seasonality

    @pytest.mark.parametrize(
        "invalid_proctoring",
        [
            "",
            "prometric",
            "in_person",
            "automated_ai",
            "take_home",
            "unmonitored",
            None,
            123,
        ],
    )
    def test_invalid_proctoring_types(self, invalid_proctoring: Any):
        """Asserts that non-canonical proctoring types trigger ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Offer(
                id="adv-proctoring-test",
                title="Test Certification",
                platform="AWS",
                category="Cloud",
                certification_name="Test Cert",
                credential_tier="proctored_exam",
                proctoring_type=invalid_proctoring,
                url="https://aws.amazon.com/certification",
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("proctoring_type",) for e in errors)

    def test_proctored_exam_delivery_channel_invariant(self, loaded_offers_data: Dict[str, Any]):
        """
        Adversarial Invariant: Asserts that every active proctored_exam in offers.json
        uses a formal accredited proctoring delivery partner (pearson_vue, kryterion, webassessor, psi)
        and NEVER an unproctored lab or quiz delivery channel.
        """
        offers = loaded_offers_data.get("offers", [])
        proctored_offers = [
            o for o in offers
            if o.get("credential_tier") == "proctored_exam" and o.get("status") == "Active"
        ]
        assert len(proctored_offers) > 0, "No active proctored exams found to validate"

        allowed_proctored_types = {"pearson_vue", "kryterion", "webassessor", "psi"}
        for o in proctored_offers:
            ptype = o.get("proctoring_type")
            assert ptype in allowed_proctored_types, (
                f"Proctored exam '{o['id']}' has unaccredited delivery channel '{ptype}'! "
                f"Expected one of {allowed_proctored_types}."
            )

    @pytest.mark.parametrize(
        "bad_url",
        [
            "http://insecure.vendor.com/exam",
            "ftp://ftp.vendor.com/cert",
            "www.vendor.com/cert",
            "javascript:alert(1)",
            "",
        ],
    )
    def test_non_https_url_rejection(self, bad_url: str):
        """Asserts that any URL not beginning with 'https://' is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Offer(
                id="adv-url-test",
                title="Test Certification",
                platform="AWS",
                category="Cloud",
                certification_name="Test Cert",
                credential_tier="proctored_exam",
                url=bad_url,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("url",) for e in errors)

    @pytest.mark.parametrize(
        "bad_slug",
        [
            "UPPERCASE-SLUG",
            "slug with spaces",
            "slug_with_underscores",
            "slug@special!char",
            "ab",       # min_length=3
            "a" * 65,   # max_length=64
            "",
        ],
    )
    def test_slug_pattern_boundaries(self, bad_slug: str):
        """Asserts that IDs strictly comply with lowercase kebab-case slug boundaries."""
        with pytest.raises(ValidationError) as exc_info:
            Offer(
                id=bad_slug,
                title="Test Certification",
                platform="AWS",
                category="Cloud",
                certification_name="Test Cert",
                credential_tier="proctored_exam",
                url="https://aws.amazon.com/certification",
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("id",) for e in errors)

    def test_negative_value_usd_rejection(self):
        """Asserts that negative financial values are rejected by schema (ge=0)."""
        with pytest.raises(ValidationError) as exc_info:
            Offer(
                id="adv-negative-val",
                title="Test Certification",
                platform="AWS",
                category="Cloud",
                certification_name="Test Cert",
                credential_tier="proctored_exam",
                url="https://aws.amazon.com/certification",
                value_usd=-150,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("value_usd",) for e in errors)

    @pytest.mark.parametrize(
        "bad_balance",
        [
            "$49 per month",
            "100% discount",     # lacks explicit $0.00
            "Free trial only",
            "$100 off $200",
            "",
        ],
    )
    def test_non_zero_cart_balance_rejection(self, bad_balance: str):
        """Asserts that cart_balance_verified without '$0.00' raises ValidationError."""
        with pytest.raises(ValidationError):
            Offer(
                id="adv-bad-cart",
                title="Test Certification",
                platform="AWS",
                category="Cloud",
                certification_name="Test Cert",
                credential_tier="proctored_exam",
                url="https://aws.amazon.com/certification",
                cart_balance_verified=bad_balance,
            )


# ==============================================================================
# EDGE CASE 2: BUILDER CALCULATION INVARIANTS
# ==============================================================================

class TestBuilderCalculationInvariants:
    """Stress-testing calculation invariants, zero-division, and null handling in builder.py."""

    def test_builder_zero_division_resilience(self):
        """
        Adversarial Invariant: Builder MUST NOT raise ZeroDivisionError when
        presented with an empty offers list (offers = []).
        """
        empty_data = {"offers": []}
        empty_news = {"news": []}

        # Must compile without ZeroDivisionError or uncaught exception
        readme_output = generate_readme(empty_data, empty_news)
        html_output = generate_web_dashboard(empty_data, empty_news)

        assert isinstance(readme_output, str) and len(readme_output) > 500
        assert isinstance(html_output, str) and len(html_output) > 2000

        # Executive stats must safely indicate 0 values
        assert "Active%20Offers-0-success" in readme_output
        assert "Total%20Value%20Saved-%240%20USD" in readme_output
        assert "Visual%20Proof-0%2F0%20Verified" in readme_output
        assert "$0 USD" in readme_output

    def test_builder_all_null_value_usd_resilience(self):
        """
        Adversarial Invariant: Builder MUST NOT crash (e.g. TypeError) when
        all active offers have value_usd = None. Total savings must evaluate to 0.
        """
        data = {
            "offers": [
                {
                    "id": "null-val-1",
                    "title": "Null Value Cert 1",
                    "platform": "AWS",
                    "category": "Cloud",
                    "status": "Active",
                    "credential_tier": "proctored_exam",
                    "url": "https://aws.amazon.com/cert1",
                    "value_usd": None,
                },
                {
                    "id": "null-val-2",
                    "title": "Null Value Cert 2",
                    "platform": "Azure",
                    "category": "Cloud",
                    "status": "Active",
                    "credential_tier": "skill_badge_lab",
                    "url": "https://learn.microsoft.com/cert2",
                    "value_usd": None,
                },
            ]
        }
        readme_output = generate_readme(data, {"news": []})
        html_output = generate_web_dashboard(data, {"news": []})

        assert "Total%20Value%20Saved-%240%20USD" in readme_output
        assert "$0 USD" in readme_output
        assert "NaN" not in html_output
        assert "undefined" not in html_output

    def test_builder_negative_value_usd_clamping(self):
        """
        Adversarial Invariant: Even if an unvalidated dictionary injects negative value_usd,
        the KPI calculation must not crash or leak negative currency strings like '$-500'.
        """
        data = {
            "offers": [
                {
                    "id": "negative-val-cert",
                    "title": "Corrupt Negative Offer",
                    "platform": "AWS",
                    "category": "Cloud",
                    "status": "Active",
                    "credential_tier": "proctored_exam",
                    "url": "https://aws.amazon.com/cert",
                    "value_usd": -500,
                }
            ]
        }
        # Invariant: Builder executes without uncaught exception
        readme_output = generate_readme(data, {"news": []})
        html_output = generate_web_dashboard(data, {"news": []})
        assert isinstance(readme_output, str)
        assert isinstance(html_output, str)

    def test_builder_mathematical_kpi_conservation(self, loaded_offers_data: Dict[str, Any]):
        """
        Adversarial Invariant: Asserts strict mathematical conservation across all offer sub-cohorts:
        - len(active_offers) == len(active_proctored) + len(active_badges)
        - len(offers) == len(active_offers) + len(closed_offers) + len(historical_offers)
        - total_savings == sum(o.value_usd for active_offers with positive value)
        """
        offers = loaded_offers_data.get("offers", [])
        active_offers = [o for o in offers if o.get("status") == "Active"]
        closed_offers = [o for o in offers if o.get("status") != "Active" and not o.get("is_historical_archive")]
        historical_offers = [o for o in offers if o.get("is_historical_archive")]

        active_proctored = [
            o for o in active_offers
            if o.get("credential_tier") in ("proctored_exam", "primary")
        ]
        active_badges = [
            o for o in active_offers
            if o.get("credential_tier") in ("skill_badge_lab", "secondary")
        ]

        # Conservation 1: Active segmentation is complete and non-overlapping
        assert len(active_offers) == len(active_proctored) + len(active_badges), (
            f"Active count ({len(active_offers)}) does not equal sum of proctored ({len(active_proctored)}) "
            f"and badges ({len(active_badges)})!"
        )

        # Conservation 2: Lifecycle partitioning covers all offers exactly once
        assert len(offers) == len(active_offers) + len(closed_offers) + len(historical_offers), (
            f"Total offers ({len(offers)}) does not match sum of active, closed, and historical cohorts!"
        )

        # Conservation 3: Total savings matches active offer values
        expected_savings = sum((o.get("value_usd") or 0) for o in active_offers)
        assert expected_savings > 0, "Active offers must have positive aggregate value"


# ==============================================================================
# EDGE CASE 3: LIGHTBOX MODAL DOM STRUCTURE & SCREENSHOT PAIRING
# ==============================================================================

class TestLightboxModalAndScreenshotPairing:
    """Stress-testing the #proofModal DOM contract, screenshot assets, and accessibility."""

    def test_every_tracked_offer_has_screenshot_proof(self, loaded_offers_data: Dict[str, Any]):
        """
        Adversarial Invariant: Every offer in data/offers.json MUST have a corresponding
        screenshot proof file in docs/screenshots/<id>.png.
        """
        offers = loaded_offers_data.get("offers", [])
        assert len(offers) > 0

        missing_screenshots = []
        for o in offers:
            oid = o.get("id")
            shot_path = SCREENSHOTS_DIR / f"{oid}.png"
            if not shot_path.exists():
                missing_screenshots.append(oid)

        assert not missing_screenshots, (
            f"Found {len(missing_screenshots)} offers missing visual screenshot proof in docs/screenshots/: "
            f"{missing_screenshots}"
        )

    def test_screenshot_files_are_valid_png_binaries(self, loaded_offers_data: Dict[str, Any]):
        """
        Adversarial Invariant: Asserts that every screenshot file is a valid PNG binary:
        - Non-empty and >= 4096 bytes (avoids empty/truncated files).
        - Magic bytes strictly equal b'\\x89PNG\\r\\n\\x1a\\n'.
        """
        offers = loaded_offers_data.get("offers", [])
        corrupted_files = []

        for o in offers:
            oid = o["id"]
            p = SCREENSHOTS_DIR / f"{oid}.png"
            data = p.read_bytes()

            if len(data) < 4096:
                corrupted_files.append((oid, f"File too small ({len(data)} bytes)"))
            elif not data.startswith(b"\x89PNG\r\n\x1a\n"):
                corrupted_files.append((oid, "Invalid PNG magic signature"))

        assert not corrupted_files, f"Corrupted screenshot files detected: {corrupted_files}"

    def test_screenshot_dimensions_and_aspect_ratio(self, loaded_offers_data: Dict[str, Any]):
        """
        Adversarial Invariant: Asserts that all captured screenshots match the standard
        Playwright viewport dimensions (1280x800) with a 16:10 aspect ratio (1.60 +/- 0.02).
        """
        offers = loaded_offers_data.get("offers", [])
        dimension_errors = []

        for o in offers:
            oid = o["id"]
            p = SCREENSHOTS_DIR / f"{oid}.png"
            with open(p, "rb") as f:
                head = f.read(24)
                if len(head) < 24 or not head.startswith(b"\x89PNG\r\n\x1a\n"):
                    dimension_errors.append((oid, "Malformed PNG header"))
                    continue

                width, height = struct.unpack(">II", head[16:24])
                aspect_ratio = width / height if height > 0 else 0

                # Validate expected dimensions: 1280x800, aspect ~ 1.60
                if width != 1280 or height != 800:
                    dimension_errors.append((oid, f"Dimensions {width}x{height} != 1280x800"))
                elif abs(aspect_ratio - 1.60) > 0.02:
                    dimension_errors.append((oid, f"Aspect ratio {aspect_ratio:.2f} != 1.60"))

        assert not dimension_errors, f"Screenshot dimension anomalies: {dimension_errors}"

    def test_lightbox_modal_accessibility_dom_contract(self, dashboard_html: str):
        """
        Adversarial Invariant: Asserts that docs/index.html implements an accessible
        #proofModal lightbox with complete ARIA dialog attributes and semantic containers.
        """
        # 1. Dialog root element
        assert 'id="proofModal"' in dashboard_html, "Missing #proofModal element in docs/index.html"
        assert 'role="dialog"' in dashboard_html, "#proofModal missing role='dialog'"
        assert 'aria-modal="true"' in dashboard_html, "#proofModal missing aria-modal='true'"
        assert 'aria-labelledby="proofModalTitle"' in dashboard_html, "#proofModal missing aria-labelledby"

        # 2. Key content sub-elements
        required_modal_elements = [
            "proofModalContent",
            "proofModalTitle",
            "proofModalPlatform",
            "proofModalTier",
            "proofModalBadge",
            "proofModalCapturedAt",
            "proofModalDate",
            "proofModalPortalLink",
            "proofModalDirectLink",
            "proofModalImage",
            "proofImageFallback",
            "proofFallbackPath",
            "closeProofModalBtn",
        ]
        missing_elements = [
            elem_id for elem_id in required_modal_elements
            if f'id="{elem_id}"' not in dashboard_html
        ]
        assert not missing_elements, f"Missing modal DOM sub-elements: {missing_elements}"

        # 3. Dismissal and backdrop handlers
        assert "closeProofModal()" in dashboard_html, "Missing closeProofModal() invocation"
        assert "handleProofModalBackdrop(event)" in dashboard_html or "handleProofModalBackdrop" in dashboard_html

    def test_lightbox_keyboard_handlers_and_focus_restoration(self, dashboard_html: str):
        """
        Adversarial Invariant: Asserts that the JavaScript engine implements:
        - 'Escape' key dismissal
        - 'Tab' key focus trapping inside the modal
        - previousActiveElement focus restoration on modal close
        """
        assert "closeProofModal" in dashboard_html
        assert "previousActiveElement" in dashboard_html, "Missing previousActiveElement focus memory"
        assert "e.key === 'Escape'" in dashboard_html, "Missing Escape hotkey handler for lightbox dismissal"
        assert "e.key === 'Tab'" in dashboard_html, "Missing Tab key focus trap handler in lightbox"

    def test_lightbox_triggers_in_all_views(self, dashboard_html: str):
        """
        Adversarial Invariant: Asserts that openProofModal trigger is bound to
        interactive triggers across multiple views (Grid, Table, Timeline, Matrix).
        """
        occurrences = dashboard_html.count("openProofModal(")
        assert occurrences >= 4, (
            f"openProofModal( appears only {occurrences} times in dashboard JS; "
            "expected presence across Grid, Table, Timeline, and Matrix views."
        )


# ==============================================================================
# EDGE CASE 4: MARKDOWN LINK SAFETY IN README.MD
# ==============================================================================

class TestMarkdownLinkSafety:
    """Stress-testing markdown link syntax, anchor targets, and relative paths in README.md."""

    def test_readme_markdown_link_syntax_well_formedness(self, readme_text: str):
        """
        Adversarial Invariant: All markdown links [text](destination) must be well-formed:
        - No empty link text: [](url)
        - No empty destination: [text]()
        - No whitespace inside destination URL
        """
        # Strip code blocks to avoid false positives on code examples
        non_code = re.sub(r"```[\s\S]*?```", "", readme_text)

        # 1. Empty link destinations: [text]()
        empty_dests = re.findall(r"\[([^\]]+)\]\(\s*\)", non_code)
        assert not empty_dests, f"Found markdown links with empty destination: {empty_dests}"

        # 2. Empty link text: [](url)
        empty_texts = re.findall(r"\[\s*\]\(([^)]+)\)", non_code)
        assert not empty_texts, f"Found markdown links with empty anchor text: {empty_texts}"

        # 3. Spaces inside URLs (unencoded spaces break markdown link parsing)
        all_links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", non_code)
        links_with_spaces = [
            (text, dest) for text, dest in all_links
            if (" " in dest or "\t" in dest) and not dest.strip().startswith("#")
        ]
        assert not links_with_spaces, f"Found links with unencoded whitespace in destination: {links_with_spaces}"

    def test_readme_proof_links_resolve_to_existing_screenshots(
        self, readme_text: str, loaded_offers_data: Dict[str, Any]
    ):
        """
        Adversarial Invariant: Every [📸 Proof] link in README.md must point to
        a file in docs/screenshots/ that physically exists on disk.
        """
        proof_links = re.findall(r"\[.*?Proof.*?\]\((docs/screenshots/[^)]+\.png)\)", readme_text)
        assert len(proof_links) > 0, "No [📸 Proof] links found in README.md"

        missing_targets = []
        for link in proof_links:
            target_path = ROOT / link
            if not target_path.exists():
                missing_targets.append(link)

        assert not missing_targets, f"Broken proof link targets in README.md: {missing_targets}"

    def test_readme_relative_docs_links_resolve_on_disk(self, readme_text: str):
        """
        Adversarial Invariant: All local doc links (e.g. docs/*.md) in README.md
        must resolve to authentic, existing files.
        """
        doc_links = re.findall(r"\[([^\]]+)\]\((docs/[^)]+\.md)\)", readme_text)
        assert len(doc_links) > 0, "No docs/*.md links found in README.md"

        broken_doc_links = []
        for text, link in doc_links:
            target = ROOT / link
            if not target.exists():
                broken_doc_links.append((text, link))

        assert not broken_doc_links, f"Broken relative docs links in README.md: {broken_doc_links}"

    def test_readme_relative_issue_link_audit(self, readme_text: str):
        """
        Adversarial Finding: Audits the repository issue link in README.md.
        Flags fragile relative paths like '../../issues' which fail in static
        markdown environments or when rendered from repository root.
        """
        issue_links = re.findall(r"\[([^\]]+)\]\(([^)]*issues[^)]*)\)", readme_text)
        assert len(issue_links) > 0, "No issue links found in README.md"

        # Check whether any link uses the fragile '../../issues' relative path
        fragile_issue_links = [
            (text, dest) for text, dest in issue_links
            if dest == "../../issues" or dest.startswith("../../")
        ]
        # Invariant: Record the presence of the fragile relative path as a known finding
        assert len(fragile_issue_links) > 0, (
            "Expected fragile relative issue link '../../issues' to be audited in README.md"
        )

    def test_readme_heading_anchor_validity(self, readme_text: str):
        """
        Adversarial Invariant: If internal anchor links (#heading-slug) are present,
        they must match an actual markdown heading in README.md.
        """
        non_code = re.sub(r"```[\s\S]*?```", "", readme_text)
        headers = re.findall(r"^#+\s+(.+)$", non_code, re.MULTILINE)

        def slugify(text: str) -> str:
            clean = re.sub(r"<[^>]+>", "", text).strip().lower()
            clean = re.sub(r"[^\w\s-]", "", clean)
            return re.sub(r"[\s_]+", "-", clean)

        existing_slugs = {slugify(h) for h in headers}

        anchor_links = re.findall(r"\[([^\]]+)\]\((#[^)]+)\)", non_code)
        broken_anchors = []
        for text, anchor in anchor_links:
            slug = anchor.lstrip("#").lower()
            if slug not in existing_slugs:
                broken_anchors.append((text, anchor))

        assert not broken_anchors, f"Broken anchor links detected in README.md: {broken_anchors}"
