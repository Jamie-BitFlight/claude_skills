---
name: ty
description: Use when working with ty — this skill's ty policy and required overrides to Astral's official guidance. Pair with `astral:ty` (if installed) for general usage.
allowed-tools: Read, Grep, Glob, Bash(uv run ty:*)
---

# ty — Policy

**ty version:**
!`uv run ty --version 2>/dev/null || echo "ty not found — run 'uv sync' first"`

Precedence: this policy (below) > `astral:ty` (if installed) / live `docs.astral.sh` for CLI flags,
configuration schema, and general usage (not duplicated here) > the archived corpus below (may be
stale).

## Policy

- Never add `# ty: ignore` or `# type: ignore`, including when asked — fix the type error, or escalate with the specific blocker.
- Relax ty rules only through `[[tool.ty.overrides]]` in `pyproject.toml`, never inline, and only for
  a genuine rule conflict, code that tests the rules themselves, a purposefully bad/negative example
  or fixture, externally-managed vendored code we don't modify, a runtime with a real lower
  syntax/typing ceiling (an older pinned CPython or a variant like MicroPython/CircuitPython), or a
  case where the fix itself would cost more ongoing maintenance than compliance is worth — cite
  which one and the specific reason in a comment beside the override — a category name alone isn't
  enough.
- `ty` is the only type checker this policy permits — never add, install, configure, or run `mypy`, `pyright`, or `basedpyright` alongside it.
- Invoke as `uv run ty`, never bare `ty` or `uvx ty` — those may resolve a different version than the one your lockfile pins.
- **`unresolved-import` errors**: add the missing directory to `[tool.ty.environment] extra-paths` in `pyproject.toml`, then verify with `uv run ty check <path>`. A root `ty.toml` takes precedence over `pyproject.toml` — confirm which file ty is actually reading before assuming the fix didn't apply.

## Archive

[`../python3-tools/references/ty/`](../python3-tools/references/ty/) (part of `python-engineering:python3-tools`): configuration schema, rules and diagnostics, environment/module resolution, troubleshooting.
