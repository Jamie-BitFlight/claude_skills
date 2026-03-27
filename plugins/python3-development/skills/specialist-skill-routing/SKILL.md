---
name: specialist-skill-routing
description: Use as the routing layer for Python development tasks — matches task descriptions against trigger lists and activates specialist skills before starting work. Covers Typer, Rich, Textual, FastMCP/MCP, ty type checker, uv, Hatchling, TOML editing, pre-commit/prek, async Python, PyPI packaging, complex linting, and technical debt modernization.
---

Scan your task description against the triggers below. For every match, call `Skill(skill="...")` **before** writing any architecture, plan, or code. Multiple matches → load all matching skills.

## CLI Framework — Typer

**Triggers**: `typer.Typer()`, `typer.run()`, `@app.command`, `@app.callback`, `typer.Option`, `typer.Argument`, `Annotated[int, typer.Option()]`, Typer subcommands, `app.add_typer()`, `CliRunner`, `typer.echo`, `typer.style`, `typer.secho`, `typer.Exit`, `typer.Abort`, `typer.confirm`, `typer.launch`, autocompletion

```text
Skill(skill="python3-development:typer")
```

Covers: app creation with `typer.Typer()` and `typer.run()`, CLI arguments and options (Annotated form), parameter types (enums, paths, dates, UUIDs, custom), subcommand composition with `add_typer()`, testing with `typer.testing.CliRunner`, output/colors/progress bars, callbacks, context, autocompletion, packaging.

---

## Terminal UI — Rich

**Triggers**: `rich.console.Console`, `rich.table.Table`, `rich.progress.track`, `rich.progress.Progress`, `rich.panel.Panel`, `rich.tree.Tree`, `rich.live.Live`, `rich.syntax.Syntax`, `rich.markdown.Markdown`, `rich.logging.RichHandler`, `rich.traceback.install`, `rich.print`, Rich markup tags, `rich.columns.Columns`, `rich.layout.Layout`, `rich.json.JSON`, `rich.pretty.pprint`, `__rich_console__`, `__rich__`, `__rich_repr__`

```text
Skill(skill="python3-development:rich")
```

Covers: Console class and markup syntax, style strings and color formats, renderables (Panel, Table, Tree, Columns, Layout), Progress and Live displays, Text class, Syntax/Markdown/Pretty/JSON rendering, RichHandler for stdlib logging, Traceback installation, `__rich_console__` and `__rich_repr__` protocols, RegexHighlighter.

---

## TUI Framework — Textual

**Triggers**: `textual.app.App`, `textual.widget.Widget`, `textual.screen.Screen`, `ComposeResult`, `compose()`, `mount()`, `query()`, `query_one()`, `textual.reactive.reactive`, `textual.css`, `@on`, `@work`, `run_worker`, `run_test`, Textual CSS, Textual events, Textual workers, `pytest-textual-snapshot`

```text
Skill(skill="python3-development:textual")
```

Covers: App lifecycle (run/exit/suspend), screen stack (push/pop/switch/modes), custom and builtin widgets, Line API, layout types (vertical/horizontal/grid), CSS selectors and pseudo-classes, events and message bubbling, custom messages, actions and key bindings, reactive attributes (watch/validate/compute/data binding), testing with Pilot API, snapshot testing, Workers and `@work` decorator.

---

## Typer + Rich Best Practices

**Triggers**: non-TTY output handling, table width measurement, Rich output in CI/piped environments, testing Rich-formatted CLI output, `Console(force_terminal=True)`, `Console(width=N)`, `Console(file=StringIO())`, `console.capture()`, `export_text()`

```text
Skill(skill="python3-development:typer-and-rich")
```

Covers: non-TTY Console behavior (width defaults, color stripping, environment variables), Measurement protocol for renderable width, Progress/Live without TTY, testing Rich output in pytest (capture, export, snapshot), CliRunner with Rich, common assertion mistakes.

---

## MCP / FastMCP

**Triggers**: building an MCP server, `FastMCP()`, `@mcp.tool`, `@mcp.resource`, MCP tools/resources/prompts, MCP transports (stdio/HTTP/SSE), server composition (`mount()`), MCP auth, MCP client, deploying an MCP server, migrating from FastMCP v2

```text
Skill(skill="fastmcp-creator:fastmcp-creator")
```

Also activate for:

- Writing tests for an MCP server → `Skill(skill="fastmcp-creator:fastmcp-python-tests")`
- Using `fastmcp list` / `fastmcp call` / `fastmcp discover` CLI → `Skill(skill="fastmcp-creator:fastmcp-client-cli")`

After loading, follow the trigger matrix inside that skill to load only the reference files relevant to your specific task.

---

## Type Checking — ty

**Triggers**: `ty check`, `ty.toml`, `[tool.ty]` in pyproject.toml, suppressing ty diagnostics, ty rule names and severity levels, ty environment/module resolution, unresolved imports in ty, migrating from mypy or pyright to ty, integrating ty with editors or CI

```text
Skill(skill="python3-development:ty")
```

Covers: CLI flags, configuration schema, rule levels (`error`/`warn`/`ignore`), suppression comments (`ty: ignore`, `type: ignore`), virtual environment discovery, Python version targeting, installation, VS Code/Neovim/Zed/PyCharm integration, troubleshooting.

Does NOT cover: deep mypy or pyright configuration (follow the project’s `pyproject.toml` when the repo already uses those tools — do not force ty). For annotation patterns shared across checkers, see python3-development references (e.g. type-safety-mypy). Does not replace a dedicated typing tutorial for writing annotations from scratch.

---

## Package Management — uv

**Triggers**: `uv add`, `uv run`, `uv build`, `uv publish`, `uv sync`, `uv lock`, `uvx`, PEP 723 inline script metadata, managing Python versions with uv, configuring package indexes or private registries, workspace configuration (`[tool.uv.workspace]`), migrating from pip/poetry/conda, CI/CD with `astral-sh/setup-uv`, Docker with uv, `uv venv`, dependency groups, `uv tool install`

```text
Skill(skill="python3-development:uv")
```

Key facts — do not guess these from training data:

- `uv venv` refuses to overwrite existing environments since 0.10.0 — pass `--clear`
- Use `uv run` not `source .venv/bin/activate`
- Use `uv add` not `uv pip install` for project dependencies
- `uv sync --frozen` for CI; `uv sync --locked` to fail if lockfile is stale
- PEP 723 shebang: `#!/usr/bin/env -S uv --quiet run --active --script`

---

## Build Backend — Hatchling

**Triggers**: `[build-system]` using hatchling, `hatch_build.py`, `[tool.hatchling]`, wheel/sdist configuration, build hooks, `hatch-vcs` version management, force-include patterns, editable installs with hatchling, setuptools migration to hatchling

```text
Skill(skill="python3-development:hatchling")
```

Covers: PEP 517/518/621/660, project metadata, wheel and sdist targets, build hooks interface, version sources, file selection with glob patterns, VCS integration, plugin architecture.

---

## TOML Editing (comment-preserving)

**Triggers**: Python code that reads AND writes `pyproject.toml` or any `.toml` file, preserving comments and formatting during modification, `tomlkit` library, atomic config file updates

```text
Skill(skill="python3-development:toml-python")
```

Use `tomlkit` (not `tomllib`) when writing or modifying TOML. `tomllib` is stdlib but read-only. Always open files in text mode (`'r'`/`'w'`), not binary.

---

## Pre-commit / prek Git Hooks

**Triggers**: `.pre-commit-config.yaml`, `prek install`, `pre-commit install`, adding or modifying git hooks, `prepare-commit-msg` hooks, distributing a tool as a pre-commit hook, detecting which hook tool is installed

```text
Skill(skill="python3-development:pre-commit")
```

Key fact: prek is a drop-in Rust replacement for pre-commit — same config file, identical CLI. Detect which is installed by reading `.git/hooks/pre-commit` line 2.

---

## Async / Concurrent Python

**Triggers**: `asyncio`, `async def`, `await`, concurrent I/O operations, `aiohttp`, `anyio`, `trio`, WebSocket servers, async background tasks, async queues, async database access, concurrent HTTP requests, async FastAPI

```text
Skill(skill="python3-development:async-python-patterns")
```

---

## PyPI Packaging

**Triggers**: configuring `pyproject.toml` for distribution, preparing a package for PyPI, entry points, optional dependencies, PEP 517/518/621

```text
Skill(skill="python3-development:python3-packaging")
```

For CI/CD pipeline to automate PyPI publishing (GitHub Actions or GitLab CI):

```text
Skill(skill="python3-development:python3-publish-release-pipeline")
```

For README files that render correctly on PyPI (`twine check`, Markdown vs RST choice, `readme` field in pyproject.toml):

```text
Skill(skill="python3-development:pypi-readme-creator")
```

---

## Complex Linting Resolution

**Triggers**: more than 3 ruff/mypy/basedpyright/pyright errors requiring root-cause analysis, type flow analysis across multiple files, deciding whether to suppress vs fix a diagnostic, linting errors you cannot resolve with standard patterns

```text
Skill(skill="holistic-linting:holistic-linting")
```

This skill behaves differently for orchestrators vs sub-agents. Orchestrators delegate to `linting-root-cause-resolver` agent; sub-agents run formatters and linters directly on touched files before completing.

---

## Technical Debt / Modernization

**Triggers**: eliminating `Any` types across a module, removing legacy typing imports (`Optional[X]`, `Union[X, Y]`, `List[X]`, `Dict[K, V]`), refactoring for Protocol usage, progressive quality improvement across multiple files

```text
Skill(skill="python3-development:stinkysnake")
```

Multi-phase workflow: static analysis → type analysis → modernization planning → plan review → test-driven implementation. Load before planning a refactor, not mid-implementation.

**Triggers**: applying modern Python 3.11+ patterns, learning about PEPs (585, 604, 695), finding modern alternatives for old code

```text
Skill(skill="python3-development:modernpython")
```

---

## Script Execution & Shebangs

**Triggers**: validating script shebangs, PEP 723 inline metadata, creating standalone executable Python scripts

```text
Skill(skill="python3-development:shebangpython")
```

---

## Development Workflows

**Triggers**: creating a structured feature development task, setting up feature tracking

```text
Skill(skill="python3-development:create-feature-task")
```

**Triggers**: creating a new Claude Code skill from a template

```text
Skill(skill="python3-development:use-command-template")
```

---

## Implementation & Refactoring Loop

**Triggers**: implementing functions following a modernization plan, running tests iteratively until passing, executing the implementation phase of a refactor

```text
Skill(skill="python3-development:snakepolish")
```

---

## Code Review & Quality Audits

**Triggers**: reviewing Python code for quality issues, auditing code before merge, checking pattern compliance, verifying architecture standards

```text
Skill(skill="python3-development:python3-review")
```

Note: If you are an orchestrator reviewing a completed feature, use the `code-reviewer` agent instead.

---

## Testing & Coverage

**Triggers**: auditing test quality, reviewing test coverage, checking for missing edge cases

```text
Skill(skill="python3-development:comprehensive-test-review")
```

**Triggers**: investigating failing tests, debugging test failures, analyzing pytest output

```text
Skill(skill="python3-development:analyze-test-failures")
```

---

## Agent Routing (For Orchestrators)

If you are an orchestrator agent, delegate to these specialized agents based on the task phase:

- **Architecture/Planning**: `Agent(subagent_type="python3-development:python-cli-design-spec")`
- **Writing Tests**: `Agent(subagent_type="python3-development:python-pytest-architect")`
- **Implementation**: `Agent(subagent_type="python3-development:python-cli-architect")`
- **Post-Implementation Review**: `Agent(subagent_type="python3-development:code-reviewer")`
