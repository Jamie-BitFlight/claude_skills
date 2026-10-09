# GitHub MCP review operations

Use this reference when the preferred bundled helper is unavailable, fails, or lacks a needed operation and GitHub MCP is available, including cloud sandboxes where the helper cannot run. The connected tools' schemas own invocation details.

## Intake

Collect the PR identity and current head, submitted reviews, review threads with nested replies and resolved history, top-level PR comments, and relevant approval signals. Follow pagination when the connector exposes it; disclose missing surfaces rather than claiming complete coverage.

Review submissions, new threads, and standalone comments are inputs regardless of whether their author matches the authenticated account. Determine whether an input has been answered from the provider thread or comment relationship and the latest content. An existing response can remain valid across unrelated commits; revisit it when the underlying evidence changes.

## Respond and monitor

Assess related inputs together, then use available MCP actions to post an evidence-backed reply or comment. Confirm the observed response and resolve eligible threads separately. If the reply succeeds but resolution fails, retain that success and retry resolution alone. Check current unresponded and unresolved inputs after actions; use repeated checks when watching for later reviews.

The helper's internal GitHub classification logic in `scripts/pr_review_github_logic.py` applies when running that helper. MCP does not require a canonical Python snapshot, fingerprint, or `ReviewCycleState`. Its outcome is established from the connected provider's observable state and the [shared review outcome contract](./review-cycle-contract.md).
