"""Exercise the consumer's pinned remote hook and the main-only version workflow."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Final

import pytest
from ruamel.yaml import YAML

ROOT: Final = Path(__file__).resolve().parents[1]
BOUNDED: Final = ("uv", "run", "--script", str(ROOT / "scripts/run_bounded.py"), "--timeout-seconds", "120", "--")
WORKFLOW: Final = ROOT / ".github/workflows/bump-marketplace.yml"
SUBJECT: Final = "chore(plugins): assign plugin versions"
PUSH_URL: Final = "https://x-access-token:fixture@github.com/owner/repo.git"


def load_yaml(path: Path) -> Any:
    """Parse one repository YAML file.

    Returns:
        The parsed document.
    """
    return YAML(typ="safe").load(path.read_text(encoding="utf-8"))


def shared_hook_repo() -> dict[str, Any]:
    """Return the versioner entry from this repository's hook configuration.

    Returns:
        The `repos` entry that installs agent-marketplace-versioner.
    """
    config = load_yaml(ROOT / ".pre-commit-config.yaml")
    return next(repo for repo in config["repos"] if "agent-marketplace-versioner" in repo["repo"])


def test_hook_checks_only_and_workflow_bumps_on_main() -> None:
    """Branches validate manifests without bumping; only main pushes assign versions."""
    shared = shared_hook_repo()
    (hook,) = shared["hooks"]
    assert hook["entry"] == "agent-marketplace-versioner reconcile --dry-run"

    workflow = load_yaml(WORKFLOW)
    assert set(workflow["on"]) == {"push", "workflow_dispatch"}
    assert workflow["on"]["push"] == {"branches": ["main"]}
    assert workflow["concurrency"]["cancel-in-progress"] is False
    job = workflow["jobs"]["bump"]
    assert "github.ref == 'refs/heads/main'" in job["if"]
    assert repr(SUBJECT) in job["if"]
    scripts = "\n".join(step.get("run", "") for step in job["steps"])
    assert repr(SUBJECT) in scripts
    actions = [step["uses"] for step in job["steps"] if "agent-marketplace-versioner@" in step.get("uses", "")]
    assert set(actions) == {f"Jamie-BitFlight/agent-marketplace-versioner@{shared['rev']}"}
    for other in ROOT.glob(".github/workflows/*.yml"):
        if other != WORKFLOW:
            assert "agent-marketplace-versioner@" not in other.read_text(), other


def run(
    directory: Path, *args: str, env: dict[str, str] | None = None, ok: bool = True
) -> subprocess.CompletedProcess[str]:
    """Run a bounded fixture command with its diagnostics retained.

    Returns:
        The completed process.
    """
    result = subprocess.run([*BOUNDED, *args], cwd=directory, env=env, check=False, capture_output=True, text=True)
    if ok:
        assert result.returncode == 0, result.stdout + result.stderr
    return result


@pytest.mark.integration
def test_branch_commits_keep_versions_and_main_workflow_bumps_once(tmp_path: Path) -> None:
    """Given merged plugin changes, the workflow bumps each changed plugin once and is idempotent."""
    # Given a consumer using this repository's exact hook configuration, published to a remote.
    yaml = YAML(typ="safe")
    shared = shared_hook_repo()
    remote = tmp_path / "remote.git"
    run(tmp_path, "git", "init", "--bare", "--initial-branch=main", str(remote))
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    run(consumer, "git", "init", "--initial-branch=main")
    run(consumer, "git", "config", "user.name", "Versioner Test")
    run(consumer, "git", "config", "user.email", "versioner@example.invalid")
    names = ("tool", "other", "idle")
    for name in names:
        manifest = consumer / f"plugins/{name}/.claude-plugin/plugin.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({"name": name, "version": "1.0.0"}))
        (consumer / f"plugins/{name}/README.md").write_text(f"{name}\n")
    # An eval fixture nested inside a plugin is also a manifest the versioner bumps.
    fixture = consumer / "plugins/tool/evals/fixture/.claude-plugin/plugin.json"
    fixture.parent.mkdir(parents=True)
    fixture.write_text(json.dumps({"name": "fixture", "version": "1.0.0"}))
    catalog = consumer / ".claude-plugin/marketplace.json"
    catalog.parent.mkdir()
    catalog.write_text(
        json.dumps({
            "name": "fixture",
            "metadata": {"version": "1.0.0"},
            "plugins": [{"name": name, "source": f"./plugins/{name}"} for name in names],
        })
    )
    with (consumer / ".pre-commit-config.yaml").open("w") as stream:
        yaml.dump({"repos": [shared]}, stream)
    run(consumer, "git", "add", ".")
    run(consumer, "git", "commit", "-m", "Initial fixture")
    run(consumer, "git", "push", "-q", str(remote), "main")

    # When a branch commit changes plugin content, the hook passes without touching versions.
    (consumer / "plugins/tool/README.md").write_text("tool changed\n")
    run(consumer, "git", "add", "plugins/tool/README.md")
    run(consumer, str(ROOT / ".venv/bin/prek"), "run", "agent-marketplace-versioner")
    assert run(consumer, "git", "diff", "--cached", "--name-only").stdout.split() == ["plugins/tool/README.md"]
    run(consumer, "git", "commit", "-m", "First merged change")

    # And an unregistered plugin fails the hook instead of being bumped or registered.
    stray = consumer / "plugins/stray/.claude-plugin/plugin.json"
    stray.parent.mkdir(parents=True)
    stray.write_text(json.dumps({"name": "stray", "version": "1.0.0"}))
    run(consumer, "git", "add", str(stray))
    rejected = run(consumer, str(ROOT / ".venv/bin/prek"), "run", "agent-marketplace-versioner", ok=False)
    assert rejected.returncode == 1, rejected.stdout + rejected.stderr
    assert "Drift detected" in rejected.stdout
    assert [entry["name"] for entry in json.loads(catalog.read_text())["plugins"]] == list(names)
    run(consumer, "git", "rm", "-q", "--cached", str(stray))
    stray.unlink()

    # Two more merges land before the workflow runs; one touches "tool" again.
    (consumer / "plugins/other/README.md").write_text("other changed\n")
    run(consumer, "git", "commit", "-qam", "Second merged change")
    (consumer / "plugins/tool/README.md").write_text("tool changed twice\n")
    (fixture.parent.parent / "input.md").write_text("fixture input\n")
    run(consumer, "git", "add", ".")
    run(consumer, "git", "commit", "-qm", "Third merged change")
    run(consumer, "git", "push", "-q", str(remote), "main")

    action = tmp_path / "action"
    run(tmp_path, "git", "clone", "--quiet", shared["repo"], str(action))
    run(action, "git", "checkout", "--quiet", shared["rev"])
    action_steps = yaml.load((action / "action.yml").read_text())["runs"]["steps"]
    action_script = next(step["run"] for step in action_steps if "run" in step)
    runs = iter(range(100))

    def run_workflow(race: str | None = None) -> Path:
        """Execute the workflow's versioner and git steps against a fresh clone of main.

        Returns:
            The checkout the workflow ran in.
        """
        checkout = tmp_path / f"checkout-{next(runs)}"
        run(tmp_path, "git", "clone", "--quiet", str(remote), str(checkout))
        run(checkout, "git", "config", f"url.{remote}.insteadOf", PUSH_URL)
        outputs_file = tmp_path / f"{checkout.name}.outputs"
        outputs_file.touch()
        env = {
            **os.environ,
            "GITHUB_REPOSITORY": "owner/repo",
            "RUNNER_TEMP": str(tmp_path),
            "SETUPTOOLS_SCM_PRETEND_VERSION": "0+action",
            "VERSIONER_SOURCE": str(action),
            "VERSIONER_REPOSITORY": str(checkout),
            "GITHUB_OUTPUT": str(outputs_file),
            "TOKEN": "fixture",
        }
        outputs: dict[str, str] = {}

        def resolve(value: str) -> str:
            return re.sub(r"\$\{\{ steps\.start\.outputs\.(\w+) \}\}", lambda match: outputs[match[1]], value)

        for step in load_yaml(WORKFLOW)["jobs"]["bump"]["steps"]:
            name = step.get("name", "")
            if "agent-marketplace-versioner@" in step.get("uses", ""):
                inputs = step["with"]
                script = action_script
                env |= {
                    "VERSIONER_COMMAND": inputs["command"],
                    "VERSIONER_MARKETPLACE": inputs.get("marketplace", "false"),
                    "VERSIONER_BASE": resolve(inputs.get("base-ref", "")),
                    "VERSIONER_HEAD": inputs.get("head-ref", "HEAD"),
                }
            elif name in {"Record starting revision", "Commit plugin versions", "Push version commit to main"}:
                script = step["run"]
                env |= {key: resolve(value) for key, value in step.get("env", {}).items() if key != "TOKEN"}
                if race and name.startswith("Push"):
                    # Another merge lands between checkout and push.
                    (consumer / race).write_text("raced\n")
                    run(consumer, "git", "commit", "-qam", "Racing merge")
                    run(consumer, "git", "push", "-q", str(remote), "main")
            else:
                continue
            run(checkout, "bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", script, env=env)
            outputs = dict(line.split("=", 1) for line in outputs_file.read_text().splitlines())
        return checkout

    def on_main(path: str, *keys: str) -> Any:
        data = json.loads(run(tmp_path, "git", "--git-dir", str(remote), "show", f"main:{path}").stdout)
        for key in keys:
            data = data[key]
        return data

    def main_head() -> str:
        return run(tmp_path, "git", "--git-dir", str(remote), "rev-parse", "main").stdout.strip()

    def plugin_versions() -> list[str]:
        return [on_main(f"plugins/{name}/.claude-plugin/plugin.json", "version") for name in names]

    # Then one run bumps each changed plugin once, replaying its commit over a racing merge.
    run_workflow(race="plugins/idle/README.md")
    assert run(tmp_path, "git", "--git-dir", str(remote), "log", "-1", "--format=%s", "main").stdout.strip() == SUBJECT
    assert plugin_versions() == ["1.0.1", "1.0.1", "1.0.0"]
    assert on_main("plugins/tool/evals/fixture/.claude-plugin/plugin.json", "version") == "1.0.1"
    assert on_main(".claude-plugin/marketplace.json", "metadata", "version") == "1.0.1"

    # The run queued behind it bumps only the plugin the racing merge changed.
    run_workflow()
    assert plugin_versions() == ["1.0.1", "1.0.1", "1.0.1"]
    assert on_main(".claude-plugin/marketplace.json", "metadata", "version") == "1.0.2"

    # A rerun on the version commit (the loop the job's `if` also skips) changes nothing.
    head = main_head()
    rerun = run_workflow()
    assert main_head() == head
    assert not run(rerun, "git", "status", "--porcelain").stdout

    # A merge that adds a plugin (registered by hand, already at its first version) bumps the catalog.
    run(consumer, "git", "pull", "-q", "--rebase", str(remote), "main")
    added = consumer / "plugins/fresh/.claude-plugin/plugin.json"
    added.parent.mkdir(parents=True)
    added.write_text(json.dumps({"name": "fresh", "version": "1.0.0"}))
    data = json.loads(catalog.read_text())
    data["plugins"].append({"name": "fresh", "source": "./plugins/fresh"})
    catalog.write_text(json.dumps(data))
    run(consumer, "git", "add", ".")
    run(consumer, "git", "commit", "-qm", "Add a plugin")
    run(consumer, "git", "push", "-q", str(remote), "main")
    run_workflow()
    assert on_main("plugins/fresh/.claude-plugin/plugin.json", "version") == "1.0.0"
    assert on_main(".claude-plugin/marketplace.json", "metadata", "version") == "1.0.3"
