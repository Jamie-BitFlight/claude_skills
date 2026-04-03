# Improvement Proposals: Ruflo

**Research entry**: ./research/agent-frameworks/ruflo.md
**Generated**: 2026-03-28
**Patterns assessed**: 8
**Backlog items created**: 0
**Deferred (low confidence)**: 3
**Skipped (already covered or tracked)**: 3

---

## Improvement 1: Goal-drift validation between task batches in implement-feature

**Source pattern**: "Hierarchical coordinator validates outputs against original goal" and "Short task cycles with verification gates" (Relevance section, Anti-Drift Swarm Configuration, README.md lines 370-383)
**Local system**: plugins/development-harness/skills/implement-feature/SKILL.md
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred -- confidence medium: the implement-feature SKILL.md progress loop was read and confirms no goal-drift check exists between batches, but the local system's `/complete-implementation` 6-phase quality gate pipeline may compensate for drift at the end of implementation rather than between batches. Whether mid-implementation drift checks would materially reduce rework has not been measured.

### Current state

The implement-feature progress loop (SKILL.md lines 38-100) dispatches ready tasks to agents, checks for `<concerns>` blocks in agent output, and appends concerns to the backlog item. Between batches, it calls `sam_status` to check task counts but does not re-validate that completed task outputs align with the original feature goal or acceptance criteria. Goal drift is only caught at the end during `/complete-implementation` Phase T2 (feature-verifier).

### Target state

After each batch of tasks completes (before calling `sam_ready` for the next batch), the orchestrator performs a lightweight goal-alignment check: reads the feature context file (`plan/feature-context-{slug}.md`) acceptance criteria and compares against the set of completed tasks' outputs. If drift is detected (completed work diverges from stated goals), the orchestrator pauses dispatch, logs the drift observation, and asks the user whether to continue, re-plan, or abort.

### Measurable signal

The implement-feature SKILL.md contains a "Goal Alignment Check" section between batch completion and next-batch dispatch. The section references the feature context file and acceptance criteria. When a drift is detected, the orchestrator output includes a message containing "Goal drift detected" before pausing.

---

## Improvement 2: Multi-reviewer consensus for code review quality gate

**Source pattern**: "Byzantine Fault Tolerance (BFT) consensus allows multiple reviewers to vote on code quality decisions, with majority (or weighted) voting preventing individual reviewer errors from blocking legitimate PRs" (Relevance section 5, README.md lines 310-312)
**Local system**: plugins/development-harness/skills/complete-implementation/SKILL.md
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred -- confidence medium: the complete-implementation SKILL.md was read and confirms only a single code-reviewer agent is dispatched in T1. However, the local system compensates through a 6-phase sequential pipeline (code review, feature verification, integration check, doc drift, doc update, context refinement) that catches different classes of issues across phases. Whether adding reviewer parallelism within T1 would improve outcomes beyond what the pipeline already catches has not been measured.

### Current state

The complete-implementation quality gates dispatch a single `code-reviewer` agent for Phase T1 (complete-implementation/SKILL.md line 1, quality gate task mapping). If that single reviewer misses an issue or produces an incorrect assessment, no second opinion corrects it until later phases (T2 feature-verifier, T3 integration-checker) which focus on different concerns.

### Target state

Phase T1 spawns 2-3 code-reviewer agents in parallel (via TeamCreate), each with a different review focus (security, performance, correctness). Results are aggregated with a simple majority-vote rule: an issue is reported only if 2+ reviewers flag it. This reduces false positives from a single reviewer while catching issues a single reviewer might miss.

### Measurable signal

The `build_quality_gate_plan` function in `sam_schema.core.quality_gates` produces a T1 task with `agent: code-reviewer` and a `reviewers: 3` field (or equivalent). The complete-implementation SKILL.md describes the multi-reviewer dispatch and aggregation pattern.

---

## Improvement 3: Cost-aware model routing with skip-LLM tier for repetitive transforms

**Source pattern**: "Token optimizer can extend Claude Code subscription usage by 250% through intelligent routing (Agent Booster for simple tasks skips LLM calls entirely, HNSW-based pattern retrieval reduces context size by 32%, caching provides 10% savings)" (Relevance section 2, README.md lines 284-313)
**Local system**: .claude/rules/model-selection.md
**Confidence**: Low
**Impact**: Medium
**Backlog**: Deferred -- confidence low: the model-selection.md rule was read and provides manual haiku/sonnet/opus guidance, but the research entry's WASM-based transform tier and automatic cost routing operate at a different architectural level (runtime code transforms vs. model selection guidance). The local system cannot implement WASM transforms within its current architecture (Claude Code skills and agents). The pattern would require building an MCP server for code transforms, which goes beyond extending existing systems.

### Current state

Model selection is guided by `.claude/rules/model-selection.md`, a static decision table mapping agent task types to haiku/sonnet/opus. There is no runtime cost tracking, no automatic downgrade to cheaper models for simple tasks, and no skip-LLM path for repetitive code transforms. Every agent invocation uses LLM inference regardless of task complexity.

### Target state

An MCP tool intercepts common repetitive code transforms (rename variable, add error handling, add type annotations) and executes them via deterministic code transforms without LLM calls. For tasks requiring LLM inference, model selection is informed by task complexity estimation rather than static rules.

### Measurable signal

A new MCP tool exists that handles at least 3 deterministic code transforms (e.g., rename, add try/catch, add type annotations) and returns results without LLM invocation. The tool is registered and callable from agent prompts. Cost reduction is measurable by comparing token usage before and after enabling the tool on a standard task set.

---

## Improvement 4: Persistent cross-session pattern storage via MCP

**Source pattern**: "RuVector's learning loop stores successful patterns from each task, builds a knowledge graph of architectural decisions, and predicts agent routing for future tasks. This enables the system to become more efficient over time." (Relevance section 3, README.md lines 299-303)
**Local system**: .claude/CLAUDE.md, .claude/rules/
**Confidence**: Low
**Impact**: Medium
**Backlog**: Deferred -- confidence low: CLAUDE.md and the rules directory were examined and contain only static context. The research entry describes a learning loop with pattern extraction, indexing, and retrieval. The local system has no equivalent. However, Claude Code's architecture (stateless sessions with CLAUDE.md as the only persistent context) may already support a lightweight version via claude-mem MCP tools (`smart_search`, `get_observations`). Whether those tools already provide pattern storage equivalent to ReasoningBank was not verified in this assessment.

### Current state

Context persists across sessions only via CLAUDE.md (static rules) and `.claude/rules/` files. Successful patterns from completed tasks are not stored, indexed, or retrievable. Each new session starts with the same static context regardless of what worked well in previous sessions.

### Target state

An MCP server stores successful implementation patterns (agent selection, tool sequences, resolution strategies) after task completion. Future sessions query this store when encountering similar tasks, receiving pattern templates that reduce planning time and improve first-attempt success rates.

### Measurable signal

After completing a SAM task, a pattern entry is written to persistent storage (file or database). A query tool returns relevant patterns when given a task description. Patterns include at minimum: task type, agent used, tools invoked, outcome (success/failure), and timestamp.

---

## Improvement 5: Task-level stall detection using LastActivity timestamps

**Source pattern**: "Hooks System + Background Workers" with lifecycle hooks and background worker auto-dispatch (Key Features section 6, CLAUDE.md lines 210-226) -- specifically the pattern of monitoring agent activity and auto-dispatching corrective actions when activity stalls.
**Local system**: plugins/development-harness/skills/implementation-manager/scripts/task_status_hook.py
**Confidence**: Medium
**Impact**: High
**Backlog**: Deferred -- confidence medium: task_status_hook.py was read and confirms it writes LastActivity timestamps on PostToolUse events (lines 1-25). Grep for "stall" across the development-harness plugin returned no matches outside of dispatch PID staleness checks. However, the implement-feature orchestrator may already handle stalled agents by observing agent timeout or non-response -- this path was not examined.

### Current state

`task_status_hook.py` writes `LastActivity` timestamps on every PostToolUse event (line 5: "PostToolUse (Write|Edit|Bash): Update LastActivity timestamp using context file"). No process reads this field to detect stalled agents. If an agent becomes stuck (infinite loop, waiting for input, silent failure), the orchestrator has no mechanism to detect the stall and take corrective action until the agent's session timeout expires.

### Target state

The implementation-manager or implement-feature orchestrator includes a stall-detection check: before dispatching the next batch, it reads `LastActivity` for all IN_PROGRESS tasks and flags any where `now - LastActivity > stall_threshold_minutes`. Stalled tasks are reported to the orchestrator with the option to retry, skip, or escalate.

### Measurable signal

A command or MCP tool query returns stall status for IN_PROGRESS tasks. Tasks with `LastActivity` older than `stall_threshold_minutes` (configurable, default 10) appear with `stall_detected: true` in the output. The implement-feature SKILL.md references stall detection in its progress loop.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Goal-drift validation between task batches | medium | Would need to measure whether mid-implementation drift checks reduce rework compared to end-of-implementation quality gates |
| Multi-reviewer consensus for code review | medium | Would need to measure whether multi-reviewer catches issues the 6-phase pipeline misses |
| Cost-aware model routing with skip-LLM tier | low | Requires WASM or equivalent code transform infrastructure incompatible with current architecture |
| Persistent cross-session pattern storage | low | claude-mem MCP tools may already provide equivalent functionality; would need to verify |
| Task-level stall detection using LastActivity | medium | Implement-feature agent timeout behavior not examined; may already handle stalls implicitly |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Native Claude Code Integration / Multi-agent decomposition | Already covered by implement-feature SAM task decomposition + TeamCreate parallel dispatch + swarm-patterns skill (7+ orchestration patterns) |
| Specialized Agent Pool (100+ pre-built agents) | Too abstract -- the gap is quantitative (more agents) not architectural; adding agents is routine, not an improvement pattern |
| Automatic Documentation from Source | Already covered by complete-implementation Phase T4 (doc-drift-auditor) and T5 (service-docs-maintainer) |
