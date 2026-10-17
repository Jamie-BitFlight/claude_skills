---
name: start-milestone
description: Start an open configured-backend milestone after explicit confirmation. Use after items are assigned and groomed; it transitions the selected work items to in-progress and optionally updates an explicitly configured GitHub Project V2 projection.
argument-hint: '{milestone-number}'
user-invocable: true
---

# Start Milestone

Resolve the backend with `dh:backend-resolution`. Require a numeric milestone number; do not treat literal unsubstituted `$ARGUMENTS` as input.

1. Call `backlog_list_milestones(state="open")`; match the requested number. If absent, call it with `state="all"`. Stop when absent or closed.
2. Call `backlog_list` and retain only returned items whose provider milestone is the selected number and whose status is not `done` or `closed`. Do not read or write local backlog files.
3. Present the exact selected item references and current statuses. Ask for confirmation before any mutation.
4. For every confirmed item, call `backlog_update(selector=<returned reference>, status="in-progress")`. Preserve any returned warnings, pending state, or error; continue only with successful updates.
5. A Project V2 projection is optional. Ask for its owner, project number, repository, and exact configured status value before invoking a project operation. Do not infer any of those values or use defaults. Report a missing or unsupported project capability instead of substituting a second store.
6. Report the backend, milestone, transitioned item references, skipped items, and every provider result.

Do not call the legacy project setup helper for backlog status. The configured backend owns durable item state.
