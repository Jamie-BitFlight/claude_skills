---
name: ruff
description: Use when working with ruff. Covers this skill's ruff policy and required overrides to Astral's official ruff guidance — load alongside the `astral:ruff` skill (which teaches ruff itself); this skill covers only its own policy additions, not general ruff usage.
allowed-tools: Read, Bash(uv run ruff:*)
---

# ruff — Policy

Precedence: this skill's policy (below) > live `docs.astral.sh` / the `astral:ruff` skill (tool facts).

The `astral:ruff` skill covers command syntax and general usage — not duplicated here.

## Policy

- Never pass `--ignore` to `ruff check` to make CI pass, and never suppress `BLE001`, `D103`, or `TRY300` by any mechanism — not even the config-level exclusions below. A `# noqa` requires explicit user approval first. For other codes, config-level per-file exclusions in `pyproject.toml` remain the approved mechanism, limited to a genuine rule conflict, code that tests the rules themselves, a purposefully bad/negative example or fixture, externally-managed vendored code we don't modify, a runtime with a real lower syntax/typing ceiling (an older pinned CPython or a variant like MicroPython/CircuitPython), or a case where the fix itself would cost more ongoing maintenance than compliance is worth — each needs the specific reason this code can't comply, not just the category name.
- `--unsafe-fixes` is permitted only with `--diff` reviewed before applying.
- Format every Python file you touch in full — do not adopt Astral's default advice to skip unformatted files; a project gating on `ruff format --check --all-files` will fail the build otherwise.
- Invoke as `uv run ruff`, never bare `ruff` or `uvx ruff` — those may resolve a different version than the one your lockfile pins.
