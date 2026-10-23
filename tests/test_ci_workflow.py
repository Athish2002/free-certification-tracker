"""
Unit and integration test suite for GitHub Actions CI Workflow Modernization (.github/workflows/tracker.yml).

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

from pathlib import Path
from typing import Any, Dict, List
import yaml
import pytest

WORKFLOW_PATH = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "tracker.yml"


@pytest.fixture(scope="module")
def workflow_yaml() -> Dict[str, Any]:
    """Loads and parses .github/workflows/tracker.yml using yaml.safe_load."""
    assert WORKFLOW_PATH.exists(), f"Workflow file not found at {WORKFLOW_PATH}"
    with open(WORKFLOW_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict), "Parsed workflow is not a dictionary"
    return data


class TestCIWorkflowConfiguration:
    """Verifies core workflow triggers, permissions, and concurrency."""

    def test_workflow_file_exists(self):
        """Assert tracker.yml exists on disk."""
        assert WORKFLOW_PATH.is_file(), f"{WORKFLOW_PATH} does not exist"

    def test_workflow_name(self, workflow_yaml: Dict[str, Any]):
        """Assert workflow name is defined and descriptive."""
        name = workflow_yaml.get("name")
        assert name and "CertPulse" in name

    def test_workflow_push_trigger(self, workflow_yaml: Dict[str, Any]):
        """Assert push trigger is configured for main branch."""
        on_trigger = workflow_yaml.get("on") or workflow_yaml.get(True)  # 'on' can parse as True in YAML 1.1
        assert on_trigger, "Workflow triggers ('on') not configured"
        assert "push" in on_trigger, "Push trigger missing"
        push_branches = on_trigger["push"].get("branches", [])
        assert "main" in push_branches, f"main branch not in push branches: {push_branches}"

    def test_workflow_schedule_trigger(self, workflow_yaml: Dict[str, Any]):
        """Assert schedule cron trigger runs every 4 hours ('0 */4 * * *')."""
        on_trigger = workflow_yaml.get("on") or workflow_yaml.get(True)
        assert "schedule" in on_trigger, "Schedule trigger missing"
        schedules = on_trigger["schedule"]
        assert isinstance(schedules, list) and len(schedules) >= 1
        crons = [s.get("cron") for s in schedules if isinstance(s, dict)]
        assert "0 */4 * * *" in crons, f"Expected cron '0 */4 * * *' not found in {crons}"

    def test_workflow_dispatch_trigger(self, workflow_yaml: Dict[str, Any]):
        """Assert workflow_dispatch trigger is present for manual runs."""
        on_trigger = workflow_yaml.get("on") or workflow_yaml.get(True)
        assert "workflow_dispatch" in on_trigger, "workflow_dispatch trigger missing"

    def test_workflow_permissions(self, workflow_yaml: Dict[str, Any]):
        """Assert all required root-level permissions are retained."""
        perms = workflow_yaml.get("permissions", {})
        assert perms.get("contents") == "write", "Missing 'contents: write' permission"
        assert perms.get("pages") == "write", "Missing 'pages: write' permission"
        assert perms.get("id-token") == "write", "Missing 'id-token: write' permission"

    def test_workflow_concurrency(self, workflow_yaml: Dict[str, Any]):
        """Assert concurrency group settings are preserved."""
        concurrency = workflow_yaml.get("concurrency", {})
        assert concurrency.get("group") == "certpulse-tracker"
        assert concurrency.get("cancel-in-progress") is False


class TestCITestJobMatrix:
    """Verifies the modernized test job with Python 3.12/3.13 matrix and parallel pytest."""

    def test_test_job_exists(self, workflow_yaml: Dict[str, Any]):
        """Assert 'test' job is present in workflow jobs."""
        jobs = workflow_yaml.get("jobs", {})
        assert "test" in jobs, "Job 'test' not found in workflow jobs"

    def test_test_job_runs_on_ubuntu(self, workflow_yaml: Dict[str, Any]):
        """Assert 'test' job runs on ubuntu-latest."""
        job = workflow_yaml["jobs"]["test"]
        assert job.get("runs-on") == "ubuntu-latest"

    def test_test_job_matrix_python_versions(self, workflow_yaml: Dict[str, Any]):
        """Assert 'test' job specifies matrix for Python 3.12 and 3.13."""
        job = workflow_yaml["jobs"]["test"]
        strategy = job.get("strategy", {})
        matrix = strategy.get("matrix", {})
        versions = matrix.get("python-version", [])
        # Versions can be strings ["3.12", "3.13"] or float parsed
        str_versions = [str(v) for v in versions]
        assert "3.12" in str_versions, f"Python 3.12 missing from matrix: {str_versions}"
        assert "3.13" in str_versions, f"Python 3.13 missing from matrix: {str_versions}"

    def test_test_job_installs_pytest_xdist(self, workflow_yaml: Dict[str, Any]):
        """Assert dependencies installation includes pytest and pytest-xdist."""
        job = workflow_yaml["jobs"]["test"]
        steps = job.get("steps", [])
        dep_steps = [s for s in steps if "run" in s and "pip install" in s["run"]]
        assert dep_steps, "No pip install step found in test job"
        combined_runs = "\n".join(s["run"] for s in dep_steps)
        assert "pytest-xdist" in combined_runs, "pytest-xdist not installed in test job"
        assert "requirements.txt" in combined_runs, "requirements.txt not installed in test job"

    def test_test_job_parallel_pytest_execution(self, workflow_yaml: Dict[str, Any]):
        """Assert pytest is executed in parallel with -n auto."""
        job = workflow_yaml["jobs"]["test"]
        steps = job.get("steps", [])
        test_steps = [s for s in steps if "run" in s and "pytest" in s["run"]]
        assert test_steps, "No pytest step found in test job"
        combined_runs = "\n".join(s["run"] for s in test_steps)
        assert "-n auto" in combined_runs, "Parallel flag '-n auto' missing from test command"

    def test_test_job_runs_e2e_suite(self, workflow_yaml: Dict[str, Any]):
        """Assert E2E test runner is executed."""
        job = workflow_yaml["jobs"]["test"]
        steps = job.get("steps", [])
        e2e_steps = [s for s in steps if "run" in s and "tests/e2e/runner.py" in s["run"]]
        assert e2e_steps, "E2E runner execution step ('python tests/e2e/runner.py') missing in test job"


class TestCIUpdateAndDeployJob:
    """Verifies update-and-deploy job gated on test job, running live pipeline and preserving file patterns."""

    def test_update_and_deploy_job_exists(self, workflow_yaml: Dict[str, Any]):
        """Assert 'update-and-deploy' job is present."""
        jobs = workflow_yaml.get("jobs", {})
        assert "update-and-deploy" in jobs, "'update-and-deploy' job missing"

    def test_update_and_deploy_gated_on_test(self, workflow_yaml: Dict[str, Any]):
        """Assert 'update-and-deploy' requires 'test' job via needs."""
        job = workflow_yaml["jobs"]["update-and-deploy"]
        needs = job.get("needs")
        if isinstance(needs, list):
            assert "test" in needs, f"'test' not in needs list: {needs}"
        else:
            assert needs == "test", f"Expected needs == 'test', got: {needs}"

    def test_update_and_deploy_runs_pipeline(self, workflow_yaml: Dict[str, Any]):
        """Assert update-and-deploy job runs 'python -m src.main'."""
        job = workflow_yaml["jobs"]["update-and-deploy"]
        steps = job.get("steps", [])
        pipeline_steps = [s for s in steps if "run" in s and "python -m src.main" in s["run"]]
        assert pipeline_steps, "Step executing 'python -m src.main' missing"

    def test_update_and_deploy_file_pattern_preservation(self, workflow_yaml: Dict[str, Any]):
        """Assert git-auto-commit preserves README.md, data files, screenshots, and docs."""
        job = workflow_yaml["jobs"]["update-and-deploy"]
        steps = job.get("steps", [])
        commit_steps = [s for s in steps if "stefanzweifel/git-auto-commit-action" in s.get("uses", "")]
        assert commit_steps, "git-auto-commit-action step missing"
        with_args = commit_steps[0].get("with", {})
        pattern = with_args.get("file_pattern", "")
        required_patterns = [
            "README.md",
            "data/*.json",
            "data/*.jsonl",
            "docs/index.html",
            "docs/*.md",
            "docs/screenshots/*.png",
        ]
        for rp in required_patterns:
            assert rp in pattern, f"Required file pattern '{rp}' missing from file_pattern: '{pattern}'"

    def test_deploy_pages_job(self, workflow_yaml: Dict[str, Any]):
        """Assert deploy-pages job is configured with needs: update-and-deploy."""
        jobs = workflow_yaml.get("jobs", {})
        assert "deploy-pages" in jobs, "'deploy-pages' job missing"
        deploy_job = jobs["deploy-pages"]
        needs = deploy_job.get("needs")
        if isinstance(needs, list):
            assert "update-and-deploy" in needs
        else:
            assert needs == "update-and-deploy"
