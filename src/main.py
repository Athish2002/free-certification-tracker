"""
Main entry point for CertPulse automation.
Coordinates collector leads discovery, deep site inspection, and compiles the README and Web Dashboard.
"""

import json
import logging
from pathlib import Path
from src.collector import fetch_reddit_leads
from src.inspector import run_inspection
from src.builder import build_all

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("certpulse.main")

CANDIDATES_FILE = Path(__file__).resolve().parent.parent / "data" / "candidates.json"

def run_pipeline():
    logger.info("=== Starting CertPulse Autonomous Pipeline ===")
    
    # 1. Fetch community leads from Reddit Atom feeds
    leads = fetch_reddit_leads()
    if leads:
        logger.info(f"Saving {len(leads)} community leads to {CANDIDATES_FILE.name}...")
        CANDIDATES_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CANDIDATES_FILE, "w", encoding="utf-8") as f:
            json.dump({"total_candidates": len(leads), "leads": leads}, f, indent=2)

    # 2. Deep site inspection: Verify 200 OK, detect soft-404s, 'Closed' notices, and multi-layer authenticity
    logger.info("Running deep liveness, soft-404, and multi-layer authenticity inspection across all tracked URLs...")
    run_inspection()

    # 3. Ingest verified engineering and cloud intelligence feeds
    logger.info("Ingesting verified engineering and research dispatches...")
    from src.news_collector import update_news_feed
    update_news_feed()
            
    # 4. Re-compile README.md and Web Dashboard with updated statuses and news
    logger.info("Compiling README.md and GitHub Pages dashboard with inspection results...")
    build_all()
    
    logger.info("=== CertPulse Pipeline Completed Successfully ===")

if __name__ == "__main__":
    run_pipeline()
