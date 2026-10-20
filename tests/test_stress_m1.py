"""
Adversarial Stress Test Suite for Milestone 1 (Data Schema & URL Ground Truth).
Authored by Challenger 1 (EMPIRICAL CHALLENGER).

Tests rigorous boundary conditions, fuzzing, round-trip serialization invariance,
VisualProof lifecycle & transitions, CandidateLead vetting stubs,
and dataset ground-truth invariants for src/models.py and data/offers.json.
"""

import json
from pathlib import Path
import pytest
from pydantic import ValidationError

from src.models import (
    Offer,
    VisualProof,
    RedemptionGuide,
    CandidateLead,
    OffersDatabase,
    OfferDataDict,
)

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "offers.json"
CANDIDATES_FILE = ROOT / "data" / "candidates.json"

VALID_OFFER_PAYLOAD = {
    "id": "stress-test-voucher",
    "title": "Stress Testing Professional Exam Voucher",
    "platform": "AWS",
    "category": "Cloud Architecture",
    "certification_name": "AWS Certified Solutions Architect",
    "credential_tier": "proctored_exam",
    "proctoring_type": "pearson_vue",
    "accredited_body": "Pearson VUE",
    "url": "https://aws.amazon.com/certification/",
    "verified_vendor_url": "https://aws.amazon.com/certification/certified-solutions-architect-associate/",
    "status": "Active",
    "seasonality": "periodic_challenge_wave",
    "value_usd": 150,
    "difficulty_tier": "Associate",
    "eligibility": "Global candidates",
    "time_period": "Q4 2026",
    "recurrence_pattern": "Quarterly",
    "application_flow_type": "Checkout Promo Code",
    "redemption_portal": "https://www.pearsonvue.com/aws",
    "checkout_field": "Promo Code",
    "cart_balance_verified": "$0.00 (100% Free / Waiver Confirmed)",
    "voucher_code": "AWSCHALLENGE2026",
    "claim_steps": "Apply promo code at Pearson VUE checkout.",
    "is_authentic_vendor": True,
    "authenticity_score": 95,
}


# ==============================================================================
# SECTION 1: FUZZING ENUMS, LITERALS & BOUNDARY VALUES
# ==============================================================================

class TestModelFuzzing:
    """Stress tests input validation and error boundaries in Offer and VisualProof."""

    @pytest.mark.parametrize("bad_tier", [
        "", "exam", "proctored", "badge", "PROCTORED_EXAM", "skill-badge",
        "proctored_exam ", " skill_badge_lab", None, 123, True, [], {}
    ])
    def test_fuzz_invalid_credential_tier(self, bad_tier):
        """credential_tier must strictly accept only 'proctored_exam' or 'skill_badge_lab'."""
        payload = {**VALID_OFFER_PAYLOAD, "credential_tier": bad_tier}
        with pytest.raises(ValidationError) as exc_info:
            Offer(**payload)
        assert "credential_tier" in str(exc_info.value)

    @pytest.mark.parametrize("bad_proctoring", [
        "", "prometric", "vue", "kryterion_online", "online",
        "PEARSON_VUE", None, 123, False, ["pearson_vue"], {"type": "pearson_vue"}
    ])
    def test_fuzz_invalid_proctoring_type(self, bad_proctoring):
        """proctoring_type must strictly enforce the closed enum."""
        payload = {**VALID_OFFER_PAYLOAD, "proctoring_type": bad_proctoring}
        with pytest.raises(ValidationError) as exc_info:
            Offer(**payload)
        assert "proctoring_type" in str(exc_info.value)

    @pytest.mark.parametrize("bad_seasonality", [
        "", "seasonal", "quarterly", "daily", "EVERGREEN",
        "rolling", None, 999, False, "annual"
    ])
    def test_fuzz_invalid_seasonality(self, bad_seasonality):
        """seasonality must strictly enforce the closed seasonality enum."""
        payload = {**VALID_OFFER_PAYLOAD, "seasonality": bad_seasonality}
        with pytest.raises(ValidationError) as exc_info:
            Offer(**payload)
        assert "seasonality" in str(exc_info.value)

    @pytest.mark.parametrize("bad_status", [
        "", "active", "ACTIVE", "Pending", "Deleted", "Archived",
        None, 0, True, "Draft", "Disabled"
    ])
    def test_fuzz_invalid_offer_status(self, bad_status):
        """status must strictly adhere to OfferStatus literal values."""
        payload = {**VALID_OFFER_PAYLOAD, "status": bad_status}
        with pytest.raises(ValidationError) as exc_info:
            Offer(**payload)
        assert "status" in str(exc_info.value)

    @pytest.mark.parametrize("bad_id", [
        "", "a", "ab",  # Too short (<3)
        "a" * 65,  # Too long (>64)
        "HAS_UPPERCASE",  # Non-lowercase
        "spaces in id",
        "has_underscores_invalid",  # Only hyphens allowed in slug pattern ^[a-z0-9-]+$
        "has.dots",
        "has/slashes",
        "has@symbols",
        None,
        12345,
    ])
    def test_fuzz_invalid_id_slug(self, bad_id):
        """id must strictly be a lowercase alphanumeric slug with hyphens, 3-64 chars."""
        payload = {**VALID_OFFER_PAYLOAD, "id": bad_id}
        with pytest.raises(ValidationError) as exc_info:
            Offer(**payload)
        assert "id" in str(exc_info.value)

    @pytest.mark.parametrize("bad_url", [
        "", "http://insecure-domain.org/exam", "ftp://files.example.com",
        "javascript:alert(1)", "file:///etc/passwd", "relative/path/to/page",
        "www.amazon.com", None, 1234
    ])
    def test_fuzz_invalid_urls(self, bad_url):
        """url must strictly begin with https:// protocol."""
        payload = {**VALID_OFFER_PAYLOAD, "url": bad_url}
        with pytest.raises(ValidationError) as exc_info:
            Offer(**payload)
        assert "url" in str(exc_info.value)

    @pytest.mark.parametrize("bad_balance", [
        "", "$245.00 Standard Checkout", "FREE", "100% DISCOUNT",
        "$0", "0.00", "Zero Dollars", "Free Tier ($50.00)", "$199 Exam Voucher"
    ])
    def test_fuzz_cart_balance_zero_dollar_requirement(self, bad_balance):
        """cart_balance_verified must strictly confirm '$0.00'."""
        payload = {**VALID_OFFER_PAYLOAD, "cart_balance_verified": bad_balance}
        with pytest.raises(ValidationError) as exc_info:
            Offer(**payload)
        assert "cart_balance_verified" in str(exc_info.value)

    @pytest.mark.parametrize("bad_score", [
        -1, -100, 101, 200, "not_a_number", None, [90], {"score": 95}
    ])
    def test_fuzz_authenticity_score_bounds(self, bad_score):
        """authenticity_score must be an integer between 0 and 100."""
        payload = {**VALID_OFFER_PAYLOAD, "authenticity_score": bad_score}
        with pytest.raises(ValidationError) as exc_info:
            Offer(**payload)
        assert "authenticity_score" in str(exc_info.value)

    @pytest.mark.parametrize("bad_usd", [
        -1, -100, "not_a_number", [150], {"value": 150}
    ])
    def test_fuzz_value_usd_bounds(self, bad_usd):
        """value_usd must be >= 0 when provided."""
        payload = {**VALID_OFFER_PAYLOAD, "value_usd": bad_usd}
        with pytest.raises(ValidationError) as exc_info:
            Offer(**payload)
        assert "value_usd" in str(exc_info.value)

    @pytest.mark.parametrize("missing_field", [
        "id", "title", "platform", "category", "certification_name",
        "credential_tier", "url"
    ])
    def test_missing_mandatory_fields_rejected(self, missing_field):
        """Omitting any mandatory field must immediately trigger ValidationError."""
        payload = {k: v for k, v in VALID_OFFER_PAYLOAD.items() if k != missing_field}
        with pytest.raises(ValidationError) as exc_info:
            Offer(**payload)
        assert missing_field in str(exc_info.value)


# ==============================================================================
# SECTION 2: ROUND-TRIP SERIALIZATION & DATA INVARIANCE
# ==============================================================================

class TestSerializationRoundTrip:
    """Tests lossless round-trip serialization across dict, JSON, and Pydantic models."""

    def test_synthetic_offer_round_trip(self):
        """Tests Offer -> model_dump() -> Offer(**dict) -> json.dumps -> json.loads -> Offer(**dict)."""
        original = Offer(**VALID_OFFER_PAYLOAD)

        # 1. model_dump round-trip
        dumped_dict = original.model_dump()
        restored_from_dict = Offer(**dumped_dict)
        assert restored_from_dict.id == original.id
        assert restored_from_dict.credential_tier == original.credential_tier
        assert restored_from_dict.proctoring_type == original.proctoring_type
        assert restored_from_dict.seasonality == original.seasonality
        assert restored_from_dict.status == original.status
        assert restored_from_dict.visual_proof.screenshot_path == original.visual_proof.screenshot_path

        # 2. json.dumps -> json.loads round-trip
        dumped_json_str = json.dumps(dumped_dict)
        parsed_json_dict = json.loads(dumped_json_str)
        restored_from_json = Offer(**parsed_json_dict)
        assert restored_from_json.id == original.id
        assert restored_from_json.credential_tier == original.credential_tier
        assert restored_from_json.visual_proof.zero_dollar_confirmed == original.visual_proof.zero_dollar_confirmed
        assert restored_from_json == original

    def test_all_dataset_offers_round_trip(self):
        """Tests that all offers in data/offers.json survive 100% lossless serialization round-trips."""
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        raw_offers = raw_data.get("offers", [])
        assert len(raw_offers) > 0

        for raw_o in raw_offers:
            o1 = Offer(**raw_o)
            d1 = o1.model_dump(mode="json")
            json_str = json.dumps(d1)
            d2 = json.loads(json_str)
            o2 = Offer(**d2)

            # Invariant equality
            assert o1.id == o2.id
            assert o1.title == o2.title
            assert o1.credential_tier == o2.credential_tier
            assert o1.proctoring_type == o2.proctoring_type
            assert o1.status == o2.status
            assert o1.seasonality == o2.seasonality
            assert o1.url == o2.url
            assert o1.verified_vendor_url == o2.verified_vendor_url
            assert o1.visual_proof.screenshot_path == o2.visual_proof.screenshot_path
            assert o1.visual_proof.status == o2.visual_proof.status
            assert o1.visual_proof.zero_dollar_confirmed == o2.visual_proof.zero_dollar_confirmed

    def test_offers_database_container_round_trip(self):
        """Tests OffersDatabase full container serialization."""
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        db1 = OffersDatabase(**raw_data)
        assert len(db1.offers) == len(raw_data["offers"])

        dumped = db1.model_dump(mode="json", by_alias=True)
        assert "$schema" in dumped
        assert dumped["$schema"] == "./schema.json"
        assert len(dumped["offers"]) == len(raw_data["offers"])

        db2 = OffersDatabase(**dumped)
        assert len(db2.offers) == len(raw_data["offers"])
        assert db2.schema_version == db1.schema_version


# ==============================================================================
# SECTION 3: VISUAL PROOF DEFAULTS & STATUS TRANSITIONS
# ==============================================================================

class TestVisualProofLifecycle:
    """Stress tests VisualProof defaults, auto-initialization, and validation invariants."""

    def test_visual_proof_auto_initialization(self):
        """When visual_proof is omitted from Offer kwargs, it is cleanly populated."""
        payload = {k: v for k, v in VALID_OFFER_PAYLOAD.items() if k not in ["visual_proof", "screenshot_path"]}
        offer = Offer(**payload)

        assert offer.visual_proof is not None
        assert offer.visual_proof.screenshot_path == "docs/screenshots/stress-test-voucher.png"
        assert offer.visual_proof.screenshot_url == "docs/screenshots/stress-test-voucher.png"
        assert offer.visual_proof.status == "placeholder"
        assert offer.visual_proof.zero_dollar_confirmed is True
        assert offer.visual_proof.maintenance_detected is False
        assert offer.visual_proof.paid_catalog_detected is False
        assert offer.screenshot_path == "docs/screenshots/stress-test-voucher.png"
        # Since status is placeholder, is_verified must be False
        assert offer.visual_proof.is_verified is False

    def test_visual_proof_explicit_override(self):
        """When visual_proof is explicitly passed, it is respected and synced."""
        custom_proof = VisualProof(
            screenshot_path="custom/path/proof.png",
            status="verified",
            zero_dollar_confirmed=True,
            maintenance_detected=False,
            paid_catalog_detected=False,
        )
        payload = {**VALID_OFFER_PAYLOAD, "visual_proof": custom_proof}
        offer = Offer(**payload)

        assert offer.visual_proof.screenshot_path == "custom/path/proof.png"
        assert offer.screenshot_path == "custom/path/proof.png"
        assert offer.visual_proof.status == "verified"
        assert offer.visual_proof.is_verified is True

    @pytest.mark.parametrize("status,zero_dollar,maintenance,paid_catalog,expected_verified", [
        ("verified", True, False, False, True),
        ("verified", False, False, False, False),   # $0 not confirmed
        ("verified", True, True, False, False),    # Maintenance detected
        ("verified", True, False, True, False),    # Paid catalog detected
        ("verified", True, True, True, False),     # Both anomalies detected
        ("placeholder", True, False, False, False), # Placeholder not yet verified
        ("missing", True, False, False, False),     # Missing screenshot
        ("failed", True, False, False, False),      # Screenshot capture failed
        ("placeholder", False, True, True, False),
    ])
    def test_visual_proof_is_verified_truth_table(
        self, status, zero_dollar, maintenance, paid_catalog, expected_verified
    ):
        """Exhaustively verifies the boolean truth table for VisualProof.is_verified."""
        vp = VisualProof(
            screenshot_path="docs/screenshots/test.png",
            status=status,
            zero_dollar_confirmed=zero_dollar,
            maintenance_detected=maintenance,
            paid_catalog_detected=paid_catalog,
        )
        assert vp.is_verified is expected_verified

    @pytest.mark.parametrize("invalid_status", [
        "active", "pending", "success", "error", "done", None, 123
    ])
    def test_visual_proof_invalid_status_rejected(self, invalid_status):
        """VisualProof status accepts only 'verified', 'missing', 'failed', 'placeholder'."""
        with pytest.raises(ValidationError):
            VisualProof(screenshot_path="docs/screenshots/test.png", status=invalid_status)


# ==============================================================================
# SECTION 4: CANDIDATE LEAD VETTING & STUB TRANSFORMATION
# ==============================================================================

class TestCandidateLeadVetting:
    """Tests CandidateLead parsing and transformation into Offer stubs."""

    def test_candidate_leads_from_file(self):
        """Verifies candidates.json parsing and stub generation."""
        with open(CANDIDATES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        leads = [CandidateLead(**l) for l in data.get("leads", [])]
        assert len(leads) > 0

        for idx, lead in enumerate(leads):
            stub = lead.to_offer_stub(f"lead-{idx}", credential_tier="proctored_exam")
            # Invariant: stub must instantiate a valid Offer directly
            candidate_offer = Offer(**stub)
            assert candidate_offer.id == f"lead-{idx}"
            assert candidate_offer.status == "Review Needed"
            assert candidate_offer.is_active() is False
            assert candidate_offer.visual_proof.is_verified is False
            assert candidate_offer.visual_proof.status == "placeholder"
            assert candidate_offer.credential_tier == "proctored_exam"


# ==============================================================================
# SECTION 5: DATASET GROUND-TRUTH & TAXONOMY INTEGRITY
# ==============================================================================

class TestDatasetGroundTruth:
    """Validates real data/offers.json invariants across all tracked certifications."""

    def test_dataset_size_and_taxonomy_split(self):
        """Asserts that all offers belong to a valid credential tier dynamically."""
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        offers = [Offer(**o) for o in data["offers"]]
        assert len(offers) > 0, "Offers database cannot be empty"

        proctored = [o for o in offers if o.credential_tier == "proctored_exam"]
        skill_badges = [o for o in offers if o.credential_tier == "skill_badge_lab"]

        assert len(proctored) + len(skill_badges) == len(offers)
        assert len(proctored) > 0
        assert len(skill_badges) > 0

    def test_no_credential_tier_crossover(self):
        """Asserts that unproctored badges never have accredited proctoring types."""
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        offers = [Offer(**o) for o in data["offers"]]
        accredited_proctors = {"pearson_vue", "kryterion", "webassessor", "psi"}

        for o in offers:
            if o.credential_tier == "skill_badge_lab":
                assert o.proctoring_type not in accredited_proctors, (
                    f"Anomaly: Skill badge '{o.id}' has formal proctoring type '{o.proctoring_type}'!"
                )
            elif o.credential_tier == "proctored_exam":
                assert o.is_proctored() is True

    def test_all_offer_urls_are_secure_https(self):
        """Asserts that all primary and verified vendor URLs use strict HTTPS."""
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        offers = [Offer(**o) for o in data["offers"]]
        for o in offers:
            assert o.url.startswith("https://"), f"Insecure URL on {o.id}: {o.url}"
            assert o.verified_vendor_url.startswith("https://"), f"Insecure verified URL on {o.id}: {o.verified_vendor_url}"

    def test_url_repair_regression_guard(self):
        """Asserts that previously broken/misleading URLs remain permanently repaired."""
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        offer_map = {o["id"]: Offer(**o) for o in data["offers"]}

        # 1. Oracle OCI must point to active Oracle Cloud landing URLs
        assert "oracle.com" in offer_map["oracle-oci-free-cert"].url
        assert "oracle.com" in offer_map["oracle-oci-generative-ai-cert"].url

        # 2. Databricks must not point to dead DNS academy.databricks.com
        assert "academy.databricks.com" not in offer_map["databricks-lakehouse-fundamentals"].url
        assert offer_map["databricks-lakehouse-fundamentals"].url == "https://www.databricks.com/learn/training/certification"

        # 3. Google Skills Boost must not point to generic marketing skills.google
        assert "skills.google" not in offer_map["gcp-cloud-skills-boost"].url
        assert offer_map["gcp-cloud-skills-boost"].url == "https://cloud.google.com/innovators"
        assert offer_map["gcp-cloud-skills-boost"].direct_verified_url == "https://go.cloudskillsboost.google/arcade"

        # 4. Linux Foundation LiFT must reflect annual_window seasonality
        assert offer_map["linux-foundation-lift"].seasonality == "annual_window"
        assert offer_map["linux-foundation-lift"].credential_tier == "proctored_exam"


# ==============================================================================
# SECTION 6: OFFERDATADICT BEHAVIOR & PYTHON INVARIANT AUDIT
# ==============================================================================

class TestOfferDataDictBehavior:
    """
    Stress-tests OfferDataDict and verifies absence of json.load monkey-patching in src/models.py.
    Audits whether standard Python dictionary contracts are preserved without global runtime mutation.
    """

    def test_offer_data_dict_iteration_vs_keys(self):
        """
        Adversarial inspection: Standard json.load must return a clean dict preserving list(d) == list(d.keys()).
        OfferDataDict provides helper accessors without breaking standard mapping contracts.
        """
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Invariant: json.load must NOT be monkeypatched into OfferDataDict globally
        assert type(data) is dict
        expected_required = {"$schema", "last_updated", "offers"}
        allowed_keys = {"$schema", "last_updated", "offers", "last_inspected", "last_truth_corroborated", "last_sync"}
        assert expected_required.issubset(set(data.keys()))
        assert set(data.keys()).issubset(allowed_keys)
        assert list(data) == list(data.keys())

        # Invariant: OfferDataDict container helper provides clean offers access
        odd = OfferDataDict(data)
        assert len(odd.offers) == len(data["offers"])
        assert len(odd.to_models()) == len(data["offers"])
        assert "$schema" in odd
        assert list(odd) == list(odd.keys())

    def test_offer_data_dict_json_dump_compatibility(self):
        """Ensures that json.dump and json.dumps continue to serialize the entire object with $schema and offers."""
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        serialized = json.dumps(data)
        parsed = json.loads(serialized)

        assert "$schema" in parsed
        assert "offers" in parsed
        assert len(parsed["offers"]) == len(data["offers"])


# ==============================================================================
# SECTION 7: REDEMPTION GUIDE SCHEMA VALIDATION
# ==============================================================================

class TestRedemptionGuideSchema:
    """Stress tests RedemptionGuide nested validation."""

    def test_redemption_guide_valid(self):
        rg = RedemptionGuide(
            portal_name="Pearson VUE",
            portal_url="https://www.pearsonvue.com",
            field_location="Voucher / Promotion Code",
            flow_type="Checkout Promo Code",
            verified_cart_balance="$0.00 (100% Free Waiver)",
            instructions=["Step 1", "Step 2"],
        )
        assert rg.portal_name == "Pearson VUE"
        assert "$0.00" in rg.verified_cart_balance

    @pytest.mark.parametrize("bad_flow", [
        "Credit Card Checkout", "In-Person Payment", "Free Form", None, 123
    ])
    def test_redemption_guide_invalid_flow(self, bad_flow):
        with pytest.raises(ValidationError):
            RedemptionGuide(
                portal_name="Pearson VUE",
                portal_url="https://www.pearsonvue.com",
                field_location="Promo",
                flow_type=bad_flow,
                verified_cart_balance="$0.00",
            )

    @pytest.mark.parametrize("bad_balance", [
        "$150.00", "FREE", "50% off", "$0.0", "Zero"
    ])
    def test_redemption_guide_invalid_balance(self, bad_balance):
        with pytest.raises(ValidationError):
            RedemptionGuide(
                portal_name="Pearson VUE",
                portal_url="https://www.pearsonvue.com",
                field_location="Promo",
                flow_type="Checkout Promo Code",
                verified_cart_balance=bad_balance,
            )

