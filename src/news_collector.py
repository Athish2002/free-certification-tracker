"""
Autonomous News & Engineering Intelligence Collector for CertPulse.
Aggregates authentic, verified technical developments, research breakthroughs,
and financial updates directly from official cloud & tech giant engineering feeds.
Strictly bans clickbait and rumor aggregators.
"""

import re
import json
import logging
import defusedxml.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from urllib.parse import urlparse
from datetime import datetime, timezone
import hashlib
import httpx

logger = logging.getLogger("certpulse.news")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
NEWS_FILE = DATA_DIR / "news.json"

VERIFIED_FEEDS = [
    {
        "company": "Amazon Web Services",
        "vendor": "Amazon Web Services",
        "source": "AWS Architecture Blog",
        "category": "Infrastructure & Silicon",
        "feed_url": "https://aws.amazon.com/blogs/architecture/feed/",
        "allowed_domain": "aws.amazon.com",
        "source_domain": "aws.amazon.com",
        "impact_badge": "Architecture RFC"
    },
    {
        "company": "Google Cloud",
        "vendor": "Google Cloud",
        "source": "Google Cloud Blog",
        "category": "Infrastructure & Silicon",
        "feed_url": "https://cloudblog.withgoogle.com/rss/",
        "allowed_domain": "cloud.google.com",
        "source_domain": "cloud.google.com",
        "impact_badge": "Cloud Platform"
    },
    {
        "company": "GitHub",
        "vendor": "GitHub",
        "source": "GitHub Engineering Blog",
        "category": "Tech Development",
        "feed_url": "https://github.blog/feed/",
        "allowed_domain": "github.blog",
        "source_domain": "github.blog",
        "impact_badge": "Developer Tooling"
    },
    {
        "company": "Cisco",
        "vendor": "Cisco",
        "source": "Cisco Blogs",
        "category": "Tech Development",
        "feed_url": "https://blogs.cisco.com/feed",
        "allowed_domain": "blogs.cisco.com",
        "source_domain": "blogs.cisco.com",
        "impact_badge": "Enterprise Networking"
    },
    {
        "company": "Microsoft",
        "vendor": "Microsoft Azure",
        "source": "Azure Blog",
        "category": "Cloud & AI",
        "feed_url": "https://azurecomcdn.azureedge.net/en-us/blog/feed/",
        "allowed_domain": "microsoft.com",
        "source_domain": "microsoft.com",
        "impact_badge": "Cloud & AI Architecture"
    },
    {
        "company": "HashiCorp",
        "vendor": "HashiCorp",
        "source": "HashiCorp Blog",
        "category": "Infrastructure & DevOps",
        "feed_url": "https://www.hashicorp.com/blog/feed.xml",
        "allowed_domain": "hashicorp.com",
        "source_domain": "hashicorp.com",
        "impact_badge": "Infrastructure as Code"
    },
    {
        "company": "Databricks",
        "vendor": "Databricks",
        "source": "Databricks Blog",
        "category": "Data & AI",
        "feed_url": "https://www.databricks.com/feed.xml",
        "allowed_domain": "databricks.com",
        "source_domain": "databricks.com",
        "impact_badge": "Lakehouse & AI"
    },
    {
        "company": "Snowflake",
        "vendor": "Snowflake",
        "source": "Snowflake Blog",
        "category": "Data Cloud",
        "feed_url": "https://www.snowflake.com/blog/feed/",
        "allowed_domain": "snowflake.com",
        "source_domain": "snowflake.com",
        "impact_badge": "Data Cloud Architecture"
    },
    {
        "company": "Red Hat",
        "vendor": "Red Hat",
        "source": "Red Hat Press Releases",
        "category": "Linux & Enterprise",
        "feed_url": "https://www.redhat.com/en/rss/press-releases",
        "allowed_domain": "redhat.com",
        "source_domain": "redhat.com",
        "impact_badge": "Linux & Enterprise"
    }
]

# Alias for backward compatibility and test runner discovery
PRIMARY_FEEDS = VERIFIED_FEEDS

BANNED_CLICKBAIT_PATTERNS = [
    r"\bshocking\b", r"\binsane\b", r"\byou won't believe\b",
    r"\bunbelievable\b", r"\bsecret trick\b", r"\bgame changer\b",
    r"\bdestroy\b", r"\bmind blowing\b", r"\bexposed\b", r"\bviral\b"
]

DISALLOWED_PR_PATTERNS = [
    r"\bumfrage\b", r"\bétude\b", r"\brecognizes\b", r"\bawards?\b",
    r"\bpartner\b", r"\bfinancial results\b", r"\bquarterly\b",
    r"\bon my first day\b", r"\branking\b", r"\bhonors\b",
    r"\bcostumer\b", r"\bwinner\b", r"\bchannel\b", r"\bsponsor\b",
    r"\byou asked for more money\b", r"\bapac innovation awards\b",
    r"\bcongratulates\b", r"\bfinalists?\b", r"\bonderzoek\b"
]


def normalize_news_text(s: str) -> str:
    """Normalizes typography and cleans unicode artifacts for cross-platform stability."""
    if not s:
        return ""
    s = s.replace("\u2019", "'").replace("\u2018", "'")
    s = s.replace("\u201c", '"').replace("\u201d", '"')
    s = s.replace("\u2013", "-").replace("\u2014", "-")
    s = s.replace("\u2026", "...")
    s = s.replace("\ufffd", "").replace(chr(65533), "")
    return " ".join(s.strip().split())


def compute_news_fingerprint(title: str, domain: str = "") -> str:
    """Computes a deterministic content fingerprint (SHA-256) of normalized title and domain."""
    norm_title = " ".join(title.lower().strip().split())
    norm_domain = domain.lower().strip()
    raw = f"{norm_title}::{norm_domain}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def is_clean_headline(title: str) -> bool:
    """Verifies that a headline is objective and devoid of clickbait buzzwords."""
    lower = title.lower()
    for pat in BANNED_CLICKBAIT_PATTERNS:
        if re.search(pat, lower):
            return False
    return True

def parse_feed_date(pub_date: str) -> str:
    """Parses various RSS/Atom date formats into canonical ISO-8601 YYYY-MM-DD string."""
    if not pub_date:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")
    pub_date = pub_date.strip()
    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", pub_date)
    if date_match:
        return date_match.group(1)
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(pub_date)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        pass
    try:
        dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except Exception:
        pass
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

def fetch_feed_entries(feed_info: Dict[str, Any], max_items: int = 3) -> List[Dict[str, Any]]:
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
                
                iso_date = parse_feed_date(pub_date)
                
                title = normalize_news_text(title)
                clean_desc = normalize_news_text(clean_desc)

                # Verification Gates:
                content = f"{title} {clean_desc}".lower()
                if not title or not link or not is_clean_headline(title):
                    continue
                if any(re.search(pat, content) for pat in BANNED_CLICKBAIT_PATTERNS):
                    continue
                if any(re.search(pat, content) for pat in DISALLOWED_PR_PATTERNS):
                    continue
                # Ensure clean English typography (reject foreign press releases)
                if len(title) > 0 and (sum(1 for c in title if ord(c) < 128) / len(title)) < 0.95:
                    continue
                
                # Assert protocol is HTTPS and domain matches authentic FQDN / subdomain (VULN-04 Defense)
                parsed_url = urlparse(link)
                scheme = (parsed_url.scheme or "").lower()
                if scheme != "https":
                    continue
                hostname = (parsed_url.hostname or "").lower()
                allowed = feed_info["allowed_domain"].lower()
                if not hostname or not (hostname == allowed or hostname.endswith("." + allowed)):
                    continue
                
                slug_id = re.sub(r"[^a-z0-9]+", "-", f"{feed_info['company']}-{title[:30]}".lower()).strip("-")
                src_domain = feed_info.get("source_domain", feed_info["allowed_domain"])
                fingerprint = compute_news_fingerprint(title, src_domain)
                
                entries.append({
                    "id": slug_id,
                    "company": feed_info["company"],
                    "source": feed_info["source"],
                    "source_domain": src_domain,
                    "category": feed_info["category"],
                    "title": title,
                    "summary": clean_desc or f"Official technical update published by {feed_info['source']}.",
                    "published_date": iso_date,
                    "date": iso_date,
                    "url": link,
                    "impact_badge": feed_info["impact_badge"],
                    "content_fingerprint": fingerprint
                })
    except Exception as e:
        logger.warning(f"Failed to fetch feed {feed_info['source']}: {e}")
        
    return entries

def save_news_feed(data: Dict[str, Any], filepath: Optional[Union[str, Path]] = None) -> None:
    """
    Saves news feed data atomically using atomic_write_json with news_schema.json pre-flight validation.
    Ensures total_items and $schema conform to data/news_schema.json.
    """
    from src.io_utils import atomic_write_json
    target = Path(filepath) if filepath else NEWS_FILE
    schema_file = DATA_DIR / "news_schema.json"

    if "news" in data:
        data["total_items"] = len(data["news"])
    if "$schema" not in data:
        data["$schema"] = "./news_schema.json"
    if "last_updated" not in data:
        data["last_updated"] = datetime.now(timezone.utc).isoformat()

    atomic_write_json(target, data, schema_path=schema_file)

def update_news_feed(news_file: Optional[Union[str, Path]] = None) -> List[Dict[str, Any]]:
    """Polls verified feeds and merges new items into data/news.json."""
    logger.info("=== Starting Verified Tech & Cloud News Feed Ingestion ===")
    target_file = Path(news_file) if news_file else NEWS_FILE
    
    if target_file.exists():
        with open(target_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {
            "$schema": "./news_schema.json",
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "total_items": 0,
            "news": []
        }
        
    existing_news = data.get("news", [])
    existing_urls = {item["url"] for item in existing_news if "url" in item}
    existing_ids = {item["id"] for item in existing_news if "id" in item}
    existing_fingerprints = {
        item.get("content_fingerprint") or compute_news_fingerprint(item.get("title", ""), item.get("source_domain", ""))
        for item in existing_news
    }
    
    new_added = 0
    for feed in VERIFIED_FEEDS:
        items = fetch_feed_entries(feed, max_items=2)
        for it in items:
            fp = it.get("content_fingerprint") or compute_news_fingerprint(it.get("title", ""), it.get("source_domain", ""))
            if it["url"] not in existing_urls and it["id"] not in existing_ids and fp not in existing_fingerprints:
                existing_news.insert(0, it)
                existing_urls.add(it["url"])
                existing_ids.add(it["id"])
                existing_fingerprints.add(fp)
                new_added += 1
                logger.info(f"[NEW INTELLIGENCE] [{it['company']}] {it['title'][:50]}...")
                
    # Cap stored news items to the top 20 freshest items
    existing_news = existing_news[:100]
    data["news"] = existing_news
    data["total_items"] = len(existing_news)

    # Git churn defense: only touch disk file if new items were actually added or file was missing
    if new_added > 0 or not target_file.exists():
        now_iso = datetime.now(timezone.utc).isoformat()
        data["last_updated"] = now_iso
        data["last_sync"] = now_iso
        save_news_feed(data, target_file)
        logger.info(f"Saved {len(existing_news)} news items ({new_added} fresh) to {target_file}.")
    else:
        logger.info(f"No fresh news items found; preserved existing news timestamp to eliminate git churn.")
        
    logger.info(f"=== News Feed Ingestion Complete: {len(existing_news)} total items ===")
    return existing_news

if __name__ == "__main__":
    update_news_feed()
