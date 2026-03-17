---
name: Unified task/plan schema module — single Pydantic source for reading, writing, and querying SAM task files
description: "The swarm-task-planner, implementation_manager, task_status_hook, and other scripts each independently parse SAM task files using different format assumptions. The swarm-task-planner produces files that implementation_manager cannot parse (observed: tasks-1-backlog-state-reconciliation.md uses `### T1:` headings instead of `## Task 1:` legacy format or YAML frontmatter per task). No single schema definition exists for what a valid task file looks like.\n\nWhat's needed: a single shared Python module containing (1) Pydantic models defining the canonical task/plan schema, (2) readers that can ingest both legacy markdown format (`## Task N:` headers) and YAML frontmatter format, normalizing to the unified model, (3) writers that produce the canonical format, (4) query functions (list tasks, get ready tasks, get task by ID, update status), and (5) schema gap detection — when reading old-format files, report which fields are missing vs the canonical schema so they can be backfilled.\n\nThis module becomes the single interface to task file data. The swarm-task-planner writes through it, implementation_manager reads through it, task_status_hook updates through it. No script parses task files ad-hoc.\n\nWhat success looks like: implementation_manager.py can parse any task file produced by swarm-task-planner regardless of format variation. Running `ready-tasks` on a task file always returns correct results. Format mismatches surface as explicit schema gap reports, not silent parse failures.\n\nHow you'll know it's working: the YAML frontmatter parse warning we hit on tasks-1-backlog-state-reconciliation.md does not occur — the unified reader handles both formats."
metadata:
  topic: unified-taskplan-schema-module-single-pydantic-source-for-re
  source: Session observation — implementation_manager.py failed to parse task file produced by swarm-task-planner (2026-03-14)
  added: '2026-03-14'
  priority: completed
  type: Feature
  status: done
  issue: '#715'
  last_synced: '2026-03-14T22:49:38Z'
  groomed: '2026-03-14'
  plan: plan/tasks-2-unified-sam-task-schema.md
---

## Fact-Check

<div><sub>2026-03-14T22:39:47Z</sub>

**Claims Checked**: 4
**VERIFIED**: 4 | **REFUTED**: 0 | **INCONCLUSIVE**: 0

| Claim | Verdict | Evidence |
|-------|---------|----------|
| swarm-task-planner produces files that implementation_manager cannot parse | VERIFIED | Observed this session: `uv run implementation_manager.py status . backlog-state-reconciliation` returned `WARNING: YAML frontmatter parsing failed` and `total_tasks: 0` on `plan/tasks-1-backlog-state-reconciliation.md` |
| Task file uses `### T1:` headings instead of `## Task N:` | VERIFIED | File read: `plan/tasks-1-backlog-state-reconciliation.md` uses `### T1: State handler helper functions` format. `grep "^## Task" plan/tasks-1-backlog-state-reconciliation.md` returned no matches. |
| No single schema definition exists for task files | VERIFIED | Code: `implementation_manager.py` has `_parse_task_section()` for legacy format, `task_format.py` has YAML frontmatter parsing. No shared Pydantic model exists. Each script has its own regex-based parser. |
| Multiple scripts independently parse task files | VERIFIED | Code: `implementation_manager.py` (legacy parser), `task_format.py` (YAML frontmatter parser), `task_status_hook.py` (regex-based status update), `split_task_file.py` (splitter), `migrate_task_format.py` (format migrator) — each with independent parsing logic |

**Method**: All claims verified via direct observation in this session (parse failure, file reads, code inspection by codebase-analyzer agent).
</div>

## RT-ICA

<div><sub>2026-03-14T22:40:05Z</sub>

**Goal**: Create a single Pydantic-based module that all SAM task file consumers share for reading, writing, querying, and validating task/plan files in any format.

**Conditions**:
1. Inventory of all task file formats currently in use | **AVAILABLE** | Three formats observed: legacy markdown (`## Task N:`), YAML frontmatter per task, and the swarm-task-planner variant (`### TN:` headings with summary frontmatter)
2. Inventory of all scripts that parse task files | **AVAILABLE** | implementation_manager.py, task_format.py, task_status_hook.py, split_task_file.py, migrate_task_format.py — identified by codebase-analyzer
3. Task file field definitions (what fields a task must/can have) | **AVAILABLE** | Documented in .claude/docs/TASK_FILE_FORMAT.md: Status, Dependencies, Priority, Complexity, Agent, Skills, Started, Completed, LastActivity, plus Acceptance Criteria and Verification Steps
4. Pydantic available in project dependencies | **AVAILABLE** | pydantic is a dependency of the project (used by backlog_core and other modules)
5. Canonical output format decision (which format the writer produces) | **DERIVABLE** | YAML frontmatter format is the documented target per TASK_FILE_FORMAT.md and migrate_task_format.py. Legacy format is read-only backward compat.
6. Location for the shared module | **DERIVABLE** | Candidates: `plugins/python3-development/skills/implementation-manager/scripts/task_schema.py` (alongside existing task_format.py) or a new shared location. Decision for planning phase.
7. Migration plan for existing consumers | **DERIVABLE** | Each consumer switches from internal parsing to importing from the shared module. Scope derivable from the consumer inventory (condition 2).

**Decision**: APPROVED — all prerequisites available or derivable. No blockers.
</div>

## Groomed (2026-03-14)

### Issue Classification

<div><sub>2026-03-14T22:40:17Z</sub>

**Type**: `missing-guardrail`

**Rationale**: No schema contract exists between the task file producer (swarm-task-planner) and consumers (implementation_manager, task_status_hook). Each component has its own parser with its own format assumptions. When the producer's output drifts, consumers fail silently or with unhelpful errors. This is a missing contract/interface, not a bug in any single component.

**Scenario-target**: When swarm-task-planner writes a task file, it passes through the shared schema module's writer. When implementation_manager reads a task file, it passes through the shared schema module's reader. Format mismatches are caught at the schema boundary with explicit gap reports, not at runtime with regex parse failures.

**Analysis method**: None required (missing-guardrail type).
</div>

### Reproducibility

<div><sub>2026-03-14T22:41:18Z</sub>

1. Have a SAM feature plan file that uses swarm-task-planner's global manifest format — a single top-level YAML frontmatter block with a `tasks:` list and `### TN:` markdown heading sections for each task body (as in `plan/tasks-1-backlog-state-reconciliation.md`).
2. Run `uv run plugins/python3-development/skills/implementation-manager/scripts/implementation_manager.py status . backlog-state-reconciliation`
3. Observe: `WARNING: YAML frontmatter parsing failed` followed by `total_tasks: 0` and no ready tasks returned.
4. Run `uv run plugins/python3-development/skills/implementation-manager/scripts/implementation_manager.py ready-tasks . backlog-state-reconciliation`
5. Observe: `{"ready_tasks": [], "count": 0}` — the orchestrator sees no work to dispatch, SAM stalls.
</div>

### Output / Evidence

<div><sub>2026-03-14T22:41:27Z</sub>

- `uv run implementation_manager.py status . backlog-state-reconciliation` → stderr: `WARNING: YAML frontmatter parsing failed` and stdout: `total_tasks: 0`. Observed directly in session 2026-03-14.
- `plan/tasks-1-backlog-state-reconciliation.md` has `tasks: [T1..T9]` in global frontmatter and `### T1:` markdown heading sections — no embedded per-task YAML blocks. `parse_task_content()` detects the file as a multi-task manifest, calls `_parse_multi_task_body()`, which splits on `\n---\n` and finds zero segments with both `task:` and `status:` fields → returns `[]`.
- `grep "^## Task" plan/tasks-1-backlog-state-reconciliation.md` returns no matches — confirms the file uses the `### TN:` variant swarm-task-planner produced, not the `## Task N:` legacy heading format or per-task YAML frontmatter blocks the parser expects.
</div>

### Priority

<div><sub>2026-03-14T22:41:38Z</sub>

8/10 — The absence of a shared schema is a systemic fragility: every time swarm-task-planner produces a format variant not anticipated by the parsers, the entire SAM pipeline stalls silently with zero tasks visible. This has already caused a real failure (backlog-state-reconciliation plan, 2026-03-14). Five independent parsers mean five places to break. Without this item, every new swarm-task-planner output variation requires a separate parser fix across multiple scripts. The item becomes a prerequisite for the dead-code cleanup (#441) that is waiting on a stable replacement.
</div>

### Impact

<div><sub>2026-03-14T22:41:48Z</sub>

- Blocks: SAM pipeline stalls when swarm-task-planner produces any format not covered by the current parser — orchestrator sees zero ready tasks and has no mechanism to know why.
- Blocks: `implement-feature` skill cannot dispatch any tasks from affected plan files; work must be done manually or the plan file must be hand-edited.
- Blocks: `task_status_hook.py` uses its own regex patterns to update status fields; format drift causes status timestamps to be silently skipped for unrecognized formats.
- Bottleneck: Five scripts (implementation_manager.py, task_format.py, task_status_hook.py, split_task_file.py, migrate_task_format.py) each add independent format assumptions. Each new format variant requires updates in N places instead of 1.
- Dead code cleanup (#441) is explicitly waiting on a stable schema replacement — that item cannot proceed until this one exists.
</div>

### Benefits

<div><sub>2026-03-14T22:41:58Z</sub>

- All SAM pipeline components (swarm-task-planner, implement-feature, start-task, task_status_hook) share one format contract — format drift produces an explicit schema gap report at the boundary, not a silent parse failure downstream.
- Dead code cleanup (#441) is unblocked: legacy regex parser and fenced YAML recovery can be removed once all consumers read through the shared module.
- `migrate_task_format.py` and `split_task_file.py` gain schema gap detection — reading an old file reports exactly which fields are missing vs the canonical schema so backfill is guided, not guessed.
- `implementation_manager ready-tasks` correctly handles the global-manifest + markdown-sections format produced by swarm-task-planner, ending the current class of "zero tasks visible" stalls.
- Future format additions require changes in one place (the schema module) rather than N scripts.
</div>

### Expected Behavior

<div><sub>2026-03-14T22:42:05Z</sub>

Running `implementation_manager.py status . <slug>` on any task file produced by swarm-task-planner returns the correct task list and ready-task count regardless of which format variant the file uses. When a file uses a recognized but legacy format, a schema gap report lists which optional fields are absent — the parse does not fail. When a file contains a format that cannot be normalized, a clear error message identifies the file, the format that was detected, and which required fields are missing. No SAM workflow component parses task file content directly — all reads and writes go through the shared module's public interface.
</div>

### Acceptance Criteria

<div><sub>2026-03-14T22:42:17Z</sub>

1. `uv run implementation_manager.py status . backlog-state-reconciliation` returns `total_tasks: 9` and lists all nine tasks from `plan/tasks-1-backlog-state-reconciliation.md` (the global-manifest + markdown-sections variant).
2. `uv run implementation_manager.py ready-tasks . backlog-state-reconciliation` returns `{"ready_tasks": ["T1"], "count": 1}` — T1 has no dependencies and status not-started.
3. No `WARNING: YAML frontmatter parsing failed` appears on stderr for any task file currently in the `plan/` directory.
4. `uv run implementation_manager.py status . <slug>` on a legacy markdown format file (`## Task N:` headings) returns tasks without error and with a schema gap report listing absent YAML fields.
5. `uv run implementation_manager.py status . <slug>` on a YAML frontmatter per-task file returns tasks without error.
6. `uv run implementation_manager.py status . <slug>` on a single-task YAML frontmatter file returns exactly one task without error.
7. Running `uv run ty check` on the shared schema module produces zero errors.
8. Running `uv run pytest` on the schema module's test suite produces zero failures with coverage of all three format parsers (global-manifest, per-task YAML, legacy markdown).
9. `task_status_hook.py` can update `status` and timestamp fields in a global-manifest format file without corrupting the YAML frontmatter.
10. A schema gap report for a legacy file lists specifically which optional fields (agent, priority, complexity, skills, etc.) are absent from each task, not just a count.
</div>

### Resources

<div><sub>2026-03-14T22:42:28Z</sub>

| Type | Item |
|------|------|
| Prior work — current multi-format parser | plugins/python3-development/skills/implementation-manager/scripts/implementation_manager.py |
| Prior work — YAML frontmatter utilities | plugins/python3-development/skills/implementation-manager/scripts/task_format.py |
| Prior work — regex status updater | plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py |
| Prior work — task file splitter | plugins/python3-development/scripts/split_task_file.py |
| Prior work — format migrator | plugins/python3-development/scripts/migrate_task_format.py |
| Prior work — existing parser tests | plugins/python3-development/skills/implementation-manager/scripts/test_task_parsing.py |
| Spec — canonical field definitions | .claude/docs/TASK_FILE_FORMAT.md |
| Example — broken format file | plan/tasks-1-backlog-state-reconciliation.md |
| Related item — dead code cleanup waiting on this | #441 (Dead code cleanup: remove legacy markdown parser) |
| Related item — SAM artifact schema validation | #88 (SAM: Artifact Schema Validation) |
</div>

### Dependencies

<div><sub>2026-03-14T22:42:35Z</sub>

- Depends on: None — all format inventories and field definitions are already available in the codebase and `.claude/docs/TASK_FILE_FORMAT.md`.
- Blocks: #441 (Dead code cleanup: remove legacy markdown parser and fenced YAML recovery from implementation_manager) — that cleanup requires a stable replacement to exist first.
- Blocks: Any SAM feature whose plan file uses the global-manifest + markdown-sections format produced by swarm-task-planner (e.g., #714 backlog-state-reconciliation).
</div>

### Effort

<div><sub>2026-03-14T22:42:44Z</sub>

Medium — The canonical schema is fully documented in `.claude/docs/TASK_FILE_FORMAT.md`. Three format readers need to be implemented (global-manifest + markdown sections, per-task YAML frontmatter, legacy `## Task N:` markdown). The main complexity is correctly extracting task metadata from the global-manifest + markdown-sections variant (tasks listed in the manifest, bodies in `### TN:` sections). The writers and query functions are straightforward once the Pydantic models are defined. Migrating the five existing scripts to import from the shared module is mechanical. Tests for all three format paths already have a starting point in `test_task_parsing.py`.
</div>

### Decision

<div><sub>2026-03-14T22:43:12Z</sub>
<details><summary>struck: 2026-03-14T22:49:38Z — Clarified: markdown is content within YAML multiline string fields, not structural</summary>

**User design directive (2026-03-14)**:

1. **Task files must be pure YAML** — no markdown with embedded metadata, no regex parsing of headings. The canonical format is YAML.
2. **Single file under 500 lines** — when the total YAML is under 500 lines, all tasks stay in one `.yaml` file.
3. **Split above 500 lines** — when over 500 lines, the plan file references paths to individual YAML task files in a directory (e.g., `plan/tasks-backlog-state-reconciliation/` with `plan.yaml` + `task-1.yaml`, `task-2.yaml`, etc.).
4. **Backward compatibility** — the reader must still ingest legacy markdown and old YAML-frontmatter-in-markdown formats, but the writer always produces pure YAML.
5. **Schema gap detection** — when reading old formats, report which fields are missing vs the canonical YAML schema so they can be backfilled.

This simplifies the module: the canonical format is YAML (readable by any YAML parser), legacy formats are read-only compat layers that normalize to the same Pydantic model.
</details>
</div>

<div><sub>2026-03-14T22:48:22Z</sub>
<details><summary>struck: 2026-03-14T22:49:38Z — Clarified: markdown is content within YAML multiline string fields, not structural</summary>

**User design directive (2026-03-14)**:

1. **Pure YAML data format** — task files are data, not documents. No markdown. The script/MCP server is the interface for reading, writing, and querying. Agents never parse files directly.
2. **Single file under 500 lines** — when total YAML is under 500 lines, all tasks stay in one `.yaml` file. Over 500 lines splits into a directory with plan-level YAML referencing individual task YAML files.
3. **CLI addressing scheme** — tasks are addressed as `P{plan}/T{task}`:
   - `sam read P1/T3` — agent reads its task assignment (returns task content, acceptance criteria, dependencies, context)
   - `sam state P1/T3 in_progress` — hook updates task state
   - `sam ready P1` — list ready tasks in plan 1
   - `sam status P1` — plan-level status summary
4. **MCP server equivalent** — same operations exposed as MCP tools so agents and hooks can call either CLI or MCP:
   - `sam_read(plan="P1", task="T3")` → task content
   - `sam_state(plan="P1", task="T3", status="in_progress")` → state update
   - `sam_ready(plan="P1")` → ready task list
5. **Backward compatibility** — reader can ingest legacy markdown and old YAML-frontmatter-in-markdown formats, normalizing to the YAML data model. Writer always produces pure YAML.
6. **Schema gap detection** — when reading old formats, report which fields are missing vs the canonical schema so they can be backfilled.
7. **Single interface principle** — swarm-task-planner writes through this module, implementation_manager reads through it, task_status_hook updates through it. No script parses task files ad-hoc.
</details>
</div>

<div><sub>2026-03-14T22:49:38Z</sub>

**User design directive (2026-03-14, revised)**:

1. **Pure YAML structure** — task files are YAML data. All structural fields (id, title, status, dependencies, agent, priority, complexity, skills) are typed YAML fields. No regex parsing of headings or markdown structure.
2. **Markdown inside YAML multiline strings** — rich text content (description, acceptance criteria, verification steps, context notes) is markdown stored in YAML multiline scalars (`|`). Machines parse the YAML structure; agents read the markdown content within fields.
3. **Single file under 500 lines** — when total YAML is under 500 lines, all tasks stay in one `.yaml` file. Over 500 lines splits into a directory with plan-level YAML referencing individual task YAML files.
4. **CLI addressing scheme** — tasks addressed as `P{plan}/T{task}`:
   - `sam read P1/T3` — agent reads its task assignment
   - `sam state P1/T3 in_progress` — hook updates task state
   - `sam ready P1` — list ready tasks in plan 1
   - `sam status P1` — plan-level status summary
5. **MCP server equivalent** — same operations as MCP tools for agents and hooks.
6. **Backward compatibility** — reader can ingest legacy markdown and old YAML-frontmatter-in-markdown formats, normalizing to the YAML data model. Writer always produces pure YAML.
7. **Schema gap detection** — when reading old formats, report which fields are missing vs canonical schema.
8. **Single interface principle** — all consumers (swarm-task-planner, implementation_manager, task_status_hook) go through this module. No ad-hoc file parsing.
</div>