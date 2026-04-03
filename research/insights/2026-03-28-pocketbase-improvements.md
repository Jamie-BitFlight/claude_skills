# Improvement Proposals: PocketBase

**Research entry**: ./research/data-infrastructure/pocketbase.md
**Generated**: 2026-03-28
**Patterns assessed**: 7
**Backlog items created**: 0
**Deferred (low confidence)**: 1
**Skipped (already covered or tracked)**: 6

---

## Improvement 1: SSE-based realtime push for swarm/task status monitoring

**Source pattern**: "The SSE-based realtime subscriptions enable Claude Code agents to build interactive features requiring server-pushed updates (e.g., collaborative editing, live task updates, real-time status dashboards)" (Relevance to Claude Code Development, section 3)
**Local system**: `.claude/skills/swarm-operations/SKILL.md`, `plugins/development-harness/skills/implementation-manager/scripts/task_status_hook.py`
**Confidence**: Low
**Impact**: Low
**Backlog**: Deferred -- confidence Low: the research entry describes PocketBase as a tool providing SSE, not a transferable mechanism. The local system uses hook-based file writes and MCP tool polling for status. Adding SSE would require MCP transport layer changes, which is architectural replacement, not extension.

### Current state

Task status updates are written to YAML plan files and SQLite dispatch state by `task_status_hook.py` on PostToolUse and SubagentStop events. Status consumers (orchestrators, `/dh:implement-feature`) poll via `sam_status` or `dispatch_wave_status` MCP tools. There is no push-based notification when a task status changes -- consumers must poll.

File: `plugins/development-harness/skills/implementation-manager/scripts/task_status_hook.py` (lines 1-30 describe PostToolUse and SubagentStop handlers).
File: `.claude/skills/swarm-operations/SKILL.md` (SendMessage is the only inter-agent communication, which is message-passing, not event streaming).

### Target state

A push-based notification mechanism where status changes trigger immediate notification to subscribing agents, rather than requiring polling. For example, when `task_status_hook.py` writes a status change, a subscriber (the orchestrator) receives immediate notification without calling `sam_status`.

### Measurable signal

Orchestrator agents receive status change notifications without issuing a polling `sam_status` call. Observable as: reduced `sam_status` call count in orchestrator transcripts, or presence of a push notification mechanism in the hook's output path.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| SSE-based realtime push for status monitoring | Low | Research entry describes PocketBase as a tool providing SSE, not a transferable mechanism. Local system would need MCP transport layer changes (architectural replacement, not extension). Would need proof-of-concept showing MCP SSE transport improves orchestrator latency to raise confidence. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Rapid Backend Prototyping | Use-case suggestion for PocketBase adoption, not a transferable mechanism. No concrete pattern to port to local system. |
| Testing Agent-Generated APIs | Already covered by fastmcp-creator testing patterns (`plugins/fastmcp-creator/skills/fastmcp-creator/SKILL.md`, references/testing.md) which provide in-memory client testing. |
| Hook-Based Extensibility | Already covered by local hook system. `plugins/plugin-creator/skills/hook-creator/SKILL.md` provides PreToolUse/PostToolUse/SubagentStop/SessionStart lifecycle hooks. PocketBase's model lifecycle hooks are domain-equivalent. |
| Lightweight Data Persistence | Already covered. SAM uses YAML plan files + SQLite dispatch state (`~/.dh/projects/{slug}/dispatch-state.db`). Adding a REST API layer on top is tool adoption, not a pattern gap. |
| Multi-SDK Support | Not applicable. Local system is Python-based with MCP protocol. PocketBase JS/Dart SDKs serve a different ecosystem. |
| Simple Testing Framework | Already covered by fastmcp-creator testing skill (`plugins/fastmcp-creator/skills/fastmcp-creator/SKILL.md`, testing reference). |
