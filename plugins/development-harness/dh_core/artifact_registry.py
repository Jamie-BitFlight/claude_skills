"""The artifact-type registry this plugin declares: which agent may register which artifact type.

:data:`REGISTRY` is the registry. It is the single source of truth for the map, and every consumer
of the map is Python, so the map is Python: a literal tuple of :class:`ArtifactTypeRow`, read by
import rather than parsed out of a document. ``docs/artifact-registry.md`` states the rules that
govern the map and names this module as where the map lives; it holds no copy of it.

Every ``artifact_register`` call -- MCP tool or ``artifact register`` CLI -- must match a row's
``(artifact_type, agents)`` pair, and :attr:`ArtifactTypeRow.gate_read` marks the types whose read
decides a workflow branch. :mod:`dh_core.workflow_multigraph.decomposition_gate` resolves an
``ARTIFACT`` referent against :data:`ARTIFACT_TYPES` -- ``plugins/development-harness/ARCHITECTURE.md``,
"The work graph" § "The decomposition-exit gate", Tier 1: an ``ARTIFACT`` referent resolves to "a
type in the artifact registry, with its id".

:attr:`ArtifactTypeRow.artifact_type` is a :class:`~backlog_core.models.ArtifactType` member rather
than a string, and two rules follow from that type alone, needing no test to hold them:

* a row naming a type with no enum member fails at import, so the registry can never declare a type
  the manifest parse would silently drop (``backlog_core/artifact_registry.py`` resolves a stored
  type through ``ArtifactType(...)`` and drops the row when that raises);
* the enum is the wider vocabulary and the registry is the subset an agent may register, so a
  member absent from :data:`REGISTRY` is written by the harness rather than by an agent -- today
  ``task-plan``, written by SAM's plan store.

A third rule holds the same way, over :attr:`ArtifactTypeRow.gate_read` rather than over
``artifact_type``: a row with `gate_read=True` naming other than exactly one registering agent
fails at import, because ``artifact_read`` without an ``artifact_id`` resolves the newest entry for
a type and a second writer would silently win the read a gate branches on. See
:meth:`ArtifactTypeRow._gate_read_type_has_exactly_one_agent` for the check and its rationale.
"""

from __future__ import annotations

from backlog_core.models import ArtifactType
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ArtifactTypeRow(BaseModel):
    """One artifact type, the writers permitted to register it, and whether a gate reads it."""

    model_config = ConfigDict(frozen=True)

    artifact_type: ArtifactType = Field(description="The type an artifact_register call passes, as its enum member.")
    agents: frozenset[str] = Field(
        default_factory=frozenset, description="The writers this row permits, as the `agent` argument's values."
    )
    gate_read: bool = Field(default=False, description="Whether a read of this type decides a workflow branch.")
    notes: str = Field(default="", description="What the type holds, and how many entries one work item carries.")
    producer_skills: frozenset[str] = Field(
        default_factory=frozenset,
        description="The skills (with the agent that does the writing, in parentheses, where a skill delegates "
        "to one) whose workflow registers this type.",
    )
    consumer_skills: frozenset[str] = Field(
        default_factory=frozenset,
        description="The skills (with the agent that does the reading, in parentheses, where a skill delegates "
        "to one) whose workflow reads this type back.",
    )

    @model_validator(mode="after")
    def _gate_read_type_has_exactly_one_agent(self) -> ArtifactTypeRow:
        """Reject a gate-read row that names other than exactly one registering agent.

        `artifact_read` called with no `artifact_id` resolves a manifest entry by
        `(item_id, artifact_type)` alone: it sorts every matching entry by `created_at` descending
        and returns only the newest. A second writer under a gate-read type therefore wins the read
        the moment it registers later, and the gate branches on whichever document happened to
        register last, with no error raised anywhere.

        Returns:
            This row, unchanged, once the check passes.

        Raises:
            ValueError: `gate_read` is `True` and `agents` does not name exactly one agent.
        """
        if self.gate_read and len(self.agents) != 1:
            msg = (
                f"{self.artifact_type.value!r} is gate_read but names {len(self.agents)} registering "
                f"agent(s) {sorted(self.agents)!r}; a gate-read type must name exactly one, because "
                "artifact_read by type alone returns only the newest entry and a second writer would "
                "silently win the read a gate branches on."
            )
            raise ValueError(msg)
        return self


REGISTRY: tuple[ArtifactTypeRow, ...] = (
    ArtifactTypeRow(
        artifact_type=ArtifactType.FEATURE_CONTEXT,
        agents=frozenset({"discovery", "feature-researcher"}),
        gate_read=False,
        notes=(
            "Discovery document. Each producer re-registers the same `artifact_id`, so the type holds one entry "
            "per item."
        ),
        producer_skills=frozenset({"discovery", "work-backlog-item", "add-new-feature (feature-researcher)"}),
        consumer_skills=frozenset({
            "planning",
            "add-new-feature",
            "final-verification",
            "start-task",
            "work-backlog-item",
            "complete-implementation (context-refinement)",
        }),
    ),
    ArtifactTypeRow(
        artifact_type=ArtifactType.ARCHITECT,
        agents=frozenset({"planning", "context-integration", "context-refinement", "{resolved_agent}"}),
        gate_read=False,
        notes=(
            "Architecture spec. Later stages re-register the same `artifact_id`, replacing the earlier revision "
            "rather than adding a sibling; `context-refinement` re-registers under the `artifact_id` its own read "
            "returned, appending annotations."
        ),
        producer_skills=frozenset({
            "planning",
            "context-integration",
            "complete-implementation (context-refinement)",
            "add-new-feature ({resolved_agent})",
        }),
        consumer_skills=frozenset({
            "context-integration",
            "task-decomposition",
            "implement-feature",
            "add-new-feature",
            "final-verification",
            "start-task",
            "complete-implementation (feature-verifier)",
        }),
    ),
    ArtifactTypeRow(
        artifact_type=ArtifactType.CODEBASE_ANALYSIS,
        agents=frozenset({"codebase-analyzer", "code-review-architecture"}),
        gate_read=False,
        notes=(
            "Codebase pattern, architecture, testing, convention, and dependency-graph documents. Intentionally "
            "multi-entry -- one per focus area or diagram. Consumers reach the full set through `artifact_list`."
        ),
        producer_skills=frozenset({"add-new-feature (codebase-analyzer)", "code-review-architecture"}),
        consumer_skills=frozenset({"add-new-feature", "complete-implementation"}),
    ),
    ArtifactTypeRow(
        artifact_type=ArtifactType.CODE_REVIEW,
        agents=frozenset({"code-reviewer"}),
        gate_read=True,
        notes=(
            "Code review verdict. One entry per reviewed task, so consumers read it by `artifact_id` "
            "(`code-review-{task_id}-{slug}`), reported in the reviewer's STATUS output. "
            "`complete-implementation` and `forensic-review` branch on `PASS` / `NEEDS-WORK` / `FAIL`."
        ),
        producer_skills=frozenset({"complete-implementation (code-reviewer)", "forensic-review (code-reviewer)"}),
        consumer_skills=frozenset({"complete-implementation", "forensic-review"}),
    ),
    ArtifactTypeRow(
        artifact_type=ArtifactType.T0_BASELINE,
        agents=frozenset({"t0-baseline-capture"}),
        gate_read=True,
        notes="Pre-implementation baseline. `tn-verification-gate` compares final state against it.",
        producer_skills=frozenset({"implement-feature (t0-baseline-capture)"}),
        consumer_skills=frozenset({"implement-feature (tn-verification-gate)"}),
    ),
    ArtifactTypeRow(
        artifact_type=ArtifactType.TN_VERIFICATION,
        agents=frozenset({"tn-verification-gate"}),
        gate_read=True,
        notes="Post-implementation verification. `complete-implementation` branches on the verdict.",
        producer_skills=frozenset({"implement-feature (tn-verification-gate)"}),
        consumer_skills=frozenset({"complete-implementation"}),
    ),
    ArtifactTypeRow(
        artifact_type=ArtifactType.RESEARCH,
        agents=frozenset({"swarm-task-planner", "ecosystem-researcher"}),
        gate_read=False,
        notes=("Investigation findings, coverage analysis, rationale. Multi-entry -- one document per investigation."),
        producer_skills=frozenset({"ecosystem-researcher"}),
        consumer_skills=frozenset({"add-new-feature"}),
    ),
    ArtifactTypeRow(
        artifact_type=ArtifactType.AUDIT_REPORT,
        agents=frozenset({"doc-drift-auditor"}),
        gate_read=False,
        notes="Documentation drift audit. Never used for a code review verdict.",
        producer_skills=frozenset({"complete-implementation (doc-drift-auditor)"}),
        consumer_skills=frozenset({"complete-implementation"}),
    ),
    ArtifactTypeRow(
        artifact_type=ArtifactType.DISPATCH_PLAN,
        agents=frozenset({"dispatch_create_plan"}),
        gate_read=False,
        notes="Milestone dispatch plan, registered by the dispatch tool rather than an agent.",
        producer_skills=frozenset({"groom-milestone"}),
        consumer_skills=frozenset({"work-milestone"}),
    ),
)
"""The registry: one row per artifact type an agent may register, in declaration order."""

ARTIFACT_TYPES: frozenset[str] = frozenset(row.artifact_type.value for row in REGISTRY)
"""Every type :data:`REGISTRY` declares, as the string an ``ARTIFACT`` referent and a tool call spell."""
