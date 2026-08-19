<p align="center">
  <img src="./assets/hero.png" alt="Python 3 Development" width="800" />
</p>

# Python 3 Development

Modern Python 3.11+ development workflows with CLI apps, testing patterns, code quality tools, and TDD best practices.


## Why Install This?

When you ask Claude to write Python code without this plugin, you might notice:

- Outdated syntax patterns from Python 3.8 or earlier
- Random library choices instead of proven combinations
- Inconsistent project structures across different files
- Tests that get immediately "fixed" to pass instead of being investigated
- Missing modern type hints and pattern matching
- Implementation that starts before understanding requirements

With this plugin, Claude applies consistent Python 3.11+ standards and routes to specialist skills automatically.

## What You Get

With this plugin installed, Claude will:

- **Plan before coding**: Discovery and analysis phases before implementation
- **Write modern Python 3.11+**: Native generics (`list[str]`), union types (`str | None`), pattern matching
- **Use proven libraries**: Typer + Rich for CLIs, pytest-mock for testing, httpx for HTTP, pydantic for validation
- **Follow consistent structure**: `pyproject.toml` with Hatchling, `uv` for dependency management
- **Investigate test failures**: Balanced approach that considers both test issues and real bugs
- **Apply quality workflows**: Integrated ruff linting, ty type checking, and pytest

## Commands

### Code Quality

| Command | Purpose |
|---------|---------|
| `/python3-development:shebangpython scripts/*.py` | Validate Python shebangs and PEP 723 metadata |
| `/python3-development:modernpython src/module.py` | Apply modern Python 3.11+ patterns |
| `/python3-development:stinkysnake src/` | Nine-phase quality improvement (analysis → planning → implementation) |
| `/python3-development:snakepolish src/` | Implementation phase for stinkysnake |
| `/python3-development:python3-review src/` | Comprehensive code review |

### Feature Development

| Command | Purpose |
|---------|---------|
| `/python3-development:python3-add-feature "Add CSV export"` | Guided feature addition with TDD |
| `/python3-development:create-feature-task "OAuth2 login"` | Structure feature development with tracking |

### Testing

| Command | Purpose |
|---------|---------|
| `/python3-development:comprehensive-test-review tests/` | Audit test quality and coverage |
| `/python3-development:analyze-test-failures test_auth.py` | Investigate failing tests systematically |

### Packaging & Publishing

| Command | Purpose |
|---------|---------|
| `/python3-development:python3-packaging` | Configure `pyproject.toml` |
| `/python3-development:python3-publish-release-pipeline github` | Set up CI/CD for PyPI |

### Debugging

| Command | Purpose |
|---------|---------|
| `/python3-development:python3-bug "feature X not working"` | Debug functional issues with logs and specs |

## Automatic Behaviors

Once installed, Claude automatically applies these patterns when working with Python code:

**Modern Python Syntax:**

- Uses `list[str]` instead of `List[str]`
- Applies `str | None` instead of `Optional[str]`
- Leverages pattern matching for complex conditionals
- Implements proper `async/await` patterns for I/O-bound work

**Library Defaults:**

- CLI apps: Typer + Rich
- HTTP clients: httpx
- Configuration: pydantic-settings
- Testing: pytest + pytest-mock + hypothesis

**Tooling Defaults:**

- `uv` for dependency management
- `ruff` for linting and formatting
- `ty` for type checking (switches to `mypy` if the project already uses it)
- Hatchling build backend
- PEP 723 inline metadata for standalone scripts

## Specialized Skills

| Skill | Domain |
|-------|--------|
| `python3-development` | Core orchestration and modern Python patterns |
| `orchestrate` | Multi-step engineering workflow with SAM tracking |
| `specialist-skill-routing` | Routes Typer, Rich, Textual, FastMCP, TOML tasks |
| `python3-test-design` | Test suite architecture and strategy |
| `async-python-patterns` | asyncio, gather, queues, WebSocket |
| `uv` | Astral uv package manager guidance |
| `hatchling` | Hatchling build backend configuration |
| `mkdocs` | MkDocs documentation with Material theme |
| `pre-commit` | Configure `.pre-commit-config.yaml` |
| `pypi-readme-creator` | Generate PyPI-compliant README files |
| `toml-python` | TOML editing with tomlkit |
| `ty` | Astral ty type checker |
| `typer` | Typer CLI framework patterns |
| `typer-and-rich` | Typer + Rich integration and testing |
| `textual` | Textual TUI framework |
| `modernpython` | PEP-by-PEP Python 3.11+ modernization |
| `shebangpython` | Shebang and PEP 723 validation |
| `stinkysnake` | Progressive quality improvement |
| `snakepolish` | Implementation phase for stinkysnake |
| `comprehensive-test-review` | Audit test quality and coverage |
| `analyze-test-failures` | Investigate failing tests systematically |
| `python3-packaging` | Configure `pyproject.toml` and packaging |
| `python3-publish-release-pipeline` | CI/CD pipeline for PyPI |

## Agents in This Plugin

| Agent | Role |
|-------|------|
| `python-cli-architect` | Implements Python CLI features (Typer/Rich) |
| `python-cli-design-spec` | Produces architecture specs for Python CLIs |
| `python-pytest-architect` | Writes pytest test suites |
| `code-reviewer` | Code review with Python quality and idiom awareness |
| `semantic-code-search` | Searches codebase by behavior, not just keywords |

## Shared Workflow Agents (development-harness)

Language-agnostic planning and verification agents are in the `development-harness` plugin. Use `@dh:` prefix:

| Agent | Role |
|-------|------|
| `@dh:feature-researcher` | Research features, produce discovery context |
| `@dh:codebase-analyzer` | Explore patterns, write structured analysis |
| `@dh:context-gathering` | Gather context for implementation |
| `@dh:plan-validator` | Validate implementation plans |
| `@dh:feature-verifier` | Goal-backward verification after implementation |
| `@dh:swarm-task-planner` | Decompose features into structured task plans |

## Example

**Without this plugin:**

You say: "Build a CLI tool to process CSV files"

Claude creates `argparse`-based CLI with `List[str]` syntax, puts code in `src/`, and immediately modifies tests to pass.

**With this plugin:**

Claude:

1. Checks existing project structure and dependencies
2. Implements with Typer + Rich, using `list[str]` and `str | None` native syntax
3. Writes pytest tests before implementation
4. When a test fails, analyzes whether it is a test bug or a real bug before deciding what to change

## Installation

First, add the marketplace (one-time setup):

```bash
/plugin marketplace add Jamie-BitFlight/claude_skills
```

Then install the plugin:

```bash
/plugin install python3-development@jamie-bitflight-skills
```

## Relationship to python-engineering

This plugin and `python-engineering` share many skills. Each also has unique skills the other does not:

**Only in `python3-development`**:
`stdlib-scripting`, `semantic-code-search`, `python-cli-architect`, `rich`, `python3-bug`, `python3-review`, `implementation-manager`, `use-command-template`, `python3-development-meta-docs`, `python3-development`

**Only in `python-engineering`**:
`python3-core`, `python3-typing`, `python3-tdd`, `python3-testing`, `python3-tools`, `python3-cli`, `python3-web`, `python3-data`, `python3-stdlib-only`, `debug`, `lint`, `review`, `cleanup`, `designing-ui-for-cli`, `orchestrating-python-development`, `python-cross-platform-smoothing`, `standards-for-python-development`, `python3-stdlib-only`

Install both plugins for full coverage. `stdlib-scripting` — which provides Claude with stdlib-only scripting patterns — is only available in this plugin.

## Requirements

- Claude Code v2.0+
- Python 3.11+ recommended
