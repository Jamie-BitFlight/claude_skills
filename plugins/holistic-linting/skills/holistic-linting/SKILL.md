---
name: holistic-linting
description: Discover and run configured quality gates for changed work, preserve diagnostics as evidence, route failures to the appropriate causal/domain capability, and verify corrections. Use for linting, formatting, type-checking, configured hook checks, or pre-completion quality verification.
---

# Holistic Linting

Run the repository's configured quality gates and treat failures as evidence to diagnose, not instructions to silence.

Read [../../ARCHITECTURE.md](../../ARCHITECTURE.md) when changing this workflow or when a diagnostic crosses language, configuration, generated-artifact, or shared-contract boundaries.

## 1. Resolve scope and configured gates

Start from the user's requested files or the files changed by the current task. Do not broaden into repository-wide cleanup unless requested or required by a configured gate.

Discover quality gates from repository configuration rather than assuming a tool set. Prefer the repository's configured hook runner when it is the authoritative aggregate gate. Use bundled deterministic discovery helpers when available; otherwise inspect the relevant configuration directly.

For `.pre-commit-config.yaml`, use [detect_hook_tool.py](../../scripts/detect_hook_tool.py) to select `prek` or `pre-commit` and run only the requested/changed files unless the user requested an all-files pass.

Record the gate, command, scope, exit status, and diagnostics. Do not call a gate clean unless it was executed successfully for the claimed scope.

## 2. Execute before interpreting

Run formatting and quality checks according to repository configuration. Formatting output is a state change; include formatter-touched files in subsequent verification.

A diagnostic establishes what the tool reported. It does not establish product intent, the correction boundary, or that the nearest line is defective.

If every applicable gate passes, report the observed commands/scopes and finish.

## 3. Classify and cluster failures

Before dispatching independent correction work, group diagnostics that can share a causal surface: the same API/type contract, configuration, generated source, dependency, or implementation boundary. Keep unrelated failures separate.

Files are not an independence boundary. Do not run concurrent corrections that may edit the same causal surface.

Classify each cluster provisionally as:

- straightforward local correction with established intent;
- causal investigation required;
- tooling/configuration question;
- out-of-scope finding.

Escalate investigation depth with consequence and uncertainty.

## 4. Diagnose at the owning boundary

For an obvious mechanically safe correction whose intent is already established, apply the smallest behavior-preserving correction using the applicable domain guidance.

Otherwise use `dh:root-cause-tracing-process` when available. Carry the original diagnostic evidence into that process; do not invent a second lint-specific root-cause method. Establish the mechanism and governing contract before deciding whether product code, configuration/tooling, or an explicit policy exception owns the correction.

Route language-specific implementation judgment to the language/domain plugin. For Python, load `python-engineering:standards-for-python-development`. Use broader Python review capabilities such as `stinkysnake`, `snakepolish`, `review`, or `python-quality-audit` only when the demonstrated scope warrants broader independent review; do not run them for every lint error.

For non-Python failures, use the applicable domain capability when available. Do not load Python-only methodology merely because this plugin historically contained it.

## 5. Protect quality-gate integrity

Do not autonomously weaken a configured gate to make it pass. This includes adding suppressions, reducing rule applicability/severity, or deleting required behavior solely to eliminate a diagnostic.

A targeted exception is a policy decision, not automatically a defect. When evidence establishes valid behavior that cannot be represented by the configured analysis without an exception, report the evidence and required authorization rather than distorting production code or silently weakening the gate.

If intent or correction ownership remains unresolved, return `UNRESOLVED` with the missing evidence/decision.

## 6. Preserve out-of-scope findings

Do not silently discard a real diagnostic because it predates the task or falls outside the requested correction boundary. Report it and hand it to the repository's existing proactive-finding/backlog policy when one exists. Do not create a plugin-specific tracking system.

An out-of-scope diagnostic does not authorize unrelated edits.

## 7. Verify the correction

Rerun every affected configured gate on the corrected surface, including files incidentally changed by formatting or correction. Re-run a broader boundary only when the correction can affect it or the configured gate requires it.

Report:

```text
Scope:
Configured gates executed:
Observed result:
Diagnostics resolved:
UNRESOLVED:
OUT_OF_SCOPE:
Additional validation required:
```

A successful rerun is verification of the exercised gate and scope, not proof of general architecture correctness.

## Bundled mechanics

- [detect_hook_tool.py](../../scripts/detect_hook_tool.py) - choose/run the configured pre-commit-compatible hook runner.
- [discover_linters.py](../../scripts/discover_linters.py) - deterministic discovery support where its detected configuration matches the target repository.

Treat script output as discovery/execution evidence, not semantic diagnosis.
