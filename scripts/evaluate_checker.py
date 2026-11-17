"""
Measures the automated keyword page check against hand-read results.

Ground truth: policy notes in data/curated_policies.json that carry `reviewed_on`. A note with
enforce_status "Active" means a reader found a sentence on the vendor page stating the terms.
Any other status means the reader did not (page gone, retired, or terms not stated).

For each of those offers this script loads the tracked page in headless Chromium, runs the
keyword check the pipeline uses (src.dom_inspector.inspect_rendered_dom), and reports how often
"keyword check says Active" agrees with "a reader confirmed the terms".

Usage: python scripts/evaluate_checker.py
Loads live vendor pages. Results vary from run to run with page rendering and bot blocking.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from playwright.sync_api import sync_playwright  # noqa: E402

from src.constants import BROWSER_HEADERS, PLAYWRIGHT_LAUNCH_ARGS  # noqa: E402
from src.dom_inspector import inspect_rendered_dom  # noqa: E402
from src.evidence_check import fetch_page  # noqa: E402


def main() -> int:
    offers = json.loads((ROOT / "data" / "offers.json").read_text(encoding="utf-8"))["offers"]
    policies = json.loads((ROOT / "data" / "curated_policies.json").read_text(encoding="utf-8"))
    targets = [o for o in offers if not o.get("is_historical_archive") and policies.get(o["id"], {}).get("reviewed_on")]
    rows = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=PLAYWRIGHT_LAUNCH_ARGS)
        page = browser.new_context(user_agent=BROWSER_HEADERS["User-Agent"], locale="en-US").new_page()
        for o in targets:
            url = o.get("url") or o.get("direct_verified_url")
            text, title = fetch_page(page, url)
            if text is None:
                keyword_active = None
                category = "load_failed"
            else:
                res = inspect_rendered_dom(text, title, final_url=page.url, original_url=url)
                keyword_active = res["status"] == "Active" and bool(res.get("zero_dollar_confirmed"))
                category = res.get("category")
            reader_confirmed = policies[o["id"]].get("enforce_status") == "Active"
            rows.append((o["id"], reader_confirmed, keyword_active, category))
        browser.close()

    print(f"{'offer':44} {'reader':9} {'keyword':9} category")
    for oid, truth, kw, cat in rows:
        kw_text = "n/a" if kw is None else ("Active" if kw else "not")
        print(f"{oid[:44]:44} {'confirmed' if truth else 'no':9} {kw_text:9} {cat}")

    judged = [(t, k) for _, t, k, _ in rows if k is not None]
    tp = sum(1 for t, k in judged if t and k)
    fp = sum(1 for t, k in judged if not t and k)
    fn = sum(1 for t, k in judged if t and not k)
    tn = sum(1 for t, k in judged if not t and not k)
    print()
    print(f"offers judged: {len(judged)} (page failed to load: {len(rows) - len(judged)})")
    print(f"keyword says Active and reader confirmed:      {tp}")
    print(f"keyword says Active but reader did NOT confirm: {fp}")
    print(f"keyword says not Active but reader confirmed:   {fn}")
    print(f"keyword says not Active and reader agreed:      {tn}")
    if tp + fp:
        print(f"when the keyword check says Active, a reader agreed {tp}/{tp + fp} times")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
