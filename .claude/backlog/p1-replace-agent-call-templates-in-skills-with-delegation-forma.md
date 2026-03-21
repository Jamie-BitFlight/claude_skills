---
name: Replace Agent(...) call templates in skills with delegation format standard
description: "SKILL.md files across the repo contain `Agent(subagent_type=\"...\", prompt=\"...\")` call templates as instructions for how to delegate. This is wrong for three reasons:\n\n1. Redundant — the orchestrator already has the Agent tool schema in its system prompt every session\n2. Fragile — when the API changes (Task→Agent rename, parameter names), every file goes stale. This already happened twice: Task→Agent rename (30+ files stale) and hallucinated `agent=` parameter (18 files, 39+ occurrences)\n3. Contradicts delegation-format.md — the existing rule in `.claude/rules/delegation-format.md` explicitly says \"This is Tool API syntax. Workflow documentation is not code\" and lists `Agent(...)` call templates as a Wrong Format\n\nThe correct convention per delegation-format.md is prose delegation steps:\n```\nN. Task is [description] with subagent_type=\"plugin:agent-name\"\n   Context to include in the prompt: [specific file paths]\n   Output: [specific artifact the agent produces]\n```\n\nScope: ~50 files across plugins/, workshops/, .claude/knowledge/, .claude/plan/ contain `Agent(subagent_type=` call template syntax that needs converting to the delegation format standard.\n\nSuccess: zero `Agent(subagent_type=` call templates remain in SKILL.md or reference files. All delegation instructions use the prose format from delegation-format.md."
metadata:
  topic: replace-agent-call-templates-in-skills-with-delegation-forma
  source: Session observation — discovered during Task→Agent rename audit (2026-03-17)
  added: '2026-03-17'
  priority: P1
  type: Refactor
  status: needs-grooming
  issue: '#774'
  last_synced: '2026-03-21T08:07:39Z'
---

## Story

As a **maintainer of the codebase**, I want to **replace agent(...) call templates in skills with delegation format standard** so that **the code is cleaner and more maintainable**.

## Description

SKILL.md files across the repo contain `Agent(subagent_type="...", prompt="...")` call templates as instructions for how to delegate. This is wrong for three reasons:

1. Redundant — the orchestrator already has the Agent tool schema in its system prompt every session
2. Fragile — when the API changes (Task→Agent rename, parameter names), every file goes stale. This already happened twice: Task→Agent rename (30+ files stale) and hallucinated `agent=` parameter (18 files, 39+ occurrences)
3. Contradicts delegation-format.md — the existing rule in `.claude/rules/delegation-format.md` explicitly says "This is Tool API syntax. Workflow documentation is not code" and lists `Agent(...)` call templates as a Wrong Format

The correct convention per delegation-format.md is prose delegation steps:
```
N. Task is [description] with subagent_type="plugin:agent-name"
   Context to include in the prompt: [specific file paths]
   Output: [specific artifact the agent produces]
```

Scope: ~50 files across plugins/, workshops/, .claude/knowledge/, .claude/plan/ contain `Agent(subagent_type=` call template syntax that needs converting to the delegation format standard.

Success: zero `Agent(subagent_type=` call templates remain in SKILL.md or reference files. All delegation instructions use the prose format from delegation-format.md.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Session observation — discovered during Task→Agent rename audit (2026-03-17)
- **Priority**: P1
- **Added**: 2026-03-17
- **Research questions**: None
