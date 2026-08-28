---
name: context-integration
description: Use when the PLAN artifact from SAM Stage 2 needs contextualization against actual codebase state — grounds the design plan in reality by performing scope analysis (NEW/MODIFY/COMPLETE classification), conflict detection between plan assumptions and codebase patterns, and resource mapping to concrete file paths and integration points. Produces an updated ARTIFACT:PLAN registered via MCP with a Contextualization section appended.
user-invocable: false
---

# SAM Stage 3 — Context Integration

## Role

You are the context integration agent for the SAM pipeline. You take an abstract
design plan and ground it in the concrete reality of the codebase. Every design
element maps to real files, patterns, and integration points.

## When to Use

- After Stage 2 Planning produces ARTIFACT:PLAN
- Before task decomposition (Stage 4) can create executable tasks
- When a plan needs concrete codebase references to be actionable

## Process

```mermaid
flowchart TD
    Start([ARTIFACT:PLAN + codebase access]) --> S1[1. Scope Analysis]
    S1 --> S2[2. Conflict Detection]
    S2 --> Q{Conflicts found?}
    Q -->|Yes| Resolve[Resolve or document conflicts]
    Resolve --> S3
    Q -->|No| S3[3. Resource Mapping]
    S3 --> S4[4. Plan Update]
    S4 --> Done([Contextualized ARTIFACT:PLAN])
```

### Step 1 — Scope Analysis

For each component in the plan, classify the implementation scope:

- **NEW** — no existing code; must be created from scratch
- **MODIFY** — existing code must change to support the design
- **COMPLETE** — existing code already satisfies this component (no work needed)

Document the evidence for each classification (file paths, function names, line ranges).

### Step 2 — Conflict Detection

Search the codebase for contradictions between the plan and existing patterns:

- **Pattern conflicts** — plan proposes a pattern that contradicts established conventions
- **Naming conflicts** — proposed names collide with existing identifiers
- **Structural conflicts** — plan assumes a structure that does not exist or differs
- **Dependency conflicts** — plan requires a dependency version incompatible with current state

For each conflict, document:

- What the plan assumes
- What the codebase actually contains
- Recommended resolution (adapt plan or refactor existing code)

### Step 3 — Resource Mapping

Identify existing codebase assets the plan can use:

- **Utilities** — helper functions, shared modules, common patterns
- **Patterns** — how similar features are implemented elsewhere
- **Configuration** — build config, linting rules, CI pipelines that apply
- **Tests** — existing test infrastructure, fixtures, helpers

Map each plan component to the concrete resources it will use.

### Step 4 — Plan Update

Re-register the updated plan via MCP:

```text
mcp__plugin_dh_backlog__artifact_register(
  item_id={issue},
  artifact_type="architect",
  artifact_id="plan/architect-{slug}.md",
  content="{full_updated_plan_markdown}",
  agent="context-integration",
)
```

This overwrites the previous `"architect"` artifact with the contextualized version.
Add the Contextualization section and mark the status checkbox as complete.

## Input

- `ARTIFACT:PLAN` via `artifact_read(item_id={issue}, artifact_type="architect")`
- Read access to the codebase

## Output

Updated `ARTIFACT:PLAN` with the following section appended:

```markdown
## Contextualization

### Scope Analysis

| Component | Scope | Evidence |
|-----------|-------|----------|
| <component from plan> | NEW / MODIFY / COMPLETE | <file paths, line ranges> |

### Conflict Report

| Conflict | Plan Assumes | Codebase Reality | Resolution |
|----------|-------------|------------------|------------|
| <conflict name> | <what plan says> | <what exists> | <adapt plan / refactor> |

### Resource Map

| Resource | Type | Location | Used By |
|----------|------|----------|---------|
| <existing asset> | utility / pattern / config / test | <file path> | <plan component> |

### Integration Points

1. **<integration point>** — <where new code connects to existing code; file and function>
2. <...>

### File Impact Summary

- Files to create — <list>
- Files to modify — <list>
- Files unchanged — <list>
```

End the same content with the status marker, so the re-registered `architect` artifact
records that Stage 3 ran:

```markdown
## Contextualization Status

- [x] Grounded in codebase (completed by Stage 3)
```

Both the `## Contextualization` section and this status marker are part of the single
`content=` string passed to `artifact_register` in Step 4. There is no separate document
to update.

## Role Resolution

This stage requires a codebase analyzer capable of reading files, searching
patterns, and understanding project structure. Use the project's language
manifest to find the appropriate codebase-analysis role for the tech stack.

## Behavioral Rules

- Never modify the design intent — only add concrete references
- If a conflict is unresolvable, document it and flag for human review

## Success Criteria

- Plan is ready for task decomposition without requiring further codebase exploration
