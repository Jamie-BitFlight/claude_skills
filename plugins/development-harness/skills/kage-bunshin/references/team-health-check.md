# Team Health Check

Inspect a named Claude Code team's live state: the last JSONL tool calls per member and the current tmux pane snapshot.

Use this only for teammates created in an interactive lead session while `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` is enabled. Under those conditions, an Agent call with a `name` creates a teammate unless the call is a fork or requests isolation. Unnamed Agent calls, forked calls, isolated calls, and calls in non-interactive `-p` sessions remain ordinary subagents. SOURCE: [Orchestrate teams of Claude Code sessions](https://code.claude.com/docs/en/agent-teams) (accessed 2026-09-06).

Run `${CLAUDE_SKILL_DIR}/scripts/monitor.py health`:

```bash
# Most recently modified team
uv run "${CLAUDE_SKILL_DIR}/scripts/monitor.py" health

# Specific team by name
uv run "${CLAUDE_SKILL_DIR}/scripts/monitor.py" health {team-name}
```

## Team name discovery

Team names come from `~/.claude/teams/`; each subdirectory is a team. The script defaults to the most recently modified team by `config.json` mtime. Pass an explicit name to target a specific team.

## Output per member

For each team member the script prints:

- **name** and **agentType** from the team config
- **Last 5 JSONL tool calls**: timestamp, tool name, and first 60 characters of input, drawn from the member's session file
- **tmux pane snapshot**: full visible content of the member's assigned tmux pane

## Session file lookup

JSONL session files are searched under `~/.claude/projects/{project-slug}/`, derived from the current git repository root. For each member, the script reads the first 3 KB of each candidate `.jsonl` file and picks the one where the member's `name` or `agentId` (`{name}@{team-name}`) appears earliest. The team-lead session is resolved directly from `leadSessionId` in the team config.

## When to use

Call `monitor.py health` after dispatching teammates to verify they are progressing. Unlike the poll-based monitor, this subcommand exits immediately after printing; it is a snapshot tool, not a watcher.

For other skills that reference this capability, load `/dh:kage-bunshin` and invoke `monitor.py health {team-name}`.
