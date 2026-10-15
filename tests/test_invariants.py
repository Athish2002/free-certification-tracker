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
from src.dom_inspector import (
    inspect_rendered_dom,
    HeadlessDOMInspector,
    CAPACITY_PATTERNS,
    COUPON_EXPIRED_PATTERNS,
    REGISTRATION_CLOSED_PATTERNS,
    DEAD_END_PATTERNS
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

def test_multiview_dashboard_invariants(html_text):
    """
    Asserts that all 4 view modes are implemented in docs/index.html:
    1. Bento Cards Grid (grid)
    2. Executive Catalog Table (list)
    3. Recurrence & Expiry Timeline Roadmap (timeline)
    4. Domain & Skill Matrix (matrix)
    """
    # 1. Switcher buttons
    for btn_id in ["viewBtnGrid", "viewBtnList", "viewBtnTimeline", "viewBtnMatrix"]:
        assert f'id="{btn_id}"' in html_text, f"Missing view switcher button: {btn_id}"

    # 2. View containers
    for container_id in ["cardsViewContainer", "listViewContainer", "timelineViewContainer", "matrixViewContainer"]:
        assert f'id="{container_id}"' in html_text, f"Missing view container: {container_id}"

    # 3. View switching function supports all 4 modes
    assert "setLayoutView(view" in html_text
    assert "'grid', 'list', 'timeline', 'matrix'" in html_text

    # 4. Keyboard shortcuts
    assert "views.indexOf(currentLayout)" in html_text, "Missing cycling logic for V key"

def test_expanded_vendor_authenticity_coverage(loaded_data):
    """
    Enforces authentic coverage across all enterprise vendors requested:
    Red Hat, HashiCorp, Palo Alto Networks, GitLab, Splunk, IBM, CNCF, Databricks, Oracle Cloud, Cisco, GitHub.
    """
    offers = loaded_data.get("offers", [])
    platforms_present = {o.get("platform") for o in offers}
    
    expected_platforms = {
        "Red Hat",
        "HashiCorp",
        "Palo Alto Networks",
        "GitLab",
        "Splunk",
        "IBM",
        "Linux Foundation / CNCF",
        "Databricks",
        "Oracle Cloud",
        "Cisco",
        "GitHub"
    }

    for p in expected_platforms:
        assert p in platforms_present, f"Expected vendor platform '{p}' not present in offers.json"

    # Assert all offers for these platforms are verified authentic
    for o in offers:
        if o.get("platform") in expected_platforms:
            assert o.get("is_authentic_vendor") is True, f"Offer {o.get('id')} failed vendor authenticity"
            assert o.get("authenticity_score", 0) >= 80, f"Offer {o.get('id')} has score < 80"
            assert o.get("url", "").startswith("https://"), f"Offer {o.get('id')} must use HTTPS"

def test_difficulty_tier_and_timeline_metadata(loaded_data):
    """
    Asserts that every offer has valid difficulty_tier and timeline metadata.
    """
    valid_tiers = {"Foundational", "Associate", "Professional"}
    offers = loaded_data.get("offers", [])

    for o in offers:
        oid = o.get("id")
        tier = o.get("difficulty_tier")
        assert tier in valid_tiers, f"Offer {oid} has invalid difficulty_tier: {tier}"
        assert "time_period" in o and str(o["time_period"]).strip() != "", f"Offer {oid} missing time_period"
        assert "recurrence_pattern" in o and str(o["recurrence_pattern"]).strip() != "", f"Offer {oid} missing recurrence_pattern"


def test_html_javascript_syntax_validity(html_text):
    """
    Asserts that the JavaScript embedded in docs/index.html is 100% syntactically valid
    and passes Node.js syntax verification with exit code 0.
    """
    import subprocess
    import tempfile

    assert "<script>" in html_text and "</script>" in html_text, "Missing script tag in index.html"
    script_content = html_text.split("<script>")[1].split("</script>")[0]

    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as tmp:
        tmp.write(script_content)
        tmp_path = Path(tmp.name)

    try:
        proc = subprocess.run(["node", "--check", str(tmp_path)], capture_output=True, text=True)
        assert proc.returncode == 0, f"JavaScript syntax error in docs/index.html:\n{proc.stderr}"
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def test_domain_matrix_technical_domains(html_text):
    """
    Asserts that all 5 required technical domains (Cloud, Security, AI/Data, DevOps, Networking)
    are configured and rendered in the Domain & Skill Matrix.
    """
    for dom_id in ["cloud", "security", "ai_data", "devops", "networking"]:
        assert f"id: '{dom_id}'" in html_text, f"Missing domain configuration for: {dom_id}"


def test_interactive_browser_view_switching():
    """
    Executes headless Chromium browser test via Playwright to verify:
    1. Zero console errors or uncaught page exceptions.
    2. Dynamic DOM rendering across Bento Grid, Table, Timeline, and Matrix.
    3. Keyboard listeners ('v', '1', '2', 't').
    4. URL query parameter synchronization and deep-linking (?view=timeline, ?view=matrix).
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("Playwright not installed in environment")

    file_url = DOCS_HTML.as_uri()

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page_errors = []
        page.on("pageerror", lambda err: page_errors.append(str(err)))

        # 1. Initial Load in Bento Grid
        page.goto(file_url)
        page.wait_for_selector("#offersGrid")
        assert page.locator("#offersGrid .primer-card").count() > 0, "No voucher cards rendered in Bento Grid"

        # 2. Switch to Table
        page.click("#viewBtnList")
        assert page.locator("#offersTableBody > div").count() > 0, "No rows rendered in Table view"

        # 3. Switch to Timeline
        page.click("#viewBtnTimeline")
        assert page.locator("#offersTimeline .primer-card").count() > 0, "No cards rendered in Timeline view"

        # 4. Switch to Matrix
        page.click("#viewBtnMatrix")
        assert page.locator("#offersMatrix .primer-card").count() > 0, "No cards rendered in Matrix view"

        # 5. Keyboard shortcut V (cycle from matrix -> grid)
        page.keyboard.press("v")
        assert page.is_visible("#cardsViewContainer"), "Keyboard 'v' failed to switch back to Grid"

        # 6. Keyboard shortcut 2 (jump to News Radar)
        page.keyboard.press("2")
        assert page.is_visible("#newsSection"), "Keyboard '2' failed to switch to News tab"

        # 7. Keyboard shortcut 1 (jump to Vouchers)
        page.keyboard.press("1")
        assert page.is_visible("#vouchersSection"), "Keyboard '1' failed to switch to Vouchers tab"

        # 8. Keyboard shortcut 3 (jump to Where Offers Are Applied / Redemption Guide)
        page.keyboard.press("3")
        assert page.is_visible("#redemptionSection"), "Keyboard '3' failed to switch to Redemption tab"
        assert page.locator("#redemptionGrid .primer-card").count() > 0, "No cards rendered in Redemption view"

        # 9. Keyboard shortcut 1 (jump to Vouchers)
        page.keyboard.press("1")
        assert page.is_visible("#vouchersSection"), "Keyboard '1' failed to switch back to Vouchers tab"

        # 10. Keyboard shortcut T (theme toggle)
        theme_init = page.evaluate("() => document.documentElement.getAttribute('data-theme')")
        page.keyboard.press("t")
        theme_toggled = page.evaluate("() => document.documentElement.getAttribute('data-theme')")
        assert theme_init != theme_toggled, f"Theme did not toggle: {theme_init} -> {theme_toggled}"

        # 11. Direct Deep-Linking URL query parameter (?view=matrix)
        page.goto(f"{file_url}?view=matrix")
        assert page.is_visible("#matrixViewContainer"), "Deep-link ?view=matrix did not activate Matrix view"

        # 12. Direct Deep-Linking URL query parameter (?view=timeline)
        page.goto(f"{file_url}?view=timeline")
        assert page.is_visible("#timelineViewContainer"), "Deep-link ?view=timeline did not activate Timeline view"

        # 13. Direct Deep-Linking URL query parameter (?tab=redemption)
        page.goto(f"{file_url}?tab=redemption")
        assert page.is_visible("#redemptionSection"), "Deep-link ?tab=redemption did not activate Redemption tab"
        assert page.locator("#redemptionGrid .primer-card").count() > 0, "No cards rendered in ?tab=redemption view"

        browser.close()

        assert len(page_errors) == 0, f"Encountered browser page errors: {page_errors}"


# --- 5. Where Offers Are Applied & Zero-Dollar Checkout Invariants ---

def test_redemption_guide_schema_invariants(loaded_data):
    """
    Enforces that every certification offer contains complete, structured redemption mechanisms,
    checkout field locations, official delivery portals, and step-by-step zero-dollar instructions.
    """
    offers = loaded_data.get("offers", [])
    assert len(offers) > 0, "Offer database cannot be empty"

    valid_flow_types = {
        "Checkout Promo Code",
        "Automated Account Link Waiver",
        "Direct Assessment Launch",
        "Scholarship Award Token",
        "Continuing Education Claim",
        "Training Milestone Token",
        "Event Voucher Code"
    }

    for o in offers:
        oid = o.get("id", "UNKNOWN")

        # 1. Top-level redemption fields presence and type
        for field in ["voucher_code", "redemption_portal", "checkout_field", "application_flow_type", "cart_balance_verified"]:
            assert field in o, f"Offer {oid} missing redemption field: {field}"
            assert str(o[field]).strip() != "", f"Offer {oid} has empty redemption field: {field}"

        assert o["application_flow_type"] in valid_flow_types, (
            f"Offer {oid} has non-standard application_flow_type: {o['application_flow_type']}"
        )
        assert "$0.00" in o["cart_balance_verified"], (
            f"Offer {oid} cart_balance_verified must confirm zero-dollar checkout: {o['cart_balance_verified']}"
        )

        # 2. Structured redemption_guide dictionary
        assert "redemption_guide" in o, f"Offer {oid} missing 'redemption_guide' dict"
        guide = o["redemption_guide"]
        assert isinstance(guide, dict), f"Offer {oid} 'redemption_guide' must be a dictionary"

        for subfield in ["portal_name", "portal_url", "field_location", "flow_type", "verified_cart_balance", "instructions"]:
            assert subfield in guide, f"Offer {oid} redemption_guide missing subfield: {subfield}"
            assert guide[subfield], f"Offer {oid} redemption_guide has empty subfield: {subfield}"

        assert "$0.00" in guide["verified_cart_balance"]
        instructions = guide["instructions"]
        assert isinstance(instructions, list), f"Offer {oid} instructions must be a list"
        assert len(instructions) >= 2, f"Offer {oid} must have at least 2 step-by-step instructions"
        for step in instructions:
            assert isinstance(step, str) and len(step.strip()) > 10, f"Offer {oid} has too short instruction step: {step}"

        # 3. Protocol security on redemption portal
        if o.get("status") == "Active":
            assert str(guide["portal_url"]).startswith("https://"), (
                f"Active offer {oid} redemption portal must use HTTPS: {guide['portal_url']}"
            )


def test_readme_and_dashboard_redemption_sync(loaded_data, readme_text, html_text):
    """
    Asserts that README.md and docs/index.html are synchronized with the
    Where Offers Are Applied zero-dollar checkout reference.
    """
    active_offers = [o for o in loaded_data.get("offers", []) if o.get("status") == "Active"]

    # 1. README redemption table and sections
    assert "## 💳 Where & How Vouchers Are Applied (Zero-Dollar Checkout Guide)" in readme_text, (
        "Missing redemption guide section header in README.md"
    )
    assert "| Official Redemption Portal | Checkout Field / Location | Application Flow | Verified Cart Balance |" in readme_text, (
        "Missing redemption table headers in README.md"
    )
    assert "**$0.00**" in readme_text, "Missing bold $0.00 balance indicator in README.md"

    for o in active_offers:
        assert o["certification_name"] in readme_text, (
            f"Active offer {o['id']} certification name missing from README redemption table"
        )
        assert o["checkout_field"] in readme_text, (
            f"Active offer {o['id']} checkout field location missing from README redemption table"
        )

    # 2. Web Dashboard interactive redemption elements
    assert 'id="tabBtnRedemption"' in html_text, "Missing tabBtnRedemption in docs/index.html"
    assert 'id="redemptionSection"' in html_text, "Missing redemptionSection in docs/index.html"
    assert 'id="redemptionGrid"' in html_text, "Missing redemptionGrid container in docs/index.html"
    assert 'renderRedemption' in html_text, "Missing renderRedemption function in docs/index.html"
    assert 'openRedemptionFor' in html_text, "Missing openRedemptionFor function in docs/index.html"
    assert 'copyVoucherToken' in html_text, "Missing copyVoucherToken function in docs/index.html"
    assert 'Cart Balance: $0.00' in html_text, "Missing Cart Balance: $0.00 badge in docs/index.html"
    assert '<span>3</span>' in html_text or '>3<' in html_text, "Missing Hotkey 3 hint in docs/index.html"


# --- 6. Headless Playwright DOM Inspection & Invariant Logic ---

def test_headless_dom_inspector_invariant_logic():
    """
    Asserts that the headless DOM inspection engine correctly detects:
    1. Cohort / seat capacity reached
    2. Expired promo / coupon codes
    3. Campaign closures
    4. Client-side dead-ends & soft-404s
    5. Silent reroutes
    6. Legitimate affirmative offer signals
    """
    # 1. Capacity Reached Invariant
    cap_text = "We apologize, but maximum capacity has been reached for this cohort of free exam candidates."
    res = inspect_rendered_dom(cap_text, rendered_title="Exam Registration Portal")
    assert res["status"] == "Registrations Closed"
    assert res["is_capacity_reached"] is True
    assert res["category"] == "capacity_reached"
    assert "capacity has been reached" in res["matched_phrase"]

    # 2. Expired Coupon Invariant
    coupon_text = "The promo code invalid or coupon has expired. Please check your redemption code."
    res = inspect_rendered_dom(coupon_text, rendered_title="Cart Checkout")
    assert res["status"] == "Expired"
    assert res["is_coupon_expired"] is True
    assert res["category"] == "coupon_expired"

    # 3. Closed Campaign Invariant
    closed_text = "This learning challenge has concluded and is no longer accepting submissions."
    res = inspect_rendered_dom(closed_text)
    assert res["status"] == "Registrations Closed"
    assert res["is_campaign_closed"] is True
    assert res["category"] == "campaign_closed"

    # 4. Soft 404 / Dead-End Invariant
    dead_text = "Sorry, 404 - page not found. The page you're looking for doesn't exist."
    res = inspect_rendered_dom(dead_text)
    assert res["status"] == "Broken Link"
    assert res["is_dead_end"] is True
    assert res["category"] == "dead_end"

    # 5. Silent Reroute Invariant
    res = inspect_rendered_dom(
        "Welcome to the general homepage catalog.",
        final_url="https://cloud.vendor.com/en-us",
        original_url="https://cloud.vendor.com/promo/free-voucher-challenge"
    )
    assert res["status"] == "Registrations Closed"
    assert res["category"] == "silent_reroute"

    # 6. Authentic Active Offer Signal
    active_text = "Complete the 30-day learning path to receive a 100% free certification exam voucher waiver."
    res = inspect_rendered_dom(active_text, rendered_title="Cloud Skills Challenge")
    assert res["status"] == "Active"
    assert res["category"] == "active"

    # 7. Redundant Link Invariant ("link is redundant" / "link is no longer active")
    redundant_text = "Notice: This link is redundant and has been replaced by the general documentation portal."
    res = inspect_rendered_dom(redundant_text, rendered_title="Offer Redirect")
    assert res["status"] == "Broken Link"
    assert res["is_dead_end"] is True
    assert res["is_redundant_link"] is True
    assert res["category"] == "redundant_link"
    assert "link is redundant" in res["matched_phrase"]

    # 8. User Prompt Phrasing: "offer is over"
    over_text = "The special promotional offer is over. Please check back next quarter."
    res = inspect_rendered_dom(over_text, rendered_title="Campaign Landing")
    assert res["status"] == "Registrations Closed"
    assert res["is_campaign_closed"] is True
    assert "offer is over" in res["matched_phrase"]

    # 9. Empty DOM / Hydration Failure Invariant
    empty_res = inspect_rendered_dom("", rendered_title="")
    assert empty_res["status"] == "Review Needed"
    assert empty_res["category"] == "empty_dom"

    # 10. Missing Affirmative Signals on Non-Empty Catalog Page
    catalog_res = inspect_rendered_dom(
        "Standard exam fee is $250. Select your test center and pay with credit card.",
        rendered_title="Pearson VUE Standard Catalog"
    )
    assert catalog_res["status"] == "Review Needed"
    assert catalog_res["category"] == "no_offer_signal"


def test_playwright_headless_dom_rendering_on_local_fixture(tmp_path):
    """
    Asserts that HeadlessDOMInspector launches headless Chromium,
    executes client-side JavaScript, and verifies dynamic DOM modifications.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("Playwright not installed in environment")

    # Create a local HTML page that uses JavaScript to inject a capacity closure alert
    html_content = """<!DOCTYPE html>
    <html>
    <head><title>Cloud Challenge Portal</title></head>
    <body>
        <div id="app">Loading campaign status...</div>
        <script>
            // Simulate client-side SPA state fetch
            setTimeout(() => {
                document.getElementById('app').innerHTML = `
                    <h1>Certification Registration</h1>
                    <div role="alert" class="alert-box">
                        Notice: seats are full and capacity has been reached for this cohort.
                    </div>
                `;
            }, 50);
        </script>
    </body>
    </html>"""

    test_file = tmp_path / "spa_test.html"
    test_file.write_text(html_content, encoding="utf-8")
    test_uri = test_file.as_uri()

    with HeadlessDOMInspector(headless=True, timeout_ms=8000) as inspector:
        assert inspector.is_available is True, "Headless Chromium failed to start"
        
        status, reason, final_url, auth_result = inspector.inspect_url(
            test_uri,
            offer={
                "id": "test-spa-offer",
                "platform": "Microsoft Azure",
                "url": test_uri
            }
        )
        assert status == "Registrations Closed", f"Expected Registrations Closed, got {status} ({reason})"
        assert "capacity has been reached" in reason.lower() or "seats are full" in reason.lower()


def test_dashboard_redemption_and_keyboard_invariants(html_text):
    """Asserts that the web dashboard implements robust clipboard fallbacks and multi-tab keyboard shortcuts."""
    assert "document.execCommand('copy')" in html_text, "Missing execCommand copy fallback in copyVoucherToken"
    assert "redemptionSearchInput" in html_text, "Missing redemptionSearchInput in docs/index.html"
    assert "currentMainTab === 'redemption'" in html_text, "Missing contextual tab check for redemption search in docs/index.html"


def test_inspector_run_inspection_loop_coverage(tmp_path, monkeypatch):
    """
    Asserts the loop invariant of run_inspection(): every non-archive offer in the collection
    must have its status, verification date, authenticity details, and notes updated,
    verifying that the update block is NOT indented outside the loop.
    """
    import src.inspector as insp

    test_offers_data = {
        "offers": [
            {
                "id": "test-offer-1",
                "title": "Test Cloud Certification 1",
                "platform": "Microsoft Azure",
                "category": "Cloud Architecture",
                "certification_name": "Azure Fundamentals",
                "url": "https://learn.microsoft.com/en-us/credentials/cert-1",
                "status": "Active",
                "claim_steps": "Follow instructions.",
                "value_usd": 99,
                "is_historical_archive": False
            },
            {
                "id": "test-offer-2",
                "title": "Test Cloud Certification 2",
                "platform": "AWS",
                "category": "Cloud Architecture",
                "certification_name": "AWS Cloud Practitioner",
                "url": "https://aws.amazon.com/certification/certified-cloud-practitioner/",
                "status": "Active",
                "claim_steps": "Follow instructions.",
                "value_usd": 100,
                "is_historical_archive": False
            },
            {
                "id": "hist-archive-3",
                "title": "Historical Promo 2024",
                "platform": "Oracle Cloud",
                "category": "Cloud Architecture",
                "certification_name": "OCI Architect Associate",
                "url": "https://mylearn.oracle.com/ou/learning-path/historical-path",
                "status": "Expired",
                "claim_steps": "Expired historical record.",
                "value_usd": 245,
                "is_historical_archive": True
            }
        ],
        "last_inspected": "2026-01-01T00:00:00Z"
    }

    test_file = tmp_path / "test_offers.json"
    test_file.write_text(json.dumps(test_offers_data, indent=2), encoding="utf-8")

    # Point DATA_FILE to tmp_path
    monkeypatch.setattr(insp, "DATA_FILE", test_file)

    # Mock inspect_url_with_retry to simulate successful verification without live network calls
    def mock_inspect(url, offer=None, max_retries=2):
        return "Active", "HTTP 200 OK (Mocked Invariant Test)", url, {
            "is_authentic_vendor": True,
            "authenticity_score": 100,
            "verdict": "VERIFIED_AUTHENTIC",
            "summary": "Mock Verified",
            "domain_verified": True,
            "ssl_verified": True,
            "redirect_secure": True,
            "corroboration_passed": True,
            "warning_flags": []
        }

    monkeypatch.setattr(insp, "inspect_url_with_retry", mock_inspect)

    # Run inspection in headless=False (HTTP gate) mode
    results = insp.run_inspection(use_headless=False)

    assert len(results) == 3, f"Expected 3 offers, got {len(results)}"

    # CRITICAL: Verify offer 1 was updated (would fail if update block was outside the loop)
    offer_1 = next(o for o in results if o["id"] == "test-offer-1")
    assert "verification_date" in offer_1, "Offer 1 was skipped! (Loop de-dent regression)"
    assert offer_1["inspection_notes"] == "HTTP 200 OK (Mocked Invariant Test)"
    assert offer_1["is_authentic_vendor"] is True

    # Verify offer 2 was also updated
    offer_2 = next(o for o in results if o["id"] == "test-offer-2")
    assert "verification_date" in offer_2, "Offer 2 was skipped!"
    assert offer_2["inspection_notes"] == "HTTP 200 OK (Mocked Invariant Test)"
    assert offer_2["is_authentic_vendor"] is True

    # Verify historical archive was preserved
    offer_3 = next(o for o in results if o["id"] == "hist-archive-3")
    assert offer_3["status"] == "Expired"
    assert offer_3["inspection_method"] == "Historical Archive Invariant"





