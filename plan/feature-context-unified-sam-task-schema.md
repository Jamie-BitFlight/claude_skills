# Feature Context: Unified SAM Task/Plan Schema Module

## Document Metadata

- **Generated**: 2026-03-14
- **Input Type**: simple_description
- **Source**: Issue #715 — Unified task/plan schema module with pure YAML data format, CLI and MCP interface
- **Status**: DISCOVERY_COMPLETE

---

## Original Request

Create a single shared Python module that is the sole interface for reading, writing, and querying SAM task/plan files. The canonical format is pure YAML (not markdown). Markdown content lives inside YAML multiline string fields. The module provides both CLI (`sam read P1/T3`, `sam state P1/T3 in_progress`, `sam ready P1`, `sam status P1`) and MCP server interfaces. Legacy markdown and YAML-frontmatter-in-markdown formats are read-only backward compatible. Schema gap detection reports missing fields on legacy reads. All consumers go through this single module — no ad-hoc file parsing.

---

## Core Intent Analysis

### WHO (Target Users)

1. **SAM pipeline components** — swarm-task-planner (writes plans), implementation_manager (reads status/ready tasks), task_status_hook (updates status/timestamps), start-task skill (claims tasks), implement-feature skill (orchestration loop)
2. **Human operators** — developers who inspect task status via CLI or need to debug SAM stalls
3. **MCP clients** — agents and hooks that call task operations programmatically through the MCP server

### WHAT (Desired Outcome)

A single Python module that:
- Defines the canonical task/plan schema as typed YAML (structural fields are YAML-native, rich text content is markdown inside YAML multiline scalars)
- Reads any existing task file format (three known variants) and normalizes to the canonical model
- Writes only pure YAML output
- Exposes CLI commands: `sam read P1/T3`, `sam state P1/T3 in_progress`, `sam ready P1`, `sam status P1`
- Exposes equivalent MCP tools: `sam_read`, `sam_state`, `sam_ready`, `sam_status` (naming TBD)
- Reports schema gaps when reading legacy formats (which optional fields are absent per task)
- Becomes the sole interface — no consumer parses task files directly

### WHEN (Trigger Conditions)

- **Immediate trigger**: `uv run implementation_manager.py status . backlog-state-reconciliation` returned `total_tasks: 0` with a YAML parse warning because the task file used a format variant (`tasks:` list in global frontmatter + prose task descriptions in markdown body) that no parser handles
- **Recurring trigger**: Every time swarm-task-planner produces a format variant not anticipated by the current parsers, the SAM pipeline stalls silently with zero visible tasks
- **Systemic trigger**: Five independent scripts parse task files with different format assumptions, creating N points of failure for each format change

### WHY (Problem Being Solved)

**No shared contract exists between task file producers and consumers.** The swarm-task-planner writes files, but there is no schema that both the planner and the implementation_manager agree on. When the planner's output drifts (as observed with `plan/tasks-1-backlog-state-reconciliation.md`), consumers fail silently — returning zero tasks instead of an error. Five scripts independently parse task files using different regex patterns and YAML detection heuristics. Each new format variant requires fixes across multiple scripts.

---

## Codebase Research

### Similar Patterns Found

#### Pattern 1: task_format.py — Shared YAML Frontmatter Utilities

- **Location**: `plugins/python3-development/skills/implementation-manager/scripts/task_format.py:1-321`
- **Relevance**: This is the closest existing pattern to the desired shared module. It provides `parse_yaml_frontmatter()`, `update_yaml_field()`, `normalize_status()`, and `resolve_task_id()`. Both `implementation_manager.py` and `task_status_hook.py` import from it.
- **Reusable**: The status normalization logic (`STATUS_MAP`, `normalize_status()`), YAML field update function (`update_yaml_field()`), and task ID resolution (`resolve_task_id()`) are directly reusable. The YAML frontmatter parsing would be replaced by the new module's more comprehensive readers.

#### Pattern 2: implementation_manager.py — Multi-Format Task Parser

- **Location**: `plugins/python3-development/skills/implementation-manager/scripts/implementation_manager.py:479-593`
- **Relevance**: Contains `parse_task_content()`, `_parse_multi_task_body()`, `parse_task_file()`, and `_parse_task_directory()`. This is the primary parsing logic that fails on the global-manifest format. It detects single-task vs multi-task files and handles directory-based task organization.
- **Reusable**: The `Task` dataclass, `TaskStatus` enum, the directory discovery logic, and the natural sort key (`_task_sort_key`) are reusable. The parsing logic itself is what needs to be replaced by the unified module.

#### Pattern 3: task_status_hook.py — Regex-Based Task Section Finder

- **Location**: `plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py:245-370`
- **Relevance**: Uses its own regex patterns (`find_task_section()`, `update_task_status()`, `add_timestamp_to_task()`) to locate and modify task sections in files. These functions operate on raw file content using line-by-line scanning — separate from both `task_format.py` and `implementation_manager.py`. This is a third independent parser.
- **Reusable**: The timestamp formatting (`get_iso_timestamp()`) and the context file management (`read_task_context()`, `write_task_context()`, `delete_task_context()`) are reusable. The regex-based section finding would be replaced.

#### Pattern 4: split_task_file.py and migrate_task_format.py — Format Conversion Scripts

- **Location**: `plugins/python3-development/scripts/split_task_file.py`, `plugins/python3-development/scripts/migrate_task_format.py`
- **Relevance**: These scripts have their own parsing logic for reading task files in various formats and converting them. They represent the fourth and fifth independent parsers in the codebase.
- **Reusable**: The split logic (single file to directory) and migration logic (legacy markdown to YAML) are useful operations that the new module could expose or that these scripts could delegate to the new module.

### Existing Infrastructure

- **Pydantic**: Already a project dependency (used by `backlog_core` and other modules). Available for schema definition.
- **ruamel.yaml**: Already the project's standard YAML library (per `.claude/rules/yaml-toml-libraries.md`). Used in `task_format.py`.
- **TASK_FILE_FORMAT.md**: Comprehensive specification at `.claude/docs/TASK_FILE_FORMAT.md` with JSON Schema, field definitions, status values, authorized writers table, and migration guide. This is the existing schema source of truth.
- **Existing tests**: `plugins/python3-development/skills/implementation-manager/scripts/test_task_parsing.py` has tests for YAML frontmatter parsing that can be extended.

### Code References

- `plugins/python3-development/skills/implementation-manager/scripts/implementation_manager.py:479-544` — `parse_task_content()` and `_parse_multi_task_body()` — the functions that fail on the global-manifest format
- `plugins/python3-development/skills/implementation-manager/scripts/implementation_manager.py:504-508` — multi-task detection logic that misses the `tasks:` list variant
- `plugins/python3-development/skills/implementation-manager/scripts/task_format.py:132-171` — `parse_yaml_frontmatter()` — shared frontmatter parser
- `plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py:245-296` — `find_task_section()` — regex-based section finder (independent parser)
- `plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py:334-361` — `update_task_status()` — regex-based status updater (independent parser)
- `.claude/docs/TASK_FILE_FORMAT.md:370-481` — JSON Schema definition for task fields
- `plan/tasks-1-backlog-state-reconciliation.md:1-19` — the file that triggered the failure (global-manifest + prose body format)

---

## Use Scenarios

### Scenario 1: Agent Reads Its Task Assignment

**Actor**: A sub-agent launched by `/start-task` to implement a specific task
**Trigger**: The implement-feature orchestrator dispatches the agent with a plan ID and task ID
**Goal**: Retrieve the task's full specification — objective, requirements, acceptance criteria, constraints, dependencies, agent assignment
**Expected Outcome**: `sam read P1/T3` returns a structured representation of task T3 from plan P1, including all typed metadata fields and the markdown content fields. The agent has everything needed to begin work without parsing the file itself.

### Scenario 2: Hook Updates Task State

**Actor**: `task_status_hook.py` responding to a `SubagentStop` or `PostToolUse` event
**Trigger**: Claude Code fires a hook event during or after task execution
**Goal**: Atomically update a task's status and timestamp fields without corrupting the file
**Expected Outcome**: `sam state P1/T3 complete` (or the equivalent MCP call) updates the status to `complete` and sets the `completed` timestamp. The YAML file is modified cleanly regardless of whether the plan is a single file or a directory of per-task files.

### Scenario 3: Orchestrator Queries Ready Tasks

**Actor**: The implement-feature skill's execution loop
**Trigger**: After each task completes, the orchestrator needs to find the next dispatchable tasks
**Goal**: Get a list of tasks that are `not-started` with all dependencies `complete`
**Expected Outcome**: `sam ready P1` returns a list of task IDs and their metadata. This works correctly for all format variants, including the global-manifest format that currently returns zero tasks.

### Scenario 4: Legacy File Ingestion with Gap Report

**Actor**: A developer or migration script processing an older task file
**Trigger**: A task file uses the legacy `## Task N:` markdown format or the YAML-frontmatter-in-markdown format
**Goal**: Read the file successfully and understand what schema fields are missing
**Expected Outcome**: The reader parses the legacy file, normalizes it to the canonical model, and returns both the parsed tasks and a gap report listing which optional fields (e.g., `skills`, `complexity`, `agent`) are absent from each task. No parse failure, no silent data loss.

### Scenario 5: Plan Status Overview

**Actor**: A human developer checking on feature progress
**Trigger**: Wanting to know how many tasks are complete, in-progress, blocked, or not-started for a feature
**Goal**: Get a summary view of plan progress
**Expected Outcome**: `sam status P1` returns counts by status, lists blocked tasks with reasons, and shows overall completion percentage. Same data the current `implementation_manager.py status` command provides, but working for all format variants.

---

## Gap Analysis

### Identified Gaps

| # | Category | Gap Description | Impact |
|---|----------|-----------------|--------|
| 1 | Scope | Three known task file format variants exist: (a) per-task YAML frontmatter, (b) global-manifest + embedded per-task YAML blocks, (c) global-manifest + prose markdown body (the broken one). Are there other variants in the 60+ plan files? | Unknown formats would still fail silently |
| 2 | Scope | The `sam` CLI addressing scheme uses `P{N}/T{N}`. How are plans identified — by sequential number, slug, or file path? Current system uses slugs (e.g., `backlog-state-reconciliation`). | CLI UX depends on addressing clarity |
| 3 | Behavior | When the writer produces pure YAML, what happens to the markdown body sections (Context, Objective, Requirements, etc.) in existing task files? They become YAML multiline string fields. Does the writer convert existing files in-place or only write new files in the canonical format? | Determines migration scope |
| 4 | Behavior | Schema gap detection reports missing fields. What action follows — log only, return structured data, write a report file? | Affects consumer integration |
| 5 | Integration | The `single interface principle` means all five existing scripts must be migrated to import from the new module. What is the migration strategy — simultaneous cutover or incremental? | Affects task decomposition and risk |
| 6 | Integration | `task_status_hook.py` currently uses regex-based line scanning to update fields because re-serializing YAML would lose comments and formatting. The new module writes pure YAML, so re-serialization is acceptable. But during the transition period, hooks may need to handle both old and new format files. | Hook must handle mixed states |
| 7 | Scope | The user specifies "single file under 500 lines; split into directory above 500 lines." Does the module auto-split on write, or is splitting a separate explicit operation? | Affects write API complexity |
| 8 | User | MCP server equivalent — is this a new MCP server or extension of the existing backlog MCP server? | Affects deployment topology |

---

## Questions Requiring Resolution

### Q1: Plan addressing scheme

- **Category**: User
- **Gap**: The CLI uses `P{N}/T{N}` notation (e.g., `sam read P1/T3`). How is `P1` resolved to a specific plan file?
- **Question**: Does `P1` mean the first plan file alphabetically, a plan with sequence number 1, the plan with slug matching a pattern, or something else? Current task files use naming like `tasks-1-backlog-state-reconciliation.md` where `1` is a sequence number — is `P1` this sequence number?
- **Options**:
  - A) `P1` = sequence number from filename (`tasks-1-*.md` or `tasks-1-*/`)
  - B) `P1` = slug-based lookup (`sam read backlog-state-reconciliation/T3`)
  - C) Both supported (numeric shorthand + slug)
- **Why It Matters**: Determines the lookup/discovery logic and whether plans need a registry
- **Resolution**: _pending_

### Q2: Legacy file conversion on read vs write

- **Category**: Behavior
- **Gap**: When a legacy file is read through the module, is it just parsed and returned in-memory, or is it also converted to the canonical YAML format on disk?
- **Question**: Should reading a legacy file through the module also rewrite it to pure YAML, or is conversion a separate explicit operation (e.g., `sam migrate P1`)?
- **Options**:
  - A) Read-only normalization — legacy files are parsed but not modified
  - B) Auto-convert on first read — legacy files are rewritten to canonical YAML
  - C) Explicit migration command — user runs `sam migrate` to convert
- **Why It Matters**: Auto-conversion could break existing references and git history. Read-only means legacy files persist indefinitely.
- **Resolution**: _pending_

### Q3: Auto-split behavior on write

- **Category**: Behavior
- **Gap**: The spec says single file under 500 lines, directory above 500 lines. Is this enforced automatically on every write?
- **Question**: When `sam state P1/T3 complete` is called and the result pushes the file over 500 lines, does the module automatically split the file into a directory? Or is splitting a manual/explicit operation?
- **Options**:
  - A) Auto-split on write when crossing threshold
  - B) Split is a separate explicit command
  - C) Writer always uses the current storage format (single/directory) and never auto-converts
- **Why It Matters**: Auto-split during a state update could surprise consumers and break file references mid-workflow
- **Resolution**: _pending_

### Q4: MCP server deployment

- **Category**: Integration
- **Gap**: MCP server equivalent is specified but deployment topology is unspecified
- **Question**: Is this a new standalone MCP server (e.g., `sam-server`), or should these tools be added to the existing backlog MCP server (`backlog_core/server.py`)?
- **Options**:
  - A) New standalone MCP server — `sam_server.py`
  - B) Extension of existing backlog MCP server
  - C) Both — shared module, exposed through both servers
- **Why It Matters**: Affects configuration, deployment, and whether users need to add a new MCP server to their config
- **Resolution**: _pending_

### Q5: File extension for canonical format

- **Category**: Scope
- **Gap**: The user specifies "pure YAML" format. Current task files use `.md` extension.
- **Question**: Should canonical YAML task files use `.yaml` extension (matching their content type) or keep `.md` for backward compatibility with tooling that expects markdown?
- **Options**:
  - A) `.yaml` extension for new canonical files
  - B) Keep `.md` extension even for pure YAML content
  - C) `.yaml` for new files, `.md` tolerated for legacy
- **Why It Matters**: File extension affects editor tooling (syntax highlighting, linting), glob patterns in existing scripts, and directory discovery logic
- **Resolution**: _pending_

### Q6: Scope of "all consumers go through this module"

- **Category**: Integration
- **Gap**: Five scripts currently parse task files independently. The backlog MCP server also queries task status via `backlog_get_ready_sam_tasks`. Are there other consumers?
- **Question**: Beyond the five identified scripts (implementation_manager.py, task_format.py, task_status_hook.py, split_task_file.py, migrate_task_format.py) and the backlog MCP server, are there other components that read or write task files? Should the `swarm-task-planner` agent also write through the module's API, or does it produce raw YAML that the module can read?
- **Why It Matters**: Missing a consumer means that consumer continues parsing ad-hoc, defeating the single-interface goal
- **Resolution**: _pending_

---

## Goals (Pending Resolution)

_These goals will be finalized after questions are resolved._

1. Define canonical task/plan schema as Pydantic models with all fields from TASK_FILE_FORMAT.md, where structural fields are typed YAML and rich text content is markdown in YAML multiline scalars
2. Implement readers for three known format variants: (a) per-task YAML frontmatter, (b) global-manifest + embedded per-task YAML blocks, (c) global-manifest + tasks-list + prose body
3. Implement backward-compatible readers for legacy markdown format (`## Task N:` headings with `**Field**: Value` markers)
4. Implement writer that produces pure YAML in canonical format
5. Implement schema gap detection that reports missing optional fields when reading legacy formats
6. Implement CLI interface with `sam read`, `sam state`, `sam ready`, `sam status` commands
7. Implement MCP server interface with equivalent operations
8. Migrate all existing consumers to import from the shared module
9. Support both single-file and directory-based task organization with appropriate threshold behavior

---

## Next Steps

After questions are resolved:

1. Update "Resolution" fields in Questions section
2. Finalize Goals section
3. Proceed to RT-ICA assessment
4. Then proceed to architecture design

---

## Post-Implementation Annotations

_Added by context-refinement agent on 2026-03-15_

### Design Refinements

1. **Shared YAML utility module**: The implementation introduced `readers/_yaml_utils.py` as a shared factory for ruamel.yaml instances. The feature context anticipated each reader importing `ruamel.yaml` independently. The shared module centralizes `YAML(typ="rt", preserve_quotes=True)` configuration and `CommentedMap` coercion. This does not change the external contract — callers still use the same reader API.
   - Original: Each reader creates its own YAML instance
   - Actual: All readers import `make_yaml()` from `readers/_yaml_utils.py`
   - Recorded in: plan/tasks-2-unified-sam-task-schema.md, Context Manifest

2. **Stdlib exceptions instead of custom exception classes**: The feature context implied custom exception types (`TaskNotFoundError`, `ClaimError`) for the query layer. The implementation uses `KeyError` for not-found tasks and `ValueError` for state violations. `AddressingError` was created in `core/addressing.py`.
   - Original: Custom exception classes expected in the query layer
   - Actual: `KeyError` (not found) and `ValueError` (invalid state) raised directly; `AddressingError` defined in `core/addressing.py`
   - Recorded in: plan/tasks-2-unified-sam-task-schema.md, Context Manifest

3. **`update_fields()` bulk API**: The writer gained a `update_fields(file_path, task_id, fields: dict)` function alongside `update_field()`. The query layer uses the plural form for atomic multi-field updates.
   - Original: Only `update_field()` (singular) described
   - Actual: Both `update_field` and `update_fields` implemented; query layer imports `update_fields`
   - Recorded in: plan/tasks-2-unified-sam-task-schema.md, Context Manifest

4. **Sync MCP tool handlers**: FastMCP 3.0.2 accepts synchronous tool handlers. All MCP tools use `def` instead of `async def`.
   - Original: "MCP tools are async signatures (required by FastMCP)"
   - Actual: Synchronous `def` handlers — avoids ruff RUF029 lint error
   - Recorded in: plan/tasks-2-unified-sam-task-schema.md, DN-1
