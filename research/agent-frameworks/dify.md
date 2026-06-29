---
title: "Dify"
research_date: "2026-02-23"
source_url: "https://dify.ai"
github_url: "https://github.com/langgenius/dify"
documentation_url: "https://docs.dify.ai"
version_at_research: "v1.13.0"
license: "Dify Open Source License (Apache 2.0 with additional conditions)"
last_verified: "2026-02-23"
version_at_verification: "v1.13.0"
next_review: "2026-05-23"
---

## Overview

Dify is an open-source platform for building LLM applications and agentic workflows. Its visual canvas
combines agentic AI workflows, RAG pipelines, agent capabilities, multi-model management, and LLMOps
observability—enabling teams to move from prototype to production without writing infrastructure code.
With 130K+ GitHub stars and 1,100+ contributors, it is one of the most widely adopted LLM application
development platforms available.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Building LLM applications requires deep infrastructure knowledge | Visual workflow canvas handles orchestration, routing, and state management |
| Switching between LLM providers is costly | Unified model management layer supports 100+ providers via a single interface |
| RAG pipelines are complex to implement and tune | Built-in document ingestion, chunking, embedding, and retrieval with configurable strategies |
| Agent tool integration requires custom code per tool | 50+ pre-built tools (Google Search, DALL·E, WolframAlpha, etc.) with custom tool support |
| Monitoring LLM app quality in production is opaque | LLMOps layer tracks logs, latency, token usage, and user feedback with annotation support |
| Human oversight in automated workflows is hard to embed | Human-in-the-Loop (HITL) node pauses execution for review, edit, and action-based routing |
| Deploying LLM apps as APIs requires bespoke backend work | Backend-as-a-Service: all capabilities expose REST APIs for integration into existing systems |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 130,011 | 2026-02-23 |
| GitHub Forks | 20,249 | 2026-02-23 |
| Open Issues | 748 | 2026-02-23 |
| Contributors | ~1,146 | 2026-02-23 |
| Watchers | 754 | 2026-02-23 |
| Latest Release | v1.13.0 | 2026-02-11 |
| Primary Language | TypeScript | 2026-02-23 |
| Repository Created | 2023 | 2026-02-23 |

---

## Key Features

### Visual Workflow Builder

- **Drag-and-drop canvas**: Compose multi-step LLM pipelines with conditional routing, loops, and parallel branches
- **Node types**: LLM, Code, HTTP Request, Template, Variable Aggregator, Iterator, Parameter Extractor, Document Extractor, Knowledge Retrieval
- **Human-in-the-Loop (HITL)**: Native "Human Input" node suspends execution; supports Webapp and Email delivery of review forms
- **Workflow versioning**: Save, compare, and roll back workflow versions
- **Streaming execution**: Workflows run in Celery workers with Redis Pub/Sub for real-time event streaming

### Comprehensive Model Support

- **100+ model providers**: OpenAI, Anthropic, Mistral, Llama 3, Gemini, Azure, AWS Bedrock, Hugging Face, Ollama, and OpenAI-compatible endpoints
- **Unified model management**: Switch models per node without rewriting workflow logic
- **System model configuration**: Set default inference, embedding, reranking, speech-to-text, and TTS models per workspace

### RAG Pipeline

- **Document ingestion**: PDF, DOCX, TXT, HTML, Markdown, CSV, and more via built-in extractors
- **Chunking strategies**: Fixed-size, semantic, parent-child, and hierarchical chunking
- **Embedding models**: Configurable embedding provider per knowledge base
- **Retrieval modes**: Semantic search, full-text search, and hybrid (weighted combination)
- **Reranking**: Optional reranker model pass for precision improvements
- **External knowledge bases**: Connect to external vector stores via API extension

### Agent Capabilities

- **Agent types**: ReAct (reasoning + acting) and LLM Function Calling based agents
- **Built-in tools**: 50+ tools including Google Search, DALL·E, Stable Diffusion, WolframAlpha, web scraping, code execution (sandboxed Python/JavaScript via Dify Sandbox)
- **Custom tools**: OpenAPI/Swagger schema import or manual tool definition
- **Tool permissions**: Per-workspace tool access control

### Prompt IDE

- **Prompt editor**: Jinja2-templated prompts with variable binding
- **Model comparison**: A/B test prompts across multiple models side-by-side
- **Dataset annotation**: Label production outputs for fine-tuning and evaluation datasets
- **Text-to-speech**: Add TTS output to chat applications

### LLMOps & Observability

- **Application logs**: Full message history with user metadata, token counts, latency
- **Performance dashboards**: Active users, token cost, response latency trends over time
- **Annotation workflows**: Mark production responses as golden examples or corrections
- **Tracing integrations**: LangFuse, LangSmith, and other observability platforms via plugin

### Backend-as-a-Service

- **REST APIs**: Every application type (chatbot, workflow, agent) exposes a stable REST API
- **Webhook support**: Trigger workflows from external events
- **Streaming API**: Server-sent events for real-time token streaming to client applications
- **Embedding widget**: Iframe or script embed for web pages

### Application Types

- **Chatbot**: Single-turn or multi-turn conversational interfaces
- **Text Generator**: Batch or single document generation workflows
- **Agent**: Autonomous tool-using agents with conversation history
- **Workflow**: Complex multi-step DAG pipelines with parallel execution

---

## Technical Architecture

### Stack Components

| Component | Technology |
|-----------|------------|
| Backend API | Python (Flask) |
| Frontend | Next.js (TypeScript) |
| Worker Queue | Celery + Redis |
| Primary Database | PostgreSQL |
| Vector Database | Weaviate / Qdrant / Chroma / pgvector (configurable) |
| Caching | Redis |
| Storage | Local / S3 / Azure Blob / Google Cloud Storage |
| Container | Docker + Docker Compose |
| Orchestration | Kubernetes (community Helm charts) |

### Execution Architecture (v1.13.0)

<eg>
Client (Web / API)
      |
   API Process (Flask)
      |
  +-----------+-------------+
  |                         |
Non-streaming runs   Workflow + Advanced Chat streaming
(API process)        (Celery: workflow_based_app_execution queue)
                             |
                       Redis Pub/Sub (PUBSUB_REDIS_URL)
                             |
                       SSE stream → Client
</eg>

### Data Flow (RAG Application)

<eg>
User query
   → Dify API
   → Knowledge Retrieval node (embed query → vector search → rerank)
   → Retrieved chunks injected into LLM prompt context
   → LLM node (configured provider/model)
   → Response streamed back via Redis Pub/Sub
   → LLMOps log written to PostgreSQL
</eg>

---

## Installation & Usage

### Quick Start with Docker Compose

```bash
# Clone the repository
git clone https://github.com/langgenius/dify.git
cd dify/docker

# Configure environment
cp .env.example .env

# Start all services (API, worker, web, sandbox, vector DB, Redis, PostgreSQL)
docker compose up -d

# Access the UI
open http://localhost/install
```

### Environment Configuration (key variables)

```bash
# Required: Secret key for session signing
SECRET_KEY=your-secret-key

# Vector store backend (weaviate | qdrant | milvus | pgvector | chroma | opensearch)
VECTOR_STORE=weaviate

# PubSub Redis for HITL/streaming (v1.13.0+)
PUBSUB_REDIS_URL=redis://redis:6379/0
PUBSUB_REDIS_CHANNEL_TYPE=pubsub  # or 'sharded' for high-throughput

# Storage backend
STORAGE_TYPE=local  # or s3, azure-blob, google-storage
```

### REST API Usage

```bash
# Call a workflow via REST API
curl -X POST https://api.dify.ai/v1/workflows/run \
  -H "Authorization: Bearer {api-key}" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": {"query": "Summarize this document"},
    "response_mode": "streaming",
    "user": "user-123"
  }'
```

---

## Relevance to Claude Code Development

### Applications

1. **Workflow orchestration reference**: Dify's node-based workflow DAG (conditional routing, parallel branches, loops, error handling) provides a mature reference architecture for designing Claude Code multi-agent pipelines.

2. **RAG pipeline patterns**: The chunking, embedding, retrieval, and reranking pipeline in Dify is a production-tested reference for the context-management and skill-generation-tools plugins.

3. **LLMOps instrumentation**: Dify's tracing, annotation, and feedback loop patterns can inform observability design in Claude Code skill execution frameworks.

4. **HITL integration**: The Human-in-the-Loop node design (pause/resume via Celery + Redis Pub/Sub) is a concrete pattern for building human-approval gates into Claude Code agentic workflows.

5. **Backend-as-a-Service model**: Exposing Claude Code agent capabilities as REST APIs mirrors Dify's BaaS approach—useful when integrating Claude Code into external systems.

### Patterns Worth Adopting

1. **Visual workflow canvas concepts**: Node abstraction (each skill as a node with defined inputs/outputs) maps well to Claude Code skill composition.

2. **Unified model abstraction layer**: Provider-agnostic model selection at the node level, rather than hardcoding a model in every skill.

3. **Annotation-driven improvement**: Production response labeling and dataset curation as a continuous improvement loop for skill quality.

4. **Streaming via Pub/Sub**: Redis Pub/Sub for fan-out streaming of execution events to multiple consumers (UI, logging, downstream agents).

5. **Sandboxed code execution**: Dify Sandbox (isolated Python/JavaScript execution environment) is a pattern for safe code execution in Claude Code tool steps.

### Integration Opportunities

1. **MCP Server for Dify**: Expose Dify workflows as MCP tools so Claude Code can invoke production Dify applications as skills.

2. **Dify as orchestration backend**: Use Dify to manage the RAG and model-routing layers while Claude Code handles coding-specific agent behavior.

3. **Cross-tool knowledge bases**: Share Dify knowledge bases (vector stores) with Claude Code context management plugins for unified document retrieval.

4. **Dify tools in Claude Code**: Import Dify's 50+ pre-built tool definitions as MCP server tools for Claude Code agents.

5. **LLMOps for Claude Code sessions**: Route Claude Code session traces to Dify's annotation/evaluation pipeline for quality monitoring.

### Competitive Analysis

| Aspect | Dify | Claude Code Plugins |
|--------|------|---------------------|
| Interface | Visual canvas + REST API | CLI + natural language |
| Workflow definition | Drag-and-drop DAG | Markdown skills + agent files |
| Model support | 100+ providers, unified | Configurable via MCP/tools |
| RAG | Built-in, production-grade | Via context-management plugins |
| Agents | ReAct + Function Calling | Claude Code native agents |
| Observability | LLMOps dashboards | Plugin-level (ai-observability plugins) |
| Deployment | Self-hosted / cloud | Local CLI / IDE |
| Extensibility | Plugin marketplace, custom tools | Skills, MCP servers |
| Target users | LLM app builders, business teams | Software developers |

---

## References

- [GitHub Repository](https://github.com/langgenius/dify) (accessed 2026-02-23)
- [Official Documentation](https://docs.dify.ai) (accessed 2026-02-23)
- [Release v1.13.0 Notes](https://github.com/langgenius/dify/releases/tag/1.13.0) (accessed 2026-02-23)
- [Model Providers List](https://docs.dify.ai/getting-started/readme/model-providers) (accessed 2026-02-23)
- [Docker Hub - langgenius](https://hub.docker.com/u/langgenius) (accessed 2026-02-23)
- [Dify Open Source License](https://github.com/langgenius/dify/blob/main/LICENSE) (accessed 2026-02-23)
- [Contributing Guide](https://github.com/langgenius/dify/blob/main/CONTRIBUTING.md) (accessed 2026-02-23)

**Research Method**: Information gathered from the official GitHub repository README, GitHub API (stars, forks, issues, contributors, releases), official documentation, and release notes. Statistics verified via direct GitHub API calls on 2026-02-23.

---
