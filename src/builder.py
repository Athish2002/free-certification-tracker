"""
Builder module for CertPulse.
Compiles data/offers.json into:
1. Production-grade GitHub README.md with executive Bento stats, verified voucher tables, and inspection badges.
2. docs/index.html - Static interactive web dashboard for GitHub Pages with live search and status filters.
"""

import json
from pathlib import Path
from datetime import datetime
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
    
    total_savings = sum(o.get("value_usd", 0) for o in active_offers)
    last_updated = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    
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
    """Generates a responsive single-page web dashboard with live search and status filters."""
    offers = data.get("offers", [])
    active_offers = [o for o in offers if o.get("status") == "Active"]
    total_savings = sum(o.get("value_usd", 0) for o in active_offers)
    
    offers_json_str = json.dumps(offers)
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CertPulse - Free Cloud & Tech Certification Tracker</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {{
            darkMode: 'class',
            theme: {{
                extend: {{
                    colors: {{
                        brand: '#2563eb'
                    }}
                }}
            }}
        }}
    </script>
</head>
<body class="bg-slate-900 text-slate-100 min-h-screen antialiased">
    <!-- Header -->
    <header class="border-b border-slate-800 bg-slate-950/80 backdrop-blur sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex flex-col md:flex-row justify-between items-center gap-4">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center font-bold text-xl shadow-lg shadow-blue-500/20">CP</div>
                <div>
                    <h1 class="text-xl font-bold tracking-tight text-white flex items-center gap-2">
                        CertPulse 
                        <span class="text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded-full">Live Tracker</span>
                    </h1>
                    <p class="text-xs text-slate-400">Autonomous Free Certification & Deep Inspection Engine</p>
                </div>
            </div>
            <div class="flex items-center gap-3">
                <span class="text-xs text-slate-400 bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700">
                    Auto-inspected for Soft 404s & Closed Windows
                </span>
            </div>
        </div>
    </header>

    <!-- Hero Bento Banner -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
            <div class="bg-gradient-to-br from-blue-900/40 to-slate-800/40 border border-blue-700/30 rounded-2xl p-6 shadow-sm">
                <span class="text-xs font-semibold uppercase tracking-wider text-blue-400">Total Value Available</span>
                <div class="text-3xl font-extrabold text-white mt-2">${total_savings:,} <span class="text-sm font-normal text-slate-400">USD</span></div>
                <p class="text-xs text-slate-400 mt-2">Aggregate value of active verified certifications listed.</p>
            </div>
            <div class="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-6 shadow-sm">
                <span class="text-xs font-semibold uppercase tracking-wider text-emerald-400">Tracked Opportunities</span>
                <div class="text-3xl font-extrabold text-white mt-2">{len(offers)} <span class="text-sm font-normal text-slate-400">Programs</span></div>
                <p class="text-xs text-slate-400 mt-2">{len(active_offers)} currently active and accepting registrations.</p>
            </div>
            <div class="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-6 shadow-sm">
                <span class="text-xs font-semibold uppercase tracking-wider text-purple-400">Inspection Guardian</span>
                <div class="text-3xl font-extrabold text-white mt-2">100% Free <span class="text-sm font-normal text-slate-400">at $0 Cost</span></div>
                <p class="text-xs text-slate-400 mt-2">Automated soft-404 heuristics running on GitHub Actions.</p>
            </div>
        </div>

        <!-- Filter Controls -->
        <div class="flex flex-col md:flex-row justify-between items-center gap-4 mb-6">
            <div class="relative w-full md:w-96">
                <input type="text" id="searchInput" placeholder="Search by provider, certification, skill..." 
                       class="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-blue-500 placeholder-slate-500">
            </div>
            <div class="flex gap-2 overflow-x-auto w-full md:w-auto pb-2 md:pb-0" id="filterPills">
                <button onclick="filterCategory('All')" class="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-blue-600 text-white whitespace-nowrap pill-btn" data-cat="All">All Categories</button>
                <button onclick="filterCategory('Security')" class="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-slate-800 text-slate-400 hover:text-white whitespace-nowrap pill-btn" data-cat="Security">Security</button>
                <button onclick="filterCategory('Cloud')" class="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-slate-800 text-slate-400 hover:text-white whitespace-nowrap pill-btn" data-cat="Cloud">Cloud</button>
                <button onclick="filterCategory('AI & Data')" class="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-slate-800 text-slate-400 hover:text-white whitespace-nowrap pill-btn" data-cat="AI & Data">AI & Data</button>
                <button onclick="filterCategory('DevOps')" class="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-slate-800 text-slate-400 hover:text-white whitespace-nowrap pill-btn" data-cat="DevOps">DevOps</button>
                <button onclick="filterCategory('Networking')" class="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-slate-800 text-slate-400 hover:text-white whitespace-nowrap pill-btn" data-cat="Networking">Networking</button>
            </div>
        </div>

        <!-- Cards Grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5" id="offersGrid">
            <!-- Dynamically populated via JavaScript -->
        </div>
    </main>

    <footer class="border-t border-slate-800 mt-16 py-8 text-center text-xs text-slate-500">
        <p>CertPulse is an open-source, community-driven zero-cost initiative.</p>
    </footer>

    <script>
        const offersData = {offers_json_str};
        let currentCategory = 'All';
        let currentSearch = '';

        function getStatusBadge(status) {{
            if (status === 'Active') {{
                return '<span class="text-xs font-semibold px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">🟢 Active</span>';
            }} else if (status === 'Registrations Closed') {{
                return '<span class="text-xs font-semibold px-2 py-0.5 rounded-md bg-amber-500/10 text-amber-400 border border-amber-500/30">🟡 Closed / Waitlist</span>';
            }} else {{
                return '<span class="text-xs font-semibold px-2 py-0.5 rounded-md bg-rose-500/10 text-rose-400 border border-rose-500/30">🔴 Expired</span>';
            }}
        }}

        function renderCards() {{
            const grid = document.getElementById('offersGrid');
            const filtered = offersData.filter(o => {{
                const matchesCat = currentCategory === 'All' || o.category.includes(currentCategory) || o.platform.includes(currentCategory);
                const text = (o.title + ' ' + o.platform + ' ' + o.certification_name + ' ' + o.category).toLowerCase();
                const matchesSearch = text.includes(currentSearch.toLowerCase());
                return matchesCat && matchesSearch;
            }});

            if (filtered.length === 0) {{
                grid.innerHTML = '<div class="col-span-full text-center py-12 text-slate-500">No vouchers found matching your search.</div>';
                return;
            }}

            grid.innerHTML = filtered.map(o => `
                <div class="bg-slate-800/60 border border-slate-700/60 hover:border-slate-600 rounded-2xl p-5 flex flex-col justify-between transition group shadow-sm hover:shadow-md">
                    <div>
                        <div class="flex justify-between items-start gap-2 mb-3">
                            <span class="text-xs font-medium px-2.5 py-1 rounded-md bg-slate-700 text-blue-400 border border-slate-600/50">${{o.platform}}</span>
                            <div class="flex items-center gap-2">
                                ${{getStatusBadge(o.status)}}
                                <span class="text-xs font-bold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-md">$${{o.value_usd}} USD</span>
                            </div>
                        </div>
                        <h3 class="text-base font-bold text-white group-hover:text-blue-400 transition leading-snug">${{o.title}}</h3>
                        <p class="text-xs text-slate-400 mt-2 line-clamp-3">${{o.claim_steps}}</p>
                    </div>
                    <div class="mt-5 pt-4 border-t border-slate-700/50 flex items-center justify-between">
                        <span class="text-xs text-slate-500">${{o.eligibility}}</span>
                        <a href="${{o.url}}" target="_blank" class="text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white px-3.5 py-1.5 rounded-lg transition shadow-sm">
                            ${{o.status === 'Active' ? 'Claim Free &rarr;' : 'View Program &rarr;'}}
                        </a>
                    </div>
                </div>
            `).join('');
        }}

        function filterCategory(cat) {{
            currentCategory = cat;
            document.querySelectorAll('.pill-btn').forEach(btn => {{
                if (btn.getAttribute('data-cat') === cat) {{
                    btn.classList.remove('bg-slate-800', 'text-slate-400');
                    btn.classList.add('bg-blue-600', 'text-white');
                }} else {{
                    btn.classList.add('bg-slate-800', 'text-slate-400');
                    btn.classList.remove('bg-blue-600', 'text-white');
                }}
            }});
            renderCards();
        }}

        document.getElementById('searchInput').addEventListener('input', (e) => {{
            currentSearch = e.target.value;
            renderCards();
        }});

        // Initial render
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
