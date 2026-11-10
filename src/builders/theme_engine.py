"""
Theme engine for CertPulse.
Defines canonical GitHub developer color palettes:
- GitHub Dark (default, dark mode)
- GitHub Light (light mode)
Generates CSS custom properties and provides inline Zero-FOIT styling scripts.
"""

import json
from typing import Any

DEFAULT_THEME = "github-dark"

THEMES: list[dict[str, Any]] = [
    {
        "id": "github-dark",
        "name": "Obsidian Cyan",
        "type": "dark",
        "dot": "#38bdf8",
        "meta": "#0d1117",
        "selector": ':root, [data-theme="github-dark"], [data-theme="dark"]',
        "tokens": {
            "--canvas-default": "#070a12",
            "--canvas-subtle": "#0e1422",
            "--canvas-inset": "#030508",
            "--border-default": "#1e293b",
            "--border-muted": "#0f172a",
            "--fg-default": "#f1f5f9",
            "--fg-muted": "#94a3b8",
            "--fg-subtle": "#64748b",
            "--accent-fg": "#38bdf8",
            "--accent-emphasis": "#0284c7",
            "--accent-subtle": "rgba(56, 189, 248, 0.15)",
            "--success-fg": "#34d399",
            "--success-emphasis": "#059669",
            "--success-subtle": "rgba(52, 211, 153, 0.15)",
            "--attention-fg": "#fbbf24",
            "--attention-subtle": "rgba(251, 191, 36, 0.15)",
            "--danger-fg": "#f87171",
            "--danger-subtle": "rgba(248, 113, 113, 0.15)",
            "--btn-default-bg": "#0e1422",
            "--btn-default-hover": "#1e293b",
            "--btn-primary-bg": "#0284c7",
            "--btn-primary-hover": "#0369a1",
            "--card-shadow": "3px 3px 0px 0px #030508",
            "--card-shadow-hover": "0 0 0 1px #38bdf8, 4px 4px 0px 0px #030508",
            "--specular-rim": "inset 0 1px 0 0 rgba(255, 255, 255, 0.08)",
            "--crt-line-color": "rgba(0, 0, 0, 0.28)",
        },
    },
    {
        "id": "github-light",
        "name": "Primer Crisp Light",
        "type": "light",
        "dot": "#0284c7",
        "meta": "#ffffff",
        "selector": '[data-theme="github-light"], [data-theme="light"]',
        "tokens": {
            "--canvas-default": "#ffffff",
            "--canvas-subtle": "#f8fafc",
            "--canvas-inset": "#f1f5f9",
            "--border-default": "#cbd5e1",
            "--border-muted": "#e2e8f0",
            "--fg-default": "#0f172a",
            "--fg-muted": "#334155",
            "--fg-subtle": "#64748b",
            "--accent-fg": "#0284c7",
            "--accent-emphasis": "#0369a1",
            "--accent-subtle": "rgba(2, 132, 199, 0.12)",
            "--success-fg": "#16a34a",
            "--success-emphasis": "#15803d",
            "--success-subtle": "rgba(22, 163, 74, 0.12)",
            "--attention-fg": "#b45309",
            "--attention-subtle": "rgba(180, 83, 9, 0.12)",
            "--danger-fg": "#dc2626",
            "--danger-subtle": "rgba(220, 38, 38, 0.12)",
            "--btn-default-bg": "#f8fafc",
            "--btn-default-hover": "#f1f5f9",
            "--btn-primary-bg": "#0284c7",
            "--btn-primary-hover": "#0369a1",
            "--card-shadow": "3px 3px 0px 0px #cbd5e1",
            "--card-shadow-hover": "0 0 0 1px #0284c7, 4px 4px 0px 0px #94a3b8",
            "--specular-rim": "inset 0 1px 0 0 rgba(255, 255, 255, 0.95)",
            "--crt-line-color": "transparent",
        },
    },
]

# Alias standard tokens and attach css_vars for ergonomic access
for _t in THEMES:
    _tok = _t["tokens"]
    _tok["--bg-primary"] = _tok.get("--canvas-default", "#0d1117")
    _tok["--bg-card"] = _tok.get("--canvas-subtle", "#161b22")
    _tok["--text-primary"] = _tok.get("--fg-default", "#e6edf3")
    _tok["--text-muted"] = _tok.get("--fg-muted", "#848d97")
    _tok["--border-color"] = _tok.get("--border-default", "#30363d")
    _tok["--accent-color"] = _tok.get("--accent-fg", "#58a6ff")
    _tok["--accent-bg"] = _tok.get("--accent-subtle", "rgba(56, 139, 253, 0.15)")
    _t["css_vars"] = _tok


def generate_css_variables() -> str:
    """Generates the unified CSS custom properties for GitHub Dark and GitHub Light."""
    lines: list[str] = [
        ":root {",
        "    --ease-out: cubic-bezier(0.23, 1, 0.32, 1);",
        "    --ease-out-expo: cubic-bezier(0.16, 1, 0.3, 1);",
        "}",
    ]

    for theme in THEMES:
        selector = theme["selector"]
        lines.append(f"\n/* {theme['name']} ({theme['type'].capitalize()}) */")
        lines.append(f"{selector} {{")
        for key, val in theme["tokens"].items():
            lines.append(f"    {key}: {val};")
        lines.append("}")

    # Standard UI utility classes
    lines.append("""
* {
    -webkit-tap-highlight-color: transparent;
}

body {
    background-color: var(--canvas-default);
    color: var(--fg-default);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif;
    transition: background-color 0.15s ease, color 0.15s ease;
    min-height: 100dvh;
}

/* STRICT INVARIANT: CRT scanlines strictly suppressed in Light Mode */
[data-theme="github-light"] .crt-scanlines,
[data-theme="light"] .crt-scanlines {
    background: none !important;
}

.crt-scanlines {
    background: linear-gradient(rgba(18, 16, 16, 0) 50%, var(--crt-line-color) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.02), rgba(0, 255, 0, 0.01), rgba(0, 0, 255, 0.02));
    background-size: 100% 3px, 6px 100%;
}

.primer-card {
    background-color: var(--canvas-subtle);
    border: 1px solid var(--border-default);
    box-shadow: var(--card-shadow), var(--specular-rim);
    transition: transform 180ms cubic-bezier(0.23, 1, 0.32, 1), 
                box-shadow 180ms cubic-bezier(0.23, 1, 0.32, 1), 
                border-color 180ms cubic-bezier(0.23, 1, 0.32, 1);
    position: relative;
}
@media (hover: hover) and (pointer: fine) {
    .primer-card:hover {
        transform: translateY(-2px);
        box-shadow: var(--card-shadow-hover);
        border-color: var(--accent-fg);
    }
    .primer-card:active {
        transform: translateY(-1px) scale(0.99);
    }
}

/* Cyber-Bento Brutal HUD utilities */
.neo-shadow {
    box-shadow: var(--card-shadow);
}
.neo-shadow-hover:hover {
    box-shadow: var(--card-shadow-hover);
}

/* ECG Waveform Telemetry Sweep & Latency Probe Animations */
@keyframes ecgSweep {
    0% { stroke-dashoffset: 60; }
    50% { stroke-dashoffset: 0; }
    100% { stroke-dashoffset: -60; }
}
.ecg-line-sweep {
    stroke-dasharray: 60 60;
    animation: ecgSweep 1.8s cubic-bezier(0.4, 0, 0.2, 1) infinite;
}
@keyframes ecgBlip {
    0%, 100% { transform: scale(0.6); opacity: 0.3; }
    45% { transform: scale(1.9); opacity: 1; filter: drop-shadow(0 0 7px #34d399); }
    60% { transform: scale(0.9); opacity: 0.5; }
}
.ecg-blip {
    animation: ecgBlip 1.8s cubic-bezier(0.4, 0, 0.2, 1) infinite;
    transform-origin: 20px 3px;
}

@keyframes latencyFlash {
    0% {
        transform: scale(1.24);
        color: #34d399;
        text-shadow: 0 0 10px rgba(16, 185, 129, 0.9);
    }
    100% {
        transform: scale(1);
        color: inherit;
        text-shadow: none;
    }
}
.latency-flash {
    display: inline-block;
    animation: latencyFlash 0.45s cubic-bezier(0.16, 1, 0.3, 1);
}

/* Marquee Ticker Tape Ribbon */
@keyframes marqueeTicker {
    0% { transform: translateX(0%); }
    100% { transform: translateX(-50%); }
}
.marquee-track {
    display: flex;
    width: max-content;
    animation: marqueeTicker 40s linear infinite;
}
.marquee-track:hover {
    animation-play-state: paused;
}

/* 3D Flip Card Mechanism */
.flip-card {
    perspective: 1000px;
}
.flip-card-inner {
    position: relative;
    width: 100%;
    transition: transform 0.6s cubic-bezier(0.23, 1, 0.32, 1);
    transform-style: preserve-3d;
}
.flip-card.is-flipped .flip-card-inner {
    transform: rotateY(180deg);
}
.flip-card-front, .flip-card-back {
    backface-visibility: hidden;
    -webkit-backface-visibility: hidden;
}
.flip-card-back {
    position: absolute;
    inset: 0;
    transform: rotateY(180deg);
    pointer-events: none;
}
.flip-card.is-flipped .flip-card-back {
    pointer-events: auto;
}
.flip-card.is-flipped .flip-card-front {
    pointer-events: none;
}

/* 14 Animated SVG Micro-Interactions Icons */
@keyframes bellRing {
    0%, 100% { transform: rotate(0); }
    20% { transform: rotate(14deg); }
    40% { transform: rotate(-14deg); }
    60% { transform: rotate(8deg); }
    80% { transform: rotate(-4deg); }
}
.bell-icon:hover, .group:hover .bell-icon {
    animation: bellRing 0.8s ease-in-out infinite;
    transform-origin: top center;
}

.lock-shackle {
    transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
    transform-origin: 7px 11px;
}
.lock-unlocked .lock-shackle {
    transform: translateY(-3px) rotate(-18deg);
}

@keyframes radarScan {
    0% { transform: scale(0.9); opacity: 0.8; }
    50% { transform: scale(1.15); opacity: 0.4; }
    100% { transform: scale(0.9); opacity: 0.8; }
}
.search-icon:hover svg, .group:hover .search-icon svg {
    animation: radarScan 1.2s ease-in-out infinite;
}

@keyframes sparkFlash {
    0%, 100% { transform: scale(1); filter: drop-shadow(0 0 0 transparent); }
    50% { transform: scale(1.22); filter: drop-shadow(0 0 8px rgba(251, 191, 36, 0.8)); }
}
.spark-icon:hover svg, .group:hover .spark-icon svg {
    animation: sparkFlash 0.6s cubic-bezier(0.23, 1, 0.32, 1) infinite;
}

@keyframes shieldSweep {
    0% { top: -20%; opacity: 0; }
    50% { opacity: 0.9; }
    100% { top: 120%; opacity: 0; }
}
.shield-scan-beam {
    animation: shieldSweep 2s ease-in-out infinite;
}

.code-icon:hover .bracket-left {
    transform: translateX(-2.5px);
    transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.code-icon:hover .bracket-right {
    transform: translateX(2.5px);
    transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
}

@keyframes flameFlicker {
    0%, 100% { transform: scale(1) rotate(0deg); }
    25% { transform: scale(1.08, 0.95) rotate(-2deg); }
    50% { transform: scale(0.96, 1.05) rotate(2deg); }
    75% { transform: scale(1.04, 0.98) rotate(-1deg); }
}
.flame-anim:hover svg, .group:hover .flame-anim svg {
    animation: flameFlicker 0.6s ease-in-out infinite;
    transform-origin: bottom center;
}

@keyframes compassSpin {
    0% { transform: rotate(0deg); }
    50% { transform: rotate(180deg); }
    100% { transform: rotate(360deg); }
}
.compass-needle {
    transform-origin: 12px 12px;
    transition: transform 0.8s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.group:hover .compass-needle, button:hover .compass-needle {
    transform: rotate(360deg);
}

@keyframes downloadBounce {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(3px); }
}
.download-arrow {
    animation: downloadBounce 1s ease-in-out infinite;
}

.spin-hover:hover svg {
    animation: compassSpin 0.9s linear infinite;
}

/* Audio Waveform Equalizer Dancing Bars */
@keyframes eqDance {
    0%, 100% { height: 4px; }
    50% { height: 14px; }
}
.eq-bar-1 { animation: eqDance 0.8s ease-in-out infinite; }
.eq-bar-2 { animation: eqDance 0.8s ease-in-out infinite 0.2s; }
.eq-bar-3 { animation: eqDance 0.8s ease-in-out infinite 0.4s; }

/* Animated Shimmer Progress Bar with Leading Pulse Dot */
@keyframes shimmerMove {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
}
.shimmer-progress {
    background: linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.3) 50%, rgba(255,255,255,0) 100%);
    background-size: 200% 100%;
    animation: shimmerMove 2s infinite;
}

.primer-card, [data-proof-id] {
    scroll-margin-top: 80px;
}

button, a.cursor-pointer, .btn, .tier-pill, .cat-pill, .news-cat-pill {
    transition: transform 140ms cubic-bezier(0.23, 1, 0.32, 1),
                filter 140ms cubic-bezier(0.23, 1, 0.32, 1),
                background-color 140ms cubic-bezier(0.23, 1, 0.32, 1),
                border-color 140ms cubic-bezier(0.23, 1, 0.32, 1),
                box-shadow 140ms cubic-bezier(0.23, 1, 0.32, 1);
    cursor: pointer;
    position: relative;
    z-index: 10;
}
@media (hover: hover) and (pointer: fine) {
    .tier-pill:hover, .cat-pill:hover, .news-cat-pill:hover {
        transform: translateY(-1.5px);
        box-shadow: 0 4px 12px -2px rgba(0, 0, 0, 0.08);
    }
}
button:active, a.cursor-pointer:active, a.tactile-btn:active, .tier-pill:active, .cat-pill:active, .news-cat-pill:active {
    transform: scale(0.98);
    filter: brightness(0.95);
}

input:focus-visible, select:focus-visible, button:focus-visible, a:focus-visible {
    outline: 2px solid var(--accent-fg);
    outline-offset: 2px;
}

.touch-scroll {
    -webkit-overflow-scrolling: touch;
    scroll-behavior: smooth;
    overscroll-behavior-x: contain;
}

::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}
::-webkit-scrollbar-thumb {
    background: var(--border-default);
    border-radius: 3px;
}

.scrollbar-none::-webkit-scrollbar {
    display: none;
}
.scrollbar-none {
    -ms-overflow-style: none;
    scrollbar-width: none;
}

@media (max-width: 640px) {
    input[type="text"], select {
        font-size: 16px !important;
    }
}
""")

    return "\n".join(lines)


def generate_zero_foit_script() -> str:
    """Inline <head> script preventing flash of unstyled content (FOIT/FOUC). Defaults to GitHub Dark (Obsidian Cyan)."""
    return """<script>
    (function() {
        try {
            const saved = localStorage.getItem('certpulse_theme_v2') || localStorage.getItem('certpulse_theme') || localStorage.getItem('theme');
            let chosen = (saved === 'github-light') ? 'github-light' : 'github-dark';
            document.documentElement.setAttribute('data-theme', chosen);
            const metaTheme = document.querySelector('meta[name="theme-color"]');
            if (metaTheme) {
                metaTheme.setAttribute('content', chosen === 'github-light' ? '#ffffff' : '#0d1117');
            }
        } catch(e) {}
    })();
    </script>"""


def generate_theme_dropdown_html() -> str:
    """Legacy helper: returns empty string as dropdown is retired in favor of clean Dark/Light toggle."""
    return ""


def get_theme_by_id(theme_id: str) -> dict[str, Any]:
    """Retrieve theme dictionary by ID, falling back to GitHub Dark / Light."""
    for theme in THEMES:
        if theme["id"] == theme_id:
            return theme
    if theme_id in ("light", "github-light", "catppuccin-latte", "solarized-light"):
        return THEMES[1]  # github-light
    return THEMES[0]  # github-dark default


def get_theme_json() -> str:
    """Returns JSON string of active themes."""
    return json.dumps(THEMES)


def generate_theme_dropdown_options() -> str:
    """Emits HTML option tags for GitHub Dark and GitHub Light."""
    options = []
    for t in THEMES:
        selected = " selected" if t["id"] == DEFAULT_THEME else ""
        options.append(f'<option value="{t["id"]}"{selected}>{t["name"]} ({t["type"]})</option>')
    return "\n".join(options)
