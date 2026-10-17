---
name: complete-milestone
description: Audit and close an open configured-backend milestone after explicitly resolving every open item. Use when a release or theme is ready for closure.
argument-hint: '{milestone-number}'
user-invocable: true
---

# Complete Milestone

Resolve the backend with `dh:backend-resolution`. Require a numeric milestone number; do not treat literal unsubstituted `$ARGUMENTS` as input.

1. Resolve the milestone by numeric `number`, using `state="all"` only to report missing/closed state.
2. Exhaust every configured-backend item page with `include_closed=true`; select only entries whose `milestone_number` equals the resolved number. Reconcile that complete set against the milestone's reported open/closed counts before audit, projection, or close. Without MCP, load `dh:dh-cli-usage` and run its absolute `<sam_cli/> backlog list --include-closed` from the target cwd.
3. Present every matching open and closed item. If open items remain, ask the user to carry each to a selected/new milestone, leave it unassigned only where supported, or close it through normal `backlog_close` lifecycle with a valid reason. Do not silently mark incomplete work done or use a raw helper.
4. Assign carried items with `backlog_assign_item_to_milestone` only after the target milestone exists and each assignment is confirmed; without MCP use `<sam_cli/> backlog assign-milestone`. Stop closure on any unresolved disposition or count mismatch.
5. After the complete membership audit contains no open item, call `backlog_close_milestone(milestone_number=<requested number>)` (CLI: `<sam_cli/> backlog close-milestone --milestone-number <requested number>`). Preserve the backend result; unsupported is a stop, never a fallback.
6. Project V2 Done is a separate GitHub projection. Ask for owner, project number, repository, and exact status value; resolve `GH_PROJECT_HELPER` absolutely and retain target cwd before invoking its explicit update-status command for every applicable issue.
7. Report backend, milestone number, complete audit/count reconciliation, every disposition, closure result, and retained warnings/pending writes.
