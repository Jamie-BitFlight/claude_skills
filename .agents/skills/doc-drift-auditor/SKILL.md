---
name: doc-drift-auditor
description: Audit documentation claims against the implementation and other authoritative repository evidence. Use when checking whether README, architecture, configuration, API, usage, or feature documentation is stale, incomplete, contradicted by code, or missing implemented behavior. Produces evidence-backed drift findings without modifying the audited code or documentation.
---

# Documentation Drift Auditor

Determine whether documentation still describes the system it governs. Treat drift as a claim-conformance problem: identify a documentation claim, identify the authoritative implementation evidence for that claim, compare them in the applicable revision/scope, and report only demonstrated disconnects.

## Resolve scope and authority

Before comparing files:

1. Identify the requested component, documentation surface, revision/branch, and environment when supplied.
2. Discover the documentation and implementation artifacts that can materially establish the requested claims. Do not scan every document or source file merely because it exists.
3. Distinguish artifact roles:
   - **normative/contract documentation** — specifies intended behavior;
   - **descriptive documentation** — describes current implementation;
   - **planning/history** — records proposed or past behavior;
   - **generated/derived documentation** — audit only when explicitly in scope or when its generator/parity is the question;
   - **implementation/tests/configuration** — observed behavior evidence, not automatically intent.
4. Record unresolved authority instead of assuming code always wins. An unambiguous normative requirement contradicted by implementation is implementation nonconformance, not necessarily documentation drift.

## Extract claims, not keywords

Identify independently testable documentation claims such as:

- supported features and public behavior;
- commands, arguments, APIs, configuration keys and defaults;
- file/layout or architecture relationships;
- setup and operational procedures;
- compatibility/version/platform statements;
- examples that imply executable behavior.

Ignore prose whose truth cannot materially affect a user or maintainer unless the user explicitly requests editorial consistency.

For each material claim, record its source and the implementation evidence needed to test it.

## Compare against implementation

Use the cheapest reliable method for each claim:

- inspect public interfaces/config schemas for interface claims;
- inspect implementation paths and tests for behavior claims;
- execute a safe focused check when static evidence cannot distinguish the possibilities;
- use git history only when chronology, regression origin, or stale-revision explanation can change the finding.

Do not infer drift merely because code changed without documentation in the same commit. A "drift window" is evidence only when a documented claim actually became false or incomplete.

## Classify demonstrated disconnects

Use categories that describe the observed relation:

- **DOCUMENTED_NOT_IMPLEMENTED** — descriptive docs claim behavior the observed implementation does not provide.
- **IMPLEMENTED_NOT_DOCUMENTED** — implemented public/user-relevant behavior is absent from documentation whose established scope should cover it.
- **OUTDATED** — documentation accurately describes an older observed behavior but not the audited revision.
- **MISMATCHED_DETAIL** — both address the same behavior but disagree on a material parameter, name, default, path, sequence, or constraint.
- **IMPLEMENTATION_NONCONFORMANCE** — normative documentation is authoritative and implementation violates it.
- **UNCERTAIN** — evidence, authority, scope, or environment is insufficient to decide.

Do not call every undocumented internal symbol drift. "Implemented but undocumented" requires evidence that the documentation's purpose/scope is expected to expose that behavior.

## Evidence contract

For each finding include:

- documentation claim with precise location;
- implementation/contract evidence with precise location;
- audited revision or commit when available;
- classification;
- consequence: what user/maintainer decision can be wrong because of the disconnect;
- smallest correction surface: documentation, implementation, generated artifact/generator, or unresolved authority;
- confidence/evidence gap when not fully resolved.

Use line numbers when stable and useful. Use commit SHAs when revision identity or chronology matters. Do not require a historical SHA for a current-state claim when the audited revision already fixes identity.

Quote only enough source text to establish the discrepancy.

## Prioritize by consequence

Do not use a fixed category-to-severity mapping. Rank findings from the consequence of the specific mismatch:

- safety/security/data-loss or incompatible public-contract errors;
- commands/config/API instructions that cause failed or incorrect execution;
- architecture/operational guidance that can produce materially wrong changes;
- discoverability gaps for user-relevant capabilities;
- minor descriptive drift.

A missing documentation entry can be higher consequence than a documented-but-unimplemented feature, or vice versa. State the concrete consequence instead of deriving priority from category alone.

## Report

When the repository defines a scratch/report convention, write the point-in-time audit there; otherwise return the report directly unless the user requested a file.

Keep correctness evidence separate from counts. Counts may summarize demonstrated findings but are not a quality score.

For each finding use:

```text
Finding: <short name>
Classification: <category>
Consequence: <critical/high/medium/low only when justified, otherwise prose consequence>
Documentation: <path:line/section + claim>
Evidence: <path:line/symbol/revision + observed reality>
Analysis: <why these conflict; OBSERVED vs DERIVED distinctions where useful>
Correction surface: <docs | implementation | generator | needs authority decision>
```

End with:

- scope and revision audited;
- findings grouped by consequence or affected surface;
- unresolved coverage/evidence;
- optional chronology only where it explains or locates drift.

## Boundaries

- Audit read-only unless the user separately asks to repair findings.
- Do not assume project structure, documentation scope, or authority without inspecting evidence.
- Do not treat planning/TODO material as a claim of current implementation.
- Do not treat tests as infallible intent; they are implementation evidence unless repository authority says otherwise.
- Do not report generated-file drift without checking whether the generator/source-of-truth is the correct correction surface.
- Do not manufacture undocumented-feature findings from private/internal implementation details.
- Do not run broad git archaeology when current-state comparison answers the question.
