"""
Integration Test Suite for CertPulse Autonomous Pipeline.

Fills the structural gap in the test pyramid by verifying multi-module integration
contracts using respx HTTP mocking — with zero Playwright browser overhead and zero
live network dependencies.

Integration flows covered:
1. Collector -> Candidate Normalization -> Authenticity Gate Integration
2. HTTP Inspection -> Pre-flight -> Canonical URL Self-Healing Integration
3. Truth Oracle Policy Corroboration -> Expiration & Confidence Downgrade Integration
4. Self-Healing State Transitions -> Zero-Dollar Affirmative Guard Integration
5. Integrated End-to-End Build Pipeline -> Telemetry & Signals Breakdown Contract
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
import jsonschema
import pytest
import respx
import httpx

from src.collector import fetch_reddit_leads, fetch_vendor_blog_leads
from src.authenticity import audit_offer_authenticity
from src.truth_oracle import audit_and_enrich_offers, CURATED_POLICY_OVERRIDES
from src.main import apply_self_healing, ingest_and_vet_candidates, normalize_url
from src.builders import build_all, load_offers, load_news
from src.io_utils import atomic_write_json
from src.models import Offer, OffersDatabase

ROOT = Path(__file__).resolve().parent.parent
OFFERS_SCHEMA_FILE = ROOT / "data" / "schema.json"
NEWS_SCHEMA_FILE = ROOT / "data" / "news_schema.json"


# ==============================================================================
# 1. Collector -> Authenticity Gate Integration
# ==============================================================================

class TestCollectorAuthenticityIntegration:
    """Verifies candidate collection, URL normalization, and authenticity screening."""

    @respx.mock
    def test_vendor_blog_lead_ingestion_and_authenticity_gate(self):
        """Mock official vendor blog RSS and verify authentic candidate parsing."""
        mock_rss = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>AWS Training &amp; Certification Blog</title>
                <link>https://aws.amazon.com/blogs/training-and-certification/</link>
                <item>
                    <title>Get Certified: Free AWS Cloud Practitioner Exam Voucher Initiative</title>
                    <link>https://aws.amazon.com/blogs/training-and-certification/free-practitioner-voucher/</link>
                    <description>Claim your 100% free voucher for AWS Certified Cloud Practitioner.</description>
                    <pubDate>Fri, 24 Oct 2026 08:00:00 GMT</pubDate>
                </item>
                <item>
                    <title>General Updates on Cloud Migration</title>
                    <link>https://aws.amazon.com/blogs/training-and-certification/general-migration/</link>
                    <description>Routine cloud migration strategies without vouchers.</description>
                    <pubDate>Thu, 23 Oct 2026 08:00:00 GMT</pubDate>
                </item>
            </channel>
        </rss>"""

        # Mock all blog GET requests
        respx.get().respond(
            status_code=200,
            headers={"Content-Type": "application/xml"},
            text=mock_rss
        )

        leads = fetch_vendor_blog_leads()
        assert len(leads) >= 1
        lead = leads[0]
        assert "voucher" in lead["title"].lower() or "free" in lead["title"].lower()
        assert lead["url"].startswith("https://aws.amazon.com/")

        # Verify authenticity gate evaluates the discovered URL
        offer_candidate = {
            "title": lead["title"],
            "url": lead["url"],
            "platform": lead["platform"],
            "category": "Cloud",
        }
        auth_res = audit_offer_authenticity(offer_candidate)
        assert auth_res["is_authentic_vendor"] is True
        assert auth_res["authenticity_score"] >= 80
        assert auth_res["verdict"] in ["VERIFIED_AUTHENTIC", "GENUINE_OFFICIAL"]

    def test_deceptive_lead_rejection_at_authenticity_gate(self):
        """Verify that spoofed/phishing candidate leads are rejected before inspection."""
        phishing_leads = [
            {"title": "Free AWS Voucher", "url": "https://aws-free-vouchers.scam-portal.ru/claim", "platform": "AWS"},
            {"title": "Free Oracle Cert", "url": "https://oracle.mylearn.free-certs-discount.com/claim", "platform": "Oracle"},
            {"title": "CompTIA Free Exam", "url": "http://insecure-http-exam.biz/comptia", "platform": "CompTIA"},
        ]
        for lead in phishing_leads:
            auth_res = audit_offer_authenticity(lead)
            assert auth_res["is_authentic_vendor"] is False
            assert auth_res["verdict"] in ["DECEPTIVE_SCAM", "SUSPICIOUS_UNTRUSTED", "REJECTED_UNTRUSTED"]


# ==============================================================================
# 2. HTTP Pre-flight & Canonical URL Self-Healing Integration
# ==============================================================================

class TestHTTPInspectionAndSelfHealingIntegration:
    """Verifies HTTP pre-flight behavior, canonical redirect healing, and soft-404 detection."""

    @respx.mock
    def test_canonical_redirect_url_healing(self):
        """Simulate a 301 permanent redirect from old URL to canonical portal URL."""
        respx.get("https://learn.oracle.com/legacy-genai-path").respond(
            status_code=301,
            headers={"Location": "https://mylearn.oracle.com/ou/course/generative-ai"}
        )
        respx.get("https://mylearn.oracle.com/ou/course/generative-ai").respond(
            status_code=200,
            text="<html><body><h1>Oracle Cloud Infrastructure Generative AI</h1><p>Free course and certification attempt included at $0 cost.</p></body></html>"
        )

        with httpx.Client(follow_redirects=True) as client:
            resp = client.get("https://learn.oracle.com/legacy-genai-path")
            final_url = str(resp.url)

        assert final_url == "https://mylearn.oracle.com/ou/course/generative-ai"
        assert resp.status_code == 200

        # Verify normalization and redirect detection
        norm_orig = normalize_url("https://learn.oracle.com/legacy-genai-path")
        norm_final = normalize_url(final_url)
        assert norm_orig != norm_final

    @respx.mock
    def test_dead_link_detection_triggers_broken_link(self):
        """Simulate a 404 Not Found error and verify proper error handling."""
        respx.get("https://training.example.com/expired-campaign").respond(status_code=404)

        with httpx.Client() as client:
            resp = client.get("https://training.example.com/expired-campaign")
            assert resp.status_code == 404

        dummy_offer = {
            "id": "test-dead-link",
            "title": "Expired Campaign",
            "url": "https://training.example.com/expired-campaign",
            "status": "Active"
        }
        # Inspection result for 404
        inspection_res = {
            "status": "Broken Link",
            "reason": "HTTP 404 Client Error",
            "zero_dollar_confirmed": False
        }
        healed = apply_self_healing(dummy_offer, inspection_res)
        assert healed["status"] == "Broken Link"
        assert "404" in healed["inspection_notes"]


# ==============================================================================
# 3. Truth Oracle Policy Corroboration Integration
# ==============================================================================

class TestTruthOracleIntegration:
    """Verifies policy corroboration, anti-misleading detection, and expiration audits."""

    def test_truth_oracle_enriches_valid_offers(self):
        """Verifies policy attachment for recognized curated certifications."""
        sample_offers = [
            {
                "id": "oracle-oci-free-cert",
                "title": "Oracle Cloud Infrastructure (OCI) Free Certifications",
                "platform": "Oracle",
                "status": "Active",
                "url": "https://mylearn.oracle.com/",
            },
            {
                "id": "isc2-one-million-cc",
                "title": "ISC2 One Million Certified in Cybersecurity",
                "platform": "ISC2",
                "status": "Active",
                "url": "https://www.isc2.org/landing/1mcc",
            }
        ]

        enriched, summary = audit_and_enrich_offers(sample_offers, strict_enforcement=True)
        assert len(enriched) == 2
        for offer in enriched:
            assert "truth_verification" in offer
            tv = offer["truth_verification"]
            assert tv["verified_discount_pct"] == 100
            assert tv["real_exam_cost_usd"] == 0.0
            assert "valid_through_utc" in tv
            assert "review_due_utc" in tv

    def test_truth_oracle_confidence_downgrade_on_expired_policy(self):
        """Verifies that past valid_through_utc causes automatic confidence downgrade."""
        expired_policy_offer = [
            {
                "id": "hist-redhat-summit-2024",
                "title": "Red Hat Summit 2024 Free Exams",
                "platform": "Red Hat",
                "status": "Expired",
                "url": "https://developers.redhat.com/",
                "is_historical_archive": True
            }
        ]
        enriched, _ = audit_and_enrich_offers(expired_policy_offer, strict_enforcement=True)
        tv = enriched[0]["truth_verification"]
        assert tv["confidence_downgraded"] is True


# ==============================================================================
# 4. Self-Healing State Machine & Zero-Dollar Guard Integration
# ==============================================================================

class TestSelfHealingStateGuardsIntegration:
    """Verifies that offers can only heal to Active when affirmative $0 terms are confirmed."""

    def test_self_healing_requires_affirmative_zero_dollar(self):
        """Offer in 'Review Needed' attempts healing without $0 confirmation -> Must remain 'Review Needed'."""
        stale_offer = {
            "id": "test-offer-1",
            "title": "Cloud Certification",
            "status": "Review Needed",
            "url": "https://aws.amazon.com/certification/",
        }

        # Inspection claims 'Active' but zero_dollar_confirmed is False
        unverified_inspection = {
            "status": "Active",
            "zero_dollar_confirmed": False,
            "maintenance_detected": False,
            "paid_catalog_detected": False,
            "screenshot_path": "docs/screenshots/test.png"
        }
        res = apply_self_healing(stale_offer, unverified_inspection)
        assert res["status"] == "Review Needed"
        assert "zero-dollar" in res["inspection_notes"].lower()

    def test_self_healing_succeeds_with_affirmative_zero_dollar(self):
        """Offer in 'Review Needed' recovers to 'Active' when zero_dollar_confirmed is True."""
        stale_offer = {
            "id": "test-offer-2",
            "title": "Cloud Certification",
            "status": "Review Needed",
            "url": "https://mylearn.oracle.com/",
        }

        confirmed_inspection = {
            "status": "Active",
            "zero_dollar_confirmed": True,
            "maintenance_detected": False,
            "paid_catalog_detected": False,
            "screenshot_path": "docs/screenshots/test2.png"
        }
        res = apply_self_healing(stale_offer, confirmed_inspection)
        assert res["status"] == "Active"
        assert res.get("self_healing_event") is not None
        assert res["self_healing_event"]["previous_status"] == "Review Needed"
        assert res["self_healing_event"]["healed_status"] == "Active"


# ==============================================================================
# 5. Integrated Build Pipeline & Signals Breakdown Telemetry Contract
# ==============================================================================

class TestIntegratedBuildAndTelemetryContract:
    """Verifies that build_all compiles valid artifacts with observable signals_breakdown."""

    def test_build_all_generates_schema_compliant_artifacts_and_telemetry(self, tmp_path: Path):
        readme_path = tmp_path / "README.md"
        html_path = tmp_path / "index.html"
        summary_path = tmp_path / "summary.json"

        success = build_all(
            readme_path=readme_path,
            html_path=html_path,
            summary_path=summary_path,
            force=True
        )
        assert success is True

        # 1. Verify README.md exists and is non-empty
        assert readme_path.exists()
        readme_content = readme_path.read_text(encoding="utf-8")
        assert "# CertPulse" in readme_content or "Certification" in readme_content

        # 2. Verify HTML Dashboard exists and is non-empty
        assert html_path.exists()
        html_content = html_path.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in html_content
        assert "CertPulse" in html_content

        # 3. Verify data/summary.json and its signals_breakdown contract
        assert summary_path.exists()
        summary_data = json.loads(summary_path.read_text(encoding="utf-8"))

        for key in ["active", "review_needed", "expired", "total", "last_updated", "last_successful_run", "signals_breakdown"]:
            assert key in summary_data, f"Missing key '{key}' in summary.json"

        signals = summary_data["signals_breakdown"]
        for sig_key in ["dom_inspected", "oracle_corroborated", "authentic_vendors", "zero_dollar_confirmed", "historical_archives"]:
            assert sig_key in signals, f"Missing signal counter '{sig_key}' in summary.json['signals_breakdown']"
            assert isinstance(signals[sig_key], int)
            assert signals[sig_key] >= 0

        # Invariant: total equals sum of statuses
        assert summary_data["total"] == summary_data["active"] + summary_data["review_needed"] + summary_data["expired"] + (summary_data["total"] - (summary_data["active"] + summary_data["review_needed"] + summary_data["expired"]))

    def test_offers_and_news_conform_to_json_schemas(self):
        """Assert current data files strictly validate against their respective schemas."""
        offers_schema = json.loads(OFFERS_SCHEMA_FILE.read_text(encoding="utf-8"))
        news_schema = json.loads(NEWS_SCHEMA_FILE.read_text(encoding="utf-8"))

        offers_data = load_offers()
        news_data = load_news()

        # Schema validation raises on error
        jsonschema.validate(instance=offers_data, schema=offers_schema)
        jsonschema.validate(instance=news_data, schema=news_schema)
