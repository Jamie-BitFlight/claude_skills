---
name: specialist-skill-routing
description: Routes Python engineering tasks to specialist skills by matching trigger patterns before any architecture, plan, or code is written. Use when working with Typer CLI frameworks, Rich or Textual terminal UIs, CLI UI/UX design, questionary prompts, FastMCP/MCP servers, ty type checker, uv package manager, Hatchling build backend, TOML editing, pre-commit/prek hooks, async Python, PyPI packaging, complex linting, technical debt modernization, testing workflows, feature development, or stdlib-only scripting.
---

Scan your task description against the triggers below. For every match, call `Skill(skill="...")` **before** writing any architecture, plan, or code. Multiple matches → load all matching skills.

## CLI Framework — Typer

**Triggers**: `typer.Typer()`, `typer.run()`, `@app.command`, `@app.callback`, `typer.Option`, `typer.Argument`, `Annotated[int, typer.Option()]`, Typer subcommands, `app.add_typer()`, `CliRunner`, `typer.echo`, `typer.style`, `typer.secho`, `typer.Exit`, `typer.Abort`, `typer.confirm`, `typer.launch`, autocompletion

```text
Skill(skill="python-engineering:typer")
```

Covers: app creation with `typer.Typer()` and `typer.run()`, CLI arguments and options (Annotated form), parameter types (enums, paths, dates, UUIDs, custom), subcommand composition with `add_typer()`, testing with `typer.testing.CliRunner`, output/colors/progress bars, callbacks, context, autocompletion, packaging.

---

## Agent-facing CLI output

**Triggers**: CLI or script implemented inside an Agent Skill or plugin; command primarily consumed by AI agents or automation.

Keep output machine-readable: compact JSON on stdout, preferably `BaseModel.model_dump_json()`; diagnostics on stderr. Do not route to Rich/UI skills unless a separate human-facing presentation mode is explicitly required.

---

## Terminal UI — Rich

**Triggers**: human-facing terminal presentation using `rich.console.Console`, `rich.table.Table`, `rich.progress.track`, `rich.progress.Progress`, `rich.panel.Panel`, `rich.tree.Tree`, `rich.live.Live`, `rich.syntax.Syntax`, `rich.markdown.Markdown`, `rich.logging.RichHandler`, `rich.traceback.install`, `rich.print`, Rich markup tags, `rich.columns.Columns`, `rich.layout.Layout`, `rich.json.JSON`, `rich.pretty.pprint`, `__rich_console__`, `__rich__`, `__rich_repr__`

```text
Skill(skill="python-engineering:python3-cli")
```

Covers: Console class and markup syntax, style strings and color formats, renderables (Panel, Table, Tree, Columns, Layout), Progress and Live displays, Text class, Syntax/Markdown/Pretty/JSON rendering, RichHandler for stdlib logging, Traceback installation, `__rich_console__` and `__rich_repr__` protocols, RegexHighlighter.


---

## TUI Framework — Textual

**Triggers**: `textual.app.App`, `textual.widget.Widget`, `textual.screen.Screen`, `ComposeResult`, `compose()`, `mount()`, `query()`, `query_one()`, `textual.reactive.reactive`, `textual.css`, `@on`, `@work`, `run_worker`, `run_test`, Textual CSS, Textual events, Textual workers, `pytest-textual-snapshot`

```text
Skill(skill="python-engineering:textual")
```

Covers: App lifecycle (run/exit/suspend), screen stack (push/pop/switch/modes), custom and builtin widgets, Line API, layout types (vertical/horizontal/grid), CSS selectors and pseudo-classes, events and message bubbling, custom messages, actions and key bindings, reactive attributes (watch/validate/compute/data binding), testing with Pilot API, snapshot testing, Workers and `@work` decorator.

---

## Typer + Rich Best Practices

**Triggers**: non-TTY output handling, table width measurement, Rich output in CI/piped environments, testing Rich-formatted CLI output, `Console(force_terminal=True)`, `Console(width=N)`, `Console(file=StringIO())`, `console.capture()`, `export_text()`

```text
Skill(skill="python-engineering:typer-and-rich")
```

Covers: non-TTY Console behavior (width defaults, color stripping, environment variables), Measurement protocol for renderable width, Progress/Live without TTY, testing Rich output in pytest (capture, export, snapshot), CliRunner with Rich, common assertion mistakes.

---

## CLI UI/UX Design — 7-Stage Workflow

**Triggers — before implementation**: designing CLI user experience, CLI display patterns, output consistency across commands, user-facing output design, CLI information architecture, shape brief, register decision (brand-cli vs product-cli), PRODUCT.md interview, DESIGN.TUI.md setup

**Triggers — during implementation**: `questionary`, `questionary.select`, `questionary.text`, `questionary.confirm`, `questionary.checkbox`, `questionary.prompt`, interactive prompts, progress bars, spinners, status indicators, tables, panels, dashboard layout, splash screens, animated welcome sequences, PyFiglet banners

**Triggers — evaluation and post-implementation**: CLI UX review, critique of existing CLI display code, UX heuristic evaluation, AI-slop check, accessibility review (NO_COLOR, non-TTY fallback, colour-blind safety), pre-ship polish pass, terminal-emulator portability check, column-alignment verification

```text
Skill(skill="python-engineering:designing-ui-for-cli")
```

Load before writing display/output/interaction code AND before declaring display work done. Runs a 7-stage discipline: Context → Register → Shape brief (user-confirmed gate) → Implement → Critique (Nielsen /40 + AI-slop) → Audit (P0–P3 severity) → Polish (22-item checklist). Any P0 audit finding blocks ship.

Covers: per-project design system contracts (PRODUCT.md, DESIGN.TUI.md), colour strategy (Restrained → Drenched), theme via scene-sentence method, register-specific permissions and bans, shape brief with confirmation gate, Nielsen heuristic critique, 5-dimension audit, 22-item polish checklist, Textual/Rich/Typer/Questionary/PyFiglet patterns.

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
Skill(skill="python-engineering:ty")
```

Covers: CLI flags, configuration schema, rule levels (`error`/`warn`/`ignore`), suppression comments (`ty: ignore`, `type: ignore`), virtual environment discovery, Python version targeting, installation, VS Code/Neovim/Zed/PyCharm integration, troubleshooting.

Does NOT cover: deep mypy or pyright configuration (follow the project's `pyproject.toml` when the repo already uses those tools — do not force ty). For annotation patterns shared across checkers, see python3-typing skill. Does not replace a dedicated typing tutorial for writing annotations from scratch.

---

## Package Management — uv

**Triggers**: `uv add`, `uv run`, `uv build`, `uv publish`, `uv sync`, `uv lock`, `uvx`, PEP 723 inline script metadata, managing Python versions with uv, configuring package indexes or private registries, workspace configuration (`[tool.uv.workspace]`), migrating from pip/poetry/conda, CI/CD with `astral-sh/setup-uv`, Docker with uv, `uv venv`, dependency groups, `uv tool install`

```text
Skill(skill="python-engineering:uv")
```

Key facts — do not guess these from training data:

- `uv venv` refuses to overwrite existing environments since 0.10.0 — pass `--clear`
- Use `uv run` not `source .venv/bin/activate`
- Use `uv add` not `uv pip install` for project dependencies
- `uv sync --frozen` for CI; `uv sync --locked` to fail if lockfile is stale
- PEP 723 shebang: `#!/usr/bin/env -S uv run --quiet --script`

---

## Build Backend — Hatchling

**Triggers**: `[build-system]` using hatchling, `hatch_build.py`, `[tool.hatchling]`, wheel/sdist configuration, build hooks, `hatch-vcs` version management, force-include patterns, editable installs with hatchling, setuptools migration to hatchling

```text
Skill(skill="python-engineering:hatchling")
```

Covers: PEP 517/518/621/660, project metadata, wheel and sdist targets, build hooks interface, version sources, file selection with glob patterns, VCS integration, plugin architecture.

---

## TOML Editing (comment-preserving)

**Triggers**: Python code that reads AND writes `pyproject.toml` or any `.toml` file, preserving comments and formatting during modification, `tomlkit` library, atomic config file updates

```text
Skill(skill="python-engineering:toml-python")
```

Use `tomlkit` (not `tomllib`) when writing or modifying TOML. `tomllib` is stdlib but read-only. Always open files in text mode (`'r'`/`'w'`), not binary.

---

## Pre-commit / prek Git Hooks

**Triggers**: `.pre-commit-config.yaml`, `prek install`, `pre-commit install`, adding or modifying git hooks, `prepare-commit-msg` hooks, distributing a tool as a pre-commit hook, detecting which hook tool is installed

```text
Skill(skill="python-engineering:pre-commit")
```

Key fact: prek is a drop-in Rust replacement for pre-commit — same config file, identical CLI. Detect which is installed by reading `.git/hooks/pre-commit` line 2.

---

## Async / Concurrent Python

**Triggers**: `asyncio`, `async def`, `await`, concurrent I/O operations, `aiohttp`, `anyio`, `trio`, WebSocket servers, async background tasks, async queues, async database access, concurrent HTTP requests, async FastAPI

```text
Skill(skill="python-engineering:async-python-patterns")
```

---

## PyPI Packaging

**Triggers**: configuring `pyproject.toml` for distribution, preparing a package for PyPI, entry points, optional dependencies, PEP 517/518/621

```text
Skill(skill="python-engineering:python3-packaging")
```

For CI/CD pipeline to automate PyPI publishing (GitHub Actions or GitLab CI):

```text
Skill(skill="python-engineering:python3-publish-release-pipeline")
```

For README files that render correctly on PyPI (`twine check`, Markdown vs RST choice, `readme` field in pyproject.toml):

```text
Skill(skill="python-engineering:pypi-readme-creator")
```

---

## Complex Linting Resolution

**Triggers**: more than 3 ruff/mypy/basedpyright/pyright errors requiring root-cause analysis, type flow analysis across multiple files, deciding whether to suppress vs fix a diagnostic, linting errors you cannot resolve with standard patterns

```text
Skill(skill="holistic-linting:holistic-linting")
```

This skill behaves differently for orchestrators vs sub-agents. Orchestrators delegate to `linting-root-cause-resolver` agent; sub-agents run formatters and linters directly on touched files before completing.

---

## Python Quality / Modernization Audit

**Triggers**: broad Python quality audit, PR/diff quality assessment, technical-debt discovery, Pythonic modernization, dependency/library substitution, maintenance-burden reduction, obsolete compatibility removal, "what can we delete?", "what should a library do for us?", or comparison with practices in large Python projects.

```text
Skill(skill="python-engineering:python-quality-audit")
```

This is the owning entryway. It fans out independent StinkySnake smell discovery, SnakePolish modernization assessment, ecosystem substitution, large-project practice, and removal/process-debt lanes, then synthesizes one verified/actionable report. Invoke `stinkysnake` or `snakepolish` directly only when the task explicitly requests that single lens.

**Triggers**: applying modern Python 3.11+ patterns, learning about PEPs (585, 604, 695), finding modern alternatives for old code

```text
Skill(skill="python-engineering:modernpython")
```

---

## Script Execution & Shebangs

**Triggers**: validating script shebangs, PEP 723 inline metadata, creating standalone executable Python scripts

```text
Skill(skill="python-engineering:shebangpython")
```

---

## Stdlib-Only / Restricted Environment Scripts

**Triggers**: writing Python scripts with no external dependencies, restricted environment scripting, refactoring a script from third-party libraries to stdlib-only

```text
Skill(skill="python-engineering:python3-stdlib-only")
```

---

## Development Workflows

**Triggers**: creating a structured feature development task, setting up feature tracking

```text
Skill(skill="python-engineering:create-feature-task")
```

**Triggers**: guided feature addition with acceptance criteria, TDD workflow, MoSCoW prioritization

```text
Skill(skill="python-engineering:python3-add-feature")
```


---

## Implementation & Refactoring Loop

**Triggers**: implementing an approved modernization/refactoring plan, applying accepted quality-audit findings, running the implementation/test loop.

Route implementation through `python-engineering:orchestrate` (or directly to `python-cli-architect` when already inside an orchestrated implementation phase) and use the appropriate TDD/testing path. `snakepolish` is assessment-only and must not be used as a writer.

---

## Code Review

**Triggers**: bounded conventional review against task acceptance criteria, correctness, security, tests, and established standards. For broad quality/modernization audits, route to `python-quality-audit` above.

```text
Skill(skill="python-engineering:review")
```

Note: If you are an orchestrator reviewing a completed feature, use the `code-reviewer` agent instead.


---

## Testing & Coverage

**Triggers**: auditing test quality, reviewing test coverage, checking for missing edge cases

```text
Skill(skill="python-engineering:comprehensive-test-review")
```

**Triggers**: investigating failing tests, debugging test failures, analyzing pytest output

```text
Skill(skill="python-engineering:analyze-test-failures")
```

**Triggers**: designing test architecture, test pyramid strategy, fixture hierarchy, mutation testing

```text
Skill(skill="python-engineering:python3-test-design")
```

**Triggers**: determining whether a test failure is a bug or test implementation issue, dual-hypothesis investigation

```text
Skill(skill="python-engineering:test-failure-mindset")
```

---

## Optional external specialists

Cross-plugin specialists are preferred accelerators, not hidden prerequisites. Before dispatching a named external agent or skill, verify that capability is available. If it is unavailable, preserve the required outcome using this plugin's own discovery, testing, review, or lint workflow. Report a blocker only when the missing capability provides something the local workflow cannot establish safely.

## Agent Routing (For Orchestrators)

If you are an orchestrator agent, delegate to these specialized agents based on the task phase:

- **Architecture/Planning**: `Agent(subagent_type="python-engineering:python-cli-design-spec")`
- **Writing Tests**: `Agent(subagent_type="python-engineering:python-pytest-architect")`
- **Implementation**: `Agent(subagent_type="python-engineering:python-cli-architect")`
- **Post-Implementation Review**: `Agent(subagent_type="python-engineering:code-reviewer")`
