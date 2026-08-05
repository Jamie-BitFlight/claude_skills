---
name: project-sam-plan-cli-stdin-removal
description: sam_schema/sam_plan.py — plan create deliberately rejects --stdin/--task-json (tested); plan append-task --stdin is the sanctioned structured-input restore point
metadata:
  type: project
---

`plugins/development-harness/sam_schema/sam_plan.py`'s modular CLI migration (PR #2781,
commit `59fd8420`) intentionally removed the old monolithic `sam create --stdin` /
`--task-json` raw-YAML/JSON ingestion path from `plan create` in favor of named typed
scalar options only (PR summary: "enforce named typed options and compact JSON stdout").
`tests_sam/test_cli_create.py::test_create_rejects_removed_ingestion_flags` is a
parametrized regression test (`["--stdin", "--task-json"]`) asserting `plan create` still
rejects both flags — do not "restore" `--stdin` on `plan create` even if a stale doc or
review comment says it "used to work there." That test is deliberate architecture, not an
oversight.

**Why:** A PR #2781 Codex review comment asked for `plan create --stdin` to be restored
because `plugins/python3-development/agents/code-reviewer.md` still referenced the old
flag and a nonexistent MCP tool `mcp__plugin_dh_sam__sam_create(tasks_yaml=...)` (the real
MCP tool is the consolidated `sam_plan` with `config.action="create"` — no `sam_create`
tool exists post-migration). Restoring `--stdin` on `create` would silently contradict the
migration's own architecture decision and its passing regression test.

**How to apply:** When asked to add back structured/bulk task input, add a `--stdin` (full
YAML task mapping, `task:` as the identifier key per `TaskId`/`TaskDefinition` alias) to
`plan append-task` instead — that command's own removed-flags test only forbids
`--task-json`, not `--stdin`, so it's the correct restore point. Pair `plan create`
(metadata-only, empty `tasks=[]`, starts in `state="drafting"`) → `plan append-task
--plan-address <id> --stdin` (repeat per task) → `plan finalize --plan-address <id>` — this
is the same three-step "large plan" workflow already documented in
`plugins/development-harness/AGENTS.md` under "Gotcha — Large plans must use the
incremental append workflow" and in `docs/TASK_FILE_FORMAT.md`'s "DH CLI Usage Guide".
Validate the stdin payload through `TaskDefinition.model_validate(...)` (has
`extra="forbid"`) — this is stricter than the old raw-dict `Task.model_validate` path,
which silently dropped unknown top-level keys (e.g. a historical `scope:` field that was
never a real `Task`/`TaskDefinition` field, even before the migration).

Canonical invocation prefix used throughout `docs/TASK_FILE_FORMAT.md`:
`uv run plugins/development-harness/sam_schema/cli.py` — not a bare `sam` console script
(the plugin's own `pyproject.toml` console-script entry is a pre-existing, unverified
artifact; don't rely on `uv run sam` resolving).

See also [[feedback-sam-task-create-hits-live-github]].
