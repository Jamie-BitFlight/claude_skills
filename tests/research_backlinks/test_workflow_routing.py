from __future__ import annotations

from pathlib import Path

from ruamel.yaml import YAML


def test_entry_validation_runs_after_advisory_backlink_failure() -> None:
    workflow_path = Path(__file__).resolve().parents[2] / ".github/workflows/code-quality.yml"
    workflow = YAML(typ="safe").load(workflow_path.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["research-validation"]["steps"]
    backlink_index = next(index for index, step in enumerate(steps) if step.get("name") == "Scan research backlinks")
    entry_index = next(index for index, step in enumerate(steps) if step.get("name") == "Validate research entries")

    assert entry_index == backlink_index + 1
    assert steps[entry_index]["if"] == "${{ always() }}"
