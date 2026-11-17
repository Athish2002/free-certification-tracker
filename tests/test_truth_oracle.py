"""
Tests for Truth Oracle: Authoritative Online Policy Corroboration Engine.
Enforces mathematical invariants, online ground-truth alignment, and anti-misleading safeguards.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from src.truth_oracle import (
    POLICY_ANNUAL_WINDOW_CLOSED,
    POLICY_HISTORICAL_EVENT_WAVE,
    POLICY_PARTIAL_DISCOUNT_COPAY,
    POLICY_STUDENT_VERIFIED_ONLY,
    POLICY_VERIFIED_100PCT_FREE,
    TRUTH_POLICY_REGISTRY,
    audit_and_enrich_offers,
    corroborate_offer,
    verify_truth_invariants,
)

ROOT = Path(__file__).resolve().parent.parent
DATA_OFFERS = ROOT / "data" / "offers.json"
README_FILE = ROOT / "README.md"
DOCS_HTML = ROOT / "docs" / "index.html"


@pytest.fixture(scope="module")
def offers_data() -> list[dict[str, Any]]:
    assert DATA_OFFERS.exists(), "data/offers.json missing"
    with open(DATA_OFFERS, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("offers", [])


class TestTruthOracleRegistry:
    """Validates the completeness and integrity of the Ground Truth Policy Registry."""

    def test_registry_contains_all_canonical_offers(self, offers_data):
        """Every tracked offer must have a defined ground truth policy in the registry."""
        for offer in offers_data:
            oid = offer["id"]
            if oid not in TRUTH_POLICY_REGISTRY:
                from src.truth_oracle import corroborate_offer

                corroborate_offer(offer)
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

    def test_no_policy_claims_zero_dollar_without_a_quoted_source(self):
        """
        Replaces an earlier test that asserted the two Oracle OCI offers were "confirmed 100% free".
        When their pages were read on 2026-11-16 one learning path was retired and the other no longer
        loaded, so that assertion encoded a claim nobody had checked. The rule that holds for every
        policy: zero_dollar_confirmed may be true only when a quoted source is recorded.
        """
        from src.truth_oracle import CURATED_POLICY_OVERRIDES, missing_evidence_fields

        for oid, policy in CURATED_POLICY_OVERRIDES.items():
            if policy.get("zero_dollar_confirmed") and policy.get("enforce_status") == "Active":
                assert missing_evidence_fields(policy) == [], f"{oid} claims zero-dollar without a quoted source"
        for oid in ["oracle-oci-free-cert", "oracle-oci-generative-ai-cert"]:
            assert CURATED_POLICY_OVERRIDES[oid]["enforce_status"] != "Active"
            assert CURATED_POLICY_OVERRIDES[oid]["zero_dollar_confirmed"] is False

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
        first_pass, _ = audit_and_enrich_offers(offers_data, strict_enforcement=True)
        second_pass, summary2 = audit_and_enrich_offers(first_pass, strict_enforcement=True)
        assert summary2["corrections_applied"] == 0, "Second audit pass should require 0 corrections"
        assert len(first_pass) == len(second_pass)

    def test_database_passes_all_truth_invariants(self, offers_data):
        """The canonical database must have zero truth invariant violations."""
        enriched, _ = audit_and_enrich_offers(offers_data, strict_enforcement=True)
        violations = verify_truth_invariants(enriched)
        assert not violations, f"Truth invariant violations detected in database: {violations}"

    def test_audit_and_enrich_preserves_verified_urls(self, offers_data):
        """Enrichment must never null out populated direct_verified_url or verified_vendor_url."""
        enriched, _ = audit_and_enrich_offers(offers_data, strict_enforcement=True)
        for orig, enr in zip(offers_data, enriched, strict=True):
            if orig.get("direct_verified_url"):
                assert enr.get("direct_verified_url") is not None, f"direct_verified_url became None for {orig['id']}"
            if orig.get("verified_vendor_url"):
                assert enr.get("verified_vendor_url") is not None, f"verified_vendor_url became None for {orig['id']}"

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
        """README.md summary must say policy notes are hand-maintained, not '100% corroborated'."""
        readme = README_FILE.read_text(encoding="utf-8")
        assert "| **Policy Notes** | **Maintained by hand** |" in readme
        assert "100% Policy Corroborated" not in readme

    def test_docs_html_contains_truth_oracle_elements(self):
        """docs/index.html must contain #proofModalTruthCard and policy indicator elements."""
        html = DOCS_HTML.read_text(encoding="utf-8")
        assert 'id="proofModalTruthCard"' in html
        assert 'id="proofModalPolicyType"' in html
        assert 'id="proofModalTruthSource"' in html
        assert 'id="proofModalTruthSourceName"' in html
        assert 'id="proofModalTruthNotes"' in html


class TestTruthOracleTimeoutCircuitBreaker:
    """Verifies that the Truth Oracle execution circuit breaker does not block on timeout."""

    def test_oracle_non_blocking_timeout_shutdown(self):
        """Shutdown with wait=False must not block main thread when worker task times out."""
        import concurrent.futures
        import time

        def hanging_task():
            time.sleep(2.0)
            return "done"

        start_time = time.perf_counter()
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        timed_out = False
        try:
            future = executor.submit(hanging_task)
            future.result(timeout=0.05)
        except (concurrent.futures.TimeoutError, TimeoutError):
            timed_out = True
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

        elapsed = time.perf_counter() - start_time
        assert timed_out is True
        # Elapsed must be substantially less than the 2.0s sleep of the background worker
        assert elapsed < 0.5, f"Executor shutdown blocked main thread: elapsed={elapsed:.3f}s"


class TestReviewDueEnforcement:
    """
    review_due_utc must be acted on: a hand-maintained policy that is past its review date
    cannot keep an offer Active. It becomes Review Needed with a note naming the date.
    """

    @staticmethod
    def _policy(review_due: str, enforce_status: str = "Active") -> dict:
        return {
            "provider": "Oracle Cloud",
            "exam_name": "Mock Cert",
            "policy_type": "verified_100pct_free",
            "real_exam_cost_usd": 0.0,
            "verified_discount_pct": 100,
            "truth_source_name": "Oracle",
            "truth_source_url": "https://mylearn.oracle.com/",
            "verdict_notes": "Notes",
            "enforce_status": enforce_status,
            "zero_dollar_confirmed": True,
            "valid_through_utc": "2099-01-01T00:00:00Z",
            "review_due_utc": review_due,
        }

    @staticmethod
    def _offer(status: str = "Active") -> dict:
        return {
            "id": "mock-review-due",
            "title": "Mock Cert",
            "platform": "Oracle Cloud",
            "url": "https://mylearn.oracle.com/cert",
            "status": status,
            "eligibility": "Global",
            "inspection_notes": "Page check passed",
            "visual_proof": {"zero_dollar_confirmed": True, "status": "missing", "screenshot_path": None},
        }

    def test_review_overdue_since_helper(self):
        from datetime import UTC, datetime

        from src.truth_oracle import review_overdue_since

        now = datetime(2026, 11, 16, tzinfo=UTC)
        assert review_overdue_since({"review_due_utc": "2026-11-01T00:00:00Z"}, now) == "2026-11-01T00:00:00Z"
        assert review_overdue_since({"review_due_utc": "2026-12-01T00:00:00Z"}, now) is None
        # Exactly on the due date is not yet overdue
        assert review_overdue_since({"review_due_utc": "2026-11-16T00:00:00Z"}, now) is None
        # Naive timestamps are read as UTC
        assert review_overdue_since({"review_due_utc": "2026-11-01T00:00:00"}, now) == "2026-11-01T00:00:00"
        # Missing / unparseable / empty inputs are not treated as overdue
        assert review_overdue_since({}, now) is None
        assert review_overdue_since(None, now) is None
        assert review_overdue_since({"review_due_utc": "not-a-date"}, now) is None
        assert review_overdue_since({"review_due_utc": None}, now) is None

    def test_overdue_active_policy_downgrades_offer_to_review_needed(self):
        from unittest.mock import patch

        from src.truth_oracle import TRUTH_POLICY_REGISTRY, audit_and_enrich_offers

        with patch.dict(TRUTH_POLICY_REGISTRY, {"mock-review-due": self._policy("2020-01-15T00:00:00Z")}):
            enriched, summary = audit_and_enrich_offers([self._offer("Active")], strict_enforcement=True)

        offer = enriched[0]
        assert offer["status"] == "Review Needed"
        assert "overdue for review since 2020-01-15" in offer["inspection_notes"]
        assert "hand-maintained policy" in offer["inspection_notes"]
        assert offer["truth_verification"]["review_overdue"] is True
        assert offer["visual_proof"]["zero_dollar_confirmed"] is False
        assert summary["corrections_applied"] >= 1

    def test_policy_within_review_date_keeps_offer_active(self):
        from unittest.mock import patch

        from src.truth_oracle import TRUTH_POLICY_REGISTRY, audit_and_enrich_offers

        with patch.dict(TRUTH_POLICY_REGISTRY, {"mock-review-due": self._policy("2099-01-01T00:00:00Z")}):
            enriched, _ = audit_and_enrich_offers([self._offer("Active")], strict_enforcement=True)

        offer = enriched[0]
        assert offer["status"] == "Active"
        assert offer["inspection_notes"] == "Page check passed"
        assert offer["truth_verification"]["review_overdue"] is False
        assert offer["visual_proof"]["zero_dollar_confirmed"] is True

    def test_overdue_policy_cannot_be_healed_back_to_active(self):
        """An offer already in Review Needed must not be promoted to Active by an overdue Active policy."""
        from unittest.mock import patch

        from src.truth_oracle import TRUTH_POLICY_REGISTRY, audit_and_enrich_offers

        with patch.dict(TRUTH_POLICY_REGISTRY, {"mock-review-due": self._policy("2020-01-15T00:00:00Z")}):
            enriched, _ = audit_and_enrich_offers([self._offer("Review Needed")], strict_enforcement=True)
        assert enriched[0]["status"] == "Review Needed"
        assert "overdue for review since 2020-01-15" in enriched[0]["inspection_notes"]

    def test_overdue_non_active_policy_keeps_its_own_status(self):
        """Overdue review only blocks Active; an Expired/Closed policy still enforces its own status."""
        from unittest.mock import patch

        from src.truth_oracle import TRUTH_POLICY_REGISTRY, audit_and_enrich_offers

        with patch.dict(
            TRUTH_POLICY_REGISTRY, {"mock-review-due": self._policy("2020-01-15T00:00:00Z", enforce_status="Expired")}
        ):
            enriched, _ = audit_and_enrich_offers([self._offer("Active")], strict_enforcement=True)
        assert enriched[0]["status"] == "Expired"
        assert "overdue for review" not in enriched[0]["inspection_notes"]

    def test_no_active_offer_in_data_has_an_overdue_policy(self):
        """Canonical data invariant: nothing in data/offers.json is Active on an overdue curated policy."""
        import json

        from src.truth_oracle import CURATED_POLICY_OVERRIDES, review_overdue_since

        data = json.loads((README_FILE.parent / "data" / "offers.json").read_text(encoding="utf-8"))
        for o in data["offers"]:
            policy = CURATED_POLICY_OVERRIDES.get(o["id"])
            if o.get("status") == "Active" and policy and policy.get("enforce_status") == "Active":
                assert review_overdue_since(policy) is None, (
                    f"{o['id']} is Active but its curated policy has been overdue for review "
                    f"since {policy.get('review_due_utc')}"
                )


class TestEvidenceRequiredForActive:
    """
    A curated policy may keep an offer Active only when it records who read the vendor page,
    when, where, and the exact sentence that states the terms.
    """

    EVIDENCE = {
        "reviewed_by": "A. Maintainer",
        "reviewed_on": "2026-11-16",
        "evidence_url": "https://mylearn.oracle.com/terms",
        "evidence_quote": "The exam is free of charge until 31 December.",
    }

    def test_missing_evidence_fields_helper(self):
        from src.truth_oracle import EVIDENCE_FIELDS, missing_evidence_fields

        assert missing_evidence_fields(None) == list(EVIDENCE_FIELDS)
        assert missing_evidence_fields({}) == list(EVIDENCE_FIELDS)
        assert missing_evidence_fields(dict(self.EVIDENCE)) == []
        # Blank strings and non-strings do not count as evidence
        assert missing_evidence_fields({**self.EVIDENCE, "evidence_quote": "   "}) == ["evidence_quote"]
        assert missing_evidence_fields({**self.EVIDENCE, "reviewed_by": None}) == ["reviewed_by"]
        # The source must be an https link
        assert missing_evidence_fields({**self.EVIDENCE, "evidence_url": "http://mylearn.oracle.com/"}) == [
            "evidence_url"
        ]

    def _run(self, policy_extra: dict, offer_status: str = "Active") -> dict:
        from unittest.mock import patch

        from src.truth_oracle import CURATED_POLICY_OVERRIDES, TRUTH_POLICY_REGISTRY, audit_and_enrich_offers

        policy = {**TestReviewDueEnforcement._policy("2099-01-01T00:00:00Z"), **policy_extra}
        offer = TestReviewDueEnforcement._offer(offer_status)
        with (
            patch.dict(CURATED_POLICY_OVERRIDES, {"mock-review-due": policy}),
            patch.dict(TRUTH_POLICY_REGISTRY, {"mock-review-due": policy}),
        ):
            enriched, _ = audit_and_enrich_offers([offer], strict_enforcement=True)
        return enriched[0]

    def test_curated_active_policy_without_evidence_is_not_active(self):
        offer = self._run({})
        assert offer["status"] == "Review Needed"
        assert "No Recorded Check" in offer["inspection_notes"]
        assert "evidence_quote" in offer["inspection_notes"]
        assert offer["visual_proof"]["zero_dollar_confirmed"] is False

    def test_partial_evidence_is_not_enough(self):
        partial = {k: v for k, v in self.EVIDENCE.items() if k != "evidence_quote"}
        offer = self._run(partial)
        assert offer["status"] == "Review Needed"
        assert "missing: evidence_quote" in offer["inspection_notes"]

    def test_curated_active_policy_with_evidence_stays_active(self):
        offer = self._run(dict(self.EVIDENCE))
        assert offer["status"] == "Active"
        assert offer["inspection_notes"] == "Page check passed"
        assert offer["truth_verification"]["evidence_quote"] == self.EVIDENCE["evidence_quote"]
        assert offer["truth_verification"]["reviewed_by"] == "A. Maintainer"

    def test_evidence_does_not_rescue_an_overdue_policy(self):
        offer = self._run({**self.EVIDENCE, "review_due_utc": "2020-01-15T00:00:00Z"})
        assert offer["status"] == "Review Needed"
        assert "overdue for review" in offer["inspection_notes"]

    def test_no_active_offer_in_data_lacks_evidence(self):
        """Canonical data invariant: every Active offer in data/offers.json has a quoted source."""
        import json

        from src.truth_oracle import CURATED_POLICY_OVERRIDES, missing_evidence_fields

        data = json.loads((README_FILE.parent / "data" / "offers.json").read_text(encoding="utf-8"))
        for o in data["offers"]:
            if o.get("status") == "Active":
                policy = CURATED_POLICY_OVERRIDES.get(o["id"])
                assert policy is not None, f"{o['id']} is Active without a curated policy"
                assert missing_evidence_fields(policy) == [], f"{o['id']} is Active without a quoted source"


class TestQuoteCheck:
    """The automated check that a recorded evidence sentence is still on the vendor page."""

    QUOTE = "The courses in this track are free, and many of the badges are also free!"
    PAGE = (
        "Hands-On Essentials\n"
        + ("Filler text about workshops. " * 20)
        + "\nThe courses in this track are  free, and many of the badges are also free!\n"
    )

    def test_quote_matching_ignores_case_whitespace_and_curly_punctuation(self):
        from src.evidence_check import quote_on_page

        assert quote_on_page(self.QUOTE, self.PAGE)
        assert quote_on_page("you’ve learned — a lot", "Badges show what YOU'VE   learned - a lot here")
        assert quote_on_page("Free Online Course", "", page_title="Intro by Cisco: Free Online Course")
        # A changed sentence does not match, and an empty quote never matches
        assert not quote_on_page(self.QUOTE, self.PAGE.replace("are also free", "cost $25"))
        assert not quote_on_page("   ", self.PAGE)

    def test_classify_separates_missing_from_unreadable(self):
        from src.evidence_check import FOUND, NOT_FOUND, UNREADABLE, classify_page

        assert classify_page(self.QUOTE, self.PAGE) == FOUND
        assert classify_page(self.QUOTE, "A long page about something else entirely. " * 20) == NOT_FOUND
        # A failed load or a near-empty page is not evidence that the sentence was removed
        assert classify_page(self.QUOTE, None) == UNREADABLE
        assert classify_page(self.QUOTE, "Loading...") == UNREADABLE

    def test_misses_accumulate_and_reset(self):
        from src.evidence_check import FOUND, NOT_FOUND, UNREADABLE, quote_missing, update_record

        rec = update_record(None, NOT_FOUND)
        assert rec["consecutive_misses"] == 1 and not quote_missing(rec)
        rec = update_record(rec, UNREADABLE)
        assert rec["consecutive_misses"] == 1 and not quote_missing(rec)
        rec = update_record(rec, NOT_FOUND)
        assert rec["consecutive_misses"] == 2 and quote_missing(rec)
        rec = update_record(rec, FOUND)
        assert rec["consecutive_misses"] == 0 and not quote_missing(rec) and rec["last_found_at"]

    def test_offer_with_missing_quote_is_not_active(self):
        from unittest.mock import patch

        from src.truth_oracle import CURATED_POLICY_OVERRIDES, TRUTH_POLICY_REGISTRY, audit_and_enrich_offers

        policy = {**TestReviewDueEnforcement._policy("2099-01-01T00:00:00Z"), **TestEvidenceRequiredForActive.EVIDENCE}

        def run(evidence_check):
            offer = {**TestReviewDueEnforcement._offer("Active"), "evidence_check": evidence_check}
            with (
                patch.dict(CURATED_POLICY_OVERRIDES, {"mock-review-due": policy}),
                patch.dict(TRUTH_POLICY_REGISTRY, {"mock-review-due": policy}),
            ):
                return audit_and_enrich_offers([offer], strict_enforcement=True)[0][0]

        gone = run({"result": "not_found", "consecutive_misses": 2})
        assert gone["status"] == "Review Needed"
        assert "Quoted Source Gone" in gone["inspection_notes"]
        assert gone["visual_proof"]["zero_dollar_confirmed"] is False
        # One miss is not enough, and a found result keeps the offer Active
        assert run({"result": "not_found", "consecutive_misses": 1})["status"] == "Active"
        assert run({"result": "found", "consecutive_misses": 0})["status"] == "Active"

    def test_retired_wording_is_treated_as_closed(self):
        from src.dom_inspector import inspect_rendered_dom

        res = inspect_rendered_dom(
            "Applied Skills. This Applied Skill assessment has been retired. Free learning.", "Credential"
        )
        assert res["status"] != "Active"
        assert res["zero_dollar_confirmed"] is False
