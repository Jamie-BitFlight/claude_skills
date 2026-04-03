# Plan Artifact Lifecycle Policy

## Purpose and Scope

This document defines the lifecycle policy for plan artifacts produced during the SAM (Structured Agent-Managed) workflow. It classifies artifacts into two categories (human-decision and generated), establishes rules for when generated artifacts may be updated, defines divergence detection and classification criteria, and specifies how divergence findings are surfaced to the human for review.

**Scope**:

- Artifact classification taxonomy and immutability/mutability rules
- Divergence detection during task execution and quality gates
- Divergence classification thresholds (design-refinement vs intent-divergence)
- Divergence recording format for task files
- Divergence reporting format at completion

**Out of scope**:

- Changes to Python scripts or CLI tools (`implementation_manager.py`, `task_status_hook.py`)
- Changes to generator agent prompts (`feature-researcher`, `swarm-task-planner`, `python-cli-design-spec`)
- Retroactive modification of existing plan artifacts (forward-only policy)

**Related documents**:

- SAM workflow documentation: [local-workflow.md](./../rules/local-workflow.md)
- Task file format specification: [TASK_FILE_FORMAT.md](./TASK_FILE_FORMAT.md)
- Start-task skill (divergence recording trigger): [start-task SKILL.md](./../skills/start-task/SKILL.md)
- Context-refinement agent (freshness check): [context-refinement.md](./../../plugins/python3-development/agents/context-refinement.md)

---

## Artifact Classification

Plan artifacts fall into two categories based on their origin and the rules governing their modification.

### Category 1: Human-Decision Artifacts (Immutable)

These artifacts capture the human's original intent. Agents must NEVER modify them.

| Artifact | Access | Created by |
|---|---|---|
| Backlog items | Via `backlog_view(selector)` or `backlog_list()` MCP tools | Human (via `/create-backlog-item`) |
| Grooming output | Embedded in backlog item under `## Groomed` | Human (via grooming session) |
| Fact-check results | Embedded in backlog item under `## Fact-Check` | Human or agent (captures human-verified facts) |
| RT-ICA assessments | Embedded in backlog item under `## RT-ICA` | Agent (captures human-approved assessment) |
| Interview transcripts | `.dh/docs/interviews/` or inline | Human |
| Human design decisions | Embedded in feature-context under `## Original Request` or backlog item | Human |

### Category 2: Generated Artifacts (Mutable, Intent-Bound)

These artifacts are produced by agents during planning phases. They may be updated, but updates must stay within the intent established by human-decision artifacts.

| Artifact | Access | Created by | Updated by |
|---|---|---|---|
| Feature context | `artifact_read(issue_number, 'feature-context')` | `feature-researcher` agent | `context-refinement` agent |
| Codebase analysis | `artifact_read(issue_number, 'codebase-analysis')` | `codebase-analyzer` agent | Not updated (informational snapshot) |
| Architecture spec | `artifact_read(issue_number, 'architect')` | `python-cli-design-spec` agent | `context-refinement` agent |
| Task plan | `sam_read(plan="P{NNN}")` | `swarm-task-planner` agent | Status fields by hooks; Context Manifest by `context-refinement` |
| Context Manifest | Embedded in task file (via `sam_read`) | `context-gathering` agent | `context-refinement` agent (existing behavior) |

---

## Rules for Human-Decision Artifacts

1. No agent may edit, append to, or rewrite a human-decision artifact.
2. Human-decision artifacts are the source of truth for intent.
3. When a generated artifact references a human-decision artifact, the reference must be by path, not by transcription (transcription decouples from the source and drifts).

---

## Rules for Generated Artifacts

1. Generated artifacts may be annotated with divergence information by the `context-refinement` agent.
2. Generated artifacts must NOT be silently rewritten to match implementation -- annotations are appended, not edits.
3. When a generated artifact's design decision conflicts with a human-decision artifact, the divergence is classified as "intent divergence" and flagged for human review.
4. Codebase analysis files are informational snapshots and are not updated. They reflect the state of the codebase at analysis time. Staleness is expected and acceptable -- they are research inputs, not living documents.

### Annotation vs Rewrite Distinction

**Annotation** (permitted): Appending a clearly demarcated section to a generated artifact that notes what changed and why. The original content remains intact. The annotation is visually distinct.

**Rewrite** (prohibited): Modifying the original content of a generated artifact to match implementation. This destroys the record of what was planned and makes it impossible to trace divergence.

---

## Divergence Detection

Divergence between plan artifacts and implementation is detected at two points in the SAM workflow:

### During Task Execution (Step 5a in start-task)

When an agent implements a task, it compares the architect spec and feature-context claims against what it is actually building. If a non-trivial difference is observed, the agent records a divergence note in the task file. See the [Divergence Recording](#divergence-recording) section for the format.

The agent records a divergence note when ALL of these conditions hold:

1. The agent is implementing something that differs from what the architect spec or feature-context describes
2. The difference is not a trivial implementation detail (e.g., different variable name, different import path)
3. The difference affects the observable behavior, structure, or scope of the feature

The agent does NOT record a divergence note for:

- Implementation choices not addressed by the plan (the plan is silent on the topic)
- Standard coding patterns or style choices
- Bug fixes in the plan's own inconsistencies (e.g., the plan references a non-existent API -- the fix is obvious)

### During Quality Gates (Phase 6 in complete-implementation)

The `context-refinement` agent performs a plan artifact freshness check after completing its existing Context Manifest update. It reads all task files for the feature, collects divergence notes and discovered-during-implementation sections, compares key claims in the architect spec against actual implementation files, and classifies each divergence. See [context-refinement.md](./../../plugins/python3-development/agents/context-refinement.md) for the agent's full process.

---

## Divergence Classification

Each divergence is classified using the following threshold table. The classification determines whether human review is required.

| Change type | Classification | Action |
|---|---|---|
| Implementation detail differs from architect spec (e.g., different function signature, different module name) | design-refinement | Auto-record in task file. No approval needed. |
| Approach differs from architect spec but achieves same goal stated in backlog item (e.g., used Strategy B instead of Strategy A) | design-refinement | Auto-record in task file and annotate architect spec. No approval needed. |
| Scope expanded or reduced beyond what backlog item specifies | intent-divergence | Record and flag for human review. |
| Goal redefined or abandoned (e.g., backlog says "add feature X" but implementation skips it) | intent-divergence | Record and flag for human review. |
| Constraint from grooming output violated (e.g., grooming says "must be backward-compatible" but implementation breaks compatibility) | intent-divergence | Record and flag for human review. |

**Intent Source resolution**: The `context-refinement` agent locates the human-decision artifact via the `Intent Source` field in the feature-context or architect spec header. If `Intent Source` is absent (pre-policy artifact), intent-divergence classification is skipped and all divergences default to design-refinement.

---

## Divergence Recording

During task execution, agents record divergence observations in the task file under a `## Divergence Notes` section. Each note follows this format:

````markdown
## Divergence Notes

### DN-1: {Brief title}

- **Plan artifact**: `artifact_read(issue_number={N}, artifact_type="architect")`, section "{section name}"
- **Plan claim**: "{quoted text from plan artifact}"
- **Actual implementation**: "{what was actually done and why}"
- **Classification**: design-refinement | intent-divergence
- **Recorded**: {ISO timestamp}
````

**Fields**:

- **Plan artifact**: File path and section name where the divergent claim appears
- **Plan claim**: Direct quotation from the plan artifact
- **Actual implementation**: Description of what was actually done and the reason for the difference
- **Classification**: The agent's assessment -- either `design-refinement` or `intent-divergence`
- **Recorded**: ISO 8601 timestamp when the note was recorded

**Counting**: The `divergence-notes` field in task file YAML frontmatter holds an integer count of divergence notes in the task body. This enables the `context-refinement` agent to quickly identify which tasks recorded divergences without parsing every task body. See [TASK_FILE_FORMAT.md](./TASK_FILE_FORMAT.md) for the field specification.

**Trigger**: This recording step is described in [start-task SKILL.md](./../skills/start-task/SKILL.md) as Step 5a.

---

## Divergence Reporting

After all tasks complete, the `context-refinement` agent (Phase 6 of the quality gates in the complete-implementation skill) performs a plan artifact freshness check and produces a structured report.

### Annotation of Plan Artifacts

If divergences are found, the agent appends a `## Post-Implementation Annotations` section to the feature-context and architect spec files:

````markdown
## Post-Implementation Annotations

_Added by context-refinement agent on {date}_

### Design Refinements

1. **{Title}**: {Description of what changed and why}
   - Original: "{quoted from plan}"
   - Actual: "{what was implemented}"
   - Recorded in: {task file path}, DN-{N}

### Intent Divergences Requiring Review

1. **{Title}**: {Description of how implementation diverges from human intent}
   - Human intent: "{quoted from backlog item or grooming output}"
   - Actual: "{what was implemented}"
   - Recorded in: {task file path}, DN-{N}
   - **Action needed**: Human review required
````

If no intent divergences are found, the `### Intent Divergences Requiring Review` subsection is omitted.

### Surfacing to the Human

When intent divergences are detected, the agent includes a `DIVERGENCE_REQUIRING_REVIEW` block in its output:

```text
DIVERGENCE_REQUIRING_REVIEW:
  1. [Title]: [Brief description]
     - Human intent: [quoted]
     - Actual: [description]
     - Task: [task file path]
```

The complete-implementation orchestrator checks for this block after Phase 6 completes. If present, it includes the divergence findings in its final summary to the human. This is informational, not blocking -- the human reviews divergences at their discretion after completion.

If no `DIVERGENCE_REQUIRING_REVIEW` block is present, the feature proceeds normally with no additional output.

---

## Artifact Manifest

The artifact manifest is a structured registry for generated artifacts. It provides a single discovery point for all plan artifacts associated with a feature, replacing ad-hoc filesystem scanning with explicit registration.

### Storage

The manifest is stored in the GitHub Issue body between HTML comment delimiters:

```html
<!-- ARTIFACT_MANIFEST_START -->
```yaml
artifacts:
  - type: feature-context
    path: plan/feature-context-my-feature.md
    status: current
    created_at: "2026-03-15T00:00:00Z"
    agent: feature-researcher
  - type: architect-spec
    path: plan/architect-my-feature.md
    status: current
    created_at: "2026-03-15T01:00:00Z"
    agent: python-cli-design-spec
  - type: task-plan
    path: plan/P719-my-feature.yaml
    status: current
    created_at: "2026-03-15T02:00:00Z"
    agent: swarm-task-planner
# Note: paths are state-relative (resolved from dh_paths.state_root(), not project root)
```
<!-- ARTIFACT_MANIFEST_END -->
```

Each entry records the artifact `type`, filesystem `path`, `status` (current, superseded, or stale), `created_at` timestamp, and the `agent` that produced it.

### Source of Truth

GitHub is the source of truth for the manifest. Local plan files under `~/.dh/projects/{slug}/plan/` are the content cache — they hold the artifact content itself, but the manifest in the issue body is the authoritative registry of what artifacts exist, their types, and their status.

### Producer Registration

Producer agents register artifacts via the `artifact_register` MCP tool after writing a plan artifact to disk. Registration adds an entry to the manifest in the GitHub Issue body. This ensures that every generated artifact is discoverable without filesystem scanning.

### Consumer Discovery

Consumer agents discover artifacts via the `artifact_list` MCP tool, which reads the manifest from the GitHub Issue body and returns the list of registered artifacts. For content access, consumers use `artifact_read`, which retrieves the artifact content by path.

### Worktree-Isolated Agents

Agents running in worktree isolation (`Agent(isolation: "worktree")`) cannot access plan artifacts via the filesystem because their working tree is a separate checkout. These agents use `artifact_read` to access artifact content via MCP instead of filesystem reads, ensuring they receive the same content as agents in the main worktree.

---

## Backward Compatibility

This policy applies forward-only. Existing plan artifacts are not retroactively modified.

### Existing Plan Artifacts

No changes are made to existing files in `~/.dh/projects/{slug}/plan/`. Existing feature-context files, architect specs, and task files continue to work as before. They lack `Artifact Type` and `Intent Source` metadata, which means:

- The `context-refinement` agent treats missing `Intent Source` as "skip intent-divergence classification"
- All divergences in pre-policy artifacts are classified as `design-refinement` (safe default)
- No retroactive annotations are added

### Existing Task Files

The `divergence-notes` field is optional with a default of 0. Existing task files without this field are unaffected. The `implementation_manager.py` parser ignores unknown fields, so the new field does not require parser changes.

### Existing Agent Behavior

- `feature-verifier` continues to read plan artifacts as ground truth for goal verification. Post-implementation annotations do not change the original content -- they are appended sections that the verifier can distinguish from the original plan.
- `doc-drift-auditor` continues to audit project documentation against code. Its scope does not overlap with plan artifact freshness checking. Phase 4 catches documentation that no longer matches code; Phase 6 catches plans that no longer match what was built.

### Lifecycle Metadata for New Artifacts

New artifacts created after this policy is in place will include lifecycle metadata headers:

- `Artifact Type: generated` -- identifies the artifact as a generated (mutable) artifact
- `Intent Source: ~/.dh/projects/{slug}/backlog/{backlog-item-file}.md` -- links to the human-decision artifact that established the intent

These fields enable the `context-refinement` agent to locate the human intent when classifying divergence. Their absence in pre-policy artifacts triggers the safe default behavior described above.

---

## Related Documents

Read these together to get the full system picture:

- [Default Development Flow](../skills/development-harness/references/default-development-flow.md) — S1-S7 stage sequencing, ARL touchpoint gates
- [Artifact Conventions](../skills/development-harness/references/artifact-conventions.md) — naming, file layout, cross-referencing
- [Workflow Architecture Diagram](./workflow-architecture-diagram.md) — data shapes, publisher-consumer map, state machine
- [Backlog Item Lifecycle](./backlog-item-lifecycle.md) — end-to-end issue journey from creation to closure
- [Task File Format](./TASK_FILE_FORMAT.md) — task field reference, authorized writers, sam CLI (snapshot — verify against `models.py` for planning)
- [Domain model source](../sam_schema/core/models.py) — authoritative field definitions (`Task` class)
