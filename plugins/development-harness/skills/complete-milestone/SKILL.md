---
name: complete-milestone
description: Audit and close an open configured-backend milestone after explicitly resolving every open item. Use when a release or theme is ready for closure.
argument-hint: '{milestone-number}'
user-invocable: true
---

# Complete Milestone

Resolve the backend with `dh:backend-resolution`. Require a numeric milestone number; do not treat literal unsubstituted `$ARGUMENTS` as input.

1. Resolve the milestone with `backlog_list_milestones(state="open")`, falling back to `state="all"` only to report an already closed or missing milestone.
2. Obtain its open and closed items from the configured backend. Present their exact references, provider identifiers, statuses, and backend warnings.
3. If open items remain, ask the user to choose one operation for each: carry it to an explicitly selected open or newly created milestone, leave it unassigned when the backend supports that operation, or close it through the normal `backlog_close` lifecycle with a valid user-provided reason. Do not silently mark incomplete work done and do not invoke a raw helper that bypasses lifecycle records.
4. Assign carried items with `backlog_assign_item_to_milestone` only after the target milestone exists and each assignment is confirmed. Preserve per-item failures and stop closure if any required disposition is unresolved.
5. After no open items remain in the source milestone, close it through the active backend's supported milestone operation. If that capability is unavailable, report the backend error and do not emulate closure with local files or a second provider.
6. A Project V2 Done update is optional and requires explicit owner, project number, repository, and status configuration. Report its provider result separately; it never substitutes for milestone or backlog closure.
7. Report the backend, audited counts, every disposition, the close result, and any retained warnings or pending writes.
