#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pydantic>=2.7",
# ]
#
# [tool.ty.environment]
# root = [".", ".."]
# ///
"""Drive the DH work ledger's whole work loop through the ``sam plan`` CLI and nothing else.

This is the cross-harness proof that a runner needs only the ability to run a command, read a file
and write a file: no MCP server, no harness of its own, and no import of the package it drives.
Every command and flag it issues is one ``dh_core/ledger_spec.py`` names; the only other program it
runs is ``git rev-parse``, for the base commit ``create --base-sha`` records. The order they run in
is the one ``docs/work-ledger/work-loop.md`` (orchestrator) and ``docs/work-ledger/runner-contract.md``
(runner) set out.

The plan it drives is ``tests_sam/fixtures/loop-plan/``: three tasks, T1 and T2 parallel and T3
dependent on both. T3's first attempt leaves its second acceptance criterion unmet, so the judge
sends it back with ``reclaim --response`` (work-loop.md row J2) and a second attempt finishes it.

The runner records rather than asserts. Every behaviour the loop is supposed to show becomes an
:class:`Observation` carrying what was expected and what was observed, keyed by a :class:`Check` and
by the task, attempt, wave or report section it belongs to, so a regression names the step that
broke. :func:`main` still exits non-zero when any observation is unsatisfied, which is the verdict a
hand run wants. Nothing is read off stdout by substring: each command's output is parsed as JSON
into a :class:`CommandResult` with typed views, and ``dispatch``'s bare attempt number and the
``unchanged`` no-op line are handled as their own documented shapes.

Run it by hand, on any platform::

    ./plugins/development-harness/tests_sam/scripted_runner.py
    uv run plugins/development-harness/tests_sam/scripted_runner.py

It writes nothing outside a work directory: ``DH_STATE_HOME`` points into one and
``BACKLOG_BACKEND`` is ``sqlite``, so the ledger it builds is its own and it reaches no network,
no shared store and no credentials. Pass ``--work-dir`` to keep that directory for inspection and
``--plugin-root`` to run against a plugin checkout other than this script's own.

The loop lives in ``tests_sam/scripted_runner_lib/``, so no one file of it grows past a single read:
``errors.py`` names every way a run stops, ``workspace.py`` resolves the toolchain and the state root
and reads the fixture files, ``ledger_cli.py`` runs one command and parses what it printed,
``observations.py`` holds what the loop watched, and ``driver.py`` drives the loop. This file is the
entry script and re-exports that surface, so it alone carries the shebang and the ``# /// script``
block, whose dependencies are the whole runner's; the modules are plain ``.py`` files, as
``rules/python-development.md`` sets out.

Some of this file's tests prove their claims by reading the source rather than running it: that
nothing in the runner imports ``dh_core`` or ``sam_schema``, that nothing in it builds a shell
command, and that the shebang and the metadata block sit on this file and on no module. Each reads
every file :func:`source_paths` returns — this script plus every module of that package — so a
module added there is held to all of them without anyone updating a list.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path

SOURCE_PATH: Path = Path(__file__).resolve()
"""This script's own file: the loop's entry point, and the artefact tests' first source."""

# The loop's modules are addressed as ``tests_sam.scripted_runner_lib.…`` so that one spelling works
# both when this file is run as a script (sys.path holds its own directory) and when it is imported
# as part of the test package (sys.path holds the plugin root). Putting the plugin root first
# satisfies the first case and is already true in the second.
PLUGIN_ROOT = str(SOURCE_PATH.parents[1])
if PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, PLUGIN_ROOT)

from tests_sam.scripted_runner_lib.driver import SEND_BACK_MARKER, LoopDriver
from tests_sam.scripted_runner_lib.errors import (
    CommandTimeoutError,
    FixtureMissingError,
    ScriptedRunnerError,
    ToolchainMissingError,
)
from tests_sam.scripted_runner_lib.ledger_cli import Argument, CommandCall, CommandResult, LedgerCli, LedgerCommandError
from tests_sam.scripted_runner_lib.observations import Check, LoopRecord, Observation, ObservationKey
from tests_sam.scripted_runner_lib.workspace import (
    FIXTURE_DIRECTORY,
    LIBRARY_DIRECTORY,
    RUN_TIMEOUT_SECONDS,
    Fixtures,
    Preparation,
    Toolchain,
    Workspace,
    prepare_workspace,
    resolve_program,
)

__all__ = [
    "FIXTURE_DIRECTORY",
    "RUN_TIMEOUT_SECONDS",
    "SEND_BACK_MARKER",
    "SOURCE_PATH",
    "Argument",
    "Check",
    "CommandCall",
    "CommandResult",
    "CommandTimeoutError",
    "FixtureMissingError",
    "Fixtures",
    "LedgerCli",
    "LedgerCommandError",
    "LoopDriver",
    "LoopRecord",
    "Observation",
    "ObservationKey",
    "Preparation",
    "ScriptedRunnerError",
    "Toolchain",
    "ToolchainMissingError",
    "Workspace",
    "build_parser",
    "main",
    "prepare_workspace",
    "report",
    "resolve_program",
    "run_loop",
    "source_paths",
]


def source_paths() -> tuple[Path, ...]:
    """Return every file the runner is built from, entry script first.

    Derived rather than listed: the library package's own directory is read, so a module added to
    the runner is held to the source-reading tests the moment it lands there.

    Returns:
        This script's path, then each module of ``scripted_runner_lib`` in name order.
    """
    return (SOURCE_PATH, *sorted(path.resolve() for path in LIBRARY_DIRECTORY.glob("*.py")))


def run_loop(
    work_dir: Path,
    *,
    plugin_root: Path | None = None,
    project_root: Path | None = None,
    timeout_seconds: int = RUN_TIMEOUT_SECONDS,
) -> LoopRecord:
    """Drive the whole work loop once under one work directory and return what it recorded.

    Args:
        work_dir: The directory the run writes everything into, state root included.
        plugin_root: The development-harness checkout holding ``sam_schema/cli.py``.
        project_root: What ``DH_PROJECT_ROOT`` names; the nearest ancestor holding ``.git`` by default.
        timeout_seconds: How long one ``sam plan`` command may take.

    Returns:
        The record of every command the loop issued and every observation it made.

    Raises:
        LedgerCommandError: When any ``sam plan`` command exits non-zero. Behavioural mismatches
            become unsatisfied observations instead, so the caller can name the step that broke.
        CommandTimeoutError: When one command does not finish inside ``timeout_seconds``.
    """
    preparation = prepare_workspace(
        work_dir, plugin_root=plugin_root, project_root=project_root, timeout_seconds=timeout_seconds
    )
    cli = LedgerCli(preparation.toolchain, preparation.workspace.environment, timeout_seconds)
    driver = LoopDriver(
        cli=cli,
        fixtures=Fixtures(FIXTURE_DIRECTORY),
        workspace=preparation.workspace,
        base_sha=preparation.toolchain.base_sha,
    )
    return driver.run()


def report(record: LoopRecord) -> int:
    """Print every unsatisfied observation and return the run's exit status.

    Args:
        record: What the loop recorded.

    Returns:
        0 when every observation held, 1 otherwise.
    """
    for failure in record.failures:
        print(
            f"scripted-runner: {failure.check.value} ({failure.label}): {failure.expectation}; "
            f"expected {failure.expected!r}, observed {failure.observed!r}",
            file=sys.stderr,
        )
    if record.failures:
        print(
            f"scripted-runner: plan {record.plan} left {len(record.failures)} observation(s) unsatisfied",
            file=sys.stderr,
        )
        return 1
    print(f"scripted-runner: plan {record.plan} reached progress done")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Return the hand-run argument parser.

    Returns:
        The parser for ``--work-dir``, ``--plugin-root`` and ``--timeout-seconds``.
    """
    parser = argparse.ArgumentParser(description="Drive the DH work ledger's whole work loop through the sam plan CLI.")
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=None,
        help="keep the run's state root here instead of in a temporary directory that is removed",
    )
    parser.add_argument(
        "--plugin-root", type=Path, default=None, help="the development-harness checkout to drive; this one by default"
    )
    parser.add_argument(
        "--timeout-seconds", type=int, default=RUN_TIMEOUT_SECONDS, help="how long one sam plan command may take"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the loop by hand, print each unsatisfied observation, and return the run's status.

    Args:
        argv: The command line, or None to read ``sys.argv``.

    Returns:
        0 when every observation held, 1 otherwise.
    """
    arguments = build_parser().parse_args(argv)
    try:
        if arguments.work_dir is not None:
            work_dir = Path(arguments.work_dir)
            work_dir.mkdir(parents=True, exist_ok=True)
            return report(
                run_loop(work_dir, plugin_root=arguments.plugin_root, timeout_seconds=arguments.timeout_seconds)
            )
        with tempfile.TemporaryDirectory(prefix="scripted-runner-") as temporary:
            return report(
                run_loop(Path(temporary), plugin_root=arguments.plugin_root, timeout_seconds=arguments.timeout_seconds)
            )
    except ScriptedRunnerError as error:
        print(f"scripted-runner: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
