---
title: "Scrapling"
research_date: "2026-02-26"
source_url: "https://github.com/D4Vinci/Scrapling"
github_url: "https://github.com/D4Vinci/Scrapling"
version_at_research: "v0.4"
license: "BSD-3-Clause"
last_verified: "2026-02-26"
version_at_verification: "v0.4"
next_review: "2026-05-26"
---

## Overview

Scrapling is an adaptive Python web scraping framework that handles everything from single HTTP requests to full-scale concurrent crawls. Its parser learns from website changes and automatically relocates elements when page structure updates, while its fetchers bypass anti-bot systems (including Cloudflare Turnstile) out of the box. It also ships a built-in MCP server that exposes scraping tools directly to Claude and other AI agents, enabling token-efficient data extraction by pre-filtering content with CSS selectors before passing it to the model.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Anti-bot systems block HTTP scraping libraries | `StealthyFetcher` spoofs browser TLS fingerprints, headers, and uses Playwright/Patchright with stealth patches to bypass Cloudflare Turnstile/Interstitial |
| Website redesigns break scrapers by changing element positions | Adaptive element tracking stores element signatures and uses similarity algorithms to relocate them after DOM changes via `auto_save=True` and `adaptive=True` |
| Scaling from one-off requests to full crawls requires switching frameworks | Single library covers `Fetcher` (HTTP), `DynamicFetcher` (browser), `StealthyFetcher` (stealth), and `Spider` (async crawler) in a unified API |
| AI agents waste tokens passing full page HTML | MCP server tools accept CSS selectors to pre-filter content before handing to AI, reducing token consumption |
| BeautifulSoup/lxml are slow for large-scale parsing | Scrapling parser benchmarks at 2.02 ms vs BeautifulSoup4+lxml at 1584 ms for 5000 nested elements |
| Managing proxies across many requests is error-prone | Built-in `ProxyRotator` class with thread-safe cyclic or custom rotation strategies, per-request overrides |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 15,072 | 2026-02-26 |
| GitHub Forks | 988 | 2026-02-26 |
| Contributors | 5 | 2026-02-26 |
| Open Issues | 9 | 2026-02-26 |
| Latest Release | v0.4 | 2026-02-15 |
| Repository Created | 2024-10-13 | 2026-02-26 |
| PyPI Downloads | See pepy.tech/project/scrapling | 2026-02-26 |

SOURCE: [GitHub API](https://api.github.com/repos/D4Vinci/Scrapling) (accessed 2026-02-26)

---

## Key Features

### Spider Framework (v0.4+)

- **Scrapy-like API**: Define spiders with `start_urls`, async `parse` callbacks, `Request`/`Response` objects, and a priority queue — familiar to Scrapy users but with no boilerplate project structure required
- **Concurrent crawling**: Configurable `concurrent_requests` limit, per-domain throttling, and `download_delay`
- **Multi-session routing**: Mix `FetcherSession`, `AsyncStealthySession`, and `AsyncDynamicSession` in a single spider; route requests to specific sessions by ID via `Request(url, sid="stealth")`
- **Pause and resume**: Checkpoint-based persistence — pass `crawldir` to `Spider.start()`, press Ctrl+C to save state, restart to resume
- **Streaming mode**: `async for item in spider.stream()` delivers items with real-time stats as they arrive, ideal for pipelines and long-running crawls
- **Blocked request detection**: Automatic detection and retry of blocked requests with customizable logic
- **Built-in export**: `result.items.to_json()` / `result.items.to_jsonl()` plus full lifecycle hooks (`on_start`, `on_close`, `on_error`, `on_scraped_item`)
- **uvloop support**: Pass `use_uvloop=True` to `spider.start()` for faster async execution

### Fetchers and Session Management

- **`Fetcher` / `FetcherSession`**: Fast HTTP requests via `curl_cffi`; supports browser TLS fingerprint impersonation (`impersonate='chrome'`), HTTP/3, and stealthy headers
- **`DynamicFetcher` / `DynamicSession`**: Full Playwright Chromium/Chrome browser automation; supports `network_idle`, `disable_resources`, `load_dom` controls
- **`StealthyFetcher` / `StealthySession`**: Patchright-based browser with stealth patches and `solve_cloudflare=True` for Cloudflare Turnstile/Interstitial bypass
- **Async variants**: `AsyncFetcher`, `AsyncStealthySession`, `AsyncDynamicSession` for `asyncio`-native workflows
- **Domain blocking**: `blocked_domains` parameter on browser fetchers blocks requests to specific domains and their subdomains
- **Automatic retries**: Browser fetchers retry on failure with configurable `retries` (default: 3) and `retry_delay` (default: 1s)

### Proxy Rotation

- **`ProxyRotator` class**: Thread-safe cyclic rotation across all session types
- **Custom strategies**: Subclass rotation logic for weighted, random, or geo-targeted selection
- **Per-request override**: Pass `proxy=` to any individual `get()` / `fetch()` call to override session proxy for that request

### Adaptive Parsing Engine

- **Smart element tracking**: `auto_save=True` stores element signatures; `adaptive=True` relocates elements using similarity algorithms after page redesigns
- **Multi-paradigm selection**: CSS selectors, XPath, BeautifulSoup-style `find_all()`, text search (`find_by_text()`), regex search
- **DOM navigation**: `.parent`, `.next_sibling`, `.previous_sibling`, `.below_elements()`, `.find_similar()` traversal methods
- **Auto selector generation**: Generate robust CSS/XPath selectors for any element
- **Enhanced text processing**: Built-in regex extraction, cleaning methods, and `orjson`-backed 10x faster JSON serialization
- **Standalone parser**: `from scrapling.parser import Selector` works directly on HTML strings without any fetcher

### MCP Server

- **Six tools**: `get`, `bulk_get`, `fetch`, `bulk_fetch`, `stealthy_fetch`, `bulk_stealthy_fetch`
- **CSS selector pre-filtering**: Pass selectors to narrow content before the AI receives it, reducing token usage compared to passing full page HTML
- **Output formats**: Markdown, HTML, or clean text extraction
- **Anti-bot support**: `stealthy_fetch` handles Cloudflare Turnstile within MCP context
- **Claude Code integration**: Documented setup for both Claude Desktop and Claude Code via `scrapling mcp` CLI entry point

### CLI and Interactive Shell

- **Extract command**: `scrapling extract get <url> output.md --css-selector '#id'` — scrape to file (`.txt`, `.md`, or `.html`) without writing code
- **Interactive IPython shell**: `scrapling shell` — launches shell with Scrapling pre-imported, curl-to-Scrapling conversion, and in-browser result preview
- **Zero-code scraping**: Use directly from the terminal for ad-hoc extraction tasks

### Performance

- **Text extraction**: 2.02 ms vs BeautifulSoup4+lxml at 1,584 ms for 5,000 nested elements (784x faster)
- **Element similarity search**: 2.39 ms vs AutoScraper at 12.45 ms (5.2x faster)
- **92% test coverage**: Full mypy and pyright type checking enforced in CI
- **Lazy loading**: Minimal memory footprint via lazy session initialization and optimized data structures

---

## Technical Architecture

Scrapling is organized into four layers:

<eg>
CLI / MCP Server (scrapling.cli, scrapling.mcp)
        |
Spider Framework (scrapling.spiders)
   - anyio-based async task scheduling
   - SessionManager routes requests to named sessions
   - CheckpointStore serializes state for pause/resume
        |
Fetcher Layer (scrapling.fetchers)
   - Fetcher / FetcherSession  -> curl_cffi (TLS impersonation, HTTP/3)
   - DynamicFetcher / DynamicSession -> Playwright (Chromium/Chrome)
   - StealthyFetcher / StealthySession -> Patchright (stealth browser)
   - ProxyRotator (thread-safe proxy management)
        |
Parser Engine (scrapling.parser)
   - lxml + cssselect for fast DOM parsing
   - Selector / Selectors classes with adaptive tracking
   - orjson for serialization
   - w3lib for HTML entity handling
</eg>

**Adaptive element tracking**: When `auto_save=True` is set on a CSS/XPath query, Scrapling stores the element's structural signature (tag, attributes, position, text fingerprint) in a local database. When `adaptive=True` is passed on a subsequent call, it uses a similarity scoring algorithm over stored signatures to relocate the element even if its selector no longer matches, surviving page redesigns.

**MCP integration**: The `scrapling[ai]` extras install `mcp>=1.24.0` and `markdownify`. The `scrapling mcp` CLI command starts a stdio MCP server exposing the six scraping tools. CSS selector parameters allow scoping extraction to specific DOM nodes before content is serialized to Markdown/HTML/text and returned to the AI.

---

## Installation & Usage

```bash
# Parser only (no fetchers)
pip install scrapling

# With all fetchers (HTTP + browser)
pip install "scrapling[fetchers]"
scrapling install  # downloads Chromium/Chrome and dependencies

# With MCP server
pip install "scrapling[ai]"

# Full install (fetchers + MCP + IPython shell)
pip install "scrapling[all]"

# Docker (all extras + browsers pre-installed)
docker pull pyd4vinci/scrapling
```

```python
# HTTP request with TLS impersonation
from scrapling.fetchers import Fetcher, FetcherSession

with FetcherSession(impersonate='chrome') as session:
    page = session.get('https://quotes.toscrape.com/', stealthy_headers=True)
    quotes = page.css('.quote .text::text').getall()

# Stealth mode: bypass Cloudflare Turnstile
from scrapling.fetchers import StealthyFetcher

page = StealthyFetcher.fetch('https://nopecha.com/demo/cloudflare', headless=True)
data = page.css('#padded_content a').getall()

# Adaptive scraping: survive page redesigns
from scrapling.fetchers import StealthyFetcher
StealthyFetcher.adaptive = True
page = StealthyFetcher.fetch('https://example.com', headless=True)
products = page.css('.product', auto_save=True)   # store signatures
products = page.css('.product', adaptive=True)    # later: find even after redesign

# Full crawler with pause/resume
from scrapling.spiders import Spider, Response

class QuotesSpider(Spider):
    name = "quotes"
    start_urls = ["https://quotes.toscrape.com/"]
    concurrent_requests = 10

    async def parse(self, response: Response):
        for quote in response.css('.quote'):
            yield {
                "text": quote.css('.text::text').get(),
                "author": quote.css('.author::text').get(),
            }
        next_page = response.css('.next a')
        if next_page:
            yield response.follow(next_page[0].attrib['href'])

result = QuotesSpider(crawldir="./crawl_data").start()
result.items.to_json("quotes.json")
```

```json
// Claude Code MCP server config (claude_desktop_config.json)
{
  "mcpServers": {
    "ScraplingServer": {
      "command": "scrapling",
      "args": ["mcp"]
    }
  }
}
```

```bash
# CLI usage: scrape to Markdown without code
scrapling extract get 'https://example.com' content.md --css-selector '#main'
scrapling extract stealthy-fetch 'https://nopecha.com/demo/cloudflare' out.html \
  --css-selector '#padded_content a' --solve-cloudflare
```

---

## Relevance to Claude Code Development

### Applications

- **MCP-assisted web research**: The built-in MCP server integrates directly with Claude Code. Claude can invoke `get`, `fetch`, or `stealthy_fetch` tools to retrieve web content during research tasks with CSS-selector scoping, reducing token usage versus passing full HTML
- **Documentation scraping for research entries**: Scrapling can automate the data-gathering phase of research curator workflows — fetching GitHub READMEs, PyPI pages, and documentation sites with anti-bot bypass when needed
- **Agent tooling for data extraction**: Research agents or orchestrators can spawn Scrapling-backed tools for structured data extraction from the web as part of multi-step pipelines

### Patterns Worth Adopting

- **CSS selector pre-filtering before AI consumption**: The MCP server pattern of narrowing content with selectors before passing to a model applies broadly — any tool that retrieves text for AI processing should offer a filter/scope parameter to reduce token waste
- **Adaptive element tracking pattern**: Storing element signatures and using similarity-based relocation is a useful resilience pattern for any automation that targets specific DOM elements in periodically-changing sources
- **Multi-session spider routing**: The `sid` parameter pattern for routing requests to different session backends (fast HTTP vs stealth browser) within a single workflow is a clean way to handle heterogeneous data sources in agent pipelines
- **Checkpoint-based pause/resume**: The `crawldir` persistence approach — serialize state on interrupt, resume from checkpoint — is a transferable pattern for long-running agent tasks that should survive interruption

### Integration Opportunities

- **Research curator agent**: Add Scrapling as the web fetching backend for the research curator skill, replacing basic `WebFetch` calls with Scrapling's MCP tools for anti-bot bypass and token efficiency
- **Direct MCP server addition**: Add `ScraplingServer` to Claude Code's MCP configuration to give all Claude Code sessions access to stealth scraping tools
- **Benchmark data retrieval**: Use Scrapling to collect PyPI download statistics, npm counts, and GitHub metrics for research entries where the standard GitHub API doesn't expose the data

---

## References

- [GitHub Repository: D4Vinci/Scrapling](https://github.com/D4Vinci/Scrapling) (accessed 2026-02-26)
- [GitHub API: repos/D4Vinci/Scrapling](https://api.github.com/repos/D4Vinci/Scrapling) (accessed 2026-02-26)
- [GitHub API: releases/latest](https://api.github.com/repos/D4Vinci/Scrapling/releases/latest) (accessed 2026-02-26)
- [Scrapling v0.4 Release Notes](https://github.com/D4Vinci/Scrapling/releases/tag/v0.4) (accessed 2026-02-26)
- [pyproject.toml](https://github.com/D4Vinci/Scrapling/blob/main/pyproject.toml) (accessed 2026-02-26)
- [MCP Server Documentation](https://github.com/D4Vinci/Scrapling/blob/main/docs/ai/mcp-server.md) (accessed 2026-02-26)
- [Official Documentation](https://scrapling.readthedocs.io/en/latest/) (accessed 2026-02-26)

---
