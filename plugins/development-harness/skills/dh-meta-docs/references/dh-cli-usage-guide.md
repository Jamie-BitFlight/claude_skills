# DH CLI Usage Guide

Grouped-command reference for the DH CLI adapter (`sam_schema/cli.py`), the validated alternate
transport for structured SAM operations outside an MCP host. Prefix every command below with the
`<sam_cli>` value from `dh-meta-docs`' SKILL.md. Every data-bearing value is a named option;
successful output is compact JSON on stdout and diagnostics are on stderr. `--format` is not
supported. In a Beads workspace, use `bd` directly for Beads-native CRUD, status, dependencies, and
readiness; use this CLI only for structured plans and workflow operations.

```text
plan list
plan read --address Pc7d8e9f0
plan read --address Pc7d8e9f0/T04
plan create --slug my-feature --goal "Route workflow I/O through the DH CLI"
plan update --plan-address Pc7d8e9f0 --context "Background context for all tasks"
plan update --plan-address Pc7d8e9f0 --task-id T04 --append-section "Divergence Notes" --section-content "### DN-1: Brief title"
plan state --address Pc7d8e9f0/T04 --new-status complete
plan claim --address Pc7d8e9f0/T04
plan ready --plan-address Pc7d8e9f0
plan status --plan-address Pc7d8e9f0
plan validate --address Pc7d8e9f0
plan migrate --plan-address tasks-3-integrate-sam-schema.md
active-task set --address Pc7d8e9f0/T04
active-task get
active-task update --set-fields-json '{"priority": 1}'
active-task clear
```

For a task-bearing plan, repeat the validated named options shown by `plan create --help`
(`--task-id`, `--task-title`, `--task-status`, `--task-agent`, `--task-dependency`,
`--task-priority`, and `--task-complexity`). For a large plan, create an empty drafting plan,
append one task at a time with `plan append-task --plan-address ...` and the same named task
fields, then run `plan finalize --plan-address ...`; serialize appends for the same plan.
`plan append-task --stdin` accepts a full YAML task mapping (using `task:` as the identifier key)
on stdin instead of the scalar options — use it when a task needs fields the scalar set omits
(`body`, `description`, `acceptance_criteria`, `verification_steps`, `handoff`, `skills`, etc.);
`--stdin` cannot be combined with the scalar task options.

The structured MCP composites remain MCP-only transport names (`sam_plan`, `sam_task`, and
`sam_active_task`) and are not CLI commands. The CLI exposes their reachable operations under
`plan`, `backlog`, `dispatch`, `artifact`, and `active-task`; consult each group's current `--help`
before invoking a less common leaf.
