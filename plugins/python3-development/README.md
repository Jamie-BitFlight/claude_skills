# Python Development

Teaches Claude modern Python 3.11+ patterns and your preferred workflows.

## Why Install This?

When you ask Claude to write Python code, Claude sometimes:

- Uses outdated syntax (old typing patterns, Python 3.8 style)
- Picks random libraries instead of ones that work well together
- Creates inconsistent project structures across different projects
- Immediately fixes tests to make them pass without investigating why they failed
- Doesn't follow conventions you use in your existing projects
- Jumps into implementation without proper planning

## What Changes

With this plugin installed, Claude will:

- **Plan before coding**: Every task starts with discovery and planning phases
- **Write modern Python 3.11+**: Native generics, union types with `|`, pattern matching
- **Use proven library combinations**: Typer+Rich for CLIs, pytest-mock for testing
- **Follow consistent project structure**: `packages/` directory, hatchling build system
- **Investigate test failures**: Balanced approach considers both test bugs and implementation bugs
- **Apply quality workflows**: Linting, formatting, type checking, and testing
- **Reference 50+ libraries**: Modern Python modules with usage guidance

## User-Invocable Commands

Run these commands directly to trigger specific workflows:

| Command                             | Purpose                                                              | Example                                    |
| ----------------------------------- | -------------------------------------------------------------------- | ------------------------------------------ |
| `/shebangpython`                    | Validate Python shebangs and PEP 723 metadata                        | `/shebangpython scripts/*.py`              |
| `/modernpython`                     | Apply modern Python 3.11+ patterns                                   | `/modernpython src/module.py`              |
| `/python3-add-feature`              | Guided feature addition with TDD                                     | `/python3-add-feature Add CSV export`      |
| `/python3-review`                   | Comprehensive code review                                            | `/python3-review src/`                     |
| `/stinkysnake`                      | Progressive quality improvement (code smells, architecture, linting) | `/stinkysnake src/`                        |
| `/snakepolish`                      | Implementation phase for stinkysnake (runs until tests pass)         | `/snakepolish src/`                        |
| `/python3-bug`                      | Debug functional issues with logs and specs                          | `/python3-bug "feature X not working"`     |
| `/python3-packaging`                | Configure pyproject.toml                                             | `/python3-packaging`                       |
| `/python3-publish-release-pipeline` | Set up CI/CD for PyPI                                                | `/python3-publish-release-pipeline github` |
| `/comprehensive-test-review`        | Audit test quality                                                   | `/comprehensive-test-review tests/`        |
| `/analyze-test-failures`            | Investigate failing tests                                            | `/analyze-test-failures test_auth.py`      |
| `/test-failure-mindset`             | Set balanced test investigation approach                             | `/test-failure-mindset`                    |
| `/create-feature-task`              | Structure feature development                                        | `/create-feature-task OAuth2 login`        |

## Skills

| Skill                              | Purpose                                                              |
| ---------------------------------- | -------------------------------------------------------------------- |
| `python3-development`              | Core orchestration and modern Python patterns                        |
| `python3-test-design`              | Test suite architecture and strategy                                 |
| `shebangpython`                    | Shebang validation and PEP 723 metadata                              |
| `modernpython`                     | Modern Python 3.11+ patterns and transformations                     |
| `python3-add-feature`              | Guided feature addition workflow                                     |
| `python3-review`                   | Comprehensive code review checklist                                  |
| `stinkysnake`                      | Progressive quality improvement (code smells, architecture, linting) |
| `snakepolish`                      | Implementation phase - implements functions until tests pass         |
| `python3-bug`                      | Debug functional issues using specs, logs, and observed behavior     |
| `python3-packaging`                | pyproject.toml and packaging configuration                           |
| `python3-publish-release-pipeline` | CI/CD pipeline for PyPI publishing                                   |
| `comprehensive-test-review`        | Test quality auditing                                                |
| `analyze-test-failures`            | Investigate failing tests                                            |
| `test-failure-mindset`             | Set balanced investigative approach                                  |
| `create-feature-task`              | Structure feature development                                        |
| `use-command-template`             | Create new skills from templates                                     |
| `async-python-patterns`            | Master asyncio and async/await patterns for high-performance apps    |
| `clear-cove-task-design`           | Write and lint agent task files with CLEAR + CoVe methodology        |
| `generate-task`                    | Generate single worker task prompts using CLEAR + CoVe standards     |
| `hatchling`                        | Comprehensive Hatchling build backend documentation                  |
| `implementation-manager`           | Query and manage feature implementation task status                  |
| `mkdocs`                           | MkDocs documentation project creation and management                 |
| `planner-rt-ica`                   | Planning-phase input completeness analysis for safe planning         |
| `pre-commit`                       | Configure git hooks using pre-commit or prek frameworks              |
| `pypi-readme-creator`              | Generate PyPI-compliant README files in Markdown or RST              |
| `toml-python`                      | Work with TOML files using tomlkit (preserves comments/formatting)   |
| `uv`                               | Astral uv package and project manager expert guidance                |
| `validation-protocol`              | Scientific validation protocol for verifying fixes work              |

## Agents

| Agent                     | Purpose                                                  |
| ------------------------- | -------------------------------------------------------- |
| `python-cli-architect`    | Build CLIs with Typer and Rich                           |
| `python-pytest-architect` | Create and modernize test suites                         |
| `python-code-reviewer`    | Review code for quality and best practices               |
| `python-cli-design-spec`  | Design CLI architecture (WHAT, not HOW)                  |
| `swarm-task-planner`      | Break down complex tasks for parallel execution          |
| `codebase-analyzer`       | Explore codebase patterns and write structured analysis  |
| `context-gathering`       | Gather comprehensive context for task implementation     |
| `context-refinement`      | Update task context with discoveries from implementation |
| `doc-drift-auditor`       | Audit documentation accuracy against implementation      |
| `feature-researcher`      | Research feature requests and produce discovery context  |
| `feature-verifier`        | Goal-backward verification after feature implementation  |
| `integration-checker`     | Verify cross-module integration and end-to-end flows     |
| `plan-validator`          | Validate implementation plans before execution           |
| `service-documentation`   | Update CLAUDE.md and module documentation                |

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

Just install it - Claude uses it automatically when working with Python code. You'll notice:

- **Task Planning**: Claude gathers context and plans before implementing
- **Modern Code**: Cleaner Python 3.11+ syntax throughout
- **Consistent Structure**: `packages/` layout, proper typing
- **Better Testing**: pytest-mock, hypothesis, mutation testing for critical code
- **Quality Gates**: Linting, formatting, and type checking integrated

## Development continuity (power-outage safe plan)

If you were interrupted mid-development and want a checkpointed, resume-friendly plan to complete the ongoing workflow work (including command→skill migration and vendoring external artifacts), follow:

- [Workflow Port Plan](./skills/python3-development/planning/python3-development-workflow-port-plan.md)

## Example

**Without this plugin**: You say "build a CLI tool to process CSV files". Claude creates it with argparse, prints plain text, uses `List[str]` syntax, puts code in `src/`, and when a test fails, immediately changes the test to match the implementation.

**With this plugin**: Same request, but Claude first gathers context and plans the approach. Then it uses Typer+Rich (progress bars, formatted tables), writes `list[str]` with native generics, puts code in `packages/csv_tool/`, includes comprehensive type hints, and when a test fails, investigates whether the test caught a real bug before deciding what to fix.

## Requirements

- Claude Code v2.0+
