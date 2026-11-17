"""
Watchlist: report when the offer-related wording on a vendor program page changes.

Free exam offers are announced on a small number of vendor pages, usually without notice.
data/watchlist.json lists those pages. Each run loads every page, keeps only the lines that
mention offer terms (free, voucher, discount, scholarship, deadline wording and so on), and
compares them with the lines kept from the previous run.

What a reported change means: wording about offers was added to or removed from the page.
It is a prompt for a person to read the page. It is not a statement that an offer exists.

A page that fails to load or shows almost no text is recorded as unreadable and is never
reported as a change. The first time a page is seen its lines become the baseline and nothing
is reported.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.evidence_check import normalize_text

logger = logging.getLogger("certpulse.watchlist")

ROOT_DIR = Path(__file__).resolve().parent.parent
WATCHLIST_FILE = ROOT_DIR / "data" / "watchlist.json"
STATE_FILE = ROOT_DIR / "data" / "watchlist_state.json"
CHANGES_FILE = ROOT_DIR / "data" / "watchlist_changes.json"

MIN_READABLE_CHARS = 200
MAX_LINE_CHARS = 300
MAX_LINES_PER_PAGE = 200
MAX_CHANGE_LOG = 100

OFFER_WORDING = re.compile(
    r"\bfree\b|no[- ]cost|at no charge|complimentary|voucher|discount|\d+\s?%\s?off|scholarship|"
    r"\bpromo|waive|challenge|sweepstakes|apply by|register by|deadline|ends on|until \w+ \d|through \w+ \d|"
    r"applications? (open|close)|has ended|has concluded|no longer available|retired",
    re.IGNORECASE,
)


def relevant_lines(page_text: str) -> list[str]:
    """Normalized, de-duplicated, sorted lines of a page that mention offer wording."""
    seen: set[str] = set()
    for raw in (page_text or "").splitlines():
        line = normalize_text(raw)
        if 8 <= len(line) <= MAX_LINE_CHARS and OFFER_WORDING.search(line):
            seen.add(line)
    return sorted(seen)[:MAX_LINES_PER_PAGE]


def compare(previous: dict[str, Any] | None, page_text: str | None, now_iso: str) -> tuple[dict[str, Any], dict | None]:
    """
    Folds one page load into the stored state for a watched page.
    Returns (new_state, change). `change` is None unless offer wording was added or removed.
    """
    prev = previous if isinstance(previous, dict) else {}
    if page_text is None or len(page_text.strip()) < MIN_READABLE_CHARS:
        return {**prev, "checked_at": now_iso, "last_result": "unreadable"}, None

    lines = relevant_lines(page_text)
    state = {
        "lines": lines,
        "checked_at": now_iso,
        "last_result": "read",
        "baseline_at": prev.get("baseline_at") or now_iso,
        "last_changed_at": prev.get("last_changed_at"),
    }
    if "lines" not in prev:
        return state, None  # first readable load: baseline only

    old = set(prev["lines"])
    added = [line for line in lines if line not in old]
    removed = sorted(old - set(lines))
    if not added and not removed:
        return state, None
    state["last_changed_at"] = now_iso
    return state, {"added": added, "removed": removed}


def load_watchlist(path: Path | None = None) -> list[dict[str, Any]]:
    file = path or WATCHLIST_FILE
    if not file.exists():
        return []
    data = json.loads(file.read_text(encoding="utf-8"))
    pages = data.get("pages", []) if isinstance(data, dict) else []
    return [p for p in pages if isinstance(p, dict) and p.get("id") and str(p.get("url", "")).startswith("https://")]


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def run_watchlist(
    watchlist_file: Path | None = None,
    state_file: Path | None = None,
    changes_file: Path | None = None,
    fetch: Any | None = None,
) -> list[dict[str, Any]]:
    """
    Checks every watched page and writes the updated state and the change log.
    Returns the changes found in this run. `fetch(url) -> text | None` can be injected for tests;
    by default pages are loaded in headless Chromium, one fresh browser page per URL.
    """
    pages = load_watchlist(watchlist_file)
    s_file = state_file or STATE_FILE
    c_file = changes_file or CHANGES_FILE
    if not pages:
        return []

    state = _read_json(s_file, {})
    if not isinstance(state, dict):
        state = {}
    now_iso = datetime.now(UTC).isoformat()
    run_changes: list[dict[str, Any]] = []

    def process(fetch_fn: Any) -> None:
        for page in pages:
            text = fetch_fn(page["url"])
            new_state, change = compare(state.get(page["id"]), text, now_iso)
            state[page["id"]] = new_state
            if change:
                run_changes.append(
                    {
                        "id": page["id"],
                        "vendor": page.get("vendor"),
                        "name": page.get("name"),
                        "url": page["url"],
                        "detected_at": now_iso,
                        **change,
                    }
                )
                logger.info("Watchlist change on %s: +%d -%d", page["id"], len(change["added"]), len(change["removed"]))

    if fetch is not None:
        process(fetch)
    else:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.warning("Playwright is not installed; watchlist skipped.")
            return []
        from src.constants import BROWSER_HEADERS, PLAYWRIGHT_LAUNCH_ARGS
        from src.evidence_check import fetch_page

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=PLAYWRIGHT_LAUNCH_ARGS)
            context = browser.new_context(user_agent=BROWSER_HEADERS["User-Agent"], locale="en-US")

            def browser_fetch(url: str) -> str | None:
                # A fresh page per URL: one failed navigation must not poison the next.
                tab = context.new_page()
                try:
                    text, _title = fetch_page(tab, url, settle_ms=5000)
                    return text
                finally:
                    tab.close()

            process(browser_fetch)
            browser.close()

    # Drop state for pages no longer on the watchlist.
    wanted = {p["id"] for p in pages}
    state = {k: v for k, v in state.items() if k in wanted}
    s_file.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    log = _read_json(c_file, {})
    history = log.get("changes", []) if isinstance(log, dict) else []
    history = (run_changes + history)[:MAX_CHANGE_LOG]
    c_file.write_text(
        json.dumps({"last_run": now_iso, "latest": run_changes, "changes": history}, indent=2, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    return run_changes


def issue_body(change: dict[str, Any]) -> str:
    """Markdown body for the GitHub issue that asks a person to read a changed page."""
    parts = [
        f"The offer-related wording on **{change.get('vendor')}: {change.get('name')}** changed.",
        "",
        f"Page: {change.get('url')}",
        f"Detected: {str(change.get('detected_at'))[:16]} UTC",
        "",
        "This is an automated notice that the page text changed. It does not mean an offer is open. "
        "Read the page. If it states a free or discounted exam offer, add it with the exact sentence "
        "quoted (`data/curated_policies.json`), otherwise close this issue.",
    ]
    for label, key in (("Wording added", "added"), ("Wording removed", "removed")):
        lines = change.get(key) or []
        if lines:
            parts += ["", f"**{label}:**"] + [f"- {line}" for line in lines[:25]]
            if len(lines) > 25:
                parts.append(f"- (and {len(lines) - 25} more)")
    return "\n".join(parts)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    found = run_watchlist()
    print(f"{len(found)} watched page(s) changed.")
