---
name: Google Agent Development Kit (ADK)
description: An open-source, code-first Python framework from Google for building, evaluating, and deploying sophisticated AI agents with multi-agent orchestration, MCP integration, and Vertex AI deployment support.
license: Apache-2.0
metadata:
  topic: google-adk
  category: agent-frameworks
  source_url: https://google.github.io/adk-docs/
  github: google/adk-python
  version: "v1.25.1"
  verified: "2026-02-26"
  next_review: "2026-05-26"
---

## Overview

Google Agent Development Kit (ADK) is an open-source, code-first Python framework that applies software development principles to AI agent creation. It is designed to simplify building, deploying, and orchestrating agent workflows from simple tasks to complex multi-agent systems. While optimized for Gemini models, ADK is model-agnostic and deployment-agnostic, supporting MCP tools, OpenAPI specs, and integration with other frameworks such as LangChain and CrewAI. A bi-weekly release cadence delivers stable versions to PyPI as `google-adk`.

SOURCE: [GitHub README](https://github.com/google/adk-python/blob/main/README.md) (accessed 2026-02-26), [Official Docs](https://google.github.io/adk-docs/) (accessed 2026-02-26)

---

## Problem Addressed

| Problem                                                        | Solution                                                                          |
| -------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| Agent framework lock-in to specific models or clouds           | Model-agnostic design; works with Gemini, OpenAI-compatible APIs, local models    |
| Multi-agent coordination is ad-hoc and fragile                 | First-class sub_agents hierarchy with LLM-driven and deterministic routing        |
| No standard evaluation pipeline for agents                     | Built-in `adk eval` CLI with evalset JSON format and conformance test reports     |
| Tool integration requires custom glue code per tool type       | Unified toolset abstraction for functions, OpenAPI specs, and MCP servers         |
| Deployment of agents requires manual containerization          | `adk deploy` for Cloud Run and Vertex AI Agent Engine with one-step packaging     |
| Development feedback loop requires building custom UIs         | Built-in dev web UI for testing, debugging, and showcasing agents locally         |
| Context window overflow in long-running sessions               | Post-invocation token-threshold compaction with configurable event retention      |
| Human-in-the-loop requires custom interrupt logic              | Built-in tool confirmation flow (HITL) with explicit confirmation before execution |

SOURCE: [GitHub README](https://github.com/google/adk-python/blob/main/README.md) (accessed 2026-02-26), [ADK Docs - Agents](https://google.github.io/adk-docs/agents/) (accessed 2026-02-26)

---

## Key Statistics

| Metric            | Value                     | Date Gathered |
| ----------------- | ------------------------- | ------------- |
| GitHub Stars      | 17,980                    | 2026-02-26    |
| GitHub Forks      | 2,975                     | 2026-02-26    |
| Open Issues       | 567                       | 2026-02-26    |
| Contributors      | 238                       | 2026-02-26    |
| PyPI Package      | google-adk                | 2026-02-26    |
| Latest Version    | v1.25.1                   | 2026-02-26    |
| Latest Release    | 2026-02-18                | 2026-02-26    |
| Primary Language  | Python                    | 2026-02-26    |
| Repository Age    | Since April 2025          | 2026-02-26    |
| Python Versions   | 3.10, 3.11, 3.12, 3.13   | 2026-02-26    |

SOURCE: [GitHub API - google/adk-python](https://api.github.com/repos/google/adk-python) (accessed 2026-02-26), [PyPI - google-adk](https://pypi.org/project/google-adk/) (accessed 2026-02-26)

---

## Key Features

### Agent Types

ADK provides three agent categories built on the `BaseAgent` foundation:

- **LlmAgent**: Uses LLMs as the core reasoning engine for dynamic, non-deterministic decision-making. Supports tool use, sub-agent delegation, and natural language instruction following.
- **Workflow Agents**: Deterministic flow control without LLM-driven routing:
  - `SequentialAgent`: Executes sub-agents in order
  - `ParallelAgent`: Runs sub-agents concurrently
  - `LoopAgent`: Repeats agent execution based on termination conditions
- **Custom Agents**: Extend `BaseAgent` directly for unique operational logic, control flows, or specialized integrations not covered by standard types.

SOURCE: [ADK Docs - Agents](https://google.github.io/adk-docs/agents/) (accessed 2026-02-26)

### Tool Ecosystem

- **Function Tools**: Python functions decorated or passed directly as tools with automatic schema extraction from type hints
- **MCP Toolset**: Native `McpToolset` class for connecting to any MCP server; `mcp>=1.23.0` included as a core dependency
- **OpenAPI Toolset**: Automatic tool generation from OpenAPI 3.x specifications with async execution support
- **Google Built-ins**: `google_search` (Gemini grounding), code execution via Gemini, Vertex AI Search
- **Agent as Tool**: Any agent can be wrapped and invoked as a tool by a parent agent
- **SkillToolset**: ADK-specific toolset type for packaging skill collections (added v1.25.0)
- **Tool Confirmation (HITL)**: Guard tool execution with explicit user confirmation before invocation; configurable per-tool

SOURCE: [GitHub README](https://github.com/google/adk-python/blob/main/README.md) (accessed 2026-02-26), [pyproject.toml](https://github.com/google/adk-python/blob/main/pyproject.toml) (accessed 2026-02-26)

### Multi-Agent Orchestration

- **Sub-agent hierarchy**: Parent `LlmAgent` delegates to `sub_agents` list; LLM decides routing at runtime
- **Agent2Agent (A2A) protocol**: Native integration with [google-a2a/A2A](https://github.com/google-a2a/A2A/) for remote agent-to-agent communication via optional `a2a` extra (`a2a-sdk>=0.3.4`)
- **Coordinator pattern**: Specialist agents (greeter, task_executor, etc.) composed under a coordinator agent
- **MCP resource access**: `McpToolset` exposes MCP resources to agents alongside tools

### Evaluation Framework

- **`adk eval` CLI**: Evaluate agent responses against `.evalset.json` test case files
- **Conformance tests**: `adk conformance test` generates structured reports on spec adherence
- **Custom metrics**: Define metric functions with threshold parameters for domain-specific scoring
- **Vertex AI evaluation**: Optionally offload evaluation to Vertex AI Client with API key authentication

SOURCE: [CHANGELOG.md](https://github.com/google/adk-python/blob/main/CHANGELOG.md) (accessed 2026-02-26)

### Deployment

- **Local dev**: `adk web` launches the built-in development UI on localhost
- **`adk api_server`**: FastAPI-based REST server with `/run`, `/health`, `/version` endpoints and `--auto_create_session` flag
- **Cloud Run**: `adk deploy cloud_run` containerizes and deploys the agent
- **Vertex AI Agent Engine**: `adk deploy agent_engine` for managed scaling; optional `google-cloud-aiplatform[agent_engines]>=1.132.0`
- **Custom containerization**: Docker/Kubernetes deployment documentation provided

### Session and Memory

- **Session service**: Pluggable backends including SQLite (`aiosqlite`), PostgreSQL (via SQLAlchemy), Spanner, and Vertex AI Session Service
- **Session rewind**: Roll back a session to before a previous invocation (`rewind` feature, v1.25.x)
- **Memory banks**: `VertexAiMemoryBankService` for persistent memory using async Vertex AI client
- **Context compaction**: Post-invocation token-threshold compaction with event retention policy (v1.25.0)

SOURCE: [pyproject.toml](https://github.com/google/adk-python/blob/main/pyproject.toml) (accessed 2026-02-26), [CHANGELOG.md](https://github.com/google/adk-python/blob/main/CHANGELOG.md) (accessed 2026-02-26)

### Observability

- **OpenTelemetry**: Full OTel integration via `opentelemetry-sdk>=1.36.0`; exporters for GCP Trace, GCP Monitoring, GCP Logging, and OTLP HTTP
- **Third-party integrations**: AgentOps, Arize AX, Phoenix, Monocle, MLflow, W&B Weave available via community integrations catalog

SOURCE: [pyproject.toml](https://github.com/google/adk-python/blob/main/pyproject.toml) (accessed 2026-02-26), [ADK Integrations](https://google.github.io/adk-docs/integrations/) (accessed 2026-02-26)

---

## Technical Architecture

### Stack Components

| Component          | Technology                                                                  |
| ------------------ | --------------------------------------------------------------------------- |
| Core Framework     | Python 3.10+ (async-first, asyncio)                                        |
| HTTP Server        | FastAPI + Uvicorn + Starlette                                               |
| Data Validation    | Pydantic v2                                                                 |
| Session Storage    | SQLite (aiosqlite), PostgreSQL (SQLAlchemy), Cloud Spanner                 |
| Artifact Storage   | Google Cloud Storage                                                        |
| LLM SDK            | google-genai >= 1.56.0 (primary); OpenAI-compatible via base_url override  |
| MCP Integration    | mcp >= 1.23.0                                                               |
| Observability      | OpenTelemetry SDK + GCP exporters                                           |
| Auth               | google-auth + authlib (for REST API tools)                                  |
| CLI                | click >= 8.1.8                                                              |
| Code Execution     | AgentEngineSandboxCodeExecutor (Vertex AI Code Execution Sandbox API)       |

### Agent Abstraction Layers

<eg>
Runner (invocation lifecycle management)
    |
LlmAgent / WorkflowAgent / CustomAgent (agent logic)
    |
Toolsets (FunctionTool, McpToolset, OpenAPIToolset, SkillToolset)
    |
LLM (google-genai SDK -> Gemini / compatible APIs)
    |
Services (SessionService, MemoryService, ArtifactService)
</eg>

### Request Flow

1. `Runner.run_async()` receives user message and session ID
2. Session loaded from `SessionService` backend
3. Agent's `_run_async_impl` dispatches to LLM or workflow logic
4. LLM generates tool calls; framework invokes toolsets
5. Tool confirmation gate checked if configured (HITL)
6. Tool responses returned to LLM for next step
7. Context compaction applied if token threshold exceeded
8. Final response streamed or returned; events persisted to session
9. OTel traces and metrics exported to configured backend

### Multi-Agent Communication

<eg>
Coordinator (LlmAgent)
    |-- sub_agents: [SpecialistA, SpecialistB]
    |   LLM decides routing at runtime
    |
Remote agent (via A2A protocol or agent-as-tool pattern)
    |   a2a-sdk for cross-network agent calls
    |
MCP servers (via McpToolset + mcp protocol)
</eg>

SOURCE: [pyproject.toml](https://github.com/google/adk-python/blob/main/pyproject.toml) (accessed 2026-02-26), [ADK Docs](https://google.github.io/adk-docs/) (accessed 2026-02-26)

---

## Installation and Usage

### Installation

```bash
# Stable release from PyPI
pip install google-adk

# With A2A protocol support
pip install google-adk[a2a]

# Development version from main branch
pip install git+https://github.com/google/adk-python.git@main
```

### Single Agent

```python
from google.adk.agents import Agent
from google.adk.tools import google_search

root_agent = Agent(
    name="search_assistant",
    model="gemini-2.5-flash",
    instruction="You are a helpful assistant. Answer user questions using Google Search when needed.",
    description="An assistant that can search the web.",
    tools=[google_search],
)
```

### Multi-Agent System

```python
from google.adk.agents import LlmAgent

greeter = LlmAgent(name="greeter", model="gemini-2.5-flash", instruction="Greet users warmly.")
task_executor = LlmAgent(name="task_executor", model="gemini-2.5-flash", instruction="Execute user tasks.")

coordinator = LlmAgent(
    name="Coordinator",
    model="gemini-2.5-flash",
    description="I coordinate greetings and tasks.",
    sub_agents=[greeter, task_executor],
)
```

### MCP Tool Integration

```python
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset

agent = LlmAgent(
    name="mcp_agent",
    model="gemini-2.5-flash",
    tools=[McpToolset(connection_params={"command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem"]})],
)
```

### Custom Function Tool

```python
from google.adk.agents import LlmAgent


def get_weather(city: str) -> dict:
    """Get current weather for a city."""
    return {"city": city, "temperature": 22, "unit": "celsius"}


agent = LlmAgent(name="weather_agent", model="gemini-2.5-flash", tools=[get_weather])
```

### Evaluation

```bash
# Run agent evaluation against test cases
adk eval \
    samples_for_testing/hello_world \
    samples_for_testing/hello_world/hello_world_eval_set_001.evalset.json

# Start local dev UI
adk web

# Start API server
adk api_server --auto_create_session
```

SOURCE: [GitHub README](https://github.com/google/adk-python/blob/main/README.md) (accessed 2026-02-26)

---

## Relevance to Claude Code Development

### Direct Applications

1. **MCP Protocol Patterns**: ADK's `McpToolset` class demonstrates production-grade patterns for connecting to MCP servers, managing session lifecycle, and handling MCP resource loading -- directly applicable to Claude Code MCP integrations.

2. **Multi-Agent Orchestration Reference**: The `sub_agents` hierarchy with LLM-driven routing mirrors Claude Code's Agent tool delegation model. ADK's coordinator/specialist decomposition patterns are directly reusable.

3. **Tool Confirmation (HITL)**: ADK's per-tool confirmation flow provides a concrete reference implementation for guarding destructive operations in Claude Code workflows.

4. **Evaluation Framework**: The `adk eval` CLI with `.evalset.json` format provides a blueprint for skill evaluation workflows in this repository.

5. **Session Rewind**: The ability to roll back to a prior invocation state has direct applicability to Claude Code agent recovery patterns after failed sub-agent runs.

### Patterns Worth Adopting

1. **Workflow Agent Types**: Sequential/Parallel/Loop agent variants as explicit primitives rather than LLM-decided control flow -- reduces non-determinism in orchestration.

2. **OpenAPI Toolset**: Automatic tool generation from OpenAPI specs enables integrating external REST APIs without writing adapter code.

3. **Token Compaction**: Post-invocation compaction with event retention policy prevents context overflow in long-running agent sessions.

4. **SkillToolset Pattern**: Packaging related tools into named toolsets matches the skills-as-modules philosophy of this repository.

### Integration Opportunities

1. **A2A Protocol**: ADK's `a2a-sdk` integration enables Claude Code agents to communicate with ADK-based agents via the Agent2Agent standard.

2. **MCP Server Exposure**: ADK agents can be exposed as MCP tools consumable by Claude Code via the MCP protocol.

3. **Vertex AI Deployment**: ADK's Agent Engine deployment path is relevant for production deployments of Claude Code-orchestrated agent pipelines on GCP.

4. **Evaluation Methodology**: ADK's conformance test report format and evalset JSON schema could inform skill validation tooling in this repository.

### Comparison with Claude Code Skills Architecture

| Aspect               | Google ADK                              | Claude Code Skills                      |
| -------------------- | --------------------------------------- | --------------------------------------- |
| Primary Use          | General-purpose agent development       | Developer workflow automation via Claude|
| Orchestration        | sub_agents hierarchy, A2A protocol      | Agent tool delegation, agent threads     |
| Tool Integration     | Functions, MCP, OpenAPI, built-ins      | MCP servers, Bash, native tools         |
| Evaluation           | adk eval CLI + evalset JSON             | Pre-commit hooks, validation scripts    |
| Session Storage      | SQLite, PostgreSQL, Spanner             | Session-scoped (skills provide memory)  |
| Model Support        | Gemini-optimized, model-agnostic        | Claude models (Anthropic)               |
| Deployment           | Cloud Run, Vertex AI Agent Engine       | CLI + IDE integration                   |
| Observability        | OpenTelemetry + GCP exporters           | Tool call history, session logs         |

---

## References

| Source                         | URL                                                                              | Accessed   |
| ------------------------------ | -------------------------------------------------------------------------------- | ---------- |
| GitHub Repository              | <https://github.com/google/adk-python>                                           | 2026-02-26 |
| GitHub README                  | <https://github.com/google/adk-python/blob/main/README.md>                       | 2026-02-26 |
| Official Documentation         | <https://google.github.io/adk-docs/>                                             | 2026-02-26 |
| Agents Documentation           | <https://google.github.io/adk-docs/agents/>                                      | 2026-02-26 |
| Integrations Catalog           | <https://google.github.io/adk-docs/integrations/>                                | 2026-02-26 |
| PyPI Package                   | <https://pypi.org/project/google-adk/>                                           | 2026-02-26 |
| pyproject.toml                 | <https://github.com/google/adk-python/blob/main/pyproject.toml>                  | 2026-02-26 |
| CHANGELOG.md                   | <https://github.com/google/adk-python/blob/main/CHANGELOG.md>                    | 2026-02-26 |
| Samples Repository             | <https://github.com/google/adk-samples>                                          | 2026-02-26 |
| Community Repository           | <https://github.com/google/adk-python-community>                                 | 2026-02-26 |
| A2A Protocol                   | <https://github.com/google-a2a/A2A/>                                             | 2026-02-26 |
| GitHub API (metadata)          | <https://api.github.com/repos/google/adk-python>                                 | 2026-02-26 |
| GitHub API (release)           | <https://api.github.com/repos/google/adk-python/releases/latest>                 | 2026-02-26 |

**Research Method**: Data gathered from GitHub API (stars, forks, issues, contributors, latest release), repository README and pyproject.toml via GitHub contents API, official documentation site, and PyPI package page. Contributor count verified via paginated GitHub contributors API (238 total across 3 pages).
