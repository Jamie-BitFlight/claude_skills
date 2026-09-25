# Holistic Linting Architecture

## Purpose

Holistic Linting owns quality-gate discovery, execution, diagnostic routing, and verification. It does not own language-specific software design.

## System boundary

```text
requested or changed work
  -> discover configured quality gates
  -> execute applicable gates
  -> preserve gate results and every emitted diagnostic
  -> classify and cluster diagnostics
  -> route diagnosis/correction
  -> verify correction integrity
  -> rerun affected gates
  -> report terminal state and finding handoffs
```

Gate verdict, diagnostic disposition, and workflow status are separate dimensions. A gate can pass while emitting advisory diagnostics; a workflow can remain blocked after a gate passes if required evidence or authority is missing.

## Ownership

Holistic Linting owns discovery of configured gates, execution evidence, diagnostic accounting, causal clustering, routing, correction-integrity verification, final reruns, and explicit unresolved/out-of-scope handoffs.

It does not own Python design standards, a duplicate general root-cause methodology, unconditional architecture review, repository backlog implementation, or copied upstream rule documentation when a current authoritative source is available.

External causal and language/domain plugins are optional capabilities unless the installed host provisions them. Resolve availability before invocation. If an unavailable capability is necessary for a safe correction, return a blocked/unresolved outcome with the missing capability and evidence. Read-only assessment does not imply authority to edit; an authorized caller/writer owns resulting corrections.

## Evidence and discovery contract

For each gate retain enough evidence to identify the gate, command, working directory, requested scope, target revision/configuration, tool identity/version when material, exit status, and emitted diagnostics. Evidence invalidated by a later edit cannot be reused as final-state proof.

Discovery terminates as exactly one of **COMPLETE**, **NO_APPLICABLE_GATES**, or **INCOMPLETE**. An empty detector result is not by itself evidence of no applicable gates. Missing executable, timeout, malformed configuration, and unsupported/custom mechanisms remain explicit.

## Diagnostic outcomes

Every material diagnostic, including warnings from a successful command, receives a disposition:

- **DEFECT** - behavior violates an established contract.
- **TOOLING_OR_CONFIGURATION_DEFECT** - analysis/configuration does not correctly represent the intended boundary.
- **JUSTIFIED_EXCEPTION** - valid behavior needs an explicit, evidence-backed and authorized policy exception.
- **UNRESOLVED** - evidence or authority is insufficient.
- **OUT_OF_SCOPE** - correction is outside the authorized boundary.

UNRESOLVED retains the diagnostic, material attempts/observations, constraint or unknown, and next evidence/decision required. OUT_OF_SCOPE retains tool/gate, rule when available, location/scope, exact diagnostic, reproduction context, and discovery revision/date. Deliver that payload to an available authorized repository consumer and record destination/receipt; otherwise return it explicitly to the caller. Never invent a plugin-local backlog.

Blocking versus advisory follows the configured repository/task contract, not diagnostic presence alone.

## Concurrency boundary

A filename neither proves independence nor dependence. Cluster by shared implementation, contract, configuration, generated-artifact, or dependency surfaces. Parallelize only correction clusters whose relevant read/write surfaces are established as independent.

## Correction-integrity contract

Before completion compare the correction against the pre-correction state and governing contract. Verify success was not manufactured by new/broadened suppressions, configuration ignore/exclusion/severity/applicability weakening, bypass/removal of a configured gate, or deletion of required behavior solely to remove a diagnostic.

Interpret matches semantically: suppression-like text in fixtures/string literals and unchanged pre-existing comments are not new weakening. Authorized exceptions remain explicit. A failed or unverified required integrity check feeds back into correction/diagnosis; a green linter alone is not completion.

## Validation contract

Preserve these observable cases:

1. Explicit unchanged files/directories remain valid requested scope.
2. Unknown/custom gate mechanisms produce INCOMPLETE rather than false completeness.
3. Discovery is read-only unless setup mutation is separately authorized.
4. Successful commands with warnings retain diagnostic dispositions.
5. Missing executable, timeout, malformed configuration, no-applicable-gate, and incomplete discovery remain distinct.
6. Incidental formatter/correction edits expand verification.
7. Unauthorized gate weakening cannot manufacture success.
8. Authorized exceptions retain evidence and authority.
9. Fixture/string suppression text and unchanged comments are not false weakening.
10. Shared cross-file causes can form one correction boundary; independent work may still parallelize.
11. File-only and supplied-evidence compatibility callers both have defined entry paths.
12. Missing external capabilities have explicit continuation/blocker outcomes.
13. Rule interpretation is version-aware where possible and has an offline/missing-evidence outcome.
14. Out-of-scope findings have a reproducible payload and delivery/return outcome.
15. Relevant later edits invalidate final evidence.
16. Read-only domain findings hand back to an authorized writer/caller.
17. Clean/no-findings and blocked outcomes are explicit.

These assertions protect behavior, not current agent names, report paths, corpus layout, or orchestration implementation.
