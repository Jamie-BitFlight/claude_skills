# Holistic Linting Architecture

## Purpose

Holistic Linting owns quality-gate discovery, execution, diagnostic routing, and verification. It does not own language-specific software design.

## System boundary

The plugin is responsible for this lifecycle:

```text
changed work
  -> discover configured quality gates
  -> execute applicable gates
  -> preserve diagnostics as evidence
  -> classify and cluster related diagnostics
  -> route diagnosis/correction
  -> rerun affected gates
  -> report observed result and unresolved diagnostics
```

## Ownership

### Holistic Linting

Owns:

- discovering configured formatters, linters, type checkers, hook runners, and other quality gates;
- executing the applicable configured gates at the smallest useful scope;
- preserving the command, scope, exit status, and diagnostics;
- grouping diagnostics when they share a likely causal surface and keeping independent failures separable;
- routing failures to an appropriate causal/domain capability;
- rerunning affected gates after an authorized correction;
- exposing unresolved and out-of-scope diagnostics.

It does not own:

- Python design standards or canned Python repairs;
- general architecture review;
- a duplicate root-cause methodology;
- repository backlog implementation;
- copied upstream rule documentation when an authoritative runtime/current source is available.

### Causal diagnosis

When a diagnostic needs investigation rather than an obvious mechanically safe correction, use the Development Harness root-cause tracing process. A quality-tool diagnostic is an observation, not proof that the implementation is defective or that the tool's suggested local edit is the right correction.

Diagnosis should establish, as far as evidence permits:

```text
conditions -> failure -> mechanism -> governing contract -> correction boundary
```

### Domain correction

Route implementation judgment to the relevant language/domain capability. For Python, Python Engineering owns Python-specific standards and review. Escalate to independent smell/modernization/review lanes only when consequence, uncertainty, or structural scope warrants them; do not run broad review machinery for every diagnostic.

## Invariants

- A green quality gate must come from an observed successful execution, not an assumption or stale report.
- Do not weaken a configured quality gate merely to manufacture success.
- Do not treat a diagnostic as authority for product intent.
- Preserve required product behavior while correcting quality failures.
- Do not silently discard a diagnostic because it is pre-existing or outside the immediate edit.
- Do not parallelize corrections that can modify a shared causal surface without establishing independence.
- Keep correctness/contract evidence separate from qualitative design judgments and efficiency telemetry.
- Increase investigation and review depth with consequence and uncertainty rather than applying one heavyweight workflow to every failure.

## Diagnostic outcomes

A diagnostic may resolve as:

- **DEFECT** - established behavior violates a governing contract; correct the cause.
- **TOOLING_OR_CONFIGURATION_DEFECT** - the configured analysis does not correctly represent the intended boundary; correct the owning tooling/configuration when authorized.
- **JUSTIFIED_EXCEPTION** - behavior is valid but requires an explicit, evidence-backed quality-policy exception. Do not create the exception autonomously when it weakens a gate.
- **UNRESOLVED** - evidence or authority is insufficient; report what is missing.
- **OUT_OF_SCOPE** - the diagnostic is real but correction is outside the requested boundary; hand it to repository policy rather than inventing a plugin-local backlog system.

## Concurrency boundary

Files are not the default unit of independent resolution. Cluster diagnostics by demonstrated or plausible shared causal surface first. Parallelize only clusters whose corrections cannot contend on the same implementation, contract, configuration, generated artifact, or dependency boundary.

## Validation contract

A restructuring of this plugin must preserve these observable behaviors:

1. Configured quality gates relevant to the requested/changed scope are discovered rather than assumed.
2. A clean result records actual gate execution.
3. Failed gates retain enough evidence to reproduce or continue diagnosis.
4. Failure resolution does not silently suppress, downgrade, or delete behavior merely to obtain green output.
5. Python-specific design decisions are routed to Python Engineering rather than reimplemented here.
6. Non-Python diagnostics remain routable without loading Python-only methodology.
7. Related cross-file diagnostics can be investigated as one causal problem.
8. Independent failures can be investigated independently.
9. Unresolved diagnostics remain visible at completion.
10. Out-of-scope findings are handed to repository policy without being silently lost.

These assertions protect behavior, not the current agent names, report paths, rule database, or orchestration implementation.
