"""
Autonomous News & Engineering Intelligence Collector for CertPulse.
Aggregates authentic, verified technical developments, research breakthroughs,
and financial updates directly from official cloud & tech giant engineering feeds.
Strictly bans clickbait and rumor aggregators.
"""

import re
import json
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any
from urllib.parse import urlparse
import httpx

logger = logging.getLogger("certpulse.news")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
NEWS_FILE = DATA_DIR / "news.json"

VERIFIED_FEEDS = [
    {
        "company": "Amazon Web Services",
        "source": "AWS Architecture Blog",
        "category": "Infrastructure & Silicon",
        "feed_url": "https://aws.amazon.com/blogs/architecture/feed/",
        "allowed_domain": "aws.amazon.com",
        "impact_badge": "Architecture RFC"
    },
    {
        "company": "Google Cloud",
        "source": "Google Cloud Blog",
        "category": "Infrastructure & Silicon",
        "feed_url": "https://cloudblog.withgoogle.com/rss/",
        "allowed_domain": "cloud.google.com",
        "impact_badge": "Cloud Platform"
    },
    {
        "company": "GitHub",
        "source": "GitHub Engineering Blog",
        "category": "Tech Development",
        "feed_url": "https://github.blog/feed/",
        "allowed_domain": "github.blog",
        "impact_badge": "Developer Tooling"
    },
    {
        "company": "Cisco",
        "source": "Cisco Blogs",
        "category": "Tech Development",
        "feed_url": "https://blogs.cisco.com/feed",
        "allowed_domain": "blogs.cisco.com",
        "impact_badge": "Enterprise Networking"
    }
]

BANNED_CLICKBAIT_PATTERNS = [
    r"\bshocking\b", r"\binsane\b", r"\byou won't believe\b",
    r"\bunbelievable\b", r"\bsecret trick\b", r"\bgame changer\b",
    r"\bdestroy\b", r"\bmind blowing\b", r"\bexposed\b", r"\bviral\b"
]

def is_clean_headline(title: str) -> bool:
    """Verifies that a headline is objective and devoid of clickbait buzzwords."""
    lower = title.lower()
    for pat in BANNED_CLICKBAIT_PATTERNS:
        if re.search(pat, lower):
            return False
    return True

def fetch_feed_entries(feed_info: Dict[str, str], max_items: int = 3) -> List[Dict[str, Any]]:
    """Fetches and parses Atom/RSS feed from an authentic primary source."""
    entries = []
    headers = {
        "User-Agent": "CertPulse-VerifiedNewsBot/2.0 (GitHub: Athish2002/free-certification-tracker)",
        "Accept": "application/rss+xml, application/atom+xml, text/xml"
    }
    
    try:
        with httpx.Client(timeout=10.0, follow_redirects=True, headers=headers) as client:
            resp = client.get(feed_info["feed_url"])
            if resp.status_code != 200:
                logger.warning(f"Feed {feed_info['source']} returned HTTP {resp.status_code}")
                return []
            
            root = ET.fromstring(resp.content)
            
            # Handle RSS 2.0
            items = root.findall(".//item")
            if not items:
                # Handle Atom
                items = root.findall(".//{http://www.w3.org/2005/Atom}entry")
                
            for item in items[:max_items]:
                # Title
                title_el = item.find("title")
                if title_el is None:
                    title_el = item.find("{http://www.w3.org/2005/Atom}title")
                title = title_el.text.strip() if title_el is not None and title_el.text else ""
                
                # Link
                link_el = item.find("link")
                if link_el is None:
                    link_el = item.find("{http://www.w3.org/2005/Atom}link")
                if link_el is not None:
                    link = link_el.text or link_el.attrib.get("href", "")
                else:
                    link = ""
                link = link.strip()
                
                # Description / Summary
                desc_el = item.find("description")
                if desc_el is None:
                    desc_el = item.find("{http://www.w3.org/2005/Atom}summary")
                if desc_el is None:
                    desc_el = item.find("{http://www.w3.org/2005/Atom}content")
                raw_desc = desc_el.text if desc_el is not None and desc_el.text else ""
                # Strip HTML tags
                clean_desc = re.sub(r"<[^>]+>", "", raw_desc).strip()
                clean_desc = " ".join(clean_desc.split())[:240]
                if clean_desc and not clean_desc.endswith("."):
                    clean_desc += "..."
                
                # Date
                pub_el = item.find("pubDate")
                if pub_el is None:
                    pub_el = item.find("{http://www.w3.org/2005/Atom}published")
                if pub_el is None:
                    pub_el = item.find("{http://www.w3.org/2005/Atom}updated")
                pub_date = pub_el.text.strip() if pub_el is not None and pub_el.text else ""
                
                # Format ISO date if possible
                date_match = re.search(r"(\d{4}-\d{2}-\d{2})", pub_date)
                if date_match:
                    iso_date = date_match.group(1)
                else:
                    iso_date = "2024-08-01"
                
                # Verification Gates:
                if not title or not link or not is_clean_headline(title):
                    continue
                
                # Assert domain is authentic
                parsed_netloc = urlparse(link).netloc.lower()
                allowed = feed_info["allowed_domain"]
                if allowed not in parsed_netloc and parsed_netloc not in allowed:
                    continue
                
                slug_id = re.sub(r"[^a-z0-9]+", "-", f"{feed_info['company']}-{title[:30]}".lower()).strip("-")
                
                entries.append({
                    "id": slug_id,
                    "company": feed_info["company"],
                    "source": feed_info["source"],
                    "source_domain": feed_info["allowed_domain"],
                    "category": feed_info["category"],
                    "title": title,
                    "summary": clean_desc or f"Official technical update published by {feed_info['source']}.",
                    "published_date": iso_date,
                    "url": link,
                    "impact_badge": feed_info["impact_badge"]
                })
    except Exception as e:
        logger.warning(f"Failed to fetch feed {feed_info['source']}: {e}")
        
    return entries

def update_news_feed() -> List[Dict[str, Any]]:
    """Polls verified feeds and merges new items into data/news.json."""
    logger.info("=== Starting Verified Tech & Cloud News Feed Ingestion ===")
    
    if NEWS_FILE.exists():
        with open(NEWS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {"news": []}
        
    existing_news = data.get("news", [])
    existing_urls = {item["url"] for item in existing_news}
    existing_ids = {item["id"] for item in existing_news}
    
    new_added = 0
    for feed in VERIFIED_FEEDS:
        items = fetch_feed_entries(feed, max_items=2)
        for it in items:
            if it["url"] not in existing_urls and it["id"] not in existing_ids:
                existing_news.insert(0, it)
                existing_urls.add(it["url"])
                existing_ids.add(it["id"])
                new_added += 1
                logger.info(f"[NEW INTELLIGENCE] [{it['company']}] {it['title'][:50]}...")
                
    now_iso = datetime.now(timezone.utc).isoformat()
    data["last_updated"] = now_iso
    data["last_sync"] = now_iso
    data["news"] = existing_news
    NEWS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(NEWS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        
    logger.info(f"=== News Feed Ingestion Complete: {len(existing_news)} total items ({new_added} fresh) ===")
    return existing_news

if __name__ == "__main__":
    update_news_feed()
