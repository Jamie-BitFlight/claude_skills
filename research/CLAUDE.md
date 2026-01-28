# Research Directory - AI-Facing Instructions

This directory contains curated research on tools, repositories, and patterns relevant to agentic AI development with Claude Code.

---

## Purpose

Provide reference material for developing Claude Code skills, agents, plugins, and workflows by documenting novel approaches from the community.

---

## Directory Structure

```text
research/
├── agent-frameworks/        # Agent SDKs and orchestration frameworks
├── agent-infrastructure/    # Infrastructure for agentic applications
├── code-auditing/           # Code security and quality auditing tools
├── coding-agents/           # Autonomous AI coding agent platforms
├── developer-tools/         # Developer productivity and workflow tools
├── mcp-ecosystem/           # MCP servers and integrations
├── research-agent-patterns/ # Multi-agent architectures and orchestration
├── skill-generation-tools/  # Tools that create AI skills/prompts
└── task-management/         # AI-powered task management for development
```

---

## When to Consult This Directory

The model MUST consult research documents when:

1. **Building new skills/agents** - Check for prior art and patterns in relevant category
2. **Designing orchestration** - Review `research-agent-patterns/` for delegation patterns
3. **Adding MCP integration** - Consult `mcp-ecosystem/` for existing tools and patterns
4. **Evaluating external tools** - Check if research already exists before web searching

---

## Research Entry Format

Each research document follows a standardized structure:

| Section                  | Purpose                           |
| ------------------------ | --------------------------------- |
| Overview                 | Brief description of tool/pattern |
| Problem Addressed        | What problem does this solve      |
| Key Features             | Detailed feature breakdown        |
| Technical Architecture   | How it works internally           |
| Relevance to Claude Code | How this applies to our work      |
| References               | Cited sources with access dates   |
| Freshness Tracking       | Version and review dates          |

---

## Freshness Policy

| Document Age | Status                        |
| ------------ | ----------------------------- |
| < 3 months   | Current                       |
| 3-6 months   | Review recommended            |
| 6-12 months  | Review required               |
| > 12 months  | Stale - requires verification |

The model MUST check `Last Verified` dates before citing research as current.

---

## Adding New Research

When adding research to this directory, the model MUST:

1. Create file in appropriate subdirectory (create new subdirectory if category doesn't exist)
2. Follow the entry format documented in [README.md](./README.md)
3. Include freshness tracking with specific dates
4. Cite all sources with access dates
5. Update README.md with new entry in appropriate table

---

## Citation Requirements

When referencing research documents elsewhere in the repository:

**Correct**: `See [OpenHands research](./research/coding-agents/openhands.md) for autonomous coding patterns`

**Incorrect**: `See research/coding-agents/openhands.md`

All references MUST use markdown link syntax with relative paths starting with `./`.

---

## Key Research Categories

### Research Agent Patterns

**Location**: [./research-agent-patterns/](./research-agent-patterns/)

Key topics: Stateless agent coordination, file-based context sharing, iterative research loops, orchestrator routing patterns, sequential chaining vs parallel delegation.

### MCP Ecosystem

**Location**: [./mcp-ecosystem/](./mcp-ecosystem/)

Key topics: Code intelligence, security scanning, knowledge graphs, token optimization, documentation grounding, hybrid search patterns.

### Agent Frameworks

**Location**: [./agent-frameworks/](./agent-frameworks/)

Key topics: Framework benchmarks (Agno, LangGraph, LlamaIndex, OpenAI, Pydantic-AI, CrewAI), memory vs stateless performance, RAG integration metrics.

---

## Related Resources

- [Workflow Diagrams](../.claude/knowledge/workflow-diagrams/) - Agentic process flow visualizations
- [Plugin Development](../plugins/) - Claude Code plugins in this repository
- [Agent Definitions](../.claude/agents/) - Custom agent configurations
- [Methodology Development](../methodology_development/) - SAM framework documentation
