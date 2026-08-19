---
paths:
- '**/*.py'
- '**/pyproject.toml'
---

# Linting Exception Conditions

Resolve linting errors — do not suppress them. Linting errors signal architectural issues, not noise.

## Acceptable Exceptions

Fix linting issues unless code falls into these categories:

1. **Vendored code** — third-party code copied without modification (not authored by model)
2. **What-not-to-do examples** — intentionally incorrect code for educational/negative test cases
3. **Historic Python version pinning** — code for Python <3.11 where modern syntax unavailable (currently no code in this category — verify before assuming)
4. **Python derivatives** — CircuitPython, MicroPython, or implementations with different syntax/missing stdlib modules

For these exceptions: update linting config files (`pyproject.toml`, `.vscode/settings.json`) to exclude the files. Do not use inline comments (`# noqa`, `# type: ignore`).

## Unacceptable Exceptions (MUST fix or escalate)

If NONE of the above apply:

1. Fix linting smell using `/holistic-linting:holistic-linting` Skill (exact methodology for addressing linting issues)
2. If unable to fix, document specific blocker
3. Adding `# type: ignore` or `# noqa` requires explicit user approval

## Rule Codes That MUST Always Be Fixed (never suppress)

- BLE001 (blind-except): Replace `except Exception` with specific exception types
- D103 (missing-docstring-in-public-function): Add docstrings to public functions
- TRY300 (try-consider-else): Restructure try/except/else blocks properly

## Per-File Exceptions in pyproject.toml (acceptable)

- `**/scripts/**`: T201 (print), S (security), DOC, ANN401, PLR0911, PLR0917, PLC0415
- `**/tests/**`: S, D, E501, ANN, DOC, PLC, SLF, PLR, EXE, N, T
- `**/assets/**`: PLC0415, DOC
- `typings/**`: N, ANN, A

**Touched Files Must Be Clean**: When files are modified/moved/renamed, all linting issues MUST be resolved before committing. Touching a file means taking responsibility for its quality.

## `--ignore` and `--unsafe-fixes`

Never pass `--ignore` to `ruff check` to make this repository's CI pass — that suppresses the same
class of error this file already prohibits suppressing by comment. `ruff check --fix --unsafe-fixes`
is permitted only after reviewing the change with `--diff` first; never apply unsafe fixes blind.
See [`astral-tool-overrides.md`](./astral-tool-overrides.md) C2 for why this departs from Astral's
own `ruff` skill, which teaches `--ignore` and `--unsafe-fixes` with no such gate.

SOURCE: User policy established in conversation (2025-01-15)
