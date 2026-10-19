"""
Adversarial Empirical Challenge Test Suite for Milestone 2:
Dual Visual Screenshot & Verification Engine Invariants.

Written by Challenger 2 (critic, specialist).
Enforces zero shallow assertions, deep invariant audits, and empirical stress-testing across:
1. Synthetic maintenance and downtime pages (Oracle 403, Cloudflare, planned maintenance).
2. Synthetic paid catalog pages ($245 standard checkout, $300 fees without promo waiver).
3. Active zero-dollar waiver vs paid catalog edge cases ($245 + 100% discount / $0.00 balance).
4. Dual visual screenshot gate degradation on missing, truncated, or corrupt image files.
5. Production screenshot artifact byte-level integrity across all tracked offers.
"""

import json
import tempfile
from pathlib import Path
from typing import Dict, Any, Tuple
import pytest

from src.dom_inspector import (
    inspect_rendered_dom,
    evaluate_dual_gate,
    MAINTENANCE_PATTERNS,
    PAID_CATALOG_PATTERNS,
    ZERO_DOLLAR_SIGNALS,
    AFFIRMATIVE_OFFER_SIGNALS
)
from src.inspector import inspect_offer

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "offers.json"
SCREENSHOTS_DIR = ROOT / "docs" / "screenshots"
PNG_MAGIC_BYTES = b"\x89PNG\r\n\x1a\n"
MIN_SCREENSHOT_BYTES = 4096


# ==============================================================================
# Helper Verification Functions
# ==============================================================================

def verify_png_file_integrity(file_path: Path) -> Tuple[bool, str]:
    """Strictly validates physical existence, file size >= 4KB, and 8-byte PNG magic header."""
    if not file_path.exists():
        return False, "File does not exist on disk"
    try:
        size = file_path.stat().st_size
        if size < MIN_SCREENSHOT_BYTES:
            return False, f"File size ({size} bytes) below minimum threshold ({MIN_SCREENSHOT_BYTES} bytes)"
        header = file_path.read_bytes()[:8]
        if header != PNG_MAGIC_BYTES:
            return False, f"Invalid magic header: {header!r} != {PNG_MAGIC_BYTES!r}"
        return True, "Valid PNG"
    except Exception as e:
        return False, f"Read error: {e}"


# ==============================================================================
# 1. Synthetic Maintenance Pages Adversarial Suite
# ==============================================================================

@pytest.mark.parametrize(
    "oracle_maintenance_text,title",
    [
        (
            "Oracle University. Our website is currently down for maintenance. "
            "Please speak with an Oracle University representative in your country.",
            "Oracle University - Maintenance"
        ),
        (
            "Oracle Cloud Infrastructure learning portal is down for maintenance. "
            "Routine maintenance in progress. We apologize for the inconvenience.",
            "System Maintenance"
        ),
        (
            "Oracle MyLearn Portal. Under scheduled maintenance. We'll be back shortly. "
            "Contact support for urgent exam scheduling.",
            "Scheduled Maintenance"
        ),
        (
            "Access Denied. 403 Forbidden. The requested service is currently unavailable "
            "due to planned maintenance window.",
            "Oracle 403 Downtime"
        ),
        (
            "Oracle University offers free certification training and vouchers. "
            "However, our website is currently down for maintenance. Try again later.",
            "Oracle Free Certs - Down for Maintenance"
        ),
        (
            "Oracle Race to Certification Challenge. Free OCI Architect Associate Exam. "
            "The portal is currently unavailable while system maintenance is in progress.",
            "OCI Challenge Maintenance"
        ),
    ]
)
def test_adversarial_oracle_maintenance_downtime_variants(oracle_maintenance_text: str, title: str):
    """
    Empirical Invariant: Under NO circumstances may an Oracle maintenance page
    be certified as 'Active', even if commingled with 'free', 'voucher', or 'OCI Challenge'.
    """
    res = inspect_rendered_dom(oracle_maintenance_text, rendered_title=title)
    
    assert res["status"] != "Active", (
        f"CRITICAL DEFECT: Oracle maintenance scenario falsely certified as 'Active': {res}"
    )
    assert res["status"] in {"Review Needed", "Server Error"}, (
        f"Expected 'Review Needed' or 'Server Error', got '{res['status']}'"
    )
    assert res["is_maintenance"] is True, "is_maintenance flag must be True"
    assert res["maintenance_detected"] is True, "maintenance_detected flag must be True"
    assert res["zero_dollar_confirmed"] is False, "zero_dollar_confirmed must be False under maintenance"
    assert res["category"] == "maintenance"

    # Dual gate cascade verification:
    gate_status, gate_reason = evaluate_dual_gate(
        dom_status=res["status"],
        has_zero_dollar=res["zero_dollar_confirmed"],
        screenshot_valid=True
    )
    assert gate_status != "Active", f"Dual gate failed to reject maintenance: {gate_status} / {gate_reason}"


@pytest.mark.parametrize(
    "cf_maintenance_text,title",
    [
        (
            "Error 521 Ray ID: 8c12345678ab9cde • 2026-10-15 12:00:00 UTC "
            "Web server is down. Cloudflare. The origin web server is down for maintenance.",
            "521 Web server is down | Cloudflare"
        ),
        (
            "Error 522 Connection timed out. Cloudflare Ray ID: 9f8e7d6c5b4a. "
            "The origin web server is currently unavailable due to scheduled maintenance.",
            "522 Connection timed out"
        ),
        (
            "Service is currently unavailable. Routine maintenance in progress. "
            "Cloudflare DDoS Protection & Gateway. We'll be back shortly.",
            "Cloudflare Maintenance Screen"
        ),
        (
            "Cloudflare Host Error. Site is currently down. Planned maintenance window active. "
            "Claim your free AWS exam voucher when service resumes.",
            "Site Down"
        ),
        (
            "503 Service Temporarily Unavailable. System downtime in effect. "
            "Cloudflare edge proxy intercepted server maintenance.",
            "503 Maintenance"
        ),
    ]
)
def test_adversarial_cloudflare_and_edge_downtime_variants(cf_maintenance_text: str, title: str):
    """
    Empirical Invariant: Cloudflare and edge proxy downtime/maintenance pages
    must be trapped as 'Review Needed' and never labeled 'Active'.
    """
    res = inspect_rendered_dom(cf_maintenance_text, rendered_title=title)

    assert res["status"] != "Active", (
        f"CRITICAL DEFECT: Cloudflare downtime falsely certified as 'Active': {res}"
    )
    assert res["status"] in {"Review Needed", "Server Error"}
    assert res["maintenance_detected"] is True
    assert res["zero_dollar_confirmed"] is False


@pytest.mark.parametrize("maint_phrase", MAINTENANCE_PATTERNS)
def test_adversarial_all_maintenance_patterns_exhaustive(maint_phrase: str):
    """
    Exhaustive Invariant: Every single maintenance pattern in MAINTENANCE_PATTERNS
    must strictly prevent 'Active' classification, even when wrapped in promotional text.
    """
    adversarial_payload = (
        f"Welcome to the Global Cloud Certification Challenge! Claim your 100% free voucher now. "
        f"Notice: {maint_phrase}. Please check back later to redeem your exam credits."
    )
    res = inspect_rendered_dom(adversarial_payload, rendered_title="Certification Voucher Portal")

    assert res["status"] != "Active", (
        f"Pattern '{maint_phrase}' failed to intercept promotion! Result: {res['status']}"
    )
    assert res["status"] in {"Review Needed", "Server Error"}
    assert res["maintenance_detected"] is True
    assert res["zero_dollar_confirmed"] is False


# ==============================================================================
# 2. Synthetic Paid Catalog Pages Adversarial Suite
# ==============================================================================

@pytest.mark.parametrize(
    "fee_str,vendor_context",
    [
        ("$245", "Oracle Cloud Infrastructure 2026 Architect Professional. Price: $245. Add to cart."),
        ("$245.00", "Oracle Database Administrator Specialist. Standard checkout fee: $245.00."),
        ("$150", "AWS Certified Solutions Architect - Associate (SAA-C03). Exam fee: $150. Add to cart."),
        ("$165", "Microsoft Certified: Azure Administrator Associate (AZ-104). Fee: $165. Schedule exam."),
        ("$300", "AWS Certified Solutions Architect - Professional (SAP-C02). Registration fee: $300. Buy exam now."),
        ("$300.00", "Cisco Certified Network Associate (CCNA 200-301). Cost: $300.00. Add to cart."),
        ("$375", "Certified Kubernetes Administrator (CKA). Catalog registration: $375. Purchase exam."),
        ("$395", "Linux Foundation Certified System Administrator (LFCS). Price: $395. Buy exam."),
        ("$99", "Cloud Foundations Exam Voucher. Price: $99. Enter credit card to purchase."),
    ]
)
def test_adversarial_paid_catalog_standard_fees(fee_str: str, vendor_context: str):
    """
    Empirical Invariant: Commercial checkout fees ($245, $150, $165, $300, $375, $395, $99)
    without affirmative zero-dollar waiver signals must trigger 'Review Needed' with paid_catalog_detected=True.
    """
    res = inspect_rendered_dom(vendor_context, rendered_title="Exam Checkout Catalog")

    assert res["status"] != "Active", (
        f"CRITICAL DEFECT: Standard paid exam fee '{fee_str}' falsely marked as 'Active'!"
    )
    assert res["status"] == "Review Needed", f"Expected 'Review Needed', got '{res['status']}'"
    assert res["is_paid_catalog"] is True, "is_paid_catalog must be True"
    assert res["paid_catalog_detected"] is True, "paid_catalog_detected must be True"
    assert res["zero_dollar_confirmed"] is False, "zero_dollar_confirmed must be False"
    assert res["category"] == "paid_catalog"

    # Dual gate cascade:
    gate_status, _ = evaluate_dual_gate(
        dom_status=res["status"],
        has_zero_dollar=res["zero_dollar_confirmed"],
        screenshot_valid=True
    )
    assert gate_status != "Active", "Dual gate failed to reject paid catalog"


@pytest.mark.parametrize(
    "deceptive_text",
    [
        "Create a free Oracle account to purchase exam vouchers. Standard price: $245. Add to cart.",
        "Sign up for a free student membership and buy exam for $300 with Pearson VUE.",
        "Free study guide and video lectures included when you purchase exam for $245.",
        "Claim your free attendance badge, then enter credit card to purchase exam ($150).",
        "Complimentary documentation access. Standard exam registration fee is $375. Add to cart.",
        "Free community access! Buy exam voucher for $395 to schedule with Kryterion.",
        "Free practice tests available. Purchase your certification exam for $165 today.",
    ]
)
def test_adversarial_paid_catalog_deceptive_free_phrasing(deceptive_text: str):
    """
    Empirical Invariant: Deceptive marketing pages mentioning 'free account', 'free study guide',
    or 'free badge' alongside a commercial checkout fee ($245, $300, etc.) must NEVER bypass
    the paid catalog filter to become 'Active'.
    """
    res = inspect_rendered_dom(deceptive_text, rendered_title="Vendor Catalog Checkout")

    assert res["status"] != "Active", (
        f"CRITICAL DEFECT: Deceptive 'free' phrasing bypassed paid catalog barrier! Text: '{deceptive_text}'"
    )
    assert res["status"] == "Review Needed"
    assert res["paid_catalog_detected"] is True
    assert res["zero_dollar_confirmed"] is False


# ==============================================================================
# 3. Active Zero-Dollar Waiver Recognition Edge Cases
# ==============================================================================

@pytest.mark.parametrize(
    "active_waiver_text,expected_phrase",
    [
        (
            "Oracle Cloud Infrastructure Architect. Standard fee: $245. "
            "Use promo code OCI-CHALLENGE for 100% discount. Order total: $0.00.",
            "$0.00"
        ),
        (
            "AWS Certified Solutions Architect Associate ($150 standard). "
            "All Builders Welcome fee waiver applied. Checkout cart balance: $0.00 USD.",
            "fee waiver"
        ),
        (
            "Microsoft Certified: Azure Administrator ($165). "
            "Cloud Skills Challenge 100% off voucher applied. Amount due: $0.00.",
            "100% off"
        ),
        (
            "Certified Kubernetes Administrator (CKA, regular $375). "
            "LiFT Scholarship recipient: zero-dollar confirmed. Order total: $0.00.",
            "zero-dollar"
        ),
        (
            "Cisco CCNA (standard $300 registration fee). "
            "Women in Networking sponsored seat: complimentary voucher applied. Cart balance: 0.00 usd.",
            "sponsored seat"
        ),
        (
            "Linux Foundation LFCS ($395). Official challenge voucher: 100% free exam. Total: $0.00.",
            "challenge voucher"
        ),
        (
            "Oracle GenAI Professional ($245 standard). "
            "Race to Certification: zero cost exam waiver code applied. Balance: $0.00.",
            "zero cost"
        ),
    ]
)
def test_adversarial_zero_dollar_waiver_overrides_catalog_price(active_waiver_text: str, expected_phrase: str):
    """
    Empirical Invariant: When an authentic zero-dollar waiver or 100% discount is present
    alongside a standard catalog price ($245, $300, etc.), the engine MUST recognize the
    legitimate promotion and classify the offer as 'Active'.
    """
    res = inspect_rendered_dom(active_waiver_text, rendered_title="Promotional Checkout")

    assert res["status"] == "Active", (
        f"FALSE NEGATIVE: Legitimate 100% waiver was falsely rejected! Got: {res}"
    )
    assert res["zero_dollar_confirmed"] is True, "zero_dollar_confirmed must be True"
    assert res["is_paid_catalog"] is False, "is_paid_catalog must remain False when waived"
    assert res["paid_catalog_detected"] is False, "paid_catalog_detected must be False when waived"

    # Verify that dual gate validates Active when screenshot is valid
    gate_status, gate_reason = evaluate_dual_gate(
        dom_status=res["status"],
        has_zero_dollar=res["zero_dollar_confirmed"],
        screenshot_valid=True,
        auth_score=95
    )
    assert gate_status == "Active", f"Dual gate failed to confirm Active status: {gate_reason}"


@pytest.mark.parametrize(
    "partial_discount_text",
    [
        "Standard exam fee is $245. Use code SAVE50 for 50% discount. Remaining balance: $122.50. Add to cart.",
        "AWS Associate exam ($150). Save 25% with Cyber Monday discount coupon. Total: $112.50. Add to cart.",
        "Certified Kubernetes Administrator ($375). Black Friday 40% off code applied. Due today: $225.00.",
        "Standard exam price: $300. Student partial discount: $100 off. Final price: $200. Purchase exam.",
    ]
)
def test_adversarial_partial_discount_is_not_active(partial_discount_text: str):
    """
    Empirical Invariant: Partial discounts (50% off, $100 off, balance > $0.00) must NEVER
    be certified as 'Active' zero-dollar offers. They must resolve to 'Review Needed'.
    """
    res = inspect_rendered_dom(partial_discount_text, rendered_title="Partial Discount Checkout")

    assert res["status"] != "Active", (
        f"CRITICAL DEFECT: Partial discount falsely certified as 'Active' free voucher! {res}"
    )
    assert res["status"] == "Review Needed"
    assert res["zero_dollar_confirmed"] is False


# ==============================================================================
# 4. Missing or Corrupt Screenshot Dual Gate Degradation Suite
# ==============================================================================

def test_adversarial_dual_gate_missing_screenshot():
    """
    Empirical Invariant: If DOM is confirmed 'Active' with zero-dollar waiver,
    but the visual screenshot is missing (screenshot_valid=False),
    the dual gate MUST downgrade status to 'Review Needed'.
    """
    status, reason = evaluate_dual_gate(
        dom_status="Active",
        has_zero_dollar=True,
        screenshot_valid=False,
        auth_score=95
    )
    assert status == "Review Needed", f"Expected 'Review Needed', got '{status}'"
    assert "Visual Proof Gate Invariant" in reason, f"Reason must cite Visual Proof Gate: {reason}"


def test_adversarial_dual_gate_authenticity_threshold():
    """
    Empirical Invariant: If DOM and screenshot are both valid, but authenticity score
    drops below 80, the offer must be downgraded to 'Review Needed'.
    """
    # Score 79 (below threshold) -> Review Needed
    status_79, reason_79 = evaluate_dual_gate(
        dom_status="Active",
        has_zero_dollar=True,
        screenshot_valid=True,
        auth_score=79
    )
    assert status_79 == "Review Needed"
    assert "Authenticity score below threshold" in reason_79

    # Score 80 (exact threshold) -> Active
    status_80, _ = evaluate_dual_gate(
        dom_status="Active",
        has_zero_dollar=True,
        screenshot_valid=True,
        auth_score=80
    )
    assert status_80 == "Active"


def test_adversarial_screenshot_file_corruption_modes(tmp_path: Path):
    """
    Empirical Invariant: Tests all physical screenshot corruption modes:
    1. Missing file -> invalid
    2. Empty file (0 bytes) -> invalid
    3. Truncated file (< 4096 bytes) -> invalid
    4. Corrupt header (wrong magic bytes, >= 4096 bytes) -> invalid
    5. Valid PNG (magic bytes + >= 4096 bytes) -> valid
    """
    # 1. Missing file
    missing_file = tmp_path / "nonexistent.png"
    ok, err = verify_png_file_integrity(missing_file)
    assert not ok and "does not exist" in err

    # 2. Empty file (0 bytes)
    empty_file = tmp_path / "empty.png"
    empty_file.write_bytes(b"")
    ok, err = verify_png_file_integrity(empty_file)
    assert not ok and "below minimum threshold" in err

    # 3. Truncated file (< 4096 bytes with valid header)
    truncated_file = tmp_path / "truncated.png"
    truncated_file.write_bytes(PNG_MAGIC_BYTES + b"\x00" * 500)
    ok, err = verify_png_file_integrity(truncated_file)
    assert not ok and "below minimum threshold" in err

    # 4. Corrupt header (>= 4096 bytes, but ASCII/JPEG/GIF header)
    corrupt_header_file = tmp_path / "corrupt_header.png"
    corrupt_header_file.write_bytes(b"GIF89a\x00\x00" + b"\x00" * 5000)
    ok, err = verify_png_file_integrity(corrupt_header_file)
    assert not ok and "Invalid magic header" in err

    # 5. One-bit mutated header
    bit_flip_file = tmp_path / "bit_flip.png"
    bit_flip_file.write_bytes(b"\x89PNH\r\n\x1a\n" + b"\x00" * 5000)
    ok, err = verify_png_file_integrity(bit_flip_file)
    assert not ok and "Invalid magic header" in err

    # 6. Valid PNG
    valid_file = tmp_path / "valid.png"
    valid_file.write_bytes(PNG_MAGIC_BYTES + b"\x00" * 5000)
    ok, msg = verify_png_file_integrity(valid_file)
    assert ok is True and msg == "Valid PNG"


def test_adversarial_downgrade_when_live_screenshot_corrupted(tmp_path: Path):
    """
    Simulates an offer that passes DOM inspection but has a corrupted screenshot on disk.
    Verifies that dual gate downgrades the offer to 'Review Needed'.
    """
    # Create corrupted screenshot on disk
    corrupt_shot = tmp_path / "corrupt-shot.png"
    corrupt_shot.write_bytes(b"CORRUPTED_TEXT_NOT_A_PNG" * 200)

    is_valid, _ = verify_png_file_integrity(corrupt_shot)
    assert is_valid is False

    # Pass to dual gate
    status, reason = evaluate_dual_gate(
        dom_status="Active",
        has_zero_dollar=True,
        screenshot_valid=is_valid,
        auth_score=95
    )
    assert status == "Review Needed"
    assert "Visual Proof Gate Invariant" in reason


# ==============================================================================
# 5. Production Screenshot Artifact Byte-Level Integrity Audit
# ==============================================================================

def test_adversarial_production_screenshots_all_offers_covered():
    """
    Empirical Invariant: Asserts that EVERY single tracked offer in data/offers.json:
    1. Has a defined screenshot_path in 'docs/screenshots/<id>.png'.
    2. The physical screenshot file exists in docs/screenshots/.
    3. The file size is strictly >= 4096 bytes.
    4. The file begins with exact 8-byte PNG magic bytes b'\\x89PNG\\r\\n\\x1a\\n'.
    5. Zero broken or placeholder screenshots exist for any tracked offer.
    """
    assert DATA_FILE.exists(), f"Missing data file: {DATA_FILE}"
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    offers = data.get("offers", [])
    assert len(offers) > 0, "Expected non-empty offers list"

    failed_offers = []
    for o in offers:
        oid = o.get("id")
        shot_path_str = o.get("screenshot_path", f"docs/screenshots/{oid}.png")
        assert shot_path_str.startswith("docs/screenshots/"), (
            f"Offer {oid} has invalid screenshot_path format: {shot_path_str}"
        )
        
        target_file = ROOT / shot_path_str
        is_valid, err_msg = verify_png_file_integrity(target_file)
        if not is_valid:
            failed_offers.append((oid, shot_path_str, err_msg))

    assert len(failed_offers) == 0, (
        f"Production screenshot integrity check failed for {len(failed_offers)} offers: {failed_offers}"
    )


def test_adversarial_empty_and_whitespace_dom_rejection():
    """
    Empirical Invariant: White-space only, empty, or unhydrated DOMs must NEVER
    be certified as 'Active'.
    """
    whitespace_samples = ["", "   ", "\n\t\r  \n", "<html><body>   </body></html>"]
    for s in whitespace_samples:
        res = inspect_rendered_dom(s)
        assert res["status"] == "Review Needed"
        assert res["zero_dollar_confirmed"] is False
        assert res["category"] in {"empty_dom", "no_offer_signal"}


# ==============================================================================
# 6. End-to-End Headless DOM Fixture Tests with inspect_offer()
# ==============================================================================

def test_adversarial_inspect_offer_synthetic_maintenance_fixture(tmp_path: Path):
    """
    Empirical Invariant: inspect_offer() running against a local HTML maintenance fixture
    must never output status='Active' and must flag maintenance_detected=True.
    """
    maint_html = tmp_path / "oracle_maint.html"
    maint_html.write_text(
        "<!DOCTYPE html><html><head><title>Oracle University Maintenance</title></head>"
        "<body><h1>Our website is currently down for maintenance</h1>"
        "<p>Free certification exams will resume when maintenance is completed.</p>"
        "</body></html>",
        encoding="utf-8"
    )

    test_offer = {
        "id": "synthetic-maint-offer",
        "title": "Oracle Synthetic Maintenance",
        "url": maint_html.as_uri(),
        "status": "Active"
    }

    result = inspect_offer(test_offer)

    assert result["status"] != "Active", (
        f"CRITICAL DEFECT: inspect_offer certified maintenance page as Active: {result}"
    )
    assert result["status"] in {"Review Needed", "Server Error"}
    assert result["maintenance_detected"] is True
    assert result["visual_proof"]["maintenance_detected"] is True
    assert result["visual_proof"]["zero_dollar_confirmed"] is False

    # Cleanup any generated synthetic screenshot
    shot_file = ROOT / "docs" / "screenshots" / "synthetic-maint-offer.png"
    if shot_file.exists():
        shot_file.unlink()


def test_adversarial_inspect_offer_synthetic_paid_catalog_fixture(tmp_path: Path):
    """
    Empirical Invariant: inspect_offer() running against a local HTML paid catalog fixture
    ($300 standard fee, add to cart, without waiver) must resolve to 'Review Needed'
    with paid_catalog_detected=True.
    """
    catalog_html = tmp_path / "cisco_catalog.html"
    catalog_html.write_text(
        "<!DOCTYPE html><html><head><title>Cisco CCNA Catalog</title></head>"
        "<body><h1>Cisco Certified Network Associate CCNA</h1>"
        "<p>Standard registration fee is $300. Buy exam now. Add to cart.</p>"
        "<p>Sign up for a free student profile to manage your booking.</p>"
        "</body></html>",
        encoding="utf-8"
    )

    test_offer = {
        "id": "synthetic-paid-offer",
        "title": "Cisco CCNA Synthetic Catalog",
        "url": catalog_html.as_uri(),
        "status": "Active"
    }

    result = inspect_offer(test_offer)

    assert result["status"] != "Active", (
        f"CRITICAL DEFECT: inspect_offer certified paid catalog as Active: {result}"
    )
    assert result["status"] == "Review Needed"
    assert result["paid_catalog_detected"] is True
    assert result["visual_proof"]["paid_catalog_detected"] is True
    assert result["visual_proof"]["zero_dollar_confirmed"] is False

    shot_file = ROOT / "docs" / "screenshots" / "synthetic-paid-offer.png"
    if shot_file.exists():
        shot_file.unlink()


def test_adversarial_inspect_offer_synthetic_active_waiver_fixture(tmp_path: Path):
    """
    Empirical Invariant: inspect_offer() running against a local HTML fixture with
    standard fee ($245) AND confirmed 100% discount ($0.00 cart balance) must be
    certified as 'Active' with valid visual proof metadata.
    """
    waiver_html = tmp_path / "oci_waiver.html"
    waiver_html.write_text(
        "<!DOCTYPE html><html><head><title>OCI Free Challenge 2026</title></head>"
        "<body><h1>Oracle Cloud Infrastructure Associate</h1>"
        "<p>Standard exam fee is $245. OCI Challenge promo code applied for 100% discount. "
        "Total cart balance: $0.00. Schedule your free exam voucher now.</p>"
        "</body></html>",
        encoding="utf-8"
    )

    test_offer = {
        "id": "synthetic-active-waiver",
        "title": "OCI Free Challenge Active",
        "url": waiver_html.as_uri(),
        "status": "Review Needed"
    }

    result = inspect_offer(test_offer)

    try:
        assert result["status"] == "Active", (
            f"FAILED: Active waiver was not certified Active: {result}"
        )
        assert result["visual_proof"]["zero_dollar_confirmed"] is True
        assert result["maintenance_detected"] is False
        assert result["paid_catalog_detected"] is False

        # Assert visual screenshot was generated and is valid
        shot_file = ROOT / "docs" / "screenshots" / "synthetic-active-waiver.png"
        assert shot_file.exists(), "Screenshot was not generated"
        is_valid, msg = verify_png_file_integrity(shot_file)
        assert is_valid is True, f"Generated screenshot invalid: {msg}"
    finally:
        shot_file = ROOT / "docs" / "screenshots" / "synthetic-active-waiver.png"
        if shot_file.exists():
            shot_file.unlink()


def test_adversarial_inspect_offer_missing_screenshot_downgrade(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """
    Empirical Invariant: If a page has valid active zero-dollar terms, but
    screenshot capture fails (e.g. browser crash or disk error), inspect_offer()
    must downgrade the offer from 'Active' to 'Review Needed'.
    """
    from src.dom_inspector import HeadlessDOMInspector

    waiver_html = tmp_path / "active_promo.html"
    waiver_html.write_text(
        "<!DOCTYPE html><html><head><title>Active Voucher</title></head>"
        "<body><h1>100% free exam voucher. Balance: $0.00.</h1></body></html>",
        encoding="utf-8"
    )

    # Monkeypatch capture_screenshot to simulate capture failure
    def mock_capture_failure(self, page, offer_id):
        return False, f"docs/screenshots/{offer_id}.png"

    monkeypatch.setattr(HeadlessDOMInspector, "capture_screenshot", mock_capture_failure)

    test_offer = {
        "id": "synthetic-failed-screenshot",
        "title": "Active Promo with Failed Screenshot",
        "url": waiver_html.as_uri(),
        "status": "Active"
    }

    result = inspect_offer(test_offer)

    assert result["status"] == "Review Needed", (
        f"Expected downgrade to 'Review Needed' when screenshot fails, got: {result['status']}"
    )
    assert "Visual Proof Gate Invariant" in result["reason"]
    assert result["visual_proof"]["status"] in {"missing", "failed"}

