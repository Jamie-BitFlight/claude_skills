#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pydantic>=2.7",
# ]
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

Keep this one file. A PEP 723 script carries its dependencies inline and so must be standalone to
stay runnable by hand, and three of its tests prove their claims by reading this source: that it
imports neither ``dh_core`` nor ``sam_schema``, that it builds no shell command, and that it
carries the canonical shebang. Moving the driver into a sibling module would take that surface out
of the file under proof.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel

SOURCE_PATH: Path = Path(__file__).resolve()
"""This module's own file; the artefact tests read it rather than run it."""

FIXTURE_DIRECTORY: Path = SOURCE_PATH.parent / "fixtures" / "loop-plan"
"""The loop-plan fixture: the plan's fields, the report sections and the send-back response."""

DEFAULT_PLUGIN_ROOT: Path = SOURCE_PATH.parent.parent
"""The development-harness checkout this script belongs to, which holds ``sam_schema/cli.py``."""

LEASE_TTL_SECONDS: int = 900
"""The lease every ``dispatch`` opens, in seconds."""

RETURN_TEXT: str = "STATUS: DONE"
"""What ``settle`` records as the launch's return, per ``dh:subagent-contract``."""

SEND_BACK_MARKER: str = "SEND-BACK-MARKER"
"""A phrase inside the send-back response, proving the judge's text reaches the next attempt."""

RESPONSE_SECTION: str = "Orchestrator Response"
"""What ``read`` heads a sent-back attempt with. Duplicated from ``ledger_spec`` by design: the
proof is that the CLI is enough, so this script may not import the package behind it."""

REPORT_SECTIONS: tuple[str, str] = ("Completion Report", "Verification Results")
"""The two sections a runner appends before ``finish``. Duplicated for the same reason."""

RUN_TIMEOUT_SECONDS: int = 300
"""How long one ``sam plan`` command may take before the run is abandoned."""

OWNER_REFERENCE: str = "work-ledger scripted runner"
"""What ``create --owner-reference`` records as the work item behind the plan."""

TASK_IDS: tuple[str, str, str] = ("T1", "T2", "T3")
"""The fixture's three tasks, in the order ``append-task`` adds them."""

FIRST_WAVE: str = "first"
SECOND_WAVE: str = "second"
SEND_BACK_WAVE: str = "send-back"

COUNT_EXPECTATIONS: dict[str, str] = {
    FIRST_WAVE: "the first wave holds two tasks",
    SECOND_WAVE: "the second wave holds one task",
}
"""How each wave's ``ready`` count reads in a failure message."""

LIST_EXPECTATIONS: dict[str, str] = {
    FIRST_WAVE: "the first wave lists {task}",
    SECOND_WAVE: "the second wave lists {task}",
    SEND_BACK_WAVE: "the send-back makes {task} ready again",
}
"""How each wave's ``ready`` membership reads in a failure message."""

ADDRESS_FLAGS: frozenset[str] = frozenset({"--address", "--plan-address"})
"""The flags that carry the plan or task a command acts on."""

NO_OP_CODE = re.compile(r"^[a-z][a-z-]*$")
"""A bare reason code, such as ``unchanged``, printed instead of a JSON result."""


# ---------------------------------------------------------------------------
# Failing loudly
# ---------------------------------------------------------------------------


class ScriptedRunnerError(RuntimeError):
    """The run cannot go on."""


class ToolchainMissingError(ScriptedRunnerError):
    """A program the run needs is not resolvable on PATH."""


class FixtureMissingError(ScriptedRunnerError):
    """A loop-plan fixture file the loop reads is absent."""


class CommandTimeoutError(ScriptedRunnerError):
    """A command did not finish inside the time the run allows it."""


# ---------------------------------------------------------------------------
# What one command is, and what it printed
# ---------------------------------------------------------------------------


class Argument(BaseModel):
    """One long flag of a ``sam plan`` command, with the value it carries."""

    name: str
    value: str | None = None


class CommandCall(BaseModel):
    """One ``sam plan`` invocation, as the surface tests read it."""

    command: str
    flags: tuple[str, ...] = ()
    address: str | None = None


class CommandResult(BaseModel):
    """One invocation's outcome, parsed rather than scraped.

    Every view below answers with a real default when the command's shape does not carry that
    field, so a caller reads an empty result instead of handling an exception.
    """

    call: CommandCall
    exit_code: int
    stdout: str
    stderr: str
    payload: dict[str, Any] | list[Any] | None = None

    @property
    def fields(self) -> dict[str, Any]:
        """Return the payload's own fields, or an empty mapping when it is not an object."""
        return self.payload if isinstance(self.payload, dict) else {}

    @property
    def findings(self) -> list[Any]:
        """Return the payload's entries, or an empty list when it is not an array."""
        return self.payload if isinstance(self.payload, list) else []

    @property
    def events(self) -> tuple[str, ...]:
        """Return the event kinds the command appended to the log."""
        recorded = self.fields.get("events")
        return tuple(str(item) for item in recorded) if isinstance(recorded, list) else ()

    @property
    def status(self) -> str | None:
        """Return the task status the command reports, when it reports one."""
        reported = self.fields.get("status")
        return str(reported) if isinstance(reported, str) else None

    @property
    def attempt(self) -> int | None:
        """Return the attempt number, from the payload or from ``dispatch``'s bare line."""
        reported = self.fields.get("attempt")
        if isinstance(reported, int):
            return reported
        printed = self.stdout.strip()
        return int(printed) if printed.isdigit() else None

    @property
    def task(self) -> str | None:
        """Return the task the command acted on, when it names one."""
        named = self.fields.get("task")
        return str(named) if isinstance(named, str) else None

    @property
    def renew_by(self) -> str | None:
        """Return the new lease deadline, when the command renewed one."""
        deadline = self.fields.get("renew_by")
        return str(deadline) if isinstance(deadline, str) else None

    @property
    def changed(self) -> dict[str, Any]:
        """Return the columns the command wrote."""
        written = self.fields.get("changed")
        return written if isinstance(written, dict) else {}

    @property
    def row(self) -> dict[str, Any]:
        """Return the task row the command rendered, when it rendered one."""
        rendered = self.fields.get("row")
        return rendered if isinstance(rendered, dict) else {}

    @property
    def items(self) -> tuple[dict[str, Any], ...]:
        """Return the task rows a listing command rendered."""
        listed = self.fields.get("items")
        return tuple(item for item in listed if isinstance(item, dict)) if isinstance(listed, list) else ()

    @property
    def count(self) -> int | None:
        """Return how many rows a listing command counted."""
        counted = self.fields.get("count")
        return counted if isinstance(counted, int) else None

    @property
    def sections(self) -> tuple[dict[str, Any], ...]:
        """Return the report sections the command rendered."""
        rendered = self.fields.get("sections")
        return tuple(item for item in rendered if isinstance(item, dict)) if isinstance(rendered, list) else ()

    @property
    def noop(self) -> str | None:
        """Return the bare no-op code the command printed instead of a result, when it did."""
        printed = self.stdout.strip()
        return printed if self.payload is None and NO_OP_CODE.match(printed) else None


class LedgerCommandError(ScriptedRunnerError):
    """A ``sam plan`` command exited non-zero, which stops the run."""

    def __init__(self, result: CommandResult) -> None:
        """Carry the command, its status and both of its streams into the message.

        Args:
            result: The outcome of the command that exited non-zero.
        """
        self.call = result.call
        self.exit_code = result.exit_code
        self.stdout = result.stdout
        self.stderr = result.stderr
        super().__init__(
            f"sam plan {result.call.command} {' '.join(result.call.flags)} exited {result.exit_code}\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )


# ---------------------------------------------------------------------------
# What the loop watched
# ---------------------------------------------------------------------------


class Check(StrEnum):
    """One named behaviour the loop is supposed to show."""

    PLAN_CREATED = "plan.created"
    PLAN_FINALIZED = "plan.finalized"
    PLAN_VALIDATES_CLEAN = "plan.validates-clean"
    READY_COUNT = "ready.count"
    READY_LISTS = "ready.lists"
    READY_WITHHOLDS = "ready.withholds"
    DISPATCH_ATTEMPT = "dispatch.attempt"
    READ_RETURNS_TASK = "read.returns-task"
    READ_IN_PROGRESS = "read.in-progress"
    READ_CARRIES_RESPONSE = "read.carries-response"
    READ_CARRIES_SEND_BACK_TEXT = "read.carries-send-back-text"
    RENEW_DEADLINE = "renew.deadline"
    SECTION_APPENDED = "section.appended"
    FINISH_COMPLETE = "finish.complete"
    SETTLE_RECORDED = "settle.recorded"
    ACCEPT_RECORDED = "accept.recorded"
    RECLAIM_NOT_STARTED = "reclaim.not-started"
    EXPORT_WROTE = "export.wrote"
    EXPORT_UNCHANGED = "export.unchanged"
    PLAN_PROGRESS_DONE = "plan.progress-done"


class ObservationKey(BaseModel):
    """Where in the loop an observation belongs, which is how a caller addresses it."""

    wave: str = ""
    task: str = ""
    attempt: int | None = None
    section: str = ""


class Observation(BaseModel):
    """What one :class:`Check` expected and what the loop actually saw."""

    check: Check
    wave: str = ""
    task: str = ""
    attempt: int | None = None
    section: str = ""
    expectation: str
    expected: str
    observed: str
    satisfied: bool

    @property
    def label(self) -> str:
        """Return where this observation belongs, for a failure message."""
        parts = [part for part in (self.task, f"attempt {self.attempt}" if self.attempt is not None else "") if part]
        if self.section:
            parts.append(self.section)
        if self.wave:
            parts.append(f"{self.wave} wave")
        return " ".join(parts) if parts else "the plan"


class Workspace(BaseModel):
    """The temporary state root a run owns, so a hand run touches no real ledger."""

    root: Path
    state_home: Path
    worktrees: Path
    environment: dict[str, str]

    def worktree_for(self, task: str) -> Path:
        """Return the worktree ``dispatch`` records for one task.

        Args:
            task: The task identifier, such as ``T1``.

        Returns:
            The directory that task's attempts run in.
        """
        return self.worktrees / task


class Toolchain(BaseModel):
    """The programs and paths one run needs before it can reach the ledger."""

    uv: Path
    git: Path
    plugin_root: Path
    cli_path: Path
    base_sha: str


class Preparation(BaseModel):
    """Everything :func:`prepare_workspace` resolved before the loop starts."""

    workspace: Workspace
    toolchain: Toolchain


class LoopRecord(BaseModel):
    """Everything one run of the loop did and saw."""

    plan: str
    workspace: Workspace
    calls: tuple[CommandCall, ...]
    observations: tuple[Observation, ...]

    def observation(
        self, check: Check, *, wave: str = "", task: str = "", attempt: int | None = None, section: str = ""
    ) -> Observation:
        """Return the one observation recorded under this check and place.

        Args:
            check: The behaviour the observation watched.
            wave: The wave it belongs to, or empty for a plan-wide observation.
            task: The task it belongs to, or empty.
            attempt: The attempt it belongs to, or None.
            section: The report section it belongs to, or empty.

        Returns:
            The matching observation.

        Raises:
            LookupError: When the loop recorded no observation in that place.
        """
        for item in self.observations:
            place = (item.wave, item.task, item.attempt, item.section)
            if item.check is check and place == (wave, task, attempt, section):
                return item
        raise LookupError(f"the loop recorded no {check.value} for {(wave, task, attempt, section)}")

    def observations_for(self, check: Check) -> tuple[Observation, ...]:
        """Return every observation recorded under one check.

        Args:
            check: The behaviour the observations watched.

        Returns:
            Every matching observation, in the order the loop recorded them.
        """
        return tuple(item for item in self.observations if item.check is check)

    @property
    def failures(self) -> tuple[Observation, ...]:
        """Return every observation the loop left unsatisfied."""
        return tuple(item for item in self.observations if not item.satisfied)


# ---------------------------------------------------------------------------
# The two things the loop reads: the fixture files and the CLI
# ---------------------------------------------------------------------------


class Fixtures:
    """Reads the loop-plan fixture files, refusing to hand back an absent one as empty text."""

    def __init__(self, directory: Path) -> None:
        """Bind the reader to one fixture directory.

        Args:
            directory: The loop-plan fixture root.
        """
        self.directory = directory

    def path(self, *parts: str) -> Path:
        """Return where one fixture file sits.

        Args:
            *parts: The path segments below the fixture root.

        Returns:
            The fixture file's path.
        """
        return self.directory.joinpath(*parts)

    def has(self, *parts: str) -> bool:
        """Return whether one fixture file exists.

        Args:
            *parts: The path segments below the fixture root.

        Returns:
            True when the file is there.
        """
        return self.path(*parts).is_file()

    def read(self, *parts: str) -> str:
        """Return one fixture file's text, without the trailing newline the file convention adds.

        Args:
            *parts: The path segments below the fixture root.

        Returns:
            The file's text as a ledger field, report section or send-back response.

        Raises:
            FixtureMissingError: When the file is absent.
        """
        target = self.path(*parts)
        if not target.is_file():
            raise FixtureMissingError(f"the loop-plan fixture has no {'/'.join(parts)}")
        return target.read_text(encoding="utf-8").rstrip("\n")


def parse_payload(stdout: str) -> dict[str, Any] | list[Any] | None:
    """Return one command's stdout as the JSON object or array it is, or None when it is neither.

    Args:
        stdout: What the command printed.

    Returns:
        The parsed object or array, or None for a bare no-op code, a bare attempt number or silence.
    """
    text = stdout.strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict | list) else None


def address_of(arguments: Sequence[Argument]) -> str | None:
    """Return the plan or task one command acts on.

    Args:
        arguments: The command's flags and their values.

    Returns:
        The ``--address`` or ``--plan-address`` value, or None when the command names neither.
    """
    for item in arguments:
        if item.name in ADDRESS_FLAGS:
            return item.value
    return None


class LedgerCli:
    """Runs one ``sam plan`` command per call, as a subprocess and never through a shell."""

    def __init__(self, toolchain: Toolchain, environment: Mapping[str, str], timeout_seconds: int) -> None:
        """Bind the driver to one CLI, one environment and one per-command timeout.

        Args:
            toolchain: The resolved ``uv`` and the CLI it runs.
            environment: The variables this run adds to the inherited environment.
            timeout_seconds: How long one command may take.
        """
        self.toolchain = toolchain
        self.environment = {**os.environ, **environment, "PYTHONIOENCODING": "utf-8"}
        self.timeout_seconds = timeout_seconds

    def run(self, command: str, arguments: Sequence[Argument]) -> CommandResult:
        """Run one ``sam plan`` command and return what it printed, parsed.

        Args:
            command: The ``sam plan`` command name.
            arguments: Its flags and their values.

        Returns:
            The command's outcome.

        Raises:
            LedgerCommandError: When the command exits non-zero, which is unexpected on this path.
            CommandTimeoutError: When the command does not finish inside the run's per-command limit.
        """
        argv = [str(self.toolchain.uv), "run", str(self.toolchain.cli_path), "plan", command]
        for item in arguments:
            argv.append(item.name)
            if item.value is not None:
                argv.append(item.value)
        try:
            completed = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=self.environment,
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as expired:
            flags = " ".join(item.name for item in arguments)
            raise CommandTimeoutError(
                f"sam plan {command} {flags} did not finish within {self.timeout_seconds} seconds"
            ) from expired
        result = CommandResult(
            call=CommandCall(
                command=command, flags=tuple(item.name for item in arguments), address=address_of(arguments)
            ),
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            payload=parse_payload(completed.stdout),
        )
        if result.exit_code != 0:
            raise LedgerCommandError(result)
        return result


# ---------------------------------------------------------------------------
# The workspace: one state root, so a hand run touches no real ledger
# ---------------------------------------------------------------------------


def resolve_program(name: str, purpose: str) -> Path:
    """Return where one program the run needs sits.

    Args:
        name: The program's name, resolved on PATH.
        purpose: Why the run needs it, for the failure message.

    Returns:
        The program's path.

    Raises:
        ToolchainMissingError: When PATH holds no such program.
    """
    found = shutil.which(name)
    if found is None:
        raise ToolchainMissingError(f"{name} is not on PATH; {purpose}")
    return Path(found)


def nearest_repository(start: Path) -> Path:
    """Return the nearest ancestor of one directory holding a ``.git`` entry.

    Args:
        start: Where to start looking.

    Returns:
        The repository root.

    Raises:
        ScriptedRunnerError: When no ancestor holds one, so ``DH_PROJECT_ROOT`` cannot resolve.
    """
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    raise ScriptedRunnerError(f"no ancestor of {start} holds a .git entry; set DH_PROJECT_ROOT")


def base_commit(git: Path, plugin_root: Path, timeout_seconds: int) -> str:
    """Return the commit ``create --base-sha`` records for the judge to diff a report against.

    Args:
        git: The resolved ``git`` program.
        plugin_root: The checkout to read HEAD from.
        timeout_seconds: How long the read may take.

    Returns:
        The commit sha.

    Raises:
        ScriptedRunnerError: When the checkout has no commit to name.
        CommandTimeoutError: When the read does not finish inside the run's per-command limit.
    """
    try:
        completed = subprocess.run(
            [str(git), "-C", str(plugin_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as expired:
        raise CommandTimeoutError(
            f"reading HEAD of {plugin_root} did not finish within {timeout_seconds} seconds"
        ) from expired
    sha = completed.stdout.strip()
    if completed.returncode != 0 or not sha:
        raise ScriptedRunnerError(
            f"no commit at {plugin_root} to diff reports against; point --plugin-root at a checkout\n"
            f"stderr: {completed.stderr}"
        )
    return sha


def prepare_workspace(
    work_dir: Path,
    *,
    plugin_root: Path | None = None,
    project_root: Path | None = None,
    timeout_seconds: int = RUN_TIMEOUT_SECONDS,
) -> Preparation:
    """Resolve the toolchain and lay out the state root one run owns.

    Args:
        work_dir: The directory the run writes everything into.
        plugin_root: The development-harness checkout holding ``sam_schema/cli.py``.
        project_root: What ``DH_PROJECT_ROOT`` names; the nearest ancestor holding ``.git`` by default.
        timeout_seconds: How long the base-commit read may take.

    Returns:
        The workspace and the toolchain the loop runs against.

    Raises:
        ScriptedRunnerError: When the checkout holds no CLI at the documented path.
    """
    uv = resolve_program("uv", "it is how sam_schema/cli.py resolves its dependencies")
    git = resolve_program("git", "the plan needs a base commit for --base-sha")
    root = plugin_root if plugin_root is not None else DEFAULT_PLUGIN_ROOT
    cli_path = root / "sam_schema" / "cli.py"
    if not cli_path.is_file():
        raise ScriptedRunnerError(f"no CLI at {cli_path}; point --plugin-root at the development-harness plugin")
    toolchain = Toolchain(
        uv=uv, git=git, plugin_root=root, cli_path=cli_path, base_sha=base_commit(git, root, timeout_seconds)
    )
    state_home = work_dir / "state"
    worktrees = work_dir / "worktrees"
    state_home.mkdir(parents=True, exist_ok=True)
    worktrees.mkdir(parents=True, exist_ok=True)
    repository = project_root if project_root is not None else nearest_repository(SOURCE_PATH.parent)
    workspace = Workspace(
        root=work_dir,
        state_home=state_home,
        worktrees=worktrees,
        # `export` writes through the configured backlog backend. SQLite keeps its database under
        # DH_STATE_HOME, so the run reaches no network and no shared store; the default is GitHub,
        # which needs credentials this script has no business holding.
        environment={"DH_STATE_HOME": str(state_home), "BACKLOG_BACKEND": "sqlite", "DH_PROJECT_ROOT": str(repository)},
    )
    return Preparation(workspace=workspace, toolchain=toolchain)


# ---------------------------------------------------------------------------
# The loop
# ---------------------------------------------------------------------------


def section_file_name(section: str) -> str:
    """Return the fixture file one report section's content lives in.

    Args:
        section: The section name, such as ``Completion Report``.

    Returns:
        The file name below ``reports/<task>/attempt-<n>/``.
    """
    return f"{section.lower().replace(' ', '-')}.md"


class LoopDriver:
    """Drives the work loop once, recording what every command showed."""

    def __init__(self, cli: LedgerCli, fixtures: Fixtures, workspace: Workspace, base_sha: str) -> None:
        """Bind the driver to one CLI, one fixture set and one workspace.

        Args:
            cli: How the driver reaches the ledger.
            fixtures: The loop-plan fixture files.
            workspace: The state root this run owns.
            base_sha: The commit ``create --base-sha`` records.
        """
        self.cli = cli
        self.fixtures = fixtures
        self.workspace = workspace
        self.base_sha = base_sha
        self.plan = ""
        self.calls: list[CommandCall] = []
        self.observations: list[Observation] = []

    # -- reaching the ledger, and writing down what came back ---------------

    def sam(self, command: str, *arguments: Argument) -> CommandResult:
        """Run one ``sam plan`` command and remember that the loop issued it.

        Args:
            command: The ``sam plan`` command name.
            *arguments: Its flags and their values.

        Returns:
            The command's outcome.
        """
        result = self.cli.run(command, arguments)
        self.calls.append(result.call)
        return result

    def plan_argument(self) -> Argument:
        """Return the ``--plan-address`` flag naming the plan this run built."""
        return Argument(name="--plan-address", value=self.plan)

    def address_argument(self, task: str) -> Argument:
        """Return the ``--address`` flag naming one task of the plan this run built.

        Args:
            task: The task identifier.

        Returns:
            The flag and its ``P/T`` value.
        """
        return Argument(name="--address", value=f"{self.plan}/{task}")

    def record(
        self, check: Check, key: ObservationKey, expectation: str, expected: str, observed: str, satisfied: bool
    ) -> None:
        """Write down what one check expected and what it saw.

        Args:
            check: The behaviour being watched.
            key: Where in the loop it belongs.
            expectation: The behaviour in prose, for a failure message.
            expected: What the loop should have seen.
            observed: What it did see.
            satisfied: Whether those agree.
        """
        self.observations.append(
            Observation(
                check=check,
                wave=key.wave,
                task=key.task,
                attempt=key.attempt,
                section=key.section,
                expectation=expectation,
                expected=expected,
                observed=observed,
                satisfied=satisfied,
            )
        )

    def record_equal(self, check: Check, key: ObservationKey, expectation: str, expected: str, observed: str) -> None:
        """Write down a check that holds when one value equals another.

        Args:
            check: The behaviour being watched.
            key: Where in the loop it belongs.
            expectation: The behaviour in prose.
            expected: The value the loop should have read.
            observed: The value it read.
        """
        self.record(check, key, expectation, expected, observed or "nothing", expected == observed)

    def record_among(
        self, check: Check, key: ObservationKey, expectation: str, expected: str, values: Sequence[str]
    ) -> None:
        """Write down a check that holds when one value is among those the command listed.

        Args:
            check: The behaviour being watched.
            key: Where in the loop it belongs.
            expectation: The behaviour in prose.
            expected: The value that should be listed.
            values: What the command listed.
        """
        self.record(check, key, expectation, expected, ", ".join(values) or "nothing", expected in values)

    def record_absent(
        self, check: Check, key: ObservationKey, expectation: str, unexpected: str, values: Sequence[str]
    ) -> None:
        """Write down a check that holds when one value is not among those the command listed.

        Args:
            check: The behaviour being watched.
            key: Where in the loop it belongs.
            expectation: The behaviour in prose.
            unexpected: The value that should be withheld.
            values: What the command listed.
        """
        self.record(
            check, key, expectation, f"no {unexpected}", ", ".join(values) or "nothing", unexpected not in values
        )

    # -- the plan: three tasks, T3 behind T1 and T2 -------------------------

    def build_plan(self) -> None:
        """Create the plan, append its three tasks, finalize it and validate it.

        ``--base-sha`` records the commit the judge diffs a report against, and it is also what
        tells ``create`` to write the ledger rather than a content record.

        Raises:
            ScriptedRunnerError: When ``create`` prints no plan id, leaving nothing to address.
        """
        created = self.sam(
            "create",
            Argument(name="--slug", value=self.fixtures.read("slug.txt")),
            Argument(name="--goal", value=self.fixtures.read("goal.txt")),
            Argument(name="--owner-reference", value=OWNER_REFERENCE),
            Argument(name="--base-sha", value=self.base_sha),
        )
        named = created.fields.get("plan")
        plan = str(named) if isinstance(named, str) else ""
        self.record(
            Check.PLAN_CREATED,
            ObservationKey(),
            "create prints the plan id every later command names",
            "a plan id",
            plan or "nothing",
            bool(plan),
        )
        if not plan:
            raise ScriptedRunnerError(f"create printed no plan id: {created.stdout!r}")
        self.plan = plan
        for task in TASK_IDS:
            self.append_task(task)
        finalized = self.sam("finalize", self.plan_argument())
        self.record_equal(
            Check.PLAN_FINALIZED,
            ObservationKey(),
            "finalize makes the plan ready",
            "ready",
            str(finalized.changed.get("state") or ""),
        )
        validated = self.sam("validate", self.plan_argument())
        self.record(
            Check.PLAN_VALIDATES_CLEAN,
            ObservationKey(),
            "validate finds nothing structural",
            "[]",
            json.dumps(validated.findings) if isinstance(validated.payload, list) else validated.stdout.strip(),
            validated.payload == [],
        )

    def append_task(self, task: str) -> None:
        """Add one task to the drafting plan and set the fields the fixture gives it.

        Args:
            task: The task identifier.
        """
        self.sam(
            "append-task",
            self.plan_argument(),
            Argument(name="--task-id", value=task),
            Argument(name="--task-title", value=self.fixtures.read("tasks", task, "title.txt")),
        )
        criteria = self.fixtures.read("tasks", task, "acceptance-criteria.md")
        steps = self.fixtures.read("tasks", task, "verification-steps.md")
        self.sam(
            "update",
            self.plan_argument(),
            Argument(name="--task-id", value=task),
            Argument(name="--set", value=f"acceptance_criteria={criteria}"),
            Argument(name="--set", value=f"verification_steps={steps}"),
        )
        if self.fixtures.has("tasks", task, "dependencies.json"):
            dependencies = self.fixtures.read("tasks", task, "dependencies.json")
            self.sam(
                "update",
                self.plan_argument(),
                Argument(name="--task-id", value=task),
                Argument(name="--set", value=f"dependencies={dependencies}"),
            )

    # -- the orchestrator's commands ---------------------------------------

    def check_ready(
        self, wave: str, *, expected_count: int | None, lists: Sequence[str], withholds: Sequence[str] = ()
    ) -> None:
        """Read the dispatchable set and write down what it holds and what it withholds.

        Args:
            wave: Which wave this ``ready`` opens.
            expected_count: How many tasks it should hold, or None when the wave does not fix one.
            lists: The tasks it must offer.
            withholds: The tasks it must not offer.
        """
        result = self.sam("ready", self.plan_argument())
        identifiers = tuple(str(item.get("id", "")) for item in result.items)
        if expected_count is not None:
            self.record_equal(
                Check.READY_COUNT,
                ObservationKey(wave=wave),
                COUNT_EXPECTATIONS[wave],
                str(expected_count),
                "" if result.count is None else str(result.count),
            )
        for task in lists:
            self.record_among(
                Check.READY_LISTS,
                ObservationKey(wave=wave, task=task),
                LIST_EXPECTATIONS[wave].format(task=task),
                task,
                identifiers,
            )
        for task in withholds:
            self.record_absent(
                Check.READY_WITHHOLDS,
                ObservationKey(wave=wave, task=task),
                f"the {wave} wave withholds the dependent task",
                task,
                identifiers,
            )

    def dispatch_task(self, task: str, expected_attempt: int) -> int:
        """Open an attempt on one task and return the attempt number ``dispatch`` printed.

        Args:
            task: The task identifier.
            expected_attempt: The attempt number this dispatch should open.

        Returns:
            The attempt number the ledger opened.

        Raises:
            ScriptedRunnerError: When ``dispatch`` prints no attempt number, leaving no runner key.
        """
        worktree = self.workspace.worktree_for(task)
        worktree.mkdir(parents=True, exist_ok=True)
        result = self.sam(
            "dispatch",
            self.address_argument(task),
            Argument(name="--ttl", value=str(LEASE_TTL_SECONDS)),
            Argument(name="--worktree", value=str(worktree)),
        )
        observed = result.attempt
        self.record(
            Check.DISPATCH_ATTEMPT,
            ObservationKey(task=task, attempt=expected_attempt),
            f"attempt {expected_attempt} of {task}",
            str(expected_attempt),
            "nothing" if observed is None else str(observed),
            observed == expected_attempt,
        )
        if observed is None:
            raise ScriptedRunnerError(f"dispatch of {task} printed no attempt number: {result.stdout!r}")
        return observed

    def settle_task(self, task: str, attempt: int) -> None:
        """Record what the launch of one attempt returned.

        Args:
            task: The task identifier.
            attempt: The attempt number.
        """
        result = self.sam(
            "settle",
            self.address_argument(task),
            Argument(name="--attempt", value=str(attempt)),
            Argument(name="--return-text", value=RETURN_TEXT),
        )
        self.record_among(
            Check.SETTLE_RECORDED,
            ObservationKey(task=task, attempt=attempt),
            f"settle records {task} attempt {attempt}",
            "task.settled",
            result.events,
        )

    def accept_task(self, task: str, note: str) -> None:
        """Judge row J1: every criterion met and every verification step passed.

        Args:
            task: The task identifier.
            note: The judge's note, stored on the row.
        """
        result = self.sam("accept", self.address_argument(task), Argument(name="--note", value=note))
        self.record_among(
            Check.ACCEPT_RECORDED, ObservationKey(task=task), f"accept records {task}", "task.accepted", result.events
        )

    def export_plan(self, wave: str) -> None:
        """Project the plan at a wave end, then prove a second export changes nothing.

        The projection hash, not the event count, is what decides, which is why the second export
        must report the ``unchanged`` no-op.

        Args:
            wave: Which wave end this export closes.
        """
        key = ObservationKey(wave=wave)
        first = self.sam("export", self.plan_argument())
        self.record(
            Check.EXPORT_WROTE,
            key,
            f"the {wave} export writes rather than reporting unchanged",
            "plan.exported",
            first.noop or ", ".join(first.events) or "nothing",
            first.noop is None and "plan.exported" in first.events,
        )
        second = self.sam("export", self.plan_argument())
        self.record(
            Check.EXPORT_UNCHANGED,
            key,
            f"a second export after the {wave} wave changes nothing",
            "unchanged",
            second.noop or ", ".join(second.events) or "nothing",
            second.noop == "unchanged",
        )

    # -- the runner's commands ---------------------------------------------

    def runner_attempt(self, task: str, attempt: int, marker: str | None = None) -> None:
        """Work one attempt the way ``docs/work-ledger/runner-contract.md`` sets out.

        Args:
            task: The task identifier.
            attempt: The attempt number, which is the runner's key.
            marker: A phrase the orchestrator's response must carry into a sent-back attempt's
                first read, or None when this attempt was not sent back.
        """
        key = ObservationKey(task=task, attempt=attempt)
        read = self.sam("read", self.address_argument(task), Argument(name="--attempt", value=str(attempt)))
        self.record_equal(Check.READ_RETURNS_TASK, key, f"read gives {task} its own row", task, str(read.task or ""))
        self.record_equal(
            Check.READ_IN_PROGRESS,
            key,
            f"read finds {task} in-progress",
            "in-progress",
            str(read.row.get("status") or ""),
        )
        if marker is not None:
            self.check_response(key, read, marker)
        renewed = self.sam("renew", self.address_argument(task), Argument(name="--attempt", value=str(attempt)))
        self.record(
            Check.RENEW_DEADLINE,
            key,
            f"renew prints the new deadline for {task}",
            "a renew_by instant",
            renewed.renew_by or "nothing",
            renewed.renew_by is not None,
        )
        for section in REPORT_SECTIONS:
            self.append_report_section(task, attempt, section)
        finished = self.sam(
            "finish",
            self.address_argument(task),
            Argument(name="--attempt", value=str(attempt)),
            Argument(name="--result", value="complete"),
        )
        self.record_equal(
            Check.FINISH_COMPLETE, key, f"finish completes {task}", "complete", str(finished.status or "")
        )

    def check_response(self, key: ObservationKey, read: CommandResult, marker: str) -> None:
        """Write down that a sent-back attempt's read is headed by the orchestrator's response.

        Args:
            key: Where in the loop these observations belong.
            read: What ``read`` returned for the sent-back attempt.
            marker: A phrase the judge's response carries.
        """
        names = tuple(str(section.get("name", "")) for section in read.sections)
        self.record_among(
            Check.READ_CARRIES_RESPONSE,
            key,
            f"read heads {key.task} with the orchestrator's response",
            RESPONSE_SECTION,
            names,
        )
        response = "\n".join(
            str(section.get("content", "")) for section in read.sections if section.get("name") == RESPONSE_SECTION
        )
        self.record(
            Check.READ_CARRIES_SEND_BACK_TEXT,
            key,
            "the response the judge sent reaches the next runner",
            marker,
            response or "nothing",
            marker in response,
        )

    def append_report_section(self, task: str, attempt: int, section: str) -> None:
        """Append one report section of one attempt from its fixture file.

        Args:
            task: The task identifier.
            attempt: The attempt number the section is tagged with.
            section: The section name.
        """
        content = self.fixtures.read("reports", task, f"attempt-{attempt}", section_file_name(section))
        result = self.sam(
            "update",
            self.plan_argument(),
            Argument(name="--task-id", value=task),
            Argument(name="--attempt", value=str(attempt)),
            Argument(name="--append-section", value=section),
            Argument(name="--section-content", value=content),
        )
        self.record_among(
            Check.SECTION_APPENDED,
            ObservationKey(task=task, attempt=attempt, section=section),
            f"update appends {section} to {task}",
            "task.section",
            result.events,
        )

    # -- the waves ----------------------------------------------------------

    def first_wave(self) -> None:
        """T1 and T2 have no dependencies, so one ``ready`` lists both and withholds T3."""
        self.check_ready(FIRST_WAVE, expected_count=2, lists=("T1", "T2"), withholds=("T3",))
        for task in ("T1", "T2"):
            attempt = self.dispatch_task(task, expected_attempt=1)
            self.runner_attempt(task, attempt)
            self.settle_task(task, attempt)
            self.accept_task(task, "every criterion met")
        self.export_plan(FIRST_WAVE)

    def second_wave(self) -> None:
        """Accepting T1 and T2 satisfies T3's dependencies, so T3 becomes the whole next wave."""
        self.check_ready(SECOND_WAVE, expected_count=1, lists=("T3",))
        attempt = self.dispatch_task("T3", expected_attempt=1)
        self.runner_attempt("T3", attempt)
        self.settle_task("T3", attempt)

    def send_back(self) -> None:
        """Judge row J2: T3 finished complete with its second acceptance criterion unmet."""
        reclaimed = self.sam(
            "reclaim",
            self.address_argument("T3"),
            Argument(name="--reason", value="judge"),
            Argument(name="--response", value=self.fixtures.read("responses", "T3", "attempt-2.md")),
        )
        self.record_equal(
            Check.RECLAIM_NOT_STARTED,
            ObservationKey(task="T3"),
            "reclaim returns T3 to not-started",
            "not-started",
            str(reclaimed.status or ""),
        )
        self.check_ready(SEND_BACK_WAVE, expected_count=None, lists=("T3",))
        attempt = self.dispatch_task("T3", expected_attempt=2)
        self.runner_attempt("T3", attempt, marker=SEND_BACK_MARKER)
        self.settle_task("T3", attempt)
        self.accept_task("T3", "the empty manifest now renders")
        self.export_plan(SEND_BACK_WAVE)

    def plan_progress(self) -> None:
        """Read the plan's own progress, which is where the loop ends."""
        result = self.sam("status", self.plan_argument())
        self.record_equal(
            Check.PLAN_PROGRESS_DONE,
            ObservationKey(),
            "the plan reports progress done",
            "done",
            str(result.fields.get("progress") or ""),
        )

    def run(self) -> LoopRecord:
        """Drive the whole loop once.

        Returns:
            Every command the loop issued and every observation it made.
        """
        self.build_plan()
        self.first_wave()
        self.second_wave()
        self.send_back()
        self.plan_progress()
        return LoopRecord(
            plan=self.plan, workspace=self.workspace, calls=tuple(self.calls), observations=tuple(self.observations)
        )


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------


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
