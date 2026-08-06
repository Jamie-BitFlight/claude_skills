# Beads and development-harness usage

This guide shows the intended boundary between Beads-native work management and the development-harness workflow operations.

## Rule of thumb

Use **`bd` directly** for work that Beads already models well. Use the **development-harness CLI or MCP operations** for structured workflow state, plans, dispatch, and evidence that Beads does not provide. The development-harness CLI is not a proxy for the `bd` CLI.

## Side-by-side workflow

The left column is the Beads-native source of truth. The right column adds the structured workflow layer only where it provides capability beyond Beads.

| Step | Beads-native operation (`bd`) | Structured workflow operation (CLI/MCP) |
|---|---|---|
| Detect the project | `test -f .beads/dh-backend && bd status --json` | No CLI proxy is needed. Select the configured Beads backend when the project is Beads-backed. |
| Create the objective | `bd create --title "..." --type epic --priority 1 --json` | Use `plan create` only when a structured SAM plan is required in addition to the Beads epic. Record both logical addresses. |
| Add work items | `bd create --title "..." --parent <epic-id> --json` | Use `plan append-task` when the task needs typed SAM fields, acceptance criteria, handoff, or verification data. |
| Set dependencies | `bd dep add <blocked-id> <blocking-id>` | No proxy is needed. The workflow records the Beads IDs and may use structured task addresses for downstream handoffs. |
| Find executable work | `bd ready --parent <epic-id> --json` | Use `plan ready` only when readiness must include structured plan/task rules beyond Beads' dependency graph. |
| Inspect an issue | `bd show <id> --json` | Use `backlog view` or the configured MCP operation when a provider-neutral logical view is required. |
| Update status | `bd update <id> --status in_progress` | Use `plan state` or `active-task` when the change is workflow execution state rather than the Beads issue state. Reconcile both when both are changed. |
| Record research or design | `bd update <id> --notes "..."` or native Beads metadata | Use `artifact register` for durable evidence that must be addressed, retrieved, or handed to another agent. Link the artifact from the Beads issue. |
| Dispatch work | Beads stores the objective, task, and dependency graph; it does not dispatch an agent. | Use `dispatch` operations and the task-worker skill for delegation, role, skills, toolsets, and handoffs. |
| Validate implementation | Beads can track the task and status. | Use `plan validate`, repository tests, and artifact registration for acceptance evidence. |
| Complete work | `bd close <id> --reason "..."` | Use `plan finalize` or the completion workflow to record evidence and follow-ups before closing the Beads item. |
| Reopen or follow up | `bd update <id> --status open` or create a follow-up issue | Use the follow-up workflow and record the new Beads ID in the completion handoff. |

## Example

```bash
# Beads owns the graph and executable-work query.
epic_id="$(bd create --title "Improve parser" --type epic --json | jq -r .id)"
task_a="$(bd create --title "Capture failure cases" --parent "$epic_id" --json | jq -r .id)"
task_b="$(bd create --title "Implement parser fix" --parent "$epic_id" --json | jq -r .id)"
bd dep add "$task_b" "$task_a"
bd ready --parent "$epic_id" --json
```

Then use the structured workflow surface for the parts Beads does not provide:

```bash
plan create \
  --slug parser-fix \
  --goal "Improve parser" \
  --context "Beads epic: $epic_id"

 artifact register \
  --item-id "$task_a" \
  --artifact-type research \
  --artifact-id findings-20260730 \
  --content "$(<findings.md)"

 plan validate \
  --address parser-fix
```

The exact CLI options must follow the validated command help for the checkout in use. The important contract is the boundary: do not recreate Beads issue/dependency commands as CLI wrappers.

## Handoff requirements

Every workflow handoff should preserve:

- Beads objective/task IDs;
- structured plan/task addresses, when created;
- artifact handles for research, plans, validation, and review;
- dependency and readiness decisions;
- final Beads status and closure reason.

Beads is the source of truth for Beads-native issue state. Structured workflow artifacts are the source of truth for evidence and workflow state that Beads does not model.

## Related documentation

- [`backend-providers.md`](backend-providers.md)
- [`TASK_FILE_FORMAT.md`](TASK_FILE_FORMAT.md)
- [`.hermes/plans/reference/cli-redesign-implementation-plan.md`](../../../.hermes/plans/reference/cli-redesign-implementation-plan.md)
