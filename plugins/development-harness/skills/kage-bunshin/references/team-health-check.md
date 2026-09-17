# Team Health Check

Inspect a named Claude Code team's live state: recent JSONL actions per member and the current tmux pane snapshot.

Use this only for teammates created in an interactive lead session while `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` is enabled. Under those conditions, an Agent call with a `name` creates a teammate unless the call is a fork or requests isolation. Unnamed Agent calls, forked calls, isolated calls, and calls in non-interactive `-p` sessions remain ordinary subagents. SOURCE: [Orchestrate teams of Claude Code sessions](https://code.claude.com/docs/en/agent-teams) (accessed 2026-09-17).

Run `${CLAUDE_SKILL_DIR}/scripts/monitor.py health`:

```bash
# Most recently modified team
uv run "${CLAUDE_SKILL_DIR}/scripts/monitor.py" health

# Specific team by name
uv run "${CLAUDE_SKILL_DIR}/scripts/monitor.py" health {team-name}

# Restrict output to the five most recent actions per member
uv run "${CLAUDE_SKILL_DIR}/scripts/monitor.py" health {team-name} --action-limit 5
```

## Team name discovery

Team names come from `~/.claude/teams/`; each subdirectory is a team. The script defaults to the most recently modified team by `config.json` mtime. Pass an explicit name to target a specific team. SOURCE: `scripts/health.py:63-70,176-184,191-194`; verified by `tests/test_health.py::test_run_health_uses_latest_team_and_prints_member_snapshot`.

## Output per member

For each team member the script prints:

- **name** and **agentType** from the team config
- **JSONL actions**: all complete tool inputs and non-empty assistant text. Set `--action-limit` to a positive count only when a smaller most-recent window is wanted; zero prints all recorded actions.
- **tmux pane snapshot**: full visible content of the member's assigned tmux pane

SOURCE: `scripts/health.py:16-43,73-112,176-240` and `scripts/monitor.py:427-478`; verified by `tests/test_health.py`.

## Session file lookup

JSONL session files are searched under `~/.claude/projects/{project-slug}/`, derived from the current git repository root. For each member, the script searches every candidate `.jsonl` file and picks the one where the member's `name` or `agentId` (`{name}@{team-name}`) appears earliest. The team-lead session is resolved directly from `leadSessionId` in the team config. SOURCE: `scripts/health.py:46-60,115-173,203,212-225`; verified by `tests/test_health.py::test_agent_last_actions_searches_all_files_and_complete_contents`.

## When to use

Call `monitor.py health` after dispatching teammates to inspect their recorded activity. Unlike the poll-based monitor, this subcommand exits immediately after printing; it is a snapshot tool, not a watcher. SOURCE: `scripts/monitor.py:453-478`; verified by `tests/test_health.py::test_main_prints_all_actions_by_default`.

For other skills that reference this capability, load `/dh:kage-bunshin` and invoke `monitor.py health {team-name}`.
