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
| PTY multiplexing and session management (Applications -> `AGENTS.md`, vt100 screen parsing, multi-session management) | Already covered. `rules/interactive-terminal-workarounds.md` (lines 7-20) prescribes tmux as the PTY provider: `tmux new-session -d -s <name>` creates named concurrent sessions and `tmux capture-pane -p` returns the rendered screen, which is the same screen-model capability the vt100 parser gives OmnySSH. OmnySSH's vt100 engine is a Rust library inside a GUI/TUI SSH client, not a tool an agent can call in place of tmux, so there is no target state that extends the rule file. |
| Real-time metrics and monitoring (Applications -> `rules/ci-workflows.md`) | Too abstract. The quoted line (`rules/ci-workflows.md` line 116) is a branch in the CI step review flowchart, deciding whether `continue-on-error: true` is acceptable on post-processing jobs. It is not a metrics or observability system. The entry's proposed change ("could inform how CI workflow observability ... is structured") names no mechanism and no observable target state. |
| Event system architecture (Applications -> `plugins/plugin-creator/skills/hook-creator/SKILL.md`) | Too abstract and incompatible. The entry says the `CoreEvent` enum over an `mpsc` channel "could inform cross-session event broadcast". Claude Code's hook events are defined by the harness, not by this repo; `hook-creator/SKILL.md` (line 10 onward) documents how to consume them. The repo has no in-process event bus to extend with this pattern, and the entry names no concrete gap. |
| Workspace-based multi-frontend architecture (Patterns Worth Adopting -> `AGENTS.md`) | The research entry itself records "Change: none". It describes a possible future multi-frontend agent system with no current local target. |
| SSH configuration parsing and host discovery (Integration Opportunities) | No current consumer. Absence is confirmed: `git grep -il "ssh config\|ssh_config\|ProxyJump" -- plugins/ .claude/skills/ .claude/agents/ rules/ docs/ AGENTS.md` returns 0 matches. The entry makes the integration conditional ("If development-harness ever needs to discover and connect to remote CI/build infrastructure"). No local workflow needs this today, so there is no failure or reliability gap to close. The parser is also a Rust crate, which would need a Python binding or rewrite under `rules/language-conventions.md`. |
