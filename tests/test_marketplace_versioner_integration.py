"""Exercise the consumer's pinned remote hook and composite action commands."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Final

import pytest
from ruamel.yaml import YAML

ROOT: Final = Path(__file__).resolve().parents[1]
BOUNDED: Final = ("uv", "run", "--script", str(ROOT / "scripts/run_bounded.py"), "--timeout-seconds", "120", "--")


def test_workflows_use_hook_revision_and_protected_repair_delivery() -> None:
    """Keep the actual shared action revision aligned with the installed hook."""
    yaml = YAML(typ="safe")
    config = yaml.load((ROOT / ".pre-commit-config.yaml").read_text())
    shared = next(repo for repo in config["repos"] if "agent-marketplace-versioner" in repo["repo"])
    expected = f"Jamie-BitFlight/agent-marketplace-versioner@{shared['rev']}"
    workflows = [
        yaml.load((ROOT / ".github/workflows" / name).read_text())
        for name in ("code-quality.yml", "bump-marketplace.yml")
    ]
    for workflow in workflows:
        actions = [
            step["uses"]
            for job in workflow["jobs"].values()
            for step in job["steps"]
            if "agent-marketplace-versioner@" in step.get("uses", "")
        ]
        assert actions
        assert set(actions) == {expected}
    repair_steps = workflows[1]["jobs"]["bump"]["steps"]
    delivery = next(step for step in repair_steps if "create-pull-request@" in step.get("uses", ""))
    assert delivery["with"]["branch"] != delivery["with"]["base"]
    assert delivery["with"]["token"] == "${{ secrets.VERSIONER_PR_TOKEN }}"
    assert delivery["with"]["title"] == delivery["with"]["commit-message"]
    assert repr(delivery["with"]["title"]) in workflows[1]["jobs"]["bump"]["if"]


def run(directory: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run a bounded fixture command with its diagnostics retained."""
    result = subprocess.run([*BOUNDED, *args], cwd=directory, check=False, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    return result


@pytest.mark.integration
def test_pinned_remote_hook_and_action_preserve_versions(tmp_path: Path) -> None:
    """Given staged content, the distributed hook bumps and action checks its commit."""
    # Given a native consumer and the exact remote hook configuration used here.
    yaml = YAML(typ="safe")
    config = yaml.load((ROOT / ".pre-commit-config.yaml").read_text())
    shared = next(repo for repo in config["repos"] if "agent-marketplace-versioner" in repo["repo"])
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    run(consumer, "git", "init", "--initial-branch=main")
    run(consumer, "git", "config", "user.name", "Versioner Test")
    run(consumer, "git", "config", "user.email", "versioner@example.invalid")
    plugin = consumer / "plugins/tool/.claude-plugin/plugin.json"
    plugin.parent.mkdir(parents=True)
    plugin.write_text(json.dumps({"name": "tool", "version": "1.0.0"}))
    skill = consumer / "plugins/tool/skills/example/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: example\ndescription: Example skill\n---\nInitial content\n")
    catalog = consumer / ".claude-plugin/marketplace.json"
    catalog.parent.mkdir()
    catalog.write_text(
        json.dumps({
            "name": "fixture",
            "metadata": {"version": "1.0.0"},
            "plugins": [{"name": "tool", "source": "./plugins/tool"}],
        })
    )
    with (consumer / ".pre-commit-config.yaml").open("w") as stream:
        yaml.dump({"repos": [shared]}, stream)
    run(consumer, "git", "add", ".")
    run(consumer, "git", "commit", "-m", "Initial fixture")
    base = run(consumer, "git", "rev-parse", "HEAD").stdout.strip()
    run(consumer, "git", "update-ref", "refs/remotes/origin/main", base)
    skill.write_text(skill.read_text() + "Changed content\n")
    run(consumer, "git", "add", str(skill))

    # When prek installs and executes the actual pinned Python hook.
    run(consumer, str(ROOT / ".venv/bin/prek"), "run", "agent-marketplace-versioner")

    # Then plugin versions advance, marketplace sync stays deferred, and reruns are idempotent.
    assert json.loads(plugin.read_text())["version"] == "1.0.1"
    assert json.loads(catalog.read_text())["metadata"]["version"] == "1.0.0"
    staged = run(consumer, "git", "diff", "--cached").stdout
    run(consumer, str(ROOT / ".venv/bin/prek"), "run", "agent-marketplace-versioner")
    assert run(consumer, "git", "diff", "--cached").stdout == staged
    run(consumer, "git", "commit", "-m", "Changed fixture")

    # Execute the composite action's published shell, without substituting local source.
    action = tmp_path / "action"
    run(tmp_path, "git", "clone", "--quiet", shared["repo"], str(action))
    run(action, "git", "checkout", "--quiet", shared["rev"])
    definition = yaml.load((action / "action.yml").read_text())
    command = next(step["run"] for step in definition["runs"]["steps"] if "run" in step)
    env = {
        **os.environ,
        "VERSIONER_SOURCE": str(action),
        "VERSIONER_REPOSITORY": str(consumer),
        "VERSIONER_COMMAND": "check",
        "VERSIONER_MARKETPLACE": "false",
        "VERSIONER_BASE": base,
        "VERSIONER_HEAD": "HEAD",
        "RUNNER_TEMP": str(tmp_path),
        "SETUPTOOLS_SCM_PRETEND_VERSION": "0+action",
    }
    result = subprocess.run(
        [*BOUNDED, "bash", "-e", "-o", "pipefail", "-c", command], env=env, check=False, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stdout + result.stderr

    # A committed change that missed the hook must fail check and be repaired by the action.
    skill.write_text(skill.read_text() + "Unversioned merged change\n")
    run(consumer, "git", "add", str(skill))
    run(consumer, "git", "commit", "-m", "Missed hook")
    env["VERSIONER_BASE"] = "HEAD~1"
    rejected = subprocess.run(
        [*BOUNDED, "bash", "-e", "-o", "pipefail", "-c", command], env=env, check=False, capture_output=True, text=True
    )
    assert rejected.returncode == 1, rejected.stdout + rejected.stderr
    env["VERSIONER_COMMAND"] = "repair"
    repaired = subprocess.run(
        [*BOUNDED, "bash", "-e", "-o", "pipefail", "-c", command], env=env, check=False, capture_output=True, text=True
    )
    assert repaired.returncode == 0, repaired.stdout + repaired.stderr
    assert json.loads(plugin.read_text())["version"] == "1.0.2"
    env["VERSIONER_COMMAND"] = "sync"
    env["VERSIONER_MARKETPLACE"] = "true"
    synchronized = subprocess.run(
        [*BOUNDED, "bash", "-e", "-o", "pipefail", "-c", command], env=env, check=False, capture_output=True, text=True
    )
    assert synchronized.returncode == 0, synchronized.stdout + synchronized.stderr
    assert json.loads(catalog.read_text())["metadata"]["version"] == "1.0.1"

    # Plugin CRUD updates local catalog membership without taking the post-merge version bump.
    run(consumer, "git", "add", ".")
    run(consumer, "git", "commit", "-m", "Apply repair")
    added = consumer / "plugins/added/.claude-plugin/plugin.json"
    added.parent.mkdir(parents=True)
    added.write_text(json.dumps({"name": "added", "version": "1.0.0"}))
    run(consumer, "git", "add", str(added))
    run(consumer, str(ROOT / ".venv/bin/prek"), "run", "agent-marketplace-versioner")
    assert {entry["name"] for entry in json.loads(catalog.read_text())["plugins"]} == {"tool", "added"}
    assert json.loads(catalog.read_text())["metadata"]["version"] == "1.0.1"
    run(consumer, "git", "commit", "-m", "Add plugin")
    run(consumer, "git", "rm", str(added))
    run(consumer, str(ROOT / ".venv/bin/prek"), "run", "agent-marketplace-versioner")
    assert [entry["name"] for entry in json.loads(catalog.read_text())["plugins"]] == ["tool"]
