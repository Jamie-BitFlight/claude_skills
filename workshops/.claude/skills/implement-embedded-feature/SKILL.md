---
name: implement-embedded-feature
description: Execute embedded firmware implementation from a task plan. Loops through tasks, delegates to appropriate agents, and tracks completion. Use after /add-embedded-feature has created a plan, or when resuming implementation work.
argument-hint: <task-file-path or feature-slug>
user-invocable: true
---
# Implement Embedded Feature

Execute tasks from a plan file created by `/add-embedded-feature`. Loops through ready tasks, delegates each to its specified agent, and tracks progress.

<feature_input>
$ARGUMENTS
</feature_input>

---

## Resolve Task File

Rules:

- If `<feature_input/>` ends with `.md`, treat it as the task file path
- Otherwise, search for `plan/tasks-*{slug}*.md`

```bash
# Find task file by slug
ls plan/tasks-*${ARGUMENTS}*.md 2>/dev/null | head -1
```

---

## Progress Loop

### Step 1: Read Task File Status

Query current plan state via sam CLI:

```bash
uv run sam status P{N}
```

Returns JSON with task counts (`completed`, `in_progress`, `not_started`) and task list with status per entry.

### Step 2: Identify Ready Tasks

A task is ready when:

- Status is `not-started`
- All tasks in `dependencies` list are `complete`

Query ready tasks via sam CLI:

```bash
uv run sam ready-tasks P{N}
```

Returns JSON: `{"feature": "...", "ready_tasks": [...], "count": N}`

### Step 3: Execute Ready Tasks

For each ready task, delegate to the specified agent:

<eg>
Agent(agent="{task.agent}", prompt="Execute this firmware implementation task:

Task: {task.title}
Description: {task.description}
Files to Modify: {task.files}

Acceptance Criteria:
{task.acceptance_criteria}

Verification Steps:
{task.verification}

Skills to use:
- /c-embedded-standards for coding patterns
- /embedded-debug-tools for flash and debug

When complete, report:
- Files modified with changes summary
- Build result (west build / make)
- Verification results

Return DONE if successful, BLOCKED if issues found.")
</eg>

### Step 4: Update Task Status

After agent completes:

- If `DONE`: Update task status to `COMPLETE`, add completion timestamp
- If `BLOCKED`: Update task status to `BLOCKED`, document blocker

### Step 5: Loop Until Complete

Repeat steps 1-4 until:

- All tasks are `COMPLETE`, OR
- No ready tasks remain (blocked or dependency cycle)

---

## Task Execution Order

Execute tasks in dependency order, respecting complexity for parallelization:

<eg>
Phase 1: Infrastructure (no dependencies)
- Header files
- Type definitions
- Configuration
[Can run in parallel if independent]

Phase 2: Implementation (depends on Phase 1)
- Core functions
- Handlers
- State machines
[Run sequentially or parallel based on dependencies]

Phase 3: Integration (depends on Phase 2)
- Wire up components
- Add to build
- Configure endpoints

Phase 4: Testing (depends on Phase 3)
- Unit tests
- Integration tests
- On-target verification
</eg>

---

## Agent Assignment

Route tasks to appropriate agents based on task type:

| Task Type              | Agent                   | Skills Loaded        |
| ---------------------- | ----------------------- | -------------------- |
| C implementation       | embedded-c-developer    | c-embedded-standards |
| Build/flash            | embedded-c-developer    | embedded-debug-tools |
| Test implementation    | embedded-test-developer | c-embedded-standards |
| Documentation          | general-purpose         | -                    |
| Architecture decisions | embedded-architect      | c-embedded-standards |

---

## Build Verification

After each implementation task, verify build:

```bash
# Zephyr/nRF Connect SDK
west build -b nrf52840dk_nrf52840

# STM32 (CMake)
cmake --build build/

# STM32CubeIDE
# Build via IDE or command line tools

# Check for warnings
west build 2>&1 | grep -i "warning:"
```

---

## Progress Reporting

After each task completion, report:

<terminal_output>
================================================================================
                    IMPLEMENTATION PROGRESS
================================================================================

Feature: {feature_name}
Task File: {task_file_path}

Progress:
- Completed: {N} / {total}
- In Progress: {N}
- Blocked: {N}
- Pending: {N}

Last Completed:
- Task {N}: {task_title}
- Files: {modified_files}
- Build: {PASS/FAIL}

Next Tasks:
1. Task {N}: {next_task_title}
2. Task {N}: {next_task_title}

Blockers (if any):
- Task {N}: {blocker_description}
================================================================================
</terminal_output>

---

## Completion Gate

When all tasks show `COMPLETE`:

1. Run final build verification
2. Run all verification steps from task file
3. Generate implementation summary

<terminal_output>
================================================================================
                    IMPLEMENTATION COMPLETE
================================================================================

Feature: {feature_name}
Total Tasks: {N}
All tasks completed successfully.

Files Modified:
- {file1}: {summary}
- {file2}: {summary}

Build Status: PASS
Flash Size: +{N} bytes
RAM Usage: +{N} bytes

Verification Results:
- [ ] Build passes
- [ ] Flash successful
- [ ] Basic functionality verified
- [ ] All acceptance criteria met

Next Steps:
1. Run full test suite
2. Review code changes
3. Commit and create PR
================================================================================
</terminal_output>

---

## Handling Blocked Tasks

When a task reports `BLOCKED`:

1. Document the blocker in task file
2. Check if other tasks can proceed
3. Report to user with options:

<eg>
Task {N} is BLOCKED: {blocker_description}

Options:
1. Resolve blocker and continue: /implement-embedded-feature {slug}
2. Skip task and proceed: /implement-embedded-feature {slug} --skip {task_id}
3. Abort implementation: Review plan and replan
</eg>

---

## Resuming Implementation

To resume after interruption:

```bash
# Resume from task file
/implement-embedded-feature plan/tasks-door-lock-feature.md

# Resume by slug
/implement-embedded-feature door-lock-feature

# Status check only
/implement-embedded-feature door-lock-feature --status
```

---

## Related Skills

- `/add-embedded-feature` - Create implementation plan
- `/c-embedded-standards` - C coding patterns
- `/embedded-debug-tools` - Flash and debug commands
