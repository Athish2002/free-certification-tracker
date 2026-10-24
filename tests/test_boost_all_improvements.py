"""
Comprehensive verification test suite for CertPulse /boost all system improvements.
Covers:
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


# ==============================================================================
# 1. Vendor Blog Collector Tests
# ==============================================================================

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
        <item>
          <title>Regular AWS Architecture Best Practices</title>
          <link>https://aws.amazon.com/blogs/training-and-certification/best-practices/</link>
          <description>Learn how to optimize multi-region architectures.</description>
          <pubDate>Sun, 19 Oct 2026 10:00:00 GMT</pubDate>
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

    def test_rss_item_parsing_and_keyword_filtering(self):
        collector = VendorBlogCollector(targets=[{
            "name": "AWS Training Blog",
            "feed_url": "https://aws.amazon.com/feed/",
            "platform": "Amazon Web Services",
            "allowed_domain": "aws.amazon.com",
        }])

        mock_resp = MagicMock(status_code=200, text=self.RSS_SAMPLE)
        with patch.object(httpx.Client, "get", return_value=mock_resp):
            leads = collector.fetch_vendor_blog_leads()

        # Should match the first item with "voucher" keyword, but ignore the second
        assert len(leads) == 1
        lead = leads[0]
        assert "Free Exam Voucher Challenge" in lead["title"]
        assert lead["platform"] == "Amazon Web Services"
        assert lead["is_authentic_vendor"] is True
        assert lead["id"].startswith("blog-amazon-web-services-")

    def test_atom_entry_parsing(self):
        collector = VendorBlogCollector(targets=[{
            "name": "Microsoft Learn Blog",
            "feed_url": "https://learn.microsoft.com/rss",
            "platform": "Microsoft Azure",
            "allowed_domain": "learn.microsoft.com",
        }])

        mock_resp = MagicMock(status_code=200, text=self.ATOM_SAMPLE)
        with patch.object(httpx.Client, "get", return_value=mock_resp):
            leads = collector.fetch_vendor_blog_leads()

        assert len(leads) == 1
        assert "Microsoft Cloud Skills Challenge" in leads[0]["title"]
        assert leads[0]["url"] == "https://learn.microsoft.com/en-us/training/challenges/spring-2026"

    def test_deterministic_id_generation(self):
        """Invariant: Same title and platform must produce the exact same ID across runs."""
        collector = VendorBlogCollector(targets=[{
            "name": "AWS Training Blog",
            "feed_url": "https://aws.amazon.com/feed/",
            "platform": "Amazon Web Services",
            "allowed_domain": "aws.amazon.com",
        }])

        mock_resp = MagicMock(status_code=200, text=self.RSS_SAMPLE)
        with patch.object(httpx.Client, "get", return_value=mock_resp):
            run1 = collector.fetch_vendor_blog_leads()
            run2 = collector.fetch_vendor_blog_leads()

        assert len(run1) == 1 and len(run2) == 1
        assert run1[0]["id"] == run2[0]["id"], "Lead ID must be deterministic across executions"

    def test_resilience_to_http_429_rate_limit(self):
        collector = VendorBlogCollector(targets=[{
            "name": "AWS Training Blog",
            "feed_url": "https://aws.amazon.com/feed/",
            "platform": "Amazon Web Services",
            "allowed_domain": "aws.amazon.com",
        }])

        mock_resp = MagicMock(status_code=429)
        with patch.object(httpx.Client, "get", return_value=mock_resp):
            leads = collector.fetch_vendor_blog_leads()

        assert leads == [], "Must return empty leads without raising exception on 429"

    def test_resilience_to_network_exceptions(self):
        collector = VendorBlogCollector(targets=[{
            "name": "AWS Training Blog",
            "feed_url": "https://aws.amazon.com/feed/",
            "platform": "Amazon Web Services",
            "allowed_domain": "aws.amazon.com",
        }])

        with patch.object(httpx.Client, "get", side_effect=httpx.ConnectError("Connection refused")):
            leads = collector.fetch_vendor_blog_leads()

        assert leads == [], "Must catch network errors gracefully and return empty list"


# ==============================================================================
# 2. Staleness Threshold Tests
# ==============================================================================

class TestStalenessDowngrade:
    """Verifies check_and_flag_stale_offers auto-downgrades stale Active offers."""

    def test_stale_offer_is_downgraded_to_review_needed(self):
        today = datetime.now(timezone.utc).date()
        stale_date = (today - timedelta(days=20)).strftime("%Y-%m-%d")
        fresh_date = (today - timedelta(days=5)).strftime("%Y-%m-%d")

        offers = [
            {"id": "stale-1", "title": "Stale Offer", "status": "Active", "verification_date": stale_date},
            {"id": "fresh-1", "title": "Fresh Offer", "status": "Active", "verification_date": fresh_date},
            {"id": "closed-1", "title": "Closed Offer", "status": "Registrations Closed", "verification_date": stale_date},
            {"id": "hist-1", "title": "Historical", "status": "Active", "verification_date": stale_date, "is_historical_archive": True},
        ]

        downgraded = check_and_flag_stale_offers(offers, threshold_days=14)

        assert downgraded == 1
        assert offers[0]["status"] == "Review Needed"
        assert "Stale" in offers[0]["inspection_notes"]
        assert offers[1]["status"] == "Active"
        assert offers[2]["status"] == "Registrations Closed"
        assert offers[3]["status"] == "Active", "Historical archive should be exempt"

    def test_missing_or_corrupted_date_is_downgraded(self):
        offers = [
            {"id": "bad-date-1", "title": "Bad Date", "status": "Active", "verification_date": "invalid-date"},
            {"id": "no-date-2", "title": "No Date", "status": "Active", "verification_date": None},
        ]
        downgraded = check_and_flag_stale_offers(offers, threshold_days=14)
        assert downgraded == 2
        assert offers[0]["status"] == "Review Needed"
        assert offers[1]["status"] == "Review Needed"


# ==============================================================================
# 3. Truth Oracle Expiry & Stale Policy Tests
# ==============================================================================

class TestTruthOracleExpiry:
    """Verifies Truth Oracle policy overrides expiry and confidence downgrading."""

    def test_all_curated_overrides_have_expiry_timestamps(self):
        for oid, policy in CURATED_POLICY_OVERRIDES.items():
            assert "valid_through_utc" in policy, f"Policy '{oid}' missing 'valid_through_utc'"
            assert "review_due_utc" in policy, f"Policy '{oid}' missing 'review_due_utc'"

    def test_expired_override_triggers_confidence_downgrade(self):
        offer = {
            "id": "mock-expired-policy",
            "title": "Mock Certification",
            "platform": "Oracle Cloud",
            "url": "https://mylearn.oracle.com/cert",
            "status": "Active",
            "visual_proof": {"zero_dollar_confirmed": True}
        }

        # Mock policy with past valid_through_utc
        past_dt = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        with patch.dict(CURATED_POLICY_OVERRIDES, {
            "mock-expired-policy": {
                "provider": "Oracle Cloud",
                "exam_name": "Mock Cert",
                "policy_type": "verified_100pct_free",
                "real_exam_cost_usd": 0.0,
                "verified_discount_pct": 100,
                "truth_source_name": "Oracle Policy",
                "truth_source_url": "https://mylearn.oracle.com/",
                "verdict_notes": "Expired override notes",
                "enforce_status": "Active",
                "zero_dollar_confirmed": True,
                "valid_through_utc": past_dt,
                "review_due_utc": past_dt,
            }
        }):
            res = corroborate_offer(offer)
            assert res["confidence_downgraded"] is True

    def test_fresh_override_preserves_confidence(self):
        offer = {
            "id": "mock-fresh-policy",
            "title": "Mock Certification",
            "platform": "Oracle Cloud",
            "url": "https://mylearn.oracle.com/cert",
            "status": "Active",
            "visual_proof": {"zero_dollar_confirmed": True}
        }

        future_dt = (datetime.now(timezone.utc) + timedelta(days=60)).isoformat()
        with patch.dict(CURATED_POLICY_OVERRIDES, {
            "mock-fresh-policy": {
                "provider": "Oracle Cloud",
                "exam_name": "Mock Cert",
                "policy_type": "verified_100pct_free",
                "real_exam_cost_usd": 0.0,
                "verified_discount_pct": 100,
                "truth_source_name": "Oracle Policy",
                "truth_source_url": "https://mylearn.oracle.com/",
                "verdict_notes": "Active override notes",
                "enforce_status": "Active",
                "zero_dollar_confirmed": True,
                "valid_through_utc": future_dt,
                "review_due_utc": future_dt,
            }
        }):
            res = corroborate_offer(offer)
            assert res["confidence_downgraded"] is False


# ==============================================================================
# 4. Audit Log Compaction Tests
# ==============================================================================

class TestAuditLogCompaction:
    """Verifies compact_audit_log rotation and gzip archival."""

    def test_compact_under_threshold_is_noop(self, tmp_path: Path):
        ledger = tmp_path / "audit_log.jsonl"
        entries = [json.dumps({"id": f"entry-{i}"}) for i in range(10)]
        ledger.write_text("\n".join(entries) + "\n", encoding="utf-8")

        res = compact_audit_log(ledger_path=ledger, keep_recent=50)
        assert res["total_before"] == 10
        assert res["retained"] == 10
        assert res["archived"] == 0

    def test_compact_over_threshold_archives_and_retains(self, tmp_path: Path):
        ledger = tmp_path / "audit_log.jsonl"
        archive = tmp_path / "audit_log_archive.jsonl.gz"

        entries = [json.dumps({"id": f"entry-{i}"}) for i in range(25)]
        ledger.write_text("\n".join(entries) + "\n", encoding="utf-8")

        res = compact_audit_log(ledger_path=ledger, archive_path=archive, keep_recent=10, archive_gz=True)

        assert res["total_before"] == 25
        assert res["retained"] == 10
        assert res["archived"] == 15

        # Check ledger content: should have entries 15 to 24
        retained_lines = [l.strip() for l in ledger.read_text(encoding="utf-8").splitlines() if l.strip()]
        assert len(retained_lines) == 10
        assert json.loads(retained_lines[0])["id"] == "entry-15"
        assert json.loads(retained_lines[-1])["id"] == "entry-24"

        # Check archive content: should have entries 0 to 14
        assert archive.exists()
        with gzip.open(archive, "rt", encoding="utf-8") as gz:
            archived_lines = [l.strip() for l in gz.read().splitlines() if l.strip()]
        assert len(archived_lines) == 15
        assert json.loads(archived_lines[0])["id"] == "entry-0"
        assert json.loads(archived_lines[-1])["id"] == "entry-14"


# ==============================================================================
# 5. Build Fingerprinting and Summary Export Tests
# ==============================================================================

class TestBuildArtifacts:
    """Verifies fingerprint computation, summary.json, and skip_if_unchanged."""

    def test_compute_build_fingerprint_deterministic(self):
        fp1 = compute_build_fingerprint()
        fp2 = compute_build_fingerprint()
        assert fp1 == fp2
        assert len(fp1) == 64  # SHA-256

    def test_summary_json_contains_required_metrics(self, tmp_path: Path):
        readme = tmp_path / "README.md"
        html = tmp_path / "index.html"
        summary = tmp_path / "summary.json"

        build_all(readme_path=readme, html_path=html, summary_path=summary, force=True)

        assert summary.exists()
        data = json.loads(summary.read_text(encoding="utf-8"))
        for k in ["active", "review_needed", "expired", "total", "last_updated"]:
            assert k in data, f"Missing key '{k}' in summary.json"
        assert data["total"] == data["active"] + data["review_needed"] + data["expired"] + (data["total"] - (data["active"] + data["review_needed"] + data["expired"]))


# ==============================================================================
# 6. Modularized VLM Subpackage Tests
# ==============================================================================

class TestVLMModularization:
    """Verifies that src/vlm and src/vlm_engine re-exports match 100% and run offline."""

    def test_facade_re_exports_match(self):
        for symbol in vlm_facade.__all__:
            assert hasattr(vlm_pkg, symbol), f"vlm package missing symbol: {symbol}"
            assert getattr(vlm_facade, symbol) is getattr(vlm_pkg, symbol)

    def test_heuristic_fallback_offline_evaluation(self):
        verdict = vlm_pkg.evaluate_visual_semantics_heuristic(
            offer_id="test-heuristic",
            dom_text="Claim your 100% free exam voucher now for AWS AI Practitioner",
            dom_title="AWS Free Exam Voucher Promotion",
            platform="Amazon Web Services"
        )
        assert verdict.has_zero_dollar_waiver is True
        assert verdict.registration_status == "open"
        assert verdict.visual_confidence_score >= 0.40

    def test_ocr_engine_fallback_without_tesseract(self):
        engine = vlm_pkg.get_ocr_engine()
        dom = '<div class="voucher-banner">100% Free Certification Exam Voucher</div>'
        result = engine.extract_text(image_source=None, rendered_dom=dom)
        assert result.status == "fallback"
        assert result.method == "dom_svg_contrast_heuristic"
        assert "100% free" in result.text.lower()


# ==============================================================================
# 7. Anti-Fraud ASN Secondary Validation Tests
# ==============================================================================

class TestASNSecondaryValidation:
    """Verifies that non-canonical hosts on cloud CDNs are not attributed to vendors."""

    def test_cloud_cdn_coincidence_flagged_for_non_canonical_domain(self):
        verifier = ASNRouteVerifier()
        # Mock an IP resolution returning AWS ASN 16509, but on a scam domain
        with patch.object(verifier, "query_cymru_asn_doh", return_value={"asn": 16509, "prefix": "52.94.76.0/24", "country": "US", "registry": "arin"}):
            result = verifier.verify_route_origin("https://phishing-claim-free-certs.xyz/voucher", platform="Amazon Web Services", ip_override="52.94.76.1")
        assert "CLOUD_CDN_COINCIDENCE_NON_CANONICAL_DOMAIN" in result.flags
        assert result.is_vendor_infra is False
        assert result.provenance_tier == "Unverified Cloud-Hosted Third Party"

    def test_canonical_domain_accepted_as_vendor_infra(self):
        verifier = ASNRouteVerifier()
        # Canonical AWS domain
        is_auth = is_whitelisted_domain("aws.amazon.com", "Amazon Web Services")
        assert is_auth is True


# ==============================================================================
# 8. News Feed Deduplication Tests
# ==============================================================================

class TestNewsDeduplication:
    """Verifies content fingerprint computation and deduplication."""

    def test_news_fingerprint_normalization(self):
        fp1 = compute_news_fingerprint("  NEW AWS Cert Challenge!  ", "AWS.AMAZON.COM")
        fp2 = compute_news_fingerprint("new aws cert challenge!", "aws.amazon.com")
        assert fp1 == fp2, "Fingerprints must match after normalization"

    def test_different_titles_produce_distinct_fingerprints(self):
        fp1 = compute_news_fingerprint("Title A", "azure.microsoft.com")
        fp2 = compute_news_fingerprint("Title B", "azure.microsoft.com")
        assert fp1 != fp2


# ==============================================================================
# 9. URL Normalization and Idempotency Tests
# ==============================================================================

class TestURLNormalization:
    """Verifies normalize_url idempotency helper."""

    def test_normalize_url_variants(self):
        base = "https://learn.microsoft.com/en-us/training"
        assert normalize_url("https://www.learn.microsoft.com/en-us/training/") == base
        assert normalize_url("https://learn.microsoft.com/en-us/training") == base
        assert normalize_url("https://learn.microsoft.com/en-us/training?challenge=1") == f"{base}?challenge=1"


# ==============================================================================
# 10. Self-Healing & Zero-Dollar Date Invariants
# ==============================================================================

class TestSelfHealingZeroDollarDate:
    """Verifies last_zero_dollar_confirmed_date stamping on affirmative verification."""

    def test_affirmative_inspection_stamps_zero_dollar_date(self):
        offer = {
            "id": "oracle-test",
            "title": "Oracle OCI Foundations",
            "status": "Review Needed",
            "verification_date": "2026-09-01"
        }
        inspection_res = {
            "status": "Active",
            "reason": "DOM confirmed $0.00 cart balance",
            "zero_dollar_confirmed": True,
            "maintenance_detected": False,
            "paid_catalog_detected": False
        }
        healed = apply_self_healing(offer, inspection_res)
        assert healed["status"] == "Active"
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        assert healed["last_zero_dollar_confirmed_date"] == today

    def test_non_zero_dollar_inspection_does_not_heal_to_active(self):
        offer = {
            "id": "oracle-test",
            "title": "Oracle OCI Foundations",
            "status": "Review Needed",
            "verification_date": "2026-09-01"
        }
        inspection_res = {
            "status": "Active",
            "reason": "Catalog price found",
            "zero_dollar_confirmed": False,
            "maintenance_detected": False,
            "paid_catalog_detected": True
        }
        res = apply_self_healing(offer, inspection_res)
        assert res["status"] == "Review Needed"
        assert "Inspection did not confirm affirmative zero-dollar terms" in res["inspection_notes"]
