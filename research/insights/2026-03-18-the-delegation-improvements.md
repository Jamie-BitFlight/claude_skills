# Improvement Proposals: The Delegation

**Research entry**: ./research/research-agent-patterns/the-delegation.md
**Generated**: 2026-03-18
**Patterns assessed**: 6
**Backlog items created**: 1 (issues: #779)
**Deferred (low confidence)**: 2
**Skipped (already covered or tracked)**: 3

---

## Improvement 1: Plan-level workflow phase field in SAM data model

**Source pattern**: "The explicit phase transitions (idle -> briefing -> working -> awaiting_approval -> done) provide a clear, finite-state model for project lifecycle management. Claude Code's SAM workflow could benefit from similar explicit phase state." (Relevance to Claude Code Development > Patterns Worth Adopting > Agency State Machine)
**Local system**: plugins/python3-development/skills/implement-feature/SKILL.md, packages/sam_schema/
**Confidence**: High
**Impact**: Medium
**Backlog**: #779 created

### Current state

The SAM workflow has three implicit phases (planning via `/add-new-feature`, execution via `/implement-feature`, quality gates via `/complete-implementation`) but no explicit plan-level phase field in the data model. Running `uv run sam status P{N}` returns task counts (`total_tasks`, `by_status`, `ready_tasks`, `blocked_tasks`, `completion_pct`) but does not report which workflow phase the plan is in. The orchestrator infers phase from task status counts (e.g., "all tasks COMPLETE" means ready for quality gates), but this inference is implicit and undocumented.

File: `plugins/python3-development/skills/implement-feature/SKILL.md` — the Progress Loop section queries `sam status` and `sam ready` but has no mechanism to read or write a plan-level phase. File: `packages/sam_schema/` — Grep for `phase` returns only code comments about addressing resolution phases, not a workflow phase field.

### Target state

The `sam_schema` Plan model includes an optional `phase` field with defined values: `planning`, `executing`, `quality-gates`, `complete`, `blocked`. The `sam status P{N}` output includes `"phase": "executing"` in its JSON response. The `/add-new-feature` skill sets phase to `planning` on plan creation. The `/implement-feature` skill sets phase to `executing` when entering the progress loop. The `/complete-implementation` skill sets phase to `quality-gates` on entry and `complete` on success.

### Measurable signal

Run `uv run sam status P{N}` on any active plan — output JSON contains a `phase` field with one of the defined values. Read any plan YAML file — frontmatter contains `phase: executing` (or equivalent). The `/implement-feature` SKILL.md references the phase field in its Progress Loop section.

---

## Improvement 2: Centralized agent action log per plan

**Source pattern**: "Every agent action is logged with timestamp, agent index, task ID, and action description. This transparency is invaluable for debugging multi-agent workflows and understanding causality." (Relevance to Claude Code Development > Patterns Worth Adopting > Transparent Action Logging)
**Local system**: plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py
**Confidence**: Low
**Impact**: Medium
**Backlog**: Deferred — confidence low: the research entry itself acknowledges "Claude Code's task_status_hook.py and task file update patterns follow this principle." The local system has per-task timestamps (Started, Completed, LastActivity) but no centralized action log. However, the hook fires on every tool call and adding a log write there could introduce performance concerns. The gap is real but the feasibility of the specific mechanism (centralized log file written by hooks) has not been validated.

### Current state

`task_status_hook.py` updates three timestamp fields per task (Started, Completed, LastActivity) but does not record what the agent did — only when it last did something. There is no centralized log file that records agent actions across all tasks in a plan. Debugging multi-agent workflows requires reading individual task files and correlating timestamps manually.

### Target state

A plan-level action log file (`plan/action-log-{slug}.jsonl`) records one JSON line per significant agent event: `{"timestamp": "...", "task_id": "T3", "agent": "python-cli-architect", "action": "claim", "detail": "..."}`. The `task_status_hook.py` appends to this log on SubagentStop and on claim events. `sam status P{N}` includes an `action_log_path` field pointing to this file.

### Measurable signal

After running `/implement-feature` on a plan with 3+ tasks, `plan/action-log-{slug}.jsonl` exists and contains one entry per task claim event and one entry per task completion event. Each entry has timestamp, task_id, agent, and action fields.

---

## Improvement 3: Reusable mid-task human approval checkpoint skill

**Source pattern**: "Generalize The Delegation's request_client_approval -> user-input -> agent-resume pattern into a reusable skill for any Claude Code workflow that requires human checkpoints." (Relevance to Claude Code Development > Integration Opportunities > Client Approval Workflow Automation)
**Local system**: plugins/python3-development/skills/start-task/SKILL.md, plugins/python3-development/skills/complete-implementation/SKILL.md
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred — confidence medium: The local system has approval gates only at `/complete-implementation` phase boundaries (after all tasks complete). There is no mechanism for a sub-agent executing a task to pause mid-execution and request human approval before continuing. However, the feasibility of implementing this within Claude Code's hook-based architecture needs investigation — Claude Code sub-agents run to completion and do not natively support "pause and resume." The Delegation runs in a browser with persistent state, which makes mid-execution pauses natural. The architectural gap between the two systems means the specific mechanism cannot be directly transplanted without design work.

### Current state

The `/start-task` skill (file: `plugins/python3-development/skills/start-task/SKILL.md`) has no mechanism for a sub-agent to halt execution and request human input mid-task. The `/complete-implementation` skill provides human review checkpoints but only after all tasks are complete. If a sub-agent encounters an ambiguity during task execution, it must either make a decision autonomously or fail the task — there is no "request approval and wait" pattern.

### Target state

A `/request-approval` skill exists that sub-agents can invoke mid-task. The skill writes an approval request file to `.claude/context/approval-request-{session_id}.json` with the question, context, and task reference. The orchestrator's progress loop checks for pending approval files before dispatching the next task and presents the request to the user. On user response, the approval file is updated and the sub-agent (or a continuation agent) resumes with the user's answer.

### Measurable signal

A SKILL.md file exists at a skills directory for `request-approval`. The `/implement-feature` Progress Loop section includes a step that checks for pending approval requests. A sub-agent can invoke `Skill(skill="request-approval", args="...")` and the orchestrator surfaces the request to the user.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Centralized agent action log per plan | Low | Research entry acknowledges local system already follows the principle via timestamps. Hook performance impact of log writes unvalidated. Would need profiling of hook latency before committing to implementation. |
| Reusable mid-task human approval checkpoint skill | Medium | Architectural gap between browser-based persistent-state agents and CLI sub-agents that run to completion. Would need a design spike to determine if pause-resume is feasible within Claude Code's hook/subagent model. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Synchronous Approval Gates | Already covered — research entry itself notes "Claude Code's /complete-implementation quality gates use a similar async gate pattern." File: `plugins/python3-development/skills/complete-implementation/SKILL.md` implements multi-phase quality gates. |
| Real-Time Status Visualization (Kanban / 3D) | Incompatible architecture — The Delegation uses WebGPU/Three.js/React for 3D visualization. Claude Code is a CLI tool. The research entry's suggestion to "Adapt The Delegation's React + Three.js UI" would require building an entirely separate application, not extending an existing local system. |
| Spatial Workstation Allocation (POI occupancy / double-dispatch prevention) | Already covered — `sam claim P{N} {task_id}` in `/start-task` SKILL.md (step 3) prevents double-dispatch with exclusive claim semantics. Research entry maps this pattern directly to the claim logic. |
