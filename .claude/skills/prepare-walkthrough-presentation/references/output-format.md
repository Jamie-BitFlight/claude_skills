# Output Format Reference

Templates and required structure for all artifacts produced by the prepare-walkthrough-presentation skill.

## Component Index Format

File: `presentation/component-index.md`

```markdown
# Component Index

## Summary

Total components identified: {N}
Total decks planned: {M}

## Components

### {component-name}

- **Type**: {app | service | package | library | worker | pipeline | platform layer | other}
- **Repo location**: {directory path}
- **Purpose**: {1-2 sentence description}
- **Related entry points**: {list from entry-points.md}
- **Walkthrough sections**: {list of section IDs that cover this component}
- **Deck**: {deck name — same as component, or merged deck name if combined}
- **Merge rationale**: {if merged with another component, explain why}

## Deck-to-Component Map

| Deck | Components Included | Rationale |
|------|-------------------|-----------|
| {deck-name} | {component list} | {why these are one deck} |
```

## Deck Plan Format

File: `presentation/deck-plans/component-deck-plan-{name}.md`

```markdown
# Deck Plan: {component-name}

## Audience

{Default: technical — engineers, tech leads, platform owners, SRE/DevOps, engineering managers}
{Override if specific audience noted}

## Narrative Arc

1. {Opening — what is this component and why does it matter}
2. {Context — where it sits in the system}
3. {Mechanics — how it works}
4. {Operations — how it is developed, tested, deployed}
5. {Risks — what remains uncertain or fragile}

## Source Material

| Walkthrough Section | Relevance to This Deck |
|--------------------|----------------------|
| Section {id}: {title} | {what it contributes} |

## Predecessor Components

| Component | Relationship |
|-----------|-------------|
| {name} | {what it sends to this component} |

## Successor Components

| Component | Relationship |
|-----------|-------------|
| {name} | {what this component sends to it} |

## Estimated Slide Count

{N} slides

## Notes

{Any special considerations for this deck — complex branching, shared infrastructure, etc.}
```

## Deck Outline Format

File: `presentation/decks/component-deck-outline-{name}.md`

The deck follows this required section structure. Each section contains one or more slides.

```markdown
# Deck: {component-name}

## Deck Metadata

- **Component**: {name}
- **Type**: {app | service | package | library | worker | pipeline | platform layer}
- **Repo location**: {path}
- **Slide count**: {N}
- **Audience**: {technical description}

## Slides

{Slides listed in order using the Slide Format below}
```

### Required Deck Sections (in order)

1. Cover slide
2. Component summary
3. System position
4. Entry points and triggers
5. Internal flow (may span multiple slides)
6. Key files and structure
7. Configuration and runtime requirements
8. Development workflow
9. Quality and testing
10. Deployment and operations
11. Risks and open questions
12. Appendix

## Slide Format

Each slide in the deck outline uses this format:

```markdown
### Slide {number}: {title}

**Section**: {deck section name from the 12 required sections}

**Purpose**: {what this slide communicates}

**Key points**:

- {point 1}
- {point 2}
- {point 3}

**Suggested visual**: {visual type and description}

**Speaker notes**:

{Detailed explanation for the presenter. Include context, nuance, and supporting details that do not belong on the slide itself. Reference specific files, functions, or configurations.}

**Evidence references**:

- {walkthrough section ID or file path} — {what it supports}

**Confidence**: {High | Medium | Low} — {basis}
```

### Visual Type Options

Use these visual types when specifying suggested visuals:

- **Component context diagram** — show this component in relation to adjacent systems
- **Sequence flow** — ordered steps through the component
- **Lifecycle flow** — startup, runtime, shutdown, or request lifecycle
- **Dependency map** — upstream and downstream dependencies
- **Deployment path** — build, package, deploy stages
- **Testing pyramid** — test types and coverage
- **Validation matrix** — quality gates and checks
- **File ownership map** — key files and their roles
- **Process timeline** — CI/CD or development workflow stages
- **Risk summary table** — risks ranked by severity and likelihood

Rules for visuals:

- Prefer diagrams derivable directly from walkthrough structure.
- Do not invent architecture not supported by source materials.
- If a visual requires unsupported assumptions, mark it as `[CONCEPTUAL]` and note the uncertainty.

## Deck Validation Report Format

File: `presentation/validation/component-deck-validation-{name}.md`

```markdown
# Deck Validation: {component-name}

## Scope

- **Deck validated**: component-deck-outline-{name}.md
- **Walkthrough sections checked**: {list of section IDs}
- **Other decks checked for consistency**: {list of deck names}

## Slide-Level Validation

### Slide {number}: {title}

- **Claims verified**: {count}
- **Issues found**: {count}
- **Details**:
  - {issue description — incorrect claim, unsupported statement, missing context}
  - **Source evidence**: {file path or walkthrough section reference}
  - **Severity**: {Critical | Major | Minor}
  - **Suggested correction**: {what to change}

## Cross-Deck Consistency

### {issue title}

- **Decks involved**: {deck names}
- **Nature**: {inconsistent terminology, contradictory relationship description, etc.}
- **Resolution**: {which version is correct, or unresolved}

## Terminology Audit

| Term | Used In | Consistent | Notes |
|------|---------|-----------|-------|
| {term} | {deck names} | {yes/no} | {discrepancy if any} |

## Confidence Assessment

| Slide | Confidence | Basis |
|-------|-----------|-------|
| {number} | {High/Medium/Low} | {reason} |

## Unresolved Issues

- {issue} — {why unresolvable}
```

## Presentation Crosswalk Format

File: `presentation/presentation-crosswalk.md`

```markdown
# Presentation Crosswalk

## Overview

Total decks: {N}
Total slides across all decks: {M}
Components covered: {list}

## Deck Index

| Deck | Component | Slides | Confidence | Validated By |
|------|-----------|--------|-----------|-------------|
| {name} | {component} | {count} | {High/Medium/Low} | {validator ID} |

## Cross-Component Navigation

### {component A} → {component B}

- **Relationship**: {what flows between them}
- **Deck A reference**: Slide {N}
- **Deck B reference**: Slide {M}
- **Consistency**: {verified consistent | discrepancy noted}

## Walkthrough-to-Deck Traceability

| Walkthrough Section | Deck(s) | Slide(s) |
|--------------------|---------|----------|
| Section {id}: {title} | {deck name} | Slides {numbers} |

## Validation Summary

| Deck | Corrections Applied | Critical Issues | Unresolved |
|------|-------------------|-----------------|------------|
| {name} | {count} | {count} | {count} |

## Open Items

- {item from walkthrough open-questions.md that affects presentations}
- {cross-deck consistency issue not fully resolved}
```
