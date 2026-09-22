#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pydantic>=2.0",
#   "pytest",
# ]
# [tool.ty.environment]
# root = ["."]
# ///
"""Single-use and canonical-argv replay authorization checks."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from rebase_test_support import VALIDATOR_PATH, run_git
from test_rebase_prepare import live_plan_data, run_execute


def test_executor_rejects_the_observed_wrong_argv_and_retry_after_reset(tmp_path: Path) -> None:
    """Reject free-form --onto input and a second replay after reset under one consumed hash."""
    repository = tmp_path / "repository"
    plan_path = tmp_path / "plan.json"
    data = live_plan_data(repository)
    plan_path.write_text(json.dumps(data), encoding="utf-8")
    expected_hash = hashlib.sha256(plan_path.read_bytes()).hexdigest()
    branch = data["branch"]
    recovery_ref = data["recovery_ref"]
    assert isinstance(branch, dict)
    assert isinstance(recovery_ref, str)
    old_tip = branch["oid"]
    assert isinstance(old_tip, str)
    wrong_argv = json.dumps([
        "git",
        "rebase",
        "--rebase-merges",
        "--reapply-cherry-picks",
        "--empty=stop",
        "--keep-empty",
        "--onto",
        "refs/heads/main",
        "refs/heads/feature",
    ])
    command = [sys.executable, str(VALIDATOR_PATH), "execute", str(plan_path)]
    rejected = subprocess.run(
        [*command, "--expected-sha256", expected_hash, "--argv-json", wrong_argv],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
    )
    first = run_execute(repository, plan_path, expected_hash)
    run_git(repository, "reset", "--hard", recovery_ref)
    second = run_execute(repository, plan_path, expected_hash)

    assert rejected.returncode != 0
    assert run_git(repository, "rev-parse", recovery_ref).stdout.strip() == old_tip
    assert first.returncode == 0
    assert second.returncode != 0
    second_output = json.loads(second.stdout)
    assert second_output["state"] == "BLOCKED_GIT_STATE"
    assert "argv" not in second_output
