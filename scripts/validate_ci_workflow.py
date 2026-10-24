#!/usr/bin/env python3
"""
Pre-commit and maintenance validation script for GitHub Actions CI Workflow (.github/workflows/tracker.yml).

Validates:
1. Workflow file exists and parses as valid YAML without errors.
2. Triggers (schedule cron '0 */4 * * *', push to main, workflow_dispatch) are preserved.
3. Root permissions (contents: write, pages: write, id-token: write) are preserved.
4. Concurrency group configuration is preserved.
5. Dual-job / matrix architecture:
   - 'test' job runs on ubuntu-latest with Python 3.12 & 3.13 matrix.
   - 'test' job installs dependencies including pytest-xdist.
   - 'test' job executes parallelized pytest discovery with '-n auto' and E2E runner.
   - 'update-and-deploy' job gates on testing via 'needs: test'.
   - 'update-and-deploy' job executes 'python -m src.main' and E2E verification.
   - 'update-and-deploy' job preserves auto-commit file_pattern covering data, docs, screenshots, and readme.
   - 'deploy-pages' job gates on 'update-and-deploy'.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict
import yaml

WORKFLOW_PATH = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "tracker.yml"


def load_workflow() -> Dict[str, Any]:
    if not WORKFLOW_PATH.exists():
        raise FileNotFoundError(f"Workflow file not found at {WORKFLOW_PATH}")
    with open(WORKFLOW_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError("Parsed workflow is not a dictionary")
    return data


def validate_workflow(workflow_yaml: Dict[str, Any]) -> None:
    # 1. Triggers & Permissions
    name = workflow_yaml.get("name")
    assert name and "CertPulse" in name, f"Invalid workflow name: {name}"

    on_trigger = workflow_yaml.get("on") or workflow_yaml.get(True)
    assert on_trigger, "Workflow triggers ('on') not configured"
    assert "push" in on_trigger, "Push trigger missing"
    assert "main" in on_trigger["push"].get("branches", []), "main branch not in push branches"

    assert "schedule" in on_trigger, "Schedule trigger missing"
    schedules = on_trigger["schedule"]
    crons = [s.get("cron") for s in schedules if isinstance(s, dict)]
    assert "0 */4 * * *" in crons, f"Expected cron '0 */4 * * *' not found in {crons}"
    assert "workflow_dispatch" in on_trigger, "workflow_dispatch trigger missing"

    perms = workflow_yaml.get("permissions", {})
    assert perms.get("contents") == "write", "Missing 'contents: write' permission"
    assert perms.get("pages") == "write", "Missing 'pages: write' permission"
    assert perms.get("id-token") == "write", "Missing 'id-token: write' permission"

    concurrency = workflow_yaml.get("concurrency", {})
    assert concurrency.get("group") == "certpulse-tracker"
    assert concurrency.get("cancel-in-progress") is False

    # 2. Test Job Matrix
    jobs = workflow_yaml.get("jobs", {})
    assert "test" in jobs, "Job 'test' not found in workflow jobs"
    test_job = jobs["test"]
    assert test_job.get("runs-on") == "ubuntu-latest"

    strategy = test_job.get("strategy", {})
    versions = [str(v) for v in strategy.get("matrix", {}).get("python-version", [])]
    assert "3.12" in versions, f"Python 3.12 missing from matrix: {versions}"
    assert "3.13" in versions, f"Python 3.13 missing from matrix: {versions}"

    steps = test_job.get("steps", [])
    dep_steps = [s for s in steps if "run" in s and "pip install" in s["run"]]
    combined_dep_runs = "\n".join(s["run"] for s in dep_steps)
    assert "pytest-xdist" in combined_dep_runs, "pytest-xdist not installed in test job"
    assert "pytest-asyncio" in combined_dep_runs, "pytest-asyncio not installed in test job"
    assert "requirements.txt" in combined_dep_runs, "requirements.txt not installed in test job"

    test_steps = [s for s in steps if "run" in s and "pytest" in s["run"]]
    combined_test_runs = "\n".join(s["run"] for s in test_steps)
    assert "-n auto" in combined_test_runs, "Parallel flag '-n auto' missing from test command"

    e2e_steps = [s for s in steps if "run" in s and "tests/e2e/runner.py" in s["run"]]
    assert e2e_steps, "E2E runner execution step missing in test job"

    cache_steps = [s for s in steps if "actions/cache" in s.get("uses", "") and "ms-playwright" in s.get("with", {}).get("path", "")]
    assert cache_steps, "Playwright browser cache step missing in test job"

    schema_steps = [s for s in steps if "run" in s and "schema.json" in s["run"]]
    assert schema_steps, "JSON schema validation step missing in test job"

    # 3. Update-and-Deploy Job
    assert "update-and-deploy" in jobs, "'update-and-deploy' job missing"
    up_job = jobs["update-and-deploy"]
    needs = up_job.get("needs")
    assert needs == "test" or (isinstance(needs, list) and "test" in needs), f"'test' not in needs: {needs}"

    up_steps = up_job.get("steps", [])
    pipeline_steps = [s for s in up_steps if "run" in s and "python -m src.main" in s["run"]]
    assert pipeline_steps, "Step executing 'python -m src.main' missing"

    commit_steps = [s for s in up_steps if "stefanzweifel/git-auto-commit-action" in s.get("uses", "")]
    assert commit_steps, "git-auto-commit-action step missing"
    pattern = commit_steps[0].get("with", {}).get("file_pattern", "")
    for rp in ["README.md", "data/*.json", "data/*.jsonl", "docs/index.html", "docs/*.md", "docs/screenshots/*.png"]:
        assert rp in pattern, f"Required pattern '{rp}' missing from file_pattern: '{pattern}'"

    # 4. Deploy-Pages Job
    assert "deploy-pages" in jobs, "'deploy-pages' job missing"
    deploy_job = jobs["deploy-pages"]
    d_needs = deploy_job.get("needs")
    assert d_needs == "update-and-deploy" or (isinstance(d_needs, list) and "update-and-deploy" in d_needs)


def main() -> int:
    try:
        wf = load_workflow()
        validate_workflow(wf)
        print("[PASS] GitHub Actions workflow (.github/workflows/tracker.yml) is valid and fully compliant.")
        return 0
    except Exception as err:
        print(f"[FAIL] Workflow validation failed: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
