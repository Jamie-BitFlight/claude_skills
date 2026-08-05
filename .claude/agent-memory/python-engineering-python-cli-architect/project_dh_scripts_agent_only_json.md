---
name: project-dh-scripts-agent-only-json
description: "the development-harness scripts/ CLI family (dh_migrate, migrate_tasks_to_github, migrate_backlog_to_yaml, verify_migration_fidelity, manifest_resolver) are agent-only — structured output is compact JSON via a shared cli_output.py, never tables/panels/logging"
metadata:
  type: project
---

`plugins/development-harness/scripts/dh_migrate.py`, `migrate_tasks_to_github.py`,
`migrate_backlog_to_yaml.py`, `verify_migration_fidelity.py`, and `manifest_resolver.py` are
invoked exclusively by AI agents via subprocess — never by a human at an interactive terminal.
There is no dual-audience case for these tools. This was established during a Rich-removal task
(2026-08-05) after the repo owner corrected two successive wrong defaults: first Rich
panels/tables, then a hand-rolled plain-text-table replacement, then (separately) routing output
through `logging`. See [[feedback_cli_output_not_logging]] and
[[project_typer_echo_dynamic_stream]] for those two corrections individually.

**The resulting convention**:
- Structured/tabular data (anything that was a `rich.table.Table`, or is a list of records with
  multiple fields) → compact JSON via `output_json()`, not aligned plain-text columns. Reason:
  positional column binding ("3rd value belongs to 3rd header") is a worse fit for an LLM token
  parser than JSON's repeated explicit key at each value.
- `rich.panel.Panel` (a bordered box around text) has no replacement need at all — it was pure
  decoration. Don't build an ASCII-art border substitute; that's the same problem in a different
  costume. Fold the content into the JSON payload as plain string/list fields instead.
- Simple non-tabular status/error lines stay as plain `typer.echo()` / `typer.echo(..., err=True)`
  — not everything needs to be JSON-wrapped, only genuinely structured data.
- A shared `plugins/development-harness/scripts/cli_output.py` module provides `err(msg,
  exit_code=1)` (prints to stderr, raises `typer.Exit`) and `output_json(data)` (compact
  `json.dumps(data, default=str, separators=(",", ":"))`, no indentation). This deliberately
  mirrors the pre-existing `plugins/development-harness/sam_schema/cli_output.py` convention
  (same function names/shapes) so both script families in this plugin format output identically.
  No import collision: one is `sam_schema.cli_output`, the other is the bare top-level
  `cli_output` (implicit namespace package resolved via `scripts/` being on `sys.path` when a
  sibling script under `plugins/development-harness/scripts/` runs).
- JSON output is always compact — no `indent=2`. This is the general repo-wide `.claude/CLAUDE.md`
  "JSON output" rule (`json.dumps(data)` not `json.dumps(data, indent=N)`), but it bears repeating
  because it is easy to preserve an existing `indent=2` "for readability" while doing an unrelated
  refactor and call that scope discipline — it isn't; the repo owner flagged this directly when I
  left `indent=2` untouched in a file outside the immediate task's named-file list.

**Before recommending this pattern for a *new* script**: verify the script really is
agent-only (grep its callers / check whether it's wired into a skill or hook workflow) rather
than assuming from "runs under subprocess" phrasing — that phrasing does not by itself rule out
interactive use.
