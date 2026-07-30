---
name: beads-workflow
description: Use when a project is backed by Beads; use bd directly for issue graph operations and the development-harness CLI only for workflow operations Beads does not provide.
---

# Beads workflow

Use Beads' `bd` CLI as the source of truth for Beads-native backlog and dependency operations. Do not proxy ordinary `bd` commands through the development-harness CLI.

## Detect the backend

Confirm the project is Beads-backed before using this skill:

```bash
test -d .beads && bd status --json
```

If `.beads` is absent or `bd status` fails, stop and use the configured backend workflow instead.

## Routing rule

| Need | Use |
|---|---|
| Create, inspect, update, close, or list Beads issues | `bd` |
| Add or inspect dependency edges | `bd dep add`, `bd dep list` |
| Find executable work | `bd ready --json` |
| Store or inspect Beads-native notes, labels, or metadata | `bd` |
| Create or validate SAM plans and workflow artifacts | Development-harness CLI or MCP operation |
| Register/read/migrate workflow artifacts | Development-harness CLI or MCP operation |
| Dispatch, validate, or complete a structured workflow step | Development-harness CLI or MCP operation |

Use one source of truth for each operation. Do not create a second issue through the CLI after creating it with `bd`.

## Required durable handoffs

When `bd` creates or changes work, record the Beads ID in the relevant plan, task, or artifact handoff. When a workflow operation creates a plan or artifact, record its logical address back on the Beads issue using the native notes/metadata facilities.

Prefer machine-readable output:

```bash
bd show <beads-id> --json
bd ready --json
bd dep list <beads-id> --json
```

Keep diagnostics separate from data when invoking the development-harness CLI: compact JSON belongs on stdout and warnings/errors belong on stderr.

## Workflow sequence

1. Use `bd` to create or locate the objective and task graph.
2. Use `bd dep add` for blocking relationships and `bd ready --json` to select executable work.
3. Use the development-harness plan/dispatch/artifact operations for structured workflow state and evidence that `bd` does not model.
4. Execute the task using the task-worker workflow and durable artifacts.
5. Update Beads status with `bd update` or `bd close`.
6. Reconcile the Beads ID, plan address, task address, and artifact handles in the final handoff.

Do not use `bd remember` as a replacement for durable workflow artifacts; reserve it for indexes or short-lived context where the provider adapter explicitly requires it.

## Capability boundary

Beads-native usage is valid even when the optional provider adapter is unavailable. The adapter exists for structured programmatic consumers such as MCP, task workers, and provider-conformance tests; it is not a requirement for agents that can invoke `bd` directly.

If a required operation is not covered by either `bd` or the provider-neutral workflow operations, stop and report the missing capability instead of inventing a proxy command.
