---
name: Add plan-mode gate to implement-feature SAM execution workflow before destructive agent dispatch
description: "**Current state**: `plugins/python3-development/skills/implement-feature/SKILL.md` dispatches task agents directly into full execution mode via `Skill(skill='start-task', ...)`. No mechanism exists for the agent to surface a structured plan for human review before the sub-agent executes file edits, bash commands, or other irreversible operations. The `start-task` skill (`plugins/python3-development/skills/start-task/SKILL.md`) claims the task and proceeds immediately to implementation in step 3 without a plan-first gate.\n\n**Target state**: `implement-feature` supports an optional `--plan-first` mode (or task-level flag `plan_review: true` in task YAML frontmatter). When enabled, the sub-agent invoked via `start-task` enters a plan-only phase: it reads task acceptance criteria, produces a structured markdown plan (listing each file it will edit, each bash command it will run, and rationale), writes the plan to `plan/task-plan-{task_id}.md`, and halts. The orchestrator (implement-feature loop) reads the plan file, surfaces it to the user for approval, and only dispatches the full execution agent after approval is received. Rejection returns feedback to the agent and requests a revised plan. This mirrors the `swarm-patterns` Pattern 5 plan_approval_response mechanism but applied at the SAM task level.\n\n**Measurable signal**: `implement-feature` SKILL.md contains a `--plan-first` flag description and a plan-approval step in its Progress Loop section. `start-task` SKILL.md documents a `plan_review: true` task field that triggers plan-only mode before execution. A task YAML file with `plan_review: true` causes `start-task` to write `plan/task-plan-{task_id}.md` and exit before any Write/Edit/Bash tool calls."
metadata:
  topic: add-plan-mode-gate-to-implement-feature-sam-execution-workfl
  source: 'Research entry: ./research/coding-agents/1code.md — pattern: Plan mode before agent mode (Patterns Worth Adopting section)'
  added: '2026-03-17'
  priority: P1
  type: Feature
  status: open
  issue: '#758'
  last_synced: '2026-03-17T01:08:48Z'
  groomed: '2026-03-17'
---

## RT-ICA

<div><sub>2026-03-17T01:07:35Z</sub>

RT-ICA Snapshot: Add plan-mode gate to implement-feature SAM execution workflow
Goal: Add optional plan-first mode to SAM task execution so agents surface a structured plan for human review before irreversible operations.
Conditions:
1. implement-feature SKILL.md execution loop structure is understood | Status: DERIVABLE
2. start-task SKILL.md task claim and execution flow is understood | Status: DERIVABLE
3. Task YAML frontmatter schema supports additional fields | Status: DERIVABLE
4. swarm-patterns Pattern 5 plan_approval_response mechanism exists and is documented | Status: DERIVABLE
5. Plan file naming convention (plan/task-plan-{task_id}.md) does not conflict with existing conventions | Status: DERIVABLE
6. Hook system (SubagentStop, PostToolUse) interaction with plan-only mode is understood | Status: DERIVABLE
7. Agent tool plan mode parameter exists for delegated agents | Status: DERIVABLE
AVAILABLE count: 0
DERIVABLE count: 7
MISSING count: 0
</div>

## Groomed (2026-03-17)

### Issue Classification

<div><sub>2026-03-17T01:08:29Z</sub>

Type: missing-guardrail
Confidence: high
Rationale: The item describes a safety mechanism that should exist but doesn't — a human review/approval gate before destructive operations (file edits, bash commands). Current state directly dispatches agents to execution without plan review. Target state adds an optional --plan-first mode with structured plan output and approval step before execution proceeds. This mirrors the established swarm-patterns Pattern 5 plan_approval_response mechanism, confirming the pattern is proven and bounded. Design is not open-ended because it has clear precedent, specific task-level flag (plan_review: true), specific output file path convention (plan/task-plan-{task_id}.md), and defined approval loop. This is a guardrail (preventing unreviewed agent actions) that is currently absent.
</div>

## Fact-Check

<div><sub>2026-03-17T01:08:48Z</sub>

Claims checked: 5
VERIFIED: 5
REFUTED: 0
INCONCLUSIVE: 0

1. CLAIM: "implement-feature dispatches task agents directly into full execution mode via Skill(skill='start-task', ...)"
   VERDICT: VERIFIED
   EVIDENCE: File: plugins/python3-development/skills/implement-feature/SKILL.md, lines 71-75 — exact quote: "Launch the agent with a prompt that invokes `start-task`: `Skill(skill="start-task", args="{task_file_path} --task {task_id}")`"

2. CLAIM: "No mechanism exists for the agent to surface a structured plan for human review before the sub-agent executes file edits"
   VERDICT: VERIFIED
   EVIDENCE: File: plugins/python3-development/skills/start-task/SKILL.md — task execution flow (steps 1-6) shows no plan-review gate. Step 6 proceeds directly: "Implement against the task acceptance criteria and run its verification steps." No intermediate plan-approval step exists in either implement-feature or start-task SKILL.md.

3. CLAIM: "start-task claims the task and proceeds immediately to implementation in step 3 without a plan-first gate"
   VERDICT: VERIFIED
   EVIDENCE: File: plugins/python3-development/skills/start-task/SKILL.md, steps 3-6 — step 3 (lines 69-90): claim task via `sam claim`. Step 4 (lines 92-105): write context file. Step 5 (lines 107-138): record divergence notes. Step 6 (line 140): "Implement against the task acceptance criteria...". No plan-approval step exists between task claim and implementation start.

4. CLAIM: "This mirrors the swarm-patterns Pattern 5 plan_approval_response mechanism"
   VERDICT: VERIFIED
   EVIDENCE: File: .claude/skills/swarm-patterns/SKILL.md, lines 182-218 — Pattern 5 titled "Plan Approval Workflow" documents: (line 196) `mode: "plan"` parameter, (line 201) plan_approval_request message handling, (lines 204-217) plan_approval_response mechanism with approve/reject logic. The pattern is proven and documented.

5. CLAIM: "Agent tool has a plan mode parameter for delegated agents"
   VERDICT: VERIFIED
   EVIDENCE: File: .claude/skills/swarm-patterns/SKILL.md, lines 191-198 — Agent call with explicit parameter: `mode: "plan",  // Requires plan approval`. This is used in Pattern 5 to control whether the agent enters plan-only mode (requiring explicit approval) vs. direct execution mode. The mechanism is documented and instantiated in working example code.
</div>