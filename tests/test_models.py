"""
Unit tests for src/models.py and data/offers.json schema compliance.
Verifies all Milestone 1 invariants and Pydantic V2 validations.
"""

import json
from pathlib import Path
import pytest
from pydantic import ValidationError

from src.models import (
    Offer,
    VisualProof,
    CandidateLead,
    OffersDatabase,
    CredentialTier,
    ProctoringType,
    Seasonality,
    OfferDataDict,
)

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "offers.json"
CANDIDATES_FILE = ROOT / "data" / "candidates.json"


def test_offers_json_clean_parsing():
    """Validates that all offers in data/offers.json parse without error."""
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    total_count = len(data["offers"])
    assert total_count > 0, "Offers database cannot be empty"

    # Test OffersDatabase container model
    db = OffersDatabase(**data)
    assert len(db.offers) == total_count

    # Test explicit key lookup
    offers_key = [Offer(**o) for o in data["offers"]]
    assert len(offers_key) == total_count

    # Test .get() lookup
    offers_get = [Offer(**o) for o in data.get("offers", [])]
    assert len(offers_get) == total_count

    # Test OfferDataDict wrapper
    odd = OfferDataDict(data)
    assert len(odd.offers) == total_count
    assert len(odd.to_models()) == total_count


def test_credential_tier_distribution():
    """Asserts that every offer belongs to a valid credential tier dynamically."""
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    offers = [Offer(**o) for o in data["offers"]]
    proctored = [o for o in offers if o.credential_tier == "proctored_exam"]
    badges = [o for o in offers if o.credential_tier == "skill_badge_lab"]

    assert len(proctored) + len(badges) == len(offers), (
        f"Taxonomy defect: {len(offers) - (len(proctored) + len(badges))} offers have unrecognized credential_tier"
    )
    assert len(proctored) > 0, "Database must contain proctored exams"
    assert len(badges) > 0, "Database must contain skill badge labs"

    # Verify is_proctored() helper method
    for p in proctored:
        assert p.is_proctored() is True
    for b in badges:
        assert b.is_proctored() is False


def test_visual_proof_metadata():
    """Asserts that visual_proof is initialized correctly on every offer."""
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    offers = [Offer(**o) for o in data["offers"]]
    for o in offers:
        assert o.visual_proof is not None
        assert o.visual_proof.screenshot_path == f"docs/screenshots/{o.id}.png"
        assert o.screenshot_path == f"docs/screenshots/{o.id}.png"
        assert o.get_screenshot_path() == f"docs/screenshots/{o.id}.png"
        if o.status == "Active":
            assert o.visual_proof.zero_dollar_confirmed is True


def test_url_repairs_verified():
    """Asserts all audited repaired URLs are active and non-misleading."""
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    offer_map = {o["id"]: Offer(**o) for o in data["offers"]}

    # Oracle OCI verified vendor URLs
    assert "oracle.com" in offer_map["oracle-oci-free-cert"].url
    assert "oracle.com" in offer_map["oracle-oci-generative-ai-cert"].url

    # Databricks Lakehouse repaired from dead DNS academy.databricks.com
    assert offer_map["databricks-lakehouse-fundamentals"].url == "https://www.databricks.com/learn/training/certification"

    # Google Cloud Skills Boost repaired from misleading skills.google root
    assert offer_map["gcp-cloud-skills-boost"].url == "https://cloud.google.com/innovators"
    assert offer_map["gcp-cloud-skills-boost"].direct_verified_url == "https://go.cloudskillsboost.google/arcade"

    # Linux Foundation LiFT annual window seasonality
    assert offer_map["linux-foundation-lift"].seasonality == "annual_window"
    assert offer_map["linux-foundation-lift"].credential_tier == "proctored_exam"


def test_visual_proof_verification_logic():
    """Tests VisualProof is_verified property under various condition combinations."""
    vp_valid = VisualProof(
        screenshot_path="docs/screenshots/test.png",
        status="verified",
        zero_dollar_confirmed=True,
        maintenance_detected=False,
        paid_catalog_detected=False,
    )
    assert vp_valid.is_verified is True

    # Maintenance detection invalidates proof
    vp_maint = VisualProof(
        screenshot_path="docs/screenshots/test.png",
        status="verified",
        zero_dollar_confirmed=True,
        maintenance_detected=True,
        paid_catalog_detected=False,
    )
    assert vp_maint.is_verified is False

    # Paid catalog detection invalidates proof
    vp_paid = VisualProof(
        screenshot_path="docs/screenshots/test.png",
        status="verified",
        zero_dollar_confirmed=True,
        maintenance_detected=False,
        paid_catalog_detected=True,
    )
    assert vp_paid.is_verified is False

    # Missing zero dollar confirmation invalidates proof
    vp_no_free = VisualProof(
        screenshot_path="docs/screenshots/test.png",
        status="verified",
        zero_dollar_confirmed=False,
    )
    assert vp_no_free.is_verified is False

    # Placeholder status is not yet verified
    vp_placeholder = VisualProof(
        screenshot_path="docs/screenshots/test.png",
        status="placeholder",
    )
    assert vp_placeholder.is_verified is False


def test_candidate_lead_parsing_and_stub():
    """Asserts that CandidateLead parses candidate leads from candidates.json."""
    with open(CANDIDATES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    leads = [CandidateLead(**l) for l in data.get("leads", [])]
    assert len(leads) > 0

    valid_platforms = {"Microsoft Azure", "Amazon Web Services", "Multi-Cloud", "Google Cloud", "Oracle Cloud", "Cisco"}
    for lead in leads:
        assert lead.source.startswith("Reddit")
        assert lead.platform in valid_platforms, f"Unexpected platform '{lead.platform}' in candidate leads"
        assert lead.url.startswith("https://")
        stub = lead.to_offer_stub("candidate-test-id", credential_tier="proctored_exam")
        assert stub["id"] == "candidate-test-id"
        assert stub["credential_tier"] == "proctored_exam"
        assert stub["status"] == "Review Needed"
        assert stub["proctoring_type"] in {"pearson_vue", "unproctored_lab"}


def test_offer_strict_validation_rejections():
    """Asserts that malformed data is rejected with ValidationError."""
    valid_base = {
        "id": "valid-test-id",
        "title": "Valid Test Certification",
        "platform": "Microsoft Azure",
        "category": "Cloud Architecture",
        "certification_name": "Azure Administrator",
        "credential_tier": "proctored_exam",
        "url": "https://learn.microsoft.com/credentials",
        "cart_balance_verified": "$0.00 (100% Free / Waiver Confirmed)",
        "claim_steps": "Follow instructions to claim voucher.",
    }

    # 1. Invalid credential tier
    with pytest.raises(ValidationError):
        Offer(**{**valid_base, "credential_tier": "unknown_tier"})

    # 2. Invalid proctoring type
    with pytest.raises(ValidationError):
        Offer(**{**valid_base, "proctoring_type": "invalid_proctor"})

    # 3. Invalid seasonality
    with pytest.raises(ValidationError):
        Offer(**{**valid_base, "seasonality": "infinite_promo"})

    # 4. Non-HTTPS URL
    with pytest.raises(ValidationError):
        Offer(**{**valid_base, "url": "http://insecure.com"})

    # 5. Non-zero cart balance
    with pytest.raises(ValidationError):
        Offer(**{**valid_base, "cart_balance_verified": "$245.00 Standard Checkout"})


def test_offers_database_container():
    """Tests OffersDatabase container model."""
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    db = OffersDatabase(**data)
    assert len(db.offers) == len(data["offers"])
    assert len(db.offers) > 0
    assert db.schema_version == "./schema.json"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
