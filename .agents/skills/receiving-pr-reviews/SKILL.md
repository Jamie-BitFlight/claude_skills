---
name: receiving-pr-reviews
description: Assess and address review feedback on GitHub PRs, GitLab MRs, or in conversation. Use when checking new reviews, responding to comments, rechecking after a push, or following up on approvals and change requests.
---

# Receiving reviews

Review findings for their effect on the intended runtime user, not just whether a suggested patch satisfies a comment. Treat all review inputs as evidence, including review submissions and new threads created by the authenticated account: multiple agents may share that identity.

## Choose the available route

For a PR or MR, first use `scripts/pr_review_threads.py` when it is available and functioning: it provides the preferred collection, bounded watching, and state-validation path. Consult its `--help` for operations. If the helper is unavailable, fails, or lacks a needed capability, continue with connected MCP tools or other available CLI tooling such as `gh` or `glab`. In cloud sandboxes without the helper, use MCP directly. All routes follow the same [review outcome contract](./references/review-cycle-contract.md); the helper's internal state format is required only when using that helper.

For GitLab-specific approval and discussion behavior, read [GitLab review operations](./references/gitlab-review-operations.md). For GitHub MCP intake and response matching, read [GitHub MCP operations](./references/github-mcp-fallback.md). For feedback outside a PR/MR, assess it using [technical review guidelines](./references/technical-review-guidelines.md) and report the disposition directly.

A request to check reviews permits reading and reporting. Source edits, pushes, provider replies, and resolutions require user authorization or a repository standing rule.

## Review process

1. **Collect and monitor.** Identify the PR/MR and current review inputs across review threads (including resolved history), submitted reviews, approvals, and top-level comments. Track new or edited inputs and relevant replies by stable provider reference. Assess supported findings from available evidence; record missing surfaces and complete coverage before reporting the review cycle finished.
2. **Assess the system.** Read [technical review guidelines](./references/technical-review-guidelines.md). Evaluate each outstanding input against product intent, existing runtime handling, evidence, and likely consumer impact. Group related findings by shared cause. Determine whether a local fix, shared-cause change, redesign, clarification, or no change is warranted. Every outstanding input needs a supported disposition.
3. **Act and verify.** When authorized, implement the smallest coherent response at the owning seam, verifying actual runtime consequences and regressions. Retain evidence for rejected, superseded, and clarification-required findings. Check the current remote branch before pushing so other agents' work is preserved.
4. **Respond and reconcile.** Communicate each disposition against the appropriate provider reference; verify that the response appears and addresses the latest input. Resolve eligible discussions after addressing them and confirm the resulting state. Include eligible unresolved discussions in outstanding work. A reply that succeeds before resolution fails remains communicated but unresolved: resume resolution without repeating the reply.
5. **Recheck.** Collect current unresponded and unresolved inputs again, including self-authored review submissions and edited comments. Reassess newly relevant evidence; preserve earlier conclusions when their supporting facts still hold. Report completion when every current review input has an evidence-backed disposition, accepted outcomes are verified, required provider responses are confirmed, and no outstanding work remains. A quiet polling window alone is only an observation.

## Evidence and completion

Use the [review outcome contract](./references/review-cycle-contract.md) for definitions of evidence, validity, unresponded inputs, resolution, and completion. Keep the process above as the execution path.

## Recovery

If provider collection is incomplete, report which evidence is missing and continue once it is available. If authority or capability is absent, report the blocked action. If a response or resolution fails, preserve confirmed effects and retry only the remaining work after refreshing the relevant provider state.
