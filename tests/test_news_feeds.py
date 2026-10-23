"""
Unit and Integration Tests for Dynamic Truth Oracle Policy Derivation
and Multi-Vendor News Feeds Expansion in CertPulse.
"""

import json
import re
from pathlib import Path
from typing import Dict, Any
from unittest.mock import patch, MagicMock

import jsonschema
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
from src.news_collector import (
    VERIFIED_FEEDS,
    is_clean_headline,
    parse_feed_date,
    fetch_feed_entries,
    save_news_feed,
    update_news_feed,
)
from src.io_utils import validate_payload
from tests.test_invariants import APPROVED_NEWS_DOMAINS

ROOT = Path(__file__).resolve().parent.parent
OFFERS_FILE = ROOT / "data" / "offers.json"
NEWS_FILE = ROOT / "data" / "news.json"
NEWS_SCHEMA = ROOT / "data" / "news_schema.json"


@pytest.fixture(scope="module")
def canonical_offers() -> list[Dict[str, Any]]:
    assert OFFERS_FILE.exists(), f"Missing canonical offers file: {OFFERS_FILE}"
    with open(OFFERS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("offers", [])


class TestDynamicTruthPolicyDerivation:
    """Verifies dynamic truth policy derivation across all canonical offers in data/offers.json."""

    def test_dynamic_registry_loads_all_39_offers(self, canonical_offers):
        """Dynamic registry builder must load and index every offer in data/offers.json."""
        assert len(canonical_offers) == 39, f"Expected 39 canonical offers, found {len(canonical_offers)}"
        registry = build_dynamic_policy_registry(OFFERS_FILE)
        assert len(registry) >= 39
        for offer in canonical_offers:
            oid = offer["id"]
            assert oid in registry, f"Offer '{oid}' was not dynamically registered in policy registry"

    def test_derive_truth_policy_structure_and_authority_rules(self, canonical_offers):
        """derive_truth_policy must extract official URL, terms URL, domain, authority rules, and expected patterns."""
        for offer in canonical_offers:
            policy = derive_truth_policy(offer)
            oid = offer["id"]

            # Required top-level attributes
            for req_key in [
                "provider", "exam_name", "policy_type", "real_exam_cost_usd",
                "verified_discount_pct", "truth_source_name", "truth_source_url",
                "verdict_notes", "category", "official_url", "terms_url", "domain",
                "authority_rules", "expected_verification_patterns"
            ]:
                assert req_key in policy, f"Offer '{oid}' derived policy missing '{req_key}'"

            # Authority rules assertions
            auth_rules = policy["authority_rules"]
            assert isinstance(auth_rules, dict), f"Offer '{oid}' authority_rules must be a dict"
            assert "domain" in auth_rules
            assert auth_rules["requires_https"] is True
            assert isinstance(auth_rules["allowed_domains"], list)

            # Expected verification patterns assertions
            exp_patterns = policy["expected_verification_patterns"]
            assert isinstance(exp_patterns, dict), f"Offer '{oid}' expected_verification_patterns must be a dict"
            assert "status" in exp_patterns
            assert "zero_dollar_expected" in exp_patterns
            assert "proctoring_type" in exp_patterns

            # Invariant assertions
            assert policy["truth_source_url"].startswith("https://"), f"Offer '{oid}' truth_source_url not HTTPS: {policy['truth_source_url']}"
            assert "." in policy["truth_source_url"]
            assert len(policy["truth_source_name"].strip()) >= 5
            assert len(policy["verdict_notes"].strip()) >= 15
            assert policy["real_exam_cost_usd"] >= 0.0
            assert 0 <= policy["verified_discount_pct"] <= 100

    def test_get_truth_policy_lookup_and_dynamic_fallback(self):
        """get_truth_policy must retrieve existing policies and dynamically derive for new offers."""
        # Known offer in registry
        known = get_truth_policy("oracle-oci-free-cert")
        assert known["policy_type"] == POLICY_VERIFIED_100PCT_FREE
        assert known["real_exam_cost_usd"] == 0.0

        # Unseen new offer dynamically passed
        unseen_offer = {
            "id": "new-test-cloud-provider-exam",
            "title": "New Test Cloud Architecture Certification",
            "company": "TestCloud",
            "category": "Cloud Computing",
            "status": "Active",
            "credential_tier": "proctored_exam",
            "url": "https://testcloud.example.com/cert",
            "value_usd": 150.0,
            "cart_balance_verified": "$0.00 (100% Free / Waiver Confirmed)"
        }
        derived = get_truth_policy("new-test-cloud-provider-exam", unseen_offer)
        assert derived["provider"] == "TestCloud"
        assert derived["policy_type"] == POLICY_VERIFIED_100PCT_FREE
        assert derived["domain"] == "testcloud.example.com"
        assert "new-test-cloud-provider-exam" in TRUTH_POLICY_REGISTRY

        # Unknown offer without metadata fallback
        fallback = get_truth_policy("completely-unknown-offer-no-data")
        assert fallback["policy_type"] == POLICY_FREE_UNPROCTORED_BADGE
        assert fallback["truth_source_url"].startswith("https://")

    def test_module_load_initializes_truth_policy_registry(self, canonical_offers):
        """TRUTH_POLICY_REGISTRY must be populated upon module load for backward compatibility."""
        assert isinstance(TRUTH_POLICY_REGISTRY, dict)
        assert len(TRUTH_POLICY_REGISTRY) >= 39
        for offer in canonical_offers:
            assert offer["id"] in TRUTH_POLICY_REGISTRY


class TestNewsFeedExpansionAndConfigurations:
    """Verifies that news feed aggregation covers all required vendors with strict security controls."""

    def test_verified_feeds_contain_all_required_vendors(self):
        """VERIFIED_FEEDS must include AWS, Google Cloud, GitHub, Cisco, Microsoft, HashiCorp, Databricks, Snowflake, Red Hat."""
        assert len(VERIFIED_FEEDS) == 9, f"Expected 9 verified feeds, found {len(VERIFIED_FEEDS)}"

        companies = {f["company"] for f in VERIFIED_FEEDS}
        required_companies = {
            "Amazon Web Services",
            "Google Cloud",
            "GitHub",
            "Cisco",
            "Microsoft",
            "HashiCorp",
            "Databricks",
            "Snowflake",
            "Red Hat"
        }
        missing = required_companies - companies
        assert not missing, f"Missing required feed vendors: {missing}"

    def test_feed_configurations_have_required_fields_and_https_urls(self):
        """Every feed entry must have complete metadata and secure HTTPS feed endpoint."""
        for feed in VERIFIED_FEEDS:
            company = feed.get("company", "UNKNOWN")
            for req_key in ["company", "source", "category", "feed_url", "allowed_domain", "impact_badge"]:
                assert req_key in feed, f"Feed for '{company}' missing required key '{req_key}'"
                assert str(feed[req_key]).strip() != "", f"Feed for '{company}' has empty '{req_key}'"

            assert feed["feed_url"].startswith("https://"), f"Feed for '{company}' must have HTTPS URL: {feed['feed_url']}"
            assert "." in feed["allowed_domain"], f"Feed for '{company}' has invalid allowed_domain: {feed['allowed_domain']}"

    def test_feed_allowed_domains_in_approved_news_domains(self):
        """All feed domains must be recognized by tests/test_invariants.py:APPROVED_NEWS_DOMAINS."""
        for feed in VERIFIED_FEEDS:
            domain = feed.get("source_domain") or feed["allowed_domain"]
            assert domain in APPROVED_NEWS_DOMAINS, (
                f"Feed domain '{domain}' for {feed['company']} not present in APPROVED_NEWS_DOMAINS"
            )

    def test_anti_clickbait_headline_filter(self):
        """is_clean_headline must allow objective engineering titles and block sensational clickbait buzzwords."""
        # Clean engineering headlines
        assert is_clean_headline("Kubernetes 1.30: Structured Authorization Configuration GA")
        assert is_clean_headline("Amazon Aurora PostgreSQL Serverless v2 Performance Benchmarks")
        assert is_clean_headline("Microsoft Azure announces next-generation Confidential GPU VMs")
        assert is_clean_headline("HashiCorp Terraform 1.9 GA: Ephemeral Values and Cross-Object Validation")
        assert is_clean_headline("Snowflake Data Clean Rooms: Architecture and Privacy-Preserving Analytics")

        # Prohibited clickbait buzzwords
        assert not is_clean_headline("Shocking new secret trick to pass certification exams")
        assert not is_clean_headline("This insane vulnerability will destroy your cloud infrastructure")
        assert not is_clean_headline("You won't believe what Google Cloud just announced")
        assert not is_clean_headline("Mind blowing AI feature exposed in latest leak")
        assert not is_clean_headline("Unbelievable DevOps game changer gone viral")


class TestFeedIngestionAndDateSynchronization:
    """Verifies that RSS/Atom parsing normalizes dates to ISO-8601 YYYY-MM-DD and writes both date keys."""

    def test_parse_feed_date_formats(self):
        """parse_feed_date must handle ISO dates, RFC-822 dates, and Atom timestamp formats."""
        # Standard ISO-8601 YYYY-MM-DD
        assert parse_feed_date("2024-10-15") == "2024-10-15"

        # RFC-822 / RFC-2822 RSS formats
        assert parse_feed_date("Tue, 15 Oct 2024 14:30:00 GMT") == "2024-10-15"
        assert parse_feed_date("15 Oct 2024 09:00:00 +0000") == "2024-10-15"

        # ISO-8601 with time and timezone
        assert parse_feed_date("2024-10-15T08:45:00Z") == "2024-10-15"
        assert parse_feed_date("2024-10-15T12:00:00+00:00") == "2024-10-15"

        # Empty or invalid string returns current UTC date in YYYY-MM-DD format
        fallback = parse_feed_date("")
        assert re.match(r"^\d{4}-\d{2}-\d{2}$", fallback)

    def test_rss_feed_ingestion_writes_both_date_and_published_date(self):
        """fetch_feed_entries must populate both 'date' and 'published_date' with valid ISO-8601 strings."""
        rss_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>HashiCorp Blog</title>
                <link>https://www.hashicorp.com/blog</link>
                <item>
                    <title>Terraform 1.9 Introduces Ephemeral Values</title>
                    <link>https://www.hashicorp.com/blog/terraform-1-9-ephemeral-values</link>
                    <description>Ephemeral values provide safe handling of temporary secrets in state.</description>
                    <pubDate>Wed, 16 Oct 2024 12:00:00 GMT</pubDate>
                </item>
            </channel>
        </rss>"""

        feed_info = {
            "company": "HashiCorp",
            "source": "HashiCorp Blog",
            "category": "Infrastructure & DevOps",
            "feed_url": "https://www.hashicorp.com/blog/feed.xml",
            "allowed_domain": "hashicorp.com",
            "source_domain": "hashicorp.com",
            "impact_badge": "Infrastructure as Code"
        }

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = rss_xml

        with patch("httpx.Client.get", return_value=mock_resp):
            entries = fetch_feed_entries(feed_info, max_items=1)

        assert len(entries) == 1
        entry = entries[0]
        assert entry["company"] == "HashiCorp"
        assert entry["source_domain"] == "hashicorp.com"
        assert entry["published_date"] == "2024-10-16"
        assert entry["date"] == "2024-10-16"
        assert re.match(r"^\d{4}-\d{2}-\d{2}$", entry["date"])
        assert re.match(r"^\d{4}-\d{2}-\d{2}$", entry["published_date"])

    def test_atom_feed_ingestion_and_domain_filter(self):
        """fetch_feed_entries must parse Atom feeds and filter out items with unapproved external domains."""
        atom_xml = b"""<?xml version="1.0" encoding="utf-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <title>Red Hat Press Releases</title>
            <entry>
                <title>Red Hat Announces OpenShift 4.16 for Hybrid Cloud</title>
                <link href="https://www.redhat.com/en/about/press-releases/openshift-4-16"/>
                <summary>New enhancements for edge workloads and container virtualization.</summary>
                <published>2024-10-18T10:00:00Z</published>
            </entry>
            <entry>
                <title>Rogue Article Pointing to Malicious Domain</title>
                <link href="https://unauthorized-domain.com/phishing"/>
                <summary>Deceptive link.</summary>
                <published>2024-10-18T10:00:00Z</published>
            </entry>
            <entry>
                <title>Insane Shocking Clickbait Title You Won't Believe</title>
                <link href="https://www.redhat.com/en/about/press-releases/clickbait"/>
                <summary>Sensationalized rumor.</summary>
                <published>2024-10-18T10:00:00Z</published>
            </entry>
        </feed>"""

        feed_info = {
            "company": "Red Hat",
            "source": "Red Hat Press Releases",
            "category": "Linux & Enterprise",
            "feed_url": "https://www.redhat.com/en/rss/press-releases",
            "allowed_domain": "redhat.com",
            "source_domain": "redhat.com",
            "impact_badge": "Linux & Enterprise"
        }

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = atom_xml

        with patch("httpx.Client.get", return_value=mock_resp):
            entries = fetch_feed_entries(feed_info, max_items=5)

        # Only the clean Red Hat domain article should pass; rogue domain and clickbait must be filtered out
        assert len(entries) == 1
        entry = entries[0]
        assert entry["title"] == "Red Hat Announces OpenShift 4.16 for Hybrid Cloud"
        assert entry["date"] == "2024-10-18"
        assert entry["published_date"] == "2024-10-18"
        assert "redhat.com" in entry["url"]


class TestAtomicSchemaWriteProtection:
    """Verifies that news feeds writing invokes atomic write protection with JSON schema validation."""

    def test_save_news_feed_valid_payload_success(self, tmp_path):
        """save_news_feed must successfully write valid news payload and ensure schema compliance."""
        target_path = tmp_path / "valid_news.json"
        sample_payload = {
            "$schema": "./news_schema.json",
            "last_updated": "2026-10-23T12:00:00+00:00",
            "news": [
                {
                    "id": "microsoft-azure-openai-enterprise-announcement",
                    "company": "Microsoft",
                    "source": "Azure Blog",
                    "source_domain": "microsoft.com",
                    "category": "Cloud & AI",
                    "title": "Announcing General Availability of GPT-4o on Azure OpenAI",
                    "summary": "Enterprise customers can now deploy high-throughput multi-modal workloads on Azure.",
                    "published_date": "2024-10-20",
                    "date": "2024-10-20",
                    "url": "https://azure.microsoft.com/en-us/blog/azure-openai-gpt-4o-ga/",
                    "impact_badge": "Cloud & AI Architecture"
                }
            ]
        }

        save_news_feed(sample_payload, filepath=target_path)

        assert target_path.exists()
        with open(target_path, "r", encoding="utf-8") as f:
            saved = json.load(f)

        assert saved["total_items"] == 1
        assert saved["$schema"] == "./news_schema.json"
        assert len(saved["news"]) == 1
        validate_payload(saved, NEWS_SCHEMA)

    def test_save_news_feed_preflight_rejection_prevents_file_corruption(self, tmp_path):
        """save_news_feed must reject invalid payloads via jsonschema and leave target untouched."""
        target_path = tmp_path / "test_rejection.json"
        target_path.write_text('{"initial": "clean_state"}', encoding="utf-8")

        corrupt_payload = {
            "$schema": "./news_schema.json",
            "last_updated": "2026-10-23T12:00:00+00:00",
            "news": [
                {
                    "id": "corrupt-article",
                    "company": "Test Company",
                    # Missing source, category, impact_badge, date!
                    "title": "Missing required fields",
                    "url": "https://test.example.com",
                    "published_date": "invalid-non-iso-date"
                }
            ]
        }

        with pytest.raises(jsonschema.ValidationError):
            save_news_feed(corrupt_payload, filepath=target_path)

        # Assert initial clean state file was NOT overwritten or corrupted
        assert target_path.read_text(encoding="utf-8") == '{"initial": "clean_state"}'
