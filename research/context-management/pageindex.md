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
  confidence_map: "Overview: high, Problem Addressed: high, Key Features: high, Technical Architecture: medium (doc + code-read), Installation & Usage: high, Limitations: medium, Relevance to Claude Code Development: medium"
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

**LocalAPI** (Source: pageindex/local_api.py — class LocalAPI) — Backs `PageIndexClient`'s local mode. Manages indexing and retrieval workflows on the client's machine, handling document submission, tree generation, and LLM-driven tree search.

**DocStore** (Source: pageindex/local_store.py — class DocStore) — Persistent local storage layer for indexed documents and their tree structures, using the filesystem for document and tree data.

**PageIndex Flash** (Source: pageindex/flash/api.py — page_index_flash()) — LLM-free tree extraction from PDF layout statistics. Analyzes PDF structure (text positioning, font sizes, spacing) to generate hierarchical tree indices without LLM API calls.

**CloudAPI** (Source: pageindex/cloud_api.py — class CloudAPI) — Handles communication with PageIndex Cloud for managed indexing and retrieval when `index="cloud"` is configured.

### Indexing Flow

1. **PDF Parsing**: Document submitted via `client.submit_document(file_path)` returns a `doc_id`. In local mode the submitted file must have a `.pdf` name; any other extension raises `PageIndexAPIError` ("only PDF files are supported in local mode"). (Source: pageindex/local_api.py — class LocalAPI)
2. **Tree Generation**:
   - Local mode: PageIndex Flash extracts layout-based structure, or LLM-driven indexing with the configured `index` model summarizes and refines nodes
   - Cloud mode: PageIndex Cloud handles parsing, OCR, and tree construction
3. **Storage**: Tree indices stored in `DocStore` (local) or PageIndex Cloud (managed)

### Retrieval Flow

1. **Query Submission**: `client.chat(question, doc_id=doc_id)` initiates retrieval. The `doc_id` parameter is typed `Optional[Union[str, list[str]]]`, so a list of document IDs is accepted. (Source: pageindex/client.py — class PageIndexClient, method `chat`)
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

- **Index model**: The README states: "`index=`: a basic model is sufficient. The tree structure itself is extracted from the document layout without an LLM; the index model only summarizes and refines it, which a basic model does well." (Source: README.md, accessed 2026-10-02)
- **Chat model**: The README states: "`chat=`: use the best model you can afford. The chat model searches the tree to retrieve information." (Source: README.md, accessed 2026-10-02)

### Agent SDK Integration

PageIndex can be integrated as tools into OpenAI Agents SDK, Claude Agent SDK, and Anthropic SDKs:

```python
from pageindex.integrations.openai_agents import get_pageindex_tools

tools = get_pageindex_tools(client=pageindex_client)
```

---

## Limitations and Caveats

- **Local mode OCR**: PageIndex local mode handles text-based PDFs. For scanned documents or images, PageIndex Cloud with OCR is required. (Source: official documentation, accessed 2026-10-02)
- **Chat model choice**: The README directs users to "use the best model you can afford" for `chat=` because that model searches the tree. Measured failure rates for weaker chat models: not mentioned in documentation. (Source: README.md, accessed 2026-10-02)
- **Citation granularity tradeoff**: Local mode provides page-level citations; cloud mode provides block-level citations with more precise location information. (Source: documentation, accessed 2026-10-02)
- **Flash indexing can refuse a document**: `flash_rejection_reason` returns a refusal when a PDF has no text layer ("scanned or image-only; run OCR before indexing it"), when a document of more than `FLAT_TREE_MAX_NODES` pages has no layout structure, or when no structure can be extracted; the latter two messages direct the caller to `mode='standard'`, "which builds the structure with the model". (Source: pageindex/flash/api.py — flash_rejection_reason())
- **Multi-document reasoning**: The README lists "multi-document search" among SDK-configurable features, and `chat` accepts a list of `doc_id` values. Whether cross-document relationships are modeled structurally: not mentioned in documentation. (Source: README.md, accessed 2026-10-02; pageindex/client.py — class PageIndexClient, method `chat`)
- **Markdown input**: In local mode `submit_document` accepts only `.pdf` files. A separate function, `md_to_tree(md_path, ...)`, exists in `pageindex/page_index_md.py`; the `chat` and `submit_document` documentation does not describe it as a path into the client. (Source: pageindex/local_api.py — class LocalAPI, pageindex/page_index_md.py — md_to_tree())

---

## Relevance to Claude Code Development

### Applications

- **Research entry assessment in `research-utilization-assessor`** -> `.claude/agents/research-utilization-assessor.md`
  - Term: `utilization`
  - Today: "Assess utilization opportunities from ./research/{category}/{name}.md"
  - Change: none — out of scope (the agent's input is a Markdown research entry, `./research/{category}/{name}.md`; PageIndex local mode rejects non-PDF files in `submit_document` (pageindex/local_api.py — class LocalAPI), and no failure of this agent on entry length is recorded in `research/insights/2026-10-02-pageindex-improvements.md`)

- **Research entry processing in `research-insight-extractor`** -> `.claude/agents/research-insight-extractor.md`
  - Term: `research entry`
  - Today: "Takes one completed research entry and produces concrete, measurable improvement proposals for this repo's skills, agents, and workflows."
  - Change: none — out of scope (the agent processes one Markdown entry per run, which it reads directly; PageIndex local mode accepts only PDF files, and the README lists multi-document search without describing cross-document relationship modeling)

### Integration Opportunities

- **PageIndex SDK as MCP tools (`index_document`, `query_index`) for PDF sources** -> `docs/MCP-INDEX.md`
  - Term: `Model Context Protocol`
  - Today: "Complete documentation for adding Model Context Protocol (MCP) servers to claude_skills plugins."
  - Change: Do not add a standalone PageIndex MCP server for Markdown: R1 of `plugins/development-harness/docs/agent-markdown-consumption-contract.md` ("A single markdown engine serves every markdown consumption path") already assigns Markdown tree navigation to the `progressive_markdown` engine, and PageIndex local mode takes only PDFs. A PageIndex-backed wrapper is only justified for PDF sources, and then as a provider feeding that engine (`plugins/development-harness/progressive_markdown/providers.py`) rather than as a parallel server.

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
