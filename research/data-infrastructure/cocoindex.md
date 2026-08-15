---
title: "CocoIndex"
research_date: "2026-02-23"
source_url: "https://github.com/cocoindex-io/cocoindex"
github_url: "https://github.com/cocoindex-io/cocoindex"
documentation_url: "https://cocoindex.io/docs"
version_at_research: "v0.3.33"
license: "Apache 2.0"
last_verified: "2026-02-23"
version_at_verification: "v0.3.33"
next_review: "2026-05-23"
---

## Overview

CocoIndex is an ultra-performant real-time data transformation framework for AI, with its core engine written in Rust. It makes it effortless to transform data with AI and keep source data and targets in sync, supporting incremental processing and data lineage out-of-the-box. Whether building vector indexes, knowledge graphs for context engineering, or performing custom AI data transformations, CocoIndex goes beyond SQL with exceptional developer velocity and production-readiness from day one.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Building AI indexes (vector, knowledge graph) requires complex ETL pipelines | Declarative dataflow API in ~100 lines of Python with plug-and-play source/target components |
| Re-indexing from scratch when source data or logic changes is slow and expensive | Incremental processing: only recomputes affected portions and reuses cached results |
| Data pipelines have hidden state and side effects making debugging hard | Dataflow programming model: each transformation creates new fields solely from inputs — full lineage out-of-box |
| Switching between vector DBs or embedding models requires significant refactoring | Standardised interface for all components; swap sources, targets, or functions in one line |
| AI data pipelines need high performance for production workloads | Rust core engine provides ultra-high throughput while Python API keeps developer ergonomics |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 5K+ (Trendshift rank #13939) | 2026-02-23 |
| PyPI Version | v0.3.33 | 2026-02-23 |
| Python Support | 3.11, 3.12, 3.13, 3.14 | 2026-02-23 |
| Development Status | Alpha (3 - Alpha) | 2026-02-23 |
| Example Flows | 25+ | 2026-02-23 |
| Discord Community | Active | 2026-02-23 |

---

## Key Features

### Dataflow Programming Model

- Each transformation creates a new field solely based on input fields — no hidden state, no mutation
- All intermediate data is observable before and after each transformation
- Data lineage is automatic and built-in with no extra configuration
- Declarative API: developers define formulas for source data, not explicit create/update/delete operations

### Incremental Processing

- Minimal recomputation when source data or transformation logic changes
- Only (re-)processes necessary portions; reuses cached results when possible
- Postgres used internally for incremental state tracking
- Out-of-box support: no additional configuration required

### Plug-and-Play Building Blocks

- **Sources**: Local files, Amazon S3, Google Cloud Storage, Azure Blob Storage, Google Drive, HackerNews (custom), HTTP APIs
- **Targets**: PostgreSQL (with pgvector), Qdrant, LanceDB, Neo4j (knowledge graphs), custom file outputs
- **Functions**: SentenceTransformer embeddings, CLIP image embeddings, LLM extraction, text splitting, PDF parsing
- Standardized interface: switch between components with one-line code changes

### Performance

- Core engine written in Rust for ultra-high throughput
- Production-ready at day zero
- Designed for large-scale AI indexing workloads

### Developer Experience

- Python API with ~100 lines to define complex indexing flows
- Claude Code plugin available (`cocoindex-skills@cocoindex`)
- 25+ ready-to-use examples covering common AI indexing patterns
- Active Discord community and YouTube tutorials

---

## Technical Architecture

<eg>
Data Sources          CocoIndex Dataflow Engine              Targets
────────────────────────────────────────────────────────────────────

┌──────────────┐     add_source()    ┌─────────────────────────┐
│ Local Files  ├────────────────────▶│                         │
└──────────────┘                     │   DataScope / Fields    │
┌──────────────┐                     │  ┌───────────────────┐  │    ┌─────────────┐
│ S3 / GCS /   ├────────────────────▶│  │  field = source   │  │    │ PostgreSQL  │
│ Azure Blob   │                     │  │  field.transform()│  │───▶│ (pgvector)  │
└──────────────┘                     │  │  field.transform()│  │    └─────────────┘
┌──────────────┐                     │  │  collector.collect│  │    ┌─────────────┐
│ Google Drive ├────────────────────▶│  └───────────────────┘  │───▶│   Qdrant    │
└──────────────┘                     │                         │    └─────────────┘
┌──────────────┐                     │   Incremental State     │    ┌─────────────┐
│ Custom APIs  ├────────────────────▶│   (Postgres-backed)     │───▶│  LanceDB    │
└──────────────┘                     │                         │    └─────────────┘
                                     │   Rust Core Engine      │    ┌─────────────┐
                                     │   (high performance)    │───▶│  Neo4j /    │
                                     └─────────────────────────┘    │ Graph DBs   │
                                                                     └─────────────┘
</eg>

**Flow definition pattern**:

1. `flow_builder.add_source(...)` — declare data source
2. `.transform(...)` chaining — define transformation functions
3. `collector.collect(...)` — gather fields into output
4. `collector.export(...)` — write to target store

---

## Installation & Usage

### Installation

```bash
# Install CocoIndex
pip install -U cocoindex

# Install Postgres (required for incremental processing)
# See: https://cocoindex.io/docs/getting_started/installation#-install-postgres

# Optional: Claude Code plugin
# /plugin marketplace add cocoindex-io/cocoindex-claude
# /plugin install cocoindex-skills@cocoindex
```

### Minimal Vector Index Flow

```python
import cocoindex


@cocoindex.flow_def(name="TextEmbedding")
def text_embedding_flow(flow_builder: cocoindex.FlowBuilder, data_scope: cocoindex.DataScope):
    # 1. Add a data source
    data_scope["documents"] = flow_builder.add_source(cocoindex.sources.LocalFile(path="markdown_files"))

    # 2. Add a collector for vector index output
    doc_embeddings = data_scope.add_collector()

    # 3. Define transformations per row
    with data_scope["documents"].row() as doc:
        # Split into chunks
        doc["chunks"] = doc["content"].transform(
            cocoindex.functions.SplitRecursively(), language="markdown", chunk_size=2000, chunk_overlap=500
        )
        with doc["chunks"].row() as chunk:
            # Embed each chunk
            chunk["embedding"] = chunk["text"].transform(
                cocoindex.functions.SentenceTransformerEmbed(model="sentence-transformers/all-MiniLM-L6-v2")
            )
            doc_embeddings.collect(
                filename=doc["filename"], location=chunk["location"], text=chunk["text"], embedding=chunk["embedding"]
            )

    # 4. Export to Postgres vector index
    doc_embeddings.export(
        "doc_embeddings",
        cocoindex.targets.Postgres(),
        primary_key_fields=["filename", "location"],
        vector_indexes=[
            cocoindex.VectorIndexDef(field_name="embedding", metric=cocoindex.VectorSimilarityMetric.COSINE_SIMILARITY)
        ],
    )
```

---

## Relevance to Claude Code Development

### Applications

- **RAG Pipeline Construction**: CocoIndex provides a production-grade framework for building and maintaining the data ingestion pipelines that feed RAG systems used by Claude Code skills
- **Knowledge Graph Building**: The `meeting_notes_graph` and `docs_to_knowledge_graph` examples show patterns for extracting structured relationships from documents — directly applicable to codebase intelligence skills
- **Incremental Context Updates**: The incremental processing model means code context indexes stay fresh without full re-indexing on every file change
- **Multi-modal Indexing**: PDF, image, and code embedding support enables rich context for AI coding assistants

### Patterns Worth Adopting

- **Dataflow Programming**: Declaring transformations as pure field mappings (no hidden state) makes pipelines testable, observable, and reproducible — a pattern applicable to Claude Code skill design
- **Collector/Export Separation**: Decoupling data collection from export target enables flexible output routing without changing transformation logic
- **Incremental-First Design**: Building systems that track what has changed and only reprocess deltas rather than full re-runs from scratch
- **Component Standardisation**: Single-interface swap for sources/targets/functions makes pipelines highly composable

### Integration Opportunities

- **Codebase Indexing Skill**: Build a Claude Code skill that uses CocoIndex to maintain an up-to-date vector index of a codebase with incremental updates on file changes
- **Research Directory Indexing**: Use CocoIndex to index the `./research/` directory and enable semantic search over research entries
- **Document Processing Pipeline**: Combine CocoIndex PDF parsing and LLM extraction with Claude's capabilities for automated documentation processing
- **MCP Data Layer**: CocoIndex can serve as the live data transformation layer feeding an MCP server that provides Claude with fresh, contextualised data

### Competitive Analysis

| Framework | Incremental | Lineage | Rust Core | AI-Native |
|-----------|-------------|---------|-----------|-----------|
| CocoIndex | ✅ Native | ✅ Auto | ✅ Yes | ✅ Yes |
| LangChain | ❌ Manual | ❌ No | ❌ No | ✅ Yes |
| Haystack | ⚠️ Partial | ❌ No | ❌ No | ✅ Yes |
| Tinybird | ✅ Yes | ⚠️ SQL | ❌ No | ✅ MCP |
| dbt | ⚠️ Partial | ✅ Yes | ❌ No | ❌ No |

---

## References

- [GitHub Repository](https://github.com/cocoindex-io/cocoindex) (accessed 2026-02-23)
- [Official Documentation](https://cocoindex.io/docs) (accessed 2026-02-23)
- [Quickstart Guide](https://cocoindex.io/docs/getting_started/quickstart) (accessed 2026-02-23)
- [PyPI Package](https://pypi.org/project/cocoindex/) (accessed 2026-02-23)
- [Quick Start Video Tutorial](https://youtu.be/gv5R8nOXsWU) (accessed 2026-02-23)
- [Discord Community](https://discord.com/invite/zpA9S2DR7s) (accessed 2026-02-23)
- [CocoIndex Claude Plugin](https://github.com/cocoindex-io/cocoindex-claude) (accessed 2026-02-23)

---
