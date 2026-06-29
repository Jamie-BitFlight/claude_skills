---
title: "Jina AI"
research_date: "2026-02-23"
source_url: "https://jina.ai"
github_url: "https://github.com/jina-ai"
documentation_url: "https://jina.ai/reader>, <https://jina.ai/embeddings"
version_at_research: "jina-embeddings-v4 (models), Reader API v1"
license: "Apache 2.0 (Reader/infrastructure); CC BY-NC 4.0 (jina-embeddings-v3); Qwen Research License (jina-embeddings-v4)"
last_verified: "2026-02-23"
version_at_verification: "jina-embeddings-v4, Reader API v1"
next_review: "2026-05-23"
---

## Overview

Jina AI is a search foundation platform providing best-in-class multimodal and multilingual embeddings, rerankers, and a URL-to-Markdown Reader API for building RAG and agentic AI systems. Founded in 2020 and acquired by Elastic in October 2025, Jina AI exposes all its models via REST APIs and open-source repositories, making high-quality semantic retrieval accessible to developers without GPU infrastructure. Its Reader API (`r.jina.ai/<url>`) converts any web page or PDF into clean Markdown in a single HTTP request, making it a widely adopted tool for LLM context enrichment.

---

## Problem Addressed

| Problem | Solution |
| ------- | -------- |
| LLMs cannot directly ingest raw HTML/PDFs | Reader API converts any URL or PDF to clean LLM-ready Markdown via a simple prefix |
| Semantic search across multilingual content is difficult | jina-embeddings-v3/v4 support 89+ languages with context windows up to 8,192 tokens |
| RAG retrieval quality degrades with large candidate sets | Reranker API (jina-reranker-m0) reorders candidates by relevance with multimodal/long-context support |
| Building neural search requires GPU infrastructure | All models exposed via hosted REST APIs with free tier and API key rate limits |
| Iterative research requires multiple search and read loops | DeepSearch agentic engine orchestrates embeddings, rerankers, and LMs for multi-hop answers |
| Embedding storage is costly for large corpora | Matryoshka Representation Learning (MRL) allows truncating vector dimensions without retraining |

---

## Key Statistics

| Metric | Value | Date Gathered |
| ------ | ----- | ------------- |
| jina-ai/jina GitHub Stars | ~21,800 | 2026-02-23 |
| jina-ai/reader GitHub Stars | ~9,800 | 2026-02-23 |
| jina-ai/reader GitHub Forks | ~756 | 2026-02-23 |
| Languages supported (embeddings) | 89+ | 2026-02-23 |
| Reader API max context window | 8,192 tokens | 2026-02-23 |
| Embedding model context window | 8,192 tokens | 2026-02-23 |
| Founded | 2020 | 2026-02-23 |
| Acquired by Elastic | October 2025 | 2026-02-23 |

---

## Key Features

### Reader API

- **Zero-setup web content extraction**: Prefix any URL with `r.jina.ai/` to receive clean Markdown; no API key needed for basic usage
- **Search grounding**: `s.jina.ai/<query>` performs live web search and returns LLM-ready results
- **PDF support**: Renders and extracts text from PDF files as well as HTML pages
- **Browser-grade rendering**: Uses headless browser engine to handle JavaScript-heavy pages
- **ReaderLM-v2**: Optional small language model backend for HTML-to-Markdown/JSON conversion (ICLR 2025); excels on complex page structures
- **Configurable extraction**: CSS selectors for extract-only, wait-for, and exclude filters
- **Streaming mode**: Stream large page content for progressive ingestion

### Embeddings API

- **jina-embeddings-v3**: Multilingual text embeddings with 89+ languages, 8,192-token context window, task-specific LoRA adapters
- **jina-embeddings-v4**: Latest multimodal model supporting text and images; Qwen-based architecture
- **Matryoshka Representation Learning**: Truncatable vector dimensions for storage efficiency without quality loss
- **Hugging Face integration**: Models available on HF Hub for local inference
- **OpenAI-compatible API**: Drop-in replacement for OpenAI embeddings endpoint

### Reranker API

- **jina-reranker-m0**: Multilingual, multimodal document reranker released April 2025; state-of-the-art on retrieval benchmarks
- **Long-context support**: Handles long documents beyond typical 512-token cross-encoder limits
- **Multimodal**: Reranks text-image mixed result sets

### DeepSearch

- **Agentic retrieval**: Iteratively searches, reads, and reasons over results to answer complex questions
- **Multi-model orchestration**: Combines Reader, embeddings, and rerankers in a single search pipeline
- **Open source**: Available as an open-source project

---

## Technical Architecture

<eg>
User Query
    |
    +-- Reader API  ──────────── r.jina.ai/<URL>  →  Clean Markdown
    |                            s.jina.ai/<query> →  Search Results (Markdown)
    |
    +-- Embeddings API  ─────── api.jina.ai/v1/embeddings  →  Dense Vectors
    |                           (text / image / multimodal)
    |
    +-- Reranker API  ──────────  api.jina.ai/v1/rerank  →  Reordered Candidates
    |
    +-- DeepSearch  ─────────── Orchestrates: Reader + Embeddings + Rerankers
                                Iterative multi-hop reasoning loop
</eg>

### API Surface

| Endpoint | Function | Auth |
| -------- | -------- | ---- |
| `r.jina.ai/<url>` | URL → Markdown | Optional API key for higher rate limits |
| `s.jina.ai/<query>` | Web search → Markdown results | Optional API key |
| `api.jina.ai/v1/embeddings` | Text/image → vectors | API key required |
| `api.jina.ai/v1/rerank` | Candidate list → reordered list | API key required |

---

## Installation & Usage

### Reader API (no installation required)

```bash
# Convert any URL to Markdown
curl https://r.jina.ai/https://example.com

# With API key for higher rate limits
curl https://r.jina.ai/https://example.com \
  -H "Authorization: Bearer <YOUR_JINA_API_KEY>"

# Web search
curl https://s.jina.ai/what+is+claude+code
```

### Embeddings API

```bash
curl https://api.jina.ai/v1/embeddings \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <YOUR_JINA_API_KEY>" \
  -d '{
    "normalized": true,
    "embedding_type": "float",
    "model": "jina-embeddings-v3",
    "input": ["Your text here"]
  }'
```

```python
from openai import OpenAI

client = OpenAI(
    api_key="<YOUR_JINA_API_KEY>",
    base_url="https://api.jina.ai/v1"
)

response = client.embeddings.create(
    model="jina-embeddings-v3",
    input=["Your text here"]
)
```

### Reranker API

```bash
curl https://api.jina.ai/v1/rerank \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <YOUR_JINA_API_KEY>" \
  -d '{
    "model": "jina-reranker-m0",
    "query": "What is Claude Code?",
    "documents": ["doc1 text", "doc2 text", "doc3 text"]
  }'
```

---

## Relevance to Claude Code Development

### Applications

- **Web context enrichment**: Use `r.jina.ai/<url>` to fetch clean Markdown from any URL inside a skill or agent, providing grounded web content to Claude without browser automation
- **RAG pipelines**: Jina embeddings + reranker combination provides a turnkey retrieval stack for augmenting Claude with document corpora
- **Research curation**: Reader API is directly applicable to the `research-curator` skill for converting source URLs to structured Markdown

### Patterns Worth Adopting

- **URL prefix pattern**: The `r.jina.ai/` prefix idiom is an extremely low-friction way to integrate web reading into any workflow — no library import or setup required
- **Two-stage retrieval**: Embed → shortlist → rerank is a proven pattern for high-quality RAG that Jina makes easy with its API surface
- **Matryoshka embeddings**: Dimension-truncatable vectors allow trading quality for storage cost at query time, not training time

### Integration Opportunities

- **`research-curator` skill**: Replace manual web scraping with `r.jina.ai/<url>` calls for consistent Markdown extraction when gathering research data
- **MCP server**: A Jina MCP server could expose Reader, Embeddings, and Reranker as tools callable by Claude directly
- **Context management plugin**: Pair Jina embeddings with a local vector store (Qdrant, LanceDB) for a self-hosted semantic memory layer

### Competitive Analysis

| Tool | Embeddings | Web Reader | Reranker | Agentic Search | Self-hosted |
| ---- | ---------- | ---------- | -------- | -------------- | ----------- |
| Jina AI | ✅ (multilingual, v3/v4) | ✅ (r.jina.ai) | ✅ (m0) | ✅ (DeepSearch) | Partial (HF models) |
| OpenAI | ✅ (text-embedding-3) | ❌ | ❌ | ✅ (Responses API) | ❌ |
| Cohere | ✅ (embed-v3) | ❌ | ✅ (rerank-v3) | ❌ | ❌ |
| Voyage AI | ✅ | ❌ | ✅ | ❌ | ❌ |

---

## References

- [Jina AI Official Website](https://jina.ai) (accessed 2026-02-23)
- [jina-ai/reader GitHub Repository](https://github.com/jina-ai/reader) (accessed 2026-02-23)
- [jina-ai/jina GitHub Repository](https://github.com/jina-ai/jina) (accessed 2026-02-23)
- [Jina Embeddings API Documentation](https://jina.ai/embeddings/) (accessed 2026-02-23)
- [jina-embeddings-v3 on Hugging Face](https://huggingface.co/jinaai/jina-embeddings-v3) (accessed 2026-02-23)
- [jina-embeddings-v4 on Hugging Face](https://huggingface.co/jinaai/jina-embeddings-v4) (accessed 2026-02-23)
- [Elastic Completes Acquisition of Jina AI](https://ir.elastic.co/news/news-details/2025/Elastic-Completes-Acquisition-of-Jina-AI-a-Leader-in-Frontier-Models-for-Multimodal-and-Multilingual-Search/default.aspx) (accessed 2026-02-23)
- [ReaderLM-v2 Blog Post](https://jina.ai/news/readerlm-v2-frontier-small-language-model-for-html-to-markdown-and-json) (accessed 2026-02-23)

---
