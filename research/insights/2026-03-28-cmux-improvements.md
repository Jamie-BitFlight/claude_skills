# Improvement Proposals: cmux

**Research entry**: ./research/agent-infrastructure/cmux.md
**Generated**: 2026-03-28
**Patterns assessed**: 5
**Backlog items created**: 0
**Deferred (low confidence)**: 1
**Skipped (already covered or tracked)**: 4

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Notification hook OSC emission | Low | task_status_hook.py runs as a Claude Code hook subprocess, not in the user's terminal PTY. Whether emitting OSC 9/99/777 sequences from this context would reach a terminal like cmux is unverified. Would need to confirm that hook stdout is piped to the terminal emulator, and that cmux (macOS-only) is present. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Browser automation (scriptable WKWebView API) | Already covered by `/agent-browser` skill at `.claude/skills/agent-browser/SKILL.md` which provides equivalent functionality via Playwright-based `agent-browser` CLI with element ref snapshots, click/fill/select commands |
| Workspace organization (per-workspace metadata sidebar) | Architectural incompatibility -- cmux provides a terminal UI with visual sidebar showing git branch, PR status, working directory per workspace. This repo provides skills/agents/workflows, not terminal UIs. The equivalent organizational concern is handled by `TeamCreate` and SAM task plans. |
| Socket API integration (Unix domain socket for external process control) | Architectural incompatibility -- cmux's socket API controls terminal panes and surfaces. The local system uses Claude Code's built-in `SendMessage`/`TeamCreate` tools for inter-agent communication. Adding socket-based external orchestration would require a fundamentally different architecture. |
| Custom commands via `cmux.json` (project-specific actions from command palette) | Already covered by the skill/agent/hook system which serves the same purpose -- project-specific commands registered via SKILL.md frontmatter in `.claude/skills/` directories |
