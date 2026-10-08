---
name: code-review-python
description: Reviews Python boundaries, typing, error handling, tests, dependencies, and supported-version idioms against the target project's contracts and active tools. Loaded by dh:code-reviewer for Python source; uses Python-engineering standards when available and retains standalone checks otherwise.
user-invocable: false
---

# Python Code Review Patterns

Stack-specific rules loaded by `dh:code-reviewer` when `pyproject.toml` or `*.py` files are detected.

Read [Review principles](../../docs/review-principles.md) before applying these checks; it defines
authority, applicability, evidence, and blocking criteria.

When available, load `/python-engineering:standards-for-python-development`; it owns the shared
Python policy and contextual defaults. If that plugin is unavailable, use the checks below with
the target's supported Python versions, contracts, and active tooling. Report the unavailable
policy reference without making Python-engineering a prerequisite for review.

## Type Annotations

- Check that public parameter and return annotations communicate the supported contract; apply the project's annotation gate, including explicit `None` returns where required.
- Contain justified `Any`, broad `object`, and unchecked casts at explicit dynamic or external boundaries with typed outputs. An explanatory comment alone does not establish safety, and replacing `Any` with broad `object` alone does not strengthen the contract.
- Match data shapes to their purpose: typed mappings where mapping behavior is required, typed value objects for internal data, and runtime validation where external data needs it. Do not require `TypedDict` for every cross-module value or migrate a coherent dataclass/Pydantic/mapping design solely for uniformity.
- Prefer native generics and union syntax for new code when the supported Python floor permits them; do not report supported existing syntax as a correctness defect.
- Check that a `Protocol` or ABC models a real substitutable contract; preserve the project's coherent choice.

## Linter Compliance

- Read the active linter configuration and report violations of its enforced rules; do not enable additional rules during review.
- Investigate bare catches and unintended library output for swallowed control signals or corruption of a caller's output contract. Prefer specific exception handling and the project's diagnostic channel.
- Flag unexplained constants, unused imports, and export ambiguity when they violate a project gate or obscure a consequential contract. Do not classify every numeric comparison as a defect.
- Preserve supported interpolation idioms, including deferred logging formatting; use the project's formatting rules rather than requiring a style migration.
- Check intended exports, including `__all__` where the project or public import contract requires it.

## Type Checker Evidence

- Discover the active checker and command from hooks/CI. Reproduce its relevant diagnostics before treating editor hints as project failures.
- Trace unresolved imports through declared dependencies, supported runtime, and source roots; do not assume every failure requires adding a dependency.
- Apply the project's suppression policy and investigate what a suppression hides. Do not invent inline ignores or relax project gates to obtain a clean result.
- Verify that checker and test import paths resolve their intended sources; they need not contain identical entries when their scopes differ.
- When independently defined shared types cause an observed incompatibility, inspect ownership and reuse the canonical contract instead of adding casts or duplicated definitions.

## Test Patterns

Use `/dh:test-reviewer` for the effectiveness procedure and evidence-backed dispositions. Preserve
the project's coherent framework and test layout. For Python tests, also check:

- Behavior-oriented names identify the scenario and expected result.
- Fixtures and doubles preserve the production boundary whose guarantee is being assessed.
- Assertions distinguish the required result; a non-`None` check is sufficient only for a contract that requires exactly that observation.
- Shared mutable state, fixtures, and cleanup do not make tests order-dependent.
- Parametrization reduces repetition without obscuring distinct obligations or diagnostics.

## Execution and Dependencies

- Use the execution and dependency commands the target actually supports; apply `uv` conventions where that is the chosen environment.
- Verify dependency changes and lockfiles agree, and that the documented clean install can provide required imports.
- For PEP 723 scripts, check inline dependencies and the supported script invocation, such as `uv run --script`. Do not require duplicate root dependencies merely for editor tooling when the standalone contract is self-contained.

## Error Handling

- Trace each catch to its recovery owner, added context, or deliberate boundary conversion. A broad catch needs a justified boundary and must preserve the relevant failure signal.
- Report swallowed errors or misleading success when the caller cannot observe a required failure; distinguish documented best-effort behavior from accidental silence.
- Exception messages must include enough context to diagnose without reading the source: `raise ValueError(f"Expected positive int, got {value!r}")` not `raise ValueError("invalid input")`
- Sentinel return values (returning `None` or `-1` on error without raising) require a documented contract — silence must be intentional and documented

## Supported Python Idioms

- Check version-specific syntax and APIs against the target's supported Python floor.
- Apply the shared Python policy's choices for `match`, `pathlib`, datetime, and exception groups when available; preserve coherent existing idioms unless a demonstrated problem justifies change.
- For TOML, follow the shared policy when available and preserve an already suitable project library. In standalone review, distinguish read-only parsing from editing that must preserve formatting/comments, and respect stdlib-only deployment constraints. Do not require `tomllib`, `tomlkit`, or a new dependency merely because another form is present.
- Investigate manual prefix/suffix slicing for incorrect boundary behavior; prefer clearer supported methods in new code where they preserve the contract.

## Anti-Patterns

```python
# WRONG: bare except
try:
    do_thing()
except:
    pass

# RIGHT: narrow except with action
try:
    do_thing()
except ConnectionError as e:
    logger.warning("Connection failed: %s", e)
    raise

# Unexplained domain limit: determine its contract before proposing a name.
if attempts > 3:
    ...

# A named limit communicates an established retry contract.
MAX_RETRY_ATTEMPTS = 3
if attempts > MAX_RETRY_ATTEMPTS:
    ...

# Supported existing path construction; not a defect solely by style.
import os

path = os.path.join(base, "config.toml")

# New code may use pathlib when it fits the project.
from pathlib import Path

path = Path(base) / "config.toml"
```
