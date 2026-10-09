# Review outcome contract

Use when assessing evidence, matching review responses, or determining completion. These meanings apply across the preferred helper, MCP, and other provider tools.

## Evidence, validity, and decisions

**Evidence** is an inspectable observation with enough context to support or contradict a claim: code, tests, runtime behavior, requirements, history, or provider state. **Finding validity** concerns whether the observation is supported within its scope. **Solution suitability** concerns whether the proposed change improves the intended consumer's experience, considering existing handling and side effects. A valid finding can warrant a different fix or no change.

**Finding addressed** means a disposition has supporting evidence and any accepted change has been verified. **Thread resolved** is the provider's discussion state, which can differ from whether the finding was addressed. **PR readiness** includes repository gates such as CI and is distinct from completion of review handling.

**Unresponded** means a current review input lacks a relevant provider-observed response to its latest content, regardless of author. **Unresolved** means its provider discussion remains open, even if acknowledged. **Outstanding** means assessment, implementation, verification, clarification, response, or eligible resolution work remains.

A submitted review or new thread is inbound even when authored by the authenticated account, because agents may share that identity. A standalone comment introducing new feedback is inbound; an authenticated top-level comment referencing an existing review is an outbound response candidate. Thread replies are response candidates established by their relationship and content. Preserve relevant resolved history for pattern analysis.

## Evidence-backed disposition

**Additional verification** is useful when it can settle a specific uncertainty relevant to the disposition. Existing evidence can be sufficient; requesting another artifact or check is itself a proposal to assess, rather than an automatic prerequisite.

For each current finding, establish a supported change, no-change decision, supersession, or focused clarification. Keep clarification questions open until answered and reassessed. Preserve enough of its provider reference, latest content, disposition, verification, and response evidence to determine outstanding work. Match responses to current content; a recorded attempt alone is insufficient evidence of delivery. Confirmed effects remain attributable to their individual inputs. When another input changes, reassess decisions affected by that change while retaining still-valid evidence and completed actions for the others.

## Completion

**Review-cycle completion** means all current review inputs have supported dispositions, observed required responses, and appropriate discussion states. It does not assert PR merge readiness. An unresolved clarification keeps review work open; a provider discussion without a resolution capability can be reported as unavailable rather than treated as an unperformed fix.

Assess supported findings from partial evidence and identify missing surfaces; establish full relevant coverage and confirm eligible discussions are resolved before reporting completion.

**Preferred transport** is the bundled helper because it automates intake and cross-referencing; **required outcome** is the review evidence and completion contract, independent of transport. When using the helper, include each inbound input in exactly one shared-cause or singleton cluster. The helper's `validate-projection`, `validate-cycle`, and `complete-cycle` commands validate its own state representation when that route is used. MCP and other transports establish the same observable outcomes through their provider capabilities.
