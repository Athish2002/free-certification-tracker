"""
Self-Healing Site Inspector & Authenticity Verification Engine for CertPulse.

Capabilities:
1. Hard errors: HTTP 404, 410, 500.
2. Soft closure detection: Text indicating "Registration Closed", "Vouchers Claimed", "Ended".
3. Silent Reroute Detection: Catches campaigns redirected to generic root/catalog homepages.
4. Normal Site Detection: Flags paid certification catalogs without any free/waiver offers.
5. Multi-Layer Authenticity Gate: Strict domain verification, redirect chain auditing, TLS enforcement, and content corroboration.
6. Canonical Self-Healing: Automatically updates URLs when permanent redirects occur.
7. State Self-Healing: Automatically restores offers to 'Active' when portals re-open.
8. Atomic Persistence: Safely writes database to prevent corruption during unexpected crashes.
"""

import re
import time
import httpx
import json
import logging
import asyncio
import concurrent.futures
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse
from typing import Dict, Any, List, Tuple, Optional, Union

from src.io_utils import atomic_write_json
from src.visual_hasher import should_skip_screenshot_write
from src.authenticity import audit_offer_authenticity
from src.dom_inspector import (
    HeadlessDOMInspector,
    DOMInspector,
    inspect_url_with_playwright,
    inspect_rendered_dom,
    evaluate_dual_gate,
    scan_accessibility_elements,
    assert_cart_balance,
    evaluate_vlm_semantic_gate,
    record_audit_entry,
    PLAYWRIGHT_LAUNCH_ARGS,
    BLOCKED_RESOURCE_TYPES,
    BLOCKED_URL_REGEX,
    CAPACITY_PATTERNS,
    COUPON_EXPIRED_PATTERNS,
    REGISTRATION_CLOSED_PATTERNS,
    MAINTENANCE_PATTERNS,
    PAID_CATALOG_PATTERNS,
    ZERO_DOLLAR_SIGNALS,
    CONFIRMED_ZERO_DOLLAR_CART
)

try:
    from playwright.async_api import async_playwright
except ImportError:
    async_playwright = None

from src.constants import (
    BROWSER_HEADERS,
    CLOSED_PATTERNS,
    SOFT_404_PATTERNS,
    AFFIRMATIVE_OFFER_SIGNALS,
    STALENESS_THRESHOLD_DAYS,
)

logger = logging.getLogger("certpulse.inspector")

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "offers.json"
SCHEMA_FILE = Path(__file__).resolve().parent.parent / "data" / "schema.json"


def check_and_flag_stale_offers(
    offers: List[Dict[str, Any]],
    threshold_days: int = STALENESS_THRESHOLD_DAYS
) -> int:
    """
    Auto-downgrades Active offers whose verification_date exceeds threshold_days
    to 'Review Needed' before the inspection sweep begins.
    """
    today = datetime.now(timezone.utc).date()
    stale_count = 0
    for offer in offers:
        if offer.get("is_historical_archive"):
            continue
        if offer.get("status") == "Active":
            v_date_str = offer.get("verification_date")
            is_stale = False
            if not v_date_str:
                is_stale = True
            else:
                try:
                    v_date = datetime.strptime(v_date_str, "%Y-%m-%d").date()
                    if (today - v_date).days > threshold_days:
                        is_stale = True
                except Exception:
                    is_stale = True
            if is_stale:
                offer["status"] = "Review Needed"
                offer["inspection_notes"] = f"Stale — last verified {v_date_str or 'unknown'} (> {threshold_days} days ago), pending re-inspection"
                stale_count += 1
                logger.warning(
                    f"[STALENESS DOWNGRADE] Offer '{offer.get('title')}' flagged as Review Needed (stale > {threshold_days}d)."
                )
    return stale_count

def clean_html(raw_html: str) -> str:
    """Removes scripts, styles, and SVG tags to inspect only user-visible text."""
    cleaned = re.sub(r'<script.*?</script>', ' ', raw_html, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r'<style.*?</style>', ' ', cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r'<svg.*?</svg>', ' ', cleaned, flags=re.DOTALL | re.IGNORECASE)
    return cleaned.lower()

def check_silent_reroute(original_url: str, final_url: str) -> bool:
    """
    Detects if a specific promotional URL was silently bounced to a generic root or login page.
    Example: site.com/promo/free-vouchers-2026 -> site.com/ or site.com/en-us
    """
    orig_parsed = urlparse(original_url)
    final_parsed = urlparse(final_url)
    
    # If original had a deep path (more than 1 segment) but final is root or /home
    orig_parts = [p for p in orig_parsed.path.split('/') if p]
    final_parts = [p for p in final_parsed.path.split('/') if p]
    
    if len(orig_parts) >= 2 and len(final_parts) <= 1:
        if any(kw in original_url.lower() for kw in ["promo", "challenge", "voucher", "free", "lift"]):
            return True
            
    return False

def inspect_url_with_retry(
    url: str,
    offer: Optional[Dict[str, Any]] = None,
    max_retries: int = 2
) -> Tuple[str, str, str, Dict[str, Any]]:
    """
    Performs deep inspection with transient retry backoff and multi-layer authenticity verification.
    Returns: (status, reason, final_canonical_url, authenticity_result)
    """
    if offer is None:
        offer = {"url": url}
    else:
        offer["url"] = url

    # Static pre-inspection authenticity gate
    pre_auth = audit_offer_authenticity(offer)
    if pre_auth.get("verdict") in ["DECEPTIVE_SCAM", "SUSPICIOUS_UNTRUSTED"]:
        return "Review Needed", f"Security Alert: Domain authenticity failed ({pre_auth['summary']})", url, pre_auth

    last_err = ""
    for attempt in range(max_retries):
        try:
            with httpx.Client(headers=BROWSER_HEADERS, timeout=12.0, follow_redirects=True) as client:
                resp = client.get(url)
                final_url = str(resp.url)
                
                # Trace full redirect chain
                redirect_chain = [str(r.url) for r in resp.history] + [final_url]
                body_text = clean_html(resp.text)

                # Execute multi-layer authenticity verification
                auth_result = audit_offer_authenticity(
                    offer=offer,
                    body_text=body_text,
                    redirect_chain=redirect_chain
                )

                # 1. Hard HTTP status codes
                if resp.status_code in [404, 410]:
                    return "Broken Link", f"HTTP {resp.status_code} Page Not Found", url, auth_result
                elif resp.status_code >= 500:
                    return "Server Error", f"HTTP {resp.status_code} Host Down", url, auth_result
                elif resp.status_code == 429:
                    return "Review Needed", "Rate Limit Invariant: HTTP 429 Too Many Requests / Bot Protection", url, auth_result
                elif resp.status_code in [401, 403]:
                    # Never blind active on 401/403! Check body for maintenance notices
                    for pat in MAINTENANCE_PATTERNS:
                        if pat in body_text:
                            return "Review Needed", f"Maintenance Invariant: Portal currently down for maintenance ('{pat}')", url, auth_result
                    return "Review Needed", f"Restricted Access Gateway: HTTP {resp.status_code} direct GET blocked without verified promotional terms", url, auth_result

                # 2. Maintenance & Downtime Invariant (evaluated before affirmative signals)
                for pat in MAINTENANCE_PATTERNS:
                    if pat in body_text:
                        return "Review Needed", f"Maintenance Invariant: Portal currently down for maintenance ('{pat}')", final_url, auth_result

                # 3. Authenticity Failure Gate (Scam / Deceptive / Untrusted Third Party)
                if not auth_result["is_authentic_vendor"]:
                    return "Review Needed", f"Authenticity Check Failed: {auth_result['summary']}", final_url, auth_result

                # 4. Check for Silent Reroutes
                if check_silent_reroute(url, final_url):
                    return "Registrations Closed", f"Silent Reroute: Redirected to generic root ({final_url})", final_url, auth_result

                # 5. Soft 404 Checks
                for pat in SOFT_404_PATTERNS:
                    if pat in body_text:
                        return "Expired", f"Detected soft-404 text: '{pat}'", final_url, auth_result

                # 6a. Capacity Limit & Cohort Saturation Invariant
                for pat in CAPACITY_PATTERNS:
                    if pat in body_text:
                        return "Registrations Closed", f"Capacity Invariant: Detected capacity limit reached / cohort full ('{pat}')", final_url, auth_result

                # 6b. Expired Coupon & Promo Code Invariant
                for pat in COUPON_EXPIRED_PATTERNS:
                    if pat in body_text:
                        return "Expired", f"Coupon Invariant: Detected expired promo/coupon code ('{pat}')", final_url, auth_result

                # 6c. Explicit Campaign Closure
                for pat in CLOSED_PATTERNS:
                    if pat in body_text:
                        return "Registrations Closed", f"Closure Invariant: Detected closure phrase: '{pat}'", final_url, auth_result

                # 7. Paid Catalog & Standard Fee Barrier Invariant (evaluated before generic affirmative signals)
                has_paid_terms = any(re.search(pat, body_text) for pat in PAID_CATALOG_PATTERNS)
                has_confirmed_zero = any(sig in body_text for sig in CONFIRMED_ZERO_DOLLAR_CART)
                if has_paid_terms and not has_confirmed_zero:
                    if offer is not None:
                        if "visual_proof" not in offer or not isinstance(offer.get("visual_proof"), dict):
                            offer["visual_proof"] = {}
                        offer["visual_proof"]["paid_catalog_detected"] = True
                        offer["visual_proof"]["zero_dollar_confirmed"] = False
                    return "Review Needed", "Catalog Pricing Invariant: Detected standard paid catalog / cart pricing ($245/checkout) without affirmative zero-dollar waiver terms", final_url, auth_result

                # 8. Normal Paid Certification Catalog Check (No free offers on page)
                has_offer_signal = any(sig in body_text for sig in AFFIRMATIVE_OFFER_SIGNALS)
                if not has_offer_signal and len(body_text) > 500:
                    return "Review Needed", "Normal Certification Site: No active free voucher or waiver signal found", final_url, auth_result

                # 9. Dual Visual Proof Gate: Check for valid screenshot proof
                offer_id = offer.get("id", "") if offer else ""
                screenshot_valid = False
                screenshot_path = f"docs/screenshots/{offer_id}.png" if offer_id else ""
                target_path = None
                if offer_id:
                    target_path = Path(__file__).resolve().parent.parent / "docs" / "screenshots" / f"{offer_id}.png"
                    if target_path.exists() and target_path.stat().st_size >= 4096:
                        try:
                            if target_path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n":
                                screenshot_valid = True
                        except Exception:
                            pass

                # Populate visual_proof metadata
                if offer is not None and offer_id:
                    proof_status = "verified" if screenshot_valid else ("failed" if (target_path and target_path.exists()) else "missing")
                    offer["visual_proof"] = {
                        "screenshot_path": screenshot_path,
                        "screenshot_url": screenshot_path,
                        "captured_at": datetime.now(timezone.utc).isoformat() if screenshot_valid else None,
                        "status": proof_status,
                        "zero_dollar_confirmed": True,
                        "maintenance_detected": False,
                        "paid_catalog_detected": False
                    }
                    offer["screenshot_path"] = screenshot_path

                if offer_id:
                    gate_status, gate_reason = evaluate_dual_gate(
                        dom_status="Active",
                        has_zero_dollar=True,
                        screenshot_valid=screenshot_valid,
                        auth_score=auth_result.get("authenticity_score", 100),
                        http_status=resp.status_code
                    )
                    if gate_status != "Active":
                        if offer is not None and "visual_proof" in offer and isinstance(offer["visual_proof"], dict):
                            offer["visual_proof"]["zero_dollar_confirmed"] = False
                        return gate_status, gate_reason, final_url, auth_result

                return "Active", f"HTTP {resp.status_code} OK (Live Verified & Authenticated)", final_url, auth_result
                
        except (httpx.ConnectTimeout, httpx.ReadTimeout) as e:
            last_err = "Read/Connect Timeout"
            time.sleep(1.5)
        except httpx.ConnectError as e:
            err_msg = str(e).lower()
            if any(term in err_msg for term in ["cert", "ssl", "tls", "handshake"]):
                fallback_auth = audit_offer_authenticity(offer)
                fallback_auth["ssl_verified"] = False
                fallback_auth["is_authentic_vendor"] = False
                fallback_auth["authenticity_score"] = max(0, fallback_auth["authenticity_score"] - 50)
                fallback_auth["verdict"] = "SUSPICIOUS_UNTRUSTED"
                fallback_auth["warning_flags"].append("TLS_CERTIFICATE_VERIFICATION_FAILED")
                fallback_auth["summary"] = f"0% Authenticity: Untrusted (TLS Handshake Failed: {str(e)[:40]})"
                return "Review Needed", f"Security Alert: SSL/TLS certificate verification failed ({str(e)[:50]})", url, fallback_auth
            last_err = f"Connect error: {str(e)[:50]}"
            time.sleep(1.5)
        except httpx.RequestError as e:
            err_msg = str(e).lower()
            if any(term in err_msg for term in ["cert", "ssl", "tls", "handshake"]):
                fallback_auth = audit_offer_authenticity(offer)
                fallback_auth["ssl_verified"] = False
                fallback_auth["is_authentic_vendor"] = False
                fallback_auth["authenticity_score"] = max(0, fallback_auth["authenticity_score"] - 50)
                fallback_auth["verdict"] = "SUSPICIOUS_UNTRUSTED"
                fallback_auth["warning_flags"].append("TLS_CERTIFICATE_VERIFICATION_FAILED")
                fallback_auth["summary"] = f"0% Authenticity: Untrusted (TLS Handshake Failed: {str(e)[:40]})"
                return "Review Needed", f"Security Alert: SSL/TLS certificate verification failed ({str(e)[:50]})", url, fallback_auth
            last_err = f"Request error: {str(e)[:50]}"
            time.sleep(1.5)
        except Exception as e:
            fallback_auth = audit_offer_authenticity(offer)
            return "Inspection Error", f"Unexpected error: {str(e)[:50]}", url, fallback_auth
            
    fallback_auth = audit_offer_authenticity(offer)
    return "Network Warning", f"Temporary network timeout after {max_retries} attempts: {last_err}", url, fallback_auth

# Alias convenience function
inspect_url_dom = inspect_url_with_playwright

class InspectionResult(list):
    """
    Dual-nature inspection result container.
    Acts as a list of offers for backwards-compatibility with existing loops,
    while also exposing dictionary keys ('summary', 'results', 'offers')
    and metrics properties for new callers and schema validation.
    """
    def __init__(self, offers: List[Dict[str, Any]], summary: Optional[Dict[str, Any]] = None):
        super().__init__(offers)
        self.summary = summary or {}
        self.results = list(offers)
        self.offers = list(offers)

    def __getitem__(self, item):
        if isinstance(item, str):
            if item == "summary":
                return self.summary
            elif item in ("results", "offers"):
                return list(self)
            raise KeyError(item)
        return super().__getitem__(item)

    def get(self, key, default=None):
        if key == "summary":
            return self.summary
        elif key in ("results", "offers"):
            return list(self)
        return default

    def __contains__(self, item):
        if isinstance(item, str) and item in ("summary", "results", "offers"):
            return True
        return super().__contains__(item)

    def keys(self):
        return ["summary", "results", "offers"]

    def values(self):
        return [self.summary, list(self), list(self)]

    def items(self):
        return [("summary", self.summary), ("results", list(self)), ("offers", list(self))]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "results": list(self),
            "offers": list(self),
        }


async def run_inspection_async(
    use_headless: bool = True,
    concurrency: int = 5,
    timeout_per_offer: int = 45,
    per_vendor_concurrency: int = 4,
) -> InspectionResult:
    """
    Asynchronous concurrency-controlled Playwright inspection engine.
    Limits in-flight portal audits with asyncio.Semaphore(concurrency),
    enforces per-vendor rate limiting via per_vendor_concurrency,
    enforces task isolation across individual offer inspections,
    applies perceptual hash delta-skipping, and atomically persists
    data/offers.json with pre-flight schema validation.
    """
    logger.info("=== Starting Concurrent Playwright DOM Authenticity Engine (concurrency=%d, per_vendor=%d) ===", concurrency, per_vendor_concurrency)
    start_time = time.time()

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    offers = data.get("offers", [])
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    screenshots_dir = Path(__file__).resolve().parent.parent / "docs" / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    status_changes = 0
    healed_count = 0
    url_healed_count = 0
    authentic_count = 0
    active_confirmed = 0
    closed_detected = 0
    screenshots_skipped_phash = 0

    # Pre-sweep staleness auto-downgrade check (Item 3)
    check_and_flag_stale_offers(offers, threshold_days=STALENESS_THRESHOLD_DAYS)

    sem = asyncio.Semaphore(concurrency)
    platform_semaphores: Dict[str, asyncio.Semaphore] = {}

    def get_platform_sem(platform_name: str) -> asyncio.Semaphore:
        plat_key = (platform_name or "unknown").strip().lower()
        if plat_key not in platform_semaphores:
            platform_semaphores[plat_key] = asyncio.Semaphore(per_vendor_concurrency)
        return platform_semaphores[plat_key]

    browser = None
    playwright_mgr = None

    if use_headless and async_playwright is not None:
        try:
            playwright_mgr = await async_playwright().start()
            browser = await playwright_mgr.chromium.launch(
                headless=True,
                args=PLAYWRIGHT_LAUNCH_ARGS
            )
            logger.info("Playwright async Chromium launched successfully.")
        except Exception as pw_err:
            logger.warning("Playwright async launch unavailable (%s). Falling back to HTTP inspection.", pw_err)
            browser = None
            playwright_mgr = None

    async def inspect_single_offer(offer: Dict[str, Any]) -> None:
        nonlocal status_changes, healed_count, url_healed_count
        nonlocal authentic_count, active_confirmed, closed_detected, screenshots_skipped_phash

        title = offer.get("title", "")
        current_url = offer.get("url", "")
        old_status = offer.get("status", "Active")
        offer_id = offer.get("id", "")

        # Task isolation: wrap entire single-offer inspection in try/except
        try:
            # 1. Historical archive record handling (no browser navigation)
            if offer.get("is_historical_archive"):
                logger.info("Preserving historical archive record: [%s] %s", offer.get('platform'), title[:40])
                auth_result = audit_offer_authenticity(offer, body_text="", redirect_chain=[current_url])
                offer["is_authentic_vendor"] = auth_result["is_authentic_vendor"]
                offer["authenticity_score"] = auth_result["authenticity_score"]
                offer["authenticity_details"] = auth_result
                offer["inspection_method"] = "Historical Archive Invariant"
                if "screenshot_path" not in offer or not offer["screenshot_path"]:
                    offer["screenshot_path"] = f"docs/screenshots/{offer_id}.png"
                if "visual_proof" not in offer or not offer["visual_proof"]:
                    offer["visual_proof"] = {
                        "screenshot_path": f"docs/screenshots/{offer_id}.png",
                        "screenshot_url": f"docs/screenshots/{offer_id}.png",
                        "captured_at": None,
                        "status": "placeholder",
                        "zero_dollar_confirmed": True,
                        "maintenance_detected": False,
                        "paid_catalog_detected": False,
                    }
                if auth_result["is_authentic_vendor"]:
                    authentic_count += 1
                if old_status == "Active":
                    active_confirmed += 1
                else:
                    closed_detected += 1
                return

            # 2. Concurrency-bounded live audit with per-vendor rate limiting
            plat_sem = get_platform_sem(offer.get("platform", ""))
            async with sem, plat_sem:
                new_status = old_status
                reason = "Audited"
                canonical_url = current_url
                auth_result = audit_offer_authenticity(offer)
                skipped_write = False

                if browser is not None:
                    context = None
                    try:
                        context = await browser.new_context(
                            viewport={"width": 1280, "height": 800},
                            user_agent=BROWSER_HEADERS["User-Agent"]
                        )
                        page = await context.new_page()

                        # Route blocking: abort analytics trackers and heavy media
                        async def handle_route(route):
                            try:
                                req = route.request
                                if req.resource_type in BLOCKED_RESOURCE_TYPES or BLOCKED_URL_REGEX.search(req.url):
                                    await route.abort()
                                else:
                                    await route.continue_()
                            except Exception:
                                pass

                        await page.route("**/*", handle_route)

                        is_local_file = current_url.startswith("file://")
                        if not is_local_file:
                            pre_auth = audit_offer_authenticity(offer)
                            if pre_auth.get("verdict") in ["DECEPTIVE_SCAM", "SUSPICIOUS_UNTRUSTED"]:
                                new_status = "Review Needed"
                                reason = f"Security Alert: Domain authenticity failed ({pre_auth['summary']})"
                                auth_result = pre_auth
                                auth_score = auth_result.get("authenticity_score", 0)
                                offer["inspection_method"] = "Playwright Headless DOM"
                                return
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

                        nav_target = offer.get("direct_verified_url") or offer.get("verified_vendor_url") or current_url
                        redirect_chain = [nav_target]
                        rendered_title = ""
                        rendered_text = ""
                        final_url = nav_target
                        http_status = 200

                        if not is_local_file:
                            try:
                                response = await page.goto(nav_target, wait_until="domcontentloaded", timeout=timeout_per_offer * 1000)
                                http_status = response.status if response else 200
                                final_url = page.url
                                if final_url != current_url:
                                    redirect_chain.append(final_url)
                                try:
                                    await page.wait_for_load_state("networkidle", timeout=2500)
                                except Exception:
                                    pass
                                rendered_title = await page.title() or ""
                                rendered_text = await page.evaluate("() => document.body ? document.body.innerText : ''")
                            except Exception as nav_err:
                                logger.info("Playwright direct navigation failed for %s (%s). Attempting HTTPX fallback...", current_url, nav_err)
                                async with httpx.AsyncClient(headers=BROWSER_HEADERS, timeout=12.0, follow_redirects=True) as client:
                                    resp = await client.get(current_url)
                                    http_status = resp.status_code
                                    final_url = str(resp.url)
                                    if final_url != current_url:
                                        redirect_chain.append(final_url)
                                    await page.set_content(resp.text, wait_until="domcontentloaded")
                                    rendered_title = await page.title() or ""
                                    rendered_text = await page.evaluate("() => document.body ? document.body.innerText : ''")
                        else:
                            response = await page.goto(nav_target, wait_until="domcontentloaded", timeout=timeout_per_offer * 1000)
                            http_status = response.status if response else 200
                            final_url = page.url
                            rendered_title = await page.title() or ""
                            rendered_text = await page.evaluate("() => document.body ? document.body.innerText : ''")

                        # Capture screenshot with delta skipping
                        target_path = screenshots_dir / f"{offer_id}.png"
                        rel_path = f"docs/screenshots/{offer_id}.png"
                        screenshot_ok = False
                        screenshot_bytes = None

                        if offer_id:
                            try:
                                screenshot_bytes = await page.screenshot(full_page=False)
                                if screenshot_bytes and len(screenshot_bytes) >= 4096 and screenshot_bytes[:8] == b"\x89PNG\r\n\x1a\n":
                                    from src.visual_hasher import is_blank_or_invalid_screenshot, should_skip_screenshot_write
                                    if target_path.exists() and not is_blank_or_invalid_screenshot(target_path):
                                        if is_blank_or_invalid_screenshot(screenshot_bytes) or (target_path.stat().st_size >= 30000 and len(screenshot_bytes) < 18000):
                                            logger.info(
                                                "Preserving existing substantive screenshot for %s (new capture is blank/spinner)",
                                                offer_id
                                            )
                                            skipped_write = True
                                            screenshot_ok = True
                                    if not skipped_write:
                                        should_skip, delta, dist = should_skip_screenshot_write(
                                            screenshot_bytes, target_path, old_status, old_status
                                        )
                                        if should_skip:
                                            logger.info(
                                                f"[SKIP] Visual diff < 5% (delta={delta:.4f}, hamming={dist}) and status unchanged. "
                                                f"Skipped write for {target_path}."
                                            )
                                            skipped_write = True
                                            screenshot_ok = True
                                        else:
                                            temp_path = target_path.with_suffix(".tmp.png")
                                            temp_path.write_bytes(screenshot_bytes)
                                            temp_path.replace(target_path)
                                            screenshot_ok = True
                                elif target_path.exists() and target_path.stat().st_size >= 4096:
                                    screenshot_ok = True
                            except Exception as sc_err:
                                logger.warning("Screenshot capture failed for %s: %s", offer_id, sc_err)
                                if target_path.exists() and target_path.stat().st_size >= 4096:
                                    screenshot_ok = True

                        # Interactive CTAs
                        try:
                            interactive_ctas = await page.evaluate("""() => {
                                const ctas = [];
                                document.querySelectorAll('button, a, [role="button"], input[type="submit"]').forEach(el => {
                                    const txt = (el.innerText || el.textContent || el.value || '').trim().toLowerCase();
                                    if (txt.length > 2 && txt.length < 80) ctas.push(txt);
                                });
                                return ctas;
                            }""")
                        except Exception:
                            interactive_ctas = []

                        # Run semantic scanning, cart balance assertion, DOM analysis, and VLM gate
                        actionability_report = scan_accessibility_elements(
                            interactive_elements=interactive_ctas,
                            page_text=rendered_text,
                            page_title=rendered_title
                        )
                        cart_verdict = assert_cart_balance(offer)
                        dom_eval = inspect_rendered_dom(
                            rendered_text=rendered_text,
                            rendered_title=rendered_title,
                            final_url=final_url,
                            original_url=current_url,
                            interactive_elements=interactive_ctas
                        )
                        vlm_verdict = evaluate_vlm_semantic_gate(
                            offer_id=offer_id,
                            url=final_url or current_url,
                            dom_text=rendered_text,
                            dom_title=rendered_title,
                            screenshot_path=rel_path if screenshot_ok else None,
                            screenshot_bytes=screenshot_bytes,
                            platform=offer.get("platform", ""),
                            offer_data=offer
                        )

                        if not is_local_file:
                            auth_result = audit_offer_authenticity(
                                offer=offer,
                                body_text=rendered_text,
                                redirect_chain=redirect_chain
                            )
                        else:
                            auth_result = pre_auth

                        auth_score = auth_result.get("authenticity_score", 90)

                        if http_status in [404, 410]:
                            new_status = "Broken Link"
                            reason = f"HTTP {http_status} Page Not Found"
                        elif http_status >= 500:
                            new_status = "Server Error"
                            reason = f"HTTP {http_status} Host Down"
                        elif http_status == 429:
                            new_status = "Review Needed"
                            reason = f"Rate Limit Invariant: HTTP {http_status} Too Many Requests / Bot Protection"
                        elif http_status in [401, 403]:
                            if dom_eval["status"] != "Active":
                                new_status = dom_eval["status"]
                                reason = dom_eval["reason"]
                            else:
                                new_status = "Review Needed"
                                reason = f"Restricted Gateway: HTTP {http_status} encountered without verified promotional terms"
                        else:
                            new_status = dom_eval["status"]
                            reason = dom_eval["reason"]

                        maintenance_detected = dom_eval.get("maintenance_detected", False)
                        paid_catalog_detected = dom_eval.get("paid_catalog_detected", False)
                        zero_dollar_confirmed = dom_eval.get("zero_dollar_confirmed", True)

                        if new_status == "Active" and actionability_report.verdict == "MARKETING_LEAD_FUNNEL":
                            new_status = "Review Needed"
                            reason = actionability_report.reason
                            zero_dollar_confirmed = False

                        if new_status == "Active" and cart_verdict.is_copay_required and cart_verdict.copay_amount_usd > 0.0:
                            new_status = "Review Needed"
                            reason = f"Cart Assertion: Copay Required (${cart_verdict.copay_amount_usd:.2f}) - {cart_verdict.reason}"
                            paid_catalog_detected = True
                            zero_dollar_confirmed = False

                        if new_status == "Active":
                            if not auth_result.get("is_authentic_vendor", True) or auth_score < 80:
                                new_status = "Review Needed"
                                reason = f"Authenticity Check Failed: {auth_result.get('summary', 'Score below threshold')}"
                            elif not zero_dollar_confirmed or maintenance_detected or paid_catalog_detected:
                                new_status = "Review Needed"
                                reason = dom_eval.get("reason", "DOM failed zero-dollar confirmation")
                            elif not screenshot_ok:
                                new_status = "Review Needed"
                                reason = "Visual Proof Gate Invariant: DOM confirmed offer, but visual screenshot proof is missing or invalid"
                            elif vlm_verdict.registration_status in ["closed", "cohort_full"]:
                                new_status = "Registrations Closed"
                                reason = f"VLM Semantic Gate: {vlm_verdict.primary_evidence}"
                                zero_dollar_confirmed = False
                            elif vlm_verdict.requires_payment_or_copay and vlm_verdict.copay_amount_usd > 0.0:
                                new_status = "Review Needed"
                                reason = f"VLM Semantic Gate: Copay required (${vlm_verdict.copay_amount_usd:.2f} USD)"
                                paid_catalog_detected = True
                                zero_dollar_confirmed = False
                            elif not vlm_verdict.has_zero_dollar_waiver:
                                new_status = "Review Needed"
                                reason = f"VLM Semantic Gate: {vlm_verdict.primary_evidence}"
                                zero_dollar_confirmed = False
                            elif vlm_verdict.visual_confidence_score < 0.60:
                                new_status = "Review Needed"
                                reason = f"VLM Semantic Gate: Low visual confidence ({vlm_verdict.visual_confidence_score:.2f} < 0.60)"
                            else:
                                reason = f"Playwright DOM Verified: HTTP {http_status} OK, active campaign validated with visual screenshot proof"

                        if new_status != "Active":
                            zero_dollar_confirmed = False

                        # If status changed, ensure screenshot write is refreshed only with a non-blank screenshot
                        if offer_id and new_status != old_status and screenshot_bytes:
                            from src.visual_hasher import is_blank_or_invalid_screenshot
                            if not is_blank_or_invalid_screenshot(screenshot_bytes):
                                temp_path = target_path.with_suffix(".tmp.png")
                                temp_path.write_bytes(screenshot_bytes)
                                temp_path.replace(target_path)
                                skipped_write = False
                            else:
                                logger.warning(
                                    "Status changed for %s, but candidate screenshot is blank/invalid. Preserving existing screenshot.",
                                    offer_id
                                )

                        canonical_url = final_url
                        if "Bot Protected" in reason or "HTTP Fallback" in reason or "Direct GET" in reason:
                            offer["inspection_method"] = "Playwright DOM (HTTP Fallback)"
                        else:
                            offer["inspection_method"] = "Playwright Headless DOM"
                    finally:
                        if context:
                            try:
                                await context.close()
                            except Exception:
                                pass
                else:
                    # Synchronous fallback runner via thread pool
                    fn = globals().get("inspect_url_with_retry", inspect_url_with_retry)
                    new_status, reason, canonical_url, auth_result = await asyncio.to_thread(
                        fn, current_url, offer=offer
                    )
                    canonical_url = canonical_url or current_url
                    offer["inspection_method"] = "HTTP Multi-Layer Gate"
                    skipped_write = False

                if skipped_write:
                    screenshots_skipped_phash += 1

                # Store structured authenticity verification results
                offer["is_authentic_vendor"] = auth_result["is_authentic_vendor"]
                offer["authenticity_score"] = auth_result["authenticity_score"]
                offer["authenticity_details"] = auth_result
                if auth_result["is_authentic_vendor"]:
                    authentic_count += 1

                # Ensure visual_proof and screenshot_path are present
                if "screenshot_path" not in offer or not offer["screenshot_path"]:
                    offer["screenshot_path"] = f"docs/screenshots/{offer_id}.png"
                if "visual_proof" not in offer or not offer["visual_proof"]:
                    offer["visual_proof"] = {
                        "screenshot_path": f"docs/screenshots/{offer_id}.png",
                        "screenshot_url": f"docs/screenshots/{offer_id}.png",
                        "captured_at": datetime.now(timezone.utc).isoformat(),
                        "status": "verified" if new_status == "Active" else "placeholder",
                        "zero_dollar_confirmed": new_status == "Active",
                        "maintenance_detected": "maintenance" in reason.lower(),
                        "paid_catalog_detected": "catalog" in reason.lower()
                    }

                # Temporal Expiry Invariant: If stated calendar expiration has passed, override to Expired
                expiry_str = str(offer.get("expiry_date", "")).strip()
                if re.match(r"^\d{4}-\d{2}-\d{2}$", expiry_str):
                    try:
                        exp_date = datetime.strptime(expiry_str, "%Y-%m-%d").date()
                        if exp_date < datetime.now(timezone.utc).date():
                            new_status = "Expired"
                            reason = f"Calendar Invariant: Stated expiration date passed ({expiry_str})"
                    except ValueError:
                        pass

                logger.info(" -> Result: %s | Reason: %s | Authenticity: %d%%", new_status, reason, auth_result['authenticity_score'])

                # Canonical URL Self-Healing: Update to clean canonical path if permanently redirected
                if canonical_url != current_url and new_status == "Active":
                    parsed_orig = urlparse(current_url).netloc
                    parsed_canon = urlparse(canonical_url).netloc
                    is_same_vendor_migration = (
                        parsed_orig in parsed_canon or 
                        parsed_canon in parsed_orig or 
                        (parsed_orig.endswith('.google') and parsed_canon.endswith('.google'))
                    )
                    if is_same_vendor_migration:
                        logger.info("[URL HEALED] Updating '%s' URL from %s -> %s", title, current_url, canonical_url)
                        offer["url"] = canonical_url
                        url_healed_count += 1

                # State Self-Healing: Re-open offer if portal recovered
                if old_status in ["Broken Link", "Expired", "Registrations Closed", "Review Needed"] and new_status == "Active":
                    logger.warning("[SELF-HEALED] Offer '%s' recovered from %s to Active!", title, old_status)
                    healed_count += 1
                    offer["self_healing_event"] = {
                        "previous_status": old_status,
                        "healed_status": "Active",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "proof_image": offer.get("screenshot_path", f"docs/screenshots/{offer_id}.png")
                    }

                # Update definitive statuses
                consecutive_failures = offer.get("consecutive_failures", 0)

                # Two-Strike Invariant (P1): Transient network/DOM blips enter grace period on Strike 1
                if old_status == "Active" and new_status in ["Review Needed", "Broken Link", "Server Error", "Registrations Closed"]:
                    if consecutive_failures < 1:
                        # Strike 1: Preserve Active, activate grace period, do not trigger false alarm status changes
                        offer["consecutive_failures"] = 1
                        offer["in_grace_period"] = True
                        new_status = "Active"
                        reason = f"Strike 1 (Grace Period): Transient check issue encountered ({reason}). Verifying in next pass."
                        logger.warning("Strike 1 for '%s': Entering grace period without flipping status.", title)
                    else:
                        # Strike 2: Confirmed degradation across consecutive scheduled passes
                        offer["consecutive_failures"] = consecutive_failures + 1
                        offer.pop("in_grace_period", None)
                elif new_status == "Active":
                    offer["consecutive_failures"] = 0
                    offer.pop("in_grace_period", None)

                if new_status in ["Active", "Registrations Closed", "Broken Link", "Expired", "Review Needed", "Server Error"]:
                    offer["status"] = new_status
                    offer["verification_date"] = today
                    offer["inspection_notes"] = reason
                    vp = offer.get("visual_proof") if isinstance(offer.get("visual_proof"), dict) else {}
                    zero_dollar_confirmed = bool(vp.get("zero_dollar_confirmed", False))
                    if new_status == "Active" and zero_dollar_confirmed:
                        offer["last_zero_dollar_confirmed_date"] = today
                    if old_status != new_status:
                        logger.warning("Status transition for '%s': %s -> %s", title, old_status, new_status)
                        status_changes += 1

                if new_status == "Active":
                    active_confirmed += 1
                else:
                    closed_detected += 1

        except Exception as e:
            logger.error("Task isolation caught failure on offer '%s': %s", offer_id, e)

    try:
        tasks = [inspect_single_offer(offer) for offer in offers]
        await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        if browser:
            try:
                await browser.close()
            except Exception:
                pass
        if playwright_mgr:
            try:
                await playwright_mgr.stop()
            except Exception:
                pass

    now_iso = datetime.now(timezone.utc).isoformat()
    data["last_inspected"] = now_iso
    data["last_sync"] = now_iso
    data["last_updated"] = now_iso
    if "$schema" not in data:
        data["$schema"] = "./schema.json"

    # Pre-flight schema validated atomic persistence
    schema_to_validate = SCHEMA_FILE if SCHEMA_FILE.exists() else None
    try:
        atomic_write_json(DATA_FILE, data, schema_path=schema_to_validate)
    except Exception as exc:
        logger.warning("Schema pre-flight validation exception (%s); writing atomically without schema enforcement.", exc)
        atomic_write_json(DATA_FILE, data, schema_path=None)

    duration = round(time.time() - start_time, 2)
    summary = {
        "total_inspected": len(offers),
        "active_confirmed": active_confirmed,
        "closed_detected": closed_detected,
        "screenshots_skipped_phash": screenshots_skipped_phash,
        "duration_seconds": duration,
        "status_changes": status_changes,
        "healed_count": healed_count,
        "url_healed_count": url_healed_count,
        "authentic_count": authentic_count,
    }
    logger.info(
        "=== Deep Inspection Finished: %d offers audited in %.2fs "
        "(%d changes, %d self-healed, %d canonical URLs updated, "
        "%d screenshots skipped via pHash, %d/%d authentic vendors) ===",
        len(offers), duration, status_changes, healed_count,
        url_healed_count, screenshots_skipped_phash, authentic_count, len(offers)
    )
    return InspectionResult(offers, summary)


def run_inspection(
    use_headless: bool = True,
    concurrency: int = 5,
    timeout_per_offer: int = 45,
    per_vendor_concurrency: int = 4,
) -> InspectionResult:
    """
    Synchronous wrapper executing run_inspection_async with concurrency-controlled Playwright.
    Maintains full backwards compatibility with src/main.py and pytest test suites.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(
                asyncio.run,
                run_inspection_async(
                    use_headless=use_headless,
                    concurrency=concurrency,
                    timeout_per_offer=timeout_per_offer,
                    per_vendor_concurrency=per_vendor_concurrency,
                )
            ).result()
    else:
        return asyncio.run(
            run_inspection_async(
                use_headless=use_headless,
                concurrency=concurrency,
                timeout_per_offer=timeout_per_offer,
                per_vendor_concurrency=per_vendor_concurrency,
            )
        )



def inspect_offer(offer: Any, capture_screenshot: bool = True) -> Dict[str, Any]:
    """
    Interface contract function: inspects a single offer and returns
    updated status, visual_proof, auth_score, verification_date,
    maintenance_detected, paid_catalog_detected.
    """
    offer_dict = offer.model_dump() if hasattr(offer, "model_dump") else dict(offer)
    url = offer_dict.get("verified_vendor_url") or offer_dict.get("url", "")
    
    with HeadlessDOMInspector(headless=True, timeout_ms=12000) as inspector:
        if inspector.is_available:
            status, reason, canonical_url, auth_result = inspector.inspect_url(url, offer=offer_dict)
        else:
            status, reason, canonical_url, auth_result = inspect_url_with_retry(url, offer=offer_dict)
            
    vp = offer_dict.get("visual_proof", {})
    return {
        "status": status,
        "reason": reason,
        "canonical_url": canonical_url,
        "auth_score": auth_result.get("authenticity_score", 0),
        "visual_proof": vp,
        "verification_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "zero_dollar_confirmed": vp.get("zero_dollar_confirmed", False) if isinstance(vp, dict) else False,
        "maintenance_detected": vp.get("maintenance_detected", False) if isinstance(vp, dict) else False,
        "paid_catalog_detected": vp.get("paid_catalog_detected", False) if isinstance(vp, dict) else False,
        "offer": offer_dict
    }


if __name__ == "__main__":
    run_inspection()
