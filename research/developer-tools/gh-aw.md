---
name: gh-aw
title: GitHub Agentic Workflows (gh-aw)
subtitle: GitHub CLI extension for defining AI-powered repository automation in Markdown
research_date: 2026-10-02
source_url: https://github.com/github/gh-aw
github_repository: https://github.com/github/gh-aw
version_at_research: v0.89.21
license: MIT
freshness_tracking:
  last_verified: 2026-10-03
  version_at_verification: v0.89.21
  next_review: 2027-01-03
  confidence_map: "Overview: high | Problem Addressed: high | Key Features: medium (doc + code-read) | Technical Architecture: medium (doc + code-read) | Installation & Usage: high | Limitations & Caveats: high | Relevance: medium"
---

# GitHub Agentic Workflows

## Overview

GitHub Agentic Workflows (`gh-aw`) is a GitHub CLI extension that enables developers to define AI-powered repository automation using Markdown with YAML frontmatter and execute these workflows securely through GitHub Actions. The tool combines natural language workflow definitions with safety constraints, agent sandboxing, and structured outputs, complementing traditional CI/CD by handling tasks requiring AI reasoning rather than deterministic logic.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Repository tasks requiring AI reasoning (issue triage, PR review, CI investigation) | Define workflows in Markdown with AI agents that make intelligent decisions |
| Unsafe or uncontrolled AI agent actions | Safe-outputs framework and strict mode enforce permissions, sandbox execution, and validated writes |
| Choosing among multiple AI engines | Built-in `engine:` values for Copilot, Claude, OpenAI Codex, Google Gemini, and Pi; per the engines reference, changing engines "requires updating `engine:` and may also require different authentication, tools, model names, or network access" |
| Lack of tool access for agents | MCP (Model Context Protocol) server integration provides structured tool access |
| GitHub API abuse or misconfiguration | Read-only execution by default; writes go through scoped permission validation |

---

## Key Features

### Natural Language Workflow Definition

- Workflows are Markdown files with YAML frontmatter: "An agentic workflow has two parts: YAML frontmatter configures triggers, permissions, tools, and the AI engine; the Markdown body tells the AI agent what to accomplish."
- No DSL or workflow YAML required; agents read task descriptions in plain English

### AI Engine Support

- Built-in support for multiple engines: "Built-in AI engines include GitHub Copilot, Claude Code, OpenAI Codex, Google Gemini, and Pi."
- Selected per workflow with the `engine:` frontmatter field; Copilot CLI is the default, "so `engine:` can be omitted when using Copilot" (engines reference). Feature support differs by engine: "Not all features are available across all engines."
- Commands that take `--engine` validate the value against the engine registry and suggest the closest match for an invalid one. Source: `cmd/gh-aw/main.go` — `validateEngine()`, `pkg/workflow/agentic_engine.go` — `GetGlobalEngineRegistry()`
- Engines under `.github/workflows/shared/` (OpenCode, Aider, Crush, Cursor, DeepSeek Harness, Kiro, Pydantic AI) are, per the engines reference, "samples only" with "no compatibility or maintenance commitment"

### Compiler & Lock Files

- `gh aw compile` command validates Markdown workflows and generates `.lock.yml` files for GitHub Actions execution
- Lock files are deterministic, reviewable, and can be committed to version control
- Compilation collects all validation errors by default; `--fail-fast` is documented in the flag help as "Stop at the first validation error instead of collecting all errors". Source: `cmd/gh-aw/main.go` — `compileCmd` flag `fail-fast`

### Security & Sandboxing

- Agent jobs are read-only and sandboxed by default
- "Strict Mode: Security-first validation and sandboxing" enforces execution constraints
- Configured GitHub writes go through validated safe-outputs jobs with scoped permissions
- Secret redaction with built-in patterns for GitHub, Azure, Google, AWS, OpenAI, and Anthropic credentials. Source: `actions/setup/js/redact_secrets.cjs` — the pattern list (also includes a Linear API key pattern)

### MCP Server Integration

- "MCP Server Integration: Connect to Model Context Protocol servers for tools"
- Workflows can define MCP servers in frontmatter for structured tool access
- `mcp-scripts:` defines custom MCP tools inline in frontmatter as JavaScript (`script:`), shell (`run:`), Python (`py:`) or Go (`go:`); each tool requires `description:` and exactly one of those four fields. Upstream renamed the earlier `safe-inputs` feature to `mcp-scripts` (changeset `minor-rename-safe-inputs-to-mcp-scripts.md`, which also adds a `safe-inputs-to-mcp-scripts` codemod)
- Inputs are typed: each `inputs:` entry takes `type`, `required`, `default`, `description` and `enum`. Tools are "generated at runtime and run as an HTTP MCP server **on the GitHub Actions runner, outside the agent container**", reached by the agent via `host.docker.internal`
- Only `env:`-declared variables are forwarded to a tool, `${{ secrets.* }}` values are masked in logs, `timeout:` defaults to 60 seconds (enforced for `run:` and `py:`, not for in-process `script:`), and output over 500 characters is saved to a file whose path, size and schema preview are returned to the agent
- The reference warns that mcp-scripts "must only implement READ-ONLY operations" because they run outside the sandbox; writes belong in safe outputs. Source: `docs/src/content/docs/reference/mcp-scripts.md`, `docs/public/schemas/mcp-scripts-config.schema.json`

### Shared Components & Repo Memory

- "Shared Components: Reusable workflow building blocks" enable common patterns across workflows
- "Repo Memory: Persistent git-backed storage for agents" allows workflows to maintain state

---

## Technical Architecture

The gh-aw tooling consists of several layered components. Each claim below is read from the v0.89.21 source tree, and the `Source:` line names the file and the exported (or, where no exported name carries the claim, the package-level) identifier.

**CLI layer**: `main.go` builds a Cobra root command and registers a large command set via `createCommandSet()` and `addCommandsToRoot()`; the set includes `compile`, `add`, `add-wizard`, `new`, `init`, `run`, `status`, `logs`, `audit`, `doctor`, `fix`, `validate`, `lint`, `mcp-server` and others. Source: `cmd/gh-aw/main.go` — `createCommandSet()`, `addCommandsToRoot()`, `rootCmd`

**Parser**: The package doc describes frontmatter parsing, markdown-body extraction, import processing and GitHub URL resolution. Frontmatter is validated against JSON schemas embedded in the package (`main_workflow_schema.json`, `mcp_config_schema.json`, `repo_config_schema.json`). Source: `pkg/parser/doc.go` — package `parser`, `pkg/parser/schema_validation.go` — `ValidateMainWorkflowFrontmatterWithSchemaAndLocation()`, `pkg/parser/schema_compiler.go` — `//go:embed schemas/main_workflow_schema.json`

**Compiler**: The central component that transforms agentic workflow files into standard GitHub Actions workflows (`.lock.yml`). It carries compile-time options including `strictMode`, `failFast`, `noEmit`, `engineOverride` and `forceStaged`. Source: `pkg/workflow/compiler_types.go` — `type Compiler`, `pkg/workflow/compiler.go` — `(*Compiler).CompileWorkflow()`, `pkg/workflow/compiler_options.go` — `NewCompiler()`

**Engine registry**: A registry of coding-agent engines keyed by ID. `EngineRegistry` registers the built-in engines at construction and exposes `GetSupportedEngines()` and `IsValidEngine()`, which the CLI's `validateEngine()` calls. The `Engine` and `CodingAgentEngine` interfaces, and the `EngineCapabilities` struct, define what an engine implementation provides. Source: `pkg/workflow/agentic_engine.go` — `type EngineRegistry`, `NewEngineRegistry()`, `GetGlobalEngineRegistry()`, `type CodingAgentEngine`, `type EngineCapabilities`. Per-workflow engine config (`engine:` as a string or object) is extracted by `pkg/workflow/engine.go` — `(*Compiler).ExtractEngineConfig()`, `type EngineConfig`

**Safe-outputs job generation**: The compiler builds a consolidated safe-outputs job that downloads the agent's output artifact and runs handler steps, so agent jobs request writes while a separate job applies them. Source: `pkg/workflow/compiler_safe_outputs_job.go` — `(*Compiler).buildConsolidatedSafeOutputsJob()`, `pkg/workflow/compiler_jobs.go` — `(*Compiler).buildSafeOutputsAndEvalsJobs()`

**Secret redaction**: The compiler collects `${{ secrets.* }}` references from generated YAML and emits a redaction step; the runtime script carries the built-in credential patterns. Source: `pkg/workflow/redact_secrets.go` — `CollectSecretReferences()`, `(*Compiler).generateSecretRedactionStep()`, `actions/setup/js/redact_secrets.cjs` — pattern list

**Action pinning**: Action references are resolved to pinned versions by a dedicated package. Source: `pkg/actionpins/resolve.go` — `ResolveActionPin()`

**Agent drain**: `agentdrain` is not an orchestration coordinator. Its README describes "Drain-style log template mining and anomaly scoring for structured agent pipeline events"; `Coordinator` owns one `Miner` per stage and supports `TrainEvent` and `AnalyzeEvent`. Source: `pkg/agentdrain/coordinator.go` — `type Coordinator`, `NewCoordinator()`, `pkg/agentdrain/README.md`

**Dependencies**: `go.mod` declares `charm.land/bubbles/v2`, `charm.land/bubbletea/v2` and `charm.land/huh/v2` for interactive CLI UI, `github.com/cli/go-gh/v2`, `github.com/modelcontextprotocol/go-sdk` (v1.8.0) and Cobra, and `go 1.26.8`. Source: `go.mod` — `module github.com/github/gh-aw`

---

## Installation & Usage

### Installation

Install as a GitHub CLI extension:

```bash
gh extension install github/gh-aw
```

### Repository Setup

Initialize a repository for agentic workflows:

```bash
gh aw init
```

Per the CLI reference, `init` creates skills, agents and a `.gitattributes` entry and is non-interactive by default; `--engine <name>` skips the Copilot-specific artifacts. Source: `docs/src/content/docs/setup/cli.md` (`gh aw init`).

### Create a Workflow

Create a new agentic workflow interactively:

```bash
gh aw new my-workflow
```

Or use the guided wizard:

```bash
gh aw add-wizard
```

### Workflow File Structure

Workflows are Markdown files with YAML frontmatter in `.github/workflows/`:

```markdown
---
emoji: 🧠
name: Issue Triager
description: Triages issues by type, labels, and assignment
on:
  issues:
    types: [opened]
permissions:
  contents: read
  actions: read
strict: true
network:
  allowed: [defaults, github]
tools:
  github:
    mode: gh-proxy
    toolsets: [default]
safe-outputs:
  add-comment:
---

# Workflow Title

Natural language instructions for the AI agent. Analyze the newly opened issue and:
1. Classify it by type (bug, feature, documentation)
2. Add appropriate labels
3. Assign to relevant team if urgent
```

### Compile & Validate

Compile all workflows to lock files:

```bash
gh aw compile
```

Run extra validation (GitHub Actions workflow schema, container image and action SHA checks) during compilation:

```bash
gh aw compile --validate
```

Validate without writing lock files:

```bash
gh aw compile --no-emit
```

### Run & Monitor

Execute a workflow:

```bash
gh aw run my-workflow
```

View workflow status:

```bash
gh aw status
```

Download and analyze execution logs:

```bash
gh aw logs my-workflow
gh aw audit <run-id>
```

### Troubleshooting

Diagnose authentication and repository setup:

```bash
gh aw doctor --repo owner/repo
```

---

## Limitations & Caveats

- **Security advisory**: "A [security vulnerability](https://github.com/github/gh-aw/security/advisories/GHSA-8h78-hpm7-29gg) was discovered in versions `>= 0.83.3, < 0.85.4` and, as a result, those releases were retired as a pre-emptive measure." Users should upgrade to v0.85.4 or later.
- **Engine differences**: "Not all features are available across all engines." Changing engines "may also require different authentication, tools, model names, or network access" (engines reference).
- **Unsupported engine samples**: OpenCode, Aider, Crush, Cursor, DeepSeek Harness, Kiro and Pydantic AI integrations "are **samples only**" with "no compatibility or maintenance commitment" (engines reference).
- **Compilation required**: "Workflows must be compiled to `.lock.yml` files before running in GitHub Actions" (`create.md`).
- **MCP scripts run outside the sandbox**: "MCP Scripts run outside the agent sandbox and must only implement READ-ONLY operations" (mcp-scripts reference).
- **Permissions scoping**: "Safe outputs buffer configured writes, validate them, and apply them in separate jobs with scoped permissions. These controls are configurable, so workflow authors must review permissions, tools, network access, and generated files before deployment."

---

## Relevance to Claude Code Development

### Applications

- **Per-workflow AI-engine selection** -> `./plugins/agent-orchestration/README.md`
  - Term: `harness`
  - Today: "A small set of skills and a contract for orchestrating sub-agents, portable across harnesses that support plugins, skills, and agents."
  - Change: none — out of scope (gh-aw's `engine:` frontmatter field picks one of Copilot, Claude, Codex, Gemini or Pi for each workflow run. This repository has no such selector: `scripts/generate_harness_compatibility.py` line 36 `HARNESSES = ["claude-code", "codex", "hermes", "kimi"]` lists plugin host compatibility targets, and `load_verification_source()` (lines 111-133) only rejects verification evidence naming an unknown plugin or harness. `plugins/agent-orchestration/` documents sub-agent dispatch and ships only `harness-notes/claude-code.md`. a case-insensitive search for `engine` over the script and the plugin directory finds no matching file. The two systems answer different questions, so no edit follows)

- **Markdown-based declarative workflow definitions** -> `./.claude/agents/backlog-mcp-validator.md`
  - Term: `frontmatter`
  - Today: "The `backlog` server is configured in this agent's `mcpServers` frontmatter."
  - Change: none — `./.claude/agents/backlog-mcp-validator.md` already covers it: its line 391 states the `backlog` server is configured in the agent's `mcpServers` frontmatter and starts automatically when the agent is invoked

### Integration Opportunities

- **Inline typed tool definitions (`mcp-scripts`)** -> `.mcp.json`
  - Term: `mcpServers`
  - Today: "\"mcpServers\": {"
  - Change: none — out of scope (gh-aw `mcp-scripts` declares typed tools (`type`, `required`, `default`, `enum`) inline in workflow frontmatter, run by an HTTP MCP server on the Actions runner outside the agent container. `.mcp.json` only registers external servers. Where this repository needs typed-input tools, `plugins/fastmcp-creator/skills/fastmcp-creator/SKILL.md` line 114 shows `@mcp.tool` on a typed function and `references/server-core.md` line 114 states FastMCP "Generates an input schema from type annotations", so the capability exists in FastMCP form. This repository has no gh-aw workflow that would host inline tools, so no gap in `.mcp.json` handling can be stated)

---

## References

- [GitHub Agentic Workflows README](https://github.com/github/gh-aw) (accessed 2026-10-02)
- [AI Engines reference](https://github.com/github/gh-aw/blob/v0.89.21/docs/src/content/docs/reference/engines.md) (accessed 2026-10-03)
- [MCP Scripts reference](https://github.com/github/gh-aw/blob/v0.89.21/docs/src/content/docs/reference/mcp-scripts.md) (accessed 2026-10-03)
- [GitHub Agentic Workflows How It Works](https://github.github.com/gh-aw/introduction/how-they-work/) (accessed 2026-10-02)
- [Quick Start Guide](https://github.github.com/gh-aw/setup/quick-start/) (accessed 2026-10-02)
- [Installation Documentation](https://raw.githubusercontent.com/github/gh-aw/main/install.md) (accessed 2026-10-02)
- [Workflow Creation Guide](https://raw.githubusercontent.com/github/gh-aw/main/create.md) (accessed 2026-10-02)
- [CHANGELOG](https://github.com/github/gh-aw/blob/main/CHANGELOG.md) (accessed 2026-10-02)
- [Security Policy](https://github.com/github/gh-aw/blob/main/SECURITY.md) (accessed 2026-10-02)
- [go.mod](https://github.com/github/gh-aw/blob/main/go.mod) (accessed 2026-10-02)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [GitHub CLI](./github-cli.md) | developer-tools | Official GitHub CLI tool that gh-aw extends as a custom command |
| [gh-skill](./gh-skill.md) | developer-tools | Skill library for GitHub CLI extending command capabilities |
| [Claude Code CLI Power Patterns](./claude-code-cli-power-patterns.md) | developer-tools | Patterns for orchestrating Claude Code CLI with other tools |
| [wrkflw](./wrkflw.md) | developer-tools | Local GitHub Actions validator enabling workflow preview before gh-aw compilation |
| [Spec Workflow MCP](../mcp-ecosystem/spec-workflow-mcp.md) | mcp-ecosystem | Spec-driven workflow MCP with similar approval-gated task execution model |
| [OctoCode MCP](../mcp-ecosystem/octocode-mcp.md) | mcp-ecosystem | Research-driven MCP with GitHub semantic code search for agent context |
| [Flue](../agent-frameworks/flue.md) | agent-frameworks | Agent harness framework supporting MCP servers and durable execution, complementing gh-aw's workflow model |
| [GitHub Patterns](../research-agent-patterns/github-patterns.md) | research-agent-patterns | Research on GitHub-based multi-agent patterns and orchestration architectures |
