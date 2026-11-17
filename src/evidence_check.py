"""
Quote check: is the sentence recorded as evidence still on the vendor page?

Each Active policy note in data/curated_policies.json records `evidence_url` and `evidence_quote`,
the sentence a reader copied from the vendor page. This module loads that page in headless
Chromium and looks for the sentence in the page title and visible text.

What a result means:
- found: the sentence is still on the page. The terms it states were true when it was read and
  the vendor has not removed the sentence. It does not prove the offer is open to a given person.
- not found: the page loaded with readable text and the sentence is not there. After
  MISSES_BEFORE_DEMOTION consecutive runs the offer stops being shown as Active.
- unreadable: the page did not load or showed almost no text (blocked, login wall, slow render).
  This is recorded but never counts for or against the offer.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("certpulse.evidence_check")

MISSES_BEFORE_DEMOTION = 2
MIN_READABLE_CHARS = 200

FOUND = "found"
NOT_FOUND = "not_found"
UNREADABLE = "unreadable"

# Curly quotes, dashes and non-breaking spaces mapped to their plain forms (by code point).
_PUNCT_MAP = {
    0x2018: "'",
    0x2019: "'",
    0x201C: '"',
    0x201D: '"',
    0x2013: "-",
    0x2014: "-",
    0x2212: "-",
    0x00A0: " ",
}


def normalize_text(text: str) -> str:
    """Lower-cases, unifies quote and dash characters, and collapses whitespace."""
    text = unicodedata.normalize("NFKC", text or "").translate(_PUNCT_MAP)
    return re.sub(r"\s+", " ", text).strip().lower()


def quote_on_page(quote: str, page_text: str, page_title: str = "") -> bool:
    """True when the whole quote appears in the page title or visible text after normalization."""
    needle = normalize_text(quote)
    if not needle:
        return False
    return needle in normalize_text(page_title) or needle in normalize_text(page_text)


def classify_page(quote: str, page_text: str | None, page_title: str = "") -> str:
    """Returns FOUND, NOT_FOUND or UNREADABLE for one loaded page."""
    if page_text is None:
        return UNREADABLE
    if quote_on_page(quote, page_text, page_title):
        return FOUND
    if len(page_text.strip()) < MIN_READABLE_CHARS:
        return UNREADABLE
    return NOT_FOUND


def update_record(previous: dict[str, Any] | None, result: str, now: datetime | None = None) -> dict[str, Any]:
    """
    Folds one check result into the stored record for an offer.
    consecutive_misses counts NOT_FOUND results in a row; FOUND resets it; UNREADABLE leaves it unchanged.
    """
    prev = previous if isinstance(previous, dict) else {}
    stamp = (now or datetime.now(UTC)).isoformat()
    misses = int(prev.get("consecutive_misses") or 0)
    record = {
        "result": result,
        "checked_at": stamp,
        "consecutive_misses": misses,
        "last_found_at": prev.get("last_found_at"),
    }
    if result == FOUND:
        record["consecutive_misses"] = 0
        record["last_found_at"] = stamp
    elif result == NOT_FOUND:
        record["consecutive_misses"] = misses + 1
    return record


def quote_missing(record: dict[str, Any] | None) -> bool:
    """True when the quote has been absent for enough consecutive runs to stop showing the offer as Active."""
    return isinstance(record, dict) and int(record.get("consecutive_misses") or 0) >= MISSES_BEFORE_DEMOTION


def quote_missing_note(evidence_url: str) -> str:
    return (
        "Quoted Source Gone: the sentence recorded as evidence was not found on "
        f"{evidence_url} in {MISSES_BEFORE_DEMOTION} consecutive checks. "
        "Not shown as Active until the vendor page is read again."
    )


def fetch_page(page: Any, url: str, timeout_ms: int = 30000, settle_ms: int = 6000) -> tuple[str | None, str]:
    """Loads `url` in an existing Playwright page. Returns (visible text or None if it failed, title)."""
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        page.wait_for_timeout(settle_ms)
        text = page.evaluate("() => (document.body || document.documentElement).innerText || ''")
        return text, page.title()
    except Exception as err:
        logger.warning("Quote check could not load %s: %s", url, err)
        return None, ""


def run_quote_checks(offers: list[dict[str, Any]], policies: dict[str, dict[str, Any]]) -> dict[str, int]:
    """
    Checks every offer whose policy records an evidence_url and evidence_quote, and stores the
    outcome on the offer under `evidence_check`. Mutates `offers` in place.
    Returns counts per result. If Playwright or Chromium is unavailable, nothing is changed.
    """
    targets = [
        (offer, policies[offer.get("id")])
        for offer in offers
        if offer.get("id") in policies
        and policies[offer["id"]].get("evidence_url")
        and policies[offer["id"]].get("evidence_quote")
    ]
    counts = {FOUND: 0, NOT_FOUND: 0, UNREADABLE: 0}
    if not targets:
        return counts
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning("Playwright is not installed; quote checks skipped.")
        return counts

    from src.constants import BROWSER_HEADERS, PLAYWRIGHT_LAUNCH_ARGS

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=PLAYWRIGHT_LAUNCH_ARGS)
            context = browser.new_context(
                user_agent=BROWSER_HEADERS["User-Agent"], locale="en-US", viewport={"width": 1280, "height": 800}
            )
            page = context.new_page()
            for offer, policy in targets:
                text, title = fetch_page(page, policy["evidence_url"])
                result = classify_page(policy["evidence_quote"], text, title)
                offer["evidence_check"] = update_record(offer.get("evidence_check"), result)
                counts[result] += 1
                logger.info("Quote check %s: %s", offer.get("id"), result)
            browser.close()
    except Exception as err:
        logger.warning("Quote checks stopped early: %s", err)
    return counts
