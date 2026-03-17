---
name: SAM task planner should include relevant skills in agent context for test-writing tasks
description: "During #328, test-writing tasks (2.1-2.11) specified agent=general-purpose but did not include the fastmcp-python-tests skill as context. This skill contains pytest patterns, FastMCP testing conventions, fixture design, and async test guidance directly relevant to the work. The swarm-task-planner agent should detect when tasks involve writing tests and automatically include testing-related skills (fastmcp-python-tests, python3-development) in the task's agent context or delegation prompt. Without this, sub-agents write tests without project-specific testing conventions."
metadata:
  topic: sam-task-planner-should-include-relevant-skills-in-agent-con
  source: 'session observation during #328 implementation'
  added: '2026-03-01'
  priority: completed
  type: Enhancement
  status: done
  issue: '#338'
  last_synced: '2026-03-01T13:34:07Z'
  groomed: '2026-03-01'
  plan: plan/tasks-13-sam-task-skills-context.md
---

## Story

As a **developer**, I want **During #328, test-writing tasks (2** so that **backlog items are tracked in GitHub**.

## Description

During #328, test-writing tasks (2.1-2.11) specified agent=general-purpose but did not include the fastmcp-python-tests skill as context. This skill contains pytest patterns, FastMCP testing conventions, fixture design, and async test guidance directly relevant to the work. The swarm-task-planner agent should detect when tasks involve writing tests and automatically include testing-related skills (fastmcp-python-tests, python3-development) in the task's agent context or delegation prompt. Without this, sub-agents write tests without project-specific testing conventions.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: session observation during #328 implementation
- **Priority**: P1
- **Added**: 2026-03-01
- **Research questions**: None

## Fact-Check

Claims checked: 3 | VERIFIED: 3 | REFUTED: 0 | INCONCLUSIVE: 0

1. VERIFIED: swarm-task-planner does not include mechanism to attach skills to tasks
   Evidence: plugins/python3-development/agents/swarm-task-planner.md — task schema has agent: field but no skills: field
2. VERIFIED: start-task skill does not read or use the Agent field from task metadata
   Evidence: .claude/skills/start-task/SKILL.md — reads task data but ignores Agent field entirely
3. VERIFIED: No pipeline mechanism exists to attach skill context to task definitions
   Evidence: Task YAML frontmatter has no skills: or context: field. Agent field is write-only.

## RT-ICA

Decision: APPROVED — all conditions available, no blockers.

Goal: Tasks in SAM plan files can declare skill dependencies so sub-agents receive domain-specific knowledge when executing.

Conditions:
1. swarm-task-planner agent files exist | AVAILABLE
2. Task YAML schema documented (TASK_FILE_FORMAT.md) | AVAILABLE
3. start-task skill reads task metadata | AVAILABLE
4. implement-feature delegates via start-task | AVAILABLE
5. Skill loading mechanism exists in Claude Code (skills: frontmatter) | AVAILABLE
6. No existing skills: field in task frontmatter | AVAILABLE — confirmed gap
7. Agent field is unused by orchestration | AVAILABLE — start-task ignores it

## Groomed (2026-03-01)

### Priority

9/10 — Blocks effective test-writing task execution in SAM workflows. Without skill context, sub-agents write tests without project-specific conventions, leading to rework or quality issues.

### Impact

- Blocks: All test-writing tasks that specify agent=general-purpose without explicit skill context
- Bottleneck: SAM task execution pipeline — orchestrators cannot ensure sub-agents have domain knowledge

### Expected Behavior

When swarm-task-planner detects a task involves writing tests (keywords: "test", "pytest", "unit test", "integration test", "fixture", "mock"), it should:
1. Add a `skills:` field to the task frontmatter
2. Include testing-related skills (e.g., fastmcp-python-tests, python3-development)
3. When start-task or implement-feature delegates, include declared skills in the delegation prompt

### Desired Structure

Task YAML frontmatter adds optional `skills:` field:

```yaml
---
task: 2.1
title: Write unit tests for scenarios
status: not-started
agent: general-purpose
skills:
  - fastmcp-python-tests
  - python3-development
dependencies: []
priority: 1
complexity: medium
---
```

### Acceptance Criteria

1. TASK_FILE_FORMAT.md documents `skills:` as optional array field
2. swarm-task-planner agent includes logic to detect test-writing keywords and add `skills:` field
3. start-task skill reads `skills:` field and passes to sub-agent
4. implement-feature skill includes `skills:` when delegating tasks
5. Task YAML roundtrip validation passes

### Scope

Two touch points:
1. swarm-task-planner (both python3-development and development-harness versions) — add skills: field generation
2. start-task + implement-feature — consume skills: field when delegating

### Dependencies

- Depends on: None (all prerequisites available per RT-ICA)
- Blocks: #337 (orchestrator bypassing delegation — root cause is no skill context), future test-writing tasks
- Related: #315 (implement-feature bypasses start-task)

### Resources

| Type | Item |
|------|------|
| Agent | plugins/python3-development/agents/swarm-task-planner.md |
| Agent | plugins/development-harness/agents/swarm-task-planner.md |
| Skill | .claude/skills/start-task/SKILL.md |
| Skill | .claude/skills/implement-feature/SKILL.md |
| Doc | .claude/docs/TASK_FILE_FORMAT.md |
| Example | plan/tasks-12-backlog-mcp-scenarios.md (issue #328) |

### Effort

Medium (~2 hours). Schema update, keyword detection, prompt composition, integration test.