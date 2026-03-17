---
name: Integrate sam_schema as sole task file interface across all SAM workflow components
description: "Seven SAM workflow components read and write task files using direct file operations (Read/Edit/Write tools) with independent format assumptions. The sam_schema module exists with CLI and MCP interfaces but no component uses them. Task files are accessed through 4 different parsers producing format drift and data loss.\n\nComponents and their current behavior (verified via agent trace 2026-03-15):\n\n1. swarm-task-planner — writes task files via Write tool with schema embedded in agent prompt. No reference to sam_schema or TASK_FILE_FORMAT.md.\n2. start-task — reads full task file via Read tool, finds its task by scanning. Writes status via Edit tool. No reference to sam_schema.\n3. task_status_hook — split: uses sam_schema for .yaml files, own parser (parse_yaml_frontmatter + regex) for .md files. Partial integration only.\n4. implementation_manager — uses sam_schema as primary reader for status/ready-tasks, but own parser for validate/claim-task. Partial integration.\n5. implement-feature — calls implementation_manager.py CLI. No reference to sam_schema or sam CLI.\n6. complete-implementation — passes raw file paths to agents. No reference to sam_schema.\n7. context-gathering — reads full file via Read, appends Context Manifest via Edit. No reference to sam_schema.\n\nWhat success looks like: every component uses sam CLI or MCP tools as its sole interface to task data. No component uses Read/Edit/Write on task files directly. The sam interface handles format detection, content extraction, and state updates regardless of backing store (YAML file, split directory, or future GitHub/SQLite backend).\n\nHow you'll know it's working: an agent assigned a task calls `sam read {slug}/T3` and receives plan goal, shared context, and its task details without reading any file. The swarm-task-planner calls `sam create` and produces valid pure YAML. The task_status_hook calls `sam state {slug}/T3 complete` for all formats without branching on file extension."
metadata:
  topic: integrate-samschema-as-sole-task-file-interface-across-all-s
  source: Session observation — agent interaction trace revealed 7 components bypass sam_schema (2026-03-15)
  added: '2026-03-15'
  priority: completed
  type: Feature
  status: done
  issue: '#719'
  last_synced: '2026-03-15T08:18:35Z'
  groomed: '2026-03-15'
  plan: plan/tasks-3-integrate-sam-schema.md
---

## RT-ICA

<div><sub>2026-03-15T06:57:09Z</sub>

**RT-ICA Snapshot** (pre-swarm baseline)

**Goal**: All 7 SAM workflow components access task files exclusively through sam_schema CLI/MCP interface — no direct Read/Edit/Write on task files.

**Conditions**:
1. sam_schema module exists with read/write/query capabilities | **AVAILABLE** | packages/sam_schema/ implemented, 421 tests, 93% coverage
2. sam CLI exists with read/state/ready/status/migrate commands | **AVAILABLE** | cli.py implemented with Typer
3. sam MCP server exists with sam_read/sam_state/sam_ready/sam_status tools | **AVAILABLE** | server.py implemented with FastMCP
4. sam CLI `create` command exists for plan creation | **MISSING** | not implemented — swarm-task-planner needs this to write plans
5. sam CLI `update` command exists for plan-level field updates | **MISSING** | not implemented — context-gathering needs this to add context
6. sam `read` returns plan goal + context alongside task details | **MISSING** | currently returns task only — start-task agents need plan context with their task
7. Inventory of exact data each component reads/writes from task files | **AVAILABLE** | traced via 7 Explore agents this session with exact quotes
8. Agent prompt files identified for all 7 components | **AVAILABLE** | paths known from Explore traces
9. implementation_manager internal parser removed in favor of sam_schema | **DERIVABLE** | sam_schema is primary but internal parser still used for validate/claim-task
10. task_status_hook .md branch removed | **DERIVABLE** | sam_schema handles all formats via readers — .md branch is redundant once sam_state works for all formats
11. Plan file naming convention agreed (P{N}-{slug} vs tasks-{N}-{slug}) | **MISSING** | discussed but not codified — affects addressing scheme
12. TASK_FILE_FORMAT.md updated to describe new system | **MISSING** | still describes old YAML-frontmatter-in-markdown format
13. #716 follow-up fixes complete (multi-doc YAML, compound IDs) | **DERIVABLE** | can be done as part of this work or sequenced before it

AVAILABLE count: 4
DERIVABLE count: 3
MISSING count: 4

**Decision**: Proceed to swarm — MISSING items are design decisions and new CLI commands, not blockers for grooming.
</div>

## Groomed (2026-03-15)

### Issue Classification

<div><sub>2026-03-15T06:58:18Z</sub>

**Classification**: missing-guardrail

**Rationale**: The core problem is not that something is broken (defect) or that a process step was skipped (procedural). The sam_schema module exists and works — 421 tests, 93% coverage. The problem is that no contract enforces its use. Seven components are free to access task files through any mechanism they choose, and they exercise that freedom through 4 independent parsers.

This is not a recurring-pattern either. A recurring-pattern would mean the same bug class keeps appearing in different places. Here the symptom (format drift, parse failures, data loss) is a consequence of the missing guardrail, not a pattern that would be fixed by addressing individual instances. Fixing one component's parser while leaving six others unconstrained does not reduce the problem space — any component can still introduce new format assumptions.

It is not unbounded-design because the solution shape is well-defined: route all task file access through sam_schema's CLI/MCP interface. The RT-ICA identifies exactly 4 MISSING items (create command, update command, plan-context-in-read, naming convention) and 3 DERIVABLE items. The design boundary is clear.

**Why not defect**: Each component works correctly in isolation against the format it expects. The failures occur at integration boundaries when format assumptions diverge — which is the definition of a missing interface contract.

**Why not recurring-pattern**: The 4 independent parsers were written independently, not as repeated attempts to solve the same problem. They are parallel implementations, not serial regressions.

**Root structural cause**: sam_schema was built as an optional library rather than a mandatory gateway. No component was updated to depend on it when it was introduced. The module's existence does not create adoption — only an enforced interface contract does. The guardrail needed is: task file I/O routes exclusively through sam_schema, and direct file operations on task files by workflow components are prohibited.
</div>

### Impact

<div><sub>2026-03-15T00:00:00Z</sub>

<div><sub>2026-03-15T06:59:54Z</sub>
</div>

<div><sub>2026-03-15T07:03:40Z</sub>

**What breaks today (current state):**

- `task_status_hook.py` `.md` branch: task completion status silently not written when sam_schema-normalized field names differ from the regex patterns in `task_format.py`. Implementation loop stalls — tasks appear never-complete to the engine.
- `claim-task` raw string splitting: produces garbled output on multi-document YAML or non-standard separators. Duplicate task dispatch is possible when claim silently no-ops.
- `implementation_manager.py validate` uses local parser — validation results diverge from what sam_schema actually accepts. A task file that passes validation may fail to parse at runtime.
- `swarm-task-planner` writes schema based on an embedded copy in the prompt. If sam_schema models evolve (new required fields, renamed fields), the planner produces non-conforming files until the prompt is manually updated.

**Cascading effects (from Impact Radius):**

- `task_format.py` (C3) is the shared dependency of the broken paths. Removing it to force sam_schema adoption breaks `migrate_task_format.py` (P4) which imports it directly.
- `test_task_parsing.py` (C5) tests only the old parser — provides false confidence that task parsing works when the sam_schema path is untested by it.
- development-harness parallel copies (P2, A13-A19) contain identical broken patterns. Any fix to the python3-development components that is not mirrored to development-harness creates a split-brain state where the same workflow behaves differently depending on which plugin is active.
- Workshop copies (A20-A23) are user-facing teaching materials. Stale examples teach direct file manipulation as the correct pattern, producing user code that bypasses sam_schema.
- Backlog MCP server SAM operations (C6-C10) — parser dependency unverified. If any of these use a local parser, backlog sync operations that touch task files can corrupt state written by sam_schema consumers.

**Bottleneck**: `task_format.py` (C3) removal is gated by migration of all consumers. C3 cannot be removed until C1, C2, P4 are migrated, which is gated on conditions 4-6 (new CLI commands: `create`, `update`, plan-context-in-`read`).
</div>

### Reproducibility

<div><sub>2026-03-15T07:02:56Z</sub>

Observed in `task_status_hook.py` — the split-parser component (highest-risk):

1. Run a SAM workflow that produces a `.md` task file (legacy format) — e.g., any task file generated before the YAML-only migration.
2. A sub-agent finishes its assigned task, triggering the `SubagentStop` hook.
3. `task_status_hook.py` enters `handle_subagent_stop()` and branches on `resolved_path.suffix == ".yaml"` (lines 548-557).
4. For `.yaml` files: calls `sam_update_status()` from sam_schema — correct path.
5. For `.md` files: calls own `update_task_status()` / `add_timestamp_to_task()` from `task_format.py` — divergent parser path.
6. The `.md` parser uses `parse_yaml_frontmatter` + regex. If the task was previously written by the sam_schema writer (which normalizes field names), the regex may fail to match, silently leaving the task status unchanged.
7. The workflow engine reads status via `implementation_manager.py ready-tasks`, which uses `sam_schema` — but the status was never written because the hook's `.md` branch failed silently.

The same format mismatch is observable in `implementation_manager.py claim-task`: run `uv run implementation_manager.py claim-task {task_file} T1` against a YAML-format task file. The claim logic uses `parse_task_content()` with raw `"\n---\n"` string splitting (line 1402) instead of sam_schema writers. On a multi-document YAML file with non-standard separators, this produces garbled output or a no-op write.
</div>

### Output / Evidence

<div><sub>2026-03-15T07:03:13Z</sub>

All claims below are VERIFIED by fact-check agent (2026-03-15):

- **4 independent parsers confirmed**: (1) `sam_schema` readers/writers, (2) `task_format.py` (`parse_yaml_frontmatter` + `update_yaml_field`), (3) `implementation_manager.py` `parse_task_file()`, (4) `implementation_manager.py` `parse_task_content()` with raw `"\n---\n"` splitting.

- **Split-parser in `task_status_hook.py`**: Branch at lines 548-557 (`handle_subagent_stop`) and 615-624 (`handle_activity_update`) — `.yaml` uses `sam_update_status()`, `.md` uses `update_task_status()`. Fact-check Claim 3 VERIFIED with exact line numbers.

- **`claim-task` bypasses sam_schema**: `implementation_manager.py` line 1402 applies claim via raw `_apply_claim_to_content()` using string splitting. `validate` command (line 1245) calls `parse_task_file()` — local parser, not sam_schema. Fact-check Claim 4 VERIFIED.

- **`sam read` discards plan context**: `get_task()` in `packages/sam_schema/sam_schema/core/query.py` lines 44-63 returns single `Task` model. Plan-level fields (`goal`, `context`, `acceptance_criteria`) loaded by `load_plan()` but discarded. Fact-check Claim 6 VERIFIED.

- **No `sam create` command**: CLI at `packages/sam_schema/sam_schema/cli.py` defines exactly 5 subcommands: `read`, `state`, `ready`, `status`, `migrate`. No `create`. Fact-check Claim 5 VERIFIED.

- **swarm-task-planner schema is embedded copy**: Lines 258-320 of `plugins/python3-development/agents/swarm-task-planner.md` contain full YAML frontmatter schema copy-pasted into the prompt. No reference to sam_schema. Fact-check Claim 1 VERIFIED.

- **Impact radius**: 72 affected files — 5 code producers, 10 code consumers, 27 agent instruction files, 11 documentation files, 3 configuration files, 10 test file groups. Source: Impact Radius section (2026-03-15).
</div>

### Priority

<div><sub>2026-03-15T07:03:23Z</sub>

9/10 — P0

The missing guardrail produces silent data loss on task status writes in any SAM workflow using `.md` format task files. The `task_status_hook.py` `.md` branch silently fails to write status when field names have been normalized by sam_schema writers. When status is not written, `implementation_manager.py ready-tasks` (which reads via sam_schema) never sees the task as COMPLETE, causing the implementation loop to stall or re-dispatch already-completed tasks.

The `claim-task` raw string splitting bypasses all sam_schema validation, meaning concurrent writes or multi-doc YAML files can produce corrupted task state with no error surface.

72 files are stale. The problem is structural — fixing individual parsers without an enforced interface contract leaves the next component free to introduce a fifth parser. The guardrail must be the fix, not parser-by-parser remediation.
</div>

### Benefits

<div><sub>2026-03-15T07:03:53Z</sub>

- Silent data loss on task status writes is eliminated — `task_status_hook.py` has one code path for all formats.
- `claim-task` concurrency safety is handled by sam_schema writers instead of raw string splitting.
- Format evolution (new fields, renamed fields, new backing stores) requires changes only in sam_schema — no component-by-component prompt updates.
- `swarm-task-planner` can produce valid task files for any future backing store (YAML file, split directory, GitHub sub-issue, SQLite) without knowing the storage format.
- `start-task` agents receive plan goal and shared context alongside their task details in a single `sam read` call — no need to read the full file and scan manually.
- Enables future backing stores: sam_schema as the sole interface means the storage layer can be swapped (e.g., from `.yaml` files to GitHub sub-issues) without changing any consumer.
- `task_format.py` can be removed — eliminates a dead code module and its test suite, reducing maintenance surface.
- development-harness and workshop copies have a single source of truth to stay in sync with.
- Unblocks #715 (sam_schema MCP integration) and #714 (task file format stabilization) by establishing the contract those items depend on.
</div>

### Expected Behavior

<div><sub>2026-03-15T07:04:07Z</sub>

After integration, each component behaves as follows — observable from outside, not describing implementation internals:

**swarm-task-planner**: Produces task files by calling `sam create` with plan metadata. The resulting file is valid according to `sam validate` regardless of backing format. No inline schema copy in the agent prompt.

**start-task**: Calls `sam read {slug}/{task-id}` and receives plan goal, shared context, and task-specific fields in one response. Does not open the task file. Calls `sam state {slug}/{task-id} in-progress` to claim the task.

**task_status_hook**: Calls `sam state {slug}/{task-id} complete` for every task completion, regardless of whether the task file is `.yaml`, `.md`, or a split directory. No file-extension branch.

**implementation_manager**: Calls `sam validate {slug}` and `sam claim-task {slug}/{task-id}` through sam_schema for all operations. No local parser code paths. `task_format.py` is not imported.

**implement-feature**: Calls `sam status {slug}` and `sam ready {slug}` to drive the execution loop. No invocation of `implementation_manager.py` for status queries.

**complete-implementation**: Passes `sam read` output (not raw file paths) to quality gate agents. Agents do not need to open task files.

**context-gathering / context-refinement**: Calls `sam update {slug} --context "..."` to append the Context Manifest. Does not use Read + Edit on the task file directly.

When any component calls a sam CLI command against a task file in any supported format, the command succeeds and the result is consistent with what other components read from the same address.
</div>

### Acceptance Criteria

<div><sub>2026-03-15T07:04:26Z</sub>

1. `grep -r "task_format" plugins/python3-development/skills/implementation-manager/scripts/` returns no matches (task_format.py removed from all consumers in that directory).

2. `grep -r "parse_yaml_frontmatter\|parse_task_file\|parse_task_content" plugins/python3-development/skills/implementation-manager/scripts/` returns no matches (local parsers removed).

3. `task_status_hook.py` contains no branch on `resolved_path.suffix == ".yaml"` — the branch is gone, not replaced with a different extension check.

4. `uv run sam create --slug test-integration --goal "verify create command"` exits 0 and produces a file readable by `sam read test-integration/T1` (end-to-end create-then-read round-trip).

5. `uv run sam read {slug}/{task-id}` output includes `goal`, `context`, and `acceptance_criteria` fields from the parent plan alongside task-specific fields.

6. `uv run sam update {slug} --context "test context value"` exits 0 and `sam read {slug}/{any-task-id}` subsequently returns the updated context value.

7. `swarm-task-planner.md` (both `plugins/python3-development/agents/` and `plugins/development-harness/agents/`) contains no inline YAML schema definition — field definitions are referenced by name, not copy-pasted.

8. `plugins/python3-development/skills/start-task/SKILL.md` contains no instruction to use the `Read` tool to open a task file — task reading is described via `sam read`.

9. `plugins/python3-development/agents/context-gathering.md` and `plugins/development-harness/agents/context-gathering.md` contain no instruction to use `Edit` to append Context Manifest — the append is described via `sam update`.

10. `uv run pytest plugins/python3-development/skills/implementation-manager/tests/` passes with no skipped tests related to parser changes (tests have been updated to exercise sam_schema interface, not task_format.py).

11. `grep -r "task_format" plugins/development-harness/` returns no matches (development-harness parallel copies also migrated).

12. `grep -r "Read tool\|Edit tool" workshops/.claude/skills/implement-embedded-feature/SKILL.md workshops/.cursor/skills/implement-embedded-feature/SKILL.md | grep "task file"` returns no matches (workshop copies updated).

13. `cat .claude/docs/TASK_FILE_FORMAT.md | grep "sam read\|sam state\|sam create"` returns at least 3 matches — the document describes sam CLI as the canonical interface.

14. `uv run sam state {slug}/{task-id} complete` called on a `.md`-format task file exits 0 and `sam read {slug}/{task-id}` returns `status: complete` (format-agnostic state write confirmed).
</div>

### Files

<div><sub>2026-03-15T07:04:41Z</sub>

**Primary components (7 SAM workflow components):**

- `plugins/python3-development/agents/swarm-task-planner.md` — writes task files; inline schema at lines 258-320
- `plugins/python3-development/skills/start-task/SKILL.md` — reads task files via Read tool
- `plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py` — split parser; branch at lines 548-557, 615-624
- `plugins/python3-development/skills/implementation-manager/scripts/implementation_manager.py` — partial sam_schema; local parsers in `validate` (line 1245) and `claim-task` (line 1402)
- `plugins/python3-development/skills/implement-feature/SKILL.md` — calls implementation_manager.py CLI
- `plugins/python3-development/skills/complete-implementation/SKILL.md` — passes raw file paths to agents
- `plugins/python3-development/agents/context-gathering.md` — Read+Edit pattern for Context Manifest

**Module being replaced:**

- `plugins/python3-development/skills/implementation-manager/scripts/task_format.py` — shared YAML utilities; all consumers must migrate before this is removed

**sam_schema gaps (new CLI commands needed):**

- `packages/sam_schema/sam_schema/cli.py` — add `create` and `update` subcommands
- `packages/sam_schema/sam_schema/core/query.py` — `get_task()` lines 44-63; plan fields discarded

**development-harness parallel copies:**

- `plugins/development-harness/agents/swarm-task-planner.md`
- `plugins/development-harness/agents/context-gathering.md`
- `plugins/development-harness/agents/context-refinement.md`
- `plugins/development-harness/skills/implementation-manager/SKILL.md`

**Key test files:**

- `plugins/python3-development/skills/implementation-manager/scripts/test_task_parsing.py` — tests old parser; must be rewritten or removed
- `plugins/python3-development/skills/implementation-manager/tests/test_task_status_hook/test_subagent_stop_integration.py` — needs update when hook parser is unified

**Documentation (confirmed stale):**

- `.claude/docs/TASK_FILE_FORMAT.md`
- `.claude/rules/local-workflow.md`
- `.claude/docs/sdlc-layers/layer-0/sam-pipeline.md`
</div>

### Resources

<div><sub>2026-03-15T07:04:55Z</sub>

| Type | Item |
|------|------|
| Related backlog | #715 — sam_schema MCP integration (unblocked by this item) |
| Related backlog | #716 — sam_schema follow-up: multi-doc YAML, compound IDs (may be sequenced before or folded in) |
| Related backlog | #714 — task file format stabilization (depends on this item's naming convention decision) |
| Analysis report | Impact Radius section in `.claude/backlog/p0-integrate-samschema-as-sole-task-file-interface-across-all-s.md` — 72-file inventory across 6 categories with critical path |
| Analysis report | Fact-Check section in same file — all 7 claims VERIFIED with exact file:line references |
| Analysis report | RT-ICA Final section in same file — 18 conditions, 4 AVAILABLE, 5 DERIVABLE, 6 MISSING, 1 UNKNOWN |
| Prior work | `packages/sam_schema/` — the target interface; 421 tests, 93% coverage |
| Prior work | `packages/sam_schema/sam_schema/cli.py` — existing 5 subcommands (read, state, ready, status, migrate) |
| Prior work | `packages/sam_schema/sam_schema/core/models.py` — Plan model with goal/context/acceptance_criteria fields (line 175) |
| Prior work | `packages/sam_schema/sam_schema/core/query.py` — get_task() that discards plan context (lines 44-63) |
| Docs | `.claude/docs/TASK_FILE_FORMAT.md` — current (stale) format description |
| Docs | `.claude/rules/local-workflow.md` — SAM workflow documentation (stale CLI references) |
</div>

### Dependencies

<div><sub>2026-03-15T07:05:12Z</sub>

**Depends on:**

- #716 (sam_schema follow-up: multi-doc YAML updates, ty diagnostic fixes) — RT-ICA marks this DERIVABLE; can be sequenced before Phase 1 or folded into it. The `claim-task` raw string splitting on `"\n---\n"` is directly affected by multi-doc YAML behavior. Recommend completing #716 before starting Phase 2 (core consumer migration).
- Plan file naming convention decision (RT-ICA condition 11: MISSING) — `P{N}-{slug}` vs `tasks-{N}-{slug}` must be codified before `sam create` command is designed, since addressing scheme depends on the convention.
- Verification of backlog MCP server SAM operations (C6-C10, RT-ICA condition 16: UNKNOWN) — must be audited as the first task before Phase 2 begins; if these files use a local parser they join the migration scope.

**Blocks (items waiting on this):**

- #715 — sam_schema MCP integration; depends on the MCP server having a stable, enforced interface that this item establishes.
- #714 — task file format stabilization; the naming convention and field set locked by this item are what #714 depends on.
- Any future backing-store migration (GitHub sub-issues as task store, SQLite) — impossible to implement safely while consumers bypass the sam_schema interface.

**Critical path within this item:**

`task_format.py` removal gates on C1/C2 migration → C1/C2 migration gates on `sam create`, `sam update`, and plan-context-in-`read` (conditions 4-6) → those three CLI gaps are Phase 1.
</div>

### Effort

<div><sub>2026-03-15T07:05:26Z</sub>

High — 72 affected files across 5 phases.

Phase breakdown:

- **Phase 1 — sam_schema CLI/MCP gaps** (conditions 4-6): `sam create`, `sam update`, plan-context-in-`read`. 3 new CLI subcommands + MCP tool entries + unit tests for each. Medium effort standalone; gating dependency for all other phases.

- **Phase 2 — Core consumer migration** (C1-C3): Migrate `implementation_manager.py` (remove fallback parser for validate/claim-task), migrate `task_status_hook.py` (unify on sam_schema for all formats), remove `task_format.py` and its tests. High complexity — `claim-task` and `task_status_hook` are used in live workflow execution; regressions produce silent data loss.

- **Phase 3 — Agent instruction updates** (A1-A27, 27 files): Update `start-task`, `implement-feature`, `complete-implementation`, `context-gathering`, `context-refinement`, `swarm-task-planner` (both plugins), plus development-harness and workshop copies. Mechanical but high volume; each file requires careful diff to avoid introducing new errors.

- **Phase 4 — Documentation** (D1-D11, 11 files): Update `TASK_FILE_FORMAT.md`, `local-workflow.md`, `sam-pipeline.md`, plugin READMEs, ADRs. Low complexity per file; high volume.

- **Phase 5 — Tests** (T1-T9): Update or rewrite 9 test file groups to exercise sam_schema interface instead of task_format.py. `test_task_parsing.py` must be rewritten from scratch.

Total: 3 new CLI commands + removal of 1 module + updates to 27 agent files + 11 docs + 9 test groups. Parallelizable across phases 3/4/5 once phase 2 is complete. Phase 1 is the critical gating dependency.
</div>

### Decision

<div><sub>2026-03-15T07:59:59Z</sub>
<details><summary>struck: 2026-03-15T08:05:57Z — Simplified: allow collisions since slugs are unique identifiers</summary>

**Plan file naming convention (resolved 2026-03-15)**:

Pattern follows GSD's hierarchical naming (observed in `/home/ubuntulinuxqa2/repos/gsd-2/.gsd/milestones/M001/slices/S01/tasks/T01-PLAN.md`):

**Convention**: `P{NNN}-{slug}` with zero-padded sequential numbering.

Single file (under 500 lines):
```
plan/P001-backlog-state-reconciliation.yaml
```

Split directory (over 500 lines):
```
plan/P001-backlog-state-reconciliation/
├── P001-PLAN.yaml        # plan-level metadata, goal, context, task list
├── P001-ARCHITECT.md      # architecture spec
├── P001-CONTEXT.md        # feature context
└── tasks/
    ├── T01.yaml
    ├── T02.yaml
    └── T03.yaml
```

**Numbering**: Sequential, local. `sam create` scans `plan/P*`, extracts highest NNN, writes `P{NNN+1}`. No GitHub dependency for numbering.

**Collision handling**: Two branches both increment to the same number. On merge, `sam` CLI detects duplicate P numbers (two `P004-*` entries) and renumbers the newer one (by git commit date) to `max+1`. This is a post-merge fixup, not a blocker.

**Task numbering**: `T{NN}` zero-padded, local to the plan. `T01` in `P001` is independent of `T01` in `P002`.

**Addressing**: `sam read P1/T3` resolves by globbing `plan/P001-*/` and finding `T03.yaml` inside. The zero-padding means `P1` matches `P001-*`.
</details>
</div>

<div><sub>2026-03-15T08:05:57Z</sub>

**Plan file naming convention (resolved 2026-03-15)**:

Pattern follows GSD's hierarchical naming (observed in `/home/ubuntulinuxqa2/repos/gsd-2/.gsd/milestones/M001/slices/S01/tasks/T01-PLAN.md`):

**Convention**: `P{NNN}-{slug}` with zero-padded sequential numbering.

Single file (under 500 lines):
```
plan/P001-backlog-state-reconciliation.yaml
```

Split directory (over 500 lines):
```
plan/P001-backlog-state-reconciliation/
├── P001-PLAN.yaml        # plan-level metadata, goal, context, task list
├── P001-ARCHITECT.md      # architecture spec
├── P001-CONTEXT.md        # feature context
└── tasks/
    ├── T01.yaml
    ├── T02.yaml
    └── T03.yaml
```

**Numbering**: Sequential, local. `sam create` scans `plan/P*`, extracts highest NNN, writes `P{NNN+1}`. No GitHub dependency for numbering.

**Collision handling**: Allowed. The slug makes each plan unique — `P004-backlog-state-reconciliation` and `P004-sam-schema-followup` are unambiguous. The number is for sort order, not identity. No renaming needed on merge.

**Task numbering**: `T{NN}` zero-padded, local to the plan. `T01` in `P001` is independent of `T01` in `P002`.

**Addressing**: `sam read P1/T3` resolves by globbing `plan/P001-*/` and finding `T03.yaml` inside. If multiple plans share a number (collision), the slug disambiguates: `sam read backlog-state-reconciliation/T3`.
</div>


## Affected Systems Inventory — Backlog #719

### Code Producers (files that WRITE task files)

| # | File | Current Behavior | Breaks? | Stale? | Code Change? | Content Update? | Test Coverage? |
|---|------|-----------------|---------|--------|-------------|----------------|---------------|
| P1 | `plugins/python3-development/agents/swarm-task-planner.md` | Writes task files via Write tool with schema embedded in agent prompt | No — Write tool produces files sam_schema can read | YES — embedded schema description diverges from sam_schema canonical models | No | YES — replace inline schema with sam_schema field reference | No |
| P2 | `plugins/development-harness/agents/swarm-task-planner.md` | Parallel copy of P1 for non-Python projects | Same as P1 | YES | No | YES | No |
| P3 | `plugins/python3-development/scripts/split_task_file.py` | Splits monolithic task files; imports sam_schema | No — already uses sam_schema | No | MAYBE — verify it uses sam_schema exclusively, no fallback parser | No | No |
| P4 | `plugins/python3-development/scripts/migrate_task_format.py` | Migrates legacy markdown to YAML frontmatter; references task_format.py | YES — if task_format.py is removed | YES — references deprecated module | YES — switch to sam_schema readers/writers | No | No |
| P5 | `plugins/python3-development/scripts/migrate_tasks_to_github.py` | Migrates task files to GitHub sub-issues | MAYBE — depends on parser used | MAYBE | YES — verify/switch to sam_schema | No | YES — `tests/test_migrate_tasks_to_github.py` |

### Code Consumers (files that READ/PARSE task files)

| # | File | Current Behavior | Breaks? | Stale? | Code Change? | Content Update? | Test Coverage? |
|---|------|-----------------|---------|--------|-------------|----------------|---------------|
| C1 | `plugins/python3-development/skills/implementation-manager/scripts/implementation_manager.py` | sam_schema primary, own parser fallback | No — already uses sam_schema | YES — fallback parser is dead code target | YES — remove fallback parser | No | YES — `tests/test_implementation_manager/test_github_flag.py` |
| C2 | `plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py` | Split parser: sam_schema for .yaml, own parser for .md | YES — if .md fallback removed without migration | YES — dual-parser is the core problem | YES — unify on sam_schema for all formats | No | YES — `tests/test_task_status_hook/test_github_sync.py`, `test_subagent_stop_integration.py` |
| C3 | `plugins/python3-development/skills/implementation-manager/scripts/task_format.py` | Shared YAML frontmatter utilities; imported by C1, C2 | YES — this is the module being replaced | YES — entire module becomes dead code | YES — remove after all consumers migrate | No | No dedicated tests |
| C4 | `plugins/python3-development/skills/implementation-manager/scripts/get_task_context.py` | Dynamic context injection; reads active-task JSON | MAYBE — depends on how it reads task files | MAYBE | YES — verify/switch to sam_schema | No | No |
| C5 | `plugins/python3-development/skills/implementation-manager/scripts/test_task_parsing.py` | Test script for task parsing | YES — tests the old parser | YES | YES — rewrite to test sam_schema interface | No | Is a test |
| C6 | `.claude/skills/backlog/backlog_core/server.py` | Backlog MCP server with SAM task operations | MAYBE — depends on internal parser | MAYBE | YES — verify uses sam_schema | No | YES — `.claude/skills/backlog/tests/test_server_sam.py` |
| C7 | `.claude/skills/backlog/backlog_core/operations.py` | Backlog operations including SAM task CRUD | MAYBE | MAYBE | YES — verify uses sam_schema | No | YES — `.claude/skills/backlog/tests/test_operations_sam.py` |
| C8 | `.claude/skills/backlog/backlog_core/parsing.py` | Backlog parsing with SAM task awareness | MAYBE | MAYBE | YES — verify uses sam_schema | No | YES — `.claude/skills/backlog/tests/test_backlog_core_parsing.py` |
| C9 | `.claude/skills/backlog/backlog_core/models.py` | Backlog models with SAM task fields | No — data models, not parsers | No | No | No | No |
| C10 | `.claude/skills/backlog/backlog_core/github.py` | GitHub sync for SAM tasks | MAYBE | MAYBE | YES — verify uses sam_schema | No | YES — `.claude/skills/backlog/tests/test_backlog_core_github.py` |

### Documentation (files that DESCRIBE task file format or workflow)

| # | File | Breaks? | Stale? | Code Change? | Content Update? | Test? |
|---|------|---------|--------|-------------|----------------|-------|
| D1 | `.claude/docs/TASK_FILE_FORMAT.md` | No | YES — describes direct-file access patterns | N/A | YES — update to describe sam_schema CLI/MCP as canonical interface | No |
| D2 | `.claude/rules/local-workflow.md` | No | YES — documents implementation_manager.py CLI commands, task_status_hook.py behavior, direct file parsing | N/A | YES — update CLI references to sam_schema equivalents | No |
| D3 | `.claude/docs/plan-artifact-lifecycle.md` | No | MAYBE — references task file mutation paths | N/A | MAYBE — verify mutation path descriptions | No |
| D4 | `.claude/docs/sdlc-layers/layer-0/sam-pipeline.md` | No | YES — describes SAM pipeline architecture | N/A | YES — update to reflect sam_schema as sole interface | No |
| D5 | `.claude/docs/sdlc-layers/layer-0/task-file-format.md` | No | YES — duplicate/overlay of D1 | N/A | YES — align with sam_schema | No |
| D6 | `.claude/decisions/ADR-010-task-file-field-name-standard.md` | No | MAYBE — field names may need sam_schema alignment note | N/A | MAYBE — add note that sam_schema is canonical implementation | No |
| D7 | `.claude/decisions/ADR-011-compat-annotation-standard.md` | No | MAYBE | N/A | MAYBE | No |
| D8 | `plugins/python3-development/README.md` | No | YES — references implementation_manager.py directly | N/A | YES | No |
| D9 | `plugins/development-harness/README.md` | No | YES — references task file patterns | N/A | YES | No |
| D10 | `plugins/python3-development/docs/ONE-TASK-PER-FILE-IMPLEMENTATION.md` | No | MAYBE — documents task file structure | N/A | MAYBE | No |
| D11 | `.claude/skills/backlog/CLI_TO_MCP_MIGRATION.md` | No | MAYBE — may reference old task interfaces | N/A | MAYBE | No |

### Agent Instructions (agent/skill files that instruct AI to interact with task files)

| # | File | Breaks? | Stale? | Code Change? | Content Update? | Test? |
|---|------|---------|--------|-------------|----------------|-------|
| A1 | `plugins/python3-development/skills/start-task/SKILL.md` | No — reads via Read tool, writes via Edit | YES — instructs direct file manipulation instead of sam_schema CLI | N/A | YES — update to use sam CLI for status changes | No |
| A2 | `plugins/python3-development/skills/implement-feature/SKILL.md` | No — calls implementation_manager.py CLI | MAYBE — CLI commands may change | N/A | YES — update CLI invocations to sam_schema equivalents | No |
| A3 | `plugins/python3-development/skills/complete-implementation/SKILL.md` | No — passes file paths to agents | No | N/A | MAYBE — verify path conventions still hold | No |
| A4 | `plugins/python3-development/skills/implementation-manager/SKILL.md` | No | YES — documents old CLI commands | N/A | YES — update command reference | No |
| A5 | `plugins/python3-development/skills/add-new-feature/SKILL.md` | No | MAYBE — references task file output | N/A | MAYBE | No |
| A6 | `plugins/python3-development/skills/create-feature-task/SKILL.md` | No | MAYBE | N/A | MAYBE | No |
| A7 | `plugins/python3-development/agents/context-gathering.md` | No — reads via Read, appends via Edit | YES — direct file manipulation | N/A | YES — update to use sam_schema | No |
| A8 | `plugins/python3-development/agents/context-refinement.md` | No | YES — same pattern as A7 | N/A | YES | No |
| A9 | `plugins/python3-development/agents/code-reviewer.md` | No | MAYBE — may reference task file structure | N/A | MAYBE | No |
| A10 | `plugins/python3-development/agents/feature-verifier.md` | No | MAYBE | N/A | MAYBE | No |
| A11 | `plugins/python3-development/agents/plan-validator.md` | No | MAYBE — validates task file structure | N/A | MAYBE | No |
| A12 | `plugins/python3-development/agents/integration-checker.md` | No | MAYBE | N/A | MAYBE | No |
| A13 | `plugins/development-harness/skills/implementation-manager/SKILL.md` | No | YES — parallel copy, references task_status_hook | N/A | YES | No |
| A14 | `plugins/development-harness/agents/context-gathering.md` | No | YES — parallel copy of A7 | N/A | YES | No |
| A15 | `plugins/development-harness/agents/context-refinement.md` | No | YES — parallel copy of A8 | N/A | YES | No |
| A16 | `plugins/development-harness/agents/swarm-task-planner.md` | No | YES — parallel copy of P1/P2 | N/A | YES | No |
| A17 | `plugins/development-harness/agents/plan-validator.md` | No | MAYBE | N/A | MAYBE | No |
| A18 | `plugins/development-harness/agents/feature-verifier.md` | No | MAYBE | N/A | MAYBE | No |
| A19 | `plugins/development-harness/agents/integration-checker.md` | No | MAYBE | N/A | MAYBE | No |
| A20 | `workshops/.claude/skills/implement-embedded-feature/SKILL.md` | No | YES — workshop copy with task file patterns | N/A | YES | No |
| A21 | `workshops/.claude/skills/add-embedded-feature/SKILL.md` | No | MAYBE | N/A | MAYBE | No |
| A22 | `workshops/.cursor/skills/implement-embedded-feature/SKILL.md` | No | YES — Cursor copy | N/A | YES | No |
| A23 | `workshops/.cursor/skills/add-embedded-feature/SKILL.md` | No | MAYBE | N/A | MAYBE | No |
| A24 | `plugins/plugin-creator/skills/start-refactor-task/SKILL.md` | No | MAYBE — parallel task system for plugin refactoring | N/A | MAYBE — depends on whether it shares task format | No |
| A25 | `plugins/plugin-creator/skills/implement-refactor/SKILL.md` | No | MAYBE | N/A | MAYBE | No |
| A26 | `.claude/skills/work-backlog-item/SKILL.md` | No | MAYBE — references task file workflow | N/A | MAYBE | No |
| A27 | `.claude/skills/verify/SKILL.md` | No | MAYBE | N/A | MAYBE | No |

### Configuration and CI

| # | File | Impact | Notes |
|---|------|--------|-------|
| CF1 | `pyproject.toml` | MAYBE — sam_schema workspace dependency | Verify sam_schema is in workspace members |
| CF2 | `packages/sam_schema/pyproject.toml` | No — this IS sam_schema | May need new CLI entry points |
| CF3 | No hooks.json files found | N/A | Hook references are in SKILL.md frontmatter, not separate JSON |

### Test Files

| # | File | Covers | Impact |
|---|------|--------|--------|
| T1 | `plugins/python3-development/skills/implementation-manager/tests/test_task_status_hook/test_github_sync.py` | C2 (task_status_hook.py) | YES — needs update when parser changes |
| T2 | `plugins/python3-development/skills/implementation-manager/tests/test_task_status_hook/test_subagent_stop_integration.py` | C2 (task_status_hook.py) | YES — needs update |
| T3 | `tests/test_implementation_manager/test_github_flag.py` | C1 (implementation_manager.py) | YES — needs update when fallback removed |
| T4 | `plugins/python3-development/skills/implementation-manager/scripts/test_task_parsing.py` | C3 (task_format.py) | YES — rewrite or remove |
| T5 | `.claude/skills/backlog/tests/test_operations_sam.py` | C7 (operations.py) | MAYBE — verify sam_schema integration |
| T6 | `.claude/skills/backlog/tests/test_server_sam.py` | C6 (server.py) | MAYBE — verify sam_schema integration |
| T7 | `.claude/skills/backlog/tests/test_backlog_core_parsing.py` | C8 (parsing.py) | MAYBE |
| T8 | `.claude/skills/backlog/tests/test_backlog_core_github.py` | C10 (github.py) | MAYBE |
| T9 | `tests/test_migrate_tasks_to_github.py` | P5 (migrate_tasks_to_github.py) | YES — if script is updated |
| T10 | `packages/sam_schema/tests/*` (17 test files) | sam_schema package itself | No — these ARE the target interface tests |

### Systems Inventory Summary

**Total affected files**: 72 (excluding plan/ artifacts, .claude/archive/, test fixtures)

- Code Producers: 5 files (P1-P5)
- Code Consumers: 10 files (C1-C10)
- Documentation: 11 files (D1-D11)
- Agent Instructions: 27 files (A1-A27)
- Configuration: 3 files (CF1-CF3)
- Tests: 10 test file groups (T1-T10)
- sam_schema package itself: ~30 files (the target interface — no changes needed beyond new CLI/MCP endpoints)

### Ecosystem Completeness Checklist

- [x] All 7 starting points expanded
- [x] development-harness parallel copies identified (A13-A19, P2)
- [x] Workshop copies identified (A20-A23)
- [x] plugin-creator parallel task system checked (A24-A25 — separate system, lower impact)
- [x] Backlog MCP server SAM operations identified (C6-C10)
- [x] All test files mapped to their subjects
- [x] Documentation at all layers checked (CLAUDE.md rules, SDLC layers, ADRs, READMEs)
- [x] No hooks.json files — hook config is in SKILL.md frontmatter
- [x] Migration scripts identified (P4, P5)
- [ ] NOT checked: `.claude/skills/backlog/backlog_core/` internal imports — need agent to verify whether these already use sam_schema or have their own parser

### Critical Path (files that WILL break or block without changes)

1. **C3 task_format.py** — the module being replaced; all its consumers must migrate first
2. **C2 task_status_hook.py** — split parser is the highest-risk consumer
3. **C1 implementation_manager.py** — fallback parser removal
4. **P4 migrate_task_format.py** — imports task_format.py directly
5. **C5 test_task_parsing.py** — tests the old parser exclusively

### Recommended Sequencing

1. First: Verify C6-C10 (backlog server) already use sam_schema — if not, they need migration too
2. Second: Migrate C1, C2 to sam_schema-only (remove fallback parsers)
3. Third: Update P4 migration script or deprecate it
4. Fourth: Remove C3 (task_format.py) and C5 (test_task_parsing.py)
5. Fifth: Update all documentation (D1-D11) and agent instructions (A1-A27)
6. Last: Update test files (T1-T9) to match new interfaces
</div>


## Fact-Check

<div><sub>2026-03-15T06:59:06Z</sub>

## Fact-Check Results (2026-03-15)

### Claim 1: "swarm-task-planner writes task files via Write tool with schema embedded in agent prompt"

**VERIFIED.** The agent file at `plugins/python3-development/agents/swarm-task-planner.md` contains the full task YAML frontmatter schema inline (lines 258-320) with field definitions for `task`, `title`, `status`, `agent`, `dependencies`, `priority`, `complexity`, `accuracy-risk`, `skills`, `parallelize-with`, `reason`, `handoff`. The agent uses `Write` tool (listed in frontmatter line 4: `tools: Read, Write, Edit, Glob, Grep, ...`). There is no import or reference to `sam_schema` anywhere in the agent file — the schema is copy-pasted into the prompt.

### Claim 2: "start-task reads full task file via Read tool, finds its task by scanning"

**PARTIALLY VERIFIED / NUANCED.** The skill at `plugins/python3-development/skills/start-task/SKILL.md` instructs the agent to "Read the task file" (line 66) and detect format (lines 36-43). However, for claiming the task it delegates to `implementation_manager.py claim-task` (lines 82-94), not raw scanning. The agent does read the file to detect format and select a task, but the actual status mutation goes through the CLI tool. The claim is accurate about reading — the agent reads the full file and scans for its task — but incomplete about the claim mechanism.

### Claim 3: "task_status_hook uses sam_schema for .yaml files, own parser for .md files"

**VERIFIED.** In `task_status_hook.py`:
- Lines 48-53: imports `sam_schema` (`SamTaskStatus`, `sam_update_status`, `sam_update_field`)
- Lines 34-40: imports own parser (`task_format`: `has_yaml_frontmatter`, `parse_yaml_frontmatter`, `update_yaml_field`)
- `handle_subagent_stop()` lines 548-557: branches on `resolved_path.suffix == ".yaml"` — uses `sam_update_status()` for `.yaml`, uses own `update_task_status()`/`add_timestamp_to_task()` for `.md`
- `handle_activity_update()` lines 615-624: same branching — `sam_update_field()` for `.yaml`, own `add_timestamp_to_task()` for `.md`

### Claim 4: "implementation_manager uses sam_schema as primary reader for status/ready-tasks, but own parser for validate/claim-task"

**VERIFIED.** In `implementation_manager.py`:
- Line 63: `from sam_schema.core.query import load_plan as sam_load_plan`
- `status` command (line 1141): calls `_load_tasks_via_sam(task_file)` which uses `sam_load_plan` (line 1051)
- `ready_tasks` command (line 1211): calls `_load_tasks_via_sam(task_file)`
- `validate` command (line 1245): calls `parse_task_file(task_file)` — the local parser, NOT sam_schema
- `claim_task` command (line 1463): calls `parse_task_content(file_content)` — the local parser. Write path uses `_apply_claim_to_content()` (line 1402) which does raw string splitting on `"\n---\n"` separators, NOT sam_schema writers.

### Claim 5: "sam CLI create command does not exist"

**VERIFIED.** The CLI at `packages/sam_schema/sam_schema/cli.py` defines exactly 5 subcommands: `read` (line 148), `state` (line 194), `ready` (line 247), `status` (line 276), `migrate` (line 311). No `create` command exists.

### Claim 6: "sam read returns task only, not plan goal + context"

**VERIFIED.** In `packages/sam_schema/sam_schema/core/query.py`, `get_task()` (lines 44-63) returns a single `Task` model. The CLI `read` command (cli.py line 175) calls `get_task()` and dumps `task.model_dump()`. The `Plan` model fields (`goal`, `context`, `acceptance_criteria`) are never surfaced through the `read` subcommand. The plan-level fields are loaded internally by `load_plan()` but discarded when extracting a single task.

### Claim 7: "Plan model now has goal, context, acceptance_criteria fields"

**VERIFIED.** In `packages/sam_schema/sam_schema/core/models.py`, the `Plan` class (line 175) contains:
- `goal: str | None = None` (line 192)
- `context: str | None = None` (line 193)
- `acceptance_criteria: str | None = Field(default=None, alias="acceptance-criteria")` (line 194)

These are documented as "Plan-level context fields (multiline markdown)" (line 191).

### Summary

All 7 claims are **VERIFIED** (Claim 2 is verified with a nuance about the claim mechanism, but the core assertion about reading and scanning is accurate). The backlog item's description accurately reflects the current codebase state.
</div>

## RT-ICA

<div><sub>2026-03-15T08:18:35Z</sub>

**RT-ICA Final** (corrected 2026-03-15, naming convention resolved)

**Goal**: All 7 SAM workflow components access task files exclusively through sam_schema CLI/MCP interface.

**Conditions**:

1. sam_schema module capabilities documented | **AVAILABLE** | packages/sam_schema/ — 421 tests, 93% coverage, CLI + MCP
2. Exact data each component reads/writes from task files | **AVAILABLE** | traced via 7 Explore agents with verbatim quotes
3. Agent prompt file paths for all 7 components | **AVAILABLE** | paths confirmed by Explore traces
4. Impact radius — full inventory of affected systems | **AVAILABLE** | 72 files across 6 categories
5. sam_schema current capabilities vs needed capabilities gap | **AVAILABLE** | need: create, update, plan-context-in-read. Have: read, state, ready, status, migrate
6. Plan file naming convention | **AVAILABLE** | User decision (2026-03-15): `P{issue}-{slug}.yaml` where issue = GitHub issue number. Existing 64 files renamed by automation. CLI addressing: `sam read P719/T3` globs `plan/P719-*.yaml`.
7. development-harness plugin sync scope | **DERIVABLE** | diff agent files between python3-development and development-harness to determine which are copies

AVAILABLE: 6, DERIVABLE: 1, MISSING: 0

**Decision**: APPROVED
</div>