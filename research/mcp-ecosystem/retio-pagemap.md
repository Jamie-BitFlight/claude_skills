---
name: Retio PageMap
description: Retio PageMap is a Python MCP server that compresses raw HTML pages (~100K tokens) into structured 2-5K token PageMap representations while preserving all interactive elements with numbered reference...
license: MIT
metadata:
  topic: retio-pagemap
  category: mcp-ecosystem
  source_url: https://github.com/Retio-ai/Retio-pagemap
  github: Retio-ai/Retio-pagemap
  version: "v0.1.3"
  verified: "2026-02-18"
  next_review: "2026-05-18"
---

## Overview

Retio PageMap is a Python MCP server that compresses raw HTML pages (~100K tokens) into structured 2-5K token PageMap representations while preserving all interactive elements with numbered reference IDs. AI agents can navigate, read, and interact with any web page at 97% fewer tokens than raw accessibility snapshots. Benchmarked at 95.2% task success across 66 tasks on e-commerce sites, compared to 39.7% for Playwright MCP and 60.9% for Firecrawl.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Playwright MCP dumps 50-540KB accessibility snapshots that overflow context windows after 2-3 page navigations | 5-stage HTML pruning pipeline produces 2-5K token PageMaps regardless of page size |
| Firecrawl and Jina Reader convert HTML to markdown but provide no interaction capability | Interactive element detection (3-tier: ARIA roles, implicit HTML roles, CDP event listeners) assigns numbered ref IDs for click/type/select actions |
| Multi-page web agent sessions exceed context budget within a few navigations | Token-budget-aware assembly caps output at configured limits, enabling unlimited multi-page sessions |
| Raw HTML contains prompt injection vectors and SSRF attack surfaces | Sanitizer applies nonce-based content boundaries, role-prefix stripping, Unicode control char removal, SSRF defense via scheme whitelist and private IP blocking |
| Web content in multiple languages requires locale-specific extraction logic | Built-in i18n module handles price/review/rating/pagination patterns for Korean, English, Japanese, French, German with auto-detection from URL domain |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 14 | 2026-02-18 |
| GitHub Forks | 2 | 2026-02-18 |
| Contributors | 1 | 2026-02-18 |
| Open Issues | 1 | 2026-02-18 |
| Latest Release | v0.1.3 | 2026-02-18 |
| Release Date | 2026-02-17 | 2026-02-18 |
| Repository Created | 2026-02-16 | 2026-02-18 |
| Primary Language | Python (350,991 bytes) | 2026-02-18 |
| Benchmark Task Success | 95.2% (66 tasks, 9 e-commerce sites) | 2026-02-18 |
| Token Reduction vs Raw HTML | 97% (2-5K vs 50-540K tokens) | 2026-02-18 |
| Cost per 66-task benchmark | $0.58 vs $6.71 (Playwright MCP) | 2026-02-18 |

---

## Key Features

### MCP Server Interface

- Exposes three MCP tools over stdio transport: `get_page_map` (navigate to URL, return structured PageMap), `execute_action` (click/type/select on ref-numbered elements), `get_page_state` (lightweight URL and title check)
- Smithery-compatible configuration with zero required API keys or external config
- Installable via `uvx retio-pagemap` with no explicit Python environment setup

### HTML Compression Pipeline (5-Stage)

- Stage 1: HTMLRAG preprocessing normalizes raw HTML structure
- Stage 2: Script extraction pulls JSON-LD structured data and React Server Component (RSC) payloads from script tags
- Stage 3: Semantic filtering removes navigation, footer, aside, and other non-content regions
- Stage 4: Schema-aware chunk selection retains product/content-relevant blocks
- Stage 5: Attribute stripping and compression removes decorative attributes while preserving semantic ones
- Budget-aware assembly applies tiktoken-based token counting to cap final output at configured limits

### Interactive Element Detection (3-Tier)

- Tier 1: ARIA roles with accessible names (buttons, links, menus) detected from accessibility tree
- Tier 2: Implicit HTML semantic roles (`<input>`, `<select>`, `<textarea>`) detected from DOM
- Tier 3: CDP (Chrome DevTools Protocol) event listener inspection identifies divs/spans with JavaScript click handlers
- All detected elements receive stable integer ref IDs for use in `execute_action` calls

### PageMap Output Format

- Structured YAML-like sections: `Actions` (interactables with ref numbers and action types), `Info` (compressed HTML with prices, titles, key content), `Images` (product/content image URLs), `Metadata` (JSON-LD, Open Graph structured data)
- Page type classification (`product_detail`, `listing`, etc.) included in output
- Serializer provides both `to_agent_prompt` (text format) and `to_json` (structured dict) output modes

### Security Hardening

- SSRF defense: scheme whitelist (http/https only), private IP range blocking (RFC 1918), post-redirect URL revalidation
- Prompt injection defense: nonce-based content boundaries prevent injected content from escaping PageMap structure, role-prefix stripping, Unicode control character removal
- Action sandboxing: only whitelisted action types (click, type, select) permitted, dangerous key combinations blocked
- Input validation: value length limits, request timeout enforcement, sanitized error messages

### Python API (Programmatic Access)

- `BrowserSession` async context manager wraps Playwright Chromium instance
- `build_page_map_live(session, url)` for live browser rendering
- `build_page_map_offline(html, url)` for pre-collected HTML without browser
- Pydantic models for all output types with full type annotations (`py.typed` marker present)

---

## Technical Architecture

<eg>
URL
 |
 v
Playwright Chromium Browser
 |-- Accessibility Tree (AX Tree) --> 3-Tier Interactive Detector --> Interactables[]
 |-- Raw HTML                      --> 5-Stage Pruning Pipeline    --> pruned_context
                                         1. HTMLRAG preprocessing (lxml)
                                         2. Script extraction (JSON-LD, RSC payloads)
                                         3. Semantic filtering (nav/footer/aside removal)
                                         4. Schema-aware chunk selection
                                         5. Attribute stripping (beautifulsoup4)
                                   --> Metadata Extractor (Open Graph, JSON-LD)
                                   --> Image Extractor
                                   --> i18n Locale Detector

All components feed into:
Budget-Aware Assembler (tiktoken token counting)
 |
 v
PageMap (dataclass)
  .page_type         -- classified page type string
  .interactables     -- List[Interactable(ref, role, label, action_types)]
  .pruned_context    -- compressed HTML string
  .images            -- List[str] (URLs)
  .metadata          -- Dict (structured data)

Serializer:
  to_agent_prompt(page_map) --> YAML-like text for LLM consumption
  to_json(page_map)         --> dict for programmatic use

MCP Server (server.py):
  get_page_map(url)                           --> PageMap text
  execute_action(ref, action, value?)         --> action result
  get_page_state()                            --> {url, title}
</eg>

Module layout within `src/pagemap/`:

- `server.py` (17,809 bytes) -- MCP server entrypoint, tool definitions
- `page_map_builder.py` (19,218 bytes) -- orchestrates live and offline build pipelines
- `pruned_context_builder.py` (28,580 bytes) -- 5-stage HTML pruning implementation
- `interactive_detector.py` (13,941 bytes) -- 3-tier interactable detection
- `browser_session.py` (10,212 bytes) -- Playwright session management with security controls
- `i18n.py` (10,377 bytes) -- locale detection and multilingual extraction patterns
- `metadata.py` (10,765 bytes) -- JSON-LD and Open Graph extraction
- `sanitizer.py` (3,993 bytes) -- prompt injection and SSRF defenses
- `serializer.py` (4,544 bytes) -- output format conversion
- `preprocessing/` -- HTMLRAG and script extraction submodule
- `pruning/` -- semantic filtering and chunk selection submodule
- `cli.py` (27,949 bytes) -- CLI entrypoint for offline use and benchmarking

---

## Installation & Usage

```bash
# Install package and Chromium browser
pip install retio-pagemap
playwright install chromium

# Or run directly without installation via uvx
uvx retio-pagemap
```

Add to `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "pagemap": {
      "command": "uvx",
      "args": ["retio-pagemap"]
    }
  }
}
```

CLI usage for offline analysis:

```bash
pagemap build --url "https://www.example.com/product/123"
```

Python API for programmatic use:

```python
import asyncio
from pagemap.browser_session import BrowserSession
from pagemap.page_map_builder import build_page_map_live, build_page_map_offline
from pagemap.serializer import to_agent_prompt, to_json


async def main():
    async with BrowserSession() as session:
        page_map = await build_page_map_live(session, "https://example.com/product/123")

        # Agent-optimized text format (2-5K tokens)
        print(to_agent_prompt(page_map))

        # Structured JSON for downstream processing
        print(to_json(page_map))

        # Direct field access
        print(page_map.page_type)  # "product_detail"
        print(page_map.interactables)  # [Interactable(ref=1, role="button", ...)]
        print(page_map.pruned_context)  # compressed HTML
        print(page_map.images)  # ["https://cdn.example.com/img.jpg"]
        print(page_map.metadata)  # {"name": "...", "price": "..."}


# Offline processing without browser
html = open("page.html").read()
page_map = build_page_map_offline(html, url="https://example.com/product/123")

asyncio.run(main())
```

---

## Relevance to Claude Code Development

### Applications

- Direct drop-in MCP server for Claude Code sessions requiring web browsing: navigate to documentation pages, extract structured content, interact with web forms, all within a single context window
- Enables multi-step web research tasks (compare library versions, check package registries, read API documentation) that would overflow context with Playwright MCP's raw accessibility snapshots
- The `get_page_state` tool provides lightweight session health checks without consuming significant token budget

### Patterns Worth Adopting

- Token-budget-aware output assembly is a transferable pattern for any agent tool that produces variable-size output; using tiktoken at the tool boundary prevents upstream context overflow rather than relying on the model to self-regulate
- 3-tier interactive element detection (ARIA roles -> implicit HTML roles -> CDP event listeners) is a robust fallback chain applicable to any accessibility-aware tool
- Nonce-based content boundaries as prompt injection defense in MCP tools processing untrusted web content is a security pattern applicable to all MCP servers that fetch and return external content
- Offline mode (`build_page_map_offline`) enables testing and benchmarking without live browser infrastructure, a pattern worth applying to any MCP server processing external data

### Integration Opportunities

- Can be added to the `claude_skills` research curator workflow for automated web research: `get_page_map` on documentation URLs, `execute_action` for pagination, structured output piped to research entry generation
- The Python API (`BrowserSession`, `build_page_map_live`) can be imported directly into companion scripts that need structured web content without standing up a full MCP server
- The multilingual i18n module (`i18n.py`) provides locale-aware extraction patterns reusable for any tool that processes international web content

---

## References

- [Retio PageMap GitHub Repository](https://github.com/Retio-ai/Retio-pagemap) (accessed 2026-02-18)
- [retio-pagemap on PyPI](https://pypi.org/project/retio-pagemap/) (accessed 2026-02-18)
- [GitHub API: repos/Retio-ai/Retio-pagemap](https://api.github.com/repos/Retio-ai/Retio-pagemap) (accessed 2026-02-18)
- [GitHub API: releases/latest](https://api.github.com/repos/Retio-ai/Retio-pagemap/releases/latest) (accessed 2026-02-18)
- [Smithery MCP Registry Configuration](https://smithery.ai/docs/config#smitheryyaml) (accessed 2026-02-18)
