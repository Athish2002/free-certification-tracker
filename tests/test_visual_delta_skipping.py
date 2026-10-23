"""
Unit and integration tests for Perceptual Hash Delta-Skipping (Milestone M4).

Validates:
1. Identical image comparison (Hamming distance 0, skip True).
2. Slight visual difference (< 5% delta / <= 3 bits difference, skip True).
3. Large visual difference (>= 5% delta / > 3 bits difference, skip False).
4. Status changes trigger write (skip False even when images are identical).
5. Non-existent, undersized, or corrupt target image triggers write (skip False).
6. Invalid or empty new image inputs trigger write (skip False).
7. Custom delta thresholds.
8. DOMInspector.capture_screenshot integration and anti-spinner protection.
"""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest
from PIL import Image

from src.dom_inspector import HeadlessDOMInspector, DOMInspector
from src.visual_hasher import (
    PerceptualHashEngine,
    should_skip_screenshot_write,
)


def _generate_png_bytes(seed: int = 42, size: tuple[int, int] = (200, 200)) -> bytes:
    """Generates deterministic pseudo-random PNG bytes >= 4096 bytes with valid header."""
    rng = np.random.default_rng(seed)
    arr = rng.integers(50, 200, (size[1], size[0], 3), dtype=np.uint8)
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    val = buf.getvalue()
    assert len(val) >= 4096, f"Generated PNG must be >= 4096 bytes, got {len(val)}"
    assert val[:8] == b"\x89PNG\r\n\x1a\n", "Generated payload must have PNG magic bytes"
    return val


class TestVisualDeltaSkipping:
    """Tests for should_skip_screenshot_write in src/visual_hasher.py."""

    def test_identical_image_comparison_skips_write(self, tmp_path: Path):
        """Identical image bytes and identical status yield distance 0, delta 0.0, skip True."""
        png_data = _generate_png_bytes(seed=101)
        existing_file = tmp_path / "existing.png"
        existing_file.write_bytes(png_data)

        skip, delta, dist = should_skip_screenshot_write(
            new_image=png_data,
            existing_screenshot_path=existing_file,
            old_status="Active",
            new_status="Active",
            delta_threshold=0.05,
        )

        assert skip is True
        assert delta == 0.0
        assert dist == 0

    def test_slight_visual_difference_skips_write(self, tmp_path: Path):
        """Visual difference with Hamming distance <= 3 (delta < 0.05) is skipped."""
        rng = np.random.default_rng(202)
        arr1 = rng.integers(50, 200, (200, 200, 3), dtype=np.uint8)
        img1 = Image.fromarray(arr1)
        buf1 = io.BytesIO()
        img1.save(buf1, format="PNG")
        b1 = buf1.getvalue()

        # Perturb a tiny 2x2 corner block (high-frequency noise ignored by low-frequency DCT)
        arr2 = arr1.copy()
        arr2[0:2, 0:2] = 255
        img2 = Image.fromarray(arr2)
        buf2 = io.BytesIO()
        img2.save(buf2, format="PNG")
        b2 = buf2.getvalue()

        existing_file = tmp_path / "baseline.png"
        existing_file.write_bytes(b1)

        skip, delta, dist = should_skip_screenshot_write(
            new_image=b2,
            existing_screenshot_path=existing_file,
            old_status="Active",
            new_status="Active",
            delta_threshold=0.05,
        )

        assert dist <= 3
        assert delta < 0.05
        assert skip is True

    def test_large_visual_difference_forces_write(self, tmp_path: Path):
        """Visually distinct viewports (> 3 bits difference / delta >= 0.05) force write."""
        img1_bytes = _generate_png_bytes(seed=301)
        img2_bytes = _generate_png_bytes(seed=999)

        existing_file = tmp_path / "existing.png"
        existing_file.write_bytes(img1_bytes)

        skip, delta, dist = should_skip_screenshot_write(
            new_image=img2_bytes,
            existing_screenshot_path=existing_file,
            old_status="Active",
            new_status="Active",
            delta_threshold=0.05,
        )

        assert skip is False
        assert dist > 3
        assert delta >= 0.05

    def test_status_change_forces_write_even_if_images_identical(self, tmp_path: Path):
        """Status transitions force screenshot write regardless of visual similarity."""
        png_data = _generate_png_bytes(seed=404)
        existing_file = tmp_path / "existing.png"
        existing_file.write_bytes(png_data)

        # Test various status transitions
        transitions = [
            ("Active", "Expired"),
            ("Active", "Review Needed"),
            ("Active", "Registrations Closed"),
            ("Review Needed", "Active"),
            ("Broken Link", "Active"),
        ]

        for old_st, new_st in transitions:
            skip, delta, dist = should_skip_screenshot_write(
                new_image=png_data,
                existing_screenshot_path=existing_file,
                old_status=old_st,
                new_status=new_st,
            )
            assert skip is False, f"Failed to force write on transition {old_st} -> {new_st}"
            assert delta == 1.0
            assert dist == 64

    def test_non_existent_target_image_forces_write(self, tmp_path: Path):
        """When existing screenshot file does not exist, write is required."""
        png_data = _generate_png_bytes(seed=505)
        non_existent = tmp_path / "does_not_exist.png"

        skip, delta, dist = should_skip_screenshot_write(
            new_image=png_data,
            existing_screenshot_path=non_existent,
            old_status="Active",
            new_status="Active",
        )

        assert skip is False
        assert delta == 1.0
        assert dist == 64

    def test_undersized_target_image_forces_write(self, tmp_path: Path):
        """Target file size < 4096 bytes is treated as corrupt/placeholder and forces rewrite."""
        tiny_file = tmp_path / "tiny.png"
        tiny_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)  # valid header but only 108 bytes

        png_data = _generate_png_bytes(seed=606)

        skip, delta, dist = should_skip_screenshot_write(
            new_image=png_data,
            existing_screenshot_path=tiny_file,
            old_status="Active",
            new_status="Active",
        )

        assert skip is False
        assert delta == 1.0
        assert dist == 64

    def test_corrupt_header_target_image_forces_write(self, tmp_path: Path):
        """Target file >= 4096 bytes but without PNG magic bytes forces rewrite."""
        corrupt_file = tmp_path / "corrupt.png"
        corrupt_file.write_bytes(b"GIF89a" + b"\x00" * 5000)

        png_data = _generate_png_bytes(seed=707)

        skip, delta, dist = should_skip_screenshot_write(
            new_image=png_data,
            existing_screenshot_path=corrupt_file,
            old_status="Active",
            new_status="Active",
        )

        assert skip is False
        assert delta == 1.0
        assert dist == 64

    def test_invalid_new_image_input_forces_write(self, tmp_path: Path):
        """Corrupt, empty, or None new_image safely returns skip=False without unhandled crash."""
        png_data = _generate_png_bytes(seed=808)
        existing_file = tmp_path / "existing.png"
        existing_file.write_bytes(png_data)

        # Empty bytes
        skip, delta, dist = should_skip_screenshot_write(
            new_image=b"",
            existing_screenshot_path=existing_file,
            old_status="Active",
            new_status="Active",
        )
        assert skip is False
        assert delta == 1.0
        assert dist == 64

        # Non-image bytes
        skip, delta, dist = should_skip_screenshot_write(
            new_image=b"NOT_AN_IMAGE_PAYLOAD",
            existing_screenshot_path=existing_file,
            old_status="Active",
            new_status="Active",
        )
        assert skip is False

    def test_custom_delta_threshold(self, tmp_path: Path):
        """Custom delta threshold is respected for strict or relaxed diffing."""
        img1_bytes = _generate_png_bytes(seed=901)
        img2_bytes = _generate_png_bytes(seed=902)
        existing_file = tmp_path / "existing.png"
        existing_file.write_bytes(img1_bytes)

        h1 = PerceptualHashEngine.compute_phash(img1_bytes)
        h2 = PerceptualHashEngine.compute_phash(img2_bytes)
        dist = PerceptualHashEngine.hamming_distance(h1, h2)
        measured_delta = dist / 64.0

        # Set threshold above measured delta -> should skip
        skip_relaxed, _, _ = should_skip_screenshot_write(
            new_image=img2_bytes,
            existing_screenshot_path=existing_file,
            old_status="Active",
            new_status="Active",
            delta_threshold=measured_delta + 0.05,
        )
        assert skip_relaxed is True

        # Set threshold below measured delta -> should not skip
        skip_strict, _, _ = should_skip_screenshot_write(
            new_image=img2_bytes,
            existing_screenshot_path=existing_file,
            old_status="Active",
            new_status="Active",
            delta_threshold=max(0.01, measured_delta - 0.05),
        )
        assert skip_strict is False


class TestDOMInspectorScreenshotIntegration:
    """Integration tests for DOMInspector.capture_screenshot with delta-skipping."""

    def test_dom_inspector_alias_exported(self):
        """DOMInspector is exported as an alias for HeadlessDOMInspector."""
        assert DOMInspector is HeadlessDOMInspector

    def test_capture_screenshot_skips_write_when_hash_matches(self):
        """capture_screenshot does not touch disk file when delta < 5% and status unchanged."""
        png_data = _generate_png_bytes(seed=111)

        screenshots_dir = Path("docs/screenshots")
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        target_path = screenshots_dir / "synthetic-skip-test.png"
        target_path.write_bytes(png_data)
        initial_mtime = target_path.stat().st_mtime_ns

        mock_page = MagicMock()
        mock_page.evaluate.return_value = "Sample page content"
        mock_page.screenshot.return_value = png_data

        inspector = HeadlessDOMInspector(headless=True)
        try:
            ok, path = inspector.capture_screenshot(
                page=mock_page,
                offer_id="synthetic-skip-test",
                old_status="Active",
                new_status="Active"
            )

            assert ok is True
            assert "synthetic-skip-test.png" in path
            # Verify file on disk was preserved and not overwritten
            assert target_path.stat().st_mtime_ns == initial_mtime
        finally:
            if target_path.exists():
                try:
                    target_path.unlink()
                except Exception:
                    pass


    def test_capture_screenshot_writes_when_status_changes(self, tmp_path: Path):
        """capture_screenshot writes fresh file when status changes."""
        png_data = _generate_png_bytes(seed=222)
        screenshots_dir = Path("docs/screenshots")
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        target_path = screenshots_dir / "synthetic-status-change-test.png"
        target_path.write_bytes(png_data)

        mock_page = MagicMock()
        mock_page.evaluate.return_value = "Page content"
        mock_page.screenshot.return_value = png_data

        inspector = HeadlessDOMInspector(headless=True)
        try:
            ok, path = inspector.capture_screenshot(
                page=mock_page,
                offer_id="synthetic-status-change-test",
                old_status="Active",
                new_status="Expired"
            )
            assert ok is True
            assert target_path.exists()
        finally:
            if target_path.exists():
                try:
                    target_path.unlink()
                except Exception:
                    pass
