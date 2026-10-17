---
name: start-milestone
description: Start an open configured-backend milestone after explicit confirmation. Use after items are assigned and groomed; it transitions the selected work items to in-progress and optionally updates an explicitly configured GitHub Project V2 projection.
argument-hint: '{milestone-number}'
user-invocable: true
---

# Start Milestone

Resolve the backend with `dh:backend-resolution`. Require a numeric milestone number; do not treat literal unsubstituted `$ARGUMENTS` as input.

1. Call `backlog_list_milestones(state="open")`; match the requested number. If absent, call it with `state="all"`. Stop when absent or closed. Retain the resolved milestone's returned `title`.
2. Call `backlog_list` through its offset/limit pagination until every applicable page has been consumed. Retain only returned items whose `milestone` equals the resolved milestone title and whose status is not `done` or `closed`. Preserve each logical reference; do not read or write local backlog files.
3. Present the exact selected item references and current statuses. Ask for confirmation before any mutation.
4. For every confirmed item, call `backlog_update(selector=<returned reference>, status="in-progress")`. Preserve any returned warnings, pending state, or error; continue only with successful updates.
5. Project V2 is a separate GitHub projection. Ask for its owner, project number, repository, and exact status value. Resolve `GH_PROJECT_HELPER` to the absolute `github_project_setup.py` path in the loaded `gh` skill without changing the target project's cwd, then run `uv run "$GH_PROJECT_HELPER" project update-status --issue-number <issue> --status "<status>" --project-number <project-number> --owner <owner> --repo <repo>` once for every successfully transitioned numeric GitHub issue. Report each helper result separately from the backend update.
6. Report the backend, milestone, transitioned item references, skipped items, and every backend/projection result.
