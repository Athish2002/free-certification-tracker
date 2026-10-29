"""
HTML dashboard builder for CertPulse web application.
Assembles the responsive single-page web dashboard with Bento grid, multi-view renderers,
accessible proof modal lightbox, and integrated theme engine.
"""

import html as html_lib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from src.builders.theme_engine import (
    DEFAULT_THEME,
    generate_css_variables,
    generate_zero_foit_script,
    generate_theme_dropdown_html,
)
from src.builders.client_bundle import generate_client_bundle
from src.builders.readme_builder import (
    DOCS_DIR,
    STATUS_BADGES,
    format_4_timezones,
    load_news,
)


def generate_web_dashboard(
    data: Union[Dict[str, Any], List[Dict[str, Any]]],
    news_data: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None,
    last_sync: Optional[str] = None,
) -> str:
    """
    Generates a high-craft, single-page web dashboard:
    - Default theme: Catppuccin Latte with 10 iconic developer color palettes.
    - Bespoke CertPulse squircle logo + vector pulse emblem.
    - Official vector SVG logos for all 22+ enterprise platforms.
    - Interactive check/claimed goal counters with localStorage persistence.
    - Automated inspection check counters (Live vs Checked).
    - Multi-view presentation (Grid, Table, Timeline, Matrix, Redemption).
    - Strict credential separation: primary written proctored exams on top, secondary unproctored badges in collapsible accordion.
    - Accessible Proof Modal Dialog with focus trapping and keyboard navigation.
    """
    if news_data is None:
        news_data = load_news()
        
    offers: List[Dict[str, Any]] = (
        data if isinstance(data, list) else (data.get("offers", []) if isinstance(data, dict) else [])
    )
    news_items: List[Dict[str, Any]] = (
        news_data if isinstance(news_data, list) else (news_data.get("news", []) if isinstance(news_data, dict) else [])
    )
    
    active_offers = [o for o in offers if o.get("status") == "Active"]
    closed_offers = [o for o in offers if o.get("status") != "Active" and not o.get("is_historical_archive")]
    historical_offers = [o for o in offers if o.get("is_historical_archive")]

    proctored_offers = [o for o in offers if o.get("credential_tier") in ("proctored_exam", "primary")]
    badge_offers = [o for o in offers if o.get("credential_tier") in ("skill_badge_lab", "secondary")]
    active_proctored = [o for o in proctored_offers if o.get("status") == "Active"]
    active_badges = [o for o in badge_offers if o.get("status") == "Active"]

    total_savings = sum((o.get("value_usd") or 0) for o in active_offers)
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
    last_sync_iso_js = last_sync_dt.isoformat() if last_sync_dt else datetime.now(timezone.utc).isoformat()
    last_updated_date = last_sync_dt.strftime("%Y-%m-%d") if last_sync_dt else datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # Safe JSON encoding preventing script breakout / XSS injections
    offers_json_str = json.dumps(offers).replace("<", "\\u003c").replace(">", "\\u003e")
    news_json_str = json.dumps(news_items).replace("<", "\\u003c").replace(">", "\\u003e")
    
    cloud_count = sum(1 for o in offers if "Cloud" in (o.get("category") or "") or "Cloud" in (o.get("platform") or ""))
    sec_count = sum(1 for o in offers if "Security" in (o.get("category") or ""))
    devops_count = sum(1 for o in offers if "DevOps" in (o.get("category") or ""))
    ai_count = sum(1 for o in offers if "AI" in (o.get("category") or "") or "Data" in (o.get("category") or ""))
    net_count = sum(1 for o in offers if "Networking" in (o.get("category") or ""))
    
    zero_foit_script = generate_zero_foit_script()
    css_variables = generate_css_variables()
    theme_dropdown_html = generate_theme_dropdown_html()
    client_script_bundle = generate_client_bundle(offers_json_str, news_json_str, last_sync_iso_js)
    
    closed_offers_markup = "".join([f'''<div class="p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2" style="background-color: var(--canvas-inset);">
        <div>
            <span class="font-bold" style="color: var(--fg-default);">{html_lib.escape(str(o.get('platform') or ''))}</span> — <span style="color: var(--fg-muted);">{html_lib.escape(str(o.get('certification_name') or o.get('title') or ''))}</span>
        </div>
        <div class="flex items-center gap-2 flex-wrap">
            <span class="px-2 py-0.5 rounded text-[10px] font-bold" style="background-color: var(--attention-subtle); color: var(--attention-fg);">{STATUS_BADGES.get(o.get('status'), o.get('status'))}</span>
            <span class="text-[11px]" style="color: var(--fg-subtle);">{html_lib.escape(str(o.get('inspection_notes', 'Under continuous review')))}</span>
            <button onclick="openProofModal('{html_lib.escape(str(o.get('id', '')))}')" class="px-2 py-0.5 rounded border text-[10px] font-semibold cursor-pointer inline-flex items-center gap-1 hover:opacity-80 transition active:scale-[0.96]" style="background-color: var(--canvas-default); border-color: var(--border-default); color: var(--fg-default);" title="View Verified Proof Screenshot Lightbox">
                <span>📸 Proof</span>
            </button>
        </div>
    </div>''' for o in closed_offers])

    return f"""<!DOCTYPE html>
<html lang="en" data-theme="{DEFAULT_THEME}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <meta name="theme-color" content="#eff1f5" id="themeColorMeta">
    <meta name="last-modified" content="{last_sync_iso_js}">
    <title>CertPulse | Free Certification Tracker & Tech Radar (Updated {last_updated_date})</title>
    <script src="https://cdn.tailwindcss.com"></script>
    {zero_foit_script}
    <style>
{css_variables}
    </style>
</head>
<body class="min-h-[100dvh] flex flex-col antialiased selection:bg-blue-500/20">

    <!-- Top Navigation Bar with Bespoke CertPulse Emblem -->
    <header class="border-b sticky top-0 z-40 backdrop-blur-md" style="background-color: var(--canvas-subtle); border-color: var(--border-default);">
        <div class="max-w-7xl mx-auto px-3.5 sm:px-6 lg:px-8 h-14 sm:h-16 flex items-center justify-between gap-2 sm:gap-4">
            
            <!-- Left: Bespoke CertPulse Logo Emblem & Brand -->
            <div class="flex items-center gap-2.5 sm:gap-3 min-w-0 cursor-pointer" onclick="scrollToTop()">
                <div class="w-8 h-8 sm:w-9 sm:h-9 rounded-xl flex items-center justify-center flex-shrink-0 shadow-md relative overflow-hidden" 
                     style="background: linear-gradient(135deg, var(--accent-fg) 0%, #04a5e5 100%);">
                    <!-- Bespoke CertPulse Vector Emblem: Telemetry Pulse Wave + Verification Star -->
                    <svg class="w-4 h-4 sm:w-5 sm:h-5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
                        <circle cx="19" cy="6" r="2.5" fill="#40a02b" stroke="#ffffff" stroke-width="1.5"/>
                    </svg>
                </div>
                <div class="flex items-center gap-1.5 sm:gap-2 text-xs sm:text-sm font-semibold min-w-0">
                    <span class="font-extrabold tracking-tight text-sm sm:text-base truncate" style="color: var(--fg-default);">CertPulse</span>
                    <span class="text-[9px] font-bold px-1.5 py-0.2 rounded-full uppercase" style="background-color: var(--accent-subtle); color: var(--accent-fg); border: 1px solid var(--accent-fg);">PRO</span>
                    <span class="hidden md:inline" style="color: var(--fg-muted);">/</span>
                    <a href="https://github.com/Athish2002/free-certification-tracker" target="_blank" class="hidden md:inline hover:underline truncate max-w-[180px]" style="color: var(--fg-muted);">
                        free-certification-tracker
                    </a>
                </div>

                <!-- Pulse Suite Switcher -->
                <nav class="hidden lg:inline-flex items-center rounded-full p-0.5 text-xs font-semibold ml-1.5 border" style="background-color: var(--canvas-inset); border-color: var(--border-default);" aria-label="Pulse Suite Navigation">
                    <span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full shadow-2xs font-bold text-[11px]" style="background-color: var(--accent-fg); color: #ffffff;">
                        <svg class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="8" r="7"/><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"/></svg>
                        Certifications
                    </span>
                    <a href="https://athish2002.github.io/free-course-tracker/" target="_blank" rel="noopener noreferrer" 
                       class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full transition text-[11px]" style="color: var(--fg-muted);" title="Switch to CoursePulse: Free University Syllabi">
                        <svg class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z"/><path d="M6 6h10"/><path d="M6 10h10"/></svg>
                        Courses
                    </a>
                </nav>
            </div>

            <!-- Right: Controls, Master UTC Telemetry, Single Theme Toggle & Repo CTA -->
            <div class="flex items-center gap-1.5 sm:gap-2.5 flex-shrink-0 relative">
                <!-- Synchronized Master UTC Telemetry Pill with Dynamic Local Offset -->
                <div id="navTimezonePill" class="hidden md:flex items-center gap-2 text-xs font-mono font-semibold px-3 py-1.5 rounded-xl border shadow-xs" style="background-color: var(--canvas-inset); border-color: var(--border-default); color: var(--fg-muted);" title="Synchronized Master UTC Telemetry with Dynamic Local Offset">
                    <span class="relative flex h-2 w-2">
                        <span class="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75" style="background-color: var(--success-fg);"></span>
                        <span class="relative inline-flex rounded-full h-2 w-2" style="background-color: var(--success-fg);"></span>
                    </span>
                    <span id="navUtcClock" class="tabular-nums font-bold" style="color: var(--fg-default);">{tz_info['utc']}</span>
                    <span id="navLocalOffset" class="text-[11px] font-medium opacity-80" style="color: var(--fg-subtle);">• Local</span>
                    <span id="navTimezoneText" class="sr-only">Last Synced: {tz_info['ticker']}</span>
                </div>

                <!-- Dark / Light Single Theme Toggle Button (Catppuccin Mocha / Catppuccin Latte) -->
                <button onclick="toggleTheme()" id="themeToggleBtn" title="Toggle Pure OLED Dark / Ceramic Light Mode (T)" aria-label="Toggle Dark / Light Contrast Mode" class="h-10 w-10 sm:h-9 sm:w-auto sm:px-3.5 rounded-xl border text-xs font-semibold flex items-center justify-center gap-1.5 transition active:scale-[0.96] shadow-xs cursor-pointer" style="background-color: var(--btn-default-bg); border-color: var(--border-default); color: var(--fg-default);">
                    <span id="themeIconSun" class="hidden flex items-center gap-1.5">
                        <svg class="w-4 h-4" viewBox="0 0 16 16" fill="currentColor"><path d="M8 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM8 0a.75.75 0 0 1 .75.75v1.5a.75.75 0 0 1-1.5 0V.75A.75.75 0 0 1 8 0Zm0 13a.75.75 0 0 1 .75.75v1.5a.75.75 0 0 1-1.5 0v-1.5A.75.75 0 0 1 8 13ZM2.343 2.343a.75.75 0 0 1 1.061 0l1.06 1.061a.75.75 0 0 1-1.06 1.06l-1.06-1.06a.75.75 0 0 1 0-1.061Zm9.193 9.193a.75.75 0 0 1 1.06 0l1.061 1.06a.75.75 0 0 1-1.06 1.061l-1.061-1.06a.75.75 0 0 1 0-1.061ZM0 8a.75.75 0 0 1 .75-.75h1.5a.75.75 0 0 1 0 1.5H.75A.75.75 0 0 1 0 8Zm13 0a.75.75 0 0 1 .75-.75h1.5a.75.75 0 0 1 0 1.5h-1.5A.75.75 0 0 1 13 8ZM2.343 13.657a.75.75 0 0 1 0-1.06l1.06-1.061a.75.75 0 1 1 1.061 1.06l-1.06 1.061a.75.75 0 0 1-1.061 0Zm9.193-9.193a.75.75 0 0 1 0-1.06l1.061-1.061a.75.75 0 0 1 1.06 1.06l-1.06 1.061a.75.75 0 0 1-1.061 0Z"></path></svg>
                        <span class="hidden sm:inline">Light</span>
                    </span>
                    <span id="themeIconMoon" class="hidden flex items-center gap-1.5">
                        <svg class="w-4 h-4" viewBox="0 0 16 16" fill="currentColor"><path d="M9.598 1.591a.749.749 0 0 1 .785-.175 7.001 7.001 0 1 1-8.967 8.967.75.75 0 0 1 .961-.96 5.5 5.5 0 0 0 7.046-7.046.75.75 0 0 1 .175-.786Zm1.616 1.945a7 7 0 0 1-7.678 7.678 5.499 5.499 0 1 0 7.678-7.678Z"></path></svg>
                        <span class="hidden sm:inline">Dark</span>
                    </span>
                </button>

                <!-- GitHub Repo Star CTA -->
                <a href="https://github.com/Athish2002/free-certification-tracker" target="_blank" aria-label="Star CertPulse on GitHub" class="h-10 w-10 sm:h-9 sm:w-auto sm:px-3 rounded-lg border text-xs font-semibold flex items-center justify-center gap-1.5 transition active:scale-[0.98] shadow-xs cursor-pointer" style="background-color: var(--btn-default-bg); border-color: var(--border-default); color: var(--fg-default);">
                    <svg height="14" viewBox="0 0 16 16" width="14" fill="currentColor">
                        <path d="M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.751.751 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.751.751 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Z"></path>
                    </svg>
                    <span class="hidden sm:inline">Star</span>
                </a>
            </div>
        </div>
    </header>

    <!-- SubNav Tabs: Active Vouchers vs Industry Tech Radar vs Where Offers Are Applied -->
    <nav class="border-b" style="background-color: var(--canvas-subtle); border-color: var(--border-default);">
        <div class="max-w-7xl mx-auto px-3.5 sm:px-6 lg:px-8 flex items-center justify-between">
            <div class="flex items-center gap-1 sm:gap-2 -mb-px overflow-x-auto touch-scroll scrollbar-none w-full sm:w-auto" id="mainTabNav">
                <button id="tabBtnVouchers" onclick="switchMainTab('vouchers')" class="flex items-center gap-2 py-3 px-3 sm:px-4 border-b-2 font-semibold text-xs sm:text-sm transition flex-shrink-0 active:scale-[0.98] min-h-[44px]" style="border-color: var(--accent-fg); color: var(--fg-default);">
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" class="flex-shrink-0">
                        <path d="M1 3.5A1.5 1.5 0 0 1 2.5 2h11A1.5 1.5 0 0 1 15 3.5v2a1.5 1.5 0 0 1-1.5 1.5.5.5 0 0 0 0 1 1.5 1.5 0 0 1 1.5 1.5v2a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 1 11.5v-2a1.5 1.5 0 0 1 1.5-1.5.5.5 0 0 0 0-1A1.5 1.5 0 0 1 1 5.5v-2Zm1.5-.5a.5.5 0 0 0-.5.5v2a2.5 2.5 0 0 0 1.5 2.298v.404A2.5 2.5 0 0 0 2 10.5v2a.5.5 0 0 0 .5.5h11a.5.5 0 0 0 .5-.5v-2a2.5 2.5 0 0 0-1.5-2.298v-.404A2.5 2.5 0 0 0 14 5.5v-2a.5.5 0 0 0-.5-.5h-11Z"></path>
                    </svg>
                    <span>Certification Vouchers</span>
                    <span id="tabBadgeVouchers" class="text-[10px] sm:text-xs px-2 py-0.5 rounded-full font-bold tabular-nums border" style="background-color: var(--accent-subtle); color: var(--accent-fg); border-color: var(--accent-fg);">{len(offers)}</span>
                </button>
                <button id="tabBtnNews" onclick="switchMainTab('news')" class="flex items-center gap-2 py-3 px-3 sm:px-4 border-b-2 font-medium text-xs sm:text-sm transition flex-shrink-0 active:scale-[0.98] min-h-[44px]" style="border-color: transparent; color: var(--fg-muted);">
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" class="flex-shrink-0">
                        <path d="M0 1.75C0 .784.784 0 1.75 0h12.5C15.216 0 16 .784 16 1.75v10.5A1.75 1.75 0 0 1 14.25 14H1.75A1.75 1.75 0 0 1 0 12.25Zm1.75-.25a.25.25 0 0 0-.25.25v10.5c0 .138.112.25.25.25h12.5a.25.25 0 0 0 .25-.25V1.75a.25.25 0 0 0-.25-.25ZM3 3h10a.75.75 0 0 1 0 1.5H3A.75.75 0 0 1 3 3Zm0 3.5h10a.75.75 0 0 1 0 1.5H3a.75.75 0 0 1 0-1.5ZM3 10h6a.75.75 0 0 1 0 1.5H3A.75.75 0 0 1 3 10Z"></path>
                    </svg>
                    <span>Industry Tech Radar</span>
                    <span id="tabBadgeNews" class="text-[10px] sm:text-xs px-2 py-0.5 rounded-full font-medium tabular-nums border" style="background-color: var(--canvas-inset); color: var(--fg-muted); border-color: var(--border-default);">{len(news_items)}</span>
                </button>
                <button id="tabBtnRedemption" onclick="switchMainTab('redemption')" class="flex items-center gap-2 py-3 px-3 sm:px-4 border-b-2 font-medium text-xs sm:text-sm transition flex-shrink-0 active:scale-[0.98] min-h-[44px]" style="border-color: transparent; color: var(--fg-muted);">
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" class="flex-shrink-0">
                        <path d="M0 4a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V4Zm2-1a1 1 0 0 0-1 1v1h14V4a1 1 0 0 0-1-1H2Zm13 4H1v5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V7Zm-9 3a1 1 0 0 1 1-1h4a1 1 0 0 1 0 2H7a1 1 0 0 1-1-1Z"></path>
                    </svg>
                    <span>Where Offers Are Applied</span>
                    <span id="tabBadgeRedemption" class="text-[10px] sm:text-xs px-2 py-0.5 rounded-full font-medium tabular-nums border" style="background-color: var(--canvas-inset); color: var(--fg-muted); border-color: var(--border-default);">{len(active_offers)}</span>
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
                <kbd class="px-1.5 py-0.5 rounded border text-[10px] font-mono" style="background-color: var(--canvas-default); border-color: var(--border-default);">3</kbd>
                <span>Redemption</span>
                <kbd class="px-1.5 py-0.5 rounded border text-[10px] font-mono" style="background-color: var(--canvas-default); border-color: var(--border-default);">T</kbd>
                <span>Theme</span>
            </div>
        </div>
    </nav>

    <!-- Main Single Page Container -->
    <main class="max-w-7xl mx-auto px-3.5 sm:px-6 lg:px-8 py-5 sm:py-8 flex-1 w-full min-w-0">
        
        <!-- SECTION 1: CERTIFICATION VOUCHERS -->
        <div id="vouchersSection">
            <!-- Hero Bento Grid with Automated Inspection & Goal Check Counters -->
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3.5 sm:gap-4 mb-5 sm:mb-8">
                <!-- Bento 1: Total Value Saved -->
                <div class="p-4 sm:p-5 rounded-2xl border primer-card flex flex-col justify-between">
                    <div class="flex items-center justify-between">
                        <span class="text-xs font-semibold uppercase tracking-wider" style="color: var(--fg-muted);">Total Savings</span>
                        <span class="w-2 h-2 rounded-full animate-pulse" style="background-color: var(--success-fg);"></span>
                    </div>
                    <div class="mt-3">
                        <div class="text-2xl sm:text-3xl font-extrabold tracking-tight tabular-nums" style="color: var(--success-fg);">
                            ${total_savings:,} <span class="text-xs font-normal" style="color: var(--fg-muted);">USD</span>
                        </div>
                        <p class="text-[11px] mt-1 text-pretty" style="color: var(--fg-muted);">Aggregate tuition value of free proctored exams</p>
                    </div>
                </div>

                <!-- Bento 2: Active Opportunities & Automated Check Status -->
                <div class="p-4 sm:p-5 rounded-2xl border primer-card flex flex-col justify-between">
                    <div class="flex items-center justify-between">
                        <span class="text-xs font-semibold uppercase tracking-wider" style="color: var(--fg-muted);">Active Offers</span>
                        <span class="text-[10px] font-bold px-1.5 py-0.2 rounded tabular-nums" style="background-color: var(--success-subtle); color: var(--success-fg);">{len(active_offers)}/{len(active_offers)} LIVE &bull; {len(offers)} CHECKED</span>
                    </div>
                    <div class="mt-3">
                        <div class="text-2xl sm:text-3xl font-extrabold tracking-tight tabular-nums" style="color: var(--fg-default);">
                            {len(active_offers)} <span class="text-xs font-normal" style="color: var(--fg-muted);">Vouchers</span>
                        </div>
                        <p class="text-[11px] mt-1 text-pretty" style="color: var(--fg-muted);">{len(active_proctored)} Proctored &bull; {len(active_badges)} Skill Badges &bull; {len(historical_offers)} Archived</p>
                    </div>
                </div>

                <!-- Bento 3: Authenticity Gate Standard -->
                <div class="p-4 sm:p-5 rounded-2xl border primer-card flex flex-col justify-between">
                    <div class="flex items-center justify-between">
                        <span class="text-xs font-semibold uppercase tracking-wider" style="color: var(--fg-muted);">Authenticity Standard</span>
                        <span class="text-[10px] font-bold px-1.5 py-0.2 rounded" style="background-color: var(--accent-subtle); color: var(--accent-fg);">VERIFIED</span>
                    </div>
                    <div class="mt-3">
                        <div class="text-2xl sm:text-3xl font-extrabold tracking-tight tabular-nums" style="color: var(--accent-fg);">
                            100% Authentic
                        </div>
                        <p class="text-[11px] mt-1 text-pretty" style="color: var(--fg-muted);">Zero scam domains, zero dumps, strict TLS</p>
                    </div>
                </div>

                <!-- Bento 4: 4-Timezone Global Telemetry & Cadence -->
                <div class="p-4 sm:p-5 rounded-2xl border primer-card flex flex-col justify-between" id="heroCadenceCard">
                    <div class="flex items-center justify-between">
                        <span class="text-xs font-semibold uppercase tracking-wider" style="color: var(--fg-muted);">Last Sync (4-TZ)</span>
                        <span class="text-[10px] font-mono font-bold px-1.5 py-0.2 rounded" style="background-color: var(--accent-subtle); color: var(--accent-fg);">4-HOUR CRON</span>
                    </div>
                    <div class="mt-3">
                        <div class="text-xs sm:text-sm font-extrabold tracking-tight tabular-nums font-mono" style="color: var(--fg-default);">
                            <span id="heroCadenceUtc">{tz_info['utc_short']}</span> &bull; <span id="heroCadenceIst" style="color: var(--accent-fg);">{tz_info['ist']}</span>
                        </div>
                        <div class="text-[11px] font-mono mt-1 tabular-nums" style="color: var(--fg-muted);">
                            <span id="heroCadenceEt">{tz_info['et']}</span> &bull; <span id="heroCadenceCet">{tz_info['cet']}</span>
                        </div>
                        <p class="text-[11px] mt-1 text-pretty" style="color: var(--fg-muted);">Automated Audit Timestamp across UTC, IST, EDT, CEST</p>
                    </div>
                </div>
            </div>

            <!-- Prominent Command-Bar Search Experience -->
            <div class="mb-4">
                <div class="relative w-full rounded-xl border shadow-xs transition-all duration-200 focus-within:ring-2 focus-within:ring-blue-500/30 focus-within:border-blue-500" style="background-color: var(--canvas-subtle); border-color: var(--border-default);">
                    <div class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none" style="color: var(--fg-muted);">
                        <svg width="18" height="18" viewBox="0 0 16 16" fill="currentColor">
                            <path d="M10.68 11.74a6 6 0 0 1-7.922-8.982 6 6 0 0 1 8.982 7.922l3.04 3.04a.749.749 0 0 1-.326 1.275.749.749 0 0 1-.734-.215ZM11.5 7a4.5 4.5 0 1 0-9 0 4.5 4.5 0 0 0 9 0Z"></path>
                        </svg>
                    </div>
                    <input type="text" id="searchInput" placeholder="Search {len(active_offers)} active certifications ({len(active_proctored)} proctored, {len(active_badges)} skill badges) by vendor, exam, tier..." 
                           class="w-full pl-10 pr-12 sm:pr-28 py-3 sm:py-3.5 text-base sm:text-sm rounded-xl focus:outline-none transition font-medium"
                           style="background-color: transparent; color: var(--fg-default);">
                    <div class="absolute inset-y-0 right-0 pr-2.5 sm:pr-3 flex items-center gap-1.5 sm:gap-2">
                        <button id="clearSearchBtn" onclick="clearSearch()" class="hidden min-w-[36px] min-h-[36px] w-9 h-9 sm:w-8 sm:h-8 rounded-lg text-sm sm:text-xs hover:opacity-80 font-bold flex items-center justify-center active:scale-[0.98] transition cursor-pointer" style="background-color: var(--canvas-inset); color: var(--fg-muted); border: 1px solid var(--border-default);" title="Clear search" aria-label="Clear search">
                            ✕
                        </button>
                        <span id="searchMatchesBadge" class="hidden sm:inline-flex text-xs font-medium px-2 py-0.5 rounded border tabular-nums" style="background-color: var(--accent-subtle); border-color: var(--accent-fg); color: var(--accent-fg);"></span>
                        <kbd class="hidden md:inline-flex items-center text-xs font-mono px-2 py-0.5 rounded border pointer-events-none" style="background-color: var(--canvas-inset); border-color: var(--border-default); color: var(--fg-muted);" title="Press / to search">/</kbd>
                    </div>
                </div>
            </div>

            <!-- Interactive Credential Tier Filter Pills -->
            <div class="flex items-center gap-1.5 p-1 rounded-xl border mb-3 overflow-x-auto touch-scroll scrollbar-none" id="tierFilterPills" style="background-color: var(--canvas-inset); border-color: var(--border-default);">
                <button onclick="filterTier('all')" id="tierPillAll" class="tier-pill min-h-[38px] px-3.5 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition active:scale-[0.98] flex items-center gap-1.5 flex-shrink-0 cursor-pointer" style="background-color: var(--accent-emphasis); color: #ffffff;" data-tier="all">
                    <span>All Credentials</span>
                    <span class="text-[10px] px-1.5 py-0.2 rounded-full tabular-nums font-bold bg-white/20">{len(offers)}</span>
                </button>
                <button onclick="filterTier('proctored_exam')" id="tierPillProctored" class="tier-pill min-h-[38px] px-3.5 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap border transition hover:opacity-80 active:scale-[0.98] flex items-center gap-1.5 flex-shrink-0 cursor-pointer" style="background-color: var(--canvas-default); border-color: var(--border-default); color: var(--fg-muted);" data-tier="proctored_exam">
                    <span>🎓 Written Proctored Exams</span>
                    <span class="text-[10px] px-1.5 py-0.2 rounded-full tabular-nums font-medium" style="background-color: var(--canvas-inset);">{len(proctored_offers)}</span>
                </button>
                <button onclick="filterTier('skill_badge_lab')" id="tierPillBadges" class="tier-pill min-h-[38px] px-3.5 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap border transition hover:opacity-80 active:scale-[0.98] flex items-center gap-1.5 flex-shrink-0 cursor-pointer" style="background-color: var(--canvas-default); border-color: var(--border-default); color: var(--fg-muted);" data-tier="skill_badge_lab">
                    <span>🎖️ Digital Skill Badges & Labs</span>
                    <span class="text-[10px] px-1.5 py-0.2 rounded-full tabular-nums font-medium" style="background-color: var(--canvas-inset);">{len(badge_offers)}</span>
                </button>
            </div>

            <!-- Unified Category Filters & Multi-View Controls Toolbar -->
            <div class="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-2.5 sm:gap-3 mb-4 p-2 sm:p-2.5 rounded-xl border shadow-xs" style="background-color: var(--canvas-subtle); border-color: var(--border-default);">
                <!-- Category Filter Pills -->
                <div class="flex gap-1.5 overflow-x-auto touch-scroll scrollbar-none pb-1.5 lg:pb-0 px-0.5" id="filterPills">
                    <button onclick="filterCategory('All')" class="cat-pill min-h-[40px] px-3.5 py-2 rounded-lg text-xs font-semibold whitespace-nowrap transition active:scale-[0.98] flex items-center gap-1.5 flex-shrink-0 cursor-pointer" style="background-color: var(--accent-emphasis); color: #ffffff;" data-cat="All">
                        <span>All</span>
                        <span class="text-[10px] px-1.5 py-0.2 rounded-full tabular-nums font-bold bg-white/20">{len(offers)}</span>
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
                        <span>📜 History</span>
                        <span class="text-[10px] px-1.5 py-0.2 rounded-full tabular-nums font-medium" style="background-color: var(--canvas-inset);">{len(historical_offers)}</span>
                    </button>
                </div>

                <!-- Controls (Sort, Status, Layout Switcher, Export) -->
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
                        <!-- Multi-View Layout Switcher (Grid, Table, Timeline, Matrix) -->
                        <div class="flex items-center rounded-lg border p-0.5 flex-1 sm:flex-initial justify-center" id="layoutControlGroup" style="background-color: var(--canvas-inset); border-color: var(--border-default);">
                            <button id="viewBtnGrid" onclick="setLayoutView('grid')" title="Bento Grid View (Press V to cycle)" class="flex-1 sm:flex-initial min-h-[38px] px-2.5 sm:px-3 py-1.5 rounded-md text-xs font-semibold flex items-center justify-center gap-1.5 transition active:scale-[0.98] cursor-pointer" style="background-color: var(--btn-default-bg); color: var(--fg-default);">
                                <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M1 2.5A1.5 1.5 0 0 1 2.5 1h3A1.5 1.5 0 0 1 7 2.5v3A1.5 1.5 0 0 1 5.5 7h-3A1.5 1.5 0 0 1 1 5.5v-3Zm8 0A1.5 1.5 0 0 1 10.5 1h3A1.5 1.5 0 0 1 15 2.5v3A1.5 1.5 0 0 1 13.5 7h-3A1.5 1.5 0 0 1 9 5.5v-3Zm-8 8A1.5 1.5 0 0 1 2.5 9h3A1.5 1.5 0 0 1 7 10.5v3A1.5 1.5 0 0 1 5.5 15h-3A1.5 1.5 0 0 1 1 13.5v-3Zm8 0A1.5 1.5 0 0 1 10.5 9h3a1.5 1.5 0 0 1 1.5 1.5v3a1.5 1.5 0 0 1-1.5 1.5h-3A1.5 1.5 0 0 1 9 13.5v-3Z"></path></svg>
                                <span>Grid</span>
                            </button>
                            <button id="viewBtnList" onclick="setLayoutView('list')" title="Catalog Table View (Press V to cycle)" class="flex-1 sm:flex-initial min-h-[38px] px-2.5 sm:px-3 py-1.5 rounded-md text-xs font-medium flex items-center justify-center gap-1.5 transition active:scale-[0.98] cursor-pointer" style="color: var(--fg-muted);">
                                <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M2 3.75C2 3.336 2.336 3 2.75 3h10.5a.75.75 0 0 1 0 1.5H2.75A.75.75 0 0 1 2 3.75Zm0 4.25c0-.414.336-.75.75-.75h10.5a.75.75 0 0 1 0 1.5H2.75A.75.75 0 0 1 2 8Zm0 4.25c0-.414.336-.75.75-.75h10.5a.75.75 0 0 1 0 1.5H2.75a.75.75 0 0 1-.75-.75Z"></path></svg>
                                <span>Table</span>
                            </button>
                            <button id="viewBtnTimeline" onclick="setLayoutView('timeline')" title="Recurrence Timeline (Press V to cycle)" class="flex-1 sm:flex-initial min-h-[38px] px-2.5 sm:px-3 py-1.5 rounded-md text-xs font-medium flex items-center justify-center gap-1.5 transition active:scale-[0.98] cursor-pointer" style="color: var(--fg-muted);">
                                <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M8 0a8 8 0 1 1 0 16A8 8 0 0 1 8 0ZM1.5 8a6.5 6.5 0 1 0 13 0 6.5 6.5 0 0 0-13 0Zm7.25-3.25v3.69l2.28 2.28a.75.75 0 1 1-1.06 1.06l-2.5-2.5a.75.75 0 0 1-.22-.53V4.75a.75.75 0 0 1 1.5 0Z"></path></svg>
                                <span>Timeline</span>
                            </button>
                            <button id="viewBtnMatrix" onclick="setLayoutView('matrix')" title="Domain & Skill Matrix View (Press V to cycle)" class="flex-1 sm:flex-initial min-h-[38px] px-2.5 sm:px-3 py-1.5 rounded-md text-xs font-medium flex items-center justify-center gap-1.5 transition active:scale-[0.98] cursor-pointer" style="color: var(--fg-muted);">
                                <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M1.5 1h13A1.5 1.5 0 0 1 16 2.5v11a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 0 13.5v-11A1.5 1.5 0 0 1 1.5 1Zm0 1.5a.5.5 0 0 0-.5.5v3h4.5V2.5H1.5Zm5.5 0v3h4.5V2.5H7Zm5.5 0v3H15V3a.5.5 0 0 0-.5-.5h-2Zm2 4.5h-3.5v3.5H15V7Zm-4.5 3.5V7H7v3.5h4.5ZM5.5 7H1v3.5h4.5V7Zm0 4.5H1v1.5a.5.5 0 0 0 .5.5H5.5v-2Zm1.5 2h4.5v-2H7v2Zm5.5 0h1.5a.5.5 0 0 0 .5-.5v-1.5h-2v2Z"></path></svg>
                                <span>Matrix</span>
                            </button>
                        </div>
                        <button onclick="exportFilteredJson()" class="min-h-[40px] h-10 px-3 rounded-lg border hover:opacity-80 active:scale-[0.98] transition flex items-center justify-center gap-1.5 text-xs font-semibold flex-shrink-0 cursor-pointer" style="background-color: var(--btn-default-bg); border-color: var(--border-default); color: var(--fg-default);" title="Export Filtered JSON">
                            <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M2.75 14A1.75 1.75 0 0 1 1 12.25v-2.5a.75.75 0 0 1 1.5 0v2.5c0 .138.112.25.25.25h10.5a.25.25 0 0 0 .25-.25v-2.5a.75.75 0 0 1 1.5 0v2.5A1.75 1.75 0 0 1 13.25 14H2.75Z"></path><path d="M7.25 1.75v7.69L4.97 7.16a.75.75 0 0 0-1.06 1.06l3.5 3.5a.75.75 0 0 0 1.06 0l3.5-3.5a.75.75 0 1 0-1.06-1.06L8.75 9.44V1.75a.75.75 0 0 0-1.5 0Z"></path></svg>
                            <span>JSON</span>
                        </button>
                    </div>
                </div>
            </div>

            <!-- Result Status Bar -->
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
                        <div class="col-span-1 text-center">Value</div>
                        <div class="col-span-3 text-right">Verification & Actions</div>
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

            <!-- Collapsible Triage Section on Same Page -->
            <div class="mt-8 pt-6 border-t" style="border-color: var(--border-default);">
                <details class="group rounded-xl border p-4 transition-all" style="background-color: var(--canvas-subtle); border-color: var(--border-default);">
                    <summary class="flex items-center justify-between font-semibold text-xs sm:text-sm cursor-pointer select-none">
                        <div class="flex items-center gap-2">
                            <span class="text-amber-500">🟡</span>
                            <span>Under Review / Yet to Confirm (Triage Pool — {len(closed_offers)} Tracked)</span>
                        </div>
                        <span class="text-xs transition-transform group-open:rotate-180" style="color: var(--fg-muted);">▼</span>
                    </summary>
                    <p class="text-xs mt-3 leading-relaxed" style="color: var(--fg-muted);">
                        Authentic vendor opportunities flagged by our automated inspector for capacity limits, closed cohorts, or ambiguous signals. Re-audited automatically every 4 hours.
                    </p>
                    <div class="mt-4 divide-y border rounded-lg overflow-hidden text-xs" style="border-color: var(--border-default);">
                        {closed_offers_markup}
                    </div>
                </details>
            </div>
        </div>

        <!-- SECTION 2: INDUSTRY TECH RADAR & ENGINEERING FEED -->
        <div id="newsSection" class="hidden">
            <!-- News Hero Bento Grid -->
            <div class="grid grid-cols-1 lg:grid-cols-12 gap-3.5 sm:gap-4 mb-5 sm:mb-8">
                <!-- Anchor Bento: Verified Dispatches -->
                <div class="lg:col-span-6 p-4 sm:p-6 rounded-2xl border primer-card relative overflow-hidden flex flex-col justify-between">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center gap-2">
                            <span class="w-2 h-2 rounded-full animate-pulse" style="background-color: var(--success-fg);"></span>
                            <span class="text-xs font-semibold" style="color: var(--fg-muted);">Live Intelligence Feed</span>
                        </div>
                        <span class="p-1.5 sm:p-2 rounded-lg flex-shrink-0" style="background-color: var(--success-subtle); color: var(--success-fg); border: 1px solid var(--success-fg);">
                            <svg width="18" height="18" viewBox="0 0 16 16" fill="currentColor"><path d="M13.78 4.22a.75.75 0 0 1 0 1.06l-7.25 7.25a.75.75 0 0 1-1.06 0L2.22 9.28a.751.751 0 0 1 .018-1.042.751.751 0 0 1 1.042-.018L6 10.94l6.72-6.72a.75.75 0 0 1 1.06 0Z"></path></svg>
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

                <!-- News Bento 2: Enterprise Scope -->
                <div class="lg:col-span-3 p-4 sm:p-6 rounded-2xl border primer-card flex flex-col justify-between">
                    <div class="flex items-center justify-between">
                        <span class="text-xs font-semibold" style="color: var(--fg-muted);">Ecosystem Scope</span>
                        <span class="p-1.5 sm:p-2 rounded-lg flex-shrink-0" style="background-color: var(--accent-subtle); color: var(--accent-fg); border: 1px solid var(--accent-fg);">
                            <svg width="18" height="18" viewBox="0 0 16 16" fill="currentColor"><path d="M1.75 1.5a.25.25 0 0 0-.25.25v8.5c0 .138.112.25.25.25h12.5a.25.25 0 0 0 .25-.25v-8.5a.25.25 0 0 0-.25-.25H1.75ZM0 1.75C0 .784.784 0 1.75 0h12.5C15.216 0 16 .784 16 1.75v8.5A1.75 1.75 0 0 1 14.25 12H9.06l.72 2.25H11.5a.75.75 0 0 1 0 1.5h-7a.75.75 0 0 1 0-1.5h1.72l.72-2.25H1.75A1.75 1.75 0 0 1 0 10.25V1.75Z"></path></svg>
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

                <!-- News Bento 3: Anti-Clickbait Guardian -->
                <div class="lg:col-span-3 p-4 sm:p-6 rounded-2xl border primer-card flex flex-col justify-between">
                    <div class="flex items-center justify-between">
                        <span class="text-xs font-semibold" style="color: var(--fg-muted);">Integrity Standard</span>
                        <span class="p-1.5 sm:p-2 rounded-lg flex-shrink-0" style="background-color: var(--attention-subtle); color: var(--attention-fg); border: 1px solid var(--attention-fg);">
                            <svg width="18" height="18" viewBox="0 0 16 16" fill="currentColor"><path d="M7.462.166a.75.75 0 0 1 .538 0l6.25 2.5a.75.75 0 0 1 .478.704c0 4.195-2.067 8.046-5.83 10.428a.75.75 0 0 1-.806 0C4.317 11.416 2.25 7.565 2.25 3.37a.75.75 0 0 1 .478-.704l6.25-2.5Zm.538 1.558L2.75 3.82c.117 3.518 1.83 6.758 4.996 8.847 3.165-2.089 4.88-5.329 4.996-8.847L8 1.724Z"></path></svg>
                        </span>
                    </div>
                    <div class="mt-3 sm:mt-4">
                        <div class="text-xl sm:text-3xl font-extrabold tracking-tight tabular-nums" style="color: var(--attention-fg);">
                            0% Clickbait <span class="text-xs sm:text-sm font-normal font-sans" style="color: var(--fg-muted);">Verified</span>
                        </div>
                        <p class="text-xs mt-1.5 sm:mt-2 leading-relaxed text-pretty" style="color: var(--fg-muted);">
                            Strict primary enterprise domain whitelist. Rumor blogs and content mills barred.
                        </p>
                    </div>
                </div>
            </div>

            <!-- News Command-Bar Search -->
            <div class="mb-4">
                <div class="relative w-full rounded-xl border shadow-xs transition-all duration-200 focus-within:ring-2 focus-within:ring-blue-500/30 focus-within:border-blue-500" style="background-color: var(--canvas-subtle); border-color: var(--border-default);">
                    <div class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none" style="color: var(--fg-muted);">
                        <svg width="18" height="18" viewBox="0 0 16 16" fill="currentColor"><path d="M10.68 11.74a6 6 0 0 1-7.922-8.982 6 6 0 0 1 8.982 7.922l3.04 3.04a.749.749 0 0 1-.326 1.275.749.749 0 0 1-.734-.215ZM11.5 7a4.5 4.5 0 1 0-9 0 4.5 4.5 0 0 0 9 0Z"></path></svg>
                    </div>
                    <input type="text" id="newsSearchInput" placeholder="Filter radar by keyword, company, topic, or domain..." 
                           class="w-full pl-10 pr-12 sm:pr-28 py-3 sm:py-3.5 text-base sm:text-sm rounded-xl focus:outline-none transition font-medium"
                           style="background-color: transparent; color: var(--fg-default);">
                    <div class="absolute inset-y-0 right-0 pr-2.5 sm:pr-3 flex items-center gap-1.5 sm:gap-2">
                        <button id="clearNewsSearchBtn" onclick="clearNewsSearch()" class="hidden min-w-[36px] min-h-[36px] w-9 h-9 sm:w-8 sm:h-8 rounded-lg text-sm sm:text-xs hover:opacity-80 font-bold flex items-center justify-center active:scale-[0.98] transition cursor-pointer" style="background-color: var(--canvas-inset); color: var(--fg-muted); border: 1px solid var(--border-default);" title="Clear search">
                            ✕
                        </button>
                        <span id="newsSearchMatchesBadge" class="hidden sm:inline-flex text-xs font-medium px-2 py-0.5 rounded border tabular-nums" style="background-color: var(--accent-subtle); border-color: var(--accent-fg); color: var(--accent-fg);"></span>
                    </div>
                </div>
            </div>

            <!-- News Filter Toolbar -->
            <div class="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-2.5 sm:gap-3 mb-4 p-2 sm:p-2.5 rounded-xl border shadow-xs" style="background-color: var(--canvas-subtle); border-color: var(--border-default);">
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

        <!-- SECTION 3: WHERE OFFERS ARE APPLIED (ZERO-DOLLAR REDEMPTION GUIDE) -->
        <div id="redemptionSection" class="hidden">
            <!-- Redemption Hero Bento Grid -->
            <div class="grid grid-cols-1 lg:grid-cols-12 gap-3.5 sm:gap-4 mb-5 sm:mb-8">
                <!-- Anchor Bento: Zero-Dollar Checkout Protocol -->
                <div class="lg:col-span-6 p-4 sm:p-6 rounded-2xl border primer-card relative overflow-hidden flex flex-col justify-between">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center gap-2">
                            <span class="w-2 h-2 rounded-full animate-pulse" style="background-color: var(--success-fg);"></span>
                            <span class="text-xs font-semibold uppercase tracking-wider" style="color: var(--fg-muted);">Redemption Protocol</span>
                        </div>
                        <span class="p-1.5 sm:p-2 rounded-lg flex-shrink-0" style="background-color: var(--success-subtle); color: var(--success-fg); border: 1px solid var(--success-fg);">
                            <svg width="18" height="18" viewBox="0 0 16 16" fill="currentColor"><path d="M13.78 4.22a.75.75 0 0 1 0 1.06l-7.25 7.25a.75.75 0 0 1-1.06 0L2.22 9.28a.751.751 0 0 1 .018-1.042.751.751 0 0 1 1.042-.018L6 10.94l6.72-6.72a.75.75 0 0 1 1.06 0Z"></path></svg>
                        </span>
                    </div>
                    <div class="mt-3 sm:mt-4">
                        <div class="text-2xl sm:text-4xl font-extrabold tracking-tight tabular-nums" style="color: var(--success-fg);">
                            $0.00 Balance <span class="text-xs sm:text-base font-normal font-sans" style="color: var(--fg-muted);">Verified Cart Total</span>
                        </div>
                        <p class="text-xs sm:text-sm mt-1.5 sm:mt-2 leading-relaxed text-pretty max-w-[65ch]" style="color: var(--fg-muted);">
                            Step-by-step guidance showing where to paste discount codes, claim SSO waivers, and verify your cart drops to $0.00 before exam checkout.
                        </p>
                    </div>
                </div>

                <!-- Bento 2: Delivery Portals -->
                <div class="lg:col-span-3 p-4 sm:p-6 rounded-2xl border primer-card flex flex-col justify-between">
                    <div class="flex items-center justify-between">
                        <span class="text-xs font-semibold uppercase tracking-wider" style="color: var(--fg-muted);">Accredited Portals</span>
                        <span class="p-1.5 sm:p-2 rounded-lg flex-shrink-0" style="background-color: var(--accent-subtle); color: var(--accent-fg); border: 1px solid var(--accent-fg);">
                            <svg width="18" height="18" viewBox="0 0 16 16" fill="currentColor"><path d="M11 2.25a.75.75 0 0 1 .75-.75h2.5a.75.75 0 0 1 .75.75v2.5a.75.75 0 0 1-1.5 0V3.56l-3.22 3.22a.75.75 0 1 1-1.06-1.06L11.44 2.5H11.75a.75.75 0 0 1-.75-.75Z"></path><path d="M2 3.75C2 2.784 2.784 2 3.75 2h4.5a.75.75 0 0 1 0 1.5h-4.5a.25.25 0 0 0-.25.25v8.5c0 .138.112.25.25.25h8.5a.25.25 0 0 0 .25-.25v-4.5a.75.75 0 0 1 1.5 0v4.5A1.75 1.75 0 0 1 12.25 14h-8.5A1.75 1.75 0 0 1 2 12.25v-8.5Z"></path></svg>
                        </span>
                    </div>
                    <div class="mt-3 sm:mt-4">
                        <div class="text-xl sm:text-3xl font-extrabold tracking-tight tabular-nums" style="color: var(--fg-default);">
                            6 Ecosystems <span class="text-xs sm:text-sm font-normal font-sans" style="color: var(--fg-muted);">Verified</span>
                        </div>
                        <p class="text-xs mt-1.5 sm:mt-2 leading-relaxed text-pretty" style="color: var(--fg-muted);">
                            Pearson VUE, Oracle MyLearn, Webassessor, Linux Foundation, Databricks Academy, Postman Academy.
                        </p>
                    </div>
                </div>

                <!-- Bento 3: Anti-Trap Guarantee -->
                <div class="lg:col-span-3 p-4 sm:p-6 rounded-2xl border primer-card flex flex-col justify-between">
                    <div class="flex items-center justify-between">
                        <span class="text-xs font-semibold uppercase tracking-wider" style="color: var(--fg-muted);">Zero-Fee Standard</span>
                        <span class="p-1.5 sm:p-2 rounded-lg flex-shrink-0" style="background-color: var(--attention-subtle); color: var(--attention-fg); border: 1px solid var(--attention-fg);">
                            <svg width="18" height="18" viewBox="0 0 16 16" fill="currentColor"><path d="M7.462.166a.75.75 0 0 1 .538 0l6.25 2.5a.75.75 0 0 1 .478.704c0 4.195-2.067 8.046-5.83 10.428a.75.75 0 0 1-.806 0C4.317 11.416 2.25 7.565 2.25 3.37a.75.75 0 0 1 .478-.704l6.25-2.5Zm.538 1.558L2.75 3.82c.117 3.518 1.83 6.758 4.996 8.847 3.165-2.089 4.88-5.329 4.996-8.847L8 1.724Z"></path></svg>
                        </span>
                    </div>
                    <div class="mt-3 sm:mt-4">
                        <div class="text-xl sm:text-3xl font-extrabold tracking-tight tabular-nums" style="color: var(--fg-default);">
                            Zero Traps <span class="text-xs sm:text-sm font-normal font-sans" style="color: var(--fg-muted);">Audited</span>
                        </div>
                        <p class="text-xs mt-1.5 sm:mt-2 leading-relaxed text-pretty" style="color: var(--fg-muted);">
                            Strictly no credit card input required on official 100% free vendor certification tracks.
                        </p>
                    </div>
                </div>
            </div>

            <!-- Redemption Search & Filter Controls -->
            <div class="p-3.5 sm:p-4 rounded-xl border mb-5 sm:mb-6" style="background-color: var(--canvas-subtle); border-color: var(--border-default);">
                <div class="flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
                    <div class="relative flex-1">
                        <input type="text" id="redemptionSearchInput" placeholder="Search by provider, certification, checkout portal, or voucher code..." 
                               oninput="renderRedemption()"
                               class="w-full text-xs sm:text-sm px-3.5 py-2 pl-9 rounded-lg border outline-none transition" 
                               style="background-color: var(--canvas-default); border-color: var(--border-default); color: var(--fg-default);">
                        <svg class="w-4 h-4 absolute left-3 top-2.5 pointer-events-none" style="color: var(--fg-muted);" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
                    </div>
                    <div class="flex items-center gap-2">
                        <select id="redemptionFlowFilter" onchange="renderRedemption()" class="text-xs sm:text-sm px-3 py-2 rounded-lg border outline-none font-medium cursor-pointer" style="background-color: var(--canvas-default); border-color: var(--border-default); color: var(--fg-default);">
                            <option value="all">All Application Flows</option>
                            <option value="Checkout Promo Code">Checkout Promo Code</option>
                            <option value="Automated Account Link Waiver">Automated Account Link Waiver</option>
                            <option value="Direct Assessment Launch">Direct Assessment Launch</option>
                            <option value="Scholarship Award Token">Scholarship Award Token</option>
                            <option value="Continuing Education Claim">Continuing Education Claim</option>
                        </select>
                    </div>
                </div>
            </div>

            <!-- Redemption Results Status Bar -->
            <div class="flex flex-col xs:flex-row items-start xs:items-center justify-between text-xs mb-4 px-1 gap-1" style="color: var(--fg-muted);">
                <div id="redemptionResultsCount">Showing {len(active_offers)} of {len(active_offers)} verified redemption protocols</div>
                <div>Checkout Assurance: <span class="font-medium text-xs" style="color: var(--success-fg);">100% Zero-Dollar ($0.00) Fee Verified</span></div>
            </div>

            <!-- Redemption Cards Grid -->
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5 sm:gap-4" id="redemptionGrid"></div>
        </div>

    </main>

    <!-- Footer -->
    <footer class="border-t py-6 sm:py-8 mt-10 sm:mt-12 text-center text-xs" style="background-color: var(--canvas-subtle); border-color: var(--border-default); color: var(--fg-muted); padding-bottom: max(1.5rem, calc(env(safe-area-inset-bottom, 0px) + 1.25rem));">
        <div class="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-3 sm:gap-4">
            <div class="text-balance">CertPulse — Open-Source Free Certification Tracker & Autonomous Intelligence Radar</div>
            <div class="flex items-center gap-4 flex-wrap justify-center">
                <a href="https://github.com/Athish2002/free-certification-tracker" target="_blank" class="hover:underline py-1" style="color: var(--accent-fg);">GitHub Repo</a>
                <a href="https://github.com/Athish2002/free-certification-tracker/issues/new/choose" target="_blank" class="hover:underline py-1" style="color: var(--accent-fg);">Submit Voucher</a>
                <a href="https://github.com/Athish2002/free-certification-tracker/actions" target="_blank" class="hover:underline py-1" style="color: var(--fg-muted);">CI Workflows</a>
            </div>
        </div>
    </footer>

    <!-- Screenshot Proof Lightbox Modal -->
    <div id="proofModal" class="hidden fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/75 backdrop-blur-md transition-all duration-200" role="dialog" aria-modal="true" aria-labelledby="proofModalTitle" onclick="handleProofModalBackdrop(event)">
        <div id="proofModalContent" class="relative w-full max-w-4xl max-h-[92dvh] flex flex-col rounded-2xl border shadow-2xl overflow-hidden" style="background-color: var(--canvas-default); border-color: var(--border-default);" onclick="event.stopPropagation()">
            <!-- Modal Header -->
            <div class="px-4 sm:px-6 py-3.5 sm:py-4 border-b flex items-center justify-between gap-3 flex-shrink-0" style="background-color: var(--canvas-subtle); border-color: var(--border-default);">
                <div class="min-w-0 flex-1">
                    <div class="flex items-center gap-2 mb-1 flex-wrap">
                        <span id="proofModalPlatform" class="font-bold text-xs" style="color: var(--fg-default);"></span>
                        <span id="proofModalTier" class="px-2 py-0.5 rounded text-[10px] font-bold border"></span>
                        <span id="proofModalTierBadge" class="hidden"></span>
                        <span id="proofModalBadge" class="px-2 py-0.5 rounded text-[10px] font-bold"></span>
                    </div>
                    <h3 id="proofModalTitle" class="font-bold text-sm sm:text-base leading-snug tracking-tight truncate text-balance" style="color: var(--fg-default);"></h3>
                    <div id="proofModalDate" class="text-xs mt-0.5 tabular-nums" style="color: var(--fg-muted);"></div>
                </div>
                <button onclick="closeProofModal()" id="closeProofModalBtn" aria-label="Close modal" class="min-w-[36px] min-h-[36px] w-9 h-9 rounded-lg text-sm font-bold flex items-center justify-center border hover:opacity-80 active:scale-[0.96] transition cursor-pointer flex-shrink-0" style="background-color: var(--canvas-inset); border-color: var(--border-default); color: var(--fg-muted);">
                    ✕
                </button>
            </div>

            <!-- Dynamic Status & Quarantine Alert Banner -->
            <div id="proofModalAlert" class="hidden px-4 sm:px-6 py-2.5 text-xs border-b flex items-start gap-2"></div>

            <!-- Modal Body (Hero Screenshot) -->
            <div class="relative flex-1 overflow-auto bg-black/5 dark:bg-black/40 p-2 sm:p-4 flex flex-col items-center justify-center min-h-[220px]">
                <img id="proofModalImage" src="" alt="Screenshot proof of zero-dollar certification terms" class="max-w-full max-h-[55dvh] sm:max-h-[60dvh] object-contain rounded-lg border shadow-sm transition-opacity" style="border-color: var(--border-default);">
                <div id="proofImageFallback" class="hidden text-xs text-center p-8" style="color: var(--fg-muted);">
                    <svg class="w-8 h-8 mx-auto mb-2 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
                    <span>Screenshot proof preview available in repository at <code class="font-mono" id="proofFallbackPath"></code></span>
                </div>
            </div>

            <!-- Truth Oracle Online Corroboration Card -->
            <div id="proofModalTruthCard" class="px-4 sm:px-6 py-2.5 border-t text-xs flex flex-col gap-1.5" style="background-color: var(--canvas-default); border-color: var(--border-default);">
                <div class="flex items-center justify-between gap-2 flex-wrap">
                    <div class="flex items-center gap-1.5 font-bold">
                        <span>🛡️ Online Truth Corroboration:</span>
                        <span id="proofModalPolicyType" class="px-1.5 py-0.5 rounded text-[10px] font-mono border"></span>
                    </div>
                    <div class="flex items-center gap-1.5">
                        <span class="text-muted">Primary Policy:</span>
                        <a id="proofModalTruthSource" href="#" target="_blank" rel="noopener" class="font-semibold underline hover:opacity-80 transition inline-flex items-center gap-1" style="color: var(--accent-fg);">
                            <span id="proofModalTruthSourceName">Vendor Policy</span>
                            <span>↗</span>
                        </a>
                    </div>
                </div>
                <p id="proofModalTruthNotes" class="text-[11px] leading-relaxed text-pretty" style="color: var(--fg-muted);"></p>
            </div>

            <!-- Modal Telemetry Strip & Action Footer -->
            <div class="px-4 sm:px-6 py-3 border-t flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs flex-shrink-0" style="background-color: var(--canvas-subtle); border-color: var(--border-default);">
                <div class="space-y-1 min-w-0">
                    <div class="flex items-center gap-2 flex-wrap">
                        <span class="font-semibold" style="color: var(--fg-default);">Capture Date:</span>
                        <span id="proofModalCapturedAt" class="font-mono tabular-nums" style="color: var(--fg-muted);"></span>
                        <span class="text-[10px] px-1.5 py-0.2 rounded font-medium border" style="background-color: var(--canvas-inset); border-color: var(--border-default); color: var(--fg-muted);">Headless Playwright</span>
                    </div>
                    <div class="flex items-center gap-2 flex-wrap">
                        <span class="font-semibold" style="color: var(--fg-default);">Voucher Terms:</span>
                        <span id="proofModalTerms" class="truncate" style="color: var(--success-fg);"></span>
                    </div>
                </div>
                <div class="flex items-center gap-2 flex-shrink-0">
                    <button onclick="closeProofModal()" class="px-3 py-1.5 rounded-lg border font-semibold transition active:scale-[0.98] cursor-pointer" style="background-color: var(--btn-default-bg); border-color: var(--border-default); color: var(--fg-default);">
                        Close
                    </button>
                    <a id="proofModalPortalLink" href="#" target="_blank" rel="noopener" class="px-3.5 py-1.5 rounded-lg text-white font-semibold transition active:scale-[0.98] inline-flex items-center gap-1.5 cursor-pointer shadow-xs" style="background-color: var(--btn-primary-bg);">
                        <span>Launch Official Portal</span>
                        <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor"><path d="M3.75 2h3.5a.75.75 0 0 1 0 1.5h-3.5a.25.25 0 0 0-.25.25v8.5c0 .138.112.25.25.25h8.5a.25.25 0 0 0 .25-.25v-3.5a.75.75 0 0 1 1.5 0v3.5A1.75 1.75 0 0 1 12.25 14h-8.5A1.75 1.75 0 0 1 2 12.25v-8.5C2 2.784 2.784 2 3.75 2Zm6.75.75a.75.75 0 0 1 .75-.75h3.5a.75.75 0 0 1 .75.75v3.5a.75.75 0 0 1-1.5 0V4.56L8.53 10.03a.75.75 0 0 1-1.06-1.06l5.47-5.47H11.25a.75.75 0 0 1-.75-.75Z"></path></svg>
                    </a>
                    <a id="proofModalDirectLink" href="#" target="_blank" rel="noopener" class="hidden"></a>
                </div>
            </div>
        </div>
    </div>

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
{client_script_bundle}
    </script>
</body>
</html>"""
