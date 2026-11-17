"""
Opens a GitHub issue for each watched page whose offer wording changed in the latest run.

Reads the `latest` list in data/watchlist_changes.json (written by src/watchlist.py) and uses the
`gh` CLI. If an open issue for the same page already exists, the change is added as a comment
instead of opening a second issue. Needs GH_TOKEN with permission to write issues.

Usage: python scripts/open_watch_issues.py [--dry-run]
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.watchlist import CHANGES_FILE, issue_body  # noqa: E402

LABEL = "watchlist"


def issue_title(change: dict) -> str:
    return f"[WATCH] {change.get('vendor')}: {change.get('name')} changed"


def _gh(args: list[str], body: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["gh", *args], input=body, capture_output=True, text=True, encoding="utf-8", check=False)


def main() -> int:
    dry_run = "--dry-run" in sys.argv
    try:
        latest = json.loads(CHANGES_FILE.read_text(encoding="utf-8")).get("latest", [])
    except (OSError, ValueError):
        latest = []
    if not latest:
        print("No watchlist changes in the latest run.")
        return 0

    failures = 0
    for change in latest:
        title = issue_title(change)
        body = issue_body(change)
        if dry_run:
            print(f"--- would open: {title}\n{body}\n")
            continue
        found = _gh(["issue", "list", "--state", "open", "--search", f'"{title}" in:title', "--json", "number"])
        numbers = [i["number"] for i in json.loads(found.stdout or "[]")] if found.returncode == 0 else []
        if numbers:
            res = _gh(["issue", "comment", str(numbers[0]), "--body-file", "-"], body)
        else:
            res = _gh(["issue", "create", "--title", title, "--label", LABEL, "--body-file", "-"], body)
            if res.returncode != 0 and "label" in (res.stderr or "").lower():
                # The label does not exist yet in this repository: open the issue without it.
                res = _gh(["issue", "create", "--title", title, "--body-file", "-"], body)
        if res.returncode != 0:
            failures += 1
            print(f"FAILED for {change.get('id')}: {(res.stderr or '').strip()[:300]}")
        else:
            print(f"OK {change.get('id')}: {(res.stdout or '').strip()}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
