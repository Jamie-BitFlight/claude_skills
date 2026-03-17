---
plan_number: 3
slug: integrate-sam-schema
feature: "Integrate sam_schema as Sole Task File Interface"
issue: 719
goal: "Route all SAM workflow task file I/O through sam CLI/MCP interface, eliminating 4 independent parsers and enabling future backing-store migration"
status: not-started
architecture: plan/architect-integrate-sam-schema.md
feature_context: plan/feature-context-integrate-sam-schema.md
codebase_analysis: plan/codebase/sam-schema-integration-patterns.md
total_tasks: 14
acceptance_criteria:
  - "AC1: task_format removed from implementation-manager scripts"
  - "AC2: Local parsers removed from implementation_manager.py"
  - "AC3: No .yaml extension branch in task_status_hook"
  - "AC4: sam create round-trips (create then read produces identical data)"
  - "AC5: sam read includes plan context in TaskAssignment response"
  - "AC6: sam update sets context on plan"
  - "AC7: No inline schema in swarm-task-planner agent prompt"
  - "AC8: No Read tool instruction in start-task skill"
  - "AC9: No Edit instruction in context-gathering agent"
  - "AC10: Tests pass with sam_schema interface"
  - "AC11: development-harness agent copies migrated"
  - "AC12: Workshop copies updated"
  - "AC13: TASK_FILE_FORMAT.md describes sam CLI as canonical interface"
  - "AC14: Format-agnostic state write on .md files (single code path)"
---

# Task Plan: Integrate sam_schema as Sole Task File Interface (#719)

## Dependency Graph

```text
Priority 1 (Foundation - no dependencies):
  T01: New sam CLI commands (create, update, claim)
  T02: Enhanced sam read (TaskAssignment)
  T03: Addressing module update (P{NNN} scheme)
  T04: TASK_FILE_FORMAT.md rewrite

Priority 2 (Core API + Tests - depends on P1):
  T05: MCP server extensions          [depends: T01, T02]
  T06: CLI + API test suite            [depends: T01, T02, T03]
  T07: File renaming script            [depends: T03]

Priority 3 (Component Migration - depends on P1+P2):
  T08: task_status_hook migration      [depends: T01]
  T09: implementation_manager cleanup  [depends: T01]
  T10: start-task skill migration      [depends: T01, T02]
  T11: implement-feature + complete-implementation skill migration [depends: T02]

Priority 4 (Agent Prompt Updates - depends on P1):
  T12: swarm-task-planner agent update [depends: T01]
  T13: context-gathering + context-refinement agent update [depends: T01]

Priority 5 (Sync + Cleanup - depends on all above):
  T14: development-harness sync + workshop copies [depends: T12, T13]
```

## Parallelization Map

```text
Parallel Group A (Priority 1): T01 | T02 | T03 | T04
Parallel Group B (Priority 2): T05 | T06 | T07
Parallel Group C (Priority 3): T08 | T09 | T10 | T11
Parallel Group D (Priority 4): T12 | T13
Sequential:                     T14 (after T12 + T13)
```

**Shared-file note**: T01 and T02 both modify `cli.py` and `query.py`. They write to different functions (T01 adds new commands; T02 modifies the existing `read` command and adds `get_task_assignment`). If merge conflicts arise at Sync Checkpoint 1, resolve by accepting both sets of changes -- they are additive, not conflicting. Alternatively, execute T01 before T02 to eliminate the risk entirely.

---

## SYNC CHECKPOINT 1: Foundation Complete

**Convergence**: T01 + T02 + T03 + T04

**Quality gates**:
- `uv run sam create`, `uv run sam update`, `uv run sam claim` commands exist and return expected JSON
- `uv run sam read P1/T1 --format json` returns TaskAssignment with plan-level fields
- Addressing module resolves both `P{NNN}-{slug}` and `tasks-{N}-{slug}` patterns
- TASK_FILE_FORMAT.md passes markdown lint

**Reflection**:
- Do the new CLI commands match the interface signatures in the architecture spec?
- Does TaskAssignment include all fields agents need?
- Does backward-compatible addressing work for existing plan files?

---

## SYNC CHECKPOINT 2: Tests + MCP Complete

**Convergence**: T05 + T06 + T07

**Quality gates**:
- MCP tools `sam_create`, `sam_update`, `sam_claim` exist and mirror CLI behavior
- Test suite passes: `uv run pytest packages/sam_schema/tests/ -v`
- Coverage remains above 80% overall, 95%+ on new CLI commands and addressing
- Migration script dry-run produces correct rename report

**Reflection**:
- Are there edge cases in addressing that property-based tests reveal?
- Does the migration script handle both single-file and directory plans?

---

## SYNC CHECKPOINT 3: Component Migration Complete

**Convergence**: T08 + T09 + T10 + T11 + T12 + T13

**Quality gates**:
- `grep -r "task_format" plugins/python3-development/skills/implementation-manager/scripts/` returns no matches
- `grep -r "implementation_manager" plugins/python3-development/skills/start-task/` returns no matches
- No `.yaml` extension branching in task_status_hook.py
- No `Read` tool instruction for task files in start-task SKILL.md
- No `Edit` tool instruction for task files in context-gathering agent
- No inline YAML schema in swarm-task-planner agent
- All existing tests pass

---

## SYNC CHECKPOINT 4: Sync Complete

**Convergence**: T14

**Quality gates**:
- development-harness agent copies match python3-development versions
- Workshop skill copies updated
- `uv run prek run --files` passes on all modified files
- All 14 acceptance criteria verified

---

---

## Context Manifest

_Generated by context-gathering agent on 2026-03-15_

### How This Currently Works: SAM Workflow Task File I/O

When a user invokes `/add-new-feature` or `/implement-feature`, the orchestrator and agents interact with task files using seven independent access paths, each with its own assumptions about file format and field ownership. This creates format drift and data loss.

**The Current Flow:**

1. **Planning Phase** (`/add-new-feature`): The `swarm-task-planner` agent generates a new plan file by directly writing YAML frontmatter via Write/Edit tools to `plan/tasks-{N}-{slug}.md` or a directory structure. The agent embeds schema assumptions inline and validates nothing — invalid fields slip through.

2. **Execution Phase** (`/implement-feature`): The orchestrator invokes `implementation_manager.py ready-tasks . {slug}` to find ready tasks. This script imports `sam_schema.core.query.load_plan()` to load the plan, then maintains its own fallback parser in `task_format.py` for legacy markdown files. It returns a JSON list of ready tasks with metadata like `agent`, `skills`, `priority`.

3. **Task Claiming** (`/start-task` skill): When an agent is dispatched to a task, the skill runs `uv run ... implementation_manager.py claim-task {slug}/T{ID}` to mark the task as in-progress. This command uses the same dual-parser pattern and writes status directly to the file.

4. **Status Synchronization** (SubagentStop hook): When the sub-agent finishes, `task_status_hook.py` fires. It reads `.claude/context/active-task-{CLAUDE_SESSION_ID}.json` to know which task was active, then calls `sam_schema.writers.yaml_writer.update_field()` for YAML files but falls back to its own regex parser for markdown files. It updates `status`, `completed` timestamp, and deletes the context file.

5. **Activity Tracking** (PostToolUse hook): On every Write, Edit, or Bash tool call, the same hook updates the `last_activity` timestamp using conditional logic that skips writes to completed tasks.

6. **Context Manifest Updates** (`context-gathering` agent): After the planning phase, an agent reads the task file using the Read tool, appends a `## Context Manifest` markdown section, and writes it back using the Edit tool. The agent maintains no schema awareness and can accidentally malform YAML.

7. **Completion Verification** (`/complete-implementation` skill): The orchestrator reads task files manually (no sam_schema calls), globs for follow-up task files by pattern (`plan/tasks-*-{slug}-followup-*.md`), and routes them through backlog linking logic.

**Where Format Drift Happens:**

- `implementation_manager.py` sees YAML and parses it with sam_schema but sees legacy markdown (`.md` with bold `**Status**: field`) and parses it with regex.
- `task_status_hook.py` uses sam_schema writers for YAML but regex for markdown.
- `swarm-task-planner` writes new task files with agent assumptions about which fields are required; no schema validation occurs at write time.
- `context-gathering` agent appends markdown sections that may break YAML structure if not careful.

**The Root Problem:**

Four independent parsers (sam_schema YAML reader, task_format.py regex, implementation_manager.py's own parser, and agent-embedded format assumptions) maintain inconsistent interpretations of the same task file. Fields parsed by one component are silently lost or misinterpreted by another. Status updates written by the hook may not be read correctly by the query layer on the next call.

### For New Feature Implementation: What Needs to Connect

This feature integrates all seven components around sam_schema as the sole interface. No component will read or write task files directly via Read/Edit/Write tools anymore. Instead:

1. **sam CLI becomes the single entry point** for all file operations. New commands (`create`, `update`, `claim`, `validate`) expose the Python query API through Typer, producing stable JSON output that becomes the contract between components.

2. **Naming convention changes**: Plans rename from `tasks-{N}-{slug}` to `P{issue}-{slug}.yaml` (pure YAML, no markdown). The addressing module must resolve both old and new patterns for backwards compatibility during transition.

3. **Agent prompts are rewritten** to invoke sam CLI instead of using Read/Edit/Write tools directly:
   - `swarm-task-planner` calls `sam create` with YAML task definitions instead of writing files
   - `context-gathering` calls `sam update --append-section` instead of using Edit tool
   - Agents receive task context via `sam read P{N}/T{M} --format json` instead of calling Read

4. **Hook scripts change**: Instead of parsing and updating files themselves, they invoke sam CLI commands (`sam state`, `sam update`) which handle format detection and atomic writes centrally.

5. **Scripts are simplified**: `implementation_manager.py` either becomes a thin wrapper around `sam` CLI or is replaced entirely. The dual-parser fallback in `task_format.py` is removed once all consumers migrate.

6. **Documentation is rewritten**: TASK_FILE_FORMAT.md shifts from describing the internal format (YAML frontmatter vs legacy markdown) to documenting the sam CLI as the canonical interface. The "Authorized Writers" table is updated to reference sam CLI commands instead of script names.

### Technical Reference Details

#### sam_schema Module Structure

**Location**: `packages/sam_schema/`

**Core modules**:
- `sam_schema/core/models.py` — Pydantic models: `Task`, `Plan`, `PlanStatus`, `TaskAssignment`
- `sam_schema/core/query.py` — Query API: `load_plan()`, `get_task()`, `get_ready_tasks()`, `update_status()`, `claim_task()` (exists but not CLI-exposed)
- `sam_schema/core/addressing.py` — Address resolution: `parse_address()`, `resolve_plan_address()` (currently resolves `tasks-{N}-{slug}` patterns; must be updated for `P{NNN}-{slug}`)
- `sam_schema/writers/yaml_writer.py` — Write API: `update_field()`, `update_fields()`, `write_plan()`
- `sam_schema/cli.py` — CLI commands: `read`, `state`, `ready`, `status`, `migrate` (missing: `create`, `update`, `claim`, `validate`)

**Existing CLI commands** (to be extended):

```bash
sam read P1/T1 --format json           # Read single task
sam state P1/T1 complete               # Update status
sam ready P1 --format json             # List ready tasks
sam status P1                           # Show plan progress
sam migrate plan/tasks-1-old.md         # Legacy format conversion
```

#### Current Component Integration Points

| Component | File | Current Access | Must Change To |
|-----------|------|-----------------|-----------------|
| swarm-task-planner agent | `plugins/python3-development/agents/swarm-task-planner.md` | Write tool + embedded YAML | `sam create` command |
| start-task skill | `plugins/python3-development/skills/start-task/SKILL.md` | `uv run implementation_manager.py claim-task` | `sam claim` command |
| task_status_hook | `plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py` | `sam_schema.writers.update_field()` (YAML) + regex (markdown) | `sam state` / `sam update` commands |
| implementation_manager CLI | `plugins/python3-development/skills/implementation-manager/scripts/implementation_manager.py` | `sam_schema.core.query.load_plan()` (primary) + `task_format.py` (fallback) | Thin wrapper around `sam` CLI OR replace entirely |
| implement-feature skill | `plugins/python3-development/skills/implement-feature/SKILL.md` | Invokes `implementation_manager.py ready-tasks` | Invokes `sam ready` command |
| context-gathering agent | `plugins/python3-development/agents/context-gathering.md` | Read tool + Edit tool | `sam read` + `sam update --append-section` |
| complete-implementation skill | `plugins/python3-development/skills/complete-implementation/SKILL.md` | Manual Read + glob pattern matching | `sam read` + `sam status` queries |

#### New CLI Command Signatures (from architecture spec)

**`sam create`** — Create a new plan

```bash
sam create {slug} --goal "..." [--plan-dir PATH] [--context "..."] [--issue N] [--stdin] [--format json]

# Inputs via --stdin: YAML with structure: { tasks: [...], context: "...", acceptance_criteria: [...] }
# Output: JSON { path: "...", plan_number: N, task_count: N }
```

**`sam update`** — Update plan metadata or append sections

```bash
sam update {address} [--set field=value] [--context "..."] [--append-section NAME] [--section-content "..."] [--format json]

# Examples:
sam update P1 --context "Feature context here"
sam update P1/T1 --append-section "Divergence Notes" --section-content "..."
sam update P1 --set acceptance-criteria-structured=true
```

**`sam claim`** — Mark a task as claimed (in-progress)

```bash
sam claim {address} [--format json]

# Output: JSON { claimed: true, task_id: "...", started: "2026-03-15T..." }
# Exit code: 1 if already claimed or not found
```

**`sam validate`** — Validate a plan (new command)

```bash
sam validate {address} [--format json]

# Output: JSON { valid: true/false, errors: [...], warnings: [...] }
```

**Enhanced `sam read`** — Include plan context in response

```bash
# Current behavior: Returns task fields only
sam read P1/T1 --format json

# New behavior: Returns TaskAssignment with plan-level fields included
# Output: JSON { plan_goal: "...", plan_context: "...", task_id: "T1", title: "...", ... }
```

#### Python API Changes Required

**`sam_schema.core.query`** — Add these functions:

```python
def create_plan(
    slug: str,
    goal: str,
    tasks: List[dict],
    plan_dir: Path = None,
    context: str = None,
    issue: int = None
) -> Plan:
    """Create new plan object and write to disk via create_plan_file()."""
    ...

def get_task_assignment(plan: Plan, task_id: str) -> TaskAssignment:
    """Get task with plan-level context included (goal, shared context)."""
    ...

def claim_task(plan: Plan, task_id: str) -> bool:
    """Mark task as claimed (in-progress). Existing but not CLI-exposed."""
    ...
```

**`sam_schema.writers.yaml_writer`** — Add these functions:

```python
def create_plan_file(path: Path, plan: Plan) -> None:
    """Write plan to file with atomic writes (tempfile + os.replace)."""
    ...

def append_section(path: Path, task_id: str, section_name: str, content: str) -> None:
    """Append markdown section to task body (e.g., Context Manifest)."""
    ...
```

#### Acceptance Criteria From Task File

1. `sam create test-feature --goal "Test" --stdin` reads YAML, creates plan file, returns JSON with path
2. `sam read` on created file returns valid task data (AC4 round-trip test)
3. `sam update P{N} --context "test context"` updates plan context field
4. `sam update P{N}/T1 --append-section "Notes" --section-content "test"` appends section
5. `sam claim P{N}/T1` sets status to in-progress with started timestamp
6. `sam claim P{N}/T1` (second call) exits non-zero (already claimed guard)
7. `sam validate P{N}` returns valid=true for valid plan
8. `sam status --all` lists all plans in plan/ directory

#### File Locations for Implementation

**Core sam_schema files to modify**:
- `packages/sam_schema/sam_schema/cli.py` — Add 4 new commands (T01)
- `packages/sam_schema/sam_schema/core/query.py` — Add `create_plan()`, `get_task_assignment()` (T01, T02)
- `packages/sam_schema/sam_schema/writers/yaml_writer.py` — Add `create_plan_file()`, `append_section()` (T01)
- `packages/sam_schema/sam_schema/core/addressing.py` — Update to resolve `P{NNN}-{slug}` pattern (T03)
- `.claude/docs/TASK_FILE_FORMAT.md` — Rewrite to describe sam CLI as canonical interface (T04)

**Component files to migrate**:
- `plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py` — Remove fallback regex, use sam CLI (T08)
- `plugins/python3-development/skills/implementation-manager/scripts/implementation_manager.py` — Wrap sam CLI or replace (T09)
- `plugins/python3-development/skills/start-task/SKILL.md` — Call `sam claim` instead of implementation_manager (T10)
- `plugins/python3-development/skills/implement-feature/SKILL.md` — Call `sam ready` instead of implementation_manager (T11)
- `plugins/python3-development/agents/swarm-task-planner.md` — Call `sam create` instead of Write tool (T12)
- `plugins/python3-development/agents/context-gathering.md` — Call `sam update --append-section` instead of Edit tool (T13)

**Test files**:
- `packages/sam_schema/tests/test_cli.py` — Add tests for create/update/claim/validate commands (T06)
- `packages/sam_schema/tests/test_addressing.py` — Add tests for `P{NNN}-{slug}` pattern (T06)

#### Development-Harness Plugin Synchronization

Seven agents have copies in both `plugins/python3-development/agents/` and `plugins/development-harness/agents/`:

- swarm-task-planner.md — Changes to call `sam create`
- context-gathering.md — Changes to call `sam update --append-section`
- context-refinement.md — May need changes to call `sam read` for context

When T12 or T13 are completed in python3-development, T14 must sync these copies to development-harness to prevent divergence.

#### Dependency Graph and Merge Risk

**Priority 1 (Foundation)**: T01, T02, T03, T04 can run in parallel.
- **Merge risk**: T01 and T02 both modify `cli.py` and `query.py`. T01 adds new functions (create_plan, claim); T02 modifies read command and adds get_task_assignment(). They don't conflict if each appends functions — execute T01 first to eliminate risk.

**Priority 2 (Tests)**: T05, T06, T07 depend on T01, T02, T03.
- Quality gates: CLI commands exist, address pattern works, tests pass with 80%+ coverage

**Priority 3 (Migration)**: T08–T11 depend on T01 (new CLI commands exist)
- Quality gates: No task_format imports, no regex fallback, all components use sam CLI

**Priority 4 (Agents)**: T12, T13 depend on T01 (new CLI commands exist)
- Quality gates: No direct file writes, no Edit/Write tool usage, agent prompts use sam CLI

**Priority 5 (Sync)**: T14 depends on T12, T13 (agent updates complete)
- Quality gates: development-harness copies match, lint passes, all 14 acceptance criteria verified

---

---
task: T01
title: "New sam CLI commands: create, update, claim, validate"
status: complete
completed: 2026-03-15T12:00:00Z
agent: python3-development:python-cli-architect
dependencies: []
priority: 1
complexity: high
accuracy-risk: medium
skills: ["python3-development"]
parallelize-with: [T02, T03, T04]
reason: "T01 writes to cli.py and query.py; T02 writes to cli.py (read command) and models.py; T03 writes to addressing.py; T04 writes to TASK_FILE_FORMAT.md. T01 and T02 both touch cli.py -- MERGE RISK exists. However, T01 adds new commands (create/update/claim/validate functions) while T02 modifies the existing read command and adds a model to models.py. They touch different functions in cli.py, so parallel execution is safe if each agent appends rather than rewrites the file."
handoff: "Report: files modified, test commands run, any schema decisions made"
started: "2026-03-15T13:01:10Z"
---

## Context

The sam_schema package (`packages/sam_schema/`) has a Typer CLI at `packages/sam_schema/sam_schema/cli.py` with 5 existing commands (read, state, ready, status, migrate). The core query API at `packages/sam_schema/sam_schema/core/query.py` has `claim_task()` at line 177 but it is not exposed via CLI. The writer at `packages/sam_schema/sam_schema/writers/yaml_writer.py` has `update_field()` and `write_plan()` but no `create_plan_file()` or `append_section()`.

This task adds 4 new CLI commands and their backing query/writer functions per architecture spec sections 4.1, 4.4, 4.5, and 12.

## Objective

Add `sam create`, `sam update`, `sam claim`, and `sam validate` CLI commands with backing `create_plan()`, `update_plan_fields()` query functions and `create_plan_file()`, `append_section()` writer functions.

## Inputs

- Architecture spec: `plan/architect-integrate-sam-schema.md` sections 4.1 (CLI commands), 4.4 (query API), 4.5 (writer API), 12 (deprecation -- validate command and status --all flag)
- Existing CLI: `packages/sam_schema/sam_schema/cli.py`
- Existing query API: `packages/sam_schema/sam_schema/core/query.py`
- Existing writer: `packages/sam_schema/sam_schema/writers/yaml_writer.py`
- Existing models: `packages/sam_schema/sam_schema/core/models.py`

## Requirements

### sam create command
1. Add `create()` command to cli.py matching architecture spec section 4.1 signature (slug, goal, plan_dir, context, issue, stdin, format)
2. Add `create_plan()` function to query.py that scans `plan/P*` for highest NNN, assigns P{NNN+1}, validates tasks against Task Pydantic model, writes via `create_plan_file()`
3. Add `create_plan_file()` function to yaml_writer.py that writes plan YAML with atomic write (tempfile + os.replace)
4. `--stdin` reads YAML with `tasks:` array from stdin; validates each task against Task model
5. Returns JSON with `{"path": "...", "plan_number": N, "task_count": N}`

### sam update command
6. Add `update()` command to cli.py matching architecture spec section 4.1 signature (address, plan_dir, set_field, context, append_section, section_content, format)
7. Add `update_plan_fields()` function to query.py
8. Add `append_section()` function to yaml_writer.py that appends a named markdown section to task body content
9. `--set field=value` updates arbitrary plan or task fields
10. `--context` shorthand for setting plan context field
11. `--append-section` + `--section-content` appends markdown section to task body

### sam claim command
12. Add `claim()` command to cli.py matching architecture spec section 4.1 signature
13. Expose existing `claim_task()` from query.py:177 via CLI
14. Exit non-zero if task already claimed or not found
15. Returns JSON `{"claimed": true, "task_id": "...", "started": "..."}`

### sam validate command
16. Add `validate()` command to cli.py per architecture spec section 12
17. Calls `load_plan()` and reports errors/warnings
18. Returns JSON `{"valid": bool, "errors": [...], "warnings": [...]}`

### sam status --all flag
19. Add `--all` flag to existing `status` command per architecture spec section 12
20. When `--all` with no address, globs `plan/P*` and returns status for each plan

## Constraints

- Use `Annotated` Typer syntax for all new commands (project standard)
- All write operations use atomic writes (tempfile + os.replace)
- Do not modify the existing `read` command (that is T02)
- Do not modify addressing.py (that is T03)
- JSON output must be stable -- these outputs become the contract per ADR-001
- Input validation via Pydantic models -- invalid fields produce actionable error messages

## Expected Outputs

- `packages/sam_schema/sam_schema/cli.py` (modified -- 4 new commands + status flag)
- `packages/sam_schema/sam_schema/core/query.py` (modified -- create_plan, update_plan_fields)
- `packages/sam_schema/sam_schema/writers/yaml_writer.py` (modified -- create_plan_file, append_section)

## Acceptance Criteria

1. `echo "tasks: [{task: T01, title: Test, status: not-started, agent: test, dependencies: [], priority: 1, complexity: low}]" | uv run sam create test-feature --goal "Test" --stdin` creates a valid plan file and returns JSON with path
2. `uv run sam read` on the created file returns valid task data (round-trip: AC4)
3. `uv run sam update P{N} --context "test context"` updates the plan context field and returns JSON confirmation
4. `uv run sam update P{N}/T1 --append-section "Notes" --section-content "test"` appends section to task body
5. `uv run sam claim P{N}/T1` sets status to in-progress and returns JSON with claimed=true and started timestamp
6. `uv run sam claim P{N}/T1` (second call) exits non-zero (already claimed)
7. `uv run sam validate P{N}` returns `{"valid": true, ...}` for a valid plan
8. `uv run sam status --all` lists all plans in plan/ directory
9. All new functions have type annotations and pass basedpyright strict mode

## Verification Steps

1. Run `uv run sam create test --goal "test" --stdin < test_input.yaml` and verify file created
2. Run `uv run sam claim P{N}/T1` twice -- first succeeds, second fails
3. Run `uv run sam validate P{N}` on created file
4. Run `uv run pytest packages/sam_schema/tests/ -k "create or update or claim or validate" -v`
5. Run `uv run basedpyright packages/sam_schema/sam_schema/cli.py`

## CoVe Checks

- Key claims to verify:
  - `claim_task()` exists at query.py:177 and has the expected signature
  - `update_field()` exists in yaml_writer.py and supports per-field updates
  - Typer `Annotated` syntax is the project standard (check existing commands)
- Verification questions:
  1. Does `claim_task()` in query.py accept `(plan, task_id)` args and return bool?
  2. Does the existing `state` command use `Annotated` Typer syntax?
  3. Does `write_plan()` in yaml_writer.py use atomic writes via tempfile?
- Evidence to collect:
  - Read first 5 lines of `claim_task()` function
  - Read one existing command signature from cli.py
  - Read `write_plan()` implementation for atomic write pattern
- Revision rule:
  - If `claim_task()` signature differs, adapt the CLI wrapper to match actual API

---
task: T02
title: "Enhanced sam read: TaskAssignment composite response"
status: complete
completed: 2026-03-15T12:00:00Z
agent: python3-development:python-cli-architect
dependencies: []
priority: 1
complexity: medium
accuracy-risk: medium
skills: ["python3-development"]
parallelize-with: [T01, T03, T04]
reason: "T02 modifies the existing read command in cli.py and adds TaskAssignment model to models.py. T01 adds new commands to cli.py (different functions). Safe to parallelize -- different functions in same file."
handoff: "Report: TaskAssignment model fields, sam read output sample, files modified"
started: "2026-03-15T13:01:13Z"
---

## Context

The `sam read` command currently returns task fields only when given a `P{N}/T{M}` address. Agents need plan-level context (goal, shared context, acceptance criteria) alongside task details in a single call per ADR-003. The architecture spec section 4.2 defines the `TaskAssignment` composite model.

## Objective

Enhance `sam read P{N}/T{M}` to return a `TaskAssignment` response containing both plan-level fields and task details, so agents receive everything needed in one call.

## Inputs

- Architecture spec: `plan/architect-integrate-sam-schema.md` sections 4.2, 4.4, 5.4
- Existing read command: `packages/sam_schema/sam_schema/cli.py` lines 148-191
- Existing models: `packages/sam_schema/sam_schema/core/models.py`
- Existing query: `packages/sam_schema/sam_schema/core/query.py`

## Requirements

1. Add `TaskAssignment` Pydantic model to `models.py` with fields: plan_number, plan_slug, plan_goal, plan_context, plan_acceptance_criteria, task (existing Task model)
2. Add `get_task_assignment()` function to query.py that composes TaskAssignment from Plan + Task
3. Modify `read` command in cli.py: when address includes task ID (P{N}/T{M}), return TaskAssignment JSON instead of bare Task JSON
4. When address is plan-only (P{N}), continue returning Plan JSON (existing behavior unchanged)
5. MCP `sam_read` tool returns TaskAssignment when task address provided (mirror CLI behavior)

## Constraints

- Do not break existing `sam read` callers that expect current Task output shape -- the new shape wraps Task inside a `task` field, which is a breaking change. This is intentional per architecture spec.
- Do not modify other commands in cli.py (those are T01)
- TaskAssignment must be serializable to JSON and YAML

## Expected Outputs

- `packages/sam_schema/sam_schema/core/models.py` (modified -- TaskAssignment model)
- `packages/sam_schema/sam_schema/core/query.py` (modified -- get_task_assignment function)
- `packages/sam_schema/sam_schema/cli.py` (modified -- read command enhancement)
- `packages/sam_schema/sam_schema/server.py` (modified -- sam_read MCP tool update)

## Acceptance Criteria

1. `uv run sam read P1/T1 --format json` returns JSON with `plan_goal`, `plan_slug`, `plan_context`, and nested `task` object (AC5)
2. `uv run sam read P1 --format json` returns Plan JSON (unchanged behavior)
3. `TaskAssignment` model validates with Pydantic and rejects missing required fields
4. MCP `sam_read` tool returns TaskAssignment JSON when task address provided

## Verification Steps

1. Create a test plan with known goal/context, read a task, verify plan fields appear in response
2. Run `uv run sam read P1 --format json` and verify it does NOT return TaskAssignment (plan-only)
3. Run `uv run pytest packages/sam_schema/tests/ -k "read" -v`
4. Run `uv run basedpyright packages/sam_schema/sam_schema/core/models.py`

## CoVe Checks

- Key claims to verify:
  - Current `sam read` output shape (what fields does it return now?)
  - Plan model has goal, context, acceptance_criteria fields
- Verification questions:
  1. What does `sam read P1/T1 --format json` currently output?
  2. Does the Plan model in models.py include a `goal` field?
  3. Does the Plan model include `acceptance_criteria` as a list field?
- Evidence to collect:
  - Read Plan model class from models.py
  - Run existing `sam read` on a test file to capture current output
- Revision rule:
  - If Plan model lacks expected fields, add them (they may need adding to the model first)

---
task: T03
title: "Addressing module: P{NNN}-{slug} resolution with backward compatibility"
status: complete
completed: 2026-03-15T12:00:00Z
agent: python3-development:python-cli-architect
dependencies: []
priority: 1
complexity: medium
accuracy-risk: medium
skills: ["python3-development"]
parallelize-with: [T01, T02, T04]
reason: "T03 modifies addressing.py only. No overlap with T01 (cli.py, query.py, yaml_writer.py), T02 (models.py, cli.py read command, server.py), or T04 (TASK_FILE_FORMAT.md)."
handoff: "Report: addressing patterns supported, backward compatibility verification, edge cases found"
started: "2026-03-15T13:01:20Z"
---

## Context

The addressing module at `packages/sam_schema/sam_schema/core/addressing.py` currently resolves `tasks-{N}-{slug}` filenames by alphabetical index. Per ADR-002 and architecture spec section 4.3, it must be updated to resolve `P{NNN}-{slug}` patterns as primary, with `tasks-{N}-{slug}` as a backward-compatible fallback per ADR-005.

## Objective

Update `resolve_plan_address()` to resolve `P{NNN}-*` patterns as primary addressing, with `tasks-{N}-{slug}` fallback for unmigrated files.

## Inputs

- Architecture spec: `plan/architect-integrate-sam-schema.md` sections 4.3, 5.2, ADR-002, ADR-005
- Existing addressing module: `packages/sam_schema/sam_schema/core/addressing.py`

## Requirements

1. `resolve_plan_address("P1", plan_dir)` globs `plan/P001-*` (zero-padded match)
2. `resolve_plan_address("P719", plan_dir)` globs `plan/P719-*`
3. `resolve_plan_address("my-slug", plan_dir)` globs `plan/P*-my-slug*`
4. Multiple matches on P{N} produce error with disambiguation list
5. Backward compatibility: if no `P{NNN}-*` match, fall back to `tasks-{N}-{slug}` pattern
6. Path traversal prevention: reject addresses containing `..` or absolute paths
7. Support both `.yaml` single-file and directory matches

## Constraints

- Fallback to `tasks-{N}-{slug}` is explicitly temporary (removed after T07 migration completes)
- Do not modify cli.py, query.py, or other modules (those are T01/T02)
- Zero-pad matching: P1 matches P001, P01, P1 (flexible input, zero-padded on disk)

## Expected Outputs

- `packages/sam_schema/sam_schema/core/addressing.py` (modified)

## Acceptance Criteria

1. `parse_address("P719/T3")` returns plan="P719", task="T3"
2. `resolve_plan_address("P1", plan_dir)` finds `plan/P001-*.yaml` or `plan/P001-*/`
3. `resolve_plan_address("my-slug", plan_dir)` finds `plan/P*-my-slug.yaml`
4. `resolve_plan_address("P1", plan_dir)` with two P001 files raises error with both paths listed
5. `resolve_plan_address("old-slug", plan_dir)` falls back to `plan/tasks-*-old-slug*` when no P-pattern match exists
6. Address with `..` raises AddressingError

## Verification Steps

1. Create test fixtures: `plan/P001-test.yaml`, `plan/P002-other.yaml`, `plan/tasks-1-legacy.md`
2. Test resolution of P1, P2, legacy slug, collision case
3. Run `uv run pytest packages/sam_schema/tests/ -k "addressing" -v`
4. Run `uv run basedpyright packages/sam_schema/sam_schema/core/addressing.py`

## CoVe Checks

- Key claims to verify:
  - Current `resolve_plan_address()` signature and return type
  - Current glob patterns used in addressing.py
- Verification questions:
  1. What arguments does `resolve_plan_address()` currently accept?
  2. What exception type does addressing.py raise on failure?
  3. Does addressing.py currently support directory-based plans?
- Evidence to collect:
  - Read `resolve_plan_address()` function signature from addressing.py
  - Read `AddressingError` class definition
- Revision rule:
  - If current function signature differs from spec, adapt new logic to existing signature where possible

---
task: T04
title: "TASK_FILE_FORMAT.md rewrite: sam CLI as canonical interface"
status: complete
completed: 2026-03-15T12:00:00Z
agent: contextual-ai-documentation-optimizer
dependencies: []
priority: 1
complexity: medium
accuracy-risk: low
skills: ["development-harness:clear-cove-task-design"]
parallelize-with: [T01, T02, T03]
reason: "T04 writes only to .claude/docs/TASK_FILE_FORMAT.md. No file overlap with any other task."
handoff: "Report: document structure, section count, any placeholder sections pending CLI completion"
started: "2026-03-15T13:01:19Z"
---

## Context

TASK_FILE_FORMAT.md at `.claude/docs/TASK_FILE_FORMAT.md` has 47 references across the codebase and serves as the canonical entry point for task file structure. Per architecture spec section 13, it must be rewritten to describe the `sam` CLI as the canonical interface. The current document describes YAML frontmatter format and regex-based parsing problems.

This task was merged from documentation rewrite needs to avoid edit conflicts. The document structure follows architecture spec section 13 exactly.

## Objective

Rewrite TASK_FILE_FORMAT.md to describe sam CLI as the canonical interface for all task file operations, with the document structure specified in architecture spec section 13.

## Inputs

- Architecture spec: `plan/architect-integrate-sam-schema.md` section 13 (document structure), section 5.3 (YAML schema), section 5.4 (TaskAssignment schema)
- Current document: `.claude/docs/TASK_FILE_FORMAT.md`
- Authorized Writers table: architecture spec section 13

## Requirements

1. Follow the document structure from architecture spec section 13:
   - Quick Reference (sam CLI command summary + MCP tool summary)
   - Naming Convention (P{NNN}-{slug}.yaml, directory format, addressing)
   - Plan Schema (plan-level fields, link to JSON Schema)
   - Task Schema (task-level fields, status values, link to JSON Schema)
   - Authorized Writers (updated table from architecture spec section 13)
   - sam CLI Usage Guide (create, read, update, state, claim, ready, status, validate, migrate with examples)
   - Legacy Format Support (read-only support, migration path, deprecation timeline)
2. Reference JSON Schema files (`plan-schema.json`, `task-schema.json`, `assignment-schema.json`) generated by `uv run sam schema` instead of embedding schema definitions inline
3. Include the updated Authorized Writers table from architecture spec section 13
4. Document `TaskAssignment` composite response shape for `sam read P{N}/T{M}`
5. Mark the migration path and deprecation timeline for `tasks-{N}-{slug}` naming

## Constraints

- This is a complete rewrite, not an incremental edit
- Do not embed full schema definitions -- reference JSON Schema files
- Keep document under 400 lines (concise reference, not tutorial)
- All code fences must have language specifiers
- All file references use `[text](./path)` markdown link format

## Expected Outputs

- `.claude/docs/TASK_FILE_FORMAT.md` (rewritten)

## Acceptance Criteria

1. Document follows the structure from architecture spec section 13 (AC13)
2. Authorized Writers table matches architecture spec section 13 table
3. sam CLI command examples are present for all 9 commands (create, read, update, state, claim, ready, status, validate, migrate)
4. Legacy format support section documents deprecation path
5. No inline schema definitions -- all reference JSON Schema files

## Verification Steps

1. Verify document structure matches architecture spec section 13 headings
2. Run `uv run prek run --files .claude/docs/TASK_FILE_FORMAT.md`
3. Verify all 9 sam commands mentioned with usage examples
4. Verify Authorized Writers table matches spec

---
task: T05
title: "MCP server extensions: sam_create, sam_update, sam_claim tools"
status: complete
completed: 2026-03-15T14:00:00Z
agent: python3-development:python-cli-architect
dependencies: [T01, T02]
priority: 2
complexity: medium
accuracy-risk: low
skills: ["python3-development"]
parallelize-with: [T06, T07]
reason: "T05 modifies server.py only. T06 writes test files. T07 writes scripts/rename_plan_files.py. No file overlap."
handoff: "Report: MCP tools added, test results"
started: "2026-03-15T13:11:58Z"
---

## Context

The MCP server at `packages/sam_schema/sam_schema/server.py` currently exposes `sam_read`, `sam_state`, `sam_ready`, `sam_status` tools. Per architecture spec section 4.6, it needs new tools mirroring the CLI commands added in T01 and the enhanced read from T02.

## Objective

Add `sam_create`, `sam_update`, `sam_claim` MCP tools to server.py, and update existing `sam_read` to return TaskAssignment when task address is provided.

## Inputs

- Architecture spec: `plan/architect-integrate-sam-schema.md` section 4.6
- Existing MCP server: `packages/sam_schema/sam_schema/server.py`
- New CLI commands from T01: create, update, claim signatures
- Enhanced read from T02: TaskAssignment return type

## Requirements

1. Add `sam_create(slug, goal, tasks_yaml, ...)` MCP tool that mirrors `sam create` CLI
2. Add `sam_update(address, fields, ...)` MCP tool that mirrors `sam update` CLI
3. Add `sam_claim(address)` MCP tool that mirrors `sam claim` CLI
4. Update existing `sam_read` tool to return TaskAssignment JSON when task address provided
5. All MCP tools delegate to the same query API functions the CLI uses
6. Return JSON strings matching CLI output format

## Constraints

- Use FastMCP `@mcp.tool()` decorator (existing pattern in server.py)
- All tools are async functions (existing pattern)
- Do not duplicate business logic -- delegate to query API

## Expected Outputs

- `packages/sam_schema/sam_schema/server.py` (modified)

## Acceptance Criteria

1. `sam_create` MCP tool accepts slug, goal, tasks_yaml params and returns JSON path response
2. `sam_update` MCP tool accepts address and fields, returns JSON confirmation
3. `sam_claim` MCP tool accepts address, returns JSON with claimed status
4. `sam_read` MCP tool returns TaskAssignment when task address provided

## Verification Steps

1. Run `uv run pytest packages/sam_schema/tests/ -k "server or mcp" -v`
2. Run `uv run basedpyright packages/sam_schema/sam_schema/server.py`
3. Verify each new tool function has docstring matching CLI command help text

---
task: T06
title: "Test suite: CLI commands, addressing, writers, migration"
status: complete
completed: 2026-03-15T14:00:00Z
agent: python3-development:python-pytest-architect
dependencies: [T01, T02, T03]
priority: 2
complexity: high
accuracy-risk: low
skills: ["fastmcp-python-tests", "python3-development"]
parallelize-with: [T05, T07]
reason: "T06 writes test files in packages/sam_schema/tests/. No overlap with T05 (server.py) or T07 (scripts/rename_plan_files.py)."
handoff: "Report: test count, coverage percentage, any failures or skipped tests"
started: "2026-03-15T13:11:38Z"
---

## Context

The sam_schema package has 421 existing tests with 93% coverage. The new CLI commands (T01), enhanced read (T02), and addressing update (T03) need comprehensive tests per architecture spec section 7. This task adds ~60 new tests covering the new functionality.

## Objective

Create comprehensive test suite for all new sam CLI commands, addressing module changes, and writer functions, maintaining 95%+ coverage on new code and 80%+ overall.

## Inputs

- Architecture spec: `plan/architect-integrate-sam-schema.md` section 7 (testing architecture)
- New code from T01: create, update, claim, validate commands + query/writer functions
- New code from T02: TaskAssignment model + get_task_assignment + enhanced read
- New code from T03: P{NNN} addressing resolution + backward compatibility
- Existing test patterns: `packages/sam_schema/tests/`

## Requirements

### CLI integration tests
1. `test_sam_create_*`: create plan from stdin YAML, verify file written, verify round-trip with sam read
2. `test_sam_update_*`: update plan fields, update task fields, append sections, verify persistence
3. `test_sam_claim_*`: claim unclaimed task (success), claim already-claimed (exit 1), claim nonexistent (exit 1)
4. `test_sam_read_assignment`: read task returns TaskAssignment with plan-level fields
5. `test_sam_validate_*`: validate valid plan (success), validate invalid plan (errors reported)
6. `test_sam_status_all`: list all plans with --all flag

### Addressing tests
7. `test_resolve_p_number`: P1 matches P001-*, P719 matches P719-*
8. `test_resolve_slug`: slug matches P*-{slug}*
9. `test_resolve_collision`: multiple P{N} matches produce error with disambiguation
10. `test_resolve_backward_compat`: tasks-{N}-{slug} fallback works for unmigrated files
11. Property-based: `@given(st.integers(min_value=1, max_value=9999))` for plan number resolution

### Writer tests
12. `test_create_plan_file`: writes valid YAML, readable by load_plan()
13. `test_append_section`: appends to task body, preserves existing content
14. `test_atomic_write_on_error`: original file preserved if write fails mid-operation

## Constraints

- Use `typer.testing.CliRunner(mix_stderr=False)` with `env={"NO_COLOR": "1"}` for CLI tests
- Use `pytest-mock` for mocking (never unittest.mock directly)
- Use `hypothesis` for property-based tests on addressing
- Test fixtures use tmp_path, not real plan/ directory
- Mark tests: `@pytest.mark.cli`, `@pytest.mark.unit`, `@pytest.mark.integration`

## Expected Outputs

- `packages/sam_schema/tests/test_cli_create.py` (new)
- `packages/sam_schema/tests/test_cli_update.py` (new)
- `packages/sam_schema/tests/test_cli_claim.py` (new)
- `packages/sam_schema/tests/test_addressing_pnnn.py` (new or modified existing)
- `packages/sam_schema/tests/test_writers_new.py` (new or modified existing)

## Acceptance Criteria

1. All new tests pass: `uv run pytest packages/sam_schema/tests/ -v` exits 0 (AC10)
2. Coverage on new CLI commands is 95%+ (check via `--cov-report=term-missing`)
3. Coverage on addressing module changes is 95%+
4. Property-based test for plan number resolution exists and passes
5. At least 60 new test functions added across all test files

## Verification Steps

1. Run `uv run pytest packages/sam_schema/tests/ -v --tb=short`
2. Run `uv run pytest packages/sam_schema/tests/ --cov=packages/sam_schema --cov-report=term-missing`
3. Verify coverage output shows 95%+ on cli.py new functions, addressing.py, yaml_writer.py new functions
4. Run `uv run pytest packages/sam_schema/tests/ -k "hypothesis" -v` to verify property-based tests

---
task: T07
title: "File renaming script: tasks-{N}-{slug} to P{NNN}-{slug}.yaml"
status: complete
completed: 2026-03-15T14:00:00Z
agent: python3-development:python-cli-architect
dependencies: [T03]
priority: 2
complexity: medium
accuracy-risk: medium
skills: ["python3-development"]
parallelize-with: [T05, T06]
reason: "T07 creates scripts/rename_plan_files.py (new file). No overlap with T05 (server.py) or T06 (test files)."
handoff: "Report: dry-run output showing rename map, backlog update count, any files that could not be mapped"
started: "2026-03-15T13:13:08Z"
---

## Context

64 existing plan files use `tasks-{N}-{slug}` naming. Per architecture spec section 14 and ADR-002, they must be renamed to `P{NNN}-{slug}.yaml`. A PEP 723 standalone script handles this one-time migration, including backlog plan field updates.

## Objective

Create `scripts/rename_plan_files.py` that renames all legacy plan files to P{NNN}-{slug} format, converts .md to pure YAML via `sam migrate`, and updates backlog plan references.

## Inputs

- Architecture spec: `plan/architect-integrate-sam-schema.md` section 14
- Existing plan files: `plan/tasks-*` (glob to discover)
- Backlog items with plan fields: `.claude/backlog/*.md`
- `sam migrate` command for format conversion

## Requirements

1. PEP 723 standalone script with dependencies: ruamel.yaml, typer, rich
2. Glob `plan/tasks-*` to find all legacy files and directories
3. Extract slug from filename (e.g., `tasks-5-my-feature.md` -> `my-feature`)
4. If linked to GitHub issue (via backlog item), use issue number as P{NNN}; otherwise assign sequential
5. If `.md` format: run `sam migrate` to convert to pure YAML before renaming
6. Rename file/directory to `P{NNN}-{slug}.yaml` (or `P{NNN}-{slug}/` for directories)
7. `--update-backlog` flag (default on): update backlog plan references via backlog CLI
8. `--dry-run` flag: report changes without executing
9. Output report: old -> new path mappings, backlog items updated

## Constraints

- Script is one-time use -- PEP 723 standalone, no package dependency
- Use `os.rename()` for filesystem operations (not shutil)
- Do not delete original files on dry-run
- Handle both single-file and directory plan formats
- Must be idempotent: running twice on already-renamed files produces no changes

## Expected Outputs

- `scripts/rename_plan_files.py` (new)

## Acceptance Criteria

1. `uv run scripts/rename_plan_files.py plan/ --dry-run` produces correct rename report
2. Script converts .md files to YAML before renaming (calls sam migrate)
3. Script updates backlog plan references when `--update-backlog` is used
4. Script is idempotent -- running on already-renamed files reports 0 changes
5. PEP 723 inline metadata includes all dependencies

## Verification Steps

1. Run `uv run scripts/rename_plan_files.py plan/ --dry-run` and verify output
2. Create test fixture directory with legacy-named files, run script, verify renames
3. Verify backlog plan field references point to new paths after migration
4. Run script again on migrated directory -- verify 0 changes reported

## CoVe Checks

- Key claims to verify:
  - `sam migrate` command exists and converts legacy markdown to pure YAML
  - Backlog CLI has an `update` command that accepts `plan=` parameter
- Verification questions:
  1. What is the exact CLI syntax for `sam migrate`?
  2. What is the backlog update CLI syntax for setting plan path?
  3. Does `os.rename()` work across filesystems or should `shutil.move()` be used?
- Evidence to collect:
  - Run `uv run sam migrate --help` to verify command exists
  - Check backlog CLI help for update command syntax
- Revision rule:
  - If sam migrate does not exist yet, add a dependency on T01 and note it

---
task: T08
title: "task_status_hook.py: remove dual-parser, unify on sam_schema"
status: complete
started: "2026-03-15T13:01:10Z"
completed: "2026-03-15T14:00:00Z"
agent: python3-development:python-cli-architect
dependencies: [T01]
priority: 3
complexity: medium
accuracy-risk: medium
skills: ["python3-development"]
parallelize-with: [T09, T10, T11]
reason: "T08 modifies task_status_hook.py. T09 modifies implementation_manager.py. T10 modifies start-task/SKILL.md. T11 modifies implement-feature/SKILL.md and complete-implementation/SKILL.md. No file overlap."
handoff: "Report: imports removed, code paths unified, test results"
---

## Context

`task_status_hook.py` at `plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py` currently has a split parser: uses sam_schema for `.yaml` files but falls back to `task_format.py` for `.md` files. Per architecture spec section 11.3, the `.yaml` extension branch must be removed and all formats handled through a single sam_schema code path.

The hook keeps the Python API (not CLI) for performance per ADR-001 exception -- hooks fire on every tool call.

## Objective

Remove the dual-parser branches and `task_format` import from task_status_hook.py, unifying all task file operations on `sam_schema.core.query` API.

## Inputs

- Architecture spec: `plan/architect-integrate-sam-schema.md` section 11.3
- Hook script: `plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py`
- task_format.py: `plugins/python3-development/skills/implementation-manager/scripts/task_format.py`

## Requirements

1. Remove `from task_format import ...` imports
2. Remove `.suffix == ".yaml"` branch in `handle_subagent_stop()` (lines 548-557 area)
3. Remove `.suffix == ".yaml"` branch in `handle_activity_update()` (lines 615-624 area)
4. Replace both branches with single call to `sam_update_status()` from sam_schema
5. Replace `parse_yaml_frontmatter()` calls with `load_plan()` from sam_schema
6. Replace `add_timestamp_to_task()` calls with `sam_update_field()` from sam_schema
7. Keep Python API imports (not CLI subprocess calls) for performance

## Constraints

- Hook must remain performant -- it fires on every Write/Edit/Bash tool call
- Do not modify task_format.py itself (it remains for now, removed later in deprecation)
- Do not change hook JSON stdin interface or event handling logic
- Do not modify SKILL.md hook declarations
- GitHub sync logic remains unchanged

## Expected Outputs

- `plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py` (modified)

## Acceptance Criteria

1. `grep -c "task_format" plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py` returns 0 (AC1 partial, AC3)
2. No `.yaml` extension branching in the script (AC3, AC14)
3. Hook correctly updates status on `.md` files through sam_schema (format-agnostic)
4. Hook correctly updates status on `.yaml` files through sam_schema
5. SubagentStop handler marks task COMPLETE with timestamp via sam_schema
6. PostToolUse handler updates LastActivity via sam_schema

## Verification Steps

1. Run `grep "task_format" plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py` -- expect no matches
2. Run `grep '\.suffix.*yaml\|\.endswith.*yaml' plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py` -- expect no matches
3. Run existing hook tests: `uv run pytest tests/ -k "task_status_hook" -v`
4. Run `uv run basedpyright plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py`

## CoVe Checks

- Key claims to verify:
  - task_status_hook.py imports from task_format (what exactly is imported?)
  - The `.suffix == ".yaml"` branch locations (are they at lines 548-557 and 615-624?)
  - sam_schema `update_status` and `update_field` function signatures
- Verification questions:
  1. What functions does task_status_hook.py import from task_format?
  2. Where exactly are the extension branching points in the script?
  3. Does `sam_update_status()` accept the same parameters as the current call sites?
- Evidence to collect:
  - Grep task_status_hook.py for "task_format" imports
  - Grep for ".suffix" or "endswith" branching on yaml/md
  - Read sam_schema update_status function signature
- Revision rule:
  - If sam_schema API signatures differ from current call sites, adapt the calls accordingly

---
task: T09
title: "implementation_manager.py: remove local parsers, delegate to sam_schema"
status: complete
completed: 2026-03-15T15:00:00Z
agent: python3-development:python-cli-architect
dependencies: [T01]
priority: 3
complexity: medium
accuracy-risk: low
skills: ["python3-development"]
parallelize-with: [T08, T10, T11]
reason: "T09 modifies implementation_manager.py only. No overlap with T08 (task_status_hook.py), T10 (start-task/SKILL.md), T11 (skill files)."
handoff: "Report: functions removed, imports removed, test results"
started: "2026-03-15T13:23:44Z"
---

## Context

`implementation_manager.py` at `plugins/python3-development/skills/implementation-manager/scripts/implementation_manager.py` currently uses sam_schema as primary reader for `status` and `ready-tasks` but has its own parser for `validate` and `claim-task`. Per architecture spec section 11.4, all local parser functions must be removed and replaced with sam_schema API calls.

## Objective

Remove all local parser functions and `task_format` imports from implementation_manager.py, delegating all operations to sam_schema API.

## Inputs

- Architecture spec: `plan/architect-integrate-sam-schema.md` section 11.4
- Script: `plugins/python3-development/skills/implementation-manager/scripts/implementation_manager.py`
- sam_schema query API: `packages/sam_schema/sam_schema/core/query.py`

## Requirements

1. Remove `parse_task_file()` function
2. Remove `parse_task_content()` function
3. Remove `_apply_claim_to_content()` function
4. Remove `from task_format import ...` imports
5. `validate` command: delegate to `load_plan()` from sam_schema -- if it parses without error, the file is valid
6. `claim-task` command: delegate to `claim_task()` from sam_schema (query.py:177)
7. Ensure `status` and `ready-tasks` commands continue working (already using sam_schema)

## Constraints

- implementation_manager.py continues to exist (deprecation is Phase 2, not this task)
- Do not change the CLI argument interface -- callers pass same arguments
- JSON output shape must remain compatible with existing callers
- Do not modify task_format.py (removed separately after all consumers migrated)

## Expected Outputs

- `plugins/python3-development/skills/implementation-manager/scripts/implementation_manager.py` (modified)

## Acceptance Criteria

1. `grep "task_format" plugins/python3-development/skills/implementation-manager/scripts/implementation_manager.py` returns no matches (AC1, AC2)
2. `grep "parse_task_file\|parse_task_content\|_apply_claim_to_content" plugins/python3-development/skills/implementation-manager/scripts/implementation_manager.py` returns no matches
3. `uv run implementation_manager.py validate . {slug}` works via sam_schema load_plan
4. `uv run implementation_manager.py claim-task {file} {task_id}` works via sam_schema claim_task

## Verification Steps

1. Run `grep "task_format" plugins/python3-development/skills/implementation-manager/scripts/implementation_manager.py`
2. Run `uv run python -c "import ast; ast.parse(open('plugins/python3-development/skills/implementation-manager/scripts/implementation_manager.py').read())"` to verify syntax
3. Run existing tests: `uv run pytest tests/ -k "implementation_manager" -v`
4. Run `uv run basedpyright plugins/python3-development/skills/implementation-manager/scripts/implementation_manager.py`

---
task: T10
title: "start-task skill: migrate to sam claim + sam read"
status: complete
completed: 2026-03-15T15:00:00Z
agent: contextual-ai-documentation-optimizer
dependencies: [T01, T02]
priority: 3
complexity: low
accuracy-risk: low
skills: ["development-harness:clear-cove-task-design"]
parallelize-with: [T08, T09, T11]
reason: "T10 modifies start-task/SKILL.md only. No overlap with T08 (hook script), T09 (implementation_manager.py), T11 (implement-feature + complete-implementation SKILL.md files)."
handoff: "Report: commands replaced, Read tool instructions removed"
started: "2026-03-15T13:23:59Z"
---

## Context

The start-task skill at `plugins/python3-development/skills/start-task/SKILL.md` currently instructs agents to read the full task file via Read tool and claim tasks via `implementation_manager.py claim-task`. Per architecture spec section 11.2, these must be replaced with `sam claim` and `sam read`.

## Objective

Update start-task SKILL.md to use `sam claim P{N}/T{M}` for task claiming and `sam read P{N}/T{M}` for reading task assignments, removing all Read tool instructions for task files.

## Inputs

- Architecture spec: `plan/architect-integrate-sam-schema.md` section 11.2
- Skill file: `plugins/python3-development/skills/start-task/SKILL.md`

## Requirements

1. Replace `uv run implementation_manager.py claim-task {file} {task_id}` with `uv run sam claim P{N}/T{M}`
2. Replace instruction to `Read(task_file_path)` with `uv run sam read P{N}/T{M} --format json`
3. Document that agent receives TaskAssignment JSON with plan goal + context + task details
4. Remove any instruction to manually edit task status via Edit tool
5. Keep hook declaration unchanged (hooks still reference task_status_hook.py via CLAUDE_SKILL_DIR)

## Constraints

- Do not modify hook declarations in SKILL.md frontmatter
- Do not change the skill's activation syntax or arguments
- Keep existing step numbering structure intact where possible

## Expected Outputs

- `plugins/python3-development/skills/start-task/SKILL.md` (modified)

## Acceptance Criteria

1. `grep -c "implementation_manager" plugins/python3-development/skills/start-task/SKILL.md` returns 0 (AC8 partial)
2. No instruction to use Read tool on task files (AC8)
3. `sam claim` command present in skill instructions
4. `sam read` command present with `--format json` in skill instructions

## Verification Steps

1. Run `grep "implementation_manager" plugins/python3-development/skills/start-task/SKILL.md` -- expect no matches
2. Run `grep "Read(" plugins/python3-development/skills/start-task/SKILL.md` -- expect no task file reads
3. Run `grep "sam claim" plugins/python3-development/skills/start-task/SKILL.md` -- expect match
4. Run `uv run prek run --files plugins/python3-development/skills/start-task/SKILL.md`

---
task: T11
title: "implement-feature + complete-implementation skills: migrate to sam CLI"
status: complete
completed: 2026-03-15T15:00:00Z
agent: contextual-ai-documentation-optimizer
dependencies: [T02]
priority: 3
complexity: low
accuracy-risk: low
skills: ["development-harness:clear-cove-task-design"]
parallelize-with: [T08, T09, T10]
reason: "T11 modifies implement-feature/SKILL.md and complete-implementation/SKILL.md. No overlap with T08 (hook script), T09 (implementation_manager.py), T10 (start-task/SKILL.md)."
handoff: "Report: commands replaced per skill, implementation_manager references removed"
started: "2026-03-15T13:23:35Z"
---

## Context

Two orchestration skills currently reference `implementation_manager.py` for task queries:
- `implement-feature` calls `implementation_manager.py status` and `ready-tasks`
- `complete-implementation` passes raw file paths to agents and reads task files for metadata

Per architecture spec sections 11.5 and 11.6, both must switch to sam CLI commands.

## Objective

Update implement-feature and complete-implementation SKILL.md files to use `sam status`, `sam ready`, and `sam read` instead of implementation_manager.py and direct file reads.

## Inputs

- Architecture spec: `plan/architect-integrate-sam-schema.md` sections 11.5, 11.6
- `plugins/python3-development/skills/implement-feature/SKILL.md`
- `plugins/python3-development/skills/complete-implementation/SKILL.md`

## Requirements

### implement-feature
1. Replace `uv run implementation_manager.py status . {slug}` with `uv run sam status P{N}`
2. Replace `uv run implementation_manager.py ready-tasks . {slug}` with `uv run sam ready P{N} --format json`
3. Update JSON output shape references if they differ between implementation_manager and sam CLI

### complete-implementation
4. Replace file-path passing with instruction to use `uv run sam read P{N}/T{M}` for task data
5. Replace plan-level status queries with `uv run sam status P{N} --format json`
6. Quality gate agents receive TaskAssignment JSON, not raw file paths

## Constraints

- Do not change skill activation syntax or arguments
- Do not modify hook declarations
- Keep existing workflow structure (phases, agent dispatch order)

## Expected Outputs

- `plugins/python3-development/skills/implement-feature/SKILL.md` (modified)
- `plugins/python3-development/skills/complete-implementation/SKILL.md` (modified)

## Acceptance Criteria

1. `grep -c "implementation_manager" plugins/python3-development/skills/implement-feature/SKILL.md` returns 0
2. `grep -c "implementation_manager" plugins/python3-development/skills/complete-implementation/SKILL.md` returns 0
3. `sam status` and `sam ready` commands present in implement-feature skill
4. `sam read` command present in complete-implementation skill

## Verification Steps

1. Run `grep "implementation_manager" plugins/python3-development/skills/implement-feature/SKILL.md` -- expect no matches
2. Run `grep "implementation_manager" plugins/python3-development/skills/complete-implementation/SKILL.md` -- expect no matches
3. Run `grep "sam status\|sam ready" plugins/python3-development/skills/implement-feature/SKILL.md` -- expect matches
4. Run `uv run prek run --files plugins/python3-development/skills/implement-feature/SKILL.md`
5. Run `uv run prek run --files plugins/python3-development/skills/complete-implementation/SKILL.md`

---
task: T12
title: "swarm-task-planner agent: remove inline schema, use sam create"
status: complete
completed: 2026-03-15T16:00:00Z
agent: contextual-ai-documentation-optimizer
dependencies: [T01]
priority: 4
complexity: medium
accuracy-risk: low
skills: ["development-harness:clear-cove-task-design"]
parallelize-with: [T13]
reason: "T12 modifies swarm-task-planner.md in python3-development only. T13 modifies context-gathering.md and context-refinement.md. No file overlap."
handoff: "Report: lines removed (inline schema), sam create instruction added, TASK_FILE_FORMAT.md reference added"
started: "2026-03-15T13:35:36Z"
---

## Context

The swarm-task-planner agent at `plugins/python3-development/agents/swarm-task-planner.md` currently embeds a YAML schema definition (approximately lines 258-320) and writes task files via the Write tool. Per architecture spec section 11.1, the inline schema must be removed and replaced with `sam create` instruction + reference to TASK_FILE_FORMAT.md.

## Objective

Update swarm-task-planner agent prompt to generate YAML task content and pipe to `sam create` instead of using Write tool with embedded schema.

## Inputs

- Architecture spec: `plan/architect-integrate-sam-schema.md` section 11.1
- Agent file: `plugins/python3-development/agents/swarm-task-planner.md`
- TASK_FILE_FORMAT.md: `.claude/docs/TASK_FILE_FORMAT.md` (rewritten in T04)

## Requirements

1. Remove inline YAML schema definition from agent prompt (the section defining task fields, typically lines 258-320)
2. Add instruction: generate task definitions as YAML and create plan using `echo "$YAML_CONTENT" | uv run sam create {slug} --goal "{goal}" --stdin`
3. Reference TASK_FILE_FORMAT.md for field definitions instead of embedding schema
4. Note that `sam create` validates all fields -- agent does not need full schema knowledge
5. Keep all other agent prompt content intact (CLEAR task writing standards, parallelization rules, etc.)

## Constraints

- Do not remove non-schema content from the agent prompt
- Keep the agent's planning methodology, dependency analysis, and sync checkpoint logic
- The `sam create` command must match the interface defined in T01
- Do not modify the development-harness copy (that is T14)

## Expected Outputs

- `plugins/python3-development/agents/swarm-task-planner.md` (modified)

## Acceptance Criteria

1. No inline YAML schema definition remains in the agent prompt (AC7)
2. `sam create` instruction is present with `--stdin` flag
3. Reference to TASK_FILE_FORMAT.md is present for field definitions
4. No `Write(` instruction for task files remains in the agent prompt

## Verification Steps

1. Run `grep -c "Write(" plugins/python3-development/agents/swarm-task-planner.md` -- expect 0 for task file writes
2. Run `grep "sam create" plugins/python3-development/agents/swarm-task-planner.md` -- expect match
3. Run `grep "TASK_FILE_FORMAT" plugins/python3-development/agents/swarm-task-planner.md` -- expect match
4. Run `uv run prek run --files plugins/python3-development/agents/swarm-task-planner.md`

---
task: T13
title: "context-gathering + context-refinement agents: replace Read/Edit with sam update"
status: complete
started: "2026-03-15T14:00:00Z"
completed: "2026-03-15T14:30:00Z"
agent: contextual-ai-documentation-optimizer
dependencies: [T01]
priority: 4
complexity: low
accuracy-risk: low
skills: ["development-harness:clear-cove-task-design"]
parallelize-with: [T12]
reason: "T13 modifies context-gathering.md and context-refinement.md. T12 modifies swarm-task-planner.md. No file overlap."
handoff: "Report: Read/Edit instructions removed, sam update instructions added per agent"
---

## Context

Two agents currently read task files via Read tool and append content via Edit tool:
- `context-gathering.md` reads task files and appends Context Manifest sections
- `context-refinement.md` reads task files and updates Context Manifest + checks plan artifact freshness

Per architecture spec section 11.7, both must switch to `sam read` for reading and `sam update` for writing.

## Objective

Update context-gathering and context-refinement agent prompts to use `sam read` for task data and `sam update` for context/section appending, removing all Read/Edit tool instructions for task files.

## Inputs

- Architecture spec: `plan/architect-integrate-sam-schema.md` section 11.7
- `plugins/python3-development/agents/context-gathering.md`
- `plugins/python3-development/agents/context-refinement.md`

## Requirements

### context-gathering agent
1. Remove instruction to use Read tool on task file
2. Remove instruction to use Edit tool to append Context Manifest
3. Add instruction: `uv run sam update P{N} --context "Context Manifest content"`
4. Add instruction: `uv run sam read P{N} --format json` for reading plan data

### context-refinement agent
5. Remove instruction to use Read tool on task file
6. Remove instruction to use Edit tool for Context Manifest updates
7. Add instruction: `uv run sam update P{N}/T{M} --append-section "Divergence Notes" --section-content "..."`
8. Add instruction: `uv run sam read P{N} --format json` for reading plan data

## Constraints

- Do not change agent frontmatter (name, description, tools, model)
- Keep plan artifact freshness check logic in context-refinement
- Do not modify development-harness copies (that is T14)

## Expected Outputs

- `plugins/python3-development/agents/context-gathering.md` (modified)
- `plugins/python3-development/agents/context-refinement.md` (modified)

## Acceptance Criteria

1. No `Edit(` instruction for task files in context-gathering agent (AC9)
2. No `Read(` instruction for task files in context-gathering agent
3. `sam update` instruction present in context-gathering agent
4. `sam update` instruction present in context-refinement agent
5. `sam read` instruction present in both agents

## Verification Steps

1. Run `grep "Edit(" plugins/python3-development/agents/context-gathering.md` -- expect no task file edits
2. Run `grep "sam update" plugins/python3-development/agents/context-gathering.md` -- expect match
3. Run `grep "sam update" plugins/python3-development/agents/context-refinement.md` -- expect match
4. Run `uv run prek run --files plugins/python3-development/agents/context-gathering.md`
5. Run `uv run prek run --files plugins/python3-development/agents/context-refinement.md`

---
task: T14
title: "development-harness sync + workshop copies + local-workflow.md update"
status: complete
completed: 2026-03-15T17:00:00Z
agent: contextual-ai-documentation-optimizer
dependencies: [T12, T13]
priority: 5
complexity: medium
accuracy-risk: low
skills: ["development-harness:clear-cove-task-design"]
parallelize-with: []
reason: "T14 is the final sync task. Must wait for T12 and T13 to complete so the source agent files are finalized before copying."
handoff: "Report: files synced (list), workshop files updated, local-workflow.md references updated, diff verification"
started: "2026-03-15T13:42:11Z"
---

## Context

The development-harness plugin contains copies of agents from python3-development (section 15 of architecture spec). After T12 and T13 update the python3-development agents, the development-harness copies must be synchronized. Additionally, workshop skill copies and `local-workflow.md` need updating.

This task was merged from three planned changes (development-harness sync, workshop updates, local-workflow.md references) to avoid coordination overhead since they share no file conflicts but depend on the same upstream changes.

## Objective

Synchronize development-harness agent copies with updated python3-development agents, update workshop copies, and update local-workflow.md to reference sam CLI instead of implementation_manager.py.

## Inputs

- Architecture spec: `plan/architect-integrate-sam-schema.md` section 15
- Updated agents from T12: `plugins/python3-development/agents/swarm-task-planner.md`
- Updated agents from T13: `plugins/python3-development/agents/context-gathering.md`, `plugins/python3-development/agents/context-refinement.md`
- Development-harness agent copies: `plugins/development-harness/agents/`
- Workshop copies: `workshops/.claude/skills/implement-embedded-feature/SKILL.md`, `workshops/.cursor/skills/implement-embedded-feature/SKILL.md`
- Local workflow doc: `.claude/rules/local-workflow.md`

## Requirements

### development-harness sync
1. Copy updated `swarm-task-planner.md` from python3-development to development-harness
2. Copy updated `context-gathering.md` from python3-development to development-harness
3. Copy updated `context-refinement.md` from python3-development to development-harness
4. Update `plugins/development-harness/skills/implementation-manager/SKILL.md` to reference sam CLI instead of implementation_manager.py (if this file exists)

### Workshop copies
5. Update `workshops/.claude/skills/implement-embedded-feature/SKILL.md` to replace Read/Edit task file instructions with sam CLI commands
6. Update `workshops/.cursor/skills/implement-embedded-feature/SKILL.md` with same changes

### local-workflow.md
7. Update `.claude/rules/local-workflow.md` to replace all `implementation_manager.py` references with sam CLI equivalents in documentation sections
8. Update command examples (e.g., `uv run implementation_manager.py status . {slug}` -> `uv run sam status P{N}`)

## Constraints

- Agent copies must match python3-development versions exactly (diff should show no differences after sync)
- Do not modify python3-development agent files (those are done in T12/T13)
- Workshop skill changes should be minimal -- only replace the task file access commands
- local-workflow.md: update documentation references only, do not change workflow structure

## Expected Outputs

- `plugins/development-harness/agents/swarm-task-planner.md` (synced)
- `plugins/development-harness/agents/context-gathering.md` (synced)
- `plugins/development-harness/agents/context-refinement.md` (synced)
- `workshops/.claude/skills/implement-embedded-feature/SKILL.md` (modified)
- `workshops/.cursor/skills/implement-embedded-feature/SKILL.md` (modified)
- `.claude/rules/local-workflow.md` (modified)

## Acceptance Criteria

1. `diff plugins/python3-development/agents/swarm-task-planner.md plugins/development-harness/agents/swarm-task-planner.md` shows no differences (AC11)
2. `diff plugins/python3-development/agents/context-gathering.md plugins/development-harness/agents/context-gathering.md` shows no differences (AC11)
3. `diff plugins/python3-development/agents/context-refinement.md plugins/development-harness/agents/context-refinement.md` shows no differences (AC11)
4. Workshop SKILL.md files reference sam CLI commands, not Read/Edit tool for task files (AC12)
5. `grep -c "implementation_manager" .claude/rules/local-workflow.md` returns 0 or only in deprecation context
6. `grep "sam status\|sam ready\|sam read\|sam claim" .claude/rules/local-workflow.md` returns matches

## Verification Steps

1. Run `diff plugins/python3-development/agents/swarm-task-planner.md plugins/development-harness/agents/swarm-task-planner.md`
2. Run `diff plugins/python3-development/agents/context-gathering.md plugins/development-harness/agents/context-gathering.md`
3. Run `diff plugins/python3-development/agents/context-refinement.md plugins/development-harness/agents/context-refinement.md`
4. Run `grep "implementation_manager" workshops/.claude/skills/implement-embedded-feature/SKILL.md` -- expect no matches
5. Run `uv run prek run --files .claude/rules/local-workflow.md`
6. Run `uv run prek run --files workshops/.claude/skills/implement-embedded-feature/SKILL.md`
