---
name: python3-core
description: "Activates on any Python task involving *.py files, uv, ruff, ty, pytest, or pyproject.toml — loads the shared Python 3.11+ standards and routes the task to the specialist skill that applies them: TDD, CLI, web, data, async, typing, packaging, publishing, documentation sites, test design, test-failure analysis, or stdlib-only constrained environments."
user-invocable: false
---

# Python Engineering Routing

Load `python-engineering:standards-for-python-development` first. It holds every rule this plugin
enforces — typing and the `Any` boundary policy, architecture and SOLID, error handling, security,
performance, identifier naming, script dependencies, Rich/Typer output, testing, and tooling
defaults. This skill routes the task to the specialist that applies them.

## Typing Lane

`python3-typing` picks the lane from the project's `requires-python` floor and the dependencies
already installed. `references/typing-matrix.md` shows each lane's imports and boundary shape;
`references/python311-features.md` through `references/python314-features.md` list what each
version adds.

## Domain Routing

Load a skill only when the task clearly matches it.

| Task | Load |
|---|---|
| Test-driven development, red-green-refactor, tests before implementation | `python3-tdd` |
| Designing a test suite — coverage strategy, test pyramid, fixture hierarchy, mutation plan | `python3-test-design` |
| Deciding whether a failing test is a genuine bug or a test defect | `analyze-test-failures` |
| Resetting the investigation approach to a test failure — dual-hypothesis protocol, red flags | `test-failure-mindset` |
| Auditing a whole suite — coverage, isolation, mock usage, naming, completeness | `comprehensive-test-review` |
| Typer/Rich CLI tools, progress bars, terminal output | `python3-cli` |
| FastAPI, Starlette, Django, Flask | `python3-web` |
| pandas, numpy, scipy, jupyter, data pipelines | `python3-data` |
| async/await, asyncio, concurrent I/O, task scheduling | `async-python-patterns` |
| Adding a feature to an existing project — discovery, MoSCoW, TDD, integration, verification | `python3-add-feature` |
| Writing a structured feature task file with phases and acceptance criteria | `create-feature-task` |
| Package metadata and build targets — pyproject.toml, build backend, entry points | `python3-packaging` |
| Publishing to PyPI or cutting a release — CI workflows, trusted publishing, TestPyPI | `python3-publish-release-pipeline` |
| uv, Hatchling, ty, pre-commit, TOML editing | `python3-tools` |
| A documentation site with MkDocs or the Material theme | `mkdocs` |
| A confirmed restriction blocking dependency installation — airgapped, no uv, no internet | `python3-stdlib-only` |
| Broad task classification is not enough to pick from this table | `specialist-skill-routing` |

Manual entrypoints: `/python-engineering:review` (code review), `/python-engineering:cleanup`
(progressive quality improvement), `/python-engineering:lint` (deterministic checks),
`/python-engineering:debug` (structured debugging).

## References

| File | Contents |
|---|---|
| `references/PEP723.md` | Inline script metadata — block syntax, shebang form, splitting a script across files |
| `references/typing-matrix.md` | Typing lane per Python version and available dependencies |
| `references/python311-features.md` … `python314-features.md` | What each Python version adds |
| `references/modern-modules.md` | Vetted Python 3.11+ modules by use case |
| `references/tool-library-registry.md` | Tool, library, and framework registry with pyproject.toml template variables |
| `references/python-development-orchestration.md` | Orchestrating a Python task across the specialist agents |
| `references/user-project-conventions.md` | Conventions extracted from production projects |

## Assets

Templates at `${CLAUDE_PLUGIN_ROOT}/skills/python3-core/assets/`:

- `version.py` — dual-mode version management
- `hatch_build.py` — build hook template
- `example.pre-commit-config.yaml` — standard git hooks
- `.editorconfig` — editor formatting
