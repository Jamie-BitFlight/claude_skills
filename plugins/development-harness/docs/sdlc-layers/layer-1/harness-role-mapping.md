# Harness Role ↔ Agent Archetype Mapping

Explicit mapping from abstract roles to agent archetypes used by the development harness.

---

## Abstract Roles

| Role | Responsibility | Consulted During |
|------|-----------------|------------------|
| **architect** | Design decisions, interface definitions, module structure | S2 Planning, S4 Task Decomposition |
| **test-designer** | Test strategy, test case generation, coverage analysis | S4 Task Decomposition, S5 Execution |
| **code-reviewer** | Code quality, pattern compliance, idiom enforcement | S6 Forensic Review |
| **design-spec** | Design specification documents, ADRs | S2 Planning |
| **linting** | Formatting, lint orchestration | S5 Execution quality gates |

---

## Agent Archetypes

| Role | Archetype | Typical Capabilities |
|------|-----------|----------------------|
| architect | Plan/Explore | Codebase analysis, architecture patterns, interface design |
| test-designer | dh:task-worker (specialist via profile_load) | Test strategy, pytest/vitest/jest patterns |
| code-reviewer | code-review | Security, performance, pattern compliance |
| design-spec | dh:task-worker (specialist via profile_load) | ADR format, spec document structure |
| linting | Skill (not agent) | Ruff, ESLint, Prettier, etc. — invoked as commands |

---

## Fallback

When a role is not declared in the manifest, the harness dispatches `dh:task-worker` for that role with no specialist profile loaded. `task-worker` executes the task directly using full dh tool permissions (SAM MCP, backlog MCP).
