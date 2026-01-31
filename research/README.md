# Research Directory

This directory contains curated research on tools, repositories, and patterns relevant to agentic AI development with Claude Code.

**Purpose**: Provide reference material for developing Claude Code skills, agents, plugins, and workflows by documenting novel approaches from the community.

---

## Directory Structure

```text
research/
├── README.md                          # This index file
├── agent-frameworks/                  # Agent SDKs and orchestration frameworks
│   ├── ai-agents-frameworks.md        # 10-framework comparative benchmark study
│   └── superpowers.md                 # Agentic skills framework and dev methodology (40K+ stars)
├── agent-infrastructure/              # Infrastructure for agentic applications
│   └── plano.md                       # AI-native proxy and data plane for multi-agent orchestration
├── code-auditing/                     # Code security and quality auditing tools
│   └── hound.md                       # Autonomous AI security auditor with knowledge graphs
├── coding-agents/                     # Autonomous AI coding agent platforms
│   └── openhands.md                   # Open platform for cloud coding agents (67K+ stars)
├── context-management/                # Memory, context window, and RAG tools
│   └── claude-mem.md                  # Persistent memory compression for Claude Code (15K+ stars)
├── data-infrastructure/               # Real-time data platforms for analytics
│   └── tinybird.md                    # Managed ClickHouse platform with MCP and analytics agents
├── developer-tools/                   # Developer productivity and workflow tools
│   ├── animejs.md                     # Lightweight JavaScript animation engine (66K+ stars)
│   ├── copier-astral.md               # Python project template with Astral toolchain (uv, ruff, ty)
│   ├── git-cliff.md                   # Customizable changelog generator from Git history
│   ├── jscpd.md                       # Copy/paste detector for 150+ languages (5K+ stars)
│   ├── orbstack.md                    # Fast Docker Desktop and Linux VM alternative for macOS
│   └── repomix.md                     # Pack codebase into AI-friendly formats (21K+ stars)
├── mcp-ecosystem/                     # MCP servers and integrations
│   ├── docs-mcp-server.md             # Local documentation index (Grounded Docs)
│   ├── mcpjam.md                      # Local inspector for MCP servers and apps
│   ├── narsil-mcp.md                  # Comprehensive code intelligence MCP server
│   └── octocode-mcp.md                # Research Driven Development platform
├── research-agent-patterns/           # Multi-agent architectures and orchestration
│   ├── compound-engineering-plugin.md # Every Inc's Plan/Work/Review/Compound workflow plugin
│   ├── github-patterns.md             # Patterns from GitHub research agent implementations
│   └── orchestrator-agent-creation-guide.md  # OpenCode orchestrator agent guide
├── skill-generation-tools/            # Tools that create AI skills/prompts
│   └── skill-seekers.md               # Documentation-to-skill automation tool
└── task-management/                   # AI-powered task management for development
    └── claude-task-master.md          # Task management system for AI-driven development (25K+ stars)
```

---

## Research Categories

### 1. Research Agent Patterns

**Location**: [./research-agent-patterns/](./research-agent-patterns/)

Research on multi-agent architectures, orchestration patterns, and research workflows.

| Document                                                                                               | Description                                                                                                            | Last Updated |
| ------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------- | ------------ |
| [compound-engineering-plugin.md](./research-agent-patterns/compound-engineering-plugin.md)             | Every Inc's Claude Code plugin with 27 agents, 20 commands - Plan/Work/Review/Compound workflow (6.8K stars)           | 2026-01-31   |
| [github-patterns.md](./research-agent-patterns/github-patterns.md)                                     | Patterns from 40+ repositories including Chief of Staff model, 12-agent academic pipelines, Pydantic AI research loops | 2025-12-09   |
| [orchestrator-agent-creation-guide.md](./research-agent-patterns/orchestrator-agent-creation-guide.md) | Comprehensive guide for creating orchestrator agents in OpenCode - routing, chaining, parallel delegation patterns     | 2026-01-26   |

**Key Topics**:

- Stateless agent coordination
- File-based context sharing
- Iterative research loops with exit criteria
- Citation and bibliography management
- Multi-phase synthesis without over-summarizing
- Orchestrator routing patterns and capability maps
- Sequential chaining vs parallel delegation
- Context hygiene and token management
- Plan/Work/Review/Compound workflow (80/20 planning-execution split)
- 14 parallel review agents for comprehensive code review
- Knowledge compounding via structured `docs/solutions/` documentation
- Smart research decision logic (risk-aware, context-aware)
- Git worktree integration for parallel development
- Claude Code plugin architecture patterns

---

### 2. MCP Ecosystem

**Location**: [./mcp-ecosystem/](./mcp-ecosystem/)

MCP servers, tools, and integrations for extending AI assistant capabilities.

| Document                                                 | Description                                                                                              | Last Updated |
| -------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- | ------------ |
| [docs-mcp-server.md](./mcp-ecosystem/docs-mcp-server.md) | Grounded Docs - local documentation index with semantic search, open-source Context7 alternative         | 2026-01-26   |
| [mcpjam.md](./mcp-ecosystem/mcpjam.md)                   | Local inspector for MCP servers, ChatGPT apps, MCP Apps with LLM playground, OAuth debugger, E2E testing | 2026-01-26   |
| [narsil-mcp.md](./mcp-ecosystem/narsil-mcp.md)           | Rust MCP server with 90 tools for code intelligence, security scanning, call graphs                      | 2026-01-26   |
| [octocode-mcp.md](./mcp-ecosystem/octocode-mcp.md)       | Research Driven Development platform with GitHub search, LSP, and GAN-inspired adversarial flow          | 2026-01-26   |

**Key Topics**:

- Code intelligence and symbol analysis
- Security scanning (OWASP, CWE, taint analysis)
- Call graph and control flow analysis
- Neural semantic search
- Knowledge graphs (SPARQL, CCG)
- Token optimization with configurable presets
- Research Driven Development (RDD) methodology
- GAN-inspired adversarial verification workflows
- GitHub semantic code search
- LSP integration (go-to-definition, find-references)
- Cross-model validation patterns
- Documentation grounding and version-specific retrieval
- Hybrid search (vector + full-text) with RRF ranking
- Privacy-first local documentation indexing
- MCP server local development and testing
- ChatGPT Apps SDK widget emulation
- MCP Apps (SEP-1865) development tooling
- OAuth 2.1 debugging and multi-protocol support
- AI-powered test case generation
- E2E evaluation across MCP clients
- Multi-LLM playground testing

---

### 3. Skill Generation Tools

**Location**: [./skill-generation-tools/](./skill-generation-tools/)

Tools and services that automate the creation of AI skills from documentation, code, and other sources.

| Document                                                      | Description                                                                            | Last Updated |
| ------------------------------------------------------------- | -------------------------------------------------------------------------------------- | ------------ |
| [skill-seekers.md](./skill-generation-tools/skill-seekers.md) | Skill Seekers - converts docs, GitHub repos, and PDFs into Claude/Gemini/OpenAI skills | 2026-01-26   |

**Key Topics**:

- Documentation scraping and extraction
- Multi-source analysis (docs + code + PDFs)
- Conflict detection between docs and implementation
- Three-Stream Architecture (Code/Docs/Insights)
- Multi-platform skill packaging

---

### 4. Code Auditing

**Location**: [./code-auditing/](./code-auditing/)

Tools and frameworks for autonomous code security auditing and vulnerability detection.

| Document                             | Description                                                                                           | Last Updated |
| ------------------------------------ | ----------------------------------------------------------------------------------------------------- | ------------ |
| [hound.md](./code-auditing/hound.md) | Autonomous AI security auditor using knowledge graphs, belief systems, and hypothesis-driven analysis | 2026-01-26   |

**Key Topics**:

- Knowledge graph-driven code analysis
- Hypothesis and belief systems for vulnerability tracking
- Scout/Strategist model switching for cost efficiency
- Coverage vs intuition planning balance
- Interactive steering via chatbot UI
- Session persistence and recovery
- Professional report generation with PoC integration

---

### 5. Agent Frameworks

**Location**: [./agent-frameworks/](./agent-frameworks/)

Agent SDKs, orchestration frameworks, and comparative studies of multi-agent architectures.

| Document                                                              | Description                                                                                                                            | Last Updated |
| --------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | ------------ |
| [ai-agents-frameworks.md](./agent-frameworks/ai-agents-frameworks.md) | Comparative learning repository for 10 AI agent frameworks with benchmarks for response time, memory, tokens, RAG, and API integration | 2026-01-31   |
| [superpowers.md](./agent-frameworks/superpowers.md)                   | Agentic skills framework with 14 skills for TDD, debugging, and subagent-driven development - works with Claude Code, Codex, OpenCode  | 2026-01-31   |

**Key Topics**:

- Framework comparison benchmarks (Agno, LangGraph, LlamaIndex, OpenAI, Pydantic-AI, CrewAI, etc.)
- Memory vs stateless agent performance
- RAG and API integration reliability metrics
- Token efficiency across frameworks
- Progressive example structures
- Subagent-driven development with two-stage review (spec compliance + code quality)
- Test-driven development enforcement for AI agents
- Skill triggering patterns and description optimization
- Fresh context per task to prevent pollution
- DOT flowcharts as executable specifications

---

### 6. Agent Infrastructure

**Location**: [./agent-infrastructure/](./agent-infrastructure/)

Infrastructure tools and platforms for deploying, orchestrating, and managing agentic applications at scale.

| Document                                    | Description                                                                                                     | Last Updated |
| ------------------------------------------- | --------------------------------------------------------------------------------------------------------------- | ------------ |
| [plano.md](./agent-infrastructure/plano.md) | AI-native proxy and data plane built on Envoy - handles orchestration, model routing, observability, guardrails | 2026-01-26   |

**Key Topics**:

- Inner loop (agent logic) vs outer loop (orchestration) separation
- Declarative YAML-based agent routing configuration
- Purpose-built routing models (Plano-Orchestrator 4B)
- Unified LLM gateway with provider abstraction
- Zero-code OpenTelemetry tracing ("Agentic Signals")
- Filter chains for guardrails and moderation
- Prompt targets for deterministic API calls

---

### 7. Developer Tools

**Location**: [./developer-tools/](./developer-tools/)

Developer productivity tools and workflow automation for software engineering with AI assistance.

| Document                                               | Description                                                                                                                  | Last Updated |
| ------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------- | ------------ |
| [animejs.md](./developer-tools/animejs.md)             | Lightweight JavaScript animation engine with declarative API, timelines, staggering, and 30+ easing functions                | 2026-01-31   |
| [copier-astral.md](./developer-tools/copier-astral.md) | Copier template for Python projects with Astral toolchain (uv, ruff, ty), pytest, MkDocs, Typer, GitHub Actions, Docker      | 2026-01-31   |
| [git-cliff.md](./developer-tools/git-cliff.md)         | Customizable changelog generator using conventional commits and regex parsers with GitHub/GitLab remote integration          | 2026-01-26   |
| [jscpd.md](./developer-tools/jscpd.md)                 | Copy/paste detector for 150+ programming languages using Rabin-Karp algorithm with CI/CD integration                         | 2026-01-31   |
| [orbstack.md](./developer-tools/orbstack.md)           | Fast, lightweight Docker Desktop and Linux VM alternative for macOS with 2-second startup and dynamic memory                 | 2026-01-31   |
| [repomix.md](./developer-tools/repomix.md)             | Pack codebase into single AI-friendly file with token counting, Tree-sitter compression, MCP server, and Claude Code plugins | 2026-01-31   |

**Key Topics**:

- Declarative animation APIs for frontend code generation
- Composable building blocks pattern (animate, stagger, timeline)
- Conventional commits specification and parsing
- Customizable Tera templates for changelog output
- GitHub/GitLab/Gitea/Bitbucket remote metadata integration
- Monorepo support with path-based filtering
- Prepend mode for incremental changelog updates
- Semantic versioning correlation (feat→minor, fix→patch)
- Configuration hierarchy (global → project → environment)
- Copy/paste detection with Rabin-Karp algorithm
- Token-based code analysis across 150+ languages
- CI/CD integration with threshold-based quality gates
- SARIF output for GitHub Security tab integration
- Git blame integration for duplication attribution
- Docker Desktop alternative with native macOS performance
- Lightweight Linux VM architecture (similar to WSL 2)
- Dynamic memory allocation (returns unused to macOS)
- Kubernetes single-node cluster for local development
- Multi-distro Linux machine support (15 distributions)
- Zero-config container domains (\*.orb.local)
- Headless/CLI mode for CI automation
- Codebase-to-AI-file packaging for LLM consumption
- Token counting with Tree-sitter code compression (~70% reduction)
- Security scanning via Secretlint integration
- MCP server mode with 7 tools for AI assistant integration
- Claude Code plugins (repomix-mcp, repomix-commands, repomix-explorer)
- Agent Skills generation from local and remote repositories
- Multiple output formats (XML optimized for Claude, Markdown, JSON, Plain)
- Remote repository processing without local cloning
- Split output for large codebases exceeding context limits
- Copier template engine for Python project scaffolding
- Astral toolchain integration (uv, ruff, ty) for modern Python development
- Feature toggles for conditional file generation
- Copier update mechanism for propagating template improvements
- Hatch envs for multi-Python version matrix testing
- Makefile abstraction for complex uv/hatch commands

---

### 8. Coding Agents

**Location**: [./coding-agents/](./coding-agents/)

Autonomous AI coding agent platforms and SDKs for building software development agents.

| Document                                     | Description                                                                                       | Last Updated |
| -------------------------------------------- | ------------------------------------------------------------------------------------------------- | ------------ |
| [openhands.md](./coding-agents/openhands.md) | OpenHands - open platform for cloud coding agents with 77.6% SWE-bench score, SDK, CLI, and cloud | 2026-01-26   |

**Key Topics**:

- Model-agnostic agent architecture
- Python SDK for agent composition
- SWE-bench benchmark performance (77.6% verified)
- Inference-time scaling with critic models
- Docker/Kubernetes sandboxed execution
- REST-based agent server for scaling
- GitHub, GitLab, Slack, Jira integrations
- Open-source alternatives to proprietary coding agents

---

### 9. Data Infrastructure

**Location**: [./data-infrastructure/](./data-infrastructure/)

Real-time data platforms and analytics infrastructure for powering AI applications and agentic workflows.

| Document                                         | Description                                                                                                  | Last Updated |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------ | ------------ |
| [tinybird.md](./data-infrastructure/tinybird.md) | Managed ClickHouse platform for real-time analytics APIs with native MCP server and analytics agents support | 2026-01-31   |

**Key Topics**:

- Managed ClickHouse with zero maintenance overhead
- SQL-to-API instant endpoint generation
- Incremental materialized views for 100x query speedup
- Events API for 1K+ RPS JSON streaming
- Native MCP server integration for AI agents
- Analytics Agents templates and best practices
- Data-as-code with Git-based version control
- Branch-based testing with isolated environments

---

### 10. Task Management

**Location**: [./task-management/](./task-management/)

AI-powered task management systems designed for AI-driven development workflows.

| Document                                                         | Description                                                                                     | Last Updated |
| ---------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- | ------------ |
| [claude-task-master.md](./task-management/claude-task-master.md) | Task Master - PRD parsing, task tracking, and MCP integration for Cursor, Windsurf, Claude Code | 2026-01-26   |

**Key Topics**:

- PRD-to-task automated decomposition
- MCP server with 36 tools (selective loading for context optimization)
- Multi-model architecture (main, research, fallback)
- Model-agnostic support (10+ AI providers)
- IDE integration (Cursor, Windsurf, VS Code, Q Developer)
- Persistent task state with dependencies
- Claude Code plugin patterns

---

### 11. Context Management

**Location**: [./context-management/](./context-management/)

Memory systems, context window optimization tools, and RAG solutions for maintaining state across AI sessions.

| Document                                            | Description                                                                                                   | Last Updated |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- | ------------ |
| [claude-mem.md](./context-management/claude-mem.md) | Claude-Mem - persistent memory compression plugin for Claude Code with 4 MCP tools and progressive disclosure | 2026-01-31   |

**Key Topics**:

- Persistent memory across Claude Code sessions
- Progressive disclosure pattern (3-layer workflow for token efficiency)
- Lifecycle hooks architecture (SessionStart, PostToolUse, SessionEnd, etc.)
- Hybrid search (SQLite FTS5 + Chroma vector embeddings)
- MCP tools for memory search (search, timeline, get_observations)
- Privacy controls with `<private>` tags
- Web viewer UI for memory inspection
- Context injection strategies

---

## Planned Categories

The following categories are planned for future research:

| Category                | Description                                        | Status   |
| ----------------------- | -------------------------------------------------- | -------- |
| `prompt-engineering/`   | Prompt optimization tools and techniques           | Planned  |
| `context-management/`   | Memory, context window, and RAG tools              | **Done** |
| `mcp-ecosystem/`        | MCP servers and integrations                       | **Done** |
| `agent-frameworks/`     | Agent SDKs and orchestration frameworks            | **Done** |
| `agent-infrastructure/` | Infrastructure for deploying agentic apps at scale | **Done** |
| `data-infrastructure/`  | Real-time data platforms for analytics             | **Done** |
| `code-auditing/`        | Code security and quality auditing tools           | **Done** |
| `developer-tools/`      | Developer productivity and workflow tools          | **Done** |
| `coding-agents/`        | Autonomous AI coding agent platforms               | **Done** |
| `task-management/`      | AI-powered task management for development         | **Done** |
| `evaluation-testing/`   | Agent evaluation and testing tools                 | Planned  |

---

## Research Entry Format

Each research document should follow this structure:

```markdown
# [Tool/Repository Name]

**Research Date**: YYYY-MM-DD
**Source URL**: <https://...>
**GitHub Repository**: <https://github.com/...> (if applicable)
**Version at Research**: vX.Y.Z
**License**: [License type]

---

## Overview
[Brief description of what this tool/pattern does]

---

## Problem Addressed
[What problem does this solve?]

---

## Key Features
[Detailed feature breakdown]

---

## Technical Architecture
[How it works internally]

---

## Relevance to Claude Code Development
[How this applies to our work]

---

## References
[Cited sources with access dates]

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | YYYY-MM-DD |
| Version at Verification | vX.Y.Z |
| Next Review Recommended | YYYY-MM-DD |
```

---

## Freshness Policy

Research documents should be reviewed periodically to ensure accuracy:

| Document Age | Review Frequency              |
| ------------ | ----------------------------- |
| < 3 months   | Current                       |
| 3-6 months   | Review recommended            |
| 6-12 months  | Review required               |
| > 12 months  | Stale - requires verification |

**Freshness indicators to monitor**:

- Version changes (check GitHub releases, PyPI, npm)
- Star/fork changes (significant growth may indicate maturity)
- Breaking API changes
- New features that affect recommendations

---

## Contributing Research

When adding new research:

1. **Create appropriate subdirectory** if the category doesn't exist
2. **Follow the entry format** documented above
3. **Include freshness tracking** with specific dates
4. **Cite all sources** with access dates
5. **Update this README** with the new entry in the appropriate table

---

## Quick Reference Links

### External Resources

- [Awesome Claude Code](https://github.com/hesreallyhim/awesome-claude-code) - 17,825 stars
- [Awesome Claude Code Subagents](https://github.com/VoltAgent/awesome-claude-code-subagents) - 5,616 stars
- [Awesome MCP Servers](https://github.com/punkpeye/awesome-mcp-servers) - 76,332 stars
- [Compound Engineering Plugin](https://github.com/EveryInc/compound-engineering-plugin) - Plan/Work/Review/Compound workflow (6,830 stars)
- [Skill Seekers](https://skillseekersweb.com/) - Documentation to AI skills
- [OpenHands](https://openhands.dev) - Open platform for cloud coding agents (67,108 stars)
- [Claude Task Master](https://task-master.dev) - AI-powered task management (25,062 stars)
- [Tinybird](https://www.tinybird.co) - Real-time data platform with managed ClickHouse and MCP
- [Claude-Mem](https://claude-mem.ai) - Persistent memory compression for Claude Code (15,681 stars)
- [Repomix](https://repomix.com) - Pack codebase into AI-friendly formats (21,597 stars)
- [Superpowers](https://github.com/obra/superpowers) - Agentic skills framework and software development methodology (40,911 stars)

### Internal References

- [Workflow Diagrams](../.claude/knowledge/workflow-diagrams/) - Agentic process flow visualizations
- [Plugin Development](../plugins/) - Claude Code plugins in this repository
- [Agent Definitions](../.claude/agents/) - Custom agent configurations
