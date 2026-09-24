---
name: audit-documentation-drift
description: Audit documentation claims against implementation and authoritative repository evidence. Use when checking whether README, architecture, configuration, API, usage, or feature documentation is stale, incomplete, contradicted by code, missing implemented behavior, or inconsistent with a normative contract.
---

# Audit Documentation Drift

Determine whether documentation still describes the system it governs. Treat drift as claim conformance: identify a documentation claim, identify the authoritative evidence governing or implementing it, compare them in the applicable revision/scope, and report only demonstrated disconnects.

## Inputs and operating mode

Resolve the audited project/component, documentation surface, revision/branch, and material environment variants from the request. Ask only for missing scope that could change the audit result.

Audit read-only. Do not repair documentation or implementation unless a separate instruction explicitly requests repair after the audit.

## Resolve scope and authority

1. Discover only documentation and implementation artifacts capable of establishing the requested claims. Do not inventory every file merely because it exists.
2. Distinguish artifact roles:
   - **normative/contract documentation** — specifies intended behavior;
   - **descriptive documentation** — describes current implementation;
   - **planning/history** — records proposed or past behavior;
   - **generated/derived documentation** — inherits from a source/generator contract;
   - **implementation/tests/configuration** — observed behavior evidence, not automatically intent.
3. Record unresolved authority instead of assuming code always wins. An unambiguous normative requirement contradicted by implementation is implementation nonconformance, not documentation drift.

## Extract testable claims

Extract claims whose truth can materially affect a user or maintainer:

- supported features and public behavior;
- commands, arguments, APIs, configuration keys/defaults and environment variables;
- architecture responsibilities and data flows;
- setup/operational procedures;
- compatibility/version/platform statements;
- executable examples.

For CLI/config-heavy systems, inspect the framework actually used (for example Typer/Click decorators, parser/schema definitions, Pydantic models, constants) rather than relying on language-specific grep recipes.

Ignore private/internal symbols unless the documentation's established purpose requires exposing them.

## Compare claims with evidence

For each material claim:

1. Record the documentation source and scope.
2. Identify what evidence would support or falsify it.
3. Inspect the strongest practical implementation/contract evidence.
4. Execute a safe focused check when static evidence cannot distinguish possibilities.
5. Use git history only when chronology, regression origin, or stale-revision explanation can change or locate the finding.
6. Separate OBSERVED evidence from DERIVED conclusions.

Do not infer drift because code changed in commits that did not touch documentation. A drift window exists only when a documented claim demonstrably became false or incomplete.

## Classify demonstrated disconnects

- **DOCUMENTED_NOT_IMPLEMENTED** — descriptive docs claim behavior the audited implementation does not provide.
- **IMPLEMENTED_NOT_DOCUMENTED** — public/user-relevant implemented behavior is absent from documentation whose established scope should cover it.
- **OUTDATED** — documentation describes an older observed behavior rather than the audited revision.
- **MISMATCHED_DETAIL** — docs and implementation disagree on a material parameter, name, default, path, sequence, or constraint.
- **IMPLEMENTATION_NONCONFORMANCE** — authoritative normative documentation is unambiguous and implementation violates it.
- **UNCERTAIN** — evidence, authority, scope, or environment cannot resolve the claim.

## Evidence contract

Each finding records:

- documentation claim and precise location;
- implementation/contract evidence and precise location;
- audited revision or commit when material;
- classification;
- concrete consequence;
- correction surface: documentation, implementation, generator/source, or authority decision;
- confidence/evidence gap where unresolved.

Use line numbers when stable and useful. Use commit SHAs when revision identity or chronology matters. Quote only enough source text to establish the discrepancy.

## Prioritize by consequence

Do not map category mechanically to severity. Assess the specific consequence:

- safety/security/data-loss or incompatible public contract;
- commands/config/API guidance causing failed or incorrect execution;
- architecture/operational guidance capable of producing materially wrong changes;
- discoverability gaps for user-relevant capabilities;
- minor descriptive inconsistency.

State why the consequence earns its priority.

## Report structure

Produce:

```markdown
# Documentation Drift Audit Report

## Scope
- Project/component:
- Revision:
- Environments/variants:
- Documentation inspected:
- Implementation/contract evidence inspected:

## Findings
### <finding>
- Classification:
- Consequence:
- Documentation:
- Evidence:
- Analysis:
- Correction surface:

## Unresolved Coverage / Evidence
<items that prevent a stronger conclusion>

## Optional Timeline
<include only when chronology materially explains or locates drift>
```

Counts may summarize demonstrated findings but are not a quality score.

## Boundaries

- Do not assume project structure, documentation scope, or authority without evidence.
- Do not treat planning/TODO material as current implementation claims.
- Do not treat tests as infallible intent.
- Do not report generated-file drift without resolving the source/generator relationship.
- Do not manufacture undocumented-feature findings from private implementation details.
- Do not run broad git archaeology when current-state comparison resolves the question.
- Do not make a correction recommendation without identifying which authoritative surface is wrong or unresolved.
- Leave persistence, artifact registration, orchestration status, and caller-specific return envelopes to the caller; they are not part of documentation-drift analysis.
