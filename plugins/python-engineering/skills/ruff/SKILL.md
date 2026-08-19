---
name: ruff
description: Use when working with ruff — this skill's ruff policy and required overrides to Astral's official guidance. Pair with `astral:ruff` (if installed) for general usage.
allowed-tools: Read, Bash(uv run ruff:*)
---

# ruff — Policy

Precedence: this policy (below) > `astral:ruff` (if installed) / live `docs.astral.sh` for command
syntax and general usage (not duplicated here).

## Policy

- Never pass `--ignore` to `ruff check` to make CI pass, and never suppress `BLE001`, `D103`, or `TRY300` by any mechanism — not even the config exclusions below. A `# noqa` requires explicit user approval first. Other codes may use per-file config exclusions in `pyproject.toml`, limited to a genuine rule conflict, code that tests the rules themselves, a purposefully bad/negative example or fixture, externally-managed vendored code we don't modify, a runtime with a real lower syntax/typing ceiling (an older pinned CPython or a variant like MicroPython/CircuitPython), or a case where the fix would cost more upkeep than compliance is worth — each needs the specific reason, not just the category name.
- `--unsafe-fixes` is permitted only with `--diff` reviewed before applying.
- Format every Python file you touch in full — do not adopt Astral's default advice to skip unformatted files; a project gating on `ruff format --check --all-files` will fail the build otherwise.
- Invoke as `uv run ruff`, never bare `ruff` or `uvx ruff` — those may resolve a different version than the one your lockfile pins.

## Archive

[`../python3-tools/references/ruff/README.md`](../python3-tools/references/ruff/README.md) (part of `python-engineering:python3-tools`) — index into a full mirror of `astral-sh/ruff`'s `docs/` tree: configuration, linter, formatter, editor integrations.
