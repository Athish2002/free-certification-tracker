"""
Main entry point for CertPulse automation.
Coordinates collector leads discovery, autonomous candidate vetting gate,
deep site inspection with self-healing recovery proof engine, and compiles
the README and Web Dashboard.
"""

from __future__ import annotations

import re
import sys
import json
import logging
import argparse
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, Set
from datetime import datetime, timezone

from src.io_utils import atomic_write_json
from src.collector import fetch_reddit_leads, vet_candidates, vet_candidate_lead
from src.inspector import run_inspection, inspect_offer
from src.builder import build_all

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("certpulse.main")

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT_DIR / "data" / "offers.json"
SCHEMA_FILE = ROOT_DIR / "data" / "schema.json"
CANDIDATES_FILE = ROOT_DIR / "data" / "candidates.json"
SCREENSHOTS_DIR = ROOT_DIR / "docs" / "screenshots"


def apply_self_healing(
    offer: Dict[str, Any],
    inspection_res: Dict[str, Any],
    proof_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Self-Healing Recovery Engine:
    During scheduled refresh, if an offer transitions from a triage/outage state
    ('Review Needed', 'Registrations Closed', 'Broken Link', or 'Expired') back to
    'Active' (e.g. Oracle University re-opens, or Salesforce launches a new cohort),
    update status to 'Active', capture/attach a fresh screenshot with ISO timestamp,
    and log the self-healing event on the Offer.
    """
    updated = dict(offer)
    old_status = updated.get("status")
    new_status = inspection_res.get("status")

    insp_vp = inspection_res.get("visual_proof") if isinstance(inspection_res.get("visual_proof"), dict) else {}
    zero_dollar = inspection_res.get(
        "zero_dollar_confirmed",
        insp_vp.get("zero_dollar_confirmed", True if new_status == "Active" else False)
    )
    maintenance = inspection_res.get(
        "maintenance_detected",
        insp_vp.get("maintenance_detected", False)
    )
    paid_catalog = inspection_res.get(
        "paid_catalog_detected",
        insp_vp.get("paid_catalog_detected", False)
    )

    triage_statuses = ["Review Needed", "Registrations Closed", "Broken Link", "Expired"]
    if old_status in triage_statuses and new_status == "Active" and zero_dollar and not maintenance and not paid_catalog:
        now_iso = datetime.now(timezone.utc).isoformat()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        offer_id = updated.get("id", "healed-offer")
        shot_path = proof_path or updated.get("screenshot_path", f"docs/screenshots/{offer_id}.png")

        updated["status"] = "Active"
        updated["verification_date"] = today
        updated["last_zero_dollar_confirmed_date"] = today
        updated["screenshot_path"] = shot_path

        # Ensure visual proof metadata is refreshed directly from inspection result
        vp = updated.get("visual_proof")
        if isinstance(vp, dict):
            vp["status"] = "verified"
            vp["captured_at"] = now_iso
            vp["zero_dollar_confirmed"] = zero_dollar
            vp["maintenance_detected"] = maintenance
            vp["paid_catalog_detected"] = paid_catalog
            vp["screenshot_path"] = shot_path
            updated["visual_proof"] = vp
        else:
            updated["visual_proof"] = {
                "screenshot_path": shot_path,
                "screenshot_url": shot_path,
                "captured_at": now_iso,
                "status": "verified",
                "zero_dollar_confirmed": zero_dollar,
                "maintenance_detected": maintenance,
                "paid_catalog_detected": paid_catalog
            }

        updated["self_healing_event"] = {
            "previous_status": old_status,
            "healed_status": "Active",
            "timestamp": now_iso,
            "proof_image": shot_path
        }
        logger.warning(
            f"[SELF-HEALING RECOVERY] Offer '{updated.get('title')}' successfully recovered from "
            f"'{old_status}' to 'Active'. Fresh visual proof attached at {shot_path}."
        )
    elif new_status in ["Active", "Registrations Closed", "Broken Link", "Expired", "Review Needed"]:
        if new_status == "Active" and (not zero_dollar or maintenance or paid_catalog):
            updated["status"] = "Review Needed"
            updated["inspection_notes"] = "Inspection did not confirm affirmative zero-dollar terms"
        else:
            updated["status"] = new_status
            if new_status == "Active" and zero_dollar:
                updated["last_zero_dollar_confirmed_date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            if "reason" in inspection_res:
                updated["inspection_notes"] = inspection_res["reason"]
        updated["verification_date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    return updated


def normalize_url(url: str) -> str:
    """Normalizes URL for duplicate detection and idempotent matching."""
    if not url:
        return ""
    try:
        from urllib.parse import urlparse
        p = urlparse(url.strip())
        netloc = p.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        path = p.path.rstrip("/")
        norm = f"{p.scheme.lower()}://{netloc}{path}"
        if p.query:
            norm += f"?{p.query}"
        return norm
    except Exception:
        return url.strip().rstrip("/")


def ingest_and_vet_candidates(
    candidates_file: Optional[Path] = None,
    offers_file: Optional[Path] = None
) -> Tuple[int, int]:
    """
    Autonomous Candidate Vetting Loop:
    1. Loads discovered community leads from data/candidates.json.
    2. Runs each lead through the dual visual verification gate (vet_candidates / inspect_offer).
    3. If affirmative zero-dollar terms and screenshot are confirmed, promotes the candidate lead
       to an Offer in data/offers.json with appropriate credential_tier (proctored_exam vs skill_badge_lab).
    4. If lead fails verification (maintenance page, paid catalog, soft-404, or unverified),
       rejects it and logs the audit reason directly in data/candidates.json.
       
    Returns: (promoted_count, rejected_count)
    """
    c_file = candidates_file or CANDIDATES_FILE
    o_file = offers_file or DATA_FILE
    
    if not c_file.exists() or c_file.stat().st_size == 0:
        logger.info(f"Empty or missing candidates file at {c_file}. Skipping candidate vetting.")
        return 0, 0
        
    try:
        with open(c_file, "r", encoding="utf-8") as f:
            cand_data = json.load(f)
    except (json.JSONDecodeError, ValueError) as err:
        logger.error(f"Corrupted candidates file at {c_file}: {err}")
        return 0, 0

    if not isinstance(cand_data, dict):
        logger.warning(f"Invalid format in candidates file {c_file}: expected JSON object.")
        return 0, 0
        
    leads = cand_data.get("leads", [])
    if not leads or not isinstance(leads, list):
        logger.info("No candidate leads present to vet.")
        return 0, 0
        
    offers_data = {"offers": []}
    if o_file.exists():
        with open(o_file, "r", encoding="utf-8") as f:
            offers_data = json.load(f)
            
    existing_urls = set()
    for o in offers_data.get("offers", []):
        for u in [o.get("url"), o.get("verified_vendor_url"), o.get("direct_verified_url")]:
            if u:
                existing_urls.add(u.rstrip("/"))
                existing_urls.add(normalize_url(u))
    
    logger.info(f"Running autonomous candidate vetting loop on {len(leads)} community leads...")
    promoted_offers, audit_log = vet_candidates(leads, existing_urls)
    
    promoted_count = len(promoted_offers)
    rejected_count = len(audit_log) - promoted_count
    
    # Ingest promoted offers into offers database with idempotency check
    if promoted_count > 0:
        logger.info(f"Promoting {promoted_count} verified zero-dollar certification offers to {o_file.name}...")
        existing_offer_ids = {o.get("id") for o in offers_data.get("offers", [])}
        seen_promoted = set()
        actually_promoted = 0
        for new_offer in promoted_offers:
            cand_u = new_offer.get("verified_vendor_url") or new_offer.get("url", "")
            norm_u = normalize_url(cand_u)
            if new_offer.get("id") in existing_offer_ids or norm_u in seen_promoted:
                logger.info(f"[DUPLICATE] Candidate lead already tracked: '{cand_u}'")
                continue
            offers_data["offers"].append(new_offer)
            existing_offer_ids.add(new_offer.get("id"))
            seen_promoted.add(norm_u)
            actually_promoted += 1
            
        now_iso = datetime.now(timezone.utc).isoformat()
        if "last_updated" not in offers_data:
            offers_data["last_updated"] = now_iso
        if "$schema" not in offers_data:
            offers_data["$schema"] = "./schema.json"
        offers_data["total_offers"] = len(offers_data.get("offers", []))

        schema_to_validate = SCHEMA_FILE if SCHEMA_FILE.exists() else None
        atomic_write_json(o_file, offers_data, schema_path=schema_to_validate)
        
    # Persist updated vetting status and audit records to candidates.json
    cand_data["total_candidates"] = len(leads)
    cand_data["last_vetted"] = datetime.now(timezone.utc).isoformat()
    cand_data["vetted_promoted_count"] = promoted_count
    cand_data["vetted_rejected_count"] = rejected_count
    
    atomic_write_json(c_file, cand_data, schema_path=None)
    
    logger.info(
        f"Candidate vetting finished: {promoted_count} promoted to Active, "
        f"{rejected_count} rejected with logged audit reasons."
    )
    return promoted_count, rejected_count


def run_self_healing_refresh(use_headless: bool = True) -> Tuple[int, int]:
    """
    Executes the scheduled site inspection pass, monitoring for portal recovery
    and executing self-healing visual proof capture.
    """
    logger.info("Running headless Playwright DOM inspection, capacity checks, and self-healing engine across tracked URLs...")
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        initial_data = json.load(f)
        
    previous_statuses = {o.get("id"): o.get("status") for o in initial_data.get("offers", [])}
    
    # Run the comprehensive inspection suite
    updated_offers = run_inspection(use_headless=use_headless)
    
    # Audit for self-healed transitions
    healed_count = 0
    total_active = 0
    for offer in updated_offers:
        oid = offer.get("id")
        old_status = previous_statuses.get(oid, "Active")
        cur_status = offer.get("status")
        
        if cur_status == "Active":
            total_active += 1
            if old_status in ["Review Needed", "Registrations Closed", "Broken Link", "Expired"]:
                healed_count += 1
                logger.warning(f"Self-healed offer confirmed: {offer.get('title')} ({old_status} -> Active)")
                
    return healed_count, total_active


def run_pipeline(
    dry_run: bool = False,
    skip_leads: bool = False,
    skip_inspection: bool = False,
    vet_only: bool = False
) -> None:
    """
    Executes the complete CertPulse Autonomous Pipeline:
    1. Reddit feed scraping for voucher signals
    2. Autonomous candidate lead vetting gate
    3. Self-healing site inspection & Playwright screenshot capture
    4. News radar updates
    5. README and Web Dashboard generation
    """
    logger.info("=== Starting CertPulse Autonomous Pipeline ===")
    if dry_run:
        logger.info("[DRY RUN MODE ACTIVE] Actions will be simulated without disk mutation.")

    # 1. Fetch community leads from Reddit Atom feeds and official vendor blogs
    if not skip_leads and not dry_run:
        logger.info("Scanning public community feeds and vendor blogs for new certification vouchers...")
        from src.collector import fetch_reddit_leads, fetch_vendor_blog_leads
        leads = fetch_reddit_leads()
        try:
            blog_leads = fetch_vendor_blog_leads()
            leads.extend(blog_leads)
        except Exception as blog_err:
            logger.warning(f"Vendor blog leads fetching failed: {blog_err}")

        if leads:
            logger.info(f"Saving {len(leads)} community leads to {CANDIDATES_FILE.name}...")
            CANDIDATES_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CANDIDATES_FILE, "w", encoding="utf-8") as f:
                json.dump({"total_candidates": len(leads), "leads": leads}, f, indent=2)

    # 2. Autonomous Candidate Vetting Loop
    promoted_count, rejected_count = 0, 0
    if not dry_run:
        logger.info("Evaluating candidate leads against dual visual ground-truth gate...")
        promoted_count, rejected_count = ingest_and_vet_candidates()

    if vet_only:
        logger.info("Vet-only requested. Skipping full site inspection and build.")
        logger.info("=== CertPulse Pipeline Completed Successfully ===")
        return

    # 3. Deep site inspection & self-healing recovery engine
    healed_count = 0
    if not skip_inspection and not dry_run:
        healed_count, _ = run_self_healing_refresh(use_headless=True)
    elif dry_run:
        logger.info("[DRY RUN] Skipping Playwright DOM inspection.")

    # 3.5 Authoritative Online Truth Oracle Corroboration Gate (with 30s circuit breaker)
    if not dry_run:
        logger.info("Executing Truth Oracle policy corroboration and anti-misleading audit...")
        import concurrent.futures
        from src.truth_oracle import audit_and_enrich_offers
        if DATA_FILE.exists():
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                o_data = json.load(f)
            initial_offers = o_data.get("offers", [])
            corrections_applied = 0
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(audit_and_enrich_offers, initial_offers, strict_enforcement=True)
                    enriched, summary = future.result(timeout=30.0)
                o_data["offers"] = enriched
                corrections_applied = summary.get("corrections_applied", 0)
                logger.info(f"Truth Oracle corroboration complete: {corrections_applied} corrections applied.")
            except (concurrent.futures.TimeoutError, TimeoutError):
                logger.error("Truth Oracle corroboration timed out after 30 seconds. Marking oracle_timeout on offers.")
                for off in o_data.get("offers", []):
                    off["oracle_timeout"] = True
                corrections_applied = 1

            # Substantive change check: only mutate on-disk data if statuses, urls, prices, or policies changed
            def _has_substantive_changes(old_list, new_list):
                if len(old_list) != len(new_list):
                    return True
                keys = ("id", "status", "url", "direct_verified_url", "verified_vendor_url", "price", "inspection_notes")
                old_map = {o["id"]: {k: o.get(k) for k in keys} for o in old_list if "id" in o}
                new_map = {o["id"]: {k: o.get(k) for k in keys} for o in new_list if "id" in o}
                return old_map != new_map

            has_changes = (
                promoted_count > 0 or
                healed_count > 0 or
                corrections_applied > 0 or
                _has_substantive_changes(initial_offers, o_data.get("offers", []))
            )

            if has_changes:
                now_iso = datetime.now(timezone.utc).isoformat()
                o_data["last_truth_corroborated"] = now_iso
                o_data["last_sync"] = now_iso
                o_data["last_updated"] = now_iso
                if "$schema" not in o_data:
                    o_data["$schema"] = "./schema.json"
                o_data["total_offers"] = len(o_data.get("offers", []))
                schema_to_validate = SCHEMA_FILE if SCHEMA_FILE.exists() else None
                atomic_write_json(DATA_FILE, o_data, schema_path=schema_to_validate)
                logger.info("Saved updated offers data to disk (substantive changes detected).")
            else:
                logger.info("No substantive offer changes detected; preserved on-disk data to eliminate git churn.")

    # 3.6 Compact and rotate audit ledger
    if not dry_run:
        try:
            from src.audit_ledger import compact_audit_log
            compact_audit_log()
        except Exception as cl_err:
            logger.warning(f"Audit log compaction failed: {cl_err}")

    # 4. Ingest verified engineering and cloud intelligence feeds
    if not dry_run:
        logger.info("Ingesting verified engineering and research dispatches...")
        from src.news_collector import update_news_feed
        update_news_feed()
    else:
        logger.info("[DRY RUN] Skipping news feed update.")

    # 5. Re-compile README.md and Web Dashboard with updated statuses and news
    if not dry_run:
        logger.info("Compiling README.md and GitHub Pages dashboard with inspection results...")
        build_all(skip_if_unchanged=True)
    else:
        logger.info("[DRY RUN] Skipping README and dashboard compile.")

    logger.info("=== CertPulse Pipeline Completed Successfully ===")


def main() -> None:
    """CLI Entrypoint with comprehensive command-line options."""
    parser = argparse.ArgumentParser(
        prog="python -m src.main",
        description="CertPulse Autonomous Certification & Voucher Intelligence Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.main                    # Run full 12-hour pipeline (refresh, vet, build)
  python -m src.main --dry-run          # Dry-run pipeline without modifying data
  python -m src.main --vet-only         # Only execute autonomous candidate lead vetting
  python -m src.main --skip-leads       # Skip scraping Reddit feeds, run vetting on existing
  python -m src.main --skip-inspection  # Ingest feeds and compile without re-inspecting URLs
        """
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate execution without mutating JSON datasets, screenshots, or dashboard."
    )
    parser.add_argument(
        "--skip-leads",
        action="store_true",
        help="Skip fetching new Reddit Atom leads; process existing candidates only."
    )
    parser.add_argument(
        "--skip-inspection",
        action="store_true",
        help="Skip headless Playwright DOM inspection of existing offers."
    )
    parser.add_argument(
        "--vet-only",
        action="store_true",
        help="Only run autonomous candidate lead vetting loop, skipping site inspection."
    )

    args = parser.parse_args()
    run_pipeline(
        dry_run=args.dry_run,
        skip_leads=args.skip_leads,
        skip_inspection=args.skip_inspection,
        vet_only=args.vet_only
    )


if __name__ == "__main__":
    main()
