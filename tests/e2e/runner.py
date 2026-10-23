"""
Unified Standalone CLI Test Runner for CertPulse E2E Test Suite.
Executes Tier 1, Tier 2, Tier 3, and Tier 4 suites and prints a structured metrics report.

Usage:
    python tests/e2e/runner.py
    python tests/e2e/runner.py --tier 1
    python tests/e2e/runner.py --verbose
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple
import pytest

E2E_DIR = Path(__file__).resolve().parent

TIER_FILES: Dict[str, Tuple[str, Path]] = {
    "Tier 1": ("Feature Isolation", E2E_DIR / "test_tier1_features.py"),
    "Tier 2": ("Boundary & Corner Cases", E2E_DIR / "test_tier2_boundaries.py"),
    "Tier 3": ("Cross-Feature Combinations", E2E_DIR / "test_tier3_combinations.py"),
    "Tier 4": ("Real-World Application Scenarios", E2E_DIR / "test_tier4_scenarios.py"),
}


class TierResultCollector:
    """Pytest plugin collecting pass/fail statistics per tier run."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.errors = 0

    def pytest_runtest_logreport(self, report):
        if report.when == "call":
            if report.passed:
                self.passed += 1
            elif report.failed:
                self.failed += 1
            elif report.skipped:
                self.skipped += 1
        elif report.failed and report.when in ("setup", "teardown"):
            self.errors += 1

    @property
    def total(self) -> int:
        return self.passed + self.failed + self.skipped + self.errors


def run_single_tier(tier_key: str, tier_name: str, file_path: Path, verbose: bool = False) -> Tuple[int, TierResultCollector, float]:
    """Runs a single test tier via pytest and collects execution telemetry."""
    collector = TierResultCollector()
    args = [str(file_path), "-q" if not verbose else "-v"]

    start_time = time.perf_counter()
    exit_code = pytest.main(args, plugins=[collector])
    duration = time.perf_counter() - start_time

    return int(exit_code), collector, duration


def print_banner():
    print("=" * 80)
    print("            CertPulse End-to-End (E2E) Test Suite Runner            ")
    print("            Requirement-Driven Opaque-Box Quality Verification       ")
    print("=" * 80)


def print_summary(tier_metrics: List[Dict[str, Any]], total_duration: float) -> int:
    """Prints formatted summary table and determines overall exit code."""
    print("\n" + "-" * 80)
    print(f"{'Tier':<10} | {'Scope / Description':<32} | {'Passed':<8} | {'Failed':<8} | {'Duration':<10}")
    print("-" * 80)

    total_passed = 0
    total_failed = 0
    total_count = 0
    has_failure = False

    for m in tier_metrics:
        total_passed += m["passed"]
        total_failed += m["failed"]
        total_count += m["total"]
        if m["failed"] > 0 or m["exit_code"] != 0:
            has_failure = True

        status_str = f"{m['passed']}/{m['total']}"
        fail_str = str(m["failed"]) if m["failed"] > 0 else "0"
        dur_str = f"{m['duration']:.2f}s"
        print(f"{m['tier']:<10} | {m['name']:<32} | {status_str:<8} | {fail_str:<8} | {dur_str:<10}")

    print("-" * 80)
    pass_rate = (total_passed / total_count * 100.0) if total_count > 0 else 0.0
    print(f"Total Tests Executed: {total_count}  |  Passed: {total_passed}  |  Failed: {total_failed}  |  Pass Rate: {pass_rate:.1f}%")
    print(f"Overall Suite Wall Time: {total_duration:.2f} seconds")
    print("=" * 80)

    if not has_failure:
        print("[SUCCESS] All E2E test suites passed with 100% determinism!")
        return 0
    else:
        print("[FAILURE] One or more E2E test suites encountered test failures.")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="CertPulse E2E Standalone Test Runner")
    parser.add_argument("--tier", type=int, choices=[1, 2, 3, 4], help="Run a specific tier only (1, 2, 3, or 4)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose pytest output")
    args = parser.parse_args()

    print_banner()

    tiers_to_run = TIER_FILES
    if args.tier:
        target_key = f"Tier {args.tier}"
        tiers_to_run = {target_key: TIER_FILES[target_key]}

    tier_metrics = []
    overall_start = time.perf_counter()

    for tier_key, (tier_desc, file_path) in tiers_to_run.items():
        if not file_path.exists():
            print(f"[ERROR] Test file {file_path} does not exist.")
            return 2

        print(f"\n>> Executing {tier_key}: {tier_desc} ({file_path.name})...")
        code, collector, dur = run_single_tier(tier_key, tier_desc, file_path, verbose=args.verbose)

        tier_metrics.append({
            "tier": tier_key,
            "name": tier_desc,
            "passed": collector.passed,
            "failed": collector.failed,
            "total": collector.total,
            "duration": dur,
            "exit_code": code,
        })

    overall_duration = time.perf_counter() - overall_start
    return print_summary(tier_metrics, overall_duration)


if __name__ == "__main__":
    sys.exit(main())
