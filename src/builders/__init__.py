"""
Builders package for CertPulse.
Deconstructs monolithic builder into focused modules:
- theme_engine: 10 developer palettes and Zero-FOIT styling
- client_bundle: Client-side JavaScript controllers and multi-view engines
- readme_builder: Markdown documentation and 4-timezone table formatting
- html_builder: Semantic HTML5 canvas and responsive view shell
"""

import os
import time
import tempfile
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


def _atomic_write_text(path: Path, content: str) -> None:
    """Atomically writes text using NamedTemporaryFile and os.replace with Windows lock retry."""
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_file = tempfile.NamedTemporaryFile(
        mode="w",
        delete=False,
        dir=str(path.parent),
        prefix=f".{path.name}.",
        suffix=".tmp",
        encoding="utf-8",
    )
    temp_path = Path(temp_file.name)
    try:
        temp_file.write(content)
        temp_file.flush()
        temp_file.close()

        # On Windows, concurrent pytest processes holding read handles can cause transient WinError 5/32
        for attempt in range(10):
            try:
                os.replace(temp_path, path)
                break
            except (PermissionError, OSError) as e:
                if attempt == 9:
                    # Fallback to direct write if target remains locked
                    try:
                        path.write_text(content, encoding="utf-8")
                        if temp_path.exists():
                            temp_path.unlink(missing_ok=True)
                        break
                    except Exception:
                        raise e
                time.sleep(0.05)
    except Exception:
        if not temp_file.closed:
            try:
                temp_file.close()
            except Exception:
                pass
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass
        raise


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

    # 1. Write README.md atomically
    readme_content = generate_readme(data, news)
    _atomic_write_text(target_readme, readme_content)
    print(f"[OK] Successfully built {target_readme}")

    # 2. Write docs/index.html atomically
    html_content = generate_web_dashboard(data, news)
    _atomic_write_text(target_html, html_content)
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
]
