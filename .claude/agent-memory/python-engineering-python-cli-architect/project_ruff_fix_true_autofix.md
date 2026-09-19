---
name: project-ruff-fix-true-autofix
description: "`ruff check` rewrites files in this repo (pyproject sets fix = true); use --no-fix for a read-only lint"
metadata:
  type: project
---

The root `pyproject.toml` `[tool.ruff]` sets `fix = true` and `unsafe-fixes = true`, so a bare
`uv run ruff check <path>` writes safe and unsafe fixes in place.

When you lint files you are auditing or that another agent owns, run
`uv run ruff check --no-fix <path>` so the check stays read-only.
