---
title: "Improvement Proposals: MemPalace"
---

## Improvement 1: PreCompact hook for emergency context preservation

**Source pattern**: "PreCompact Hook — fires before context compression; emergency save before window shrinks" (Section 7: Auto-Save Hooks for Claude Code, lines 186-191)
**Local system**: `.claude/hooks/` (project hooks directory)
**Confidence**: High
**Impact**: High
**Backlog**: #1677 created

### Current state

The `.claude/hooks/` directory contains three hooks: `run-commands-try-all.cjs` (command execution), `validate-delegation.cjs` (delegation validation), `stop-backlog-reminder.cjs` (backlog reminders). None of these hooks fires on context compression events. When a Claude Code session approaches context window limits and compresses history, accumulated decisions, debugging insights, and architectural context from the current session are silently lost. The `start-task/SKILL.md` PostToolUse hook (`task_status_hook.py`) tracks task activity timestamps but does not preserve session knowledge.

### Target state

A PreCompact hook (`.claude/hooks/pre-compact-save.cjs`) fires before context window compression. The hook extracts and persists to a durable location (e.g., `.tmp/scratch/session-context/` or a configured MCP endpoint) the following from the current session: key decisions made, files modified, errors encountered and resolved, and any active task context. The saved context is retrievable by subsequent sessions or post-compression continuation.

### Measurable signal

File `.claude/hooks/pre-compact-save.cjs` exists and is registered in hooks configuration. After a context compression event, a file exists at the configured output path containing structured session knowledge from before compression. The hook appears in `hooks.json` or `settings.json` with the appropriate event matcher.

---

## Improvement 2: Periodic session knowledge auto-save hook

**Source pattern**: "Save Hook — fires every 15 messages; triggers structured save of topics, decisions, quotes, code changes; regenerates L1 critical facts" (Section 7: Auto-Save Hooks for Claude Code, lines 186-187)
**Local system**: `.claude/hooks/` (project hooks directory), `plugins/development-harness/skills/start-task/SKILL.md`
**Confidence**: High
**Impact**: Medium
**Backlog**: #1678 created

### Current state

The `start-task/SKILL.md` PostToolUse hook writes a `LastActivity` timestamp on every Write/Edit/Bash tool call via `task_status_hook.py`. This tracks when work last happened but does not capture what was decided or discovered. No hook fires periodically (e.g., every N tool calls or messages) to save accumulated session knowledge — topics discussed, decisions locked in, code changes made, errors resolved. If a session crashes, is interrupted, or exhausts credits, accumulated knowledge beyond what was committed to files is lost.

### Target state

A PostToolUse hook (or a wrapper around the existing `task_status_hook.py`) fires every N tool calls (configurable, default 15) and appends a structured knowledge snapshot to a session log file. The snapshot includes: active task ID (if any), files modified since last snapshot, decisions or conclusions stated in recent assistant messages (extracted from tool call context), and current working hypothesis. The output file is at a predictable path (e.g., `~/.dh/projects/{slug}/session-logs/{session-id}.jsonl`).

### Measurable signal

After 15+ tool calls in a session, a file exists at `~/.dh/projects/{slug}/session-logs/` containing structured JSONL entries with timestamps, file lists, and extracted decisions. A new session can read this file to understand what the previous session was working on and what it decided.

---

## Improvement 3: Agent diary pattern for specialist knowledge persistence

**Source pattern**: "Agents use mempalace_diary_write to record patterns they notice (e.g., reviewer remembers bug patterns)" and "Cross-agent learning: one agent reads another's diary via mempalace_diary_read" (Section 2: Multi-Agent Coordination, lines 336-340)
**Local system**: `.claude/skills/swarm-operations/SKILL.md`, `.claude/skills/swarm-patterns/SKILL.md`
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred — confidence medium: The swarm system uses stateless agents by design (SAM methodology). Whether adding persistent per-agent memory would improve outcomes or conflict with the stateless handoff model requires analysis of actual session transcripts showing knowledge loss between agent invocations. The kaizen analysis pipeline could provide this evidence but has not been run for this specific pattern.

### Current state

Swarm agents (`swarm-operations/SKILL.md`) are stateless — each agent invocation starts fresh with only the prompt and any passed file paths. When `@dh:code-reviewer` notices a recurring bug pattern across multiple reviews, that knowledge dies with the agent session. The next invocation of the same reviewer agent has no access to patterns discovered in previous sessions. No diary/journal mechanism exists in the swarm tools (TeamCreate, SendMessage, TaskCreate, Agent).

### Target state

Specialist agents (code-reviewer, codebase-analyzer, feature-verifier) can append observations to a persistent diary file and read prior entries on startup. Diary entries are structured (timestamp, agent name, observation type, content). A new agent session loads its diary as part of initialization, gaining access to patterns and insights from previous invocations.

### Measurable signal

A diary file exists at a predictable path per agent name. After a code-reviewer session that identifies a recurring pattern, the diary file contains an entry describing that pattern. A subsequent code-reviewer session's prompt or initialization step references the diary content.

---

## Improvement 4: Structured wake-up context layer

**Source pattern**: "wake-up context loads only ~170 tokens of critical facts (identity, team, projects, preferences) and queries fire on demand" (Section on Problem Addressed, line 30-31) and "L0 (identity) + L1 (critical facts) are generated, optionally compressed to AAAK, and injected into system prompt" (Section on Data Flow, line 231)
**Local system**: `.claude/CLAUDE.md`, `.claude/rules/`
**Confidence**: Low
**Impact**: Low
**Backlog**: Deferred — confidence low: CLAUDE.md already serves as the wake-up context layer, loading project identity, constraints, and behavioral rules on every session start. The research entry's pattern is about loading from a semantic database of past conversations, while the local system loads from authored instruction files. Whether the local system would benefit from a dynamic facts layer generated from past sessions (vs. the current manually-authored CLAUDE.md) is unclear without measuring what knowledge is actually lost between sessions. The local system may already have equivalent coverage via CLAUDE.md + rules/ + MEMORY.md.

### Current state

CLAUDE.md loads on every session with project identity, constraints, tool usage rules, and behavioral standards. `.claude/rules/` loads context-specific rules. MEMORY.md persists key learnings across sessions. These are manually authored and maintained. There is no automatic extraction of "critical facts" from past session transcripts — the wake-up context is what was explicitly written, not what was discovered.

### Target state

A lightweight facts layer (separate from CLAUDE.md) is auto-generated from session logs, containing: active project priorities, recent decisions, unresolved issues, and team member assignments. This layer loads alongside CLAUDE.md but is machine-generated rather than hand-authored.

### Measurable signal

A file at a predictable path contains auto-generated facts with timestamps. The file is updated after each session. Content differs from CLAUDE.md in that it reflects discovered knowledge, not authored instructions.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Agent diary pattern for specialist knowledge persistence | Medium | Stateless agent design is intentional (SAM methodology). Need kaizen transcript analysis showing knowledge loss between agent invocations to confirm this is a real problem, not a theoretical gap. |
| Structured wake-up context layer | Low | CLAUDE.md + rules/ + MEMORY.md may already provide equivalent coverage. No measurement of what session knowledge is actually lost. The local system's authored-instruction model may be superior to auto-extracted facts for this repo's use case. |
| Structured memory hierarchy (wings/rooms/halls) for multi-agent systems | Low | MemPalace's palace structure is a retrieval optimization for its specific ChromaDB backend. The local system organizes knowledge via file paths and skill/agent namespaces, which may be equivalent. No evidence that retrieval quality is a bottleneck in the local system. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Benchmark validation (96.6% LongMemEval) | Informational — validates MemPalace's architecture, not a pattern to adopt in local systems |
| Local-first privacy | Philosophical alignment — the local system already runs entirely on-machine with no external API calls required for core operations |
| Known limitations (AAAK regression, ChromaDB pinning, etc.) | Caveats about MemPalace itself, not patterns for local improvement |
