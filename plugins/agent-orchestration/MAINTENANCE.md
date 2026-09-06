# Plugin maintenance

## Design decisions

- **Intentional content duplication for self-containment.** This plugin cannot link outside its
  own directory (see `tests/test_plugin_self_containment.py`, which fails the build on any
  cross-boundary path or link), so three files restate content that also lives in this repo's
  `rules/` directory instead of pointing at it:
  - `skills/delegate/references/harness-notes/claude-code.md`'s Isolation section restates
    worktree mechanics also covered by `rules/commit-cadence-and-worktrees.md`.
  - `skills/delegate/references/fix-cycle.md` restates the reproduce-first cycle from
    `rules/fix-delegation-discipline.md`.
  - `skills/delegate/references/sub-agent-contract.md` and `skills/delegate/SKILL.md` restate the
    `.tmp/scratch/reports/<date>-<slug>.md` convention that `rules/scratch-directory.md` also
    documents.

  This is by design, not an oversight — do not "fix" it by adding a link or bare mention of
  `rules/` into any plugin runtime file, and do not collapse these into a single shared reference
  without first relaxing the self-containment test.

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
