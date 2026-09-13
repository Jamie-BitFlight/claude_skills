# Improvement Proposals: Skylos

**Research entry**: ./research/code-auditing/skylos.md
**Generated**: 2026-09-13
**Patterns assessed**: 4
**Backlog items created**: 1 (issues: #3509)
**Deferred (low confidence)**: 2
**Skipped (already covered or tracked)**: 1

---

## Improvement 1: Distinguish incomplete evidence from failed final verification

**Source pattern**: “Preserve an `incomplete` state when a requested proof cannot be established” rather than treating unsupported or uncertain checks as a pass. (Relevance to Claude Code Development → Patterns Worth Adopting)
**Local system**: `plugins/development-harness/skills/final-verification/SKILL.md`; `plugins/development-harness/skills/dh-meta-docs/references/default-development-flow.md`
**Confidence**: High
**Impact**: Medium
**Backlog**: #3509 created

### Current state

The Stage 7 template allows only `CERTIFIED` or `NOT_CERTIFIED`; its required-truth and quality-gate tables allow only `YES / NO` and `PASS / FAIL`. Missing or unsupported verification evidence is therefore recorded as a gap under `NOT_CERTIFIED` and routed to corrective task decomposition, despite not demonstrating that a requirement is false.

### Target state

Stage 7 has an `INCOMPLETE` outcome and per-check status that distinguishes unavailable or insufficient evidence from a demonstrated failure. The final-verification artifact preserves the evidence-gap reason and routes `INCOMPLETE` to evidence acquisition, environment remediation, or explicit human decision, while only demonstrated requirement failure follows the corrective-implementation loop.

### Measurable signal

`final-verification/SKILL.md`, the default-flow reference, stage taxonomy, and artifact-conventions reference document `INCOMPLETE`; a completed S7 artifact can record a goal or quality gate as `INCOMPLETE` with a reason; its documented routing does not create corrective implementation tasks until the evidence gap is resolved or explicitly classified as failure.

## Improvement 2: Bind final-verification evidence to an input provenance record

**Source pattern**: The `defend` attestation digest binds deterministic evidence to scanned-file hashes, policy, plugin set, filters, inventory, scores, framework selection, and check evidence. (Relevance to Claude Code Development → Patterns Worth Adopting)
**Local system**: `plugins/development-harness/skills/final-verification/SKILL.md`
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred — confidence medium: the skill lacks a provenance digest, but the artifact backend may already preserve sufficient revision metadata; its storage and comparison guarantees need verification before selecting the correct extension point.

### Current state

The Stage 7 artifact records file paths, test output, observations, and quality-gate summaries, but its template does not require a machine-comparable identity for the verified repository revision, configured gate commands, or evidence inputs.

### Target state

The verification artifact includes a deterministic provenance record covering the checked revision, changed/scanned files, gate commands and configuration, and captured evidence, with a stable digest that a later gate can compare before relying on the certification.

### Measurable signal

A final-verification artifact contains a named provenance block and digest; rerunning certification against unchanged inputs reproduces the digest, while changing a covered source file or gate configuration changes it.

## Improvement 3: Define an optional deterministic source-verifier quality gate

**Source pattern**: Use the MCP `verify_change` result as one evidence source in a coding-agent verification gate, subject to repository language support and the accepted `incomplete` policy. (Relevance to Claude Code Development → Integration Opportunities)
**Local system**: `plugins/development-harness/templates/language-manifest-template.md`; `plugins/development-harness/skills/final-verification/SKILL.md`
**Confidence**: Low
**Impact**: Low
**Backlog**: Deferred — confidence low: the source explicitly makes suitability conditional, and this checkout has no Skylos command, MCP server, supported-language inventory, or policy for handling its `incomplete` result.

### Current state

The language-manifest template specifies format, lint, typecheck, test, standards, and live-validation gates. No local gate contract describes a third-party deterministic source-verifier result or its applicability constraints.

### Target state

If a project chooses Skylos and supports its proof scope, a language manifest can declare it as an optional evidence-producing gate, including supported languages, invocation, and explicit handling for `pass`, `fail`, and `incomplete` results.

### Measurable signal

A sample language manifest and final-verification record show the optional gate's command, applicability conditions, and result-to-routing mapping; an unsupported-language fixture records `incomplete` rather than `pass`.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Attested deterministic verification evidence | medium | Verify artifact-provider revision and immutability semantics before defining a new digest format. |
| `verify_change` as an optional gate | low | Confirm Skylos installation, target-language support, and the desired `incomplete` policy in a consuming project. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Behavioral contracts for agent tool calls, refusals, and source references | The repository has no mapped agent-runtime test harness or existing contract format to extend; introducing Skylos's external format would be a new system rather than an extension of a verified local one. |
