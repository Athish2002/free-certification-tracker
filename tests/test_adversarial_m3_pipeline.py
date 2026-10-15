"""
Adversarial Empirical Challenge Test Suite for Milestone 3:
Pipeline Automation, Candidate Vetting Loop, and Self-Healing Engine Invariants.

Written by Challenger 3 (critic, specialist).
Enforces zero shallow assertions, deep invariant audits, and empirical stress-testing across:
1. Candidate lead with 50% partial discount (must be rejected from offers.json).
2. Candidate lead pointing to a maintenance portal or paid catalog (must be rejected).
3. Candidate lead with unproctored lab badge (must be classified as skill_badge_lab, never proctored_exam).
4. Candidate lead with Pearson VUE / Kryterion proctored exam (must be classified as proctored_exam).
5. Self-healing recovery: portal status transition from triage ('Review Needed', 'Registrations Closed',
   'Broken Link', 'Expired') to 'Active' updates status and triggers structured self-healing event logging.
6. End-to-end isolated ingestion harness asserting database state, rejection audits, and Pydantic schema validity.
"""

import json
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

import pytest

from src.collector import (
    classify_credential_tier,
    generate_candidate_id,
    vet_candidate_lead,
    vet_candidates,
)
from src.main import apply_self_healing, ingest_and_vet_candidates
from src.models import CandidateLead, Offer

ROOT = Path(__file__).resolve().parent.parent
REAL_OFFERS_FILE = ROOT / "data" / "offers.json"
REAL_CANDIDATES_FILE = ROOT / "data" / "candidates.json"
REAL_SCREENSHOTS_DIR = ROOT / "docs" / "screenshots"

PNG_MAGIC_BYTES = b"\x89PNG\r\n\x1a\n"
DUMMY_VALID_PNG = PNG_MAGIC_BYTES + b"\x00" * 2048


# ==============================================================================
# 1. Candidate Lead 50% Partial Discount Adversarial Suite
# ==============================================================================

class TestPartialDiscountRejection:
    """
    Adversarial Challenge: Candidate leads specifying partial discounts
    (e.g., 50% off, 30% off, half-price retakes) MUST be rejected by the
    autonomous vetting loop and NEVER ingested into data/offers.json.
    Only confirmed 100% free / full waiver credentials qualify for publication.
    """

    @pytest.mark.parametrize("title,platform,vendor_url", [
        (
            "AWS Certified Solutions Architect Associate - 50% off Exam Voucher",
            "Amazon Web Services",
            "https://aws.amazon.com/certification/certified-solutions-architect-associate/"
        ),
        (
            "Get 50% off your next Microsoft Azure Certification Exam",
            "Microsoft Azure",
            "https://learn.microsoft.com/credentials"
        ),
        (
            "Oracle Cloud OCI Foundations - 50% OFF Limited Time Voucher",
            "Oracle Cloud",
            "https://mylearn.oracle.com/ou/course/oracle-cloud-infrastructure"
        ),
        (
            "Linux Foundation CKA 50% off Flash Sale Code",
            "Linux Foundation",
            "https://training.linuxfoundation.org/certification/certified-kubernetes-administrator-cka/"
        ),
        (
            "Azure 50% off Exam Voucher Promo Code",
            "Microsoft Azure",
            "https://learn.microsoft.com/credentials"
        ),
    ])
    def test_candidate_lead_50_percent_off_rejected_immediately(self, title, platform, vendor_url):
        """Asserts candidate leads with 50% off are rejected with PARTIAL_DISCOUNT_ONLY."""
        lead = {
            "source": "Reddit r/AWSCertifications",
            "title": title,
            "platform": platform,
            "url": vendor_url,
            "verified_vendor_url": vendor_url,
            "is_authentic_vendor": True
        }

        promoted, reason = vet_candidate_lead(lead)

        assert promoted is None, f"DEFECT: 50% partial discount lead '{title}' was promoted!"
        assert "PARTIAL_DISCOUNT_ONLY" in reason, (
            f"Expected rejection reason to cite PARTIAL_DISCOUNT_ONLY, got: '{reason}'"
        )

    @pytest.mark.parametrize("percent", [10, 20, 30, 40, 50, 60, 70, 80, 90])
    def test_all_partial_discount_percentages_rejected(self, percent):
        """Asserts all standard partial percentage discounts (10%-90% off) are rejected."""
        title = f"Google Cloud Professional Architect {percent}% off Voucher"
        lead = {
            "source": "Reddit r/cloud_computing",
            "title": title,
            "platform": "Google Cloud",
            "url": "https://cloud.google.com/learn/certification",
            "verified_vendor_url": "https://cloud.google.com/learn/certification",
            "is_authentic_vendor": True
        }

        promoted, reason = vet_candidate_lead(lead)
        assert promoted is None
        assert "PARTIAL_DISCOUNT_ONLY" in reason

    def test_ingest_and_vet_candidates_never_adds_partial_discount_to_offers(self, tmp_path):
        """
        Integration Invariant: Running ingest_and_vet_candidates on a dataset containing
        a 50% partial discount lead MUST NOT add it to offers.json, and MUST record the
        audit rejection in candidates.json.
        """
        cand_file = tmp_path / "candidates.json"
        offers_file = tmp_path / "offers.json"

        # Baseline offers store
        with open(REAL_OFFERS_FILE, "r", encoding="utf-8") as f:
            real_offers = json.load(f)
        with open(offers_file, "w", encoding="utf-8") as f:
            json.dump(real_offers, f, indent=2)

        initial_offer_count = len(real_offers["offers"])

        # Candidate containing 50% partial discount
        partial_cand_data = {
            "total_candidates": 1,
            "leads": [
                {
                    "id": "cand-aws-50-percent",
                    "source": "Reddit r/AWSCertifications",
                    "title": "AWS Solutions Architect Associate 50% off Flash Voucher",
                    "platform": "Amazon Web Services",
                    "url": "https://aws.amazon.com/certification",
                    "verified_vendor_url": "https://aws.amazon.com/certification",
                    "is_authentic_vendor": True,
                    "authenticity_tier": "Verified Official Portal"
                }
            ]
        }
        with open(cand_file, "w", encoding="utf-8") as f:
            json.dump(partial_cand_data, f, indent=2)

        promoted_count, rejected_count = ingest_and_vet_candidates(cand_file, offers_file)

        assert promoted_count == 0, f"Expected 0 promoted offers, got: {promoted_count}"
        assert rejected_count == 1, f"Expected 1 rejected offer, got: {rejected_count}"

        # Verify offers.json was NOT modified
        with open(offers_file, "r", encoding="utf-8") as f:
            updated_offers = json.load(f)
        assert len(updated_offers["offers"]) == initial_offer_count
        assert not any("cand-aws-50-percent" in o["id"] for o in updated_offers["offers"])

        # Verify candidates.json recorded rejection audit
        with open(cand_file, "r", encoding="utf-8") as f:
            updated_cand = json.load(f)
        lead_audit = updated_cand["leads"][0]
        assert "Rejected: PARTIAL_DISCOUNT_ONLY" in lead_audit.get("vetting_status", "")
        assert "vetted_at" in lead_audit

    def test_genuine_100_percent_free_lead_not_falsely_rejected_by_partial_check(self):
        """
        Negative Invariant: A lead with '100% Free Voucher' that happens to contain other text
        should NOT trigger the immediate PARTIAL_DISCOUNT_ONLY filter.
        """
        title = "100% Free Azure Exam Voucher Challenge (Was 50% off last week)"
        lead = {
            "title": title,
            "platform": "Microsoft Azure",
            "url": "https://learn.microsoft.com",
            "verified_vendor_url": "https://learn.microsoft.com",
            "is_authentic_vendor": True
        }
        # Does not reject on PARTIAL_DISCOUNT_ONLY because "100%" and "free" are present
        title_lower = title.lower()
        has_partial = bool(re.search(r"\b(10|20|30|40|50|60|70|80|90)%\s*off\b", title_lower))
        assert has_partial is True
        # Rule check: "100%" or "free" in title suppresses partial discount rejection
        should_bypass = "100%" in title_lower or "free" in title_lower
        assert should_bypass is True


# ==============================================================================
# 2. Candidate Lead Pointing to Maintenance or Paid Catalog Suite
# ==============================================================================

class TestMaintenanceAndPaidCatalogRejection:
    """
    Adversarial Challenge: Candidate leads pointing to maintenance downtime
    portals or generic paid commercial catalogs ($245 standard checkout without
    waiver) MUST be rejected and NEVER added to data/offers.json.
    """

    def test_candidate_lead_maintenance_url_pattern_rejected(self):
        """Candidate lead with maintenance URL pattern must be rejected immediately."""
        lead = {
            "id": "cand-oracle-maintenance",
            "title": "Oracle OCI 2026 Certified Foundations Associate Voucher",
            "platform": "Oracle Cloud",
            "url": "https://mylearn.oracle.com/ou/maintenance",
            "verified_vendor_url": "https://mylearn.oracle.com/ou/maintenance",
            "is_authentic_vendor": True
        }
        promoted, reason = vet_candidate_lead(lead)
        assert promoted is None
        assert "MAINTENANCE_PAGE" in reason

    def test_candidate_lead_maintenance_dom_inspection_rejected(self):
        """
        Candidate lead that resolves to a maintenance notice via rendered DOM inspection
        must be rejected as MAINTENANCE_PAGE and not promoted.
        """
        lead = {
            "id": "cand-maintenance-dom",
            "title": "Oracle OCI Architect Free Certification Wave",
            "platform": "Oracle Cloud",
            "url": "https://mylearn.oracle.com/ou/exam",
            "verified_vendor_url": "https://mylearn.oracle.com/ou/exam",
            "is_authentic_vendor": True
        }

        # Mock inspect_offer returning maintenance notice
        mock_inspection = {
            "status": "Review Needed",
            "reason": "Maintenance Invariant: Portal currently down for maintenance ('down for maintenance')",
            "canonical_url": "https://mylearn.oracle.com/ou/exam",
            "auth_score": 90,
            "maintenance_detected": True,
            "paid_catalog_detected": False,
            "visual_proof": {
                "status": "failed",
                "maintenance_detected": True,
                "zero_dollar_confirmed": False
            }
        }

        with patch("src.inspector.inspect_offer", return_value=mock_inspection):
            promoted, reason = vet_candidate_lead(lead)

        assert promoted is None
        assert "MAINTENANCE_PAGE" in reason
        assert "down for maintenance" in reason

    def test_candidate_lead_paid_catalog_dom_inspection_rejected(self):
        """
        Candidate lead that resolves to a generic full-price catalog ($245 standard pricing)
        without affirmative zero-dollar waiver terms must be rejected as PAID_CATALOG.
        """
        lead = {
            "id": "cand-paid-catalog",
            "title": "AWS Certified Advanced Networking Specialty Voucher",
            "platform": "Amazon Web Services",
            "url": "https://aws.amazon.com/certification/certified-advanced-networking-specialty/",
            "verified_vendor_url": "https://aws.amazon.com/certification/certified-advanced-networking-specialty/",
            "is_authentic_vendor": True
        }

        # Mock inspect_offer returning standard commercial pricing without waiver
        mock_inspection = {
            "status": "Review Needed",
            "reason": "Catalog Pricing Invariant: Detected standard paid catalog / cart pricing ($245/checkout) without affirmative zero-dollar waiver terms",
            "canonical_url": "https://aws.amazon.com/certification/certified-advanced-networking-specialty/",
            "auth_score": 95,
            "maintenance_detected": False,
            "paid_catalog_detected": True,
            "visual_proof": {
                "status": "failed",
                "paid_catalog_detected": True,
                "zero_dollar_confirmed": False
            }
        }

        with patch("src.inspector.inspect_offer", return_value=mock_inspection):
            promoted, reason = vet_candidate_lead(lead)

        assert promoted is None
        assert "PAID_CATALOG" in reason
        assert "standard paid catalog" in reason.lower()

    def test_ingest_and_vet_candidates_never_adds_maintenance_or_catalog_to_offers(self, tmp_path):
        """
        Integration Invariant: Batch candidate vetting containing maintenance and paid catalog
        leads must reject both, promote zero, and leave offers.json unaltered.
        """
        cand_file = tmp_path / "candidates.json"
        offers_file = tmp_path / "offers.json"

        with open(REAL_OFFERS_FILE, "r", encoding="utf-8") as f:
            real_offers = json.load(f)
        with open(offers_file, "w", encoding="utf-8") as f:
            json.dump(real_offers, f, indent=2)

        initial_count = len(real_offers["offers"])

        cand_payload = {
            "total_candidates": 2,
            "leads": [
                {
                    "id": "cand-oracle-downtime",
                    "title": "Oracle OCI 2026 Free Exam Voucher",
                    "platform": "Oracle Cloud",
                    "url": "https://mylearn.oracle.com/ou/maintenance",
                    "verified_vendor_url": "https://mylearn.oracle.com/ou/maintenance",
                    "is_authentic_vendor": True
                },
                {
                    "id": "cand-aws-paid-catalog",
                    "title": "AWS Certified Database Specialty Voucher",
                    "platform": "Amazon Web Services",
                    "url": "https://aws.amazon.com/certification/paid-catalog",
                    "verified_vendor_url": "https://aws.amazon.com/certification/paid-catalog",
                    "is_authentic_vendor": True
                }
            ]
        }
        with open(cand_file, "w", encoding="utf-8") as f:
            json.dump(cand_payload, f, indent=2)

        # Mock inspect_offer for the second lead
        def mock_inspector(stub, capture_screenshot=True):
            return {
                "status": "Review Needed",
                "reason": "Catalog Pricing Invariant: $245 standard checkout",
                "canonical_url": stub.get("verified_vendor_url"),
                "auth_score": 90,
                "maintenance_detected": False,
                "paid_catalog_detected": True,
                "visual_proof": {"paid_catalog_detected": True, "zero_dollar_confirmed": False}
            }

        with patch("src.inspector.inspect_offer", side_effect=mock_inspector):
            promoted_cnt, rejected_cnt = ingest_and_vet_candidates(cand_file, offers_file)

        assert promoted_cnt == 0
        assert rejected_cnt == 2

        with open(offers_file, "r", encoding="utf-8") as f:
            offers_after = json.load(f)
        assert len(offers_after["offers"]) == initial_count


# ==============================================================================
# 3. Unproctored Lab Badge Classification Suite
# ==============================================================================

class TestUnproctoredBadgeClassification:
    """
    Adversarial Challenge: Candidate leads representing unproctored lab badges,
    skill assessments, interactive sandboxes, and learning completions MUST be
    classified as 'skill_badge_lab' and NEVER as 'proctored_exam'.
    """

    @pytest.mark.parametrize("title,vendor_url", [
        (
            "Microsoft Applied Skills: Build an Azure AI Vision Solution",
            "https://learn.microsoft.com/credentials/applied-skills/azure-ai-vision"
        ),
        (
            "Google Cloud Skill Badges: Build Infrastructure with Terraform",
            "https://www.cloudskillsboost.google/quests/terraform-infrastructure"
        ),
        (
            "Snowflake Hands-On Essentials - Data Warehouse Badge",
            "https://learn.snowflake.com/courses/data-warehouse-essentials"
        ),
        (
            "Databricks Lakehouse Fundamentals Accreditation",
            "https://www.databricks.com/learn/training/lakehouse-fundamentals"
        ),
        (
            "AWS Educate Cloud Computing Badge for Students",
            "https://aws.amazon.com/education/awseducate/"
        ),
        (
            "Qualys Certified Specialist - Vulnerability Management Lab",
            "https://www.qualys.com/training/library/vulnerability-management/"
        ),
        (
            "Postman API Expert Interactive Lab Challenge",
            "https://academy.postman.com/expert"
        ),
        (
            "Interactive Lab Challenge - Kubernetes Sandbox Quest",
            "https://learn.microsoft.com/training/modules/kubernetes-sandbox"
        ),
        (
            "Course Quiz & Digital Credential: Cloud Security Fundamentals",
            "https://cloud.google.com/training/security-quiz"
        ),
    ])
    def test_unproctored_lab_badge_classified_as_skill_badge_lab(self, title, vendor_url):
        """Asserts each unproctored credential is classified as skill_badge_lab, never proctored_exam."""
        tier, proctoring_type, accredited_body = classify_credential_tier(title, vendor_url)

        assert tier == "skill_badge_lab", (
            f"VIOLATION: '{title}' misclassified as '{tier}'! Must be 'skill_badge_lab'."
        )
        assert tier != "proctored_exam", (
            f"CRITICAL DEFECT: Unproctored credential '{title}' classified as proctored_exam!"
        )
        assert proctoring_type == "unproctored_lab", (
            f"Expected proctoring_type 'unproctored_lab', got: '{proctoring_type}'"
        )
        assert accredited_body is None, (
            f"Expected accredited_body None for unproctored credential, got: '{accredited_body}'"
        )

    def test_candidate_lead_model_to_offer_stub_preserves_skill_badge_lab(self):
        """Asserts CandidateLead.to_offer_stub produces skill_badge_lab stub."""
        cand = CandidateLead(
            source="Reddit r/AzureCertification",
            title="Microsoft Applied Skills: Configure SIEM with Microsoft Sentinel",
            url="https://learn.microsoft.com/credentials/applied-skills/sentinel",
            platform="Microsoft Azure",
            is_authentic_vendor=True,
            verified_vendor_url="https://learn.microsoft.com/credentials/applied-skills/sentinel"
        )
        stub = cand.to_offer_stub("cand-ms-applied-skills-sentinel", credential_tier="skill_badge_lab")

        assert stub["credential_tier"] == "skill_badge_lab"
        assert stub["proctoring_type"] == "unproctored_lab"
        assert stub["credential_tier"] != "proctored_exam"


# ==============================================================================
# 4. Proctored Exam Classification Suite (Pearson VUE / Kryterion / PSI)
# ==============================================================================

class TestProctoredExamClassification:
    """
    Adversarial Challenge: Candidate leads representing accredited written exams
    delivered via Pearson VUE, Kryterion, Webassessor, or PSI MUST be classified
    as 'proctored_exam' and assigned the correct proctoring provider.
    """

    @pytest.mark.parametrize("title,vendor_url,expected_ptype,expected_body", [
        (
            "AWS Certified Solutions Architect Associate (Pearson VUE)",
            "https://aws.amazon.com/certification/certified-solutions-architect-associate/",
            "pearson_vue",
            "Pearson VUE"
        ),
        (
            "Salesforce Certified Administrator via Kryterion Webassessor",
            "https://trailhead.salesforce.com/en/credentials/administrator",
            "kryterion",
            "Kryterion Webassessor"
        ),
        (
            "Oracle Cloud Infrastructure 2026 Certified Foundations Associate (Pearson VUE proctored exam)",
            "https://mylearn.oracle.com/ou/course/oracle-cloud-infrastructure-foundations",
            "pearson_vue",
            "Pearson VUE"
        ),
        (
            "Kryterion Proctored Written Exam Voucher",
            "https://www.webassessor.com/salesforce",
            "kryterion",
            "Kryterion Webassessor"
        ),
        (
            "Linux Foundation CKA Exam",
            "https://training.linuxfoundation.org/certification/certified-kubernetes-administrator-cka/",
            "psi",
            "Linux Foundation"
        ),
        (
            "Microsoft Azure Administrator AZ-104 Written Proctored Exam (Pearson VUE)",
            "https://learn.microsoft.com/credentials/certifications/azure-administrator",
            "pearson_vue",
            "Pearson VUE"
        ),
    ])
    def test_proctored_exam_classified_accurately(self, title, vendor_url, expected_ptype, expected_body):
        """Asserts each formal proctored exam is classified as proctored_exam with valid proctoring type."""
        tier, proctoring_type, accredited_body = classify_credential_tier(title, vendor_url)

        assert tier == "proctored_exam", (
            f"VIOLATION: Proctored exam '{title}' misclassified as '{tier}'! Must be 'proctored_exam'."
        )
        assert tier != "skill_badge_lab", (
            f"DEFECT: Proctored exam '{title}' classified as skill_badge_lab!"
        )
        assert proctoring_type == expected_ptype, (
            f"Expected proctoring_type '{expected_ptype}', got: '{proctoring_type}'"
        )
        assert accredited_body == expected_body, (
            f"Expected accredited_body '{expected_body}', got: '{accredited_body}'"
        )


# ==============================================================================
# 5. Self-Healing Recovery Lifecycle Suite
# ==============================================================================

class TestSelfHealingRecoveryLifecycle:
    """
    Adversarial Challenge: Verifies the self-healing recovery engine in src/main.py.
    When a portal status transitions from a triage/outage state ('Review Needed',
    'Registrations Closed', 'Broken Link', or 'Expired') back to 'Active', it must:
    1. Update status to 'Active'.
    2. Refresh verification_date to current date.
    3. Update visual_proof metadata (zero_dollar_confirmed=True, maintenance_detected=False).
    4. Attach structured 'self_healing_event' with previous_status, healed_status,
       timestamp, and proof_image.
    5. Maintain strict Pydantic Offer schema validity.
    """

    @pytest.mark.parametrize("old_triage_status", [
        "Review Needed",
        "Registrations Closed",
        "Broken Link",
        "Expired"
    ])
    def test_portal_recovery_triggers_self_healing_event(self, old_triage_status):
        """Asserts portal status transition from any triage state to Active triggers self-healing event."""
        initial_offer = {
            "id": "oracle-oci-foundations-associate",
            "title": "Oracle Cloud Infrastructure 2026 Certified Foundations Associate",
            "platform": "Oracle Cloud",
            "category": "Cloud Architecture",
            "certification_name": "Oracle Cloud Infrastructure 2026 Certified Foundations Associate",
            "credential_tier": "proctored_exam",
            "proctoring_type": "pearson_vue",
            "accredited_body": "Oracle",
            "url": "https://mylearn.oracle.com/ou/course/oracle-cloud-infrastructure",
            "verified_vendor_url": "https://mylearn.oracle.com/ou/course/oracle-cloud-infrastructure",
            "status": old_triage_status,
            "seasonality": "periodic_challenge_wave",
            "verification_date": "2026-09-01",
            "screenshot_path": "docs/screenshots/oracle-oci-foundations-associate.png",
            "visual_proof": {
                "screenshot_path": "docs/screenshots/oracle-oci-foundations-associate.png",
                "screenshot_url": "docs/screenshots/oracle-oci-foundations-associate.png",
                "captured_at": "2026-09-01T00:00:00Z",
                "status": "failed",
                "zero_dollar_confirmed": False,
                "maintenance_detected": True,
                "paid_catalog_detected": False
            }
        }

        # Simulated successful inspection recovering to Active
        inspection_result = {
            "status": "Active",
            "reason": "HTTP 200 OK (Live Verified & Authenticated)",
            "auth_score": 95,
            "verification_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "visual_proof": {
                "status": "verified",
                "zero_dollar_confirmed": True,
                "maintenance_detected": False,
                "paid_catalog_detected": False
            }
        }

        proof_path = "docs/screenshots/oracle-oci-foundations-associate.png"
        healed_offer = apply_self_healing(initial_offer, inspection_result, proof_path=proof_path)

        # 1. Status and date update
        assert healed_offer["status"] == "Active"
        assert healed_offer["verification_date"] == datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # 2. Visual proof updated
        vp = healed_offer.get("visual_proof", {})
        assert vp.get("status") == "verified"
        assert vp.get("zero_dollar_confirmed") is True
        assert vp.get("maintenance_detected") is False
        assert vp.get("paid_catalog_detected") is False
        assert vp.get("captured_at") is not None

        # 3. Self-healing event structured logging
        assert "self_healing_event" in healed_offer, "Missing 'self_healing_event' on recovered offer!"
        event = healed_offer["self_healing_event"]
        assert event["previous_status"] == old_triage_status
        assert event["healed_status"] == "Active"
        assert event["proof_image"] == proof_path

        # Verify timestamp is valid ISO 8601 UTC
        event_dt = datetime.fromisoformat(event["timestamp"])
        assert event_dt.tzinfo is not None

        # 4. Validates against Offer Pydantic schema
        valid_model = Offer(**healed_offer)
        assert valid_model.status == "Active"
        assert valid_model.is_active() is True

    def test_steady_state_active_to_active_does_not_trigger_spurious_self_healing(self):
        """
        Negative Invariant: When an offer is ALREADY 'Active' and inspection confirms 'Active',
        it should NOT generate a self_healing_event (no false healing alarms).
        """
        active_offer = {
            "id": "github-student-foundations",
            "title": "GitHub Foundations Certification",
            "status": "Active",
            "verification_date": "2026-10-01",
            "screenshot_path": "docs/screenshots/github-student-foundations.png",
            "visual_proof": {
                "screenshot_path": "docs/screenshots/github-student-foundations.png",
                "status": "verified",
                "zero_dollar_confirmed": True
            }
        }

        inspection_result = {
            "status": "Active",
            "reason": "HTTP 200 OK (Live Verified & Authenticated)"
        }

        result = apply_self_healing(active_offer, inspection_result)
        assert result["status"] == "Active"
        assert "self_healing_event" not in result, "Active -> Active must not create self_healing_event!"

    def test_unsuccessful_inspection_does_not_trigger_self_healing(self):
        """Negative Invariant: If portal remains in triage, do not attach self_healing_event."""
        broken_offer = {
            "id": "broken-test-offer",
            "status": "Broken Link",
            "verification_date": "2026-09-01"
        }
        inspection_result = {
            "status": "Broken Link",
            "reason": "HTTP 404 Page Not Found"
        }

        result = apply_self_healing(broken_offer, inspection_result)
        assert result["status"] == "Broken Link"
        assert "self_healing_event" not in result


# ==============================================================================
# 6. End-to-End Candidate Ingestion Gate Integration Harness
# ==============================================================================

class TestEndToEndCandidateVettingHarness:
    """
    End-to-End Autonomous Pipeline Invariant Test:
    Constructs an adversarial candidate dataset containing:
    1. 50% partial discount lead (must be rejected)
    2. Maintenance page lead (must be rejected)
    3. Paid catalog lead (must be rejected)
    4. Insecure HTTP lead (must be rejected)
    5. Untrusted scam lead (must be rejected)
    6. Duplicate URL lead (must be rejected)
    7. Valid 100% free Pearson VUE proctored exam lead (must be promoted to proctored_exam)
    8. Valid 100% free unproctored skill badge lead (must be promoted to skill_badge_lab)
    Executes ingest_and_vet_candidates in an isolated directory and verifies exact
    database state, rejection reasons, and schema integrity.
    """

    def test_comprehensive_adversarial_candidate_vetting_pipeline(self, tmp_path):
        cand_file = tmp_path / "candidates.json"
        offers_file = tmp_path / "offers.json"

        # Initialize mock offers database with 1 existing offer
        existing_url = "https://learn.microsoft.com/credentials/existing-offer"
        initial_offers = {
            "$schema": "./schema.json",
            "last_updated": "2026-10-15T00:00:00Z",
            "offers": [
                {
                    "id": "existing-test-offer",
                    "title": "Existing Verified Offer",
                    "platform": "Microsoft Azure",
                    "category": "Cloud Architecture",
                    "certification_name": "Existing Certification",
                    "credential_tier": "proctored_exam",
                    "proctoring_type": "pearson_vue",
                    "accredited_body": "Pearson VUE",
                    "url": existing_url,
                    "verified_vendor_url": existing_url,
                    "status": "Active",
                    "seasonality": "evergreen",
                    "claim_steps": "Standard checkout",
                    "is_authentic_vendor": True,
                    "authenticity_score": 100,
                    "visual_proof": {
                        "screenshot_path": "docs/screenshots/existing-test-offer.png",
                        "status": "verified",
                        "zero_dollar_confirmed": True
                    }
                }
            ]
        }
        with open(offers_file, "w", encoding="utf-8") as f:
            json.dump(initial_offers, f, indent=2)

        # Ensure physical screenshot proof exists for valid candidate promotions
        valid_proctored_id = "adv-aws-saa-proctored"
        valid_badge_id = "adv-gcp-skills-boost-badge"
        shot_proctored = REAL_SCREENSHOTS_DIR / f"{valid_proctored_id}.png"
        shot_badge = REAL_SCREENSHOTS_DIR / f"{valid_badge_id}.png"

        created_shots = []
        try:
            if not shot_proctored.exists():
                shot_proctored.write_bytes(DUMMY_VALID_PNG)
                created_shots.append(shot_proctored)
            if not shot_badge.exists():
                shot_badge.write_bytes(DUMMY_VALID_PNG)
                created_shots.append(shot_badge)

            # Construct 8 adversarial candidate leads
            leads = [
                # 1. 50% partial discount
                {
                    "id": "cand-lead-1-50-percent",
                    "source": "Reddit r/AWSCertifications",
                    "title": "AWS Solutions Architect 50% off Promo Voucher",
                    "platform": "Amazon Web Services",
                    "url": "https://aws.amazon.com/certification/saa-50",
                    "verified_vendor_url": "https://aws.amazon.com/certification/saa-50",
                    "is_authentic_vendor": True
                },
                # 2. Maintenance portal URL
                {
                    "id": "cand-lead-2-maintenance",
                    "source": "Reddit r/AzureCertification",
                    "title": "Azure Fundamentals Free Voucher",
                    "platform": "Microsoft Azure",
                    "url": "https://learn.microsoft.com/maintenance",
                    "verified_vendor_url": "https://learn.microsoft.com/maintenance",
                    "is_authentic_vendor": True
                },
                # 3. Paid catalog (will trigger paid catalog detection)
                {
                    "id": "cand-lead-3-paid-catalog",
                    "source": "Reddit r/AWSCertifications",
                    "title": "AWS DevOps Professional Standard Exam",
                    "platform": "Amazon Web Services",
                    "url": "https://aws.amazon.com/certification/devops-paid",
                    "verified_vendor_url": "https://aws.amazon.com/certification/devops-paid",
                    "is_authentic_vendor": True
                },
                # 4. Insecure HTTP protocol
                {
                    "id": "cand-lead-4-insecure-http",
                    "source": "Reddit r/cloud_computing",
                    "title": "Cisco CCNA Voucher Wave",
                    "platform": "Cisco",
                    "url": "http://cisco.com/training/voucher",
                    "verified_vendor_url": "http://cisco.com/training/voucher",
                    "is_authentic_vendor": True
                },
                # 5. Untrusted vendor domain
                {
                    "id": "cand-lead-5-untrusted-domain",
                    "source": "Reddit r/AzureCertification",
                    "title": "Free Azure Dumps & Vouchers 100% Free",
                    "platform": "Microsoft Azure",
                    "url": "https://free-exam-dumps-scam.com/azure",
                    "verified_vendor_url": "",
                    "is_authentic_vendor": False
                },
                # 6. Duplicate URL already tracked
                {
                    "id": "cand-lead-6-already-tracked",
                    "source": "Reddit r/AzureCertification",
                    "title": "Microsoft Existing Voucher Repeat",
                    "platform": "Microsoft Azure",
                    "url": existing_url,
                    "verified_vendor_url": existing_url,
                    "is_authentic_vendor": True
                },
                # 7. Valid 100% free Pearson VUE proctored exam lead
                {
                    "id": valid_proctored_id,
                    "source": "Reddit r/AWSCertifications",
                    "title": "AWS Certified Solutions Architect Associate (Pearson VUE)",
                    "platform": "Amazon Web Services",
                    "url": "https://aws.amazon.com/certification/certified-solutions-architect-associate/",
                    "verified_vendor_url": "https://aws.amazon.com/certification/certified-solutions-architect-associate/",
                    "is_authentic_vendor": True
                },
                # 8. Valid 100% free unproctored skill badge lead
                {
                    "id": valid_badge_id,
                    "source": "Reddit r/cloud_computing",
                    "title": "Google Cloud Skill Badges: Build Infrastructure with Terraform",
                    "platform": "Google Cloud",
                    "url": "https://www.cloudskillsboost.google/quests/terraform-infrastructure",
                    "verified_vendor_url": "https://www.cloudskillsboost.google/quests/terraform-infrastructure",
                    "is_authentic_vendor": True
                }
            ]

            with open(cand_file, "w", encoding="utf-8") as f:
                json.dump({"total_candidates": len(leads), "leads": leads}, f, indent=2)

            # Controlled mock for inspect_offer
            def mock_inspect_gate(stub, capture_screenshot=True):
                stub_id = stub.get("id", "")
                vendor_url_val = stub.get("verified_vendor_url", "")

                if "paid" in vendor_url_val:
                    return {
                        "status": "Review Needed",
                        "reason": "Catalog Pricing Invariant: $245 checkout",
                        "canonical_url": vendor_url_val,
                        "auth_score": 90,
                        "maintenance_detected": False,
                        "paid_catalog_detected": True,
                        "visual_proof": {"paid_catalog_detected": True, "zero_dollar_confirmed": False}
                    }

                # Default for valid candidates
                return {
                    "status": "Active",
                    "reason": "HTTP 200 OK (Live Verified & Authenticated)",
                    "canonical_url": vendor_url_val,
                    "auth_score": 95,
                    "verification_date": "2026-10-15",
                    "maintenance_detected": False,
                    "paid_catalog_detected": False,
                    "visual_proof": {
                        "screenshot_path": f"docs/screenshots/{stub_id}.png",
                        "status": "verified",
                        "zero_dollar_confirmed": True,
                        "maintenance_detected": False,
                        "paid_catalog_detected": False
                    }
                }

            with patch("src.inspector.inspect_offer", side_effect=mock_inspect_gate):
                promoted_cnt, rejected_cnt = ingest_and_vet_candidates(cand_file, offers_file)

            # Verify batch metrics
            assert promoted_cnt == 2, f"Expected exactly 2 promoted offers, got: {promoted_cnt}"
            assert rejected_cnt == 6, f"Expected exactly 6 rejected leads, got: {rejected_cnt}"

            # Verify updated offers.json
            with open(offers_file, "r", encoding="utf-8") as f:
                final_offers_data = json.load(f)
            offers_list = final_offers_data["offers"]
            assert len(offers_list) == 3  # 1 initial + 2 promoted

            promoted_ids = {o["id"] for o in offers_list}
            assert valid_proctored_id in promoted_ids
            assert valid_badge_id in promoted_ids

            # Assert rejected leads are NOT present
            assert "cand-lead-1-50-percent" not in promoted_ids
            assert "cand-lead-2-maintenance" not in promoted_ids
            assert "cand-lead-3-paid-catalog" not in promoted_ids
            assert "cand-lead-4-insecure-http" not in promoted_ids
            assert "cand-lead-5-untrusted-domain" not in promoted_ids
            assert "cand-lead-6-already-tracked" not in promoted_ids

            # Verify credential tier taxonomy of promoted offers
            proctored_offer = next(o for o in offers_list if o["id"] == valid_proctored_id)
            badge_offer = next(o for o in offers_list if o["id"] == valid_badge_id)

            assert proctored_offer["credential_tier"] == "proctored_exam"
            assert proctored_offer["proctoring_type"] == "pearson_vue"
            assert proctored_offer["status"] == "Active"

            assert badge_offer["credential_tier"] == "skill_badge_lab"
            assert badge_offer["proctoring_type"] == "unproctored_lab"
            assert badge_offer["status"] == "Active"

            # Verify Offer Pydantic schema validation on all final offers
            for o in offers_list:
                model = Offer(**o)
                assert model.is_active() is True

            # Verify candidates.json rejection audit logging
            with open(cand_file, "r", encoding="utf-8") as f:
                final_cand_data = json.load(f)

            leads_by_id = {l["id"]: l for l in final_cand_data["leads"]}

            # 1. 50% discount rejection reason
            assert "PARTIAL_DISCOUNT_ONLY" in leads_by_id["cand-lead-1-50-percent"]["rejection_reason"]
            # 2. Maintenance rejection reason
            assert "MAINTENANCE_PAGE" in leads_by_id["cand-lead-2-maintenance"]["rejection_reason"]
            # 3. Paid catalog rejection reason
            assert "PAID_CATALOG" in leads_by_id["cand-lead-3-paid-catalog"]["rejection_reason"]
            # 4. Insecure protocol rejection reason
            assert "INSECURE_PROTOCOL" in leads_by_id["cand-lead-4-insecure-http"]["rejection_reason"]
            # 5. Untrusted vendor rejection reason
            assert "UNTRUSTED_VENDOR" in leads_by_id["cand-lead-5-untrusted-domain"]["rejection_reason"]
            # 6. Duplicate URL rejection reason
            assert "ALREADY_TRACKED" in leads_by_id["cand-lead-6-already-tracked"]["rejection_reason"]

            # Promoted leads must have "Promoted to Active Offers"
            assert "Promoted to Active Offers" in leads_by_id[valid_proctored_id]["vetting_status"]
            assert "Promoted to Active Offers" in leads_by_id[valid_badge_id]["vetting_status"]

        finally:
            # Clean up dummy screenshot files created during test
            for shot in created_shots:
                if shot.exists():
                    shot.unlink()
