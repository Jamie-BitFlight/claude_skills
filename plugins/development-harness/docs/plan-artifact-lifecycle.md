# Plan and Artifact Lifecycle

This policy defines how agents create, read, update, register, and verify plans
and artifacts. The configured backend owns the complete lifecycle: work-item
grooming, plan and task state, artifact manifests, and artifact content.

Read [backend-providers.md](./backend-providers.md) for backend selection,
cache states, and provider troubleshooting.

<lifecycle_contract>

## Storage contract

Use one active backend for the work item and everything it owns. Address plans
and artifacts with logical references, not provider-specific paths:

| Logical record | Identity | Owner |
|---|---|---|
| Plan | Logical `plan_id` | The plan's opaque work-item reference, when linked |
| Artifact manifest | Owner reference plus the canonical `manifest` name | The work item |
| Artifact content | Owner reference, artifact type, and logical name | The work item or plan |

Use `sam_plan`, `sam_task`, `artifact_list`, and `artifact_read` to access these
logical records. Treat the returned owner reference, revision, and status as the
observable identity and state; do not infer authority from a local path.

Remote backends may return `stale=true`, `pending=true`, or unavailable errors;
local SQLite and memory backends do not use the remote cache contract. Follow the
handling rules in [backend-providers.md](./backend-providers.md) before claiming
that a write or verification is complete.

</lifecycle_contract>

<artifact_classes>

## Artifact classes

### Human-decision artifacts

Treat the following as immutable intent:

- The work item description and acceptance criteria.
- Groomed sections, including fact-check, RT-ICA, constraints, and impact.
- Human decisions recorded in the work item or a generated artifact's intent
  source.
- Interview or decision records explicitly identified as human input.

Read these records from the configured backend. Agents MUST preserve their
meaning and MUST NOT rewrite them to match an implementation.

### Generated artifacts

Treat the following as intent-bound, generated records:

- Feature context and research summaries.
- Codebase analysis snapshots.
- Architecture and design specifications.
- Task plans, task sections, and context manifests.
- Validation, report, and divergence records.

Generated content may receive an appended annotation, but its original content
remains intact. A codebase analysis is a snapshot: record newer facts elsewhere
instead of silently changing the original analysis.

</artifact_classes>

<agent_workflow>

## Agent workflow

Complete these steps in order. Each step has a checkable completion criterion.

1. **Resolve intent.** Read the work item with `backlog_view` and inspect its
   acceptance criteria, groomed sections, and owner reference. If required
   intent is absent, report the missing section and stop. **Complete when:** the
   input and its authoritative owner reference are recorded.
2. **Create or locate the plan.** Use `sam_plan` to create or read the plan and
   use `sam_task` to inspect its tasks. Keep the same owner reference as the work
   item. **Complete when:** a plan read returns the expected goal, owner, task
   identifiers, and statuses.
3. **Produce generated artifacts.** Write the feature context, architecture,
   analysis, or report content required by the task. Preserve links to intent
   sources instead of copying intent into the artifact. **Complete when:** each
   artifact has a logical type, name, producer, and content.
4. **Register content.** Call `artifact_register` with the work-item or plan
   owner reference and the generated content. Register a manifest entry even
   when the provider stores the content natively. **Complete when:**
   `artifact_list` returns one current entry for every produced artifact and
   `artifact_read` returns the registered content.
5. **Claim and execute tasks.** Claim work with `sam_task`, make the smallest
   implementation that satisfies the plan, and update task state through
   `sam_task`. **Complete when:** each changed task has a terminal status and
   its evidence is readable through the same backend.
6. **Record divergence.** Compare implementation behavior with the plan and
   intent sources. Record every material difference in the task or report
   content using the format below. **Complete when:** every recorded difference
   has a classification, owner reference, source section, reason, and timestamp.
7. **Verify and close.** Re-read the acceptance criteria, plan status, manifest,
   and required artifact content. Resolve or close the work item only after all
   required evidence is current and provider-acknowledged. **Complete when:**
   no required read is stale or unavailable and no required write remains
   pending.

When a remote read is stale, use it only as explicitly labelled context and
repeat the read after reachability returns. When a write is pending, report the
queue state and do not mark the corresponding task or work item complete.

</agent_workflow>

<divergence_policy>

## Divergence policy

Record a divergence when all of these are true:

1. The implementation differs from an architect, feature-context, or groomed
   claim.
2. The difference is more than a naming, import, or style choice.
3. The difference changes observable behavior, structure, constraints, or scope.

Do not record a divergence when the plan is silent, a standard coding pattern
fills the gap, or the implementation corrects an obvious inconsistency without
changing intent.

Classify each recorded difference as follows:

| Difference | Classification | Required action |
|---|---|---|
| A module, signature, or implementation detail changed while the goal and constraints remain satisfied | `design-refinement` | Append a note and annotate the generated design artifact. |
| The approach changed but still satisfies the work-item goal | `design-refinement` | Append a note and annotate the generated design artifact. |
| Scope, goal, or a groomed constraint changed | `intent-divergence` | Append a note and surface it for human review. |

If an older artifact has no intent source, classify a difference as
`design-refinement` and record that the intent source was unavailable. Do not
invent a human decision.

### Divergence note

Append notes to generated task or report content with this shape:

````markdown
## Divergence Notes

### DN-1: {brief title}

- **Owner reference**: `{work-item or plan reference}`
- **Plan artifact**: `artifact_read(item_id={owner_ref}, artifact_type="architect")`, section "{section}"
- **Plan claim**: "{short quotation or precise paraphrase}"
- **Actual implementation**: "{what changed and why}"
- **Classification**: `design-refinement` | `intent-divergence`
- **Recorded**: {ISO 8601 timestamp}
````

The note count in task metadata is a convenience index. The note body remains
the evidence source.

### Freshness report

After execution, compare every material claim in the plan and generated
artifacts with the implementation. Append a `Post-Implementation Annotations`
section to generated artifacts when differences exist. Keep the original text,
link each note to its task, and include a `DIVERGENCE_REQUIRING_REVIEW` block in
the completion report when any `intent-divergence` exists.

</divergence_policy>

<manifest_policy>

## Manifest policy

The active backend stores one logical manifest per work-item owner. The manifest
records artifact type, logical name, status, producer, creation or update time,
and content revision. It is the discovery index; it is not a second copy of the
artifact body.

Producer agents MUST:

1. Produce content with a stable logical artifact type and name.
2. Register or idempotently update it with `artifact_register`.
3. Read it back with `artifact_list` and `artifact_read`.

Consumer agents MUST:

1. Discover entries with `artifact_list` before selecting an existing artifact.
2. Read the selected content with `artifact_read`.
3. Treat a missing entry, stale result, unavailable result, or pending write as
   incomplete evidence.

Registration is idempotent for the same owner, type, and logical name. A retry
may update the existing entry; it MUST NOT create a second current entry.

</manifest_policy>

<migration_policy>

## Forward compatibility and migration debt

Apply this policy to new records. Preserve existing human intent and generated
content while it is being read. Existing records may contain path fields or
provider-specific references; treat those fields as migration metadata and
rewrite them only through the configured backend's migration operation.

Do not make a file path the canonical artifact identity, add a second backend
selector, or silently copy an old record into a new authority. A migration is
complete only when the manifest lists the logical owner, type, name, status, and
content revision and `artifact_read` returns the migrated content.

</migration_policy>

## Related documents

- [Backend providers](./backend-providers.md) — one-backend ownership, cache states, and configuration.
- [Default development flow](../skills/development-harness/references/default-development-flow.md) — stage sequencing.
- [Artifact conventions](../skills/development-harness/references/artifact-conventions.md) — naming and cross-referencing.
- [Backlog item lifecycle](./backlog-item-lifecycle.md) — work-item grooming and closure.
- [Task file format](./TASK_FILE_FORMAT.md) — legacy field reference; verify current fields against the active backend.
