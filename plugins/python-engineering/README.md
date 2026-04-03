# Python Engineering Plugin

Opinionated Python 3.11+ development system for Claude Code.

## What This Is

One coherent Python engineering system, not a pile of unrelated prompts. Establishes strong defaults and routes to narrow specialist skills.

## Architecture

### One Automatic Router

- `python3-core` — loads on every Python task, establishes defaults, routes to specialists

### Manual Entrypoints (slash commands)

| Command | Purpose |
|---|---|
| `/python-engineering:orchestrate` | Multi-step engineering workflow |
| `/python-engineering:review` | Code review |
| `/python-engineering:lint` | Deterministic quality checks |
| `/python-engineering:cleanup` | Structured cleanup and modernization |
| `/python-engineering:debug` | Structured debugging |

### Specialist Skills (auto-loaded when relevant)

| Skill | Domain |
|---|---|
| `python3-typing` | Typed-boundary and validation policy |
| `python3-testing` | TDD, pytest, property-based testing |
| `python3-cli` | CLI and script development (Typer/Rich) |
| `python3-web` | Web and API development |
| `python3-data` | Data and scientific Python |
| `python3-stdlib-only` | Constrained/legacy environments |
| `python3-tools` | uv, Hatchling, ty, pre-commit, packaging |
| `python3-tdd` | TDD workflow entrypoint |

### Backward-Compat Skills

| Skill | Status |
|---|---|
| `modernpython` | Kept — reference for PEP-by-PEP modernization |
| `shebangpython` | Kept — shebang and PEP 723 validation |
| `stinkysnake` | Kept — progressive quality improvement |
| `snakepolish` | Kept — implementation phase for stinkysnake |

### Agents

| Agent | Role |
|---|---|
| `python-cli-architect` | Implements Python CLI code |
| `python-pytest-architect` | Writes pytest test suites |
| `code-reviewer` | General code review |
| `python-cli-design-spec` | Architecture specifications |
| `semantic-code-search` | Semantic search over codebases |

## Standing Defaults (applied by `python3-core` on every task)

- SOLID as active design guidance
- Code smells as design signals to investigate
- Type coverage as project health metric
- `Any` forbidden outside boundary modules
- pytest + pytest-mock, AAA pattern, 80% coverage
- uv, ruff, ty (default), hatchling
- Python 3.11+ target (3.10 is compatibility lane)

## Typing Policy

The plugin auto-detects the strongest valid typing strategy:

| Python | Dependencies | Strategy |
|---|---|---|
| 3.10 | stdlib only | `TypeAlias`, `Protocol`, `TypeGuard` |
| 3.11+ | stdlib only | `Self`, `TypedDict` + `NotRequired`, `TypeVar` |
| 3.11+ | pydantic | Pydantic models at boundaries, `TypeAdapter` |
| 3.11+ | hypothesis | Property-based tests for validators |
| 3.12+ | — | `type` statement for aliases |
| 3.13+ | — | `TypeIs` replaces `TypeGuard` |

## Deterministic Scripts

- `scripts/detect-type-checker.sh` — detect ty/mypy/pyright from hooks/CI
- `scripts/detect-environment.py` — detect Python version, dependencies, typing lane
- `scripts/check-typing-boundaries.sh` — Any/cast outside boundary modules
- `scripts/check-typing-boundaries.py` — AST-based Any/cast check
- `scripts/detect-python-version.sh` — extract requires-python
- `scripts/validate-manifest.sh` — validate plugin structure

## Installation

```bash
/plugin marketplace add Jamie-BitFlight/claude_skills
/plugin install python-engineering@jamie-bitflight-skills
```

## From python3-development

This plugin replaces `python3-development`. The old plugin should be uninstalled first:

```bash
/plugin uninstall python3-development@jamie-bitflight-skills
/plugin install python-engineering@jamie-bitflight-skills
```
