# Output Format Reference

Templates and required structure for all artifacts produced by the linear-walkthrough skill.

## Coverage Plan Format

File: `walkthrough/coverage-plan.md`

```markdown
# Coverage Plan

## Repository Summary

- **Repository**: {name}
- **Primary languages**: {languages}
- **Frameworks**: {frameworks}
- **Package boundaries**: {monorepo structure, services, libraries}
- **Total estimated source tokens**: {estimate}

## Agent Assignments

### Agent {id}: {scope title}

- **Scope**: {1-2 sentence description of what this agent traces}
- **Entry points**: {list of entry points this agent follows}
- **Assigned files/directories**:
  - {path1} — {reason for assignment}
  - {path2} — {reason for assignment}
- **Estimated token budget**: {tokens}
- **Dependencies on other agents**: {none, or list of agent IDs whose output informs this agent}
- **Shared infrastructure files**: {files this agent reads that are also assigned to other agents, with justification}

## Coverage Map

| File/Directory | Assigned Agent | Reason |
|---------------|---------------|--------|
| {path} | Agent {id} | {reason} |

## Uncovered Areas

| File/Directory | Reason Not Covered | Priority |
|---------------|-------------------|----------|
| {path} | {reason} | {high/medium/low} |
```

## Entry Point Index Format

File: `walkthrough/entry-points.md`

```markdown
# Entry Point Index

## Summary

Total entry points identified: {N}

## Entry Points

### {name}

- **Type**: {application bootstrap | CLI command | HTTP/RPC server | worker/job runner | scheduled task | event consumer | test harness | deployment entry point | local development startup | other}
- **File**: {file path with line number if applicable}
- **Purpose**: {what this entry point does}
- **Owning subsystem**: {subsystem or module name}
- **Downstream walkthrough section**: Section {id}
- **Discovery evidence**: {how this was identified — file name pattern, framework convention, config reference, explicit main() call}
```

## Walkthrough Section Format

File: `walkthrough/sections/walkthrough-section-{id}.md`

Each section answers these questions explicitly:

- What comes before this?
- What happens here?
- What comes after this?
- Why does this section exist?
- What files define it?
- What assumptions or dependencies does it rely on?
- How would a developer verify this behavior?

```markdown
# Section {id}: {title}

## Metadata

- **Section ID**: {id}
- **Title**: {descriptive title}
- **Owning files**: {list of primary files that define this section}
- **Upstream sections**: {section IDs that feed into this, or "None — entry point"}
- **Downstream sections**: {section IDs that this feeds into, or "None — terminal"}
- **Triggering entry points**: {entry point names from entry-points.md}
- **Agent**: {agent ID that produced this section}

## Context

**What comes before this**: {description of prerequisite state, prior execution, or triggering conditions}

**Why this section exists**: {the role this subsystem plays in the overall codebase}

## Step-by-Step Flow

1. **{Step title}** (`{file:line}`)
   - {What happens at this step}
   - {Data or control passed}
   - {Side effects if any}

2. **{Step title}** (`{file:line}`)
   - {What happens}
   - Branch: {if condition} → {outcome A} | {otherwise} → {outcome B}

{Continue for all steps in execution order}

## Key Interfaces

| Symbol | File | Role |
|--------|------|------|
| {class/function/module name} | {file path} | {what it does in this flow} |

## Configuration and Dependencies

- **Config files**: {list of config files that affect this flow}
- **Environment variables**: {relevant env vars}
- **External dependencies**: {APIs, databases, queues, services}
- **Internal prerequisites**: {other modules that must be initialized first}

## Inputs and Outputs

- **Key inputs**: {what data enters this subsystem}
- **Key outputs**: {what data leaves this subsystem}
- **Side effects**: {file writes, network calls, state mutations, logs, metrics}

## What Comes After

{Description of downstream systems, next stages in the pipeline, or terminal state}

## Operational Notes

{Deployment considerations, scaling behavior, failure modes, retry logic, error handling patterns}

## Confidence and Open Questions

- **Confidence**: {High | Medium | Low} — {basis for confidence level}
- **Verified claims**: {list of claims verified against source code}
- **Inferences**: {list of claims marked as [INFERENCE] with reasoning}
- **Open questions**: {unresolved uncertainties}
```

## Validation Report Format

File: `walkthrough/validation/validation-report-{id}.md`

```markdown
# Validation Report {id}

## Scope

- **Sections validated**: {list of section IDs}
- **Validator agent**: {agent ID}
- **Source files checked**: {count and list of key files read for verification}

## Corrections

### Correction {n}

- **Section**: {section ID}
- **Location**: {step number or subsection}
- **Original claim**: {what the section stated}
- **Actual behavior**: {what the source code shows}
- **Source evidence**: {file:line reference}
- **Severity**: {Critical — wrong sequence or invented behavior | Major — missing prerequisite or broken reference | Minor — imprecise wording or missing detail}

## Contradictions With Other Sections

### Contradiction {n}

- **Sections involved**: {section IDs}
- **Nature**: {what each section claims}
- **Resolution**: {which is correct based on source, or unresolved}

## Consistency Check

- **Naming consistency**: {any inconsistent use of terms across sections}
- **Terminology alignment**: {terms used differently in different sections}
- **System boundary clarity**: {any ambiguity about where one subsystem ends and another begins}

## Confidence Assessment

| Section | Confidence | Basis |
|---------|-----------|-------|
| {id} | {High/Medium/Low} | {reason} |

## Unresolved Issues

- {issue description} — {why it could not be resolved}
```

## Unified Walkthrough Format

File: `walkthrough/unified-walkthrough.md`

The unified walkthrough merges all validated sections into one navigable document with six major parts.

### Part 1: Executive Overview

```markdown
# {Repository Name} — Codebase Walkthrough

## What This Codebase Is

{2-3 paragraphs describing the system's purpose, users, and scope}

## Major Systems

| System | Purpose | Key Files |
|--------|---------|-----------|
| {name} | {purpose} | {primary files} |

## How The Pieces Fit Together

{Narrative or diagram showing system relationships and data flow}
```

### Part 2: Entry Point Index

Reproduce the entry point index from `walkthrough/entry-points.md`, enhanced with links to the corresponding walkthrough sections in this document.

### Part 3: Linear Walkthrough Sections

Include all validated walkthrough sections in a logical reading order. Connect them with predecessor/successor links so a reader can navigate sequentially.

Each section preserves its full structure from the section format above. Add navigation at the top of each section:

```markdown
**Previous**: [Section {id}: {title}](#section-{id}-{title}) | **Next**: [Section {id}: {title}](#section-{id}-{title})
```

### Part 4: Cross-Cutting System Coverage

Cover these areas as separate subsections. If the codebase does not include an area, state that explicitly rather than omitting the section.

- Systems architecture
- Project design and code organization
- Development requirements and local setup
- Deployment and delivery systems
- Quality control systems (linting, formatting, type checking, static analysis)
- Testing processes (unit, integration, e2e, smoke)
- Review procedures
- Documentation processes and references
- Observability, logging, metrics, and alerting
- Security, secrets, permissions, and environment boundaries
- Data stores, schemas, migrations, queues, and caches
- Runtime dependencies and external integrations

### Part 5: Repository Process Coverage

Document how the repo is worked on and operated:

- Build and packaging flows
- CI pipelines
- CD and release flows
- Branching or review practices (if discoverable)
- Linting, formatting, type checking, static analysis
- Unit, integration, e2e, and smoke tests
- Documentation generation or maintenance workflows

### Part 6: Validation Appendix

```markdown
## Validation Appendix

### Validation Coverage

| Section | Validated By | Corrections Applied | Confidence |
|---------|-------------|-------------------|------------|
| {id} | Validator {id} | {count} | {High/Medium/Low} |

### Corrections Applied

{Summary of all corrections from validation reports}

### Contradictions Found and Resolved

{Summary of contradictions and their resolutions}

### Unresolved Uncertainties

{Consolidated list from all validation reports and open-questions.md}
```

## Open Questions Format

File: `walkthrough/open-questions.md`

```markdown
# Open Questions

## Unresolved Uncertainties

### {question title}

- **Related sections**: {section IDs}
- **Nature**: {what is uncertain}
- **Why unresolved**: {what would be needed to resolve — access to runtime, external docs, domain expert}
- **Impact**: {how this uncertainty affects understanding of the codebase}

## Partial Coverage Areas

| Area | Coverage Level | What Is Missing | Priority |
|------|---------------|-----------------|----------|
| {area} | {partial/none} | {description} | {high/medium/low} |

## Follow-Up Suggestions

- {Suggested investigation or additional walkthrough scope}
```
