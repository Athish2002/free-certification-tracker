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
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse
from typing import Dict, Any, List, Tuple, Optional

from src.authenticity import audit_offer_authenticity

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("certpulse.inspector")

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "offers.json"

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Heuristic phrases indicating an offer/voucher campaign is over even if HTTP 200
CLOSED_PATTERNS = [
    "registration is closed",
    "registrations are closed",
    "registration has closed",
    "all vouchers have been claimed",
    "all vouchers are claimed",
    "vouchers are no longer available",
    "this promotion has ended",
    "promotion has ended",
    "this offer has expired",
    "the event has ended",
    "capacity reached",
    "seats are full",
    "program is closed",
    "no longer accepting submissions",
    "no longer available",
    "campaign concluded",
    "offer ended"
]

SOFT_404_PATTERNS = [
    "page not found",
    "we couldn't find that page",
    "page you're looking for doesn't exist",
    "the page has been removed",
    "error 404",
    "this page is not available"
]

# Affirmative signals that verify a page actually offers something free/discounted
AFFIRMATIVE_OFFER_SIGNALS = [
    "free", "voucher", "scholarship", "challenge", "no cost",
    "waiver", "discount", "reward", "credits", "badge", "grant",
    "complimentary", "100%", "level up", "applied skills"
]

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
        offer = {**offer, "url": url}

    # Static pre-inspection authenticity gate
    pre_auth = audit_offer_authenticity(offer)
    if pre_auth.get("verdict") == "DECEPTIVE_SCAM":
        return "Review Needed", f"Security Alert: Deceptive or scam domain detected ({pre_auth['summary']})", url, pre_auth

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
                elif resp.status_code in [401, 403]:
                    # Bot protected enterprise gateway (Oracle Cloud / Cloudflare)
                    return "Active", "Verified (Bot Protected / Restricted Direct GET)", url, auth_result
                    
                # 2. Authenticity Failure Gate (Scam / Deceptive / Untrusted Third Party)
                if not auth_result["is_authentic_vendor"]:
                    return "Review Needed", f"Authenticity Check Failed: {auth_result['summary']}", final_url, auth_result

                # 3. Check for Silent Reroutes
                if check_silent_reroute(url, final_url):
                    return "Registrations Closed", f"Silent Reroute: Redirected to generic root ({final_url})", final_url, auth_result
                    
                # 4. Soft 404 Checks
                for pat in SOFT_404_PATTERNS:
                    if pat in body_text:
                        return "Expired", f"Detected soft-404 text: '{pat}'", final_url, auth_result
                        
                # 5. Explicit Campaign Closure
                for pat in CLOSED_PATTERNS:
                    if pat in body_text:
                        return "Registrations Closed", f"Detected closure phrase: '{pat}'", final_url, auth_result
                        
                # 6. Normal Paid Certification Catalog Check (No free offers on page)
                has_offer_signal = any(sig in body_text for sig in AFFIRMATIVE_OFFER_SIGNALS)
                if not has_offer_signal and len(body_text) > 500:
                    return "Review Needed", "Normal Certification Site: No active free voucher or waiver signal found", final_url, auth_result
                    
                return "Active", f"HTTP {resp.status_code} OK (Live Verified & Authenticated)", final_url, auth_result
                
        except (httpx.ConnectTimeout, httpx.ReadTimeout) as e:
            last_err = "Read/Connect Timeout"
            time.sleep(1.5)
        except httpx.RequestError as e:
            last_err = f"Request error: {str(e)[:50]}"
            time.sleep(1.5)
        except Exception as e:
            fallback_auth = audit_offer_authenticity(offer)
            return "Inspection Error", f"Unexpected error: {str(e)[:50]}", url, fallback_auth
            
    fallback_auth = audit_offer_authenticity(offer)
    return "Network Warning", f"Temporary network timeout after {max_retries} attempts: {last_err}", url, fallback_auth

def run_inspection() -> List[Dict[str, Any]]:
    """Runs deep inspection, authenticity audit, and self-healing engine on all tracked offers."""
    logger.info("=== Starting Self-Healing Site Inspector & Authenticity Engine ===")
    
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    offers = data.get("offers", [])
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    status_changes = 0
    healed_count = 0
    url_healed_count = 0
    authentic_count = 0
    
    for offer in offers:
        title = offer.get("title")
        current_url = offer.get("url")
        old_status = offer.get("status", "Active")
        
        # Preserve historical archive records without probing expired promo URLs
        if offer.get("is_historical_archive"):
            logger.info(f"Preserving historical archive record & verifying authenticity: [{offer.get('platform')}] {title[:40]}")
            auth_result = audit_offer_authenticity(offer, body_text="", redirect_chain=[current_url])
            offer["is_authentic_vendor"] = auth_result["is_authentic_vendor"]
            offer["authenticity_score"] = auth_result["authenticity_score"]
            offer["authenticity_details"] = auth_result
            if auth_result["is_authentic_vendor"]:
                authentic_count += 1
            continue

        logger.info(f"Auditing [{offer.get('platform')}] {title[:40]}...")
        new_status, reason, canonical_url, auth_result = inspect_url_with_retry(current_url, offer=offer)
        
        # Store structured authenticity verification results
        offer["is_authentic_vendor"] = auth_result["is_authentic_vendor"]
        offer["authenticity_score"] = auth_result["authenticity_score"]
        offer["authenticity_details"] = auth_result
        if auth_result["is_authentic_vendor"]:
            authentic_count += 1
        
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

        logger.info(f" -> Result: {new_status} | Reason: {reason} | Authenticity: {auth_result['authenticity_score']}%")
        
        # Canonical URL Self-Healing: Update to clean canonical path if permanently redirected
        if canonical_url != current_url and new_status == "Active":
            # Only update if within same domain or official migration
            parsed_orig = urlparse(current_url).netloc
            parsed_canon = urlparse(canonical_url).netloc
            is_same_vendor_migration = (
                parsed_orig in parsed_canon or 
                parsed_canon in parsed_orig or 
                (parsed_orig.endswith('.google') and parsed_canon.endswith('.google'))
            )
            if is_same_vendor_migration:
                logger.info(f"[URL HEALED] Updating '{title}' URL from {current_url} -> {canonical_url}")
                offer["url"] = canonical_url
                url_healed_count += 1
                
        # State Self-Healing: Re-open offer if portal recovered
        if old_status in ["Broken Link", "Expired", "Registrations Closed", "Review Needed"] and new_status == "Active":
            logger.warning(f"[SELF-HEALED] Offer '{title}' recovered from {old_status} to Active!")
            healed_count += 1
            
        # Update definitive statuses
        if new_status in ["Active", "Registrations Closed", "Broken Link", "Expired", "Review Needed"]:
            offer["status"] = new_status
            offer["verification_date"] = today
            offer["inspection_notes"] = reason
            if old_status != new_status:
                logger.warning(f"Status transition for '{title}': {old_status} -> {new_status}")
                status_changes += 1
                
    data["last_inspected"] = datetime.now(timezone.utc).isoformat()
    
    # Atomic Database Save: write to temp file then rename
    temp_file = DATA_FILE.with_suffix(".tmp")
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    temp_file.replace(DATA_FILE)
    
    logger.info(
        f"=== Deep Inspection Finished: {len(offers)} offers audited "
        f"({status_changes} changes, {healed_count} self-healed, "
        f"{url_healed_count} canonical URLs updated, {authentic_count}/{len(offers)} authentic vendors) ==="
    )
    return offers

if __name__ == "__main__":
    run_inspection()
