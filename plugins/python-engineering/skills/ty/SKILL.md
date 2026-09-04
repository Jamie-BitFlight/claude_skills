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
- **`unresolved-import` in a PEP 723 standalone script** (a `# /// script ... ///` header importing a sibling module): the project's `pyproject.toml` does not apply here — a script with inline metadata has no first-party roots by default. Set `root`, not `extra-paths` — `extra-paths` is documented for third-party/non-conventionally-installed paths, not for granting first-party roots, and ty's own docs name this exact PEP 723 case for `root`.
  ```python
  #!/usr/bin/env -S uv run --quiet --script
  # /// script
  # requires-python = ">=3.11"
  #
  # [tool.ty.environment]
  # root = ["."]
  # ///
  ```
  CONSTRAINT: `root` replaces ty's default root auto-detection entirely — it does not add to it. Always include `"."` (the script's own directory) in the list, even when the sibling module you need lives elsewhere, or the script loses its own PEP-723-isolated-environment context and its declared inline dependencies stop resolving too (`root = [".."]` alone breaks `pydantic`/`typer` resolution for a script one directory away from the package it imports; `root = [".", ".."]` resolves both). Verify with `uv run ty check <script>.py` against the script file directly, not the project root — and if the script declares PEP 723 dependencies, confirm those still resolve after adding `root`, not just the sibling import.
