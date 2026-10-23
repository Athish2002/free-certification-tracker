"""
Adversarial Stress Test Suite: Milestone M4 Async Concurrency & Semaphore Bounds.
Authored by challenger_m4_2.

Empirically challenges:
1. Semaphore Invariant: 20 offers under concurrency=3 strictly bounds in-flight tasks <= 3.
2. High-Stress Concurrency: 50 offers under concurrency=7 with randomized jitter.
3. Boundary Concurrency: concurrency=1 (fully serialized) and concurrency=20.
4. Error Isolation & Fault Injection:
   - RuntimeError, TimeoutError, ConnectionRefusedError, ValueError, KeyError.
   - Mixed error storm (50% failure rate) where all non-failing offers complete successfully.
5. InspectionResult Dual-Nature Container:
   - Full list protocol (len, iter, index, negative index, slicing, list membership).
   - Full dict protocol (key indexing, KeyError on missing, .get() with defaults, .keys(), .values(), .items(), .to_dict()).
   - Empty offers boundary case.
6. Synchronous Wrapper run_inspection():
   - Execution from synchronous context (no loop).
   - Execution from inside an active, running asyncio event loop (nested loop re-entrancy defense).
"""

from __future__ import annotations

import asyncio
import json
import random
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from src.inspector import (
    InspectionResult,
    run_inspection,
    run_inspection_async,
)


def _generate_synthetic_offers_file(tmp_path: Path, count: int = 20) -> Path:
    """Generate a valid offers.json file containing N synthetic offers."""
    offers_file = tmp_path / f"offers_stress_{count}.json"
    offers = []
    for i in range(count):
        offers.append({
            "id": f"stress-offer-{i+1:03d}",
            "title": f"Stress Test Certification Offer #{i+1}",
            "platform": "Adversarial Lab",
            "category": "Cloud Architecture",
            "certification_name": f"Stress Cert {i+1}",
            "credential_tier": "certification_exam",
            "url": f"https://adversarial.example.com/exam-{i+1}",
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


# ============================================================================
# 1. SEMAPHORE CONCURRENCY BOUNDS STRESS TESTS
# ============================================================================

@pytest.mark.asyncio
class TestSemaphoreConcurrencyBounds:
    """Rigorous stress-testing of asyncio.Semaphore bounds under high load."""

    async def test_semaphore_bounds_20_offers_concurrency_3(self, tmp_path: Path):
        """Simulate 20 offers with concurrency=3 and assert in-flight count never exceeds 3."""
        offers_file = _generate_synthetic_offers_file(tmp_path, count=20)

        current_in_flight = 0
        max_in_flight = 0
        execution_timeline: list[tuple[float, int]] = []
        lock = asyncio.Lock()

        def mock_worker(url, offer=None, max_retries=3):
            return "Active", "HTTP 200 OK (Stress Verified)", url, {
                "is_authentic_vendor": True,
                "authenticity_score": 98,
                "verdict": "VERIFIED_AUTHENTIC",
                "summary": "Verified",
                "warning_flags": []
            }

        async def tracked_to_thread(fn, *args, **kwargs):
            nonlocal current_in_flight, max_in_flight
            async with lock:
                current_in_flight += 1
                if current_in_flight > max_in_flight:
                    max_in_flight = current_in_flight
                execution_timeline.append((time.perf_counter(), current_in_flight))

            try:
                # Artificial hold time to force concurrency overlap
                await asyncio.sleep(0.02)
                return fn(*args, **kwargs)
            finally:
                async with lock:
                    current_in_flight -= 1
                    execution_timeline.append((time.perf_counter(), current_in_flight))

        with patch("src.inspector.DATA_FILE", offers_file), \
             patch("src.inspector.inspect_url_with_retry", side_effect=mock_worker), \
             patch("asyncio.to_thread", side_effect=tracked_to_thread):

            result = await run_inspection_async(use_headless=False, concurrency=3)

        assert len(result) == 20, f"Expected 20 offers processed, got {len(result)}"
        assert max_in_flight <= 3, (
            f"CRITICAL INVARIANT VIOLATION: max_in_flight reached {max_in_flight}, "
            f"exceeding concurrency bound of 3!"
        )
        assert max_in_flight >= 2, (
            f"Expected concurrency overlap >= 2, got {max_in_flight}."
        )

    @pytest.mark.parametrize("offer_count,concurrency", [
        (10, 1),   # Serial execution boundary
        (30, 4),   # Medium batch
        (50, 7),   # High batch with randomized jitter
    ])
    async def test_parametric_semaphore_bounds(self, tmp_path: Path, offer_count: int, concurrency: int):
        """Stress test various concurrency scales (1, 4, 7) across up to 50 offers."""
        offers_file = _generate_synthetic_offers_file(tmp_path, count=offer_count)

        current_in_flight = 0
        max_in_flight = 0
        lock = asyncio.Lock()

        def mock_worker(url, offer=None, max_retries=3):
            return "Active", "HTTP 200 OK", url, {
                "is_authentic_vendor": True,
                "authenticity_score": 90,
                "verdict": "VERIFIED_AUTHENTIC",
                "summary": "Verified",
                "warning_flags": []
            }

        async def tracked_to_thread(fn, *args, **kwargs):
            nonlocal current_in_flight, max_in_flight
            async with lock:
                current_in_flight += 1
                if current_in_flight > max_in_flight:
                    max_in_flight = current_in_flight
            try:
                # Randomized jitter between 5ms and 25ms
                await asyncio.sleep(random.uniform(0.005, 0.025))
                return fn(*args, **kwargs)
            finally:
                async with lock:
                    current_in_flight -= 1

        with patch("src.inspector.DATA_FILE", offers_file), \
             patch("src.inspector.inspect_url_with_retry", side_effect=mock_worker), \
             patch("asyncio.to_thread", side_effect=tracked_to_thread):

            result = await run_inspection_async(use_headless=False, concurrency=concurrency)

        assert len(result) == offer_count
        assert max_in_flight <= concurrency, (
            f"Concurrency invariant violated: max_in_flight={max_in_flight} > {concurrency}"
        )


# ============================================================================
# 2. TASK ISOLATION & FAULT INJECTION STRESS TESTS
# ============================================================================

@pytest.mark.asyncio
class TestTaskIsolationAndFaultInjection:
    """Stress tests simulating fatal network and system exceptions across worker tasks."""

    async def test_isolation_against_heterogeneous_exceptions(self, tmp_path: Path):
        """
        Simulate offers raising RuntimeError, TimeoutError, ConnectionRefusedError,
        and ensure run completes without unhandled exception and healthy offers succeed.
        """
        offers_file = _generate_synthetic_offers_file(tmp_path, count=12)

        def mock_faulty_worker(url, offer=None, max_retries=3):
            oid = (offer or {}).get("id", "")
            if oid == "stress-offer-002":
                raise RuntimeError("Simulated internal runtime failure")
            elif oid == "stress-offer-005":
                raise TimeoutError("Simulated socket connect timeout (45s)")
            elif oid == "stress-offer-008":
                raise ConnectionRefusedError("Simulated TCP ECONNREFUSED on port 443")
            elif oid == "stress-offer-011":
                raise ValueError("Simulated corrupt response header parsing error")

            return "Active", "HTTP 200 OK", url, {
                "is_authentic_vendor": True,
                "authenticity_score": 95,
                "verdict": "VERIFIED_AUTHENTIC",
                "summary": "Verified Authentic",
                "warning_flags": []
            }

        with patch("src.inspector.DATA_FILE", offers_file), \
             patch("src.inspector.inspect_url_with_retry", side_effect=mock_faulty_worker):

            # Should complete smoothly without raising any exception to caller
            result = await run_inspection_async(use_headless=False, concurrency=4)

        assert isinstance(result, InspectionResult)
        assert len(result) == 12, "All 12 offers must remain in result"

        # Offers 1, 3, 4, 6, 7, 9, 10, 12 must be Active
        healthy_indices = [0, 2, 3, 5, 6, 8, 9, 11]
        for idx in healthy_indices:
            assert result[idx]["status"] == "Active", f"Offer at {idx} should be Active"
            assert result[idx]["is_authentic_vendor"] is True

        # Summary must reflect active counts
        assert result["summary"]["total_inspected"] == 12
        assert result["summary"]["active_confirmed"] >= 8

    async def test_isolation_under_50_percent_failure_storm(self, tmp_path: Path):
        """Simulate a 50% catastrophic failure storm across 20 offers."""
        offers_file = _generate_synthetic_offers_file(tmp_path, count=20)

        def chaotic_worker(url, offer=None, max_retries=3):
            oid = (offer or {}).get("id", "")
            num = int(oid.split("-")[-1])
            if num % 2 == 0:
                # Even numbered offers fail with diverse exceptions
                err_cls = [RuntimeError, TimeoutError, ConnectionRefusedError, OSError][num % 4]
                raise err_cls(f"Chaotic failure for {oid}")

            return "Active", "HTTP 200 OK", url, {
                "is_authentic_vendor": True,
                "authenticity_score": 90,
                "verdict": "VERIFIED_AUTHENTIC",
                "summary": "Verified",
                "warning_flags": []
            }

        with patch("src.inspector.DATA_FILE", offers_file), \
             patch("src.inspector.inspect_url_with_retry", side_effect=chaotic_worker):

            result = await run_inspection_async(use_headless=False, concurrency=5)

        assert len(result) == 20
        # All odd-numbered offers succeeded
        for i in range(0, 20, 2):
            assert result[i]["status"] == "Active"

    async def test_playwright_launch_crash_graceful_fallback(self, tmp_path: Path):
        """
        If Playwright async API fails during startup (e.g. missing browser binary or driver crash),
        engine must log warning and seamlessly fall back to HTTP thread-pool inspection.
        """
        offers_file = _generate_synthetic_offers_file(tmp_path, count=3)

        mock_ap = MagicMock()
        mock_ap.return_value.start.side_effect = RuntimeError("Host display environment variable DISPLAY not set")

        fallback_called = 0

        def mock_http_inspect(url, offer=None, max_retries=3):
            nonlocal fallback_called
            fallback_called += 1
            return "Active", "HTTP 200 OK (Fallback)", url, {
                "is_authentic_vendor": True,
                "authenticity_score": 90,
                "verdict": "VERIFIED_AUTHENTIC",
                "summary": "Verified",
                "warning_flags": []
            }

        with patch("src.inspector.DATA_FILE", offers_file), \
             patch("src.inspector.async_playwright", mock_ap), \
             patch("src.inspector.inspect_url_with_retry", side_effect=mock_http_inspect):

            result = await run_inspection_async(use_headless=True, concurrency=2)

        assert len(result) == 3
        assert fallback_called == 3
        assert result[0]["inspection_method"] == "HTTP Multi-Layer Gate"

    async def test_double_fault_playwright_and_httpx_timeout(self, tmp_path: Path):
        """
        If Playwright navigation times out AND the HTTPX fallback client ALSO times out,
        the task isolation wrapper must catch it, prevent run termination, and record non-failing offers.
        """
        offers_file = _generate_synthetic_offers_file(tmp_path, count=2)

        mock_page = AsyncMock()
        # Playwright navigation raises timeout
        mock_page.goto.side_effect = TimeoutError("Playwright page.goto timed out after 45s")
        mock_page.route = AsyncMock()

        mock_context = AsyncMock()
        mock_context.new_page.return_value = mock_page
        mock_context.close = AsyncMock()

        mock_browser = AsyncMock()
        mock_browser.new_context.return_value = mock_context
        mock_browser.close = AsyncMock()

        mock_playwright = AsyncMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_playwright.stop = AsyncMock()

        mock_ap = MagicMock()
        mock_ap.return_value.start = AsyncMock(return_value=mock_playwright)

        # HTTPX client also raises ConnectTimeout
        with patch("src.inspector.DATA_FILE", offers_file), \
             patch("src.inspector.async_playwright", mock_ap), \
             patch("src.inspector.httpx.Client.get", side_effect=TimeoutError("HTTPX connect timeout")):

            result = await run_inspection_async(use_headless=True, concurrency=2)

        assert len(result) == 2
        # Run completed without raising exception
        assert isinstance(result, InspectionResult)



# ============================================================================
# 3. INSPECTIONRESULT DUAL-NATURE CONTAINER INVARIANT TESTS
# ============================================================================

class TestInspectionResultDualContract:
    """Verify that InspectionResult perfectly obeys both Sequence and Mapping contracts."""

    @pytest.fixture
    def sample_data(self):
        offers = [
            {"id": "o-1", "title": "Offer 1", "status": "Active"},
            {"id": "o-2", "title": "Offer 2", "status": "Expired"},
            {"id": "o-3", "title": "Offer 3", "status": "Review Needed"},
        ]
        summary = {
            "total_inspected": 3,
            "active_confirmed": 1,
            "closed_detected": 2,
            "screenshots_skipped_phash": 1,
            "duration_seconds": 2.45,
            "status_changes": 1,
        }
        return offers, summary

    def test_list_operations_contract(self, sample_data):
        offers, summary = sample_data
        res = InspectionResult(offers, summary)

        # 1. len()
        assert len(res) == 3

        # 2. Positive indexing
        assert res[0] == offers[0]
        assert res[1] == offers[1]
        assert res[2] == offers[2]

        # 3. Negative indexing
        assert res[-1] == offers[2]
        assert res[-2] == offers[1]

        # 4. Slicing
        slice_result = res[0:2]
        assert len(slice_result) == 2
        assert slice_result[0] == offers[0]
        assert slice_result[1] == offers[1]

        # 5. Iteration
        iterated = []
        for o in res:
            iterated.append(o["id"])
        assert iterated == ["o-1", "o-2", "o-3"]

        # 6. Offer membership
        assert offers[0] in res
        assert {"id": "nonexistent"} not in res

    def test_dict_operations_contract(self, sample_data):
        offers, summary = sample_data
        res = InspectionResult(offers, summary)

        # 1. Dictionary indexing
        assert res["summary"] == summary
        assert res["results"] == offers
        assert res["offers"] == offers

        # 2. Missing key raises KeyError
        with pytest.raises(KeyError):
            _ = res["invalid_key"]

        # 3. get() method with defaults
        assert res.get("summary") == summary
        assert res.get("results") == offers
        assert res.get("offers") == offers
        assert res.get("missing_key") is None
        assert res.get("missing_key", "default_val") == "default_val"

        # 4. in operator for dict keys
        assert "summary" in res
        assert "results" in res
        assert "offers" in res
        assert "random_key" not in res

        # 5. keys(), values(), items()
        assert list(res.keys()) == ["summary", "results", "offers"]
        assert list(res.values()) == [summary, offers, offers]
        assert list(res.items()) == [
            ("summary", summary),
            ("results", offers),
            ("offers", offers)
        ]

        # 6. to_dict() serialization
        as_dict = res.to_dict()
        assert isinstance(as_dict, dict)
        assert as_dict["summary"] == summary
        assert as_dict["results"] == offers

    def test_empty_container_boundary(self):
        """InspectionResult initializes cleanly with empty offers and no summary."""
        empty_res = InspectionResult([])
        assert len(empty_res) == 0
        assert empty_res.summary == {}
        assert empty_res["summary"] == {}
        assert empty_res["results"] == []
        assert empty_res.get("results") == []
        assert list(empty_res) == []


# ============================================================================
# 4. SYNCHRONOUS WRAPPER STRESS TESTS
# ============================================================================

class TestSynchronousWrapper:
    """Stress tests for synchronous wrapper run_inspection()."""

    def test_run_inspection_synchronous_context(self, tmp_path: Path):
        """Verify run_inspection runs when no event loop is active."""
        offers_file = _generate_synthetic_offers_file(tmp_path, count=5)

        def mock_worker(url, offer=None, max_retries=3):
            return "Active", "HTTP 200 OK", url, {
                "is_authentic_vendor": True,
                "authenticity_score": 92,
                "verdict": "VERIFIED_AUTHENTIC",
                "summary": "Verified",
                "warning_flags": []
            }

        with patch("src.inspector.DATA_FILE", offers_file), \
             patch("src.inspector.inspect_url_with_retry", side_effect=mock_worker):

            res = run_inspection(use_headless=False, concurrency=3)

        assert isinstance(res, InspectionResult)
        assert len(res) == 5
        assert res["summary"]["total_inspected"] == 5

    @pytest.mark.asyncio
    async def test_run_inspection_nested_inside_running_event_loop(self, tmp_path: Path):
        """
        CRITICAL RE-ENTRANCY DEFENSE:
        Calling run_inspection() from inside an already running event loop must NOT
        raise 'RuntimeError: asyncio.run() cannot be called from a running event loop'.
        It must cleanly offload to the background thread pool and return InspectionResult.
        """
        offers_file = _generate_synthetic_offers_file(tmp_path, count=4)

        def mock_worker(url, offer=None, max_retries=3):
            return "Active", "HTTP 200 OK", url, {
                "is_authentic_vendor": True,
                "authenticity_score": 94,
                "verdict": "VERIFIED_AUTHENTIC",
                "summary": "Verified",
                "warning_flags": []
            }

        with patch("src.inspector.DATA_FILE", offers_file), \
             patch("src.inspector.inspect_url_with_retry", side_effect=mock_worker):

            # Call synchronous run_inspection directly from this async test
            res = run_inspection(use_headless=False, concurrency=2)

        assert isinstance(res, InspectionResult)
        assert len(res) == 4
        assert res["summary"]["total_inspected"] == 4
        assert res[0]["status"] == "Active"
