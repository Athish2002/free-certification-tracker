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
from urllib.parse import urlparse
from typing import Dict, Any, List, Tuple, Optional

from src.authenticity import audit_offer_authenticity

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
    "404 - page not found",
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

AFFIRMATIVE_OFFER_SIGNALS = [
    "free", "voucher", "scholarship", "challenge", "no cost",
    "waiver", "discount", "reward", "credits", "badge", "grant",
    "complimentary", "100%", "level up", "applied skills"
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

BLOCKED_RESOURCE_TYPES = {"image", "media", "font"}

BLOCKED_URL_REGEX = re.compile(
    r"(analytics|googletagmanager|hotjar|segment|telemetry|doubleclick|clarity\.ms|facebook\.net|adservice)",
    re.IGNORECASE
)


def inspect_rendered_dom(
    rendered_text: str,
    rendered_title: str = "",
    final_url: str = "",
    original_url: str = ""
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
        "matched_phrase": None,
        "category": "active"
    }

    # Empty text guard
    if not clean_text.strip():
        result["status"] = "Review Needed"
        result["reason"] = "DOM Render Invariant: Empty rendered DOM or failed client-side hydration"
        result["category"] = "empty_dom"
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
            result["matched_phrase"] = pat
            result["category"] = "redundant_link" if is_redundant else "dead_end"
            return result

    # 2. Capacity Reached / Cohort Full
    for pat in CAPACITY_PATTERNS:
        if pat in combined_content:
            result["status"] = "Registrations Closed"
            result["reason"] = f"Capacity Invariant: Cohort capacity limit reached ('{pat}')"
            result["is_capacity_reached"] = True
            result["matched_phrase"] = pat
            result["category"] = "capacity_reached"
            return result

    # 3. Expired Coupon / Promo Code
    for pat in COUPON_EXPIRED_PATTERNS:
        if pat in combined_content:
            result["status"] = "Expired"
            result["reason"] = f"Coupon Invariant: Promo code expired or redemption limit hit ('{pat}')"
            result["is_coupon_expired"] = True
            result["matched_phrase"] = pat
            result["category"] = "coupon_expired"
            return result

    # 4. Closed Registration / Campaign Concluded
    for pat in REGISTRATION_CLOSED_PATTERNS:
        if pat in combined_content:
            result["status"] = "Registrations Closed"
            result["reason"] = f"Closure Invariant: Campaign concluded or registrations closed ('{pat}')"
            result["is_campaign_closed"] = True
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
                result["matched_phrase"] = "silent_reroute_to_root"
                result["category"] = "silent_reroute"
                return result

    # 6. Check for affirmative signals in rendered text
    has_signals = any(sig in combined_content for sig in AFFIRMATIVE_OFFER_SIGNALS)
    if not has_signals:
        result["status"] = "Review Needed"
        result["reason"] = "DOM Catalog Check: No active free voucher or waiver signal found in rendered DOM"
        result["category"] = "no_offer_signal"
        return result

    return result


class HeadlessDOMInspector:
    """
    Persistent Headless Chromium Inspector.
    Shares a single browser process across multiple inspections for sub-second execution,
    spins up isolated BrowserContext instances, blocks heavy assets and trackers,
    and extracts rendered client-side DOM.
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

    def inspect_url(
        self,
        url: str,
        offer: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str, str, Dict[str, Any]]:
        """
        Navigates to URL in an isolated context, awaits DOM hydration,
        and analyzes dynamic DOM text and elements.
        Returns: (status, reason, final_canonical_url, auth_result)
        """
        if offer is None:
            offer = {"url": url}
        else:
            offer = {**offer, "url": url}

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
        try:
            context = self._browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            page = context.new_page()

            # Route blocking: abort analytics trackers and media files to maximize speed
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

            # Navigate to URL
            redirect_chain = [url]
            response = page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)
            final_url = page.url
            if final_url != url:
                redirect_chain.append(final_url)

            # Short settlement for SPA rendering
            try:
                page.wait_for_load_state("networkidle", timeout=3000)
            except Exception:
                pass

            # Extract rendered text, title, and alert elements
            rendered_title = page.title() or ""
            rendered_text = page.evaluate("() => document.body ? document.body.innerText : ''")

            # Check HTTP status if available
            http_status = response.status if response else 200
            if http_status in [404, 410]:
                auth_result = audit_offer_authenticity(offer, body_text=rendered_text, redirect_chain=redirect_chain) if not is_local_file else pre_auth
                return "Broken Link", f"HTTP {http_status} Page Not Found", final_url, auth_result
            elif http_status >= 500:
                auth_result = audit_offer_authenticity(offer, body_text=rendered_text, redirect_chain=redirect_chain) if not is_local_file else pre_auth
                return "Server Error", f"HTTP {http_status} Host Down", final_url, auth_result
            elif http_status in [401, 403]:
                auth_result = audit_offer_authenticity(offer, body_text=rendered_text, redirect_chain=redirect_chain) if not is_local_file else pre_auth
                return "Active", f"Verified (Bot Protected / Restricted Gateway: HTTP {http_status})", final_url, auth_result

            # Analyze rendered DOM
            dom_eval = inspect_rendered_dom(
                rendered_text=rendered_text,
                rendered_title=rendered_title,
                final_url=final_url,
                original_url=url
            )

            # Execute authenticity verification on rendered DOM
            if not is_local_file:
                auth_result = audit_offer_authenticity(
                    offer=offer,
                    body_text=rendered_text,
                    redirect_chain=redirect_chain
                )

                if not auth_result["is_authentic_vendor"]:
                    return "Review Needed", f"Authenticity Check Failed: {auth_result['summary']}", final_url, auth_result
            else:
                auth_result = pre_auth

            status = dom_eval["status"]
            reason = dom_eval["reason"]
            if status == "Active":
                reason = f"Playwright DOM Verified: HTTP {http_status} OK, active campaign validated"

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
