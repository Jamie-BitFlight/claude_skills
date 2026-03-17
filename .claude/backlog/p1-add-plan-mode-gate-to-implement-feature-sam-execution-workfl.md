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
  last_synced: '2026-03-17T01:08:29Z'
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