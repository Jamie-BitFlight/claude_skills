"""The work-failure vocabulary a Worker names when work could not proceed.

:data:`KNOWN_FAILURE_TYPES` is the table. It is the single source of truth for the vocabulary, and
every consumer of the table is Python -- the ``sam known-failure-types`` CLI command and the
``sam_known_failure_types`` MCP tool both import it -- so the table is Python: a literal tuple of
:class:`FailureTypeRow`, read by import rather than parsed out of a document
(``rules/data-format-selection.md``). It is deliberately extensible: a row is added when a failure
occurs that no existing row names.

Roles below are ``plugins/development-harness/CONTEXT.md``'s: Orchestrator, Manager, Worker,
Dispatcher, with Load, Dispatch and Delegate as the actions.

Boundary -- three vocabularies, one direction of flow
=====================================================

This vocabulary is **not** ``dh_core.ledger_spec.REASONS`` and **not** the ``reclaim --reason``
vocabulary. They answer three different questions, and merging any two of them loses the answer to
one of them.

* :data:`dh_core.ledger_spec.REASONS` -- why a **CLI command** refused, no-op'd, or recorded an
  outcome about a ledger row: ``leased``, ``not-ready``, ``stale-attempt``, ``archived``,
  ``attempts-exhausted``, ``report-missing``. Closed, owned by the state machine, printed by the
  command itself. No agent chooses one; the ledger does.
* ``reclaim --reason`` -- what the **Orchestrator** says when it sends a task back for another
  attempt (``dh_core.ledger_spec.COMMANDS``, the ``reclaim`` command). Free text today; a
  concurrent design proposes closing that vocabulary in ``ledger_spec.py``, derived by the existing
  ``dh_core.ledger.store.flag_vocabulary()`` the way ``FINISH_RESULTS`` already is. Owned by the
  Orchestrator.
* :data:`KNOWN_FAILURE_TYPES` (this module) -- what the **Worker** says about why the work could not
  proceed. Extensible, owned by the workflow rather than by the state machine.

The flow is one-directional and has exactly one step per party::

    Worker reports a failure type  ->  the router maps it to a route  ->  the Orchestrator records
    a reclaim --reason

Nothing flows the other way: a ``reclaim --reason`` never becomes a failure type, and a ``REASONS``
code never becomes either.

**The rule that keeps them apart:** if the ledger already refuses with a ``REASONS`` code for a
condition, an agent must not invent a failure type for the same condition -- the refusal is already
typed, already printed, and already routable. ``tests/test_known_failure_types.py`` enforces the
mechanical half of that rule: no code in this table collides with a ``REASONS`` code. The
conditions that are ledger refusals rather than failure types are named in
:data:`LEDGER_OWNED_CONDITIONS` so the boundary is data rather than an argument to re-run.

Why the category is a field and the code is derived
===================================================

:attr:`FailureTypeRow.category` is a :class:`FailureCategory` member and :attr:`FailureTypeRow.code`
is computed from it as ``f"{category}:{specific}"``. The alternative -- storing ``code`` as a string
and splitting the category back out of it -- leaves the category set open: a mistyped prefix mints a
new category with no error, and nothing can enumerate the categories without scanning the codes.
With the category typed, a row naming a category with no enum member fails at import, the prefix
and the category cannot disagree because there is only one of them, and the categories are
enumerable from the enum. This mirrors ``dh_core/artifact_registry.py``, where the typed
``artifact_type`` field removes a drift test rather than needing one.
"""

from __future__ import annotations

from collections import Counter
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, computed_field


class FailureCategory(StrEnum):
    """The namespace half of a failure code -- what kind of thing went wrong."""

    PRE_REQUISITES_MISSING = "pre-requisites-missing"
    """Something the step needed to exist before it started does not exist."""

    INPUT_UNUSABLE = "input-unusable"
    """The input exists and is well-formed, but cannot drive this step's work."""

    OUTPUT_UNUSABLE = "output-unusable"
    """The step ran and produced something a consumer cannot read or trust."""

    ENVIRONMENT = "environment"
    """The repository or host state blocks the work; a repair fixes it, a bare retry does not."""

    AUTHORITY = "authority"
    """The step is permitted neither the tool nor the decision the work requires."""

    RESOURCE = "resource"
    """A budget -- context, tokens, spend, rate, disk -- ran out."""

    LIVENESS = "liveness"
    """The step is running but not progressing."""

    CONTRADICTION = "contradiction"
    """Two results that must agree do not, or a later result invalidates an earlier one."""

    HUMAN_INPUT_REQUIRED = "human-input-required"
    """Only a person can supply what the step needs next."""


class RecoveryDisposition(StrEnum):
    """How a failure type can be recovered from, as one closed axis a router can key on.

    These are the repo owner's framing of recovery, kept as an enum rather than as prose inside
    :attr:`FailureTypeRow.description` so a router reads a value instead of parsing a sentence.
    """

    AUTOMATIC = "automatic"
    """Recoverable without anything outside the loop changing -- re-read, or re-run the step."""

    RETRY_TRANSIENT = "retry-transient"
    """Retryable like a timeout: the identical call may succeed with nothing changed."""

    MANUAL_FIX = "manual-fix"
    """Recoverable only after a repair step runs; a retry before the repair fails identically."""

    SYSTEM_ERROR = "system-error"
    """An error using a system the step requires; the step is not at fault and cannot repair it."""

    SURFACE_TO_USER = "surface-to-user"
    """Blocked in a way no agent can clear; it must reach a person."""

    KNOWN_PROCESS = "known-process"
    """Blocked, but a written procedure clears it without a person deciding anything."""

    UPSTREAM_DEPENDENCY = "upstream-dependency"
    """Blocked on work another agent must resolve before this step can requeue."""

    ASSETS_NOT_FOUND = "assets-not-found"
    """Blocked because expected assets, artifacts, reports or data were not found."""


class SuggestedRoute(BaseModel):
    """One path a router may take for a failure type. Suggestions, not a single hard route."""

    model_config = ConfigDict(frozen=True)

    action: str = Field(description="What the router should consider doing, as one imperative sentence.")
    source: str = Field(
        description=(
            "Where this suggestion came from, so a later reader can tell a derived route from an invented one: "
            "a scenario id from the failure-path design, or the statement that established it."
        )
    )


class FailureTypeRow(BaseModel):
    """One work-failure type an agent may name in its status report."""

    model_config = ConfigDict(frozen=True)

    category: FailureCategory = Field(description="The namespace half of the code.")
    specific: str = Field(
        pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$",
        description="The specific half of the code, in kebab case; joined to the category by a colon.",
    )
    description: str = Field(
        description="What condition this names, written for an agent choosing between failure types."
    )
    recovery: RecoveryDisposition = Field(description="How this failure type can be recovered from.")
    suggested_routes: tuple[SuggestedRoute, ...] = Field(
        default=(),
        description=(
            "Paths a router may take. Empty means no route is settled yet -- not that none exists. "
            "A row is left empty rather than filled with an invented route."
        ),
    )
    origin: str = Field(
        description=(
            "Where this row came from: a scenario id of the failure-path design for the "
            "`/dh:work-backlog-item work` chain, or `taxonomy:<class>` for a failure class that design "
            "does not observe."
        )
    )

    @computed_field(description="The namespaced failure code, `category:specific`.")
    @property
    def code(self) -> str:
        """Return the namespaced failure code.

        Returns:
            ``f"{category}:{specific}"`` -- the value an agent names in a status report.
        """
        return f"{self.category.value}:{self.specific}"


class KnownFailureTypesPage(BaseModel):
    """A window over :data:`KNOWN_FAILURE_TYPES`, with the totals a caller needs to page further."""

    model_config = ConfigDict(frozen=True)

    total: int = Field(description="How many failure types the table holds, before any windowing.")
    offset: int = Field(description="How many rows were skipped before this window.")
    returned: int = Field(description="How many rows this window holds.")
    failure_types: tuple[FailureTypeRow, ...] = Field(description="The rows in this window, in table order.")


KNOWN_FAILURE_TYPES: tuple[FailureTypeRow, ...] = (
    FailureTypeRow(
        category=FailureCategory.PRE_REQUISITES_MISSING,
        specific="expected-code-functionality-not-available-in-worktree",
        description=(
            "The step needs a named piece of code -- a type, class, function, endpoint, migration -- that the plan "
            "implies exists, and it is not in the worktree the step is running in. Nothing was read and found "
            "wanting, so this is not `input-unusable:*`; the worktree is operable, so this is not "
            "`environment:worktree-not-workable`. Its repair decomposes into reconciling this worktree with the "
            "branch prior tasks landed on and then re-checking for the symbol, so name the symbol looked for."
        ),
        recovery=RecoveryDisposition.UPSTREAM_DEPENDENCY,
        suggested_routes=(
            SuggestedRoute(
                action=(
                    "Reconcile the worktree with the work already landed: check the worktree exists and work can "
                    "continue, identify any unmerged work, merge it to the feature branch, rebase the task branch "
                    "on the feature branch, then re-check whether the named symbol now exists."
                ),
                source="repo owner's worked repair route for this code",
            ),
            SuggestedRoute(
                action="Check whether a prior task was supposed to create this functionality and did not.",
                source="repo owner's worked example for this code",
            ),
        ),
        origin="design:D13",
    ),
    FailureTypeRow(
        category=FailureCategory.PRE_REQUISITES_MISSING,
        specific="upstream-artifact-not-registered",
        description=(
            "An artifact this step must read -- a review verdict, an analysis document, a report -- has no entry to "
            "read. The producing step either never ran or never registered its output."
        ),
        recovery=RecoveryDisposition.ASSETS_NOT_FOUND,
        suggested_routes=(
            SuggestedRoute(
                action=(
                    "Send the producing task back for another attempt; never read the absence as a passing verdict."
                ),
                source="design:E2",
            ),
        ),
        origin="design:E2",
    ),
    FailureTypeRow(
        category=FailureCategory.PRE_REQUISITES_MISSING,
        specific="referenced-work-item-not-found",
        description=(
            "The selector, address or reference the step was given matches no work item. The lookup succeeded and "
            "returned nothing, as distinct from the lookup itself failing."
        ),
        recovery=RecoveryDisposition.ASSETS_NOT_FOUND,
        suggested_routes=(
            SuggestedRoute(
                action="Surface to the human with the candidates the selector did match, and stop this chain.",
                source="design:A1",
            ),
        ),
        origin="design:A1",
    ),
    FailureTypeRow(
        category=FailureCategory.PRE_REQUISITES_MISSING,
        specific="required-work-not-in-plan",
        description=(
            "The step found work that has to happen before its own can, and no task in the plan covers it -- an "
            "unresolved referent, an architectural defect, scope the sizing missed, a blocking review finding. The "
            "step records what it found; it does not extend the graph itself, which is a decomposer's authority."
        ),
        recovery=RecoveryDisposition.UPSTREAM_DEPENDENCY,
        origin="design:D13,D14,B8,C3,E1",
    ),
    FailureTypeRow(
        category=FailureCategory.PRE_REQUISITES_MISSING,
        specific="undeclared-upstream-task-incomplete",
        description=(
            "The step depends on another task in the plan that has not finished, and that dependency is not on its "
            "row. A declared, unmet dependency is not this: the ledger already refuses that dispatch with "
            "`not-ready`."
        ),
        recovery=RecoveryDisposition.UPSTREAM_DEPENDENCY,
        origin="design:D2,B6",
    ),
    FailureTypeRow(
        category=FailureCategory.INPUT_UNUSABLE,
        specific="target-in-terminal-state",
        description=(
            "The work item or task the step was to act on exists but is already closed, resolved or archived, so "
            "there is nothing for this step to do to it."
        ),
        recovery=RecoveryDisposition.SURFACE_TO_USER,
        suggested_routes=(
            SuggestedRoute(
                action="Surface to the human together with the evidence recorded when it was closed.",
                source="design:A3",
            ),
        ),
        origin="design:A3",
    ),
    FailureTypeRow(
        category=FailureCategory.INPUT_UNUSABLE,
        specific="under-specified",
        description=(
            "The input is present and well-formed but does not determine an action -- several are consistent with "
            "it. Softer than a missing input, and the case an agent is most likely to paper over by inventing the "
            "missing half. Report this instead of choosing."
        ),
        recovery=RecoveryDisposition.SURFACE_TO_USER,
        origin="taxonomy:contract-failures",
    ),
    FailureTypeRow(
        category=FailureCategory.INPUT_UNUSABLE,
        specific="belongs-to-a-different-subject",
        description=(
            "The input exists, parses, and is about something else -- another task, another item, another revision. "
            "Reading a gate-read artifact by type rather than by its `artifact_id` returns the newest document of "
            "that type rather than this step's, with no error anywhere."
        ),
        recovery=RecoveryDisposition.AUTOMATIC,
        origin="taxonomy:undetected",
    ),
    FailureTypeRow(
        category=FailureCategory.INPUT_UNUSABLE,
        specific="empty-or-absent-indistinguishable",
        description=(
            "A read returned nothing and the step cannot tell a legitimately empty result from having looked in the "
            "wrong place. Report this rather than treating the empty result as a fact about the world."
        ),
        recovery=RecoveryDisposition.KNOWN_PROCESS,
        origin="taxonomy:undetected",
    ),
    FailureTypeRow(
        category=FailureCategory.INPUT_UNUSABLE,
        specific="malformed",
        description=(
            "The input this step must consume does not parse, or parses into a shape the step cannot use. The "
            "producer has to re-emit it; re-reading the same bytes will not change the outcome."
        ),
        recovery=RecoveryDisposition.UPSTREAM_DEPENDENCY,
        origin="taxonomy:contract-failures",
    ),
    FailureTypeRow(
        category=FailureCategory.OUTPUT_UNUSABLE,
        specific="false-completion",
        description=(
            "A step reported success -- a DONE status, `finish --result complete` -- having produced nothing usable "
            "against its criteria. Named by whichever step detects it, never by the step that reported the success: "
            "the success channel is exactly what fails to carry this."
        ),
        recovery=RecoveryDisposition.AUTOMATIC,
        suggested_routes=(
            SuggestedRoute(
                action="Record the finding against the task and send that same task back for another attempt.",
                source="design:D5",
            ),
        ),
        origin="taxonomy:undetected",
    ),
    FailureTypeRow(
        category=FailureCategory.OUTPUT_UNUSABLE,
        specific="report-malformed",
        description=(
            "The step's own output exists but does not meet the shape its consumer reads -- an artifact with no "
            "STATUS line, prose where structured data was expected, a section under the wrong name. Distinct from an "
            "absent report section, which the ledger already refuses with `report-missing`."
        ),
        recovery=RecoveryDisposition.AUTOMATIC,
        origin="taxonomy:contract-failures",
    ),
    FailureTypeRow(
        category=FailureCategory.OUTPUT_UNUSABLE,
        specific="schema-drift",
        description=(
            "The step ran against a renamed field, a stale enum member or a moved key, succeeded on its own terms, "
            "and produced something no downstream consumer can read. The step and the consumer disagree about the "
            "schema, so neither one reports an error."
        ),
        recovery=RecoveryDisposition.MANUAL_FIX,
        origin="taxonomy:contract-failures",
    ),
    FailureTypeRow(
        category=FailureCategory.ENVIRONMENT,
        specific="required-system-unavailable",
        description=(
            "A system the step requires -- the configured backend, the forge, a network service -- could not be "
            "reached at all, or refused every call. Not a permission problem; see `authority:tool-or-scope-denied` "
            "for that."
        ),
        recovery=RecoveryDisposition.SYSTEM_ERROR,
        suggested_routes=(SuggestedRoute(action="Stop the chain and surface to the human.", source="design:A2"),),
        origin="design:A2",
    ),
    FailureTypeRow(
        category=FailureCategory.ENVIRONMENT,
        specific="required-system-timed-out",
        description=(
            "A system the step requires did not answer within its window. The identical call may succeed with "
            "nothing changed, which is what separates this from `required-system-unavailable` and from "
            "`resource:budget-exhausted`."
        ),
        recovery=RecoveryDisposition.RETRY_TRANSIENT,
        origin="taxonomy:owner-framing",
    ),
    FailureTypeRow(
        category=FailureCategory.ENVIRONMENT,
        specific="worktree-not-workable",
        description=(
            "The worktree itself cannot be operated on: uncommitted changes the step must not disturb, an "
            "unresolved merge conflict, a missing or diverged branch. The repair is to the worktree, whatever code "
            "it holds. When the worktree is operable and a specific symbol is simply absent, that is "
            "`pre-requisites-missing:expected-code-functionality-not-available-in-worktree` instead. A retry in the "
            "same state fails identically."
        ),
        recovery=RecoveryDisposition.MANUAL_FIX,
        origin="taxonomy:resource-and-authority",
    ),
    FailureTypeRow(
        category=FailureCategory.ENVIRONMENT,
        specific="dependency-not-installed",
        description=(
            "A tool, runtime or package the step must run is not installed or not on the path. Installing it is a "
            "repair step, not a retry."
        ),
        recovery=RecoveryDisposition.MANUAL_FIX,
        origin="taxonomy:resource-and-authority",
    ),
    FailureTypeRow(
        category=FailureCategory.AUTHORITY,
        specific="tool-or-scope-denied",
        description=(
            "A tool call was denied, a token lacked the scope, or a sandbox restriction blocked the operation. The "
            "step is capable of the work and is not permitted it."
        ),
        recovery=RecoveryDisposition.SURFACE_TO_USER,
        suggested_routes=(
            SuggestedRoute(
                action="Surface to the human without retrying; a denial is not transient and no upstream step clears it.",
                source="repo owner's failure taxonomy, resource-and-authority class",
            ),
        ),
        origin="taxonomy:resource-and-authority",
    ),
    FailureTypeRow(
        category=FailureCategory.RESOURCE,
        specific="budget-exhausted",
        description=(
            "A budget ran out: context window, token or spend allowance, rate limit, disk. Distinct from a timeout "
            "-- the same work retried unchanged exhausts the same budget again."
        ),
        recovery=RecoveryDisposition.SURFACE_TO_USER,
        suggested_routes=(
            SuggestedRoute(
                action="Split the work into smaller units rather than retrying it whole.",
                source="repo owner's failure taxonomy, resource-and-authority class",
            ),
            SuggestedRoute(
                action="Surface to the human so the budget can be raised.",
                source="repo owner's failure taxonomy, resource-and-authority class",
            ),
        ),
        origin="taxonomy:resource-and-authority",
    ),
    FailureTypeRow(
        category=FailureCategory.LIVENESS,
        specific="no-progress-loop",
        description=(
            "The step is running but not advancing: it retries the same failing operation, or exchanges the same "
            "question and answer with a peer, without the state changing between rounds."
        ),
        recovery=RecoveryDisposition.SURFACE_TO_USER,
        suggested_routes=(
            SuggestedRoute(
                action=(
                    "Let the task's attempt budget bound it, and surface to the human when the ledger reports "
                    "`attempts-exhausted`."
                ),
                source="design:D9",
            ),
        ),
        origin="taxonomy:concurrency-and-liveness",
    ),
    FailureTypeRow(
        category=FailureCategory.CONTRADICTION,
        specific="conflicting-verdicts",
        description=(
            "Two steps that must agree returned opposite verdicts on the same work -- a passing code review against "
            "a failing verification, two reviewers disagreeing on the same finding. Which verdict wins is not "
            "written anywhere, so the step must not pick one."
        ),
        recovery=RecoveryDisposition.SURFACE_TO_USER,
        origin="taxonomy:blast-radius",
    ),
    FailureTypeRow(
        category=FailureCategory.CONTRADICTION,
        specific="completed-work-invalidated",
        description=(
            "This step's finding makes work that already completed, and possibly was already accepted, wrong. The "
            "blast radius reaches beyond this step's own task, and nothing rolls the earlier work back on its own."
        ),
        recovery=RecoveryDisposition.SURFACE_TO_USER,
        origin="design:E4",
    ),
    FailureTypeRow(
        category=FailureCategory.HUMAN_INPUT_REQUIRED,
        specific="decision-outside-agent-authority",
        description=(
            "The step reached a decision only a person may make -- a product choice, a trade-off between stated "
            "goals, permission to do something destructive. Distinct from `input-unusable:under-specified`, where "
            "the input is merely incomplete."
        ),
        recovery=RecoveryDisposition.SURFACE_TO_USER,
        suggested_routes=(
            SuggestedRoute(
                action="Surface the question to the human, then resume this same task once the answer is recorded.",
                source="design:D3",
            ),
        ),
        origin="design:D3",
    ),
    FailureTypeRow(
        category=FailureCategory.HUMAN_INPUT_REQUIRED,
        specific="answer-not-received",
        description=(
            "The step is blocked awaiting an answer a person was asked for, and the answer has not arrived. The "
            "question was delivered; nothing is wrong except that the wait has no end."
        ),
        recovery=RecoveryDisposition.SURFACE_TO_USER,
        origin="taxonomy:blast-radius",
    ),
)


LEDGER_OWNED_CONDITIONS: tuple[tuple[str, str], ...] = (
    ("dispatch refused because another attempt holds the lease", "leased"),
    ("dispatch refused because a declared dependency or conflict group is unmet", "not-ready"),
    ("a command arrived from a superseded attempt, including a task claimed by a newer one", "stale-attempt"),
    ("the plan is archived, so no command may act on it", "archived"),
    ("the attempt budget is spent", "attempts-exhausted"),
    ("a report section has no row at the current attempt", "report-missing"),
    ("acceptance is asked of a task that is not complete", "not-complete"),
    ("the ledger database sits on a filesystem WAL mode cannot share", "network-filesystem"),
)
"""Conditions the ledger already refuses with a :data:`dh_core.ledger_spec.REASONS` code, paired with
that code. An agent must not invent a failure type for any of them: the refusal is already typed and
already routable. Kept as data so the boundary is checkable rather than an argument to re-run --
``tests/test_known_failure_types.py`` asserts each named code is a real ``REASONS`` code, and that no
failure code collides with one."""


def _check_codes_unique() -> None:
    """Fail at import when two rows share a code.

    Raises:
        ValueError: When :data:`KNOWN_FAILURE_TYPES` holds two rows with the same code.
    """
    counts = Counter(row.code for row in KNOWN_FAILURE_TYPES)
    duplicates = sorted(code for code, count in counts.items() if count > 1)
    if duplicates:
        msg = f"KNOWN_FAILURE_TYPES holds duplicate codes: {', '.join(duplicates)}"
        raise ValueError(msg)


_check_codes_unique()


def failure_type(code: str) -> FailureTypeRow | None:
    """Return the row a code names.

    Args:
        code: A namespaced failure code, ``category:specific``.

    Returns:
        The matching :class:`FailureTypeRow`, or ``None`` when the table holds no such code.
    """
    return next((row for row in KNOWN_FAILURE_TYPES if row.code == code), None)


def page(offset: int = 0, limit: int | None = None) -> KnownFailureTypesPage:
    """Return a window over the table, and the total it was taken from.

    The whole table is the default: ``page()`` returns every row. A window is taken only when the
    caller asks for one, and the result always carries ``total`` so a caller reading a window knows
    what it is a window of.

    Args:
        offset: How many rows to skip. Must not be negative.
        limit: How many rows to return at most. ``None`` (the default) returns every remaining row.
            Must not be negative when given.

    Returns:
        A :class:`KnownFailureTypesPage` holding the window and the table's total row count.

    Raises:
        ValueError: When ``offset`` is negative, or ``limit`` is given and negative.
    """
    if offset < 0:
        msg = f"offset must not be negative, got {offset}"
        raise ValueError(msg)
    if limit is not None and limit < 0:
        msg = f"limit must not be negative, got {limit}"
        raise ValueError(msg)
    end = len(KNOWN_FAILURE_TYPES) if limit is None else offset + limit
    window = KNOWN_FAILURE_TYPES[offset:end]
    return KnownFailureTypesPage(
        total=len(KNOWN_FAILURE_TYPES), offset=offset, returned=len(window), failure_types=window
    )


__all__ = [
    "KNOWN_FAILURE_TYPES",
    "LEDGER_OWNED_CONDITIONS",
    "FailureCategory",
    "FailureTypeRow",
    "KnownFailureTypesPage",
    "RecoveryDisposition",
    "SuggestedRoute",
    "failure_type",
    "page",
]
