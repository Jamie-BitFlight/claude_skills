# spawn-tasks

Spawn parallel Claude Code sessions from confirmed subtasks. Each session gets its own isolated git worktree and tmux pane with full task context.

## Skills

| Skill | Description |
|-------|-------------|
| `/spawn-tasks` | Write task files and spawn one Claude Code session per subtask |

## Usage

1. In a Claude Code session, plan and confirm your subtasks
2. Run `/spawn-tasks`
3. Claude shows the task list and asks for confirmation
4. Sessions open as new tmux panes (falls back to Terminal.app on macOS)

## Smart Spawning

If tasks have sequential dependencies, Claude recommends running them in order instead of parallelizing blindly.

## Source

[github.com/theradengai/spawn-tasks](https://github.com/theradengai/spawn-tasks)
