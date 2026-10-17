# DH CLI Command Reference

Grouped-command reference for the DH CLI adapter, the validated alternate transport for structured
SAM operations outside an MCP host. Load `dh:dh-cli-usage` and prefix every command below with its
`<sam_cli/>` value. Every data-bearing value is a named option; successful output is compact JSON on
stdout and diagnostics are on stderr. `--format` is not supported. In a Beads workspace, use `bd`
directly for Beads-native CRUD, status, dependencies, and readiness; use this CLI only for structured
plans and workflow operations.

Before executing a dispatched attempt, read
[the runner contract](../../../docs/work-ledger/runner-contract.md) for the complete runner
sequence, including report prerequisites and explicit outcome selection. Before returning or
interpreting a dispatched agent's response, load `dh:subagent-contract` for transport semantics.

```text
plan list
plan read --address Pc7d8e9f0
plan read --address Pc7d8e9f0/T04
plan create --slug my-feature --goal "Route workflow I/O through the DH CLI"
plan update --plan-address Pc7d8e9f0 --context "Background context for all tasks"
plan update --plan-address Pc7d8e9f0 --task-id T04 --append-section "Divergence Notes" --section-content "### DN-1: Brief title"
plan claim --address Pc7d8e9f0/T04
plan ready --plan-address Pc7d8e9f0
plan status --plan-address Pc7d8e9f0
plan validate --address Pc7d8e9f0
plan migrate --plan-address tasks-3-integrate-sam-schema.md
```

```text
backlog create-milestone --title "Release"
backlog list-milestone-members --milestone-number 7
backlog assign-milestone --issue-number 42 --milestone-number 7
backlog assign-milestone --issue-number 42 --clear
backlog close-milestone --milestone-number 7
```

`backlog close-milestone` calls the configured backend's `close_milestone` operation and returns the closed milestone with its title, state, due date, and live member counts. GitHub, SQLite, and Memory implement the integer milestone contract; Beads does not, so its typed milestone-capability refusal is the result rather than a fallback store. Use the returned logical/provider data directly; do not replace it with raw provider or filesystem writes.

`backlog list-milestone-members --milestone-number N` returns every native member the configured provider counts for milestone `N`, including ordinary provider issues without DH sections. Each member contains `issue_number`, `title`, native `OPEN`/`CLOSED` `state`, and `milestone_number`; use this result to reconcile a completion audit rather than deriving totals from `backlog list`.


For a zero-attempt direct completion, append one complete `Direct Completion Record`, read it
back, then move state. The record must include non-empty `TASK:`, `FILES_CHANGED:`, `COMMITS:`,
`REUSE DECISION:`, `VERIFICATION:`, and `NOTES:` fields; `--force` does not bypass this evidence
or attempt-owned report requirements.

```text
plan update --plan-address Pc7d8e9f0 --task-id T04 --append-section "Direct Completion Record" --section-content "TASK: completed directly
FILES_CHANGED: none
COMMITS: none
REUSE DECISION: ADOPT — existing capability
VERIFICATION: none
NOTES: none"
plan read --address Pc7d8e9f0/T04
plan state --address Pc7d8e9f0/T04 --new-status=complete --reason "why this moved without a runner"
```

For a task-bearing plan, repeat the validated named options shown by `plan create --help`
(`--task-id`, `--task-title`, `--task-status`, `--task-agent`, `--task-dependency`,
`--task-priority`, and `--task-complexity`). For a large plan, create an empty drafting plan,
append one task at a time with `plan append-task --plan-address ...` and the same named task
fields, then run `plan finalize --plan-address ...`; serialize appends for the same plan.
`plan append-task --stdin` accepts a full YAML task mapping (using `task:` as the identifier key)
on stdin instead of the scalar options. Use it when a task needs fields the scalar set omits
(`body`, `description`, `acceptance_criteria`, `verification_steps`, `handoff`, `skills`, etc.).
`--stdin` cannot be combined with the scalar task options.

The structured MCP composites remain MCP-only transport names (`sam_plan`, `sam_task`, and
`sam_active_task`) and are not CLI commands. The CLI exposes their reachable operations under
`plan`, `backlog`, `dispatch`, `artifact`, and `active-task`; consult each group's current `--help`
before invoking a less common leaf.

Once `plan import` puts a plan on the work ledger, `sam_plan`'s `read`, `status`, `ready`,
`update`, `append_task`, and `finalize` actions and `sam_task`'s `read`, `state`, and `update`
actions read and write the ledger instead of the plan's original content record. The CLI's `plan`
commands read and write that same store once the plan is imported. `sam_plan`'s `list` and
`sam_task`'s `claim` keep answering from the content record regardless. `append_task`'s
`conflict_group` field mirrors `plan append-task --conflict-group`. `ready`'s `full` flag takes
effect once the ledger holds the plan: `false` returns the routing manifest; `true` returns every
column.
