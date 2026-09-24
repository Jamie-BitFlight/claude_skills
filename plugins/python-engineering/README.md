<p align="center">
  <img src="./assets/hero.png" alt="Python Engineering" width="800" />
</p>

# Python Engineering

Opinionated Python 3.11+ engineering system. Establishes strong defaults and routes tasks to specialist skills for TDD, CLI, web, data/science, and constrained environments.

## Why Install This?

Without this plugin, Claude applies generic Python patterns and makes ad-hoc decisions about typing, testing tooling, and project structure. With it:

- Every Python task automatically applies Python 3.11+ standards
- Tasks are routed to specialist skills (CLI, web, data, TDD, typing) based on what you are building
- Code quality gates run via `ruff`, `ty`, and `pytest`, while `python-quality-audit` can fan out deeper smell, modernization, ecosystem, and maintenance analysis
- Multi-step features get a structured task file via `create-feature-task`
  (`.claude/tasks/{feature-name}.md`) capturing phases, acceptance criteria, and context

## Architecture

### One Automatic Router

`python3-core` loads on every Python task, establishes defaults, and routes to specialists based on the task domain.

`/python-engineering:orchestrate` is the primary user entrypoint. It classifies the task,
loads the appropriate specialist skills, and delegates through this plugin's own agent
chain — architect (design) → implement → test → review — sized to the task: a one-line fix
goes straight to implement → review, while a multi-file feature runs the full chain. This
command is model-invocable — Claude can route work internally using the orchestrate
workflow.

### Manual Entrypoints (slash commands)

| Command | Use When |
|---|---|
| `/python-engineering:orchestrate` | Any Python task — primary entrypoint |
| `/python-engineering:python-quality-audit PR|diff|staged|unstaged|path` | Broad read-only Python quality and modernization audit; primary entryway for StinkySnake + SnakePolish + ecosystem research |
| `/python-engineering:review` | Bounded conventional code review against task requirements and standards |
| `/python-engineering:lint` | Deterministic quality checks |
| `/python-engineering:cleanup` | Structured cleanup and modernization |
| `/python-engineering:debug` | Structured debugging |
| `/python-engineering:python3-tdd` | Start a feature test-first |
| `/python-engineering:stinkysnake path/to/file.py` | Read-only smell hunter; normally invoked as an audit lane |
| `/python-engineering:snakepolish path/to/file.py` | Read-only forward-looking Python modernization assessor; normally invoked as an audit lane |
| `/python-engineering:modernpython` | Apply Python 3.11+ modernization patterns |
| `/python-engineering:python3-add-feature` | Guided feature addition workflow |
| `/python-engineering:comprehensive-test-review tests/` | Audit test suite quality |
| `/python-engineering:analyze-test-failures` | Diagnose test failures systematically |
| `/python-engineering:python3-packaging` | Configure `pyproject.toml` and packaging |
| `/python-engineering:python3-publish-release-pipeline` | Set up PyPI publishing CI/CD |
| `/python-engineering:hatchling` | Hatchling build backend configuration |
| `/python-engineering:pre-commit` | Set up `.pre-commit-config.yaml` |
| `/python-engineering:mkdocs` | MkDocs with Material theme documentation |
| `/python-engineering:pypi-readme-creator` | Create a README for a PyPI package |
| `/python-engineering:async-python-patterns` | asyncio, gather, queues, WebSocket patterns |
| `/python-engineering:shebangpython` | Validate and fix Python shebangs and PEP 723 metadata |
| `/python-engineering:ty` | ty type checker usage and configuration |

### Specialist Skills (auto-loaded when relevant)

These skills are not invoked directly — `python3-core` and `orchestrate` load them automatically.

| Skill | Domain |
|---|---|
| `python3-core` | Python 3.11+ standards, SOLID, code smell detection — activates on any `.py` file |
| `python3-typing` | Typed-boundary policy, Protocol, TypeIs, native generics |
| `python3-testing` | pytest, fixtures, parametrize, Hypothesis, coverage targets, property-based testing |
| `python3-cli` | Typer + Rich, Annotated syntax, CliRunner, PEP 723 scripts |
| `python3-web` | FastAPI, aiohttp, web and API development |
| `python3-data` | Data and scientific Python |
| `python3-stdlib-only` | Constrained/legacy environments (last resort) |
| `python3-tools` | uv, Hatchling, ty, prek, pre-commit, packaging |
| `python3-tdd` | Red-green-refactor TDD workflow |
| `typer` | Typer CLI framework — Annotated syntax, enum restrictions, path types |
| `typer-and-rich` | Typer + Rich integration, CliRunner snapshot testing, non-TTY output |
| `textual` | Textual TUI framework |
| `specialist-skill-routing` | Routes Typer, Rich, Textual, FastMCP, uv, TOML tasks to correct specialist |
| `orchestrating-python-development` | Agent selection criteria for orchestrators |
| `standards-for-python-development` | Shared typing, testing, and CLI standards reference |
| `python3-test-design` | pytest suite architecture and coverage strategy |
| `test-failure-mindset` | Root-cause approach to test failures |
| `designing-ui-for-cli` | CLI UX design, 7-stage workflow; integrates impeccable design rigour |

### Quality Audit Architecture

`python-quality-audit` is the public entryway for broad assessment. It accepts a PR, git diff, staged/unstaged work, file, or directory and fans out independent evidence gathering before synthesis:

```text
python-quality-audit
  ├─ stinkysnake       smell / standards / maintenance-debt discovery
  ├─ snakepolish       Python/stdlib/ecosystem modernization assessment
  ├─ ecosystem lane    maintained-library substitution research
  ├─ project lane      practices from substantial current Python projects
  └─ removal lane      dead code/process/compatibility and deletion opportunities
       ↓
  evidence-backed, deduplicated, actionable report
```

StinkySnake and SnakePolish remain directly invokable for a single lens, but neither edits code. The audit distinguishes observed/derived/external evidence from hypotheses and requires a verification path before calling material changes actionable.

### Retained Utility Skills

| Skill | Status |
|---|---|
| `modernpython` | Reference for PEP-by-PEP modernization |
| `shebangpython` | Shebang and PEP 723 validation |
| `stinkysnake` | Focused read-only smell hunter |
| `snakepolish` | Focused read-only modernization assessor |

### Agents

| Agent | Role |
|---|---|
| `python-cli-architect` | Implements Python CLI features and fixes — primary implementation agent |
| `python-pytest-architect` | Writes pytest test suites |
| `python-cli-design-spec` | Designs CLI architecture and produces architecture specifications |
| `code-reviewer` | Bounded post-implementation review; broad quality/modernization review routes through `python-quality-audit` |
| `adversarial-solution-design` | Stress-tests design decisions before committing |
| `semantic-code-search` | Searches codebase by identifier, import shape, type signature and code pattern |

## Standing Defaults (applied on every task)

| Category | Standard |
|---|---|
| Python version | 3.11+ — native generics, `match`, `Self`, `StrEnum` |
| Package manager | `uv` — `uv add`, `uv run`, `uv lock` |
| Linter | `ruff` |
| Quality gates | `prek` — unified pre-commit hook runner |
| Type checker | `ty` (Astral) — not mypy |
| Test runner | `pytest`; prefer pytest-mock and Hypothesis when their seams/properties strengthen the tests |
| Build backend | Hatchling |
| File size limit | 500 LOC — architect and reviewer agents enforce this per file |
| `Any` usage | Keep out of the typed core; localize justified dynamic-boundary exceptions by file |
| Type annotations | Strong typing by default; follow coherent project conventions and truthful boundary types |
| Coverage | Behavior/risk driven; respect a project's configured gate rather than inventing a percentage |
| Design | SOLID as active guidance; code smells as signals to investigate |

## Typing Policy

- `Any`, broad `object`, and unchecked `cast()` are forbidden in normal internal code
- Use `TypeVar`, `Protocol`, `TypedDict`, `dataclass`, or Pydantic models instead
- Boundary inputs (raw API/user data) must be validated and returned as typed internal objects
- `ty` is the enforcer — inline `# ty: ignore` suppressions are prohibited

The plugin auto-detects the strongest valid typing strategy from Python version and available dependencies:

| Python | Dependencies | Strategy |
|---|---|---|
| 3.10 | stdlib only | `TypeAlias`, `Protocol`, `TypeGuard` |
| 3.11+ | stdlib only | `Self`, `TypedDict` + `NotRequired`, `TypeVar` |
| 3.11+ | pydantic | Pydantic models at boundaries, `TypeAdapter` |
| 3.11+ | hypothesis | Property-based tests for validators |
| 3.12+ | — | `type` statement for aliases |
| 3.13+ | — | `TypeIs` replaces `TypeGuard` |

## Quick Start

```bash
# Install the plugin
/plugin install python-engineering@jamie-bitflight-skills

# Start any Python task — this is the entry point
/python-engineering:orchestrate "Add a CLI command that processes CSV files"

# Broad quality/modernization audit of existing code
/python-engineering:python-quality-audit src/myapp/

# Single-lens smell hunt
/python-engineering:stinkysnake src/myapp/processor.py

# Test-first feature
/python-engineering:python3-tdd "Add rate limiting to the API client"

# Code review
/python-engineering:review src/myapp/
```

## From python3-development

This plugin replaces `python3-development`. If you have the old plugin installed:

```bash
/plugin uninstall python3-development@jamie-bitflight-skills
/plugin install python-engineering@jamie-bitflight-skills
```

## Installation

First, add the marketplace (one-time setup):

```bash
/plugin marketplace add Jamie-BitFlight/claude_skills
```

Then install the plugin:

```bash
/plugin install python-engineering@jamie-bitflight-skills
```
