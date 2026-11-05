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
        "name": "GitHub Dark",
        "type": "dark",
        "dot": "#58a6ff",
        "meta": "#0d1117",
        "selector": ':root, [data-theme="github-dark"], [data-theme="dark"]',
        "tokens": {
            "--canvas-default": "#0d1117",
            "--canvas-subtle": "#161b22",
            "--canvas-inset": "#010409",
            "--border-default": "#30363d",
            "--border-muted": "#21262d",
            "--fg-default": "#e6edf3",
            "--fg-muted": "#848d97",
            "--fg-subtle": "#6e7681",
            "--accent-fg": "#58a6ff",
            "--accent-emphasis": "#1f6feb",
            "--accent-subtle": "rgba(56, 139, 253, 0.15)",
            "--success-fg": "#3fb950",
            "--success-emphasis": "#238636",
            "--success-subtle": "rgba(46, 160, 67, 0.15)",
            "--attention-fg": "#d29922",
            "--attention-subtle": "rgba(187, 128, 9, 0.15)",
            "--danger-fg": "#f85149",
            "--danger-subtle": "rgba(248, 81, 73, 0.15)",
            "--btn-default-bg": "#21262d",
            "--btn-default-hover": "#30363d",
            "--btn-primary-bg": "#238636",
            "--btn-primary-hover": "#2ea043",
            "--card-shadow": "0 0 0 1px rgba(255, 255, 255, 0.08), 0 2px 4px rgba(0, 0, 0, 0.2), 0 8px 24px -4px rgba(0, 0, 0, 0.4)",
            "--card-shadow-hover": "0 0 0 1px rgba(56, 139, 253, 0.45), 0 4px 12px rgba(0, 0, 0, 0.3), 0 20px 40px -8px rgba(0, 0, 0, 0.65)",
            "--specular-rim": "inset 0 1px 0 0 rgba(255, 255, 255, 0.12)",
        },
    },
    {
        "id": "github-light",
        "name": "GitHub Light",
        "type": "light",
        "dot": "#0969da",
        "meta": "#ffffff",
        "selector": '[data-theme="github-light"], [data-theme="light"]',
        "tokens": {
            "--canvas-default": "#ffffff",
            "--canvas-subtle": "#f6f8fa",
            "--canvas-inset": "#eaeef2",
            "--border-default": "#d0d7de",
            "--border-muted": "#afb8c1",
            "--fg-default": "#1f2328",
            "--fg-muted": "#656d76",
            "--fg-subtle": "#8c959f",
            "--accent-fg": "#0969da",
            "--accent-emphasis": "#0969da",
            "--accent-subtle": "#ddf4ff",
            "--success-fg": "#1a7f37",
            "--success-emphasis": "#1f883d",
            "--success-subtle": "#dafbe1",
            "--attention-fg": "#9a6700",
            "--attention-subtle": "#fff8c5",
            "--danger-fg": "#cf222e",
            "--danger-subtle": "#ffebe9",
            "--btn-default-bg": "#f6f8fa",
            "--btn-default-hover": "#eaeef2",
            "--btn-primary-bg": "#1f883d",
            "--btn-primary-hover": "#1a7f37",
            "--card-shadow": "0 0 0 1px rgba(31, 35, 40, 0.12), 0 1px 3px rgba(31, 35, 40, 0.04), 0 6px 16px rgba(31, 35, 40, 0.04)",
            "--card-shadow-hover": "0 0 0 1px #0969da, 0 4px 12px rgba(9, 105, 218, 0.12), 0 16px 32px -4px rgba(31, 35, 40, 0.12)",
            "--specular-rim": "inset 0 1px 0 0 rgba(255, 255, 255, 0.95)",
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
        box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.1), 0 8px 16px -4px rgba(0, 0, 0, 0.04), 0 20px 40px -8px rgba(0, 0, 0, 0.08);
        border-color: var(--accent-fg);
    }
    .primer-card:active {
        transform: translateY(-1px) scale(0.99);
    }
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
    """Inline <head> script preventing flash of unstyled content (FOIT/FOUC). Defaults to GitHub Dark with OS preference sync."""
    return """<script>
    (function() {
        try {
            const saved = localStorage.getItem('certpulse_theme_v2') || localStorage.getItem('certpulse_theme') || localStorage.getItem('theme');
            let chosen = saved;
            if (chosen !== 'github-light' && chosen !== 'github-dark') {
                const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
                chosen = prefersDark ? 'github-dark' : 'github-light';
            }
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
