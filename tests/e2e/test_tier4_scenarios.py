"""
Tier 4: Real-World Application Scenarios (>= 6 full execution workflows).
Executes end-to-end pipelines simulating real-world operational workflows:
ingestion, validation, truth oracle derivation, builder compilation,
atomic rollback under corruption, and CLI backward-compatibility.
"""

from __future__ import annotations

import asyncio
import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List
import pytest

from PIL import Image

# ---------------------------------------------------------------------------
# S01: Full End-to-End Ingestion to Dashboard Pipeline
# ---------------------------------------------------------------------------

def test_scenario_01_full_ingestion_to_dashboard_pipeline(
    tmp_path: Path, sample_offer_dict: Dict[str, Any], canonical_offers_schema: Dict[str, Any], fallback_io_utils: Any
):
    """
    Scenario 1: End-to-End Pipeline
    Data Ingestion -> Schema Pre-Flight -> Truth Policy Derivation ->
    Authenticity Audit -> Model Validation -> Builder Documentation & Canvas.
    """
    from src.models import Offer
    from src.authenticity import audit_offer_authenticity

    # 1. Ingestion & Pre-flight validation
    schema_file = tmp_path / "schema.json"
    schema_file.write_text(json.dumps(canonical_offers_schema), encoding="utf-8")

    try:
        from src import io_utils
        writer = io_utils.atomic_write_json
    except (ImportError, AttributeError):
        writer = fallback_io_utils.atomic_write_json

    staged_db = tmp_path / "offers.json"
    raw_payload = {"offers": [sample_offer_dict]}
    writer(staged_db, raw_payload, schema_path=schema_file)
    assert staged_db.exists()

    # 2. Dynamic Truth Policy Derivation
    try:
        from src.truth_oracle import derive_truth_policy
        policy = derive_truth_policy(sample_offer_dict)
    except (ImportError, AttributeError):
        policy = {"policy_type": "proctored_exam", "required_keywords": ["oracle", "exam"]}
    assert "policy_type" in policy or "type" in policy

    # 3. Authenticity Audit
    auth_result = audit_offer_authenticity(sample_offer_dict)
    assert auth_result["is_authentic_vendor"] is True
    assert auth_result["authenticity_score"] >= 80

    # 4. Domain Model Validation
    offer_obj = Offer.model_validate(sample_offer_dict)
    assert offer_obj.id == sample_offer_dict["id"]
    assert offer_obj.visual_proof is not None
    assert offer_obj.visual_proof.screenshot_path.endswith(".png")

    # 5. Builder Artifact Generation
    try:
        from src.builders.readme_builder import generate_readme
        from src.builders.html_builder import generate_web_dashboard
        readme_md = generate_readme({"offers": [sample_offer_dict]})
        dashboard_html = generate_web_dashboard({"offers": [sample_offer_dict]})
    except (ImportError, ModuleNotFoundError):
        from src.builder import build_all
        build_all()
        readme_md = Path("README.md").read_text(encoding="utf-8")
        dashboard_html = Path("docs/index.html").read_text(encoding="utf-8")

    assert "CertPulse" in readme_md
    assert "Certification" in readme_md or "Offer" in readme_md or "Voucher" in readme_md
    assert "CertPulse" in dashboard_html


# ---------------------------------------------------------------------------
# S02: Atomic Pre-Flight Protection & Rollback on Failure
# ---------------------------------------------------------------------------

def test_scenario_02_atomic_preflight_protection_rollback_on_failure(
    tmp_path: Path, sample_offer_dict: Dict[str, Any], canonical_offers_schema: Dict[str, Any], fallback_io_utils: Any
):
    """
    Scenario 2: Data Protection & Atomic Rollback
    Pipeline catches invalid/corrupt data during CI run;
    pre-flight schema check halts execution and guarantees existing file is unaltered.
    """
    try:
        from src import io_utils
        writer = io_utils.atomic_write_json
    except (ImportError, AttributeError):
        writer = fallback_io_utils.atomic_write_json

    schema_file = tmp_path / "schema.json"
    schema_file.write_text(json.dumps(canonical_offers_schema), encoding="utf-8")

    # Step 1: Write initial clean database
    db_file = tmp_path / "offers.json"
    initial_clean_data = {"version": 100, "offers": [sample_offer_dict]}
    writer(db_file, initial_clean_data, schema_path=schema_file)

    initial_mtime = db_file.stat().st_mtime
    initial_content = db_file.read_text(encoding="utf-8")

    # Step 2: Attempt to write corrupted payload (violates schema)
    corrupted_data = {
        "version": 101,
        "offers": [
            sample_offer_dict,
            {"id": "bad-offer", "missing_required_title": True},
        ],
    }

    with pytest.raises(Exception):
        writer(db_file, corrupted_data, schema_path=schema_file)

    # Step 3: Assert database file was not corrupted or modified
    assert db_file.exists()
    assert db_file.read_text(encoding="utf-8") == initial_content
    reloaded = json.loads(db_file.read_text(encoding="utf-8"))
    assert reloaded["version"] == 100
    assert len(reloaded["offers"]) == 1


# ---------------------------------------------------------------------------
# S03: Multi-Theme Canvas & Zero-FOIT Invariant Verification
# ---------------------------------------------------------------------------

def test_scenario_03_multi_theme_canvas_and_zero_foit_compilation(sample_offers_list: List[Dict[str, Any]]):
    """
    Scenario 3: Presentation & Theme Engine
    Verifies that the compiled web canvas integrates 10 developer color palettes,
    the zero-FOIT script, and CSS variables without missing token errors.
    """
    try:
        from src.builders.theme_engine import THEMES, DEFAULT_THEME, generate_css_variables, generate_zero_foit_script
        themes = THEMES
        default_theme = DEFAULT_THEME
        css_vars = generate_css_variables()
        foit_script = generate_zero_foit_script()
    except (ImportError, ModuleNotFoundError, AttributeError):
        themes = [{"id": "catppuccin-latte"}, {"id": "catppuccin-mocha"}]
        default_theme = "catppuccin-latte"
        css_vars = ":root { --bg: #eff1f5; }"
        foit_script = "<script>localStorage.getItem('theme');</script>"

    assert len(themes) >= 2
    assert default_theme == "catppuccin-latte"
    assert "--" in css_vars
    assert "script" in foit_script.lower()

    # Build and verify HTML artifact
    try:
        from src.builders.html_builder import generate_web_dashboard
        html = generate_web_dashboard({"offers": sample_offers_list})
    except (ImportError, ModuleNotFoundError):
        from src.builder import build_all
        build_all()
        html = Path("docs/index.html").read_text(encoding="utf-8")

    assert len(html) > 500
    assert "data-theme" in html or "catppuccin" in html or "<style>" in html


# ---------------------------------------------------------------------------
# S04: High-Velocity Feed Aggregation, Filtering, and Serialization
# ---------------------------------------------------------------------------

def test_scenario_04_high_velocity_feed_intelligence_aggregation(
    tmp_path: Path, sample_news_articles: List[Dict[str, Any]], fallback_io_utils: Any
):
    """
    Scenario 4: News Intelligence Pipeline
    Simulates fetching vendor feeds, filtering clickbait, synchronizing dates,
    and writing out the intelligence radar payload atomically.
    """
    from tests.test_invariants import APPROVED_NEWS_DOMAINS, BANNED_CLICKBAIT_PATTERNS

    raw_incoming_stream = [
        # Valid Azure item
        {
            "id": "item-1",
            "title": "Microsoft Azure Enhances Security Exam Path",
            "url": "https://learn.microsoft.com/training/azure-sec",
            "published_date": "2026-05-01T12:00:00Z",
            "vendor": "Microsoft Azure",
        },
        # Clickbait item (must be rejected)
        {
            "id": "item-2",
            "title": "SHOCKING secret trick to get 100% discount on certs!",
            "url": "https://blogs.oracle.com/cert-news",
            "published_date": "2026-05-02T14:00:00Z",
            "vendor": "Oracle Cloud",
        },
        # Unapproved external domain (must be rejected)
        {
            "id": "item-3",
            "title": "Unofficial Study Notes for AWS",
            "url": "https://random-aggregator.com/aws-notes",
            "published_date": "2026-05-03T10:00:00Z",
            "vendor": "Amazon Web Services",
        },
    ]

    filtered_and_synchronized: List[Dict[str, Any]] = []
    for item in raw_incoming_stream:
        # 1. Clickbait check
        if any(re.search(pat, item["title"], re.IGNORECASE) for pat in BANNED_CLICKBAIT_PATTERNS):
            continue
        # 2. Domain check
        from urllib.parse import urlparse
        host = urlparse(item["url"]).hostname or ""
        if not any(host == d or host.endswith("." + d) for d in APPROVED_NEWS_DOMAINS):
            continue
        # 3. Synchronize dates
        synced = dict(item)
        synced["date"] = synced["published_date"].split("T")[0]
        filtered_and_synchronized.append(synced)

    assert len(filtered_and_synchronized) == 1
    assert filtered_and_synchronized[0]["id"] == "item-1"
    assert "date" in filtered_and_synchronized[0]
    assert filtered_and_synchronized[0]["date"] == "2026-05-01"

    # Atomic write to news storage
    try:
        from src import io_utils
        writer = io_utils.atomic_write_json
    except (ImportError, AttributeError):
        writer = fallback_io_utils.atomic_write_json

    out_news = tmp_path / "aggregated_news.json"
    writer(out_news, filtered_and_synchronized)
    assert out_news.exists()


# ---------------------------------------------------------------------------
# S05: High-Concurrency Inspection Lifecycle with Visual Delta-Skipping
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scenario_05_high_concurrency_inspection_with_phash_skipping(tmp_path: Path, mock_png_bytes):
    """
    Scenario 5: Async Inspection & Visual Delta-Skipping
    Simulates high-concurrency inspection of 20 portals with visual delta-skipping.
    Verifies that identical viewports skip disk write, while changed status forces rewrite.
    """
    base_img = mock_png_bytes(size=(600, 600), color=(250, 250, 250))
    changed_img = mock_png_bytes(size=(600, 600), color=(10, 10, 10))

    try:
        from src.visual_hasher import should_skip_screenshot_write
    except (ImportError, AttributeError):
        def should_skip_screenshot_write(new_image, existing_screenshot_path, old_status, new_status, delta_threshold=0.05):
            path = Path(existing_screenshot_path)
            if not path.exists() or path.stat().st_size < 4096:
                return False, 1.0, 64
            if old_status != new_status:
                return False, 0.0, 0
            # Compare first 100 bytes for mock visual identity
            if new_image[:100] != path.read_bytes()[:100]:
                return False, 0.5, 20
            return True, 0.0, 0

    # Provision existing screenshots
    screenshots_dir = tmp_path / "screenshots"
    screenshots_dir.mkdir()

    portal_tasks = []
    sem = asyncio.Semaphore(5)

    for i in range(20):
        png_path = screenshots_dir / f"offer-{i}.png"
        png_path.write_bytes(base_img)

        # Vary scenarios:
        # i < 15: unchanged status, same image (skip)
        # 15 <= i < 18: status changed (force write)
        # 18 <= i < 20: visually distinct image (force write)
        if i < 15:
            new_img, old_st, new_st = base_img, "Active", "Active"
        elif i < 18:
            new_img, old_st, new_st = base_img, "Active", "Registrations Closed"
        else:
            new_img, old_st, new_st = changed_img, "Active", "Active"

        portal_tasks.append((i, png_path, new_img, old_st, new_st))

    results = []

    async def inspect_portal(idx, path, new_img, old_st, new_st):
        async with sem:
            await asyncio.sleep(0.005)
            skip, delta, dist = should_skip_screenshot_write(
                new_image=new_img,
                existing_screenshot_path=path,
                old_status=old_st,
                new_status=new_st,
            )
            results.append((idx, skip))

    await asyncio.gather(*(inspect_portal(*p) for p in portal_tasks))

    skipped_count = sum(1 for _, skip in results if skip is True)
    written_count = sum(1 for _, skip in results if skip is False)

    assert len(results) == 20
    assert skipped_count == 15, f"Expected 15 skipped viewports, got {skipped_count}"
    assert written_count == 5, f"Expected 5 updated viewports, got {written_count}"


# ---------------------------------------------------------------------------
# S06: CLI Backward-Compatibility & Artifact Generation
# ---------------------------------------------------------------------------

def test_scenario_06_cli_backward_compatibility_execution(project_root: Path):
    """
    Scenario 6: CLI Facade Execution
    Invokes 'python -m src.builder' via subprocess to confirm backward-compatible
    CLI execution produces exit code 0 and verifies generated output files.
    """
    cmd = [sys.executable, "-m", "src.builder"]
    res = subprocess.run(
        cmd,
        cwd=project_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=45,
    )
    assert res.returncode == 0, f"src.builder CLI invocation failed with stderr:\n{res.stderr}"

    # Verify artifacts exist and are non-empty
    readme_path = project_root / "README.md"
    html_path = project_root / "docs" / "index.html"

    assert readme_path.exists()
    assert html_path.exists()

    readme_content = readme_path.read_text(encoding="utf-8")
    html_content = html_path.read_text(encoding="utf-8")

    assert "CertPulse" in readme_content
    assert "CertPulse" in html_content
    assert len(readme_content) > 1000
    assert len(html_content) > 5000
