---
title: "Claude CodePro"
subtitle: "Containerized Claude Code dev environment with modular rules, hooks, and MCP integrations"
category: "developer-tools"
resource_url: "https://github.com/lcatlett/claude-codepro"
github_url: "https://github.com/lcatlett/claude-codepro"
date_created: "2026-05-25"
date_last_reviewed: "2026-05-25"
status: published
---

# Claude CodePro

## Overview

Claude CodePro is a professional development environment framework designed specifically for Claude Code users. It provides a pre-configured, containerized setup with modular rules, intelligent hooks, MCP server integrations, and domain-specific skills for full-stack development workflows. The project emphasizes spec-driven development with test-driven discipline through Claude Code's slash commands (/setup, /plan, /implement, /verify).

**Key Identity**:
- Name: claude-codepro
- Version: 1.0.0 (released 2026-01-06)
- Language: Python (>= 3.12, < 3.13)
- License: GNU Affero General Public License v3.0
- Author: Max Ritter (@maxritter)
- Website: <https://claude-code.pro>

SOURCE: README.md (accessed 2026-05-25), pyproject.toml (accessed 2026-05-25), LICENSE (accessed 2026-05-25)

## Problem Addressed

Claude CodePro solves context fragmentation and workflow inconsistency for Claude Code users. It addresses:

1. **Inconsistent coding standards** - Multiple projects use different linting, formatting, and type-checking rules
2. **Context management overhead** - AI agents lose productivity when context windows fill without guidance
3. **Quality assurance gaps** - Manual testing and quality checks slow development cycles
4. **Integration complexity** - Setting up LSP servers, MCP integrations, and IDE tools requires manual configuration
5. **Development environment isolation** - Local tool version conflicts prevent reliable reproduction of issues

The solution containerizes a pre-configured Linux environment with automated setup, enforcing conventions through modular rules, intelligent hooks, and integrated MCP servers.

SOURCE: README.md § "🛠️ Professional Development Environment for Claude Code (CC)", "📒 How-to-use" (accessed 2026-05-25)

## Key Statistics

| Metric | Value |
|--------|-------|
| Repository files | 81 files across code, config, and docs |
| Last commit | 2026-01-06T15:37:37Z |
| Python version | 3.12 (exactly) |
| Installation version reference | v3.3.8 (installation script) |
| License | GNU Affero General Public License v3.0 |
| Semantic release enabled | Yes (Angular preset with automatic versioning) |

NOTE: Repository metadata does not include public star count. GitHub URL points to lcatlett/claude-codepro, but README and install script reference maxritter/claude-codepro. Exact curator/fork relationship not documented in primary sources reviewed.

SOURCE: pyproject.toml [project] section (version 1.0.0), README.md § Installation (curl v3.3.8 reference), .releaserc.json (semantic-release configuration), git log (2026-01-06 timestamp), .devcontainer/devcontainer.json (node v22 constraint), LICENSE header (2025 copyright, Max Ritter)

## Key Features

### Spec-Driven Workflow via Slash Commands

Four core commands orchestrate development from spec to verification:

- **`/setup`** - Initializes project context, builds semantic search index of codebase, injects persistent memory via claude-mem
- **`/plan`** - Asks clarifying questions based on input, generates detailed specification with exact code signatures and requirements
- **`/implement`** - Executes specification with mandatory test-driven discipline (tests fail first), auto-manages context usage when approaching limit
- **`/verify`** - End-to-end verification of all acceptance criteria against tests, code quality checks, and security scanning

SOURCE: README.md § "📦 What's Inside > 📋 Spec-Driven Workflow via Slash Commands" (accessed 2026-05-25)

### Modular Rules System

Auto-loading rule files define project behavior without manual context injection:

- **Standard rules** in `.claude/rules/standard/` — Best practices for TDD, context management, documented in version control (auto-updated on claude-codepro updates)
- **Custom rules** in `.claude/rules/custom/` — Project-specific conventions never overwritten by updates
- **Path-specific rules** — YAML frontmatter enables scoping rules to file patterns (e.g., Python-specific rules for `src/**/*.py`)
- **Skills** — Domain-specific `@`-referenceable guides with names like `@backend-python-standards`, `@testing-writing-guidelines`, `@frontend-responsive-design-standards`
- **Auto-loading** — Claude Code automatically loads all `.claude/rules/*.md` as project memory on startup

Skill inventory: 12 documented skills spanning backend API standards, Python/migration standards, testing, and frontend (responsive design, accessibility, components, CSS).

SOURCE: README.md § "💡 Modular Rules System", `.claude/skills/` directory listing (12 SKILL.md files present in repository), ".claude/rules" folder structure (accessed 2026-05-25)

### Enhanced Context and Capabilities via MCP Servers

Three MCP servers are configured in the lcatlett fork's `.mcp.json` (the upstream maxritter project documents five servers including Claude Mem and MCP Lazy Loading, which are not present in this fork):

- **claude-context** - Semantic search across codebase via `@zilliz/claude-context-mcp@latest`
- **tavily** - Web search capabilities via `tavily-mcp@latest`
- **Ref** - Documentation and reference tools via `ref-tools-mcp@latest`

Configuration: `.mcp.json` declares servers; Claude Code loads them automatically on `/mcp` command.

SOURCE: .mcp.json file contents (accessed 2026-05-25) — lcatlett fork; README.md § "🔌 Enhanced Context and Capabilities via MCP Servers" (upstream maxritter, describes 5 servers)

### Intelligent Hooks for Quality, Standards, and Context

Five hook categories enforce discipline automatically:

- **Qlty Quality** - Post-edit hook: automated formatting and linting across all supported languages
- **Python Quality** - Post-edit hook: uv, ruff, mypy, basedpyright linting and type checking (optional, Python-specific)
- **TDD Enforcer** - Pre-edit hook: warns before modifying code without failing tests first
- **Context Monitor** - Post-tool hook: warns at 85% and 95% context usage
- **Claude Memory** - Various hooks: intelligently inject claude-mem context via persistent memory server (port 37777)

SOURCE: README.md § "🛠️ Intelligent Hooks for Quality, Standards and Context" (accessed 2026-05-25)

### One-Command Installation

Complete setup via automated script with containerization:

- **LSP Servers** - Python and TypeScript language servers for extended IDE code intelligence
- **Dev Container Required** - Isolated Linux environment (Alpine-based) with all tools pre-configured
- **Automated Setup Script** - Single command installs Docker image, configures IDE extensions, injects rules, initializes MCP servers
- **Shell Integration** - Auto-configures bash, fish, and zsh with `ccp` alias for launching Claude Code
- **IDE Compatible** - Works with VS Code, Cursor, Windsurf, and Antigravity (any IDE supporting Claude Code extension)

Installation via: `curl -fsSL https://raw.githubusercontent.com/maxritter/claude-codepro/v3.3.8/install.sh | bash`

SOURCE: README.md § "🏗️ One-Command Installation", installation script reference v3.3.8 (accessed 2026-05-25)

## Technical Architecture

### Container and Environment Setup

The development environment relies on dev containers with declarative configuration:

- **Dockerfile-based build** - `.devcontainer/devcontainer.json` specifies image construction
- **Container runtime name** - Uses project slug (e.g., `claude-codepro`) for consistent naming
- **Shared workspace** - `/workspaces/{{PROJECT_SLUG}}/` inside container maps to source directory
- **Port forwarding** - Port 37777 forwarded for claude-mem persistent memory server

### IDE Extensions (VS Code)

17 VS Code extensions pre-installed:

| Extension ID | Purpose |
|---|---|
| anthropic.claude-code | Claude Code IDE integration |
| charliermarsh.ruff | Python formatter/linter |
| dbaeumer.vscode-eslint | JavaScript/TypeScript linting |
| dotenv.dotenv-vscode | .env file syntax |
| esbenp.prettier-vscode | Multi-language code formatter |
| github.github-vscode-theme | GitHub theme |
| lumirelle.shell-format-rev | Shell script formatting |
| ms-python.debugpy | Python debugging |
| ms-python.mypy-type-checker | Python type checking |
| ms-python.python | Python language support |
| detachhead.basedpyright | Python type checker (alternative) |
| pkief.material-icon-theme | File icons |
| redhat.vscode-xml | XML support |
| redhat.vscode-yaml | YAML support |
| tamasfe.even-better-toml | TOML support |

SOURCE: .devcontainer/devcontainer.json § customizations.vscode.extensions (accessed 2026-05-25)

### Dev Container Features

Declarative features from devcontainer specification install tools and runtimes:

| Feature | Version | Purpose |
|---------|---------|---------|
| common-utils | 2 | zsh, oh-my-zsh, package upgrades |
| node | 22 | Node.js runtime (v22 required for Claude Code compatibility) |
| docker | 1 | Docker-outside-of-Docker for container operations |
| uv | latest | Python package manager and virtual environment |
| ruff | latest | Python linter/formatter |
| mypy | 2 | Python type checker |
| git | latest | Version control |

SOURCE: .devcontainer/devcontainer.json § features (accessed 2026-05-25). Note: Comment states "Claude Context is not compatible with later versions" of Node.js, constraining to v22.

### Code Components

The installer module provides CLI and configuration management:

- **cli.py** - Entry point for `ccp` command, handles initialization and launch
- **downloads.py** - Manages installer artifact downloads (Docker images, dependencies)
- **ui.py** - Terminal UI rendering for setup prompts and status
- **errors.py** - Custom exception types
- **__init__.py** - Package metadata and version export

Dependencies: rich (TUI), httpx (HTTP client), typer (CLI framework), platformdirs (OS paths), pyinstaller (executable generation)

SOURCE: pyproject.toml [project] dependencies, [dependency-groups] dev (accessed 2026-05-25); repository structure listing (accessed 2026-05-25)

### Versioning and Release Process

Semantic versioning via automated release pipeline:

- **Angular preset** - Commit types map to release types: `feat` → minor, `fix/perf/docs/refactor` → patch, `breaking` → major, `chore/test/build/ci` → no release
- **Automatic version updates** - Release prep updates version in `installer/__init__.py`, README.md, install.sh, and devcontainer.json
- **GitHub releases** - Semantic release plugin publishes to GitHub releases automatically
- **Git assets** - Version-bumped files committed with message "chore(release): {version}" [skip ci]

SOURCE: .releaserc.json full configuration (accessed 2026-05-25)

## Installation & Usage

### Prerequisites

1. **IDE** - VS Code, Cursor, Windsurf, or Antigravity with Claude Code extension
2. **Docker** - Docker Desktop or Docker Engine for dev container support
3. **Git** - For repository cloning

SOURCE: README.md § "🚀 Getting Started > Prerequisites" (accessed 2026-05-25)

### Installation Steps

1. **Run installer**: `curl -fsSL https://raw.githubusercontent.com/maxritter/claude-codepro/v3.3.8/install.sh | bash`
   - Script auto-detects OS (Linux/macOS/Windows via WSL)
   - Pulls and builds Docker image
   - Configures IDE extensions
   - Injects rules into project
   - Creates `ccp` alias in shell

2. **Open project in IDE** - Open the project directory in VS Code/Cursor/Windsurf

3. **Configure Claude Code**:
   - Run `/config` command to verify configuration
   - Run `/ide` command to connect to IDE diagnostics and verify MCP servers online
   - Run `/context` command to verify rules are loaded (should show rules in context window)

4. **Initialize project**:
   - Run `/setup` command to index codebase and initialize semantic search

SOURCE: README.md § "🚀 Getting Started > Installation", "📒 How-to-use > ⚙️ Configuration", "👣 First Steps" (accessed 2026-05-25)

### Customizing Rules

Project-specific rules are stored in `.claude/rules/custom/` and are never overwritten by updates. Custom rules follow the same markdown format as standard rules and can include YAML frontmatter for path-specific scoping:

```yaml
---
paths: src/**/*.py
---
# Python-specific rules for this project
```

SOURCE: README.md § "🎯 Customizing Rules" (accessed 2026-05-25)

## Relevance to Claude Code Development

Claude CodePro is directly relevant to Claude Code users for these use cases:

1. **Accelerating spec-to-code cycles** - `/plan` command generates exact specifications; `/implement` executes with TDD enforcement; `/verify` validates end-to-end
2. **Maintaining coding standards across projects** - Modular rules system encodes team conventions as persistent memory
3. **Managing context window limitations** - `/implement` command auto-detects context usage (85%/95% warnings) and manages prompt size automatically
4. **Enabling cross-platform development** - Dev container ensures consistent Linux environment across macOS/Windows developer machines
5. **Integrating semantic search** - claude-context MCP server enables project-wide code understanding for better code generation
6. **Enforcing test-driven discipline** - TDD Enforcer hook prevents code modifications without failing tests first

The framework treats Claude Code as a "professional-grade IDE" (not just a chat interface) by providing deterministic workflows (slash commands), persistent project memory, and quality gates at each phase.

SOURCE: README.md § "🛠️ Professional Development Environment for Claude Code (CC)", all core features sections (accessed 2026-05-25)

## Limitations and Caveats

**Dev Container Requirement** - Strict isolation via containerization means:
- Requires Docker Desktop or Docker Engine (no native support without containers)
- Local file edits trigger rebuilds when container configuration changes
- Debugging workflows that cross container boundaries require extra setup

**Node.js Version Lock** - `.devcontainer/devcontainer.json` constrains to Node.js v22 with explicit comment: "Claude Context is not compatible with later versions." This means:
- Cannot use newer Node.js versions that may fix critical security issues
- Projects requiring Node v23+ cannot run under claude-codepro without modification
- LTS node versions beyond v22 are not usable

**Python Version Lock** - `pyproject.toml` specifies `requires-python = ">=3.12,<3.13"` (exact minor version)
- Cannot use Python 3.13 or later without project modification
- Limits access to performance improvements and language features in newer Python releases

**Limited IDE Support** - While the framework claims "IDE Compatible" (VS Code, Cursor, Windsurf, Antigravity), all documentation and testing focus on VS Code. Compatibility with other IDEs not validated.

**GPU/CUDA Support** - Docker configuration does not include CUDA or GPU drivers. ML/data science workloads requiring GPU acceleration require manual image extension.

**Installation Script Complexity** - Single-command install via curl-bash pattern ("`curl ... | bash`") presents security risks:
- User cannot inspect script before execution
- Network interception or repository compromise could inject malicious code
- No checksum verification user can validate before running

**Custom Rules Require Manual Version Tracking** - While standard rules auto-update, custom rules must be manually maintained. No merge/conflict resolution guidance when upstream changes overlap with customizations.

**No Documented Upgrade Path** - README does not document how to upgrade claude-codepro in existing projects or rollback to prior versions if an upgrade breaks the workflow.

NOTE: These limitations are inferred from architecture and configuration files. No limitations section exists in official documentation (README, SKILL files, or docs site). The absence of documented limitations does not confirm absence of limitations — it reflects documentation scope.

SOURCE: pyproject.toml requires-python constraint, .devcontainer/devcontainer.json Node.js version with comment, README.md missing Limitations/Caveats section (accessed 2026-05-25)

## References

- [GitHub Repository — lcatlett/claude-codepro](https://github.com/lcatlett/claude-codepro) (noted as fork; upstream is maxritter/claude-codepro) — accessed 2026-05-25
- [Official Website](https://claude-code.pro) — referenced in README; not directly accessed
- [Installation Script](https://raw.githubusercontent.com/maxritter/claude-codepro/v3.3.8/install.sh) — referenced version v3.3.8 — accessed via README 2026-05-25
- README.md (primary documentation) — accessed 2026-05-25
- pyproject.toml (project metadata and dependencies) — accessed 2026-05-25
- LICENSE (AGPL-3.0 terms, copyright attribution) — accessed 2026-05-25
- .devcontainer/devcontainer.json (container and IDE configuration) — accessed 2026-05-25
- .mcp.json (MCP server configuration) — accessed 2026-05-25
- .releaserc.json (semantic versioning configuration) — accessed 2026-05-25

## Freshness Tracking

| Section | Confidence | Last Verified |
|---------|-----------|---|
| Identity/Metadata | high | 2026-05-25 (pyproject.toml, LICENSE, README headers) |
| Problem Addressed | high | 2026-05-25 (README problem statement sections) |
| Key Features | high | 2026-05-25 (README feature documentation, source code inventory) |
| Technical Architecture | high | 2026-05-25 (devcontainer, pyproject, code file structure) |
| Installation & Usage | medium | 2026-05-25 (README instructions; curl script not directly validated) |
| Limitations | low | 2026-05-25 (inferred from architecture; no official limitations documented) |
| Relevance to Claude Code | high | 2026-05-25 (README explicitly addresses Claude Code workflows) |

**Next Review**: 2026-08-25 (3 months)

**Notes on Confidence**:
- High confidence sections are grounded in version-controlled source files (pyproject.toml, .devcontainer/devcontainer.json, LICENSE)
- Medium confidence on installation due to reliance on remote script (v3.3.8) not directly fetched
- Low confidence on limitations because official docs do not document constraints; inferences made from configuration and architecture
- Repository owner ambiguity (lcatlett vs. maxritter) noted but does not affect accuracy of feature/architecture descriptions, which are present in both locations' README
