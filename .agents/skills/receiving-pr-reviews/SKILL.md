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

1. **Collect and monitor.** Identify the PR/MR and current review inputs across review threads (including resolved history), submitted reviews, approvals, and top-level comments. Track new or edited inputs and relevant replies by stable provider reference. The working view is sufficient when all available relevant surfaces have been checked and gaps are disclosed.
2. **Assess the system.** Read [technical review guidelines](./references/technical-review-guidelines.md). Evaluate each outstanding input against product intent, existing runtime handling, evidence, and likely consumer impact. Group related findings by shared cause. Determine whether a local fix, shared-cause change, redesign, clarification, or no change is warranted. Every outstanding input needs a supported disposition.
3. **Act and verify.** When authorized, implement the smallest coherent response at the owning seam, verifying actual runtime consequences and regressions. Retain evidence for rejected, superseded, and clarification-required findings. Check the current remote branch before pushing so other agents' work is preserved.
4. **Respond and reconcile.** Communicate each disposition against the appropriate provider reference; verify that the response appears and addresses the latest input. Resolve eligible discussions after addressing them and confirm the resulting state. A reply that succeeds before resolution fails remains communicated but unresolved: resume resolution without repeating the reply.
5. **Recheck.** Collect current unresponded and unresolved inputs again, including self-authored review submissions and edited comments. Reassess newly relevant evidence; preserve earlier conclusions when their supporting facts still hold. Report completion when no outstanding work remains and accepted outcomes are verified. A quiet polling window alone is only an observation.

## Working definitions

- **Evidence:** inspectable code, tests, runtime behavior, requirements, history, or provider observations relevant to a claim.
- **Valid finding:** a claim supported within its stated scope; the suggested fix is assessed separately.
- **Runtime consequence:** the current or proposed effect on the intended consumer, including reliability, usability, cost, and maintenance.
- **Unresponded:** a review input without a relevant, provider-observed response to its latest content, regardless of author identity.
- **Unresolved:** a provider discussion still open; it may already have a response.
- **Outstanding:** work still requiring assessment, implementation, verification, clarification, or response. Completion concerns outstanding work, not just thread flags.

## Recovery

If provider collection is incomplete, report which evidence is missing and continue once it is available. If authority or capability is absent, report the blocked action. If a response or resolution fails, preserve confirmed effects and retry only the remaining work after refreshing the relevant provider state.
