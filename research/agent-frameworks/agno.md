# Agno

| Field         | Value                                                    |
| ------------- | -------------------------------------------------------- |
| Research Date | 2026-01-31                                               |
| Primary URL   | <https://docs.agno.com>                                  |
| GitHub        | <https://github.com/agno-agi/agno>                       |
| PyPI          | <https://pypi.org/project/agno/>                         |
| Version       | v2.4.7 (released 2026-01-28)                             |
| License       | Apache-2.0                                               |
| Discord       | <https://www.agno.com/discord>                           |
| Community     | <https://community.agno.com/>                            |

---

## Overview

Agno is a Python framework for building multi-agent systems that learn and improve with every interaction. Unlike stateless agents that forget after each session, Agno agents persist user profiles across sessions, accumulate knowledge across conversations, and transfer learned insights across users. The framework provides model-agnostic support for 40+ providers, built-in toolkits, vector store integrations, and a production runtime called AgentOS.

---

## Problem Addressed

| Problem                                           | Solution                                                                |
| ------------------------------------------------- | ----------------------------------------------------------------------- |
| Agents are stateless and forget between sessions  | Learning system persists user profiles and memories across sessions     |
| Knowledge doesn't transfer between users          | Learned knowledge transfers across users, improving system over time    |
| Building multi-agent systems is complex           | Teams and workflows abstractions coordinate multiple agents             |
| RAG integration requires custom implementation    | Built-in agentic RAG with 20+ vector stores, hybrid search, reranking   |
| Production deployment is separate concern         | AgentOS runtime + control plane UI for monitoring and management        |
| Tool integration varies across frameworks         | 100+ built-in toolkits, first-class MCP and A2A protocol support        |
| Model lock-in limits flexibility                  | Model-agnostic: OpenAI, Anthropic, Google, local models, 40+ providers  |

---

## Key Statistics

| Metric            | Value                     | Date Gathered |
| ----------------- | ------------------------- | ------------- |
| GitHub Stars      | 37,379                    | 2026-01-31    |
| GitHub Forks      | 4,954                     | 2026-01-31    |
| Open Issues       | 489                       | 2026-01-31    |
| Contributors      | ~385                      | 2026-01-31    |
| PyPI Monthly DL   | 1,158,777                 | 2026-01-31    |
| PyPI Weekly DL    | 294,556                   | 2026-01-31    |
| Primary Language  | Python                    | 2026-01-31    |
| Repository Age    | Since May 2022            | 2026-01-31    |

---

## Key Features

### Learning System

- **User profiles**: Persist across sessions, accumulate user-specific context
- **User memories**: Store insights and facts about users across conversations
- **Learned knowledge**: Transfers across users, improving system globally
- **Learning modes**: Always-on or agentic (agent decides when to learn)
- **Decision logging**: Track and analyze agent decisions for improvement

### Core Framework

- **Model-agnostic**: 40+ providers (OpenAI, Anthropic, Google, Llama, Mistral, DeepSeek, Groq, Ollama, vLLM)
- **Type-safe I/O**: `input_schema` and `output_schema` for structured data
- **Async-first**: Built for long-running tasks and concurrent execution
- **Natively multimodal**: Text, images, audio, video, files
- **Guardrails**: Validation and security constraints for agent behavior

### Multi-Agent Orchestration

- **Teams**: Coordinate multiple agents with shared memory and distributed RAG
- **Workflows**: Chain agents, teams, and functions into automated pipelines
- **Human-in-the-loop**: Confirmations, approvals, overrides at decision points
- **A2A protocol**: Agent-to-agent communication standard support
- **MCP support**: First-class Model Context Protocol integration

### Knowledge and RAG

- **Agentic RAG**: Intelligent retrieval with agent-guided search
- **20+ vector stores**: Comprehensive vector database support
- **Hybrid search**: Combine dense and sparse retrieval
- **Reranking**: Improve retrieval quality with reranking models
- **Multiple sources**: URLs, S3, GCS, YouTube, PDFs, and more

### Reasoning Capabilities

- **Reasoning models**: Support for o1, o3, and other reasoning-trained models
- **Reasoning tools**: Give agents tools that enable reasoning (think, analyze)
- **Reasoning harness**: `reasoning=True` for chain-of-thought with tool use

### Storage

- **Session history**: Persistent conversation storage
- **State management**: Agent state persistence across sessions
- **Supported backends**: Postgres, SQLite, DynamoDB, Firestore, MongoDB, Redis, SingleStore, SurrealDB

### Production Infrastructure

- **AgentOS runtime**: Ready-to-use FastAPI-based deployment
- **Control plane UI**: Monitor and manage agents via <https://os.agno.com>
- **Evals**: Accuracy (LLM-as-judge), performance (latency, memory), reliability metrics
- **100+ toolkits**: Web search, SQL, email, APIs, Discord, Slack, Docker, custom tools

---

## Technical Architecture

### Stack Components

| Component       | Technology                                          |
| --------------- | --------------------------------------------------- |
| Core Framework  | Python (async-first design)                         |
| Runtime         | AgentOS (FastAPI-based)                             |
| Storage         | Pluggable (Postgres, SQLite, DynamoDB, etc.)        |
| Vector Stores   | 20+ integrations (Pinecone, Weaviate, Chroma, etc.) |
| Model Providers | 40+ (OpenAI, Anthropic, Google, local, etc.)        |
| Control Plane   | AgentOS UI (os.agno.com)                            |

### Agent Abstraction Layers

```text
Workflows (complex orchestration)
    |
Teams (multi-agent coordination)
    |
Agents (single agent with tools, knowledge, learning)
    |
Models (40+ provider implementations)
```

### Data Flow

1. User input received by agent
2. Agent retrieves relevant knowledge (RAG)
3. Agent reasons with model and available tools
4. Learning system captures insights (if enabled)
5. Response generated with structured output
6. Session state persisted to storage
7. Metrics logged for evals

---

## Installation and Usage

### Installation

```bash
# Using pip
pip install agno

# Using uv (recommended)
uv pip install agno
```

### Basic Agent (with Learning)

```python
from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.openai import OpenAIResponses

agent = Agent(
    model=OpenAIResponses(id="gpt-4o"),
    db=SqliteDb(db_file="tmp/agents.db"),
    learning=True,  # Enable learning across sessions
)

# Agent now remembers users and improves over time
response = agent.run("What can you help me with?")
```

### Agent with Tools

```python
from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.tools.web_search import WebSearchTools

agent = Agent(
    model=Claude(id="claude-sonnet-4-20250514"),
    tools=[WebSearchTools()],
    instructions="You are a helpful research assistant.",
)
```

### Multi-Agent Team

```python
from agno.agent import Agent
from agno.team import Team

researcher = Agent(name="researcher", role="Research topics")
writer = Agent(name="writer", role="Write content")

team = Team(
    agents=[researcher, writer],
    workflow="sequential",  # or "parallel", "routing"
)
```

### Agent with Knowledge (RAG)

```python
from agno.agent import Agent
from agno.knowledge.pdf import PDFKnowledge
from agno.vectordb.pgvector import PgVector

knowledge = PDFKnowledge(
    path="./documents/",
    vector_db=PgVector(table_name="documents"),
)

agent = Agent(
    knowledge=knowledge,
    search_knowledge=True,
)
```

---

## Cookbook Examples

The [cookbook](https://github.com/agno-agi/agno/tree/main/cookbook) provides hundreds of examples:

| Directory           | Content                                           |
| ------------------- | ------------------------------------------------- |
| `00_quickstart/`    | Fundamentals, building on previous examples       |
| `01_showcase/`      | Advanced real-world use cases                     |
| `02_agents/`        | Tools, RAG, structured outputs, multimodal        |
| `03_teams/`         | Multi-agent coordination, async flows             |
| `04_workflows/`     | Complex process orchestration                     |
| `05_agent_os/`      | Deployment to APIs, Slack, WhatsApp               |
| `06_storage/`       | Postgres, SQLite, DynamoDB, MongoDB               |
| `07_knowledge/`     | Chunking, embedders, vector databases             |
| `08_learning/`      | Decision logging, preference tracking             |
| `09_evals/`         | Accuracy, performance, reliability testing        |
| `10_reasoning/`     | Chain-of-thought, reasoning tools                 |

---

## Relevance to Claude Code Development

### Direct Applications

1. **Multi-Agent Orchestration Patterns**: Teams and workflows abstractions provide reference architecture for coordinating Claude Code sub-agents.

2. **Learning System Design**: User profile persistence and knowledge transfer patterns could inform session-aware skill development.

3. **MCP Integration Patterns**: First-class MCP support demonstrates integration approaches for Model Context Protocol tools.

4. **Tool Architecture**: 100+ built-in toolkits show patterns for tool organization and discoverability.

5. **RAG Implementation**: Agentic RAG with hybrid search provides reference for knowledge-augmented agent design.

### Patterns Worth Adopting

1. **Learning Modes**: "Always" vs "agentic" learning modes allow agents to decide when knowledge capture is valuable.

2. **Type-Safe I/O**: `input_schema` and `output_schema` ensure structured data contracts between agents.

3. **Reasoning Harness**: `reasoning=True` flag for enabling chain-of-thought is a clean abstraction.

4. **Human-in-the-Loop**: Explicit confirmation/approval points in workflows prevent autonomous runaway.

5. **Eval Categories**: Separating accuracy, performance, and reliability metrics provides clear measurement framework.

### Integration Opportunities

1. **MCP Server**: Agno agents could be exposed as MCP tools for Claude Code workflows.

2. **A2A Protocol**: Agent-to-agent communication standard could enable Agno-Claude Code interop.

3. **Tool Reuse**: 100+ toolkits could inspire or directly inform Claude Code tool implementations.

4. **Knowledge Pipeline**: Document loading from URLs, S3, GCS patterns applicable to skill reference ingestion.

5. **Eval Framework**: Agno's eval patterns could inform Claude Code skill testing approaches.

### Comparison with Claude Code

| Aspect              | Agno                           | Claude Code                    |
| ------------------- | ------------------------------ | ------------------------------ |
| Primary Use         | Multi-agent systems            | Developer workflow automation  |
| Learning            | Built-in persistence           | Session-based (skills persist) |
| Orchestration       | Teams, workflows, A2A          | Agent delegation, Task tool    |
| Tool Integration    | 100+ toolkits, MCP, A2A        | MCP, custom tools              |
| Model Support       | 40+ providers                  | Claude models (Anthropic)      |
| Runtime             | AgentOS (FastAPI)              | CLI + IDE integration          |
| Knowledge           | Agentic RAG, vector stores     | Skills, references             |

---

## References

| Source                    | URL                                                      | Accessed   |
| ------------------------- | -------------------------------------------------------- | ---------- |
| Official Documentation    | <https://docs.agno.com/introduction>                     | 2026-01-31 |
| GitHub Repository         | <https://github.com/agno-agi/agno>                       | 2026-01-31 |
| GitHub README             | <https://github.com/agno-agi/agno/blob/main/README.md>   | 2026-01-31 |
| Cookbook                  | <https://github.com/agno-agi/agno/tree/main/cookbook>    | 2026-01-31 |
| PyPI Package              | <https://pypi.org/project/agno/>                         | 2026-01-31 |
| PyPI Stats                | <https://pypistats.org/packages/agno>                    | 2026-01-31 |
| AgentOS Control Plane     | <https://os.agno.com>                                    | 2026-01-31 |
| Community Forum           | <https://community.agno.com/>                            | 2026-01-31 |
| LLM Documentation         | <https://docs.agno.com/llms-full.txt>                    | 2026-01-31 |

**Research Method**: Information gathered from official GitHub repository README, GitHub API (stars, forks, issues, releases), PyPI statistics API, and cookbook README. Statistics verified via direct API calls.

---

## Freshness Tracking

| Field              | Value                               |
| ------------------ | ----------------------------------- |
| Version Documented | v2.4.7                              |
| Release Date       | 2026-01-28                          |
| GitHub Stars       | 37,379 (as of 2026-01-31)           |
| Monthly Downloads  | 1,158,777 (as of 2026-01-31)        |
| Next Review Date   | 2026-05-01                          |

**Review Triggers**:

- Major version release (v3.x)
- Significant new feature (new learning modes, orchestration patterns)
- GitHub stars milestone (40K, 50K)
- PyPI downloads milestone (2M monthly)
- New production runtime capabilities
- Breaking changes to Teams/Workflows API
- New model provider integrations of note
