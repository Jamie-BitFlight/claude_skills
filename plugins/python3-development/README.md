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

## What You Get

With this plugin installed, Claude will:

- **Plan before coding**: Discovery and analysis phases before implementation
- **Write modern Python 3.11+**: Native generics (`list[str]`), union types (`str | None`), pattern matching
- **Use proven libraries**: Typer+Rich for CLIs, pytest-mock for testing, httpx for HTTP, pydantic for validation
- **Follow consistent structure**: `packages/` directory layout, hatchling build system, proper type hints
- **Investigate test failures**: Balanced approach that considers both test issues and real bugs
- **Apply quality workflows**: Integrated linting (ruff), formatting, type checking (ty by default; mypy when the project already uses it), and testing (pytest)
- **Reference 50+ modern libraries**: Built-in guidance for asyncio, FastAPI, SQLAlchemy, and more

## Commands

Run these commands directly to trigger specific workflows:

### Code Quality

| Command | Purpose | Example |
|---------|---------|---------|
| `/python3-development:shebangpython` | Validate Python shebangs and PEP 723 metadata | `/python3-development:shebangpython scripts/*.py` |
| `/python3-development:modernpython` | Apply modern Python 3.11+ patterns | `/python3-development:modernpython src/module.py` |
| `/python3-development:stinkysnake` | Progressive quality improvement (analysis → planning → implementation) | `/python3-development:stinkysnake src/` |
| `/python3-development:snakepolish` | Implementation phase for stinkysnake (runs until tests pass) | `/python3-development:snakepolish src/` |
| `/python3-development:python3-review` | Comprehensive code review | `/python3-development:python3-review src/` |

### Feature Development

| Command | Purpose | Example |
|---------|---------|---------|
| `/python3-development:python3-add-feature` | Guided feature addition with TDD | `/python3-development:python3-add-feature Add CSV export` |
| `/python3-development:create-feature-task` | Structure feature development with tracking | `/python3-development:create-feature-task OAuth2 login` |
| `/dh:add-new-feature` | SAM-style feature workflow (discovery → analysis → tasks) | `/dh:add-new-feature user authentication` |
| `/dh:implement-feature` | Execute SAM task plan by delegating ready tasks | `/dh:implement-feature auth` (feature slug) |
| `/dh:start-task` | Start or complete specific task in SAM task file | `/dh:start-task auth --task 1.1` (feature slug) |
| `/dh:complete-implementation` | Holistic completion (review, verify, integrate, document) | `/dh:complete-implementation auth` (feature slug) |

### Testing

| Command | Purpose | Example |
|---------|---------|---------|
| `/python3-development:comprehensive-test-review` | Audit test quality and coverage | `/python3-development:comprehensive-test-review tests/` |
| `/python3-development:analyze-test-failures` | Investigate failing tests systematically | `/python3-development:analyze-test-failures test_auth.py` |
| `/python3-development:test-failure-mindset` | Set balanced test investigation approach | `/python3-development:test-failure-mindset` |

### Packaging & Publishing

| Command | Purpose | Example |
|---------|---------|---------|
| `/python3-development:python3-packaging` | Configure pyproject.toml | `/python3-development:python3-packaging` |
| `/python3-development:python3-publish-release-pipeline` | Set up CI/CD for PyPI | `/python3-development:python3-publish-release-pipeline github` |

### Debugging & Task Management

| Command | Purpose | Example |
|---------|---------|---------|
| `/python3-development:python3-bug` | Debug functional issues with logs and specs | `/python3-development:python3-bug "feature X not working"` |
| `/python3-development:use-command-template` | Create new skills from templates | `/python3-development:use-command-template "API client wrapper"` |

## Claude Improvements

### Automatic Behaviors

Once installed, Claude automatically applies these improvements when working with Python code:

**Modern Python Patterns**:
- Uses `list[str]` instead of `List[str]`
- Applies `str | None` instead of `Optional[str]`
- Leverages pattern matching for complex conditionals
- Implements proper `async/await` patterns for I/O-bound work

**Library Selection**:
- CLI apps: Typer + Rich (progress bars, formatted output)
- HTTP clients: httpx (async support, modern API)
- JSON handling: orjson (faster than stdlib)
- Configuration: pydantic-settings (typed config)
- Testing: pytest + pytest-mock + hypothesis

**Project Structure**:
- `packages/` directory for multi-package repos
- `pyproject.toml` with hatchling build backend
- `uv` for dependency management (10-100x faster than pip)
- PEP 723 inline metadata for standalone scripts

**Testing Philosophy**:
- Investigates failures instead of auto-fixing tests
- Considers both test bugs and implementation bugs
- Writes tests before implementation (TDD)
- Uses mutation testing for critical code paths

**Code Quality**:
- Runs ruff for linting and formatting
- Uses **ty** for type checking by default; keeps **mypy** when the project already configures it (no forced migration)
- Eliminates `Any` types progressively
- Follows DRY and SRP principles

### Specialized Skills

The plugin includes 34 skills that guide Claude's behavior:

| Skill | What It Does |
|-------|--------------|
| `python3-development` | Core orchestration and modern Python patterns |
| `python3-test-design` | Test suite architecture and strategy |
| `async-python-patterns` | Master asyncio and async/await for high-performance apps |
| `uv` | Astral uv package manager expert guidance |
| `hatchling` | Comprehensive hatchling build backend documentation |
| `mkdocs` | MkDocs documentation project creation and management |
| `pre-commit` | Configure git hooks using pre-commit or prek |
| `pypi-readme-creator` | Generate PyPI-compliant README files |
| `toml-python` | Work with TOML using tomlkit (preserves formatting) |
| `stdlib-scripting` | Stdlib-only scripting for restricted environments |
| `ty` | Astral ty type checker guidance |

| `comprehensive-test-review` | Audit test quality and coverage |
| `analyze-test-failures` | Investigate failing tests systematically |
| `test-failure-mindset` | Set balanced test investigation approach |

And more specialized skills for code review, packaging, bug fixing, and feature development.

> Task management and planning skills (`implementation-manager`, `planner-rt-ica`, `clear-cove-task-design`, `generate-task`, `validation-protocol`) were moved to the `development-harness` plugin. Use `/dh:` prefix for those skills.

### Specialized Agents

The plugin provides 6 Python-specific agents:

| Agent | Specialization |
|-------|----------------|
| `python-cli-architect` | Build CLIs with Typer and Rich |
| `python-cli-design-spec` | Produce architecture specs for Python CLIs |
| `python-pytest-architect` | Create and modernize test suites |
| `code-reviewer` | General code review with Python awareness, quality, and idioms |
| `semantic-code-search` | Semantic search over Python codebases |

### Shared Workflow Agents (development-harness)

12 language-agnostic agents were moved to the `development-harness` plugin during the
deduplication refactor. Invoke them with the `@dh:` prefix:

| Agent | Specialization |
|-------|----------------|
| `@dh:feature-researcher` | Research features and produce discovery context |
| `@dh:codebase-analyzer` | Explore patterns and write structured analysis |
| `@dh:context-gathering` | Gather comprehensive context for implementation |
| `@dh:context-refinement` | Update task context with implementation discoveries |
| `@dh:plan-validator` | Validate implementation plans before execution |
| `@dh:feature-verifier` | Goal-backward verification after implementation |
| `@dh:integration-checker` | Verify cross-module integration and end-to-end flows |
| `@dh:doc-drift-auditor` | Audit documentation accuracy against code |
| `@dh:swarm-task-planner` | Decompose features into structured task plans |
| `@dh:ecosystem-researcher` | Research domain ecosystems and technology landscapes |
| `@dh:t0-baseline-capture` | Capture baseline metrics before implementation |
| `@dh:tn-verification-gate` | Verify acceptance criteria post-implementation |

## Installation

First, add the marketplace (one-time setup):

```bash
/plugin marketplace add Jamie-BitFlight/claude_skills
```

Then install the plugin:

```bash
/plugin install python3-development@jamie-bitflight-skills
```

## Usage

Just install it - Claude uses it automatically when working with Python code.

### With Commands

Invoke specific workflows directly:

```bash
# Improve code quality progressively
/python3-development:stinkysnake src/myapp/

# Add a new feature with TDD
/python3-development:python3-add-feature "Add rate limiting to API"

# Review test coverage
/python3-development:comprehensive-test-review tests/

# Set up PyPI publishing
/python3-development:python3-publish-release-pipeline github
```

### Automatic Application

Claude automatically uses this plugin when you:

- Ask to create Python files
- Request code reviews
- Work with Python projects
- Debug Python issues
- Add features to Python codebases

## Example

**Without this plugin**:

You say: "Build a CLI tool to process CSV files"

Claude creates:
- `argparse` for CLI (verbose, dated API)
- Plain text output
- `List[str]` and `Optional[str]` syntax
- Code in `src/` directory
- When test fails, immediately changes test to match implementation

**With this plugin**:

Same request, but Claude:

1. **Gathers context**: Checks for existing project structure, dependencies
2. **Plans approach**: Designs CLI with Typer, identifies output format needs
3. **Implements modern code**:
   - Typer + Rich (progress bars, formatted tables)
   - `list[str]` and `str | None` native syntax
   - Code in `packages/csv_tool/`
   - Comprehensive type hints
   - PEP 723 metadata for standalone script option
4. **Tests first**: Writes pytest tests before implementation
5. **Investigates failures**: When test fails, analyzes whether it's a test bug or real bug before deciding what to fix

## Reference Documentation

The plugin includes extensive reference documentation:

- **50+ Modern Python Libraries**: Usage patterns and best practices for asyncio, FastAPI, SQLAlchemy, pydantic, httpx, typer, rich, and more
- **User Project Conventions**: Extracted patterns from real-world production projects
- **Tool & Library Registry**: Development tools for linting, testing, build automation
- **API References**: Integration guides for common APIs
- **Workflow Patterns**: TDD, feature addition, refactoring, code review

## Requirements

- Claude Code v2.0+
- Python 3.11+ recommended (for modern syntax patterns)

## Development Continuity

If interrupted mid-development and need to resume workflow work (command→skill migration, vendoring):

- [Workflow Port Plan](./skills/python3-development/planning/python3-development-workflow-port-plan.md)

---

> **The Ancient Woe**
>
> *The agony of commissioning a grand stone castle, only to realize thy masons are using spoons instead of chisels, and nobody brought a parchment of the blueprints!*

> **The Bard's Decree**
>
> *"Out, damned chaos! I demand a master architect who measures twice, cuts once, and builds upon a foundation of unyielding stone, lest the tempest blow our manor to the mud!"*
