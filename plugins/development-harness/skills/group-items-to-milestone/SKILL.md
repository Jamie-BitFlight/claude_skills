---
name: group-items-to-milestone
description: Assign existing configured-backend work items to an open milestone. Use after create-milestone with a milestone number and optional P0/P1/P2 or title filter.
argument-hint: '{milestone-number} [P0|P1|P2|title-filter]'
user-invocable: true
---

# Group Items to Milestone

Resolve the backend with `dh:backend-resolution`. Require a numeric milestone number; do not treat literal unsubstituted `$ARGUMENTS` as input.

1. Call `backlog_list_milestones(state="open")`, then `state="all"` only when needed. Stop if the requested milestone is absent or closed.
2. Call `backlog_list` through the configured backend. Apply the optional priority or title filter to the returned logical items. Keep each item reference, priority, provider issue identifier, and current milestone exactly as returned.
3. Present items with a numeric provider issue identifier for selection. Mark already assigned items. Do not inspect `.claude/backlog`, cache files, or a second provider.
4. For a selected item without an assignable issue identifier, report it as not assignable and direct the user to its normal `dh:work-backlog-item create` lifecycle. Never invent an issue body, Story, Acceptance Criteria, type, or writeback.
5. Ask the user to confirm the exact selected identifiers. For every selected, unassigned numeric issue, call `backlog_assign_item_to_milestone(issue_number=<returned issue>, milestone_number=<requested number>)`. Preserve every warning, pending flag, and error; do not claim failed assignments.
6. Project V2 is an optional GitHub projection, not durable backlog state. Run a project update only after the user supplies explicit owner, project number, repository, and target status. If the active backend lacks the capability, report that result and leave the project unchanged.
7. Report the active backend, assigned references, unchanged assignments, unassignable items, and each provider outcome. Continue with `dh:groom-milestone` only after assignment outcomes are reported.
