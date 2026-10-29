"""
Headless Playwright DOM Inspection & Dynamic Offer Verification Engine for CertPulse.

Capabilities:
1. Dynamic Single-Page App (SPA) DOM Rendering:
   Launches headless Chromium, navigates with resilient timeouts and tracker/media blocking,
   awaits DOM hydration, and captures client-rendered text and interactive elements.
2. Capacity & Cohort Saturation Invariant:
   Detects client-rendered alerts ("capacity has been reached", "cohort full", "seats no longer available", "waitlist active").
3. Expired Coupon & Promo Code Invariant:
   Detects dynamic checkout/coupon validation errors ("coupon has expired", "promo code invalid", "redemption limit reached").
4. Concluded Campaigns & Closed Registration Invariant:
   Detects JS-rendered banners ("registration closed", "campaign has concluded", "offer is over").
5. Redundant & Broken Redirection Invariant:
   Detects client-side SPA 404s, error routes, or silent bounces to generic portals.
6. Seamless Graceful Degradation:
   Falls back to standard HTTP multi-layer verification if browser automation is restricted or in offline environments.
"""

import re
import logging
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse
from typing import Dict, Any, List, Tuple, Optional

from src.authenticity import audit_offer_authenticity
from src.vlm_engine import evaluate_vlm_semantic_gate, VLMSemanticVerdict
from src.accessibility_scanner import scan_accessibility_elements, ActionabilityReport
from src.cart_emulator import assert_cart_balance, CartAssertionVerdict
from src.audit_ledger import record_audit_entry

logger = logging.getLogger("certpulse.dom_inspector")

# Specific heuristic phrases indicating capacity limits or full cohorts
CAPACITY_PATTERNS = [
    "capacity has been reached",
    "capacity reached",
    "cohort is full",
    "cohort full",
    "seats no longer available",
    "seats are full",
    "all seats have been filled",
    "all seats are filled",
    "waitlist active",
    "waitlist only",
    "join the waitlist",
    "joined the waitlist",
    "registration limit reached",
    "capacity has been filled",
    "maximum capacity reached",
    "maximum capacity",
    "maximum attendees reached",
    "session is full",
    "sessions are full",
    "no seats remaining",
    "no seats left",
    "sold out"
]

# Heuristic phrases indicating expired coupon / promo code / redemption limit
COUPON_EXPIRED_PATTERNS = [
    "coupon has expired",
    "coupon expired",
    "promo code invalid",
    "promo code has expired",
    "code is no longer valid",
    "redemption limit reached",
    "redemption limit has been reached",
    "discount no longer valid",
    "promotional code is no longer active",
    "voucher code expired",
    "voucher code is expired",
    "voucher is no longer valid",
    "voucher has expired",
    "promotion code invalid",
    "offer has expired",
    "promotion has ended",
    "discount code expired",
    "voucher code invalid",
    "redemption code has expired",
    "discount code is invalid",
    "invalid discount code",
    "coupon code is not valid",
    "promotion is no longer available"
]

# Heuristic phrases indicating registration is closed or campaign concluded
REGISTRATION_CLOSED_PATTERNS = [
    "has concluded",
    "closed new enrollments",
    "has closed new enrollments",
    "registration is closed",
    "registrations are closed",
    "registration has closed",
    "registration closed",
    "all vouchers have been claimed",
    "all vouchers are claimed",
    "vouchers are no longer available",
    "this promotion has ended",
    "promotion has ended",
    "this offer has expired",
    "the event has ended",
    "this event has ended",
    "event has concluded",
    "program is closed",
    "program has closed",
    "program concluded",
    "program has concluded",
    "program has ended",
    "no longer accepting submissions",
    "no longer accepting applications",
    "no longer accepting new enrollments",
    "enrollments are closed",
    "enrollment is closed",
    "campaign concluded",
    "campaign has concluded",
    "offer ended",
    "offer is over",
    "milestone achieved"
]

# Heuristic phrases indicating redundant or broken promotional links
REDUNDANT_LINK_PATTERNS = [
    "link is redundant",
    "redundant link",
    "this link is redundant",
    "this link is no longer active",
    "this link is no longer valid",
    "link is no longer active",
    "link is no longer valid",
    "this link has expired",
    "link has expired",
    "link expired",
    "link is broken",
    "link is inactive",
    "link is no longer available"
]

# Soft 404 & Dead-End Redirection Patterns
DEAD_END_PATTERNS = [
    "page not found",
    "error 404",
    "404 error",
    "404 - page not found",
    "not found",
    "couldn't find what you're looking for",
    "no longer exists",
    "requires registration/login or no longer exists",
    "we couldn't find that page",
    "page you're looking for doesn't exist",
    "the page has been removed",
    "this page is not available",
    "looks like this page doesn't exist",
    "requested url was not found",
    "sorry, we can't find that page",
    "access denied",
    "403 forbidden",
    "unauthorized"
] + REDUNDANT_LINK_PATTERNS

# Specific heuristic phrases indicating downtime or scheduled maintenance
MAINTENANCE_PATTERNS = [
    "down for maintenance",
    "website is currently down for maintenance",
    "our website is currently down",
    "our website is down",
    "site is currently down",
    "scheduled maintenance",
    "under scheduled maintenance",
    "performing scheduled maintenance",
    "system maintenance",
    "under maintenance",
    "maintenance window",
    "routine maintenance",
    "planned maintenance",
    "site maintenance",
    "service maintenance",
    "service is currently unavailable",
    "temporarily unavailable due to maintenance",
    "system is undergoing maintenance",
    "we'll be back shortly",
    "page is currently unavailable",
    "system downtime",
    "portal is currently unavailable",
    "maintenance in progress"
]

# Patterns detecting standard commercial checkout catalogs and exam fees lacking zero-dollar waivers
PAID_CATALOG_PATTERNS = [
    r"\$245(?:\.00)?\b",   # Oracle standard exam fee
    r"\$165(?:\.00)?\b",   # Microsoft standard associate fee
    r"\$150(?:\.00)?\b",   # AWS Associate exam fee
    r"\$300(?:\.00)?\b",   # AWS Professional / Cisco fee
    r"\$375(?:\.00)?\b",   # CKA / LFCS exam fee
    r"\$395(?:\.00)?\b",   # Linux Foundation standard catalog fee
    r"\$99(?:\.00)?\b",    # Fundamental cert standard price
    r"\badd to cart\b",
    r"\bbuy exam\b",
    r"\bpurchase exam\b",
    r"\benter credit card to purchase\b"
]

# Signals affirmatively proving a zero-dollar waiver or 100% discount
ZERO_DOLLAR_SIGNALS = [
    "100% discount",
    "100% off",
    "100% free",
    "$0.00",
    "0.00 usd",
    "zero-dollar",
    "zero cost",
    "fee waiver",
    "free voucher",
    "free exam voucher",
    "scholarship",
    "challenge voucher",
    "no cost",
    "complimentary voucher",
    "waiver code",
    "sponsored seat"
]

# Strict confirmed zero-dollar checkout signals required to override paid catalog pricing
CONFIRMED_ZERO_DOLLAR_CART = [
    "$0.00",
    "0.00 usd",
    "100% discount",
    "100% off",
    "fee waiver",
    "waiver code"
]

AFFIRMATIVE_OFFER_SIGNALS = [
    "free", "voucher", "scholarship", "challenge", "no cost",
    "waiver", "discount", "reward", "credits", "badge", "grant",
    "complimentary", "100%", "level up", "applied skills", "$0.00"
]

# Patterns indicating corporate enterprise marketing, sales-pitch, or lead-capture landing pages
MARKETING_LEAD_PATTERNS = [
    "speak to an ai expert",
    "speak to an expert",
    "talk to an expert",
    "speak to our experts",
    "speak to sales",
    "talk to sales",
    "contact sales",
    "connect with sales",
    "contact an expert",
    "request a demo",
    "request demo",
    "schedule a demo",
    "download whitepaper",
    "download datasheet",
    "idc marketscape",
    "gartner magic quadrant",
    "forrester wave",
    "see what analysts are saying",
    "contact us for enterprise pricing",
    "book a sales meeting"
]

# Signals indicating genuine actionable educational or certification fulfillment
ACTIONABLE_FULFILLMENT_SIGNALS = [
    "enroll",
    "enroll in path",
    "enroll for free",
    "start course",
    "start learning",
    "schedule exam",
    "schedule free exam",
    "book exam",
    "take assessment",
    "start assessment",
    "claim voucher",
    "apply voucher",
    "register for exam",
    "start lab",
    "launch lab",
    "take exam",
    "begin course",
    "view learning path",
    "mylearn",
    "course curriculum",
    "learning path",
    "exam details"
]

# Chromium launch arguments optimized for sandboxed headless execution
PLAYWRIGHT_LAUNCH_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-gpu",
    "--disable-dev-shm-usage",
    "--dns-result-order=ipv4first",
    "--no-first-run",
    "--no-zygote"
]

# Allow images and webfonts so screenshots render faithfully; block only heavy audio/video media
BLOCKED_RESOURCE_TYPES = {"media"}

BLOCKED_URL_REGEX = re.compile(
    r"(analytics|googletagmanager|hotjar|segment|telemetry|doubleclick|clarity\.ms|facebook\.net|adservice)",
    re.IGNORECASE
)


def inspect_rendered_dom(
    rendered_text: str,
    rendered_title: str = "",
    final_url: str = "",
    original_url: str = "",
    interactive_elements: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Analyzes dynamically rendered DOM text, page title, and URL navigation
    against five invariant categories:
    1. Capacity Limits / Cohort Saturation
    2. Expired Coupon / Promo Code
    3. Closed Registration / Campaign Concluded
    4. Soft 404 / Dead-End Redirection / Redundant Links
    5. Silent Reroute Detection
    """
    clean_text = rendered_text.lower()
    title_text = rendered_title.lower()
    combined_content = f"{title_text} {clean_text}"

    result = {
        "status": "Active",
        "reason": "DOM verified: Active opportunity rendered with valid credentials signals",
        "final_url": final_url or original_url,
        "is_capacity_reached": False,
        "is_coupon_expired": False,
        "is_campaign_closed": False,
        "is_dead_end": False,
        "is_redundant_link": False,
        "is_maintenance": False,
        "maintenance_detected": False,
        "is_paid_catalog": False,
        "paid_catalog_detected": False,
        "zero_dollar_confirmed": True,
        "matched_phrase": None,
        "category": "active"
    }

    # Empty text guard
    if not clean_text.strip():
        result["status"] = "Review Needed"
        result["reason"] = "DOM Render Invariant: Empty rendered DOM or failed client-side hydration"
        result["zero_dollar_confirmed"] = False
        result["category"] = "empty_dom"
        return result

    # 0. Maintenance & Downtime Detection Invariant (Evaluated first to take precedence)
    for pat in MAINTENANCE_PATTERNS:
        if pat in combined_content:
            result["status"] = "Review Needed"
            result["reason"] = f"Maintenance Invariant: Portal currently down for maintenance ('{pat}')"
            result["is_maintenance"] = True
            result["maintenance_detected"] = True
            result["zero_dollar_confirmed"] = False
            result["matched_phrase"] = pat
            result["category"] = "maintenance"
            return result

    # 1. Soft 404 / Redundant Link / Dead-end Detection
    for pat in DEAD_END_PATTERNS:
        if pat in combined_content:
            is_redundant = any(rw in pat for rw in ["redundant", "link"])
            result["status"] = "Broken Link"
            result["reason"] = (
                f"DOM Redundant Link Invariant: Detected redundant or defunct link ('{pat}')"
                if is_redundant
                else f"DOM Dead-End: Detected soft-404 or access barrier in rendered DOM ('{pat}')"
            )
            result["is_dead_end"] = True
            result["is_redundant_link"] = is_redundant
            result["zero_dollar_confirmed"] = False
            result["matched_phrase"] = pat
            result["category"] = "redundant_link" if is_redundant else "dead_end"
            return result

    # 2. Capacity Reached / Cohort Full
    for pat in CAPACITY_PATTERNS:
        if pat in combined_content:
            result["status"] = "Registrations Closed"
            result["reason"] = f"Capacity Invariant: Cohort capacity limit reached ('{pat}')"
            result["is_capacity_reached"] = True
            result["zero_dollar_confirmed"] = False
            result["matched_phrase"] = pat
            result["category"] = "capacity_reached"
            return result

    # 3. Expired Coupon / Promo Code
    for pat in COUPON_EXPIRED_PATTERNS:
        if pat in combined_content:
            result["status"] = "Expired"
            result["reason"] = f"Coupon Invariant: Promo code expired or redemption limit hit ('{pat}')"
            result["is_coupon_expired"] = True
            result["zero_dollar_confirmed"] = False
            result["matched_phrase"] = pat
            result["category"] = "coupon_expired"
            return result

    # 4. Closed Registration / Campaign Concluded
    for pat in REGISTRATION_CLOSED_PATTERNS:
        if pat in combined_content:
            result["status"] = "Registrations Closed"
            result["reason"] = f"Closure Invariant: Campaign concluded or registrations closed ('{pat}')"
            result["is_campaign_closed"] = True
            result["zero_dollar_confirmed"] = False
            result["matched_phrase"] = pat
            result["category"] = "campaign_closed"
            return result

    # 5. Silent Reroute Detection in SPA Client Routing
    if original_url and final_url:
        orig_parsed = urlparse(original_url)
        final_parsed = urlparse(final_url)
        orig_parts = [p for p in orig_parsed.path.split('/') if p]
        final_parts = [p for p in final_parsed.path.split('/') if p]
        if len(orig_parts) >= 2 and len(final_parts) <= 1:
            if any(kw in original_url.lower() for kw in ["promo", "challenge", "voucher", "free", "lift"]):
                result["status"] = "Registrations Closed"
                result["reason"] = f"Silent Reroute: Navigated from deep promo to root ({final_url})"
                result["zero_dollar_confirmed"] = False
                result["matched_phrase"] = "silent_reroute_to_root"
                result["category"] = "silent_reroute"
                return result

    # 5b. Marketing Funnel & Sales Lead Trap Invariant
    has_marketing_lead = any(pat in combined_content for pat in MARKETING_LEAD_PATTERNS)
    if has_marketing_lead:
        has_actionable = any(sig in combined_content for sig in ACTIONABLE_FULFILLMENT_SIGNALS)
        if interactive_elements:
            has_actionable = has_actionable or any(
                any(sig in el for sig in ACTIONABLE_FULFILLMENT_SIGNALS) for el in interactive_elements
            )
        if not has_actionable:
            matched_pat = next(pat for pat in MARKETING_LEAD_PATTERNS if pat in combined_content)
            result["status"] = "Review Needed"
            result["reason"] = f"Marketing Funnel Invariant: Page is a corporate marketing/sales lead portal ('{matched_pat}') without actionable course enrollment or exam scheduling CTAs"
            result["is_marketing_lead"] = True
            result["marketing_lead_detected"] = True
            result["zero_dollar_confirmed"] = False
            result["matched_phrase"] = matched_pat
            result["category"] = "marketing_lead"
            return result

    # 5c. Paid Catalog & Standard Fee Barrier Invariant (Evaluated before generic affirmative signals)
    has_paid_terms = any(re.search(pat, combined_content) for pat in PAID_CATALOG_PATTERNS)
    has_confirmed_zero = any(sig in combined_content for sig in CONFIRMED_ZERO_DOLLAR_CART)
    if has_paid_terms and not has_confirmed_zero:
        result["status"] = "Review Needed"
        result["reason"] = "Catalog Pricing Invariant: Detected standard paid catalog / cart pricing ($245/checkout) without affirmative zero-dollar waiver terms"
        result["is_paid_catalog"] = True
        result["paid_catalog_detected"] = True
        result["zero_dollar_confirmed"] = False
        result["category"] = "paid_catalog"
        return result

    # 6. Check for affirmative signals in rendered text
    has_signals = any(sig in combined_content for sig in AFFIRMATIVE_OFFER_SIGNALS)
    if not has_signals:
        result["status"] = "Review Needed"
        result["reason"] = "DOM Catalog Check: No active free voucher or waiver signal found in rendered DOM"
        result["zero_dollar_confirmed"] = False
        result["category"] = "no_offer_signal"
        return result

    result["zero_dollar_confirmed"] = True
    return result


def evaluate_dual_gate(
    dom_status: str,
    has_zero_dollar: bool,
    screenshot_valid: bool,
    auth_score: int = 95,
    http_status: int = 200,
    vlm_verdict: Optional[Any] = None
) -> Tuple[str, str]:
    """
    Evaluates the dual visual ground-truth gate:
    An offer is Active iff G_DOM (affirmative zero-dollar terms, no maintenance, no paid catalog)
    AND G_Visual (screenshot exists and valid >= 4KB PNG) AND AuthScore >= 80
    AND VLM Semantic Gate (registration open, zero-dollar waiver, no copay, visual confidence >= 0.60).
    """
    if dom_status != "Active":
        return dom_status, "DOM failed affirmative check"
    if not has_zero_dollar:
        return "Review Needed", "DOM failed affirmative check: missing affirmative zero-dollar waiver"
    if auth_score < 80:
        return "Review Needed", f"Authenticity score below threshold ({auth_score}/100)"
    if not screenshot_valid:
        return "Review Needed", "Visual Proof Gate Invariant: DOM confirmed offer, but visual screenshot proof is missing or invalid"

    if vlm_verdict is not None:
        if isinstance(vlm_verdict, dict):
            reg_status = vlm_verdict.get("registration_status", "open")
            req_copay = vlm_verdict.get("requires_payment_or_copay", False)
            copay_usd = vlm_verdict.get("copay_amount_usd", 0.0)
            has_waiver = vlm_verdict.get("has_zero_dollar_waiver", True)
            conf = vlm_verdict.get("visual_confidence_score", 1.0)
            evidence = vlm_verdict.get("primary_evidence", "")
        else:
            reg_status = getattr(vlm_verdict, "registration_status", "open")
            req_copay = getattr(vlm_verdict, "requires_payment_or_copay", False)
            copay_usd = getattr(vlm_verdict, "copay_amount_usd", 0.0)
            has_waiver = getattr(vlm_verdict, "has_zero_dollar_waiver", True)
            conf = getattr(vlm_verdict, "visual_confidence_score", 1.0)
            evidence = getattr(vlm_verdict, "primary_evidence", "") or ""

        if reg_status in ["closed", "cohort_full", "waitlist"]:
            return "Registrations Closed", f"VLM Semantic Gate: {evidence or 'Registration concluded, cohort full, or waitlist active'}"
        if req_copay:
            copay_msg = f" (${copay_usd:.2f} USD)" if copay_usd > 0.0 else ""
            return "Review Needed", f"VLM Semantic Gate: Copay or fee required{copay_msg}"
        if not has_waiver:
            return "Review Needed", f"VLM Semantic Gate: {evidence or 'No affirmative zero-dollar waiver'}"
        if conf < 0.60:
            return "Review Needed", f"VLM Semantic Gate: Low visual confidence ({conf:.2f} < 0.60)"

    return "Active", f"Playwright DOM Verified: HTTP {http_status} OK, active campaign validated with visual screenshot proof"


class HeadlessDOMInspector:
    """
    Persistent Headless Chromium Inspector.
    Shares a single browser process across multiple inspections for sub-second execution,
    spins up isolated BrowserContext instances, blocks heavy assets and trackers,
    captures hero viewport screenshots, and extracts rendered client-side DOM.
    """

    def __init__(self, headless: bool = True, timeout_ms: int = 15000):
        self.headless = headless
        self.timeout_ms = timeout_ms
        self._playwright = None
        self._browser = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def start(self):
        try:
            from playwright.sync_api import sync_playwright
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=self.headless,
                args=PLAYWRIGHT_LAUNCH_ARGS
            )
            logger.info("Headless Chromium DOM Inspector initialized successfully.")
        except Exception as e:
            logger.warning(f"Could not initialize Playwright Chromium: {e}. Fallback to HTTP inspection active.")
            self._browser = None

    def close(self):
        if self._browser:
            try:
                self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._playwright:
            try:
                self._playwright.stop()
            except Exception:
                pass
            self._playwright = None

    @property
    def is_available(self) -> bool:
        return self._browser is not None

    def capture_screenshot(
        self,
        page,
        offer_id: str,
        old_status: str = "Active",
        new_status: str = "Active",
        **kwargs: Any,
    ) -> Tuple[bool, str]:
        """
        Captures 1280x800 hero viewport screenshot into docs/screenshots/<offer_id>.png.
        Performs perceptual hash delta-skipping (< 5% delta and status unchanged) to avoid
        redundant disk writes.
        Asserts PNG magic bytes and minimum file size >= 4096 bytes.
        """
        if not offer_id:
            return False, ""
        screenshots_dir = Path(__file__).resolve().parent.parent / "docs" / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        target_path = screenshots_dir / f"{offer_id}.png"
        rel_path = f"docs/screenshots/{offer_id}.png"

        temp_path = target_path.with_suffix(".tmp.png")
        try:
            # Check for SPA hydration: wait for content rendering if body text is sparse
            try:
                text_len = len(page.evaluate("() => document.body ? document.body.innerText.trim() : ''"))
                if text_len < 100:
                    page.wait_for_timeout(2000)
            except Exception:
                pass

            screenshot_bytes = page.screenshot(path=str(temp_path), full_page=False)
            if (not screenshot_bytes or not isinstance(screenshot_bytes, bytes)) and temp_path.exists():
                screenshot_bytes = temp_path.read_bytes()

            if temp_path.exists() and temp_path.stat().st_size >= 4096:
                header = temp_path.read_bytes()[:8]
                if header == b"\x89PNG\r\n\x1a\n":
                    new_size = temp_path.stat().st_size
                    from src.visual_hasher import is_blank_or_invalid_screenshot, should_skip_screenshot_write
                    # Anti-blank & anti-spinner protection: never overwrite an existing rich screenshot
                    # with a blank, unhydrated, or tiny loading spinner capture
                    if target_path.exists() and not is_blank_or_invalid_screenshot(target_path):
                        if is_blank_or_invalid_screenshot(temp_path) or (target_path.stat().st_size >= 30000 and new_size < 18000):
                            logger.info(f"Preserving existing substantive screenshot for {offer_id} ({target_path.stat().st_size} bytes vs {new_size} bytes / blank={is_blank_or_invalid_screenshot(temp_path)})")
                            try:
                                temp_path.unlink()
                            except Exception:
                                pass
                            return True, rel_path

                    # Check perceptual hash delta skipping
                    should_skip, delta, dist = should_skip_screenshot_write(
                        screenshot_bytes or temp_path, target_path, old_status, new_status
                    )
                    if should_skip:
                        logger.info(
                            f"[SKIP] Visual diff < 5% (delta={delta:.4f}, hamming={dist}) and status unchanged. "
                            f"Skipped write for {target_path}."
                        )
                        try:
                            temp_path.unlink()
                        except Exception:
                            pass
                        return True, rel_path

                    temp_path.replace(target_path)
                    return True, rel_path
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass
            # If target already exists and is valid, preserve it
            if target_path.exists() and target_path.stat().st_size >= 4096:
                header = target_path.read_bytes()[:8]
                if header == b"\x89PNG\r\n\x1a\n":
                    return True, rel_path
            return False, rel_path
        except Exception as e:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass
            logger.warning(f"Failed to capture screenshot for {offer_id}: {e}")
            if target_path.exists() and target_path.stat().st_size >= 4096:
                return True, rel_path
            return False, rel_path

    def inspect_url(
        self,
        url: str,
        offer: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str, str, Dict[str, Any]]:
        """
        Navigates to URL in an isolated context, awaits DOM hydration,
        captures visual screenshot proof, analyzes rendered DOM invariants,
        and enforces the dual visual ground-truth gate.
        Returns: (status, reason, final_canonical_url, auth_result)
        """
        if offer is None:
            offer = {"url": url}
        else:
            offer["url"] = url

        # 1. Pre-inspection authenticity gate
        is_local_file = url.startswith("file://")
        if not is_local_file:
            pre_auth = audit_offer_authenticity(offer)
            if pre_auth.get("verdict") in ["DECEPTIVE_SCAM", "SUSPICIOUS_UNTRUSTED"]:
                return "Review Needed", f"Security Alert: Domain authenticity failed ({pre_auth['summary']})", url, pre_auth
        else:
            pre_auth = {
                "is_authentic_vendor": True,
                "authenticity_score": 100,
                "verdict": "VERIFIED_AUTHENTIC",
                "summary": "Local File Fixture Validated",
                "domain_verified": True,
                "ssl_verified": True,
                "redirect_secure": True,
                "corroboration_passed": True
            }

        if not self._browser:
            from src.inspector import inspect_url_with_retry
            return inspect_url_with_retry(url, offer=offer)

        context = None
        offer_id = offer.get("id", "")
        screenshots_dir = Path(__file__).resolve().parent.parent / "docs" / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        screenshot_ok = False
        screenshot_path = f"docs/screenshots/{offer_id}.png" if offer_id else ""

        try:
            context = self._browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            page = context.new_page()

            # Route blocking: abort analytics trackers and heavy media
            def handle_route(route):
                try:
                    req = route.request
                    if req.resource_type in BLOCKED_RESOURCE_TYPES or BLOCKED_URL_REGEX.search(req.url):
                        route.abort()
                    else:
                        route.continue_()
                except Exception:
                    pass

            page.route("**/*", handle_route)

            # Adaptive Verification: Resolve dual-phase targets (prioritizing deep claim URL for syllabus proof)
            from src.adaptive_verifier import (
                resolve_dual_phase_targets,
                classify_platform_cluster,
                get_pre_navigation_storage,
                audit_redirect_degradation,
                calculate_proof_quality_score,
            )
            dual_targets = resolve_dual_phase_targets(offer)
            cluster_prof = classify_platform_cluster(offer.get("platform", ""), url)
            nav_target = dual_targets.primary_nav_target
            redirect_chain = [nav_target]

            # Pre-inject cookie consent storage tokens to bypass OneTrust / TrustArc / Cookiebot in < 50ms
            if not is_local_file:
                storage_preset = get_pre_navigation_storage(nav_target)
                if storage_preset.get("local_storage"):
                    try:
                        storage_items = [
                            f"window.localStorage.setItem({repr(k)}, {repr(v)});"
                            for k, v in storage_preset["local_storage"].items()
                        ]
                        page.add_init_script("\n".join(storage_items))
                    except Exception:
                        pass
            rendered_title = ""
            rendered_text = ""
            final_url = nav_target
            http_status = 200

            if not is_local_file:
                try:
                    response = page.goto(nav_target, wait_until="domcontentloaded", timeout=self.timeout_ms)
                    http_status = response.status if response else 200
                    final_url = page.url
                    if final_url != url:
                        redirect_chain.append(final_url)

                    # Audit redirect degradation to catch silent 302 bounces to generic homepages
                    is_degraded, deg_reason, url_score = audit_redirect_degradation(nav_target, final_url)
                    if is_degraded:
                        logger.warning(f"Redirect degradation detected for {offer_id}: {deg_reason}")

                    try:
                        page.wait_for_load_state(cluster_prof.wait_condition, timeout=2500)
                    except Exception:
                        pass
                    rendered_title = page.title() or ""
                    rendered_text = page.evaluate("() => document.body ? document.body.innerText : ''")
                except Exception as nav_err:
                    logger.info(f"Playwright direct navigation failed for {url} ({nav_err}). Attempting HTTPX fallback...")
                    import httpx
                    try:
                        from src.inspector import BROWSER_HEADERS
                        with httpx.Client(headers=BROWSER_HEADERS, timeout=12.0, follow_redirects=True) as client:
                            resp = client.get(url)
                            http_status = resp.status_code
                            final_url = str(resp.url)
                            if final_url != url:
                                redirect_chain.append(final_url)
                            page.set_content(resp.text, wait_until="domcontentloaded")
                            try:
                                page.wait_for_load_state("networkidle", timeout=1500)
                            except Exception:
                                pass
                            rendered_title = page.title() or ""
                            rendered_text = page.evaluate("() => document.body ? document.body.innerText : ''")
                    except Exception as fb_err:
                        logger.warning(f"Both direct navigation and HTTPX fallback failed for {url}: {fb_err}")
                        rendered_title = ""
                        rendered_text = ""
                        final_url = url
                        http_status = 500
            else:
                response = page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)
                http_status = response.status if response else 200
                final_url = page.url
                try:
                    page.wait_for_load_state("networkidle", timeout=2500)
                except Exception:
                    pass
                rendered_title = page.title() or ""
                rendered_text = page.evaluate("() => document.body ? document.body.innerText : ''")

            # Capture visual screenshot proof
            if offer_id:
                old_st = offer.get("status", "Active") if offer else "Active"
                try:
                    screenshot_ok, screenshot_path = self.capture_screenshot(
                        page, offer_id, old_status=old_st, new_status=old_st
                    )
                except TypeError:
                    screenshot_ok, screenshot_path = self.capture_screenshot(page, offer_id)

            # Extract interactive elements for semantic CTA inspection
            interactive_ctas = []
            try:
                interactive_ctas = page.evaluate("""() => {
                    const ctas = [];
                    document.querySelectorAll('button, a, [role="button"], input[type="submit"]').forEach(el => {
                        const txt = (el.innerText || el.textContent || el.value || '').trim().toLowerCase();
                        if (txt.length > 2 && txt.length < 80) ctas.push(txt);
                    });
                    return ctas;
                }""")
            except Exception:
                interactive_ctas = []

            # Run Semantic Accessibility Scanner
            actionability_report = scan_accessibility_elements(
                interactive_elements=interactive_ctas,
                page_text=rendered_text,
                page_title=rendered_title
            )

            # Run Synthetic Cart Balance Assertion
            cart_verdict = assert_cart_balance(offer)

            # Analyze rendered DOM
            dom_eval = inspect_rendered_dom(
                rendered_text=rendered_text,
                rendered_title=rendered_title,
                final_url=final_url,
                original_url=url,
                interactive_elements=interactive_ctas
            )

            # Read screenshot bytes for VLM analysis
            screenshot_bytes = None
            if screenshot_ok and screenshot_path:
                target_file = screenshots_dir / f"{offer_id}.png"
                if target_file.exists():
                    try:
                        screenshot_bytes = target_file.read_bytes()
                    except Exception:
                        screenshot_bytes = None

            # Execute Tier 3 Multimodal VLM Semantic Gate
            vlm_verdict = evaluate_vlm_semantic_gate(
                offer_id=offer_id,
                url=final_url or url,
                dom_text=rendered_text,
                dom_title=rendered_title,
                screenshot_path=screenshot_path if screenshot_ok else None,
                screenshot_bytes=screenshot_bytes,
                platform=offer.get("platform", "") if offer else "",
                offer_data=offer
            )

            # Authenticity verification on rendered DOM
            if not is_local_file:
                auth_result = audit_offer_authenticity(
                    offer=offer,
                    body_text=rendered_text,
                    redirect_chain=redirect_chain
                )
            else:
                auth_result = pre_auth

            auth_score = auth_result.get("authenticity_score", 90)

            # Check HTTP status codes
            if http_status in [404, 410]:
                status = "Broken Link"
                reason = f"HTTP {http_status} Page Not Found"
            elif http_status >= 500:
                status = "Server Error"
                reason = f"HTTP {http_status} Host Down"
            elif http_status == 429:
                status = "Review Needed"
                reason = f"Rate Limit Invariant: HTTP {http_status} Too Many Requests / Bot Protection"
            elif http_status in [401, 403]:
                # 401/403 restricted gateway: never blind active!
                if dom_eval["status"] != "Active":
                    status = dom_eval["status"]
                    reason = dom_eval["reason"]
                else:
                    status = "Review Needed"
                    reason = f"Restricted Gateway: HTTP {http_status} encountered without verified promotional terms"
            else:
                status = dom_eval["status"]
                reason = dom_eval["reason"]

            # Dual Visual Ground-Truth Gate:
            # An offer is Active iff G_DOM (affirmative $0 terms, no maintenance, no paid catalog)
            # AND G_Visual (screenshot exists and valid >= 4KB PNG) AND AuthScore >= 80
            # AND VLM Semantic Gate (registration open, zero dollar waiver, no copay, confidence >= 0.60).
            maintenance_detected = dom_eval.get("maintenance_detected", False)
            paid_catalog_detected = dom_eval.get("paid_catalog_detected", False)
            zero_dollar_confirmed = dom_eval.get("zero_dollar_confirmed", True)

            # Actionability & Cart Balance Invariant Gates
            if status == "Active" and actionability_report.verdict == "MARKETING_LEAD_FUNNEL":
                status = "Review Needed"
                reason = actionability_report.reason
                zero_dollar_confirmed = False

            if status == "Active" and cart_verdict.is_copay_required and cart_verdict.copay_amount_usd > 0.0:
                status = "Review Needed"
                reason = f"Cart Assertion: Copay Required (${cart_verdict.copay_amount_usd:.2f}) - {cart_verdict.reason}"
                paid_catalog_detected = True
                zero_dollar_confirmed = False

            if status == "Active":
                if not auth_result.get("is_authentic_vendor", True) or auth_score < 80:
                    status = "Review Needed"
                    reason = f"Authenticity Check Failed: {auth_result.get('summary', 'Score below threshold')}"
                elif not zero_dollar_confirmed or maintenance_detected or paid_catalog_detected:
                    status = "Review Needed"
                    reason = dom_eval.get("reason", "DOM failed zero-dollar confirmation")
                elif not screenshot_ok:
                    status = "Review Needed"
                    reason = "Visual Proof Gate Invariant: DOM confirmed offer, but visual screenshot proof is missing or invalid"
                elif vlm_verdict.registration_status in ["closed", "cohort_full"]:
                    status = "Registrations Closed"
                    reason = f"VLM Semantic Gate: {vlm_verdict.primary_evidence}"
                    zero_dollar_confirmed = False
                elif vlm_verdict.requires_payment_or_copay and vlm_verdict.copay_amount_usd > 0.0:
                    status = "Review Needed"
                    reason = f"VLM Semantic Gate: Copay required (${vlm_verdict.copay_amount_usd:.2f} USD)"
                    paid_catalog_detected = True
                    zero_dollar_confirmed = False
                elif not vlm_verdict.has_zero_dollar_waiver:
                    status = "Review Needed"
                    reason = f"VLM Semantic Gate: {vlm_verdict.primary_evidence}"
                    zero_dollar_confirmed = False
                elif vlm_verdict.visual_confidence_score < 0.60:
                    status = "Review Needed"
                    reason = f"VLM Semantic Gate: Low visual confidence ({vlm_verdict.visual_confidence_score:.2f} < 0.60)"
                else:
                    reason = f"Playwright DOM Verified: HTTP {http_status} OK, active campaign validated with visual screenshot proof"

            # Enforce ground-truth invariant: non-active offers never confirm zero-dollar terms
            if status != "Active":
                zero_dollar_confirmed = False

            # If status transitioned away from initial status, refresh screenshot write
            if offer_id and status != old_st:
                try:
                    self.capture_screenshot(page, offer_id, old_status=old_st, new_status=status)
                except Exception:
                    pass

            # Populate visual_proof metadata on offer
            if offer is not None:
                target_file = screenshots_dir / f"{offer_id}.png" if offer_id else None
                if status == "Active" and screenshot_ok:
                    proof_status = "verified"
                elif status in ["Broken Link", "Server Error"]:
                    proof_status = "failed"
                elif not screenshot_ok or not target_file or not target_file.exists():
                    proof_status = "missing"
                else:
                    proof_status = "placeholder"

                pqs_res = calculate_proof_quality_score(
                    url_score=url_score if 'url_score' in locals() else 100.0,
                    dom_score=100.0 if status == "Active" else 50.0,
                    visual_score=100.0 if screenshot_ok else 50.0,
                    corroboration_score=100.0 if auth_result.get("corroboration_passed") else 50.0
                )
                offer["adaptive_verification"] = {
                    "cluster": cluster_prof.code if 'cluster_prof' in locals() else "ENTERPRISE_LMS",
                    "pqs_score": pqs_res.score,
                    "pqs_tier": pqs_res.tier,
                    "dual_phase_divergence": dual_targets.is_divergent if 'dual_targets' in locals() else False,
                }

                offer["visual_proof"] = {
                    "screenshot_path": screenshot_path,
                    "screenshot_url": screenshot_path,
                    "captured_at": datetime.now(timezone.utc).isoformat(),
                    "status": proof_status,
                    "zero_dollar_confirmed": zero_dollar_confirmed,
                    "maintenance_detected": maintenance_detected,
                    "paid_catalog_detected": paid_catalog_detected,
                    "vlm_verdict": vlm_verdict.model_dump() if vlm_verdict else None,
                    "visual_confidence_score": vlm_verdict.visual_confidence_score if vlm_verdict else None,
                    "badge_phash_matched": vlm_verdict.badge_phash_matched if vlm_verdict else False,
                    "ocr_text_snippet": vlm_verdict.ocr_text_snippet if vlm_verdict else None,
                }
                if offer_id:
                    offer["screenshot_path"] = screenshot_path

            # Record Cryptographic Audit Receipt
            if offer_id:
                try:
                    record_audit_entry(
                        offer_id=offer_id,
                        url=final_url,
                        dom_text=rendered_text,
                        screenshot_path=screenshot_path if screenshot_ok else None,
                        status=status,
                        actionability_verdict=actionability_report.verdict,
                        cart_balance_verified=cart_verdict.cart_balance_str
                    )
                except Exception as audit_err:
                    logger.debug(f"Audit log recording error for {offer_id}: {audit_err}")

            return status, reason, final_url, auth_result

        except Exception as e:
            logger.warning(f"Playwright navigation error for {url}: {e}. Falling back to HTTP inspection.")
            from src.inspector import inspect_url_with_retry
            return inspect_url_with_retry(url, offer=offer)

        finally:
            if context:
                try:
                    context.close()
                except Exception:
                    pass


def inspect_url_with_playwright(
    url: str,
    offer: Optional[Dict[str, Any]] = None,
    timeout_ms: int = 15000
) -> Tuple[str, str, str, Dict[str, Any]]:
    """
    Convenience one-shot inspection function utilizing headless Playwright.
    Launches a dedicated inspector instance and safely evaluates the target URL.
    """
    with HeadlessDOMInspector(headless=True, timeout_ms=timeout_ms) as inspector:
        return inspector.inspect_url(url, offer=offer)


# Class alias for DOMInspector
DOMInspector = HeadlessDOMInspector

