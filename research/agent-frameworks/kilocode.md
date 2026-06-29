---
title: "Kilocode"
research_date: "2026-06-29"
source_url: "https://github.com/Kilo-Org/kilocode"
version_at_research: "v7.3.54"
license: "MIT"
last_verified: "2026-06-29"
version_at_verification: "v7.3.54"
next_review: "2026-09-29"
---

## Overview

Kilocode (marketed as "Kilo Code") is an open-source, multi-platform AI coding agent that generates and edits code from natural language. It meets developers where they work via three distinct interfaces: a VS Code extension, JetBrains IDEs, and a command-line interface. The tool is built on a Turborepo-based monorepo, forks and extends the open-source OpenCode project, and provides access to over 500 AI models with zero markup—developers pay provider rates directly. Kilocode emphasizes agentic engineering with specialized agent personas (Code, Plan, Ask, Debug, Review) and supports autonomous CI/CD execution via a `--auto` flag.

SOURCE: README.md — "Kilo Code is an AI coding agent that meets you everywhere you work: VS Code, JetBrains, and the CLI. It's open source with open pricing. You pick from 500+ models, switch between them mid-task, and pay the model provider's rate with zero markup." (accessed 2026-06-29)

## Problem Addressed

Kilocode addresses the lack of a unified, provider-agnostic AI coding agent framework with support across multiple development environments. It solves several specific challenges:

1. **Platform fragmentation** — developers must choose between IDE-specific AI tools (Copilot, Codeium) or CLI-only solutions, losing continuity across VS Code, JetBrains, and terminal-driven workflows.

2. **Provider lock-in** — commercial AI tools often restrict model selection or charge substantial markups on top of base model rates.

3. **Task specialization** — generic code assistants apply the same strategy to architecture planning, debugging, code review, and incremental editing, when different tasks benefit from different agent behavior.

4. **Automation in CI/CD** — autonomous AI-driven code generation and repair in continuous integration pipelines lacks a standard open-source framework.

SOURCE: README.md — "500+ models with mid-task switching, so you can match latency, cost, and reasoning to the job" and "self-checking so the agent reviews and corrects its own work." (accessed 2026-06-29)

## Key Statistics

- **GitHub Stars**: 25,000 (as of 2026-06-29)
- **GitHub Forks**: 2,800 (as of 2026-06-29)
- **Contributors**: 1,066 (as of 2026-06-29)
- **Latest Release**: v7.3.54 (released 2026-06-23)
- **Commits**: 24,378 total commits on main branch (as of 2026-06-29)
- **Supported Models**: 500+ models across all major providers (Claude, GPT, Gemini, etc.)
- **Deployment Targets**: VS Code, JetBrains (IntelliJ suite), CLI, Cloud Agent (web), Automated Code Reviews (PR service), KiloClaw (always-on agent)
- **Active Monorepo Packages**: 10+ including core CLI, VS Code extension, JetBrains plugin, gateway, telemetry, SDK, UI components, and internationalization

SOURCE: GitHub repository page — "25k stars", "2.8k forks", "Contributors 1,066" and AGENTS.md Release Notes indicating "v7.3.54" released "23 Jun 01:51" (accessed 2026-06-29)

## Key Features

### Multi-Platform Deployment
Kilocode ships as three first-class clients—all powered by a shared CLI core:
- **VS Code Extension** — sidebar chat + Agent Manager (multi-session orchestration panel with git worktree isolation)
- **JetBrains Plugin** — native IDE integration for IntelliJ, PyCharm, WebStorm, GoLand, and other JetBrains products
- **CLI** — terminal-based interaction with `kilo` command and `kilo serve` background service; Homebrew, npm, Bun, pnpm, and Arch AUR installation paths supported

SOURCE: README.md Installation section and AGENTS.md §Products — "All products are clients of the CLI (`packages/opencode/`), which contains the AI agent runtime, HTTP server, and session management." (accessed 2026-06-29)

### Specialized Agent Personas
Five agent archetypes, each optimized for different tasks:
1. **Code** — default, implements and edits code from natural language across multiple files
2. **Plan** — designs architecture and writes implementation plans before code generation
3. **Ask** — answers questions about the codebase without file modifications
4. **Debug** — troubleshoots and traces runtime and logic issues
5. **Review** — surfaces issues across performance, security, style, and test coverage dimensions

SOURCE: README.md §Agents — "Kilo ships with specialized agents you switch between depending on the task. You can also build your own custom agents." (accessed 2026-06-29)

### Multi-Model Provider Routing with Mid-Task Switching
- Access to 500+ models including GPT-5.5, Claude Opus 4.7, Claude Sonnet 4.6, Gemini 3.1 Pro Preview, and others
- **Zero markup pricing** — developers pay model provider rates directly; Kilocode charges no platform fee
- **Mid-task switching** — change models within a single task based on latency, cost, or reasoning requirements
- Gateway (`@kilocode/kilo-gateway`) handles provider routing and authentication

SOURCE: README.md — "Create an account and you'll have access to 500+ models including GPT-5.5, Claude Opus 4.7, Claude Sonnet 4.6, and Gemini 3.1 Pro Preview, all at provider pricing." (accessed 2026-06-29)

### Code Generation and Inline Autocomplete
- **Multi-file generation** — implement features spanning multiple files from natural language
- **Inline ghost-text suggestions** — VS Code autocomplete-style suggestions with tab-to-accept UX
- **Self-checking** — agent reviews and corrects its own work before returning results

SOURCE: README.md §What it does — "Code generation from natural language, across multiple files" and "Inline autocomplete with ghost-text suggestions and tab to accept." (accessed 2026-06-29)

### Automation and CI/CD Integration
- **Autonomous mode** — `kilo run --auto` flag disables permission prompts for fully autonomous execution in CI/CD pipelines
- **Automated code reviews** — service at app.kilo.ai/code-reviews for PR-based AI review workflows
- **KiloClaw** — always-on AI agent mode for continuous background tasks
- **Terminal and browser control** — agent can run shell commands and automate web interactions

SOURCE: README.md §Autonomous Mode — "`kilo run` with `--auto` for fully autonomous operation with no prompts, built for CI/CD pipelines" (accessed 2026-06-29)

### MCP Marketplace Integration
- Wire up Model Context Protocol (MCP) servers to extend agent capabilities
- Marketplace for discovering and installing MCP-based tool extensions

SOURCE: README.md §What it does — "MCP marketplace to find and wire up MCP servers that extend what the agent can do." (accessed 2026-06-29)

## Technical Architecture

### Monorepo Organization (Turborepo + Bun)
The project uses Turborepo for orchestration and Bun as the package manager and runtime. Key architectural modules:

- **`packages/opencode/`** (`@kilocode/cli`) — Core engine containing the AI agent runtime, HTTP server, and session management. This is a fork of upstream OpenCode enhanced for Kilo specifics. Houses TUI, `kilo run`, and `kilo serve` implementations.
- **`packages/kilo-vscode/`** (`kilo-code`) — VS Code extension with sidebar chat and Agent Manager (multi-session orchestration with git worktree isolation).
- **`packages/kilo-jetbrains/`** — JetBrains IDE plugin with IntelliJ source lookup and UI thread management.
- **`packages/sdk/js/`** (`@kilocode/sdk`) — Auto-generated TypeScript SDK for server API communication (not edited by hand).
- **`packages/kilo-gateway/`** (`@kilocode/kilo-gateway`) — Authentication and provider routing logic.
- **`packages/kilo-telemetry/`** (`@kilocode/kilo-telemetry`) — PostHog analytics and OpenTelemetry observability.
- **`packages/kilo-ui/`** (`@kilocode/kilo-ui`) — SolidJS component library shared by extension webview and documentation.
- **`packages/util/`** (`@opencode-ai/util`) — Shared utilities (error handling, path manipulation, retry logic).
- **`packages/plugin/`** (`@kilocode/plugin`) — Plugin and tool interface definitions.

SOURCE: AGENTS.md §Monorepo Structure and §Package Instructions — "Turborepo + Bun workspaces" (accessed 2026-06-29)

### Session and Service Architecture
- **Shared KiloConnectionService** — in VS Code, one service is created for the sidebar, each Kilo editor tab, and Agent Manager; lazily starts and reuses one `kilo serve` backend process
- **Directory-keyed state isolation** — `InstanceState` data is isolated per worktree; active service state (`Snapshot.trackState`) is shared across requests
- **HTTP + Server-Sent Events (SSE)** — products communicate with `kilo serve` backend via HTTP and SSE using the auto-generated `@kilocode/sdk`

SOURCE: AGENTS.md §Products — "In each VS Code extension host, one `KiloConnectionService` is created for the sidebar, every Kilo editor tab, and Agent Manager; it lazily starts and reuses one current `kilo serve` backend at a time." (accessed 2026-06-29)

### Fork Integration Strategy
Kilocode is a fork of OpenCode, with careful management of shared code to minimize merge conflicts during upstream syncs. Kilo-specific code lives in dedicated directories with `kilocode` in the name (e.g., `packages/opencode/src/kilocode/`, `packages/kilo-gateway/`). Changes to shared OpenCode files are marked with `kilocode_change` comments and must be kept minimal. Conflict resolution uses `zdiff3` merge style to preserve the common ancestor during conflicts.

SOURCE: AGENTS.md §Fork Merge Process — "Kilo CLI is a fork of opencode. Everything is shared code from OpenCode, except folders that contain `kilo` in the name or have a parent directory that contains `kilo` in the name." (accessed 2026-06-29)

### Technology Stack
The monorepo uses:
- **TypeScript** (v5.8.2) as the primary language
- **Bun** (v1.3.14) as the package manager and runtime
- **Turborepo** (v2.9.14) for task orchestration
- **Effect** (v4.0.0-beta.66) for structured concurrency and error handling
- **Solid.js** (v1.9.12) for UI components (SolidJS, not React)
- **Hono** (v4.12.12) for HTTP server framework
- **Vite** (v7.3.2) with Tailwind CSS for web UI builds
- **Oxlint** (v1.60.0) for TypeScript and JavaScript linting
- **Playwright** (v1.59.1) for testing
- **Zod** (v4.1.8) for schema validation
- **Drizzle ORM** (v1.0.0-rc.2) for database access

SOURCE: package.json catalog dependencies and devDependencies (accessed 2026-06-29)

### Agent Runtime
The agent runtime powers the five specialized personas (Code, Plan, Ask, Debug, Review). Each agent type is configurable and can be extended via custom agent definitions. The runtime integrates:
- Tool execution framework for calling external APIs and shell commands
- Self-checking mechanism where agents review their own output
- MCP server integration for extensibility
- Multi-model support with provider abstraction

SOURCE: AGENTS.md §Products — "Kilo CLI is an open source AI coding agent that generates code from natural language, automates tasks, and supports 500+ AI models." (accessed 2026-06-29)

## Installation & Usage

### VS Code Extension
Install from the VS Code Marketplace or search for "Kilo Code" in the Extensions panel:

```bash
# Direct installation URL
https://marketplace.visualstudio.com/items?itemName=kilocode.Kilo-Code
```

Create an account to access 500+ models. The extension bundles the CLI binary and spawns a `kilo serve` process as a child.

SOURCE: README.md §Installation > VS Code (accessed 2026-06-29)

### CLI Installation
Install via npm, curl, pnpm, Bun, Homebrew, or Arch Linux AUR:

```bash
# npm
npm install -g @kilocode/cli

# curl
curl -fsSL https://kilo.ai/cli/install | bash

# pnpm
pnpm add -g @kilocode/cli

# Bun
bun add -g @kilocode/cli

# Homebrew (macOS / Linux)
brew install Kilo-Org/tap/kilo

# Arch Linux (AUR)
paru -S kilo-bin
```

Then run `kilo` in any project directory to start an interactive session.

SOURCE: README.md §Installation > CLI (accessed 2026-06-29)

### CLI Binary Download
Download platform-specific binaries from the Releases page:
- **Windows x64**: `kilo-windows-x64.zip`
- **macOS Apple Silicon**: `kilo-darwin-arm64.zip`
- **macOS Intel**: `kilo-darwin-x64.zip`
- **Linux x64**: `kilo-linux-x64.tar.gz`
- **Linux ARM**: `kilo-linux-arm64.tar.gz`

Additional variants: `x64-baseline` (older CPUs without AVX), `musl` (Alpine/minimal Docker images), and source code archives.

SOURCE: README.md §Installation > Install the CLI from GitHub Releases (accessed 2026-06-29)

### JetBrains Plugin
Search "Kilo Code" in `Settings → Plugins` or install from the JetBrains Marketplace:

```bash
# Direct URL
https://plugins.jetbrains.com/plugin/28350-kilo-code
```

SOURCE: README.md §Installation > JetBrains (accessed 2026-06-29)

### Basic Usage

#### Interactive Mode
```bash
kilo
```

Runs an interactive agent session in the terminal TUI.

#### Autonomous Mode (CI/CD)
```bash
kilo run --auto "run tests and fix any failures"
```

Fully autonomous execution with no permission prompts; suitable for CI/CD pipelines. The `--auto` flag disables all confirmation dialogs.

#### Cloud Agent
Access the web-based agent at [app.kilo.ai/cloud](https://app.kilo.ai/cloud) with no local installation required.

#### Automated Code Reviews
Set up PR-based code reviews at [app.kilo.ai/code-reviews](https://app.kilo.ai/code-reviews).

#### Always-On Agent (KiloClaw)
Spin up an always-on background agent at [app.kilo.ai/claw](https://app.kilo.ai/claw).

SOURCE: README.md §Installation and §Autonomous Mode (accessed 2026-06-29)

### Development Setup
The monorepo uses Bun with conventional commit style (`type(scope): summary`). Development commands:

```bash
# Run dev server
bun run dev

# Launch VS Code extension with dev mode
bun run extension

# Typecheck (uses tsgo, not tsc)
bun turbo typecheck

# Test (CLI only, not from root)
cd packages/opencode && bun test

# Linting
bun run lint
```

Contributions follow a conventional commit format with scopes matching package names (`vscode`, `cli`, `agent-manager`, `sdk`, etc.). User-facing changes require changesets via `bunx changeset add`.

SOURCE: AGENTS.md §Build and Dev and §Commits and PR Titles (accessed 2026-06-29)

## Relevance to Claude Code Development

### Agent Framework Patterns
Kilocode demonstrates a mature multi-agent architecture with specialized personas (Code, Plan, Ask, Debug, Review) that separate concerns by task intent. Claude Code could adopt similar persona patterns to improve consistency and task fit. The separation of agent types and configurable switching provides a reference model for task-specific reasoning strategies.

### Multi-Platform Client Architecture
Kilocode's unified backend (`kilo serve`) with multiple client frontends (VS Code, JetBrains, CLI, web) mirrors the multi-client pattern emerging in AI development tools. The shared HTTP+SSE communication layer and directory-keyed state isolation could inform Claude Code's multi-IDE support strategy.

### Model Provider Abstraction
Kilocode's zero-markup multi-model routing via `@kilocode/kilo-gateway` demonstrates a clean separation between agent orchestration and LLM provider integration. Claude Code's current tight coupling to the Anthropic API could benefit from a similar abstraction layer to support future model flexibility.

### MCP Marketplace and Tool Extensibility
The MCP server integration pattern provides a reference implementation for extensible tool ecosystems. Claude Code's tool system could adopt MCP as a standard interface for third-party extensions, enabling a "marketplace" discovery pattern similar to Kilocode's.

### Monorepo Organization and Test Infrastructure
Kilocode's Turborepo + Bun structure with package-level testing (never from root), strict typing (tsgo), and per-package quality gates provides a scalable model for multi-platform delivery. The adherence to single-responsibility in package organization and the split between shared OpenCode code and Kilo-specific directories offers patterns for managing complexity in large AI tool repositories.

### Autonomous Execution and CI/CD Integration
The `--auto` flag and autonomous mode pattern for CI/CD environments establish a framework for agent-driven automation without confirmation prompts. Claude Code's scripting and batch execution modes could adopt similar safety boundaries.

SOURCE: AGENTS.md §Products and §Monorepo Structure; README.md §Agents and §What it does (accessed 2026-06-29)

## Limitations and Caveats

### Provider Dependency
While Kilocode offers 500+ models, actual availability depends on active provider accounts and API keys. The tool cannot function for models without configured credentials, limiting the theoretical model count to practically available options per user.

SOURCE: README.md — "Create an account and you'll have access to 500+ models" implies authentication and configuration prerequisites (accessed 2026-06-29)

### Fork Maintenance Overhead
The fork relationship with OpenCode introduces ongoing merge and conflict resolution costs. Despite `kilocode_change` markers and `zdiff3` merge strategies, regular upstream syncs require careful coordination. Shared file modifications must remain minimal to avoid compounding merge complexity.

SOURCE: AGENTS.md §Fork Merge Process — "We regularly merge upstream changes from opencode" and "minimize merge conflicts and keep the sync process smooth" (accessed 2026-06-29)

### Beta Dependencies
Key runtime dependencies such as Effect (v4.0.0-beta.66), Drizzle ORM (v1.0.0-rc.2), and OpenAuth (v0.0.0-20250322224806) are in beta or pre-release status. Production stability depends on upstream library maturity.

SOURCE: package.json catalog — Multiple `beta` and `rc` version specifiers (accessed 2026-06-29)

### JetBrains Plugin Complexity
The JetBrains plugin requires Java 21 and Gradle, with a separate build pipeline from the CLI and VS Code extension. Development of changes affecting the plugin requires Java environment setup and IntelliJ SDK integration, raising the entry barrier for contributors.

SOURCE: AGENTS.md §Build and Dev — "Requires Java 21; do not run `java -version` as a routine preflight. Only check Java when a Gradle/Java command fails with a Java-version or missing-Java error." (accessed 2026-06-29)

### Autonomous Mode Safety
The `--auto` flag disables all permission prompts and allows the agent to execute any action without confirmation. The documentation explicitly states "Only use it in trusted environments." Misuse could result in unintended file modifications, command execution, or data loss in production systems.

SOURCE: README.md §Autonomous Mode — "`--auto` disables all permission prompts and lets the agent execute any action without confirmation. Only use it in trusted environments." (accessed 2026-06-29)

### Documentation Scope
While the README and AGENTS.md provide architectural context, detailed API documentation, custom agent creation guides, and plugin development guides are deferred to external sites (kilo.ai/docs). Community-driven documentation may have coverage gaps.

SOURCE: README.md — "For configuration and everything else, head over to the docs" linking to <https://kilo.ai/docs> (accessed 2026-06-29)

## References

- GitHub Repository: <https://github.com/Kilo-Org/kilocode> (accessed 2026-06-29)
- Latest Release: <https://github.com/Kilo-Org/kilocode/releases/latest> — v7.3.54 (released 2026-06-23, accessed 2026-06-29)
- README.md: <https://github.com/Kilo-Org/kilocode/blob/main/README.md> (accessed 2026-06-29)
- AGENTS.md (Development Guide): <https://github.com/Kilo-Org/kilocode/blob/main/AGENTS.md> (accessed 2026-06-29)
- package.json: <https://github.com/Kilo-Org/kilocode/blob/main/package.json> (accessed 2026-06-29)
- Official Documentation: <https://kilo.ai/docs> (accessed 2026-06-29)
- VS Code Marketplace: <https://marketplace.visualstudio.com/items?itemName=kilocode.Kilo-Code> (accessed 2026-06-29)
- JetBrains Marketplace: <https://plugins.jetbrains.com/plugin/28350-kilo-code> (accessed 2026-06-29)
- Community: Discord <https://kilo.ai/discord>, X <https://x.com/kilocode>, Reddit <https://reddit.com/r/kilocode/> (accessed 2026-06-29)
