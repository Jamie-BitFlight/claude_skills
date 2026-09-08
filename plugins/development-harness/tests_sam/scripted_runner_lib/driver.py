"""The loop itself: the order ``work-loop.md`` and ``runner-contract.md`` put the commands in.

The plan driven here is ``tests_sam/fixtures/loop-plan/``: three tasks, T1 and T2 parallel and T3
dependent on both. T3's first attempt leaves its second acceptance criterion unmet, so the judge
sends it back with ``reclaim --response`` (work-loop.md row J2) and a second attempt finishes it.

Every command and flag this module issues is one ``dh_core/ledger_spec.py`` names, and none of the
values it duplicates from that specification are imported: the proof is that the CLI is enough, so
the runner may not reach into the package behind it.
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from tests_sam.scripted_runner_lib.errors import ScriptedRunnerError
from tests_sam.scripted_runner_lib.ledger_cli import Argument, CommandCall, CommandResult, LedgerCli
from tests_sam.scripted_runner_lib.observations import Check, LoopRecord, ObservationKey, ObservationLog
from tests_sam.scripted_runner_lib.workspace import Fixtures, Workspace

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
        self.log = ObservationLog()

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
        self.log.record(
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
        self.log.record_equal(
            Check.PLAN_FINALIZED,
            ObservationKey(),
            "finalize makes the plan ready",
            "ready",
            str(finalized.changed.get("state") or ""),
        )
        validated = self.sam("validate", self.plan_argument())
        self.log.record(
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
            self.log.record_equal(
                Check.READY_COUNT,
                ObservationKey(wave=wave),
                COUNT_EXPECTATIONS[wave],
                str(expected_count),
                "" if result.count is None else str(result.count),
            )
        for task in lists:
            self.log.record_among(
                Check.READY_LISTS,
                ObservationKey(wave=wave, task=task),
                LIST_EXPECTATIONS[wave].format(task=task),
                task,
                identifiers,
            )
        for task in withholds:
            self.log.record_absent(
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
        self.log.record(
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
        self.log.record_among(
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
        self.log.record_among(
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
        self.log.record(
            Check.EXPORT_WROTE,
            key,
            f"the {wave} export writes rather than reporting unchanged",
            "plan.exported",
            first.noop or ", ".join(first.events) or "nothing",
            first.noop is None and "plan.exported" in first.events,
        )
        second = self.sam("export", self.plan_argument())
        self.log.record(
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
        self.log.record_equal(
            Check.READ_RETURNS_TASK, key, f"read gives {task} its own row", task, str(read.task or "")
        )
        self.log.record_equal(
            Check.READ_IN_PROGRESS,
            key,
            f"read finds {task} in-progress",
            "in-progress",
            str(read.row.get("status") or ""),
        )
        if marker is not None:
            self.check_response(key, read, marker)
        renewed = self.sam("renew", self.address_argument(task), Argument(name="--attempt", value=str(attempt)))
        self.log.record(
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
        self.log.record_equal(
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
        self.log.record_among(
            Check.READ_CARRIES_RESPONSE,
            key,
            f"read heads {key.task} with the orchestrator's response",
            RESPONSE_SECTION,
            names,
        )
        response = "\n".join(
            str(section.get("content", "")) for section in read.sections if section.get("name") == RESPONSE_SECTION
        )
        self.log.record(
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
        self.log.record_among(
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
        self.log.record_equal(
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
        self.log.record_equal(
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
            plan=self.plan, workspace=self.workspace, calls=tuple(self.calls), observations=self.log.recorded
        )
