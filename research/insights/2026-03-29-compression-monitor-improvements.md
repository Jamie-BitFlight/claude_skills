# Improvement Proposals: compression-monitor

**Research entry**: ./research/ai-observability/compression-monitor.md
**Generated**: 2026-03-29
**Patterns assessed**: 6
**Backlog items created**: 3 (issues: #1109, #1110, #1111)
**Deferred (low confidence)**: 3 (medium: 2, low: 1)
**Skipped (already covered or tracked)**: 1

---

## Improvement 1: Behavioral fingerprint tracking in PostToolUse hook

**Source pattern**: "Behavioral Footprint -- Tool-Use Pattern Tracking: Shifts in response length, tool-call frequency, and latency across session boundaries." (Section: Key Features, subsection 2)
**Local system**: `plugins/development-harness/skills/implementation-manager/scripts/task_status_hook.py`
**Confidence**: High
**Impact**: Medium
**Backlog**: #1109 created

### Current state

`task_status_hook.py` fires on every PostToolUse event (line 6-7: "PostToolUse (Write|Edit|Bash): Update LastActivity timestamp using context file"). The handler reads the active task context and updates a `LastActivity` timestamp in the SAM task plan. No other behavioral data is recorded -- tool name, response length, tool-call count per turn, or latency are all discarded. The hook input JSON contains `tool_name`, `tool_input`, and timing data but none of it is persisted.

### Target state

The PostToolUse handler in `task_status_hook.py` appends a lightweight behavioral record to a JSONL file at `~/.dh/projects/{slug}/telemetry/behavioral-{session_id}.jsonl`. Each record contains: `timestamp`, `tool_name`, `response_length` (chars), `turn_number` (incrementing counter per session). A companion `behavioral_summary.py` script reads the JSONL and computes per-window fingerprints (mean response length, tool-call ratio, tool diversity) to detect shifts across the session.

### Measurable signal

File `~/.dh/projects/{slug}/telemetry/behavioral-{session_id}.jsonl` exists after a session with at least one PostToolUse event. Each line is valid JSON with keys `timestamp`, `tool_name`, `response_length`, `turn_number`. Running `behavioral_summary.py --session {session_id}` outputs a shift score comparing the first and second halves of the session.

---

## Improvement 2: Real-time drift scoring in PostToolUse hook

**Source pattern**: "Claude Code Plugin: `.claude-plugin/` folder enables real-time monitoring via PostToolUse hook" and "Behavioral Footprint: shift_score between sessions: normalized distance across response length and tool-call ratio" (Sections: Technical Architecture, Integration Points)
**Local system**: `plugins/development-harness/skills/implementation-manager/scripts/task_status_hook.py`
**Confidence**: High
**Impact**: High
**Backlog**: #1110 created

### Current state

The PostToolUse hook fires on every Write, Edit, and Bash tool call but only updates a timestamp. No computation is performed on behavioral data. When context compression occurs mid-session, the orchestrator continues with no signal that operational patterns have changed. The hook infrastructure is already in place and supports the `strict` profile for additional checks (line 76-85: HookProfile enum with MINIMAL, STANDARD, STRICT), but no strict-mode behavioral check exists for PostToolUse.

### Target state

When `CLAUDE_SKILLS_HOOK_PROFILE=strict`, the PostToolUse handler computes a rolling behavioral shift score from the last N tool calls (stored in the telemetry JSONL from Improvement 1). If the shift score exceeds a configurable threshold, the hook emits a warning via stderr: `[hook] behavioral drift detected: shift_score={score:.3f} (threshold={threshold})`. This warning is visible to the orchestrator and can trigger investigation or session checkpoint behavior. The threshold is configurable via `CLAUDE_SKILLS_DRIFT_THRESHOLD` environment variable (default: 0.3, matching compression-monitor's HIGH threshold).

### Measurable signal

With `CLAUDE_SKILLS_HOOK_PROFILE=strict` and `CLAUDE_SKILLS_DRIFT_THRESHOLD=0.3`, after a context compression event, the PostToolUse hook output on stderr includes `behavioral drift detected` when the shift score exceeds 0.3. Without compression, the message does not appear during normal operation.

---

## Improvement 3: Delegation prompt quality measurement across session

**Source pattern**: "Delegation Quality Analysis: Analyzes file-path specificity, constraint density, verification presence. Compares pre/post boundary metrics. Detects when delegation instructions degrade post-compression." (Section: Key Features, subsection 4)
**Local system**: `plugins/development-harness/skills/implement-feature/SKILL.md`
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred -- confidence medium: the implement-feature skill generates delegation prompts via orchestrator text output, not via a structured API. Measuring "file-path specificity" and "constraint density" in delegation prompts would require parsing the orchestrator's Agent tool calls, which is not directly observable from the hook infrastructure. The hook receives PostToolUse events for Write/Edit/Bash but not for Agent tool invocations. Verifying this gap would require confirming whether SubagentStop hook input contains the original delegation prompt text.

### Current state

The implement-feature skill (line 81-97) dispatches agents with prompts that include task file paths and skill-loading instructions. There is no mechanism to measure whether these prompts degrade in quality over a long session -- for example, whether later delegations contain fewer file paths, less specific constraints, or omit verification steps compared to earlier delegations in the same session.

### Target state

A delegation quality log captures key metrics from each Agent tool dispatch: number of file paths referenced, number of constraint keywords, presence of verification/validation instructions. A post-session report compares early vs. late delegation quality to detect degradation.

### Measurable signal

After running implement-feature on a plan with 5+ tasks, a file at `~/.dh/projects/{slug}/telemetry/delegation-quality-{slug}.jsonl` contains one record per dispatched agent with fields: `task_id`, `file_path_count`, `constraint_density`, `has_verification_step`, `dispatch_order`. A summary command shows whether quality metrics decline with dispatch order.

---

## Improvement 4: Negative-space decision logging for agent deliberation

**Source pattern**: "Negative-Space Logging: Append-only event log: two record types: skip (option considered + criterion for skipping) and skip_resolution (eventual outcome). Requires explicit instrumentation at agent decision points." (Section: Key Features, subsection 5)
**Local system**: `plugins/development-harness/skills/start-task/SKILL.md`, `task_status_hook.py`
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred -- confidence medium: the local system's agents do not currently have explicit decision-point instrumentation. Adding skip/resolution logging would require modifying agent prompts to call a logging function at decision points, which is a design choice the agent prompts do not currently support. The hook infrastructure could receive these events but agents would need to emit them explicitly. The research entry itself notes the false-negative rate on implicit suppression is unbounded (line 292).

### Current state

Agents dispatched by implement-feature produce outputs and tool calls but do not log options they considered and rejected. When an agent skips a verification step or chooses one approach over another, no record exists of the deliberation. Post-compression, if deliberation is suppressed (agent stops considering certain options), this is invisible.

### Target state

Agent prompts include a structured skip-logging instruction: before skipping a verification step, approach, or tool call, the agent writes a skip record to a JSONL file. The record contains: `cycle_id`, `option_considered`, `criterion`, `significance`. A resolution record is written when the outcome is observed.

### Measurable signal

After completing a task where agents face decision points, `~/.dh/projects/{slug}/telemetry/negative-space-{session_id}.jsonl` contains skip records. A calibration report compares agent-assigned significance labels against actual outcome impact.

---

## Improvement 5: Lead-lag drift ordering in multi-agent swarms

**Source pattern**: "Lead-Lag Protocol: In multi-agent systems, compression drift compounds. Agent A drifts -> Agent B inherits A's post-drift outputs -> B's behavior contaminates. By recording which instrument fires first in each agent, the lead-lag ordering reveals the root cause (which agent drifted first)." (Section: Design Decisions)
**Local system**: `.claude/skills/swarm-operations/SKILL.md`, `.claude/skills/swarm-patterns/SKILL.md`
**Confidence**: Low
**Impact**: Medium
**Backlog**: Deferred -- confidence low: the local swarm system does not produce behavioral telemetry per-agent within a team. TeamCreate/SendMessage do not expose behavioral fingerprints. Assessing whether lead-lag ordering is feasible requires knowing whether individual teammate tool-call patterns are accessible from the team leader, which is not documented in swarm-operations.

### Current state

Swarm patterns (parallel specialists, pipeline workflows) dispatch multiple agents simultaneously via TeamCreate. No per-agent behavioral telemetry is collected. If Agent A drifts after compression and contaminates Agent B's inputs, the team leader has no signal to identify Agent A as the drift source.

### Target state

Each teammate in a swarm emits behavioral fingerprint snapshots (tool-call ratio, response length mean) at regular intervals. The team leader can query per-agent drift scores and determine firing order to identify the root-cause agent.

### Measurable signal

After a swarm operation, per-agent behavioral JSONL files exist. A lead-lag analysis command identifies which agent's drift score changed first.

---

## Improvement 6: Vocabulary decay detection for constraint persistence

**Source pattern**: "Ghost Lexicon -- Vocabulary Decay Detection: Loss of low-frequency, high-precision terms after a compression boundary. High-precision terms (e.g., 'immutable', 'schema', 'rollback') are more vulnerable to compression loss than common terms. Their disappearance signals constraint loss without output-quality change." (Section: Key Features, subsection 1)
**Local system**: `CLAUDE.md`, `.claude/rules/`
**Confidence**: High
**Impact**: Medium
**Backlog**: #1111 created

### Current state

The CLAUDE.md and rules/ files define high-precision constraint terms (e.g., "surgical removal", "fail-fast", "reproduction-first", "chain of verification", "stateless handoff") that agents must follow. After context compression, there is no mechanism to verify whether the orchestrator's outputs still contain these terms. If compression causes the orchestrator to stop using "reproduction-first" vocabulary while still producing fix-related outputs, the behavioral change is invisible.

### Target state

A vocabulary canary list is maintained as a structured file at `.claude/rules/vocabulary-canary.md` containing high-precision constraint terms extracted from CLAUDE.md and rules/. A companion script `vocabulary_canary_check.py` takes a session JSONL log and checks whether canary terms appear in orchestrator outputs before and after detected compression boundaries. A decay score above 0.3 triggers a warning.

### Measurable signal

File `.claude/rules/vocabulary-canary.md` exists with 20+ high-precision terms. Running `vocabulary_canary_check.py --session {path}` produces a decay score and lists ghost terms (present pre-compression, absent post-compression). Score below 0.1 = LOW, 0.1-0.3 = MODERATE, above 0.3 = HIGH.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Delegation prompt quality measurement | Medium | Need to verify whether SubagentStop hook input contains original delegation prompt text; Agent tool dispatch is not observable from PostToolUse hooks |
| Negative-space decision logging | Medium | Requires modifying agent prompt templates to emit structured skip events; current agent architecture has no decision-point instrumentation hooks |
| Lead-lag drift ordering in swarms | Low | Swarm telemetry infrastructure does not exist; per-agent behavioral data is not accessible from team leader; multiple architectural assumptions needed |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Stall detection via LastActivity | Already tracked in backlog as #87 (SAM: Timeout/Stall Detection) and #448 (Stall detection for subagent tasks) |
