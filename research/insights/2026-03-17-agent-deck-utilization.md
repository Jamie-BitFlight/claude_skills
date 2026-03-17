# Utilization Proposals: Agent Deck

**Research entry**: ./research/developer-tools/agent-deck.md
**Generated**: 2026-03-17
**Integration surfaces found**: 4 (CLI | Web API | Hooks | Config files)
**Proposals written**: 0
**Skipped**: 5 — architectural gap; no existing local orchestrator

---

## Skipped Systems

| Local System | Reason skipped |
|---|---|
| `.claude/skills/orchestrating-swarms/SKILL.md` | Orchestrates Claude Code teams/swarms internally via TeamCreate/SendMessage. Agent Deck targets multi-tool, multi-instance coordination (Claude Code + Gemini CLI + OpenCode + Codex). Scope mismatch — Agent Deck manages external session lifecycle; orchestrating-swarms manages internal swarm messaging. |
| `.claude/skills/session-historian/SKILL.md` | Reads and indexes past JSONL session transcripts for context recovery. Agent Deck manages live multi-session coordination, MCP pooling, conductor setup, and Docker sandboxing. No overlap — session-historian is retrospective; Agent Deck is active infrastructure. |
| `.claude/agents/context-gathering.md` | Builds context manifests for individual tasks by reading related codebase files. Agent Deck orchestrates multiple tool instances and manages MCPs/skills/conductors system-wide. Different scope — task context vs. session infrastructure. |
| `.claude/agents/research-utilization-assessor.md` | Assesses research entries for integration opportunities (this agent). Agent Deck is a session manager, not a tool that this agent calls. No self-referential integration. |
| `.claude/skills/backlog/` suite | Manages backlog items, GitHub issues, and task state. Agent Deck manages tool sessions, MCPs, conductors, and Docker sandboxes. Non-overlapping domains. |

---

## Architecture Notes

Agent Deck provides rich integration surfaces but requires an architectural component that does not yet exist in this codebase:

1. **CLI Integration**: `agent-deck add . -c claude --worktree`, `agent-deck mcp attach`, `agent-deck conductor setup` are all callable via subprocess. But no local skill or orchestration workflow currently spawns and manages multiple Claude Code instances across projects.

2. **Web API Integration**: The web UI (<http://127.0.0.1:8420>) offers WebSocket and REST endpoints for session monitoring and control. No local skill currently polls or controls external sessions via this API.

3. **Hook System**: Agent Deck installs hooks into Claude Code to detect session state changes. This mechanism is compatible with Claude Code's hook system, but would require a new conductor-like agent to read and act on hook payloads.

4. **TOML Configuration**: Agent Deck's `~/.agent-deck/config.toml` can be read and modified programmatically. No local skill currently manages multi-session or multi-profile configuration.

### Future Integration Opportunity

A new **"Multi-Session Orchestrator"** skill could:
- Spawn and manage multiple Claude Code instances via `agent-deck add` + CLI commands
- Toggle MCPs per session via `agent-deck mcp attach/detach`
- Set up conductors for monitoring via `agent-deck conductor setup`
- Poll the web API (<http://127.0.0.1:8420>) for session status
- Manage profiles and skill pools

This would be suitable for workflows like:
- Running parallel code reviews across feature branches (each in its own worktree + session)
- Coordinating multi-agent research tasks with shared MCP resources (socket pooling)
- Orchestrating CI/CD agents with remote control via Telegram/Slack integration

However, such a skill does not yet exist, and therefore no utilization proposal can be written.

---

## Confidence Assessment

**Integration surfaces are real and callable**: ✓ Confirmed
- Agent Deck installs via package manager or curl
- CLI commands are documented and testable
- Web API listens on localhost:8420 with documented endpoints
- Hook installation is explicit (`claude-hooks-cmd` in Agent Deck source code)
- TOML config is parse-able with standard tools

**No suitable local caller identified**: ✓ Confirmed
- Searched `.claude/agents/` — all are task/domain specialists, not orchestrators
- Searched `.claude/skills/` — all are feature-specific, not infrastructure-management
- Session-historian is retrospective (reads past JSONL), not active (manages live sessions)
- Orchestrating-swarms is internal (Claude Code teams), not external (multi-tool instances)

**Recommendation**: Add this research entry to the backlog as an exploratory item for future multi-session orchestration architecture. The integration surface is proven and documented; the missing piece is the orchestrator component in the local codebase.
