# Improvement Proposals: Mission Control

**Research entry**: ./research/agent-frameworks/mission-control.md
**Generated**: 2026-04-03
**Patterns assessed**: 8
**Backlog items created**: 0
**Deferred (low confidence)**: 4
**Skipped (already covered or tracked)**: 4

---

## Improvement 1: Stall detection for in-progress SAM tasks using LastActivity timestamps

**Source pattern**: "Health monitoring -- Detects stalled agents, auto-nudges or reassigns stuck work" (Section: Convoy Mode -- Parallel Multi-Agent Execution, line 80)
**Local system**: plugins/development-harness/skills/implementation-manager/scripts/task_status_hook.py, plugins/development-harness/skills/implementation-manager/scripts/implementation_manager.py
**Confidence**: Medium
**Impact**: High
**Backlog**: Deferred -- confidence Medium: task_status_hook.py writes LastActivity on every tool call, but the consuming side (implementation_manager.py or SAM MCP `sam_ready`/`sam_status`) was not exhaustively searched to confirm no stall-detection code path exists in a module not yet read (e.g., dispatch_state.py has `dispatch_stale_check` for milestone-level work, which may partially cover this at the dispatch layer)

### Current state

`task_status_hook.py` writes `**LastActivity**: {ISO timestamp}` to task sections on every Write, Edit, or Bash call (PostToolUse hook, lines 186-191 of SKILL.md). However, no process reads this field to detect or act on stalled agents at the SAM task level. The `sam_ready` and `sam_status` MCP tools return task status but do not flag tasks where `status=in-progress` and `now - LastActivity` exceeds a threshold. The dispatch layer has `dispatch_stale_check` for milestone-scoped PID liveness, but this operates at the process level, not the SAM task level.

### Target state

The `sam_status` MCP tool (or a new `sam_stale_check` tool) flags tasks where `status=in-progress` and `now - LastActivity > stall_threshold_minutes`. The threshold is configurable (default 15 minutes). Output includes `stall_detected: true` and `minutes_since_activity: N` for each stalled task. The `/dh:execution` orchestrator can use this to reassign or nudge stalled work.

### Measurable signal

Run `mcp__plugin_dh_sam__sam_status(plan="P1")` -- output includes `stall_detected` field for in-progress tasks. A task with LastActivity older than the threshold shows `stall_detected: true`.

---

## Improvement 2: Checkpoint recovery for long-running agent work

**Source pattern**: "Checkpoint recovery -- Work resumes from last checkpoint if a session crashes, not from scratch" (Section: Convoy Mode -- Parallel Multi-Agent Execution, line 81)
**Local system**: .claude/skills/swarm-operations/SKILL.md, .claude/skills/swarm-patterns/SKILL.md, plugins/development-harness/skills/start-task/SKILL.md
**Confidence**: Low
**Impact**: High
**Backlog**: Deferred -- confidence Low: the swarm system has heartbeat timeout and task reclaim for crashed workers (swarm-operations SKILL.md lines 313-318), but the concept of "resume from last checkpoint" (partial work state persistence) versus "re-execute from scratch" requires investigation into whether Claude Code sessions can serialize partial state at all. The architecture may not support mid-task state serialization.

### Current state

When a swarm teammate crashes, it is marked inactive after a 5-minute heartbeat timeout (swarm-operations SKILL.md line 313). Another teammate can claim its tasks. However, work starts from scratch -- there is no checkpoint mechanism to resume from partial completion. The `active-task-{session_id}.json` context file tracks which task is active but stores no progress state. The dispatch system tracks wave-item completion but not intra-task progress.

### Target state

Long-running tasks write periodic checkpoint files (e.g., `~/.dh/projects/{slug}/context/checkpoint-{session_id}-{task_id}.json`) containing enough state for a replacement agent to resume rather than restart. The checkpoint contains: files modified so far, acceptance criteria items completed, and a natural-language progress summary. On task reassignment, the replacement agent reads the checkpoint and skips completed steps.

### Measurable signal

After a simulated crash (kill an agent session mid-task), the replacement agent reads a checkpoint file and begins work from the last checkpoint rather than the beginning. The checkpoint file exists at the expected path and contains structured progress data.

---

## Improvement 3: Per-task cost tracking integrated into SAM status

**Source pattern**: "Per-task cost tracking -- See exact cost to build each feature" and "Daily and monthly caps -- Auto-pause dispatch when exceeded" (Section: Cost Tracking & Budget Caps, lines 108-110)
**Local system**: plugins/development-harness/skills/implementation-manager/SKILL.md, plugins/development-harness/skills/work-milestone/SKILL.md
**Confidence**: Low
**Impact**: Medium
**Backlog**: Deferred -- confidence Low: Claude Code does not currently expose per-session token/cost metrics via an API accessible to hooks or MCP servers. The research entry describes cost tracking within Mission Control's own runtime (OpenClaw Gateway), which has native cost reporting. Without a Claude Code API for session-level cost data, there is no implementation path. The gap is real but the mechanism is architecturally incompatible at this time.

### Current state

The SAM task system tracks task status, timestamps, and agent assignments. No cost data is captured per task or per agent session. The dispatch system tracks wave completion but not cost. There is no budget cap mechanism that would auto-pause dispatch when spending exceeds a threshold.

### Target state

If Claude Code exposes per-session cost metrics, the task_status_hook (SubagentStop event) would capture session cost and write it to a `cost` field in the task YAML. The `sam_status` output would include per-task cost and cumulative feature cost. The dispatch system would compare cumulative cost against a configurable budget cap before spawning new wave items.

### Measurable signal

`mcp__plugin_dh_sam__sam_status(plan="P1")` output includes a `cost` field per task and a `total_cost` field for the feature. A budget cap in plan frontmatter triggers dispatch pause when exceeded.

---

## Improvement 4: Autonomous skill extraction from completed tasks

**Source pattern**: "Skill Extraction -- On task completion, LLM analyzes activities + deliverables to extract 0-3 reusable procedures" and "Bayesian confidence scores (prior weight 2) prevent cold-start inflation" (Section: Agent Skill Creation Loop, lines 97-101)
**Local system**: plugins/plugin-creator/skills/skill-creator/SKILL.md
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred -- confidence Medium: the local skill-creator is a human-triggered skill for creating new skills from specifications. It does not have an autonomous extraction loop. However, the gap assessment requires reading the full skill-creator SKILL.md to confirm there is no "post-task skill extraction" hook or workflow. The Grep for "skill.*extract" returned no matches in skill-creator/SKILL.md, but the file is large and was only partially searched. Additionally, the research entry's Bayesian confidence scoring mechanism operates on a persistent skill database -- the local system uses file-based skills with no confidence metadata, making the architectures partially incompatible.

### Current state

Skill creation is manually triggered via `/plugin-creator:skill-creator`. There is no post-task hook that analyzes completed task artifacts to extract reusable procedures. Skills have no confidence scores, usage tracking, or promotion/deprecation lifecycle. The skill-creator SKILL.md contains no reference to automatic extraction, Bayesian scoring, or usage-based promotion.

### Target state

A post-completion hook (triggered by the SubagentStop event after task completion) optionally invokes an LLM analysis of the task's activities and deliverables to propose 0-3 reusable skill candidates. Candidates are written to a `~/.dh/projects/{slug}/skill-candidates/` directory for human review. Each candidate includes a confidence score based on task outcome and pattern frequency.

### Measurable signal

After completing a SAM task, a file appears at `~/.dh/projects/{slug}/skill-candidates/{task-id}-candidates.md` containing 0-3 skill proposals with confidence scores. A `skill-candidates list` command shows all pending candidates.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Stall detection for in-progress SAM tasks | Medium | dispatch_stale_check partially covers this at milestone level; need to verify whether it also applies to SAM task-level execution to confirm the gap |
| Checkpoint recovery for long-running agent work | Low | Claude Code session state serialization is architecturally unclear; need to confirm whether partial-task state can be persisted and restored by a different session |
| Per-task cost tracking | Low | Claude Code does not expose per-session cost metrics via an accessible API; no implementation path exists without upstream platform support |
| Autonomous skill extraction from completed tasks | Medium | Partial search of skill-creator; Bayesian confidence scoring requires persistent skill database incompatible with current file-based skill architecture |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Agent orchestration (Convoy Mode parallel execution with dependency graphs) | Already covered: swarm-patterns SKILL.md implements Pipeline (Pattern 2) with TaskCreate dependencies and TaskUpdate addBlockedBy, equivalent to DAG-based parallel execution. Swarm Pattern 3 implements self-organizing parallel work pools. |
| Preference Learning (swipe feedback capture and injection) | Too abstract for this repo: Claude Code is a CLI tool without a persistent user preference database or approval UI. The pattern requires a stateful server and user-facing decision interface that does not map to the local architecture. |
| Real-Time Activity Feed (SSE-based multi-agent monitoring) | Already covered: Claude Code swarm operations provide automatic message delivery to leader inbox, idle_notification events, task_completed events, and heartbeat monitoring (swarm-operations SKILL.md lines 218-268). The mechanism differs (inbox files vs SSE) but the observable capability (real-time agent activity visibility) is equivalent. |
| Workspace Isolation (git worktrees and sandboxes) | Already covered: the dispatch system in work-milestone uses git worktrees for concurrent builds (confirmed by Grep results showing worktree references in 10+ dispatch and milestone files). |
