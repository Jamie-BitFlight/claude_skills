# Improvement Proposals: OmnySSH

**Research entry**: ./research/developer-tools/omnyssh.md
**Generated**: 2026-10-02
**Patterns assessed**: 5
**Backlog items created**: 0
**Deferred (low confidence)**: 0
**Skipped (already covered or tracked)**: 5

---

No actionable improvement proposals. Every pattern in the entry's "Relevance to Claude Code
Development" section was assessed against the local file it maps to; none produced a concrete,
observable before/after gap. Reasons per pattern are in the Skipped Patterns table below.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| (none) | — | — |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| PTY multiplexing and session management (Applications -> `AGENTS.md`) | Already covered — `rules/interactive-terminal-workarounds.md` (lines 7-20) documents tmux as the current PTY provider for Claude Code. OmnySSH's vt100 screen model is a Rust library inside a GUI/TUI SSH client, not a callable tool for agent orchestration. |
| Real-time metrics and monitoring (Applications -> `rules/ci-workflows.md`, line 116) | Out-of-scope. The rule is about CI job sequencing (continue-on-error acceptability), not pipeline metrics architecture. Development-harness has no live metrics collection surface that OmnySSH's patterns could extend. |
| Event system architecture (Applications -> `plugins/plugin-creator/skills/hook-creator/SKILL.md`, lines 10+) | Out-of-scope — Claude Code's hook events are defined by the harness, not in this repository. No local event bus exists for OmnySSH's `CoreEvent` pattern to extend. |
| Workspace-based multi-frontend architecture (Patterns Worth Adopting -> `ARCHITECTURE.md`) | The research entry itself records "Change: out-of-scope". Claude_skills already uses directory-based workspace architecture; the library/frontends pattern OmnySSH demonstrates (core engine depended on by UI implementations) is not a direct parallel to plugin composition. |
| SSH configuration parsing and host discovery (Integration Opportunities) | No current consumer. Absence is confirmed: `git grep -il "ssh config\|ssh_config\|ProxyJump" -- plugins/ .claude/skills/ .claude/agents/ rules/ docs/ AGENTS.md` returns 0 matches. The entry makes the integration conditional ("If development-harness ever needs to discover and connect to remote CI/build infrastructure"). No local workflow needs this today, so there is no failure or reliability gap to close. The parser is also a Rust crate, which would need a Python binding or rewrite under `rules/language-conventions.md`. |
