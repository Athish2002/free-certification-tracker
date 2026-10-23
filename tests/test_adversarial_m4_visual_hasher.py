"""
Adversarial Stress Test Suite for Visual Perceptual Hasher & Delta-Skipping (Milestone M4).

Challenger: challenger_m4_1
Focus: should_skip_screenshot_write adversarial boundary testing, edge cases,
       corruption resilience, status transition invariants, and type safety.
"""

from __future__ import annotations

import concurrent.futures
import io
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
from PIL import Image

from src.visual_hasher import (
    PerceptualHashEngine,
    should_skip_screenshot_write,
)


def _create_valid_png(size: tuple[int, int] = (250, 250), seed: int = 42) -> bytes:
    """Creates a deterministic valid PNG payload guaranteed to be >= 4096 bytes with PNG magic header."""
    rng = np.random.default_rng(seed)
    arr = rng.integers(30, 220, (size[1], size[0], 3), dtype=np.uint8)
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    val = buf.getvalue()
    assert len(val) >= 4096
    assert val[:8] == b"\x89PNG\r\n\x1a\n"
    return val


class TestAdversarialDeltaSkippingBoundaries:
    """Stress-test the exact mathematical boundaries of Hamming distance and delta thresholds."""

    @pytest.fixture
    def baseline_png_file(self, tmp_path: Path) -> Path:
        p = tmp_path / "valid_baseline.png"
        p.write_bytes(_create_valid_png(seed=100))
        return p

    def test_hamming_0_identical_image(self, baseline_png_file: Path):
        """Hamming distance 0 (exact match) MUST return True, delta 0.0, dist 0."""
        png_data = baseline_png_file.read_bytes()
        skip, delta, dist = should_skip_screenshot_write(
            new_image=png_data,
            existing_screenshot_path=baseline_png_file,
            old_status="Active",
            new_status="Active",
            delta_threshold=0.05,
        )
        assert skip is True
        assert delta == 0.0
        assert dist == 0

    @pytest.mark.parametrize("target_dist,expected_skip", [
        (0, True),
        (1, True),
        (2, True),
        (3, True),
        (4, False),
        (5, False),
        (10, False),
        (64, False),
    ])
    def test_controlled_hamming_boundary_at_threshold_0_05(
        self, baseline_png_file: Path, target_dist: int, expected_skip: bool
    ):
        """
        Threshold boundary stress:
        delta_threshold = 0.05
        dist=0 -> delta=0.000000 -> < 0.05 -> True
        dist=1 -> delta=0.015625 -> < 0.05 -> True
        dist=2 -> delta=0.031250 -> < 0.05 -> True
        dist=3 -> delta=0.046875 -> < 0.05 -> True
        dist=4 -> delta=0.062500 -> >= 0.05 -> False
        """
        # Baseline pHash: 64 zeros (16 hex chars)
        base_hash = "0000000000000000"
        # Generate hash with exact target_dist bits set to 1
        val = (1 << target_dist) - 1 if target_dist <= 64 else 0
        target_hash = f"{val:016x}"
        assert PerceptualHashEngine.hamming_distance(base_hash, target_hash) == target_dist

        # Patch compute_phash so existing returns base_hash and new_image returns target_hash
        def mock_compute(img_input, **kwargs):
            if isinstance(img_input, Path) and img_input == baseline_png_file:
                return base_hash
            return target_hash

        with patch.object(PerceptualHashEngine, "compute_phash", side_effect=mock_compute):
            skip, delta, dist = should_skip_screenshot_write(
                new_image=b"dummy_bytes",
                existing_screenshot_path=baseline_png_file,
                old_status="Active",
                new_status="Active",
                delta_threshold=0.05,
            )

            expected_delta = target_dist / 64.0
            assert dist == target_dist
            assert pytest.approx(delta, 1e-6) == expected_delta
            assert skip is expected_skip, (
                f"Boundary failure at dist={target_dist}, delta={delta:.6f}: "
                f"expected skip={expected_skip}, got {skip}"
            )

    @pytest.mark.parametrize("delta_threshold,dist,expected_skip", [
        (0.00, 0, False),   # delta 0.0 not < 0.00 -> False
        (0.01, 0, True),    # delta 0.0 < 0.01 -> True
        (0.0625, 4, False), # delta 4/64 = 0.0625 not < 0.0625 -> False
        (0.0626, 4, True),  # delta 4/64 = 0.0625 < 0.0626 -> True
        (1.00, 64, False),  # delta 64/64 = 1.0 not < 1.0 -> False
        (1.01, 64, True),   # delta 64/64 = 1.0 < 1.01 -> True
    ])
    def test_custom_delta_threshold_edge_cases(
        self, baseline_png_file: Path, delta_threshold: float, dist: int, expected_skip: bool
    ):
        """Precision test on custom threshold values."""
        base_hash = "0000000000000000"
        val = (1 << dist) - 1
        target_hash = f"{val:016x}"

        with patch.object(PerceptualHashEngine, "compute_phash") as mock_phash:
            mock_phash.side_effect = lambda inp, **kwargs: base_hash if isinstance(inp, Path) else target_hash
            skip, delta, out_dist = should_skip_screenshot_write(
                new_image=b"custom_payload",
                existing_screenshot_path=baseline_png_file,
                old_status="Active",
                new_status="Active",
                delta_threshold=delta_threshold,
            )
            assert out_dist == dist
            assert skip is expected_skip


class TestAdversarialStatusTransitions:
    """Stress-test status transition invariance."""

    @pytest.fixture
    def baseline_png_file(self, tmp_path: Path) -> Path:
        p = tmp_path / "valid_baseline.png"
        p.write_bytes(_create_valid_png(seed=200))
        return p

    @pytest.mark.parametrize("old_st,new_st,expected_skip", [
        # Disparate statuses MUST force write (skip=False, delta=1.0, dist=64)
        ("Active", "Expired", False),
        ("Active", "Closed", False),
        ("Active", "Review Needed", False),
        ("Active", "Registrations Closed", False),
        ("Expired", "Active", False),
        ("Review Needed", "Active", False),
        ("Broken Link", "Active", False),
        ("Active", "Upcoming", False),
        ("Active", "", False),
        ("", "Active", False),
        # Identical status under case and whitespace variations MUST allow skipping
        ("Active", "Active", True),
        ("Active", "active", True),
        ("ACTIVE", "active", True),
        ("  Active  ", "active", True),
        ("Review Needed", "review needed", True),
        # Non-string or coercible types
        (1, "1", True),
        (True, "True", True),
    ])
    def test_status_transitions_with_identical_image(
        self, baseline_png_file: Path, old_st: any, new_st: any, expected_skip: bool
    ):
        png_data = baseline_png_file.read_bytes()
        skip, delta, dist = should_skip_screenshot_write(
            new_image=png_data,
            existing_screenshot_path=baseline_png_file,
            old_status=old_st,
            new_status=new_st,
            delta_threshold=0.05,
        )
        assert skip is expected_skip
        if not expected_skip:
            assert delta == 1.0
            assert dist == 64
        else:
            assert delta == 0.0
            assert dist == 0


class TestAdversarialCorruptAndInvalidExistingFiles:
    """Stress-test invalid, corrupted, or undersized existing screenshot targets."""

    @pytest.fixture
    def valid_new_png(self) -> bytes:
        return _create_valid_png(seed=300)

    def test_existing_path_is_none(self, valid_new_png: bytes):
        skip, delta, dist = should_skip_screenshot_write(
            new_image=valid_new_png,
            existing_screenshot_path=None,  # type: ignore
            old_status="Active",
            new_status="Active",
        )
        assert skip is False
        assert delta == 1.0
        assert dist == 64

    def test_existing_file_does_not_exist(self, tmp_path: Path, valid_new_png: bytes):
        missing = tmp_path / "ghost_file.png"
        skip, delta, dist = should_skip_screenshot_write(
            new_image=valid_new_png,
            existing_screenshot_path=missing,
            old_status="Active",
            new_status="Active",
        )
        assert skip is False
        assert delta == 1.0
        assert dist == 64

    def test_existing_target_is_a_directory(self, tmp_path: Path, valid_new_png: bytes):
        sub_dir = tmp_path / "screenshots_dir"
        sub_dir.mkdir()
        skip, delta, dist = should_skip_screenshot_write(
            new_image=valid_new_png,
            existing_screenshot_path=sub_dir,
            old_status="Active",
            new_status="Active",
        )
        assert skip is False
        assert delta == 1.0
        assert dist == 64

    def test_existing_file_is_zero_bytes(self, tmp_path: Path, valid_new_png: bytes):
        empty_file = tmp_path / "empty.png"
        empty_file.write_bytes(b"")
        skip, delta, dist = should_skip_screenshot_write(
            new_image=valid_new_png,
            existing_screenshot_path=empty_file,
            old_status="Active",
            new_status="Active",
        )
        assert skip is False
        assert delta == 1.0
        assert dist == 64

    def test_existing_file_is_exactly_4095_bytes_boundary(self, tmp_path: Path, valid_new_png: bytes):
        """Files strictly below 4096 bytes MUST force rewrite."""
        boundary_file = tmp_path / "boundary_4095.png"
        boundary_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * (4095 - 8))
        assert boundary_file.stat().st_size == 4095

        skip, delta, dist = should_skip_screenshot_write(
            new_image=valid_new_png,
            existing_screenshot_path=boundary_file,
            old_status="Active",
            new_status="Active",
        )
        assert skip is False
        assert delta == 1.0
        assert dist == 64

    def test_existing_file_large_text_file(self, tmp_path: Path, valid_new_png: bytes):
        """Text file >= 4096 bytes without PNG header MUST force rewrite."""
        text_file = tmp_path / "readme.txt"
        text_file.write_text("A" * 10000, encoding="utf-8")
        assert text_file.stat().st_size >= 4096

        skip, delta, dist = should_skip_screenshot_write(
            new_image=valid_new_png,
            existing_screenshot_path=text_file,
            old_status="Active",
            new_status="Active",
        )
        assert skip is False
        assert delta == 1.0
        assert dist == 64

    def test_existing_file_jpeg_magic_bytes(self, tmp_path: Path, valid_new_png: bytes):
        """JPEG file >= 4096 bytes with FF D8 FF magic bytes MUST force rewrite."""
        jpeg_file = tmp_path / "photo.jpg"
        jpeg_file.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 5000)
        assert jpeg_file.stat().st_size >= 4096

        skip, delta, dist = should_skip_screenshot_write(
            new_image=valid_new_png,
            existing_screenshot_path=jpeg_file,
            old_status="Active",
            new_status="Active",
        )
        assert skip is False
        assert delta == 1.0
        assert dist == 64

    def test_existing_file_png_header_but_corrupt_data(self, tmp_path: Path, valid_new_png: bytes):
        """File >= 4096 bytes with PNG header but garbage body raises hash error, caught safely."""
        corrupt_body = tmp_path / "corrupt_body.png"
        corrupt_body.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\xff" * 5000)
        assert corrupt_body.stat().st_size >= 4096

        skip, delta, dist = should_skip_screenshot_write(
            new_image=valid_new_png,
            existing_screenshot_path=corrupt_body,
            old_status="Active",
            new_status="Active",
        )
        assert skip is False
        assert delta == 1.0
        assert dist == 64


class TestAdversarialNewImageInputs:
    """Stress-test invalid, aberrant, or hostile new_image inputs."""

    @pytest.fixture
    def baseline_png_file(self, tmp_path: Path) -> Path:
        p = tmp_path / "valid_baseline.png"
        p.write_bytes(_create_valid_png(seed=400))
        return p

    def test_new_image_none(self, baseline_png_file: Path):
        skip, delta, dist = should_skip_screenshot_write(
            new_image=None,  # type: ignore
            existing_screenshot_path=baseline_png_file,
            old_status="Active",
            new_status="Active",
        )
        assert skip is False
        assert delta == 1.0
        assert dist == 64

    def test_new_image_empty_bytes(self, baseline_png_file: Path):
        skip, delta, dist = should_skip_screenshot_write(
            new_image=b"",
            existing_screenshot_path=baseline_png_file,
            old_status="Active",
            new_status="Active",
        )
        assert skip is False
        assert delta == 1.0
        assert dist == 64

    def test_new_image_arbitrary_unsupported_types(self, baseline_png_file: Path):
        for bad_input in [12345, [1, 2, 3], {"type": "image"}, 3.14159]:
            skip, delta, dist = should_skip_screenshot_write(
                new_image=bad_input,  # type: ignore
                existing_screenshot_path=baseline_png_file,
                old_status="Active",
                new_status="Active",
            )
            assert skip is False
            assert delta == 1.0
            assert dist == 64

    def test_new_image_nonexistent_filepath(self, baseline_png_file: Path, tmp_path: Path):
        ghost_path = tmp_path / "does_not_exist_new.png"
        skip, delta, dist = should_skip_screenshot_write(
            new_image=ghost_path,
            existing_screenshot_path=baseline_png_file,
            old_status="Active",
            new_status="Active",
        )
        assert skip is False
        assert delta == 1.0
        assert dist == 64

    def test_new_image_pil_instance(self, baseline_png_file: Path):
        """PIL Image instance passed as new_image should work smoothly."""
        with Image.open(baseline_png_file) as img:
            skip, delta, dist = should_skip_screenshot_write(
                new_image=img,
                existing_screenshot_path=baseline_png_file,
                old_status="Active",
                new_status="Active",
            )
            assert skip is True
            assert delta == 0.0
            assert dist == 0


class TestAdversarialConcurrencyAndThreadSafety:
    """Stress-test concurrent evaluations on the same existing screenshot file."""

    def test_concurrent_identical_checks_do_not_deadlock(self, tmp_path: Path):
        png_data = _create_valid_png(seed=500)
        target = tmp_path / "shared_target.png"
        target.write_bytes(png_data)

        def worker_check(thread_id: int):
            return should_skip_screenshot_write(
                new_image=png_data,
                existing_screenshot_path=target,
                old_status="Active",
                new_status="Active",
                delta_threshold=0.05,
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker_check, i) for i in range(30)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert len(results) == 30
        for skip, delta, dist in results:
            assert skip is True
            assert delta == 0.0
            assert dist == 0
