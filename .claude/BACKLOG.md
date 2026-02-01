---
last-updated: 2026-02-01
p0-count: 0
p1-count: 1
p2-count: 2
ideas-count: 0
---

# Backlog

Tracked features, ideas, and deferred work for grooming and future sessions.

---

## P0 - Must Have

_(Empty)_

---

## P1 - Should Have

### Create ecosystem-researcher agent

**Source**: [external-pattern-integration-2026-02-01.md](.claude/external-pattern-integration-2026-02-01.md)
**Added**: 2026-02-01
**Description**: New agent for ecosystem/domain research before roadmap creation. Supports three modes - Ecosystem discovery, Feasibility assessment, Comparison analysis.
**Patterns from**: gsd-project-researcher.md (research modes)
**Suggested location**: `plugins/python3-development/agents/ecosystem-researcher.md`

---

## P2 - Could Have

### Enhance swarm-task-planner with multi-source synthesis

**Source**: [external-pattern-integration-2026-02-01.md](.claude/external-pattern-integration-2026-02-01.md)
**Added**: 2026-02-01
**Description**: Add pattern for synthesizing outputs from multiple parallel research agents into unified summary documents.
**Patterns from**: gsd-research-synthesizer.md
**Suggested location**: `plugins/python3-development/agents/swarm-task-planner.md`

### Add context compliance checking

**Source**: [external-pattern-integration-2026-02-01.md](.claude/external-pattern-integration-2026-02-01.md)
**Added**: 2026-02-01
**Description**: Verify plans comply with user decisions (Decisions/Discretion/Deferred format). Requires adopting GSD CONTEXT.md artifact format.
**Patterns from**: gsd-plan-checker.md (context compliance dimension)
**Suggested location**: `plugins/python3-development/agents/plan-validator.md` or new CONTEXT.md format

---

## Ideas

_(Empty - add ideas discovered during sessions)_

---

## Completed

_(Move items here when done, with completion date)_

---

## Format Guide

```markdown
### Item title

**Source**: [link or description of where this came from]
**Added**: YYYY-MM-DD
**Description**: What needs to be done
**Patterns from**: (optional) External source if from pattern integration
**Suggested location**: (optional) Where this should be implemented
```
