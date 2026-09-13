# Improvement Proposals: Skylos

**Research entry**: ./research/code-auditing/skylos.md
**Generated**: 2026-09-13
**Patterns assessed**: 4
**Backlog items created**: 1 (issues: #3509)
**Deferred (confidence too low to backlog)**: 3
**Skipped (already covered or tracked)**: 0

---

## Improvement 1: Distinguish incomplete evidence from failed final verification

**Source pattern**: “Preserve an `incomplete` state when a requested proof cannot be established” rather than treating unsupported or uncertain checks as a pass. (Relevance to Claude Code Development → Patterns Worth Adopting)
**Local system**: `plugins/development-harness/skills/final-verification/SKILL.md`; `plugins/development-harness/skills/dh-meta-docs/references/default-development-flow.md`
**Confidence**: High
**Impact**: Medium
**Backlog**: #3509 created

### Current state

The Stage 7 template allows only `CERTIFIED` or `NOT_CERTIFIED`; its required-truth and quality-gate tables allow only `YES / NO` and `PASS / FAIL`. Missing or unsupported verification evidence is therefore recorded as a gap under `NOT_CERTIFIED` and routed to corrective task decomposition, despite not demonstrating that a requirement is false — the Gaps block records "what evidence is missing" and its Remediation Path loops back to Stage 4 (`final-verification/SKILL.md`, Gaps and Remediation Path sections).

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
**Local system**: `plugins/development-harness/templates/language-manifest-template.md`; `plugins/development-harness/skills/dh-meta-docs/references/language-manifest-schema.md`
**Confidence**: Low
**Impact**: Low
**Backlog**: Deferred — confidence low: the source explicitly makes suitability conditional, and this checkout has no Skylos command, MCP server, supported-language inventory, or policy for handling its `incomplete` result.

### Current state

The language-manifest template specifies format, lint, typecheck, test, standards, and live-validation gates. `plugins/development-harness/skills/dh-meta-docs/references/language-manifest-schema.md` already defines one gate with applicability conditions and a non-binary result: `live_validation` accepts the sentinel values `agent-browser` and `claude-skill`, under which the feature-verifier records `DEFERRED_BROWSER` or `DEFERRED_SKILL` instead of running the command, and a command that exceeds the documented 120-second timeout returns `GAPS_FOUND` "rather than `PASS` or `FAIL`". What is absent is a gate contract for a *third-party* deterministic source-verifier — one whose applicability is bounded by the tool's own supported-language matrix rather than by the delivery surface.

### Target state

If a project chooses Skylos and supports its proof scope, a language manifest can declare it as an optional evidence-producing gate, including supported languages, invocation, and explicit handling for `pass`, `fail`, and `incomplete` results.

### Measurable signal

A sample language manifest and final-verification record show the optional gate's command, applicability conditions, and result-to-routing mapping; an unsupported-language fixture records `incomplete` rather than `pass`.

## Improvement 4: Extend the review-verdict contract to cover tool calls, refusals, and source references

**Source pattern**: Agent behavior contracts can require or forbid tool calls, constrain an exact tool sequence and call count, require response substrings and source IDs, and require an explicit refusal. (Key Features → Agent verification and behavior testing)
**Local system**: `plugins/development-harness/skills/review-verdict-contract/references/verdict-schema.md`; `plugins/development-harness/skills/subagent-contract/SKILL.md`; `plugins/development-harness/skills/dispatch-contract/SKILL.md`
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred — the extension point is identified and the gap is real, but two scoping questions precede an item: whether the tool-call and refusal axes belong in `verdict-schema.md` alongside the existing per-perspective blocks or in a separate scenario file, and whether the three-state result this needs is the same one #3509 introduces at Stage 7. Settle the overlap with #3509 first; splitting them produces two competing result taxonomies.

### Current state

Each of Skylos's three behavior-contract axes already has a local precedent, but they are declared in three separate places and none of them is executable as a scenario. Refusals appear twice — `verdict-schema.md` §2.1 requires a `skip_reason` field when `verdict == SKIP` and §2.3 defines the detection rule that selects SKIP, and `subagent-contract/SKILL.md` requires a first-line `STATUS: DONE` or `STATUS: BLOCKED` and says to "Return BLOCKED when a required input is missing, rather than inferring it." Source references appear as `verdict-schema.md`'s conservation invariant and its check that a finding's description appear "verbatim in some `entries[].descriptions`", which exists to catch a synthesizer altering attributions. Tool calls appear as `dispatch-contract/SKILL.md`'s prose rule that a dispatched specialist's "declared tools reach every operation handed over", and as `subagent-contract/SKILL.md`'s "Report every command you ran with its outcome." The first is a selection-time rule and the second a reporting duty; neither is a post-hoc check that the agent called only what it was scoped to.

### Target state

One declared contract covers all three axes for a dispatched agent, in the schema idiom `verdict-schema.md` already uses and already invites extending ("Future perspectives may define additional SKIP detection rules using the same pattern-list structure in this file"). A contract can state which tools an agent must or must not call, which refusal state is the correct outcome for a given input, and which source identifiers its findings must carry — and a run can be checked against it rather than reviewed as prose.

### Measurable signal

A contract file declares required and forbidden tool calls, an expected refusal state, and required source identifiers for at least one dispatched `dh:` agent; a run that calls an undeclared tool or omits a required source identifier is reported as a contract violation rather than passing review, and one that correctly refuses is distinguished from one that failed.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Attested deterministic verification evidence | medium | Verify artifact-provider revision and immutability semantics before defining a new digest format. |
| `verify_change` as an optional gate | low | Confirm Skylos installation, target-language support, and the desired `incomplete` policy in a consuming project. |
| Behavioral contracts for agent tool calls, refusals, and source references | medium | Extension point identified (Improvement 4); resolve the result-taxonomy overlap with #3509 before opening an item. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| — | No pattern assessed in this pass was skipped. |
