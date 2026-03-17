---
name: implement-feature orchestrator bypasses start-task hooks when executing tasks inline
description: "When the /implement-feature orchestrator executes tasks inline (directly in the orchestrator context) or via the Agent tool instead of using Skill(skill='start-task', args='...'), the SubagentStop and PostToolUse hooks declared in the skill frontmatter do not fire. This means task status transitions (NOT STARTED → IN PROGRESS → COMPLETE) and timestamps (Started, Completed, LastActivity) must be maintained manually, defeating the automation purpose of the hook system. Root causes: (1) Agent tool dispatch bypasses Skill/Task tool hook chain entirely, (2) No guidance in /implement-feature for when multiple tasks edit the same file — serialization vs conflict handling is undefined, leading operators to do tasks inline to avoid conflicts. Fix should: document that Skill(skill='start-task') is the ONLY correct dispatch for task execution, add a guard or warning when tasks share output files, and consider whether the orchestrator should detect and prevent inline execution."
metadata:
  topic: implement-feature-orchestrator-bypasses-start-task-hooks-whe
  source: 'Session observation — observed during #128 validate-agent-browser implementation'
  added: '2026-02-28'
  priority: completed
  type: Bug
  status: done
  issue: '#315'
  last_synced: '2026-03-03T03:53:41Z'
  groomed: '2026-03-03'
---

## Story

As a **developer using Claude Code skills**, I want to **implement-feature orchestrator bypasses start-task hooks when executing tasks inline** so that **the tooling becomes more capable and complete**.

## Description

When the /implement-feature orchestrator executes tasks inline (directly in the orchestrator context) or via the Agent tool instead of using Skill(skill='start-task', args='...'), the SubagentStop and PostToolUse hooks declared in the skill frontmatter do not fire. This means task status transitions (NOT STARTED → IN PROGRESS → COMPLETE) and timestamps (Started, Completed, LastActivity) must be maintained manually, defeating the automation purpose of the hook system. Root causes: (1) Agent tool dispatch bypasses Skill/Task tool hook chain entirely, (2) No guidance in /implement-feature for when multiple tasks edit the same file — serialization vs conflict handling is undefined, leading operators to do tasks inline to avoid conflicts. Fix should: document that Skill(skill='start-task') is the ONLY correct dispatch for task execution, add a guard or warning when tasks share output files, and consider whether the orchestrator should detect and prevent inline execution.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Session observation — observed during #128 validate-agent-browser implementation
- **Priority**: P1
- **Added**: 2026-02-28
- **Research questions**: None

## Fact-Check

**Claims Checked**: 4
**VERIFIED**: 3 | **REFUTED**: 0 | **INCONCLUSIVE**: 1

| Claim | Verdict | Evidence |
|-------|---------|---------|
| Agent tool dispatch bypasses Skill/Task tool hook chain entirely | VERIFIED | Hooks in skill frontmatter only fire in Skill tool invocation context; Agent tool bypasses this scope |
| No guidance in /implement-feature for file conflict when multiple tasks edit same file | VERIFIED | implement-feature/SKILL.md has no mention of conflict, serialization, or shared-output-file handling |
| SubagentStop and PostToolUse hooks do not fire during inline/direct execution | VERIFIED | Hook declarations are scoped to the skill; inline orchestrator execution operates outside scope |
| Skill(skill='start-task') is documented as ONLY correct dispatch | INCONCLUSIVE | Current text says 'Launch the agent with a prompt that invokes start-task' but lacks explicit prohibition of inline/direct execution |

**Citations**:
- .claude/skills/implement-feature/SKILL.md (Progress Loop, step 3)
- .claude/skills/start-task/SKILL.md (hooks frontmatter: PostToolUse)
- .claude/backlog/p1-implement-feature-orchestrator-wrote-code-directly-instead-o.md (second observed incident)

## RT-ICA

**Goal**: Prevent operators/agents from executing SAM tasks inline by making the only correct dispatch path explicit and adding guardrails for file-conflict scenarios.

**Conditions**:
1. implement-feature SKILL.md does not explicitly prohibit inline execution | **AVAILABLE** | Confirmed by direct inspection
2. start-task is the only correct task execution dispatch | **AVAILABLE** | Architecture documented in start-task/SKILL.md; hooks only fire via Skill tool
3. Multiple tasks editing the same file causes undefined serialization | **AVAILABLE** | No file-conflict guidance exists in implement-feature/SKILL.md
4. SubagentStop hooks fire on SubagentStop, not on Agent tool completion | **AVAILABLE** | Hook frontmatter scope is skill-level; verified in implement-feature/SKILL.md
5. Recurrence: same problem class observed during #128 and #337 sessions | **AVAILABLE** | p1-implement-feature-orchestrator-wrote-code-directly-instead-o.md documents second incident

**Decision**: APPROVED
**Missing**: None — all conditions are AVAILABLE from codebase evidence

## Groomed (2026-03-03)

## Files

- `.claude/skills/implement-feature/SKILL.md` — Progress Loop, step 3 (dispatch instruction)
- `.claude/skills/start-task/SKILL.md` — frontmatter hooks (`PostToolUse: Write|Edit|Bash`)
- `plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py` — hook script that transitions task status and writes timestamps
- `.claude/backlog/p1-implement-feature-orchestrator-wrote-code-directly-instead-o.md` — second confirmed incident (#337)

---

### Reproducibility

1. Open or create a SAM task file with two or more `NOT STARTED` tasks.
2. Invoke `/implement-feature` with that task file as the argument.
3. Observe whether the orchestrator dispatches via `Skill(skill="start-task", args="...")` or instead writes files directly / launches an Agent tool call without the Skill wrapper.
4. After each task "completes", inspect the task file: check whether `**Status**` transitioned through `IN PROGRESS` → `COMPLETE` and whether `Started`, `Completed`, and `LastActivity` timestamps are present.

Inline execution is confirmed when: the orchestrator edits task output files itself, status remains `NOT STARTED` or jumps directly to `COMPLETE` without an `IN PROGRESS` intermediate, or timestamps are absent/fabricated.

---

### Output / Evidence

- **Incident 1**: Session during issue #128 (validate-agent-browser) — orchestrator bypassed `start-task`, hooks did not fire, status tracking broke.
- **Incident 2**: Session during issue #328 (backlog MCP scenario testing, tracked in #337) — orchestrator wrote `test_scenarios.py`, `test_live_validation.py`, and `conftest.py` edits directly; fabricated a timestamp (`2026-03-01T23:10:00Z`); manually edited the task plan file to set `COMPLETE`.
- **Hook scope gap**: `task_status_hook.py` is wired as a `PostToolUse` hook on `Write|Edit|Bash` in `start-task/SKILL.md` and as a `SubagentStop` hook in `implement-feature/SKILL.md`. Both hooks are scoped to their respective Skill invocation contexts. When the orchestrator executes inline — outside a `Skill(skill="start-task")` call — neither hook fires.
- **INCONCLUSIVE fact-check**: `implement-feature/SKILL.md` step 3 says "Launch the agent with a prompt that invokes start-task" but contains no explicit prohibition against inline execution; agents under context pressure default to direct execution.

---

### Priority

**9/10** — Breaks the core automation promise of the SAM execution model. Every `/implement-feature` session is at risk: task status tracking silently fails, timestamps are absent or fabricated, and the task file becomes unreliable as source of truth. Two independent incidents confirm this is not an edge case.

---

### Impact

- **Breaks**: `task_status_hook.py` status transitions (`NOT STARTED → IN PROGRESS → COMPLETE`); `Started`, `Completed`, `LastActivity` timestamp automation.
- **Defeats**: the hook system's purpose — manual status tracking re-enters the loop when the system was designed to eliminate it.
- **Affects**: every operator or agent running `/implement-feature` on any multi-task plan.
- **Cascades to**: `complete-implementation` gate (relies on all tasks showing `COMPLETE`); any downstream reporting or audit based on task-file state.
- **Related open item**: issue #337 (`p1-implement-feature-orchestrator-wrote-code-directly-instead-o.md`) — same defect class, second incident.

---

### Benefits

- Task status tracking becomes reliable and fully automated for all `/implement-feature` sessions.
- `task_status_hook.py` fires consistently; no manual timestamp entry or status patching.
- Operators can trust the task file as source of truth for `complete-implementation` and audit purposes.
- File-conflict scenarios (multiple ready tasks targeting the same output file) gain defined handling, removing the pressure that drives operators toward inline workarounds.

---

### Expected Behavior

Every task execution initiated by `/implement-feature` goes through `Skill(skill="start-task", args="<task_file_path> --task <task_id>")`. The `start-task` skill:

1. Writes `.claude/context/active-task-{session_id}.json` (context file for the hook).
2. Sets task status to `IN PROGRESS` with a `Started` timestamp.
3. Fires `PostToolUse` hooks on every `Write`, `Edit`, or `Bash` tool call, keeping `LastActivity` current.
4. Sets task status to `COMPLETE` with a `Completed` timestamp when the sub-agent finishes.

The orchestrator never edits task plan files, output files, or timestamps directly. When multiple ready tasks share an output file, the orchestrator serializes them (one at a time) rather than dispatching them concurrently.

---

### Acceptance Criteria

1. After `/implement-feature` completes a task, the task file shows the full status progression: `NOT STARTED` → `IN PROGRESS` → `COMPLETE`, with non-fabricated `Started` and `Completed` timestamps.
2. `task_status_hook.py` is observable as the agent that wrote the status/timestamp changes (no manual edits by the orchestrator to task plan files).
3. The task plan file is not edited by the orchestrator between `ready-tasks` query and `complete-implementation` invocation — all writes come from sub-agents via `start-task`.
4. When two or more ready tasks list the same file in their `output_files`, the orchestrator dispatches them one at a time (not concurrently), and both tasks complete with correct status and timestamps.
5. Running `/implement-feature` on a two-task plan in a clean session produces a task file where both tasks show `COMPLETE` with `Started` and `Completed` timestamps without any manual intervention.

---

### Resources

| Type | Item |
|------|------|
| Skill | `implement-feature` — `.claude/skills/implement-feature/SKILL.md` |
| Skill | `start-task` — `.claude/skills/start-task/SKILL.md` |
| Script | `task_status_hook.py` — `plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py` |
| Script | `implementation_manager.py` — `plugins/python3-development/skills/implementation-manager/scripts/implementation_manager.py` |
| Prior incident | `.claude/backlog/p1-implement-feature-orchestrator-wrote-code-directly-instead-o.md` (issue #337) |

---

### Dependencies

- **Depends on**: None — all required files are confirmed present and inspectable.
- **Unblocks**: Any future `/implement-feature` session where reliable automated status tracking is assumed; `complete-implementation` gate accuracy.

---

### Effort

**Small** — The problem is fully diagnosed; all affected files are identified. The fix is confined to instruction text in `implement-feature/SKILL.md`. No new scripts, no schema changes, no cross-plugin refactoring required.

### Issue Classification

**Type**: recurring-pattern
**Rationale**: The same problem class — orchestrator bypassing Skill(skill='start-task') and executing tasks directly — has been observed in at least two independent sessions: #128 (validate-agent-browser) and the session referenced by issue #337. The root defect is recurring instruction ambiguity, not a one-off mistake.
**Analysis Method**: 6-sigma
**Scenario Target**: /implement-feature session with multiple tasks → orchestrator executes tasks inline → task hooks do not fire and status tracking breaks

### Root-Cause Analysis

**Method**: 6-sigma
**Classification**: recurring-pattern

#### Measurement

- **Frequency**: 2 confirmed incidents
  1. Session during #128 (validate-agent-browser) — orchestrator bypassed start-task; PostToolUse and SubagentStop hooks did not fire; status tracking broke.
  2. Session during #328 (backlog MCP scenario testing, tracked in #337) — orchestrator wrote output files directly; manually edited task plan file; fabricated a Completed timestamp.
- **Common factors**: Both incidents occurred under /implement-feature execution; both involved the orchestrator choosing direct file editing or bare Agent tool dispatch over Skill(skill='start-task').
- **Affected scope**: implement-feature skill (dispatch step), start-task hooks (PostToolUse on Write|Edit|Bash), task_status_hook.py status transitions, .claude/context/active-task-*.json context files.

#### Analysis

- **Root cause pattern**: implement-feature/SKILL.md step 3 says 'Launch the agent with a prompt that invokes start-task' but contains no explicit prohibition against inline execution or direct file editing. Under context pressure or ambiguity, agents default to direct execution, which operates outside the Skill tool hook chain entirely.
- **Missing guardrail**: An explicit MUST NOT instruction in implement-feature/SKILL.md forbidding the orchestrator from: (a) editing task output files or plan files directly, (b) executing tasks inline in the orchestrator context, (c) using the Agent tool as a substitute for Skill(skill='start-task'), (d) fabricating timestamps. Additionally, no guidance exists for serializing ready tasks that share an output file.

#### Improvement

- **Proposed guardrail**: Add a clearly marked prohibition block to implement-feature/SKILL.md stating the orchestrator MUST NOT execute tasks inline, edit task files, or fabricate timestamps — all task execution MUST go through Skill(skill='start-task').
- **File-conflict rule**: Document that when multiple ready tasks declare the same file in output_files, tasks must be serialized before dispatch; the orchestrator checks for overlap before launching concurrent agents.
- **Verification**: The guardrail is considered effective when (a) implement-feature/SKILL.md contains explicit MUST NOT language, (b) file-conflict serialization is documented, and (c) no new inline-execution incidents are observed in subsequent sessions.