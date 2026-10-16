"""
Tests for Truth Oracle: Authoritative Online Policy Corroboration Engine.
Enforces mathematical invariants, online ground-truth alignment, and anti-misleading safeguards.
"""

import json
from pathlib import Path
from typing import Dict, Any, List

import pytest

from src.truth_oracle import (
    TRUTH_POLICY_REGISTRY,
    POLICY_VERIFIED_100PCT_FREE,
    POLICY_STUDENT_VERIFIED_ONLY,
    POLICY_PARTIAL_DISCOUNT_COPAY,
    POLICY_ANNUAL_WINDOW_CLOSED,
    POLICY_HISTORICAL_EVENT_WAVE,
    POLICY_FREE_UNPROCTORED_BADGE,
    corroborate_offer,
    audit_and_enrich_offers,
    verify_truth_invariants,
)

ROOT = Path(__file__).resolve().parent.parent
DATA_OFFERS = ROOT / "data" / "offers.json"
README_FILE = ROOT / "README.md"
DOCS_HTML = ROOT / "docs" / "index.html"


@pytest.fixture(scope="module")
def offers_data() -> List[Dict[str, Any]]:
    assert DATA_OFFERS.exists(), "data/offers.json missing"
    with open(DATA_OFFERS, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("offers", [])


class TestTruthOracleRegistry:
    """Validates the completeness and integrity of the Ground Truth Policy Registry."""

    def test_registry_contains_all_canonical_offers(self, offers_data):
        """Every tracked offer must have a defined ground truth policy in the registry."""
        for offer in offers_data:
            oid = offer["id"]
            assert oid in TRUTH_POLICY_REGISTRY, f"Offer '{oid}' missing from TRUTH_POLICY_REGISTRY"

    def test_registry_entries_have_valid_https_urls(self):
        """Every truth source URL in the registry must be a valid HTTPS vendor endpoint."""
        for oid, policy in TRUTH_POLICY_REGISTRY.items():
            url = policy.get("truth_source_url", "")
            assert url.startswith("https://"), f"Offer '{oid}' truth_source_url is not HTTPS: '{url}'"
            assert "." in url, f"Offer '{oid}' truth_source_url invalid format: '{url}'"

    def test_registry_entries_have_truth_sources_and_verdicts(self):
        """Every policy entry must have an authoritative truth source name and verdict explanation."""
        for oid, policy in TRUTH_POLICY_REGISTRY.items():
            name = policy.get("truth_source_name", "")
            notes = policy.get("verdict_notes", "")
            assert len(name.strip()) >= 5, f"Offer '{oid}' missing meaningful truth_source_name"
            assert len(notes.strip()) >= 15, f"Offer '{oid}' missing detailed verdict_notes"


class TestPolicyTruthCorroboration:
    """Audits specific high-risk credentials to guarantee zero misleading representations."""

    def test_juniper_partial_discount_copay_truth(self):
        """Juniper Open Learning must be classified as 75% discount voucher requiring ~$50 USD fee."""
        juniper = TRUTH_POLICY_REGISTRY.get("juniper-open-learning")
        assert juniper is not None
        assert juniper["policy_type"] == POLICY_PARTIAL_DISCOUNT_COPAY
        assert juniper["real_exam_cost_usd"] == 50.0
        assert juniper["verified_discount_pct"] == 75
        assert "75%" in juniper["verdict_notes"]
        assert "50" in juniper["verdict_notes"]

    def test_linux_foundation_lift_annual_window_truth(self):
        """Linux Foundation LiFT must reflect annual scholarship window closed outside April."""
        lift = TRUTH_POLICY_REGISTRY.get("linux-foundation-lift")
        assert lift is not None
        assert lift["policy_type"] == POLICY_ANNUAL_WINDOW_CLOSED
        assert lift["enforce_status"] == "Registrations Closed"
        assert not lift["zero_dollar_confirmed"]
        assert "April" in lift["verdict_notes"]

    def test_isc2_one_million_cc_closure_truth(self):
        """ISC2 1MCC must reflect concluded enrollment capacity."""
        isc2 = TRUTH_POLICY_REGISTRY.get("isc2-one-million-cc")
        assert isc2 is not None
        assert isc2["policy_type"] == POLICY_ANNUAL_WINDOW_CLOSED
        assert isc2["enforce_status"] == "Registrations Closed"
        assert not isc2["zero_dollar_confirmed"]

    def test_hashicorp_terraform_associate_concluded_truth(self):
        """HashiCorp Terraform Associate must reflect standard $70.50 fee and concluded community wave."""
        hashi = TRUTH_POLICY_REGISTRY.get("hashicorp-terraform-associate-community")
        assert hashi is not None
        assert hashi["policy_type"] == POLICY_HISTORICAL_EVENT_WAVE
        assert hashi["enforce_status"] == "Expired"
        assert hashi.get("is_historical_archive") is True
        assert hashi["real_exam_cost_usd"] == 70.50

    def test_oracle_oci_free_cert_verified_truth(self):
        """Oracle OCI Foundations & Generative AI must be confirmed as 100% free via Oracle MyLearn."""
        for oid in ["oracle-oci-free-cert", "oracle-oci-generative-ai-cert"]:
            oracle = TRUTH_POLICY_REGISTRY.get(oid)
            assert oracle is not None
            assert oracle["policy_type"] == POLICY_VERIFIED_100PCT_FREE
            assert oracle["real_exam_cost_usd"] == 0.0
            assert oracle["verified_discount_pct"] == 100
            assert oracle["zero_dollar_confirmed"] is True
            assert "mylearn.oracle.com" in oracle["truth_source_url"]

    def test_github_foundations_student_restriction_truth(self):
        """GitHub Foundations must reflect student verification prerequisite."""
        gh = TRUTH_POLICY_REGISTRY.get("github-foundations-cert-wave")
        assert gh is not None
        assert gh["policy_type"] == POLICY_STUDENT_VERIFIED_ONLY
        assert "Student" in gh["truth_source_name"]


class TestAuditAndEnrichPipeline:
    """Verifies that the audit and enrichment engine operates with mathematical precision."""

    def test_audit_idempotency(self, offers_data):
        """Running audit_and_enrich_offers multiple times produces zero subsequent mutations."""
        first_pass, summary1 = audit_and_enrich_offers(offers_data, strict_enforcement=True)
        second_pass, summary2 = audit_and_enrich_offers(first_pass, strict_enforcement=True)
        assert summary2["corrections_applied"] == 0, "Second audit pass should require 0 corrections"
        assert len(first_pass) == len(second_pass)

    def test_database_passes_all_truth_invariants(self, offers_data):
        """The canonical database must have zero truth invariant violations."""
        enriched, _ = audit_and_enrich_offers(offers_data, strict_enforcement=True)
        violations = verify_truth_invariants(enriched)
        assert not violations, f"Truth invariant violations detected in database: {violations}"

    def test_adversarial_detection_of_fake_active_lift(self):
        """Corroboration engine must flag LiFT as misleading if falsely marked Active."""
        fake_lift = {
            "id": "linux-foundation-lift",
            "title": "Linux Foundation LiFT Scholarships",
            "status": "Active",  # Deceptive: annual window is closed
            "cart_balance_verified": "$0.00 (100% Free / Waiver Confirmed)",
        }
        truth = corroborate_offer(fake_lift)
        assert truth["is_misleading"] is True
        assert any("annual window closed" in r for r in truth["misleading_reasons"])

    def test_adversarial_detection_of_fake_zero_dollar_juniper(self):
        """Corroboration engine must flag Juniper as misleading if claiming $0.00 without copay disclosure."""
        fake_juniper = {
            "id": "juniper-open-learning",
            "title": "Juniper Open Learning",
            "status": "Active",
            "cart_balance_verified": "$0.00 (100% Free / Waiver Confirmed)",  # Missing copay disclosure
        }
        truth = corroborate_offer(fake_juniper)
        assert truth["is_misleading"] is True
        assert any("requires $50.00" in r for r in truth["misleading_reasons"])


class TestTruthOracleUISynchronization:
    """Verifies that truth verification metadata is rendered across README and Web Dashboard."""

    def test_readme_contains_truth_oracle_executive_kpi(self):
        """README.md executive summary table must feature the Truth Oracle Engine metric."""
        readme = README_FILE.read_text(encoding="utf-8")
        assert "| **Truth Oracle Engine** | **100% Policy Corroborated** |" in readme

    def test_docs_html_contains_truth_oracle_elements(self):
        """docs/index.html must contain #proofModalTruthCard and policy indicator elements."""
        html = DOCS_HTML.read_text(encoding="utf-8")
        assert 'id="proofModalTruthCard"' in html
        assert 'id="proofModalPolicyType"' in html
        assert 'id="proofModalTruthSource"' in html
        assert 'id="proofModalTruthSourceName"' in html
        assert 'id="proofModalTruthNotes"' in html
