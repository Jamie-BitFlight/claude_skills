---
name: spawn-tasks
description: Spawn parallel Claude Code sessions from planned subtasks. Each session gets its own worktree and tmux pane with full task context.
user_invocable: true
---

# Spawn Tasks — Parallel Session Launcher

## When to Use

User triggers this skill after breaking down a project into subtasks in the current conversation. This skill writes task files and spawns independent Claude Code sessions for each subtask.

## Workflow

1. **Collect tasks from conversation context**: Gather all subtasks that were discussed and confirmed with the user. Each task needs: name, goal, context, relevant files, constraints, and acceptance criteria.

2. **Write task files**: For each subtask, create a markdown file at `.tasks/spawn/{task-name}.md` in the current project directory. Create the directory if it doesn't exist.

Task file template:

```markdown
# Task: {task name}

## Goal
{what this subtask should accomplish}

## Context
{architectural background, dependencies, related modules}

## Relevant Files
{list of key file paths}

## Constraints
{consensus docs to follow, technical limitations, things to avoid}

## Acceptance Criteria
{how to verify the task is complete}
```

3. **Spawn sessions**: For each task file, run the following Bash command:

```bash
claude -w "{task-name}" --tmux "$(cat .tasks/spawn/{task-name}.md)"
```

This command:
- `-w "{task-name}"`: Creates an isolated git worktree named after the task
- `--tmux`: Opens in a new tmux pane (uses iTerm2 native panes when available)
- The task file content is passed as the initial prompt

4. **Report**: After all sessions are spawned, tell the user:
   - How many sessions were created
   - The tmux session name so they can attach (`tmux attach` or check iTerm2 panes)
   - How to switch between panes (Ctrl+B then number, or iTerm2 Cmd+[ ])
   - Remind them that each session has its own worktree, so changes don't conflict

## Important Notes

- **Always confirm with the user** before spawning. Show the task list and ask for approval.
- If tmux is not installed, fall back to opening Terminal.app windows via osascript:
  ```bash
  osascript -e "tell application \"Terminal\" to do script \"cd '$(pwd)' && claude -w '{task-name}' \\\"$(cat .tasks/spawn/{task-name}.md)\\\"\""
  ```
- Task files are kept in `.tasks/spawn/` for reference. They are NOT deleted after spawning.
- The task file content should be self-contained — the spawned session has NO access to the main conversation's context.
- Include references to project docs (like `docs/final-consensus/`) in the task context so the spawned session knows to check them.
