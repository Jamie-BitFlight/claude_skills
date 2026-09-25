"""CI wiring contracts that keep selective execution visible to the merge gate."""

from __future__ import annotations

from pathlib import Path

import pytest
from ruamel.yaml import YAML

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def workflow() -> dict:
    """Read the actual workflow, including its matrix and condition expressions."""
    return YAML(typ="safe").load((ROOT / ".github/workflows/code-quality.yml").read_text(encoding="utf-8"))


def test_workflow_does_not_hide_required_checks_with_path_filters(workflow: dict) -> None:
    """Every requested event can report the stable gate, even for documentation."""
    assert set(workflow["on"]) == {"push", "pull_request", "workflow_dispatch"}
    assert workflow["on"]["pull_request"] is None
    assert workflow["on"]["push"] == {"branches": ["main"]}
    assert workflow["jobs"]["quality-gate"]["name"] == "Quality Gate"


def test_gate_requires_planner_and_all_blocking_lanes(workflow: dict) -> None:
    """A new blocking lane cannot be silently omitted from the aggregate verdict."""
    jobs = workflow["jobs"]
    gate = jobs["quality-gate"]
    advisory = {"research-validation", "test-e2e"}
    assert set(gate["needs"]) == set(jobs) - advisory - {"quality-gate"}
    assert gate["if"] == "always()"
    vote = gate["steps"][0]
    assert vote["uses"] == "re-actors/alls-green@release/v1"
    assert vote["with"]["jobs"] == "${{ toJSON(needs) }}"
    assert vote["with"]["allowed-skips"] == (
        "${{ needs.changes.outputs.plan && fromJSON(needs.changes.outputs.plan).allowed_skips || '' }}"
    )
    assert "allowed-failures" not in vote["with"]
    for name in gate["needs"]:
        assert not jobs[name].get("continue-on-error", False)


def test_selected_lanes_use_the_same_plan_and_exact_job_key(workflow: dict) -> None:
    """Planning and job scheduling cannot disagree about which skips are expected."""
    for name, job in workflow["jobs"].items():
        if name in {"changes", "audit-dependencies", "quality-gate", "test-e2e"}:
            continue
        assert job["needs"] == "changes"
        assert job["if"] == f"${{{{ fromJSON(needs.changes.outputs.plan).checks['{name}'] }}}}"


@pytest.mark.parametrize(("name", "lane"), [("test-python", "unit_matrix"), ("test-integration", "integration_matrix")])
def test_matrix_executes_paths_via_json_not_shell(workflow: dict, name: str, lane: str) -> None:
    """Matrix targets remain data, and a failing shard does not cancel its peers."""
    job = workflow["jobs"][name]
    assert job["strategy"] == {"fail-fast": False, "matrix": f"${{{{ fromJSON(needs.changes.outputs.plan).{lane} }}}}"}
    assert job["env"]["CI_SHARD"] == "${{ toJSON(matrix) }}"
    assert job["env"]["CI_PLAN"] == "${{ needs.changes.outputs.plan }}"
    assert [step["run"] for step in job["steps"] if "run" in step] == [
        "uv run --script .github/ci/run.py pytest"
    ]


def test_scoped_linters_have_history_after_composite_checkout(workflow: dict) -> None:
    """The setup action's inner checkout must not shallow the required diff history."""
    for name in ("lint-python", "lint-js", "lint-markdown", "lint-shell", "file-hygiene", "manifest-sync"):
        setup = next(
            step for step in workflow["jobs"][name]["steps"] if step.get("uses") == "./.github/actions/setup-python"
        )
        assert setup["with"]["fetch-depth"] == 0
    action = YAML(typ="safe").load((ROOT / ".github/actions/setup-python/action.yml").read_text(encoding="utf-8"))
    assert action["inputs"]["fetch-depth"]["default"] == "1"
    assert action["runs"]["steps"][0]["with"]["fetch-depth"] == "${{ inputs.fetch-depth }}"


def test_dependencies_are_a_global_audit_even_without_python_changes(workflow: dict) -> None:
    """Removing the last dependency use from prose must still exercise the audit."""
    job = workflow["jobs"]["audit-dependencies"]
    assert "if" not in job
    assert any("audit-dependencies --all-files" in step.get("run", "") for step in job["steps"])
    assert all("audit-dependencies" not in step.get("run", "") for step in workflow["jobs"]["lint-python"]["steps"])


def test_file_hygiene_retains_structural_workflow_validation(workflow: dict) -> None:
    """YAML parsing alone cannot establish that an Actions workflow is valid."""
    step = next(step for step in workflow["jobs"]["file-hygiene"]["steps"] if "run" in step)
    assert "actionlint" not in step["env"]["SKIP"].split(",")
    assert step["run"] == "uv run --script .github/ci/run.py prek"


def test_live_e2e_retains_sandbox_and_cleanup_boundaries(workflow: dict) -> None:
    """Path scoping does not broaden live access or cancel sandbox cleanup."""
    job = workflow["jobs"]["test-e2e"]
    assert job["if"] == "github.ref == 'refs/heads/main' || github.event_name == 'workflow_dispatch'"
    assert job["concurrency"]["cancel-in-progress"] is False
    assert job["env"]["GITHUB_REPO"] == "${{ vars.DH_E2E_REPOSITORY }}"
    steps = job["steps"]
    cleanup = next(step for step in steps if step.get("name", "").startswith("Emergency cleanup"))
    assert cleanup["if"] == "always() && steps.sandbox.outcome == 'success'"
    assert cleanup["env"]["GITHUB_TOKEN"] == "${{ secrets.DH_E2E_TOKEN }}"
    assert "scripts/run_bounded.py --timeout-seconds 90" in cleanup["run"]
    assert any(step.get("uses") == "actions/upload-artifact@v7" and step.get("if") == "always()" for step in steps)
