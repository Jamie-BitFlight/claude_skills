"""The scripted runner: the whole work loop driven by a POSIX shell and the ``sam plan`` CLI.

``scripted_runner.sh`` is the cross-harness proof that a runner needs nothing but a shell. It
builds the ``fixtures/loop-plan`` plan — T1 and T2 parallel, T3 behind both — dispatches each
task, works it the way ``docs/work-ledger/runner-contract.md`` sets out, judges it the way
``docs/work-ledger/work-loop.md`` sets out, sends T3 back once with ``reclaim --response`` because
its first attempt left an acceptance criterion unmet, and finishes with the plan reporting
progress ``done``. It stops on the first unexpected exit code, so its own exit status is the whole
verdict.

Two tests here. One reads the script and holds every command and flag it runs against
``dh_core.ledger_spec.COMMANDS``, so the proof cannot quietly start depending on a surface the
specification does not name. The other runs it.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest
from dh_core import ledger_spec

SCRIPT: Path = Path(__file__).parent / "scripted_runner.sh"
"""The shell script under test."""

FIXTURE_DIR: Path = Path(__file__).parent / "fixtures" / "loop-plan"
"""The plan the script drives, as the files it reads its flag values from."""

RUN_TIMEOUT_SECONDS = 900
"""How long the whole loop may take; every ``sam plan`` call starts its own interpreter."""

LINE_CONTINUATION = re.compile(r"\\\n\s*")
"""A shell line continuation and the indentation after it, joined before the calls are read."""

SAM_CALL = re.compile(r"^\s+sam (?P<command>[a-z][a-z-]*)(?P<arguments>.*)$", re.MULTILINE)
"""One call of the script's ``sam`` helper: the command name and everything after it."""

LONG_FLAG = re.compile(r"--[a-z][a-z-]*")
"""A long flag inside one call's arguments."""

posix_only = pytest.mark.skipif(os.name != "posix", reason="the scripted runner is a POSIX shell script")


def script_calls() -> list[tuple[str, set[str]]]:
    """Read every ``sam plan`` call the script makes.

    Returns:
        One ``(command, flags)`` pair per call, in the order the script writes them.
    """
    text = LINE_CONTINUATION.sub(" ", SCRIPT.read_text(encoding="utf-8"))
    return [
        (match.group("command"), set(LONG_FLAG.findall(match.group("arguments")))) for match in SAM_CALL.finditer(text)
    ]


def test_the_scripted_runner_calls_only_commands_and_flags_the_specification_names() -> None:
    """Every command the script runs is a ``COMMANDS`` entry, and every flag is one of its own."""
    declared = {command.name: {flag.name for flag in command.flags} for command in ledger_spec.COMMANDS}
    calls = script_calls()

    assert calls, "no sam plan calls were read out of the script"
    for command, flags in calls:
        assert command in declared, f"{command} is not a ledger_spec.COMMANDS entry"
        assert flags <= declared[command], f"{command} is called with {sorted(flags - declared[command])}"


def test_the_scripted_runner_drives_every_command_the_loop_needs() -> None:
    """The script runs the whole loop, from ``ready`` through the send-back to ``status``."""
    needed = {
        "create",
        "append-task",
        "update",
        "finalize",
        "validate",
        "ready",
        "dispatch",
        "read",
        "renew",
        "finish",
        "settle",
        "accept",
        "reclaim",
        "status",
    }

    called = {command for command, _ in script_calls()}

    assert needed <= called, f"the script never runs {sorted(needed - called)}"


@posix_only
def test_the_scripted_runner_is_runnable_by_hand() -> None:
    """The script and its fixture are on disk, and the script is executable from a plain shell."""
    assert SCRIPT.is_file()
    assert os.access(SCRIPT, os.X_OK), f"{SCRIPT} is not executable"
    assert (FIXTURE_DIR / "tasks" / "T3" / "dependencies.json").is_file()


@posix_only
def test_the_scripted_runner_drives_the_plan_to_progress_done(tmp_path: Path) -> None:
    """Running the script exits zero, which means every command in the loop went as the loop says."""
    work_dir = tmp_path / "work"

    process = subprocess.run(
        [str(SCRIPT)],
        capture_output=True,
        text=True,
        timeout=RUN_TIMEOUT_SECONDS,
        check=False,
        env={**os.environ, "SCRIPTED_RUNNER_WORK_DIR": str(work_dir)},
    )

    assert process.returncode == 0, f"stdout:\n{process.stdout}\nstderr:\n{process.stderr}"
    assert "reached progress done" in process.stdout
