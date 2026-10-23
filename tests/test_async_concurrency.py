"""
Unit and integration tests for Concurrent Inspection Engine (Milestone M4).

Validates:
1. run_inspection_async concurrency bounding (verify at most N tasks in flight via semaphore).
2. Graceful task error isolation (network/socket failure on one offer does not abort the run).
3. Synchronous wrapper run_inspection executes cleanly and returns InspectionResult.
4. InspectionResult dual-nature container behaves as both a list of offers and a metrics dictionary.
5. Mocked Playwright async browser inspection execution.
6. Schema-validated atomic write integration on database persistence.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.inspector import (
    InspectionResult,
    run_inspection,
    run_inspection_async,
)


def _create_mock_offers_file(tmp_path: Path, count: int = 10) -> Path:
    """Helper creating a test data/offers.json file with N synthetic offers."""
    offers_file = tmp_path / "offers.json"
    offers = []
    for i in range(count):
        offers.append({
            "id": f"synthetic-offer-{i+1}",
            "title": f"Microsoft Azure Certification Offer {i+1}",
            "platform": "Microsoft Azure",
            "category": "Cloud Architecture",
            "certification_name": f"Azure Fundamentals {i+1}",
            "credential_tier": "certification_exam",
            "url": f"https://learn.microsoft.com/credentials/certifications/azure-fundamentals-{i+1}",
            "status": "Active",
            "expiry_date": "2026-12-31"
        })
    data = {
        "$schema": "./schema.json",
        "last_updated": "2026-10-23T00:00:00Z",
        "total_offers": count,
        "offers": offers
    }
    offers_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return offers_file


@pytest.fixture(autouse=True)
def cleanup_synthetic_screenshots():
    """Teardown fixture ensuring no synthetic test screenshots linger in docs/screenshots."""
    yield
    sc_dir = Path("docs/screenshots")
    if sc_dir.exists():
        for p in sc_dir.glob("synthetic-offer-*.png"):
            try:
                p.unlink()
            except Exception:
                pass




@pytest.mark.asyncio
class TestAsyncConcurrencyEngine:
    """Tests verifying async concurrency and semaphore bounding in src/inspector.py."""

    async def test_run_inspection_async_concurrency_bounding(self, tmp_path: Path):
        """Verify that asyncio.Semaphore(5) strictly bounds active in-flight tasks to <= 5."""
        offers_file = _create_mock_offers_file(tmp_path, count=15)

        current_in_flight = 0
        max_in_flight = 0
        lock = asyncio.Lock()

        def mock_worker_sync(url, offer=None, max_retries=3):
            nonlocal current_in_flight, max_in_flight
            # Synchronous work inside to_thread
            auth_mock = {
                "is_authentic_vendor": True,
                "authenticity_score": 95,
                "verdict": "VERIFIED_AUTHENTIC",
                "summary": "Mock Authenticity",
                "warning_flags": []
            }
            return "Active", "HTTP 200 OK (Concurrency Test)", url, auth_mock

        async def tracked_to_thread(fn, *args, **kwargs):
            nonlocal current_in_flight, max_in_flight
            async with lock:
                current_in_flight += 1
                if current_in_flight > max_in_flight:
                    max_in_flight = current_in_flight
            try:
                await asyncio.sleep(0.04)  # Hold task open to enforce overlap
                return fn(*args, **kwargs)
            finally:
                async with lock:
                    current_in_flight -= 1

        with patch("src.inspector.DATA_FILE", offers_file), \
             patch("src.inspector.inspect_url_with_retry", side_effect=mock_worker_sync), \
             patch("asyncio.to_thread", side_effect=tracked_to_thread):

            result = await run_inspection_async(use_headless=False, concurrency=5)

        assert len(result) == 15
        assert max_in_flight <= 5, f"Semaphore invariant violated: max_in_flight was {max_in_flight} > 5"

    async def test_run_inspection_async_graceful_task_isolation(self, tmp_path: Path):
        """Verify that a network failure or exception on one offer does not crash other offers."""
        offers_file = _create_mock_offers_file(tmp_path, count=5)

        def mock_inspect_with_isolated_failures(url, offer=None, max_retries=3):
            offer_id = (offer or {}).get("id", "")
            if offer_id == "synthetic-offer-2":
                raise ConnectionResetError("Remote server closed connection")
            if offer_id == "synthetic-offer-4":
                raise TimeoutError("TCP Handshake timeout after 45s")
            return "Active", "HTTP 200 OK", url, {
                "is_authentic_vendor": True,
                "authenticity_score": 90,
                "verdict": "VERIFIED_AUTHENTIC",
                "summary": "Verified",
                "warning_flags": []
            }

        with patch("src.inspector.DATA_FILE", offers_file), \
             patch("src.inspector.inspect_url_with_retry", side_effect=mock_inspect_with_isolated_failures):

            result = await run_inspection_async(use_headless=False, concurrency=3)

        assert len(result) == 5, "All 5 offers must be retained despite isolated failures"
        # Offers 1, 3, 5 successfully verified
        assert result[0]["status"] == "Active"
        assert result[2]["status"] == "Active"
        assert result[4]["status"] == "Active"

    async def test_run_inspection_async_with_mocked_playwright(self, tmp_path: Path):
        """Verify Playwright async API execution path with mocked browser/page."""
        offers_file = _create_mock_offers_file(tmp_path, count=3)

        mock_page = AsyncMock()
        mock_page.goto.return_value = MagicMock(status=200)
        mock_page.url = "https://vendor-cloud.example.com/voucher-1"
        mock_page.title.return_value = "Vendor 100% Free Certification Exam Voucher"
        mock_page.evaluate.return_value = "Registration open for free exam certification voucher. Balance: $0.00."
        # Provide valid PNG bytes >= 4096 bytes
        from tests.test_visual_delta_skipping import _generate_png_bytes
        mock_page.screenshot.return_value = _generate_png_bytes(seed=777)
        mock_page.route = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()

        mock_context = AsyncMock()
        mock_context.new_page.return_value = mock_page
        mock_context.close = AsyncMock()

        mock_browser = AsyncMock()
        mock_browser.new_context.return_value = mock_context
        mock_browser.close = AsyncMock()

        mock_playwright = AsyncMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_playwright.stop = AsyncMock()

        mock_ap_inst = MagicMock()
        mock_ap_inst.start = AsyncMock(return_value=mock_playwright)

        with patch("src.inspector.DATA_FILE", offers_file), \
             patch("src.inspector.async_playwright", return_value=mock_ap_inst):

            result = await run_inspection_async(use_headless=True, concurrency=2)

        assert len(result) == 3
        assert mock_browser.new_context.call_count >= 1
        assert mock_browser.close.call_count == 1
        assert mock_playwright.stop.call_count == 1


class TestSynchronousWrapperAndResultModel:
    """Tests for the synchronous wrapper and InspectionResult container."""

    def test_run_inspection_sync_wrapper(self, tmp_path: Path):
        """run_inspection executes synchronously and returns InspectionResult."""
        offers_file = _create_mock_offers_file(tmp_path, count=4)

        def mock_inspect(url, offer=None, max_retries=3):
            return "Active", "HTTP 200 OK", url, {
                "is_authentic_vendor": True,
                "authenticity_score": 95,
                "verdict": "VERIFIED_AUTHENTIC",
                "summary": "Mock",
                "warning_flags": []
            }

        with patch("src.inspector.DATA_FILE", offers_file), \
             patch("src.inspector.inspect_url_with_retry", side_effect=mock_inspect):

            result = run_inspection(use_headless=False, concurrency=2)

        assert isinstance(result, InspectionResult)
        assert len(result) == 4
        assert "summary" in result
        assert result["summary"]["total_inspected"] == 4

    def test_inspection_result_dual_nature_interface(self):
        """InspectionResult supports both list iteration/indexing and dict lookup."""
        sample_offers = [
            {"id": "o1", "title": "Offer 1", "status": "Active"},
            {"id": "o2", "title": "Offer 2", "status": "Expired"}
        ]
        sample_summary = {
            "total_inspected": 2,
            "active_confirmed": 1,
            "closed_detected": 1,
            "screenshots_skipped_phash": 1,
            "duration_seconds": 1.5,
        }

        res = InspectionResult(sample_offers, sample_summary)

        # 1. List behaviors
        assert isinstance(res, list)
        assert len(res) == 2
        assert res[0]["id"] == "o1"
        assert res[1]["id"] == "o2"
        # Iteration yields offer dictionaries
        for item in res:
            assert "id" in item
            assert "title" in item

        # 2. Dictionary behaviors
        assert "summary" in res
        assert "results" in res
        assert "offers" in res
        assert res["summary"]["total_inspected"] == 2
        assert res.get("summary") == sample_summary
        assert res["results"] == sample_offers
        assert res.get("results") == sample_offers
        assert "screenshots_skipped_phash" in res["summary"]

        # 3. Dict view helpers
        assert "summary" in res.keys()
        assert "results" in res.keys()
        d = res.to_dict()
        assert isinstance(d, dict)
        assert d["summary"]["active_confirmed"] == 1
        assert len(d["results"]) == 2

    def test_atomic_schema_persistence_with_valid_payload(self, tmp_path: Path):
        """run_inspection safely updates offers.json via atomic_write_json."""
        offers_file = _create_mock_offers_file(tmp_path, count=2)

        def mock_inspect(url, offer=None, max_retries=3):
            return "Active", "HTTP 200 OK", url, {
                "is_authentic_vendor": True,
                "authenticity_score": 100,
                "verdict": "VERIFIED_AUTHENTIC",
                "summary": "Verified",
                "warning_flags": []
            }

        with patch("src.inspector.DATA_FILE", offers_file), \
             patch("src.inspector.inspect_url_with_retry", side_effect=mock_inspect):

            run_inspection(use_headless=False, concurrency=2)

        # Verify file on disk was atomically updated with timestamps
        content = json.loads(offers_file.read_text(encoding="utf-8"))
        assert "last_inspected" in content
        assert "last_sync" in content
        assert "last_updated" in content
        assert len(content["offers"]) == 2
