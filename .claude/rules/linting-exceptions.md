---
paths:
- '**/*.py'
- '**/pyproject.toml'
---

# Linting Exception Conditions

Resolve linting errors — do not suppress them. Linting errors signal architectural issues, not noise.
Pythonic, fully-typed, well-written code is achievable in nearly every case. An exception is rare and
must be justified for the specific code in question — a category name alone is not a justification.

## Acceptable Exceptions

Code qualifies for an exception only when BOTH hold: (1) it matches one of the categories below, AND
(2) a specific, written reason explains why *this exact code* cannot be made compliant. "Tests use
mocks" is not a justification. "This mock's target signature is generated at runtime by
`unittest.mock.create_autospec`, so ANN001 cannot resolve a static type for it" is.

1. **Rule conflicts** — two enabled lint/type rules make mutually exclusive demands on the same code
   (a genuine tooling contradiction, not a style disagreement). Document which two rules conflict and
   how.
2. **Testing the rules themselves** — fixture/example code whose entire purpose is verifying a linter
   or rule correctly catches (or doesn't catch) a specific violation. The violation is the subject
   under test, not a mistake.
3. **Negative/bad-code examples or fixtures** — code that is purposefully non-compliant because its
   role requires it: a documentation example showing an anti-pattern, or a fixture that must contain
   malformed/bad code to exercise how *other* code (not a linter) handles it. Distinct from category
   2: this isn't testing the rules, it's demonstrating or feeding bad input on purpose. The
   non-compliance is the point, not an oversight.
4. **Externally-managed vendored code** — third-party code copied in verbatim that we do not modify
   and that continues to be maintained upstream. This does **not** cover vendored code we've adopted
   and made our own — once we own it, it must be brought into full compliance like everything else.
5. **Environment-constrained runtimes** — code whose actual deployment target has a real, lower
   syntax/typing ceiling than this repo's general 3.11+ baseline: an older pinned CPython (e.g. a
   production system still on 3.9), or a Python variant (MicroPython, CircuitPython, or another
   implementation with different syntax support or a reduced/missing stdlib). The fix is never to
   suppress linting — it's to set the correct `target-version` / type-checker environment config for
   that code so tooling enforces *that environment's* real ceiling (no walrus operator, no
   `match`/`case`, etc. where the target can't run them) instead of either this repo's default or
   nothing at all. Verify the actual target version before assuming a ceiling — never guess it.

For these exceptions: update linting config files (`pyproject.toml`, `.vscode/settings.json`) to
exclude the files or set a scoped `target-version` for the affected paths, and cite the category plus
the specific justification in a comment beside the config entry. Do not use inline comments (`# noqa`,
`# type: ignore`) as the mechanism.

## Unacceptable Exceptions (MUST fix or escalate)

If none of the above apply, or the only justification given is a category label with no specific
reason:

1. Fix linting smell using `/holistic-linting:holistic-linting` Skill (exact methodology for addressing linting issues)
2. If unable to fix, document specific blocker
3. Adding `# type: ignore` or `# noqa` requires explicit user approval

## Rule Codes That MUST Always Be Fixed (never suppress)

These are never eligible for any exception above, including environment-constrained runtimes:

- BLE001 (blind-except): Replace `except Exception` with specific exception types
- D103 (missing-docstring-in-public-function): Add docstrings to public functions
- TRY300 (try-consider-else): Restructure try/except/else blocks properly

**Touched Files Must Be Clean**: When files are modified/moved/renamed, all linting issues MUST be resolved before committing. Touching a file means taking responsibility for its quality.

## `--ignore` and `--unsafe-fixes`

Never pass `--ignore` to `ruff check` to make this repository's CI pass — that suppresses the same
class of error this file already prohibits suppressing by comment. `ruff check --fix --unsafe-fixes`
is permitted only after reviewing the change with `--diff` first; never apply unsafe fixes blind.
See [`astral-tool-overrides.md`](./astral-tool-overrides.md) C2 for why this departs from Astral's
own `ruff` skill, which teaches `--ignore` and `--unsafe-fixes` with no such gate.

SOURCE: User policy established in conversation (2025-01-15); narrowed 2026-08-19 to require a
per-instance justification, replace ad hoc categories with rule-conflict / rule-testing /
externally-managed-vendored / environment-constrained-runtime, and remove blanket per-directory
exemptions (see `pyproject.toml`'s `[tool.ruff.lint.per-file-ignores]` — those entries still exist
and are not yet brought into this policy; each needs its own justification or removal).
