# TrustGraph: Context Development Platform

**Project**: TrustGraph AI
**Repository**: <https://github.com/trustgraph-ai/trustgraph>
**License**: Apache License 2.0
**Language**: Python
**Latest Update**: 2026-03-28

---

## Overview

TrustGraph is a graph-native context development platform designed for building AI applications that require structured knowledge retrieval at scale. Unlike traditional databases or vector stores, TrustGraph combines multi-model storage (relational, document, graph, vector), semantic retrieval pipelines, and agentic workflow support in a single integrated system. It positions itself as the infrastructure layer for "context engineering"—the practice of building, versioning, and deploying structured knowledge bases that LLMs can reason about reliably.

The platform ships with Docker containers and Kubernetes manifests for local or cloud deployment, eliminating the need for external API keys (except for third-party LLM services).

---

## Problem Addressed

**Challenge**: Building reliable AI applications requires more than vector search or traditional databases. Applications need:
- Structured, connected knowledge with provenance tracking
- Multi-modal data handling (text, code, images, video, audio)
- Semantic consistency through ontology enforcement
- Ability to version and promote knowledge like code
- Native support for multi-agent workflows that query and update knowledge
- Deployment flexibility (local Docker to Kubernetes)

**Solution**: TrustGraph provides "Context Cores"—portable, versioned bundles of structured knowledge including ontologies, entity relationships, embeddings, and retrieval policies. Agents can query these cores via REST/WebSocket/Python APIs and receive evidence-grounded results with provenance.

---

## Key Statistics

- **Stars**: 1,714 (as of 2026-03-28)
- **Forks**: 165
- **License**: Apache 2.0
- **Last Updated**: 2026-03-28
- **Created**: 2024-07-10
- **Primary Language**: Python
- **Python Requirement**: ≥3.8

---

## Key Features

### 1. Multi-Model Storage Layer

TrustGraph unifies four distinct storage models:

1. **Relational/Tabular Storage**: Traditional row/column data via Apache Cassandra
   - Supports SQL-like structured queries on knowledge facts
   - Enables analytical workloads over knowledge graphs
   - Query mechanism: hybrid translation layer converting graph queries to columnar queries

2. **Key-Value Storage**: Fast lookups for entity metadata and configuration
   - Backing: Cassandra (tunable for other backends)

3. **Graph Storage**: Entity-relationship networks with RDF/SPO (Subject-Predicate-Object) semantics
   - Core data structure: `node → edge → {node | literal}`
   - Supports relationship traversal and path queries
   - Bidirectional edge following for reachability analysis

4. **Vector Storage**: Semantic similarity search over embeddings
   - Backing: Qdrant vector database
   - Direct mapping from NLP queries to graph nodes via embeddings
   - Enables "embedding-based graph navigation" (query → embeddings → graph nodes)

**Mechanism**: A single query can traverse multiple storage models—for example, find entities semantically similar to a question (vector), retrieve their relationships (graph), and join with structured facts (relational).

### 2. Ontology-Driven Knowledge Extraction (OntoRAG)

OntoRAG enforces semantic consistency during knowledge extraction by:

- **Dynamic Ontology Selection**: Uses embedding similarity to select relevant ontology elements for each text chunk
- **Extraction Validation**: All extracted triples must conform to predefined ontological structures (class hierarchies, property domains/ranges)
- **Semantic Consistency Guarantee**: Maintains formal constraint validity across the entire knowledge graph

**Service Name**: `kg-extract-ontology`
**Alternative Extraction Modes**: Non-ontology-driven extraction via `kg-extract-definitions` and `kg-extract-relationships` (no formal constraints).

### 3. RAG Pipeline Support (Triple-Mode)

The platform ships with three integrated RAG implementations:

1. **DocumentRAG**: Retrieves and ranks document chunks by semantic relevance
   - Mechanism: TF-IDF + vector similarity combination
   - Use case: Q&A over unstructured text collections

2. **GraphRAG**: Traverses knowledge graph to construct entity-centric subgraphs for LLM context
   - Graph traversal algorithm: depth-limited graph exploration with entity ranking
   - Use case: Structured fact retrieval with relationship context
   - Optimization note: Subject to performance bottlenecks with large graphs (recursive traversal, sequential label resolution, unbounded caching)

3. **OntologyRAG** (OntoRAG): Combines graph traversal with ontology-conformant entity resolution
   - Mechanism: Semantic constraint validation during subgraph construction
   - Use case: High-fidelity knowledge queries with formal constraint guarantees

### 4. Workbench UI

The Workbench provides a full-featured web interface (port 8888 default) with:

- **Vector Search**: Semantic similarity search across knowledge bases
- **Chat Interfaces**: Agent chat, GraphRAG chat, direct LLM chat
- **Relationship Explorer**: Deep relationship analysis in installed knowledge bases
- **3D Graph Visualizer**: Interactive 3D visualization of entity networks
- **Flow Designer**: No-code workflow builder for defining custom retrieval pipelines
- **Knowledge Base Management**: Library staging, installation, versioning
- **Ontology/Schema Editor**: Visual creation of domain-specific constraints
- **LLM Parameter Tuning**: Runtime adjustment of temperature, top_k, etc. across flows
- **Prompt Management**: Central repository for reusable prompt templates
- **Agent Tool Definition**: Binding collections, knowledge cores, MCP servers to agent tools

### 5. Agentic System (Single & Multi-Agent)

**Single Agent Mode**: ReAct pattern with tool access
- Agent tools directly access collections and knowledge cores
- Tools retrieve facts, reason, and report observations
- Integrated MCP support for external tool connections

**Multi-Agent Mode**: Orchestrated agent workflows
- Agents trigger pub-sub events for inter-agent communication
- Reentrant pub-sub support enables complex workflows (agent A's observation triggers agent B's query)
- Message-driven architecture prevents tight coupling

**MCP Integration**: Connect to any MCP-compliant server as an agent tool
- Bearer token support for authenticated MCP connections
- Tool grouping allows organizing MCP tools into collections

### 6. Context Cores (Portable Knowledge Bundles)

A Context Core packages everything an agent needs to know:

- **Ontology**: Domain-specific schema (RDF/OWL format)
- **Context Graph**: Entities and relationships extracted/curated for the domain
- **Embeddings**: Pre-computed vector indexes for fast semantic entry points
- **Source Manifests & Provenance**: Attribution metadata (where facts came from, when derived, confidence)
- **Retrieval Policies**: Traversal rules, freshness constraints, authority ranking

**Workflow**: Build and test a core → version it → deploy to production → roll back or promote to new version
This treats context like code (version control, testing, promotion).

### 7. Embedded LLM Inference Stack

TrustGraph includes production-ready LLM serving options:

- **vLLM**: High-throughput inference for Hugging Face models
- **TGI** (Text Generation Inference): Multi-GPU text generation
- **Ollama**: Lightweight local inference
- **LM Studio**: Desktop LLM interface with API server
- **Llamafiles**: Single-binary executable LLMs

**Integration**: These run as managed services in the TrustGraph Docker deployment—no separate LLM API key needed for open models.

### 8. Public LLM API Support

Integration with major LLM providers:

| Provider | Support | Notes |
|----------|---------|-------|
| Anthropic | ✓ | Full API support |
| OpenAI | ✓ | Full API support |
| Google VertexAI | ✓ | Full API support |
| Google AI Studio | ✓ | Full API support |
| Cohere | ✓ | Full API support |
| Mistral | ✓ | Full API support |
| AWS Bedrock | ✓ | Dedicated `trustgraph-bedrock` module |
| Azure OpenAI | ✓ | Full API support |
| Azure AI | ✓ | Full API support |

### 9. Full API Surfaces

1. **REST API**: Standard HTTP endpoints for all operations (documented at `/reference/apis/rest.html`)
2. **WebSocket API**: Streaming responses and real-time updates (documented at `/reference/apis/websocket.html`)
3. **Python SDK**: Synchronous and asynchronous clients (documented at `/reference/apis/python`)
4. **CLI**: Command-line tool for deployment, knowledge base management, and local testing (documented at `/reference/cli/`)

---

## Technical Architecture

### Core Design Principles

TrustGraph is built on 7 foundational architectural decisions:

1. **SPO/RDF Graph Model**: Subject-Predicate-Object triples as the universal representation
   - Provides maximum flexibility and interoperability
   - Supports translation to other graph query languages (Cypher, SPARQL, etc.)
   - Enables both node-to-node and node-to-literal relationships

2. **LLM-Native Optimization**: Every architectural choice prioritizes LLM reasoning capability
   - Graph schemas are designed for natural language understanding
   - Semantic search is optimized for embedding-based entry points

3. **Embedding-Based Navigation**: Direct path from natural language to graph entities via semantic similarity
   - Avoids complex intermediate query generation
   - Reduces latency between user intent and knowledge retrieval

4. **Distributed Entity Resolution with Deterministic IDs**: Supports parallel extraction across multiple processes
   - Deterministic identifier generation ensures same entity → same ID across processes
   - Pragmatic acknowledgment that ~20% of edge cases may require fallback mechanisms

5. **Event-Driven Pub-Sub Messaging**: Apache Pulsar enables loose coupling between system components
   - Knowledge extraction, storage, and query components communicate via message streams
   - Supports real-time updates and asynchronous processing

6. **Reentrant Agent Communication**: Pub-sub system handles complex agent workflows
   - Agents can trigger and respond to each other safely
   - Prevents infinite loops through workflow state tracking

7. **Columnar Query Compatibility**: Enables analytical queries alongside graph operations
   - Query translation layer converts graph queries to columnar (Cassandra) operations
   - Supports business intelligence and reporting workloads

### System Components

#### Storage Layer

| Component | Technology | Purpose | Scalability |
|-----------|-----------|---------|------------|
| Multi-Model Storage | Apache Cassandra | Relational, key-value, and graph data | Horizontal via sharding |
| Vector Index | Qdrant | Semantic similarity search | Clustering support |
| Object Storage | Garage (S3-compatible) | File and multimedia storage | Distributed object store |

#### Message & Coordination

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Pub/Sub Messaging | Apache Pulsar | Event-driven component coordination |
| Observability | Prometheus + Grafana | Metrics collection and visualization |
| Logs | Loki | Distributed log aggregation |

#### API Layer

| Component | Type | Clients |
|-----------|------|---------|
| REST Gateway | HTTP API | Web clients, CLI tools |
| WebSocket Gateway | WebSocket API | Real-time streaming clients |
| Python SDK | Native library | `trustgraph` package on PyPI |

#### Processing Pipelines

- **kg-extract-ontology**: Ontology-conformant triple extraction
- **kg-extract-definitions**: Non-ontology entity extraction
- **kg-extract-relationships**: Relationship extraction service
- **flow-engine**: Custom workflow execution
- **agent-executor**: ReAct agent implementation with tool calling

### Data Flow Example: Graph RAG Query

```
User Query → Embedding Service → Qdrant (vector search) → Entity nodes
                                                              ↓
                                                    Graph Traversal Service
                                                              ↓
                                                    Cassandra (entity data)
                                                              ↓
                                                    Label Resolution (batch)
                                                              ↓
                                                    Context Subgraph → LLM
```

---

## Installation & Usage

### Quickstart (Configuration-Driven Deployment)

TrustGraph provides an interactive configuration tool to generate deployment manifests:

```bash
npx @trustgraph/config
```

This tool:
- Generates `deploy.zip` containing either `docker-compose.yaml` (for Docker/Podman) or `resources.yaml` (for Kubernetes)
- Outputs `INSTALLATION.md` with deployment instructions
- Provides a browser-based alternative at <https://config-ui.demo.trustgraph.ai/>

### Docker Deployment Example

```bash
# After running the config tool, extract deploy.zip
unzip deploy.zip
cd deploy

# Deploy with Docker
docker-compose up -d

# Access the Workbench at http://localhost:8888
# Access Grafana dashboard at http://localhost:3000 (admin/admin)
```

### Python API Example

```python
from trustgraph.api import Api

# Initialize client (local development)
api = Api(url="http://localhost:8088/")

# Execute a GraphRAG query
response = api.flow().id("default").graph_rag(
    query="What are the main topics?",
    user="trustgraph",
    collection="default"
)

# Use async variant for concurrent requests
async with Api() as api:
    async_flow = api.async_flow().id("default")
    result = await async_flow.graph_rag(...)
```

### Python SDK Components

**Core Classes** (imported from `trustgraph.api`):
- `Api`: Main entry point for all operations
- `Flow`/`AsyncFlow`: Synchronous and asynchronous flow execution
- `FlowInstance`/`AsyncFlowInstance`: Flow instances bound to a specific flow ID
- `SocketClient`/`AsyncSocketClient`: WebSocket clients for streaming
- `BulkClient`/`AsyncBulkClient`: Batch operations (ingest, export)
- `Metrics`/`AsyncMetrics`: Performance metrics and telemetry

**Data Types**:
- `Triple`: RDF triple (subject, predicate, object)
- `CollectionMetadata`: Collection configuration and statistics
- `RAGChunk`: Retrieved context chunk with metadata
- `AgentThought`/`AgentObservation`/`AgentAnswer`: Agent reasoning trace

### CLI Usage

```bash
# Installation
pip install trustgraph-cli

# Local configuration and deployment
trustgraph config generate docker-compose.yaml 1.8.3

# Knowledge base operations
trustgraph kb list
trustgraph kb install --path ./my-knowledge-core

# Query and debugging
trustgraph query --collection default --query "What entities exist?"
```

---

## Relevance to Claude Code Development

TrustGraph is highly relevant for Claude Code developers building agent-based applications, particularly in these scenarios:

### 1. Multi-Agent Knowledge Orchestration
Developers can use TrustGraph Context Cores as a shared knowledge layer for multi-agent teams. Each agent queries the same versioned knowledge base, ensuring consistency across agent decisions. The pub-sub event system enables agents to notify peers of important discoveries.

**Use case**: Building a development team simulator where agents (code reviewer, test architect, documentation reviewer) all reference the same codebase analysis and constraints.

### 2. Context Window Optimization for Long Tasks
Instead of repeatedly including full codebase documentation in prompts, agents can query TrustGraph's semantic indexes to retrieve only relevant portions. This preserves context budget for reasoning rather than data transfer.

**Use case**: Analyzing a 50K-line codebase—send only the 2KB of architectural diagrams and entity relationships relevant to the query, not the entire spec.

### 3. Persistent Knowledge Across Sessions
Context Cores enable building knowledge across sessions. An agent's analysis in session N can be packaged as a core, versioned, and reused in session N+1 with confidence that the knowledge hasn't drifted.

**Use case**: A project analysis agent that learns about the codebase over multiple sessions and refines its understanding without re-reading source files.

### 4. Evidence-Grounded Agent Responses
GraphRAG and OntoRAG provide provenance tracking—every fact returned includes its source document, extraction confidence, and chain of inference. This enables agents to cite evidence when explaining decisions.

**Use case**: An agent recommends a refactoring and cites the three architectural principles from the design spec that support the change.

### 5. Streaming Agent Responses
WebSocket API support enables real-time agent reasoning traces—agents can emit thoughts and observations as they compute, with streaming LLM completions.

**Use case**: A UI displaying agent thinking in real-time as it works through a problem.

### 6. Multi-Modal Knowledge Representation
TrustGraph handles images, videos, and audio alongside text. Agents building visual documentation or analyzing screenshots can store findings in the same knowledge base as code analysis.

**Use case**: A visual design agent that updates design specs as context cores, cross-referencing them with code structure analysis.

---

## Limitations and Caveats

1. **GraphRAG Performance at Scale**
   - Current implementation exhibits quadratic or worse complexity in graph size due to recursive traversal without memoization
   - Database load increases significantly with deeper traversal (3+ hops) and large entity sets
   - Specification acknowledges 50-80% reduction in queries targeted through planned caching improvements (not yet implemented in main branch)
   - **Workaround**: Limit traversal depth in flow configuration, use OntoRAG for smaller, well-defined ontologies

2. **No Built-In Multi-Tenancy Isolation**
   - Specification exists for multi-tenant support but scope and implementation status not documented in reviewed sources
   - Current behavior: single-tenant per deployment instance
   - **Workaround**: Deploy separate TrustGraph instances per tenant

3. **Label Resolution Bottleneck**
   - Sequential label fetching for subgraph construction (up to 3 queries per triple component)
   - Not parallelized in current implementation
   - **Workaround**: Cache warmed during ontology loading phase

4. **Cassandra Consolidation Not Complete**
   - Multiple database backend migration paths documented (neo4j consolidation, other options) but current state unclear
   - May affect upgrade paths between versions
   - **Recommendation**: Review release notes before major version upgrades

5. **Limited Formal Guarantees on Entity Deduplication**
   - Deterministic ID generation supports ~80% of entity resolution scenarios
   - Remaining 20% of edge cases explicitly acknowledged as requiring fallback mechanisms (not detailed in spec)
   - **Workaround**: Post-extraction curation for high-precision ontologies

6. **Knowledge Core Versioning Is Manual**
   - Context Cores version like code, but version promotion workflow not automated
   - No built-in CI/CD integration for core testing and deployment
   - **Workaround**: Integrate TrustGraph operations into existing deployment pipelines

7. **Not Mentioned in Documentation**
   - Query time complexity bounds for semantic similarity at scale (Qdrant clustering behavior)
   - Backup and disaster recovery procedures
   - Data export/import formats for migrating between TrustGraph instances
   - SLA guarantees or uptime expectations

---

## References

- **Main Documentation**: <https://docs.trustgraph.ai> (accessed 2026-03-28)
- **GitHub Repository**: <https://github.com/trustgraph-ai/trustgraph> (accessed 2026-03-28)
- **README.md**: Core feature descriptions and quickstart (accessed 2026-03-28)
- **Tech Spec — Architecture Principles**: <https://github.com/trustgraph-ai/trustgraph/blob/main/docs/tech-specs/architecture-principles.md> (accessed 2026-03-28)
- **Tech Spec — OntoRAG**: <https://github.com/trustgraph-ai/trustgraph/blob/main/docs/tech-specs/ontorag.md> (accessed 2026-03-28)
- **Tech Spec — GraphRAG Performance Optimization**: <https://github.com/trustgraph-ai/trustgraph/blob/main/docs/tech-specs/graphrag-performance-optimization.md> (accessed 2026-03-28)
- **Python API Documentation**: <https://github.com/trustgraph-ai/trustgraph/blob/main/docs/python-api.md> (accessed 2026-03-28)
- **PyPI Package**: <https://pypi.org/project/trustgraph/> (accessed 2026-03-28)
- **Discord Community**: <https://discord.gg/sQMwkRz5GX>
- **Blog**: <https://blog.trustgraph.ai/subscribe>

---

## Freshness Tracking

| Section | Confidence | Last Verified | Next Review |
|---------|-----------|---------------|------------|
| **Identity/Metadata** | high | 2026-03-28 | 2026-06-28 |
| **Key Features** | high | 2026-03-28 | 2026-06-28 |
| **Technical Architecture** | high | 2026-03-28 | 2026-06-28 |
| **Installation & Usage** | high | 2026-03-28 | 2026-06-28 |
| **Relevance to Claude Code** | high | 2026-03-28 | 2026-06-28 |
| **Limitations** | medium | 2026-03-28 | 2026-06-28 |

**Confidence Rationale**:
- Identity/Metadata: GitHub API + live repository inspection (high)
- Key Features: README and tech specs read in full (high)
- Architecture: Foundation document fully read, design decisions explicit in source (high)
- Installation: Quickstart and Python API docs fully read (high)
- Relevance: Assessed from feature set and primary documentation (high)
- Limitations: Source specifications and performance optimization docs reviewed; some edge cases explicitly noted as undocumented (medium)
