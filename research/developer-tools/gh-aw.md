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
  next_review: 2026-11-14
  confidence_map: "Overview: high | Problem Addressed: high | Key Features: medium (doc + code-read) | Technical Architecture: medium (doc + code-read) | Installation & Usage: high | Limitations and Caveats: high"
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

- Agent jobs are read-only and sandboxed by default: "Supported agent jobs run with minimal permissions and no write access by default." Source: `docs/src/content/docs/introduction/how-they-work.mdx`; the security architecture page describes the sandbox as the Agent Workflow Firewall (AWF) plus an API proxy and an MCP Gateway (`docs/src/content/docs/introduction/architecture.mdx`)
- "Strict Mode: Security-first validation and sandboxing" enforces execution constraints. Per the frontmatter reference, `strict:` "Enables enhanced security validation for production workflows. Default: `true`"; workflows compiled with `strict: false` "cannot run on public repositories", and setting `"strict": true` in `.github/workflows/aw.json` enforces strict mode for every `gh aw compile` invocation in the repository. In strict mode, `${{ secrets.* }}` in the workflow-level `env:` section and `run-install-scripts: true` are compilation errors, and disabling the agent sandbox (`sandbox.agent: false`) is rejected; the network reference adds that strict mode warns when individual ecosystem member domains (for example `pypi.org`) are listed instead of the ecosystem identifier. Source: `docs/src/content/docs/reference/frontmatter.md`, `docs/src/content/docs/reference/network.md`, `docs/src/content/docs/reference/sandbox.md`
- The agent sandbox defaults to `sandbox.agent: awf` (Agent Workflow Firewall); per the sandbox reference, `sandbox.agent.runtime` selects among `docker` (default), `docker-sudo-iptables`, `gvisor` (deprecated), `docker-sbx` (deprecated) and `cloud-hypervisor` (preview). Source: `docs/src/content/docs/reference/sandbox.md`
- Configured GitHub writes go through validated safe-outputs jobs with scoped permissions
- Secret redaction with built-in patterns for GitHub, Azure, Google, AWS, OpenAI, and Anthropic credentials. Source: `actions/setup/js/redact_secrets.cjs` — the pattern list (also includes a Linear API key pattern)

### MCP Server Integration

- "MCP Server Integration: Connect to Model Context Protocol servers for tools"
- Workflows can define MCP servers in frontmatter for structured tool access. Per the tools reference, an `mcp-servers:` entry takes `command` + `args` (process-based), `container` (Docker image), `url` + `headers` (HTTP endpoint), `registry` (informational registry URI), `env`, `allowed` (tool restrictions) and `required`; by default every server must pass a startup connectivity check, and `required: false` turns an unreachable server into a warning. Example from that reference:

  ```yaml
  mcp-servers:
    slack:
      command: "npx"
      args: ["-y", "@slack/mcp-server"]
      env:
        SLACK_BOT_TOKEN: "${{ secrets.SLACK_BOT_TOKEN }}"
      allowed: ["send_message", "get_channel_history"]
  ```

  Source: `docs/src/content/docs/reference/tools.md` (Custom MCP Servers)
- `mcp-scripts:` defines custom MCP tools inline in frontmatter as JavaScript (`script:`), shell (`run:`), Python (`py:`) or Go (`go:`); each tool requires `description:` and exactly one of those four fields. Upstream renamed the earlier `safe-inputs` feature to `mcp-scripts` (changeset `minor-rename-safe-inputs-to-mcp-scripts.md`, which also adds a `safe-inputs-to-mcp-scripts` codemod)
- Inputs are typed: each `inputs:` entry takes `type`, `required`, `default`, `description` and `enum`. Tools are "generated at runtime and run as an HTTP MCP server **on the GitHub Actions runner, outside the agent container**", reached by the agent via `host.docker.internal`
- Only `env:`-declared variables are forwarded to a tool, `${{ secrets.* }}` values are masked in logs, `timeout:` defaults to 60 seconds (enforced for `run:` and `py:`, not for in-process `script:`), and output over 500 characters is saved to a file whose path, size and schema preview are returned to the agent
- The reference warns that mcp-scripts "must only implement READ-ONLY operations" because they run outside the sandbox; writes belong in safe outputs. Source: `docs/src/content/docs/reference/mcp-scripts.md`, `docs/public/schemas/mcp-scripts-config.schema.json`

### Shared Components & Repo Memory

- "Shared Components: Reusable workflow building blocks" enable common patterns across workflows. Per the imports reference, a workflow lists shared files under `imports:` in frontmatter (for example `shared/common-tools.md`), or uses `{{#runtime-import filepath}}` in the markdown body; "Files without a trigger event are shared workflow components" that are validated and importable but "not compiled into standalone GitHub Actions". Shared workflows that declare an `import-schema` take parameters through `uses`/`with`, and a file may appear at most once in an import graph (importing it with different `with` values is a compile-time error). Merge rules per the compilation reference: tools deep-merge, imported MCP servers override same-named main-workflow servers, network domains are unioned, and the main workflow's safe-outputs override imported ones per type. Source: `docs/src/content/docs/reference/imports.md`, `docs/src/content/docs/reference/compilation-process.md`
- "Repo Memory: Persistent git-backed storage for agents" allows workflows to maintain state. Per the repo-memory reference, `tools: repo-memory: true` creates branch `memory/default`, mounted at `/tmp/gh-aw/repo-memory-default/`, and files auto-commit and push after workflow completion. Options include `branch-name`, `branch-prefix`, `file-glob`, `max-file-size` (default 100KB), `max-file-count` (default 100), `max-patch-size` (default 10KB, max 1MB), `allowed-extensions` and `validation.script`; multiple configurations are a list with a required `id` each. gh-aw auto-commits and pushes when changes are present and threat detection passes. Source: `docs/src/content/docs/reference/repo-memory.md`

---

## Technical Architecture

The gh-aw tooling consists of several layered components. Each claim below is read from the v0.89.21 source tree, and the `Source:` line names the file and the exported (or, where no exported name carries the claim, the package-level) identifier.

**End-to-end execution flow**: Per the compilation reference, `gh aw compile` runs five phases (parsing, validation, job construction, dependency resolution, YAML generation) and emits a `.lock.yml`; "the markdown body is loaded at runtime", so instructions can be edited without recompilation. The generated jobs run in topological order: pre-activation (role checks, deadlines, skip conditions; only when needed) -> activation (context preparation, event-text sanitization, lock-file freshness) -> agent (runs the configured engine and MCP servers, uploads `agent_output.json` as an artifact) -> detection (scans agent output; only when `safe-outputs.threat-detection:` is configured) -> safe-output jobs (download the artifact and perform the GitHub API writes) -> conclusion (aggregates results). Source: `docs/src/content/docs/reference/compilation-process.md` (Overview, Compilation Phases, Job Types, Job Dependency Graphs)

**Design rationale for the job split**: The compilation reference states that detection, safe outputs and conclusion "form a **sequential security pipeline**" and "cannot be merged because GitHub Actions permissions are per-job and immutable for the duration of a job"; a combined job "would hold write permissions while running threat detection, defeating least privilege and letting a compromised agent bypass the gate". It lists further reasons for job-level isolation: hard gating through the `safe_outputs` condition `needs.detection.outputs.success == 'true'`, `always()` semantics for `conclusion`, right-sized runners, concurrency isolation, and artifact-based handoff. The security architecture page frames this as plan-level trust, in which "the trusted compiler decomposes a workflow into stages" and the SafeOutputs subsystem buffers externalized writes as artifacts. Source: `docs/src/content/docs/reference/compilation-process.md` (Why Detection, Safe Outputs, and Conclusion Are Separate Jobs), `docs/src/content/docs/introduction/architecture.mdx` (Layer 3: Plan-Level Trust). The sources searched do not state a design rationale for the engine-registry split specifically; that is not mentioned in the documentation read.

**Extension points** (documented as workflow-author configuration, not as a plugin API): `engine:` selects an engine from the registry; `imports:` and `{{#runtime-import ...}}` add shared components; `mcp-servers:` and `mcp-scripts:` add tools; `safe-outputs.jobs:` adds custom jobs with full GitHub Actions syntax, and `jobs:` adds further workflow jobs with user-defined dependencies. Source: `docs/src/content/docs/reference/engines.md`, `docs/src/content/docs/reference/imports.md`, `docs/src/content/docs/reference/tools.md`, `docs/src/content/docs/reference/compilation-process.md` (Custom Jobs)

**CLI layer**: `main.go` builds a Cobra root command and registers the commands built by `createCommandSet()` (35 command constructors in its struct literal at v0.89.21, counted from `cmd/gh-aw/main.go`) and `addCommandsToRoot()`; the set includes `add`, `add-wizard`, `init`, `status`, `logs`, `audit`, `doctor`, `fix`, `validate`, `lint` and `mcp-server`, and `compile` and `new` are defined separately as `compileCmd` and `newCmd`. Source: `cmd/gh-aw/main.go` — `createCommandSet()`, `addCommandsToRoot()`, `rootCmd`

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
on:
  issues:
    types: [opened]

tools:
  github:
    toolsets: [issues]
---

# Workflow Description

Read the issue #${{ github.event.issue.number }}. Add a comment to the issue listing useful resources and links.
```

Source: the example in `docs/src/content/docs/reference/workflow-structure.md`, which describes each workflow as two parts: "YAML frontmatter wrapped in `---` for configuration and a markdown body for agent instructions". Workflow files live in `.github/workflows` as `*.md` and compile to `*.lock.yml`. The frontmatter reference separately documents optional fields such as `emoji:` ("An optional emoji to represent the workflow visually"), `strict:` and `sandbox:` (`docs/src/content/docs/reference/frontmatter.md`).

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

Source for the commands in this section: `docs/src/content/docs/setup/cli.md` (`new`, `add-wizard`, `compile`, `run`, `status`, `logs`, `audit`, `doctor`) and the `--validate` / `--no-emit` flag help in `cmd/gh-aw/main.go` (`compileCmd`).

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

## Limitations and Caveats

- **Security advisory**: "A [security vulnerability](https://github.com/github/gh-aw/security/advisories/GHSA-8h78-hpm7-29gg) was discovered in versions `>= 0.83.3, < 0.85.4` and, as a result, those releases were retired as a pre-emptive measure." Users should upgrade to v0.85.4 or later.
- **Engine differences**: "Not all features are available across all engines." Changing engines "may also require different authentication, tools, model names, or network access" (engines reference).
- **Unsupported engine samples**: OpenCode, Aider, Crush, Cursor, DeepSeek Harness, Kiro and Pydantic AI integrations "are **samples only**" with "no compatibility or maintenance commitment" (engines reference).
- **Compilation required**: "Workflows must be compiled to `.lock.yml` files before running in GitHub Actions" (`create.md`).
- **MCP scripts run outside the sandbox**: "MCP Scripts run outside the agent sandbox and must only implement READ-ONLY operations" (mcp-scripts reference).
- **Permissions scoping**: "Safe outputs buffer configured writes, validate them, and apply them in separate jobs with scoped permissions. These controls are configurable, so workflow authors must review permissions, tools, network access, and generated files before deployment."

---

## References

- [GitHub Agentic Workflows README](https://github.com/github/gh-aw) (accessed 2026-10-02)
- [CLI reference](https://github.com/github/gh-aw/blob/v0.89.21/docs/src/content/docs/setup/cli.md) (accessed 2026-10-06)
- [Compilation Process reference](https://github.com/github/gh-aw/blob/v0.89.21/docs/src/content/docs/reference/compilation-process.md) (accessed 2026-10-06)
- [Security Architecture](https://github.com/github/gh-aw/blob/v0.89.21/docs/src/content/docs/introduction/architecture.mdx) (accessed 2026-10-06)
- [Frontmatter reference](https://github.com/github/gh-aw/blob/v0.89.21/docs/src/content/docs/reference/frontmatter.md) (accessed 2026-10-06)
- [Network reference](https://github.com/github/gh-aw/blob/v0.89.21/docs/src/content/docs/reference/network.md) (accessed 2026-10-06)
- [Sandbox reference](https://github.com/github/gh-aw/blob/v0.89.21/docs/src/content/docs/reference/sandbox.md) (accessed 2026-10-06)
- [Tools reference](https://github.com/github/gh-aw/blob/v0.89.21/docs/src/content/docs/reference/tools.md) (accessed 2026-10-06)
- [Imports reference](https://github.com/github/gh-aw/blob/v0.89.21/docs/src/content/docs/reference/imports.md) (accessed 2026-10-06)
- [Repo Memory reference](https://github.com/github/gh-aw/blob/v0.89.21/docs/src/content/docs/reference/repo-memory.md) (accessed 2026-10-06)
- [Workflow Structure reference](https://github.com/github/gh-aw/blob/v0.89.21/docs/src/content/docs/reference/workflow-structure.md) (accessed 2026-10-06)
- [How They Work (source)](https://github.com/github/gh-aw/blob/v0.89.21/docs/src/content/docs/introduction/how-they-work.mdx) (accessed 2026-10-06)
- [AI Engines reference](https://github.com/github/gh-aw/blob/v0.89.21/docs/src/content/docs/reference/engines.md) (accessed 2026-10-03)
- [MCP Scripts reference](https://github.com/github/gh-aw/blob/v0.89.21/docs/src/content/docs/reference/mcp-scripts.md) (accessed 2026-10-03)
- [GitHub Agentic Workflows How It Works](https://github.github.com/gh-aw/introduction/how-they-work/) (accessed 2026-10-02)
- [Quick Start Guide](https://github.github.com/gh-aw/setup/quick-start/) (accessed 2026-10-02)
- [Installation Documentation](https://raw.githubusercontent.com/github/gh-aw/main/install.md) (accessed 2026-10-02)
- [Workflow Creation Guide](https://raw.githubusercontent.com/github/gh-aw/main/create.md) (accessed 2026-10-02)
- [CHANGELOG](https://github.com/github/gh-aw/blob/main/CHANGELOG.md) (accessed 2026-10-02)
- [Security Policy](https://github.com/github/gh-aw/blob/main/SECURITY.md) (accessed 2026-10-02)
- [go.mod](https://github.com/github/gh-aw/blob/v0.89.21/go.mod) (accessed 2026-10-06)

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
