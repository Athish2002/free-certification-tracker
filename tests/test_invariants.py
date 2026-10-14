"""
End-to-End Output Verification & Mathematical Invariant Test Suite.
Enforces structural payload integrity, cross-format synchronization (JSON vs README vs HTML),
calendar conservation laws, and verified authentic news radar integrity across CertPulse.
"""

import re
import json
import pytest
from pathlib import Path

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
