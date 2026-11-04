"""
Regression & Invariant Tests for Inspector Security Flow & Resource Management.
Verifies:
1. Insecure URL schemes (non-HTTPS) are properly demoted to 'Review Needed' and persisted.
2. Deceptive scam domains are properly demoted to 'Review Needed' and persisted without early exit bypass.
3. Playwright launcher cleans up driver manager if chromium launch raises an exception.
"""

import json
from datetime import datetime, UTC
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.inspector import run_inspection_async


@pytest.mark.asyncio
async def test_insecure_http_scheme_is_demoted_to_review_needed(tmp_path):
    """
    RCA Regression Test:
    Offers with http:// (insecure scheme) must be demoted from Active to Review Needed,
    and must not be bypassed by early returns before status persistence.
    """
    today_iso = datetime.now(UTC).strftime("%Y-%m-%d")
    fake_data = {
        "$schema": "./schema.json",
        "offers": [
            {
                "id": "test-insecure-offer",
                "title": "Insecure Scheme Exam Voucher",
                "platform": "Unknown Provider",
                "category": "Cloud Architecture",
                "certification_name": "Insecure Cert",
                "credential_tier": "proctored_exam",
                "url": "http://insecure-example.org/free-exam",
                "status": "Active",
                "verification_date": today_iso,
                "is_authentic_vendor": True,
                "authenticity_score": 90,
                "authenticity_details": {"verdict": "VERIFIED_AUTHENTIC"},
                "expiry_date": None,
                "cart_balance_verified": "$0.00 (100% Free / Waiver Confirmed)",
            }
        ]
    }

    data_file = tmp_path / "offers.json"
    data_file.write_text(json.dumps(fake_data), encoding="utf-8")

    with patch("src.inspector.DATA_FILE", data_file):
        mock_browser = MagicMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)

        mock_pw_mgr = AsyncMock()
        mock_pw_mgr.chromium.launch = AsyncMock(return_value=mock_browser)

        mock_pw = MagicMock()
        mock_pw.return_value.start = AsyncMock(return_value=mock_pw_mgr)

        with patch("src.inspector.async_playwright", mock_pw):
            await run_inspection_async(use_headless=True, concurrency=1)

    saved_data = json.loads(data_file.read_text(encoding="utf-8"))
    saved_offer = saved_data["offers"][0]

    assert saved_offer["status"] == "Review Needed", (
        f"Expected 'Review Needed' due to insecure scheme, got '{saved_offer['status']}'"
    )
    assert "Insecure or forbidden URL scheme" in saved_offer["inspection_notes"]
    assert saved_offer["is_authentic_vendor"] is False


@pytest.mark.asyncio
async def test_deceptive_scam_domain_is_demoted_to_review_needed(tmp_path):
    """
    RCA Regression Test:
    Offers pointing to deceptive phishing/dumps domains must be demoted to Review Needed,
    and must not be bypassed before database persistence.
    """
    today_iso = datetime.now(UTC).strftime("%Y-%m-%d")
    fake_data = {
        "$schema": "./schema.json",
        "offers": [
            {
                "id": "test-scam-offer",
                "title": "Braindump Scam Voucher",
                "platform": "Microsoft Azure",
                "category": "Cloud Architecture",
                "certification_name": "AZ-900 Exam",
                "credential_tier": "proctored_exam",
                "url": "https://free-exam-dumps-and-vouchers.scam/az900",
                "status": "Active",
                "verification_date": today_iso,
                "is_authentic_vendor": True,
                "authenticity_score": 90,
                "authenticity_details": {"verdict": "VERIFIED_AUTHENTIC"},
                "expiry_date": None,
                "cart_balance_verified": "$0.00 (100% Free / Waiver Confirmed)",
            }
        ]
    }

    data_file = tmp_path / "offers.json"
    data_file.write_text(json.dumps(fake_data), encoding="utf-8")

    with patch("src.inspector.DATA_FILE", data_file):
        mock_browser = MagicMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)

        mock_pw_mgr = AsyncMock()
        mock_pw_mgr.chromium.launch = AsyncMock(return_value=mock_browser)

        mock_pw = MagicMock()
        mock_pw.return_value.start = AsyncMock(return_value=mock_pw_mgr)

        with patch("src.inspector.async_playwright", mock_pw):
            await run_inspection_async(use_headless=True, concurrency=1)

    saved_data = json.loads(data_file.read_text(encoding="utf-8"))
    saved_offer = saved_data["offers"][0]

    assert saved_offer["status"] == "Review Needed", (
        f"Expected 'Review Needed' for scam domain, got '{saved_offer['status']}'"
    )
    assert "Domain authenticity failed" in saved_offer["inspection_notes"]
    assert saved_offer["is_authentic_vendor"] is False


@pytest.mark.asyncio
async def test_playwright_mgr_stopped_if_chromium_launch_fails(tmp_path):
    """
    RCA Regression Test:
    If playwright.start() succeeds but chromium.launch fails, playwright_mgr.stop()
    must be called in the except block to prevent orphan driver process leaks.
    """
    fake_data = {"$schema": "./schema.json", "offers": []}
    data_file = tmp_path / "offers.json"
    data_file.write_text(json.dumps(fake_data), encoding="utf-8")

    mock_pw_mgr = AsyncMock()
    mock_pw_mgr.chromium.launch = AsyncMock(side_effect=RuntimeError("Browser binary missing"))

    mock_pw = MagicMock()
    mock_pw.return_value.start = AsyncMock(return_value=mock_pw_mgr)

    with patch("src.inspector.DATA_FILE", data_file), patch("src.inspector.async_playwright", mock_pw):
        await run_inspection_async(use_headless=True, concurrency=1)

    mock_pw_mgr.stop.assert_awaited_once()
