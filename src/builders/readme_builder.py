"""
README markdown generator for CertPulse repository documentation.
Renders summary metrics, the active offers tables, 4-timezone timestamps, and
collapsible sections for the historical archive, triage pool, news list and claiming guides.

Wording rule: only claim what the pipeline actually does. Links are checked for
reachability and closure notices; policy notes are maintained by hand.
"""

import json
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

DATA_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "offers.json"
NEWS_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "news.json"
README_FILE = Path(__file__).resolve().parent.parent.parent / "README.md"
DOCS_DIR = Path(__file__).resolve().parent.parent.parent / "docs"
DOCS_HTML = DOCS_DIR / "index.html"
REPO_ROOT = DOCS_DIR.parent

STATUS_BADGES = {
    "Active": "🟢 Active",
    "Registrations Closed": "🟡 Closed / Waitlist",
    "Expired": "🔴 Expired",
    "Broken Link": "⚠️ Broken Link",
    "Server Error": "⚠️ Server Error",
    "Review Needed": "🟡 Review Needed",
}


def _safe_format_tz(dt: datetime, tz_name: str, fallback_offset_hours: float, fallback_label: str) -> str:
    """Safely formats datetime for a target timezone with UTC-offset fallback on bare OS / missing tzdata."""
    try:
        tz = ZoneInfo(tz_name)
        fmt = "%H:%M IST" if tz_name == "Asia/Kolkata" else "%H:%M %Z"
        return dt.astimezone(tz).strftime(fmt)
    except Exception:
        fb_tz = timezone(timedelta(hours=fallback_offset_hours))
        return dt.astimezone(fb_tz).strftime(f"%H:%M {fallback_label}")


def format_4_timezones(dt: datetime | str | None = None) -> dict[str, str]:
    """Formats a datetime across 4 canonical global timezones: UTC, IST, US Eastern (ET), and Central Europe (CET/CEST)."""
    parsed_dt: datetime | None = None
    if isinstance(dt, datetime):
        parsed_dt = dt
    elif isinstance(dt, str) and dt.strip() and dt.strip().upper() != "N/A":
        try:
            parsed_dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except Exception:
            parsed_dt = None

    if parsed_dt is None:
        parsed_dt = datetime.now(UTC)

    parsed_dt = parsed_dt.replace(tzinfo=UTC) if parsed_dt.tzinfo is None else parsed_dt.astimezone(UTC)

    utc_str = parsed_dt.strftime("%Y-%m-%d %H:%M UTC")
    utc_time_only = parsed_dt.strftime("%H:%M UTC")
    ist_str = _safe_format_tz(parsed_dt, "Asia/Kolkata", 5.5, "IST")
    et_str = _safe_format_tz(parsed_dt, "America/New_York", -5.0, "EST")
    cet_str = _safe_format_tz(parsed_dt, "Europe/Berlin", 1.0, "CET")

    return {
        "utc": utc_str,
        "utc_short": utc_time_only,
        "ist": ist_str,
        "et": et_str,
        "cet": cet_str,
        "ticker": f"{utc_time_only} • {ist_str} • {et_str} • {cet_str}",
        "banner": f"`{utc_str}` ({ist_str} • {et_str} • {cet_str})",
    }


def load_offers() -> dict[str, Any]:
    """Loads offers from data/offers.json."""
    if not DATA_FILE.exists():
        return {"offers": []}
    with open(DATA_FILE, encoding="utf-8") as f:
        return json.load(f)


def load_news() -> dict[str, Any]:
    """Loads intelligence radar items from data/news.json."""
    if not NEWS_FILE.exists():
        return {"news": []}
    with open(NEWS_FILE, encoding="utf-8") as f:
        return json.load(f)


def _escape_md(text: Any) -> str:
    """Escapes pipe characters in markdown table cells."""
    if text is None:
        return ""
    return str(text).replace("|", "\\|")


def proof_path(o: dict[str, Any]) -> str | None:
    """
    Returns the repository-relative screenshot path only when the offer has a real captured
    screenshot: visual_proof.status is "verified" AND the image file exists on disk.
    """
    vp = o.get("visual_proof") if isinstance(o.get("visual_proof"), dict) else {}
    if vp.get("status") != "verified":
        return None
    path = vp.get("screenshot_path") or o.get("screenshot_path")
    if not path or not isinstance(path, str):
        return None
    try:
        if not (REPO_ROOT / path).is_file():
            return None
    except OSError:
        return None
    return path.replace("\\", "/")


def has_real_proof(o: dict[str, Any]) -> bool:
    """True when proof_path() finds a real captured screenshot for the offer."""
    return proof_path(o) is not None


def _proof_cell(o: dict[str, Any]) -> str:
    """Markdown table cell: a screenshot link when one really exists, otherwise a dash."""
    path = proof_path(o)
    return f"[📸 Screenshot]({path})" if path else "—"


def _status_cell(o: dict[str, Any]) -> str:
    """Status badge plus the date the page was last checked by the automated inspector."""
    status_text = STATUS_BADGES.get(o.get("status", "Active"), "🟢 Active")
    checked = o.get("last_zero_dollar_confirmed_date")
    if checked:
        status_text += f"<br><sub>Page checked: {checked}</sub>"
    elif o.get("status") == "Active":
        status_text += "<br><sub>Not yet page-checked</sub>"
    return status_text


def _source_cell(o: dict[str, Any]) -> str:
    """
    Markdown table cell naming where the terms come from. When a person has recorded reading the
    vendor page, shows the quoted sentence, who read it and when; otherwise says so plainly.
    """
    tv = o.get("truth_verification") if isinstance(o.get("truth_verification"), dict) else {}
    quote = tv.get("evidence_quote")
    evidence_url = tv.get("evidence_url")
    if quote and evidence_url and tv.get("reviewed_on") and tv.get("reviewed_by"):
        ec = o.get("evidence_check") if isinstance(o.get("evidence_check"), dict) else {}
        check = {
            "found": f"; sentence still on the page at the automated check of {str(ec.get('checked_at', ''))[:10]}",
            "not_found": f"; sentence NOT found at the automated check of {str(ec.get('checked_at', ''))[:10]}",
        }.get(ec.get("result"), "")
        return (
            f'[Vendor terms]({evidence_url}): "{_escape_md(quote)}"'
            f"<br><sub>Read by {_escape_md(tv['reviewed_by'])} on {_escape_md(tv['reviewed_on'])}{check}</sub>"
        )
    name = _escape_md(tv.get("truth_source_name") or f"{o.get('platform')} Policy")
    url = tv.get("truth_source_url") or o.get("direct_verified_url") or o.get("url")
    return f"[{name}]({url})<br><sub>No quoted source recorded</sub>"


_EMPTY_SECTION_NOTE = (
    "*Nothing is listed here right now. An offer appears only when someone has recorded reading the vendor's "
    "terms (with the sentence quoted) and that check is within its review date. "
    "See the 'Needs Re-Check' list below for everything waiting on that.*"
)


def _watchlist_rows() -> list[str]:
    """Markdown rows for the watched program pages, from data/watchlist.json and its state file."""
    data_dir = DATA_FILE.parent
    try:
        pages = json.loads((data_dir / "watchlist.json").read_text(encoding="utf-8")).get("pages", [])
    except (OSError, ValueError, AttributeError):
        return []
    try:
        state = json.loads((data_dir / "watchlist_state.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        state = {}
    rows = []
    for page in pages:
        st = state.get(page.get("id"), {}) if isinstance(state, dict) else {}
        changed = str(st.get("last_changed_at") or "")[:10] or "no change seen yet"
        if st.get("last_result") == "unreadable":
            read = "could not be read"
        else:
            read = str(st.get("checked_at") or "")[:10] or "not yet"
        rows.append(
            f"| **{_escape_md(page.get('vendor'))}** | [{_escape_md(page.get('name'))}]({page.get('url')}) | {changed} | {read} |"
        )
    return rows


def copay_terms(o: dict[str, Any]) -> str | None:
    """For partial discounts, returns e.g. '75% off; you pay about $50'. None for other offers."""
    tv = o.get("truth_verification") if isinstance(o.get("truth_verification"), dict) else {}
    cost = tv.get("real_exam_cost_usd") or 0
    if tv.get("policy_type") != "partial_discount_copay" or cost <= 0:
        return None
    pct = tv.get("verified_discount_pct")
    pct_text = f"{pct:g}% off; " if isinstance(pct, (int, float)) and 0 < pct < 100 else ""
    return f"{pct_text}you pay about ${cost:g}"


def classify_offer_tier(o: dict[str, Any]) -> str:
    """Classifies an offer into 'wave' (limited-time exam wave), 'discount' (active ongoing discount/voucher), or 'badge' (skill badge & lab)."""
    tv = o.get("truth_verification") or {}
    otype = (o.get("offer_type") or "").lower()
    seas = (o.get("seasonality") or "").lower()
    oid = (o.get("id") or "").lower()
    title = (o.get("title") or "").lower()
    rec = (o.get("recurrence_pattern") or "").lower()

    # 1. Partial / Ongoing Discounts & Student Vouchers
    is_partial_copay = tv.get("policy_type") == "partial_discount_copay" or (tv.get("real_exam_cost_usd") or 0) > 0
    is_student_discount = "student" in seas or "student" in otype or "student" in oid
    is_discount_type = ("discount" in otype and "100% free" not in otype) or ("%" in otype and "100%" not in otype)
    if is_partial_copay or is_student_discount or is_discount_type:
        return "discount"

    # An unproctored course or badge is never an exam wave, whatever its seasonality tag says.
    if o.get("credential_tier") in ("skill_badge_lab", "secondary"):
        return "badge"

    # 2. Exam Waves (Seasonal challenge waves, limited-time cohorts, annual/event windows)
    if (
        seas in ("periodic_challenge_wave", "annual_window", "monthly_sweepstakes", "event_driven")
        or "wave" in oid
        or "wave" in title
        or "challenge" in title
        or "wave" in rec
        or "cohort" in rec
    ):
        return "wave"

    # 3. Free Skill Badges & Labs
    return "badge"


def generate_readme(
    data: dict[str, Any] | list[dict[str, Any]],
    news_data: dict[str, Any] | list[dict[str, Any]] | None = None,
    last_sync: str | None = None,
) -> str:
    """
    Generates a compact, executive README.md.
    Active offers are organized into a clean master table.
    Large secondary archives (recurrence roadmap, triage pool, news radar, and claiming steps)
    are collapsed within native GitHub <details> disclosure tags for rapid reading and zero bloat.
    """
    if news_data is None:
        news_data = load_news()

    offers: list[dict[str, Any]] = (
        data if isinstance(data, list) else (data.get("offers", []) if isinstance(data, dict) else [])
    )
    news_items: list[dict[str, Any]] = (
        news_data if isinstance(news_data, list) else (news_data.get("news", []) if isinstance(news_data, dict) else [])
    )

    active_offers = [o for o in offers if o.get("status") == "Active"]
    closed_offers = [o for o in offers if o.get("status") != "Active" and not o.get("is_historical_archive")]
    historical_offers = [o for o in offers if o.get("is_historical_archive")]

    proctored_offers = [o for o in offers if o.get("credential_tier") in ("proctored_exam", "primary")]
    badge_offers = [o for o in offers if o.get("credential_tier") in ("skill_badge_lab", "secondary")]
    active_proctored = [o for o in proctored_offers if o.get("status") == "Active"]
    active_badges = [o for o in badge_offers if o.get("status") == "Active"]
    _proctored_tiers = ("proctored_exam", "primary")
    # Proctored offers that are neither a discount nor tagged as a wave still belong with the exam offers,
    # never with the always-free badges.
    active_waves = [
        o
        for o in active_offers
        if classify_offer_tier(o) == "wave"
        or (classify_offer_tier(o) == "badge" and o.get("credential_tier") in _proctored_tiers)
    ]
    active_discounts = [o for o in active_offers if classify_offer_tier(o) == "discount"]
    # Each active offer appears in exactly one table.
    active_badge_rows = [
        o
        for o in active_offers
        if classify_offer_tier(o) == "badge" and o.get("credential_tier") not in _proctored_tiers
    ]

    verified_proofs_count = sum(1 for o in offers if has_real_proof(o))
    proof_pct = round(verified_proofs_count / len(offers) * 100) if offers else 0
    review_offers = [o for o in offers if o.get("status") == "Review Needed"]

    last_sync_raw = (
        last_sync
        or (data.get("last_sync") if isinstance(data, dict) else None)
        or (data.get("last_truth_corroborated") if isinstance(data, dict) else None)
        or (data.get("last_inspected") if isinstance(data, dict) else None)
        or (data.get("last_updated") if isinstance(data, dict) else None)
    )
    last_sync_dt = None
    if last_sync_raw:
        try:
            last_sync_dt = datetime.fromisoformat(str(last_sync_raw).replace("Z", "+00:00"))
        except Exception:
            last_sync_dt = None
    tz_info = format_4_timezones(last_sync_dt)
    last_updated = tz_info["utc"]

    lines: list[str] = []
    lines.append("# CertPulse: Free Cloud & Tech Certification Tracker")
    lines.append("")
    lines.append(
        "> A list of free and discounted certification exam offers, free skill badges, and continuing education credits from vendors such as AWS, Microsoft, Google Cloud, Cisco, ISC2, Oracle, Linux Foundation / CNCF, Snowflake, Databricks, Red Hat, GitLab, Splunk, IBM and GitHub. Links point to official vendor domains and are checked automatically twice a day for reachability and closure notices. The policy notes (what is free, for whom, and any co-pay) are maintained by hand and can be out of date: always confirm the terms on the vendor's own page before relying on them."
    )
    lines.append("")
    if (REPO_ROOT / "LICENSE").is_file():
        lines.append("![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg) ")
    lines.append(f"![Active Offers](https://img.shields.io/badge/Active%20Offers-{len(active_offers)}-success.svg) ")
    lines.append(f"![Offers Tracked](https://img.shields.io/badge/Offers%20Tracked-{len(offers)}-blue.svg) ")
    lines.append(
        f"![Proctored Exams](https://img.shields.io/badge/Proctored%20Exams-{len(active_proctored)}%20Active-success.svg) "
    )
    lines.append(
        f"![Skill Badges](https://img.shields.io/badge/Skill%20Badges-{len(active_badges)}%20Active-blue.svg) "
    )
    lines.append(
        f"![Screenshots](https://img.shields.io/badge/Screenshots-{verified_proofs_count}%2F{len(offers)}%20Captured-blue.svg) "
    )
    lines.append("![Link Checks](https://img.shields.io/badge/Link%20Checks-Twice%20Daily-blue.svg) ")
    lines.append("![Automated By](https://img.shields.io/badge/Automated%20By-GitHub%20Actions-purple.svg) ")
    lines.append(
        "![Maintainer](https://img.shields.io/badge/Maintained%20By-Solo%20Developer%20(Athish%20R%20S)-blueviolet.svg) "
    )
    lines.append("![Support](https://img.shields.io/badge/Support-Best--Effort%20(No%20SLA)-orange.svg)")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Value | What it means |")
    lines.append("| :--- | :--- | :--- |")
    lines.append(
        f"| **Active Offers** | **{len(active_offers)}** | Listed as open only when someone has recorded reading the vendor's terms (sentence quoted, with name and date), that check is within its review date, and no closure notice has been found |"
    )
    lines.append(
        f"| **Proctored Exam Offers** | **{len(active_proctored)} Active** ({len(proctored_offers)} Tracked) | Offers for proctored exams (Pearson VUE, Kryterion, Webassessor and similar) |"
    )
    lines.append(
        f"| **Free Skill Badges & Labs** | **{len(active_badges)} Active** ({len(badge_offers)} Tracked) | Unproctored courses, labs and digital badges |"
    )
    lines.append(
        f"| **Offers Tracked** | **{len(offers)} Total** ({len(active_offers)} Active, {len(closed_offers)} Triage, {len(historical_offers)} Archived) | Each tracked link is loaded by the inspector and screened for error pages and closure wording |"
    )
    lines.append(
        f"| **Needs Review** | **{len(review_offers)}** | Not shown as Active: an automated check was inconclusive, the hand-maintained policy note is past its review date, or nobody has recorded reading the vendor's terms |"
    )
    lines.append(
        f"| **Screenshots Captured** | **{verified_proofs_count}/{len(offers)} ({proof_pct}%)** | Offers with a real screenshot of the vendor page in docs/screenshots/. A screenshot shows the page loaded; it is not proof of the offer terms |"
    )
    lines.append(
        f"| **Historical Archive** | **{len(historical_offers)} Campaigns** | Past campaigns written up by hand; no screenshots of the original pages exist |"
    )
    lines.append(f"| **News Items** | **{len(news_items)}** | Posts pulled from official vendor blogs and feeds |")
    lines.append(
        "| **Link Domains** | **Official vendor domains** | Tracked links are restricted to an allow-list of vendor domains and must use HTTPS |"
    )
    lines.append(
        "| **Policy Notes** | **Maintained by hand** | Co-pays, eligibility and windows are written by the maintainer in `data/curated_policies.json`, each with a review date and a quoted source. Without a quoted source, or past the review date, an offer is shown as Review Needed, not Active |"
    )
    lines.append(
        f"| **Last Automated Inspection** | {tz_info['banner']} | Reachability and closure-notice check (UTC, IST, ET, CET) |"
    )
    lines.append("| **Hosting** | **GitHub Actions & GitHub Pages** | No paid infrastructure |")
    lines.append(
        "| **Maintainer** | **[Athish R S](https://github.com/Athish2002)** | One person; best-effort response |"
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"## Time-Limited Free Exam Offers ({len(active_waves)} Active)")
    lines.append(
        "> Free or fully waived exam attempts that are open for a limited window. These are the offers that go away, so each row shows the sentence on the vendor page that states the terms."
    )
    lines.append("")
    lines.append(
        "| Provider | Certification & Program | Category | Cadence & Wave | Exam List Price | Status | Screenshot | Source of Terms | Link |"
    )
    lines.append("| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :--- | :--- |")
    for o in active_waves:
        provider = _escape_md(o.get("platform"))
        cert = _escape_md(o.get("certification_name") or o.get("title"))
        cat = _escape_md(o.get("category", "General"))
        cadence = _escape_md(o.get("recurrence_pattern") or "Periodic Wave")
        val = f"${o.get('value_usd')}" if o.get("value_usd") else "—"
        status_text = _status_cell(o)
        proof_link = _proof_cell(o)
        truth_link = _source_cell(o)
        url = o.get("direct_verified_url") or o.get("url", "#")
        lines.append(
            f"| **{provider}** | {cert} | {cat} | `{cadence}` | {val} | {status_text} | {proof_link} | {truth_link} | [**Vendor Page**]({url}) |"
        )
    if not active_waves:
        lines.extend(["", _EMPTY_SECTION_NOTE])
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"## Discounts and Student-Only Offers ({len(active_discounts)} Active)")
    lines.append(
        "> Ongoing student offers and partial discounts. A partial discount is not a free exam: the amount you still pay is shown in the cost column."
    )
    lines.append("")
    lines.append(
        "| Provider | Discount / Voucher Program | Category | Terms & Prereqs | Cost to You | Status | Screenshot | Source of Terms | Link |"
    )
    lines.append("| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :--- | :--- |")
    for o in active_discounts:
        provider = _escape_md(o.get("platform"))
        cert = _escape_md(o.get("certification_name") or o.get("title"))
        cat = _escape_md(o.get("category", "General"))
        elig = _escape_md(o.get("eligibility") or "Continuous Discount")
        val = copay_terms(o) or "See vendor terms"
        status_text = _status_cell(o)
        proof_link = _proof_cell(o)
        truth_link = _source_cell(o)
        url = o.get("direct_verified_url") or o.get("url", "#")
        lines.append(
            f"| **{provider}** | {cert} | {cat} | {elig} | {val} | {status_text} | {proof_link} | {truth_link} | [**Vendor Page**]({url}) |"
        )
    if not active_discounts:
        lines.extend(["", _EMPTY_SECTION_NOTE])
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"## Always-Free Courses and Badges ({len(active_badge_rows)} Active / {len(badge_offers)} Tracked)")
    lines.append(
        "> Unproctored courses, labs and digital badges that vendors offer free as a matter of course. They are not exam vouchers and no price or saving is shown."
    )
    lines.append("")
    lines.append(
        "| Provider | Credential & Assessment | Category | Tier | Status | Screenshot | Source of Terms | Link |"
    )
    lines.append("| :--- | :--- | :--- | :---: | :---: | :---: | :--- | :--- |")
    for o in active_badge_rows:
        provider = _escape_md(o.get("platform"))
        cert = _escape_md(o.get("certification_name") or o.get("title"))
        cat = _escape_md(o.get("category", "General"))
        tier = _escape_md(o.get("difficulty_tier", "Foundational"))
        status_text = _status_cell(o)
        proof_link = _proof_cell(o)
        truth_link = _source_cell(o)
        url = o.get("direct_verified_url") or o.get("url", "#")
        lines.append(
            f"| **{provider}** | {cert} | {cat} | `{tier}` | {status_text} | {proof_link} | {truth_link} | [**Vendor Page**]({url}) |"
        )
    if not active_badge_rows:
        lines.extend(["", _EMPTY_SECTION_NOTE])
    lines.append("")

    if historical_offers:
        lines.append("---")
        lines.append("")
        lines.append("<details>")
        lines.append(
            f"<summary><b>📜 Historical Voucher Archive & Recurrence Patterns ({len(historical_offers)} Campaigns)</b> — <i>Click to expand</i></summary>"
        )
        lines.append("")
        lines.append(
            "> Past campaigns, listed to show when vendors have tended to run them. These entries were written by hand and are not independently verified: no screenshot or archive of the original campaign pages is kept here."
        )
        lines.append("")
        lines.append(
            "| Provider | Certification & Exam Code | Type | Exam List Price | Promo Period | Recurrence Pattern | Notes |"
        )
        lines.append("| :--- | :--- | :--- | :---: | :---: | :--- | :--- |")
        for o in historical_offers:
            provider = _escape_md(o.get("platform"))
            cert = _escape_md(o.get("certification_name") or o.get("title"))
            exam = f"<br>`{o.get('exam_code')}`" if o.get("exam_code") else ""
            otype = _escape_md(o.get("offer_type"))
            val = f"${o.get('value_usd')}" if o.get("value_usd") else "—"
            period = _escape_md(o.get("time_period", "Concluded"))
            recur = _escape_md(o.get("recurrence_pattern", "Annual / Rolling"))
            notes = _escape_md(o.get("inspection_notes", "Concluded"))
            lines.append(f"| **{provider}** | **{cert}**{exam} | `{otype}` | {val} | {period} | {recur} | {notes} |")
        lines.append("")
        lines.append("</details>")
        lines.append("")

    if closed_offers:
        lines.append("---")
        lines.append("")
        lines.append("<details>")
        lines.append(
            f"<summary><b>Needs Re-Check, Closed or Expired ({len(closed_offers)})</b> — <i>Click to expand</i></summary>"
        )
        lines.append("")
        lines.append(
            "> Offers that are closed, expired, or could not be confirmed: the inspector found a closure notice or an inconclusive page, the hand-maintained policy note is past its review date, or nobody has recorded reading the vendor's terms. Pages are re-loaded twice a day; the terms are only re-read when a person does it."
        )
        lines.append("")
        lines.append("| Provider | Certification | Triage Status | Screenshot | Reason / Inspection Note |")
        lines.append("| :--- | :--- | :---: | :---: | :--- |")
        for o in closed_offers:
            status_badge = STATUS_BADGES.get(o.get("status"), o.get("status"))
            reason = _escape_md(o.get("inspection_notes", "Concluded"))
            proof_link = _proof_cell(o)
            lines.append(
                f"| **{_escape_md(o.get('platform'))}** | {_escape_md(o.get('certification_name') or o.get('title'))} | {status_badge} | {proof_link} | {reason} |"
            )
        lines.append("")
        lines.append("</details>")
        lines.append("")

    if news_items:
        lines.append("---")
        lines.append("")
        lines.append("## 📰 Vendor Engineering News")
        lines.append(
            "> Recent posts pulled automatically from official vendor engineering blogs and RSS/Atom feeds. Items are filtered by source domain and keywords; the summaries come from the feeds and are not reviewed by a person."
        )
        lines.append("")
        lines.append("<details>")
        lines.append(f"<summary><b>View news items ({len(news_items)})</b> — <i>Click to expand</i></summary>")
        lines.append("")
        lines.append("| Published | Vendor | Category | Tag | Headline & Feed Summary | Source |")
        lines.append("| :--- | :--- | :--- | :---: | :--- | :--- |")
        for item in news_items:
            date = item.get("published_date", "")
            company = _escape_md(item.get("company", ""))
            cat = _escape_md(item.get("category", ""))
            badge = f"`{item.get('impact_badge', '')}`" if item.get("impact_badge") else ""
            title = _escape_md(item.get("title", ""))
            summary = _escape_md(item.get("summary", ""))
            url = item.get("url", "#")
            source_name = _escape_md(item.get("source", item.get("source_domain", "")))
            domain = _escape_md(item.get("source_domain", ""))

            headline_cell = f"**[{title}]({url})**<br>{summary}"
            source_cell = f"[{source_name}]({url})<br>`{domain}`"
            lines.append(f"| `{date}` | **{company}** | {cat} | {badge} | {headline_cell} | {source_cell} |")
        lines.append("")
        lines.append("</details>")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("<details>")
    lines.append(
        f"<summary><b>📋 How to Claim (All {len(active_offers)} Active Offers)</b> — <i>Click to expand</i></summary>"
    )
    lines.append("")
    lines.append(
        "> These steps are written by hand from the vendor pages and are not tested end to end. Vendors change their flows; follow what the vendor page says if it differs."
    )
    lines.append("")
    for o in active_offers:
        lines.append(f"#### {o.get('title')}")
        lines.append(f"- **Provider:** {o.get('platform')}")
        copay = copay_terms(o)
        if copay:
            lines.append(f"- **Cost to You:** {copay}")
        lines.append(f"- **Eligibility:** {o.get('eligibility')}")
        lines.append(f"- **Steps to Claim:** {o.get('claim_steps')}")
        target_link = o.get("direct_verified_url") or o.get("url")
        lines.append(f"- **Official Link:** [{target_link}]({target_link})")
        lines.append("")
    lines.append("</details>")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 💳 Where & How Vouchers Are Applied (Checkout Guide)")
    lines.append(
        "> Where each offer is redeemed and what you should expect to pay. CertPulse does not hold or publish voucher codes: real codes are issued to you by the vendor. The expected cost is written by hand from the vendor's stated terms; no test purchase is made. If the checkout shows a different amount, trust the checkout."
    )
    lines.append("")
    lines.append(
        "| Provider | Certification | Official Redemption Portal | Checkout Field / Location | Application Flow | Expected Cost (not test-purchased) |"
    )
    lines.append("| :--- | :--- | :--- | :--- | :---: | :---: |")
    for o in active_offers:
        provider = _escape_md(o.get("platform"))
        cert = _escape_md(o.get("certification_name") or o.get("title"))
        guide = o.get("redemption_guide") or {}
        portal_name = _escape_md(guide.get("portal_name", o.get("platform")))
        portal_url = guide.get("portal_url", o.get("direct_verified_url") or o.get("url"))
        field_loc = _escape_md(guide.get("field_location", o.get("checkout_field", "Promo / Voucher Code input")))
        flow = _escape_md(guide.get("flow_type", o.get("application_flow_type", "Checkout Promo Code")))
        bal = _escape_md(guide.get("verified_cart_balance") or o.get("cart_balance_verified") or "Unverified")
        lines.append(
            f"| **{provider}** | {cert} | [{portal_name}]({portal_url}) | `{field_loc}` | `{flow}` | **{bal}** |"
        )
    lines.append("")
    lines.append("<details>")
    lines.append(
        f"<summary><b>🔍 Step-by-Step Checkout Guides (All {len(active_offers)} Active Offers)</b> — <i>Click to expand</i></summary>"
    )
    lines.append("")
    for o in active_offers:
        guide = o.get("redemption_guide") or {}
        lines.append(f"#### {o.get('title')}")
        lines.append(
            f"- **Official Redemption Portal:** [{guide.get('portal_name', o.get('platform'))}]({guide.get('portal_url', o.get('direct_verified_url') or o.get('url'))})"
        )
        lines.append(f"- **Checkout Field Location:** `{guide.get('field_location', o.get('checkout_field'))}`")
        lines.append(f"- **Application Flow Type:** `{guide.get('flow_type', o.get('application_flow_type'))}`")
        lines.append(
            f"- **Expected Cost (not test-purchased):** **{guide.get('verified_cart_balance') or o.get('cart_balance_verified') or 'Unverified'}**"
        )
        lines.append("- **Checkout Steps:**")
        instructions = guide.get("instructions")
        if not instructions or not isinstance(instructions, list):
            instructions = [o.get("claim_steps", "Complete registration at official vendor portal.")]
        for step in instructions:
            lines.append(f"  1. {step}")
        lines.append("")
    lines.append("</details>")
    lines.append("")

    watch_rows = _watchlist_rows()
    if watch_rows:
        lines.append("---")
        lines.append("")
        lines.append("## Watched Program Pages")
        lines.append(
            "> Free exam offers are usually announced on a handful of vendor pages, without notice. "
            "These pages are loaded twice a day and compared with the previous run. When the wording about "
            "offers on a page changes, an issue labelled `watchlist` is opened so that someone reads the page. "
            "A change is a reason to look, not a confirmed offer. To be told about changes, watch this "
            "repository's issues."
        )
        lines.append("")
        lines.append("| Vendor | Page | Offer wording last changed | Last read |")
        lines.append("| :--- | :--- | :---: | :---: |")
        lines.extend(watch_rows)
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 🛡️ What Is and Is Not Checked")
    lines.append("")
    lines.append("What the automation does:")
    lines.append("")
    lines.append(
        "1. **Official domains only**: tracked links must be HTTPS and on an allow-list of vendor domains. Link shorteners and third-party coupon sites are rejected."
    )
    lines.append(
        "2. **Reachability and closure notices, twice a day**: a headless browser loads each page and looks for error pages, soft-404s and wording such as 'registration closed'. It also looks for words like 'free' or 'badge' on the page. That is a keyword check, not a confirmation of price: measured on 2026-11-16 against 28 pages read one by one, it called 19 offers Active and the reader could confirm the terms for 9 of them. It cannot make an offer Active on its own."
    )
    lines.append(
        "3. **Screenshots**: where a capture succeeded, a screenshot of the page as loaded is stored in `docs/screenshots/`. Offers without one show a dash."
    )
    lines.append(
        "4. **Quote check**: for offers with a recorded source sentence, the page is loaded again and searched for that exact sentence. If it is missing in two consecutive runs, the offer stops being shown as Active. A page that does not load or shows no text is recorded as unreadable and counts neither way."
    )
    lines.append(
        "5. **Watched program pages**: a fixed list of vendor pages is compared with the previous run, and an issue is opened when the wording about offers changes. This finds pages worth reading; it does not find or confirm offers."
    )
    lines.append(
        "6. **Hand-maintained policy notes**: co-pays, eligibility limits and enrollment windows are written by the maintainer in `data/curated_policies.json`. Each note must carry the sentence quoted from the vendor page, who read it and when, and a review date. Without those, or once the review date passes, the offer is shown as Review Needed, not Active."
    )
    lines.append("")
    lines.append("What it does not do:")
    lines.append("")
    lines.append(
        "- It does not register for exams, apply vouchers, or complete a checkout, so no price is confirmed by purchase."
    )
    lines.append("- It does not hold or publish voucher codes.")
    lines.append(
        "- It cannot tell you whether an offer is still available to you: eligibility, region and capacity limits are set by the vendor."
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Architecture: How This Repo Updates Itself")
    lines.append("")
    lines.append("```mermaid")
    lines.append("flowchart TD")
    lines.append("    subgraph Ingest [1. Ingestion Engine - Every 12h (Twice Daily)]")
    lines.append("        A[Official Vendor Feeds] --> C[GitHub Actions Runner]")
    lines.append("        B[Community Candidate Feeds] --> C")
    lines.append("    end")
    lines.append("")
    lines.append("    subgraph Verify [2. Page Checks]")
    lines.append("        C --> D[Playwright Headless Chromium]")
    lines.append("        D --> E[DOM Liveness & Closed Notice Detector]")
    lines.append("        D --> F[Screenshot Capture<br>docs/screenshots/*.png]")
    lines.append("        E & F --> G[Domain Allow-List & Hand-Maintained Policy Notes]")
    lines.append("    end")
    lines.append("")
    lines.append("    subgraph Store [3. Segmented Datastores]")
    lines.append("        G --> H[(data/offers.json)]")
    lines.append("        C --> I[(data/news.json)]")
    lines.append("    end")
    lines.append("")
    lines.append("    subgraph Publish [4. Publish]")
    lines.append("        H & I --> J[Static Site & README Builder]")
    lines.append("        J --> K[README.md]")
    lines.append("        J --> L[GitHub Pages Web Dashboard]")
    lines.append("    end")
    lines.append("```")
    lines.append("")
    lines.append("1. **No external servers**: runs on scheduled GitHub Actions (`ubuntu-latest`) and GitHub Pages.")
    lines.append(
        "2. **Exams and badges kept apart**: proctored exam offers are listed separately from unproctored skill badges and learning paths."
    )
    lines.append(
        "3. **Page checks and screenshots**: headless Chromium renders each page, screens it for closure and maintenance wording, and saves a viewport screenshot to `docs/screenshots/` when the capture succeeds."
    )
    lines.append(
        "4. **Status changes**: when a previously closed page loads again without a closure notice, the status can return to Active on the next run. This is a page-level signal and can be wrong; the hand-maintained policy note takes precedence."
    )
    lines.append(
        "5. **News ingestion**: posts are pulled from official vendor feeds, filtered by an allow-list of domains."
    )
    lines.append(
        "6. **Single source**: `README.md` and `docs/index.html` are both generated from `data/offers.json` and `data/news.json`."
    )
    lines.append("")
    if (DOCS_DIR / "DEEP_DIVE_PAST_FAILURES_AND_ARCHITECTURE_RFC.md").is_file():
        lines.append(
            "Background on the design: [architecture notes](docs/DEEP_DIVE_PAST_FAILURES_AND_ARCHITECTURE_RFC.md)."
        )
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 👤 Maintainer & Expectations")
    lines.append("")
    lines.append(
        "CertPulse is maintained by one person, [Athish R S](https://github.com/Athish2002), in spare time. There is no team and no guaranteed response time. Issues and pull requests are looked at when time allows."
    )
    lines.append("")
    lines.append(
        "The link checks run on a schedule without anyone watching. The policy notes do not update themselves: they are only as current as their last manual review, which is why overdue entries are downgraded to Review Needed."
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 🤝 Contributing & Submitting Offers")
    lines.append("")
    lines.append(
        "Contributions are welcome. If you find a new free offer on an official vendor page, or notice one here that has closed or is described wrongly:"
    )
    lines.append(
        "- **Report something wrong**: Open an issue with the [Report a Wrong or Closed Offer](../../issues/new?template=report_wrong.yml) template. Corrections are recorded in [CORRECTIONS.md](CORRECTIONS.md)."
    )
    lines.append(
        "- **Submit an Offer**: Open an issue with the [Submit an Offer](../../issues/new?template=submit_voucher.yml) template. It asks for the sentence on the vendor page that states the terms."
    )
    lines.append(
        "- **Submit a Pull Request**: Edit `data/offers.json` and `data/curated_policies.json`. CI validates the JSON schemas; it does not check that the offer is real, so include the quoted source."
    )
    lines.append(
        "- **Review Expectations**: Reviews happen on a best-effort basis. Please link the vendor page that states the terms."
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        f"*Maintained by [Athish R S](https://github.com/Athish2002). Links are checked automatically every 12 hours; last run `{last_updated}`.*"
    )

    return "\n".join(lines)
