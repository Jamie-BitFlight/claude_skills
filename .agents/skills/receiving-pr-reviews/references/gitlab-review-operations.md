# GitLab review operations

Read for GitLab MRs. Use available `glab` or connected provider tools according to their own invocation contracts.

Bind the MR IID to its project and host. Collect discussions, notes, approvals, award signals, diff versions, and resolved history as supported. When target identity or required evidence is ambiguous, report the missing fact.

System notes are provider metadata; named approvers and explicit review signals are inputs. A zero-required approval configuration does not establish that an actor approved. GitLab has no established equivalent to GitHub's Codex-specific approval convention.

Use stable discussion references when replying. Confirm the reply before resolving a discussion, and confirm resolution separately. For top-level feedback, use the available MR note operation. When a discussion cannot be resolved, record that limitation and retain the confirmed communication. Refresh current review inputs after actions and apply the [shared review outcome contract](./review-cycle-contract.md).

Provider documentation: [glab API](https://docs.gitlab.com/cli/api/), [discussions](https://docs.gitlab.com/api/discussions/), [notes](https://docs.gitlab.com/api/notes/), [approvals](https://docs.gitlab.com/api/merge_request_approvals/).
