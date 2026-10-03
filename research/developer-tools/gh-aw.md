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
  last_verified: 2026-10-02
  version_at_verification: v0.89.21
  next_review: 2027-01-02
  confidence_map: "Overview: high | Problem Addressed: high | Key Features: high | Technical Architecture: medium (code-read) | Installation & Usage: high | Limitations & Caveats: high | Relevance: medium"
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
| Switching between multiple AI engines | Built-in support for Copilot, Claude, OpenAI Codex, Google Gemini, and Pi without workflow rewrite |
| Lack of tool access for agents | MCP (Model Context Protocol) server integration provides structured tool access |
| GitHub API abuse or misconfiguration | Read-only execution by default; writes go through scoped permission validation |

---

## Key Features

### Natural Language Workflow Definition

- Workflows are Markdown files with YAML frontmatter: "An agentic workflow has two parts: YAML frontmatter configures triggers, permissions, tools, and the AI engine; the Markdown body tells the AI agent what to accomplish."
- No DSL or workflow YAML required; agents read task descriptions in plain English

### AI Engine Support

- Built-in support for multiple engines: "Built-in AI engines include GitHub Copilot, Claude Code, OpenAI Codex, Google Gemini, and Pi."
- Selectable per-workflow with `--engine` flag validation and suggestions

### Compiler & Lock Files

- `gh aw compile` command validates Markdown workflows and generates `.lock.yml` files for GitHub Actions execution
- Lock files are deterministic, reviewable, and can be committed to version control
- Compilation failure reports all validation errors together or fails fast with `--fail-fast` flag

### Security & Sandboxing

- Agent jobs are read-only and sandboxed by default
- "Strict Mode: Security-first validation and sandboxing" enforces execution constraints
- Configured GitHub writes go through validated safe-outputs jobs with scoped permissions
- Secret redaction with built-in patterns for GitHub, Azure, Google, AWS, OpenAI, and Anthropic credentials

### MCP Server Integration

- "MCP Server Integration: Connect to Model Context Protocol servers for tools"
- Workflows can define MCP servers in frontmatter for structured tool access
- Safe-inputs framework validates tool inputs before agent use

### Shared Components & Repo Memory

- "Shared Components: Reusable workflow building blocks" enable common patterns across workflows
- "Repo Memory: Persistent git-backed storage for agents" allows workflows to maintain state

---

## Technical Architecture

The gh-aw tooling consists of several layered components:

**CLI & Parser Layer**: The main entry point (`cmd/gh-aw/main.go`) uses Cobra for command routing. Supported commands include `init`, `new`, `compile`, `run`, `logs`, `audit`, `doctor`, `add-wizard`, `status`, and `fix`. The parser package handles Markdown+YAML syntax validation against a JSON Schema specification.

**Compiler**: The central component that transforms agentic workflow files into standard GitHub Actions workflows (`.lock.yml`). Compiled workflows embed:
- Agent task prompts and system instructions
- AI engine selection and configuration
- MCP server definitions and tool mappings
- Safe-outputs middleware configuration for write validation
- Permission scoping for repository access

**Engine Registry**: A pluggable architecture for AI engines. The registry (`pkg/workflow/engine.go`) maintains a list of supported engines and their configuration. Validation occurs before compilation to provide user-friendly error messages with suggestions.

**Workflow Package** (`pkg/workflow/`): Core domain logic including:
- Action resolution and pinning for GitHub Actions dependencies
- Agent drain and orchestration coordination
- Safe-outputs job generation and validation
- Secret pattern detection and redaction

**Safe-Outputs Framework**: Middleware layer that intercepts and validates structured writes to GitHub APIs. Instead of direct API calls, agents emit structured JSON that safe-outputs jobs validate against declared permissions before execution.

**Dependencies**: Uses `charm.land` (bubbletea/bubbles) for interactive CLI UI, `github.com/cli/go-gh/v2` for GitHub CLI SDK integration, `github.com/modelcontextprotocol/go-sdk` (v1.8.0) for MCP protocol support, and `spf13/cobra` for CLI framework. Written in Go 1.26.8.

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

This creates the `.github/aw/` directory structure and initializes workflow configuration.

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

Validate without compiling:

```bash
gh aw compile --validate
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
- **MCP server availability**: MCP server integrations require the server to be available during workflow execution; unavailable servers will fail the workflow.
- **Engine dependency**: "Workflows must specify a valid engine; fallback or auto-detection is not supported." Token limits vary by engine and may impact complex reasoning tasks.
- **Compilation required**: "Workflows must be compiled to `.lock.yml` before execution; direct Markdown execution in GitHub Actions is not supported."
- **Permissions scoping**: "Safe outputs buffer configured writes, validate them, and apply them in separate jobs with scoped permissions. These controls are configurable, so workflow authors must review permissions, tools, network access, and generated files before deployment."

---

## Relevance to Claude Code Development

### Applications

- **Multi-engine AI agent orchestration** -> `./.claude/skills/README.md`
  - Term: `orchestration`
  - Today: "Provides a global contract that enforces disciplined behavior patterns for specialist agents in orchestrated workflows. Not directly user-invocable - loaded by role-based agents that participate in orchestration patterns."
  - Change: already covered — `scripts/generate_harness_compatibility.py` keeps a `HARNESSES` registry and rejects unknown names (lines 124-131)

- **Markdown-based declarative workflow definitions** -> `./.claude/agents/backlog-mcp-validator.md`
  - Term: `frontmatter`
  - Today: "The `backlog` server is configured in this agent's `mcpServers` frontmatter."
  - Change: none — `.claude/agents/` files use YAML frontmatter for MCP server configuration; gh-aw validates a similar pattern for workflow tools

### Integration Opportunities

- **MCP server integration patterns** -> `.mcp.json`
  - Term: `MCP`
  - Today: "`mcpServers` configuration with environment variable indirection: `"REF_API_KEY": "$REF_API_KEY"`"
  - Change: out of scope — the entry does not say what safe-inputs validates or against what schema, so no gap in `.mcp.json` handling can be stated

---

## References

- [GitHub Agentic Workflows README](https://github.com/github/gh-aw) (accessed 2026-10-02)
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
