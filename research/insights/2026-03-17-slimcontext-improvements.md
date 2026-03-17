# Improvement Proposals: SlimContext

**Research entry**: ./research/context-management/slimcontext.md
**Generated**: 2026-03-17
**Patterns assessed**: 7
**Backlog items created**: 0
**Deferred (low confidence)**: 2
**Skipped (already covered or tracked)**: 5

---

## Improvement 1: Compression guard to prevent context compaction during tool-use cycles

**Source pattern**: "Both strategies only compress when the last message is from a user role (to avoid disrupting assistant-assistant or tool-use cycles). Long tool-use sequences (assistant <-> tool -> assistant <-> tool) may accumulate tokens without triggering compression if final message is not user message." (Limitations and Caveats section)
**Local system**: plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py
**Confidence**: Low
**Impact**: Medium
**Backlog**: Deferred -- confidence low: Claude Code's context compaction is controlled by the Claude Code runtime, not by this repository's hooks. The task_status_hook.py fires on PostToolUse events but does not control when or how context compaction occurs. Implementing a compression guard would require access to Claude Code's internal context management, which is outside this repository's control surface.

### Current state

The task_status_hook.py script fires on PostToolUse (Write|Edit|Bash) events and updates LastActivity timestamps. There is no mechanism in this repository that controls when Claude Code's internal context compaction triggers. Context compaction can occur mid-tool-use-cycle, as documented in backlog item #113 (observed during agentskill-kaizen build).

### Target state

A guard mechanism that signals to the runtime (or to the orchestrator) that context compaction should be deferred during active tool-use sequences. This would require either: (a) a Claude Code API for deferring compaction, or (b) an orchestrator-level pattern that checkpoints critical state before compaction can occur.

### Measurable signal

An active `/start-task` execution with rapid Write/Edit/Bash cycles does not lose structured task state to context compaction mid-cycle. Verifiable by: no instances of "phase completion status existed only in ephemeral context" (symptom from #113) after implementing the guard.

---

## Improvement 2: Token budget configuration per agent delegation

**Source pattern**: "TokenBudgetConfig: Shared configuration tuple (maxModelTokens, thresholdPercent, estimateTokens, minRecentMessages)" and "Memory Budget Allocation: Token budget config aligns with Claude Code's token accounting for sub-agent work -- both require explicit token thresholds and preservation rules." (Technical Architecture and Relevance sections)
**Local system**: plugins/python3-development/skills/implement-feature/SKILL.md
**Confidence**: Low
**Impact**: Medium
**Backlog**: Deferred -- confidence low: The implement-feature SKILL.md does not contain any token budget configuration. However, SAM: Context Size Management (#111) and SAM: Cost/Token Management (#120) already track the need for token budget guidance. The specific TokenBudgetConfig pattern (maxModelTokens, thresholdPercent, estimateTokens, minRecentMessages) from SlimContext is a TypeScript interface for chat history compression -- it would need significant adaptation to apply to Claude Code's agent delegation model, which dispatches sub-agents rather than managing chat history arrays.

### Current state

The implement-feature SKILL.md (plugins/python3-development/skills/implement-feature/SKILL.md) dispatches sub-agents with no explicit token budget. The delegation prompt does not specify max context size, threshold for when to summarize prior work, or minimum recent messages to preserve. Token management is entirely implicit -- the Claude Code runtime handles it.

### Target state

Agent delegation prompts include a token budget hint (e.g., estimated context consumption target) that the orchestrator uses to decide when to summarize prior agent outputs before passing them to the next agent. Configuration fields in task YAML frontmatter or skill frontmatter.

### Measurable signal

Task YAML or skill YAML contains a `token_budget` or equivalent field. The implement-feature orchestrator reads this field and adjusts delegation prompt size accordingly. Run: `grep -r "token_budget" plugins/python3-development/skills/` returns at least one match.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Compression guard for tool-use cycles | low | Claude Code's context compaction is runtime-controlled, not repo-controlled. Would need Claude Code API access or a new checkpoint mechanism to implement. Check whether Claude Code exposes compaction hooks or deferral signals. |
| Token budget configuration per agent | low | Already partially tracked by #111 and #120. SlimContext's specific TokenBudgetConfig is a chat-history-compression interface, not directly applicable to agent delegation. Would need prototype to validate whether token budget hints in delegation prompts reduce context pressure. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Token-threshold-triggered compression | Already tracked in backlog as #111 (SAM: Context Size Management) -- covers explicit guidance for measuring and managing context size per agent |
| System message preservation during compression | Already covered by Claude Code runtime behavior -- system messages (CLAUDE.md, rules) are loaded from disk on each session, not managed as chat history messages that could be dropped |
| Configurable recent-message preservation | Already tracked in backlog as #113 (Multi-session build state lost during context compaction) -- the core issue of preserving recent structured state during compaction |
| Summarization of older context into narrative | Already tracked in backlog as #113 -- the observed symptom was exactly this: compaction converted structured state to narrative, losing actionable structure |
| BYOM model pattern for compression | Too abstract for this repo -- SlimContext's BYOM pattern is a TypeScript interface design for pluggable LLM providers; Claude Code already uses a single provider (Claude) and does not need a model abstraction layer for compression |
