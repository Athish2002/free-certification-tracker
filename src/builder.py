"""
Builder module for CertPulse.
Compiles data/offers.json and data/news.json into:
1. Production-grade GitHub README.md with executive Bento stats, verified voucher tables, historical recurrence archive, and verified intelligence radar.
2. docs/index.html - Static interactive GitHub Primer web dashboard with Dark/Light Contrast modes, dual presentation views (Bento Grid & Catalog Table), and live verified tech radar.
"""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "offers.json"
NEWS_FILE = Path(__file__).resolve().parent.parent / "data" / "news.json"
README_FILE = Path(__file__).resolve().parent.parent / "README.md"
DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"
DOCS_HTML = DOCS_DIR / "index.html"

STATUS_BADGES = {
    "Active": "🟢 Active",
    "Registrations Closed": "🟡 Closed / Waitlist",
    "Expired": "🔴 Expired",
    "Broken Link": "⚠️ Broken Link",
    "Server Error": "⚠️ Server Error"
}

def load_offers() -> Dict[str, Any]:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def load_news() -> Dict[str, Any]:
    if not NEWS_FILE.exists():
        return {"news": []}
    with open(NEWS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def generate_readme(data: Dict[str, Any], news_data: Dict[str, Any] = None) -> str:
    if news_data is None:
        news_data = load_news()
        
    offers: List[Dict[str, Any]] = data.get("offers", [])
    news_items: List[Dict[str, Any]] = news_data.get("news", [])
    
    active_offers = [o for o in offers if o.get("status") == "Active"]
    closed_offers = [o for o in offers if o.get("status") != "Active" and not o.get("is_historical_archive")]
    historical_offers = [o for o in offers if o.get("is_historical_archive")]
    
    total_savings = sum((o.get("value_usd") or 0) for o in active_offers)
    last_updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    
    # Categorize active offers
    categories = {}
    for o in active_offers:
        cat = o.get("category", "General")
        categories.setdefault(cat, []).append(o)

    lines = []
    lines.append("# CertPulse: Autonomous Free Cloud & Tech Certification Tracker")
    lines.append("")
    lines.append(f"> **Automated, 100% free, and self-updating repository** tracking verified 100% free certification exam vouchers, accredited micro-credentials, and continuing education credits across AWS, Azure, Google Cloud, Cisco, ISC2, Oracle, Linux Foundation / CNCF, Snowflake, Databricks, Red Hat, HashiCorp, Palo Alto Networks, GitLab, Splunk, IBM, and GitHub.")
    lines.append("")
    lines.append("![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg) ")
    lines.append(f"![Active Vouchers](https://img.shields.io/badge/Active%20Offers-{len(active_offers)}-success.svg) ")
    lines.append(f"![Total Savings](https://img.shields.io/badge/Total%20Value%20Saved-%24{total_savings}%20USD-gold.svg) ")
    lines.append("![Deep Inspection](https://img.shields.io/badge/Inspection-Liveness%20%26%20Soft404%20Checked-brightgreen.svg) ")
    lines.append("![Authenticity](https://img.shields.io/badge/Authenticity-100%25%20Verified%20Vendor-success.svg) ")
    lines.append("![Automated By](https://img.shields.io/badge/Automated%20By-GitHub%20Actions-purple.svg)")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append("")
    lines.append("| Metric | Value | Definition |")
    lines.append("| :--- | :--- | :--- |")
    lines.append(f"| **Active Opportunities** | **{len(active_offers)}** | Verified 100% free exams & live registration windows |")
    lines.append(f"| **Total Financial Value** | **${total_savings:,} USD** | Aggregate savings if claimed today |")
    lines.append(f"| **Historical Archive Tracked** | **{len(historical_offers)} Campaigns** | Past promotional cycles & recurrence roadmaps |")
    lines.append(f"| **Verified Tech Dispatches** | **{len(news_items)} Reports** | Official primary cloud engineering updates |")
    lines.append(f"| **Authenticity Gate** | **100% Primary Vendor Verified** | Zero scam domains, zero dumps, strict TLS |")
    lines.append(f"| **Last Automated Inspection** | `{last_updated}` | Auto-audited for 404s and 'Closed' notices |")
    lines.append("| **Hosting & Compute Cost** | **$0.00 / Month** | 100% native to GitHub Actions & GitHub Pages |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Verified Active Certification Offers")
    lines.append("")
    
    for cat_name, cat_offers in categories.items():
        lines.append(f"### {cat_name}")
        lines.append("")
        lines.append("| Provider | Certification & Program | Type | Value (USD) | Status | Authenticity | Claim Link |")
        lines.append("| :--- | :--- | :--- | :---: | :---: | :---: | :--- |")
        for o in cat_offers:
            provider = o.get("platform")
            cert = o.get("certification_name")
            val = f"${o.get('value_usd')}" if o.get('value_usd') else "Free"
            otype = o.get("offer_type")
            status_text = STATUS_BADGES.get(o.get("status", "Active"), "🟢 Active")
            auth_badge = f"🛡️ {o.get('authenticity_score', 100)}% Verified" if o.get("is_authentic_vendor", True) else "⚠️ Review Needed"
            url = o.get("url")
            lines.append(f"| **{provider}** | {cert} | `{otype}` | {val} | {status_text} | {auth_badge} | [**Claim Offer**]({url}) |")
        lines.append("")

    if historical_offers:
        lines.append("---")
        lines.append("")
        lines.append("## 📜 Historical Voucher Archive & Recurrence Patterns")
        lines.append("> Cloud providers regularly launch recurring 100% free certification campaigns (annual developer conferences, seasonal training challenges, and beta programs). Track past campaign timeframes and historical recurrence patterns below to anticipate upcoming waves.")
        lines.append("")
        lines.append("| Provider | Certification & Exam Code | Type | Value (USD) | Active Promo Period | Recurrence Pattern | Notes / Archival Reason |")
        lines.append("| :--- | :--- | :--- | :---: | :---: | :--- | :--- |")
        for o in historical_offers:
            provider = o.get("platform")
            cert = o.get("certification_name")
            exam = f"<br>`{o.get('exam_code')}`" if o.get("exam_code") else ""
            otype = o.get("offer_type")
            val = f"${o.get('value_usd')}" if o.get("value_usd") else "Free"
            period = o.get("time_period", "Concluded")
            recur = o.get("recurrence_pattern", "Annual / Rolling")
            notes = o.get("inspection_notes", "Concluded")
            lines.append(f"| **{provider}** | **{cert}**{exam} | `{otype}` | {val} | {period} | {recur} | {notes} |")
        lines.append("")
        
    if closed_offers:
        lines.append("---")
        lines.append("")
        lines.append("## Recently Closed / Expired Opportunities")
        lines.append("> These offers were active previously but our automated inspector detected that registration has reached capacity, expired, or returned an error.")
        lines.append("")
        lines.append("| Provider | Certification | Concluded Status | Reason / Inspection Note |")
        lines.append("| :--- | :--- | :---: | :--- |")
        for o in closed_offers:
            status_badge = STATUS_BADGES.get(o.get("status"), o.get("status"))
            reason = o.get("inspection_notes", "Concluded")
            lines.append(f"| **{o.get('platform')}** | {o.get('certification_name')} | {status_badge} | {reason} |")
        lines.append("")

    if news_items:
        lines.append("---")
        lines.append("")
        lines.append("## 📰 Verified Cloud & Engineering Intelligence Radar")
        lines.append("> Autonomous technical intelligence stream tracking authentic engineering breakthroughs, architecture RFCs, silicon innovations, and SEC financial filings directly from primary enterprise sources (**AWS**, **Microsoft Azure**, **Google Cloud**, **Oracle Cloud**, **Cisco**, **GitHub**, **Linux Foundation**, **Databricks**, **Snowflake**). Strictly zero rumors, gossip, or clickbait aggregators.")
        lines.append("")
        lines.append("| Published | Enterprise | Category | Focus / Badge | Technical Briefing & Headline | Verified Source |")
        lines.append("| :--- | :--- | :--- | :---: | :--- | :--- |")
        for item in news_items:
            date = item.get("published_date", "")
            company = item.get("company", "")
            cat = item.get("category", "")
            badge = f"`{item.get('impact_badge', '')}`" if item.get("impact_badge") else ""
            title = item.get("title", "")
            summary = item.get("summary", "")
            url = item.get("url", "")
            source_name = item.get("source", item.get("source_domain", ""))
            domain = item.get("source_domain", "")
            
            headline_cell = f"**[{title}]({url})**<br>{summary}"
            source_cell = f"[{source_name}]({url})<br>`{domain}`"
            lines.append(f"| `{date}` | **{company}** | {cat} | {badge} | {headline_cell} | {source_cell} |")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Detailed Claiming Instructions")
    lines.append("")
    for o in active_offers:
        lines.append(f"#### {o.get('title')}")
        lines.append(f"- **Provider:** {o.get('platform')}")
        lines.append(f"- **Value:** ${o.get('value_usd')} USD")
        lines.append(f"- **Eligibility:** {o.get('eligibility')}")
        lines.append(f"- **Steps to Claim:** {o.get('claim_steps')}")
        lines.append(f"- **Official Link:** [{o.get('url')}]({o.get('url')})")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Architecture: How This Repo Updates Itself ($0 Cost)")
    lines.append("")
    lines.append("```mermaid")
    lines.append("flowchart LR")
    lines.append("    A[Public RSS & Community Feeds] -->|Scheduled Cron every 4h| B[GitHub Actions Runner]")
    lines.append("    B -->|Inspect Liveness & Soft 404s| C[Deep Inspector Engine]")
    lines.append("    B -->|Poll Official Engineering Feeds| N[News Collector]")
    lines.append("    C -->|Classify & Flag Status| D[data/offers.json]")
    lines.append("    N -->|Filter Buzzwords & Verify Domains| M[data/news.json]")
    lines.append("    D & M -->|Static Builder| E[README.md]")
    lines.append("    D & M -->|Static Deploy| F[GitHub Pages Dashboard]")
    lines.append("```")
    lines.append("")
    lines.append("1. **Zero External Servers**: Runs directly on GitHub Actions (`ubuntu-latest`).")
    lines.append("2. **Deep Inspection Guardian**: The crawler not only checks HTTP status codes (404/500) but reads page HTML to spot 'Registrations Closed' or 'All vouchers claimed' notices.")
    lines.append("3. **Verified Tech Radar Ingestion**: Polls primary enterprise feeds, applies strict domain whitelisting, and enforces zero-clickbait heuristic filters.")
    lines.append("4. **Zero Git Noise**: Only commits changes to `README.md` and data stores when actual updates are detected.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Contributing & Submitting Offers")
    lines.append("")
    lines.append("Found a new free voucher or noticed an expired link?")
    lines.append("- Open an issue using the [Submit Free Voucher](../../issues) template.")
    lines.append("- Or open a quick PR editing `data/offers.json`.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"*Built for the tech community. Audited automatically on `{last_updated}`.*")
    
    return "\n".join(lines)

def generate_web_dashboard(data: Dict[str, Any], news_data: Dict[str, Any] = None) -> str:
    """Generates an authentic GitHub Primer web dashboard with Dark and Light Contrast modes, Bento & Table catalog views, and verified tech radar."""
    if news_data is None:
        news_data = load_news()
        
    offers = data.get("offers", [])
    news_items = news_data.get("news", [])
    
    active_offers = [o for o in offers if o.get("status") == "Active"]
    closed_offers = [o for o in offers if o.get("status") != "Active" and not o.get("is_historical_archive")]
    historical_offers = [o for o in offers if o.get("is_historical_archive")]
    total_savings = sum((o.get("value_usd") or 0) for o in active_offers)
    last_updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    
    offers_json_str = json.dumps(offers)
    news_json_str = json.dumps(news_items)
    
    cloud_count = sum(1 for o in offers if "Cloud" in o.get("category", "") or "Cloud" in o.get("platform", ""))
    sec_count = sum(1 for o in offers if "Security" in o.get("category", ""))
    devops_count = sum(1 for o in offers if "DevOps" in o.get("category", ""))
    ai_count = sum(1 for o in offers if "AI" in o.get("category", "") or "Data" in o.get("category", ""))
    net_count = sum(1 for o in offers if "Networking" in o.get("category", ""))
    
    return f"""<!DOCTYPE html>
<html lang="en" data-theme="dark" data-color-mode="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <meta name="theme-color" content="#0d1117" id="themeColorMeta">
    <title>CertPulse | Free Certification Directory & Tech Radar</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        /* GitHub Primer Dual Theme System: Dark & Light Contrast (Antigravity & Emil Design Craft) */
        :root {{
            --ease-out: cubic-bezier(0.23, 1, 0.32, 1);
        }}
        :root[data-theme="dark"] {{
            --canvas-default: #0d1117;
            --canvas-subtle: #161b22;
            --canvas-inset: #010409;
            --border-default: #30363d;
            --border-muted: #21262d;
            --fg-default: #e6edf3;
            --fg-muted: #848d97;
            --fg-subtle: #6e7681;
            --accent-fg: #2f81f7;
            --accent-emphasis: #1f6feb;
            --accent-subtle: rgba(56, 139, 253, 0.15);
            --success-fg: #3fb950;
            --success-emphasis: #238636;
            --success-subtle: rgba(46, 160, 67, 0.15);
            --attention-fg: #d29922;
            --attention-subtle: rgba(187, 128, 9, 0.15);
            --danger-fg: #f85149;
            --danger-subtle: rgba(248, 81, 73, 0.15);
            --btn-default-bg: #21262d;
            --btn-default-hover: #30363d;
            --btn-primary-bg: #238636;
            --btn-primary-hover: #2ea043;
            --card-shadow: 0 0 0 1px rgba(255, 255, 255, 0.08), 0 2px 4px rgba(0, 0, 0, 0.2), 0 8px 24px -4px rgba(0, 0, 0, 0.4);
            --card-shadow-hover: 0 0 0 1px rgba(56, 139, 253, 0.45), 0 4px 12px rgba(0, 0, 0, 0.3), 0 20px 40px -8px rgba(0, 0, 0, 0.65);
            --specular-rim: inset 0 1px 0 0 rgba(255, 255, 255, 0.12);
        }}
        :root[data-theme="light"] {{
            --canvas-default: #ffffff;
            --canvas-subtle: #f6f8fa;
            --canvas-inset: #f6f8fa;
            --border-default: #24292f;
            --border-muted: #57606a;
            --fg-default: #0e1116;
            --fg-muted: #4b535d;
            --fg-subtle: #6e7781;
            --accent-fg: #0550ae;
            --accent-emphasis: #0550ae;
            --accent-subtle: #ddf4ff;
            --success-fg: #116329;
            --success-emphasis: #116329;
            --success-subtle: #dafbe1;
            --attention-fg: #6e4d00;
            --attention-subtle: #fff8c5;
            --danger-fg: #a40e26;
            --danger-subtle: #ffebe9;
            --btn-default-bg: #f6f8fa;
            --btn-default-hover: #eaeef2;
            --btn-primary-bg: #116329;
            --btn-primary-hover: #0d4a1f;
            --card-shadow: 0 0 0 1px rgba(36, 41, 47, 0.12), 0 1px 2px rgba(36, 41, 47, 0.04), 0 4px 12px rgba(36, 41, 47, 0.04);
            --card-shadow-hover: 0 0 0 1px #0550ae, 0 3px 8px rgba(5, 80, 174, 0.12), 0 16px 32px -4px rgba(36, 41, 47, 0.15);
            --specular-rim: inset 0 1px 0 0 rgba(255, 255, 255, 0.9);
        }}

        * {{
            -webkit-tap-highlight-color: transparent;
        }}

        body {{
            background-color: var(--canvas-default);
            color: var(--fg-default);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif;
            transition: background-color 0.15s ease, color 0.15s ease;
            min-height: 100dvh;
        }}

        .primer-card {{
            background-color: var(--canvas-subtle);
            border: 1px solid var(--border-default);
            box-shadow: var(--card-shadow), var(--specular-rim);
            transition: transform 180ms var(--ease-out), 
                        box-shadow 180ms var(--ease-out), 
                        border-color 150ms ease;
        }}
        @media (hover: hover) and (pointer: fine) {{
            .primer-card:hover {{
                transform: translateY(-3px);
                box-shadow: var(--card-shadow-hover), var(--specular-rim);
                border-color: var(--accent-fg);
            }}
        }}

        /* Emil Kowalski Tactile Button Standard */
        button:active, a.tactile-btn:active {{
            transform: scale(0.98);
            transition: transform 80ms var(--ease-out);
        }}

        /* Accessible focus rings */
        input:focus-visible, select:focus-visible, button:focus-visible, a:focus-visible {{
            outline: 2px solid var(--accent-fg);
            outline-offset: 2px;
        }}

        /* Mobile Touch & Scroll Physics */
        .touch-scroll {{
            -webkit-overflow-scrolling: touch;
            scroll-behavior: smooth;
            overscroll-behavior-x: contain;
        }}

        /* Subtle scrollbars */
        ::-webkit-scrollbar {{
            width: 6px;
            height: 6px;
        }}
        ::-webkit-scrollbar-thumb {{
            background: var(--border-default);
            border-radius: 3px;
        }}

        .scrollbar-none::-webkit-scrollbar {{
            display: none;
        }}
        .scrollbar-none {{
            -ms-overflow-style: none;
            scrollbar-width: none;
        }}

        /* Prevent iOS auto-zoom on input focus */
        @media (max-width: 640px) {{
            input[type="text"], select {{
                font-size: 16px !important;
            }}
        }}
    </style>
</head>
<body class="min-h-[100dvh] flex flex-col antialiased selection:bg-blue-500/20">

    <!-- GitHub Top Navigation Bar (Mobile Optimized) -->
    <header class="border-b sticky top-0 z-40 backdrop-blur-md" style="background-color: var(--canvas-subtle); border-color: var(--border-default);">
        <div class="max-w-7xl mx-auto px-3.5 sm:px-6 lg:px-8 h-14 sm:h-16 flex items-center justify-between gap-2 sm:gap-4">
            
            <!-- Left: Brand Breadcrumb -->
            <div class="flex items-center gap-2 sm:gap-3 min-w-0">
                <a href="https://github.com/Athish2002/free-certification-tracker" target="_blank" class="hover:opacity-80 transition flex-shrink-0" aria-label="GitHub Repository">
                    <svg height="26" viewBox="0 0 16 16" width="26" style="fill: var(--fg-default);" class="sm:w-7 sm:h-7">
                        <path d="M8 0c4.42 0 8 3.58 8 8a8.013 8.013 0 0 1-5.45 7.59c-.4.08-.55-.17-.55-.38 0-.27.01-1.13.01-2.2 0-.75-.25-1.23-.54-1.48 1.78-.2 3.65-.88 3.65-3.95 0-.88-.31-1.59-.82-2.15.08-.2.36-1.02-.08-2.12 0 0-.67-.22-2.2.82-.64-.18-1.32-.27-2-.27-.68 0-1.36.09-2 .27-1.53-1.03-2.2-.82-2.2-.82-.44 1.1-.16 1.92-.08 2.12-.51.56-.82 1.28-.82 2.15 0 3.06 1.86 3.75 3.64 3.95-.23.2-.44.55-.51 1.07-.46.21-1.61.55-2.33-.66-.15-.24-.6-.83-1.23-.82-.67.01-.27.38.01.53.34.19.73.9.82 1.13.16.45.68 1.31 2.69.94 0 .67.01 1.3.01 1.49 0 .21-.15.45-.55.38A7.995 7.995 0 0 1 0 8c0-4.42 3.58-8 8-8Z"></path>
                    </svg>
                </a>
                <div class="flex items-center gap-1.5 sm:gap-2 text-xs sm:text-sm font-semibold min-w-0">
                    <span class="font-bold tracking-tight text-sm sm:text-base truncate" style="color: var(--fg-default);">CertPulse</span>
                    <span class="hidden md:inline" style="color: var(--fg-muted);">/</span>
                    <a href="https://github.com/Athish2002/free-certification-tracker" target="_blank" class="hidden md:inline hover:underline truncate max-w-[180px]" style="color: var(--fg-muted);">
                        free-certification-tracker
                    </a>
                    <span class="text-[10px] sm:text-xs px-1.5 sm:px-2 py-0.5 rounded-full font-medium flex-shrink-0" style="background-color: var(--canvas-inset); color: var(--fg-muted); border: 1px solid var(--border-default);">Public</span>
                </div>
            </div>

            <!-- Right: Controls & Dark/Light Toggle -->
            <div class="flex items-center gap-1.5 sm:gap-2.5 flex-shrink-0">
                <!-- Verified Live Badge (Desktop) -->
                <div class="hidden md:flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-md" style="background-color: var(--canvas-inset); border: 1px solid var(--border-default); color: var(--fg-muted);">
                    <span class="w-2 h-2 rounded-full animate-pulse" style="background-color: var(--success-fg);"></span>
                    <span>100% Free Directory</span>
                </div>

                <!-- Dark / Light Contrast Mode Toggle Button -->
                <button onclick="toggleTheme()" id="themeToggleBtn" title="Toggle Dark / Light Contrast Mode (T)" aria-label="Toggle Dark / Light Contrast Mode" class="h-10 w-10 sm:h-9 sm:w-auto sm:px-3 rounded-lg border text-xs font-semibold flex items-center justify-center gap-1.5 transition active:scale-[0.98] shadow-xs cursor-pointer" style="background-color: var(--btn-default-bg); border: 1px solid var(--border-default); color: var(--fg-default);">
                    <span id="themeIconSun" class="hidden flex items-center gap-1.5">
                        <svg class="w-4 h-4" viewBox="0 0 16 16" fill="currentColor">
                            <path d="M8 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM8 0a.75.75 0 0 1 .75.75v1.5a.75.75 0 0 1-1.5 0V.75A.75.75 0 0 1 8 0Zm0 13a.75.75 0 0 1 .75.75v1.5a.75.75 0 0 1-1.5 0v-1.5A.75.75 0 0 1 8 13ZM2.343 2.343a.75.75 0 0 1 1.061 0l1.06 1.061a.75.75 0 0 1-1.06 1.06l-1.06-1.06a.75.75 0 0 1 0-1.061Zm9.193 9.193a.75.75 0 0 1 1.06 0l1.061 1.06a.75.75 0 0 1-1.06 1.061l-1.061-1.06a.75.75 0 0 1 0-1.061ZM0 8a.75.75 0 0 1 .75-.75h1.5a.75.75 0 0 1 0 1.5H.75A.75.75 0 0 1 0 8Zm13 0a.75.75 0 0 1 .75-.75h1.5a.75.75 0 0 1 0 1.5h-1.5A.75.75 0 0 1 13 8ZM2.343 13.657a.75.75 0 0 1 0-1.06l1.06-1.061a.75.75 0 1 1 1.061 1.06l-1.06 1.061a.75.75 0 0 1-1.061 0Zm9.193-9.193a.75.75 0 0 1 0-1.06l1.061-1.061a.75.75 0 0 1 1.06 1.06l-1.06 1.061a.75.75 0 0 1-1.061 0Z"></path>
                        </svg>
                        <span class="hidden sm:inline">Light</span>
                    </span>
                    <span id="themeIconMoon" class="hidden flex items-center gap-1.5">
                        <svg class="w-4 h-4" viewBox="0 0 16 16" fill="currentColor">
                            <path d="M9.598 1.591a.749.749 0 0 1 .785-.175 7.001 7.001 0 1 1-8.967 8.967.75.75 0 0 1 .961-.96 5.5 5.5 0 0 0 7.046-7.046.75.75 0 0 1 .175-.786Zm1.616 1.945a7 7 0 0 1-7.678 7.678 5.499 5.499 0 1 0 7.678-7.678Z"></path>
                        </svg>
                        <span class="hidden sm:inline">Dark</span>
                    </span>
                </button>

                <!-- GitHub Star CTA -->
                <a href="https://github.com/Athish2002/free-certification-tracker" target="_blank" aria-label="Star CertPulse on GitHub" class="h-10 w-10 sm:h-9 sm:w-auto sm:px-3 rounded-lg border text-xs font-semibold flex items-center justify-center gap-1.5 transition active:scale-[0.98] shadow-xs cursor-pointer" style="background-color: var(--btn-default-bg); border: 1px solid var(--border-default); color: var(--fg-default);">
                    <svg height="14" viewBox="0 0 16 16" width="14" fill="currentColor">
                        <path d="M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.751.751 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.751.751 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Z"></path>
                    </svg>
                    <span class="hidden sm:inline">Star</span>
                </a>
            </div>
        </div>
    </header>

    <!-- Top Navigation Tabs: Active Certifications vs Industry Tech Radar -->
    <nav class="border-b" style="background-color: var(--canvas-subtle); border-color: var(--border-default);">
        <div class="max-w-7xl mx-auto px-3.5 sm:px-6 lg:px-8 flex items-center justify-between">
            <div class="flex items-center gap-1 sm:gap-2 -mb-px overflow-x-auto touch-scroll scrollbar-none w-full sm:w-auto" id="mainTabNav">
                <button id="tabBtnVouchers" onclick="switchMainTab('vouchers')" class="flex items-center gap-2 py-3 px-3 sm:px-4 border-b-2 font-semibold text-xs sm:text-sm transition flex-shrink-0 active:scale-[0.98] min-h-[44px]" style="border-color: var(--accent-fg); color: var(--fg-default);">
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" class="flex-shrink-0">
                        <path d="M1 3.5A1.5 1.5 0 0 1 2.5 2h11A1.5 1.5 0 0 1 15 3.5v2a1.5 1.5 0 0 1-1.5 1.5.5.5 0 0 0 0 1 1.5 1.5 0 0 1 1.5 1.5v2a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 1 11.5v-2a1.5 1.5 0 0 1 1.5-1.5.5.5 0 0 0 0-1A1.5 1.5 0 0 1 1 5.5v-2Zm1.5-.5a.5.5 0 0 0-.5.5v2a2.5 2.5 0 0 0 1.5 2.298v.404A2.5 2.5 0 0 0 2 10.5v2a.5.5 0 0 0 .5.5h11a.5.5 0 0 0 .5-.5v-2a2.5 2.5 0 0 0-1.5-2.298v-.404A2.5 2.5 0 0 0 14 5.5v-2a.5.5 0 0 0-.5-.5h-11Z"></path>
                    </svg>
                    <span><span class="hidden xs:inline">Certification </span>Vouchers</span>
                    <span id="tabBadgeVouchers" class="text-[10px] sm:text-xs px-2 py-0.5 rounded-full font-medium tabular-nums border" style="background-color: var(--accent-subtle); color: var(--accent-fg); border-color: var(--accent-fg);">{len(offers)}</span>
                </button>
                <button id="tabBtnNews" onclick="switchMainTab('news')" class="flex items-center gap-2 py-3 px-3 sm:px-4 border-b-2 font-medium text-xs sm:text-sm transition flex-shrink-0 active:scale-[0.98] min-h-[44px]" style="border-color: transparent; color: var(--fg-muted);">
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" class="flex-shrink-0">
                        <path d="M0 1.75C0 .784.784 0 1.75 0h12.5C15.216 0 16 .784 16 1.75v10.5A1.75 1.75 0 0 1 14.25 14H1.75A1.75 1.75 0 0 1 0 12.25Zm1.75-.25a.25.25 0 0 0-.25.25v10.5c0 .138.112.25.25.25h12.5a.25.25 0 0 0 .25-.25V1.75a.25.25 0 0 0-.25-.25ZM3 3h10a.75.75 0 0 1 0 1.5H3A.75.75 0 0 1 3 3Zm0 3.5h10a.75.75 0 0 1 0 1.5H3a.75.75 0 0 1 0-1.5ZM3 10h6a.75.75 0 0 1 0 1.5H3A.75.75 0 0 1 3 10Z"></path>
                    </svg>
                    <span><span class="hidden xs:inline">Industry </span>Tech Radar</span>
                    <span id="tabBadgeNews" class="text-[10px] sm:text-xs px-2 py-0.5 rounded-full font-medium tabular-nums border" style="background-color: var(--canvas-inset); color: var(--fg-muted); border-color: var(--border-default);">{len(news_items)}</span>
                </button>
            </div>
            
            <div class="hidden lg:flex items-center gap-2 text-xs" style="color: var(--fg-subtle);">
                <span class="text-[11px] font-medium">Hotkeys:</span>
                <kbd class="px-1.5 py-0.5 rounded border text-[10px] font-mono" style="background-color: var(--canvas-default); border-color: var(--border-default);">V</kbd>
                <span>Views</span>
                <kbd class="px-1.5 py-0.5 rounded border text-[10px] font-mono" style="background-color: var(--canvas-default); border-color: var(--border-default);">1</kbd>
                <span>Vouchers</span>
                <kbd class="px-1.5 py-0.5 rounded border text-[10px] font-mono" style="background-color: var(--canvas-default); border-color: var(--border-default);">2</kbd>
                <span>Radar</span>
                <kbd class="px-1.5 py-0.5 rounded border text-[10px] font-mono" style="background-color: var(--canvas-default); border-color: var(--border-default);">T</kbd>
                <span>Theme</span>
            </div>
        </div>
    </nav>

    <!-- Main Container -->
    <main class="max-w-7xl mx-auto px-3.5 sm:px-6 lg:px-8 py-5 sm:py-8 flex-1 w-full min-w-0">
        
        <!-- SECTION 1: CERTIFICATION VOUCHERS -->
        <div id="vouchersSection">
            <!-- Hero Bento Grid (Asymmetrical Executive Standard) -->
            <div class="grid grid-cols-1 lg:grid-cols-12 gap-3.5 sm:gap-4 mb-5 sm:mb-8">
                <!-- Anchor Bento: Total Financial Value (Col-Span 6 on LG) -->
                <div class="lg:col-span-6 p-4 sm:p-6 rounded-2xl border primer-card relative overflow-hidden flex flex-col justify-between">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center gap-2">
                            <span class="w-2 h-2 rounded-full animate-pulse" style="background-color: var(--success-fg);"></span>
                            <span class="text-xs font-semibold" style="color: var(--fg-muted);">Live Financial Value</span>
                        </div>
                        <span class="p-1.5 sm:p-2 rounded-lg flex-shrink-0" style="background-color: var(--success-subtle); color: var(--success-fg); border: 1px solid var(--success-fg);">
                            <svg width="18" height="18" viewBox="0 0 16 16" fill="currentColor">
                                <path d="M8.75.75a.75.75 0 0 0-1.5 0V2h-.984c-.983 0-1.9.362-2.589 1.026C3.003 3.673 2.6 4.595 2.6 5.64c0 .91.308 1.688.886 2.26.567.562 1.34.942 2.264 1.192l.67.182c.76.205 1.25.437 1.53.685.26.23.35.474.35.743 0 .365-.154.67-.44.89-.3.23-.743.358-1.36.358-.603 0-1.05-.122-1.38-.342a1.29 1.29 0 0 1-.53-.872.75.75 0 0 0-1.49.172c.153.998.666 1.734 1.45 2.198.647.383 1.488.582 2.47.604v1.18a.75.75 0 0 0 1.5 0v-1.19c.983-.024 1.834-.34 2.483-.93.673-.613 1.017-1.472 1.017-2.46 0-.895-.316-1.66-.908-2.23-.58-.558-1.38-.93-2.316-1.182l-.645-.175c-.75-.204-1.223-.424-1.48-.656-.239-.214-.34-.442-.34-.707 0-.323.14-.597.412-.792.292-.21.72-.32 1.288-.32.535 0 .944.103 1.222.288.29.193.473.488.547.88a.75.75 0 0 0 1.478-.276c-.16-.862-.573-1.543-1.25-1.986A4.323 4.323 0 0 0 8.75 3.2V.75Z"></path>
                            </svg>
                        </span>
                    </div>
                    <div class="mt-3 sm:mt-4">
                        <div class="text-2xl sm:text-4xl font-extrabold tracking-tight tabular-nums" style="color: var(--fg-default);">
                            ${total_savings:,} <span class="text-xs sm:text-base font-normal font-sans" style="color: var(--fg-muted);">USD Available</span>
                        </div>
                        <p class="text-xs sm:text-sm mt-1.5 sm:mt-2 leading-relaxed text-pretty max-w-[65ch]" style="color: var(--fg-muted);">
                            Aggregate tuition value of verified 100% free proctored cloud exams, accredited credentials, and official vendor grants.
                        </p>
                    </div>
                </div>

                <!-- Bento 2: Active Opportunities (Col-Span 3 on LG) -->
                <div class="lg:col-span-3 p-4 sm:p-6 rounded-2xl border primer-card flex flex-col justify-between">
                    <div class="flex items-center justify-between">
                        <span class="text-xs font-semibold" style="color: var(--fg-muted);">Opportunities</span>
                        <span class="p-1.5 sm:p-2 rounded-lg flex-shrink-0" style="background-color: var(--accent-subtle); color: var(--accent-fg); border: 1px solid var(--accent-fg);">
                            <svg width="18" height="18" viewBox="0 0 16 16" fill="currentColor">
                                <path d="M13.78 4.22a.75.75 0 0 1 0 1.06l-7.25 7.25a.75.75 0 0 1-1.06 0L2.22 9.28a.751.751 0 0 1 .018-1.042.751.751 0 0 1 1.042-.018L6 10.94l6.72-6.72a.75.75 0 0 1 1.06 0Z"></path>
                            </svg>
                        </span>
                    </div>
                    <div class="mt-3 sm:mt-4">
                        <div class="text-xl sm:text-3xl font-extrabold tracking-tight tabular-nums" style="color: var(--success-fg);">
                            {len(active_offers)} <span class="text-xs sm:text-sm font-normal font-sans" style="color: var(--fg-muted);">Active</span>
                        </div>
                        <p class="text-xs mt-1.5 sm:mt-2 leading-relaxed text-pretty" style="color: var(--fg-muted);">
                            {len(historical_offers)} historical promotional cycles archived for recurrence tracking.
                        </p>
                    </div>
                </div>

                <!-- Bento 3: Official Verification (Col-Span 3 on LG) -->
                <div class="lg:col-span-3 p-4 sm:p-6 rounded-2xl border primer-card flex flex-col justify-between">
                    <div class="flex items-center justify-between">
                        <span class="text-xs font-semibold" style="color: var(--fg-muted);">Authenticity Standard</span>
                        <span class="p-1.5 sm:p-2 rounded-lg flex-shrink-0" style="background-color: var(--attention-subtle); color: var(--attention-fg); border: 1px solid var(--attention-fg);">
                            <svg width="18" height="18" viewBox="0 0 16 16" fill="currentColor">
                                <path d="M7.462.166a.75.75 0 0 1 .538 0l6.25 2.5a.75.75 0 0 1 .478.704c0 4.195-2.067 8.046-5.83 10.428a.75.75 0 0 1-.806 0C4.317 11.416 2.25 7.565 2.25 3.37a.75.75 0 0 1 .478-.704l6.25-2.5Zm.538 1.558L2.75 3.82c.117 3.518 1.83 6.758 4.996 8.847 3.165-2.089 4.88-5.329 4.996-8.847L8 1.724Z"></path>
                            </svg>
                        </span>
                    </div>
                    <div class="mt-3 sm:mt-4">
                        <div class="text-xl sm:text-3xl font-extrabold tracking-tight tabular-nums" style="color: var(--attention-fg);">
                            100% Authentic <span class="text-xs sm:text-sm font-normal font-sans" style="color: var(--fg-muted);">Verified</span>
                        </div>
                        <p class="text-xs mt-1.5 sm:mt-2 leading-relaxed text-pretty" style="color: var(--fg-muted);">
                            Zero scam domains, zero dumps, strict TLS & official vendor corroboration.
                        </p>
                    </div>
                </div>
            </div>

            <!-- Prominent Command-Bar Search Experience (UX Enhanced & Mobile Optimized) -->
            <div class="mb-4">
                <div class="relative w-full rounded-xl border shadow-xs transition-all duration-200 focus-within:ring-2 focus-within:ring-blue-500/30 focus-within:border-blue-500" style="background-color: var(--canvas-subtle); border-color: var(--border-default);">
                    <div class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none" style="color: var(--fg-muted);">
                        <svg width="18" height="18" viewBox="0 0 16 16" fill="currentColor">
                            <path d="M10.68 11.74a6 6 0 0 1-7.922-8.982 6 6 0 0 1 8.982 7.922l3.04 3.04a.749.749 0 0 1-.326 1.275.749.749 0 0 1-.734-.215ZM11.5 7a4.5 4.5 0 1 0-9 0 4.5 4.5 0 0 0 9 0Z"></path>
                        </svg>
                    </div>
                    <input type="text" id="searchInput" placeholder="Search certifications, providers, exam codes..." 
                           class="w-full pl-10 pr-12 sm:pr-28 py-3 sm:py-3.5 text-base sm:text-sm rounded-xl focus:outline-none transition font-medium"
                           style="background-color: transparent; color: var(--fg-default);">
                    <div class="absolute inset-y-0 right-0 pr-2.5 sm:pr-3 flex items-center gap-1.5 sm:gap-2">
                        <button id="clearSearchBtn" onclick="clearSearch()" class="hidden min-w-[36px] min-h-[36px] w-9 h-9 sm:w-8 sm:h-8 rounded-lg text-sm sm:text-xs hover:opacity-80 font-bold flex items-center justify-center active:scale-[0.98] transition cursor-pointer" style="background-color: var(--canvas-inset); color: var(--fg-muted); border: 1px solid var(--border-default);" title="Clear search" aria-label="Clear search">
                            <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                                <path d="M3.72 3.72a.75.75 0 0 1 1.06 0L8 6.94l3.22-3.22a.749.749 0 0 1 1.275.326.749.749 0 0 1-.215.734L9.06 8l3.22 3.22a.749.749 0 0 1-.326 1.275.749.749 0 0 1-.734-.215L8 9.06l-3.22 3.22a.751.751 0 0 1-1.042-.018.751.751 0 0 1-.018-1.042L6.94 8 3.72 4.78a.75.75 0 0 1 0-1.06Z"></path>
                            </svg>
                        </button>
                        <span id="searchMatchesBadge" class="hidden sm:inline-flex text-xs font-medium px-2 py-0.5 rounded border tabular-nums" style="background-color: var(--accent-subtle); border-color: var(--accent-fg); color: var(--accent-fg);"></span>
                        <kbd class="hidden md:inline-flex items-center text-xs font-mono px-2 py-0.5 rounded border pointer-events-none" style="background-color: var(--canvas-inset); border-color: var(--border-default); color: var(--fg-muted);" title="Press / to search">/</kbd>
                    </div>
                </div>
            </div>

            <!-- Category Filters and View Controls Toolbar -->
            <div class="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-2.5 sm:gap-3 mb-4 p-2 sm:p-2.5 rounded-xl border shadow-xs" style="background-color: var(--canvas-subtle); border-color: var(--border-default);">
                <!-- Category Pills (Horizontally Scrollable with Touch Physics) -->
                <div class="flex gap-1.5 overflow-x-auto touch-scroll scrollbar-none pb-1.5 lg:pb-0 px-0.5" id="filterPills">
                    <button onclick="filterCategory('All')" class="cat-pill min-h-[40px] px-3.5 py-2 rounded-lg text-xs font-semibold whitespace-nowrap transition active:scale-[0.98] flex items-center gap-1.5 flex-shrink-0 cursor-pointer" style="background-color: var(--accent-emphasis); color: #ffffff;" data-cat="All">
                        <span>All</span>
                        <span class="text-[10px] px-1.5 py-0.2 rounded-full tabular-nums font-medium bg-white/20">{len(offers)}</span>
                    </button>
                    <button onclick="filterCategory('Cloud')" class="cat-pill min-h-[40px] px-3.5 py-2 rounded-lg text-xs font-medium whitespace-nowrap border transition hover:opacity-80 active:scale-[0.98] flex items-center gap-1.5 flex-shrink-0 cursor-pointer" style="background-color: var(--canvas-default); border-color: var(--border-default); color: var(--fg-muted);" data-cat="Cloud">
                        <span>Cloud</span>
                        <span class="text-[10px] px-1.5 py-0.2 rounded-full tabular-nums font-medium" style="background-color: var(--canvas-inset);">{cloud_count}</span>
                    </button>
                    <button onclick="filterCategory('Security')" class="cat-pill min-h-[40px] px-3.5 py-2 rounded-lg text-xs font-medium whitespace-nowrap border transition hover:opacity-80 active:scale-[0.98] flex items-center gap-1.5 flex-shrink-0 cursor-pointer" style="background-color: var(--canvas-default); border-color: var(--border-default); color: var(--fg-muted);" data-cat="Security">
                        <span>Security</span>
                        <span class="text-[10px] px-1.5 py-0.2 rounded-full tabular-nums font-medium" style="background-color: var(--canvas-inset);">{sec_count}</span>
                    </button>
                    <button onclick="filterCategory('DevOps')" class="cat-pill min-h-[40px] px-3.5 py-2 rounded-lg text-xs font-medium whitespace-nowrap border transition hover:opacity-80 active:scale-[0.98] flex items-center gap-1.5 flex-shrink-0 cursor-pointer" style="background-color: var(--canvas-default); border-color: var(--border-default); color: var(--fg-muted);" data-cat="DevOps">
                        <span>DevOps</span>
                        <span class="text-[10px] px-1.5 py-0.2 rounded-full tabular-nums font-medium" style="background-color: var(--canvas-inset);">{devops_count}</span>
                    </button>
                    <button onclick="filterCategory('AI & Data')" class="cat-pill min-h-[40px] px-3.5 py-2 rounded-lg text-xs font-medium whitespace-nowrap border transition hover:opacity-80 active:scale-[0.98] flex items-center gap-1.5 flex-shrink-0 cursor-pointer" style="background-color: var(--canvas-default); border-color: var(--border-default); color: var(--fg-muted);" data-cat="AI & Data">
                        <span>AI & Data</span>
                        <span class="text-[10px] px-1.5 py-0.2 rounded-full tabular-nums font-medium" style="background-color: var(--canvas-inset);">{ai_count}</span>
                    </button>
                    <button onclick="filterCategory('Networking')" class="cat-pill min-h-[40px] px-3.5 py-2 rounded-lg text-xs font-medium whitespace-nowrap border transition hover:opacity-80 active:scale-[0.98] flex items-center gap-1.5 flex-shrink-0 cursor-pointer" style="background-color: var(--canvas-default); border-color: var(--border-default); color: var(--fg-muted);" data-cat="Networking">
                        <span>Networking</span>
                        <span class="text-[10px] px-1.5 py-0.2 rounded-full tabular-nums font-medium" style="background-color: var(--canvas-inset);">{net_count}</span>
                    </button>
                    <button onclick="filterCategory('History')" class="cat-pill min-h-[40px] px-3.5 py-2 rounded-lg text-xs font-medium whitespace-nowrap border transition hover:opacity-80 active:scale-[0.98] flex items-center gap-1.5 flex-shrink-0 cursor-pointer" style="background-color: var(--canvas-default); border-color: var(--border-default); color: var(--accent-fg);" data-cat="History">
                        <span>📜 Past History</span>
                        <span class="text-[10px] px-1.5 py-0.2 rounded-full tabular-nums font-medium" style="background-color: var(--canvas-inset);">{len(historical_offers)}</span>
                    </button>
                </div>

                <!-- Controls (Sort, Status, Layout, Export) -->
                <div class="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
                    <div class="grid grid-cols-2 sm:flex items-center gap-2">
                        <select id="sortSelect" onchange="renderCards()" class="w-full sm:w-auto min-h-[40px] text-xs py-2 px-2.5 rounded-lg border font-medium focus:outline-none" style="background-color: var(--canvas-default); border-color: var(--border-default); color: var(--fg-default);">
                            <option value="val-desc">Highest Value ($$$)</option>
                            <option value="val-asc">Lowest Value ($)</option>
                            <option value="name-asc">Provider (A to Z)</option>
                        </select>
                        <select id="statusFilter" onchange="onStatusFilterChange()" class="w-full sm:w-auto min-h-[40px] text-xs py-2 px-2.5 rounded-lg border font-medium focus:outline-none" style="background-color: var(--canvas-default); border-color: var(--border-default); color: var(--fg-default);">
                            <option value="active" selected>Active ({len(active_offers)})</option>
                            <option value="all">All Records ({len(offers)})</option>
                            <option value="history">Past History ({len(historical_offers)})</option>
                            <option value="closed">Concluded ({len(closed_offers)})</option>
                        </select>
                    </div>
                    <div class="flex items-center justify-between sm:justify-start gap-2">
                        <!-- Layout Switcher (Grid vs Table vs Timeline vs Matrix) -->
                        <div class="flex items-center rounded-lg border p-0.5 flex-1 sm:flex-initial justify-center" id="layoutControlGroup" style="background-color: var(--canvas-inset); border-color: var(--border-default);">
                            <button id="viewBtnGrid" onclick="setLayoutView('grid')" title="Bento Grid View (Press V to cycle)" class="flex-1 sm:flex-initial min-h-[38px] px-2.5 sm:px-3 py-1.5 rounded-md text-xs font-semibold flex items-center justify-center gap-1.5 transition active:scale-[0.98] cursor-pointer" style="background-color: var(--btn-default-bg); color: var(--fg-default);">
                                <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                                    <path d="M1 2.5A1.5 1.5 0 0 1 2.5 1h3A1.5 1.5 0 0 1 7 2.5v3A1.5 1.5 0 0 1 5.5 7h-3A1.5 1.5 0 0 1 1 5.5v-3Zm8 0A1.5 1.5 0 0 1 10.5 1h3A1.5 1.5 0 0 1 15 2.5v3A1.5 1.5 0 0 1 13.5 7h-3A1.5 1.5 0 0 1 9 5.5v-3Zm-8 8A1.5 1.5 0 0 1 2.5 9h3A1.5 1.5 0 0 1 7 10.5v3A1.5 1.5 0 0 1 5.5 15h-3A1.5 1.5 0 0 1 1 13.5v-3Zm8 0A1.5 1.5 0 0 1 10.5 9h3a1.5 1.5 0 0 1 1.5 1.5v3a1.5 1.5 0 0 1-1.5 1.5h-3A1.5 1.5 0 0 1 9 13.5v-3Z"></path>
                                </svg>
                                <span>Grid</span>
                            </button>
                            <button id="viewBtnList" onclick="setLayoutView('list')" title="Catalog Table View (Press V to cycle)" class="flex-1 sm:flex-initial min-h-[38px] px-2.5 sm:px-3 py-1.5 rounded-md text-xs font-medium flex items-center justify-center gap-1.5 transition active:scale-[0.98] cursor-pointer" style="color: var(--fg-muted);">
                                <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                                    <path d="M2 3.75C2 3.336 2.336 3 2.75 3h10.5a.75.75 0 0 1 0 1.5H2.75A.75.75 0 0 1 2 3.75Zm0 4.25c0-.414.336-.75.75-.75h10.5a.75.75 0 0 1 0 1.5H2.75A.75.75 0 0 1 2 8Zm0 4.25c0-.414.336-.75.75-.75h10.5a.75.75 0 0 1 0 1.5H2.75a.75.75 0 0 1-.75-.75Z"></path>
                                </svg>
                                <span>Table</span>
                            </button>
                            <button id="viewBtnTimeline" onclick="setLayoutView('timeline')" title="Recurrence & Expiry Timeline Roadmap (Press V to cycle)" class="flex-1 sm:flex-initial min-h-[38px] px-2.5 sm:px-3 py-1.5 rounded-md text-xs font-medium flex items-center justify-center gap-1.5 transition active:scale-[0.98] cursor-pointer" style="color: var(--fg-muted);">
                                <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                                    <path d="M8 0a8 8 0 1 1 0 16A8 8 0 0 1 8 0ZM1.5 8a6.5 6.5 0 1 0 13 0 6.5 6.5 0 0 0-13 0Zm7.25-3.25v3.69l2.28 2.28a.75.75 0 1 1-1.06 1.06l-2.5-2.5a.75.75 0 0 1-.22-.53V4.75a.75.75 0 0 1 1.5 0Z"></path>
                                </svg>
                                <span>Timeline</span>
                            </button>
                            <button id="viewBtnMatrix" onclick="setLayoutView('matrix')" title="Domain & Skill Matrix View (Press V to cycle)" class="flex-1 sm:flex-initial min-h-[38px] px-2.5 sm:px-3 py-1.5 rounded-md text-xs font-medium flex items-center justify-center gap-1.5 transition active:scale-[0.98] cursor-pointer" style="color: var(--fg-muted);">
                                <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                                    <path d="M1.5 1h13A1.5 1.5 0 0 1 16 2.5v11a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 0 13.5v-11A1.5 1.5 0 0 1 1.5 1Zm0 1.5a.5.5 0 0 0-.5.5v3h4.5V2.5H1.5Zm5.5 0v3h4.5V2.5H7Zm5.5 0v3H15V3a.5.5 0 0 0-.5-.5h-2Zm2 4.5h-3.5v3.5H15V7Zm-4.5 3.5V7H7v3.5h4.5ZM5.5 7H1v3.5h4.5V7Zm0 4.5H1v1.5a.5.5 0 0 0 .5.5H5.5v-2Zm1.5 2h4.5v-2H7v2Zm5.5 0h1.5a.5.5 0 0 0 .5-.5v-1.5h-2v2Z"></path>
                                </svg>
                                <span>Matrix</span>
                            </button>
                        </div>
                        <!-- Export JSON -->
                        <button onclick="exportFilteredJson()" class="min-h-[40px] h-10 px-3 rounded-lg border hover:opacity-80 active:scale-[0.98] transition flex items-center justify-center gap-1.5 text-xs font-semibold flex-shrink-0 cursor-pointer" style="background-color: var(--btn-default-bg); border-color: var(--border-default); color: var(--fg-default);" title="Export Filtered JSON" aria-label="Export JSON">
                            <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M2.75 14A1.75 1.75 0 0 1 1 12.25v-2.5a.75.75 0 0 1 1.5 0v2.5c0 .138.112.25.25.25h10.5a.25.25 0 0 0 .25-.25v-2.5a.75.75 0 0 1 1.5 0v2.5A1.75 1.75 0 0 1 13.25 14H2.75Z"></path><path d="M7.25 1.75v7.69L4.97 7.16a.75.75 0 0 0-1.06 1.06l3.5 3.5a.75.75 0 0 0 1.06 0l3.5-3.5a.75.75 0 1 0-1.06-1.06L8.75 9.44V1.75a.75.75 0 0 0-1.5 0Z"></path></svg>
                            <span>JSON</span>
                        </button>
                        <!-- Share Link -->
                        <button onclick="copyShareLink()" title="Copy Shareable Link" aria-label="Share link" class="min-h-[40px] h-10 px-3 rounded-lg border hover:opacity-80 active:scale-[0.98] transition flex items-center justify-center gap-1.5 text-xs font-semibold flex-shrink-0 cursor-pointer" style="background-color: var(--btn-default-bg); border-color: var(--border-default); color: var(--fg-default);">
                            <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                                <path d="M13.5 0a2.5 2.5 0 0 0-2.316 3.447L6.082 5.998a2.502 2.502 0 1 0 0 4.004l5.102 2.551a2.5 2.5 0 1 0 .898-1.796L6.98 8.206a2.518 2.518 0 0 0 0-.412l5.102-2.551A2.5 2.5 0 1 0 13.5 0Z"></path>
                            </svg>
                            <span>Share</span>
                        </button>
                    </div>
                </div>
            </div>

            <!-- Result Status Sub-bar -->
            <div class="flex flex-col xs:flex-row items-start xs:items-center justify-between text-xs mb-4 px-1 gap-1" style="color: var(--fg-muted);">
                <div id="resultsCount">Showing {len(active_offers)} of {len(offers)} vouchers</div>
                <div>Audited: <span class="tabular-nums font-medium">{last_updated}</span></div>
            </div>

            <!-- View Container 1: Bento Cards Grid -->
            <div id="cardsViewContainer">
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" id="offersGrid"></div>
            </div>

            <!-- View Container 2: Executive Catalog Table -->
            <div id="listViewContainer" class="hidden">
                <div class="rounded-xl border overflow-hidden shadow-xs" style="background-color: var(--canvas-subtle); border-color: var(--border-default);">
                    <div class="hidden sm:grid grid-cols-12 gap-3 px-4 py-3 border-b text-xs font-semibold uppercase tracking-wider" style="background-color: var(--canvas-inset); border-color: var(--border-default); color: var(--fg-muted);">
                        <div class="col-span-3">Provider</div>
                        <div class="col-span-5">Certification & Program</div>
                        <div class="col-span-2 text-center">Value</div>
                        <div class="col-span-2 text-right">Action</div>
                    </div>
                    <div id="offersTableBody" class="divide-y" style="border-color: var(--border-muted);"></div>
                </div>
            </div>

            <!-- View Container 3: Recurrence & Expiry Timeline Roadmap -->
            <div id="timelineViewContainer" class="hidden">
                <div id="offersTimeline" class="space-y-6"></div>
            </div>

            <!-- View Container 4: Domain & Skill Matrix -->
            <div id="matrixViewContainer" class="hidden">
                <div id="offersMatrix" class="space-y-6"></div>
            </div>
        </div>

        <!-- SECTION 2: INDUSTRY TECH RADAR & ENGINEERING FEED -->
        <div id="newsSection" class="hidden">
            <!-- News Hero Bento Grid (Asymmetrical Executive Standard) -->
            <div class="grid grid-cols-1 lg:grid-cols-12 gap-3.5 sm:gap-4 mb-5 sm:mb-8">
                <!-- Anchor Bento: Verified Dispatches (Col-Span 6 on LG) -->
                <div class="lg:col-span-6 p-4 sm:p-6 rounded-2xl border primer-card relative overflow-hidden flex flex-col justify-between">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center gap-2">
                            <span class="w-2 h-2 rounded-full animate-pulse" style="background-color: var(--success-fg);"></span>
                            <span class="text-xs font-semibold" style="color: var(--fg-muted);">Live Intelligence Feed</span>
                        </div>
                        <span class="p-1.5 sm:p-2 rounded-lg flex-shrink-0" style="background-color: var(--success-subtle); color: var(--success-fg); border: 1px solid var(--success-fg);">
                            <svg width="18" height="18" viewBox="0 0 16 16" fill="currentColor">
                                <path d="M13.78 4.22a.75.75 0 0 1 0 1.06l-7.25 7.25a.75.75 0 0 1-1.06 0L2.22 9.28a.751.751 0 0 1 .018-1.042.751.751 0 0 1 1.042-.018L6 10.94l6.72-6.72a.75.75 0 0 1 1.06 0Z"></path>
                            </svg>
                        </span>
                    </div>
                    <div class="mt-3 sm:mt-4">
                        <div class="text-2xl sm:text-4xl font-extrabold tracking-tight tabular-nums" style="color: var(--success-fg);">
                            {len(news_items)} Briefings <span class="text-xs sm:text-base font-normal font-sans" style="color: var(--fg-muted);">Live Dispatches</span>
                        </div>
                        <p class="text-xs sm:text-sm mt-1.5 sm:mt-2 leading-relaxed text-pretty max-w-[65ch]" style="color: var(--fg-muted);">
                            Silicon architecture breakthroughs, small language models, distributed systems RFCs, and SEC revenue filings.
                        </p>
                    </div>
                </div>

                <!-- News Bento 2: Enterprise Scope (Col-Span 3 on LG) -->
                <div class="lg:col-span-3 p-4 sm:p-6 rounded-2xl border primer-card flex flex-col justify-between">
                    <div class="flex items-center justify-between">
                        <span class="text-xs font-semibold" style="color: var(--fg-muted);">Ecosystem Scope</span>
                        <span class="p-1.5 sm:p-2 rounded-lg flex-shrink-0" style="background-color: var(--accent-subtle); color: var(--accent-fg); border: 1px solid var(--accent-fg);">
                            <svg width="18" height="18" viewBox="0 0 16 16" fill="currentColor">
                                <path d="M1.75 1.5a.25.25 0 0 0-.25.25v8.5c0 .138.112.25.25.25h12.5a.25.25 0 0 0 .25-.25v-8.5a.25.25 0 0 0-.25-.25H1.75ZM0 1.75C0 .784.784 0 1.75 0h12.5C15.216 0 16 .784 16 1.75v8.5A1.75 1.75 0 0 1 14.25 12H9.06l.72 2.25H11.5a.75.75 0 0 1 0 1.5h-7a.75.75 0 0 1 0-1.5h1.72l.72-2.25H1.75A1.75 1.75 0 0 1 0 10.25V1.75Z"></path>
                            </svg>
                        </span>
                    </div>
                    <div class="mt-3 sm:mt-4">
                        <div class="text-xl sm:text-3xl font-extrabold tracking-tight tabular-nums" style="color: var(--fg-default);">
                            9 Giants <span class="text-xs sm:text-sm font-normal font-sans" style="color: var(--fg-muted);">Tracked</span>
                        </div>
                        <p class="text-xs mt-1.5 sm:mt-2 leading-relaxed text-pretty" style="color: var(--fg-muted);">
                            AWS, Azure, Google Cloud, Oracle Cloud, Cisco, GitHub, CNCF, Databricks, Snowflake.
                        </p>
                    </div>
                </div>

                <!-- News Bento 3: Anti-Clickbait Guardian (Col-Span 3 on LG) -->
                <div class="lg:col-span-3 p-4 sm:p-6 rounded-2xl border primer-card flex flex-col justify-between">
                    <div class="flex items-center justify-between">
                        <span class="text-xs font-semibold" style="color: var(--fg-muted);">Integrity Standard</span>
                        <span class="p-1.5 sm:p-2 rounded-lg flex-shrink-0" style="background-color: var(--attention-subtle); color: var(--attention-fg); border: 1px solid var(--attention-fg);">
                            <svg width="18" height="18" viewBox="0 0 16 16" fill="currentColor">
                                <path d="M7.462.166a.75.75 0 0 1 .538 0l6.25 2.5a.75.75 0 0 1 .478.704c0 4.195-2.067 8.046-5.83 10.428a.75.75 0 0 1-.806 0C4.317 11.416 2.25 7.565 2.25 3.37a.75.75 0 0 1 .478-.704l6.25-2.5Zm.538 1.558L2.75 3.82c.117 3.518 1.83 6.758 4.996 8.847 3.165-2.089 4.88-5.329 4.996-8.847L8 1.724Z"></path>
                            </svg>
                        </span>
                    </div>
                    <div class="mt-3 sm:mt-4">
                        <div class="text-xl sm:text-3xl font-extrabold tracking-tight tabular-nums" style="color: var(--attention-fg);">
                            0% Clickbait <span class="text-xs sm:text-sm font-normal font-sans" style="color: var(--fg-muted);">Verified</span>
                        </div>
                        <p class="text-xs mt-1.5 sm:mt-2 leading-relaxed text-pretty" style="color: var(--fg-muted);">
                            Strict primary enterprise domain whitelist. Rumor blogs and content mills strictly barred.
                        </p>
                    </div>
                </div>
            </div>

            <!-- News Command-Bar Search (UX Enhanced & Mobile Optimized) -->
            <div class="mb-4">
                <div class="relative w-full rounded-xl border shadow-xs transition-all duration-200 focus-within:ring-2 focus-within:ring-blue-500/30 focus-within:border-blue-500" style="background-color: var(--canvas-subtle); border-color: var(--border-default);">
                    <div class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none" style="color: var(--fg-muted);">
                        <svg width="18" height="18" viewBox="0 0 16 16" fill="currentColor">
                            <path d="M10.68 11.74a6 6 0 0 1-7.922-8.982 6 6 0 0 1 8.982 7.922l3.04 3.04a.749.749 0 0 1-.326 1.275.749.749 0 0 1-.734-.215ZM11.5 7a4.5 4.5 0 1 0-9 0 4.5 4.5 0 0 0 9 0Z"></path>
                        </svg>
                    </div>
                    <input type="text" id="newsSearchInput" placeholder="Filter radar by keyword, company, topic, or domain..." 
                           class="w-full pl-10 pr-12 sm:pr-28 py-3 sm:py-3.5 text-base sm:text-sm rounded-xl focus:outline-none transition font-medium"
                           style="background-color: transparent; color: var(--fg-default);">
                    <div class="absolute inset-y-0 right-0 pr-2.5 sm:pr-3 flex items-center gap-1.5 sm:gap-2">
                        <button id="clearNewsSearchBtn" onclick="clearNewsSearch()" class="hidden min-w-[36px] min-h-[36px] w-9 h-9 sm:w-8 sm:h-8 rounded-lg text-sm sm:text-xs hover:opacity-80 font-bold flex items-center justify-center active:scale-[0.98] transition cursor-pointer" style="background-color: var(--canvas-inset); color: var(--fg-muted); border: 1px solid var(--border-default);" title="Clear search" aria-label="Clear search">
                            <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                                <path d="M3.72 3.72a.75.75 0 0 1 1.06 0L8 6.94l3.22-3.22a.749.749 0 0 1 1.275.326.749.749 0 0 1-.215.734L9.06 8l3.22 3.22a.749.749 0 0 1-.326 1.275.749.749 0 0 1-.734-.215L8 9.06l-3.22 3.22a.751.751 0 0 1-1.042-.018.751.751 0 0 1-.018-1.042L6.94 8 3.72 4.78a.75.75 0 0 1 0-1.06Z"></path>
                            </svg>
                        </button>
                        <span id="newsSearchMatchesBadge" class="hidden sm:inline-flex text-xs font-medium px-2 py-0.5 rounded border tabular-nums" style="background-color: var(--accent-subtle); border-color: var(--accent-fg); color: var(--accent-fg);"></span>
                    </div>
                </div>
            </div>

            <!-- News Filter Toolbar -->
            <div class="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-2.5 sm:gap-3 mb-4 p-2 sm:p-2.5 rounded-xl border shadow-xs" style="background-color: var(--canvas-subtle); border-color: var(--border-default);">
                <!-- News Category Pills (Horizontally Scrollable) -->
                <div class="flex gap-1.5 overflow-x-auto touch-scroll scrollbar-none pb-1.5 lg:pb-0 px-0.5" id="newsCategoryPills">
                    <button onclick="filterNewsCategory('All')" class="news-cat-pill min-h-[40px] px-3.5 py-2 rounded-lg text-xs font-semibold whitespace-nowrap transition active:scale-[0.98] flex items-center gap-1.5 flex-shrink-0 cursor-pointer" style="background-color: var(--accent-emphasis); color: #ffffff;" data-cat="All">
                        <span>All Topics</span>
                        <span class="text-[10px] px-1.5 py-0.2 rounded-full tabular-nums font-medium bg-white/20">{len(news_items)}</span>
                    </button>
                    <button onclick="filterNewsCategory('Infrastructure & Silicon')" class="news-cat-pill min-h-[40px] px-3.5 py-2 rounded-lg text-xs font-medium whitespace-nowrap border transition hover:opacity-80 active:scale-[0.98] flex items-center gap-1.5 flex-shrink-0 cursor-pointer" style="background-color: var(--canvas-default); border-color: var(--border-default); color: var(--fg-muted);" data-cat="Infrastructure & Silicon">
                        <span>Silicon & Hardware</span>
                    </button>
                    <button onclick="filterNewsCategory('Research & AI')" class="news-cat-pill min-h-[40px] px-3.5 py-2 rounded-lg text-xs font-medium whitespace-nowrap border transition hover:opacity-80 active:scale-[0.98] flex items-center gap-1.5 flex-shrink-0 cursor-pointer" style="background-color: var(--canvas-default); border-color: var(--border-default); color: var(--fg-muted);" data-cat="Research & AI">
                        <span>Research & AI</span>
                    </button>
                    <button onclick="filterNewsCategory('Tech Development')" class="news-cat-pill min-h-[40px] px-3.5 py-2 rounded-lg text-xs font-medium whitespace-nowrap border transition hover:opacity-80 active:scale-[0.98] flex items-center gap-1.5 flex-shrink-0 cursor-pointer" style="background-color: var(--canvas-default); border-color: var(--border-default); color: var(--fg-muted);" data-cat="Tech Development">
                        <span>Tech & Tooling</span>
                    </button>
                    <button onclick="filterNewsCategory('Enterprise & Financials')" class="news-cat-pill min-h-[40px] px-3.5 py-2 rounded-lg text-xs font-medium whitespace-nowrap border transition hover:opacity-80 active:scale-[0.98] flex items-center gap-1.5 flex-shrink-0 cursor-pointer" style="background-color: var(--canvas-default); border-color: var(--border-default); color: var(--fg-muted);" data-cat="Enterprise & Financials">
                        <span>Financials & Cloud</span>
                    </button>
                </div>

                <!-- News Company & Sort Select -->
                <div class="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
                    <div class="grid grid-cols-2 sm:flex items-center gap-2">
                        <select id="newsCompanySelect" onchange="renderNews()" class="w-full sm:w-auto min-h-[40px] text-xs py-2 px-2.5 rounded-lg border font-medium focus:outline-none" style="background-color: var(--canvas-default); border-color: var(--border-default); color: var(--fg-default);">
                            <option value="All">All Companies</option>
                            <option value="Amazon Web Services">AWS</option>
                            <option value="Microsoft Azure">Microsoft Azure</option>
                            <option value="Google Cloud">Google Cloud</option>
                            <option value="Oracle Cloud">Oracle Cloud</option>
                            <option value="GitHub">GitHub</option>
                            <option value="Cisco">Cisco</option>
                            <option value="Databricks">Databricks</option>
                            <option value="Snowflake">Snowflake</option>
                            <option value="Linux Foundation / CNCF">Linux / CNCF</option>
                        </select>
                        <select id="newsSortSelect" onchange="renderNews()" class="w-full sm:w-auto min-h-[40px] text-xs py-2 px-2.5 rounded-lg border font-medium focus:outline-none" style="background-color: var(--canvas-default); border-color: var(--border-default); color: var(--fg-default);">
                            <option value="date-desc">Newest First</option>
                            <option value="date-asc">Oldest First</option>
                            <option value="company-asc">Company (A to Z)</option>
                        </select>
                    </div>
                    <button onclick="exportFilteredNewsJson()" class="min-h-[40px] h-10 px-3.5 rounded-lg border text-xs font-semibold hover:opacity-80 active:scale-[0.98] transition flex items-center justify-center gap-1.5 flex-shrink-0 cursor-pointer" style="background-color: var(--btn-default-bg); border-color: var(--border-default); color: var(--fg-default);" title="Export Filtered News JSON" aria-label="Export News JSON">
                        <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M2.75 14A1.75 1.75 0 0 1 1 12.25v-2.5a.75.75 0 0 1 1.5 0v2.5c0 .138.112.25.25.25h10.5a.25.25 0 0 0 .25-.25v-2.5a.75.75 0 0 1 1.5 0v2.5A1.75 1.75 0 0 1 13.25 14H2.75Z"></path><path d="M7.25 1.75v7.69L4.97 7.16a.75.75 0 0 0-1.06 1.06l3.5 3.5a.75.75 0 0 0 1.06 0l3.5-3.5a.75.75 0 1 0-1.06-1.06L8.75 9.44V1.75a.75.75 0 0 0-1.5 0Z"></path></svg>
                        <span>JSON</span>
                    </button>
                </div>
            </div>

            <!-- News Results Status Bar -->
            <div class="flex flex-col xs:flex-row items-start xs:items-center justify-between text-xs mb-4 px-1 gap-1" style="color: var(--fg-muted);">
                <div id="newsResultsCount">Showing {len(news_items)} of {len(news_items)} verified dispatches</div>
                <div>Primary Domain Whitelist: <span class="font-medium text-xs" style="color: var(--success-fg);">Strict Verification Enforced</span></div>
            </div>

            <!-- News Cards Grid -->
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5 sm:gap-4" id="newsGrid"></div>
        </div>

    </main>

    <!-- Footer -->
    <footer class="border-t py-6 sm:py-8 mt-10 sm:mt-12 text-center text-xs" style="background-color: var(--canvas-subtle); border-color: var(--border-default); color: var(--fg-muted); padding-bottom: max(1.5rem, calc(env(safe-area-inset-bottom, 0px) + 1.25rem));">
        <div class="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-3 sm:gap-4">
            <div class="text-balance">CertPulse — Open-Source Certification Directory & Verified Tech Radar</div>
            <div class="flex items-center gap-4 flex-wrap justify-center">
                <a href="https://github.com/Athish2002/free-certification-tracker" target="_blank" class="hover:underline py-1" style="color: var(--accent-fg);">GitHub Repo</a>
                <a href="https://github.com/Athish2002/free-certification-tracker/issues/new/choose" target="_blank" class="hover:underline py-1" style="color: var(--accent-fg);">Submit Voucher</a>
                <a href="https://primer.style" target="_blank" class="hover:underline py-1" style="color: var(--fg-muted);">GitHub Primer</a>
            </div>
        </div>
    </footer>

    <!-- Toast Notification for Micro-Interactions -->
    <div id="toastNotification" class="fixed bottom-4 sm:bottom-5 left-4 right-4 sm:left-auto sm:right-5 z-50 transform translate-y-20 opacity-0 transition-all duration-300 pointer-events-none p-3.5 rounded-xl border shadow-xl flex items-center justify-between sm:justify-start gap-2.5 text-xs font-semibold max-w-sm sm:max-w-none ml-auto" style="background-color: var(--canvas-subtle); border-color: var(--border-default); color: var(--fg-default); margin-bottom: env(safe-area-inset-bottom, 0px);">
        <div class="flex items-center gap-2 min-w-0">
            <svg class="w-4 h-4 text-emerald-400 flex-shrink-0" viewBox="0 0 16 16" fill="currentColor">
                <path d="M13.78 4.22a.75.75 0 0 1 0 1.06l-7.25 7.25a.75.75 0 0 1-1.06 0L2.22 9.28a.751.751 0 0 1 .018-1.042.751.751 0 0 1 1.042-.018L6 10.94l6.72-6.72a.75.75 0 0 1 1.06 0Z"></path>
            </svg>
            <span id="toastMessage" class="truncate">Action completed</span>
        </div>
    </div>

    <!-- Application Script -->
    <script>
        const offersData = {offers_json_str};
        const newsData = {news_json_str};

        let currentMainTab = 'vouchers';
        let currentCategory = 'All';
        let currentSearch = '';
        let currentLayout = 'grid';

        let currentNewsCategory = 'All';
        let currentNewsSearch = '';

        // Authentic Brand Logos (SVG Vector Library)
        function getPlatformIconSvg(platform) {{
            if (platform.includes('AWS') || platform.includes('Amazon')) {{
                return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16" fill="#ff9900"><path d="M8.2 1.8a4.8 4.8 0 0 0-4.3 2.7 3.6 3.6 0 0 0-2.3 3.4 3.6 3.6 0 0 0 3.6 3.6h7a3.4 3.4 0 0 0 3.4-3.4 3.4 3.4 0 0 0-2.8-3.3 4.8 4.8 0 0 0-4.6-3z"/><path d="M3 13.5c3.5 1.7 7 1.7 10 0" stroke="#ff9900" stroke-width="1.5" stroke-linecap="round"/></svg>`;
            }}
            if (platform.includes('Azure') || platform.includes('Microsoft')) {{
                return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16"><rect x="1" y="1" width="6.5" height="6.5" fill="#f25022"/><rect x="8.5" y="1" width="6.5" height="6.5" fill="#7fba00"/><rect x="1" y="8.5" width="6.5" height="6.5" fill="#00a4ef"/><rect x="8.5" y="8.5" width="6.5" height="6.5" fill="#ffb900"/></svg>`;
            }}
            if (platform.includes('Google')) {{
                return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16"><path d="M10.2 4.4A3.8 3.8 0 0 0 4 6.2a3 3 0 0 0-2 2.8 3 3 0 0 0 3 3h7.5a3 3 0 0 0 3-3 3 3 0 0 0-2.5-3 3.8 3.8 0 0 0-2.8-1.6z" fill="#4285f4"/><path d="M10.2 4.4a3.8 3.8 0 0 0-3.5 2.4l1.8 1.8a2 2 0 0 1 1.7-1.2 2 2 0 0 1 2 2l1.3-.3a3 3 0 0 0-3.3-4.7z" fill="#ea4335"/><path d="M13 9a3 3 0 0 1-3 3H5a3 3 0 0 1-1.8-.6l1.2-1.2a2 2 0 0 0 .6.3h5a2 2 0 0 0 2-2z" fill="#34a853"/><path d="M2 9a3 3 0 0 1 3-3l1 1a2 2 0 0 0-2 2z" fill="#fbbc05"/></svg>`;
            }}
            if (platform.includes('Oracle')) {{
                return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16"><rect x="1" y="3.5" width="14" height="9" rx="4.5" fill="#f80000"/><rect x="3.5" y="5.5" width="9" height="5" rx="2.5" fill="var(--canvas-subtle)"/></svg>`;
            }}
            if (platform.includes('Cisco')) {{
                return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16" fill="#1ba0d7"><rect x="1" y="7" width="1.5" height="6" rx="0.75"/><rect x="3.5" y="4" width="1.5" height="9" rx="0.75"/><rect x="6" y="8" width="1.5" height="5" rx="0.75"/><rect x="8.5" y="8" width="1.5" height="5" rx="0.75"/><rect x="11" y="4" width="1.5" height="9" rx="0.75"/><rect x="13.5" y="7" width="1.5" height="6" rx="0.75"/></svg>`;
            }}
            if (platform.includes('GitHub')) {{
                return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16" fill="currentColor"><path d="M8 0c4.42 0 8 3.58 8 8a8.013 8.013 0 0 1-5.45 7.59c-.4.08-.55-.17-.55-.38 0-.27.01-1.13.01-2.2 0-.75-.25-1.23-.54-1.48 1.78-.2 3.65-.88 3.65-3.95 0-.88-.31-1.59-.82-2.15.08-.2.36-1.02-.08-2.12 0 0-.67-.22-2.2.82-.64-.18-1.32-.27-2-.27-.68 0-1.36.09-2 .27-1.53-1.03-2.2-.82-2.2-.82-.44 1.1-.16 1.92-.08 2.12-.51.56-.82 1.28-.82 2.15 0 3.06 1.86 3.75 3.64 3.95-.23.2-.44.55-.51 1.07-.46.21-1.61.55-2.33-.66-.15-.24-.6-.83-1.23-.82-.67.01-.27.38.01.53.34.19.73.9.82 1.13.16.45.68 1.31 2.69.94 0 .67.01 1.3.01 1.49 0 .21-.15.45-.55.38A7.995 7.995 0 0 1 0 8c0-4.42 3.58-8 8-8Z"/></svg>`;
            }}
            if (platform.includes('Linux') || platform.includes('CNCF')) {{
                return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16"><path d="M8 1l5.5 3.2v6.4L8 13.8l-5.5-3.2V4.2L8 1z" stroke="#58a6ff" stroke-width="1.2" fill="none"/><circle cx="8" cy="7.5" r="2.5" fill="#58a6ff"/></svg>`;
            }}
            if (platform.includes('Databricks')) {{
                return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16" fill="#ff3621"><path d="M8 1L2 4.5l6 3.5 6-3.5L8 1zm0 5L2 9.5l6 3.5 6-3.5L8 6zm0 5l-6 3.5 6 3.5 6-3.5L8 11z"/></svg>`;
            }}
            if (platform.includes('Snowflake')) {{
                return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16"><path d="M8 1v14M1 8h14M3 3l10 10M3 13L13 3M6 2l2 2 2-2M6 14l2-2 2 2M2 6l2 2-2 2M14 6l-2 2 2 2" stroke="#29b5e8" stroke-width="1.5" stroke-linecap="round"/></svg>`;
            }}
            if (platform.includes('MongoDB')) {{
                return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16" fill="#00ed64"><path d="M8 1c.5 1.5 4 4.5 4 8a4 4 0 0 1-8 0c0-3.5 3.5-6.5 4-8z"/><path d="M8 3v10" stroke="#001e2b" stroke-width="0.8"/></svg>`;
            }}
            if (platform.includes('Salesforce')) {{
                return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16" fill="#00a1e0"><path d="M6 4a3.5 3.5 0 0 1 3.4 2.7 3 3 0 0 1 3.6 3 2.5 2.5 0 0 1-2.5 2.3H5a3 3 0 0 1-.9-5.8A3.5 3.5 0 0 1 6 4z"/></svg>`;
            }}
            if (platform.includes('Postman')) {{
                return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16" fill="#ff6c37"><circle cx="8" cy="8" r="6.5"/><path d="M5 8l2.5 2.5L11 5" stroke="#ffffff" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
            }}
            if (platform.includes('Juniper')) {{
                return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16"><rect x="2" y="2" width="12" height="12" rx="3" fill="#00739c"/><path d="M6 6h4v4H6z" fill="#ffffff"/></svg>`;
            }}
            if (platform.includes('Fortinet')) {{
                return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16" fill="#ee3124"><rect x="2" y="3" width="5.5" height="4.5" rx="1"/><rect x="8.5" y="3" width="5.5" height="4.5" rx="1"/><rect x="2" y="8.5" width="5.5" height="4.5" rx="1"/><rect x="8.5" y="8.5" width="5.5" height="4.5" rx="1"/></svg>`;
            }}
            if (platform.includes('ISC2')) {{
                return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16" fill="#008752"><path d="M8 1L2.5 3v5c0 3.5 2.5 6 5.5 7 3-1 5.5-3.5 5.5-7V3L8 1zm0 3a2.5 2.5 0 0 1 2.5 2.5c0 1.2-.8 2.2-2 2.4v2.1h-1V8.9a2.5 2.5 0 0 1-2-2.4A2.5 2.5 0 0 1 8 4z"/></svg>`;
            }}
            if (platform.includes('Qualys')) {{
                return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16"><circle cx="8" cy="8" r="6" stroke="#ed1c24" stroke-width="1.5" fill="none"/><path d="M9 10l2.5 2.5" stroke="#ed1c24" stroke-width="2" stroke-linecap="round"/></svg>`;
            }}
            if (platform.includes('Red Hat')) {{
                return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16"><path d="M14.5 10.5c-.8 0-1.8-.3-2.6-.7-.6 1.4-2 2.2-3.9 2.2-2.3 0-4-1.2-4-2.8 0-.4.1-.7.3-1C2.9 8.2 2 7.7 2 7.2c0-.5.8-1 2.3-1.3C5 4.5 6.4 3 8 3c2.2 0 3.7 1.6 4.1 3.8 1.4.3 2.4 1 2.4 1.8 0 .5-.7 1-2 1.3.4.2.8.4 1.2.6.5-.2.8-.2.8 0 0 .5-1.1.8-2 .8z" fill="#ee0000"/></svg>`;
            }}
            if (platform.includes('HashiCorp')) {{
                return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16" fill="#027bfd"><path d="M2.5 2h3v12h-3zm8 0h3v12h-3zm-5.5 4.5h5v3h-5z"/></svg>`;
            }}
            if (platform.includes('Palo Alto')) {{
                return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16" fill="#fa582d"><path d="M8 1L2 4v5c0 3.5 2.5 5.5 6 6 3.5-.5 6-2.5 6-6V4L8 1zm0 2.2l4 2v3.8c0 2.4-1.6 3.9-4 4.3-2.4-.4-4-1.9-4-4.3V5.2l4-2z"/></svg>`;
            }}
            if (platform.includes('GitLab')) {{
                return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16" fill="#fc6d26"><path d="M8 14.5L1.5 5.8l2.2-6.5L8 4.2l4.3-4.9 2.2 6.5L8 14.5z"/></svg>`;
            }}
            if (platform.includes('Splunk')) {{
                return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16" fill="#f15b24"><path d="M3 2.5l5.5 5.5L3 13.5h3l5.5-5.5L6 2.5H3zm7 11h3v-2h-3v2z"/></svg>`;
            }}
            if (platform.includes('IBM')) {{
                return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16" fill="#0f62fe"><rect x="1" y="2" width="14" height="1"/><rect x="1" y="4" width="14" height="1"/><rect x="1" y="6" width="14" height="1"/><rect x="1" y="8" width="14" height="1"/><rect x="1" y="10" width="14" height="1"/><rect x="1" y="12" width="14" height="1"/></svg>`;
            }}
            return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16" fill="var(--accent-fg)"><circle cx="8" cy="8" r="6"/></svg>`;
        }}

        // Tab Switching Engine (Vouchers vs Tech Radar)
        function switchMainTab(tab, updateUrl = true) {{
            currentMainTab = tab;
            const vouchersSec = document.getElementById('vouchersSection');
            const newsSec = document.getElementById('newsSection');
            const tabVouchers = document.getElementById('tabBtnVouchers');
            const tabNews = document.getElementById('tabBtnNews');
            const badgeVouchers = document.getElementById('tabBadgeVouchers');
            const badgeNews = document.getElementById('tabBadgeNews');
            const layoutGroup = document.getElementById('layoutControlGroup');

            if (tab === 'news') {{
                vouchersSec.classList.add('hidden');
                newsSec.classList.remove('hidden');
                if (layoutGroup) layoutGroup.classList.add('hidden');

                tabNews.style.borderColor = 'var(--accent-fg)';
                tabNews.style.color = 'var(--fg-default)';
                tabNews.classList.add('font-semibold');
                tabNews.classList.remove('font-medium');

                tabVouchers.style.borderColor = 'transparent';
                tabVouchers.style.color = 'var(--fg-muted)';
                tabVouchers.classList.remove('font-semibold');
                tabVouchers.classList.add('font-medium');

                if (badgeNews) {{
                    badgeNews.style.backgroundColor = 'var(--accent-subtle)';
                    badgeNews.style.borderColor = 'var(--accent-fg)';
                    badgeNews.style.color = 'var(--accent-fg)';
                }}
                if (badgeVouchers) {{
                    badgeVouchers.style.backgroundColor = 'var(--canvas-inset)';
                    badgeVouchers.style.borderColor = 'var(--border-default)';
                    badgeVouchers.style.color = 'var(--fg-muted)';
                }}

                renderNews();
            }} else {{
                newsSec.classList.add('hidden');
                vouchersSec.classList.remove('hidden');
                if (layoutGroup) layoutGroup.classList.remove('hidden');

                tabVouchers.style.borderColor = 'var(--accent-fg)';
                tabVouchers.style.color = 'var(--fg-default)';
                tabVouchers.classList.add('font-semibold');
                tabVouchers.classList.remove('font-medium');

                tabNews.style.borderColor = 'transparent';
                tabNews.style.color = 'var(--fg-muted)';
                tabNews.classList.remove('font-semibold');
                tabNews.classList.add('font-medium');

                if (badgeVouchers) {{
                    badgeVouchers.style.backgroundColor = 'var(--accent-subtle)';
                    badgeVouchers.style.borderColor = 'var(--accent-fg)';
                    badgeVouchers.style.color = 'var(--accent-fg)';
                }}
                if (badgeNews) {{
                    badgeNews.style.backgroundColor = 'var(--canvas-inset)';
                    badgeNews.style.borderColor = 'var(--border-default)';
                    badgeNews.style.color = 'var(--fg-muted)';
                }}

                renderCards();
            }}

            if (updateUrl) syncUrlParams();
        }}

        // Dual Theme Controller: Dark vs Light Contrast
        function initTheme() {{
            const urlParams = new URLSearchParams(window.location.search);
            const savedTheme = urlParams.get('theme') || localStorage.getItem('certpulse_theme') || 'dark';
            applyTheme(savedTheme === 'light' ? 'light' : 'dark', false);
            
            const savedLayout = urlParams.get('view') || localStorage.getItem('certpulse_layout') || 'grid';
            setLayoutView(savedLayout, false);

            const initialQuery = urlParams.get('q');
            if (initialQuery) {{
                document.getElementById('searchInput').value = initialQuery;
                currentSearch = initialQuery;
                document.getElementById('clearSearchBtn').classList.remove('hidden');
            }}
            const initialCat = urlParams.get('cat');
            if (initialCat) {{
                currentCategory = initialCat;
                updateCatPills();
            }}

            const savedTab = urlParams.get('tab');
            if (savedTab === 'news') {{
                switchMainTab('news', false);
            }} else {{
                switchMainTab('vouchers', false);
            }}
        }}

        function toggleTheme() {{
            const current = document.documentElement.getAttribute('data-theme') || 'dark';
            const target = current === 'dark' ? 'light' : 'dark';
            applyTheme(target, true);
            showToast(target === 'light' ? 'Switched to Light Contrast mode' : 'Switched to Dark mode');
        }}

        function applyTheme(target, updateUrl = true) {{
            document.documentElement.setAttribute('data-theme', target);
            document.documentElement.setAttribute('data-color-mode', target);
            localStorage.setItem('certpulse_theme', target);

            const metaTheme = document.getElementById('themeColorMeta');
            if (metaTheme) {{
                metaTheme.setAttribute('content', target === 'dark' ? '#0d1117' : '#ffffff');
            }}

            const sun = document.getElementById('themeIconSun');
            const moon = document.getElementById('themeIconMoon');
            if (target === 'dark') {{
                sun.classList.remove('hidden');
                moon.classList.add('hidden');
            }} else {{
                sun.classList.add('hidden');
                moon.classList.remove('hidden');
            }}

            if (updateUrl) syncUrlParams();
            if (currentMainTab === 'news') renderNews();
            else renderCards();
        }}

        function setLayoutView(view, updateUrl = true) {{
            const validViews = ['grid', 'list', 'timeline', 'matrix'];
            if (!validViews.includes(view)) view = 'grid';
            currentLayout = view;

            const containers = {{
                grid: document.getElementById('cardsViewContainer'),
                list: document.getElementById('listViewContainer'),
                timeline: document.getElementById('timelineViewContainer'),
                matrix: document.getElementById('matrixViewContainer')
            }};

            const buttons = {{
                grid: document.getElementById('viewBtnGrid'),
                list: document.getElementById('viewBtnList'),
                timeline: document.getElementById('viewBtnTimeline'),
                matrix: document.getElementById('viewBtnMatrix')
            }};

            validViews.forEach(v => {{
                if (containers[v]) {{
                    if (v === view) containers[v].classList.remove('hidden');
                    else containers[v].classList.add('hidden');
                }}
                if (buttons[v]) {{
                    if (v === view) {{
                        buttons[v].style.backgroundColor = 'var(--btn-default-bg)';
                        buttons[v].style.color = 'var(--fg-default)';
                        buttons[v].classList.add('font-semibold');
                        buttons[v].classList.remove('font-medium');
                    }} else {{
                        buttons[v].style.backgroundColor = 'transparent';
                        buttons[v].style.color = 'var(--fg-muted)';
                        buttons[v].classList.remove('font-semibold');
                        buttons[v].classList.add('font-medium');
                    }}
                }}
            }});

            localStorage.setItem('certpulse_layout', view);
            if (updateUrl) syncUrlParams();
            renderCards();
        }}

        function syncUrlParams() {{
            const params = new URLSearchParams();
            const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
            if (currentTheme === 'light') params.set('theme', 'light');
            if (currentMainTab !== 'vouchers') params.set('tab', currentMainTab);
            if (currentLayout !== 'grid') params.set('view', currentLayout);
            if (currentCategory !== 'All') params.set('cat', currentCategory);
            if (currentSearch.trim() !== '') params.set('q', currentSearch.trim());

            const newUrl = window.location.pathname + (params.toString() ? '?' + params.toString() : '');
            window.history.replaceState({{}}, '', newUrl);
        }}

        let toastTimeout = null;
        function showToast(msg) {{
            const toast = document.getElementById('toastNotification');
            document.getElementById('toastMessage').textContent = msg;
            if (toastTimeout) clearTimeout(toastTimeout);
            toast.classList.remove('translate-y-20', 'opacity-0');
            toast.classList.add('translate-y-0', 'opacity-100');
            toastTimeout = setTimeout(() => {{
                toast.classList.remove('translate-y-0', 'opacity-100');
                toast.classList.add('translate-y-20', 'opacity-0');
            }}, 2400);
        }}

        function copySteps(btnEl, offerId) {{
            const offer = offersData.find(item => item.id === offerId);
            if (!offer) {{
                showToast('Unable to find voucher details');
                return;
            }}
            const textToCopy = `${{offer.title}}\\n\\nOfficial URL:\\n${{offer.url}}\\n\\nHow to Claim:\\n${{offer.claim_steps}}`;
            navigator.clipboard.writeText(textToCopy).then(() => {{
                if (btnEl) {{
                    const originalHtml = btnEl.innerHTML;
                    btnEl.innerHTML = `<svg width="14" height="14" viewBox="0 0 16 16" fill="var(--success-fg)"><path d="M13.78 4.22a.75.75 0 0 1 0 1.06l-7.25 7.25a.75.75 0 0 1-1.06 0L2.22 9.28a.751.751 0 0 1 .018-1.042.751.751 0 0 1 1.042-.018L6 10.94l6.72-6.72a.75.75 0 0 1 1.06 0Z"></path></svg><span class="text-xs font-semibold" style="color: var(--success-fg);">Copied!</span>`;
                    setTimeout(() => {{ btnEl.innerHTML = originalHtml; }}, 1800);
                }}
                showToast('Promo steps copied to clipboard!');
            }}).catch(() => {{
                showToast('Unable to copy to clipboard');
            }});
        }}

        function copyShareLink() {{
            syncUrlParams();
            if (navigator.clipboard && navigator.clipboard.writeText) {{
                navigator.clipboard.writeText(window.location.href).then(() => {{
                    showToast('Direct link with active filters copied!');
                }}).catch(() => {{
                    showToast('Unable to copy share link');
                }});
            }} else {{
                showToast('Clipboard API not supported in this browser');
            }}
        }}

        function exportFilteredJson() {{
            const filtered = getFilteredData();
            const dataBlob = new Blob([JSON.stringify(filtered, null, 2)], {{ type: 'application/json' }});
            const url = URL.createObjectURL(dataBlob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `certpulse-vouchers-${{new Date().toISOString().slice(0, 10)}}.json`;
            a.click();
            URL.revokeObjectURL(url);
            showToast('Filtered vouchers exported as JSON');
        }}

        function exportFilteredNewsJson() {{
            const cat = currentNewsCategory;
            const company = document.getElementById('newsCompanySelect').value;
            const search = currentNewsSearch.toLowerCase().trim();

            const filtered = newsData.filter(item => {{
                if (cat !== 'All' && item.category !== cat) return false;
                if (company !== 'All' && item.company !== company) return false;
                if (search !== '') {{
                    const haystack = (item.title + ' ' + item.summary + ' ' + item.company + ' ' + item.category + ' ' + (item.impact_badge || '') + ' ' + item.source_domain).toLowerCase();
                    if (!haystack.includes(search)) return false;
                }}
                return true;
            }});

            const dataBlob = new Blob([JSON.stringify(filtered, null, 2)], {{ type: 'application/json' }});
            const url = URL.createObjectURL(dataBlob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `certpulse-news-${{new Date().toISOString().slice(0, 10)}}.json`;
            a.click();
            URL.revokeObjectURL(url);
            showToast('Filtered intelligence radar exported as JSON');
        }}

        function clearSearch() {{
            const input = document.getElementById('searchInput');
            input.value = '';
            currentSearch = '';
            document.getElementById('clearSearchBtn').classList.add('hidden');
            document.getElementById('searchMatchesBadge').classList.add('hidden');
            syncUrlParams();
            renderCards();
        }}

        function clearNewsSearch() {{
            const input = document.getElementById('newsSearchInput');
            input.value = '';
            currentNewsSearch = '';
            document.getElementById('clearNewsSearchBtn').classList.add('hidden');
            document.getElementById('newsSearchMatchesBadge').classList.add('hidden');
            renderNews();
        }}

        function getPlatformColor(platform) {{
            const isLight = document.documentElement.getAttribute('data-theme') === 'light';
            if (platform.includes('Azure') || platform.includes('Microsoft')) return isLight ? '#0062a8' : '#0078d4';
            if (platform.includes('AWS') || platform.includes('Amazon')) return isLight ? '#c05b00' : '#ff9900';
            if (platform.includes('Google')) return isLight ? '#1a73e8' : '#4285f4';
            if (platform.includes('Cisco')) return isLight ? '#0b7da8' : '#1ba0d7';
            if (platform.includes('ISC2')) return isLight ? '#006b40' : '#008752';
            if (platform.includes('Oracle')) return isLight ? '#c70000' : '#f80000';
            if (platform.includes('GitHub')) return isLight ? '#1a7f37' : '#2ea043';
            if (platform.includes('Snowflake')) return isLight ? '#0088be' : '#29b5e8';
            if (platform.includes('Databricks')) return isLight ? '#c2331b' : '#ff3621';
            if (platform.includes('Linux') || platform.includes('CNCF')) return isLight ? '#002f6c' : '#58a6ff';
            if (platform.includes('MongoDB')) return isLight ? '#008438' : '#00ed64';
            if (platform.includes('Postman')) return isLight ? '#d44315' : '#ff6c37';
            if (platform.includes('Red Hat')) return isLight ? '#c00000' : '#ee0000';
            if (platform.includes('HashiCorp')) return isLight ? '#005fb8' : '#027bfd';
            if (platform.includes('Palo Alto')) return isLight ? '#c83f1c' : '#fa582d';
            if (platform.includes('GitLab')) return isLight ? '#d44e15' : '#fc6d26';
            if (platform.includes('Splunk')) return isLight ? '#c44312' : '#f15b24';
            if (platform.includes('IBM')) return isLight ? '#0043ce' : '#0f62fe';
            if (platform.includes('Fortinet')) return isLight ? '#b81d12' : '#ee3124';
            if (platform.includes('Juniper')) return isLight ? '#005573' : '#00739c';
            if (platform.includes('Qualys')) return isLight ? '#bd1219' : '#ed1c24';
            if (platform.includes('Salesforce')) return isLight ? '#0075a3' : '#00a1e0';
            return 'var(--accent-fg)';
        }}

        function getFilteredData() {{
            const sortMode = document.getElementById('sortSelect').value;
            const statusMode = document.getElementById('statusFilter').value;
            const search = currentSearch.toLowerCase().trim();

            let filtered = offersData.filter(o => {{
                // 1. SubNav Category Filter
                if (currentCategory === 'History') {{
                    if (!o.is_historical_archive && o.status !== 'Expired') return false;
                }} else if (currentCategory !== 'All' && !o.category.includes(currentCategory) && !o.platform.includes(currentCategory)) {{
                    return false;
                }}

                // 2. Select Status Filter (active when not browsing Past History category)
                if (currentCategory !== 'History') {{
                    if (statusMode === 'active' && o.status !== 'Active') return false;
                    if (statusMode === 'history' && !o.is_historical_archive && o.status !== 'Expired') return false;
                    if (statusMode === 'closed' && (o.status === 'Active' || o.is_historical_archive)) return false;
                }}

                // 3. Search Query matching
                if (search !== '') {{
                    const text = (
                        o.title + ' ' + 
                        o.platform + ' ' + 
                        o.certification_name + ' ' + 
                        (o.exam_code || '') + ' ' + 
                        (o.time_period || '') + ' ' + 
                        (o.recurrence_pattern || '') + ' ' + 
                        o.category + ' ' + 
                        (o.eligibility || '') + ' ' + 
                        (o.claim_steps || '')
                    ).toLowerCase();
                    const words = search.split(/\\s+/);
                    const allMatch = words.every(word => text.includes(word));
                    if (!allMatch) return false;
                }}

                return true;
            }});

            filtered.sort((a, b) => {{
                if (sortMode === 'val-desc') return (b.value_usd || 0) - (a.value_usd || 0);
                if (sortMode === 'val-asc') return (a.value_usd || 0) - (b.value_usd || 0);
                if (sortMode === 'name-asc') return a.platform.localeCompare(b.platform);
                return 0;
            }});

            return filtered;
        }}

        function renderCards() {{
            const filtered = getFilteredData();
            const grid = document.getElementById('offersGrid');
            const tableBody = document.getElementById('offersTableBody');
            const matchBadge = document.getElementById('searchMatchesBadge');

            document.getElementById('resultsCount').textContent = `Showing ${{filtered.length}} of ${{offersData.length}} vouchers`;
            
            if (currentSearch.trim() !== '') {{
                matchBadge.textContent = `${{filtered.length}} found`;
                matchBadge.classList.remove('hidden');
            }} else {{
                matchBadge.classList.add('hidden');
            }}

            if (filtered.length === 0) {{
                const emptyHtml = `
                    <div class="col-span-full py-16 text-center border rounded-xl" style="background-color: var(--canvas-subtle); border-color: var(--border-default);">
                        <svg class="mx-auto w-10 h-10 mb-3" style="color: var(--fg-muted);" viewBox="0 0 16 16" fill="currentColor">
                            <path d="M1.5 8a6.5 6.5 0 1 1 13 0 6.5 6.5 0 0 1-13 0ZM8 0a8 8 0 1 0 0 16A8 8 0 0 0 8 0ZM5 5a1 1 0 0 0 0 2 1 1 0 0 0 0-2Zm6 0a1 1 0 1 0 0 2 1 1 0 0 0 0-2Zm-7.465 5.5a.75.75 0 0 1 1.05-.14 4.5 4.5 0 0 0 6.83 0 .75.75 0 1 1 1.17.94 6 6 0 0 1-9.11 0 .75.75 0 0 1 .06-1Z"></path>
                        </svg>
                        <h3 class="text-base font-bold" style="color: var(--fg-default);">No matching certifications found</h3>
                        <p class="text-xs mt-1" style="color: var(--fg-muted);">Try adjusting your search terms or selecting another category.</p>
                        <button onclick="clearSearch()" class="mt-3 text-xs font-semibold px-3 py-1.5 rounded-md border cursor-pointer" style="background-color: var(--btn-default-bg); border-color: var(--border-default); color: var(--accent-fg);">Reset Search</button>
                    </div>
                `;
                grid.innerHTML = emptyHtml;
                tableBody.innerHTML = emptyHtml;
                const timelineContainer = document.getElementById('offersTimeline');
                if (timelineContainer) timelineContainer.innerHTML = emptyHtml;
                const matrixContainer = document.getElementById('offersMatrix');
                if (matrixContainer) matrixContainer.innerHTML = emptyHtml;
                return;
            }}

            if (currentLayout === 'grid') {{
                grid.innerHTML = filtered.map(o => {{
                    const isLive = (o.status === 'Active');
                    const isHistory = Boolean(o.is_historical_archive || o.status === 'Expired');
                    
                    let statusLabel, badgeBg, badgeColor;
                    if (o.status === 'Active') {{
                        statusLabel = '🟢 Active';
                        badgeBg = 'var(--success-subtle)';
                        badgeColor = 'var(--success-fg)';
                    }} else if (o.is_historical_archive || o.status === 'Expired') {{
                        statusLabel = '📜 Concluded';
                        badgeBg = 'rgba(110, 118, 129, 0.15)';
                        badgeColor = 'var(--fg-muted)';
                    }} else if (o.status === 'Registrations Closed') {{
                        statusLabel = '🟡 Closed';
                        badgeBg = 'var(--attention-subtle)';
                        badgeColor = 'var(--attention-fg)';
                    }} else if (o.status === 'Review Needed') {{
                        statusLabel = '⚠️ Review';
                        badgeBg = 'var(--attention-subtle)';
                        badgeColor = 'var(--attention-fg)';
                    }} else {{
                        statusLabel = '🔴 Expired';
                        badgeBg = 'rgba(248, 81, 73, 0.15)';
                        badgeColor = 'var(--danger-fg)';
                    }}

                    const brandColor = getPlatformColor(o.platform);
                    const brandIcon = getPlatformIconSvg(o.platform);

                    const examBadge = o.exam_code ? `
                        <div class="mt-2 flex items-center gap-1.5 flex-wrap">
                            <span class="text-xs font-mono font-medium px-2 py-0.5 rounded border" style="background-color: var(--canvas-inset); border-color: var(--border-default); color: var(--fg-default);" title="Official Exam Code">
                                Exam: ${{o.exam_code}}
                            </span>
                        </div>
                    ` : '';

                    const timePeriodInfo = o.time_period ? `
                        <div class="text-xs mt-2 font-medium flex items-center gap-1.5" style="color: var(--accent-fg);">
                            <svg class="w-3.5 h-3.5 flex-shrink-0" viewBox="0 0 16 16" fill="currentColor"><path d="M4.75 0a.75.75 0 0 1 .75.75V2h5V.75a.75.75 0 0 1 1.5 0V2h1.25c.966 0 1.75.784 1.75 1.75v10.5A1.75 1.75 0 0 1 13.25 16H2.75A1.75 1.75 0 0 1 1 14.25V3.75C1 2.784 1.784 2 2.75 2H4V.75A.75.75 0 0 1 4.75 0ZM2.5 7.5v6.75c0 .138.112.25.25.25h10.5a.25.25 0 0 0 .25-.25V7.5Zm10.75-2a.25.25 0 0 0-.25-.25H2.75a.25.25 0 0 0-.25.25V6h11Z"></path></svg>
                            <span class="truncate">📅 Period: ${{o.time_period}}</span>
                        </div>
                    ` : '';

                    const recurrenceInfo = o.recurrence_pattern ? `
                        <div class="text-xs mt-1 font-medium flex items-center gap-1.5" style="color: var(--fg-muted);">
                            <svg class="w-3.5 h-3.5 flex-shrink-0" viewBox="0 0 16 16" fill="currentColor"><path d="M8 0a8 8 0 1 1 0 16A8 8 0 0 1 8 0ZM1.5 8a6.5 6.5 0 1 0 13 0 6.5 6.5 0 0 0-13 0Zm7.25-3.25v3.69l2.28 2.28a.75.75 0 1 1-1.06 1.06l-2.5-2.5a.75.75 0 0 1-.22-.53V4.75a.75.75 0 0 1 1.5 0Z"></path></svg>
                            <span class="truncate">🔁 Recurrence: ${{o.recurrence_pattern}}</span>
                        </div>
                    ` : '';

                    const actionBtnText = isLive ? 'Claim Free' : (isHistory ? 'Archive Link' : 'View Link');
                    const actionBtnBg = isLive ? 'var(--btn-primary-bg)' : 'var(--btn-default-bg)';
                    const actionBtnColor = isLive ? '#ffffff' : 'var(--fg-default)';
                    const actionBtnBorder = isLive ? 'transparent' : 'var(--border-default)';

                    const authScore = (typeof o.authenticity_score === 'number') ? o.authenticity_score : 100;
                    const isAuth = (o.is_authentic_vendor !== false);
                    const authSummary = (o.authenticity_details && o.authenticity_details.summary) ? o.authenticity_details.summary : '100% Authentic: Verified Official Vendor Portal with strict TLS';
                    const authChip = isAuth ? `
                        <span class="text-[11px] font-semibold px-2 py-0.5 rounded border flex items-center gap-1 tabular-nums" style="background-color: var(--success-subtle); color: var(--success-fg); border-color: var(--success-fg);" title="${{authSummary}}">
                            <svg class="w-3 h-3 flex-shrink-0" viewBox="0 0 16 16" fill="currentColor"><path d="M7.467.133a1.748 1.748 0 0 1 1.066 0l5.25 1.68A1.75 1.75 0 0 1 15 3.48V7c0 1.566-.32 3.182-1.303 4.682-.983 1.498-2.585 2.813-5.032 3.855a1.697 1.697 0 0 1-1.33 0c-2.447-1.042-4.049-2.357-5.032-3.855C1.32 10.182 1 8.566 1 7V3.48a1.75 1.75 0 0 1 1.217-1.667l5.25-1.68ZM8 1.62 3.25 3.14a.25.25 0 0 0-.174.238V7c0 1.258.26 2.532 1.05 3.738.79 1.205 2.06 2.25 4.024 3.09a.197.197 0 0 0 .15 0c1.964-.84 3.234-1.885 4.024-3.09.79-1.206 1.05-2.48 1.05-3.738V3.378a.25.25 0 0 0-.174-.238L8 1.62Z"></path><path d="m10.854 6.146-3.5 3.5a.5.5 0 0 1-.708 0l-1.5-1.5a.5.5 0 1 1 .708-.708L7 8.543l3.146-3.147a.5.5 0 0 1 .708.708Z"></path></svg>
                            <span>${{authScore}}% Authentic</span>
                        </span>
                    ` : `
                        <span class="text-[11px] font-semibold px-2 py-0.5 rounded border flex items-center gap-1 tabular-nums" style="background-color: var(--attention-subtle); color: var(--attention-fg); border-color: var(--attention-fg);" title="${{authSummary}}">
                            <span>⚠️ Review Domain</span>
                        </span>
                    `;

                    return `
                        <div class="primer-card p-4 sm:p-5 rounded-xl flex flex-col justify-between">
                            <div>
                                <div class="flex items-center justify-between gap-2 mb-2.5">
                                    <span class="text-xs font-bold px-2.5 py-1 rounded-lg flex items-center gap-2 max-w-[70%]" style="background-color: var(--canvas-inset); color: ${{brandColor}}; border: 1px solid var(--border-default);">
                                        <span class="flex items-center justify-center flex-shrink-0">${{brandIcon}}</span>
                                        <span class="truncate">${{o.platform}}</span>
                                    </span>
                                    <span class="text-xs font-semibold px-2 py-0.5 rounded-md tabular-nums flex-shrink-0" style="background-color: ${{badgeBg}}; color: ${{badgeColor}}; border: 1px solid ${{badgeColor}};">
                                        ${{statusLabel}}
                                    </span>
                                </div>

                                <h3 class="text-sm sm:text-base font-bold leading-snug hover:underline cursor-pointer text-balance" style="color: var(--fg-default);" onclick="window.open('${{o.url}}', '_blank')">
                                    ${{o.title}}
                                </h3>

                                <div class="flex items-center gap-2 mt-2 flex-wrap">
                                    <span class="text-xs font-mono font-bold px-2 py-0.5 rounded border tabular-nums" style="background-color: var(--success-subtle); color: var(--success-fg); border-color: var(--success-fg);">
                                        $${{o.value_usd || 0}} USD Value
                                    </span>
                                    ${{authChip}}
                                    <span class="text-xs font-medium" style="color: var(--fg-muted);">
                                        ${{o.offer_type}}
                                    </span>
                                </div>

                                ${{examBadge}}
                                ${{timePeriodInfo}}
                                ${{recurrenceInfo}}

                                <details class="mt-3.5 text-xs group cursor-pointer">
                                    <summary class="font-semibold select-none flex items-center justify-between py-1.5 hover:underline" style="color: var(--accent-fg);">
                                        <span>${{isHistory ? 'View Archived Promotion & Details' : 'View How to Claim'}}</span>
                                        <svg class="w-3.5 h-3.5 transition group-open:rotate-180 flex-shrink-0" viewBox="0 0 16 16" fill="currentColor"><path d="M4.427 7.427l3.396 3.396a.25.25 0 0 0 .354 0l3.396-3.396A.25.25 0 0 0 11.396 7H4.604a.25.25 0 0 0-.177.427Z"></path></svg>
                                    </summary>
                                    <div class="mt-2 p-3 rounded-lg text-xs leading-relaxed space-y-2 border" style="background-color: var(--canvas-inset); border-color: var(--border-muted); color: var(--fg-default);">
                                        <div>
                                            <span class="font-semibold block text-xs mb-0.5" style="color: var(--fg-muted);">Eligibility</span>
                                            <p class="text-pretty">${{o.eligibility || 'Open to all learners and developers.'}}</p>
                                        </div>
                                        <div>
                                            <span class="font-semibold block text-xs mb-0.5" style="color: var(--fg-muted);">Authenticity Verification</span>
                                            <p class="text-pretty text-[11px]" style="color: var(--success-fg);">🛡️ ${{authSummary}}</p>
                                        </div>
                                        <div>
                                            <span class="font-semibold block text-xs mb-0.5" style="color: var(--fg-muted);">${{isHistory ? 'Archived Instructions / Context' : 'Claim Instructions'}}</span>
                                            <p class="whitespace-pre-line text-pretty">${{o.claim_steps}}</p>
                                        </div>
                                    </div>
                                </details>
                            </div>

                            <div class="mt-4 pt-3 border-t flex items-center justify-between gap-2" style="border-color: var(--border-muted);">
                                <button onclick="copySteps(this, '${{o.id}}')" class="min-h-[40px] px-3.5 py-2 rounded-lg border text-xs font-semibold hover:opacity-80 active:scale-[0.98] transition flex items-center gap-1.5 flex-shrink-0 cursor-pointer" style="background-color: var(--btn-default-bg); border-color: var(--border-default); color: var(--fg-default);" title="Copy claim steps to clipboard" aria-label="Copy claim steps">
                                    <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M0 6.75C0 5.784.784 5 1.75 5h1.5a.75.75 0 0 1 0 1.5h-1.5a.25.25 0 0 0-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 0 0 .25-.25v-1.5a.75.75 0 0 1 1.5 0v1.5A1.75 1.75 0 0 1 9.25 16h-7.5A1.75 1.75 0 0 1 0 14.25Z"></path><path d="M5 1.75C5 .784 5.784 0 6.75 0h7.5C15.216 0 16 .784 16 1.75v7.5A1.75 1.75 0 0 1 14.25 11h-7.5A1.75 1.75 0 0 1 5 9.25Zm1.75-.25a.25.25 0 0 0-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 0 0 .25-.25v-7.5a.25.25 0 0 0-.25-.25Z"></path></svg>
                                    <span>Copy Guide</span>
                                </button>
                                <a href="${{o.url}}" target="_blank" class="flex-1 min-h-[40px] flex items-center justify-center text-center px-4 py-2 rounded-lg text-xs font-bold transition hover:opacity-90 active:scale-[0.98] border shadow-xs cursor-pointer" style="background-color: ${{actionBtnBg}}; color: ${{actionBtnColor}}; border-color: ${{actionBtnBorder}};">
                                    <span>${{actionBtnText}}</span>
                                    <svg class="w-3.5 h-3.5 ml-1.5 flex-shrink-0" viewBox="0 0 16 16" fill="currentColor"><path d="M3.75 2h3.5a.75.75 0 0 1 0 1.5h-3.5a.25.25 0 0 0-.25.25v8.5c0 .138.112.25.25.25h8.5a.25.25 0 0 0 .25-.25v-3.5a.75.75 0 0 1 1.5 0v3.5A1.75 1.75 0 0 1 12.25 14h-8.5A1.75 1.75 0 0 1 2 12.25v-8.5C2 2.784 2.784 2 3.75 2Zm6.5.75a.75.75 0 0 1 .75-.75h3.5a.75.75 0 0 1 .75.75v3.5a.75.75 0 0 1-1.5 0V4.56L9.53 8.78a.75.75 0 0 1-1.06-1.06l4.22-4.22H11a.75.75 0 0 1-.75-.75Z"></path></svg>
                                </a>
                            </div>
                        </div>
                    `;
                }}).join('');
            }} else if (currentLayout === 'list') {{
                // Executive Directory Table Catalog View (Mobile Responsive Cards / Desktop Rows)
                tableBody.innerHTML = filtered.map(o => {{
                    const isLive = (o.status === 'Active');
                    const isHistory = Boolean(o.is_historical_archive || o.status === 'Expired');
                    
                    let statusLabel, badgeBg, badgeColor;
                    if (o.status === 'Active') {{
                        statusLabel = 'Active';
                        badgeBg = 'var(--success-subtle)';
                        badgeColor = 'var(--success-fg)';
                    }} else if (o.is_historical_archive || o.status === 'Expired') {{
                        statusLabel = 'Concluded';
                        badgeBg = 'rgba(110, 118, 129, 0.15)';
                        badgeColor = 'var(--fg-muted)';
                    }} else if (o.status === 'Registrations Closed') {{
                        statusLabel = 'Closed';
                        badgeBg = 'var(--attention-subtle)';
                        badgeColor = 'var(--attention-fg)';
                    }} else if (o.status === 'Review Needed') {{
                        statusLabel = 'Review';
                        badgeBg = 'var(--attention-subtle)';
                        badgeColor = 'var(--attention-fg)';
                    }} else {{
                        statusLabel = 'Expired';
                        badgeBg = 'rgba(248, 81, 73, 0.15)';
                        badgeColor = 'var(--danger-fg)';
                    }}

                    const brandColor = getPlatformColor(o.platform);
                    const brandIcon = getPlatformIconSvg(o.platform);

                    const examChip = o.exam_code ? `<span class="px-2 py-0.5 rounded border text-xs font-mono font-medium" style="background-color: var(--canvas-inset); border-color: var(--border-default); color: var(--fg-default);">${{o.exam_code}}</span>` : '';
                    const timeChip = o.time_period ? `<span class="text-xs font-medium" style="color: var(--accent-fg);">📅 ${{o.time_period}}</span>` : '';

                    const actionBtnText = isLive ? 'Claim' : (isHistory ? 'Archive' : 'View');
                    const actionBtnBg = isLive ? 'var(--btn-primary-bg)' : 'var(--btn-default-bg)';
                    const actionBtnColor = isLive ? '#ffffff' : 'var(--fg-default)';
                    const actionBtnBorder = isLive ? 'transparent' : 'var(--border-default)';

                    const authScore = (typeof o.authenticity_score === 'number') ? o.authenticity_score : 100;
                    const isAuth = (o.is_authentic_vendor !== false);
                    const authSummary = (o.authenticity_details && o.authenticity_details.summary) ? o.authenticity_details.summary : '100% Authentic: Verified Official Vendor Portal with strict TLS';
                    const authChip = isAuth ? `
                        <span class="text-[10px] font-semibold px-1.5 py-0.5 rounded border flex items-center gap-1 tabular-nums" style="background-color: var(--success-subtle); color: var(--success-fg); border-color: var(--success-fg);" title="${{authSummary}}">
                            <svg class="w-2.5 h-2.5 flex-shrink-0" viewBox="0 0 16 16" fill="currentColor"><path d="M7.467.133a1.748 1.748 0 0 1 1.066 0l5.25 1.68A1.75 1.75 0 0 1 15 3.48V7c0 1.566-.32 3.182-1.303 4.682-.983 1.498-2.585 2.813-5.032 3.855a1.697 1.697 0 0 1-1.33 0c-2.447-1.042-4.049-2.357-5.032-3.855C1.32 10.182 1 8.566 1 7V3.48a1.75 1.75 0 0 1 1.217-1.667l5.25-1.68ZM8 1.62 3.25 3.14a.25.25 0 0 0-.174.238V7c0 1.258.26 2.532 1.05 3.738.79 1.205 2.06 2.25 4.024 3.09a.197.197 0 0 0 .15 0c1.964-.84 3.234-1.885 4.024-3.09.79-1.206 1.05-2.48 1.05-3.738V3.378a.25.25 0 0 0-.174-.238L8 1.62Z"></path><path d="m10.854 6.146-3.5 3.5a.5.5 0 0 1-.708 0l-1.5-1.5a.5.5 0 1 1 .708-.708L7 8.543l3.146-3.147a.5.5 0 0 1 .708.708Z"></path></svg>
                            <span>${{authScore}}% Authentic</span>
                        </span>
                    ` : `
                        <span class="text-[10px] font-semibold px-1.5 py-0.5 rounded border flex items-center gap-1 tabular-nums" style="background-color: var(--attention-subtle); color: var(--attention-fg); border-color: var(--attention-fg);" title="${{authSummary}}">
                            <span>⚠️ Review</span>
                        </span>
                    `;

                    return `
                        <div class="p-3.5 sm:p-4 sm:grid sm:grid-cols-12 gap-3 items-center text-xs transition hover:bg-[var(--canvas-default)]">
                            <!-- Mobile Top Row / Desktop Col 1: Provider & Logo -->
                            <div class="col-span-3 flex items-center justify-between sm:justify-start gap-2.5 mb-2 sm:mb-0">
                                <div class="flex items-center gap-2 min-w-0">
                                    <span class="p-1 rounded-md border flex items-center justify-center flex-shrink-0" style="background-color: var(--canvas-inset); border-color: var(--border-default);">
                                        ${{brandIcon}}
                                    </span>
                                    <div class="min-w-0">
                                        <span class="font-bold block truncate text-xs" style="color: ${{brandColor}};">${{o.platform}}</span>
                                        <span class="text-[11px] truncate block" style="color: var(--fg-muted);">${{o.offer_type}}</span>
                                    </div>
                                </div>
                                <!-- Mobile Only: Value & Status Badges right aligned -->
                                <div class="flex sm:hidden items-center gap-1.5 flex-shrink-0">
                                    <span class="font-mono font-bold text-[11px] px-2 py-0.5 rounded border tabular-nums" style="background-color: var(--success-subtle); color: var(--success-fg); border-color: var(--success-fg);">
                                        $${{o.value_usd || 0}}
                                    </span>
                                    <span class="text-[11px] font-semibold px-2 py-0.5 rounded tabular-nums" style="background-color: ${{badgeBg}}; color: ${{badgeColor}}; border: 1px solid ${{badgeColor}};">
                                        ${{statusLabel}}
                                    </span>
                                </div>
                            </div>

                            <!-- Certification Name & Details -->
                            <div class="col-span-5 min-w-0 pr-0 sm:pr-2 mb-2 sm:mb-0">
                                <a href="${{o.url}}" target="_blank" class="font-bold leading-snug hover:underline block text-xs sm:text-sm text-balance" style="color: var(--fg-default);" title="${{o.title}}">
                                    ${{o.title}}
                                </a>
                                <div class="flex items-center gap-2 mt-1 flex-wrap text-xs" style="color: var(--fg-muted);">
                                    ${{examChip}}
                                    <span class="px-2 py-0.5 rounded border font-medium text-[11px]" style="background-color: var(--canvas-inset); border-color: var(--border-default); color: var(--fg-subtle);">${{o.category}}</span>
                                    ${{authChip}}
                                    ${{timeChip ? `<span class="opacity-40">/</span>${{timeChip}}` : ''}}
                                </div>
                            </div>

                            <!-- Desktop Only: Value & Status -->
                            <div class="hidden sm:flex col-span-2 sm:flex-col items-center justify-center gap-1.5 mb-2 sm:mb-0">
                                <span class="font-mono font-bold text-xs px-2.5 py-0.5 rounded border tabular-nums" style="background-color: var(--success-subtle); color: var(--success-fg); border-color: var(--success-fg);">
                                    $${{o.value_usd || 0}} USD
                                </span>
                                <span class="text-xs font-semibold px-2 py-0.5 rounded tabular-nums" style="background-color: ${{badgeBg}}; color: ${{badgeColor}}; border: 1px solid ${{badgeColor}};">
                                    ${{statusLabel}}
                                </span>
                            </div>

                            <!-- Action Buttons: Responsive for Mobile & Desktop -->
                            <div class="col-span-2 flex items-center justify-between sm:justify-end gap-2 pt-2 sm:pt-0 border-t sm:border-t-0" style="border-color: var(--border-muted);">
                                <button onclick="copySteps(this, '${{o.id}}')" class="min-h-[40px] px-3 py-2 rounded-lg border hover:opacity-80 active:scale-[0.98] transition flex items-center gap-1.5 text-xs font-semibold cursor-pointer" style="background-color: var(--btn-default-bg); border-color: var(--border-default); color: var(--fg-default);" title="Copy claim steps" aria-label="Copy claim steps">
                                    <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M0 6.75C0 5.784.784 5 1.75 5h1.5a.75.75 0 0 1 0 1.5h-1.5a.25.25 0 0 0-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 0 0 .25-.25v-1.5a.75.75 0 0 1 1.5 0v1.5A1.75 1.75 0 0 1 9.25 16h-7.5A1.75 1.75 0 0 1 0 14.25Z"></path><path d="M5 1.75C5 .784 5.784 0 6.75 0h7.5C15.216 0 16 .784 16 1.75v7.5A1.75 1.75 0 0 1 14.25 11h-7.5A1.75 1.75 0 0 1 5 9.25Zm1.75-.25a.25.25 0 0 0-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 0 0 .25-.25v-7.5a.25.25 0 0 0-.25-.25Z"></path></svg>
                                    <span class="sm:hidden">Guide</span>
                                </button>
                                <a href="${{o.url}}" target="_blank" class="flex-1 sm:flex-initial min-h-[40px] flex items-center justify-center text-center px-3.5 py-2 rounded-lg text-xs font-bold transition hover:opacity-90 active:scale-[0.98] border whitespace-nowrap cursor-pointer" style="background-color: ${{actionBtnBg}}; color: ${{actionBtnColor}}; border-color: ${{actionBtnBorder}};">
                                    <span>${{actionBtnText}}</span>
                                    <svg class="w-3.5 h-3.5 ml-1.5 flex-shrink-0" viewBox="0 0 16 16" fill="currentColor"><path d="M3.75 2h3.5a.75.75 0 0 1 0 1.5h-3.5a.25.25 0 0 0-.25.25v8.5c0 .138.112.25.25.25h8.5a.25.25 0 0 0 .25-.25v-3.5a.75.75 0 0 1 1.5 0v3.5A1.75 1.75 0 0 1 12.25 14h-8.5A1.75 1.75 0 0 1 2 12.25v-8.5C2 2.784 2.784 2 3.75 2Zm6.5.75a.75.75 0 0 1 .75-.75h3.5a.75.75 0 0 1 .75.75v3.5a.75.75 0 0 1-1.5 0V4.56L9.53 8.78a.75.75 0 0 1-1.06-1.06l4.22-4.22H11a.75.75 0 0 1-.75-.75Z"></path></svg>
                                </a>
                            </div>
                        </div>
                    `;
                }}).join('');
            }} else if (currentLayout === 'timeline') {{
                const timelineContainer = document.getElementById('offersTimeline');
                
                const rollingOffers = filtered.filter(o => o.status === 'Active' && (!o.time_period || o.time_period.toLowerCase().includes('rolling') || o.time_period.toLowerCase().includes('continuous')));
                const seasonalOffers = filtered.filter(o => o.status === 'Active' && !rollingOffers.includes(o));
                const historicalOffers = filtered.filter(o => o.status !== 'Active' || o.is_historical_archive);

                const groups = [
                    {{
                        title: "🚀 Active Rolling Tracks & Continuous Enrollment",
                        desc: "Verified 100% free certifications and exam vouchers open year-round for immediate booking and completion.",
                        badge: `${{rollingOffers.length}} Active Tracks`,
                        badgeClass: "var(--success-subtle)",
                        badgeColor: "var(--success-fg)",
                        items: rollingOffers
                    }},
                    {{
                        title: "⚡ Active Seasonal Waves & Application Cohorts",
                        desc: "Time-windowed promotional challenges, community waves, and quarterly scholarship application sprints.",
                        badge: `${{seasonalOffers.length}} Active Waves`,
                        badgeClass: "var(--accent-subtle)",
                        badgeColor: "var(--accent-fg)",
                        items: seasonalOffers
                    }},
                    {{
                        title: "📜 Historical Waves & Annual Recurrence Milestones",
                        desc: "Tracked past conference promotional campaigns to predict upcoming seasonal developer conference waves.",
                        badge: `${{historicalOffers.length}} Recurrence Anchors`,
                        badgeClass: "rgba(110, 118, 129, 0.15)",
                        badgeColor: "var(--fg-muted)",
                        items: historicalOffers
                    }}
                ];

                timelineContainer.innerHTML = groups.filter(g => g.items.length > 0).map(group => {{
                    const cardsHtml = group.items.map(o => {{
                        const isLive = (o.status === 'Active');
                        const brandColor = getPlatformColor(o.platform);
                        const brandIcon = getPlatformIconSvg(o.platform);
                        const authScore = (typeof o.authenticity_score === 'number') ? o.authenticity_score : 100;
                        const actionBtnText = isLive ? 'Claim Free' : 'Archive Link';
                        const actionBtnBg = isLive ? 'var(--btn-primary-bg)' : 'var(--btn-default-bg)';
                        const actionBtnColor = isLive ? '#ffffff' : 'var(--fg-default)';
                        const actionBtnBorder = isLive ? 'transparent' : 'var(--border-default)';

                        return `
                            <div class="relative pl-6 sm:pl-8 pb-6 group">
                                <div class="absolute -left-[9px] top-1.5 w-4 h-4 rounded-full border-2 flex items-center justify-center" style="left: -9px; background-color: var(--canvas-default); border-color: ${{isLive ? 'var(--success-fg)' : 'var(--border-default)'}};">
                                    <div class="w-2 h-2 rounded-full ${{isLive ? 'animate-pulse' : ''}}" style="background-color: ${{isLive ? 'var(--success-fg)' : 'var(--fg-muted)'}};"></div>
                                </div>
                                <div class="primer-card p-4 sm:p-5 rounded-xl border flex flex-col justify-between">
                                    <div>
                                        <div class="flex flex-wrap items-center justify-between gap-2 mb-2">
                                            <div class="flex items-center gap-2 flex-wrap">
                                                <span class="text-xs font-bold px-2 py-0.5 rounded-md flex items-center gap-1.5 border" style="background-color: var(--canvas-inset); color: ${{brandColor}}; border-color: var(--border-default);">
                                                    <span class="flex items-center justify-center flex-shrink-0">${{brandIcon}}</span>
                                                    <span>${{o.platform}}</span>
                                                </span>
                                                <span class="text-xs font-semibold px-2 py-0.5 rounded-md border flex items-center gap-1 tabular-nums" style="background-color: var(--canvas-inset); color: var(--accent-fg); border-color: var(--border-muted);">
                                                    <span>📅 ${{o.time_period || 'Rolling'}}</span>
                                                </span>
                                                ${{o.recurrence_pattern ? `
                                                    <span class="text-xs font-medium px-2 py-0.5 rounded-md border hidden xs:inline-flex" style="background-color: var(--canvas-inset); color: var(--fg-muted); border-color: var(--border-muted);">
                                                        🔁 ${{o.recurrence_pattern}}
                                                    </span>
                                                ` : ''}}
                                            </div>
                                            <span class="text-xs font-bold px-2.5 py-0.5 rounded-full tabular-nums" style="background-color: var(--success-subtle); color: var(--success-fg); border: 1px solid var(--success-fg);">
                                                $${{o.value_usd || 0}} USD Value
                                            </span>
                                        </div>

                                        <h3 class="text-sm sm:text-base font-bold hover:underline cursor-pointer" style="color: var(--fg-default);" onclick="window.open('${{o.url}}', '_blank')">
                                            ${{o.title}}
                                        </h3>

                                        <div class="flex items-center gap-2 mt-2 flex-wrap">
                                            ${{o.exam_code ? `
                                                <span class="text-xs font-mono font-medium px-2 py-0.5 rounded border" style="background-color: var(--canvas-inset); border-color: var(--border-default); color: var(--fg-default);">
                                                    Exam: ${{o.exam_code}}
                                                </span>
                                            ` : ''}}
                                            <span class="text-xs px-2 py-0.5 rounded border font-semibold tabular-nums" style="background-color: var(--success-subtle); color: var(--success-fg); border-color: var(--success-fg);">
                                                🛡️ ${{authScore}}% Verified
                                            </span>
                                            <span class="text-xs font-medium" style="color: var(--fg-muted);">
                                                Tier: ${{o.difficulty_tier || 'Associate'}}
                                            </span>
                                        </div>

                                        <p class="text-xs mt-2 text-pretty leading-relaxed" style="color: var(--fg-muted);">
                                            ${{o.claim_steps ? o.claim_steps.slice(0, 160) + (o.claim_steps.length > 160 ? '...' : '') : ''}}
                                        </p>
                                    </div>

                                    <div class="mt-3 pt-2.5 border-t flex items-center justify-between gap-2" style="border-color: var(--border-muted);">
                                        <button onclick="copySteps(this, '${{o.id}}')" class="min-h-[40px] px-3 py-1.5 rounded-lg border text-xs font-semibold hover:opacity-80 active:scale-[0.98] transition flex items-center gap-1.5 cursor-pointer" style="background-color: var(--btn-default-bg); border-color: var(--border-default); color: var(--fg-default);">
                                            <span>Copy Guide</span>
                                        </button>
                                        <a href="${{o.url}}" target="_blank" class="min-h-[40px] px-4 py-1.5 rounded-lg text-xs font-bold transition hover:opacity-90 active:scale-[0.98] flex items-center gap-1 border shadow-xs cursor-pointer" style="background-color: ${{actionBtnBg}}; color: ${{actionBtnColor}}; border-color: ${{actionBtnBorder}};">
                                            <span>${{actionBtnText}}</span>
                                            <svg class="w-3.5 h-3.5" viewBox="0 0 16 16" fill="currentColor"><path d="M3.75 2h3.5a.75.75 0 0 1 0 1.5h-3.5a.25.25 0 0 0-.25.25v8.5c0 .138.112.25.25.25h8.5a.25.25 0 0 0 .25-.25v-3.5a.75.75 0 0 1 1.5 0v3.5A1.75 1.75 0 0 1 12.25 14h-8.5A1.75 1.75 0 0 1 2 12.25v-8.5C2 2.784 2.784 2 3.75 2Zm6.5.75a.75.75 0 0 1 .75-.75h3.5a.75.75 0 0 1 .75.75v3.5a.75.75 0 0 1-1.5 0V4.56L9.53 8.78a.75.75 0 0 1-1.06-1.06l4.22-4.22H11a.75.75 0 0 1-.75-.75Z"></path></svg>
                                        </a>
                                    </div>
                                </div>
                            </div>
                        `;
                    }}).join('');

                    return `
                        <div class="rounded-xl border p-4 sm:p-5" style="background-color: var(--canvas-subtle); border-color: var(--border-default);">
                            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-4 mb-4 border-b" style="border-color: var(--border-muted);">
                                <div>
                                    <h3 class="text-sm sm:text-base font-bold" style="color: var(--fg-default);">${{group.title}}</h3>
                                    <p class="text-xs mt-0.5" style="color: var(--fg-muted);">${{group.desc}}</p>
                                </div>
                                <span class="self-start sm:self-center text-xs font-semibold px-2.5 py-1 rounded-md border tabular-nums" style="background-color: ${{group.badgeClass}}; color: ${{group.badgeColor}}; border-color: ${{group.badgeColor}};">
                                    ${{group.badge}}
                                </span>
                            </div>
                            <div class="border-l-2 ml-2 sm:ml-4 pl-2 sm:pl-4 space-y-2 relative" style="border-color: var(--border-default);">
                                ${{cardsHtml}}
                            </div>
                        </div>
                    `;
                }}).join('');
            }} else if (currentLayout === 'matrix') {{
                const matrixContainer = document.getElementById('offersMatrix');

                const domains = [
                    {{ id: 'cloud', name: 'Cloud Infrastructure & Architecture', icon: '☁️', matcher: o => o.category.includes('Cloud') || o.platform.includes('AWS') || o.platform.includes('Azure') || o.platform.includes('Google') || o.platform.includes('Oracle') }},
                    {{ id: 'security', name: 'Cybersecurity & Zero Trust Defense', icon: '🛡️', matcher: o => o.category.includes('Security') || ['ISC2', 'Palo Alto Networks', 'Splunk', 'IBM', 'Qualys', 'Fortinet'].includes(o.platform) || (o.platform === 'Cisco' && (o.category.includes('Security') || o.title.includes('Cyber'))) }},
                    {{ id: 'ai_data', name: 'AI, Machine Learning & Data Systems', icon: '🤖', matcher: o => o.category.includes('AI') || o.category.includes('Data') || ['Databricks', 'Snowflake', 'MongoDB'].includes(o.platform) || o.title.includes('AI') || o.title.includes('Data') }},
                    {{ id: 'devops', name: 'DevOps, SRE & Cloud Native', icon: '⚙️', matcher: o => o.category.includes('DevOps') || ['Linux Foundation / CNCF', 'Red Hat', 'HashiCorp', 'GitLab', 'GitHub', 'Postman'].includes(o.platform) }},
                    {{ id: 'networking', name: 'Enterprise Networking & Telemetry', icon: '🌐', matcher: o => o.category.includes('Networking') || (['Cisco', 'Juniper Networks'].includes(o.platform) && !o.category.includes('Security') && !o.title.includes('Cyber')) }}
                ];

                const activeDomains = domains.filter(dom => filtered.some(dom.matcher));
                const displayDomains = activeDomains.length > 0 ? activeDomains : domains;

                const tiers = [
                    {{ id: 'Foundational', name: 'Foundational', level: 'Level 100', color: 'var(--success-fg)', desc: 'Concepts & Overview' }},
                    {{ id: 'Associate', name: 'Associate', level: 'Level 200', color: 'var(--accent-fg)', desc: 'Practitioner & Dev' }},
                    {{ id: 'Professional', name: 'Professional', level: 'Level 300+', color: '#a371f7', desc: 'Specialist & Architect' }}
                ];

                matrixContainer.innerHTML = `
                    <div class="rounded-xl border overflow-hidden shadow-xs" style="background-color: var(--canvas-subtle); border-color: var(--border-default);">
                        <!-- Desktop Matrix Column Header -->
                        <div class="hidden lg:grid grid-cols-12 gap-3 px-4 py-3 border-b text-xs font-semibold" style="background-color: var(--canvas-inset); border-color: var(--border-default); color: var(--fg-muted);">
                            <div class="col-span-3">Technical Domain</div>
                            <div class="col-span-3 flex items-center justify-between">
                                <span>🟢 Foundational (100)</span>
                                <span class="text-[10px] opacity-70">Entry & Overview</span>
                            </div>
                            <div class="col-span-3 flex items-center justify-between">
                                <span>🔵 Associate (200)</span>
                                <span class="text-[10px] opacity-70">Practitioner & Dev</span>
                            </div>
                            <div class="col-span-3 flex items-center justify-between">
                                <span>🟣 Professional (300+)</span>
                                <span class="text-[10px] opacity-70">Specialist & Architect</span>
                            </div>
                        </div>

                        <div class="divide-y" style="border-color: var(--border-muted);">
                            ${{displayDomains.map(dom => {{
                                const domainOffers = filtered.filter(dom.matcher);
                                
                                return `
                                    <div class="p-4 sm:p-5 lg:grid lg:grid-cols-12 lg:gap-4 items-start">
                                        <!-- Domain Title Column -->
                                        <div class="lg:col-span-3 mb-3 lg:mb-0">
                                            <div class="flex items-center gap-2">
                                                <span class="text-base">${{dom.icon}}</span>
                                                <h4 class="text-sm font-bold" style="color: var(--fg-default);">${{dom.name}}</h4>
                                            </div>
                                            <p class="text-xs mt-1" style="color: var(--fg-muted);">${{domainOffers.length}} vouchers in this domain</p>
                                        </div>

                                        <!-- Tier Columns -->
                                        ${{tiers.map(tier => {{
                                            const tierOffers = domainOffers.filter(o => (o.difficulty_tier || 'Associate') === tier.id);
                                            
                                            return `
                                                <div class="lg:col-span-3 mb-3 lg:mb-0 rounded-lg p-2.5 border" style="background-color: var(--canvas-inset); border-color: var(--border-default);">
                                                    <div class="flex items-center justify-between pb-1.5 mb-2 border-b lg:hidden" style="border-color: var(--border-muted);">
                                                        <span class="text-xs font-bold" style="color: ${{tier.color}};">${{tier.name}} (${{tier.level}})</span>
                                                        <span class="text-[11px] tabular-nums" style="color: var(--fg-muted);">${{tierOffers.length}}</span>
                                                    </div>

                                                    ${{tierOffers.length === 0 ? `
                                                        <div class="py-4 text-center text-xs" style="color: var(--fg-muted);">
                                                            <span class="italic">No vouchers in this tier</span>
                                                        </div>
                                                    ` : `
                                                        <div class="space-y-2">
                                                            ${{tierOffers.map(o => {{
                                                                const brandColor = getPlatformColor(o.platform);
                                                                const brandIcon = getPlatformIconSvg(o.platform);
                                                                const isLive = (o.status === 'Active');

                                                                return `
                                                                    <div class="primer-card p-2.5 rounded-lg border text-xs flex flex-col justify-between" style="border-color: var(--border-muted);">
                                                                        <div>
                                                                            <div class="flex items-center justify-between gap-1 mb-1">
                                                                                <span class="font-bold flex items-center gap-1 truncate" style="color: ${{brandColor}};">
                                                                                    <span class="flex-shrink-0">${{brandIcon}}</span>
                                                                                    <span class="truncate">${{o.platform}}</span>
                                                                                </span>
                                                                                <span class="text-[10px] font-bold px-1.5 py-0.2 rounded tabular-nums flex-shrink-0" style="background-color: var(--success-subtle); color: var(--success-fg);">
                                                                                    $${{o.value_usd || 0}}
                                                                                </span>
                                                                            </div>
                                                                            <a href="${{o.url}}" target="_blank" class="font-semibold block hover:underline leading-snug line-clamp-2" style="color: var(--fg-default);" title="${{o.title}}">
                                                                                ${{o.title}}
                                                                            </a>
                                                                            ${{o.exam_code ? `
                                                                                <span class="text-[10px] font-mono mt-1 inline-block px-1 rounded border" style="background-color: var(--canvas-default); border-color: var(--border-muted); color: var(--fg-muted);">
                                                                                    ${{o.exam_code}}
                                                                                </span>
                                                                            ` : ''}}
                                                                        </div>
                                                                        <div class="mt-2 pt-1.5 border-t flex items-center justify-between gap-1" style="border-color: var(--border-muted);">
                                                                            <button onclick="copySteps(this, '${{o.id}}')" class="min-h-[30px] px-2 py-1 rounded text-[11px] font-semibold border hover:opacity-80 cursor-pointer" style="background-color: var(--btn-default-bg); border-color: var(--border-default); color: var(--fg-default);">
                                                                                Copy
                                                                            </button>
                                                                            <a href="${{o.url}}" target="_blank" class="min-h-[30px] px-2.5 py-1 rounded text-[11px] font-bold border transition flex items-center gap-1" style="background-color: ${{isLive ? 'var(--btn-primary-bg)' : 'var(--btn-default-bg)'}}; color: ${{isLive ? '#ffffff' : 'var(--fg-default)'}}; border-color: ${{isLive ? 'transparent' : 'var(--border-default)'}};">
                                                                                <span>${{isLive ? 'Claim' : 'Archive'}}</span>
                                                                                <svg class="w-3 h-3" viewBox="0 0 16 16" fill="currentColor"><path d="M3.75 2h3.5a.75.75 0 0 1 0 1.5h-3.5a.25.25 0 0 0-.25.25v8.5c0 .138.112.25.25.25h8.5a.25.25 0 0 0 .25-.25v-3.5a.75.75 0 0 1 1.5 0v3.5A1.75 1.75 0 0 1 12.25 14h-8.5A1.75 1.75 0 0 1 2 12.25v-8.5C2 2.784 2.784 2 3.75 2Zm6.5.75a.75.75 0 0 1 .75-.75h3.5a.75.75 0 0 1 .75.75v3.5a.75.75 0 0 1-1.5 0V4.56L9.53 8.78a.75.75 0 0 1-1.06-1.06l4.22-4.22H11a.75.75 0 0 1-.75-.75Z"></path></svg>
                                                                            </a>
                                                                        </div>
                                                                    </div>
                                                                `;
                                                            }}).join('')}}
                                                        </div>
                                                    `}}
                                                </div>
                                            `;
                                        }}).join('')}}
                                    </div>
                                `;
                            }}).join('')}}
                        </div>
                    </div>
                `;
            }}
            initCardTilt();
        }}

        function onStatusFilterChange() {{
            const statusSelect = document.getElementById('statusFilter');
            if (statusSelect) {{
                if (statusSelect.value === 'history' && currentCategory !== 'History') {{
                    currentCategory = 'History';
                    updateCatPills();
                }} else if (statusSelect.value !== 'history' && currentCategory === 'History') {{
                    currentCategory = 'All';
                    updateCatPills();
                }}
            }}
            syncUrlParams();
            renderCards();
        }}

        function filterCategory(cat) {{
            currentCategory = cat;
            const statusSelect = document.getElementById('statusFilter');
            if (statusSelect) {{
                if (cat === 'History') {{
                    statusSelect.value = 'history';
                }} else if (statusSelect.value === 'history') {{
                    statusSelect.value = 'all';
                }}
            }}
            updateCatPills();
            syncUrlParams();
            renderCards();
        }}

        function updateCatPills() {{
            document.querySelectorAll('.cat-pill').forEach(btn => {{
                if (btn.getAttribute('data-cat') === currentCategory) {{
                    btn.style.backgroundColor = 'var(--accent-emphasis)';
                    btn.style.color = '#ffffff';
                    btn.style.borderColor = 'transparent';
                }} else {{
                    btn.style.backgroundColor = 'var(--canvas-default)';
                    btn.style.color = 'var(--fg-muted)';
                    btn.style.borderColor = 'var(--border-default)';
                }}
            }});
        }}

        // Industry Tech Radar News Renderer
        function filterNewsCategory(cat) {{
            currentNewsCategory = cat;
            document.querySelectorAll('.news-cat-pill').forEach(btn => {{
                if (btn.getAttribute('data-cat') === currentNewsCategory) {{
                    btn.style.backgroundColor = 'var(--accent-emphasis)';
                    btn.style.color = '#ffffff';
                    btn.style.borderColor = 'transparent';
                }} else {{
                    btn.style.backgroundColor = 'var(--canvas-default)';
                    btn.style.color = 'var(--fg-muted)';
                    btn.style.borderColor = 'var(--border-default)';
                }}
            }});
            renderNews();
        }}

        function renderNews() {{
            const grid = document.getElementById('newsGrid');
            const cat = currentNewsCategory;
            const company = document.getElementById('newsCompanySelect').value;
            const sortMode = document.getElementById('newsSortSelect').value;
            const search = currentNewsSearch.toLowerCase().trim();
            const matchBadge = document.getElementById('newsSearchMatchesBadge');

            let filtered = newsData.filter(item => {{
                // Category
                if (cat !== 'All' && item.category !== cat) return false;
                // Company
                if (company !== 'All' && item.company !== company) return false;
                // Search
                if (search !== '') {{
                    const haystack = (item.title + ' ' + item.summary + ' ' + item.company + ' ' + item.category + ' ' + (item.impact_badge || '') + ' ' + item.source_domain).toLowerCase();
                    if (!haystack.includes(search)) return false;
                }}
                return true;
            }});

            // Sort
            filtered.sort((a, b) => {{
                if (sortMode === 'date-desc') return b.published_date.localeCompare(a.published_date);
                if (sortMode === 'date-asc') return a.published_date.localeCompare(b.published_date);
                if (sortMode === 'company-asc') return a.company.localeCompare(b.company);
                return 0;
            }});

            document.getElementById('newsResultsCount').textContent = `Showing ${{filtered.length}} of ${{newsData.length}} verified dispatches`;
            
            if (currentNewsSearch.trim() !== '') {{
                matchBadge.textContent = `${{filtered.length}} found`;
                matchBadge.classList.remove('hidden');
            }} else {{
                matchBadge.classList.add('hidden');
            }}

            if (filtered.length === 0) {{
                grid.innerHTML = `
                    <div class="col-span-full py-16 text-center border rounded-xl" style="background-color: var(--canvas-subtle); border-color: var(--border-default);">
                        <svg class="mx-auto w-10 h-10 mb-3" style="color: var(--fg-muted);" viewBox="0 0 16 16" fill="currentColor">
                            <path d="M1.5 8a6.5 6.5 0 1 1 13 0 6.5 6.5 0 0 1-13 0ZM8 0a8 8 0 1 0 0 16A8 8 0 0 0 8 0ZM5 5a1 1 0 0 0 0 2 1 1 0 0 0 0-2Zm6 0a1 1 0 1 0 0 2 1 1 0 0 0 0-2Zm-7.465 5.5a.75.75 0 0 1 1.05-.14 4.5 4.5 0 0 0 6.83 0 .75.75 0 1 1 1.17.94 6 6 0 0 1-9.11 0 .75.75 0 0 1 .06-1Z"></path>
                        </svg>
                        <h3 class="text-base font-bold" style="color: var(--fg-default);">No matching dispatches found</h3>
                        <p class="text-xs mt-1" style="color: var(--fg-muted);">Try selecting another company, topic, or resetting search.</p>
                        <button onclick="clearNewsSearch()" class="mt-3 text-xs font-semibold px-3 py-1.5 rounded-md border cursor-pointer" style="background-color: var(--btn-default-bg); border-color: var(--border-default); color: var(--accent-fg);">Reset Search</button>
                    </div>
                `;
                return;
            }}

            grid.innerHTML = filtered.map(item => {{
                const brandColor = getPlatformColor(item.company);
                const brandIcon = getPlatformIconSvg(item.company);
                const impactBadge = item.impact_badge ? `
                    <span class="text-xs font-mono font-medium px-2 py-0.5 rounded border" style="background-color: var(--accent-subtle); border-color: var(--accent-fg); color: var(--accent-fg);">
                        ${{item.impact_badge}}
                    </span>
                ` : '';

                return `
                    <div class="primer-card p-4 sm:p-5 rounded-xl flex flex-col justify-between">
                        <div>
                            <div class="flex items-center justify-between gap-2 mb-2.5">
                                <span class="text-xs font-bold px-2.5 py-1 rounded-lg flex items-center gap-2 max-w-[70%]" style="background-color: var(--canvas-inset); color: ${{brandColor}}; border: 1px solid var(--border-default);">
                                    <span class="flex items-center justify-center flex-shrink-0">${{brandIcon}}</span>
                                    <span class="truncate">${{item.company}}</span>
                                </span>
                                <span class="text-xs tabular-nums font-medium flex-shrink-0" style="color: var(--fg-muted);">
                                    ${{item.published_date}}
                                </span>
                            </div>

                            <div class="flex items-center gap-1.5 mb-2 flex-wrap">
                                ${{impactBadge}}
                                <span class="text-[11px] sm:text-xs px-2 py-0.5 rounded border font-medium" style="background-color: var(--canvas-inset); border-color: var(--border-default); color: var(--fg-subtle);">
                                    ${{item.category}}
                                </span>
                            </div>

                            <h3 class="text-sm sm:text-base font-bold leading-snug hover:underline cursor-pointer text-balance" style="color: var(--fg-default);" onclick="window.open('${{item.url}}', '_blank')">
                                ${{item.title}}
                            </h3>

                            <p class="text-xs mt-2.5 leading-relaxed text-pretty" style="color: var(--fg-muted);">
                                ${{item.summary}}
                            </p>
                        </div>

                        <div class="mt-4 pt-3 border-t flex items-center justify-between text-xs" style="border-color: var(--border-muted);">
                            <div class="flex items-center gap-1.5 text-xs font-medium min-w-0" style="color: var(--success-fg);" title="Domain verified on official enterprise whitelist">
                                <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor" class="flex-shrink-0">
                                    <path d="M13.78 4.22a.75.75 0 0 1 0 1.06l-7.25 7.25a.75.75 0 0 1-1.06 0L2.22 9.28a.751.751 0 0 1 .018-1.042.751.751 0 0 1 1.042-.018L6 10.94l6.72-6.72a.75.75 0 0 1 1.06 0Z"></path>
                                </svg>
                                <span class="font-medium text-xs truncate max-w-[120px] sm:max-w-[160px]">${{item.source_domain}}</span>
                            </div>
                            <a href="${{item.url}}" target="_blank" class="min-h-[40px] px-3.5 py-2 rounded-lg text-xs font-semibold transition hover:opacity-80 active:scale-[0.98] border flex items-center gap-1.5 flex-shrink-0 cursor-pointer" style="background-color: var(--btn-default-bg); border-color: var(--border-default); color: var(--accent-fg);">
                                <span>Official Post</span>
                                <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor"><path d="M3.75 2h3.5a.75.75 0 0 1 0 1.5h-3.5a.25.25 0 0 0-.25.25v8.5c0 .138.112.25.25.25h8.5a.25.25 0 0 0 .25-.25v-3.5a.75.75 0 0 1 1.5 0v3.5A1.75 1.75 0 0 1 12.25 14h-8.5A1.75 1.75 0 0 1 2 12.25v-8.5C2 2.784 2.784 2 3.75 2Zm6.5.75a.75.75 0 0 1 .75-.75h3.5a.75.75 0 0 1 .75.75v3.5a.75.75 0 0 1-1.5 0V4.56L9.53 8.78a.75.75 0 0 1-1.06-1.06l4.22-4.22H11a.75.75 0 0 1-.75-.75Z"></path></svg>
                            </a>
                        </div>
                    </div>
                `;
            }}).join('');
            initCardTilt();
        }}

        // Dynamic Pointer Tilt & Hover Elevation Physics (Desktop fine pointers only)
        function initCardTilt() {{
            if (window.matchMedia('(hover: hover) and (pointer: fine)').matches) {{
                document.querySelectorAll('.primer-card').forEach(card => {{
                    if (card.getAttribute('data-tilt-attached')) return;
                    card.setAttribute('data-tilt-attached', 'true');
                    card.addEventListener('mousemove', (e) => {{
                        const rect = card.getBoundingClientRect();
                        const x = e.clientX - rect.left;
                        const y = e.clientY - rect.top;
                        const centerX = rect.width / 2;
                        const centerY = rect.height / 2;
                        const rotateX = ((y - centerY) / centerY) * -3;
                        const rotateY = ((x - centerX) / centerX) * 3;
                        card.style.transform = `perspective(1000px) rotateX(${{rotateX.toFixed(2)}}deg) rotateY(${{rotateY.toFixed(2)}}deg) translateY(-3px)`;
                    }});
                    card.addEventListener('mouseleave', () => {{
                        card.style.transform = '';
                    }});
                }});
            }}
        }}

        // Keyboard Shortcuts
        document.addEventListener('keydown', (e) => {{
            const isEditing = ['INPUT', 'SELECT', 'TEXTAREA'].includes(document.activeElement.tagName);
            if (e.key === 'Escape') {{
                if (document.activeElement.id === 'searchInput') {{
                    clearSearch();
                    document.getElementById('searchInput').blur();
                }} else if (document.activeElement.id === 'newsSearchInput') {{
                    clearNewsSearch();
                    document.getElementById('newsSearchInput').blur();
                }}
                return;
            }}
            if (isEditing) return;

            if (e.key === '1') {{
                e.preventDefault();
                switchMainTab('vouchers');
            }}
            if (e.key === '2') {{
                e.preventDefault();
                switchMainTab('news');
            }}
            if (e.key === '/') {{
                e.preventDefault();
                if (currentMainTab === 'news') {{
                    document.getElementById('newsSearchInput').focus();
                }} else {{
                    document.getElementById('searchInput').focus();
                }}
            }}
            if (e.key === 'v' || e.key === 'V') {{
                if (currentMainTab === 'vouchers') {{
                    const views = ['grid', 'list', 'timeline', 'matrix'];
                    const nextIdx = (views.indexOf(currentLayout) + 1) % views.length;
                    setLayoutView(views[nextIdx]);
                }}
            }}
            if (e.key === 't' || e.key === 'T') {{
                toggleTheme();
            }}
        }});

        // Input Listeners
        document.getElementById('searchInput').addEventListener('input', (e) => {{
            currentSearch = e.target.value;
            const clearBtn = document.getElementById('clearSearchBtn');
            if (currentSearch.trim() !== '') clearBtn.classList.remove('hidden');
            else clearBtn.classList.add('hidden');
            syncUrlParams();
            renderCards();
        }});

        document.getElementById('newsSearchInput').addEventListener('input', (e) => {{
            currentNewsSearch = e.target.value;
            const clearBtn = document.getElementById('clearNewsSearchBtn');
            if (currentNewsSearch.trim() !== '') clearBtn.classList.remove('hidden');
            else clearBtn.classList.add('hidden');
            renderNews();
        }});

        // Boot
        initTheme();
        renderCards();
    </script>
</body>
</html>
"""

def build_all():
    data = load_offers()
    news_data = load_news()
    
    # 1. Write README.md
    readme_content = generate_readme(data, news_data)
    with open(README_FILE, "w", encoding="utf-8") as f:
        f.write(readme_content)
    print(f"[OK] Successfully built {README_FILE}")
    
    # 2. Write docs/index.html
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    html_content = generate_web_dashboard(data, news_data)
    with open(DOCS_HTML, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[OK] Successfully built {DOCS_HTML}")

if __name__ == "__main__":
    build_all()
