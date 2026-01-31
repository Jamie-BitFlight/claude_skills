# copier-astral - Python Project Template with Astral Toolchain

**Research Date**: January 31, 2026
**Source URL**: <https://ritwiktiwari.github.io/copier-astral/>
**GitHub Repository**: <https://github.com/ritwiktiwari/copier-astral>
**Documentation**: <https://ritwiktiwari.github.io/copier-astral/>
**Version at Research**: v1.1
**License**: MIT

---

## Overview

copier-astral is an opinionated Copier template for bootstrapping Python projects using Astral's modern toolchain. It provides batteries-included project scaffolding with linting (ruff), type checking (ty), package management (uv), testing (pytest + hatch), documentation (MkDocs), CLI framework (Typer), and CI/CD (GitHub Actions) pre-configured and ready to use.

**Core Value Proposition**: Generate production-ready Python project structure in seconds with modern Astral tooling (uv, ruff, ty) instead of legacy pip/flake8/mypy, eliminating hours of boilerplate configuration.

---

## Problem Addressed

| Problem | How copier-astral Solves It |
|---------|----------------------------|
| Setting up Python projects requires extensive boilerplate | Single command generates complete project with all tooling configured |
| Legacy tooling (pip, flake8, mypy) is slow and fragmented | Uses Astral's unified toolchain: uv (10-100x faster), ruff (replaces flake8/black/isort), ty (fast type checker) |
| Inconsistent project structures across teams | Enforces standardized layout with best practices baked in |
| CI/CD setup is repetitive and error-prone | Pre-configured GitHub Actions for testing, linting, publishing |
| Documentation setup is tedious | MkDocs with Material theme and mkdocstrings ready to deploy |
| Multi-Python version testing is complex | Hatch envs with matrix testing across Python 3.10-3.13 |
| Project updates don't flow back to generated code | Copier update mechanism allows syncing template improvements |

---

## Key Statistics (as of January 31, 2026)

| Metric | Value |
|--------|-------|
| GitHub Stars | 6 |
| Forks | 0 |
| Open Issues | 3 |
| Primary Language | Jinja |
| Created | January 28, 2026 |
| Latest Release | v1.1 (January 31, 2026) |
| License | MIT |
| Repository Size | 1,539 KB |

---

## Key Features

### 1. Astral Toolchain Integration

| Tool | Purpose | Benefit |
|------|---------|---------|
| **uv** | Package management, venv, dependencies | 10-100x faster than pip |
| **ty** | Type checking | Astral's new fast type checker |
| **ruff** | Linting + formatting | Replaces flake8, black, isort in single tool |

### 2. Testing Infrastructure

- **pytest**: Industry-standard test framework
- **hatch**: Multi-version testing with matrix envs
- **pytest-cov**: Coverage reporting with Codecov integration
- **Matrix testing**: Python 3.10, 3.11, 3.12, 3.13 support

### 3. Documentation

- **MkDocs**: Static site generator
- **Material theme**: Modern, responsive documentation
- **mkdocstrings**: Auto-generate API docs from docstrings
- **GitHub Pages**: Automatic deployment via Actions

### 4. CLI Support (Optional)

- **Typer**: Modern CLI framework with type hints
- Pre-configured entry point in pyproject.toml
- Help text and command structure ready

### 5. CI/CD Workflows

- **Test workflow**: Runs on PR and push to main
- **Lint workflow**: Ruff + ty checks
- **Docs workflow**: Build and deploy to GitHub Pages
- **Release workflow**: Automatic PyPI publishing on tag
- **Codecov integration**: Coverage badge and reports

### 6. Containerization (Optional)

- **Dockerfile**: Multi-stage build for minimal image size
- **Docker Compose**: Development environment setup
- Production-ready container configuration

### 7. Code Quality

- **pre-commit hooks**: Enforced formatting and linting
- **Ruff configuration**: Comprehensive rule set in pyproject.toml
- **Type annotations**: Strict typing enforced by ty

### 8. Template Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `project_name` | string | - | Human-readable project name |
| `project_description` | string | "A Python package" | Short description |
| `project_slug` | string | derived | Python package name |
| `python_version` | choice | 3.12 | Minimum Python (3.10-3.13) |
| `python_versions_matrix` | string | "3.10,3.11,3.12,3.13" | CI matrix versions |
| `include_cli` | bool | true | Include Typer CLI |
| `include_github_actions` | bool | true | Include CI/CD workflows |
| `include_docker` | bool | true | Include Dockerfile |
| `include_docs` | bool | true | Include MkDocs |
| `include_precommit` | bool | true | Include pre-commit hooks |
| `include_codecov` | bool | true | Include Codecov |
| `include_pypi_publish` | bool | true | Include PyPI publishing |
| `license` | choice | MIT | MIT, Apache-2.0, GPL-3.0, BSD-3-Clause, ISC, Proprietary |

---

## Technical Architecture

```text
copier copy --trust gh:ritwiktiwari/copier-astral my-project
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│                 Copier Template Engine                   │
│  ┌─────────────────────────────────────────────────┐    │
│  │           Interactive Prompts                    │    │
│  │  - Project metadata (name, author, license)      │    │
│  │  - Feature toggles (CLI, Docker, docs)           │    │
│  │  - Python version selection                      │    │
│  └─────────────────────────────────────────────────┘    │
│                         │                                │
│                         ▼                                │
│  ┌─────────────────────────────────────────────────┐    │
│  │           Jinja2 Template Processing             │    │
│  │  - copier-template-extensions for slug/git info  │    │
│  │  - Conditional file inclusion based on options   │    │
│  │  - Variable substitution in all files            │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│              Generated Project Structure                 │
│                                                         │
│  my-project/                                            │
│  ├── src/my_project/                                    │
│  │   ├── __init__.py                                    │
│  │   ├── main.py                                        │
│  │   └── cli.py (if include_cli)                        │
│  ├── tests/                                             │
│  │   └── test_main.py                                   │
│  ├── docs/ (if include_docs)                            │
│  ├── .github/workflows/ (if include_github_actions)     │
│  ├── Dockerfile (if include_docker)                     │
│  ├── pyproject.toml                                     │
│  ├── Makefile                                           │
│  └── .pre-commit-config.yaml (if include_precommit)     │
└─────────────────────────────────────────────────────────┘
```

---

## Installation & Usage

### Prerequisites

```bash
# Install Copier
pip install copier

# Install required extension for custom Jinja2 filters
pip install copier-template-extensions
```

### Generate a Project

```bash
# From GitHub (recommended)
copier copy --trust gh:ritwiktiwari/copier-astral my-project

# From local clone
copier copy --trust /path/to/copier-astral my-project
```

**Note**: The `--trust` flag is required because the template uses custom Jinja2 extensions for auto-detecting git user info and generating slugified package names.

### Post-Generation Setup

```bash
cd my-project

# Initialize git and install dependencies
git init -b main
make install

# Activate virtual environment
source .venv/bin/activate

# Install pre-commit hooks (if enabled)
pre-commit install
uv run pre-commit run -a

# Verify everything works
make verify
make test
```

### Development Commands

| Command | Description |
|---------|-------------|
| `make install` | Install all dependencies |
| `make verify` | Run all checks (lint, format, type-check) |
| `make fix` | Auto-fix lint and format issues |
| `make test` | Run tests |
| `make test-cov` | Run tests with coverage |
| `make test-matrix` | Run tests across all Python versions |
| `make docs` | Build documentation |
| `make docs-serve` | Serve documentation locally |

### Releasing

```bash
# Create version tag (triggers PyPI publish workflow)
git tag v0.1.0
git push --tags
```

### Updating Existing Projects

```bash
# Sync with latest template improvements
copier update --trust
```

---

## Generated Project Structure

```text
my-project/
├── src/
│   └── my_project/
│       ├── __init__.py          # Package version
│       ├── main.py              # Core module
│       └── cli.py               # Typer CLI (optional)
├── tests/
│   └── test_main.py             # Test examples
├── docs/                        # MkDocs (optional)
│   ├── index.md
│   └── api.md
├── .github/
│   └── workflows/               # CI/CD (optional)
│       ├── test.yml
│       ├── lint.yml
│       ├── docs.yml
│       └── release.yml
├── .pre-commit-config.yaml      # Pre-commit hooks (optional)
├── Dockerfile                   # Container (optional)
├── docker-compose.yml           # Dev environment (optional)
├── pyproject.toml               # Project config (uv, ruff, hatch)
├── Makefile                     # Dev commands
├── LICENSE
└── README.md
```

---

## Relevance to Claude Code Development

### Direct Applications

1. **Plugin Scaffolding**: Use as base template for generating new Claude Code plugins with consistent structure
2. **Skill Development**: Bootstrap Python-based skills with proper testing and type checking
3. **MCP Server Templates**: Foundation for creating MCP servers with Astral tooling
4. **Agent Infrastructure**: Scaffold agent implementations with production-ready CI/CD

### Patterns Worth Adopting

1. **Astral Toolchain**: uv + ruff + ty combination is significantly faster than legacy pip + flake8 + mypy
2. **Makefile Abstraction**: Simple `make verify`, `make test` commands abstract complex uv/hatch invocations
3. **Copier Update Mechanism**: Template improvements can propagate to existing projects via `copier update`
4. **Feature Toggles**: Conditional file generation based on boolean options is clean for customization
5. **Matrix Testing**: Hatch envs for multi-Python testing without Docker complexity
6. **Single Source of Truth**: pyproject.toml contains all tool configurations (ruff, pytest, hatch, etc.)

### Integration Opportunities

1. **claude-code-plugin-template**: Fork/adapt for Claude Code plugin-specific scaffolding
2. **mcp-server-template**: Specialize for MCP server projects with FastMCP defaults
3. **skill-template**: Create skill-specific variant with SKILL.md and references/ structure
4. **Pre-commit Integration**: This repo already uses prek - could sync ruff configurations

### Key Insight

copier-astral demonstrates the modern Python tooling stack that Claude Code-related projects should adopt. The Astral toolchain (uv, ruff, ty) provides 10-100x performance improvements over legacy tools while maintaining compatibility. The Copier template mechanism allows project structure standardization with the ability to propagate improvements to existing projects - a pattern applicable to Claude Code plugin/skill templates.

---

## References

1. **Documentation Site**: <https://ritwiktiwari.github.io/copier-astral/> (accessed 2026-01-31)
2. **GitHub Repository**: <https://github.com/ritwiktiwari/copier-astral> (accessed 2026-01-31)
3. **User Guide**: <https://ritwiktiwari.github.io/copier-astral/guide/> (accessed 2026-01-31)
4. **Template Options**: <https://ritwiktiwari.github.io/copier-astral/options/> (accessed 2026-01-31)
5. **Copier Documentation**: <https://copier.readthedocs.io/> (accessed 2026-01-31)
6. **uv Documentation**: <https://docs.astral.sh/uv/> (accessed 2026-01-31)
7. **ruff Documentation**: <https://docs.astral.sh/ruff/> (accessed 2026-01-31)
8. **ty Documentation**: <https://docs.astral.sh/ty/> (accessed 2026-01-31)
9. **Typer Documentation**: <https://typer.tiangolo.com/> (accessed 2026-01-31)
10. **MkDocs Material**: <https://squidfunk.github.io/mkdocs-material/> (accessed 2026-01-31)

---

## Related Tools

| Tool | Relationship |
|------|--------------|
| [cookiecutter](https://github.com/cookiecutter/cookiecutter) | Original Python project template tool (Copier is successor) |
| [copier](https://github.com/copier-org/copier) | Template engine this project uses |
| [python-project-template](https://github.com/rochacbruno/python-project-template) | Alternative Copier template without Astral tooling |
| [cruft](https://github.com/cruft/cruft) | Cookiecutter with update capability (similar to Copier) |
| [hatch](https://hatch.pypa.io/) | Python project manager used for multi-version testing |

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | 2026-01-31 |
| Version at Verification | v1.1 |
| GitHub Stars at Verification | 6 |
| Next Review Recommended | 2026-04-30 (3 months) |

**Change Detection Indicators**:

- Monitor GitHub releases for version changes
- Check for new template options added
- Review pyproject.toml for tooling version updates
- Track Astral toolchain releases (uv, ruff, ty)
- Watch for breaking changes in Copier template syntax
