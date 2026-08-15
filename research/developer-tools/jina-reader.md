---
title: "Jina Reader"
research_date: "2026-02-23"
source_url: "https://jina.ai/reader"
github_url: "https://github.com/jina-ai/reader"
version_at_research: "Not versioned (continuously deployed from main branch)"
license: "Apache 2.0"
last_verified: "2026-02-23"
version_at_verification: "Continuously deployed (no versioning)"
next_review: "2026-05-23"
---

## Overview

Jina Reader is an open-source API service that converts any URL or web search query into clean, LLM-friendly Markdown output. Accessed via a URL prefix (`r.jina.ai/<url>`) or search prefix (`s.jina.ai/<query>`), it requires zero installation and no API key for basic use. The single codebase backing the hosted API is powered by Puppeteer and headless Chrome, enabling full JavaScript/SPA rendering before extraction, and is continuously deployed from the GitHub repository to the `r.jina.ai` endpoint.

---

## Problem Addressed

| Problem | Solution |
| ------- | -------- |
| LLMs cannot process raw HTML directly | Reader converts any URL to clean Markdown with a single `curl` or prefix URL call |
| JavaScript-heavy SPAs are inaccessible to simple scrapers | Puppeteer + headless Chrome renders full SPA content before extraction |
| Web search results return only title/URL/snippet | `s.jina.ai` fetches and extracts full content from the top 5 search result pages |
| PDFs embedded in web pages are not readable by LLMs | Reader renders and extracts text from arbitrary PDF URLs |
| Images in pages lack text descriptions for LLMs | VLM-powered image captioning adds `Image [idx]: [caption]` alt tags on demand |
| Streaming pages return incomplete content | Streaming mode (`Accept: text/event-stream`) waits for stable page render |
| Cached content may be stale for time-sensitive queries | `x-no-cache: true` header bypasses the 1-hour page cache |

---

## Key Statistics

| Metric | Value | Date Gathered |
| ------ | ----- | ------------- |
| GitHub Stars | ~9,800 | 2026-02-23 |
| GitHub Forks | ~756 | 2026-02-23 |
| License | Apache 2.0 | 2026-02-23 |
| Deployment model | Continuously deployed from main | 2026-02-23 |
| Search results returned | Top 5 per query | 2026-02-23 |
| Page cache lifetime | 3,600 seconds (1 hour) | 2026-02-23 |

---

## Key Features

### Read Mode (`r.jina.ai`)

- **Zero-setup URL to Markdown**: Prefix any URL with `https://r.jina.ai/` — no install, no API key for basic use
- **SPA support**: Full JavaScript rendering via Puppeteer + headless Chrome handles React, Vue, Angular apps
- **PDF extraction**: Reads and converts arbitrary PDFs from any URL (e.g., `r.jina.ai/https://nasa.gov/...pdf`)
- **Streaming mode**: Send `Accept: text/event-stream` to receive progressively more complete content chunks
- **JSON mode**: Send `Accept: application/json` for structured `{url, title, content}` response

### Search Mode (`s.jina.ai`)

- **Grounded web search**: Prepend `https://s.jina.ai/` to a query; retrieves and fully extracts the top 5 result pages
- **In-site search**: Restrict results to specific domains with `?site=domain.com` query parameter
- **JSON search results**: Returns list of 5 `{title, content, url}` objects in JSON mode

### Request Header Controls

- `x-with-generated-alt: true` — VLM-generated captions for all images lacking alt tags
- `x-respond-with: markdown|html|text|screenshot` — bypass readability filtering for raw output
- `x-target-selector: <CSS>` — extract only content matching a CSS selector
- `x-wait-for-selector: <CSS>` — wait until a specific DOM element appears before extraction
- `x-timeout: <seconds>` — override default page load timeout
- `x-no-cache: true` / `x-cache-tolerance: <seconds>` — cache control
- `x-proxy-url: <url>` — route requests through a custom proxy
- `x-set-cookie: <value>` — forward cookies to the target page (bypasses cache)

### Deployment and Architecture

- **Live codebase**: The repository IS the production service; every commit to main is deployed to `r.jina.ai`
- **Open source (Apache 2.0)**: Fully auditable and self-hostable
- **Internal submodule**: `thinapps-shared` handles decorators, logging, and secrets management (not open-sourced but not required for core function)

---

## Technical Architecture

<eg>
User Request
    |
    +-- r.jina.ai/<url>
    |       |
    |       +-- Puppeteer + headless Chrome
    |       |   (renders JS, waits for DOM, handles SPAs)
    |       |
    |       +-- Readability filter  (or bypass via x-respond-with)
    |       |
    |       +-- Optional: VLM image captioning
    |       |
    |       +-- Output: Markdown / HTML / text / JSON / screenshot
    |
    +-- s.jina.ai/<query>
            |
            +-- Web search → top 5 URLs
            |
            +-- r.jina.ai applied to each URL in parallel
            |
            +-- Output: 5× {title, content, url}  (Markdown or JSON)
</eg>

### Streaming Chunk Model

<eg>
Reader:    chunk1 ──────> chunk2 ──────> chunk3 (most complete)
                 |               |              |
                 v               v              v
LLM:       process(chunk1)  process(chunk2)  process(chunk3)
</eg>

Each subsequent streaming chunk contains more complete content than the previous one; the final chunk is authoritative.

---

## Installation & Usage

### Read — no installation required

```bash
# Basic URL to Markdown (no API key)
curl https://r.jina.ai/https://example.com

# SPA or slow page with explicit timeout
curl -H 'x-timeout: 30' https://r.jina.ai/https://example.com

# Wait for specific DOM element
curl -H 'x-wait-for-selector: #main-content' https://r.jina.ai/https://example.com

# Extract only a specific section
curl -H 'x-target-selector: article.post-body' https://r.jina.ai/https://example.com

# JSON output
curl -H 'Accept: application/json' https://r.jina.ai/https://example.com

# Streaming mode (most complete result)
curl -H 'Accept: text/event-stream' https://r.jina.ai/https://example.com

# With API key for higher rate limits
curl -H 'Authorization: Bearer <YOUR_JINA_API_KEY>' https://r.jina.ai/https://example.com

# SPA with hash routing (POST method)
curl -X POST 'https://r.jina.ai/' -d 'url=https://example.com/#/route'
```

### Search — no installation required

```bash
# Web search → full content from top 5 results
curl 'https://s.jina.ai/What%20is%20Claude%20Code%3F'

# In-site search
curl 'https://s.jina.ai/reader+api?site=jina.ai'

# JSON output (5 results)
curl -H 'Accept: application/json' 'https://s.jina.ai/What%20is%20Claude%20Code%3F'
```

### Python integration

```python
import httpx

# Read a URL
response = httpx.get(f"https://r.jina.ai/{url}", headers={"Authorization": "Bearer <YOUR_JINA_API_KEY>"})
markdown_content = response.text

# Search the web
response = httpx.get(
    "https://s.jina.ai/claude+code+plugins",
    headers={"Accept": "application/json", "Authorization": "Bearer <YOUR_JINA_API_KEY>"},
)
results = response.json()  # list of {title, content, url}
```

---

## Relevance to Claude Code Development

### Applications

- **`research-curator` skill**: Use `r.jina.ai/<url>` instead of `WebFetch` for guaranteed clean Markdown extraction from source URLs during research entry creation
- **Agent web grounding**: Agents that need to verify facts or read documentation can use `r.jina.ai/<url>` as a single-line web reader with no library dependencies
- **Search-augmented skills**: Any skill requiring live web knowledge can use `s.jina.ai/<query>` for full-content grounded search results (vs. title/snippet from search APIs)

### Patterns Worth Adopting

- **URL prefix pattern**: The `r.jina.ai/` prefix idiom is the lowest-friction possible web content integration — a single URL substitution, no client library, no API key for basic usage
- **Streaming for completeness**: Using `Accept: text/event-stream` and taking the final chunk ensures maximum content extraction for dynamically loaded pages
- **CSS selector targeting**: `x-target-selector` provides surgical extraction when full-page content includes noise (navigation, footers, ads)

### Integration Opportunities

- **Replace `WebFetch` in skills**: Reader provides more reliable Markdown output than raw `WebFetch` for complex or JS-rendered pages
- **MCP tool wrapper**: A lightweight MCP server wrapping `r.jina.ai` and `s.jina.ai` would give Claude Code a dedicated, reliable web reading tool
- **Pre-processing pipeline**: Pipe Reader output through Jina's reranker to score relevance of extracted sections before injecting into context

---

## References

- [jina-ai/reader GitHub Repository](https://github.com/jina-ai/reader) (accessed 2026-02-23)
- [Jina Reader Live Demo](https://jina.ai/reader#demo) (accessed 2026-02-23)
- [Jina Reader API Builder](https://jina.ai/reader#apiform) (accessed 2026-02-23)
- [Jina Reader Rate Limits / Pricing](https://jina.ai/reader#pricing) (accessed 2026-02-23)
- [Jina Reader for Search Grounding Blog Post](https://jina.ai/news/jina-reader-for-search-grounding-to-improve-factuality-of-llms) (accessed 2026-02-23)
- [Apache-2.0 License](https://github.com/jina-ai/reader/blob/main/LICENSE) (accessed 2026-02-23)

---
