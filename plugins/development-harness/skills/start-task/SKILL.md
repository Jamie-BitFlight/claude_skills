---
name: start-task
description: Use when an agent needs to pick up a specific SAM task, set it in progress, implement its acceptance criteria, and signal completion. Activates when executing tasks from a SAM task file — updates status to IN PROGRESS with a Started timestamp, writes active-task context for hooks, and supports --complete to mark tasks done. Triggers on task execution within the implement-feature loop.
argument-hint: <task-file-path> [--task <task-id>] [--complete <task-id>]
user-invocable: true
hooks:
  PostToolUse:
  - matcher: Write|Edit|Bash
    hooks:
    - type: command
      command: python3 "${CLAUDE_SKILL_DIR}/../../implementation-manager/scripts/task_status_hook.py"
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

1. Run `mcp__plugin_dh_sam__sam_state(plan="P{N}", task="T{M}", status="complete")` to mark the task complete.
2. Output: `Task {ID} marked as complete`

---

## Starting a Task

1. Read the task assignment via the SAM MCP tool:

   ```text
   mcp__plugin_dh_sam__sam_read(plan="P{N}", task="T{M}")
   ```

   The response is a `TaskAssignment` JSON object containing:
   - `plan.goal` — the overall feature goal
   - `plan.context` — plan-level context manifest (architecture decisions, codebase notes)
   - `task` — full task details: title, requirements, constraints, acceptance criteria, verification steps
   - `task.skills` — skill names to load before implementing

   Use the address form `P{N}/T{M}` where `N` is the plan number and `M` is the task number from the `--task` argument.

1a. **Discover plan artifacts via manifest** (when issue number is known):

   If the `TaskAssignment` JSON contains a `parent_issue_number` or the plan has an `issue` field, query the artifact manifest to discover available plan artifacts:

   ```text
   mcp__plugin_dh_backlog__artifact_list(issue_number=N)
   ```

   If the response contains artifacts (non-empty `artifacts` list), use `artifact_read` to fetch the architect spec and feature context content:

   ```text
   mcp__plugin_dh_backlog__artifact_read(issue_number=N, artifact_type="architect")
   mcp__plugin_dh_backlog__artifact_read(issue_number=N, artifact_type="feature-context")
   ```

   Use the returned content as context for implementation instead of reading filesystem paths directly. This is especially important for worktree-isolated agents that cannot access uncommitted plan files from the root worktree.

   **Fallback**: If `artifact_list` returns an empty manifest (no `artifacts` entries) or an error, fall back to filesystem path conventions (`dh_paths.plan_dir() / "architect-{slug}.md"` and `dh_paths.plan_dir() / "feature-context-{slug}.md"`). This ensures backward compatibility with issues that predate the artifact manifest system.

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

   Use `sam_claim` MCP tool. This is the ONLY permitted way to mark a task in-progress.
   Do NOT edit status or started fields directly with the Edit tool.

   ```text
   mcp__plugin_dh_sam__sam_claim(plan="P{N}", task="T{M}")
   ```

   If the response contains `"claimed": false`:

   - The task was already claimed by another agent, or is complete, or could not be found.
   - Output the full JSON result for the orchestrator.
   - STOP. Do not proceed with implementation. Do not write the context file.
   - The orchestrator's hook will detect the stop and the task remains in its current state.

   If the response contains `"claimed": true`:

   - The task is claimed. `status: in-progress` and `started:` are written on disk.
   - Proceed to step 4 (write context file) and step 5 (implement).

4. Write the active-task context file (required for hook-driven updates). The context directory is resolved via `dh_paths.context_dir(session_id)`:

```bash
# Python (preferred — uses dh_paths):
import json
from dh_paths import context_dir
ctx = context_dir(session_id="${CLAUDE_SESSION_ID}")
ctx.mkdir(parents=True, exist_ok=True)
(ctx / f"active-task-${CLAUDE_SESSION_ID}.json").write_text(
    json.dumps({"task_file_path": "{task_file_path}", "task_id": "{task_id}", "parent_issue_number": N})
)

# Shell fallback (when Python not available):
mkdir -p "$(python3 -c 'from dh_paths import context_dir; print(context_dir("${CLAUDE_SESSION_ID}"))')"
printf '%s' '{"task_file_path": "{task_file_path}", "task_id": "{task_id}", "parent_issue_number": N}' \
    > "$(python3 -c 'from dh_paths import context_dir; print(context_dir("${CLAUDE_SESSION_ID}") / "active-task-${CLAUDE_SESSION_ID}.json")')"
```

Omit `parent_issue_number` if the story issue number is not known. The hook treats absence as
`None` and skips GitHub sync.

If `parent_issue_number` is known and `github_issue` field is set in the task YAML, call
`backlog_core.gh_client.update_task_status(repo, github_issue, "in-progress")` after the
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

- **Plan artifact**: `artifact_read(issue_number={N}, artifact_type="architect")`, section "{section name}"
- **Plan claim**: "{quoted text from plan artifact}"
- **Actual implementation**: "{what was actually done and why}"
- **Classification**: design-refinement | intent-divergence
- **Recorded**: {ISO timestamp}
````

   After appending a note, update `divergence-notes: {count}` in YAML frontmatter
   (or add `**Divergence Notes**: {count}` in legacy format).

   For full artifact classification rules and divergence thresholds, see
   [plan-artifact-lifecycle.md](../../docs/plan-artifact-lifecycle.md).

6. **Commit message restriction — Fixes #N trailers are PROHIBITED in task-level commits.**

   Task-level commits must NEVER include `Fixes #N`, `Closes #N`, or `Resolves #N` trailers.
   These trailers trigger automatic GitHub issue closure. Issue closure is handled exclusively
   by `/complete-implementation` in its final commit step, after all quality gates pass.
   Including these trailers in task commits causes premature issue closure before verification
   is complete.

7. Implement against the task acceptance criteria and run its verification steps.
