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
5. After no open items remain in the source milestone, call `backlog_close_milestone(milestone_number=<requested number>)` (CLI: `backlog close-milestone --milestone-number <requested number>`). Preserve the returned backend result; an unsupported backend remains a stop, never a fallback store.
6. Project V2 Done is a separate GitHub projection. Ask for owner, project number, repository, and exact status value. Resolve `GH_PROJECT_HELPER` to the absolute `github_project_setup.py` path in the loaded `gh` skill without changing the target project's cwd, then run `uv run "$GH_PROJECT_HELPER" project update-status --issue-number <closed issue> --status "<status>" --project-number <project-number> --owner <owner> --repo <repo>` for every applicable issue. Report each result separately from milestone closure.
7. Report the backend, audited counts, every disposition, the close result, and any retained warnings or pending writes.
