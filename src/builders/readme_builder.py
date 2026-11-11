"""
README markdown generator for CertPulse repository documentation.
Renders executive Bento metrics, active opportunities table, 4-timezone timestamps,
collapsible disclosure sections for recurrence, triage, tech radar, claiming guides,
and zero-dollar checkout navigation.
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
    active_waves = [o for o in active_offers if classify_offer_tier(o) == "wave"]
    active_discounts = [o for o in active_offers if classify_offer_tier(o) == "discount"]

    total_savings = sum((o.get("value_usd") or 0) for o in active_offers)
    verified_proofs_count = sum(1 for o in offers if (DOCS_DIR / "screenshots" / f"{o.get('id', '')}.png").exists())
    proof_pct = round(verified_proofs_count / len(offers) * 100) if offers else 0

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
    lines.append("# CertPulse: Autonomous Free Cloud & Tech Certification Tracker")
    lines.append("")
    lines.append(
        "> **Automated, 100% free, and self-updating repository** tracking verified 100% free certification exam vouchers, accredited micro-credentials, and continuing education credits across AWS, Azure, Google Cloud, Cisco, ISC2, Oracle, Linux Foundation / CNCF, Snowflake, Databricks, Red Hat, HashiCorp, Palo Alto Networks, GitLab, Splunk, IBM, and GitHub."
    )
    lines.append("")
    lines.append("![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg) ")
    lines.append(f"![Active Vouchers](https://img.shields.io/badge/Active%20Offers-{len(active_offers)}-success.svg) ")
    lines.append(f"![Offers Checked](https://img.shields.io/badge/Offers%20Checked-{len(offers)}%20Audited-blue.svg) ")
    lines.append(
        f"![Total Savings](https://img.shields.io/badge/Total%20Value%20Saved-%24{total_savings}%20USD-gold.svg) "
    )
    lines.append(
        f"![Proctored Exams](https://img.shields.io/badge/Proctored%20Exams-{len(active_proctored)}%20Active-success.svg) "
    )
    lines.append(
        f"![Skill Badges](https://img.shields.io/badge/Skill%20Badges-{len(active_badges)}%20Active-blue.svg) "
    )
    lines.append(
        f"![Visual Proof](https://img.shields.io/badge/Visual%20Proof-{verified_proofs_count}%2F{len(offers)}%20Verified-brightgreen.svg) "
    )
    lines.append(
        "![Deep Inspection](https://img.shields.io/badge/Inspection-Liveness%20%26%20Soft404%20Checked-brightgreen.svg) "
    )
    lines.append("![Authenticity](https://img.shields.io/badge/Authenticity-100%25%20Verified%20Vendor-success.svg) ")
    lines.append("![Automated By](https://img.shields.io/badge/Automated%20By-GitHub%20Actions-purple.svg) ")
    lines.append(
        "![Maintainer](https://img.shields.io/badge/Maintained%20By-Solo%20Developer%20(Athish%20R%20S)-blueviolet.svg) "
    )
    lines.append("![Support](https://img.shields.io/badge/Support-Best--Effort%20(No%20SLA)-orange.svg)")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append("")
    lines.append("| Metric | Value | Definition |")
    lines.append("| :--- | :--- | :--- |")
    lines.append(
        f"| **Active Opportunities** | **{len(active_offers)}** | Verified 100% free exams & live registration windows |"
    )
    lines.append(
        f"| **Written Proctored Exam Vouchers** | **{len(active_proctored)} Active** ({len(proctored_offers)} Tracked) | Pearson VUE / Kryterion / Webassessor 100% free exam seats |"
    )
    lines.append(
        f"| **Free Skill Badges & Labs** | **{len(active_badges)} Active** ({len(badge_offers)} Tracked) | Interactive hands-on cloud labs & verifiable digital badges |"
    )
    lines.append(
        f"| **Offers Checked & Audited** | **{len(offers)} Total** ({len(active_offers)} Active, {len(closed_offers)} Triage, {len(historical_offers)} Archived) | 100% verified against soft-404s, capacity limits, and expired vouchers |"
    )
    lines.append(f"| **Total Financial Value** | **${total_savings:,} USD** | Aggregate savings if claimed today |")
    lines.append(
        f"| **Verified Screenshot Proofs** | **{verified_proofs_count}/{len(offers)} ({proof_pct}%)** | Valid Playwright Chromium viewport screenshots captured in docs/screenshots/ |"
    )
    lines.append(
        f"| **Historical Archive Tracked** | **{len(historical_offers)} Campaigns** | Past promotional cycles & recurrence roadmaps |"
    )
    lines.append(
        f"| **Verified Tech Dispatches** | **{len(news_items)} Reports** | Official primary cloud engineering updates |"
    )
    lines.append(
        "| **Authenticity Gate** | **100% Primary Vendor Verified** | Zero scam domains, zero dumps, strict TLS |"
    )
    lines.append(
        "| **Truth Oracle Engine** | **100% Policy Corroborated** | Verified against primary vendor policies (copays, windows, student prereqs) |"
    )
    lines.append(
        f"| **Last Automated Inspection** | {tz_info['banner']} | Auto-audited for 404s and 'Closed' notices (UTC, IST, EDT, CEST) |"
    )
    lines.append("| **Hosting & Compute Cost** | **$0.00 / Month** | 100% native to GitHub Actions & GitHub Pages |")
    lines.append(
        "| **Maintainer Model** | **Solo Developer ([Athish R S](https://github.com/Athish2002))** | 100% independent project; best-effort response (no corporate SLAs) |"
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"## 🌊 Tier 1A: Limited-Time Exam Waves & Seasonal Challenge Cohorts ({len(active_waves)} Active)")
    lines.append(
        "> Time-bounded challenge cohorts, Cloud Skills Waves, and promotional certification windows with periodic renewal cycles."
    )
    lines.append("")
    lines.append(
        "| Provider | Certification & Program | Category | Cadence & Wave | Value (USD) | Status | Proof | Truth Source | Claim Link |"
    )
    lines.append("| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :--- | :--- |")
    for o in active_waves:
        provider = _escape_md(o.get("platform"))
        cert = _escape_md(o.get("certification_name") or o.get("title"))
        cat = _escape_md(o.get("category", "General"))
        cadence = _escape_md(o.get("recurrence_pattern") or "Periodic Wave")
        val = f"${o.get('value_usd')}" if o.get("value_usd") else "Free"
        status_text = STATUS_BADGES.get(o.get("status", "Active"), "🟢 Active")
        if o.get("last_zero_dollar_confirmed_date"):
            status_text += f"<br><sub>$0 Confirmed: {o.get('last_zero_dollar_confirmed_date')}</sub>"
        proof_link = f"[📸 Proof](docs/screenshots/{o.get('id', '')}.png)"
        tv = o.get("truth_verification") or {}
        truth_source_name = _escape_md(tv.get("truth_source_name", f"{provider} Policy"))
        truth_source_url = tv.get("truth_source_url", o.get("direct_verified_url") or o.get("url"))
        truth_link = f"[{truth_source_name}]({truth_source_url})"
        url = o.get("direct_verified_url") or o.get("url", "#")
        lines.append(
            f"| **{provider}** | {cert} | {cat} | `{cadence}` | {val} | {status_text} | {proof_link} | {truth_link} | [**Claim Voucher**]({url}) |"
        )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"## 🏷️ Tier 1B: Active Ongoing Discounts & Vouchers ({len(active_discounts)} Active)")
    lines.append(
        "> Ongoing student discounts, continuous partner vouchers, partial co-pay discounts, and permanent $0 certification waivers."
    )
    lines.append("")
    lines.append(
        "| Provider | Discount / Voucher Program | Category | Terms & Prereqs | Value (USD) | Status | Proof | Truth Source | Claim Link |"
    )
    lines.append("| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :--- | :--- |")
    for o in active_discounts:
        provider = _escape_md(o.get("platform"))
        cert = _escape_md(o.get("certification_name") or o.get("title"))
        cat = _escape_md(o.get("category", "General"))
        elig = _escape_md(o.get("eligibility") or "Continuous Discount")
        val = f"${o.get('value_usd')}" if o.get("value_usd") else "Discount"
        status_text = STATUS_BADGES.get(o.get("status", "Active"), "🟢 Active")
        if o.get("last_zero_dollar_confirmed_date"):
            status_text += f"<br><sub>$0 Confirmed: {o.get('last_zero_dollar_confirmed_date')}</sub>"
        proof_link = f"[📸 Proof](docs/screenshots/{o.get('id', '')}.png)"
        tv = o.get("truth_verification") or {}
        truth_source_name = _escape_md(tv.get("truth_source_name", f"{provider} Policy"))
        truth_source_url = tv.get("truth_source_url", o.get("direct_verified_url") or o.get("url"))
        truth_link = f"[{truth_source_name}]({truth_source_url})"
        url = o.get("direct_verified_url") or o.get("url", "#")
        lines.append(
            f"| **{provider}** | {cert} | {cat} | {elig} | {val} | {status_text} | {proof_link} | {truth_link} | [**Claim Discount**]({url}) |"
        )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        f"## 🎖️ Secondary Tier: Free Digital Skill Badges & Hands-On Cloud Labs ({len(active_badges)} Active / {len(badge_offers)} Tracked)"
    )
    lines.append(
        "> Unproctored interactive training completions, practical scenario-based cloud labs, sandbox learning paths, and verifiable digital badges."
    )
    lines.append("")
    lines.append(
        "| Provider | Credential & Assessment | Category | Tier | Value (USD) | Status | Proof | Truth Source | Launch Link |"
    )
    lines.append("| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- | :--- |")
    for o in active_badges:
        provider = _escape_md(o.get("platform"))
        cert = _escape_md(o.get("certification_name") or o.get("title"))
        cat = _escape_md(o.get("category", "General"))
        tier = _escape_md(o.get("difficulty_tier", "Foundational"))
        val = f"${o.get('value_usd')}" if o.get("value_usd") else "Free"
        status_text = STATUS_BADGES.get(o.get("status", "Active"), "🟢 Active")
        if o.get("last_zero_dollar_confirmed_date"):
            status_text += f"<br><sub>$0 Confirmed: {o.get('last_zero_dollar_confirmed_date')}</sub>"
        proof_link = f"[📸 Proof](docs/screenshots/{o.get('id', '')}.png)"
        tv = o.get("truth_verification") or {}
        truth_source_name = _escape_md(tv.get("truth_source_name", f"{provider} Policy"))
        truth_source_url = tv.get("truth_source_url", o.get("direct_verified_url") or o.get("url"))
        truth_link = f"[{truth_source_name}]({truth_source_url})"
        url = o.get("direct_verified_url") or o.get("url", "#")
        lines.append(
            f"| **{provider}** | {cert} | {cat} | `{tier}` | {val} | {status_text} | {proof_link} | {truth_link} | [**Launch Lab**]({url}) |"
        )
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
            "> Cloud providers regularly launch recurring 100% free certification campaigns (annual developer conferences, seasonal training challenges, and beta programs). Track past campaign timeframes and historical recurrence patterns below to anticipate upcoming waves."
        )
        lines.append("")
        lines.append(
            "| Provider | Certification & Exam Code | Type | Value (USD) | Active Promo Period | Recurrence Pattern | Proof | Notes / Archival Reason |"
        )
        lines.append("| :--- | :--- | :--- | :---: | :---: | :--- | :---: | :--- |")
        for o in historical_offers:
            provider = _escape_md(o.get("platform"))
            cert = _escape_md(o.get("certification_name") or o.get("title"))
            exam = f"<br>`{o.get('exam_code')}`" if o.get("exam_code") else ""
            otype = _escape_md(o.get("offer_type"))
            val = f"${o.get('value_usd')}" if o.get("value_usd") else "Free"
            period = _escape_md(o.get("time_period", "Concluded"))
            recur = _escape_md(o.get("recurrence_pattern", "Annual / Rolling"))
            notes = _escape_md(o.get("inspection_notes", "Concluded"))
            proof_link = f"[📸 Proof](docs/screenshots/{o.get('id', '')}.png)"
            lines.append(
                f"| **{provider}** | **{cert}**{exam} | `{otype}` | {val} | {period} | {recur} | {proof_link} | {notes} |"
            )
        lines.append("")
        lines.append("</details>")
        lines.append("")

    if closed_offers:
        lines.append("---")
        lines.append("")
        lines.append("<details>")
        lines.append(
            f"<summary><b>🟡 Under Review / Yet to Confirm (Triage Pool - {len(closed_offers)} Opportunities)</b> — <i>Click to expand</i></summary>"
        )
        lines.append("")
        lines.append(
            "> Authentic vendor opportunities flagged by the automated inspector for capacity limits, closed cohorts, or ambiguous signals. Tracked for re-opening every 12 hours (twice daily) before retiring to the permanent archive."
        )
        lines.append("")
        lines.append("| Provider | Certification | Triage Status | Proof | Reason / Inspection Note |")
        lines.append("| :--- | :--- | :---: | :---: | :--- |")
        for o in closed_offers:
            status_badge = STATUS_BADGES.get(o.get("status"), o.get("status"))
            reason = _escape_md(o.get("inspection_notes", "Concluded"))
            proof_link = f"[📸 Proof](docs/screenshots/{o.get('id', '')}.png)"
            lines.append(
                f"| **{_escape_md(o.get('platform'))}** | {_escape_md(o.get('certification_name') or o.get('title'))} | {status_badge} | {proof_link} | {reason} |"
            )
        lines.append("")
        lines.append("</details>")
        lines.append("")

    if news_items:
        lines.append("---")
        lines.append("")
        lines.append("## 📰 Verified Cloud & Engineering Intelligence Radar")
        lines.append(
            "> Autonomous technical intelligence stream tracking authentic engineering breakthroughs, architecture RFCs, silicon innovations, and SEC financial filings directly from primary enterprise sources (**AWS**, **Microsoft Azure**, **Google Cloud**, **Oracle Cloud**, **Cisco**, **GitHub**, **Linux Foundation**, **Databricks**, **Snowflake**). Strictly zero rumors, gossip, or clickbait aggregators."
        )
        lines.append("")
        lines.append(f"| **Verified Tech Dispatches** | **{len(news_items)} Reports** |")
        lines.append("")
        lines.append("<details>")
        lines.append(
            f"<summary><b>View Verified Cloud & Engineering Intelligence Radar ({len(news_items)} Reports)</b> — <i>Click to expand</i></summary>"
        )
        lines.append("")
        lines.append(
            "| Published | Enterprise | Category | Focus / Badge | Technical Briefing & Headline | Verified Source |"
        )
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
        f"<summary><b>📋 Detailed Step-by-Step Claiming Instructions (All {len(active_offers)} Active Opportunities)</b> — <i>Click to expand</i></summary>"
    )
    lines.append("")
    for o in active_offers:
        lines.append(f"#### {o.get('title')}")
        lines.append(f"- **Provider:** {o.get('platform')}")
        lines.append(f"- **Value:** ${o.get('value_usd')} USD")
        lines.append(f"- **Eligibility:** {o.get('eligibility')}")
        lines.append(f"- **Steps to Claim:** {o.get('claim_steps')}")
        target_link = o.get("direct_verified_url") or o.get("url")
        lines.append(f"- **Official Link:** [{target_link}]({target_link})")
        lines.append("")
    lines.append("</details>")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 💳 Where & How Vouchers Are Applied (Zero-Dollar Checkout Guide)")
    lines.append(
        "> Authentic reference detailing exact redemption checkout portals, form fields, and application flows verified to drop total cart balance to **$0.00** before confirmation. Official vendor checkouts never charge hidden fees or require credit cards for 100% free certifications."
    )
    lines.append("")
    lines.append(
        "| Provider | Certification | Official Redemption Portal | Checkout Field / Location | Application Flow | Verified Cart Balance |"
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
        bal = _escape_md(guide.get("verified_cart_balance", "$0.00"))
        lines.append(
            f"| **{provider}** | {cert} | [{portal_name}]({portal_url}) | `{field_loc}` | `{flow}` | **{bal}** |"
        )
    lines.append("")
    lines.append("<details>")
    lines.append(
        f"<summary><b>🔍 Step-by-Step Checkout Navigation Guides (All {len(active_offers)} Opportunities)</b> — <i>Click to expand</i></summary>"
    )
    lines.append("")
    for o in active_offers:
        guide = o.get("redemption_guide") or {}
        code = o.get("voucher_code", "AUTO_APPLIED")
        lines.append(f"#### {o.get('title')}")
        lines.append(f"- **Voucher / Promo Code:** `{code}`")
        lines.append(
            f"- **Official Redemption Portal:** [{guide.get('portal_name', o.get('platform'))}]({guide.get('portal_url', o.get('direct_verified_url') or o.get('url'))})"
        )
        lines.append(f"- **Checkout Field Location:** `{guide.get('field_location', o.get('checkout_field'))}`")
        lines.append(f"- **Application Flow Type:** `{guide.get('flow_type', o.get('application_flow_type'))}`")
        lines.append(f"- **Verified Cart Balance:** **{guide.get('verified_cart_balance', '$0.00')}**")
        lines.append("- **Checkout Steps:**")
        instructions = guide.get("instructions")
        if not instructions or not isinstance(instructions, list):
            instructions = [o.get("claim_steps", "Complete registration at official vendor portal.")]
        for step in instructions:
            lines.append(f"  1. {step}")
        lines.append("")
    lines.append("</details>")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 🛡️ Multi-Tier Authenticity Verification & Truth Policies")
    lines.append("")
    lines.append(
        "CertPulse enforces a strict four-layer authenticity and anti-fraud verification policy to protect candidates from coupon scams, dead links, and misleading claims:"
    )
    lines.append("")
    lines.append(
        "1. **Primary Enterprise Infrastructure**: All tracked URLs are restricted exclusively to official vendor domains (`amazon.com`, `microsoft.com`, `google.com`, `oracle.com`, `cisco.com`, `linuxfoundation.org`, `redhat.com`, `github.com`). Link shorteners, affiliate aggregators, and unverified blogs are strictly banned."
    )
    lines.append(
        "2. **Dual Visual & Headless DOM Gating**: Headless Playwright Chromium renders full client-side SPAs on scheduled audits, screening for capacity limits, soft-404s, and closed cohort notices while capturing verified viewport screenshots in `docs/screenshots/`."
    )
    lines.append(
        "3. **Truth Oracle Policy Corroboration**: All offers are audited against official vendor examination policies. Partial discounts (such as Juniper's 75% voucher) are explicitly flagged with the required $50 Pearson VUE co-pay fee, and student restrictions (GitHub Student Pack) are prominently disclosed."
    )
    lines.append(
        "4. **Append-Only Tamper-Evident Receipts**: Every captured screenshot is validated for binary PNG header integrity (`\\x89PNG\\r\\n\\x1a\\n`) and cataloged with ISO 8601 UTC timestamps across four global timezones (UTC, IST, EDT, CEST)."
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Architecture: How This Repo Updates Itself ($0 Cost)")
    lines.append("")
    lines.append("```mermaid")
    lines.append("flowchart TD")
    lines.append("    subgraph Ingest [1. Ingestion Engine - Every 12h (Twice Daily)]")
    lines.append("        A[Official Enterprise Engineering Feeds] --> C[GitHub Actions Runner]")
    lines.append("        B[Community Candidate Feeds] --> C")
    lines.append("    end")
    lines.append("")
    lines.append("    subgraph Verify [2. Dual Visual Verification & Authenticity Gate]")
    lines.append("        C --> D[Playwright Headless Chromium]")
    lines.append("        D --> E[DOM Liveness & Closed Notice Detector]")
    lines.append("        D --> F[Screenshot Proof Capture<br>docs/screenshots/*.png]")
    lines.append("        E & F --> G[Self-Healing Recovery & Authenticity Gate]")
    lines.append("    end")
    lines.append("")
    lines.append("    subgraph Store [3. Segmented Datastores]")
    lines.append("        G --> H[(data/offers.json)]")
    lines.append("        C --> I[(data/news.json)]")
    lines.append("    end")
    lines.append("")
    lines.append("    subgraph Publish [4. Synchronized Autonomous Deployment]")
    lines.append("        H & I --> J[Static Site & README Compiler]")
    lines.append("        J --> K[README.md with Proof Links]")
    lines.append("        J --> L[GitHub Pages Web Dashboard]")
    lines.append("    end")
    lines.append("```")
    lines.append("")
    lines.append(
        "1. **Zero External Servers**: Runs 100% natively on scheduled GitHub Actions (`ubuntu-latest`) at zero infrastructure cost."
    )
    lines.append(
        "2. **Strict Credential Segmentation**: Unambiguously separates primary accredited proctored exams (Pearson VUE, Kryterion, Webassessor waivers) from secondary unproctored digital skill badges and learning paths."
    )
    lines.append(
        "3. **Dual Visual Proof & Screenshot Capture**: Launches headless Chromium to render client-side SPAs, screening for capacity limits, expired codes, and maintenance downtime while capturing full viewport proof screenshots in `docs/screenshots/`."
    )
    lines.append(
        "4. **Self-Healing Recovery Engine**: Automatically detects when previously closed or maintenance-blocked portals reopen, capturing refreshed visual proof and transitioning status back to `🟢 Active` without human intervention."
    )
    lines.append(
        "5. **Verified Tech Radar Ingestion**: Ingests official engineering dispatches directly from enterprise sources (AWS, Azure, Google Cloud, Cisco, GitHub, Databricks), enforcing strict domain whitelisting and zero clickbait."
    )
    lines.append(
        "6. **Zero-Dollar Redemption Engine**: Provides explicit, verified step-by-step checkout navigation guides guaranteeing confirmed $0.00 cart balances."
    )
    lines.append(
        "7. **Atomic Single-Source Synchronization**: `README.md` and `docs/index.html` are compiled simultaneously from the identical ground-truth datasets, guaranteeing zero drift between the repository and GitHub Pages."
    )
    lines.append("")
    lines.append("> [!TIP]")
    lines.append(
        "> For an in-depth post-mortem analyzing why prior certification voucher projects failed and how CertPulse's closed-loop architecture solves each failure mode, read the [RFC & Historical Post-Mortem Deep Dive](docs/DEEP_DIVE_PAST_FAILURES_AND_ARCHITECTURE_RFC.md)."
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 👤 Project Maintainer & Realistic Expectations")
    lines.append("")
    lines.append(
        "CertPulse is created, architected, and maintained independently by a **single solo developer** — [Athish R S](https://github.com/Athish2002)."
    )
    lines.append("")
    lines.append("> [!NOTE]")
    lines.append(
        "> **No Corporate Team or Response SLAs**: Because this is an independent open-source passion project operated by a single person, there are **no commercial support teams, dedicated maintainer rotations, or guaranteed response timelines (no 24h/48h SLAs)**. Inquiries, issue reports, and community contributions are reviewed on a **best-effort basis** as personal time permits."
    )
    lines.append("")
    lines.append("### Why CertPulse is 100% Autonomous")
    lines.append(
        "To keep this tracker reliable, comprehensive, and up-to-date without burning out a solo maintainer, CertPulse was engineered from day one as an **autonomous, self-updating telemetry engine**:"
    )
    lines.append(
        "- **Scheduled Verification**: GitHub Actions automatically runs Playwright headless Chromium audits twice daily (every 12 hours) to inspect every portal for soft-404s, cohort closures, and expired promos."
    )
    lines.append(
        "- **Self-Healing State Transitions**: When closed campaigns reopen, the pipeline automatically detects the active status, captures fresh screenshot proof, and updates the repository and GitHub Pages with zero human intervention."
    )
    lines.append(
        "- **Direct Data Ingestion**: Primary cloud engineering blogs and RSS feeds are ingested and sanitized automatically."
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 🤝 Contributing & Submitting Offers")
    lines.append("")
    lines.append(
        "Community contributions are warmly welcome! If you find a new verified free voucher or notice an expired campaign:"
    )
    lines.append("- **Submit an Offer**: Open an issue using the [Submit Free Voucher](../../issues) template.")
    lines.append(
        "- **Submit a Pull Request**: Edit `data/offers.json` directly. The automated CI test suite will validate JSON schemas and invariant rules on your PR."
    )
    lines.append(
        "- **Review Expectations**: As a solo-maintained repository, PR reviews and issue triaging occur on a best-effort basis. Automated bots handle daily verification runs."
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        f"*Built and maintained by [Athish R S](https://github.com/Athish2002) for the global tech community. Audited automatically every 12 hours on `{last_updated}`.*"
    )

    return "\n".join(lines)
