---
name: ty
description: Use when working with ty — this skill's ty policy and required overrides to Astral's official guidance. Pair with `astral:ty` (if installed) for general usage.
allowed-tools: Read, Grep, Glob, Bash(uv run ty:*)
---

# ty — Policy

**ty version:**
!`uv run ty --version 2>/dev/null || echo "ty not found — run 'uv sync' first"`

Precedence: this policy (below) > `astral:ty` (if installed) / live `docs.astral.sh` for CLI flags,
configuration schema, and general usage (not duplicated here).

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
- **`unresolved-import` in a PEP 723 standalone script** (a `# /// script ... ///` header importing a sibling module): the repo's `pyproject.toml` does not apply here — ty treats the script as its own isolated project. Put `extra-paths` inside the script's own metadata block instead:
  ```python
  #!/usr/bin/env -S uv run --quiet --script
  # /// script
  # requires-python = ">=3.11"
  #
  # [tool.ty.environment]
  # extra-paths = ["."]
  # ///
  ```
  Working examples in this repo: `scripts/validate_codex_plugin_isolated.py`, `plugins/development-harness/sam_schema/cli.py` (accessed 2026-09-04). Verify with `uv run ty check <script>.py` against the script file directly, not the repo root.
