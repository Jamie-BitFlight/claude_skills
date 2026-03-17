# Feature Context: Integrate sam_schema as Sole Task File Interface

## Document Metadata

- **Generated**: 2026-03-15
- **Input Type**: existing_document
- **Source**: `.claude/backlog/p0-integrate-samschema-as-sole-task-file-interface-across-all-s.md` (Issue #719, P0)
- **Status**: DISCOVERY_COMPLETE

---

## Original Request

Seven SAM workflow components access task files through direct file operations (Read/Edit/Write tools) with independent format assumptions. The sam_schema module exists (`packages/sam_schema/`) with CLI and MCP interfaces but no component uses them. Task files are accessed through 4 different parsers producing format drift and data loss. Integrate sam_schema as the sole interface for all task file operations across all SAM workflow components.

---

## Core Intent Analysis

### WHO (Target Users)

1. **SAM workflow orchestrator** (`/implement-feature`, `/add-new-feature`) -- the skill that loops through tasks and dispatches agents
2. **Sub-agents** (`start-task`, `context-gathering`, `swarm-task-planner`) -- agents that read/write task data as part of their work
3. **Hook scripts** (`task_status_hook.py`) -- automated scripts triggered by Claude Code events that update task lifecycle fields
4. **CLI scripts** (`implementation_manager.py`) -- the current task query interface, partially integrated with sam_schema

### WHAT (Desired Outcome)

Every SAM workflow component uses the `sam` CLI or MCP tools as its sole interface to task data. No component reads or writes task files directly via Read/Edit/Write tools. The sam interface handles format detection, content extraction, and state updates regardless of backing store.

Observable success criteria from the backlog item:
- An agent assigned a task calls `sam read {slug}/T3` and receives plan goal, shared context, and task details without reading any file
- The `swarm-task-planner` calls `sam create` and produces valid pure YAML
- The `task_status_hook` calls `sam state` instead of its own regex parser
- `implementation_manager.py` is either replaced by or becomes a thin wrapper around the `sam` CLI

### WHEN (Trigger Conditions)

This feature is triggered every time a SAM workflow executes -- during planning (`/add-new-feature`), execution (`/implement-feature`), and completion (`/complete-implementation`). Every task lifecycle transition touches the affected components.

### WHY (Problem Being Solved)

**Format drift and data loss**: 4 independent parsers (sam_schema YAML reader, task_format.py regex, implementation_manager.py's own parser, and agent-embedded format assumptions) produce inconsistent interpretations of the same task files. Fields parsed by one component are silently lost or misinterpreted by another.

**Backend lock-in**: Direct file I/O means every component is coupled to the filesystem. Moving to GitHub Issues, SQLite, or any other backing store requires changing every component independently.

**ARL alignment**: Per the [ARL research](./plugins/agentskill-kaizen/references/arl.md), autonomous execution requires machine-verifiable interfaces between components. Direct file manipulation is not machine-verifiable -- there is no schema validation, no contract enforcement, and no way to detect format violations before they propagate. The sam_schema module provides the contract layer that ARL gate R3 (input validation) requires.

---

## Codebase Research

### Similar Patterns Found

#### Pattern 1: sam_schema CLI (existing, unused by workflow)

- **Location**: `packages/sam_schema/sam_schema/cli.py:1-366`
- **Relevance**: This is the interface that all components should use. Provides `read`, `state`, `ready`, `status`, `migrate` commands with JSON/YAML/Rich output.
- **Reusable**: Entire CLI is the target interface. Commands already exist for read, status update, ready-task query, and migration.

#### Pattern 2: sam_schema MCP server (existing, unused by workflow)

- **Location**: `packages/sam_schema/sam_schema/server.py:1-127`
- **Relevance**: Provides `sam_read`, `sam_state`, `sam_ready`, `sam_status` as MCP tools. Agents with MCP access could use these instead of CLI.
- **Reusable**: Direct MCP tool access for agents within Claude Code sessions.

#### Pattern 3: sam_schema query layer with claim_task

- **Location**: `packages/sam_schema/sam_schema/core/query.py:177-202`
- **Relevance**: `claim_task()` exists in the Python API but is NOT exposed via CLI or MCP. The `start-task` skill currently calls `implementation_manager.py claim-task` which uses its own parser for some operations.
- **Reusable**: The function is ready; it needs CLI and MCP exposure.

#### Pattern 4: task_status_hook partial integration

- **Location**: `plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py`
- **Relevance**: Already uses sam_schema for `.yaml` files but falls back to its own parser (`parse_yaml_frontmatter` + regex) for `.md` files. Demonstrates the split-brain problem this feature solves.
- **Reusable**: The sam_schema code path in this script is the target pattern; the fallback path is what gets removed.

#### Pattern 5: implementation_manager partial integration

- **Location**: `plugins/python3-development/skills/implementation-manager/scripts/implementation_manager.py`
- **Relevance**: Uses sam_schema as primary reader for `status` and `ready-tasks` commands, but its own parser for `validate` and `claim-task`. Demonstrates partial migration state.
- **Reusable**: The sam_schema-using code paths are the reference pattern.

#### Pattern 6: Addressing system

- **Location**: `packages/sam_schema/sam_schema/core/addressing.py:1-132`
- **Relevance**: Provides `P{N}/T{M}` address resolution and slug matching. Currently resolves `tasks-{N}-{slug}` filenames. The user decision to use `P{issue}-{slug}.yaml` naming would need this module updated.
- **Reusable**: Address parsing and resolution logic.

### Existing Infrastructure

The sam_schema module already provides:
- **Models**: `Task`, `Plan`, `PlanStatus`, `ReadResult`, `SchemaGap` (`packages/sam_schema/sam_schema/core/models.py`)
- **Readers**: Format detection, YAML reader, legacy markdown reader, frontmatter reader, manifest reader, normalization (`packages/sam_schema/sam_schema/readers/`)
- **Writers**: Atomic YAML write (single file or directory), per-field update preserving comments (`packages/sam_schema/sam_schema/writers/yaml_writer.py`)
- **Query**: load_plan, get_task, list_tasks, get_ready_tasks, update_status, get_plan_status, claim_task (`packages/sam_schema/sam_schema/core/query.py`)
- **Dependencies**: Cycle detection, ready-task computation, blocked-task identification (`packages/sam_schema/sam_schema/core/dependencies.py`)
- **CLI**: `sam read`, `sam state`, `sam ready`, `sam status`, `sam migrate` (`packages/sam_schema/sam_schema/cli.py`)
- **MCP**: `sam_read`, `sam_state`, `sam_ready`, `sam_status` (`packages/sam_schema/sam_schema/server.py`)

### Code References

- `packages/sam_schema/sam_schema/cli.py:148-191` -- `sam read` command (reads task, outputs JSON/YAML/Rich)
- `packages/sam_schema/sam_schema/cli.py:193-243` -- `sam state` command (updates task status)
- `packages/sam_schema/sam_schema/cli.py:246-272` -- `sam ready` command (lists ready tasks)
- `packages/sam_schema/sam_schema/cli.py:275-307` -- `sam status` command (plan progress summary)
- `packages/sam_schema/sam_schema/cli.py:310-365` -- `sam migrate` command (legacy to pure YAML)
- `packages/sam_schema/sam_schema/core/query.py:177-202` -- `claim_task()` (NOT exposed via CLI/MCP)
- `packages/sam_schema/sam_schema/core/addressing.py:41-85` -- `resolve_plan_address()` (resolves `tasks-{N}-{slug}` patterns)
- `packages/sam_schema/sam_schema/writers/yaml_writer.py:242-289` -- `write_plan()` (single file or directory output)
- `.claude/docs/TASK_FILE_FORMAT.md:179-235` -- Authorized Writers table (field ownership rules)

---

## Use Scenarios

### Scenario 1: Agent Reads Its Task Assignment

**Actor**: Sub-agent spawned by `/start-task`
**Trigger**: Agent is dispatched to work on task T3 in plan P719
**Goal**: Receive plan context, shared goals, and task-specific details without reading any file directly
**Expected Outcome**: Agent calls `sam read P719/T3 --format json` (or uses `sam_read` MCP tool) and receives a JSON payload containing: plan goal, plan context, task ID, title, status, acceptance criteria, verification steps, constraints, and all other task fields. Agent never calls `Read` on a task file.

### Scenario 2: Task Planner Creates a New Plan

**Actor**: `swarm-task-planner` agent during `/add-new-feature`
**Trigger**: Architecture spec is complete, agent needs to produce task decomposition
**Goal**: Create a valid SAM task plan file through the `sam` interface
**Expected Outcome**: Agent calls `sam create` with plan metadata and task definitions (exact input format TBD -- see Q1). The sam CLI validates all fields against the schema, writes pure YAML using atomic writes, and returns the output path. No Write tool call on task files.

### Scenario 3: Hook Updates Task Status on Agent Completion

**Actor**: `task_status_hook.py` (SubagentStop handler)
**Trigger**: Claude Code fires SubagentStop event after a sub-agent finishes
**Goal**: Mark the task as complete with a timestamp
**Expected Outcome**: Hook calls `sam state P{N}/T{M} complete` (CLI) or equivalent Python API. The sam interface handles format detection (whether file is .yaml, .md, or directory), updates the status field, adds the completed timestamp, and writes atomically. Hook does not parse the file itself.

### Scenario 4: Orchestrator Queries Ready Tasks

**Actor**: `/implement-feature` orchestrator skill
**Trigger**: Orchestrator needs to find the next task to dispatch
**Goal**: Get list of tasks whose dependencies are all satisfied
**Expected Outcome**: Orchestrator calls `sam ready P{N} --format json` and receives a JSON array of ready task objects. Each object includes task ID, title, agent, skills, and priority. Orchestrator does not call `implementation_manager.py ready-tasks`.

### Scenario 5: Context-Gathering Agent Appends Context Manifest

**Actor**: `context-gathering` agent during `/add-new-feature` Phase 6
**Trigger**: Agent has gathered context and needs to append it to the task file
**Goal**: Add a Context Manifest section to the plan or task
**Expected Outcome**: Agent uses `sam update` (TBD -- see Q3) to write the context field on the plan or task. The sam interface handles the write atomically. Agent does not call `Edit` on the task file.

---

## Gap Analysis

### Identified Gaps

| # | Category | Gap Description | Impact |
|---|----------|-----------------|--------|
| 1 | Scope | `sam create` command does not exist in CLI or MCP | swarm-task-planner cannot produce task files through sam interface |
| 2 | Scope | `sam claim` command does not exist in CLI or MCP (but `claim_task()` exists in Python API) | start-task cannot claim tasks through sam interface |
| 3 | Scope | `sam update` (general field update) does not exist in CLI or MCP (only `sam state` for status) | context-gathering and other agents cannot update arbitrary fields |
| 4 | Scope | Naming convention change: user decided `P{issue}-{slug}.yaml` but addressing module resolves `tasks-{N}-{slug}` | Address resolution will fail with new naming convention |
| 5 | Behavior | `sam read` returns task fields but not plan-level context (goal, shared context) in the same response | Agents need both plan context and task details in one call |
| 6 | Integration | TASK_FILE_FORMAT.md Authorized Writers table references `implementation_manager.py` and `task_status_hook.py` by name -- needs updating if those scripts change their write path | Documentation drift if scripts are refactored |
| 7 | Scope | Legacy `.md` format support -- unclear if this integration should also remove legacy format support or maintain backwards compatibility during transition | Affects scope of reader changes |
| 8 | Integration | `implementation_manager.py` overlaps with `sam` CLI -- unclear whether it gets replaced, wrapped, or coexists | Two CLIs doing similar things creates confusion |

---

## Questions Requiring Resolution

### Q1: What inputs does `sam create` accept?

- **Category**: Behavior
- **Gap**: Gap #1 -- `sam create` does not exist
- **Question**: When the `swarm-task-planner` agent creates a new plan, what is the input format? Does it pipe a YAML document to stdin, pass a file path to a template, or provide structured arguments? Does `sam create` accept plan metadata (feature, goal, description) separately from task definitions, or as a single document?
- **Options**:
  - A) Single YAML document on stdin containing plan metadata + tasks array
  - B) Plan metadata as CLI arguments + tasks as a YAML file path
  - C) A directory path where the agent has already written files, and `sam create` validates and normalizes them
- **Why It Matters**: Determines how agents interact with the create interface. Option A is simplest for LLM agents (write YAML to stdout, pipe to sam). Option C preserves current Write-then-validate pattern.
- **Resolution**: _pending_

### Q2: Does `P{issue}-{slug}.yaml` replace `tasks-{N}-{slug}` naming?

- **Category**: Scope
- **Gap**: Gap #4 -- naming convention change
- **Question**: The user decided on `P{issue}-{slug}.yaml` naming. Does this replace the current `tasks-{N}-{slug}` pattern entirely? What does `{issue}` refer to -- the GitHub issue number (e.g., P719)? How does this affect existing plan files?
- **Options**:
  - A) New naming convention for all new plans; existing plans keep old names until migrated
  - B) All plans (existing and new) must be renamed
  - C) Both conventions coexist permanently; addressing module supports both
- **Why It Matters**: The addressing module (`addressing.py`) currently resolves `tasks-{N}-{slug}` patterns. Changing the naming convention requires updating the resolution logic, and migrating existing files or supporting dual patterns.
- **Resolution**: _pending_

### Q3: How does `sam update` work for non-status fields?

- **Category**: Behavior
- **Gap**: Gap #3 -- no general field update command
- **Question**: The context-gathering agent needs to write a Context Manifest, the start-task agent needs to write divergence notes, and other agents may need to update arbitrary fields. Should `sam update` be a general `sam update P{N}/T{M} --field context-notes --value "..."` command, or should there be specific commands for each use case (e.g., `sam context`, `sam divergence`)?
- **Options**:
  - A) Generic `sam update P{N}/T{M} field=value` (one command, any field)
  - B) Specific commands per use case (`sam context`, `sam divergence`, etc.)
  - C) Generic update for metadata fields + a separate `sam append` for body content
- **Why It Matters**: The `update_field` and `update_fields` functions already exist in the writer (`yaml_writer.py:417-501`). This is about CLI/MCP surface design, not capability.
- **Resolution**: _pending_

### Q4: What happens to `implementation_manager.py`?

- **Category**: Integration
- **Gap**: Gap #8 -- overlapping CLIs
- **Question**: `implementation_manager.py` currently provides `list-features`, `status`, `ready-tasks`, `validate`, and `claim-task`. The `sam` CLI provides `read`, `state`, `ready`, `status`, `migrate`. Should `implementation_manager.py` be replaced entirely by the `sam` CLI, become a thin wrapper, or coexist for backwards compatibility?
- **Options**:
  - A) Replace entirely -- all callers switch to `sam` CLI
  - B) Thin wrapper -- `implementation_manager.py` delegates to `sam` CLI internally
  - C) Coexist -- both CLIs remain, with sam_schema as the shared library layer
- **Why It Matters**: The backlog item says "implementation_manager.py is either replaced by or becomes a thin wrapper around the sam CLI." But the skill docs (`local-workflow.md`) and hook scripts reference `implementation_manager.py` by path. Changing the entry point affects all callers.
- **Resolution**: _pending_

### Q5: Should `sam read` return plan context alongside task details?

- **Category**: Behavior
- **Gap**: Gap #5 -- plan context not included in task read
- **Question**: When an agent calls `sam read P{N}/T{M}`, should the response include plan-level fields (goal, context, acceptance criteria) alongside the task fields? Or should agents make two calls (`sam status P{N}` for plan context + `sam read P{N}/T{M}` for task)?
- **Options**:
  - A) `sam read` returns task fields only; plan context via separate `sam plan P{N}` command
  - B) `sam read` returns both plan context and task fields in a single response (nested JSON)
  - C) `sam read` has a `--with-context` flag that optionally includes plan-level fields
- **Why It Matters**: The backlog item explicitly states agents should get "plan goal, shared context, and its task details" from a single call. This is core to the HOOTL vision -- reducing the number of interactions an agent needs.
- **Resolution**: _pending_

### Q6: Should legacy `.md` format support be removed as part of this integration?

- **Category**: Scope
- **Gap**: Gap #7 -- legacy format support
- **Question**: The sam_schema readers support legacy markdown, YAML frontmatter, and pure YAML formats. Task_status_hook and implementation_manager maintain their own fallback parsers for `.md` files. Should this integration also sunset the `.md` format, or maintain backwards compatibility?
- **Options**:
  - A) Remove `.md` support -- all files must be pure YAML after migration
  - B) Keep `.md` read support but only write pure YAML
  - C) Keep full `.md` read/write support (current state, just route through sam_schema)
- **Why It Matters**: Removing `.md` support simplifies the codebase significantly but requires migrating all existing task files first. Keeping it means the sam_schema readers handle the complexity centrally instead of each component doing it independently.
- **Resolution**: _pending_

---

## Goals (Pending Resolution)

_These goals will be finalized after questions are resolved._

1. All 7 SAM workflow components use `sam` CLI or MCP tools as their sole interface to task data
2. No component uses Read/Edit/Write tools directly on task files
3. `sam create` command exists and is used by swarm-task-planner for plan creation
4. `sam claim` command exists and is used by start-task for task claiming
5. `sam update` (or equivalent) exists for general field updates (context, divergence notes, etc.)
6. Addressing module supports the `P{issue}-{slug}.yaml` naming convention
7. `implementation_manager.py` role is clarified (replaced, wrapped, or coexistent)
8. TASK_FILE_FORMAT.md Authorized Writers table is updated to reflect new write paths
9. Legacy `.md` format handling is centralized in sam_schema (regardless of whether format is sunset)

---

## Next Steps

After questions are resolved:

1. Update "Resolution" fields in Questions section
2. Finalize Goals section
3. Proceed to RT-ICA assessment
4. Then proceed to architecture design
