# Plugin maintenance

## Future improvements

- `SubagentStop` hook enforcing the STATUS-first contract.
  - What: a `SubagentStop` hook (Claude Code mechanic) that fails the stop if the sub-agent's
    final message does not begin with `STATUS: DONE|PARTIAL|BLOCKED`.
  - Why deferred: no such hook exists in this plugin yet; `references/sub-agent-contract.md`
    states the requirement but nothing enforces it mechanically.
  - Depends on: harness support for the `SubagentStop` event (see
    `skills/delegate/references/harness-notes/claude-code.md` for Claude Code's dispatch
    mechanics) and, if adopted, likely lives alongside `orchestrator-discipline`'s hooks rather
    than in this plugin.
