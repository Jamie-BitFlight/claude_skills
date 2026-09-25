"""Behavioral contracts for change-aware CI selection and command execution."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path) -> ModuleType:
    """Load a CI entry point without adding its generic names to sys.path."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


planner = load_module("ci_plan_under_test", ROOT / ".github/ci/plan.py")
runner = load_module("ci_run_under_test", ROOT / ".github/ci/run.py")


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    """Create distinct plugin, nested, colocated, and global test boundaries."""
    paths = [
        "plugins/alpha/tests",
        "plugins/alpha/model/tests",
        "plugins/alpha/scripts",
        "plugins/beta/tests",
        "plugins/development-harness/tests",
        "tests",
        ".agents/tool/scripts",
    ]
    for path in [*paths, "plugins/content-only", ".claude", "tests/research_backlinks"]:
        (tmp_path / path).mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests/test_rebase_publication_identity.py").write_text("", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        "[tool.pytest.ini_options]\n"
        f"testpaths = {json.dumps(paths)}\n"
        'pythonpath = [".", "plugins/alpha/scripts", "plugins/development-harness"]\n',
        encoding="utf-8",
    )
    return tmp_path


def names(plan: dict, lane: str = "unit_matrix") -> set[str]:
    """Read observable shard identities from a plan."""
    return {shard["name"] for shard in plan[lane]["include"]}


def test_plugin_change_keeps_all_nested_and_colocated_paths(repository: Path) -> None:
    """One plugin's content selects its complete configured suite and global guards."""
    plan = planner.build_plan(repository, ["plugins/alpha/skills/example/SKILL.md"])
    assert names(plan) == {"alpha", "global"}
    alpha = next(shard for shard in plan["unit_matrix"]["include"] if shard["name"] == "alpha")
    assert alpha["paths"] == ["plugins/alpha/tests", "plugins/alpha/model/tests", "plugins/alpha/scripts"]
    assert plan["checks"]["lint-markdown"]
    assert not plan["checks"]["lint-python"]
    assert not plan["checks"]["test-cross-backend"]
    assert not plan["checks"]["test-integration"]
    assert plan["validation_paths"] == ["plugins/alpha"]


def test_full_partition_equals_authoritative_testpaths_once(repository: Path) -> None:
    """No configured directory disappears or runs in two shards after partitioning."""
    plan = planner.build_plan(repository, None)
    actual = [path for shard in plan["unit_matrix"]["include"] for path in shard["paths"]]
    expected = [
        "plugins/alpha/tests",
        "plugins/alpha/model/tests",
        "plugins/alpha/scripts",
        "plugins/beta/tests",
        "plugins/development-harness/tests",
        "tests",
        ".agents/tool/scripts",
    ]
    assert sorted(actual) == sorted(expected)
    assert len(actual) == len(set(actual))
    assert plan["allowed_skips"] == ""
    assert names(plan, "integration_matrix") == {"development-harness", "research-backlinks", "rebase-publication"}


@pytest.mark.parametrize("path", ["plugins/alpha/scripts/test_cli.py", "plugins/alpha/model/tests/test_model.py"])
def test_test_only_python_change_is_plugin_local(repository: Path, path: str) -> None:
    """A test edit does not become a shared provider merely because it is Python."""
    plan = planner.build_plan(repository, [path])
    assert names(plan) == {"alpha", "global"}
    assert plan["checks"]["typecheck-ty"]


@pytest.mark.parametrize("path", ["plugins/alpha/scripts/api.py", "plugins/alpha/tests/conftest.py"])
def test_shared_imports_and_fixtures_expand_tests_not_file_lint(repository: Path, path: str) -> None:
    """Shared Python consumers are not silently skipped, but file-local lint stays local."""
    plan = planner.build_plan(repository, [path])
    assert names(plan) == {"alpha", "beta", "development-harness", "global"}
    assert plan["full_tests"]
    assert not plan["lint_all"]


@pytest.mark.parametrize(
    "path",
    [
        "pyproject.toml",
        "uv.lock",
        "scripts/shared.py",
        "tests/test_guard.py",
        ".github/workflows/code-quality.yml",
        ".agents/tool/scripts/helper.py",
        "new-unclassified-directory/input.data",
        "plugins/alpha/.ruff.toml",
        ".pre-commit-config.yaml",
    ],
)
def test_shared_or_unknown_inputs_fail_safe_to_full_checks(repository: Path, path: str) -> None:
    """An unclassified dependency cannot produce a falsely narrow success."""
    plan = planner.build_plan(repository, [path])
    assert plan["full_tests"]
    assert plan["lint_all"]


def test_file_hygiene_retains_full_inventory_for_cross_file_invariants() -> None:
    """A deleted target can break an unchanged symlink outside the diff."""
    argv = runner.command("prek", {"lint_all": False, "base": "a" * 40, "head": "b" * 40}, {})
    assert "--all-files" in argv
    assert "--from-ref" not in argv


@pytest.mark.parametrize("path", ["README.md", "docs/design.md", "rules/policy.md"])
def test_documentation_keeps_global_guards_without_plugin_suites(repository: Path, path: str) -> None:
    """Repository documentation still exercises global contract tests."""
    plan = planner.build_plan(repository, [path])
    assert names(plan) == {"global"}
    assert not plan["checks"]["validate-plugins"]
    assert not plan["checks"]["manifest-sync"]
    assert plan["checks"]["audit-dependencies"]
    assert plan["checks"]["file-hygiene"]


def test_research_selects_its_integration_lane_and_advisory_scan(repository: Path) -> None:
    """Production-vault scanning is not enabled for unrelated plugin edits."""
    plan = planner.build_plan(repository, ["research/tools/example.md"])
    assert names(plan) == {"global"}
    assert names(plan, "integration_matrix") == {"research-backlinks"}
    assert plan["checks"]["research-validation"]
    assert not plan["checks"]["test-cross-backend"]


def test_dh_content_selects_backend_and_dh_integration(repository: Path) -> None:
    """Development-harness changes retain its expensive dedicated lanes."""
    plan = planner.build_plan(repository, ["plugins/development-harness/skills/example/SKILL.md"])
    assert names(plan) == {"development-harness", "global"}
    assert names(plan, "integration_matrix") == {"development-harness"}
    assert plan["checks"]["test-cross-backend"]


def test_plugin_without_pytest_suite_has_validation_but_no_empty_pytest(repository: Path) -> None:
    """Content-only plugins do not accidentally invoke unqualified pytest."""
    plan = planner.build_plan(repository, ["plugins/content-only/SKILL.md"])
    assert names(plan) == {"global"}
    assert plan["validation_paths"] == ["plugins/content-only"]


def test_deleted_plugin_is_not_sent_to_validator(repository: Path) -> None:
    """Deletion keeps manifest/global checks without validating a missing directory."""
    plan = planner.build_plan(repository, ["plugins/deleted-plugin/SKILL.md"])
    assert plan["validation_paths"] == []
    assert plan["checks"]["manifest-sync"]
    assert names(plan) == {"global"}


def test_missing_configured_suite_is_an_error(repository: Path) -> None:
    """Removing a suite directory without updating testpaths cannot pass silently."""
    (repository / "plugins/beta/tests").rmdir()
    with pytest.raises(ValueError, match="Configured testpath does not exist"):
        planner.build_plan(repository, ["README.md"])


def test_extensionless_files_do_not_bypass_language_checks(repository: Path) -> None:
    """Prek may recognize Python or shell from a shebang instead of an extension."""
    plan = planner.build_plan(repository, ["plugins/content-only/bin/execute"])
    assert all(plan["checks"][job] for job in planner.LANGUAGE_SUFFIXES)


def test_skip_allowlist_contains_exactly_unselected_blocking_jobs(repository: Path) -> None:
    """Failed/cancelled selected work is never on a blanket skip allowlist."""
    plan = planner.build_plan(repository, ["README.md"])
    expected = {job for job, enabled in plan["checks"].items() if not enabled and job != "research-validation"}
    assert set(plan["allowed_skips"].split(",")) == expected
    assert "test-python" not in expected
    assert "audit-dependencies" not in expected


@pytest.mark.parametrize("event", ["push", "workflow_dispatch", "schedule", "merge_group"])
def test_non_pr_events_use_full_validation(repository: Path, event: str) -> None:
    """Full validation does not depend on a possibly incomplete last-commit diff."""
    paths, base, head, reason = planner.changed_paths(repository, event, "", "")
    assert paths is None
    assert base == head == ""
    assert "full regression run" in reason


def test_missing_or_unavailable_diff_is_full_not_empty(repository: Path) -> None:
    """Missing history cannot turn an unknown change set into no work."""
    assert planner.changed_paths(repository, "pull_request", "", "")[0] is None
    assert planner.changed_paths(repository, "pull_request", "a" * 40, "b" * 40)[0] is None


def git(repo: Path, *args: str) -> str:
    """Exercise actual Git semantics in a disposable, credential-free repository."""
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True, timeout=30
    ).stdout.strip()


def test_real_git_diff_handles_renames_deletions_and_base_only_changes(repository: Path) -> None:
    """Both rename owners vote; the PR diff excludes changes made only on its base."""
    git(repository, "init", "-b", "main")
    git(repository, "config", "user.name", "CI fixture")
    git(repository, "config", "user.email", "fixture@example.invalid")
    old = repository / "plugins/alpha/old name\nwith newline.md"
    old.write_text("moved content\n", encoding="utf-8")
    git(repository, "add", ".")
    git(repository, "commit", "-m", "fixture baseline")
    common = git(repository, "rev-parse", "HEAD")
    git(repository, "switch", "-c", "topic")
    new = repository / "plugins/beta/new name\nwith newline.md"
    old.rename(new)
    git(repository, "add", "-A")
    git(repository, "commit", "-m", "move between owners")
    head = git(repository, "rev-parse", "HEAD")
    git(repository, "switch", "main")
    (repository / "base-only.txt").write_text("not a PR change\n", encoding="utf-8")
    git(repository, "add", ".")
    git(repository, "commit", "-m", "advance base independently")
    base = git(repository, "rev-parse", "HEAD")
    paths, merge_base, selected_head, _reason = planner.changed_paths(repository, "pull_request", base, head)
    assert merge_base == common
    assert selected_head == head
    assert set(paths) == {str(old.relative_to(repository)), str(new.relative_to(repository))}
    assert names(planner.build_plan(repository, paths)) == {"alpha", "beta", "global"}


def test_large_diff_has_no_path_filter_truncation(repository: Path) -> None:
    """A relevant file beyond an API-style first page still selects its owner."""
    changes = [f"plugins/alpha/docs/{index}.md" for index in range(400)] + ["plugins/beta/SKILL.md"]
    assert names(planner.build_plan(repository, changes)) == {"alpha", "beta", "global"}


@pytest.mark.parametrize("paths", [[], None, ["../escape"], ["--collect-only"], ["/absolute"]])
def test_runner_rejects_empty_or_unsafe_pytest_targets(paths: object) -> None:
    """No target must fail, rather than falling back to all testpaths."""
    with pytest.raises(ValueError, match=r"non-empty|Unsafe target path"):
        runner.command("pytest", {}, {"paths": paths})


def test_runner_preserves_marker_coverage_defaults_and_argv_boundaries() -> None:
    """Coverage/xdist remain in addopts, and paths are not shell-expanded."""
    argv = runner.command(
        "pytest", {}, {"paths": ["plugins/a directory/tests"], "marker": "integration and not research_vault"}
    )
    assert argv == [
        "uv",
        "run",
        "--locked",
        "pytest",
        "-m",
        "integration and not research_vault",
        "-v",
        "plugins/a directory/tests",
    ]
    assert "--no-cov" not in argv
    assert "-o" not in argv


def test_runner_lints_diff_or_full_tree_explicitly() -> None:
    """A missing diff must not be treated as an empty passing check."""
    argv = runner.command("prek", {"lint_all": False, "base": "a" * 40, "head": "b" * 40}, {}, "ruff")
    assert argv == [
        "uv",
        "run",
        "--locked",
        "prek",
        "run",
        "ruff",
        "--from-ref",
        "a" * 40,
        "--to-ref",
        "b" * 40,
        "--show-diff-on-failure",
    ]
    assert "--all-files" in runner.command("prek", {"lint_all": True}, {}, "ruff")
    with pytest.raises(ValueError, match="immutable comparison"):
        runner.command("prek", {"lint_all": False}, {}, "ruff")


@pytest.mark.skipif(os.name == "nt", reason="Exercises the POSIX runner process boundary used by GitHub CI")
@pytest.mark.parametrize("exit_code", [1, 2, 5])
def test_runner_propagates_actual_child_failure(tmp_path: Path, exit_code: int) -> None:
    """An actual child executable controls the runner exit code, including no tests."""
    fake_uv = tmp_path / "uv"
    fake_uv.write_text(f"#!/bin/sh\nexit {exit_code}\n", encoding="utf-8")
    fake_uv.chmod(0o755)
    env = dict(
        os.environ,
        PATH=f"{tmp_path}{os.pathsep}{os.environ['PATH']}",
        CI_PLAN='{"version":1}',
        CI_SHARD='{"paths":["tests"]}',
    )
    result = subprocess.run(
        [sys.executable, str(ROOT / ".github/ci/run.py"), "pytest"],
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == exit_code


@pytest.mark.parametrize("registry_changed", [False, True])
def test_marketplace_version_bump_does_not_expand_plugin_content_change(
    repository: Path, registry_changed: bool
) -> None:
    """Normal version bumps stay local; changed registration still tests everything."""
    git(repository, "init", "-b", "main")
    git(repository, "config", "user.name", "CI fixture")
    git(repository, "config", "user.email", "fixture@example.invalid")
    manifest = repository / ".claude-plugin/marketplace.json"
    manifest.parent.mkdir()
    document = {"metadata": {"version": "1.0.0"}, "plugins": [{"name": "alpha", "source": "./plugins/alpha"}]}
    manifest.write_text(json.dumps(document), encoding="utf-8")
    git(repository, "add", ".")
    git(repository, "commit", "-m", "fixture baseline")
    base = git(repository, "rev-parse", "HEAD")
    document["metadata"]["version"] = "1.0.1"
    if registry_changed:
        document["plugins"].append({"name": "beta", "source": "./plugins/beta"})
    manifest.write_text(json.dumps(document), encoding="utf-8")
    (repository / "plugins/alpha/README.md").write_text("changed\n", encoding="utf-8")
    git(repository, "add", ".")
    git(repository, "commit", "-m", "fixture plugin change")
    head = git(repository, "rev-parse", "HEAD")
    paths, resolved, tip, reason = planner.changed_paths(repository, "pull_request", base, head)
    plan = planner.build_plan(repository, paths, resolved, tip, reason)
    assert plan["full_tests"] is registry_changed
    assert names(plan) == (
        {"alpha", "beta", "development-harness", "global"} if registry_changed else {"alpha", "global"}
    )
    assert plan["checks"]["manifest-sync"]


def test_marketplace_comparison_without_history_is_conservative(repository: Path) -> None:
    """Unavailable manifest evidence does not become an assumed version-only bump."""
    plan = planner.build_plan(repository, [".claude-plugin/marketplace.json", "plugins/alpha/README.md"])
    assert plan["full_tests"]
    assert plan["lint_all"]
