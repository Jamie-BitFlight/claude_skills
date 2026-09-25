# Improvement Proposals: Skylos

**Research entry**: ./research/code-auditing/skylos.md
**Generated**: 2026-09-13
**Backlog items opened**: #3509

---

<!-- removed-skill-citations -->
> **Superseded citations:** `plugins/development-harness/templates/language-manifest-template.md` and `plugins/development-harness/skills/dh-meta-docs/references/language-manifest-schema.md`, Improvement 3's entire Local system, were deleted in commit `aee7ce482` (#3427, 2026-09-16). The `.dh/language-manifest.yaml` format they documented is retired, and the retirement is now enforced: `plugins/development-harness/tests/test_retired_terms.py` fails if the term reappears in any runtime-read plugin file. Roles and quality gates resolve through `mcp__plugin_dh_backlog__profile_list()` and repository discovery instead. There is no successor gate-contract document, so Improvement 3 is superseded rather than repointed — see the note under its own heading.

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

> **Superseded — do not action.** This proposal extends a gate contract that no longer exists. Both files named in its Local system were deleted in `aee7ce482` (#3427) and the `.dh/language-manifest.yaml` format is a retired term enforced by `plugins/development-harness/tests/test_retired_terms.py`. A third-party source-verifier gate would now have to be expressed against `profile_list()` and repository discovery; whether it can be is an open question, not a described change. The dead paths below are left as the record of what was analysed.

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

## Improvement 4: Make agent tool calls, refusals, and source references checkable against a declared contract

**Source pattern**: Agent behavior contracts can require or forbid tool calls, constrain an exact tool sequence and call count, require response substrings and source IDs, and require an explicit refusal. (Key Features → Agent verification and behavior testing)
**Local system**: `plugins/development-harness/skills/review-verdict-contract/references/verdict-schema.md`; `plugins/development-harness/skills/subagent-contract/SKILL.md`; `plugins/development-harness/skills/dispatch-contract/SKILL.md`
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred — the gap is real and the carrier for two of the three axes is identified, but two questions precede an item. First, the refusal axis needs an observed-response contract that has no local precedent at all, so it is a larger piece of work than extending `verdict-schema.md` and should not be bundled with the other two. Second, whether the result taxonomy this needs is the same one #3509 introduces at Stage 7 — settle that overlap first, since splitting it produces two competing taxonomies.

### Current state

Skylos's three behavior-contract axes are unevenly covered here. Two have local precedents, declared in separate places and none executable as a scenario; the third has none. Refusal in Skylos's sense — an agent declining a prohibited request in its own response — has no local precedent at all. The two nearest constructs are orchestration statuses about whether work ran, not about what an agent answered: `verdict-schema.md` §2.3 selects `SKIP` when "none of the changed files matches the UI file pattern list", which marks a perspective inapplicable, and `subagent-contract/SKILL.md` says to "Return BLOCKED when a required input is missing, rather than inferring it." Neither can express "this input should have been refused, and was", so this axis needs an observed-behavior contract rather than an extension of the verdict schema. Source references appear as `verdict-schema.md`'s conservation invariant and its check that a finding's description appear "verbatim in some `entries[].descriptions`", which exists to catch a synthesizer altering attributions. Tool calls appear as `dispatch-contract/SKILL.md`'s prose rule that a dispatched specialist's "declared tools reach every operation handed over", and as `subagent-contract/SKILL.md`'s "Report every command you ran with its outcome." The first is a selection-time rule and the second a reporting duty; neither is a post-hoc check that the agent called only what it was scoped to.

### Target state

The tool-call and source-reference axes are declared in one place and checked after a run rather than reviewed as prose. `verdict-schema.md` is the candidate carrier for those two: it already holds the source-reference conservation checks and already invites extension ("Future perspectives may define additional SKIP detection rules using the same pattern-list structure in this file"). The refusal axis needs a different vehicle — a contract over an agent's observed response, which no local artifact currently models — so it is scoped separately rather than forced into a verdict block that describes whether a review ran.

### Measurable signal

A contract declares required and forbidden tool calls and required source identifiers for at least one dispatched `dh:` agent, and a run that calls an undeclared tool or omits a required source identifier is reported as a contract violation rather than passing review. Separately, for the refusal axis: a recorded agent response that should have declined a prohibited request is distinguished from one that failed the task, by a check over the response itself rather than by its `STATUS` line.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Attested deterministic verification evidence | medium | Verify artifact-provider revision and immutability semantics before defining a new digest format. |
| `verify_change` as an optional gate | low | Confirm Skylos installation, target-language support, and the desired `incomplete` policy in a consuming project. |
| Behavioral contracts for agent tool calls, refusals, and source references | medium | Carrier identified for the tool-call and source-reference axes (Improvement 4); the refusal axis has no local precedent and needs separate scoping, and the result-taxonomy overlap with #3509 must be resolved first. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| — | No pattern assessed in this pass was skipped. |
