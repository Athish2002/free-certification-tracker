"""
End-to-End Output Verification & Mathematical Invariant Test Suite.
Enforces structural payload integrity, cross-format synchronization (JSON vs README vs HTML),
calendar conservation laws, and verified authentic news radar integrity across CertPulse.
"""

import re
import json
import pytest
from pathlib import Path
from src.authenticity import (
    clean_hostname,
    check_domain_authenticity,
    check_ssl_and_protocol,
    check_redirect_chain_security,
    audit_offer_authenticity,
    SCAM_DOMAIN_KEYWORDS,
    BANNED_URL_SHORTENERS,
    SUSPICIOUS_TLDS
)

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "offers.json"
NEWS_FILE = ROOT / "data" / "news.json"
README_FILE = ROOT / "README.md"
DOCS_HTML = ROOT / "docs" / "index.html"

CANONICAL_STATUSES = {
    "Active", "Registrations Closed", "Expired", "Broken Link",
    "Review Needed", "Server Error", "Network Warning"
}

APPROVED_NEWS_DOMAINS = {
    "aws.amazon.com",
    "microsoft.com",
    "cloud.google.com",
    "blogs.oracle.com",
    "blogs.cisco.com",
    "github.blog",
    "linuxfoundation.org",
    "databricks.com",
    "snowflake.com"
}

BANNED_CLICKBAIT_PATTERNS = [
    r"\bshocking\b", r"\binsane\b", r"\byou won't believe\b",
    r"\bunbelievable\b", r"\bsecret trick\b", r"\bgame changer\b",
    r"\bdestroy\b", r"\bmind blowing\b", r"\bexposed\b", r"\bviral\b"
]

@pytest.fixture(scope="session")
def loaded_data():
    assert DATA_FILE.exists(), f"Missing primary data store: {DATA_FILE}"
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture(scope="session")
def loaded_news():
    assert NEWS_FILE.exists(), f"Missing news data store: {NEWS_FILE}"
    with open(NEWS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture(scope="session")
def readme_text():
    assert README_FILE.exists(), f"Missing README.md: {README_FILE}"
    with open(README_FILE, "r", encoding="utf-8") as f:
        return f.read()

@pytest.fixture(scope="session")
def html_text():
    assert DOCS_HTML.exists(), f"Missing docs/index.html: {DOCS_HTML}"
    with open(DOCS_HTML, "r", encoding="utf-8") as f:
        return f.read()

# --- 1. Structural Schema Invariants ---

def test_json_schema_invariants(loaded_data):
    """Asserts that all offers strictly conform to expected types and required attributes."""
    offers = loaded_data.get("offers", [])
    assert len(offers) > 0, "Offer database cannot be empty"

    seen_ids = set()
    for o in offers:
        # Key presence
        for req_field in ["id", "title", "platform", "category", "certification_name", "url", "status", "claim_steps"]:
            assert req_field in o, f"Offer {o.get('id', 'UNKNOWN')} missing required field: {req_field}"
            assert str(o[req_field]).strip() != "", f"Offer {o.get('id')} has blank {req_field}"

        # Uniqueness invariant
        oid = o["id"]
        assert oid not in seen_ids, f"Duplicate offer id detected: {oid}"
        seen_ids.add(oid)

        # URL invariant
        url = str(o["url"])
        assert url.startswith("https://"), f"Offer {oid} URL must be secure HTTPS: {url}"

        # Canonical status invariant
        assert o["status"] in CANONICAL_STATUSES, f"Offer {oid} has non-canonical status: {o['status']}"

        # Value invariant (must be non-negative integer or None)
        val = o.get("value_usd")
        if val is not None:
            assert isinstance(val, (int, float)) and val >= 0, f"Invalid value_usd for {oid}: {val}"

def test_news_json_schema_invariants(loaded_news):
    """Asserts that verified engineering news items meet strict integrity and authenticity invariants."""
    news_items = loaded_news.get("news", [])
    assert len(news_items) >= 10, f"Expected at least 10 news items, found {len(news_items)}"

    seen_ids = set()
    for item in news_items:
        # Key presence
        for req_field in ["id", "company", "source", "source_domain", "category", "title", "summary", "published_date", "url"]:
            assert req_field in item, f"News item {item.get('id', 'UNKNOWN')} missing field: {req_field}"
            assert str(item[req_field]).strip() != "", f"News item {item.get('id')} has empty field {req_field}"

        # Uniqueness
        nid = item["id"]
        assert nid not in seen_ids, f"Duplicate news id: {nid}"
        seen_ids.add(nid)

        # Domain whitelist invariant (strictly authentic primary enterprise domains)
        domain = item["source_domain"]
        assert domain in APPROVED_NEWS_DOMAINS, f"Domain '{domain}' not in approved enterprise whitelist for {nid}"

        # URL HTTPS invariant
        assert item["url"].startswith("https://"), f"News URL must be HTTPS: {item['url']}"

        # Date format invariant (YYYY-MM-DD)
        assert re.match(r"^\d{4}-\d{2}-\d{2}$", item["published_date"]), f"Invalid published_date for {nid}: {item['published_date']}"

        # Zero clickbait invariant
        content = (item["title"] + " " + item["summary"]).lower()
        for pat in BANNED_CLICKBAIT_PATTERNS:
            assert not re.search(pat, content), f"Clickbait buzzword detected in {nid}: pattern {pat}"

# --- 2. Mathematical Conservation Laws & Cross-Format Sync ---

def test_readme_and_json_mathematical_sync(loaded_data, readme_text):
    """
    Asserts mathematical conservation laws:
    Total Value Saved in README == sum(value_usd) of Active offers in JSON.
    Total Active Count in README badge == count(Active offers) in JSON.
    """
    offers = loaded_data.get("offers", [])
    active_offers = [o for o in offers if o.get("status") == "Active"]
    expected_savings = sum((o.get("value_usd") or 0) for o in active_offers)
    expected_count = len(active_offers)

    # 1. Assert Badge Count
    count_badge_match = re.search(r"!\[Active Vouchers\]\(https://img\.shields\.io/badge/Active%20Offers-(\d+)-success\.svg\)", readme_text)
    assert count_badge_match is not None, "Active Offers count badge missing in README"
    assert int(count_badge_match.group(1)) == expected_count, (
        f"README badge active count ({count_badge_match.group(1)}) desynchronized with JSON active count ({expected_count})"
    )

    # 2. Assert Badge Savings Value
    val_badge_match = re.search(r"!\[Total Savings\]\(https://img\.shields\.io/badge/Total%20Value%20Saved-%24(\d+)%20USD-gold\.svg\)", readme_text)
    assert val_badge_match is not None, "Total Savings badge missing in README"
    assert int(val_badge_match.group(1)) == expected_savings, (
        f"README badge savings value (${val_badge_match.group(1)}) desynchronized with JSON total (${expected_savings})"
    )

    # 3. Assert Executive Summary Table matches
    assert f"| **Active Opportunities** | **{expected_count}** |" in readme_text
    assert f"| **Total Financial Value** | **${expected_savings:,} USD** |" in readme_text

def test_readme_news_radar_sync(loaded_news, readme_text):
    """Asserts that the intelligence radar table in README.md accurately reflects all news items."""
    news_items = loaded_news.get("news", [])
    assert "## 📰 Verified Cloud & Engineering Intelligence Radar" in readme_text, "Missing news radar heading in README"
    assert f"| **Verified Tech Dispatches** | **{len(news_items)} Reports** |" in readme_text

    for item in news_items:
        assert item["title"] in readme_text, f"News title '{item['title']}' not rendered in README table"
        assert item["url"] in readme_text, f"News URL '{item['url']}' not linked in README table"

def test_web_dashboard_payload_sync(loaded_data, loaded_news, html_text):
    """
    Asserts that the static web dashboard contains the full, valid JSON payloads
    for both offersData and newsData.
    """
    offers = loaded_data.get("offers", [])
    news = loaded_news.get("news", [])
    
    # 1. Offers JSON payload sync
    match_offers = re.search(r"const offersData = (\[.*?\]);", html_text, flags=re.DOTALL)
    assert match_offers is not None, "Embedded offersData script variable not found in docs/index.html"
    embedded_offers = json.loads(match_offers.group(1))
    assert len(embedded_offers) == len(offers), (
        f"Dashboard offersData count ({len(embedded_offers)}) != JSON offers count ({len(offers)})"
    )

    # 2. News JSON payload sync
    match_news = re.search(r"const newsData = (\[.*?\]);", html_text, flags=re.DOTALL)
    assert match_news is not None, "Embedded newsData script variable not found in docs/index.html"
    embedded_news = json.loads(match_news.group(1))
    assert len(embedded_news) == len(news), (
        f"Dashboard newsData count ({len(embedded_news)}) != JSON news count ({len(news)})"
    )

# --- 3. Anti-Divergence Regression Checks ---

def test_no_dead_code_or_unresolved_todos(readme_text, html_text):
    """Verifies production cleanliness: zero placeholder stubs."""
    for text, name in [(readme_text, "README.md"), (html_text, "docs/index.html")]:
        assert "TODO" not in text, f"Unresolved TODO found in {name}"
        assert "FIXME" not in text, f"Unresolved FIXME found in {name}"
        assert "undefined" not in text, f"'undefined' string leak found in {name}"

def test_mobile_ux_invariants(html_text):
    """Verifies mobile responsiveness, safe area insets, touch targets, and iOS zoom prevention."""
    assert 'viewport-fit=cover' in html_text, "Missing viewport-fit=cover in docs/index.html"
    assert 'name="theme-color"' in html_text, "Missing theme-color meta tag in docs/index.html"
    assert 'safe-area-inset-bottom' in html_text, "Missing safe-area-inset-bottom handling in docs/index.html"
    assert 'touch-scroll' in html_text, "Missing touch-scroll CSS class in docs/index.html"
    assert '16px !important' in html_text, "Missing 16px mobile input rule to prevent iOS Safari auto-zoom"
    assert 'min-h-[44px]' in html_text, "Missing min-h-[44px] for SubNav touch targets in docs/index.html"
    assert 'min-h-[40px]' in html_text, "Missing min-h-[40px] for interactive buttons and pills in docs/index.html"
    assert 'onStatusFilterChange' in html_text, "Missing onStatusFilterChange function for filter synchronization"
    assert 'offersData.find' in html_text, "copySteps should lookup offer in offersData by ID to avoid escaping bugs"

# --- 4. Multi-Layer Authenticity & Anti-Scam Security Invariants ---

def test_offer_authenticity_schema_invariants(loaded_data):
    """
    Enforces that every certification offer contains verified authenticity metadata,
    high trust scores, and valid structured verification details.
    """
    offers = loaded_data.get("offers", [])
    assert len(offers) > 0, "Offer database cannot be empty"

    for o in offers:
        oid = o.get("id", "UNKNOWN")
        
        # 1. Flag presence & type invariant
        assert "is_authentic_vendor" in o, f"Offer {oid} missing 'is_authentic_vendor' flag"
        assert isinstance(o["is_authentic_vendor"], bool), f"Offer {oid} 'is_authentic_vendor' must be boolean"
        assert o["is_authentic_vendor"] is True, f"Offer {oid} failed authenticity verification: {o.get('inspection_notes')}"

        # 2. Score invariant [80, 100]
        assert "authenticity_score" in o, f"Offer {oid} missing 'authenticity_score'"
        score = o["authenticity_score"]
        assert isinstance(score, int), f"Offer {oid} 'authenticity_score' must be integer"
        assert 80 <= score <= 100, f"Offer {oid} has authenticity score below acceptable threshold: {score}"

        # 3. Details dictionary invariant
        assert "authenticity_details" in o, f"Offer {oid} missing 'authenticity_details'"
        details = o["authenticity_details"]
        assert isinstance(details, dict), f"Offer {oid} 'authenticity_details' must be a dict"
        assert details.get("domain_verified") is True, f"Offer {oid} domain not verified in details"
        assert details.get("ssl_verified") is True, f"Offer {oid} SSL not verified in details"
        assert details.get("redirect_secure") is True, f"Offer {oid} redirect not verified in details"
        assert details.get("trust_tier") in {"Official Vendor Portal", "Accredited Exam Partner", "Accredited Educational Institution"}

def test_domain_authenticity_and_anti_scam_invariants(loaded_data):
    """
    Asserts zero scam voucher farms, zero braindumps, strict HTTPS,
    and verified primary vendor or partner domains across all offers.
    """
    offers = loaded_data.get("offers", [])
    for o in offers:
        oid = o["id"]
        url = str(o["url"])

        # 1. Strict HTTPS protocol invariant
        ssl_ok, ssl_flags = check_ssl_and_protocol(url)
        assert ssl_ok is True, f"Offer {oid} failed SSL/TLS protocol check: {ssl_flags}"

        # 2. Domain whitelist & platform matching
        domain_ok, tier, reason, flags = check_domain_authenticity(url, o.get("platform", ""))
        assert domain_ok is True, f"Offer {oid} domain failed authenticity check: {reason} (flags: {flags})"
        assert tier in {"Official Vendor Portal", "Accredited Exam Partner", "Accredited Educational Institution"}

        # 3. Zero scam keywords in domain hostname
        host = clean_hostname(url)
        for scam_kw in SCAM_DOMAIN_KEYWORDS:
            assert scam_kw not in host, f"Offer {oid} host contains scam keyword '{scam_kw}': {host}"

        # 4. Zero banned shorteners in domain hostname
        for shortener in BANNED_URL_SHORTENERS:
            assert host != shortener and not host.endswith("." + shortener), (
                f"Offer {oid} host uses disallowed shortener '{shortener}': {host}"
            )

        # 5. Zero suspicious TLDs in domain hostname
        for tld in SUSPICIOUS_TLDS:
            assert not host.endswith(tld), (
                f"Offer {oid} host uses high-risk scam TLD '{tld}': {host}"
            )

def test_authenticity_engine_adversarial_rejection():
    """
    Asserts that the authenticity engine vigorously rejects typosquatting,
    scam voucher farms, braindumps, paywall traps, open redirects, vendor mismatches, and insecure transports.
    """
    adversarial_cases = [
        # Typosquatting Microsoft (must strictly be DECEPTIVE_SCAM)
        {
            "offer": {"platform": "Microsoft Azure", "url": "https://micros0ft-freecerts.top/promo"},
            "body": "",
            "expected_verdict": ["DECEPTIVE_SCAM"]
        },
        # Typosquatting Salesforce
        {
            "offer": {"platform": "Salesforce", "url": "https://salesf0rce.com/voucher"},
            "body": "",
            "expected_verdict": ["DECEPTIVE_SCAM"]
        },
        # Exam braindump domain
        {
            "offer": {"platform": "Amazon Web Services", "url": "https://aws-examdumps.xyz/vouchers"},
            "body": "",
            "expected_verdict": ["DECEPTIVE_SCAM"]
        },
        # Disallowed shortener cloaking
        {
            "offer": {"platform": "Google Cloud", "url": "https://bit.ly/azure-free-voucher"},
            "body": "",
            "expected_verdict": ["DECEPTIVE_SCAM"]
        },
        # Insecure HTTP
        {
            "offer": {"platform": "Microsoft Azure", "url": "http://learn.microsoft.com/credentials"},
            "body": "",
            "expected_verdict": ["SUSPICIOUS_UNTRUSTED"]
        },
        # Userinfo spoofing injection
        {
            "offer": {"platform": "Microsoft Azure", "url": "https://admin:secret@learn.microsoft.com/credentials"},
            "body": "",
            "expected_verdict": ["SUSPICIOUS_UNTRUSTED"]
        },
        # Open redirect target to scam domain
        {
            "offer": {"platform": "Microsoft Azure", "url": "https://learn.microsoft.com/external?goto=https://scam-dumps.xyz"},
            "body": "",
            "expected_verdict": ["DECEPTIVE_SCAM"]
        },
        # Vendor mismatch (cross-vendor spoofing)
        {
            "offer": {"platform": "Microsoft Azure", "url": "https://cisco.com/free-vouchers"},
            "body": "",
            "expected_verdict": ["DECEPTIVE_SCAM", "SUSPICIOUS_UNTRUSTED"]
        },
        # Legitimate domain with exam dump scam content
        {
            "offer": {"platform": "Oracle Cloud", "url": "https://education.oracle.com/oracle-cloud-infrastructure"},
            "body": "Download our guaranteed pass 100% real braindump exam questions and answers.",
            "expected_verdict": ["DECEPTIVE_SCAM"]
        },
        # Legitimate domain with credit card paywall trap
        {
            "offer": {"platform": "Cisco", "url": "https://u.cisco.com/"},
            "body": "Credit card is required to enroll. 7-day trial then $49 billed automatically after trial.",
            "expected_verdict": ["DECEPTIVE_SCAM"]
        },
        # Deceptive paywall auto-renewal
        {
            "offer": {"platform": "Salesforce", "url": "https://trailhead.salesforce.com/quests"},
            "body": "Credit card is required for account creation. Subscription auto-renews at $39/mo.",
            "expected_verdict": ["DECEPTIVE_SCAM"]
        },
        # Expired promo/coupon code page
        {
            "offer": {"platform": "Databricks", "url": "https://www.databricks.com/learn/training/certification"},
            "body": "Sorry, this promo code is invalid or has expired.",
            "expected_verdict": ["DECEPTIVE_SCAM"]
        }
    ]

    for case in adversarial_cases:
        res = audit_offer_authenticity(case["offer"], body_text=case["body"])
        assert res["is_authentic_vendor"] is False, f"Adversarial case succeeded unexpectedly: {case['offer']['url']}"
        assert res["verdict"] in case["expected_verdict"], (
            f"Adversarial case {case['offer']['url']} returned {res['verdict']}, expected {case['expected_verdict']}"
        )
        assert res["authenticity_score"] <= 50, f"Adversarial case received too high score: {res['authenticity_score']}"

def test_redirect_chain_security_invariant():
    """
    Asserts that redirect chains with protocol downgrades, shorteners,
    affiliate trackers, or malicious destinations are detected and rejected.
    """
    # 1. Clean genuine chain
    clean_chain = [
        "https://learn.microsoft.com/en-us/training",
        "https://learn.microsoft.com/en-us/credentials/applied-skills/"
    ]
    ok, flags = check_redirect_chain_security(clean_chain, "Microsoft Azure")
    assert ok is True
    assert "CLEAN_REDIRECT_CHAIN" in flags

    # 2. Insecure HTTP downgrade
    downgrade_chain = [
        "https://aws.amazon.com/education",
        "http://aws.amazon.com/education/awseducate/"
    ]
    ok, flags = check_redirect_chain_security(downgrade_chain, "Amazon Web Services")
    assert ok is False
    assert "REDIRECT_SSL_DOWNGRADE" in flags

    # 3. Cloaked redirect through shortener
    shortener_chain = [
        "https://google.com/promo",
        "https://bit.ly/gcp-cert",
        "https://cloudskillsboost.google/"
    ]
    ok, flags = check_redirect_chain_security(shortener_chain, "Google Cloud")
    assert ok is False
    assert "REDIRECT_THROUGH_SHORTENER" in flags

    # 4. Intermediate hop routing through scam domain
    scam_hop_chain = [
        "https://learn.microsoft.com/start",
        "https://scam-ad-tracker.xyz/click",
        "https://learn.microsoft.com/finish"
    ]
    ok, flags = check_redirect_chain_security(scam_hop_chain, "Microsoft Azure")
    assert ok is False
    assert any("REDIRECT_THROUGH_SUSPICIOUS_TLD" in f or "REDIRECT_THROUGH_SCAM" in f for f in flags)

    # 5. Intermediate hop routing through affiliate network
    affiliate_hop_chain = [
        "https://aws.amazon.com/promo",
        "https://cj.com/track",
        "https://aws.amazon.com/finish"
    ]
    ok, flags = check_redirect_chain_security(affiliate_hop_chain, "Amazon Web Services")
    assert ok is False
    assert any("AFFILIATE" in f for f in flags)

    # 6. Redirecting to external untrusted scam destination
    scam_dest_chain = [
        "https://u.cisco.com/promo",
        "https://scam-voucher-farm.xyz/affiliate-lead"
    ]
    ok, flags = check_redirect_chain_security(scam_dest_chain, "Cisco")
    assert ok is False
    assert "REDIRECT_UNTRUSTED_DESTINATION" in flags

def test_educational_institution_authenticity_invariant():
    """Asserts that accredited university and academic domains are verified authentic."""
    uni_cases = [
        "https://online.stanford.edu/courses/cloud-computing",
        "https://cs50.harvard.edu/x",
        "https://mitxonline.mit.edu/courses"
    ]
    for url in uni_cases:
        ok, tier, _, flags = check_domain_authenticity(url, "")
        assert ok is True
        assert tier == "Accredited Educational Institution"
        assert "ACCREDITED_UNIVERSITY_DOMAIN" in flags

def test_readme_and_dashboard_authenticity_sync(loaded_data, readme_text, html_text):
    """
    Asserts that the README badge and Web Dashboard prominently display
    verified vendor authenticity metrics and zero-scam disclosures.
    """
    # README authenticity indicators
    assert "![Authenticity](https://img.shields.io/badge/Authenticity-100%25%20Verified%20Vendor-success.svg)" in readme_text
    assert "| **Authenticity Gate** | **100% Primary Vendor Verified** |" in readme_text

    # Web Dashboard authenticity indicators
    assert "Authenticity Standard" in html_text
    assert "100% Authentic" in html_text
    assert "Zero scam domains, zero dumps, strict TLS" in html_text


