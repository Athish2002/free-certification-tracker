"""
Builders package for CertPulse.
Deconstructs monolithic builder into focused modules:
- theme_engine: 10 developer palettes and Zero-FOIT styling
- client_bundle: Client-side JavaScript controllers and multi-view engines
- readme_builder: Markdown documentation and 4-timezone table formatting
- html_builder: Semantic HTML5 canvas and responsive view shell
"""

from typing import Dict, Any, Optional
from pathlib import Path

from src.builders.theme_engine import (
    THEMES,
    DEFAULT_THEME,
    generate_css_variables,
    generate_zero_foit_script,
    generate_theme_dropdown_html,
    generate_theme_dropdown_options,
    get_theme_by_id,
    get_theme_json,
)
from src.builders.client_bundle import generate_client_bundle
from src.builders.readme_builder import (
    generate_readme,
    format_4_timezones,
    load_offers,
    load_news,
    DATA_FILE,
    NEWS_FILE,
    README_FILE,
    DOCS_DIR,
    DOCS_HTML,
    STATUS_BADGES,
)
from src.builders.html_builder import generate_web_dashboard


def build_all(
    readme_path: Optional[Path] = None,
    html_path: Optional[Path] = None,
) -> bool:
    """
    Compiles data/offers.json and data/news.json into:
    1. README.md: GitHub repository documentation
    2. docs/index.html: Single-page executive web application
    Removes legacy auxiliary HTML artifacts to maintain a single canonical Pages entry point.
    """
    target_readme = Path(readme_path) if readme_path else README_FILE
    target_html = Path(html_path) if html_path else DOCS_HTML

    data = load_offers()
    news = load_news()

    # 1. Write README.md
    readme_content = generate_readme(data, news)
    target_readme.parent.mkdir(parents=True, exist_ok=True)
    target_readme.write_text(readme_content, encoding="utf-8")
    print(f"[OK] Successfully built {target_readme}")

    # 2. Write docs/index.html
    html_content = generate_web_dashboard(data, news)
    target_html.parent.mkdir(parents=True, exist_ok=True)
    target_html.write_text(html_content, encoding="utf-8")
    print(f"[OK] Successfully built {target_html}")

    # 3. Clean up legacy archetype_studio.html if present
    if not html_path:
        studio_file = DOCS_DIR / "archetype_studio.html"
        if studio_file.exists():
            try:
                studio_file.unlink()
                print(f"[OK] Cleaned up {studio_file} (maintaining single canonical docs/index.html)")
            except Exception as e:
                print(f"[WARN] Could not unlink {studio_file}: {e}")

    return True


__all__ = [
    "build_all",
    "generate_readme",
    "generate_web_dashboard",
    "format_4_timezones",
    "load_offers",
    "load_news",
    "DATA_FILE",
    "NEWS_FILE",
    "README_FILE",
    "DOCS_DIR",
    "DOCS_HTML",
    "STATUS_BADGES",
    "THEMES",
    "DEFAULT_THEME",
    "generate_css_variables",
    "generate_zero_foit_script",
    "generate_theme_dropdown_html",
    "generate_theme_dropdown_options",
    "get_theme_by_id",
    "get_theme_json",
    "generate_client_bundle",
]
