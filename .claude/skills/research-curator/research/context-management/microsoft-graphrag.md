# Microsoft GraphRAG

| Field         | Value                                                                                                       |
| ------------- | ----------------------------------------------------------------------------------------------------------- |
| Research Date | 2026-01-31                                                                                                  |
| Primary URL   | <https://microsoft.github.io/graphrag/>                                                                     |
| GitHub        | <https://github.com/microsoft/graphrag>                                                                     |
| PyPI          | <https://pypi.org/project/graphrag/>                                                                        |
| arXiv Paper   | <https://arxiv.org/pdf/2404.16130>                                                                          |
| Version       | v3.0.1 (released 2026-01-28)                                                                                |
| License       | MIT                                                                                                         |
| Blog Post     | <https://www.microsoft.com/en-us/research/blog/graphrag-unlocking-llm-discovery-on-narrative-private-data/> |

---

## Overview

GraphRAG is a modular graph-based Retrieval-Augmented Generation (RAG) system developed by Microsoft Research. It extracts meaningful, structured data from unstructured text using LLMs to create a knowledge graph, then uses these connections to answer questions that span many documents or require thematic understanding. Unlike traditional vector-based RAG, GraphRAG excels at answering abstract questions like "What are the top themes in this dataset?" by leveraging community detection and hierarchical summarization.

---

## Problem Addressed

| Problem                                                 | Solution                                                                      |
| ------------------------------------------------------- | ----------------------------------------------------------------------------- |
| Vector/keyword search fails on cross-document questions | Knowledge graph connects information across large volumes of documents        |
| Thematic questions unanswerable with traditional RAG    | Community detection and hierarchical summarization enable abstract reasoning  |
| RAG limited to local context around retrieved chunks    | Global search via map-reduce over community reports provides dataset overview |
| Noisy data with conflicting information                 | Graph structure surfaces relationships and identifies authoritative entities  |
| Single retrieval strategy limits flexibility            | Multiple search modes: Local, Global, DRIFT, Basic for different query types  |
| LLM costs high for re-indexing on errors                | Built-in LLM caching prevents redundant API calls during indexing             |
| Lock-in to specific storage or model providers          | Factory pattern allows custom implementations for all subsystems              |

---

## Key Statistics

| Metric           | Value            | Date Gathered |
| ---------------- | ---------------- | ------------- |
| GitHub Stars     | 30,637           | 2026-01-31    |
| GitHub Forks     | 3,229            | 2026-01-31    |
| Open Issues      | 95               | 2026-01-31    |
| PyPI Monthly DL  | 60,312           | 2026-01-31    |
| PyPI Weekly DL   | 19,803           | 2026-01-31    |
| PyPI Daily DL    | 4,051            | 2026-01-31    |
| Primary Language | Python           | 2026-01-31    |
| Repository Age   | Since March 2024 | 2026-01-31    |
| Python Required  | >=3.11, <3.14    | 2026-01-31    |

---

## Key Features

### Indexing Pipeline

- **Entity extraction**: LLM-powered extraction of entities, relationships, and claims from raw text
- **Community detection**: Graph-based clustering to identify related entity communities
- **Hierarchical summarization**: Community reports generated at multiple levels of granularity
- **Chunk embedding**: Text chunks embedded for vector similarity search
- **Entity embedding**: Entities embedded for semantic retrieval
- **LLM caching**: Cached completions for idempotent, resilient indexing
- **Configurable workflows**: Modular pipeline with customizable steps and prompts

### Query Mechanisms

- **Local Search**: Combines AI-extracted knowledge graph with text chunks for entity-specific questions
- **Global Search**: Map-reduce over community reports for dataset-wide thematic questions
- **DRIFT Search**: Expands local search breadth using community insights for comprehensive answers
- **Basic Search**: Vector RAG baseline for comparison (top-k chunk retrieval)
- **Question Generation**: Generates follow-up questions for deeper investigation

### Architecture

- **Monorepo structure**: Modular packages (graphrag-cache, graphrag-chunking, graphrag-common, graphrag-input, graphrag-llm, graphrag-storage, graphrag-vectors)
- **Factory pattern**: Extensible providers for models, storage, cache, vectors, input readers
- **Parquet outputs**: Indexes stored as Parquet tables for efficient querying
- **CLI and Python API**: Multiple interfaces for indexing and querying

### Model Support

- **OpenAI**: Direct API integration
- **Azure OpenAI**: Full support with managed identity authentication
- **LiteLLM wrapper**: Extensible to additional providers
- **Prompt tuning**: Guidance for domain-specific prompt optimization

### Storage Backends

- **File storage**: Local filesystem for development
- **Azure Blob Storage**: Cloud storage integration
- **CosmosDB**: Distributed database support
- **Vector stores**: LanceDB, Azure AI Search, CosmosDB vector search

---

## Technical Architecture

### Pipeline Flow

```text
Load Documents
    |
Chunk Documents
    |
    +-- Extract Graph --> Detect Communities --> Generate Reports --> Embed Reports
    |
    +-- Extract Claims
    |
    +-- Embed Chunks
    |
    +-- Embed Entities
```

### Knowledge Model

| Component         | Description                                          |
| ----------------- | ---------------------------------------------------- |
| Documents         | Source text files (txt, CSV, JSON)                   |
| Text Units        | Chunked document segments                            |
| Entities          | Extracted named entities (people, places, things)    |
| Relationships     | Connections between entities                         |
| Claims            | Factual assertions extracted from text               |
| Communities       | Clusters of related entities from graph analysis     |
| Community Reports | LLM-generated summaries at multiple hierarchy levels |
| Embeddings        | Vector representations for semantic search           |

### Factory Extensions

| Subsystem      | Purpose                         | Built-in Options                      |
| -------------- | ------------------------------- | ------------------------------------- |
| Language Model | Chat and embed methods          | LiteLLM wrapper (OpenAI, Azure, etc.) |
| Input Reader   | Document ingestion              | Text, CSV, JSON                       |
| Cache          | LLM response caching            | File, Blob, CosmosDB                  |
| Storage        | Index persistence               | File, Blob, CosmosDB                  |
| Vector Store   | Embedding storage and retrieval | LanceDB, Azure AI Search, CosmosDB    |
| Workflows      | Pipeline step customization     | Default GraphRAG pipeline             |

---

## Installation and Usage

### Installation

```bash
# Using pip
pip install graphrag

# Using uv
uv pip install graphrag
```

### Quick Start

```bash
# Initialize workspace
mkdir graphrag_project && cd graphrag_project
graphrag init

# Configure API key in .env
# GRAPHRAG_API_KEY=<your-api-key>

# Add documents to ./input directory
curl https://www.gutenberg.org/cache/epub/24022/pg24022.txt -o ./input/book.txt

# Run indexing
graphrag index

# Query with Global Search (thematic questions)
graphrag query "What are the top themes in this story?"

# Query with Local Search (entity-specific questions)
graphrag query "Who is Scrooge and what are his main relationships?" --method local
```

### Python API

```python
from graphrag.api import build_index, local_search, global_search

# Index documents
await build_index(root="./graphrag_project")

# Local search for entity questions
result = await local_search(
    root="./graphrag_project",
    query="What are the healing properties of chamomile?"
)

# Global search for thematic questions
result = await global_search(
    root="./graphrag_project",
    query="What are the main themes across all documents?"
)
```

### Azure OpenAI Configuration

```yaml
# settings.yaml
models:
  default_chat_model:
    type: chat
    model_provider: azure
    model: gpt-4.1
    deployment_name: <AZURE_DEPLOYMENT_NAME>
    api_base: https://<instance>.openai.azure.com
    api_version: 2024-02-15-preview
    auth_type: azure_managed_identity  # Optional: for managed auth
```

---

## Relevance to Claude Code Development

### Direct Applications

1. **Knowledge-Augmented Skills**: GraphRAG patterns could inform how Claude Code skills organize and retrieve reference documentation, using graph structure instead of flat files.

2. **Cross-Document Reasoning**: The community detection and hierarchical summarization approach provides a model for answering questions that span multiple skill reference files.

3. **Thematic Query Support**: Global search mechanism could inspire how Claude Code answers abstract questions about a codebase ("What patterns does this project follow?").

4. **Context Window Optimization**: Community reports provide compressed summaries that could reduce token usage while maintaining comprehensive coverage.

5. **Caching Patterns**: LLM caching strategy applicable to Claude Code for expensive operations.

### Patterns Worth Adopting

1. **Multiple Search Strategies**: Local vs Global vs DRIFT search demonstrates value of query-type-specific retrieval strategies.

2. **Community Detection**: Graph clustering to identify related concepts could improve skill organization and cross-referencing.

3. **Hierarchical Summarization**: Multi-level community reports enable both detailed and overview queries on same index.

4. **Factory Pattern**: Extensible providers for all subsystems enable customization without core changes.

5. **Parquet Outputs**: Columnar format for index storage enables efficient analytical queries.

### Integration Opportunities

1. **MCP Server**: GraphRAG could be exposed as an MCP tool for Claude Code to query indexed knowledge bases.

2. **Skill Indexing**: Index skill reference documentation with GraphRAG for enhanced retrieval in complex multi-skill queries.

3. **Codebase Understanding**: Index codebase documentation/comments to answer architectural questions.

4. **Research Aggregation**: Index research entries (like this one) for cross-resource thematic queries.

### Comparison: GraphRAG vs Traditional RAG

| Aspect                    | GraphRAG                              | Traditional Vector RAG        |
| ------------------------- | ------------------------------------- | ----------------------------- |
| Cross-document reasoning  | Strong (graph connections)            | Weak (isolated chunks)        |
| Thematic/abstract queries | Strong (community reports)            | Weak (no global context)      |
| Entity-specific queries   | Strong (local search + graph)         | Moderate (chunk retrieval)    |
| Indexing cost             | High (LLM-intensive extraction)       | Low (embedding only)          |
| Query latency             | Higher (map-reduce for global)        | Lower (single retrieval)      |
| Storage requirements      | Higher (graph + reports + embeddings) | Lower (embeddings only)       |
| Update complexity         | Higher (re-extraction)                | Lower (re-embed changed docs) |

### Cost Considerations

The README explicitly warns: "GraphRAG indexing can be an expensive operation." Best practices:

- Start with small test datasets
- Use inexpensive/fast models for initial experimentation
- Leverage LLM caching to avoid redundant API calls
- Consider update strategies before large indexing jobs

---

## References

| Source                     | URL                                                                                                         | Accessed   |
| -------------------------- | ----------------------------------------------------------------------------------------------------------- | ---------- |
| GitHub Repository          | <https://github.com/microsoft/graphrag>                                                                     | 2026-01-31 |
| Official Documentation     | <https://microsoft.github.io/graphrag/>                                                                     | 2026-01-31 |
| arXiv Paper                | <https://arxiv.org/pdf/2404.16130>                                                                          | 2026-01-31 |
| Microsoft Research Blog    | <https://www.microsoft.com/en-us/research/blog/graphrag-unlocking-llm-discovery-on-narrative-private-data/> | 2026-01-31 |
| PyPI Package               | <https://pypi.org/project/graphrag/>                                                                        | 2026-01-31 |
| PyPI Stats                 | <https://pypistats.org/packages/graphrag>                                                                   | 2026-01-31 |
| RAI Transparency Document  | <https://github.com/microsoft/graphrag/blob/main/RAI_TRANSPARENCY.md>                                       | 2026-01-31 |
| Query Engine Documentation | <https://microsoft.github.io/graphrag/query/overview/>                                                      | 2026-01-31 |
| Indexing Documentation     | <https://microsoft.github.io/graphrag/index/overview/>                                                      | 2026-01-31 |
| Architecture Documentation | <https://microsoft.github.io/graphrag/index/architecture/>                                                  | 2026-01-31 |

**Research Method**: Information gathered from official GitHub repository README, RAI transparency document, documentation pages (query overview, index overview, architecture), GitHub API for statistics, PyPI API for package info and download statistics. All claims verified against primary sources.

---

## Freshness Tracking

| Field              | Value                     |
| ------------------ | ------------------------- |
| Version Documented | v3.0.1                    |
| Release Date       | 2026-01-28                |
| GitHub Stars       | 30,637 (as of 2026-01-31) |
| Monthly Downloads  | 60,312 (as of 2026-01-31) |
| Next Review Date   | 2026-05-01                |

**Review Triggers**:

- Major version release (v4.x)
- Significant new query mechanisms
- New storage or model provider integrations
- GitHub stars milestone (40K, 50K)
- PyPI downloads milestone (100K monthly)
- New community detection algorithms
- Breaking changes to knowledge model or API
- Integration with Claude/Anthropic models
