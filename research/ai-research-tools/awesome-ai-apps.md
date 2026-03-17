# Awesome AI Apps — Research Collection of 70+ LLM-Powered Applications

## Overview

**Awesome AI Apps** is a comprehensive, actively maintained repository curating 70+ practical examples, tutorials, and recipes for building LLM-powered applications. Created by Arindam Majumder and maintained by a core team, the repository serves as a learning resource and reference collection for developers building with modern AI frameworks. The projects span from beginner-friendly starter agents to production-grade multi-agent systems, RAG applications, and memory-augmented agents.

**Repository URL**: <https://github.com/Arindam200/awesome-ai-apps>

**License**: MIT

**Current Stats** (as of 2026-03-17):
- **Stars**: 9,278
- **Forks**: 1,167
- **Primary Language**: Python
- **Topics**: agents, ai, hacktoberfest, llm, mcp
- **Repository Created**: 2025-02-16
- **Last Updated**: 2026-03-17

## Problem Addressed

Developers learning AI agent frameworks and LLM-powered applications face fragmented documentation across multiple frameworks (Agno, OpenAI SDK, LangChain, CrewAI, AWS Strands, etc.) with limited interconnected examples. This repository solves this by providing:

1. **Framework diversity** — Examples across 10+ different agent frameworks in a single curated location
2. **Progressive complexity** — Projects organized by difficulty level (starter → simple → advanced)
3. **Real-world use cases** — Each project demonstrates a concrete application pattern (finance tracking, RAG, multi-agent research, memory systems)
4. **Best practices documentation** — Each project includes comprehensive README with setup, usage, and technical details
5. **Production patterns** — Advanced examples showing multi-stage workflows, observability, guardrails, and deployment patterns

## Key Features

### 1. **Six-Tier Project Organization**

Projects are organized into hierarchical categories with clear progression:

- **Starter Agents** (13 projects) — Quick-start boilerplate examples for learning different frameworks. Includes Agno, OpenAI SDK, LlamaIndex, CrewAI, PydanticAI, LangChain, AWS Strands, Camel AI, DSPy, Google ADK, cagent, Sayna, and KAOS starters.
- **Simple Agents** (14 projects) — Straightforward, practical single-purpose agents. Examples include finance tracking, human-in-the-loop execution, newsletter generation, calendar scheduling, web automation, and intelligent model routing.
- **MCP Agents** (12 projects) — Projects using the Model Context Protocol for external tool integration. Includes semantic RAG, GitHub repository analysis, database interactions, hotel booking, and Docker sandbox execution via MCP.
- **Memory Agents** (12 projects) — Agents with persistent memory capabilities using frameworks like GibsonAI Memori. Examples include arXiv research assistants, blog writers, social media automation, job search agents, and brand reputation monitoring.
- **RAG Applications** (11 projects) — Retrieval-augmented generation examples with vector databases. Includes PDF chat, resume optimization, code exploration, OCR-based document processing, and enterprise RAG with quality evaluation.
- **Advanced Agents** (14 projects) — Complex multi-agent pipelines for production workflows. Examples include financial research, deep research agents with web scraping, candidate analysis, job finders, trend analysis, conference proposal generation, and temporal-based agents.

**Total: 76 documented projects** across all categories.

### 2. **Comprehensive AWS Strands Course**

An 8-lesson hands-on course (in `course/aws_strands/`) progressing from fundamentals to production patterns:

1. **01_basic_agent** — Create first agent, configure model, add simple tools
2. **02_session_management** — Persistent conversations and agent state
3. **03_structured_output** — Extract structured data with Pydantic models
4. **04_mcp_agent** — Multi-Capability Protocol tool integration
5. **05_human_in_the_loop_agent** — Pause for human input/approval before continuing
6. **06_multi_agent_pattern** — Four specialized sub-lessons:
   - 06_1_agent_as_tools — Orchestrator delegating to specialized agents
   - 06_2_swarm_agent — Dynamic agent handoffs within a group
   - 06_3_graph_agent — Explicit structured workflows via directed graphs
   - 06_4_workflow_agent — Sequential research pipelines
7. **07_observability** — OpenTelemetry and Langfuse monitoring
8. **08_guardrails** — Safety measures and content filtering

Each lesson includes complete working examples with full setup instructions.

### 3. **Framework Coverage**

The repository covers 10+ AI frameworks and SDKs:

- **Agno** — Most frequently used across projects (starter, simple, memory, advanced, RAG)
- **OpenAI Agents SDK** — Native OpenAI agent runtime with async execution
- **LlamaIndex** — Document indexing and RAG
- **CrewAI** — Multi-agent orchestration and research crews
- **PydanticAI** — Structured output and type-safe agents
- **LangChain + LangGraph** — Graph-based workflows and ReAct agents
- **AWS Strands** — Amazon's agent SDK with comprehensive course
- **Camel AI** — Performance benchmarking and model comparison
- **DSPy** — Framework for building and optimizing AI systems
- **Google ADK** — Google Agent Development Kit for trend analysis and conferences
- **Mastra AI** — Modern agent framework (weather agents)
- **Temporal** — Durable workflows for state management across distributed agents

### 4. **Technology Stack Across Projects**

- **Inference Providers**: Nebius Token Factory (extensively used), OpenAI (GPT-4, GPT-4o-mini), Qwen3 (via Nebius), Gemma, Nvidia Nemotron
- **Vector Databases**: Qdrant (semantic search), Couchbase (multi-agent)
- **Memory Systems**: GibsonAI Memori (v3 for long-term memory fabric), Memori with Exa
- **Web Scraping**: ScrapeGraph AI, Firecrawl (newsletter integration), Bright Data
- **Search APIs**: Exa (AI search), SerpApi (Google Search), RouteLLM (cost optimization)
- **Voice/STT**: Deepgram, ElevenLabs, Azure Speech, Google Cloud Speech
- **Collaboration**: Cal.com (calendar), Gmail (email), Taskade (project management)
- **Observability**: Langfuse, OpenTelemetry, Okahu
- **DevOps/Deployment**: Docker (E2B sandboxing), Temporal (workflow engine), AgentField (Kubernetes for AI agents)

### 5. **Development Practices**

**Dependency Management**:
- 62 projects use `pyproject.toml` (modern approach with version pinning)
- 24 projects use `requirements.txt`
- Repository recommends `uv` (Rust-based package manager) for faster installs

**Code Quality**:
- Consistent snake_case naming conventions for project directories
- Black or Ruff formatters encouraged
- `.env.example` files provided in every project (no committed secrets)
- Comprehensive README templates in `.github/README_TEMPLATE.md`

**Python Version Support**:
- Minimum Python 3.10+
- Python 3.11+ recommended for newer projects

## Technical Architecture

### Multi-Agent Patterns

Advanced agents implement specialized patterns for complex workflows:

```
Orchestrator Agent (delegates tasks)
├── Searcher Agent (gathers information)
├── Analyst Agent (processes findings)
└── Writer Agent (generates output)
```

**Example**: Deep Researcher Agent with Agno and ScrapeGraph AI uses this pattern to perform multi-stage research with web scraping.

### MCP Integration Pattern

Model Context Protocol agents follow a standard initialization pattern:

```
MCPServerStdio (external tool wrapper)
├── Environment variables (API keys, tokens)
├── Command execution (npx, python subprocess)
└── Tool registration (functions exposed to agent)
```

Used across GitHub MCP agents, database integrations, and Couchbase servers.

### RAG Architecture

RAG applications implement retrieval + generation:

```
User Query
├── Vector Embedding
├── Similarity Search (Qdrant, vector store)
├── Chunk Retrieval
└── LLM Generation (with context from retrieved docs)
```

Examples: PDF chat, resume optimization, code exploration with semantic RAG.

### Memory-Augmented Agents

Memory agents use persistent storage for context retention:

```
Agent Execution
├── Query (user input)
├── Memory Retrieval (GibsonAI Memori)
├── Context Assembly
├── LLM Response
└── Memory Update (store facts, preferences)
```

Used for personalization in blog writing, job search tracking, and brand reputation monitoring.

## Relevance to Claude Code Development

### 1. **Multi-Framework Comparison Reference**

The repository demonstrates how different AI frameworks (Agno, OpenAI SDK, LangChain, AWS Strands, CrewAI) solve the same problems with different abstractions. This is valuable for Claude Code plugin architects designing agent-agnostic interfaces or adapters.

**Specific Use Cases**:
- Evaluating which frameworks best fit feature requirements
- Building framework-agnostic agent abstractions
- Understanding MCP integration patterns across implementations

### 2. **Production Agent Patterns**

Advanced examples showcase production-ready patterns:
- Multi-agent orchestration with task delegation
- Observability integration (Langfuse, OpenTelemetry)
- Safety guardrails and content filtering
- Human-in-the-loop execution
- Temporal-based durable workflows for state management

**Direct Application**: These patterns inform the design of `/implement-feature` task execution, `t0-baseline-capture` verification, and `context-refinement` consistency checking in SAM workflows.

### 3. **MCP Server Design Inspiration**

The `mcp_ai_agents/` directory contains 12 projects demonstrating MCP server patterns:
- Custom MCP server implementation
- Couchbase MCP Server (database integration)
- GitHub MCP Agent (repository analysis)
- E2B Docker MCP Agent (sandboxed execution)
- Taskade MCP Agent (project management)

**Relevance**: Understanding MCP design patterns helps Claude Code extensions expose tools via the Model Context Protocol.

### 4. **Memory and Context Management**

Memory agent examples using GibsonAI Memori demonstrate:
- Long-term memory fabric for context retention
- Preference tracking across conversations
- Style consistency in multi-turn interactions
- Fact accumulation in research workflows

**Application**: Claude Code skills could adopt similar memory patterns for maintaining agent state and user preferences across sessions.

### 5. **Course-Based Learning Structure**

The AWS Strands course demonstrates a pedagogical approach:
- Progressive complexity (beginner → intermediate → advanced)
- Each lesson builds on the previous
- Complete working examples
- Three recommended learning paths

This structure is directly applicable to designing Claude Code plugin tutorials and learning tracks.

## Usage and Installation

### Quick Start

```bash
# Clone repository
git clone https://github.com/Arindam200/awesome-ai-apps.git
cd awesome-ai-apps

# Choose a project
cd starter_ai_agents/agno_starter  # Example

# Setup environment
cp .env.example .env
# Edit .env with your API keys (NEBIUS_API_KEY, OPENAI_API_KEY, etc.)

# Install dependencies (using uv recommended for speed)
uv sync
# or
pip install -r requirements.txt

# Run the agent
python main.py
# or for Streamlit apps
streamlit run app.py
```

### Project-Specific Commands

Each project directory is self-contained. Navigation to specific category required:

```bash
# Run a simple agent (finance tracking)
cd simple_ai_agents/finance_agent
python main.py

# Run a RAG application (PDF chat)
cd rag_apps/pdf_rag_analyser
streamlit run app.py

# Run an MCP agent (GitHub repository analysis)
cd mcp_ai_agents/github_mcp_agent
python main.py

# Work through AWS Strands course
cd course/aws_strands/01_basic_agent
python main.py
```

### Common API Keys Required

- `NEBIUS_API_KEY` — Nebius Token Factory (most projects)
- `OPENAI_API_KEY` — OpenAI models
- `GITHUB_PERSONAL_ACCESS_TOKEN` — GitHub MCP agents
- `SGAI_API_KEY` — ScrapeGraph AI (web scraping agents)
- `MEMORI_API_KEY` — GibsonAI Memori (memory agents)
- `EXA_API_KEY` — Exa AI search
- `SERPAPI_API_KEY` — Google Search API

## Limitations and Caveats

### 1. **Documentation Variance**

Project documentation quality varies across the 76 projects. While every project includes a README, depth and completeness vary:
- Starter agents have minimal documentation (2–3 KB)
- Advanced agents and course materials are more comprehensive (10–20 KB)
- Some newer projects may have less tested setup instructions

**Mitigation**: Course materials and advanced agent examples provide the most reliable documentation. Starter projects should be verified experimentally.

### 2. **API Key Dependencies**

Nearly all projects require external API keys (OpenAI, Nebius, GitHub, etc.). Running examples incurs API costs. Many use `NEBIUS_API_KEY` (cost-effective inference) as primary provider, but some require OpenAI or other paid services.

**Practical Impact**: Budget allocation needed for exploration; starter projects recommend Nebius for cost optimization.

### 3. **Python Version Requirements**

Minimum Python 3.10+, recommended 3.11+. Some newer projects with advanced dependencies may require 3.12. No Python version management automation provided in repository; developers must manage local Python environments.

### 4. **Dependency Management Heterogeneity**

Projects use either `requirements.txt` or `pyproject.toml` without a unified approach. The repository recommends `uv` but doesn't enforce it, leading to varying install times and potential version conflict scenarios.

**Workaround**: The repository's `.claude/CLAUDE.md` documents this and recommends `uv` for faster installs.

### 5. **Framework-Specific Knowledge Required**

Each project demonstrates a different framework (Agno, OpenAI SDK, LangChain, CrewAI, AWS Strands, etc.). No unified abstraction layer or common interface is provided. Developers learning multiple frameworks must understand framework-specific patterns individually.

**Scope Note**: This is intentional—the repository's purpose is to showcase framework diversity, not unify them.

### 6. **Production Readiness Varies**

Projects labeled "advanced" include production patterns, but they are still examples, not production-hardened systems. No error recovery, retry logic, or comprehensive logging is guaranteed across all examples.

**Verification Required**: Advanced examples should be audited before deploying to production.

### 7. **No Automatic Updates**

The repository is manually maintained. While recently updated (2026-03-17), new framework releases and API changes may not be immediately reflected in project examples. Developers should verify examples against current framework documentation.

## Confidence Summary

| Section | Confidence | Notes |
|---------|-----------|-------|
| **Identity/Metadata** | High | Repository metadata extracted via GitHub API; star count, forks, license verified 2026-03-17 |
| **Project Organization** | High | README provides complete table of contents with 76 projects categorized; manually verified directory structure |
| **Technical Architecture** | High | Code-read from sample projects; pattern extraction from starter, simple, and advanced agents confirmed |
| **Features** | High | Extracted directly from main README and course materials; framework listings verified against project pyproject.toml files |
| **Installation & Usage** | Medium | Instructions extracted from README and course materials; actual execution not performed (requires API keys) |
| **Limitations** | Medium | Inferred from documentation gaps and API dependencies; comprehensive limitation testing not performed |

## References

1. **GitHub Repository**: <https://github.com/Arindam200/awesome-ai-apps> (accessed 2026-03-17)
   - README.md — Project overview, feature list, 6-tier categorization, course information
   - CONTRIBUTING.md — Contributing guidelines, project structure standards
   - CLAUDE.md — Development patterns, framework coverage, common commands
   - LICENSE — MIT License, copyright 2025 Arindam Majumder

2. **Repository Metadata**: <https://api.github.com/repos/Arindam200/awesome-ai-apps> (accessed 2026-03-17)
   - Stars: 9,278
   - Forks: 1,167
   - License: MIT
   - Topics: agents, ai, hacktoberfest, llm, mcp
   - Created: 2025-02-16T13:57:00Z
   - Updated: 2026-03-17T17:22:55Z

3. **AWS Strands Course README**: `course/aws_strands/README.md` in repository (accessed 2026-03-17)
   - 8-lesson structure with learning paths
   - Lesson descriptions and progression

4. **Starter Project Example**: `starter_ai_agents/agno_starter/README.md` (accessed 2026-03-17)
   - Project structure and installation patterns
   - Framework example: Agno with Nebius

5. **Repository Contributing Guidelines**: <https://github.com/Arindam200/awesome-ai-apps/blob/main/CONTRIBUTING.md> (accessed 2026-03-17)
   - Project categorization standards (snake_case naming, folder structure)
   - Dependency management practices (pyproject.toml vs requirements.txt)
   - Code style expectations (Black, Ruff formatters)
   - `.env.example` practices (no committed secrets)

## Freshness Tracking

**Last Reviewed**: 2026-03-17
**Next Review**: 2026-06-17 (3 months)

**Key Fields to Monitor**:
- Star count (baseline: 9,278 as of 2026-03-17)
- Active project count (baseline: 76 documented projects)
- Primary framework adoption (Agno currently most common)
- Course completion/test status (AWS Strands course fully documented)
- Framework updates (AWS Strands, Agno, OpenAI SDK versions should be checked)
- API key dependencies (track new providers or deprecations)

**Change Log**: Initial entry — 2026-03-17

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [ai-agents-frameworks.md](../agent-frameworks/ai-agents-frameworks.md) | agent-frameworks | comparative learning benchmark for 10 agent frameworks (overlaps with Awesome AI Apps' framework coverage) |
| [copilotkit.md](../agent-frameworks/copilotkit.md) | agent-frameworks | React-first agentic frontend framework (featured framework in Awesome AI Apps starter agents) |
| [dify.md](../agent-frameworks/dify.md) | agent-frameworks | Open-source LLM application platform with visual workflow builder (similar RAG + agent capabilities) |
| [liteagents.md](../agent-frameworks/liteagents.md) | agent-frameworks | Multi-tool AI development toolkit with 11 agents (overlaps with Awesome AI Apps' agent framework diversity) |
| [micro-agent.md](../agent-frameworks/micro-agent.md) | agent-frameworks | Lightweight Python ReAct agent framework with MCP multi-server support (shared architecture pattern) |
| [openfang.md](../agent-frameworks/openfang.md) | agent-frameworks | Rust Agent OS with 40 channel adapters and SKILL.md support (implements production patterns from Awesome AI Apps) |
| [superpowers.md](../agent-frameworks/superpowers.md) | agent-frameworks | Agentic skills framework with 14 skills and subagent-driven development (developer experience mirror) |
| [everything-claude-code.md](../agent-frameworks/everything-claude-code.md) | agent-frameworks | Comprehensive agent performance system with 65+ skills, 16 agents, 40+ commands (production orchestration patterns) |
| [gstack.md](../agent-frameworks/gstack.md) | agent-frameworks | Role-specific cognition switching for Claude Code with specialized agents (production agent handoff patterns) |
| [ai-data-science-team.md](../research-agent-patterns/ai-data-science-team.md) | research-agent-patterns | LangGraph supervisor + 9 specialist agents with sandboxed execution (multi-agent orchestration like Awesome AI Apps) |
| [oh-my-opencode.md](../research-agent-patterns/oh-my-opencode.md) | research-agent-patterns | Production-scale orchestration with Sisyphus/Atlas/Prometheus architecture (advanced multi-agent patterns similar to Awesome AI Apps' advanced agents) |
| [browsermcp-mcp.md](../mcp-ecosystem/browsermcp-mcp.md) | mcp-ecosystem | Browser automation via MCP (shared MCP integration pattern with Awesome AI Apps' 12 MCP agent projects) |
| [sourcesyncai-mcp.md](../mcp-ecosystem/sourcesyncai-mcp.md) | mcp-ecosystem | 28-tool MCP bridge for knowledge bases (complementary tool integration approach to Awesome AI Apps' MCP servers) |
| [ultra-mcp.md](../mcp-ecosystem/ultra-mcp.md) | mcp-ecosystem | Single MCP interface routing to multiple providers with cost tracking (provider diversity mirrors Awesome AI Apps' inference providers) |
| [scrapling.md](../developer-tools/scrapling.md) | developer-tools | Python web scraping framework with built-in MCP server for Claude agents (implements ScrapeGraph AI pattern from Awesome AI Apps) |
| [surf-cli.md](../developer-tools/surf-cli.md) | developer-tools | AI agent Chrome control via extension (agent browser automation capability used in Awesome AI Apps) |
| [the-unwind-ai.md](./the-unwind-ai.md) | ai-research-tools | AI builder newsletter with 740+ posts and companion awesome-llm-apps repo (similar LLM application reference collection) |
| [piebald.md](../developer-tools/piebald.md) | developer-tools | Cross-platform agentic AI desktop client with parallel subagents (desktop implementation of agent patterns) |
| [accomplish.md](../coding-agents/accomplish.md) | coding-agents | Local-first AI desktop agent with MCP tools and 15 providers (implements Awesome AI Apps' multi-agent, multi-provider patterns) |
| [cline.md](../coding-agents/cline.md) | coding-agents | Open-source autonomous coding agent with human-in-the-loop approvals (HITL pattern demonstrated in Awesome AI Apps' simple agents) |
