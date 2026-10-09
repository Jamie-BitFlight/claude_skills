# Review outcome contract

Use when assessing evidence, matching review responses, or determining completion. These meanings apply across the preferred helper, MCP, and other provider tools.

## Evidence and validity

**Evidence** is an inspectable observation with enough context to support or contradict a claim: code, tests, runtime behavior, requirements, history, or provider state. **Validity** concerns whether the claim is supported within its scope; the proposed fix requires a separate judgment about runtime consequences and existing handling.

**Unresponded** means a current review input lacks a relevant provider-observed response to its latest content, regardless of author. **Unresolved** means its provider discussion remains open, even if acknowledged. **Outstanding** means assessment, implementation, verification, clarification, or response work remains.

A submitted review, new thread, or standalone comment is an input even when authored by the authenticated account, because agents may share that identity. A reply inside a thread is a response candidate established by its relationship and content. Preserve relevant resolved history for pattern analysis.

## Evidence-backed disposition

For each current finding, establish a supported change, no-change decision, supersession, or focused clarification. Preserve enough of its provider reference, latest content, disposition, verification, and response evidence to determine outstanding work. Match responses to current content; a recorded attempt alone is insufficient evidence of delivery.

## Completion

A review cycle is complete when every current review input has an evidence-backed disposition, accepted outcomes are verified, required provider responses are observed, and no clarification or other outstanding work remains. Assess supported findings from partial evidence and identify missing surfaces; establish full relevant coverage before reporting completion.

The helper's `validate-projection`, `validate-cycle`, and `complete-cycle` commands validate its own state representation when that route is used. MCP and other transports establish the same observable outcomes through their provider capabilities.
