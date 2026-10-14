"""
Collector module for CertPulse.
Fetches high-intent free certification voucher leads from public community feeds
and official vendor channels without any API fees.
Enforces domain authenticity checks on discovered outbound links.
"""

import re
import time
import httpx
import logging
import xml.etree.ElementTree as ET
from typing import List, Dict, Any
from datetime import datetime, timezone

from src.authenticity import check_domain_authenticity, SCAM_DOMAIN_KEYWORDS, BANNED_URL_SHORTENERS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("certpulse.collector")

ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/atom+xml,application/xml,text/xml;q=0.9,*/*;q=0.8"
}

REDDIT_TARGETS = [
    {
        "subreddit": "AzureCertification",
        "query": "voucher OR challenge OR free",
        "platform": "Microsoft Azure"
    },
    {
        "subreddit": "AWSCertifications",
        "query": "voucher OR free OR discount",
        "platform": "Amazon Web Services"
    },
    {
        "subreddit": "cloud_computing",
        "query": "free certification voucher",
        "platform": "Multi-Cloud"
    }
]

VOUCHER_KEYWORDS = [
    "voucher", "challenge", "free exam", "100%", "cloud skills",
    "level up", "levelup", "promo code", "discount code"
]

NOISE_KEYWORDS = [
    "passed az", "passed aws", "failed", "exam tomorrow", "cancelled my exam",
    "lost my voucher", "retry az", "exam dump", "braindump", "dumps"
]

URL_REGEX = re.compile(r'https?://[^\s<>"\'\)]+')

def fetch_reddit_leads() -> List[Dict[str, Any]]:
    """
    Fetches Atom RSS feeds from Reddit search endpoints.
    Applies high-signal intent filters, scam suppression, and domain authenticity auditing.
    """
    discovered_leads = []
    
    with httpx.Client(headers=BROWSER_HEADERS, timeout=12.0, follow_redirects=True) as client:
        for idx, target in enumerate(REDDIT_TARGETS):
            if idx > 0:
                time.sleep(3.5)  # Polite spacing to avoid Reddit 429 burst blocks
                
            sub = target["subreddit"]
            url = f"https://www.reddit.com/r/{sub}/search.rss?q={target['query']}&restrict_sr=1&sort=new"
            try:
                logger.info(f"Scanning r/{sub} feed for high-intent voucher signals...")
                response = client.get(url)
                if response.status_code == 200:
                    root = ET.fromstring(response.text)
                    entries = root.findall("atom:entry", ATOM_NS)
                    logger.info(f"Retrieved {len(entries)} candidate posts from r/{sub}.")
                    
                    for entry in entries:
                        title_el = entry.find("atom:title", ATOM_NS)
                        link_el = entry.find("atom:link", ATOM_NS)
                        content_el = entry.find("atom:content", ATOM_NS)
                        updated_el = entry.find("atom:updated", ATOM_NS)
                        
                        title = title_el.text.strip() if title_el is not None and title_el.text else ""
                        link = link_el.attrib.get("href") if link_el is not None else ""
                        content = content_el.text.strip() if content_el is not None and content_el.text else ""
                        updated = updated_el.text if updated_el is not None and updated_el.text else datetime.now(timezone.utc).isoformat()
                        
                        title_lower = title.lower()
                        combined_lower = f"{title_lower} {content.lower()}"
                        
                        # Discard noise posts (passed exams, complaints, braindump requests)
                        if any(noise in title_lower for noise in NOISE_KEYWORDS):
                            continue
                            
                        # Extract outbound URLs from post body
                        found_urls = URL_REGEX.findall(content)
                        # Filter out Reddit internal URLs
                        external_urls = [u for u in found_urls if "reddit.com" not in u and "redd.it" not in u]
                        
                        # Scam & banned shortener suppression
                        has_scam_link = False
                        for ext_url in external_urls:
                            ext_lower = ext_url.lower()
                            if any(scam in ext_lower for scam in SCAM_DOMAIN_KEYWORDS):
                                has_scam_link = True
                                break
                            if any(shortener in ext_lower for shortener in BANNED_URL_SHORTENERS):
                                has_scam_link = True
                                break
                                
                        if has_scam_link:
                            logger.warning(f"Discarding lead with suspicious / scam link: {title[:40]}")
                            continue

                        # Check for verified official vendor destination
                        verified_vendor_url = ""
                        is_authentic_vendor = False
                        for ext_url in external_urls:
                            is_auth, tier, _, _ = check_domain_authenticity(ext_url, target["platform"])
                            if is_auth:
                                is_authentic_vendor = True
                                verified_vendor_url = ext_url
                                break

                        # Intent rule: keyword in title OR 2+ keywords in body
                        matched_in_title = [kw for kw in VOUCHER_KEYWORDS if kw in title_lower]
                        matched_in_body = [kw for kw in VOUCHER_KEYWORDS if kw in combined_lower]
                        
                        is_high_signal = len(matched_in_title) > 0 or len(matched_in_body) >= 2 or is_authentic_vendor
                        
                        if is_high_signal:
                            discovered_leads.append({
                                "source": f"Reddit r/{sub}",
                                "title": title,
                                "url": link,
                                "platform": target["platform"],
                                "timestamp": updated,
                                "keywords": matched_in_title or matched_in_body,
                                "match_confidence": "High (Title)" if matched_in_title else "Medium (Multi-Keyword)",
                                "is_authentic_vendor": is_authentic_vendor,
                                "verified_vendor_url": verified_vendor_url,
                                "authenticity_tier": "Verified Official Portal" if is_authentic_vendor else "Community Lead"
                            })
                elif response.status_code == 429:
                    logger.warning(f"Reddit r/{sub} returned 429 rate limit (will retry next scheduled run).")
                else:
                    logger.warning(f"r/{sub} returned HTTP {response.status_code}")
            except Exception as e:
                logger.error(f"Error checking r/{sub}: {e}")
                
    logger.info(f"High-signal community leads captured: {len(discovered_leads)}")
    return discovered_leads
