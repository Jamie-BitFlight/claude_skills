---
name: python3-core
description: Activates on any Python task involving *.py files, uv, ruff, ty, pytest, or pyproject.toml — establishes Python 3.11+ coding standards, SOLID design guidance, strict typing policy, testing defaults (pytest + pytest-mock), tooling expectations (uv, ruff, ty, hatchling), and code smell detection as design signals. Routes to specialist skills for TDD, CLI, web, data, async, or constrained environments.
user-invocable: false
---

# Python Engineering Standards

Consult `references/python3-standards.md` for the full standards document.

## Standing Defaults (apply to every Python task)

### Code Quality

- Python 3.11+ native types: `list[str]`, `str | None`, `Self`, `TypeAlias`
- Google-style docstrings (Args/Returns/Raises)
- SOLID principles as active design guidance, not checklist items
- Functions under 50 lines; max 3 nesting levels
- `__all__` in public modules
- No `Any`, broad `object`, or unchecked `cast()` in internal code
- Code smells are design signals to investigate, not noise to suppress
- Expand acronyms in public names: `greatest_common_divisor()` not `gcd()`; domain
  acronyms (URL, API, SQL, HTTP, JSON, XML) are exempt; see `references/python3-standards.md` §1.5

### Type Coverage

- Type coverage is a project health metric
- Adapt strictness to project constraints (see typing policy below)
- Boundary modules are the ONLY place `Any` is permitted
- Boundary code must validate and convert raw input immediately

### Testing Defaults

- pytest + pytest-mock (never unittest.mock)
- AAA pattern; behavioral test names (`test_{fn}_{scenario}_{result}`)
- 80% coverage minimum; 95% + mutation testing for critical paths
- Dual-hypothesis on test failure: both test-bug and implementation-bug are possible

### Tooling

- `uv` for dependency management
- `ruff` for linting and formatting
- `ty` (Astral) as default type checker; keep mypy/pyright when the project already uses them
- `pytest` for testing
- `hatchling` as default build backend
- Detect active checker from `.pre-commit-config.yaml` then CI, not from presence of config sections

### Design Principles

- Code smell detection drives refactoring decisions
- Fail-fast error handling: catch specific exceptions only when you can recover or add context
- Use `e.add_note()` for exception context; never swallow exceptions
- Protocol classes for dependency injection and duck typing
- Factory patterns for complex object creation

## Typing Policy

### Rules

1. `Any`, broad `object`, and unchecked `cast()` are FORBIDDEN in normal internal code
2. They are ALLOWED only at explicit system boundaries where unknown-shape external data enters
3. Boundary code must live in dedicated validator, parser, adapter, or boundary modules
4. Boundary code must immediately validate and convert raw input into strongly typed internal objects
5. If Pydantic is available, prefer Pydantic models or `TypeAdapter`
6. If Hypothesis is available, boundary validation should include property-based tests
7. Boundary modules may be the only place with narrow lint exceptions for `Any`
8. The typed core must not receive raw unvalidated payloads

### Strategy Selection (auto-detected)

Load `python3-typing` for the full matrix. Summary:

| Python Version | Dependencies Available | Strategy |
|---|---|---|
| 3.10 constrained | stdlib only | `TypeAlias`, `Protocol`, `TypeGuard`; no third-party |
| 3.11+ stdlib | stdlib only | `TypeAlias`, `TypeVar`, `Self`, `TypedDict` + `NotRequired` |
| 3.11+ with Pydantic | pydantic available | Pydantic models at boundaries; `TypeAdapter` for ad-hoc |
| 3.11+ with Hypothesis | hypothesis available | Property-based tests for validators and boundaries |
| 3.12 | — | `type` statement for type aliases |
| 3.13 | — | `TypeIs` (PEP 742) replaces `TypeGuard` where bidirectional narrowing needed |
| 3.14 | — | Deferred evaluation of annotations (PEP 649) |

## Domain Routing

Only load when the task clearly matches. Do NOT preload all of these.

### TDD Workflow

Load `python3-tdd` when the task involves test-driven development, writing tests before implementation, or red-green-refactor workflows.

### CLI Applications

Load `python3-cli` when building Typer/Rich CLI tools, scripts with progress bars, or terminal output.

### Web Applications

Load `python3-web` when working with FastAPI, Starlette, Django, or Flask.

### Data / Scientific Python

Load `python3-data` when working with pandas, numpy, scipy, jupyter, or data pipelines.

### Constrained / Legacy Environments

Load `python3-stdlib-only` ONLY when confirmed environment restrictions prevent dependency installation (airgapped, no uv, no internet). Do NOT assume restrictions.

### Test Suite Design

Load `python3-test-design` when designing test suites before implementation — coverage strategy, test pyramid distribution, fixture hierarchy, mutation testing plan.

### Test Failure Analysis

Load `analyze-test-failures` when analyzing failing tests to determine whether the failure is a genuine bug or a test implementation issue.

### Test Suite Review

Load `comprehensive-test-review` when conducting a full test quality audit — coverage, isolation, mock usage, naming, completeness.

### Test Investigation Approach

Load `test-failure-mindset` when resetting investigation approach to test failures — dual-hypothesis protocol, red flags, worked examples.

### Feature Addition Workflow

Load `python3-add-feature` when adding a new feature to an existing Python project — discovery, MoSCoW prioritization, TDD implementation, integration, verification.

### SAM Task Creation

Load `create-feature-task` when creating a structured feature task with SAM tracking — produces task documentation with phases, acceptance criteria, and context preservation ready for the SAM pipeline.

### Package Configuration

Load `python3-packaging` when configuring package metadata or build targets — pyproject.toml templates, build backend options (Hatchling/Setuptools/Flit), entry points, dependency specification.

### PyPI Publishing Pipeline

Load `python3-publish-release-pipeline` when publishing to PyPI or cutting a release — GitHub Actions / GitLab CI workflows, trusted publishing, version management, TestPyPI.

### Specialist Skill Routing

Load `specialist-skill-routing` at the start of any Python task to activate granular trigger-based routing across all 17+ specialist categories. This is the master router — agents activate it before starting work when broad task classification is insufficient.

### Quality Workflows

- `/python-engineering:review` — comprehensive code review (manual entrypoint)
- `/python-engineering:cleanup` — progressive quality improvement (manual entrypoint)
- `/python-engineering:lint` — deterministic quality checks (manual entrypoint)
- `/python-engineering:debug` — structured debugging (manual entrypoint)

### Async/Concurrent Python

Load `async-python-patterns` when the task involves async/await patterns, asyncio, concurrent I/O operations, task scheduling, or non-blocking systems.

### Documentation Sites

Load `mkdocs` when the task involves generating a documentation site with MkDocs or Material theme.

### Tool-Specific

Load `python3-tools` when the task involves uv, Hatchling, ty, pre-commit, TOML editing, or PyPI packaging.

## Assets

Templates available at `${CLAUDE_PLUGIN_ROOT}/skills/python3-core/assets/`:

- `version.py` — dual-mode version management
- `hatch_build.py` — build hook template
- `example.pre-commit-config.yaml` — standard git hooks
- `.editorconfig` — editor formatting
