"""The scripted runner: the whole work loop driven by the ``sam plan`` CLI and nothing else.

``scripted_runner.py`` is the cross-harness proof that a runner needs only the ability to run a
command, read a file and write a file. It builds the ``fixtures/loop-plan`` plan — T1 and T2
parallel, T3 behind both — dispatches each task, works it the way
``docs/work-ledger/runner-contract.md`` sets out, judges it the way ``docs/work-ledger/work-loop.md``
sets out, sends T3 back once with ``reclaim --response`` because its first attempt left an
acceptance criterion unmet, and finishes with the plan reporting progress ``done``.

The runner does not assert; it *records*. Every behaviour the loop is supposed to show is written
down as an :class:`~tests_sam.scripted_runner.Observation` carrying what was expected and what was
observed, keyed by a :class:`~tests_sam.scripted_runner.Check` and by the task, attempt, wave or
report section it belongs to. That is what lets a regression here name the step that broke instead
of reporting an exit status. ``report()`` still returns a non-zero status when any observation is
unsatisfied, so a human running the script by hand gets a verdict rather than a listing.

Three tests read the script rather than run it: one holds it to the canonical PEP 723 shebang, one
proves it never imports the package it drives, and one proves it names no construct that would tie
it to POSIX. A handful more hold the preconditions the run refuses to start without — the toolchain,
the CLI, the base commit, the fixture files and the state root that keeps a hand run off any real
ledger. The rest drive the loop once, in a session-scoped fixture, and assert the recorded
observations one by one. Three more hold every command and flag the loop actually issued against
``dh_core.ledger_spec.COMMANDS`` and ``RETIRED_COMMANDS``, so the proof cannot quietly start
depending on a surface the specification does not name.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest
from dh_core import ledger_spec

from tests_sam import scripted_runner
from tests_sam.scripted_runner import Check, LoopRecord, Observation, Preparation

pytestmark = pytest.mark.xdist_group("scripted-runner")
"""Every test here shares one run of the loop, so they must share one xdist worker."""

CANONICAL_SHEBANG = "#!/usr/bin/env -S uv run --quiet --script"
"""``rules/script-invocation.md``: the only shebang a PEP 723 script in this repository carries."""

DRIVEN_PACKAGE_IMPORT = re.compile(r"^\s*(?:from|import)\s+(?:dh_core|sam_schema)\b", re.MULTILINE)
"""An import of the very package the runner exists to drive from the outside."""

PLATFORM_BOUND_CONSTRUCTS: dict[str, re.Pattern[str]] = {
    "a shell parses its command line": re.compile(r"shell\s*=\s*True"),
    "a command runs through os.system": re.compile(r"\bos\.system\("),
    "a command runs through a shell helper": re.compile(r"\bsubprocess\.get(?:status)?output\("),
    "a POSIX interpreter or absolute path is named": re.compile(
        r"""["']/(?:bin|usr|tmp|etc|var)/|["'](?:sh|bash)["']"""
    ),
    "a POSIX-only child hook is passed": re.compile(r"\bpreexec_fn\b|\bos\.setsid\b|\bos\.fork\b"),
    "a POSIX signal or process group is used": re.compile(r"\bsignal\.SIG|\bos\.kill(?:pg)?\("),
    "correctness rests on a permission bit": re.compile(r"\.chmod\(|\bos\.access\("),
    "a path is built by hand rather than by pathlib": re.compile(r"\bos\.path\.join\("),
}
"""Constructs that would tie the runner to POSIX, each named the way its failure would read.

The shebang line is exempt: it is inert on Windows, where the script is run through ``uv run``, and
``rules/script-invocation.md`` requires it verbatim. Every pattern below is checked against the rest
of the source.
"""

FIRST_WAVE = "first"
SECOND_WAVE = "second"
SEND_BACK_WAVE = "send-back"

RUNNER_ATTEMPTS: tuple[tuple[str, int], ...] = (("T1", 1), ("T2", 1), ("T3", 1), ("T3", 2))
"""Every (task, attempt) pair the loop works, in the order the loop reaches them."""

ATTEMPT_IDS: tuple[str, ...] = tuple(f"{task}-attempt-{attempt}" for task, attempt in RUNNER_ATTEMPTS)
"""Readable parametrisation ids for :data:`RUNNER_ATTEMPTS`."""

SECTION_APPENDS: tuple[tuple[str, int, str], ...] = tuple(
    (task, attempt, section) for task, attempt in RUNNER_ATTEMPTS for section in ledger_spec.REPORT_SECTIONS
)
"""Every report section the loop appends, as (task, attempt, section name)."""

SECTION_IDS: tuple[str, ...] = tuple(
    f"{task}-attempt-{attempt}-{section.lower().replace(' ', '-')}" for task, attempt, section in SECTION_APPENDS
)
"""Readable parametrisation ids for :data:`SECTION_APPENDS`."""

EXPORTED_WAVES: tuple[str, ...] = (FIRST_WAVE, SEND_BACK_WAVE)
"""The wave ends ``docs/work-ledger/work-loop.md`` "Export" projects the plan at."""

LOOP_COMMANDS: frozenset[str] = frozenset({
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
    "export",
    "status",
})
"""The commands the whole loop needs, from ``create`` through the send-back to ``status``."""


# ---------------------------------------------------------------------------
# The one run every behavioural test reads
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def loop_record(tmp_path_factory: pytest.TempPathFactory) -> LoopRecord:
    """Drive the whole work loop once and return what it recorded.

    Returns:
        The record of every command the loop issued and every observation it made.
    """
    work_dir = tmp_path_factory.mktemp("scripted-runner")
    return scripted_runner.run_loop(work_dir)


@pytest.fixture
def preparation(tmp_path: Path) -> Preparation:
    """Resolve the toolchain and lay out a state root under one test's own directory.

    Returns:
        What the runner resolves before it issues a single command.
    """
    return scripted_runner.prepare_workspace(tmp_path)


def assert_satisfied(observation: Observation) -> None:
    """Fail with the observation's own wording when it is unsatisfied.

    Args:
        observation: The recorded observation to hold.
    """
    assert observation.satisfied, (
        f"{observation.check.value}: {observation.expectation}; "
        f"expected {observation.expected!r}, observed {observation.observed!r}"
    )


# ---------------------------------------------------------------------------
# The runner as an artefact: a PEP 723 script that drives the CLI from outside
# ---------------------------------------------------------------------------


def test_the_runner_is_a_pep723_script_runnable_by_hand() -> None:
    """The runner carries the canonical shebang, a PEP 723 block, and the executable bit."""
    source = scripted_runner.SOURCE_PATH.read_text(encoding="utf-8")

    assert source.startswith(f"{CANONICAL_SHEBANG}\n"), "the runner does not carry the canonical PEP 723 shebang"
    assert "# /// script" in source, "the runner declares no PEP 723 metadata block"
    if os.name == "posix":
        assert os.access(scripted_runner.SOURCE_PATH, os.X_OK), f"{scripted_runner.SOURCE_PATH} is not executable"


def test_the_runner_never_imports_the_package_it_drives() -> None:
    """The proof is that the CLI is enough, so the runner may not reach the package behind it."""
    source = scripted_runner.SOURCE_PATH.read_text(encoding="utf-8")

    found = DRIVEN_PACKAGE_IMPORT.findall(source)

    assert not found, f"the runner imports the package it is meant to drive as a subprocess: {found}"


def test_the_runner_names_no_construct_that_would_tie_it_to_posix() -> None:
    """The runner must run on Windows, so nothing below the shebang may assume a POSIX host."""
    shebang, _, body = scripted_runner.SOURCE_PATH.read_text(encoding="utf-8").partition("\n")

    found = sorted(reason for reason, pattern in PLATFORM_BOUND_CONSTRUCTS.items() if pattern.search(body))

    assert shebang == CANONICAL_SHEBANG, "the exempted first line is not the shebang"
    assert not found, f"the runner will not run on Windows: {found}"


def test_the_loop_plan_fixture_the_runner_reads_is_on_disk() -> None:
    """The artefact is the script and the plan it drives; neither is a proof without the other."""
    assert scripted_runner.FIXTURE_DIRECTORY.is_dir(), f"no loop-plan fixture at {scripted_runner.FIXTURE_DIRECTORY}"
    assert (scripted_runner.FIXTURE_DIRECTORY / "responses" / "T3" / "attempt-2.md").is_file(), (
        "the fixture holds no send-back response, so the loop's distinctive step cannot run"
    )


def test_a_missing_fixture_stops_the_run_rather_than_reading_as_empty_text() -> None:
    """An absent field file must not reach the ledger as an empty acceptance criterion."""
    fixtures = scripted_runner.Fixtures(scripted_runner.FIXTURE_DIRECTORY / "no-such-plan")

    with pytest.raises(scripted_runner.FixtureMissingError) as raised:
        fixtures.read("tasks", "T1", "title.txt")

    assert "tasks/T1/title.txt" in str(raised.value)


# ---------------------------------------------------------------------------
# What the run refuses to start without
# ---------------------------------------------------------------------------


def test_a_program_the_run_needs_is_named_when_path_does_not_hold_it() -> None:
    """``uv`` resolves the CLI's dependencies and ``git`` names the base commit; neither is optional."""
    with pytest.raises(scripted_runner.ToolchainMissingError) as raised:
        scripted_runner.resolve_program("dh-no-such-program", "the plan needs a base commit for --base-sha")

    assert "dh-no-such-program" in str(raised.value)
    assert "--base-sha" in str(raised.value)


def test_a_checkout_without_the_cli_stops_the_run(tmp_path: Path) -> None:
    """The runner drives ``sam_schema/cli.py``, so a checkout lacking it has nothing to prove."""
    with pytest.raises(scripted_runner.ScriptedRunnerError) as raised:
        scripted_runner.prepare_workspace(tmp_path / "work", plugin_root=tmp_path / "not-a-plugin")

    assert "cli.py" in str(raised.value)


def test_the_run_records_the_checkouts_head_as_the_plans_base_sha(preparation: Preparation) -> None:
    """``create --base-sha`` records the commit a judge diffs a report against."""
    assert re.fullmatch(r"[0-9a-f]{40}", preparation.toolchain.base_sha), (
        f"the run resolved no base commit: {preparation.toolchain.base_sha!r}"
    )


def test_the_run_reaches_no_network_no_shared_store_and_no_credentials(
    preparation: Preparation, tmp_path: Path
) -> None:
    """The state root is the run's own and the backlog backend is local, so a hand run stays offline."""
    environment = preparation.workspace.environment

    assert environment["BACKLOG_BACKEND"] == "sqlite", "export would write through the default GitHub backend"
    assert environment["DH_STATE_HOME"] == str(preparation.workspace.state_home)
    assert preparation.workspace.state_home.is_relative_to(tmp_path)
    assert (Path(environment["DH_PROJECT_ROOT"]) / ".git").exists(), "DH_PROJECT_ROOT names no repository"


def test_a_non_zero_exit_carries_the_command_its_status_and_both_streams() -> None:
    """Every refusal and no-op code is unexpected on this path, so a non-zero exit stops the run loudly."""
    result = scripted_runner.CommandResult(
        call=scripted_runner.CommandCall(command="accept", flags=("--address", "--note"), address="P0/T1"),
        exit_code=3,
        stdout="what it printed",
        stderr="why it refused",
    )

    message = str(scripted_runner.LedgerCommandError(result))

    assert "accept" in message
    assert "--address" in message
    assert "3" in message
    assert "what it printed" in message
    assert "why it refused" in message


def test_a_command_that_does_not_finish_stops_the_run_by_name(preparation: Preparation) -> None:
    """A hung command reaches the same surface as every other failure, not a traceback."""
    cli = scripted_runner.LedgerCli(preparation.toolchain, preparation.workspace.environment, timeout_seconds=0)

    with pytest.raises(scripted_runner.CommandTimeoutError) as raised:
        cli.run("status", (scripted_runner.Argument(name="--plan-address", value="P0"),))

    assert "status" in str(raised.value)
    assert "--plan-address" in str(raised.value)


# ---------------------------------------------------------------------------
# Building the plan
# ---------------------------------------------------------------------------


def test_create_prints_a_plan_id(loop_record: LoopRecord) -> None:
    """``create`` writes the ledger plan every later command names."""
    assert_satisfied(loop_record.observation(Check.PLAN_CREATED))
    assert loop_record.plan, "the loop recorded no plan id"


def test_finalize_makes_the_plan_ready(loop_record: LoopRecord) -> None:
    """``finalize`` moves the plan out of drafting, which is what makes it dispatchable."""
    assert_satisfied(loop_record.observation(Check.PLAN_FINALIZED))


def test_validate_finds_nothing_structural(loop_record: LoopRecord) -> None:
    """``validate`` reports no finding on the plan the fixture describes."""
    assert_satisfied(loop_record.observation(Check.PLAN_VALIDATES_CLEAN))


# ---------------------------------------------------------------------------
# The waves: what ready lists and what it withholds
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("wave", "count"), [(FIRST_WAVE, 2), (SECOND_WAVE, 1)], ids=[FIRST_WAVE, SECOND_WAVE])
def test_ready_holds_the_wave_it_should(loop_record: LoopRecord, wave: str, count: int) -> None:
    """The first wave is T1 and T2; accepting both makes the second wave T3 alone."""
    assert_satisfied(loop_record.observation(Check.READY_COUNT, wave=wave))
    assert loop_record.observation(Check.READY_COUNT, wave=wave).expected == str(count)


@pytest.mark.parametrize("task", ["T1", "T2"])
def test_the_first_wave_lists_both_parallel_tasks(loop_record: LoopRecord, task: str) -> None:
    """T1 and T2 have no dependencies, so one ``ready`` lists both."""
    assert_satisfied(loop_record.observation(Check.READY_LISTS, wave=FIRST_WAVE, task=task))


def test_the_first_wave_withholds_the_dependent_task(loop_record: LoopRecord) -> None:
    """T3 depends on T1 and T2, so the first wave must not offer it."""
    assert_satisfied(loop_record.observation(Check.READY_WITHHOLDS, wave=FIRST_WAVE, task="T3"))


def test_the_second_wave_lists_the_dependent_task(loop_record: LoopRecord) -> None:
    """Accepting T1 and T2 satisfies T3's dependencies, so T3 becomes the whole next wave."""
    assert_satisfied(loop_record.observation(Check.READY_LISTS, wave=SECOND_WAVE, task="T3"))


def test_the_send_back_makes_the_dependent_task_ready_again(loop_record: LoopRecord) -> None:
    """``reclaim`` returns T3 to the dispatchable set rather than leaving it held."""
    assert_satisfied(loop_record.observation(Check.READY_LISTS, wave=SEND_BACK_WAVE, task="T3"))


# ---------------------------------------------------------------------------
# One attempt: dispatch, read, renew, the two report sections, finish
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("task", "attempt"), RUNNER_ATTEMPTS, ids=ATTEMPT_IDS)
def test_dispatch_prints_the_attempt_number(loop_record: LoopRecord, task: str, attempt: int) -> None:
    """``dispatch`` opens the attempt and prints its number, which is the runner's key."""
    observation = loop_record.observation(Check.DISPATCH_ATTEMPT, task=task, attempt=attempt)

    assert_satisfied(observation)
    assert observation.observed == str(attempt)


@pytest.mark.parametrize(("task", "attempt"), RUNNER_ATTEMPTS, ids=ATTEMPT_IDS)
def test_read_returns_the_tasks_own_row(loop_record: LoopRecord, task: str, attempt: int) -> None:
    """A runner's first command reads its own task, not the plan and not a sibling."""
    assert_satisfied(loop_record.observation(Check.READ_RETURNS_TASK, task=task, attempt=attempt))


@pytest.mark.parametrize(("task", "attempt"), RUNNER_ATTEMPTS, ids=ATTEMPT_IDS)
def test_read_finds_the_task_in_progress(loop_record: LoopRecord, task: str, attempt: int) -> None:
    """A dispatched attempt is in-progress until its ``finish``."""
    assert_satisfied(loop_record.observation(Check.READ_IN_PROGRESS, task=task, attempt=attempt))


def test_read_heads_the_second_attempt_with_the_orchestrator_response(loop_record: LoopRecord) -> None:
    """``read`` renders ``ledger_spec.RESPONSE_SECTION`` above the sent-back attempt's own sections."""
    observation = loop_record.observation(Check.READ_CARRIES_RESPONSE, task="T3", attempt=2)

    assert_satisfied(observation)
    assert observation.expected == ledger_spec.RESPONSE_SECTION


def test_the_send_back_text_reaches_the_next_attempt(loop_record: LoopRecord) -> None:
    """The judge's ``--response`` is what the next runner reads first, not merely a stored note."""
    observation = loop_record.observation(Check.READ_CARRIES_SEND_BACK_TEXT, task="T3", attempt=2)

    assert_satisfied(observation)
    assert observation.expected == scripted_runner.SEND_BACK_MARKER


@pytest.mark.parametrize(("task", "attempt"), RUNNER_ATTEMPTS, ids=ATTEMPT_IDS)
def test_renew_prints_a_new_deadline(loop_record: LoopRecord, task: str, attempt: int) -> None:
    """``renew`` is how a runner keeps a lease past a long step, so it must report the new deadline."""
    assert_satisfied(loop_record.observation(Check.RENEW_DEADLINE, task=task, attempt=attempt))


@pytest.mark.parametrize(("task", "attempt", "section"), SECTION_APPENDS, ids=SECTION_IDS)
def test_appending_a_report_section_emits_a_task_section_event(
    loop_record: LoopRecord, task: str, attempt: int, section: str
) -> None:
    """Both report sections of every attempt are appended, each tagged with its attempt."""
    assert_satisfied(loop_record.observation(Check.SECTION_APPENDED, task=task, attempt=attempt, section=section))


@pytest.mark.parametrize(("task", "attempt"), RUNNER_ATTEMPTS, ids=ATTEMPT_IDS)
def test_finish_completes_the_task(loop_record: LoopRecord, task: str, attempt: int) -> None:
    """``finish --result complete`` is the runner's last ledger command and leaves the task complete."""
    assert_satisfied(loop_record.observation(Check.FINISH_COMPLETE, task=task, attempt=attempt))


# ---------------------------------------------------------------------------
# The orchestrator's side: settle, accept, the send-back
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("task", "attempt"), RUNNER_ATTEMPTS, ids=ATTEMPT_IDS)
def test_settle_records_what_the_launch_returned(loop_record: LoopRecord, task: str, attempt: int) -> None:
    """``settle`` records the launch's return text before the judge reads the row."""
    assert_satisfied(loop_record.observation(Check.SETTLE_RECORDED, task=task, attempt=attempt))


@pytest.mark.parametrize("task", ["T1", "T2", "T3"])
def test_accept_records_the_task(loop_record: LoopRecord, task: str) -> None:
    """Judge row J1: every criterion met and every verification step passed."""
    assert_satisfied(loop_record.observation(Check.ACCEPT_RECORDED, task=task))


def test_reclaim_returns_the_task_to_not_started(loop_record: LoopRecord) -> None:
    """Judge row J2: the send-back reopens T3 rather than failing it."""
    assert_satisfied(loop_record.observation(Check.RECLAIM_NOT_STARTED, task="T3"))


def test_the_send_back_falls_between_the_two_dispatches_of_the_dependent_task(loop_record: LoopRecord) -> None:
    """``reclaim`` is what makes the second attempt possible, so it must sit between the dispatches."""
    dispatch_positions = [
        position
        for position, call in enumerate(loop_record.calls)
        if call.command == "dispatch" and call.address == f"{loop_record.plan}/T3"
    ]
    reclaim_positions = [position for position, call in enumerate(loop_record.calls) if call.command == "reclaim"]

    assert len(dispatch_positions) == 2, f"T3 was dispatched {len(dispatch_positions)} times, not twice"
    assert len(reclaim_positions) == 1, f"the loop reclaimed {len(reclaim_positions)} times, not once"
    assert dispatch_positions[0] < reclaim_positions[0] < dispatch_positions[1]


# ---------------------------------------------------------------------------
# Export and the end of the plan
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("wave", EXPORTED_WAVES)
def test_the_wave_end_export_writes(loop_record: LoopRecord, wave: str) -> None:
    """The first ``export`` of a wave end projects the plan rather than reporting a no-op."""
    assert_satisfied(loop_record.observation(Check.EXPORT_WROTE, wave=wave))


@pytest.mark.parametrize("wave", EXPORTED_WAVES)
def test_an_immediate_second_export_reports_unchanged(loop_record: LoopRecord, wave: str) -> None:
    """A second ``export`` with no new events is the ``unchanged`` no-op: the hash decides, not the count."""
    observation = loop_record.observation(Check.EXPORT_UNCHANGED, wave=wave)

    assert_satisfied(observation)
    assert observation.expected == "unchanged"


def test_the_plan_ends_at_progress_done(loop_record: LoopRecord) -> None:
    """The loop runs until ``status`` reports plan progress ``done``, which is the whole verdict."""
    assert_satisfied(loop_record.observation(Check.PLAN_PROGRESS_DONE))


def test_the_loop_records_no_unsatisfied_observation(loop_record: LoopRecord) -> None:
    """Nothing the loop watched came out wrong, including anything the tests above do not name."""
    failures = [f"{item.check.value}({item.label}): {item.expectation}" for item in loop_record.failures]

    assert not failures, f"the loop recorded unsatisfied observations: {failures}"


def test_a_clean_run_ends_by_naming_the_plan_that_reached_progress_done(
    loop_record: LoopRecord, capsys: pytest.CaptureFixture[str]
) -> None:
    """The one line a hand run prints on success names the plan, so the ledger can be inspected after."""
    status = scripted_runner.report(loop_record)

    assert status == 0
    assert capsys.readouterr().out.strip() == f"scripted-runner: plan {loop_record.plan} reached progress done"


def test_an_unsatisfied_observation_fails_the_run_and_names_the_step_that_broke(
    loop_record: LoopRecord, capsys: pytest.CaptureFixture[str]
) -> None:
    """Recording rather than asserting is only worth it if the verdict still names the broken step."""
    broken = loop_record.observations[0].model_copy(update={"satisfied": False})
    record = loop_record.model_copy(update={"observations": (broken, *loop_record.observations[1:])})

    status = scripted_runner.report(record)

    assert status == 1
    captured = capsys.readouterr()
    assert broken.check.value in captured.err
    assert broken.expectation in captured.err
    assert "reached progress done" not in captured.out


# ---------------------------------------------------------------------------
# The surface: only what ledger_spec.COMMANDS names
# ---------------------------------------------------------------------------


def test_the_runner_calls_only_commands_the_specification_names(loop_record: LoopRecord) -> None:
    """Every command the loop issued is a ``ledger_spec.COMMANDS`` entry."""
    declared = {command.name for command in ledger_spec.COMMANDS}
    called = {call.command for call in loop_record.calls}

    assert called, "the loop recorded no CLI calls"
    assert called <= declared, f"the loop calls commands the specification does not name: {sorted(called - declared)}"


def test_every_flag_the_runner_passes_is_one_its_command_declares(loop_record: LoopRecord) -> None:
    """Every flag the loop passed is one the command it passed it to declares."""
    declared = {command.name: {flag.name for flag in command.flags} for command in ledger_spec.COMMANDS}

    undeclared = {
        call.command: sorted(set(call.flags) - declared.get(call.command, set()))
        for call in loop_record.calls
        if set(call.flags) - declared.get(call.command, set())
    }

    assert not undeclared, f"the loop passes flags the specification does not name: {undeclared}"


def test_the_runner_calls_no_retired_command(loop_record: LoopRecord) -> None:
    """``ledger_spec.RETIRED_COMMANDS`` names surfaces the ledger withdrew; the proof may not use one."""
    called = {call.command for call in loop_record.calls}
    retired = called & set(ledger_spec.RETIRED_COMMANDS)

    assert not retired, f"the loop calls retired commands: {sorted(retired)}"


def test_the_runner_drives_every_command_the_loop_needs(loop_record: LoopRecord) -> None:
    """The loop runs the whole surface, from ``create`` through the send-back to ``status``."""
    called = {call.command for call in loop_record.calls}

    assert called >= LOOP_COMMANDS, f"the loop never runs {sorted(LOOP_COMMANDS - called)}"


# ---------------------------------------------------------------------------
# The workspace: a hand run touches no real ledger
# ---------------------------------------------------------------------------


def test_the_loop_writes_nothing_outside_the_work_directory(tmp_path: Path, loop_record: LoopRecord) -> None:
    """The run's state root is its own, so running the proof by hand cannot reach a real ledger."""
    assert loop_record.workspace.state_home.is_dir()
    assert tmp_path not in loop_record.workspace.state_home.parents
    assert loop_record.workspace.root in loop_record.workspace.state_home.parents
