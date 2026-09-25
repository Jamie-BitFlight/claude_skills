---
name: holistic-linting
description: Discover and run configured quality gates for requested or changed work, preserve diagnostics as evidence, route failures to the appropriate causal/domain capability, and verify corrections. Use for linting, formatting, type-checking, configured hook checks, or pre-completion quality verification.
---

# Holistic Linting

Run configured quality gates and treat diagnostics as evidence to diagnose, not instructions to silence. Read [../../ARCHITECTURE.md](../../ARCHITECTURE.md) when changing this workflow or when a diagnostic crosses language, configuration, generated-artifact, or shared-contract boundaries.

## 1. Resolve scope and discover gates

Start from explicitly requested files/directories, or task-changed files when no scope was supplied. Do not broaden into repository-wide cleanup unless requested or required by an authoritative configured gate.

Inspect repository configuration read-only. Prefer an aggregate hook/task command when repository configuration makes it authoritative; preserve unknown/custom configured hooks rather than silently reducing them to a known-tool allowlist. Do not use `discover_linters.py` for runtime discovery: it is a setup/documentation writer.

When `.pre-commit-config.yaml` is authoritative, [detect_hook_tool.py](./scripts/detect_hook_tool.py) may assist runner selection. Resolve the script from this installed skill directory, not the caller's working directory. Its answer is evidence about runner selection, not proof that all configured gates were discovered.

Classify discovery as `COMPLETE`, `NO_APPLICABLE_GATES`, or `INCOMPLETE`. Missing executables, malformed/unsupported configuration, timeout, and no-applicable-gate are distinct outcomes. Never turn an empty/unknown result into a pass.

For every planned gate retain command, cwd, scope, revision/config identity, and tool identity/version when material.

## 2. Execute and account for diagnostics

Run formatting and quality checks according to repository configuration. Formatting is a state change; add formatter-touched files to the affected verification surface.

Record exit status and emitted diagnostics for every gate. Gate success and diagnostic disposition are separate: a zero exit can still emit warnings/advisories. Account for those diagnostics before completion without promoting repository-approved warnings into failures.

If no diagnostic requires correction, continue through integrity/final reporting; do not bypass out-of-scope/advisory accounting.

## 3. Classify and cluster

Classify every material diagnostic as defect, tooling/configuration defect, justified-exception candidate, unresolved, or out-of-scope. Blocking versus advisory follows repository/task policy.

Cluster diagnostics that can share an API/type contract, configuration, generated source, dependency, or implementation boundary. A filename is not itself proof of independence or dependence. Parallelize only correction clusters whose relevant surfaces are established as independent.

## 4. Diagnose at the owning boundary

Apply an obvious mechanically safe correction only when intent is already established.

Otherwise, if `dh:root-cause-tracing-process` is actually available in the host, pass it the original gate evidence and use it to establish mechanism, governing contract, and correction boundary. If unavailable, perform only bounded causal work supported by current evidence; return `UNRESOLVED` when the missing capability/evidence prevents a safe decision.

Resolve a language/domain capability before invoking it. For Python, use `python-engineering:standards-for-python-development` when available. Broader read-only Python review capabilities such as StinkySnake, SnakePolish, `review`, or `python-quality-audit` are conditional assessment lanes, not automatic writers. If unavailable, do not invent their conclusions; if they return findings, hand correction to the caller or another authorized writer.

For non-Python failures, use an available owning domain capability when it materially improves the decision. Do not load Python methodology by default.

### Rule interpretation

Interpret a rule from evidence corresponding to the configured tool/version where practical.

- Ruff: prefer the installed tool's `ruff rule <CODE>`.
- MyPy: prefer matching-version documentation; when unavailable/offline, use the bundled [MyPy rule index](./references/rules/mypy/index.md) and [vendored MyPy docs](./references/mypy-docs/) as fallback evidence, marking version uncertainty.
- Bandit: prefer current installed/official evidence, with the bundled [Bandit rule index](./references/rules/bandit/index.md) as offline fallback.
- Other checkers: use installed/current documentation when available. For typing failures, trace expected/actual types upstream and inspect third-party stubs/configuration when relevant.

If authoritative interpretation cannot be established, retain that as missing evidence rather than guessing.

## 5. Protect quality-gate integrity

Do not autonomously add/broaden suppressions, reduce configured applicability/severity, bypass a gate, or delete required behavior merely to obtain green output.

A targeted exception is a policy decision. When evidence establishes valid behavior that requires one, record the proposed exception and required authority. Applied authorized exceptions remain explicit in final evidence.

## 6. Preserve unresolved and out-of-scope findings

For `UNRESOLVED`, retain the original diagnostic, material attempts/observations, fundamental constraint or unknown, and next evidence/decision required. An unresolved blocking requirement prevents successful workflow status.

For `OUT_OF_SCOPE`, retain tool/gate, rule when available, location/scope, exact diagnostic, reproduction command/context, and discovery revision/date. Deliver it to an existing authorized repository policy/tracker when available and record destination/receipt. If no consumer exists or delivery is unavailable, return the complete payload to the caller. Do not create a plugin-specific tracker.

## 7. Verify correction integrity and final state

Before accepting a corrected state:

1. Compare relevant source/configuration against the pre-correction state.
2. Check for newly added/broadened suppression, ignore/exclusion/severity/applicability weakening, gate bypass/removal, and deletion of required behavior.
3. Distinguish live suppression from suppression-like fixture/string text and unchanged pre-existing comments.
4. Confirm any exception is explicitly authorized.
5. Rerun every affected configured gate, including incidentally changed files.
6. If a relevant edit occurs after verification, invalidate and rerun the affected evidence.

A failed or unverified required integrity check returns to diagnosis/correction. A successful linter rerun alone is insufficient.

Report:

```text
Workflow status: DONE | BLOCKED
Scope:
Discovery: COMPLETE | NO_APPLICABLE_GATES | INCOMPLETE
Configured gates executed:
Gate results:
Diagnostic dispositions: (include explicit none)
Corrections and integrity evidence:
UNRESOLVED: (include explicit none)
OUT_OF_SCOPE and delivery status: (include explicit none)
Additional validation required:
```

Use `DONE` only when required gates/integrity checks are terminal for the claimed scope. `BLOCKED` identifies the missing evidence, authority, capability, or failing required gate.

## Bundled mechanics

- [detect_hook_tool.py](./scripts/detect_hook_tool.py) assists pre-commit-compatible runner selection.
- `discover_linters.py` is a separately authorized setup/documentation utility; it is not the runtime discovery API.

Script output is evidence, not semantic diagnosis.
