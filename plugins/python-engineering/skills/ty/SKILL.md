---
name: ty
description: Use when working with ty in this repository. Covers this repository's ty conventions and required overrides to Astral's official ty guidance — load alongside `/astral:ty` (which teaches ty itself); this skill covers only what is specific to this codebase.
allowed-tools: Read, Grep, Glob, Bash
---

# ty — This Repo's Conventions

**ty version:**
!`uv run ty --version 2>/dev/null || echo "ty not found — run 'uv sync' first"`

Precedence: this repo's policy (below) > live `docs.astral.sh` / the `astral:ty` skill (tool facts) > the archived corpus linked below (may be stale).

Load `/astral:ty` next for CLI flags, configuration schema, and general usage — it is not duplicated here.

## Repo-specific policy

- Never add `# ty: ignore` or `# type: ignore` to source in this repository, including when a user asks for it — fix the type error instead, or escalate with the specific blocker.
- Relax ty rules only through `[[tool.ty.overrides]]` in `pyproject.toml`, never inline, and only for a case matching one of the acceptable-exception categories in `.claude/rules/linting-exceptions.md` (cite the category in a comment beside the override).
- `ty` is the only type checker that gates CI here — never add, install, configure, or run `mypy`, `pyright`, or `basedpyright`.
- Invoke as `uv run ty`, never bare `ty` or `uvx ty` — those resolve a different version than the one CI gates against.
- **`unresolved-import` errors**: add the missing directory to `[tool.ty.environment] extra-paths` in `pyproject.toml`, then verify with `uv run ty check <path>`. A root `ty.toml` takes precedence over `pyproject.toml` — confirm which file ty is actually reading before assuming the fix didn't apply.

Full conflict table (ty rows C1, C5, C7): `.claude/rules/astral-tool-overrides.md`.

## Archive

`python3-tools/references/ty/` (load via `Skill(skill="python-engineering:python3-tools")`) holds a generated, possibly-stale snapshot of `docs.astral.sh` — configuration schema, rules and diagnostics, environment/module resolution, troubleshooting. Check `docs.astral.sh` directly if anything there is disputed or looks out of date.
