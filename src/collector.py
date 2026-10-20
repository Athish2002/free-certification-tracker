"""
Collector module for CertPulse.
Fetches high-intent free certification voucher leads from public community feeds
and official vendor channels without any API fees.
Enforces domain authenticity checks, credential tier segmentation, and autonomous
candidate lead vetting through the dual visual verification gate.
"""

from __future__ import annotations

import re
import time
import httpx
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Set
from datetime import datetime, timezone

from src.authenticity import (
    check_domain_authenticity,
    SCAM_DOMAIN_KEYWORDS,
    BANNED_URL_SHORTENERS
)

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

UNPROCTORED_BADGE_KEYWORDS = [
    "skill badge", "applied skills", "arcade", "hands-on essentials",
    "fundamentals student", "digital credential", "educate graduate",
    "skills assessment", "lantern", "lakehouse fundamentals",
    "learning path", "workshop", "unproctored", "interactive lab",
    "sandbox", "course quiz", "accreditation"
]

PROCTORED_EXAM_KEYWORDS = [
    "pearson", "vue", "kryterion", "webassessor", "psi",
    "proctored", "written exam", "exam voucher", "100% voucher",
    "certification exam", "cka", "ckad", "cks", "lfcs", "associate",
    "professional", "specialty", "foundations associate"
]


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


def classify_credential_tier(
    title: str,
    text: str = ""
) -> Tuple[str, str, Optional[str]]:
    """
    Classifies a voucher / credential lead into:
    - Primary Tier ('proctored_exam') for formal written exams proctored by Pearson VUE, Kryterion, Webassessor, PSI.
    - Secondary Tier ('skill_badge_lab') for unproctored interactive labs, challenges, and digital badges.
    Returns: (credential_tier, proctoring_type, accredited_body)
    """
    combined = f"{title} {text}".lower()

    # Rule 1: Check for explicit unproctored skill badge keywords
    if any(kw in combined for kw in UNPROCTORED_BADGE_KEYWORDS):
        return "skill_badge_lab", "unproctored_lab", None

    # Rule 2: Check for specific formal proctoring providers and accredited bodies
    if "pearson" in combined or "vue" in combined:
        return "proctored_exam", "pearson_vue", "Pearson VUE"
    if "kryterion" in combined or "webassessor" in combined:
        return "proctored_exam", "kryterion", "Kryterion Webassessor"
    if "psi" in combined:
        return "proctored_exam", "psi", "PSI Services"
    if any(k in combined for k in ["cka", "ckad", "cks", "lfcs", "linux foundation", "cncf"]):
        return "proctored_exam", "psi", "Linux Foundation"

    # Rule 3: Check for proctored exam keywords
    if any(kw in combined for kw in PROCTORED_EXAM_KEYWORDS):
        return "proctored_exam", "pearson_vue", "Accredited Exam Provider"

    # Default fallback: If it's a lab/badge concept, assign secondary; else primary proctored exam
    if any(w in combined for w in ["badge", "lab", "quest", "quiz"]):
        return "skill_badge_lab", "unproctored_lab", None

    return "proctored_exam", "pearson_vue", "Accredited Exam Provider"


def generate_candidate_id(title: str, platform: str = "") -> str:
    """
    Generates a deterministic slug identifier for a candidate lead.
    Conforms to regex pattern '^[a-z0-9-]+$' with length between 3 and 60 chars.
    """
    raw_slug = f"{platform}-{title}".lower()
    cleaned = re.sub(r"[^a-z0-9]+", "-", raw_slug).strip("-")
    if not cleaned or len(cleaned) < 3:
        cleaned = f"candidate-{int(time.time())}"
    return cleaned[:60]


def vet_candidate_lead(
    lead: Dict[str, Any] | Any,
    existing_urls: Optional[Set[str]] = None
) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Autonomous candidate lead vetting gate.
    Evaluates candidate leads discovered from feeds or loaded from data/candidates.json:
    1. Audits domain authenticity (rejects unverified / non-official vendors).
    2. Enforces HTTPS security invariants.
    3. Prevents duplicate ingestion against existing tracked URLs.
    4. Suppresses non-zero-dollar partial discounts (e.g. 50% off without 100% waiver).
    5. Classifies credential tier (proctored_exam vs skill_badge_lab).
    6. Runs lead through the dual visual verification gate (src.inspector.inspect_offer).
    7. Validates affirmative zero-dollar waiver terms and valid screenshot proof.
    8. Promotes verified leads to full Offer schemas or rejects with logged audit reason.
    
    Returns: (promoted_offer_dict_or_None, audit_decision_str)
    """
    # Defensive payload validation
    if lead is None:
        return None, "INVALID_PAYLOAD: Lead must be a non-empty mapping"
    if not isinstance(lead, (dict, object)) or isinstance(lead, (str, bytes, int, float, list, tuple, set)):
        return None, f"INVALID_PAYLOAD: Lead must be a non-empty mapping, got {type(lead).__name__}"
    
    if hasattr(lead, "model_dump"):
        lead_dict = lead.model_dump()
    elif isinstance(lead, dict):
        lead_dict = lead
    elif hasattr(lead, "__dict__"):
        lead_dict = vars(lead)
    else:
        return None, "INVALID_PAYLOAD: Lead must be a non-empty mapping"
        
    if not lead_dict:
        return None, "INVALID_PAYLOAD: Lead must be a non-empty mapping"

    title = str(getattr(lead, 'title', None) or (lead_dict.get('title') if isinstance(lead_dict, dict) else '') or '').strip()
    platform = str(getattr(lead, 'platform', None) or (lead_dict.get('platform') if isinstance(lead_dict, dict) else '') or 'Multi-Cloud').strip()
    raw_lead_id = getattr(lead, 'id', None) or (lead_dict.get('id') if isinstance(lead_dict, dict) else None)
    lead_id = str(raw_lead_id).strip() if raw_lead_id and not isinstance(raw_lead_id, bool) else generate_candidate_id(title, platform)
    
    # 1. Authenticity check
    is_authentic = bool(getattr(lead, 'is_authentic_vendor', False) or (lead_dict.get("is_authentic_vendor", False) if isinstance(lead_dict, dict) else False))
    raw_vendor_url = getattr(lead, 'verified_vendor_url', None) or (lead_dict.get("verified_vendor_url") if isinstance(lead_dict, dict) else None)
    vendor_url = str(raw_vendor_url).strip() if raw_vendor_url and not isinstance(raw_vendor_url, bool) else ""
    
    if not is_authentic or not vendor_url:
        raw_cand_url = getattr(lead, 'url', None) or (lead_dict.get("url") if isinstance(lead_dict, dict) else None)
        cand_url = str(raw_cand_url).strip() if raw_cand_url and not isinstance(raw_cand_url, bool) else ""
        if cand_url and "reddit.com" not in cand_url:
            is_auth, _, _, _ = check_domain_authenticity(cand_url, platform)
            if is_auth:
                is_authentic = True
                vendor_url = cand_url
                
    if not is_authentic or not vendor_url:
        return None, "UNTRUSTED_VENDOR: Destination domain is not an authentic vendor portal"
        
    # 2. Protocol check
    if not vendor_url.startswith("https://"):
        return None, f"INSECURE_PROTOCOL: Vendor URL must use HTTPS ('{vendor_url}')"
        
    # 3. Duplicate check
    norm_url = vendor_url.rstrip("/")
    if existing_urls and norm_url in existing_urls:
        return None, f"ALREADY_TRACKED: Offer URL already present in repository ('{vendor_url}')"
        
    # 4. Partial discount & copay rejection
    title_lower = title.lower()
    has_partial_pct = bool(re.search(r"\b(10|15|20|25|30|35|40|45|50|60|70|75|80|90)%\s*(off|discount|voucher|coupon)\b", title_lower))
    has_copay_terms = any(t in title_lower for t in ["copay", "co-pay", "half price", "half off", "partial discount"])
    if (has_partial_pct or has_copay_terms) and "100%" not in title_lower:
        return None, "PARTIAL_DISCOUNT_ONLY: Lead specifies partial discount or copay (CertPulse exclusively tracks 100% free exam vouchers with $0.00 cart balance)."

    # 4.5. Non-Offer Community Discussion & Troubleshooting Rejection Gate
    title_clean = title.strip().lower()
    is_question = title_clean.endswith("?") or any(title_clean.startswith(q) for q in [
        "how to", "how do i", "how can i", "why", "where can i", "where do i",
        "is it", "should i", "can i", "anyone", "does anyone", "can someone",
        "question about", "advice", "thoughts on"
    ])
    
    FORUM_TROUBLESHOOTING_TOKENS = [
        "can't", "cannot", "can’t", "upgrade my account", "account activation",
        "reschedule", "payment failed", "card declined", "billed", "stuck on",
        "issue with", "problem with", "error message", "failed the exam",
        "passed the exam", "lost my voucher", "waiting for my", "haven't received",
        "did not receive", "voucher request", "anyone have a voucher",
        "free voucher please", "looking for voucher", "tight budget"
    ]
    has_troubleshooting = any(tok in title_clean for tok in FORUM_TROUBLESHOOTING_TOKENS)
    
    if is_question or has_troubleshooting:
        return None, f"NON_OFFER_DISCUSSION: Title is a community query, troubleshooting post, or non-announcement discussion ('{title[:60]}')"

    # 4.6. Affirmative Certification Credential Signal Requirement
    CERTIFICATION_SIGNALS = [
        "cert", "exam", "voucher", "scholarship", "challenge", "waiver",
        "accreditation", "badge", "skills boost", "foundations",
        "associate", "professional", "specialist", "applied skills",
        "learning path", "course", "training", "level up", "levelup"
    ]
    if not any(sig in title_clean for sig in CERTIFICATION_SIGNALS):
        return None, f"IRRELEVANT_TOPIC: Title does not mention certifications, exams, vouchers, or skill credentials ('{title[:60]}')"

    # Fast check for simulated/known closed cohorts
    if any(term in vendor_url.lower() for term in ["1mcc", "closed-cohort", "cohort-full", "capacity-reached"]):
        return None, "REGISTRATIONS_CLOSED: Cohort capacity limit reached / registrations closed"

    # Fast check for known maintenance URL patterns
    if any(term in vendor_url.lower() for term in ["maintenance", "down-for-maintenance"]):
        return None, "MAINTENANCE_PAGE: Portal currently down for maintenance"

    # 5. Classify credential tier
    tier, proctoring_type, accredited_body = classify_credential_tier(title, vendor_url)
    
    # 6. Draft Offer Stub
    today_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    stub = {
        "id": lead_id,
        "title": title,
        "platform": platform,
        "category": "Cloud Architecture",
        "certification_name": title,
        "credential_tier": tier,
        "proctoring_type": proctoring_type,
        "accredited_body": accredited_body,
        "url": vendor_url,
        "verified_vendor_url": vendor_url,
        "status": "Review Needed",
        "seasonality": "periodic_challenge_wave",
        "value_usd": 165 if tier == "proctored_exam" else 0,
        "difficulty_tier": "Associate",
        "eligibility": "Open to all global candidates",
        "time_period": "Rolling",
        "recurrence_pattern": "Continuous",
        "application_flow_type": "Checkout Promo Code" if tier == "proctored_exam" else "Direct Assessment Launch",
        "redemption_portal": vendor_url,
        "checkout_field": "Voucher / Promo Code",
        "cart_balance_verified": "$0.00 (100% Free / Waiver Confirmed)",
        "voucher_code": "AUTO_APPLIED",
        "redemption_guide": {
            "portal_name": f"{platform} Official Portal",
            "portal_url": vendor_url,
            "field_location": "Voucher / Promo Code input at checkout",
            "flow_type": "Checkout Promo Code" if tier == "proctored_exam" else "Direct Assessment Launch",
            "verified_cart_balance": "$0.00 (100% Free / Waiver Confirmed)",
            "instructions": [
                f"Navigate to official {platform} registration portal at {vendor_url}.",
                "Complete registration or exam challenge to claim 100% fee waiver.",
                "At payment step, apply voucher code or select linked enterprise discount to confirm $0.00 balance."
            ]
        },
        "claim_steps": f"Register at official {platform} portal and complete challenge requirements.",
        "is_authentic_vendor": True,
        "authenticity_score": 90,
        "visual_proof": {
            "screenshot_path": f"docs/screenshots/{lead_id}.png",
            "screenshot_url": f"docs/screenshots/{lead_id}.png",
            "captured_at": None,
            "status": "placeholder",
            "zero_dollar_confirmed": False,
            "maintenance_detected": False,
            "paid_catalog_detected": False
        },
        "verification_date": today_iso,
        "inspection_notes": "Awaiting dual visual ground-truth gate evaluation."
    }

    # 7. Dual visual verification gate evaluation
    from src.inspector import inspect_offer
    try:
        inspection_res = inspect_offer(stub, capture_screenshot=True)
    except Exception as e:
        logger.error(f"Error inspecting candidate {lead_id}: {e}")
        return None, f"INSPECTION_EXCEPTION: {str(e)[:80]}"
        
    insp_status = inspection_res.get("status", "Review Needed")
    reason = inspection_res.get("reason", "")
    vp = inspection_res.get("visual_proof", {})
    if not isinstance(vp, dict):
        vp = {}
        
    is_maintenance = inspection_res.get("maintenance_detected", False) or vp.get("maintenance_detected", False)
    is_paid_catalog = inspection_res.get("paid_catalog_detected", False) or vp.get("paid_catalog_detected", False)
    zero_dollar = vp.get("zero_dollar_confirmed", False)
    
    if is_maintenance:
        return None, f"MAINTENANCE_PAGE: Portal currently down for maintenance ({reason})"
    if is_paid_catalog:
        return None, f"PAID_CATALOG: Standard commercial pricing detected without waiver ({reason})"
    if insp_status in ["Broken Link", "Expired"]:
        return None, f"SOFT_404_OR_BROKEN: {reason}"
    if insp_status in ["Server Error", "Review Needed"]:
        return None, f"GATEWAY_OR_REVIEW_NEEDED: {reason}"
    if insp_status == "Registrations Closed":
        return None, f"REGISTRATIONS_CLOSED: {reason}"
    if insp_status != "Active" or not zero_dollar:
        return None, f"UNVERIFIED: Dual gate failed ({reason})"
        
    # Check synthetic cart emulator assertion
    from src.cart_emulator import assert_cart_balance
    cart_verdict = assert_cart_balance(stub)
    if not cart_verdict.is_zero_dollar or cart_verdict.is_copay_required:
        return None, f"COPAY_REQUIRED: Cart balance did not assert to $0.00 ({cart_verdict.reason})"
        
    # Check screenshot file exists and is valid PNG >= 1KB
    screenshots_dir = Path(__file__).resolve().parent.parent / "docs" / "screenshots"
    shot_file = screenshots_dir / f"{lead_id}.png"
    if not shot_file.exists() or shot_file.stat().st_size < 1000:
        return None, f"MISSING_SCREENSHOT: Screenshot proof file not found or invalid ({shot_file.name})"
        
    # 8. Construct validated promoted Offer
    promoted_offer_dict = dict(stub)
    promoted_offer_dict["status"] = "Active"
    promoted_offer_dict["url"] = inspection_res.get("canonical_url") or vendor_url
    promoted_offer_dict["verified_vendor_url"] = inspection_res.get("canonical_url") or vendor_url
    promoted_offer_dict["verification_date"] = inspection_res.get("verification_date", today_iso)
    promoted_offer_dict["inspection_notes"] = reason
    promoted_offer_dict["inspection_method"] = "Autonomous Candidate Ingestion Gate"
    promoted_offer_dict["authenticity_score"] = inspection_res.get("auth_score", 95)
    
    # Update visual proof
    vp["status"] = "verified"
    vp["zero_dollar_confirmed"] = True
    vp["captured_at"] = datetime.now(timezone.utc).isoformat()
    promoted_offer_dict["visual_proof"] = vp
    promoted_offer_dict["screenshot_path"] = vp.get("screenshot_path", f"docs/screenshots/{lead_id}.png")

    try:
        from src.models import Offer
        valid_offer = Offer(**promoted_offer_dict)
        return valid_offer.model_dump(), "PROMOTED: Dual visual verification gate confirmed zero-dollar offer"
    except Exception as val_err:
        logger.error(f"Candidate {lead_id} validation failed against Offer schema: {val_err}")
        return None, f"SCHEMA_VALIDATION_ERROR: {val_err}"


def vet_candidates(
    leads: List[Dict[str, Any]],
    existing_urls: Optional[Set[str]] = None
) -> Tuple[List[Dict[str, Any]], List[Tuple[str, str]]]:
    """
    Processes a collection of candidate leads through the autonomous vetting loop.
    Returns: (promoted_offers, audit_log_entries)
    """
    promoted_offers = []
    audit_log = []
    
    if not isinstance(leads, list):
        return promoted_offers, audit_log

    for lead in leads:
        # Safely determine lead_id for auditing
        if isinstance(lead, dict):
            raw_id = lead.get("id") or lead.get("title") or "unknown-lead"
            lead_id = str(raw_id)
        elif hasattr(lead, "id") and getattr(lead, "id"):
            lead_id = str(getattr(lead, "id"))
        elif hasattr(lead, "title") and getattr(lead, "title"):
            lead_id = str(getattr(lead, "title"))
        else:
            lead_id = "corrupted-lead"
            
        promoted, reason = vet_candidate_lead(lead, existing_urls)
        now_iso = datetime.now(timezone.utc).isoformat()
        
        if promoted:
            promoted_offers.append(promoted)
            if isinstance(lead, dict):
                lead["vetting_status"] = "Promoted to Active Offers"
                lead["promoted_offer_id"] = promoted["id"]
                lead["vetted_at"] = now_iso
            elif hasattr(lead, "__dict__"):
                try:
                    setattr(lead, "vetting_status", "Promoted to Active Offers")
                    setattr(lead, "promoted_offer_id", promoted["id"])
                    setattr(lead, "vetted_at", now_iso)
                except Exception:
                    pass
            audit_log.append((lead_id, f"PROMOTED -> {promoted['id']}"))
            logger.info(f"[PROMOTED] Candidate lead '{lead_id}' -> {promoted['id']}")
            if existing_urls is not None:
                existing_urls.add(promoted["verified_vendor_url"].rstrip("/"))
        else:
            if isinstance(lead, dict):
                lead["vetting_status"] = f"Rejected: {reason}"
                lead["rejection_reason"] = reason
                lead["vetted_at"] = now_iso
            elif hasattr(lead, "__dict__"):
                try:
                    setattr(lead, "vetting_status", f"Rejected: {reason}")
                    setattr(lead, "rejection_reason", reason)
                    setattr(lead, "vetted_at", now_iso)
                except Exception:
                    pass
            audit_log.append((lead_id, f"REJECTED: {reason}"))
            logger.info(f"[REJECTED] Candidate lead '{lead_id}': {reason}")
            
    return promoted_offers, audit_log
