"""
Builder module for CertPulse.
Compiles data/offers.json into:
1. Production-grade GitHub README.md with executive Bento stats, verified voucher tables, and inspection badges.
2. docs/index.html - Static interactive web dashboard for GitHub Pages with live search and status filters.
"""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "offers.json"
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

def generate_readme(data: Dict[str, Any]) -> str:
    offers: List[Dict[str, Any]] = data.get("offers", [])
    active_offers = [o for o in offers if o.get("status") == "Active"]
    closed_offers = [o for o in offers if o.get("status") != "Active"]
    
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
    lines.append(f"> **Automated, 100% free, and self-updating repository** tracking verified 100% free certification exam vouchers, accredited micro-credentials, and continuing education credits across AWS, Azure, Google Cloud, Cisco, ISC2, Oracle, Linux Foundation, Snowflake, and GitHub.")
    lines.append("")
    lines.append("![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg) ")
    lines.append(f"![Active Vouchers](https://img.shields.io/badge/Active%20Offers-{len(active_offers)}-success.svg) ")
    lines.append(f"![Total Savings](https://img.shields.io/badge/Total%20Value%20Saved-%24{total_savings}%20USD-gold.svg) ")
    lines.append("![Deep Inspection](https://img.shields.io/badge/Inspection-Liveness%20%26%20Soft404%20Checked-brightgreen.svg) ")
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
        lines.append("| Provider | Certification & Program | Type | Value (USD) | Status | Claim Link |")
        lines.append("| :--- | :--- | :--- | :---: | :---: | :--- |")
        for o in cat_offers:
            provider = o.get("platform")
            cert = o.get("certification_name")
            val = f"${o.get('value_usd')}" if o.get('value_usd') else "Free"
            otype = o.get("offer_type")
            status_text = STATUS_BADGES.get(o.get("status", "Active"), "🟢 Active")
            url = o.get("url")
            lines.append(f"| **{provider}** | {cert} | `{otype}` | {val} | {status_text} | [**Claim Offer**]({url}) |")
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
    lines.append("    A[Public RSS & Community Feeds] -->|Scheduled Cron every 6h| B[GitHub Actions Runner]")
    lines.append("    B -->|Inspect Liveness & Soft 404s| C[Deep Inspector Engine]")
    lines.append("    C -->|Classify & Flag Status| D[data/offers.json]")
    lines.append("    D -->|Jinja2 Compiler| E[README.md]")
    lines.append("    D -->|Static Deploy| F[GitHub Pages Dashboard]")
    lines.append("```")
    lines.append("")
    lines.append("1. **Zero External Servers**: Runs directly on GitHub Actions (`ubuntu-latest`).")
    lines.append("2. **Deep Inspection Guardian**: The crawler not only checks HTTP status codes (404/500) but reads page HTML to spot 'Registrations Closed' or 'All vouchers claimed' notices.")
    lines.append("3. **Zero Git Noise**: Only commits changes to `README.md` and `data/offers.json` when actual updates are detected.")
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

def generate_web_dashboard(data: Dict[str, Any]) -> str:
    """Generates an authentic GitHub Primer web dashboard with Dark and Light Contrast modes and dual presentation views."""
    offers = data.get("offers", [])
    active_offers = [o for o in offers if o.get("status") == "Active"]
    total_savings = sum((o.get("value_usd") or 0) for o in active_offers)
    last_updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    offers_json_str = json.dumps(offers)
    
    return f"""<!DOCTYPE html>
<html lang="en" data-theme="dark" data-color-mode="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CertPulse | GitHub Primer Free Certification Tracker</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        /* GitHub Primer Dual Theme System: Dark & Light Contrast */
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
            --card-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
            --card-shadow-hover: 0 6px 20px rgba(1, 4, 9, 0.6);
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
            --card-shadow: 0 1px 3px rgba(36, 41, 47, 0.15);
            --card-shadow-hover: 0 4px 14px rgba(36, 41, 47, 0.25);
        }}

        body {{
            background-color: var(--canvas-default);
            color: var(--fg-default);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif;
            transition: background-color 0.2s ease, color 0.2s ease;
        }}

        .primer-card {{
            background-color: var(--canvas-subtle);
            border: 1px solid var(--border-default);
            box-shadow: var(--card-shadow);
            transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), 
                        box-shadow 0.2s cubic-bezier(0.16, 1, 0.3, 1), 
                        border-color 0.2s ease;
        }}
        .primer-card:hover {{
            transform: translateY(-2px);
            box-shadow: var(--card-shadow-hover);
            border-color: var(--accent-fg);
        }}

        .issue-row {{
            background-color: var(--canvas-default);
            border-bottom: 1px solid var(--border-muted);
            transition: background-color 0.15s ease;
        }}
        .issue-row:hover {{
            background-color: var(--canvas-subtle);
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
    </style>
</head>
<body class="min-h-screen flex flex-col antialiased selection:bg-blue-500/20">

    <!-- GitHub Top Navigation Bar -->
    <header class="border-b sticky top-0 z-40 backdrop-blur-md" style="background-color: var(--canvas-subtle); border-color: var(--border-default);">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
            
            <!-- Left: Brand Breadcrumb -->
            <div class="flex items-center gap-3">
                <a href="https://github.com/Athish2002/free-certification-tracker" target="_blank" class="hover:opacity-80 transition" aria-label="GitHub Repository">
                    <svg height="28" viewBox="0 0 16 16" width="28" style="fill: var(--fg-default);">
                        <path d="M8 0c4.42 0 8 3.58 8 8a8.013 8.013 0 0 1-5.45 7.59c-.4.08-.55-.17-.55-.38 0-.27.01-1.13.01-2.2 0-.75-.25-1.23-.54-1.48 1.78-.2 3.65-.88 3.65-3.95 0-.88-.31-1.59-.82-2.15.08-.2.36-1.02-.08-2.12 0 0-.67-.22-2.2.82-.64-.18-1.32-.27-2-.27-.68 0-1.36.09-2 .27-1.53-1.03-2.2-.82-2.2-.82-.44 1.1-.16 1.92-.08 2.12-.51.56-.82 1.28-.82 2.15 0 3.06 1.86 3.75 3.64 3.95-.23.2-.44.55-.51 1.07-.46.21-1.61.55-2.33-.66-.15-.24-.6-.83-1.23-.82-.67.01-.27.38.01.53.34.19.73.9.82 1.13.16.45.68 1.31 2.69.94 0 .67.01 1.3.01 1.49 0 .21-.15.45-.55.38A7.995 7.995 0 0 1 0 8c0-4.42 3.58-8 8-8Z"></path>
                    </svg>
                </a>
                <div class="flex items-center gap-2 text-sm font-semibold">
                    <a href="https://github.com/Athish2002" target="_blank" class="hover:underline" style="color: var(--accent-fg);">Athish2002</a>
                    <span style="color: var(--fg-muted);">/</span>
                    <a href="https://github.com/Athish2002/free-certification-tracker" target="_blank" class="hover:underline flex items-center gap-1.5" style="color: var(--fg-default);">
                        free-certification-tracker
                    </a>
                    <span class="text-xs px-2 py-0.5 rounded-full font-medium" style="background-color: var(--canvas-inset); color: var(--fg-muted); border: 1px solid var(--border-default);">Public</span>
                </div>
            </div>

            <!-- Right: Controls, Dual Presentation Switcher & Dark/Light Toggle -->
            <div class="flex items-center gap-2">
                <!-- Live Pipeline Badge -->
                <div class="hidden lg:flex items-center gap-1.5 text-xs font-mono px-2.5 py-1 rounded-md" style="background-color: var(--canvas-inset); border: 1px solid var(--border-default); color: var(--fg-muted);">
                    <span class="w-2 h-2 rounded-full animate-pulse" style="background-color: var(--success-fg);"></span>
                    <span>Cron: 4h Sync</span>
                </div>

                <!-- Dual Presentation Layout Switcher (Grid vs Issues Table) -->
                <div class="flex items-center rounded-md border p-0.5" style="background-color: var(--canvas-inset); border-color: var(--border-default);">
                    <button id="viewBtnGrid" onclick="setLayoutView('grid')" title="Bento Grid View (v)" class="px-2.5 py-1 rounded text-xs font-semibold flex items-center gap-1.5 transition" style="background-color: var(--btn-default-bg); color: var(--fg-default);">
                        <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                            <path d="M1 2.5A1.5 1.5 0 0 1 2.5 1h3A1.5 1.5 0 0 1 7 2.5v3A1.5 1.5 0 0 1 5.5 7h-3A1.5 1.5 0 0 1 1 5.5v-3Zm8 0A1.5 1.5 0 0 1 10.5 1h3A1.5 1.5 0 0 1 15 2.5v3A1.5 1.5 0 0 1 13.5 7h-3A1.5 1.5 0 0 1 9 5.5v-3Zm-8 8A1.5 1.5 0 0 1 2.5 9h3A1.5 1.5 0 0 1 7 10.5v3A1.5 1.5 0 0 1 5.5 15h-3A1.5 1.5 0 0 1 1 13.5v-3Zm8 0A1.5 1.5 0 0 1 10.5 9h3a1.5 1.5 0 0 1 1.5 1.5v3a1.5 1.5 0 0 1-1.5 1.5h-3A1.5 1.5 0 0 1 9 13.5v-3Z"></path>
                        </svg>
                        <span class="hidden sm:inline">Bento Grid</span>
                    </button>
                    <button id="viewBtnList" onclick="setLayoutView('list')" title="Issues Table View (v)" class="px-2.5 py-1 rounded text-xs font-medium flex items-center gap-1.5 transition" style="color: var(--fg-muted);">
                        <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                            <path d="M2 3.75C2 3.336 2.336 3 2.75 3h10.5a.75.75 0 0 1 0 1.5H2.75A.75.75 0 0 1 2 3.75Zm0 4.25c0-.414.336-.75.75-.75h10.5a.75.75 0 0 1 0 1.5H2.75A.75.75 0 0 1 2 8Zm0 4.25c0-.414.336-.75.75-.75h10.5a.75.75 0 0 1 0 1.5H2.75a.75.75 0 0 1-.75-.75Z"></path>
                        </svg>
                        <span class="hidden sm:inline">Issues List</span>
                    </button>
                </div>

                <!-- Dark / Light Contrast Mode Toggle Button -->
                <button onclick="toggleTheme()" id="themeToggleBtn" title="Toggle Dark / Light Contrast Mode (t)" class="p-2 rounded-md border text-sm transition flex items-center justify-center hover:opacity-80" style="background-color: var(--btn-default-bg); border-color: var(--border-default); color: var(--fg-default);">
                    <!-- Sun Icon (shown when in dark mode) -->
                    <svg id="themeIconSun" class="w-4 h-4 hidden" viewBox="0 0 16 16" fill="currentColor">
                        <path d="M8 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM8 0a.75.75 0 0 1 .75.75v1.5a.75.75 0 0 1-1.5 0V.75A.75.75 0 0 1 8 0Zm0 13a.75.75 0 0 1 .75.75v1.5a.75.75 0 0 1-1.5 0v-1.5A.75.75 0 0 1 8 13ZM2.343 2.343a.75.75 0 0 1 1.061 0l1.06 1.061a.75.75 0 0 1-1.06 1.06l-1.06-1.06a.75.75 0 0 1 0-1.061Zm9.193 9.193a.75.75 0 0 1 1.06 0l1.061 1.06a.75.75 0 0 1-1.06 1.061l-1.061-1.06a.75.75 0 0 1 0-1.061ZM0 8a.75.75 0 0 1 .75-.75h1.5a.75.75 0 0 1 0 1.5H.75A.75.75 0 0 1 0 8Zm13 0a.75.75 0 0 1 .75-.75h1.5a.75.75 0 0 1 0 1.5h-1.5A.75.75 0 0 1 13 8ZM2.343 13.657a.75.75 0 0 1 0-1.06l1.06-1.061a.75.75 0 1 1 1.061 1.06l-1.06 1.061a.75.75 0 0 1-1.061 0Zm9.193-9.193a.75.75 0 0 1 0-1.06l1.061-1.061a.75.75 0 0 1 1.06 1.06l-1.06 1.061a.75.75 0 0 1-1.061 0Z"></path>
                    </svg>
                    <!-- Moon Icon (shown when in light mode) -->
                    <svg id="themeIconMoon" class="w-4 h-4 hidden" viewBox="0 0 16 16" fill="currentColor">
                        <path d="M9.598 1.591a.749.749 0 0 1 .785-.175 7.001 7.001 0 1 1-8.967 8.967.75.75 0 0 1 .961-.96 5.5 5.5 0 0 0 7.046-7.046.75.75 0 0 1 .175-.786Zm1.616 1.945a7 7 0 0 1-7.678 7.678 5.499 5.499 0 1 0 7.678-7.678Z"></path>
                    </svg>
                </button>

                <!-- GitHub Star CTA -->
                <a href="https://github.com/Athish2002/free-certification-tracker" target="_blank" class="text-xs font-semibold px-3 py-1.5 rounded-md border flex items-center gap-1.5 transition hover:opacity-90" style="background-color: var(--btn-default-bg); border-color: var(--border-default); color: var(--fg-default);">
                    <svg height="14" viewBox="0 0 16 16" width="14" fill="currentColor">
                        <path d="M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.751.751 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.751.751 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Z"></path>
                    </svg>
                    <span class="hidden sm:inline">Star</span>
                </a>
            </div>
        </div>
    </header>

    <!-- Main Container -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1 w-full">
        
        <!-- Hero Bento Grid (Primer Style) -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
            <!-- Bento 1: Value Saved -->
            <div class="p-5 rounded-lg border primer-card">
                <div class="flex items-center justify-between">
                    <span class="text-xs font-semibold uppercase tracking-wider" style="color: var(--fg-muted);">Total Value Available</span>
                    <span class="p-1.5 rounded-md" style="background-color: var(--success-subtle); color: var(--success-fg); border: 1px solid var(--success-fg);">
                        <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                            <path d="M8.75.75a.75.75 0 0 0-1.5 0V2h-.984c-.983 0-1.9.362-2.589 1.026C3.003 3.673 2.6 4.595 2.6 5.64c0 .91.308 1.688.886 2.26.567.562 1.34.942 2.264 1.192l.67.182c.76.205 1.25.437 1.53.685.26.23.35.474.35.743 0 .365-.154.67-.44.89-.3.23-.743.358-1.36.358-.603 0-1.05-.122-1.38-.342a1.29 1.29 0 0 1-.53-.872.75.75 0 0 0-1.49.172c.153.998.666 1.734 1.45 2.198.647.383 1.488.582 2.47.604v1.18a.75.75 0 0 0 1.5 0v-1.19c.983-.024 1.834-.34 2.483-.93.673-.613 1.017-1.472 1.017-2.46 0-.895-.316-1.66-.908-2.23-.58-.558-1.38-.93-2.316-1.182l-.645-.175c-.75-.204-1.223-.424-1.48-.656-.239-.214-.34-.442-.34-.707 0-.323.14-.597.412-.792.292-.21.72-.32 1.288-.32.535 0 .944.103 1.222.288.29.193.473.488.547.88a.75.75 0 0 0 1.478-.276c-.16-.862-.573-1.543-1.25-1.986A4.323 4.323 0 0 0 8.75 3.2V.75Z"></path>
                        </svg>
                    </span>
                </div>
                <div class="text-3xl font-extrabold mt-2 font-mono tracking-tight" style="color: var(--fg-default);">
                    ${total_savings:,} <span class="text-sm font-normal" style="color: var(--fg-muted);">USD</span>
                </div>
                <p class="text-xs mt-2" style="color: var(--fg-muted);">100% free proctored exams and official accredited credentials.</p>
            </div>

            <!-- Bento 2: Active Opportunities -->
            <div class="p-5 rounded-lg border primer-card">
                <div class="flex items-center justify-between">
                    <span class="text-xs font-semibold uppercase tracking-wider" style="color: var(--fg-muted);">Verified Opportunities</span>
                    <span class="p-1.5 rounded-md" style="background-color: var(--accent-subtle); color: var(--accent-fg); border: 1px solid var(--accent-fg);">
                        <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                            <path d="M13.78 4.22a.75.75 0 0 1 0 1.06l-7.25 7.25a.75.75 0 0 1-1.06 0L2.22 9.28a.751.751 0 0 1 .018-1.042.751.751 0 0 1 1.042-.018L6 10.94l6.72-6.72a.75.75 0 0 1 1.06 0Z"></path>
                        </svg>
                    </span>
                </div>
                <div class="text-3xl font-extrabold mt-2 font-mono tracking-tight" style="color: var(--success-fg);">
                    {len(active_offers)} <span class="text-sm font-normal" style="color: var(--fg-muted);">Active / {len(offers)} Total</span>
                </div>
                <p class="text-xs mt-2" style="color: var(--fg-muted);">Audited across Azure, AWS, GCP, Cisco, ISC2, Oracle, & Linux Foundation.</p>
            </div>

            <!-- Bento 3: Self-Healing Inspection -->
            <div class="p-5 rounded-lg border primer-card">
                <div class="flex items-center justify-between">
                    <span class="text-xs font-semibold uppercase tracking-wider" style="color: var(--fg-muted);">Self-Healing Invariant Bot</span>
                    <span class="p-1.5 rounded-md" style="background-color: var(--attention-subtle); color: var(--attention-fg); border: 1px solid var(--attention-fg);">
                        <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                            <path d="M1.705 8.005a.75.75 0 0 1 .834.656 5.5 5.5 0 0 0 9.592 2.97l-1.204-1.204a.25.25 0 0 1 .177-.427h3.646a.25.25 0 0 1 .25.25v3.646a.25.25 0 0 1-.427.177l-1.38-1.38A7 7 0 0 1 1.05 8.84a.75.75 0 0 1 .656-.834ZM8 2.5a5.487 5.487 0 0 0-4.131 1.869l1.204 1.204A.25.25 0 0 1 4.896 6H1.25A.25.25 0 0 1 1 5.75V2.104a.25.25 0 0 1 .427-.177l1.38 1.38A7 7 0 0 1 14.95 7.16a.75.75 0 1 1-1.49.178A5.5 5.5 0 0 0 8 2.5Z"></path>
                        </svg>
                    </span>
                </div>
                <div class="text-3xl font-extrabold mt-2 font-mono tracking-tight" style="color: var(--accent-fg);">
                    Every 4 Hours <span class="text-sm font-normal" style="color: var(--fg-muted);">Cron</span>
                </div>
                <p class="text-xs mt-2" style="color: var(--fg-muted);">Deep HTTP inspection: auto-detects soft 404s, silent reroutes, & closed forms.</p>
            </div>
        </div>

        <!-- Filter, Search, and Sort Controls (GitHub Primer Standard) -->
        <div class="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3 mb-4 p-3 rounded-lg border" style="background-color: var(--canvas-subtle); border-color: var(--border-default);">
            
            <!-- Left: Instant Search with / Hotkey and GitHub Query Syntax -->
            <div class="relative flex-1 max-w-md">
                <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none" style="color: var(--fg-muted);">
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                        <path d="M10.68 11.74a6 6 0 0 1-7.922-8.982 6 6 0 0 1 8.982 7.922l3.04 3.04a.749.749 0 0 1-.326 1.275.749.749 0 0 1-.734-.215ZM11.5 7a4.5 4.5 0 1 0-9 0 4.5 4.5 0 0 0 9 0Z"></path>
                    </svg>
                </div>
                <input type="text" id="searchInput" placeholder="Filter vouchers or type 'is:active', 'cat:Cloud'..." 
                       class="w-full pl-9 pr-14 py-1.5 text-sm rounded-md border focus:outline-none focus:ring-2 focus:ring-blue-500 transition"
                       style="background-color: var(--canvas-default); border-color: var(--border-default); color: var(--fg-default);">
                <div class="absolute inset-y-0 right-0 pr-2 flex items-center gap-1">
                    <button id="clearSearchBtn" onclick="clearSearch()" class="hidden p-1 rounded text-xs hover:opacity-80" style="color: var(--fg-muted);" title="Clear search">✕</button>
                    <kbd class="text-[10px] font-mono px-1.5 py-0.5 rounded border pointer-events-none" style="background-color: var(--canvas-subtle); border-color: var(--border-default); color: var(--fg-muted);">/</kbd>
                </div>
            </div>

            <!-- Middle: Category SubNav Filters with Primer CounterLabels -->
            <div class="flex gap-1.5 overflow-x-auto pb-1 lg:pb-0" id="filterPills">
                <button onclick="filterCategory('All')" class="cat-pill px-3 py-1 rounded-md text-xs font-semibold whitespace-nowrap transition flex items-center gap-1.5" style="background-color: var(--accent-emphasis); color: #ffffff;" data-cat="All">
                    <span>All</span>
                    <span class="text-[10px] px-1.5 py-0.2 rounded-full font-mono bg-white/20">{len(offers)}</span>
                </button>
                <button onclick="filterCategory('Cloud')" class="cat-pill px-3 py-1 rounded-md text-xs font-medium whitespace-nowrap border transition hover:opacity-80 flex items-center gap-1.5" style="background-color: var(--canvas-default); border-color: var(--border-default); color: var(--fg-muted);" data-cat="Cloud">
                    <span>Cloud</span>
                    <span class="text-[10px] px-1.5 py-0.2 rounded-full font-mono" style="background-color: var(--canvas-inset);">5</span>
                </button>
                <button onclick="filterCategory('Security')" class="cat-pill px-3 py-1 rounded-md text-xs font-medium whitespace-nowrap border transition hover:opacity-80 flex items-center gap-1.5" style="background-color: var(--canvas-default); border-color: var(--border-default); color: var(--fg-muted);" data-cat="Security">
                    <span>Security</span>
                    <span class="text-[10px] px-1.5 py-0.2 rounded-full font-mono" style="background-color: var(--canvas-inset);">4</span>
                </button>
                <button onclick="filterCategory('DevOps')" class="cat-pill px-3 py-1 rounded-md text-xs font-medium whitespace-nowrap border transition hover:opacity-80 flex items-center gap-1.5" style="background-color: var(--canvas-default); border-color: var(--border-default); color: var(--fg-muted);" data-cat="DevOps">
                    <span>DevOps</span>
                    <span class="text-[10px] px-1.5 py-0.2 rounded-full font-mono" style="background-color: var(--canvas-inset);">3</span>
                </button>
                <button onclick="filterCategory('AI & Data')" class="cat-pill px-3 py-1 rounded-md text-xs font-medium whitespace-nowrap border transition hover:opacity-80 flex items-center gap-1.5" style="background-color: var(--canvas-default); border-color: var(--border-default); color: var(--fg-muted);" data-cat="AI & Data">
                    <span>AI & Data</span>
                    <span class="text-[10px] px-1.5 py-0.2 rounded-full font-mono" style="background-color: var(--canvas-inset);">3</span>
                </button>
                <button onclick="filterCategory('Networking')" class="cat-pill px-3 py-1 rounded-md text-xs font-medium whitespace-nowrap border transition hover:opacity-80 flex items-center gap-1.5" style="background-color: var(--canvas-default); border-color: var(--border-default); color: var(--fg-muted);" data-cat="Networking">
                    <span>Networking</span>
                    <span class="text-[10px] px-1.5 py-0.2 rounded-full font-mono" style="background-color: var(--canvas-inset);">1</span>
                </button>
            </div>

            <!-- Right: Sort, Status, and Share / Export Menu -->
            <div class="flex items-center gap-2">
                <select id="sortSelect" onchange="renderCards()" class="text-xs py-1.5 px-2.5 rounded-md border font-medium focus:outline-none" style="background-color: var(--canvas-default); border-color: var(--border-default); color: var(--fg-default);">
                    <option value="val-desc">Sort: Value (High to Low)</option>
                    <option value="val-asc">Sort: Value (Low to High)</option>
                    <option value="name-asc">Sort: Provider (A to Z)</option>
                </select>
                <select id="statusFilter" onchange="renderCards()" class="text-xs py-1.5 px-2.5 rounded-md border font-medium focus:outline-none" style="background-color: var(--canvas-default); border-color: var(--border-default); color: var(--fg-default);">
                    <option value="active" selected>Status: Active ({len(active_offers)})</option>
                    <option value="all">Status: All ({len(offers)})</option>
                    <option value="closed">Status: Concluded ({len(offers) - len(active_offers)})</option>
                </select>
                <!-- Share Button -->
                <button onclick="copyShareLink()" title="Copy Shareable Link" class="p-1.5 rounded-md border hover:opacity-80 transition flex items-center gap-1 text-xs" style="background-color: var(--btn-default-bg); border-color: var(--border-default); color: var(--fg-default);">
                    <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                        <path d="M13.5 0a2.5 2.5 0 0 0-2.316 3.447L6.082 5.998a2.502 2.502 0 1 0 0 4.004l5.102 2.551a2.5 2.5 0 1 0 .898-1.796L6.98 8.206a2.518 2.518 0 0 0 0-.412l5.102-2.551A2.5 2.5 0 1 0 13.5 0Z"></path>
                    </svg>
                </button>
            </div>
        </div>

        <!-- Quick Filter Tokens Bar -->
        <div class="flex items-center gap-2 mb-4 text-xs overflow-x-auto pb-1">
            <span class="font-semibold uppercase tracking-wider text-[11px]" style="color: var(--fg-subtle);">Quick Tokens:</span>
            <button onclick="appendToken('is:active')" class="px-2 py-0.5 rounded border text-[11px] font-mono hover:opacity-80 transition" style="background-color: var(--canvas-subtle); border-color: var(--border-default); color: var(--accent-fg);">is:active</button>
            <button onclick="appendToken('val:>100')" class="px-2 py-0.5 rounded border text-[11px] font-mono hover:opacity-80 transition" style="background-color: var(--canvas-subtle); border-color: var(--border-default); color: var(--success-fg);">val:&gt;100</button>
            <button onclick="appendToken('cat:Security')" class="px-2 py-0.5 rounded border text-[11px] font-mono hover:opacity-80 transition" style="background-color: var(--canvas-subtle); border-color: var(--border-default); color: var(--fg-muted);">cat:Security</button>
            <button onclick="appendToken('cat:Cloud')" class="px-2 py-0.5 rounded border text-[11px] font-mono hover:opacity-80 transition" style="background-color: var(--canvas-subtle); border-color: var(--border-default); color: var(--fg-muted);">cat:Cloud</button>
            <button onclick="exportFilteredJson()" class="ml-auto px-2 py-0.5 rounded border text-[11px] font-semibold hover:opacity-80 transition flex items-center gap-1" style="background-color: var(--canvas-subtle); border-color: var(--border-default); color: var(--fg-muted);">
                <span>⬇ JSON</span>
            </button>
        </div>

        <!-- Result Status Sub-bar -->
        <div class="flex items-center justify-between text-xs mb-4 px-1" style="color: var(--fg-muted);">
            <div id="resultsCount">Showing {len(active_offers)} of {len(offers)} vouchers</div>
            <div>Audited: <span class="font-mono">{last_updated}</span></div>
        </div>

        <!-- Dual Presentation Container: Bento Cards Grid or GitHub Issues Table -->
        <div id="cardsViewContainer">
            <!-- Grid View -->
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" id="offersGrid"></div>
        </div>

        <div id="listViewContainer" class="hidden">
            <!-- Issues Table View -->
            <div class="rounded-lg border overflow-hidden" style="border-color: var(--border-default);">
                <div class="p-3 border-b flex items-center justify-between text-xs font-semibold" style="background-color: var(--canvas-subtle); border-color: var(--border-default); color: var(--fg-muted);">
                    <div class="flex items-center gap-4">
                        <span class="flex items-center gap-1 text-[var(--fg-default)]">
                            <svg width="14" height="14" viewBox="0 0 16 16" fill="var(--success-fg)"><path d="M8 9.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3Z"></path><path d="M8 0a8 8 0 1 1 0 16A8 8 0 0 1 8 0ZM1.5 8a6.5 6.5 0 1 0 13 0 6.5 6.5 0 0 0-13 0Z"></path></svg>
                            <span id="listOpenCount">{len(active_offers)} Active Offers</span>
                        </span>
                    </div>
                    <div>GitHub Issue Format</div>
                </div>
                <div id="offersTableBody"></div>
            </div>
        </div>

    </main>

    <!-- Footer -->
    <footer class="border-t py-6 mt-12 text-center text-xs" style="background-color: var(--canvas-subtle); border-color: var(--border-default); color: var(--fg-muted);">
        <div class="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-3">
            <div>CertPulse — Open-Source GitHub Primer Autonomous Voucher Engine</div>
            <div class="flex items-center gap-4">
                <a href="https://github.com/Athish2002/free-certification-tracker" target="_blank" class="hover:underline" style="color: var(--accent-fg);">GitHub Repo</a>
                <a href="https://github.com/Athish2002/free-certification-tracker/issues/new/choose" target="_blank" class="hover:underline" style="color: var(--accent-fg);">Submit Voucher</a>
                <a href="https://primer.style" target="_blank" class="hover:underline" style="color: var(--fg-muted);">GitHub Primer</a>
            </div>
        </div>
    </footer>

    <!-- Toast Notification for Micro-Interactions -->
    <div id="toastNotification" class="fixed bottom-5 right-5 z-50 transform translate-y-20 opacity-0 transition-all duration-300 pointer-events-none p-3.5 rounded-lg border shadow-xl flex items-center gap-2.5 text-xs font-semibold" style="background-color: var(--canvas-subtle); border-color: var(--border-default); color: var(--fg-default);">
        <svg class="w-4 h-4 text-emerald-400" viewBox="0 0 16 16" fill="currentColor">
            <path d="M13.78 4.22a.75.75 0 0 1 0 1.06l-7.25 7.25a.75.75 0 0 1-1.06 0L2.22 9.28a.751.751 0 0 1 .018-1.042.751.751 0 0 1 1.042-.018L6 10.94l6.72-6.72a.75.75 0 0 1 1.06 0Z"></path>
        </svg>
        <span id="toastMessage">Action completed</span>
    </div>

    <!-- Application Script -->
    <script>
        const offersData = {offers_json_str};
        let currentCategory = 'All';
        let currentSearch = '';
        let currentLayout = 'grid';

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
            renderCards();
        }}

        function setLayoutView(view, updateUrl = true) {{
            currentLayout = view;
            const gridContainer = document.getElementById('cardsViewContainer');
            const listContainer = document.getElementById('listViewContainer');
            const btnGrid = document.getElementById('viewBtnGrid');
            const btnList = document.getElementById('viewBtnList');

            if (view === 'list') {{
                gridContainer.classList.add('hidden');
                listContainer.classList.remove('hidden');
                btnList.style.backgroundColor = 'var(--btn-default-bg)';
                btnList.style.color = 'var(--fg-default)';
                btnGrid.style.backgroundColor = 'transparent';
                btnGrid.style.color = 'var(--fg-muted)';
            }} else {{
                listContainer.classList.add('hidden');
                gridContainer.classList.remove('hidden');
                btnGrid.style.backgroundColor = 'var(--btn-default-bg)';
                btnGrid.style.color = 'var(--fg-default)';
                btnList.style.backgroundColor = 'transparent';
                btnList.style.color = 'var(--fg-muted)';
            }}
            localStorage.setItem('certpulse_layout', view);
            if (updateUrl) syncUrlParams();
            renderCards();
        }}

        function syncUrlParams() {{
            const params = new URLSearchParams();
            const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
            if (currentTheme === 'light') params.set('theme', 'light');
            if (currentLayout !== 'grid') params.set('view', currentLayout);
            if (currentCategory !== 'All') params.set('cat', currentCategory);
            if (currentSearch.trim() !== '') params.set('q', currentSearch.trim());

            const newUrl = window.location.pathname + (params.toString() ? '?' + params.toString() : '');
            window.history.replaceState({{}}, '', newUrl);
        }}

        function showToast(msg) {{
            const toast = document.getElementById('toastNotification');
            document.getElementById('toastMessage').textContent = msg;
            toast.classList.remove('translate-y-20', 'opacity-0');
            toast.classList.add('translate-y-0', 'opacity-100');
            setTimeout(() => {{
                toast.classList.remove('translate-y-0', 'opacity-100');
                toast.classList.add('translate-y-20', 'opacity-0');
            }}, 2200);
        }}

        function copySteps(btnEl, title, steps) {{
            const textToCopy = `${{title}}\\n\\nHow to Claim:\\n${{steps}}`;
            navigator.clipboard.writeText(textToCopy).then(() => {{
                if (btnEl) {{
                    const originalHtml = btnEl.innerHTML;
                    btnEl.innerHTML = `<svg width="14" height="14" viewBox="0 0 16 16" fill="var(--success-fg)"><path d="M13.78 4.22a.75.75 0 0 1 0 1.06l-7.25 7.25a.75.75 0 0 1-1.06 0L2.22 9.28a.751.751 0 0 1 .018-1.042.751.751 0 0 1 1.042-.018L6 10.94l6.72-6.72a.75.75 0 0 1 1.06 0Z"></path></svg>`;
                    setTimeout(() => {{ btnEl.innerHTML = originalHtml; }}, 1800);
                }}
                showToast('Promo steps copied to clipboard!');
            }}).catch(() => {{
                showToast('Unable to copy to clipboard');
            }});
        }}

        function copyShareLink() {{
            syncUrlParams();
            navigator.clipboard.writeText(window.location.href).then(() => {{
                showToast('Direct link with active filters copied!');
            }});
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

        function appendToken(token) {{
            const input = document.getElementById('searchInput');
            input.value = (input.value.trim() + ' ' + token).trim();
            currentSearch = input.value;
            document.getElementById('clearSearchBtn').classList.remove('hidden');
            syncUrlParams();
            renderCards();
        }}

        function clearSearch() {{
            const input = document.getElementById('searchInput');
            input.value = '';
            currentSearch = '';
            document.getElementById('clearSearchBtn').classList.add('hidden');
            syncUrlParams();
            renderCards();
        }}

        function getPlatformColor(platform) {{
            const isLight = document.documentElement.getAttribute('data-theme') === 'light';
            if (platform.includes('Azure')) return isLight ? '#0062a8' : '#0078d4';
            if (platform.includes('AWS')) return isLight ? '#c05b00' : '#ff9900';
            if (platform.includes('Google')) return isLight ? '#1a73e8' : '#4285f4';
            if (platform.includes('Cisco')) return isLight ? '#0b7da8' : '#1ba0d7';
            if (platform.includes('ISC2')) return isLight ? '#006b40' : '#008752';
            if (platform.includes('Oracle')) return isLight ? '#c70000' : '#f80000';
            if (platform.includes('GitHub')) return isLight ? '#1a7f37' : '#2ea043';
            if (platform.includes('Snowflake')) return isLight ? '#0088be' : '#29b5e8';
            if (platform.includes('MongoDB')) return isLight ? '#008438' : '#00ed64';
            if (platform.includes('Postman')) return isLight ? '#d44315' : '#ff6c37';
            if (platform.includes('Linux')) return isLight ? '#002f6c' : '#58a6ff';
            return 'var(--accent-fg)';
        }}

        function parseGitHubQuery(queryStr) {{
            const tokens = {{
                freeText: [],
                status: null,
                category: null,
                platform: null,
                minValue: null
            }};
            const parts = queryStr.split(/\\s+/);
            for (const p of parts) {{
                if (p.startsWith('is:')) {{
                    tokens.status = p.slice(3).toLowerCase();
                }} else if (p.startsWith('cat:') || p.startsWith('category:')) {{
                    tokens.category = p.split(':')[1].toLowerCase();
                }} else if (p.startsWith('vendor:') || p.startsWith('platform:')) {{
                    tokens.platform = p.split(':')[1].toLowerCase();
                }} else if (p.startsWith('val:>')) {{
                    const valNum = parseInt(p.slice(5), 10);
                    if (!isNaN(valNum)) tokens.minValue = valNum;
                }} else if (p.trim() !== '') {{
                    tokens.freeText.push(p.toLowerCase());
                }}
            }}
            return tokens;
        }}

        function getFilteredData() {{
            const sortMode = document.getElementById('sortSelect').value;
            const statusMode = document.getElementById('statusFilter').value;
            const parsedQuery = parseGitHubQuery(currentSearch);

            let filtered = offersData.filter(o => {{
                // 1. SubNav Category
                if (currentCategory !== 'All' && !o.category.includes(currentCategory) && !o.platform.includes(currentCategory)) {{
                    return false;
                }}

                // 2. Select Status Filter
                if (statusMode === 'active' && o.status !== 'Active') return false;
                if (statusMode === 'closed' && o.status === 'Active') return false;

                // 3. GitHub Search Query Tokens
                if (parsedQuery.status) {{
                    if (parsedQuery.status === 'active' && o.status !== 'Active') return false;
                    if (parsedQuery.status === 'closed' && o.status === 'Active') return false;
                }}
                if (parsedQuery.category && !o.category.toLowerCase().includes(parsedQuery.category)) return false;
                if (parsedQuery.platform && !o.platform.toLowerCase().includes(parsedQuery.platform)) return false;
                if (parsedQuery.minValue !== null && (o.value_usd || 0) < parsedQuery.minValue) return false;

                // 4. Free text keywords
                if (parsedQuery.freeText.length > 0) {{
                    const text = (o.title + ' ' + o.platform + ' ' + o.certification_name + ' ' + o.category + ' ' + (o.eligibility || '') + ' ' + (o.claim_steps || '')).toLowerCase();
                    const allMatch = parsedQuery.freeText.every(word => text.includes(word));
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

            document.getElementById('resultsCount').textContent = `Showing ${{filtered.length}} of ${{offersData.length}} vouchers`;
            const activeInFiltered = filtered.filter(o => o.status === 'Active').length;
            const listOpenCount = document.getElementById('listOpenCount');
            if (listOpenCount) listOpenCount.textContent = `${{activeInFiltered}} Active Offers`;

            if (filtered.length === 0) {{
                const emptyHtml = `
                    <div class="col-span-full py-16 text-center border rounded-lg" style="background-color: var(--canvas-subtle); border-color: var(--border-default);">
                        <svg class="mx-auto w-10 h-10 mb-3" style="color: var(--fg-muted);" viewBox="0 0 16 16" fill="currentColor">
                            <path d="M1.5 8a6.5 6.5 0 1 1 13 0 6.5 6.5 0 0 1-13 0ZM8 0a8 8 0 1 0 0 16A8 8 0 0 0 8 0ZM5 5a1 1 0 0 0 0 2 1 1 0 0 0 0-2Zm6 0a1 1 0 1 0 0 2 1 1 0 0 0 0-2Zm-7.465 5.5a.75.75 0 0 1 1.05-.14 4.5 4.5 0 0 0 6.83 0 .75.75 0 1 1 1.17.94 6 6 0 0 1-9.11 0 .75.75 0 0 1 .06-1Z"></path>
                        </svg>
                        <h3 class="text-base font-bold" style="color: var(--fg-default);">No matching vouchers found</h3>
                        <p class="text-xs mt-1" style="color: var(--fg-muted);">Try relaxing search tokens or clearing filters.</p>
                        <button onclick="clearSearch()" class="mt-3 text-xs font-semibold px-3 py-1.5 rounded-md border" style="background-color: var(--btn-default-bg); border-color: var(--border-default); color: var(--accent-fg);">Reset Filters</button>
                    </div>
                `;
                grid.innerHTML = emptyHtml;
                tableBody.innerHTML = emptyHtml;
                return;
            }}

            if (currentLayout === 'grid') {{
                grid.innerHTML = filtered.map(o => {{
                    const isLive = (o.status === 'Active');
                    const badgeBg = isLive ? 'var(--success-subtle)' : 'var(--attention-subtle)';
                    const badgeColor = isLive ? 'var(--success-fg)' : 'var(--attention-fg)';
                    const statusLabel = isLive ? '🟢 Active' : (o.status === 'Registrations Closed' ? '🟡 Closed' : '🔴 Expired');
                    const brandColor = getPlatformColor(o.platform);

                    return `
                        <div class="primer-card p-5 rounded-lg flex flex-col justify-between">
                            <div>
                                <div class="flex items-center justify-between gap-2 mb-2.5">
                                    <span class="text-xs font-bold px-2.5 py-0.5 rounded-md flex items-center gap-1.5" style="background-color: var(--canvas-inset); color: ${{brandColor}}; border: 1px solid var(--border-default);">
                                        <span class="w-1.5 h-1.5 rounded-full" style="background-color: ${{brandColor}};"></span>
                                        ${{o.platform}}
                                    </span>
                                    <span class="text-[11px] font-semibold px-2 py-0.5 rounded-md font-mono" style="background-color: ${{badgeBg}}; color: ${{badgeColor}}; border: 1px solid ${{badgeColor}};">
                                        ${{statusLabel}}
                                    </span>
                                </div>

                                <h3 class="text-sm font-bold leading-snug hover:underline cursor-pointer" style="color: var(--fg-default);" onclick="window.open('${{o.url}}', '_blank')">
                                    ${{o.title}}
                                </h3>

                                <div class="flex items-center gap-2 mt-2">
                                    <span class="text-xs font-mono font-bold px-2 py-0.5 rounded border" style="background-color: var(--success-subtle); color: var(--success-fg); border-color: var(--success-fg);">
                                        $${{o.value_usd || 0}} USD Value
                                    </span>
                                    <span class="text-[11px] font-medium" style="color: var(--fg-muted);">
                                        ${{o.offer_type}}
                                    </span>
                                </div>

                                <details class="mt-3.5 text-xs group cursor-pointer">
                                    <summary class="font-semibold select-none flex items-center gap-1 hover:underline" style="color: var(--accent-fg);">
                                        <span>How to Claim</span>
                                        <svg class="w-3.5 h-3.5 transform group-open:rotate-90 transition-transform" viewBox="0 0 16 16" fill="currentColor">
                                            <path d="M6.22 3.22a.75.75 0 0 1 1.06 0l4.25 4.25a.75.75 0 0 1 0 1.06l-4.25 4.25a.751.751 0 0 1-1.042-.018.751.751 0 0 1-.018-1.042L9.94 8 6.22 4.28a.75.75 0 0 1 0-1.06Z"></path>
                                        </svg>
                                    </summary>
                                    <p class="mt-2 p-2.5 rounded-md border leading-relaxed" style="background-color: var(--canvas-inset); border-color: var(--border-muted); color: var(--fg-default);">
                                        ${{o.claim_steps}}
                                    </p>
                                </details>
                            </div>

                            <div class="mt-4 pt-3.5 border-t flex items-center justify-between" style="border-color: var(--border-muted);">
                                <span class="text-[11px] font-medium" style="color: var(--fg-muted);">
                                    ${{o.eligibility || 'Global'}}
                                </span>
                                <div class="flex items-center gap-2">
                                    <button onclick="copySteps(this, '${{o.title.replace(/'/g, "\\\\'") }}', '${{o.claim_steps.replace(/'/g, "\\\\'") }}')" title="Copy promo steps" class="p-1.5 rounded-md border hover:opacity-80 transition flex items-center justify-center" style="background-color: var(--btn-default-bg); border-color: var(--border-default); color: var(--fg-default);">
                                        <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                                            <path d="M0 6.75C0 5.784.784 5 1.75 5h1.5a.75.75 0 0 1 0 1.5h-1.5a.25.25 0 0 0-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 0 0 .25-.25v-1.5a.75.75 0 0 1 1.5 0v1.5A1.75 1.75 0 0 1 9.25 16h-7.5A1.75 1.75 0 0 1 0 14.25Z"></path>
                                            <path d="M5 1.75C5 .784 5.784 0 6.75 0h7.5C15.216 0 16 .784 16 1.75v7.5A1.75 1.75 0 0 1 14.25 11h-7.5A1.75 1.75 0 0 1 5 9.25Zm1.75-.25a.25.25 0 0 0-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 0 0 .25-.25v-7.5a.25.25 0 0 0-.25-.25Z"></path>
                                        </svg>
                                    </button>
                                    <a href="${{o.url}}" target="_blank" class="text-xs font-semibold px-3 py-1.5 rounded-md transition shadow-sm flex items-center gap-1 text-white hover:opacity-90" style="background-color: var(--btn-primary-bg);">
                                        <span>${{isLive ? 'Claim Free' : 'View'}}</span>
                                        <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor">
                                            <path d="M3.75 2h3.5a.75.75 0 0 1 0 1.5h-3.5a.25.25 0 0 0-.25.25v8.5c0 .138.112.25.25.25h8.5a.25.25 0 0 0 .25-.25v-3.5a.75.75 0 0 1 1.5 0v3.5A1.75 1.75 0 0 1 12.25 14h-8.5A1.75 1.75 0 0 1 2 12.25v-8.5C2 2.784 2.784 2 3.75 2Zm6.75.75a.75.75 0 0 1 .75-.75h4a.75.75 0 0 1 .75.75v4a.75.75 0 0 1-1.5 0V3.56l-5.72 5.72a.751.751 0 0 1-1.042-.018.751.751 0 0 1-.018-1.042L12.94 2.5H10.5a.75.75 0 0 1-.75-.75Z"></path>
                                        </svg>
                                    </a>
                                </div>
                            </div>
                        </div>
                    `;
                }}).join('');
            }} else {{
                // Issues Table Row View
                tableBody.innerHTML = filtered.map(o => {{
                    const isLive = (o.status === 'Active');
                    const brandColor = getPlatformColor(o.platform);
                    const statusIconColor = isLive ? 'var(--success-fg)' : 'var(--attention-fg)';

                    return `
                        <div class="issue-row p-3 flex items-start justify-between gap-3 text-xs">
                            <div class="flex items-start gap-2.5 flex-1 min-w-0">
                                <span class="mt-0.5" style="color: ${{statusIconColor}};">
                                    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                                        <path d="M8 9.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3Z"></path>
                                        <path d="M8 0a8 8 0 1 1 0 16A8 8 0 0 1 8 0ZM1.5 8a6.5 6.5 0 1 0 13 0 6.5 6.5 0 0 0-13 0Z"></path>
                                    </svg>
                                </span>
                                <div class="flex-1 min-w-0">
                                    <div class="flex items-center gap-2 flex-wrap">
                                        <a href="${{o.url}}" target="_blank" class="font-bold text-sm hover:underline cursor-pointer" style="color: var(--fg-default);">
                                            ${{o.title}}
                                        </a>
                                        <span class="text-[10px] font-bold px-2 py-0.5 rounded-full" style="background-color: var(--canvas-inset); color: ${{brandColor}}; border: 1px solid var(--border-default);">
                                            ${{o.platform}}
                                        </span>
                                        <span class="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border" style="background-color: var(--success-subtle); color: var(--success-fg); border-color: var(--success-fg);">
                                            $${{o.value_usd || 0}} USD
                                        </span>
                                    </div>
                                    <div class="text-[11px] mt-1 flex items-center gap-2" style="color: var(--fg-muted);">
                                        <span class="font-mono">#${{o.id}}</span>
                                        <span>•</span>
                                        <span>${{o.category}}</span>
                                        <span>•</span>
                                        <span>${{o.eligibility || 'Global'}}</span>
                                    </div>
                                    <details class="mt-1 text-xs group">
                                        <summary class="font-medium cursor-pointer hover:underline" style="color: var(--accent-fg);">Claim instructions &rarr;</summary>
                                        <div class="mt-1 p-2 rounded border" style="background-color: var(--canvas-inset); border-color: var(--border-muted); color: var(--fg-default);">
                                            ${{o.claim_steps}}
                                        </div>
                                    </details>
                                </div>
                            </div>
                            <div class="flex items-center gap-2 whitespace-nowrap">
                                <button onclick="copySteps(this, '${{o.title.replace(/'/g, "\\\\'") }}', '${{o.claim_steps.replace(/'/g, "\\\\'") }}')" class="p-1.5 rounded border hover:opacity-80 transition" style="background-color: var(--btn-default-bg); border-color: var(--border-default); color: var(--fg-default);" title="Copy instructions">
                                    <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M0 6.75C0 5.784.784 5 1.75 5h1.5a.75.75 0 0 1 0 1.5h-1.5a.25.25 0 0 0-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 0 0 .25-.25v-1.5a.75.75 0 0 1 1.5 0v1.5A1.75 1.75 0 0 1 9.25 16h-7.5A1.75 1.75 0 0 1 0 14.25Z"></path><path d="M5 1.75C5 .784 5.784 0 6.75 0h7.5C15.216 0 16 .784 16 1.75v7.5A1.75 1.75 0 0 1 14.25 11h-7.5A1.75 1.75 0 0 1 5 9.25Zm1.75-.25a.25.25 0 0 0-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 0 0 .25-.25v-7.5a.25.25 0 0 0-.25-.25Z"></path></svg>
                                </button>
                                <a href="${{o.url}}" target="_blank" class="px-3 py-1.5 rounded text-xs font-semibold text-white transition hover:opacity-90" style="background-color: var(--btn-primary-bg);">
                                    ${{isLive ? 'Claim' : 'View'}}
                                </a>
                            </div>
                        </div>
                    `;
                }}).join('');
            }}
        }}

        function filterCategory(cat) {{
            currentCategory = cat;
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

        // Keyboard Shortcuts
        document.addEventListener('keydown', (e) => {{
            if (e.key === '/' && document.activeElement.tagName !== 'INPUT') {{
                e.preventDefault();
                document.getElementById('searchInput').focus();
            }}
            if (e.key === 'Escape' && document.activeElement.id === 'searchInput') {{
                clearSearch();
                document.getElementById('searchInput').blur();
            }}
            if ((e.key === 'v' || e.key === 'V') && document.activeElement.tagName !== 'INPUT') {{
                setLayoutView(currentLayout === 'grid' ? 'list' : 'grid');
            }}
            if ((e.key === 't' || e.key === 'T') && document.activeElement.tagName !== 'INPUT') {{
                toggleTheme();
            }}
        }});

        document.getElementById('searchInput').addEventListener('input', (e) => {{
            currentSearch = e.target.value;
            const clearBtn = document.getElementById('clearSearchBtn');
            if (currentSearch.trim() !== '') clearBtn.classList.remove('hidden');
            else clearBtn.classList.add('hidden');
            syncUrlParams();
            renderCards();
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
    
    # 1. Write README.md
    readme_content = generate_readme(data)
    with open(README_FILE, "w", encoding="utf-8") as f:
        f.write(readme_content)
    print(f"[OK] Successfully built {README_FILE}")
    
    # 2. Write docs/index.html
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    html_content = generate_web_dashboard(data)
    with open(DOCS_HTML, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[OK] Successfully built {DOCS_HTML}")

if __name__ == "__main__":
    build_all()
