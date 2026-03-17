---
name: start-task
description: Start or complete a specific task inside a SAM task file. Updates task status to IN PROGRESS with Started timestamp, writes active-task context for hooks, and supports --complete to mark tasks complete. Use when an agent needs to pick up a SAM task, set it in progress, implement acceptance criteria, and signal completion.
argument-hint: <task-file-path> [--task <task-id>] [--complete <task-id>]
user-invocable: true
hooks:
  PostToolUse:
  - matcher: Write|Edit|Bash
    hooks:
    - type: command
      command: python3 "${CLAUDE_SKILL_DIR}/../../implementation-manager/scripts/task_status_hook.py"
version: 1.0.0
last_updated: '2026-02-28'
python_compatibility: 3.11+
---
# Start Task (SAM Task Execution Helper)

You are implementing a specific task from a SAM task file.

<task_input>
$ARGUMENTS
</task_input>

---

## Parse Arguments

- `task_file_path` (required): path to a `plan/tasks-*.md` file
- `--task <id>` (optional): Task ID to start (defaults to first ready task)
- `--complete <id>` (optional): Task ID to mark COMPLETE

---

## If `--complete <task-id>` Provided

1. Run `uv run sam state P{N}/T{M} complete` to mark the task complete.
2. Output: `Task {ID} marked as complete`

---

## Starting a Task

1. Read the task assignment via `sam read`:

   ```bash
   uv run sam read P{N}/T{M} --format json
   ```

   The response is a `TaskAssignment` JSON object containing:
   - `plan.goal` — the overall feature goal
   - `plan.context` — plan-level context manifest (architecture decisions, codebase notes)
   - `task` — full task details: title, requirements, constraints, acceptance criteria, verification steps
   - `task.skills` — skill names to load before implementing

   Use the address form `P{N}/T{M}` where `N` is the plan number and `M` is the task number from the `--task` argument.

2. Select the task:
   - If `--task` provided, use that ID
   - Else pick the first task where status is `not-started` and all dependencies are resolved (check `task.dependencies` in the TaskAssignment)

2a. **Load task-level skills** (if present):
   - Read `task.skills` from the `TaskAssignment` JSON (an array of skill names).
   - If absent or empty, skip (backward compatible with older task files).
   - For each skill name, invoke: `Skill(skill="{skill-name}")`
   - If a skill fails to load, log a warning and continue. Do not abort task execution.
   - **Redundancy note**: The orchestrator (`/implement-feature`) may also include skill-loading instructions in the delegation prompt. This is intentional redundancy — loading a skill twice is a no-op.
   - Task-level skills are **additive** to any skills already declared in the agent definition's frontmatter.

3. Claim the task (prevents duplicate dispatch):

   Run `sam claim`. This is the ONLY permitted way to mark a task in-progress.
   Do NOT edit status or started fields directly with the Edit tool.

   ```bash
   CLAIM_RESULT=$(uv run sam claim P{N}/T{M})
   CLAIM_EXIT=$?
   echo "$CLAIM_RESULT"
   ```

   If exit code is non-zero (`CLAIM_EXIT != 0`):

   - The task was already claimed by another agent, or is complete, or could not be found.
   - Output the full JSON result for the orchestrator.
   - STOP. Do not proceed with implementation. Do not write the context file.
   - The orchestrator's hook will detect the stop and the task remains in its current state.

   If exit code is 0 (`CLAIM_EXIT == 0`):

   - The task is claimed. `status: in-progress` and `started:` are written on disk.
   - Proceed to step 4 (write context file) and step 5 (implement).

4. Write the active-task context file (required for hook-driven updates):

```bash
mkdir -p .claude/context
printf '%s' '{"task_file_path": "{task_file_path}", "task_id": "{task_id}", "parent_issue_number": N}' > ".claude/context/active-task-${CLAUDE_SESSION_ID}.json"
```

Omit `parent_issue_number` if the story issue number is not known. The hook treats absence as
`None` and skips GitHub sync.

If `parent_issue_number` is known and `github_issue` field is set in the task YAML, call
`backlog_core.github.update_task_status(repo, github_issue, "in-progress")` after the
`claim-task` step to sync the in-progress status to GitHub. Failure is non-fatal — continue
regardless.

5. **Record divergence observations during implementation.**

   While implementing, if you discover that the architect spec or feature-context
   describes something that does not match what you are implementing, append a
   divergence note to the task file under a `## Divergence Notes` section.

   **When to record**: Record a divergence note when ALL of these hold:
   - You are implementing something that differs from what the architect spec or
     feature-context describes
   - The difference is not a trivial implementation detail (e.g., different variable
     name, different import path)
   - The difference affects the observable behavior, structure, or scope of the feature

   **Divergence note format**:

````markdown
## Divergence Notes

### DN-1: {Brief title}

- **Plan artifact**: plan/architect-{slug}.md, section "{section name}"
- **Plan claim**: "{quoted text from plan artifact}"
- **Actual implementation**: "{what was actually done and why}"
- **Classification**: design-refinement | intent-divergence
- **Recorded**: {ISO timestamp}
````

   After appending a note, update `divergence-notes: {count}` in YAML frontmatter
   (or add `**Divergence Notes**: {count}` in legacy format).

   For full artifact classification rules and divergence thresholds, see
   [.claude/docs/plan-artifact-lifecycle.md](./../../../../.claude/docs/plan-artifact-lifecycle.md).

6. Implement against the task acceptance criteria and run its verification steps.
