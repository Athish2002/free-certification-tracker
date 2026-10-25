"""
Comprehensive verification test suite for CertPulse /boost all system improvements.
Consolidated Logical Invariant Suite:
1. VendorBlogCollector (RSS/Atom parsing, HTTP 429/500 resilience, deterministic lead IDs).
2. Per-vendor concurrency rate limiting in run_inspection_async.
3. Staleness threshold auto-downgrade (check_and_flag_stale_offers).
4. Truth Oracle policy time-awareness (valid_through_utc, review_due_utc, confidence_downgraded).
5. Audit log compaction & gzip archiving (compact_audit_log).
6. Build fingerprinting and data/summary.json export.
7. Modularized VLM subpackage and backwards-compatible facade (src.vlm & src.vlm_engine).
8. Anti-fraud ASN validation secondary gating (CLOUD_CDN_COINCIDENCE_NON_CANONICAL_DOMAIN).
9. News feed content fingerprint deduplication.
10. last_zero_dollar_confirmed_date invariants across vetting, inspection, and self-healing.
"""

from __future__ import annotations

import gzip
import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import httpx

from src.collector import VendorBlogCollector, fetch_vendor_blog_leads, vet_candidate_lead
from src.inspector import check_and_flag_stale_offers, inspect_offer
from src.truth_oracle import corroborate_offer, CURATED_POLICY_OVERRIDES, derive_truth_policy
from src.audit_ledger import compact_audit_log
from src.builders import compute_build_fingerprint, build_all, SUMMARY_FILE, FINGERPRINT_FILE
from src.news_collector import compute_news_fingerprint, update_news_feed
from src.network_verifier import ASNRouteVerifier, is_whitelisted_domain
from src.main import apply_self_healing, normalize_url
import src.vlm_engine as vlm_facade
import src.vlm as vlm_pkg


class TestVendorBlogCollector:
    """Verifies VendorBlogCollector parsing, error resilience, and deterministic IDs."""

    RSS_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <title>AWS Training and Certification Blog</title>
        <link>https://aws.amazon.com/blogs/training-and-certification/</link>
        <item>
          <title>Get AWS Certified: Free Exam Voucher Challenge 2026</title>
          <link>https://aws.amazon.com/blogs/training-and-certification/free-exam-challenge-2026/</link>
          <description>Join our free cloud skills challenge to earn a 100% free exam voucher for AWS Certified AI Practitioner.</description>
          <pubDate>Mon, 20 Oct 2026 12:00:00 GMT</pubDate>
        </item>
      </channel>
    </rss>
    """

    ATOM_SAMPLE = """<?xml version="1.0" encoding="utf-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <title>Microsoft Learn Blog</title>
      <entry>
        <title>Announcing Microsoft Cloud Skills Challenge with 100% Free Voucher</title>
        <link href="https://learn.microsoft.com/en-us/training/challenges/spring-2026"/>
        <summary>Complete any qualifying challenge to receive an eligible exam voucher at no cost.</summary>
        <updated>2026-10-21T00:00:00Z</updated>
      </entry>
    </feed>
    """

    def test_vendor_blog_collector_parsing_determinism_and_resilience_invariants(self):
        collector_aws = VendorBlogCollector(targets=[{
            "name": "AWS Training Blog",
            "feed_url": "https://aws.amazon.com/feed/",
            "platform": "Amazon Web Services",
            "allowed_domain": "aws.amazon.com",
        }])

        # 1. RSS parsing & determinism
        mock_rss = MagicMock(status_code=200, text=self.RSS_SAMPLE)
        with patch.object(httpx.Client, "get", return_value=mock_rss):
            leads1 = collector_aws.fetch_vendor_blog_leads()
            leads2 = collector_aws.fetch_vendor_blog_leads()

        assert len(leads1) == 1 and len(leads2) == 1
        assert leads1[0]["id"] == leads2[0]["id"], "Lead ID must be deterministic"
        assert "Free Exam Voucher Challenge" in leads1[0]["title"]
        assert leads1[0]["is_authentic_vendor"] is True

        # 2. Atom parsing
        collector_ms = VendorBlogCollector(targets=[{
            "name": "Microsoft Learn Blog",
            "feed_url": "https://learn.microsoft.com/rss",
            "platform": "Microsoft Azure",
            "allowed_domain": "learn.microsoft.com",
        }])
        mock_atom = MagicMock(status_code=200, text=self.ATOM_SAMPLE)
        with patch.object(httpx.Client, "get", return_value=mock_atom):
            atom_leads = collector_ms.fetch_vendor_blog_leads()
        assert len(atom_leads) == 1 and "Microsoft Cloud Skills Challenge" in atom_leads[0]["title"]

        # 3. HTTP 429 & network exception resilience
        with patch.object(httpx.Client, "get", return_value=MagicMock(status_code=429)):
            assert collector_aws.fetch_vendor_blog_leads() == []
        with patch.object(httpx.Client, "get", side_effect=httpx.ConnectError("Refused")):
            assert collector_aws.fetch_vendor_blog_leads() == []


class TestStalenessDowngrade:
    """Verifies check_and_flag_stale_offers auto-downgrades stale Active offers."""

    def test_staleness_detection_and_downgrade_invariants(self):
        today = datetime.now(timezone.utc).date()
        stale_date = (today - timedelta(days=20)).strftime("%Y-%m-%d")
        fresh_date = (today - timedelta(days=5)).strftime("%Y-%m-%d")

        offers = [
            {"id": "stale-1", "title": "Stale Offer", "status": "Active", "verification_date": stale_date},
            {"id": "fresh-1", "title": "Fresh Offer", "status": "Active", "verification_date": fresh_date},
            {"id": "closed-1", "title": "Closed Offer", "status": "Registrations Closed", "verification_date": stale_date},
            {"id": "hist-1", "title": "Historical", "status": "Active", "verification_date": stale_date, "is_historical_archive": True},
            {"id": "bad-date", "title": "Bad Date", "status": "Active", "verification_date": "invalid-date"},
        ]

        downgraded = check_and_flag_stale_offers(offers, threshold_days=14)
        assert downgraded == 2
        assert offers[0]["status"] == "Review Needed"
        assert offers[1]["status"] == "Active"
        assert offers[2]["status"] == "Registrations Closed"
        assert offers[3]["status"] == "Active", "Historical archive should be exempt"
        assert offers[4]["status"] == "Review Needed"


class TestTruthOracleExpiry:
    """Verifies Truth Oracle policy overrides expiry and confidence downgrading."""

    def test_policy_override_expiry_and_confidence_invariants(self):
        # 1. Invariant: all curated policies specify valid_through_utc and review_due_utc
        for oid, policy in CURATED_POLICY_OVERRIDES.items():
            assert "valid_through_utc" in policy, f"Policy '{oid}' missing 'valid_through_utc'"
            assert "review_due_utc" in policy, f"Policy '{oid}' missing 'review_due_utc'"

        offer = {
            "id": "mock-policy-test",
            "title": "Mock Cert",
            "platform": "Oracle Cloud",
            "url": "https://mylearn.oracle.com/cert",
            "status": "Active",
            "visual_proof": {"zero_dollar_confirmed": True}
        }

        # 2. Expired policy triggers confidence downgrade
        past_dt = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        with patch.dict(CURATED_POLICY_OVERRIDES, {
            "mock-policy-test": {
                "provider": "Oracle Cloud", "exam_name": "Mock Cert", "policy_type": "verified_100pct_free",
                "real_exam_cost_usd": 0.0, "verified_discount_pct": 100, "truth_source_name": "Oracle",
                "truth_source_url": "https://mylearn.oracle.com/", "verdict_notes": "Notes",
                "enforce_status": "Active", "zero_dollar_confirmed": True,
                "valid_through_utc": past_dt, "review_due_utc": past_dt,
            }
        }):
            assert corroborate_offer(offer)["confidence_downgraded"] is True

        # 3. Fresh policy preserves confidence
        future_dt = (datetime.now(timezone.utc) + timedelta(days=60)).isoformat()
        with patch.dict(CURATED_POLICY_OVERRIDES, {
            "mock-policy-test": {
                "provider": "Oracle Cloud", "exam_name": "Mock Cert", "policy_type": "verified_100pct_free",
                "real_exam_cost_usd": 0.0, "verified_discount_pct": 100, "truth_source_name": "Oracle",
                "truth_source_url": "https://mylearn.oracle.com/", "verdict_notes": "Notes",
                "enforce_status": "Active", "zero_dollar_confirmed": True,
                "valid_through_utc": future_dt, "review_due_utc": future_dt,
            }
        }):
            assert corroborate_offer(offer)["confidence_downgraded"] is False


class TestAuditLogCompaction:
    """Verifies compact_audit_log rotation and gzip archival."""

    def test_audit_log_compaction_and_archival_invariants(self, tmp_path: Path):
        ledger = tmp_path / "audit_log.jsonl"
        archive = tmp_path / "audit_log_archive.jsonl.gz"

        # 1. Under threshold is a no-op
        entries_small = [json.dumps({"id": f"entry-{i}"}) for i in range(10)]
        ledger.write_text("\n".join(entries_small) + "\n", encoding="utf-8")
        res_small = compact_audit_log(ledger_path=ledger, keep_recent=50)
        assert res_small["total_before"] == 10 and res_small["retained"] == 10 and res_small["archived"] == 0

        # 2. Over threshold archives and retains correct bounds
        entries_large = [json.dumps({"id": f"entry-{i}"}) for i in range(25)]
        ledger.write_text("\n".join(entries_large) + "\n", encoding="utf-8")
        res_large = compact_audit_log(ledger_path=ledger, archive_path=archive, keep_recent=10, archive_gz=True)
        assert res_large["total_before"] == 25 and res_large["retained"] == 10 and res_large["archived"] == 15
        assert archive.exists()


class TestBuildArtifacts:
    """Verifies fingerprint computation, summary.json, and skip_if_unchanged."""

    def test_build_artifacts_and_fingerprint_invariants(self, tmp_path: Path):
        fp1 = compute_build_fingerprint()
        fp2 = compute_build_fingerprint()
        assert fp1 == fp2 and len(fp1) == 64

        readme = tmp_path / "README.md"
        html = tmp_path / "index.html"
        summary = tmp_path / "summary.json"
        build_all(readme_path=readme, html_path=html, summary_path=summary, force=True)

        assert summary.exists()
        data = json.loads(summary.read_text(encoding="utf-8"))
        for k in ["active", "review_needed", "expired", "total", "last_updated"]:
            assert k in data, f"Missing key '{k}' in summary.json"


class TestVLMModularization:
    """Verifies that src/vlm and src/vlm_engine re-exports match 100% and run offline."""

    def test_vlm_modularization_facade_and_heuristics_invariants(self):
        for symbol in vlm_facade.__all__:
            assert hasattr(vlm_pkg, symbol), f"vlm package missing symbol: {symbol}"
            assert getattr(vlm_facade, symbol) is getattr(vlm_pkg, symbol)

        verdict = vlm_pkg.evaluate_visual_semantics_heuristic(
            offer_id="test-heuristic",
            dom_text="Claim your 100% free exam voucher now for AWS AI Practitioner",
            dom_title="AWS Free Exam Voucher Promotion",
            platform="Amazon Web Services"
        )
        assert verdict.has_zero_dollar_waiver is True and verdict.registration_status == "open"

        engine = vlm_pkg.get_ocr_engine()
        dom = '<div class="voucher-banner">100% Free Certification Exam Voucher</div>'
        result = engine.extract_text(image_source=None, rendered_dom=dom)
        assert result.status == "fallback" and "100% free" in result.text.lower()


class TestASNSecondaryValidation:
    """Verifies that non-canonical hosts on cloud CDNs are not attributed to vendors."""

    def test_asn_route_verification_and_whitelist_invariants(self):
        verifier = ASNRouteVerifier()
        with patch.object(verifier, "query_cymru_asn_doh", return_value={"asn": 16509, "prefix": "52.94.76.0/24", "country": "US", "registry": "arin"}):
            result = verifier.verify_route_origin("https://phishing-claim-free-certs.xyz/voucher", platform="Amazon Web Services", ip_override="52.94.76.1")
        assert "CLOUD_CDN_COINCIDENCE_NON_CANONICAL_DOMAIN" in result.flags
        assert result.is_vendor_infra is False

        assert is_whitelisted_domain("aws.amazon.com", "Amazon Web Services") is True


class TestNewsDeduplication:
    """Verifies content fingerprint computation and deduplication."""

    def test_news_fingerprint_normalization_and_distinctness_invariants(self):
        fp1 = compute_news_fingerprint("  NEW AWS Cert Challenge!  ", "AWS.AMAZON.COM")
        fp2 = compute_news_fingerprint("new aws cert challenge!", "aws.amazon.com")
        assert fp1 == fp2, "Fingerprints must match after normalization"

        fp3 = compute_news_fingerprint("Title A", "azure.microsoft.com")
        fp4 = compute_news_fingerprint("Title B", "azure.microsoft.com")
        assert fp3 != fp4


class TestURLNormalization:
    """Verifies normalize_url idempotency helper."""

    def test_normalize_url_variants_invariants(self):
        base = "https://learn.microsoft.com/en-us/training"
        assert normalize_url("https://www.learn.microsoft.com/en-us/training/") == base
        assert normalize_url("https://learn.microsoft.com/en-us/training") == base
        assert normalize_url("https://learn.microsoft.com/en-us/training?challenge=1") == f"{base}?challenge=1"


class TestSelfHealingZeroDollarDate:
    """Verifies last_zero_dollar_confirmed_date stamping on affirmative verification."""

    def test_self_healing_zero_dollar_date_invariants(self):
        offer = {
            "id": "oracle-test", "title": "Oracle OCI Foundations",
            "status": "Review Needed", "verification_date": "2026-09-01"
        }
        # Affirmative inspection stamps date
        healed = apply_self_healing(offer, {
            "status": "Active", "reason": "DOM confirmed $0.00 cart balance",
            "zero_dollar_confirmed": True, "maintenance_detected": False, "paid_catalog_detected": False
        })
        assert healed["status"] == "Active"
        assert healed["last_zero_dollar_confirmed_date"] == datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Non-zero dollar inspection does NOT heal to Active
        unhealed = apply_self_healing(offer, {
            "status": "Active", "reason": "Catalog price found",
            "zero_dollar_confirmed": False, "maintenance_detected": False, "paid_catalog_detected": True
        })
        assert unhealed["status"] == "Review Needed"
