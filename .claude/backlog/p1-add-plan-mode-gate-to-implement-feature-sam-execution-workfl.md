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
  last_synced: '2026-03-17T01:02:44Z'
---