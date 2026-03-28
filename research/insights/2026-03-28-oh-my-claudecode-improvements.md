# Improvement Proposals: oh-my-claudecode

**Research entry**: ./research/agent-orchestration/oh-my-claudecode.md
**Generated**: 2026-03-28
**Patterns assessed**: 7
**Backlog items created**: 0 (no backlog MCP tools available in this session)
**Deferred (low confidence)**: 3
**Skipped (already covered or tracked)**: 3

---

## Improvement 1: Verify-fix loop for failed tasks in implement-feature

**Source pattern**: "Ralph mode and the team-verify-fix pipeline address a core failure mode: partial task completion. Rather than hoping agents succeed, OMC implements explicit verify-fix loops." (Section: Relevance to Claude Code Development, subsection 3)
**Local system**: plugins/development-harness/skills/implement-feature/SKILL.md
**Confidence**: Medium
**Impact**: High
**Backlog**: Deferred -- confidence medium: the local system's complete-implementation quality gates may already serve as the retry mechanism, but the research entry's specific pattern (loop within execution, not after) would need deeper analysis of failure rates to confirm value

### Current state

The implement-feature progress loop (lines 38-114 of SKILL.md) dispatches ready tasks to agents and moves to the next batch when all complete. When a sub-agent fails or produces incorrect output, the task is marked COMPLETE by the SubagentStop hook regardless of quality. There is no verify-then-retry cycle within the execution loop itself. The quality check happens only after ALL tasks are marked COMPLETE, via `/complete-implementation`.

### Target state

The implement-feature progress loop includes a verification step after each task agent returns. If the task's acceptance criteria are not met (verifiable by running the task's verification commands), the task status is set back to NOT_STARTED (or a new FAILED status) and re-queued for the next dispatch cycle. A configurable retry limit (e.g., `max_retries: 2` in task YAML) prevents infinite loops.

### Measurable signal

After implementation: a task with a failing verification command is re-dispatched up to `max_retries` times before being marked BLOCKED. Observable via `sam_status` showing tasks in `blocked` state with a `retry_count` field. The implement-feature SKILL.md contains a "Verify-Fix Loop" section with the retry logic.

---

## Improvement 2: Automated skill extraction from debugging sessions

**Source pattern**: "The `/learner` command auto-extracts debugging patterns into reusable skills, solving the 'how do I remember this fix next time?' problem. Shows how to build knowledge capture into orchestration systems without heavyweight knowledge management infrastructure." (Section: Relevance to Claude Code Development, subsection 4)
**Local system**: plugins/plugin-creator/skills/skill-creator/SKILL.md
**Confidence**: Low
**Impact**: Medium
**Backlog**: Deferred -- confidence low: the local system uses manual skill creation via `/plugin-creator:skill-creator`. Whether automated extraction would produce skills meeting the repo's quality standards (citations, frontmatter validation, reference files) is unclear without experimentation. The local skill format is significantly more structured than OMC's simple YAML-with-triggers format.

### Current state

Skills are created manually by invoking `/plugin-creator:skill-creator` with explicit content. There is no mechanism to detect that a debugging session produced a reusable pattern, extract that pattern, and create a skill file automatically. Each session's discoveries are lost unless a human explicitly requests skill creation.

### Target state

A post-session hook or command (analogous to OMC's `/learner`) analyzes the session transcript for debugging patterns that were successfully applied (error encountered, root cause identified, fix applied, verification passed). When such a pattern is detected, it generates a draft skill file in a staging area (e.g., `.tmp/skill-drafts/`) with trigger keywords, the debugging pattern, and a quality flag indicating it needs human review before promotion to a real skill.

### Measurable signal

After implementation: `.tmp/skill-drafts/` contains at least one auto-generated skill draft after a debugging session. The draft includes `triggers:` field, a `## Pattern` section, and a `## Quality: draft -- needs review` marker. A command exists to promote drafts to real skills via `/plugin-creator:skill-creator`.

---

## Improvement 3: Session summary and replay artifacts for multi-agent workflows

**Source pattern**: "HUD statusline, session summaries, and replay logs enable post-hoc debugging of multi-agent workflows. Critical for understanding what went wrong in complex orchestration." (Section: Relevance to Claude Code Development, subsection 6)
**Local system**: plugins/development-harness/skills/implementation-manager/scripts/task_status_hook.py
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred -- confidence medium: the local system writes active-task context files and the SAM MCP provides `sam_status` for progress queries, but there is no session-level summary artifact written after a multi-agent workflow completes. The gap is real but the specific mechanism (JSON session summary, JSONL replay log) may not be the right format for this repo's file-based artifact system. Needs design work.

### Current state

The task_status_hook.py writes `active-task-{session_id}.json` context files during execution and updates LastActivity timestamps in task YAML files. After a session ends, there is no summary artifact produced. To understand what happened in a multi-agent workflow, one must reconstruct events from individual task status changes in the plan YAML and any git commit history.

### Target state

After an implement-feature session completes (all tasks dispatched, quality gates run), a session summary artifact is written to `~/.dh/projects/{slug}/sessions/{YYYY-MM-DD}-{feature-slug}.json` containing: tasks dispatched (with agent, duration, outcome), retry counts, quality gate results, total token estimate, and any concerns logged. This artifact is queryable via a new `sam_session_summary` MCP tool.

### Measurable signal

After implementation: completing an implement-feature run produces a file at the sessions path. Running `sam_session_summary(plan="P{N}")` returns structured JSON with per-task timing and outcome data.

---

## Improvement 4: Layered skill composition model

**Source pattern**: "The skill composition system shows how to layer capabilities without combinatorial explosion." (Section: Relevance to Claude Code Development, subsection 1)
**Local system**: .claude/skills/swarm-patterns/SKILL.md, plugins/development-harness/skills/start-task/SKILL.md
**Confidence**: Low
**Impact**: Low
**Backlog**: Deferred -- confidence low: OMC's three-layer model (guarantee/enhancement/execution) is described at a high level in the research entry but the internal composition mechanics are not documented. The local system already supports task-level skill loading (start-task SKILL.md lines 78-97) where tasks declare skills additively. Whether OMC's layered approach offers a concrete improvement over the existing additive model cannot be determined without examining OMC's source code.

### Current state

Skills are loaded additively per task via the `skills` field in task YAML. There is no priority layering -- all skills contribute equally to the agent's context. No concept of "guarantee layer" (always-on safety/quality skills) vs "enhancement layer" (optional parallelism, git semantics) vs "execution layer" (primary task skill).

### Target state

A skill composition config (project-level or plan-level) defines which skills belong to guarantee, enhancement, and execution layers. Guarantee-layer skills are always injected. Enhancement-layer skills are injected based on task properties (e.g., parallel-safe tasks get the parallelism skill). Execution-layer skills come from the task's `skills` field.

### Measurable signal

A configuration file or plan-level field defines skill layers. Tasks dispatched via implement-feature include guarantee-layer skills automatically without declaring them in each task's `skills` field.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Verify-fix loop for failed tasks | medium | Need failure rate data from real implement-feature runs to confirm the gap causes actual task failures vs being caught by complete-implementation quality gates |
| Automated skill extraction from debugging sessions | low | OMC's simple trigger-keyword format is much less structured than this repo's skill format; feasibility of auto-extraction meeting quality standards is unverified |
| Session summary and replay artifacts | medium | Gap is real but optimal artifact format and MCP tool design need specification work before backlogging |
| Layered skill composition model | low | OMC's internal composition mechanics are undocumented; cannot confirm the layered model offers concrete benefit over existing additive loading |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Multi-Agent Coordination Patterns (pattern 1) | Already covered: swarm-operations/SKILL.md provides TeamCreate, SendMessage, TeamDelete; swarm-patterns/SKILL.md provides parallel specialist, pipeline, and self-organizing patterns; implement-feature dispatches parallel teams when 2+ tasks are ready |
| Model Routing & Cost Optimization (pattern 2) | Already covered: .claude/rules/model-selection.md implements the same Haiku/Sonnet/Opus tier mapping by cognitive task type with identical rationale |
| Hooks & Plugin Integration (pattern 5) | Already covered: task_status_hook.py handles PostToolUse and SubagentStop events; start-task SKILL.md declares hook configuration; session-start hooks exist in .claude/hooks/ |
| Cross-Provider Orchestration (pattern 7) | Incompatible with architecture: this repo targets Claude Code exclusively; cross-provider (Codex/Gemini) coordination is outside scope |
