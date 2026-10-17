---
name: group-items-to-milestone
description: Assign existing configured-backend work items to an open milestone. Use after create-milestone with a milestone number and optional P0/P1/P2 or title filter.
argument-hint: '{milestone-number} [P0|P1|P2|title-filter]'
user-invocable: true
---

# Group Items to Milestone

Resolve the backend with `dh:backend-resolution`. Require a numeric milestone number; do not treat literal unsubstituted `$ARGUMENTS` as input.

1. Resolve the open milestone by returned numeric `number`; use `state="all"` only to report missing/closed state.
2. Exhaust every `backlog_list` page before applying the optional priority/title filter. Preserve each logical reference, provider issue identifier, and `milestone_number`. Without MCP, load `dh:dh-cli-usage` and use its absolute `<sam_cli/> backlog list --include-closed` from the target cwd.
3. Present the complete candidate set. Mark an item assigned only when `milestone_number` equals the requested number; title equality is not identity.
4. A selected existing item without a numeric provider issue is not a new backlog item. Run that item's existing `dh:work-backlog-item work <reference>` route (or report its returned binding failure); never create another backlog record or author an issue body.
5. Ask the user to confirm exact logical references. Assign each bound numeric issue with `backlog_assign_item_to_milestone(issue_number=<returned issue>, milestone_number=<requested number>)`; without MCP use `<sam_cli/> backlog assign-milestone --issue-number <issue> --milestone-number <number>`. Preserve errors and do not claim failed assignments.
6. Project V2 is a separate GitHub projection. Ask for owner, project number, repository, and exact status value. Resolve `GH_PROJECT_HELPER` to the absolute `github_project_setup.py` path in the loaded `gh` skill without changing target cwd, then invoke its explicit update-status command for every successful assignment.
7. Report the active backend, complete candidate/assignment outcomes, bound/unbound existing items, and projection results. Continue with `dh:groom-milestone` only after outcomes are reported.
