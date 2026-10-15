"""
Adversarial Empirical Challenge Test Suite for Milestone 5 Phase 2:
Adversarial Coverage Hardening (Core Verification Engine & Automation Pipeline).

Written by Challenger 1 (critic, specialist).
Enforces zero shallow assertions, deep invariant audits, and empirical stress-testing across:
1. Extreme anti-bot HTTP response codes (429 Too Many Requests, 503 Backend Fetch Failed, 502 Bad Gateway)
   - Graceful downgrade to 'Review Needed' or triage state, never falsely 'Active', never unhandled exception.
2. DOM inspection with deceptive content
   - Pages containing standard commercial fees ($245.00, $165.00, $300.00, Cart Total) commingled with
     marketing phrases like "Free certification" or "Free exam" without affirmative zero-dollar checkout terms.
   - Strict assertion that status is NEVER falsely certified as 'Active'.
3. Corrupted or zero-byte candidate payloads in collector ingestion
   - Candidate vetting safely discards None, zero-byte files, malformed JSON, and corrupt leads without crashing.
4. Concurrent or repeated self-healing events
   - Idempotence of recovery transitions, thread-safe execution, clean audit logging, and Pydantic Offer schema conformance.
"""

import json
import re
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from src.collector import (
    classify_credential_tier,
    generate_candidate_id,
    vet_candidate_lead,
    vet_candidates,
    fetch_reddit_leads
)
from src.dom_inspector import (
    HeadlessDOMInspector,
    evaluate_dual_gate,
    inspect_rendered_dom,
    inspect_url_with_playwright,
    MAINTENANCE_PATTERNS,
    PAID_CATALOG_PATTERNS,
    ZERO_DOLLAR_SIGNALS,
    AFFIRMATIVE_OFFER_SIGNALS
)
from src.inspector import (
    inspect_offer,
    inspect_url_with_retry,
    run_inspection
)
from src.main import apply_self_healing, ingest_and_vet_candidates
from src.models import CandidateLead, Offer, OffersDatabase

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "offers.json"
CANDIDATES_FILE = ROOT / "data" / "candidates.json"
SCREENSHOTS_DIR = ROOT / "docs" / "screenshots"

PNG_MAGIC_BYTES = b"\x89PNG\r\n\x1a\n"
DUMMY_VALID_PNG = PNG_MAGIC_BYTES + b"\x00" * 4096


# ==============================================================================
# Helper Fixtures & Utilities
# ==============================================================================

@pytest.fixture
def mock_valid_screenshot(tmp_path):
    """Provides a valid screenshot file on disk satisfying >= 4KB PNG requirements."""
    shot_dir = tmp_path / "screenshots"
    shot_dir.mkdir(parents=True, exist_ok=True)
    shot_file = shot_dir / "test-offer.png"
    shot_file.write_bytes(DUMMY_VALID_PNG)
    return shot_file


# ==============================================================================
# Edge Case 1: Extreme Anti-Bot HTTP Response Codes (429, 502, 503)
# ==============================================================================

class TestAntiBotAndGatewayErrorDowngrade:
    """
    Adversarial Challenge: When encountering anti-bot rate-limiting (429 Too Many Requests)
    or gateway/backend outages (502 Bad Gateway, 503 Backend Fetch Failed / Service Unavailable),
    the inspection and verification engine MUST gracefully downgrade to a triage status
    (such as 'Review Needed' or 'Server Error') and NEVER certify an offer as 'Active',
    regardless of page text or screenshot presence. It must never raise unhandled exceptions.
    """

    @pytest.mark.parametrize("status_code,status_text", [
        (429, "429 Too Many Requests - Cloudflare Rate Limit Exceeded"),
        (502, "502 Bad Gateway - Upstream Server Error"),
        (503, "503 Backend Fetch Failed - Service Temporarily Unavailable"),
    ])
    def test_inspect_url_with_retry_anti_bot_codes_never_active(self, status_code, status_text):
        """
        Asserts that HTTP 429, 502, and 503 responses never result in status='Active',
        even when the response body deceptively includes promotional keywords.
        """
        offer = {
            "id": "oracle-oci-foundations-associate",
            "title": "Oracle Cloud Infrastructure Foundations Associate",
            "url": "https://mylearn.oracle.com/ou/course/oracle-cloud-infrastructure",
            "platform": "Oracle Cloud"
        }

        mock_resp = MagicMock()
        mock_resp.status_code = status_code
        mock_resp.url = offer["url"]
        mock_resp.history = []
        mock_resp.text = f"<html><body><h1>{status_text}</h1><p>Claim your free certification voucher.</p></body></html>"

        with patch("httpx.Client.get", return_value=mock_resp), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.stat") as mock_stat, \
             patch("pathlib.Path.read_bytes", return_value=DUMMY_VALID_PNG):
            mock_stat.return_value.st_size = 5000

            status, reason, final_url, auth_result = inspect_url_with_retry(offer["url"], offer=dict(offer))

            assert status != "Active", (
                f"CRITICAL VULNERABILITY: HTTP {status_code} ({status_text}) was falsely certified as 'Active'!"
            )
            assert status in ["Review Needed", "Server Error"], (
                f"Expected HTTP {status_code} to downgrade to 'Review Needed' or 'Server Error', got: '{status}'"
            )

    @pytest.mark.parametrize("status_code", [429, 502, 503])
    def test_run_inspection_downgrades_database_status_on_gateway_error(self, status_code, tmp_path):
        """
        Asserts that run_inspection does NOT leave an offer in 'Active' state
        in data/offers.json when encountering 429, 502, or 503.
        """
        test_data_file = tmp_path / "offers.json"
        initial_data = {
            "offers": [
                {
                    "id": "aws-cloud-quest-practitioner",
                    "title": "AWS Cloud Quest Practitioner",
                    "platform": "Amazon Web Services",
                    "category": "Cloud Architecture",
                    "certification_name": "AWS Cloud Quest",
                    "credential_tier": "skill_badge_lab",
                    "url": "https://aws.amazon.com/training/digital/aws-cloud-quest/",
                    "status": "Active"
                }
            ]
        }
        test_data_file.write_text(json.dumps(initial_data), encoding="utf-8")

        mock_resp = MagicMock()
        mock_resp.status_code = status_code
        mock_resp.url = "https://aws.amazon.com/training/digital/aws-cloud-quest/"
        mock_resp.history = []
        mock_resp.text = f"HTTP {status_code} Gateway Intercept"

        with patch("src.inspector.DATA_FILE", test_data_file), \
             patch("httpx.Client.get", return_value=mock_resp):
            updated_offers = run_inspection(use_headless=False)
            inspected_status = updated_offers[0]["status"]

            assert inspected_status != "Active", (
                f"DEFECT: Offer remained 'Active' in database after HTTP {status_code} response!"
            )

    def test_collector_feed_graceful_handling_on_reddit_429(self):
        """
        Asserts that fetch_reddit_leads handles HTTP 429 rate limit responses gracefully
        without raising unhandled exceptions or returning corrupt lead entries.
        """
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.text = "Too Many Requests"

        with patch("httpx.Client.get", return_value=mock_resp), \
             patch("time.sleep", return_value=None):
            leads = fetch_reddit_leads()
            assert isinstance(leads, list)
            assert len(leads) == 0

    @pytest.mark.parametrize("code", [429, 502, 503])
    def test_candidate_vetting_rejects_lead_on_gateway_error(self, code):
        """
        Asserts that candidate lead vetting rejects leads pointing to URLs returning 429/502/503
        and never promotes them to active offers.
        """
        lead = {
            "source": "Reddit r/AzureCertification",
            "title": "Free Microsoft Exam Voucher Wave",
            "url": "https://learn.microsoft.com/credentials",
            "verified_vendor_url": "https://learn.microsoft.com/credentials",
            "platform": "Microsoft Azure",
            "is_authentic_vendor": True
        }

        mock_resp = MagicMock()
        mock_resp.status_code = code
        mock_resp.url = lead["verified_vendor_url"]
        mock_resp.history = []
        mock_resp.text = f"HTTP {code} Service Error"

        with patch("src.dom_inspector.HeadlessDOMInspector.is_available", new=False), \
             patch("httpx.Client.get", return_value=mock_resp):
            promoted, reason = vet_candidate_lead(lead)
            assert promoted is None, f"DEFECT: Lead was promoted under HTTP {code}!"
            assert reason is not None


# ==============================================================================
# Edge Case 2: DOM Inspection with Deceptive Content
# ==============================================================================

class TestDeceptiveContentDOMInspection:
    """
    Adversarial Challenge: Marketing landing pages frequently commingle promotional claims
    (e.g., "Free certification", "Free training", "Free exam preparation") with commercial checkout
    catalogs (e.g., "Cart Total: $245.00", "Add to Cart: $165.00", "Enter credit card to purchase").
    
    Invariant: An offer MUST NEVER be classified as 'Active' unless there is affirmative confirmation
    of a zero-dollar waiver ($0.00 / 100% discount / waiver code applied). If paid catalog fees exist
    without affirmative zero-dollar checkout terms, the page MUST be classified as 'Review Needed'.
    """

    @pytest.mark.parametrize("deceptive_snippet,fee_label", [
        (
            "Oracle University Learning Portal. Free certification training and course modules. "
            "To schedule your proctored exam: Cart Total: $245.00. Add to cart to proceed.",
            "$245 Oracle fee"
        ),
        (
            "Welcome to Microsoft Learn! Free certification paths and self-paced interactive modules. "
            "Pearson VUE proctored exam checkout: Cart Total: $165.00. Enter credit card to purchase.",
            "$165 Microsoft Associate fee"
        ),
        (
            "AWS Training & Certification. Free exam prep courses and sample questions. "
            "Ready to take the AWS Solutions Architect exam? Total: $150.00. Add to cart.",
            "$150 AWS fee"
        ),
        (
            "Cisco Learning Network. Free certification study groups. "
            "CCNA written examination fee: $300.00. Add to cart to reserve your seat.",
            "$300 Cisco fee"
        ),
        (
            "Linux Foundation Training. Free certification webinars and syllabus. "
            "CKA Examination Registration: $395.00 standard catalog price. Buy exam now.",
            "$395 Linux Foundation fee"
        ),
        (
            "Databricks Academy. Free certification overview. "
            "Certification Exam Voucher: $200.00. Enter credit card to purchase.",
            "Generic paid fee"
        ),
    ])
    def test_deceptive_marketing_with_paid_cart_total_never_active(self, deceptive_snippet, fee_label):
        """
        Asserts that pages containing both "Free certification" and standard checkout fees
        are NEVER certified as 'Active', and are correctly flagged with paid_catalog_detected=True.
        """
        res = inspect_rendered_dom(
            rendered_text=deceptive_snippet,
            rendered_title="Free Certification Catalog & Exam Registration",
            final_url="https://vendor.com/exam/checkout"
        )

        assert res["status"] != "Active", (
            f"CRITICAL DEFECT: Deceptive page with {fee_label} was falsely certified as 'Active'! "
            f"Result: {res}"
        )
        assert res["status"] == "Review Needed", (
            f"Expected status to downgrade to 'Review Needed', got '{res['status']}'"
        )
        assert res["zero_dollar_confirmed"] is False, (
            f"zero_dollar_confirmed must be False when checkout requires payment ({fee_label})"
        )

    def test_oracle_free_cert_with_cart_total_245_explicit(self):
        """
        Exact Edge Case from Mission Specification:
        Page containing both 'Free certification' and 'Cart Total: $245.00' without discount coupon.
        Assert status is never falsely 'Active'.
        """
        content = (
            "Oracle University 2026. Explore Free certification learning paths. "
            "Selected item: Oracle Cloud Infrastructure 2026 Certified Architect Associate. "
            "Cart Total: $245.00. Enter payment information to complete your order."
        )
        res = inspect_rendered_dom(content, rendered_title="Oracle Exam Checkout")

        assert res["status"] != "Active", (
            f"CRITICAL DEFECT: Oracle $245 cart total falsely classified as 'Active'!"
        )
        assert res["status"] == "Review Needed"
        assert res["zero_dollar_confirmed"] is False

    def test_legitimate_zero_dollar_waiver_with_discount_coupon_is_active(self):
        """
        Positive Control: An authentic zero-dollar waiver page that contains both
        the original price ($245.00) AND affirmative 100% discount / $0.00 cart balance.
        This MUST be recognized as valid zero-dollar confirmation.
        """
        legitimate_content = (
            "Oracle University Promotion. Exam: OCI Architect Associate. "
            "Original Price: $245.00. "
            "Promotion Applied: Race to Certification 100% discount code. "
            "Order Total: $0.00. Zero cost registration confirmed."
        )
        res = inspect_rendered_dom(legitimate_content, rendered_title="Order Confirmation - $0.00")

        assert res["zero_dollar_confirmed"] is True
        assert res["status"] == "Active"

    def test_dual_gate_rejects_offer_when_dom_detects_paid_catalog(self):
        """
        Asserts that evaluate_dual_gate enforces downgrade when DOM inspection
        indicates a paid catalog without affirmative waiver terms.
        """
        gate_status, gate_reason = evaluate_dual_gate(
            dom_status="Review Needed",
            has_zero_dollar=False,
            screenshot_valid=True,
            auth_score=95,
            http_status=200
        )
        assert gate_status == "Review Needed"
        assert "DOM failed" in gate_reason or "affirmative" in gate_reason


# ==============================================================================
# Edge Case 3: Corrupted or Zero-Byte Candidate Payloads in Collector
# ==============================================================================

class TestCorruptedCandidatePayloads:
    """
    Adversarial Challenge: Community lead feeds, webhooks, and candidates.json files
    may present corrupted, zero-byte, malformed, or hostile payloads.
    
    Invariant: The collector and candidate ingestion engine must safely discard all
    corrupt, truncated, or zero-byte payloads without raising unhandled exceptions or
    corrupting the data/offers.json database.
    """

    @pytest.mark.parametrize("corrupt_lead,description", [
        (None, "None object"),
        ({}, "Empty dictionary"),
        ("", "Empty string"),
        (b"", "Zero-byte bytearray"),
        ({"title": None, "url": None}, "Dictionary with None values"),
        ({"title": 12345, "url": True, "platform": None}, "Dictionary with invalid types"),
        ({"id": "malicious", "url": "not_a_url", "is_authentic_vendor": True}, "Malformed non-HTTP URL"),
        ({"title": "Valid Title", "url": "http://insecure-http-url.com", "is_authentic_vendor": True}, "Insecure HTTP URL"),
        ("not_a_dictionary_at_all", "Raw string payload"),
        (42, "Integer payload"),
        ([1, 2, 3], "List payload instead of lead object"),
    ])
    def test_vet_candidate_lead_safely_discards_corrupted_payload(self, corrupt_lead, description):
        """
        Asserts that vet_candidate_lead safely discards any corrupted candidate payload
        without raising an unhandled exception.
        """
        try:
            promoted, reason = vet_candidate_lead(corrupt_lead)
            assert promoted is None, f"DEFECT: Corrupted lead ({description}) was promoted!"
            assert isinstance(reason, str)
        except Exception as e:
            pytest.fail(f"CRASH DEFECT: vet_candidate_lead raised unhandled {type(e).__name__} on {description}: {e}")

    def test_vet_candidates_batch_with_mixed_corrupt_and_valid_leads(self):
        """
        Asserts that vet_candidates processes a batch containing corrupted payloads,
        safely rejecting corrupt entries without interrupting the evaluation of valid leads.
        """
        corrupted_batch = [
            None,
            {},
            b"",
            {"title": None},
            "string_payload",
            {
                "source": "Reddit r/AzureCertification",
                "title": "50% off Azure Certification",
                "url": "https://learn.microsoft.com/credentials",
                "platform": "Microsoft Azure",
                "is_authentic_vendor": True
            }
        ]

        try:
            promoted, audit_log = vet_candidates(corrupted_batch)
            assert isinstance(promoted, list)
            assert isinstance(audit_log, list)
            assert len(promoted) == 0  # 50% off and corrupted must all be rejected
            assert len(audit_log) == len(corrupted_batch)
        except Exception as e:
            pytest.fail(f"CRASH DEFECT: vet_candidates crashed on batch with corrupt entries: {e}")

    def test_ingest_and_vet_candidates_zero_byte_file(self, tmp_path):
        """
        Asserts that ingest_and_vet_candidates handles a zero-byte candidates.json file
        gracefully without raising JSONDecodeError.
        """
        empty_cand_file = tmp_path / "candidates.json"
        empty_cand_file.write_bytes(b"")

        empty_offers_file = tmp_path / "offers.json"
        empty_offers_file.write_text(json.dumps({"offers": []}), encoding="utf-8")

        try:
            promoted, rejected = ingest_and_vet_candidates(
                candidates_file=empty_cand_file,
                offers_file=empty_offers_file
            )
            assert promoted == 0
            assert rejected == 0
        except Exception as e:
            pytest.fail(f"CRASH DEFECT: ingest_and_vet_candidates raised unhandled {type(e).__name__} on zero-byte file: {e}")

    def test_ingest_and_vet_candidates_malformed_json_file(self, tmp_path):
        """
        Asserts that ingest_and_vet_candidates handles syntax-corrupted JSON files
        without crashing the automation refresh pipeline.
        """
        corrupt_cand_file = tmp_path / "candidates.json"
        corrupt_cand_file.write_text("{ 'broken_json': [ unterminated", encoding="utf-8")

        empty_offers_file = tmp_path / "offers.json"
        empty_offers_file.write_text(json.dumps({"offers": []}), encoding="utf-8")

        try:
            promoted, rejected = ingest_and_vet_candidates(
                candidates_file=corrupt_cand_file,
                offers_file=empty_offers_file
            )
            assert promoted == 0
            assert rejected == 0
        except Exception as e:
            pytest.fail(f"CRASH DEFECT: ingest_and_vet_candidates raised unhandled {type(e).__name__} on malformed JSON: {e}")


# ==============================================================================
# Edge Case 4: Concurrent or Repeated Self-Healing Events
# ==============================================================================

class TestSelfHealingIdempotenceAndConcurrency:
    """
    Adversarial Challenge: During automated refresh or concurrent execution, self-healing
    events may be triggered multiple times in succession or concurrently across threads.
    
    Invariant:
    1. Idempotence: Repeated self-healing evaluations of an already recovered offer must not
       mutate timestamps, corrupt existing self-healing audit metadata, or duplicate logs.
    2. Concurrency: Concurrent calls to apply_self_healing must remain thread-safe and
       produce valid, schema-compliant Offer objects.
    3. Schema Integrity: Every healed offer must strictly satisfy the Pydantic Offer schema.
    """

    def test_repeated_self_healing_event_idempotence(self):
        """
        Asserts that applying self-healing repeatedly to an already healed offer
        maintains state idempotence and does not overwrite original recovery timestamps.
        """
        original_offer = {
            "id": "oracle-oci-foundations-associate",
            "title": "Oracle Cloud Infrastructure Foundations Associate",
            "platform": "Oracle Cloud",
            "category": "Cloud Architecture",
            "certification_name": "Oracle Cloud Foundations",
            "credential_tier": "proctored_exam",
            "url": "https://mylearn.oracle.com/ou/course/oracle-cloud-infrastructure",
            "status": "Review Needed",
            "screenshot_path": "docs/screenshots/oracle-oci-foundations-associate.png"
        }

        # Step 1: Portal recovers from 'Review Needed' to 'Active'
        inspection_heal = {
            "status": "Active",
            "reason": "Portal online: affirmative zero-dollar voucher confirmed"
        }
        healed_first = apply_self_healing(original_offer, inspection_heal)

        assert healed_first["status"] == "Active"
        assert "self_healing_event" in healed_first
        first_event = healed_first["self_healing_event"]
        assert first_event["previous_status"] == "Review Needed"
        assert first_event["healed_status"] == "Active"
        first_timestamp = first_event["timestamp"]

        # Step 2: Next scheduled run evaluates the now 'Active' offer (still Active)
        inspection_steady = {
            "status": "Active",
            "reason": "Portal online: affirmative zero-dollar voucher confirmed"
        }
        healed_second = apply_self_healing(healed_first, inspection_steady)

        assert healed_second["status"] == "Active"
        # Idempotence assertion: self_healing_event timestamp must be preserved, not overwritten
        assert healed_second.get("self_healing_event") == first_event, (
            "DEFECT: Repeated self-healing on active offer modified the audit event!"
        )

    def test_self_healing_all_triage_source_states(self):
        """
        Asserts that self-healing correctly handles recovery from all recognized triage states:
        'Review Needed', 'Registrations Closed', 'Broken Link', and 'Expired'.
        """
        triage_states = ["Review Needed", "Registrations Closed", "Broken Link", "Expired"]

        for triage_status in triage_states:
            offer = {
                "id": "test-healed-offer",
                "title": "Test Cloud Certification",
                "platform": "Multi-Cloud",
                "category": "Cloud Architecture",
                "certification_name": "Test Cert",
                "credential_tier": "proctored_exam",
                "url": "https://aws.amazon.com/test",
                "status": triage_status,
                "screenshot_path": "docs/screenshots/test-healed-offer.png"
            }

            healed = apply_self_healing(offer, {"status": "Active", "reason": "Recovered online"})

            assert healed["status"] == "Active", f"Failed to heal from '{triage_status}'"
            assert healed.get("self_healing_event", {}).get("previous_status") == triage_status
            assert healed.get("self_healing_event", {}).get("healed_status") == "Active"

    def test_concurrent_self_healing_thread_safety(self):
        """
        Simulates 25 concurrent threads applying self-healing to distinct and shared offers
        to verify absence of race conditions, exceptions, or schema corruption.
        """
        errors = []
        results = []

        def worker(thread_idx: int):
            try:
                offer = {
                    "id": f"concurrent-offer-{thread_idx % 5}",
                    "title": f"Concurrent Offer {thread_idx % 5}",
                    "platform": "Google Cloud",
                    "category": "Cloud Architecture",
                    "certification_name": "Cloud Digital Leader",
                    "credential_tier": "proctored_exam",
                    "url": "https://cloud.google.com/certification",
                    "status": "Review Needed",
                    "screenshot_path": f"docs/screenshots/concurrent-offer-{thread_idx % 5}.png"
                }
                healed = apply_self_healing(offer, {"status": "Active", "reason": f"Thread {thread_idx} verified"})
                results.append(healed)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(25)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread safety failure in apply_self_healing: {errors}"
        assert len(results) == 25
        for res in results:
            assert res["status"] == "Active"
            assert "self_healing_event" in res

    def test_healed_offer_strictly_conforms_to_pydantic_schema(self):
        """
        Asserts that an offer dictionary produced by self-healing validates cleanly
        against the Pydantic Offer schema with zero validation errors.
        """
        raw_offer = {
            "id": "oracle-oci-foundations-associate",
            "title": "Oracle Cloud Infrastructure Foundations Associate",
            "platform": "Oracle Cloud",
            "category": "Cloud Architecture",
            "certification_name": "Oracle Cloud Foundations",
            "credential_tier": "proctored_exam",
            "proctoring_type": "pearson_vue",
            "accredited_body": "Oracle University",
            "url": "https://mylearn.oracle.com/ou/course/oracle-cloud-infrastructure",
            "status": "Review Needed",
            "screenshot_path": "docs/screenshots/oracle-oci-foundations-associate.png",
            "cart_balance_verified": "$0.00 (100% Free / Waiver Confirmed)"
        }

        healed_dict = apply_self_healing(raw_offer, {"status": "Active", "reason": "Restored"})

        try:
            valid_model = Offer(**healed_dict)
            assert valid_model.status == "Active"
            assert valid_model.id == raw_offer["id"]
        except Exception as e:
            pytest.fail(f"Pydantic schema validation defect on healed offer: {e}")
