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
| Real-time metrics and monitoring (Applications -> `rules/ci-workflows.md`, line 116) | Out-of-scope. The verified observation is that `rules/ci-workflows.md` uses "metrics" only as an example of a post-processing CI job whose `continue-on-error: true` is acceptable; it is about CI job sequencing, not host metrics collection. No repository-wide claim about metrics surfaces is made. |
| Event system architecture (Applications -> `plugins/plugin-creator/skills/hook-creator/SKILL.md`, lines 10+) | Out-of-scope. The verified observation is that `hook-creator/SKILL.md` describes hooks that consume events defined by the Claude Code harness, whereas `CoreEvent` is an in-process Rust enum sent over a `tokio` `mpsc` channel inside OmnySSH. No repository-wide claim about event buses is made. |
| Workspace-based multi-frontend architecture (Patterns Worth Adopting -> `ARCHITECTURE.md`) | The research entry itself records "Change: out-of-scope". Claude_skills already uses directory-based workspace architecture; the library/frontends pattern OmnySSH demonstrates (core engine depended on by UI implementations) is not a direct parallel to plugin composition. |
| SSH configuration parsing and host discovery (Integration Opportunities) | No current consumer found by the searched terms. Over `:/plugins/ :/.claude/skills/ :/.claude/agents/ :/rules/ :/docs/ :/AGENTS.md`, `git grep --full-name -il` returned 0 matches for each of `"SSH config"`, `"ssh-config"` and `"ProxyJump"`; this records only that those terms found nothing, not that no SSH handling exists elsewhere in the repository. The entry makes the integration conditional ("if development-harness ever needs to discover and connect to remote CI/build infrastructure"). No local workflow needs this today, so there is no failure or reliability gap to close. The parser is also a Rust crate, which would need a Python binding or rewrite under `rules/language-conventions.md`. |
