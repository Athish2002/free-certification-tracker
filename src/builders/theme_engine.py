"""
Theme engine for CertPulse.
Defines 10 iconic developer color palettes (Catppuccin Latte default, Catppuccin Mocha,
GitHub Dark, GitHub Light, Dracula, Nord, Tokyo Night, One Dark, Gruvbox Dark, Solarized Light),
generates CSS custom properties, and provides inline Zero-FOIT styling scripts.
"""

import json
from typing import Dict, Any, List

DEFAULT_THEME = "catppuccin-latte"

THEMES: List[Dict[str, Any]] = [
    {
        "id": "catppuccin-latte",
        "name": "Catppuccin Latte",
        "type": "light",
        "dot": "#1e66f5",
        "meta": "#eff1f5",
        "selector": ':root, [data-theme="catppuccin-latte"], [data-theme="light"]',
        "tokens": {
            "--canvas-default": "#eff1f5",
            "--canvas-subtle": "#e6e9ef",
            "--canvas-inset": "#dce0e8",
            "--border-default": "#ccd0da",
            "--border-muted": "#bcc0cc",
            "--fg-default": "#4c4f69",
            "--fg-muted": "#5c5f77",
            "--fg-subtle": "#6c6f85",
            "--accent-fg": "#1e66f5",
            "--accent-emphasis": "#1e66f5",
            "--accent-subtle": "rgba(30, 102, 245, 0.12)",
            "--success-fg": "#40a02b",
            "--success-emphasis": "#40a02b",
            "--success-subtle": "rgba(64, 160, 43, 0.12)",
            "--attention-fg": "#df8e1d",
            "--attention-subtle": "rgba(223, 142, 29, 0.12)",
            "--danger-fg": "#d20f39",
            "--danger-subtle": "rgba(210, 15, 57, 0.12)",
            "--btn-default-bg": "#e6e9ef",
            "--btn-default-hover": "#dce0e8",
            "--btn-primary-bg": "#1e66f5",
            "--btn-primary-hover": "#04a5e5",
            "--card-shadow": "0 1px 3px 0 rgba(76, 79, 105, 0.08), 0 1px 2px -1px rgba(76, 79, 105, 0.06)",
            "--card-shadow-hover": "0 4px 6px -1px rgba(76, 79, 105, 0.12), 0 2px 4px -2px rgba(76, 79, 105, 0.06)",
            "--specular-rim": "inset 0 1px 1px 0 rgba(255, 255, 255, 0.6)",
        },
    },
    {
        "id": "catppuccin-mocha",
        "name": "Catppuccin Mocha",
        "type": "dark",
        "dot": "#cba6f7",
        "meta": "#1e1e2e",
        "selector": '[data-theme="catppuccin-mocha"]',
        "tokens": {
            "--canvas-default": "#1e1e2e",
            "--canvas-subtle": "#181825",
            "--canvas-inset": "#11111b",
            "--border-default": "#313244",
            "--border-muted": "#45475a",
            "--fg-default": "#cdd6f4",
            "--fg-muted": "#a6adc8",
            "--fg-subtle": "#9399b2",
            "--accent-fg": "#89b4fa",
            "--accent-emphasis": "#cba6f7",
            "--accent-subtle": "rgba(203, 166, 247, 0.15)",
            "--success-fg": "#a6e3a1",
            "--success-emphasis": "#a6e3a1",
            "--success-subtle": "rgba(166, 227, 161, 0.15)",
            "--attention-fg": "#f9e2af",
            "--attention-subtle": "rgba(249, 226, 175, 0.15)",
            "--danger-fg": "#f38ba8",
            "--danger-subtle": "rgba(243, 139, 168, 0.15)",
            "--btn-default-bg": "#313244",
            "--btn-default-hover": "#45475a",
            "--btn-primary-bg": "#89b4fa",
            "--btn-primary-hover": "#b4befe",
            "--card-shadow": "0 1px 3px 0 rgba(0, 0, 0, 0.3)",
            "--card-shadow-hover": "0 4px 6px -1px rgba(0, 0, 0, 0.45)",
            "--specular-rim": "inset 0 1px 1px 0 rgba(255, 255, 255, 0.05)",
        },
    },
    {
        "id": "github-dark",
        "name": "GitHub Dark",
        "type": "dark",
        "dot": "#58a6ff",
        "meta": "#0d1117",
        "selector": '[data-theme="github-dark"], [data-theme="dark"]',
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
        "selector": '[data-theme="github-light"]',
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
    {
        "id": "dracula",
        "name": "Dracula",
        "type": "dark",
        "dot": "#bd93f9",
        "meta": "#282a36",
        "selector": '[data-theme="dracula"]',
        "tokens": {
            "--canvas-default": "#282a36",
            "--canvas-subtle": "#21222c",
            "--canvas-inset": "#191a21",
            "--border-default": "#44475a",
            "--border-muted": "#6272a4",
            "--fg-default": "#f8f8f2",
            "--fg-muted": "#6272a4",
            "--fg-subtle": "#ff79c6",
            "--accent-fg": "#bd93f9",
            "--accent-emphasis": "#bd93f9",
            "--accent-subtle": "rgba(189, 147, 249, 0.15)",
            "--success-fg": "#50fa7b",
            "--success-emphasis": "#50fa7b",
            "--success-subtle": "rgba(80, 250, 123, 0.15)",
            "--attention-fg": "#f1fa8c",
            "--attention-subtle": "rgba(241, 250, 140, 0.15)",
            "--danger-fg": "#ff5555",
            "--danger-subtle": "rgba(255, 85, 85, 0.15)",
            "--btn-default-bg": "#44475a",
            "--btn-default-hover": "#6272a4",
            "--btn-primary-bg": "#bd93f9",
            "--btn-primary-hover": "#ff79c6",
            "--card-shadow": "0 1px 3px 0 rgba(0, 0, 0, 0.4)",
            "--card-shadow-hover": "0 4px 6px -1px rgba(0, 0, 0, 0.5)",
            "--specular-rim": "inset 0 1px 1px 0 rgba(255, 255, 255, 0.05)",
        },
    },
    {
        "id": "nord",
        "name": "Nord",
        "type": "dark",
        "dot": "#88c0d0",
        "meta": "#2e3440",
        "selector": '[data-theme="nord"]',
        "tokens": {
            "--canvas-default": "#2e3440",
            "--canvas-subtle": "#3b4252",
            "--canvas-inset": "#242933",
            "--border-default": "#434c5e",
            "--border-muted": "#4c566a",
            "--fg-default": "#eceff4",
            "--fg-muted": "#d8dee9",
            "--fg-subtle": "#e5e9f0",
            "--accent-fg": "#88c0d0",
            "--accent-emphasis": "#81a1c1",
            "--accent-subtle": "rgba(136, 192, 208, 0.15)",
            "--success-fg": "#a3be8c",
            "--success-emphasis": "#a3be8c",
            "--success-subtle": "rgba(163, 190, 140, 0.15)",
            "--attention-fg": "#ebcb8b",
            "--attention-subtle": "rgba(235, 203, 139, 0.15)",
            "--danger-fg": "#bf616a",
            "--danger-subtle": "rgba(191, 97, 106, 0.15)",
            "--btn-default-bg": "#434c5e",
            "--btn-default-hover": "#4c566a",
            "--btn-primary-bg": "#88c0d0",
            "--btn-primary-hover": "#81a1c1",
            "--card-shadow": "0 1px 3px 0 rgba(0, 0, 0, 0.35)",
            "--card-shadow-hover": "0 4px 6px -1px rgba(0, 0, 0, 0.45)",
            "--specular-rim": "inset 0 1px 1px 0 rgba(255, 255, 255, 0.05)",
        },
    },
    {
        "id": "tokyo-night",
        "name": "Tokyo Night",
        "type": "dark",
        "dot": "#7aa2f7",
        "meta": "#1a1b26",
        "selector": '[data-theme="tokyo-night"]',
        "tokens": {
            "--canvas-default": "#1a1b26",
            "--canvas-subtle": "#16161e",
            "--canvas-inset": "#0f0f14",
            "--border-default": "#292e42",
            "--border-muted": "#3b4261",
            "--fg-default": "#c0caf5",
            "--fg-muted": "#9aa5ce",
            "--fg-subtle": "#565f89",
            "--accent-fg": "#7aa2f7",
            "--accent-emphasis": "#7aa2f7",
            "--accent-subtle": "rgba(122, 162, 247, 0.15)",
            "--success-fg": "#9ece6a",
            "--success-emphasis": "#9ece6a",
            "--success-subtle": "rgba(158, 206, 106, 0.15)",
            "--attention-fg": "#e0af68",
            "--attention-subtle": "rgba(224, 175, 104, 0.15)",
            "--danger-fg": "#f7768e",
            "--danger-subtle": "rgba(247, 118, 142, 0.15)",
            "--btn-default-bg": "#292e42",
            "--btn-default-hover": "#3b4261",
            "--btn-primary-bg": "#7aa2f7",
            "--btn-primary-hover": "#bb9af7",
            "--card-shadow": "0 1px 3px 0 rgba(0, 0, 0, 0.4)",
            "--card-shadow-hover": "0 4px 6px -1px rgba(0, 0, 0, 0.5)",
            "--specular-rim": "inset 0 1px 1px 0 rgba(255, 255, 255, 0.05)",
        },
    },
    {
        "id": "one-dark",
        "name": "One Dark",
        "type": "dark",
        "dot": "#61afef",
        "meta": "#282c34",
        "selector": '[data-theme="one-dark"]',
        "tokens": {
            "--canvas-default": "#282c34",
            "--canvas-subtle": "#21252b",
            "--canvas-inset": "#1b1d23",
            "--border-default": "#3b4048",
            "--border-muted": "#4b5263",
            "--fg-default": "#abb2bf",
            "--fg-muted": "#7f848e",
            "--fg-subtle": "#5c6370",
            "--accent-fg": "#61afef",
            "--accent-emphasis": "#61afef",
            "--accent-subtle": "rgba(97, 175, 239, 0.15)",
            "--success-fg": "#98c379",
            "--success-emphasis": "#98c379",
            "--success-subtle": "rgba(152, 195, 121, 0.15)",
            "--attention-fg": "#e5c07b",
            "--attention-subtle": "rgba(229, 192, 123, 0.15)",
            "--danger-fg": "#e06c75",
            "--danger-subtle": "rgba(224, 108, 117, 0.15)",
            "--btn-default-bg": "#3b4048",
            "--btn-default-hover": "#4b5263",
            "--btn-primary-bg": "#61afef",
            "--btn-primary-hover": "#c678dd",
            "--card-shadow": "0 1px 3px 0 rgba(0, 0, 0, 0.35)",
            "--card-shadow-hover": "0 4px 6px -1px rgba(0, 0, 0, 0.45)",
            "--specular-rim": "inset 0 1px 1px 0 rgba(255, 255, 255, 0.05)",
        },
    },
    {
        "id": "gruvbox-dark",
        "name": "Gruvbox Dark",
        "type": "dark",
        "dot": "#fe8019",
        "meta": "#282828",
        "selector": '[data-theme="gruvbox-dark"]',
        "tokens": {
            "--canvas-default": "#282828",
            "--canvas-subtle": "#1d2021",
            "--canvas-inset": "#141617",
            "--border-default": "#3c3836",
            "--border-muted": "#504945",
            "--fg-default": "#ebdbb2",
            "--fg-muted": "#a89984",
            "--fg-subtle": "#928374",
            "--accent-fg": "#fe8019",
            "--accent-emphasis": "#fe8019",
            "--accent-subtle": "rgba(254, 128, 25, 0.15)",
            "--success-fg": "#b8bb26",
            "--success-emphasis": "#b8bb26",
            "--success-subtle": "rgba(184, 187, 38, 0.15)",
            "--attention-fg": "#fabd2f",
            "--attention-subtle": "rgba(250, 189, 47, 0.15)",
            "--danger-fg": "#fb4934",
            "--danger-subtle": "rgba(251, 73, 52, 0.15)",
            "--btn-default-bg": "#3c3836",
            "--btn-default-hover": "#504945",
            "--btn-primary-bg": "#fe8019",
            "--btn-primary-hover": "#fabd2f",
            "--card-shadow": "0 1px 3px 0 rgba(0, 0, 0, 0.4)",
            "--card-shadow-hover": "0 4px 6px -1px rgba(0, 0, 0, 0.5)",
            "--specular-rim": "inset 0 1px 1px 0 rgba(255, 255, 255, 0.05)",
        },
    },
    {
        "id": "solarized-light",
        "name": "Solarized Light",
        "type": "light",
        "dot": "#2aa198",
        "meta": "#fdf6e3",
        "selector": '[data-theme="solarized-light"]',
        "tokens": {
            "--canvas-default": "#fdf6e3",
            "--canvas-subtle": "#eee8d5",
            "--canvas-inset": "#e0d8c3",
            "--border-default": "#cb4b16",
            "--border-muted": "#93a1a1",
            "--fg-default": "#657b83",
            "--fg-muted": "#586e75",
            "--fg-subtle": "#839496",
            "--accent-fg": "#268bd2",
            "--accent-emphasis": "#268bd2",
            "--accent-subtle": "rgba(38, 139, 210, 0.12)",
            "--success-fg": "#859900",
            "--success-emphasis": "#859900",
            "--success-subtle": "rgba(133, 153, 0, 0.12)",
            "--attention-fg": "#b58900",
            "--attention-subtle": "rgba(181, 137, 0, 0.12)",
            "--danger-fg": "#dc322f",
            "--danger-subtle": "rgba(220, 50, 47, 0.12)",
            "--btn-default-bg": "#eee8d5",
            "--btn-default-hover": "#e0d8c3",
            "--btn-primary-bg": "#268bd2",
            "--btn-primary-hover": "#2aa198",
            "--card-shadow": "0 1px 3px 0 rgba(101, 123, 131, 0.1)",
            "--card-shadow-hover": "0 4px 6px -1px rgba(101, 123, 131, 0.15)",
            "--specular-rim": "inset 0 1px 1px 0 rgba(255, 255, 255, 0.8)",
        },
    },
]

# Alias standard tokens and attach css_vars for ergonomic access
for _t in THEMES:
    _tok = _t["tokens"]
    _tok["--bg-primary"] = _tok.get("--canvas-default", "#eff1f5")
    _tok["--bg-card"] = _tok.get("--canvas-subtle", "#e6e9ef")
    _tok["--text-primary"] = _tok.get("--fg-default", "#4c4f69")
    _tok["--text-muted"] = _tok.get("--fg-muted", "#5c5f77")
    _tok["--border-color"] = _tok.get("--border-default", "#ccd0da")
    _tok["--accent-color"] = _tok.get("--accent-fg", "#1e66f5")
    _tok["--accent-bg"] = _tok.get("--accent-subtle", "rgba(30, 102, 245, 0.12)")
    _t["css_vars"] = _tok


def generate_css_variables() -> str:
    """Generates the unified CSS custom properties for all 10 developer themes."""
    lines: List[str] = [
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
    transition: transform 180ms var(--ease-out), 
                box-shadow 180ms var(--ease-out), 
                border-color 150ms ease;
}
@media (hover: hover) and (pointer: fine) {
    .primer-card:hover {
        transform: translateY(-3px);
        box-shadow: var(--card-shadow-hover), var(--specular-rim);
        border-color: var(--accent-fg);
    }
}

button:active, a.tactile-btn:active {
    transform: scale(0.98);
    transition: transform 80ms var(--ease-out);
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

/* Theme Item in Dropdown */
.theme-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 7px 10px;
    border-radius: 8px;
    cursor: pointer;
    transition: background 0.12s;
}
.theme-item:hover {
    background: var(--btn-default-bg);
}
""")

    return "\n".join(lines)


def generate_zero_foit_script() -> str:
    """Inline <head> script preventing flash of unstyled content (FOIT/FOUC)."""
    return """<script>
    // Inline Zero-FOIT theme initialization (default: catppuccin-latte)
    (function() {
        try {
            const saved = localStorage.getItem('certpulse_theme_v2') || localStorage.getItem('certpulse_theme') || localStorage.getItem('theme') || 'catppuccin-latte';
            const valid = ['catppuccin-latte', 'catppuccin-mocha', 'github-dark', 'github-light', 'dracula', 'nord', 'tokyo-night', 'one-dark', 'gruvbox-dark', 'solarized-light', 'light', 'dark'];
            const chosen = valid.includes(saved) ? saved : 'catppuccin-latte';
            document.documentElement.setAttribute('data-theme', chosen);
            const metaTheme = document.querySelector('meta[name="theme-color"]');
            if (metaTheme) {
                const metaMap = {'catppuccin-latte':'#eff1f5','catppuccin-mocha':'#1e1e2e','github-dark':'#0d1117','github-light':'#ffffff','dracula':'#282a36','nord':'#2e3440','tokyo-night':'#1a1b26','one-dark':'#282c34','gruvbox-dark':'#282828','solarized-light':'#fdf6e3'};
                if (metaMap[chosen]) metaTheme.setAttribute('content', metaMap[chosen]);
            }
        } catch(e) {}
    })();
    </script>"""


def generate_theme_dropdown_html() -> str:
    """Emits the dropdown menu markup for all 10 developer themes."""
    items_html = []
    for t in THEMES:
        items_html.append(f"""
        <div class="theme-item text-xs font-medium" onclick="selectTheme('{t['id']}')">
            <div class="flex items-center gap-2">
                <span class="w-3 h-3 rounded-full flex-shrink-0" style="background-color: {t['dot']}; border: 1px solid var(--border-default);"></span>
                <span style="color: var(--fg-default);">{t['name']}</span>
            </div>
            <span class="text-[10px] uppercase font-mono px-1 rounded" style="color: var(--fg-subtle);">{t['type']}</span>
        </div>""")

    return f"""
    <div id="themeDropdownMenu" class="hidden absolute right-0 top-full mt-2 w-56 rounded-xl border p-1.5 shadow-2xl z-50 transition-all duration-150" style="background-color: var(--canvas-subtle); border-color: var(--border-default);">
        <div class="px-2.5 py-1.5 text-[11px] font-semibold uppercase tracking-wider border-b mb-1 flex items-center justify-between" style="border-color: var(--border-muted); color: var(--fg-muted);">
            <span>Color Themes (10)</span>
            <span class="text-[9px] font-mono">1-10</span>
        </div>
        <div class="space-y-0.5 max-h-72 overflow-y-auto touch-scroll scrollbar-none">
            {"".join(items_html)}
        </div>
    </div>"""


def get_theme_by_id(theme_id: str) -> Dict[str, Any]:
    """Retrieve theme dictionary by ID, falling back to default theme if not found."""
    for theme in THEMES:
        if theme["id"] == theme_id:
            return theme
    for theme in THEMES:
        if theme["id"] == DEFAULT_THEME:
            return theme
    return THEMES[0]


def get_theme_json() -> str:
    """Returns JSON string of all themes."""
    return json.dumps(THEMES)


def generate_theme_dropdown_options() -> str:
    """Emits HTML option tags for all 10 developer themes."""
    options = []
    for t in THEMES:
        selected = " selected" if t["id"] == DEFAULT_THEME else ""
        options.append(f'<option value="{t["id"]}"{selected}>{t["name"]} ({t["type"]})</option>')
    return "\n".join(options)

