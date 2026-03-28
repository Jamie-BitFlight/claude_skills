---
title: Chroma - Open-Source Vector Database Infrastructure
slug: chroma
resource_type: vector-database
category: data-infrastructure
created_date: 2026-03-28
last_reviewed_date: 2026-03-28
source_url: https://github.com/chroma-core/chroma
maturity_level: production
---

## Overview

Chroma is an open-source vector database and AI data infrastructure project designed to provide vector, hybrid, and full-text search capabilities. The project emphasizes ease of use with a minimal API surface, multi-language support (Python, JavaScript), and a hosted cloud offering (Chroma Cloud). Chroma is built on Rust for performance-critical components with Python bindings for accessibility.

**Key Identity:**

- Name: `chromadb` (PyPI package)
- Repository: `chroma-core/chroma` (GitHub)
- License: Apache License 2.0
- Latest Release: v1.5.5 (published 2026-03-10)
- Language: Rust (primary), Python (bindings and API layer)
- Python Support: >=3.9

---

## Problem Addressed

Chroma addresses the challenge of embedding and searching unstructured data (documents, text, images) for AI applications. It eliminates the friction of vector database setup by providing:

1. **Automatic Embedding**: Tokenization, embedding generation, and indexing handled automatically or customizable with user-provided embeddings
2. **Simple Unified Query API**: Four core operations (`create_collection`, `add`, `query`, `get`) cover 95% of use cases
3. **Search Flexibility**: Vector similarity search, hybrid search (vector + metadata), and full-text search in a single interface
4. **Deployment Flexibility**: In-memory (prototyping), persistent local, client-server, or managed cloud
5. **Production Readiness**: OpenTelemetry observability, Kubernetes orchestration support, authentication and authorization, rate limiting, quota management

---

## Key Statistics

- **GitHub Stars**: 26,951 (as of 2026-03-28)
- **GitHub Forks**: 2,147 (as of 2026-03-28)
- **Repository Created**: 2022-10-05
- **Last Updated**: 2026-03-28 02:02 UTC
- **Topics**: agents, ai, ai-agents, database, rust, rust-lang
- **Release Cadence**: Monday tagged releases on PyPI/npm; hotfixes throughout week (from README)

---

## Key Features

### 1. Core API — Four Function Simplicity

From README: "The core API is only 4 functions" — `create_collection()`, `add()`, `query()`, `get()`. This minimalism is documented as intentional design:

```python
import chromadb
client = chromadb.Client()
collection = client.create_collection("all-my-documents")
collection.add(
    documents=["This is document1"],
    metadatas=[{"source": "notion"}],
    ids=["doc1"]
)
results = collection.query(
    query_texts=["This is a query"],
    n_results=2
)
```

### 2. Automatic Embedding

By default, documents are tokenized and embedded automatically using built-in embedding functions (ONNX Runtime-based). Users can override with custom embeddings via the `embeddings` parameter. Source: `chromadb/__init__.py` re-exports `EmbeddingFunction` and `Embeddings` types indicating user-supplied embedding support.

### 3. Metadata Filtering and Hybrid Search

Collections support metadata filters on insertion (`metadatas` parameter, type `Metadatas`) and filtering on query (`where` parameter for metadata, `where_document` for document content). Full-text search integration via `FtsIndexConfig` (Tantivy full-text engine, from Cargo.toml). Hybrid search via Reciprocal Rank Fusion (`Rrf` operator in `chromadb/__init__.py`).

### 4. Multi-Deployment Modes

- **In-Memory**: `chromadb.Client()` — ephemeral, for prototyping
- **Persistent Local**: Add path parameter for SQLite-backed persistence
- **Client-Server**: `chroma run --path /chroma_db_path` (from README) spawns HTTP server
- **Distributed**: Kubernetes-native deployment via Helm; `tilt up` local dev orchestration (from DEVELOP.md)
- **Chroma Cloud**: Managed serverless offering with free credits signup

### 5. Query Planning and Execution Engine

`chromadb/execution/` module contains expression planner and executor. Search API exports `Search`, `Key`, `Knn`, `Rrf` operators for building complex query plans. Enables columnar filtering and KNN ranking composition.

### 6. Vector Index Options

From `chromadb/api/types.py`, multiple index configurations supported:

- **HNSW** (`HnswIndexConfig`): Hierarchical Navigable Small World approximate nearest neighbor index
- **Spann** (`SpannIndexConfig`): Learned index method
- **Full-Text Search** (`FtsIndexConfig`): Tantivy-backed inverted index for text
- **Sparse Vectors** (`SparseVectorIndexConfig`, `SparseVector`, `SparseEmbeddingFunction`): Sparse embedding support

### 7. Production Features

**Authentication & Authorization**: `chromadb/auth/` module contains token-based authentication (`TokenTransportHeader`) and authorization logic.

**Observability**: OpenTelemetry integration (`chromadb/telemetry/`) with gRPC OTLP exporter for traces and metrics.

**Rate Limiting & Quotas**: `chromadb/rate_limit/` and `chromadb/quota/` modules for resource governance.

**Data Segmentation**: `chromadb/segment/` implements abstract segment interface with distributed and local implementations, enabling distributed query processing.

---

## Technical Architecture

### Language and Build

- **Primary Implementation**: Rust (26 workspace crates in `Cargo.toml`)
- **Python Bindings**: PyO3 via maturin build backend; Python version constraint >=3.9, release >=0.24.1
- **Build System**: maturin for compiled extension; setuptools_scm for version derivation from git tags

### Core Component Structure

**Rust Workspace Crates** (from Cargo.toml):

1. **Indexing**: `chroma-index` (vector indexing), `chroma-storage` (block storage), `chroma-cache` (caching)
2. **Execution**: `chroma-segment` (distributed segment coordination), `worker` (async task execution)
3. **Data Layer**: `chroma-sysdb` (system metadata), `chroma-sqlite` (SQLite backend), `chroma-log` (write-ahead log)
4. **Networking**: `chroma-frontend` (API gateway), `tonic` (gRPC), `axum` (HTTP)
5. **Coordination**: `chroma-memberlist` (gossip membership), `chroma-system` (distributed system state)
6. **Infrastructure**: `chroma-metering` (usage tracking), `chroma-tracing` (distributed tracing)

**Python API Layer** (from `chromadb/` structure):

- `chromadb/api/`: Client, AsyncClient, FastAPI server implementations
- `chromadb/db/`: Database abstraction and persistence
- `chromadb/segment/impl/`: Segment implementations (local, distributed)
- `chromadb/execution/`: Query planner and expression executor
- `chromadb/server/`: HTTP/gRPC server wrappers

### Key Dependencies (from Cargo.toml and pyproject.toml)

**Rust (core indexing and performance)**:

- `hnswlib` (custom fork): HNSW vector search
- `usearch`: Vector search library
- `tantivy`: Full-text search engine
- `tokio`: Async runtime
- `tonic`: gRPC framework
- `axum`: HTTP web framework
- `sqlx`: Database abstraction (SQLite, PostgreSQL support)
- `object_store`: Cloud storage abstraction (S3, GCP)
- `opentelemetry-*`: Observability SDKs
- `pyo3`: Python bindings

**Python**:

- `pydantic >= 2.0`: Data validation and serialization
- `uvicorn >= 0.18.3`: ASGI server
- `onnxruntime >= 1.14.1`: ML model execution for embeddings
- `grpcio >= 1.58.0`: gRPC client/server
- `kubernetes >= 28.1.0`: K8s client for distributed deployments
- `httpx >= 0.27.0`: Async HTTP client
- `rich >= 10.11.0`: Terminal formatting
- `opentelemetry-*`: Observability

### Distributed Architecture

Chroma supports horizontal scaling via:

1. **Segment-based Partitioning**: Collections distributed across segment replicas; queries routed to responsible segments (from `chromadb/segment/distributed/`)
2. **Kubernetes Native**: Tilt configuration orchestrates query-service, worker, index-service pods; StatefulSet for coordination (from DEVELOP.md)
3. **System Database**: `chroma-sysdb` (SQLite/Postgres-backed) maintains collection-to-segment mappings
4. **Log Service**: Write-ahead logging via `chroma-log-service` for consistency
5. **Member Discovery**: `chroma-memberlist` (gossip protocol) for cluster membership

---

## Installation & Usage

### Python Installation

```bash
pip install chromadb  # Latest from PyPI
```

From README: Release cadence is Monday tagged releases; supports both PyPI and npm.

### JavaScript Installation

```bash
npm install chromadb
```

### Local Usage Example

```python
import chromadb

# In-memory (ephemeral)
client = chromadb.Client()

# Persistent (SQLite)
client = chromadb.Client()  # defaults to ~/.chroma

# Create and query
collection = client.create_collection("my-docs")
collection.add(documents=["text1", "text2"], ids=["id1", "id2"])
results = collection.query(query_texts=["search term"], n_results=2)
```

### Server Mode

```bash
# Start server at localhost:8000
chroma run --path /path/to/db
```

CLI entry point: `chroma = "chromadb.cli.cli:app"` (from pyproject.toml) — powered by Typer.

### Docker Deployment

Dockerfiles present for Linux and Windows (`Dockerfile`, `Dockerfile.windows` in repo root). Chroma Cloud signup provides managed hosted option with $5 free credits and 30-second setup.

### Development Setup

Requires:

- Python virtual environment
- Protobuf compiler (`brew install protobuf` on macOS)
- For distributed dev: Docker, Kubernetes, Tilt, Helm

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -r requirements_dev.txt
pre-commit install
maturin dev  # Build Rust bindings
```

Unit tests via `pytest` (configured in `pyproject.toml` with `asyncio_mode = "auto"`). Tests assume `tilt up` running for distributed tests (from DEVELOP.md).

---

## Relevance to Claude Code Development

### Direct Use Cases

1. **AI Agent Memory and RAG**: Chroma provides the vector search infrastructure for Retrieval-Augmented Generation, critical for agent prompt context. Agents can store and retrieve documents/embeddings to augment reasoning.

2. **Embedding Function Integration**: Python support for custom `EmbeddingFunction` allows agents to plug in LLM-specific embedding models or use multi-modal embeddings (image, text).

3. **Metadata-Based Filtering**: Agents can organize documents by source, date, relevance score, and filter during query — enabling fine-grained context control.

4. **Hybrid Search Patterns**: Combining vector similarity with metadata filters enables semantic search with business logic constraints (time windows, source whitelisting, etc.).

### Agent Infrastructure Relevance

- **Async Support**: `AsyncClient` and `AsyncClientAPI` enable non-blocking vector operations in agent event loops.

- **Authentication**: Token-based auth (`TokenTransportHeader`) supports securing vector data in multi-tenant agent deployments.

- **Observability**: OpenTelemetry integration enables tracing vector operations within agent execution traces.

- **Deployment Flexibility**: Chroma's multiple deployment modes (in-process for quick prototyping, server mode for service architecture, Kubernetes for scale) match agent infrastructure patterns.

### Limitations

1. **No Built-in Versioning**: Collections are mutable; historical snapshots require external management.

2. **Single-Shard in-Memory**: In-memory mode has no distributed sharding; scaling requires server deployment.

3. **Embedding Throughput**: ONNX Runtime-based embeddings may not saturate GPU; custom embedding functions required for high-throughput use cases.

4. **Transaction Scope**: Query operations are point-in-time; cross-collection transactions not supported.

---

## Limitations and Caveats

1. **No Multi-Model Transactions**: Chroma does not support ACID transactions across collections; updates are collection-local.

2. **Manual Schema Management**: While collections auto-detect field types, schema definition is implicit in metadata shape; migrations require code changes.

3. **Deletion Semantics**: Soft deletes (marking deleted); hard delete with compaction not automatic.

4. **Index Rebuild**: Switching index types (HNSW to Spann) requires collection re-creation; no in-place index migration.

5. **Cloud Service Beta**: Chroma Cloud is a managed offering with separate SLA and feature set from open-source; not all open-source features guaranteed in cloud.

6. **Memory Pressure**: In-memory collections load entire datasets into RAM; large datasets require server/cloud deployment with persistence.

---

## References

### Primary Sources

- **GitHub Repository**: <https://github.com/chroma-core/chroma> (accessed 2026-03-28)
- **Official Homepage**: <https://www.trychroma.com/> (accessed via README)
- **Documentation**: <https://docs.trychroma.com/> (referenced in README)
- **Chroma Cloud**: <https://trychroma.com/signup> (referenced in README)
- **Discord Community**: <https://discord.gg/MMeYNTmh3x> (referenced in README)

### Source Files Analyzed

- `README.md` — Feature overview, API surface, getting started
- `pyproject.toml` — Python package metadata, dependencies, build config
- `Cargo.toml` — Rust workspace structure, crate dependencies, version info
- `DEVELOP.md` — Development setup, build procedures, testing guidance
- `chromadb/__init__.py` — Public API exports, type definitions
- `chromadb/api/` — Client/server implementation structure
- `chromadb/segment/`, `chromadb/execution/` — Distributed architecture

### GitHub API Queries

- Repository metadata: `https://api.github.com/repos/chroma-core/chroma` (2026-03-28)
- Latest release: `https://api.github.com/repos/chroma-core/chroma/releases/latest` (2026-03-28)

---

## Freshness Tracking

**Last Research Date**: 2026-03-28

**Confidence Summary**:

- **Identity/Metadata**: high — GitHub API, official repository, version from releases endpoint
- **Key Statistics**: high — GitHub API (stars, forks, created date, last update)
- **Features**: high — README, source code exports (`__init__.py`), pyproject.toml dependencies
- **Architecture**: high — Cargo.toml workspace structure, module layout, source files read
- **Installation & Usage**: high — README examples, pyproject.toml scripts, DEVELOP.md verified
- **Limitations**: medium — inferred from codebase structure and feature set; no explicit limitations doc found
- **Relevance**: medium — assessed from architecture; no direct Claude Code usage documentation found

**Next Review Date**: 2026-06-28 (3 months)

**Notes**: Chroma is actively maintained with weekly releases. Kubernetes and distributed features are production-ready. The project has clear API stability (core 4-function API unchanged). Documentation is comprehensive but spread across repository README, docs site, and code. Cloud offering is separate managed service with distinct feature parity from OSS.

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Claude-Mem - Persistent Memory Compression for Claude Code](../context-management/claude-mem.md) | context-management | Uses Chroma as embedded vector database for hybrid semantic search in AI agent memory |
| [CocoIndex](./cocoindex.md) | data-infrastructure | Complementary AI data transformation framework with native Chroma target for vector index building |
| [SimpleMem-Cross: Persistent Cross-Conversation Memory for LLM Agents](../context-management/simplemem-cross.md) | context-management | Shares use case for persistent agent memory with token-budgeted vector search and semantic retrieval |
| [Jina AI](../context-management/jina-ai.md) | context-management | Provides embedding models and APIs that feed into Chroma for RAG knowledge bases |
| [Zvec — Alibaba's Embedded Vector Database](./zvec.md) | data-infrastructure | Alternative embedded vector database with similar deployment model and dense/sparse vector support |
| [Local Memory - Persistent Memory Infrastructure for AI Agents](../context-management/local-memory.md) | context-management | Uses Qdrant for vector search in agent memory; shared pattern for persistent semantic retrieval across sessions |
| [MotherDuck](./motherduck.md) | data-infrastructure | Serverless analytics warehouse with Dual Execution model; complements Chroma for querying structured metadata alongside vectors |
| [Dolt](./dolt.md) | data-infrastructure | Version-controlled SQL database enabling reproducible training data snapshots; pairs with Chroma for versioned knowledge bases |
