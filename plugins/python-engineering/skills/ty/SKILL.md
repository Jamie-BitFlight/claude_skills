---
name: ty
description: Use when working with ty. Covers this skill's ty policy and required overrides to Astral's official ty guidance — load alongside the `astral:ty` skill (which teaches ty itself); this skill covers only its own policy additions, not general ty usage.
allowed-tools: Read, Grep, Glob, Bash(uv run ty:*)
---

# ty — Policy

**ty version:**
!`uv run ty --version 2>/dev/null || echo "ty not found — run 'uv sync' first"`

Precedence: this skill's policy (below) > live `docs.astral.sh` / the `astral:ty` skill (tool facts) > the archived corpus linked below (may be stale).

The `astral:ty` skill covers CLI flags, configuration schema, and general usage — not duplicated here.

## Policy

- Never add `# ty: ignore` or `# type: ignore` to source under this policy, including when a user asks for it — fix the type error instead, or escalate with the specific blocker.
- Relax ty rules only through `[[tool.ty.overrides]]` in `pyproject.toml`, never inline, and only for
  a genuine rule conflict, code that tests the rules themselves, a purposefully bad/negative example
  or fixture, externally-managed vendored code we don't modify, a runtime with a real lower
  syntax/typing ceiling (an older pinned CPython or a variant like MicroPython/CircuitPython), or a
  case where the fix itself would cost more ongoing maintenance than compliance is worth — cite
  which one and the specific reason this code can't comply, in a comment beside the override. A
  category name alone is not sufficient justification.
- `ty` is the only type checker this policy permits — never add, install, configure, or run `mypy`, `pyright`, or `basedpyright` alongside it.
- Invoke as `uv run ty`, never bare `ty` or `uvx ty` — those may resolve a different version than the one your lockfile pins.
- **`unresolved-import` errors**: add the missing directory to `[tool.ty.environment] extra-paths` in `pyproject.toml`, then verify with `uv run ty check <path>`. A root `ty.toml` takes precedence over `pyproject.toml` — confirm which file ty is actually reading before assuming the fix didn't apply.

## Archive

[`../python3-tools/references/ty/`](../python3-tools/references/ty/), part of the `python-engineering:python3-tools` skill, holds a generated, possibly-stale snapshot of `docs.astral.sh` — configuration schema, rules and diagnostics, environment/module resolution, troubleshooting. Check `docs.astral.sh` directly if anything there is disputed or looks out of date.
