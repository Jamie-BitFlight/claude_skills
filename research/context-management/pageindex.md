---
name: pageindex
title: PageIndex
subtitle: Reasoning-based vectorless RAG with hierarchical tree index
research_date: 2026-10-02
source_url: https://github.com/VectifyAI/PageIndex
github_repository: https://github.com/VectifyAI/PageIndex
version_at_research: 0.2.10
license: MIT
freshness_tracking:
  last_verified: 2026-10-02
  version_at_verification: 0.2.10
  next_review: 2027-01-02
  confidence_map: "Overview: high, Problem Addressed: high, Key Features: high, Technical Architecture: high (doc + code-read), Installation & Usage: high, Limitations: medium"
---

# PageIndex

## Overview

PageIndex is a vectorless, reasoning-based RAG (Retrieval-Augmented Generation) engine that replaces traditional vector-based retrieval with hierarchical tree indexing and LLM reasoning. Instead of semantic similarity search, PageIndex lets an LLM reason its way through a document's structure to find relevant information, mirroring how human experts read complex documents. It delivers traceable, explainable, context-aware retrieval with no vector databases or document chunking required.

The Python SDK supports both local mode (on-machine indexing with your own LLM keys) and cloud mode (managed indexing and storage via PageIndex Cloud), with integrations available for OpenAI Agents SDK, Claude Agent SDK, and Anthropic SDKs.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Vector RAG retrieves by semantic similarity, not relevance | PageIndex uses LLM reasoning over document structure to find actually relevant information, not just similar-sounding text |
| Long documents exceed context windows when passed natively | PageIndex's tree retrieval only reads the nodes its reasoning reaches, costing 2.1–16.6× less than native PDF input depending on document length |
| Vector retrieval is opaque ("vibe retrieval") | PageIndex returns traceable results explicitly cited to specific pages and blocks within documents |
| Document chunking loses structural context | Tree indexing preserves document hierarchy, letting the LLM reason about layout, sections, and relationships |
| Vector indices require external infrastructure | PageIndex local mode indexes and retrieves entirely on-machine with just an LLM API key |

---

## Key Features

### Reasoning-Based Retrieval

- Uses LLM reasoning to search a hierarchical tree index instead of semantic similarity search
- Retrieved results are traceable to explicit page numbers and block IDs
- Context-aware: incorporates conversation history and domain knowledge in retrieval decisions, not just query embedding

### Local and Cloud Modes

- **Local mode**: Index, retrieve, and chat entirely on your machine with your own LLM key (`pip install -U pageindex`)
- **Cloud mode**: Offload indexing and storage to managed PageIndex Cloud, which handles OCR, image understanding, and metadata
- Both modes use the same SDK client; switching requires only changing the `index="cloud"` parameter

### PageIndex Flash Indexing

- Fast tree index generation for text-based PDFs using layout statistics, not LLM processing
- Default indexing method in PageIndex SDK local mode as of August 2026
- Reduces indexing cost to approximately $0.001 per page using basic models like gpt-5.6-luna

### Integration with Agent SDKs

- Tools available for OpenAI Agents SDK, Claude Agent SDK, and Anthropic SDKs
- MCP server support for integration with other frameworks
- Supports multi-document search and citations with configurable citation granularity (page-level in local mode, block-level in cloud)

### Cost Efficiency

- Indexing: ~$0.001 per page; a 1,000-page document costs ~$1 to index once
- Querying: Native PDF input costs 2.1× more at 52 pages, 16.6× more at 420 pages
- Indexing time scales linearly: 13 seconds for 9 pages, 4.5 minutes for 1,098 pages

### Benchmark Performance

- Achieved 98.7% accuracy on FinanceBench (financial document QA benchmark), vastly outperforming vector-based RAG (~50%)
- Benchmark evaluated on 62 questions over 34 PDFs (1,945 pages) where answers are facts stated in running text
- Accuracy scales with model choice: higher-capability models significantly improve retrieval accuracy

---

## Technical Architecture

### Core Components

**PageIndexClient** — Main SDK entry point supporting three operational modes via constructor parameters:
- `index`: controls indexing strategy (`"gpt-5.6-luna"`, other model names for local mode; `"cloud"` for cloud mode)
- `chat`: specifies the model for searching the tree (`"gpt-5.6-sol"`, OpenAI/Anthropic/Claude model identifiers, or `"litellm/{provider}/{model}"`)

**LocalAPI** (Source: pageindex/local_api.py) — Backs `PageIndexClient`'s local mode. Manages indexing and retrieval workflows on the client's machine, handling document submission, tree generation, and LLM-driven tree search.

**DocStore** (referenced in LocalAPI) — Persistent local storage layer for indexed documents and their tree structures, using the filesystem for document and tree data.

**PageIndex Flash** (Source: pageindex/flash module) — LLM-free tree extraction from PDF layout statistics. Analyzes PDF structure (text positioning, font sizes, spacing) to generate hierarchical tree indices without LLM API calls.

**CloudAPI** — Handles communication with PageIndex Cloud for managed indexing and retrieval when `index="cloud"` is configured.

### Indexing Flow

1. **PDF Parsing**: Document submitted via `client.submit_document(file_path)` returns a `doc_id`
2. **Tree Generation**:
   - Local mode: PageIndex Flash extracts layout-based structure, or LLM-driven indexing with the configured `index` model summarizes and refines nodes
   - Cloud mode: PageIndex Cloud handles parsing, OCR, and tree construction
3. **Storage**: Tree indices stored in `DocStore` (local) or PageIndex Cloud (managed)

### Retrieval Flow

1. **Query Submission**: `client.chat(question, doc_id=doc_id)` initiates retrieval
2. **Tree Search**: Chat model (configured via `chat=`) reasons over the tree structure, selecting which nodes to read
3. **Context Assembly**: Only the nodes the model reached are fetched and assembled into the prompt context
4. **Response Generation**: Model generates answer with citations extracted and deduplicated from tree node metadata

### Citation Handling

- Parses two citation tag formats: legacy `<doc=...;page=...;block=...>` and modern `<cite doc=... page=... block=.../>`
- Deduplicates citations, extracting document ID, page number, and optional block ID
- Returns structured citation list with `{document, page, [block_id]}`

### SDK Dependencies

- **openai** (≥1.70.0): Required for OpenAI model integration
- **mcp** (≥1.19.0, <3): Model Context Protocol for integration with other tools
- **anthropic** (≥0.122.0, optional): For Anthropic Claude model integration
- **claude-agent-sdk** (optional): For Claude Agent SDK integration
- **PyPDF2** (≥3.0.0), **pypdfium2** (≥5): PDF parsing
- **litellm** (≥1.97.0): Multi-provider LLM routing
- **python-dotenv**, **pyyaml**, **Pillow**: Utility dependencies for configuration and image handling

---

## Installation & Usage

### Installation

```bash
pip install -U pageindex
```

### Local Mode: Indexing and Retrieval

```python
import os
from pageindex import PageIndexClient

os.environ["OPENAI_API_KEY"] = "your-openai-key"

# Create client with local indexing and ChatGPT for search
client = PageIndexClient(
    index="gpt-5.6-luna",  # model to build the tree index
    chat="gpt-5.6-sol",  # model to search the tree
)

# Submit document for indexing (returns doc_id immediately; indexing happens asynchronously)
doc_id = client.submit_document("report.pdf")["doc_id"]

# Query the indexed document
answer = client.chat("What was the 2023 operating margin?", doc_id=doc_id)
print(answer)
```

### Cloud Mode: Managed Indexing

```python
import os
from pageindex import PageIndexClient

os.environ["PAGEINDEX_API_KEY"] = "your-pageindex-key"
os.environ["OPENAI_API_KEY"] = "your-openai-key"

# Create client with cloud indexing, local model for search
client = PageIndexClient(
    index="cloud",  # build and store the index in PageIndex Cloud
    chat="gpt-5.6-sol",  # use your preferred model for chat
)

# Submit document (Cloud handles OCR, image understanding)
doc_id = client.submit_document("report.pdf", wait=True)["doc_id"]
answer = client.chat("What was the 2023 operating margin?", doc_id=doc_id)
print(answer)
```

### Model Recommendations

- **Index model**: A basic model is sufficient because the tree structure is extracted from layout without LLM processing (Flash indexing). The index model only summarizes and refines nodes.
- **Chat model**: Use the best model available. The chat model drives tree search and directly affects retrieval accuracy. Cost scales with model capability and document length accessed.

### Agent SDK Integration

PageIndex can be integrated as tools into OpenAI Agents SDK, Claude Agent SDK, and Anthropic SDKs:

```python
from pageindex.integrations.openai_agents import get_pageindex_tools

tools = get_pageindex_tools(client=pageindex_client)
```

---

## Limitations and Caveats

- **Local mode OCR**: PageIndex local mode handles text-based PDFs. For scanned documents or images, PageIndex Cloud with OCR is required. (Source: official documentation, accessed 2026-10-02)
- **Model cost variability**: Retrieval cost and accuracy depend directly on the chat model's capabilities; weaker models may miss relevant sections. (Inferred from SDK architecture: chat model drives tree search and directly affects accuracy.)
- **Citation granularity tradeoff**: Local mode provides page-level citations; cloud mode provides block-level citations with more precise location information. (Source: documentation, accessed 2026-10-02)
- **Indexing not optimized for sparse documents**: Flash indexing works best on documents with clear layout structure; documents with irregular formatting may require the slower LLM-driven indexing path. (Inferred from Flash indexing design: layout-based extraction assumes clear document structure.)
- **Multi-document reasoning**: While PageIndex supports multi-document search, cross-document reasoning connections are not explicitly modeled in the tree structure; reasoning happens at retrieval time only. (Inferred from architecture: tree indices are per-document; multi-doc queries concatenate results without structural cross-references.)

---

## Relevance to Claude Code Development

### Applications

- **Long document analysis in agents** -> `.claude/agents/research-utilization-assessor.md`
  - Term: `research utilization`
  - Today: "Assess whether an existing skill, agent, or workflow in this repo could directly call, depend on, or integrate the tool described in a research entry as an external service, API, or SDK dependency."
  - Change: Integrate PageIndex SDK to enable research-utilization-assessor to analyze long research documents, PDFs, and reference materials by querying indexed trees instead of passing full documents, reducing API cost and context pressure.

- **Document-based agent tools** -> `AGENTS.md`
  - Term: `delegate`
  - Today: "When the user says \"can you\", they mean \"orchestrate this via sub-agents\" — delegate accordingly."
  - Change: PageIndex integrations with Claude Agent SDK (claude-agent-sdk optional dependency) and Anthropic SDK enable agents to retrieve precise, traceable information from long documents without exhausting context, supporting delegation workflows over large reference materials.

- **Research entry processing and multi-document synthesis** -> `.claude/agents/research-insight-extractor.md`
  - Term: `document retrieval`
  - Today: Referenced as part of extracting insights from research entries and creating structured analysis of external tools.
  - Change: PageIndex enables research-insight-extractor to index and query multiple research entries and external documentation simultaneously, identifying patterns and connections across documents that would be expensive or impossible with native PDF input to the model.

### Patterns Worth Adopting

- **Hierarchical information organization** -> `plugins/development-harness/dh_core/ledger_spec.py`
  - Term: `tree structure retrieval`
  - Today: Work ledger defines a state machine and task tracking structure; reading a task requires sequential access through status fields.
  - Change: none — `ledger_spec.py` already models tasks as structured hierarchies; PageIndex's tree reasoning approach could inspire similar reasoning-based navigation patterns when tasks or workflows grow complex.

### Integration Opportunities

- **PageIndex MCP server for long-document retrieval in agent workflows** -> `docs/MCP-INDEX.md`
  - Today: The repo documents MCP architecture and integration patterns (`docs/MCP-INDEX.md`, `docs/mcp-architecture-analysis.md`), and multiple plugins expose MCP servers for specialized tasks. Document analysis is addressed per-skill (e.g., `audit-documentation-drift` for drift detection, `codebase-analyzer` for code understanding) but no unified MCP service exists for general-purpose reasoning-based document indexing and retrieval.
  - Change: Create an MCP server wrapping PageIndex SDK to expose document indexing and retrieval as MCP tools available to any agent in the system. Expose tools for `index_document(file_path, doc_id)`, `query_index(doc_id, question)`, and `get_citations(result)` operations. Allow configuration via PageIndex Cloud API key or local model settings. Agents would use this to retrieve from long reference documents without exhausting context, complementing task-specific analysis skills.

---

## References

- [PageIndex GitHub Repository](https://github.com/VectifyAI/PageIndex) (accessed 2026-10-02)
- [PageIndex Documentation](https://docs.pageindex.ai) (accessed 2026-10-02)
- [PageIndex OSS Benchmark](https://github.com/VectifyAI/PageIndex-OSS-Benchmark) (accessed 2026-10-02)
- [FinanceBench Evaluation Results](https://github.com/VectifyAI/Mafin2.5-FinanceBench) (accessed 2026-10-02)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Samuraizer](../ai-research-tools/samuraizer.md) | ai-research-tools | Full-stack RAG system with semantic search and knowledge graphs |
| [Jina Reader](../context-management/jina-ai.md) | context-management | Search foundation providing Reader API and embeddings for document retrieval pipelines |
| [SourceSync.ai](../context-management/sourcesyncai.md) | context-management | Managed RAG platform with alternative indexing approach (auto-sync vs reasoning-based tree search) |
| [Chroma](../data-infrastructure/chroma.md) | data-infrastructure | Vector database; PageIndex presents vectorless retrieval as alternative to semantic similarity search |
| [Grounded Docs](../mcp-ecosystem/docs-mcp-server.md) | mcp-ecosystem | Local documentation retrieval via MCP; PageIndex extends this pattern with LLM-reasoned tree indexing |
