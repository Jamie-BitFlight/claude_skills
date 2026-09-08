"""What the loop watched: the named behaviours, what each expected, and what it saw.

The runner records rather than asserts. Every behaviour the loop is supposed to show becomes an
:class:`Observation` carrying what was expected and what was observed, keyed by a :class:`Check` and
by the task, attempt, wave or report section it belongs to, so a regression names the step that
broke instead of reporting an exit status.
"""

from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum

from pydantic import BaseModel

from tests_sam.scripted_runner_lib.ledger_cli import CommandCall
from tests_sam.scripted_runner_lib.workspace import Workspace


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


class ObservationLog:
    """Writes down what each check expected and what the loop saw, in the order it saw it.

    The loop's job is to drive the commands; deciding whether what came back agrees with what the
    step promised is this class's, which is why every comparison the loop makes is one of the four
    shapes below rather than an inline assertion.
    """

    def __init__(self) -> None:
        """Start an empty log."""
        self.entries: list[Observation] = []

    @property
    def recorded(self) -> tuple[Observation, ...]:
        """Return every observation written down so far, in the order the loop made it."""
        return tuple(self.entries)

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
        self.entries.append(
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
