---
name: start-milestone
description: Start an open configured-backend milestone after explicit confirmation. Use after items are assigned and groomed; it transitions the selected work items to in-progress and optionally updates an explicitly configured GitHub Project V2 projection.
argument-hint: '{milestone-number}'
user-invocable: true
---

# Start Milestone

Resolve the backend with `dh:backend-resolution`. Require a numeric milestone number; do not treat literal unsubstituted `$ARGUMENTS` as input.

1. Resolve the requested milestone by its returned numeric `number`; retain both its number and title. Do not identify members by title because titles may be duplicated.
2. With MCP, exhaust `backlog_list(include_closed=true)` offset/limit pages. Select only entries whose string `milestone_number` equals the resolved number string. Retain full membership for audit, but derive transitions/projections only from entries whose native `state` is not `CLOSED` and whose workflow status is not terminal. Without the DH MCP, load `dh:dh-cli-usage`, resolve its absolute `<sam_cli/>` path while retaining target cwd, and run `backlog list --include-closed`; use its complete configured-backend result and the same identity/lifecycle fields. Stop with the reported prerequisite/error if neither transport is available.
3. Present exact membership and the nonterminal transition subset. Ask for confirmation before any mutation.
4. For every confirmed transition-subset item, call `backlog_update(selector=<returned reference>, status="in-progress")`; without MCP use `<sam_cli/> backlog update --selector <reference> --status in-progress`. Preserve every returned warning, pending state, or error.
5. Project V2 is a separate GitHub projection. Ask for its owner, project number, repository, and exact status value. Resolve `GH_PROJECT_HELPER` to the absolute `github_project_setup.py` path in the loaded `gh` skill without changing the target project's cwd, then run `uv run "$GH_PROJECT_HELPER" project update-status --issue-number <issue> --status "<status>" --project-number <project-number> --owner <owner> --repo <repo>` once for every successfully transitioned numeric GitHub issue. Report each helper result separately from the backend update.
6. Report the backend, milestone number, transitioned item references, skipped items, and every backend/projection result.
