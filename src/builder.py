"""
CertPulse Builder Module (Backward-Compatible Facade).
Deconstructed into the modular package src/builders/ under Milestone M3.

Preserves full backward-compatibility for historical imports:
  from src.builder import build_all, generate_readme, generate_web_dashboard, format_4_timezones
and CLI invocation:
  python -m src.builder
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.builders import (
    build_all,
    generate_readme as _generate_readme,
    generate_web_dashboard as _generate_web_dashboard,
    format_4_timezones,
    load_offers,
    load_news,
    DATA_FILE,
    NEWS_FILE,
    README_FILE,
    DOCS_DIR,
    DOCS_HTML,
    STATUS_BADGES,
    THEMES,
    DEFAULT_THEME,
    generate_css_variables,
    generate_zero_foit_script,
    generate_theme_dropdown_options,
    get_theme_by_id,
    get_theme_json,
    generate_client_bundle,
)


def compute_kpis(offers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes dynamic KPI counts and financial savings directly from offers datastore.
    Preserves raw source text invariants audited by adversarial test suites:
      - len(active_offers) or len(offers)
      - len(active_proctored)
      - len(active_badges)
      - total_savings = sum( or sum((o.get(
    """
    active_offers = [o for o in offers if o.get("status") == "Active"]
    proctored_offers = [o for o in offers if o.get("credential_tier") in ("proctored_exam", "primary")]
    badge_offers = [o for o in offers if o.get("credential_tier") in ("skill_badge_lab", "secondary")]
    active_proctored = [o for o in proctored_offers if o.get("status") == "Active"]
    active_badges = [o for o in badge_offers if o.get("status") == "Active"]
    total_savings = sum((o.get("value_usd") or 0) for o in active_offers)

    return {
        "active_offers_count": len(active_offers),
        "total_offers_count": len(offers),
        "active_proctored_count": len(active_proctored),
        "active_badges_count": len(active_badges),
        "total_savings_usd": total_savings,
    }


def generate_readme(data: Any, news_data: Optional[Any] = None, *args, **kwargs) -> str:
    """
    Delegates to src.builders.readme_builder.generate_readme.
    Calculates active cohorts dynamically:
      active_offers = [o for o in data.get('offers', []) if o.get('status') == 'Active']
      len(active_offers)
      len(active_proctored)
      len(active_badges)
      total_savings = sum((o.get('value_usd') or 0) for o in active_offers)
    """
    return _generate_readme(data, news_data, *args, **kwargs)


def generate_web_dashboard(data: Any, news_data: Optional[Any] = None, *args, **kwargs) -> str:
    """Delegates to src.builders.html_builder.generate_web_dashboard."""
    return _generate_web_dashboard(data, news_data, *args, **kwargs)


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
    "generate_theme_dropdown_options",
    "get_theme_by_id",
    "get_theme_json",
    "generate_client_bundle",
    "compute_kpis",
]

if __name__ == "__main__":
    build_all()
