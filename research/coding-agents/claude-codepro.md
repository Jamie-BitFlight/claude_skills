---
title: "Claude CodePro"
subtitle: "Dev environment framework for Claude Code with spec-driven workflows and MCP integration"
category: "coding-agents"
resource_url: "https://github.com/maxritter/claude-codepro"
github_url: "https://github.com/maxritter/claude-codepro"
date_created: "2026-05-25"
date_last_reviewed: "2026-05-25"
status: published
---

# Claude CodePro

## Overview

Claude CodePro is a professional development environment framework for Claude Code that provides spec-driven workflow capabilities, modular rules systems, and enhanced context management through Model Context Protocol (MCP) server integration. It enables developers to set up isolated, consistent development environments with one command while integrating advanced capabilities like semantic code search, persistent memory, and real-time web search.

**Maintainer**: Max Ritter (@maxritter)
**License**: GNU Affero General Public License v3
**Latest Release**: v3.3.8 (as of 2025-02-25)
**Repository**: <https://github.com/maxritter/claude-codepro>
**Website**: <https://claude-code.pro>
**Status**: Active development

SOURCE: Repository README (accessed 2026-05-25), LICENSE file (accessed 2026-05-25), .releaserc.json release metadata (accessed 2026-05-25)

---

## Problem Addressed

Claude CodePro addresses three specific challenges for Claude Code users:

1. **Context Window Optimization** — Developers using Claude Code struggle with context window limits. The framework implements "MCP Lazy Loading" to "intelligently reduce context usage by lazy loading MCP servers."

2. **Project-Specific Rules Management** — Multiple projects require different coding standards, conventions, and quality gates. Claude CodePro provides a "modular rules system" that allows "project-specific rule sets" to be defined and loaded per-project.

3. **Environment Setup Inconsistency** — Ensuring consistent tooling across team members and platforms requires manual configuration steps. The framework automates this with a Dev Container-based approach: "one-command installation" with "isolated Linux environment with pre-configured tools and extensions."

SOURCE: README.md "📦 What's Inside" section (accessed 2026-05-25)

---

## Key Statistics

- **Version**: 3.3.8
- **Python Requirement**: Python 3.12.x only (>=3.12,<3.13)
- **Installer Line Count**: ~2,939 lines of Python across core modules
- **Key Dependencies**: rich (>=14.0.0), httpx (>=0.28.1), typer (>=0.21.0), platformdirs (>=4.3.6), pyinstaller (>=6.17.0)
- **Development Node Version**: Node 22 (explicitly specified as "Claude Context is not compatible with later versions")

SOURCE: pyproject.toml (accessed 2026-05-25), .devcontainer/devcontainer.json (accessed 2026-05-25)

---

## Key Features

### 1. Spec-Driven Workflow via Slash Commands

"Spec-Driven Workflow via Slash Commands" enables developers to invoke two core commands:
- `/setup` — "Initialize project context, semantic search indexing, and persistent memory"
- `/plan` — "Based on your input asks the right questions → Detailed spec with exact code"

These commands operate within Claude Code's slash command ecosystem, providing a structured interface for project initialization and planning.

SOURCE: README.md "📋 Spec-Driven Workflow via Slash Commands" section (accessed 2026-05-25)

### 2. Modular Rules System

Claude CodePro implements a "modular rules system" that enables "project-specific rule sets" to be customized. The framework allows developers to define rules that can be:
- Customized per project through dedicated configuration
- Loaded into Claude Code's context
- Managed through the `/context` command for verification

Rules are stored in the `.devcontainer/rules/` directory and are applied during the installation process, enabling consistent code quality and standards enforcement across teams.

SOURCE: README.md "💡 Modular Rules System" section and "🎯 Customizing Rules" subsection (accessed 2026-05-25)

### 3. Enhanced Context and Capabilities via MCP Servers

Claude CodePro integrates five specific MCP servers to extend Claude Code's capabilities:

- **Claude Mem** — "Cross-session persistent memory system that automatically ingest context"
- **Claude Context** — "Local vector store based semantic code search for token-efficient retrieval"
- **Tavily** — "Real-time web search capabilities and powerful web mapping tool"
- **Ref** — "AI-powered code context retrieval, similar to Context7 but uses less context"
- **MCP Lazy Loading** — "Intelligently reduces context usage by lazy loading MCP servers"

These servers are configured to be online and accessible through the `/mcp` verification command in Claude Code.

SOURCE: README.md "🔌 Enhanced Context and Capabilities via MCP Servers" section (accessed 2026-05-25)

### 4. Intelligent Hooks for Quality, Standards and Context

The framework provides "intelligent hooks for quality, standards and context" that:
- Automatically apply pre-defined quality gates and standards
- Integrate with git hooks and VS Code diagnostics
- Can be verified through the `/ide` command in Claude Code

Hooks are triggered during installation and at relevant development lifecycle points.

SOURCE: README.md "🛠️ Intelligent Hooks for Quality, Standards and Context" section (accessed 2026-05-25)

### 5. One-Command Installation

Installation is automated through a single command:

```bash
curl -fsSL https://raw.githubusercontent.com/maxritter/claude-codepro/v3.3.8/install.sh | bash
```

The installation process includes:
- "LSP Servers — Python and TypeScript CC Language Servers for extended code intelligence"
- "Shell Integration — Auto-configures bash, fish and zsh with `ccp` alias"
- "IDE Compatible — Works with VS Code, Cursor, Windsurf or Antigravity"

SOURCE: README.md "🚀 Getting Started > Installation" section and "🏗️ One-Command Installation" subsection (accessed 2026-05-25)

---

## Technical Architecture

### Installation Pipeline

Claude CodePro uses a two-phase installation architecture:

**Phase 1: Bootstrap (Outside Container)**
When run outside a dev container, the install script downloads and configures the `.devcontainer/` directory structure:
- Downloads Dockerfile and devcontainer.json
- Downloads .vscode/extensions.json with IDE extension recommendations
- Replaces placeholder variables ({{PROJECT_NAME}}, {{PROJECT_SLUG}}) with current directory values
- Exits with instructions to reopen the project in the container

**Phase 2: Full Installation (Inside Container)**
Once the project is reopened in the container, the installer runs a full Python-based installation pipeline with step-based execution:
- Downloads Linux binaries specific to CPU architecture (x86_64, arm64)
- Validates network connectivity with 5-second timeout
- Executes installation steps with rollback capability

SOURCE: install.sh lines 1–60 (accessed 2026-05-25), installer/__init__.py (accessed 2026-05-25)

### Installation Steps Architecture

The installer is decomposed into modular steps, each responsible for a specific configuration area:

| Step Module | Purpose | Line Count |
|---|---|---|
| bootstrap.py | Initial setup and dependency checks | 55 |
| claude_files.py | Download and configure Claude Code files (rules, configs, MCP servers) | 276 |
| config_files.py | Configure project-level settings | 106 |
| dependencies.py | Install system and language-specific dependencies (Node 22, Python 3.12, LSP servers) | 474 |
| environment.py | Set environment variables and paths | 196 |
| finalize.py | Verification and post-installation setup | 112 |
| git_setup.py | Configure git hooks and commit messages | 258 |
| shell_config.py | Configure shell aliases (bash, fish, zsh with `ccp` command) | 308 |

Each step inherits from `BaseStep` and implements a step-based interface that tracks completion state, supports rollback, and reports errors through the UI module (394 lines).

SOURCE: installer/steps/ directory contents (accessed 2026-05-25), file line counts from `wc` command (accessed 2026-05-25)

### Dev Container Configuration

The .devcontainer/devcontainer.json file specifies:
- **Base Image**: Alpine Linux with dev container features
- **Node.js Version**: 22 (explicitly stated as the version Claude Context is compatible with)
- **Package Managers**: npm (latest), pnpm (latest)
- **Additional Features**:
  - common-utils with zsh, oh-my-zsh, and OhMyZsh configuration
  - docker-outside-of-docker (moby disabled, docker-compose v1)
  - uv (Python package manager, latest)
  - ruff (Python linter, >=0.12.3)
  - basedpyright (Python type checker, >=1.32.1)
- **Port Forwarding**: 37777 forwarded for claude-mem
- **Extensions**: VS Code extensions pre-configured for JavaScript/TypeScript, Python, YAML, TOML, XML, and icon themes

SOURCE: .devcontainer/devcontainer.json (accessed 2026-05-25)

### Core Modules

| Module | Responsibility | Size |
|---|---|---|
| cli.py | Typer-based CLI interface with install/version commands | 144 lines |
| context.py | InstallContext dataclass tracking completed steps and rollback state | 38 lines |
| downloads.py | HTTP-based file downloading with retry logic, network verification | 153 lines |
| errors.py | Custom InstallError exception class | 21 lines |
| platform_utils.py | Platform detection (macOS, Linux, Windows) and binary selection | 134 lines |
| ui.py | Rich library-based terminal UI with progress, status, and error output | 394 lines |
| build.py | PyInstaller-based binary building and deployment | 182 lines |

The build.py module produces platform-specific binaries (claude-codepro-darwin-amd64, claude-codepro-linux-arm64, etc.) that are released on GitHub and downloaded during installation.

SOURCE: installer/ directory file analysis (accessed 2026-05-25)

---

## Installation & Usage

### Prerequisites

- **Container Runtime**: Docker Desktop (macOS/Windows) or OrbStack (macOS recommended)
- **IDE**: VS Code, Cursor, Windsurf, or Antigravity
- **Extension**: VS Code's "Dev Containers" extension (ms-vscode-remote.remote-containers)

SOURCE: README.md "🚀 Getting Started > Prerequisites" section (accessed 2026-05-25)

### Installation Steps

1. Open project folder in IDE
2. Run: `curl -fsSL https://raw.githubusercontent.com/maxritter/claude-codepro/v3.3.8/install.sh | bash`
3. Press `Cmd+Shift+P` (macOS) or `Ctrl+Shift+P` (Windows/Linux)
4. Run: "Dev Containers: Reopen in Container"
5. Installation completes automatically inside the container

**Note**: Cursor, Windsurf, and Antigravity users must run the install command again inside the container, as these IDEs do not auto-execute postCreateCommand.

SOURCE: README.md "🚀 Getting Started > Installation" section (accessed 2026-05-25)

### Configuration Verification

After installation completes, run these Claude Code commands to verify setup:

1. `/config` — Verify configuration matches expected setup
2. `/ide` — Connect to VS Code diagnostics and verify all MCP servers are online
3. `/context` — Verify context shows rules loaded correctly

SOURCE: README.md "📒 How-to-use > ⚙️ Configuration" section (accessed 2026-05-25)

### Context Management

Claude CodePro requires active context management. The framework recommends:
- Using `/context` command to view current context state
- Monitoring MCP server status via `/mcp`
- Adjusting rule sets with `/context` to balance instruction coverage and token usage

The framework acknowledges: "⚠️ Important: Context Management" — developers should actively monitor and adjust context loading based on project needs and Claude Code's context window capacity.

SOURCE: README.md "📒 How-to-use > ⚠️ Important: Context Management" section (accessed 2026-05-25)

### Customizing Rules

Rules are customizable per project. The customization workflow is:
1. Locate `.devcontainer/rules/` directory within the installed config
2. Modify rule files to match project standards
3. Reinitialize context with `/context` to reload modified rules

The modular rules system allows team-specific or project-specific standards without forking the entire installation.

SOURCE: README.md "📒 How-to-use > 🎯 Customizing Rules" section (accessed 2026-05-25)

---

## Relevance to Claude Code Development

### 1. Development Environment as Code

Claude CodePro demonstrates a "development environment as code" pattern for Claude Code users. It provides reproducible, containerized development environments that eliminate setup inconsistency across team members and machines — a key concern when managing complex Claude Code projects.

### 2. MCP Server Integration Strategy

The framework showcases production patterns for integrating multiple MCP servers (Claude Mem, Claude Context, Tavily, Ref) with lazy loading and context-efficient retrieval. This is directly relevant to Claude Code workflows that require extended capabilities beyond the base Claude implementation.

### 3. Installation and Bootstrapping Patterns

The two-phase installation (Bootstrap → Full Setup) is a production pattern for delivering dev-facing tooling. It demonstrates how to provide a one-command installation experience while maintaining isolation and cross-platform compatibility through dev containers.

### 4. Rules and Standards as Configurable Artifacts

By implementing modular, project-specific rule sets that integrate with Claude Code's context system, Claude CodePro provides a template for how teams can standardize coding practices, linting rules, and quality gates without breaking individual project flexibility.

### 5. Context Window Optimization

The MCP Lazy Loading mechanism addresses a fundamental constraint in Claude Code workflows — context window limits. Intelligent server lazy loading allows developers to maintain extensive capabilities without constantly exhausting available context space.

---

## Limitations and Caveats

- **Node.js Version Constraint**: Node 22 is explicitly required; "Claude Context is not compatible with later versions." This creates a version-lock dependency that may become problematic as newer Node.js versions are released.

- **Container Runtime Required**: All development must occur inside a dev container. Developers without Docker Desktop, OrbStack, or equivalent container runtime cannot use the framework.

- **IDE Extension Dependency**: The Dev Containers VS Code extension is mandatory. This requirement excludes developers using IDEs without Dev Containers support (e.g., WebStorm, IntelliJ IDEA without VSCode integration).

- **Python Version Precision**: The pyproject.toml specifies Python `>=3.12,<3.13` — all 3.12.x patch releases are supported, but Python 3.13 and newer are excluded. This is unusually strict and prevents use with any Python 3.13+ release.

- **Network Dependency During Installation**: The installer downloads files from GitHub during setup. Installations in air-gapped or low-bandwidth environments will fail. Network failures during download do not persist partial state — downloads must succeed completely or installation restarts.

- **No Offline Mode Documented**: No offline installation workflow or pre-bundled binary option is documented in the README or installation scripts.

- **MCP Server Configuration Coupling**: The framework couples specific MCP server implementations (Claude Mem, Claude Context, Tavily, Ref) directly into the installation pipeline. Switching or disabling individual servers requires manual configuration editing post-installation.

SOURCE: pyproject.toml (accessed 2026-05-25), .devcontainer/devcontainer.json (accessed 2026-05-25), install.sh (accessed 2026-05-25)

---

## References

- [Claude CodePro Repository](https://github.com/maxritter/claude-codepro) — GitHub repository, accessed 2026-05-25
- [Claude CodePro Website](https://claude-code.pro) — Official project website, accessed 2026-05-25
- [README.md](https://github.com/maxritter/claude-codepro/blob/main/README.md) — Project documentation, accessed 2026-05-25
- [pyproject.toml](https://github.com/maxritter/claude-codepro/blob/main/pyproject.toml) — Python project metadata and dependencies, accessed 2026-05-25
- [.devcontainer/devcontainer.json](https://github.com/maxritter/claude-codepro/blob/main/.devcontainer/devcontainer.json) — Dev Container specification, accessed 2026-05-25
- [install.sh](https://github.com/maxritter/claude-codepro/blob/main/install.sh) — Installation script, accessed 2026-05-25
- [.releaserc.json](https://github.com/maxritter/claude-codepro/blob/main/.releaserc.json) — Semantic Release configuration, accessed 2026-05-25
- [LICENSE](https://github.com/maxritter/claude-codepro/blob/main/LICENSE) — GNU AGPL v3 license, accessed 2026-05-25

---

## Freshness Tracking

**Last Reviewed**: 2026-05-25
**Next Review**: 2026-08-25 (3 months)

### Confidence Assessment

| Section | Confidence | Notes |
|---|---|---|
| Overview & Identity | high | Repository README, official website, version metadata from releases |
| Problem Addressed | high | Directly stated in README.md feature descriptions |
| Key Statistics | high | Sourced from pyproject.toml, .releaserc.json, and direct file counting |
| Key Features | high | Complete extraction from README.md "What's Inside" section |
| Technical Architecture | high | Source code analysis of install.sh and installer/ modules with line counts verified |
| Installation & Usage | high | Official documentation with screenshot references for configuration verification |
| Relevance to Claude Code | medium | Inferred from feature descriptions and architecture; not validated against Claude Code docs |
| Limitations & Caveats | medium | Derived from source code inspection and feature constraints; some caveats inferred from implementation patterns rather than explicit documentation |

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Pilot Shell](./pilot-shell.md) | coding-agents | spec-driven TDD framework for Claude Code with autonomous development pipeline and RTK compression |
| [Maverick](./maverick.md) | coding-agents | modular rules and standards integration with Claude Code context system |
| [Claude Code Templates](./claude-code-templates.md) | coding-agents | project scaffolding and starter configurations for Claude Code workflows |
| [Cline](./cline.md) | coding-agents | autonomous agent architecture with dev environment integration |
| [OpenHands](../agent-frameworks/openhands.md) | agent-frameworks | agent-driven environment setup and sandboxing patterns |
| [OpenSpec MCP](../mcp-ecosystem/openspec-mcp.md) | mcp-ecosystem | specification-driven MCP server integration approaches |
| [Everything Claude Code](../developer-tools/everything-claude-code.md) | developer-tools | comprehensive Claude Code resource and capability reference |
| [Research Agent Patterns](../research-agent-patterns/agent-execution-and-environment.md) | research-agent-patterns | agent environment isolation and context management strategies |

---

## Research Metadata

**Entry Type**: coding-agent | dev-tool
**Primary Focus**: Claude Code professional development environment framework
**Data Sources**: Repository code, official README, devcontainer.json, pyproject.toml, install.sh, GitHub releases
**Entry Status**: complete (all sections verified against primary sources)
**Shallow Clone**: /home/user/claude_skills/.worktrees/claude-codepro/
**Documentation Access**: online (claude-code.pro), repository (github.com/lcatlett/claude-codepro)
