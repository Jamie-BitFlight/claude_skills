---
title: "Improvement Proposals: Trellis -- Multi-Platform AI Coding Framework"
---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Cross-Tool Workflow Consistency | Incompatible with repo architecture -- this repo is Claude Code-specific by design. Multi-platform config generation (Cursor, OpenCode, Codex, etc.) is outside scope. Trellis generates platform-specific wiring; this repo builds deep Claude Code workflows. |
| Agent Parallel Execution (git worktrees) | Already implemented. `/dh:work-milestone` dispatches parallel kage-bunshin sessions in isolated worktrees (SKILL.md line 44: `git worktree add worktrees/{slug}`). `/dh:kage-bunshin` provides spawn/send/read/status/stop lifecycle for persistent peer sessions. Backlog #974 tracks `--worktree` flag for individual items. Backlog #975 tracks TeamCreate dispatch option. |
| Task and Plan Integration (task PRDs) | Already covered and more advanced. SAM 7-stage pipeline stores task YAML in `~/.dh/projects/{slug}/plan/`, with full lifecycle management via `sam_create`, `sam_read`, `sam_claim`, `sam_state`, `sam_update` MCP tools. Task files include dependencies, acceptance criteria, agent assignments, and state machine transitions -- exceeding Trellis's PRD-only model. |
| Multi-Agent Memory and Continuity (workspace journals) | Already tracked in backlog as #317 ("Structured session work logs with pre-compact and session-start hooks"). That item describes the exact same capability: (1) pre-compact hook to snapshot work log, (2) committed log file convention, (3) session-start hook to inject prior session context. |

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Hook-Based Task Context Injection | Low | Trellis's PreToolUse hook for context injection (v0.3.6 release notes) is mentioned without specifics -- no hook signatures, execution timing, or payload format documented. The local repo has PreToolUse hooks (block-context-direct-writes.cjs) and SessionStart hooks (session-start-session-id.cjs), but neither auto-injects task context. The gap is real in principle but the Trellis source pattern is too vague to produce a concrete improvement. Backlog #317 already captures the session-start context injection use case. To raise confidence: read Trellis source code at `src/templates/` to extract the actual PreToolUse hook implementation and payload format. |

---

## Improvement 1: SessionStart hook auto-loads active task context for resuming agents

**Source pattern**: "Journals in `.trellis/workspace/` preserve what happened last time, so each new session starts with real context." (Relevance section 4) and "PreToolUse hook for CC v2.1.63+" (Key Features section 6)
**Local system**: `plugins/development-harness/hooks/session-start-session-id.cjs`
**Confidence**: Low
**Impact**: Medium
**Backlog**: Deferred -- confidence Low: Trellis hook implementation details are undocumented in reviewed sources. Backlog #317 already tracks the broader session continuity problem with a concrete 3-part solution (pre-compact hook, log file convention, session-start injection). This improvement would be a subset of #317.

### Current state

The SessionStart hook (`plugins/development-harness/hooks/session-start-session-id.cjs`) captures the session ID from stdin JSON and injects it as `CLAUDE_CODE_SESSION_ID` into the environment. It does not read any prior session state, task context, or workspace journal. When an agent session starts (or resumes after context compaction), it has zero awareness of what the prior session accomplished, what task was in progress, or what decisions were made.

The `session-historian` skill (`.claude/skills/session-historian/SKILL.md`) can search prior transcripts post-hoc via DuckDB, but requires manual invocation -- it is a pull mechanism, not an automatic push.

### Target state

The SessionStart hook reads the active task context (`~/.dh/projects/{slug}/context/active-task-{session-id}.json`) and the most recent session work log, then injects a summary into the conversation context via `hookSpecificOutput`. The injected context includes: current task ID and status, last 3 completed actions, and any blockers or decisions from the prior session.

### Measurable signal

A new session started in a project with an active SAM task receives a `hookSpecificOutput` message containing the task ID, status, and recent activity -- without the user or agent invoking any skill or command. Verifiable by reading the SessionStart hook output JSON for the `hookSpecificOutput` field when `active-task-*.json` exists.
