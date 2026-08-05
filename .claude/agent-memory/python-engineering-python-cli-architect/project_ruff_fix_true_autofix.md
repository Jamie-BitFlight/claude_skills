---
name: project-ruff-fix-true-autofix
description: "this repo's pyproject.toml sets [tool.ruff] fix = true, so plain `ruff check` (no --fix flag) auto-modifies files in place — expect and re-Read after running it"
metadata:
  type: project
---

`claude_skills/pyproject.toml` has `[tool.ruff] fix = true`. This means a bare `uv run ruff check
<file>` auto-applies safe fixes (mainly import sorting/grouping) and reports `"N fixed"` in its
output — it is not read-only the way `ruff check` is in repos without that setting.

**How to apply**: after running `ruff check` on a file you're mid-edit on, re-`Read` it before
your next `Edit` call — the harness will also surface a system-reminder noting the file changed
on disk, but don't rely solely on that; if you already have stale content in context and try an
`Edit` against it, the old_string may no longer match. Observed repeatedly during the
development-harness Rich-removal task (2026-08-05): ruff moved a newly-added
`from cli_output import ...` line into its own import paragraph (isort classified the sibling
`scripts/` module as first-party/local, separated by a blank line from `typer`/`ruamel.yaml`)
without being asked to `--fix`.
