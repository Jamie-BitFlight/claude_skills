# Cline - Open-Source Autonomous Coding Agent

**Research Date**: 2026-02-23
**Source URL**: <https://cline.bot>
**GitHub Repository**: <https://github.com/cline/cline>
**Documentation**: <https://docs.cline.bot>
**VS Code Marketplace**: <https://marketplace.visualstudio.com/items?itemName=saoudrizwan.claude-dev>
**Version at Research**: v3.66.0
**License**: Apache-2.0

---

## Overview

Cline is an open-source autonomous coding agent that integrates directly into VS Code and the terminal (CLI + Editor). It handles complex, multi-step software development tasks — creating and editing files, executing terminal commands, automating browser interactions, and extending its own capabilities via MCP servers — while requiring explicit human approval for every action. Cline supports any AI provider (Anthropic, OpenAI, Google, AWS Bedrock, local models) and is positioned as the open, privacy-first alternative to proprietary agents like GitHub Copilot.

**Core Value Proposition**: A fully transparent, human-in-the-loop coding agent that works with any LLM, keeps code on your infrastructure, and can be extended via open standards (MCP, skills, hooks).

---

## Problem Addressed

| Problem | Solution |
| ----------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| Proprietary coding assistants lock teams into specific LLM vendors | Model-agnostic architecture supports Anthropic, OpenAI, Google, AWS Bedrock, Azure, Groq, Cerebras, and local models via Ollama/LM Studio |
| AI agents making unsanctioned changes to production code | Human-in-the-loop GUI requires explicit approval for every file change, terminal command, and browser action |
| Enterprise compliance and data residency requirements | All inference routed through your own API keys; code never sent to Cline's servers |
| Agentic tools that can't understand large, complex codebases | AST parsing, regex search, and file structure analysis for project-wide understanding without overflowing context |
| High AI inference costs with opaque billing | Per-request token and cost tracking; no markup on API usage — you pay providers directly |
| One-size-fits-all AI tools that can't be customized | Extensible via `.clinerules`, skills, hooks, workflows, subagents, and MCP servers |

---

## Key Statistics (as of 2026-02-23)

| Metric | Value | Date Gathered |
| --------------------- | ----------- | -------------- |
| GitHub Stars | ~58,200 | 2026-02-23 |
| GitHub Forks | ~5,800 | 2026-02-23 |
| Contributors | 400+ | 2026-02-23 |
| Latest Release | v3.66.0 | 2026-02-21 |
| VS Code Installs | Millions | 2026-02-23 |
| Open Issues | Active | 2026-02-23 |
| License | Apache-2.0 | — |
| Release Cadence | Multiple/week | 2026-02-23 |

---

## Key Features

### Autonomous Agent with Human-in-the-Loop

- Handles multi-step development tasks end-to-end (create, edit, test, fix, deploy)
- Every file change, terminal command, and browser action requires explicit user approval
- Visual diff view for reviewing all file modifications before accepting
- Checkpoint system (Git-like) for rolling back any step in a task

### Codebase Intelligence

- Reads and analyzes file structures, source code ASTs, and configuration files
- Regex search across the entire project to locate relevant code
- Proactively monitors linter and compiler errors, fixes issues without prompting
- Context-window management to handle large codebases without overflow

### Multi-Model Support

- Supports OpenRouter, Anthropic, OpenAI, Google Gemini, AWS Bedrock, Azure, GCP Vertex, Cerebras, and Groq
- Connects to local models via LM Studio or Ollama
- OpenRouter integration fetches latest available models in real time
- Per-task and per-request token and cost tracking

### Terminal and Command Execution

- Executes commands directly in the VS Code integrated terminal (VSCode v1.93+ shell integration)
- "Proceed While Running" for long-lived processes (dev servers, builds)
- Monitors background terminal output to react to new errors
- Supports installing packages, running test suites, deploying applications

### Browser Automation

- Headless browser integration using Claude Computer Use capability
- Click, type, scroll, screenshot, and capture console logs
- Full-stack interactive debugging — launches dev servers and performs E2E tests
- Screenshot-to-code support (attach mockup images, get functional implementations)

### Extensibility

- **MCP Servers**: Extend Cline with any Model Context Protocol tool — create custom tools and data sources
- **Skills**: Reusable prompt libraries that improve Cline's domain knowledge
- **Hooks**: Event-based automation (pre/post-task scripts)
- **Workflows**: Structured multi-step procedures stored in the workspace
- **Subagents**: Spawn parallel Cline instances for concurrent tasks
- **`.clinerules`**: Per-project rule files controlling Cline's behavior
- **`.clineignore`**: Exclude files and directories from Cline's context

### Cline CLI

- Command-line interface for headless/CI/CD automation
- Interactive mode for terminal-first developers
- CI/CD integration for automated development pipelines

### Enterprise Features

- **Single Sign-On (SSO)** and role-based access control (RBAC)
- **Centralized API key management** and remote configuration
- **Usage analytics and observability**: OpenTelemetry export, Datadog/Grafana/Splunk integration
- **Audit logging**: Selective audit trails for file changes and admin events
- **No markup on AI costs**: Teams pay providers at their negotiated rates
- **Compliance-ready**: Code stays on-premises; no remote indexing or vendor-side training

---

## Technical Architecture

<eg>
┌─────────────────────────────────────────────────────────────────┐
│                         Cline Agent                              │
└─────────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   VS Code Ext   │  │   Cline CLI     │  │   Enterprise     │
│                 │  │                 │  │   Dashboard      │
│ - Sidebar GUI   │  │ - Headless mode │  │ - SSO / RBAC     │
│ - Diff viewer   │  │ - Interactive   │  │ - Usage analytics│
│ - Approval UI   │  │ - CI/CD hooks   │  │ - Audit logs     │
└─────────────────┘  └─────────────────┘  └─────────────────┘
         │                    │
         └──────────┬─────────┘
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Cline Core Engine                            │
│                                                                  │
│  Task Planner → Tool Executor → Approval Gate → Result Monitor  │
│                                                                  │
│  Tools: FileSystem | Terminal | Browser | MCP | Subagents       │
└─────────────────────────────────────────────────────────────────┘
                    │
         ┌──────────┼──────────┐
         ▼          ▼          ▼
┌──────────────┐ ┌─────────┐ ┌──────────────────────────────────┐
│  LLM Provider│ │   MCP   │ │   Workspace                       │
│              │ │ Servers │ │                                    │
│ - Anthropic  │ │         │ │ .clinerules / .clineignore         │
│ - OpenAI     │ │ Custom  │ │ skills/ / hooks/ / workflows/      │
│ - Gemini     │ │ tools & │ │ checkpoints (Git-like snapshots)   │
│ - Bedrock    │ │ data    │ │                                    │
│ - Local LLMs │ │ sources │ │                                    │
└──────────────┘ └─────────┘ └──────────────────────────────────┘
</eg>

**Key architectural decisions**:

- **Plan & Act modes**: Separate "planning" (reasoning) phase from "execution" phase — prevents wasted API calls on implementation before strategy is solid
- **Context compression**: Manages long-running tasks without exceeding context window limits
- **Checkpoint system**: Snapshots workspace state at each step for granular rollback
- **Zero data egress**: All API calls go directly from the developer's machine to LLM providers

---

## Installation & Usage

### VS Code Extension

```bash
# Install from VS Code Marketplace
# Search for "Cline" or "saoudrizwan.claude-dev"
# Or install via command line:
code --install-extension saoudrizwan.claude-dev
```

### Cline CLI

```bash
# Install globally via npm
npm install -g @cline/cli

# Run in interactive mode
cline

# Run a specific task headlessly
cline --task "Add unit tests to src/utils.ts" --model claude-3-7-sonnet
```

### Configuration Example (.clinerules)

<eg>
# .clinerules
- Always write tests for new functions
- Use TypeScript strict mode
- Follow project ESLint rules before committing
- Ask before modifying package.json dependencies
</eg>

---

## Modes of Operation

### Plan Mode

Cline reasons about the task, proposes a strategy, and discusses options before taking any action. Ideal for complex or ambiguous tasks where strategy matters.

### Act Mode

Cline executes immediately, step-by-step, with approvals at each action. Best for well-defined, scoped tasks.

### Auto-Approve

For trusted, low-risk operations, users can configure auto-approval rules to reduce friction on repetitive tasks.

---

## Relevance to Claude Code Development

### Applications

- **Direct Competitor Analysis**: Cline is explicitly positioned as an open-source alternative to Claude Code; understanding its feature set, UX patterns, and community feedback informs Claude Code product development
- **MCP Ecosystem Reference**: Cline's MCP marketplace implementation is a mature example of extensibility patterns to study
- **Plugin Architecture Patterns**: Skills, hooks, workflows, and `.clinerules` concepts map closely to this repository's plugin and skill model
- **CLI Design Reference**: Cline CLI's headless/CI/CD patterns are relevant to automating Claude Code workflows
- **Enterprise Feature Blueprint**: Cline's enterprise governance features (SSO, RBAC, audit logs, cost tracking) represent what production-grade agent deployments require

### Patterns Worth Adopting

- **Plan & Act separation**: Two-mode operation prevents wasted LLM calls — plan first, execute second
- **Checkpoint/rollback system**: Per-step workspace snapshots enable fine-grained recovery from mistakes
- **`.clinerules` per-project config**: Lightweight, file-based behavioral rules that travel with the repo
- **Explicit approval gates**: Visual diff views + per-action approval dialogs as the UX model for safe automation
- **Cost transparency**: Per-request token/cost tracking surfaced in the UI — builds trust and prevents runaway costs
- **Context window management**: AST-based project analysis with selective context inclusion rather than dumping all files

### Integration Opportunities

- **Shared MCP Tool Ecosystem**: Cline and Claude Code both support MCP — skills developed for one may transfer to the other
- **Parallel Testing**: Run the same tasks against Cline and Claude Code to benchmark feature parity and identify gaps
- **`.clinerules` ↔ Claude Code skills**: The `.clinerules` pattern could inform how Claude Code skills encode project-specific behavioral constraints
- **Cline CLI for CI/CD**: Cline CLI can automate development tasks in GitHub Actions pipelines, complementing Claude Code's agent execution capabilities

### Competitive Analysis

| Feature | Cline | Claude Code |
| ----------------------------- | ---------------------- | ------------------- |
| Open Source | Yes (Apache-2.0) | No |
| IDE Integration | VS Code extension | Terminal CLI |
| Model Support | Any (multi-provider) | Claude only |
| Human-in-the-Loop | Yes (required) | Yes (configurable) |
| MCP Support | Yes (native) | Yes (native) |
| CLI / Headless Mode | Yes | Yes |
| Enterprise Governance | Yes (SSO, RBAC, audit) | Limited |
| Browser Automation | Yes | Limited |
| Custom Skills/Hooks | Yes | Yes (this repo) |
| Pricing Model | Free + $20/user/mo teams | Subscription |
| Data Residency | On-premise (your keys) | Anthropic-managed |
| Benchmark Performance | Not published | Not published |

---

## References

- [Cline Official Website](https://cline.bot) (accessed 2026-02-23)
- [GitHub Repository: cline/cline](https://github.com/cline/cline) (accessed 2026-02-23)
- [Cline Documentation](https://docs.cline.bot/home) (accessed 2026-02-23)
- [VS Code Marketplace: Cline](https://marketplace.visualstudio.com/items?itemName=saoudrizwan.claude-dev) (accessed 2026-02-23)
- [Cline Enterprise Documentation](https://docs.cline.bot/enterprise-solutions/overview) (accessed 2026-02-23)
- [Cline CLI Documentation](https://docs.cline.bot/cline-cli/overview) (accessed 2026-02-23)
- [GitHub Releases: cline/cline](https://github.com/cline/cline/releases) (accessed 2026-02-23)

---

## Freshness Tracking

| Field | Value |
| ------------------------------- | --------------------- |
| Last Verified | 2026-02-23 |
| Version at Verification | v3.66.0 |
| GitHub Stars at Verification | ~58,200 |
| Next Review Recommended | 2026-05-23 (3 months) |

**Change Detection Indicators**:

- Monitor GitHub releases for new versions (currently multiple releases per week)
- Track feature announcements on the [Cline blog](https://cline.bot/blog)
- Check pricing changes (Teams tier was free through Q1 2026, then $20/user/month)
- Watch for MCP marketplace expansions
- Monitor star growth trajectory (highly active community)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Claude CodePro](./claude-codepro.md) | coding-agents | referenced by Claude CodePro (coding-agents) |
