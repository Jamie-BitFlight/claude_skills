# Artifact Conventions

SAM artifact naming, logical identifiers, and cross-referencing conventions for the development harness.

---

## Principle

Every stage in the SAM pipeline produces a named artifact. These artifacts are the only communication channel between stages. No stage relies on conversation memory — each reads its predecessor's artifact via MCP and writes its own via MCP. This is the stateless property of SAM.

---

## Cross-Reference Token Pattern

**Format:** `ARTIFACT:{TYPE}({SCOPE_OR_ID})`

**Types:**

- `ARTIFACT:DISCOVERY({feature-slug})` — S1 output
- `ARTIFACT:PLAN({feature-slug})` — S2 output
- `ARTIFACT:CONTEXT({feature-slug})` — S3 output (amends S2)
- `ARTIFACT:TASK({task-id})` — S4 output (one per task)
- `ARTIFACT:EXECUTION({task-id})` — S5 output (one per task)
- `ARTIFACT:REVIEW({feature-slug})` — S6 output
- `ARTIFACT:VERIFICATION({feature-slug})` — S7 output

**Usage in artifacts:** Each artifact includes a header block with references to predecessor and successor artifacts.

```markdown
---
artifact: ARTIFACT:PLAN(add-jwt-auth)
predecessor: ARTIFACT:DISCOVERY(add-jwt-auth)
successor: ARTIFACT:CONTEXT(add-jwt-auth)
feature: add-jwt-auth
stage: S2
created: 2026-02-15
---
```

---

## Storage Model

Artifacts are stored and retrieved via two distinct MCP systems. No stage reads or writes filesystem paths directly — all access goes through MCP tool calls.

### Artifact System

Document-level artifacts (discovery, plan, context integration) are managed by the backlog MCP server:

- **Write:** `artifact_register(item_id=item_id, artifact_type=artifact_type, artifact_id=artifact_id, agent=agent, content=content)` — registers the logical artifact identifier and writes optional content through the configured provider.
- **Read:** `artifact_read(item_id=item_id, artifact_type=artifact_type)` — returns `{artifact_type, path, content, status}` from the configured provider. The `path` response field carries the registered logical `artifact_id`.
- **List:** `artifact_list(item_id=item_id, artifact_type=None)` — enumerates registered artifacts for an issue.

Artifact types used in the S1–S7 pipeline:

- `"feature-context"` — S1 Discovery output
- `"architect"` — S2 Plan output (updated by S3 Context Integration)

Task plans are SAM-owned records, not artifact-registry content. Use `sam_plan` and `sam_task` for
their complete lifecycle; never register or read task-plan content with `artifact_register` or
`artifact_read`.

### SAM System

Task plans and task-level state are managed by the SAM MCP server:

- **Create:** `sam_plan(config={"action": "create", "slug": slug, "goal": goal, "tasks": [task_dict, ...], "owner_reference": item_ref})` — creates a provider-owned plan associated with the backlog item's opaque reference and returns its `plan_ref`. Pass `tasks=[]` to create a drafting plan for incremental append.
- **Link:** `backlog_update(selector=item_ref, plan=plan_ref)` — stores the returned plan address on the backlog item.
- **Read plan:** `sam_plan(plan=plan_ref, config={"action": "read"})` — returns the provider-owned plan.
- **Read task:** `sam_task(plan=plan_ref, task=task_id, config={"action": "read"})` — returns a `TaskAssignment` model with plan-level context and task fields.
- **Update task:** `sam_task(plan=plan_ref, task=task_id, config={"action": "update", "append_section": ..., "section_content": ...})` — appends sections to task bodies. Used by S5 Execution, S6 Forensic Review, and S7 Final Verification to store results within the task structure.

Task plans are stored by the configured SAM backend and addressed by the `plan_ref` returned from creation. Access is exclusively via MCP tools. The storage format is an implementation detail of the backend; do not assume YAML, JSON, or any filesystem path.

### Backlog System

Backlog item metadata and grooming state are accessed via:

- **View:** `backlog_view(selector, summary=false)` — returns full item context including `sections` dict (groomed fields), labels, and priority.
- **List:** `backlog_list()` — enumerates all backlog items for scanning and counting.

---

## Logical Identifier Conventions

The names below are logical artifact identifiers. A provider may map one to a repository-relative
path, an issue-native record, or another native key; callers must not use the identifier as a
filesystem path.

### Feature-Level Artifacts

**Pattern:** `{stage-prefix}-{feature-slug}.md`

**Stage prefixes by stage:**

- S1 — `discovery`
- S2 — `plan`
- S3 — `context`
- S6 — `review`
- S7 — `verification`

**Feature slug rules:**

- Derived from the feature name or request
- Lowercase, hyphen-separated
- Max 50 characters
- No special characters beyond hyphens

**Examples:**

- `discovery-add-jwt-auth.md`
- `plan-refactor-payment-module.md`
- `review-add-csv-export.md`

### Task-Level Artifacts

**Pattern:** `{stage-prefix}-{task-id}-{task-slug}.md`

**Stage prefixes for task-level:**

- S4 — `task`
- S5 — `execution`

**Task ID rules:**

- Three-digit zero-padded integer
- Assigned sequentially during S4 Task Decomposition
- IDs are stable — not renumbered after creation

**Task slug rules:**

- Brief description of the task
- Same formatting rules as feature slug

**Examples:**

- `task-001-add-jwt-middleware.md`
- `task-002-add-token-validation.md`
- `execution-001-add-jwt-middleware.md`
- `execution-002-add-token-validation.md`

---

## Artifact Types

### DISCOVERY

**Stage:** S1
**Purpose:** Capture requirements, codebase context, constraints, and resolved role assignments.

**Required sections:**

- Feature request (original, verbatim)
- Codebase context (structure, relevant files, patterns)
- Constraints identified (bound and unbound)
- Role resolution results (which agents assigned to which roles)
- Quality gates configured
- ARL touchpoint assessment for Gate 1

### PLAN

**Stage:** S2
**Purpose:** Development plan with task graph, acceptance criteria, and RT-ICA analysis.

**Required sections:**

- RT-ICA gap analysis (present, partial, missing information)
- Task graph with dependencies
- Task skeletons with acceptance criteria
- Quality gate schedule (which gates run at which stages)
- Unblock paths for tasks with missing information

### CONTEXT

**Stage:** S3
**Purpose:** Plan validated against actual codebase state.

**Required sections:**

- Validation results per plan element
- Codebase discrepancies found (if any)
- Plan amendments (if needed)
- Verified integration points
- Confirmed dependency availability

### TASK

**Stage:** S4
**Purpose:** Individual executable task record.

**Required sections:**

- Task ID and description
- Predecessor artifact reference
- Assigned agent (from role resolution)
- Inputs (files to read, context needed)
- Acceptance criteria (testable, specific)
- Quality gates to run after completion
- Dependencies on other tasks (if any)

### EXECUTION

**Stage:** S5
**Purpose:** Record of what was implemented for a task.

**Required sections:**

- Task reference
- Files created or modified (with paths)
- Implementation decisions and rationale
- Quality gate results (pass/fail per gate)
- Deviations from plan (if any)

### REVIEW

**Stage:** S6
**Purpose:** Forensic review comparing execution against acceptance criteria.

**Required sections:**

- Per-task verdict (COMPLETE or NEEDS_WORK)
- Acceptance criteria evaluation (pass/fail per criterion)
- Quality gate summary
- Regression check results
- NEEDS_WORK details (what failed, what to fix)

### VERIFICATION

**Stage:** S7
**Purpose:** Final certification against original requirements.

**Required sections:**

- Per-requirement verdict (MET or NOT_MET)
- Traceability matrix (requirement to task to implementation)
- Full quality gate results
- Integration verification results
- Final verdict (CERTIFIED or NOT_CERTIFIED)
- NOT_CERTIFIED details (what requirements are unmet)

---

## Cross-Referencing Between Artifacts

Each artifact references its immediate predecessor and the tasks it relates to.

**Forward references:** When S4 creates tasks, each task artifact includes `predecessor: ARTIFACT:PLAN({feature-slug})`.

**Backward references:** When S6 reviews tasks, the review artifact includes references to all `ARTIFACT:EXECUTION({task-id})` artifacts.

**Traceability chain:** S7 verification builds a complete traceability matrix linking requirements (from S1) through plan (S2), tasks (S4), execution (S5), and review (S6).

---

## Artifact Lifecycle

Artifacts persist after feature completion for auditability. The configured providers own storage
and lifecycle; callers retain only the artifact `artifact_id` and SAM `plan_ref` logical addresses.
Remote-capable providers may maintain an offline file cache internally. Local memory, SQLite, and
Beads providers store their native records directly and do not require that cache.

---

## Related Documents

Read these together to get the full system picture:

- [Default Development Flow](./default-development-flow.md) — S1-S7 stage sequencing, ARL touchpoint gates
- [Workflow Architecture Diagram](../../../docs/workflow-architecture-diagram.md) — data shapes, publisher-consumer map, state machine
- [Plan Artifact Lifecycle](../../../docs/plan-artifact-lifecycle.md) — immutable vs mutable artifacts, divergence detection
- [Backlog Item Lifecycle](../../../docs/backlog-item-lifecycle.md) — end-to-end issue journey from creation to closure
- [Task File Format](../../../docs/TASK_FILE_FORMAT.md) — task field reference, authorized writers, sam CLI (snapshot — verify against `models.py` for planning)
- [Domain model source](../../../sam_schema/core/models.py) — authoritative field definitions (`Task` class)

## Sources

- SAM methodology: <https://github.com/bitflight-devops/stateless-agent-methodology>
- Default development flow: [./default-development-flow.md](./default-development-flow.md)
