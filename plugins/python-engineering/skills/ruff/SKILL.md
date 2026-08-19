---
name: ruff
description: Use when working with ruff in this repository. Covers this repository's ruff conventions and required overrides to Astral's official ruff guidance — load alongside `/astral:ruff` (which teaches ruff itself); this skill covers only what is specific to this codebase.
allowed-tools: Read
---

# ruff — This Repo's Conventions

Precedence: this repo's policy (below) > live `docs.astral.sh` / the `astral:ruff` skill (tool facts) > `.claude/rules/linting-exceptions.md` for the full exception policy.

Load `/astral:ruff` next for command syntax and general usage — it is not duplicated here.

## Repo-specific policy

- Never pass `--ignore` to `ruff check` to make CI pass, and never suppress `BLE001`, `D103`, or `TRY300` by any mechanism. A `# noqa` requires explicit user approval first. Config-level per-file exclusions in `pyproject.toml` remain the approved mechanism — see the categories in `.claude/rules/linting-exceptions.md`.
- `--unsafe-fixes` is permitted only with `--diff` reviewed before applying.
- Format every Python file you touch — `ruff-format` is both a prek hook and an `--all-files` CI gate here, so skipping unformatted files (Astral's default advice) fails the build instead of keeping the diff clean.
- Invoke as `uv run ruff`, never bare `ruff` or `uvx ruff` — those resolve a different version than the one CI gates against.

Full conflict table (ruff rows C2, C3): `.claude/rules/astral-tool-overrides.md`.
