"""
Empirical Stress Test Suite for Dynamic Truth Oracle Policy Derivation.
Authored by challenger_m2_1 to empirically stress-test boundary conditions,
pathological inputs, dynamic derivation, and registry fallbacks.
"""

import json
import tempfile
from pathlib import Path
from typing import Dict, Any, List

import pytest

from src.truth_oracle import (
    TRUTH_POLICY_REGISTRY,
    CURATED_POLICY_OVERRIDES,
    POLICY_VERIFIED_100PCT_FREE,
    POLICY_STUDENT_VERIFIED_ONLY,
    POLICY_PARTIAL_DISCOUNT_COPAY,
    POLICY_ANNUAL_WINDOW_CLOSED,
    POLICY_HISTORICAL_EVENT_WAVE,
    POLICY_FREE_UNPROCTORED_BADGE,
    derive_truth_policy,
    build_dynamic_policy_registry,
    get_truth_policy,
    corroborate_offer,
)

ROOT = Path(__file__).resolve().parent.parent
OFFERS_FILE = ROOT / "data" / "offers.json"


@pytest.fixture(scope="module")
def canonical_offers() -> List[Dict[str, Any]]:
    assert OFFERS_FILE.exists(), f"Missing canonical offers file: {OFFERS_FILE}"
    with open(OFFERS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("offers", [])


class TestEmpiricalCanonicalInvariants:
    """Empirically asserts that all 39 canonical offers in data/offers.json produce valid truth policies."""

    def test_canonical_offer_count_is_exactly_39(self, canonical_offers):
        assert len(canonical_offers) == 39, f"Expected exactly 39 offers, got {len(canonical_offers)}"

    def test_all_39_offers_produce_valid_https_policies(self, canonical_offers):
        """Every canonical offer must derive a complete, valid truth policy with HTTPS truth source URL."""
        for offer in canonical_offers:
            oid = offer.get("id")
            assert oid, "Offer missing ID"
            policy = derive_truth_policy(offer)

            # Invariant 1: Top-level required keys
            for key in [
                "provider", "exam_name", "policy_type", "real_exam_cost_usd",
                "verified_discount_pct", "truth_source_name", "truth_source_url",
                "verdict_notes", "enforce_status", "category", "official_url",
                "domain", "authority_rules", "expected_verification_patterns"
            ]:
                assert key in policy, f"Offer '{oid}' missing policy key '{key}'"

            # Invariant 2: Truth source URL must be valid HTTPS
            ts_url = policy["truth_source_url"]
            assert ts_url.startswith("https://"), f"Offer '{oid}' truth_source_url is not HTTPS: {ts_url}"
            assert "." in ts_url, f"Offer '{oid}' truth_source_url missing domain dot: {ts_url}"

            # Invariant 3: Descriptive text length
            assert len(policy["truth_source_name"].strip()) >= 5, f"Offer '{oid}' truth_source_name too short"
            assert len(policy["verdict_notes"].strip()) >= 15, f"Offer '{oid}' verdict_notes too short"

            # Invariant 4: Financial realism
            assert policy["real_exam_cost_usd"] >= 0.0, f"Offer '{oid}' real_exam_cost_usd is negative"
            assert 0 <= policy["verified_discount_pct"] <= 100, f"Offer '{oid}' invalid discount pct"

            # Invariant 5: Authority rules schema
            auth = policy["authority_rules"]
            assert auth["requires_https"] is True
            assert isinstance(auth["allowed_domains"], list)

            # Invariant 6: Expected verification patterns
            exp = policy["expected_verification_patterns"]
            assert exp["status"] in [
                "Active", "Registrations Closed", "Expired", "Broken Link",
                "Review Needed", "Server Error", "Network Warning"
            ]
            assert isinstance(exp["zero_dollar_expected"], bool)


class TestEmpiricalDynamicDerivationNewOffers:
    """Stress-tests dynamic derivation for newly seen offers not in data/offers.json."""

    def test_unseen_new_offer_derives_and_registers_policy(self):
        new_id = "new-challenger-cloud-exam-2026"
        new_offer = {
            "id": new_id,
            "title": "Challenger Cloud Solutions Architect Associate",
            "company": "ChallengerCloud",
            "category": "Cloud Computing",
            "status": "Active",
            "credential_tier": "proctored_exam",
            "url": "https://challengercloud.example.org/certifications/solutions-architect",
            "cart_balance_verified": "$0.00 (100% Free / Waiver Confirmed)",
            "value_usd": 200.0,
        }

        # get_truth_policy must derive dynamically and cache in registry
        policy = get_truth_policy(new_id, offer=new_offer)
        assert policy["provider"] == "ChallengerCloud"
        assert policy["policy_type"] == POLICY_VERIFIED_100PCT_FREE
        assert policy["domain"] == "challengercloud.example.org"
        assert policy["truth_source_url"] == "https://challengercloud.example.org/certifications/solutions-architect"
        assert policy["real_exam_cost_usd"] == 0.0
        assert policy["verified_discount_pct"] == 100
        assert new_id in TRUTH_POLICY_REGISTRY

    def test_unseen_student_offer_derives_student_policy(self):
        student_id = "new-student-academic-pass"
        student_offer = {
            "id": student_id,
            "title": "Academic Database Developer Pass",
            "company": "AcademicDB",
            "category": "Database",
            "status": "Active",
            "credential_tier": "proctored_exam",
            "url": "https://academicdb.edu/students",
            "eligibility": "Verified Student Only (SheerID)",
        }
        policy = derive_truth_policy(student_offer)
        assert policy["policy_type"] == POLICY_STUDENT_VERIFIED_ONLY
        assert policy["truth_source_url"] == "https://academicdb.edu/students"

    def test_unseen_copay_offer_derives_copay_policy(self):
        copay_id = "new-network-copay-voucher"
        copay_offer = {
            "id": copay_id,
            "title": "Network Specialist Associate",
            "company": "NetCorp",
            "status": "Active",
            "url": "https://netcorp.com/voucher",
            "cart_balance_verified": "75% Discount applied with $50 Co-Pay required at Pearson VUE",
        }
        policy = derive_truth_policy(copay_offer)
        assert policy["policy_type"] == POLICY_PARTIAL_DISCOUNT_COPAY
        assert policy["real_exam_cost_usd"] == 50.0
        assert policy["verified_discount_pct"] == 75


class TestEmpiricalRegistryFallbacks:
    """Stress-tests build_dynamic_policy_registry under corrupt, empty, and nonexistent conditions."""

    def test_nonexistent_file_falls_back_without_crash(self):
        reg = build_dynamic_policy_registry("non_existent_offers_file_xyz_999.json")
        assert isinstance(reg, dict)
        assert len(reg) >= len(CURATED_POLICY_OVERRIDES)
        assert "isc2-one-million-cc" in reg

    def test_empty_offers_list_falls_back_without_crash(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({"offers": []}, f)
            temp_path = f.name
        try:
            reg = build_dynamic_policy_registry(temp_path)
            assert isinstance(reg, dict)
            assert len(reg) >= len(CURATED_POLICY_OVERRIDES)
            assert "juniper-open-learning" in reg
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_corrupt_json_file_falls_back_without_crash(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            f.write("{ INVALID JSON NOT PARSABLE ...")
            temp_path = f.name
        try:
            reg = build_dynamic_policy_registry(temp_path)
            assert isinstance(reg, dict)
            assert len(reg) >= len(CURATED_POLICY_OVERRIDES)
            assert "oracle-oci-free-cert" in reg
        finally:
            Path(temp_path).unlink(missing_ok=True)


class TestEmpiricalPathologicalInputs:
    """Stress-tests derive_truth_policy with minimal, missing, strange, and boundary inputs."""

    def test_empty_dictionary_input(self):
        policy = derive_truth_policy({})
        assert isinstance(policy, dict)
        assert policy["policy_type"] == POLICY_FREE_UNPROCTORED_BADGE
        assert policy["truth_source_url"] == "https://certpulse.org/truth"
        assert policy["provider"] == "Vendor"

    def test_minimal_dict_with_only_id(self):
        policy = derive_truth_policy({"id": "bare-minimum-id"})
        assert policy["policy_type"] == POLICY_FREE_UNPROCTORED_BADGE
        assert policy["truth_source_url"] == "https://certpulse.org/truth"

    def test_empty_category_and_empty_company(self):
        policy = derive_truth_policy({"id": "empty-fields", "category": "", "company": ""})
        assert policy["category"] == ""
        assert policy["truth_source_url"] == "https://certpulse.org/truth"

    @pytest.mark.parametrize("strange_url,expected_source_url", [
        ("javascript:alert(1)", "https://certpulse.org/truth"),
        ("mailto:support@certpulse.org", "https://certpulse.org/truth"),
        ("ftp://files.example.org/exam.pdf", "https://files.example.org"),
        ("not-a-valid-url-format", "https://certpulse.org/truth"),
        ("http://192.168.1.50:8080/portal", "https://192.168.1.50:8080"),
        ("http://10.0.0.1/cert", "https://10.0.0.1"),
        ("http://insecure.vendor.com/exam", "https://insecure.vendor.com"),
    ])
    def test_strange_urls_and_internal_ips(self, strange_url, expected_source_url):
        policy = derive_truth_policy({"id": "test-url", "url": strange_url, "company": "UrlVendor"})
        assert policy["truth_source_url"].startswith("https://")
        assert policy["truth_source_url"] == expected_source_url

    def test_missing_nested_metadata_dictionaries(self):
        """Omitting authenticity_details, visual_proof, and redemption_guide defaults safely."""
        policy = derive_truth_policy({
            "id": "test-no-nested",
            "url": "https://example.com/cert",
            "authenticity_details": None,
            "visual_proof": None,
            "redemption_guide": None,
        })
        assert policy["authority_rules"]["requires_https"] is True
        assert policy["expected_verification_patterns"]["zero_dollar_expected"] is True

    def test_adversarial_explicit_null_keys_behavior(self):
        """
        Documents empirical behavior when input dictionaries contain explicit None values
        (from raw untyped JSON deserialization).
        """
        # When 'id' is explicitly None, startswith fails
        with pytest.raises(AttributeError):
            derive_truth_policy({"id": None})

        # When 'platform' is explicitly None and 'company' is missing, provider is None and provider.lower() fails
        with pytest.raises(AttributeError):
            derive_truth_policy({"id": "test", "platform": None})

        # When 'url' is explicitly None and no other URL keys exist, official_url.startswith fails
        with pytest.raises(AttributeError):
            derive_truth_policy({"id": "test", "url": None})
