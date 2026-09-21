---
name: wigolo
title: wigolo — Local-First Web Intelligence for AI Agents
subtitle: Self-hosted MCP server for agent web research, zero-key by default
research_date: 2026-09-21
source_url: https://github.com/KnockOutEZ/wigolo
github_repository: https://github.com/KnockOutEZ/wigolo
version_at_research: v0.2.0
license: AGPL
freshness_tracking:
  last_verified: 2026-09-21
  version_at_verification: v0.2.0
  next_review: 2026-12-21
  confidence_map: "Overview: high | Features: high | Architecture: high (code-read) | Installation: high | Limitations and Caveats: high | Relevance: high"
---

# wigolo

## Overview

wigolo is a self-hosted Model Context Protocol (MCP) server that provides AI agents with local-first web intelligence capabilities. Described as "Local-first web intelligence for AI agents — no keys, no cloud, no metered bill," it integrates directly into Claude Code, Cursor, Codex, Gemini CLI, OpenCode, and other AI agents through MCP, along with LangChain, CrewAI, LlamaIndex, and self-hosted deployments. The architecture is built on Node.js (≥ 20) and ships with approximately 1.5 GB of on-device models and browser engine, requiring no cloud services or API keys for core functionality.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Agent web research requires external APIs and per-query billing | Local-first processing with no metered charges; no API keys for core tools (search, fetch, crawl, extract, cache, find_similar) |
| Search engine service instability and outages affect agent autonomy | 18 search engines with rank fusion; any single engine failure barely impacts results; results degradation is reported, not silent |
| Extracting structured data from web pages requires manual parsing or expensive cloud extraction APIs | Built-in extract tool with structured output modes (tables, JSON-LD, key-value pairs) and ML-scored direct citations |
| Interstitial challenges and anti-bot systems block typical headless browser approaches | Tiered fetch ladder with signal-driven escalation; learning per-domain; automatic clearance cookie reuse; honest reporting when walls remain up |

---

## Key Features

### Web Intelligence Tools

The server exposes 10 primary tools:

- **search** — Query 18 search engines with configurable result merging, ML reranking, format options (full markdown, ML-scored highlights, synthesized answers), and time/domain filtering. Example parameters: `query` (string or array), `category` ("general" | "news" | "code" | "docs" | "papers"), `max_results` (default 5, cap 20), `format` ("full" | "highlights" | "answer" | "stream_answer")

- **fetch** — Retrieve single URLs with tiered escalation: attempts plain HTTP, escalates to headless browser on observable signals (SPA markers, challenge bodies, thin content), learns per-domain. Respects robots.txt and per-domain rate limits.

- **crawl** — Follow links across a site within configurable depth and page count limits, useful for large documentation sets or product comparison research.

- **extract** — Pull structured data from pages with modes: `tables` (HTML tables), `structured` (tables + definition lists + JSON-LD + key-value pairs), or schema-based field extraction with ML scoring.

- **cache** — Query local keyword and vector index before network calls; built with FTS5 (full-text search) and embeddings.

- **find_similar** — Vector similarity search against cached pages using on-device embedding model (default BAAI/bge-small-en-v1.5); supports ML reranking with optional flashrank.

- **research** — Multi-step synthesis that decomposes a question, plans parallel searches/fetches, and optionally synthesizes results via LLM (opt-in, local LLM or cloud fallback).

- **agent** — Natural-language task execution with schema support; auto-plans queries and URLs, executes within time/page budget, optionally applies a JSON schema for structured output.

- **diff** — Compare two versions of a page (cached or live fetch) and extract what changed.

- **watch** — Monitor a URL for changes over time and report when drift is detected.

### Architecture and Execution

A single Node process speaks MCP (JSON-RPC over stdio). All heavy compute is lazy-loaded and runs locally:

- **Fetch Router**: Tiered escalation with learned per-domain behavior. Starts with plain HTTP, escalates to headless browser on observable signals (SPA detection, challenge interstitials, content thinness). Reuses clearance cookies per domain. Respects robots.txt and implements polite per-domain rate limiting ("research-grade volumes for one agent on one machine").

- **Search Engine Aggregation**: 18 sources (including Google, Bing, SearXNG, and others) ranked by custom fusion algorithm. Results are deduplicated and re-ranked. Optional ML reranking via flashrank.

- **Local Data Layer**: Keyword-indexed cache + vector index powered by embeddings. TTL-based expiration (default 7 days per `CACHE_TTL_CONTENT`); stored in `~/.wigolo/` (configurable via `WIGOLO_DATA_DIR`).

- **On-Device Models**: Browser engine (Chromium, Firefox, or WebKit selectable), embeddings model (default BAAI/bge-small-en-v1.5), optional reranker. All models run on host machine.

- **Optional LLM Integration**: Synthesis-only; off by default. When enabled, results are checked against source and nulled if absent. "Code beats model" — deterministic work (dedup, rank fusion, schema matching, canonicalization) stays off the LLM.

All 1.5 GB of models/engine is downloaded and cached on first use via `npx wigolo init`.

### Advanced Capabilities

- **Anti-Bot Escalation (Tier 0)**: Rotates request identity on `403`, impersonates browser TLS fingerprint, hardens headless browser, waits out JavaScript challenges with clearance-cookie capture, applies per-domain backoff. For datacenter/residential IP reputation walls, users opt into proxies or challenge-solver sidecars (all off by default). Failure cases are labeled (`blocked_by_challenge`), not returned as content shells.

- **Structured Data Extraction**: Direct citation with ML scoring; skips markdown parsing entirely. Supports tables, JSON-LD, OpenGraph metadata, key-value pairs, and definition lists in one call.

- **Multi-Source Schema Extraction**: Apply a JSON schema across multiple pages in parallel; aggregate results. Example: "Find pricing tiers for Supabase, Firebase, Clerk" with schema-based field extraction.

- **Framework Integrations**: Wired into Claude Code, Cursor, Codex, Gemini CLI, OpenCode, VS Code, Windsurf, Zed, Antigravity. Also available as TypeScript/Python SDKs, Docker container, REST API, and standalone binary.

---

## Technical Architecture

**Core Flow:**

```
AI Agent
  ↓ (MCP JSON-RPC over stdio)
wigolo Node process
  ├─ Tool dispatcher → 10 tools
  ├─ Fetch Router (tiered escalation, per-domain learning)
  ├─ Search Engine Aggregator (18 engines, rank fusion)
  ├─ Local Cache (FTS5 keyword index + vector index)
  ├─ Browser Pool (Chromium/Firefox/WebKit, configurable count default 3)
  └─ ML Models (embeddings, optional reranker)
      ↓
Optional: LLM synthesis (on-device or cloud, opt-in)
```

**Fetch Escalation Ladder:**

1. Plain HTTP request (robots.txt respected, rate-limited)
2. Observable signal detected? → Launch headless browser, wait for interstitial challenges, capture clearance cookies for domain reuse
3. Wall remains up? → Label as `blocked_by_challenge`, return explicit failure (never a challenge shell as "content")

**Search Ranking:**

Input: 18 engine results → Dedupe → Reciprocal Rank Fusion → ML rerank (optional flashrank) → Return top-N with scoring.

**Caching Strategy:**

- Keyword index (FTS5) for text search
- Vector index (embeddings) for semantic search
- Per-domain learned routing (which escalation strategy worked last time)
- TTL-based expiration (default 7 days, configurable)

---

## Installation & Usage

### Quick Setup

```bash
# One-command setup for local engine + agent wiring
npx wigolo init                              # local engine only
npx wigolo init --agents=claude-code,cursor  # engine + wire Claude Code + Cursor
```

**Requirements:**
- Node ≥ 20
- ~1.5 GB free disk (browser engine + models)
- macOS, Linux, or Windows

**Supported agents** for `--agents` flag: `claude-code`, `cursor`, `codex`, `gemini-cli`, `opencode`, `vscode`, `windsurf`, `zed`, `antigravity` (comma-separated).

**Installation channels:**
- npm (primary): `npx wigolo` or install globally
- Docker: `ghcr.io/knockoutez/wigolo` (slim or full image with preinstalled models)
- PyPI: `wigolo` (Python SDK)
- Homebrew, curl installer, and single-file binary: see [installation guide](https://github.com/KnockOutEZ/wigolo/blob/main/docs/installation.md)
- MCP Registry: `io.github.KnockOutEZ/wigolo`
- Directories: Glama, Smithery, mcp.so, LobeHub

### Health Check

```bash
npx wigolo doctor
```

Verifies all components (browser engine, search engines, models, embeddings) and reports status per component before first use.

### Usage Examples

**Search with result merging:**

```json
{
  "query": ["react server components patterns", "RSC data fetching"],
  "category": "docs",
  "include_domains": ["react.dev"],
  "max_results": 5
}
```

**Structured extraction with schema:**

```json
{
  "url": "https://example.com/pricing",
  "mode": "structured",
  "schema": {
    "type": "object",
    "properties": {
      "tier_name": { "type": "string" },
      "monthly_cost": { "type": "string" }
    }
  }
}
```

**Multi-source agent research:**

```json
{
  "prompt": "Compare pricing and features for Supabase, Firebase, and Clerk",
  "schema": {
    "type": "object",
    "properties": {
      "provider": { "type": "string" },
      "free_tier": { "type": "string" },
      "paid_start": { "type": "string" }
    }
  },
  "max_pages": 12
}
```

### Configuration

Top environment variables (all optional; defaults are safe):

| Variable | Default | Purpose |
|----------|---------|---------|
| `WIGOLO_DATA_DIR` | `~/.wigolo` | Cache, search engine, plugins, embeddings |
| `SEARXNG_MODE` | `native` | `native` (Python search engine local) or `docker` |
| `WIGOLO_EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | On-device embeddings for find_similar |
| `WIGOLO_RERANKER` | `none` | `flashrank` for ML reranking |
| `MAX_BROWSERS` | `3` | Browser pool size |
| `CACHE_TTL_CONTENT` | `604800` (7 days) | Page cache TTL in seconds |
| `LOG_LEVEL` | `info` | `debug`, `info`, `warn`, `error` |

Full config reference: `src/config.ts` in the repository.

### Docker

**Stdio MCP (wire into any MCP client):**

```bash
docker run -i --rm -v wigolo-data:/data ghcr.io/knockoutez/wigolo
```

**HTTP server for remote/multi-client use:**

```bash
docker run -p 3333:3333 -v wigolo-data:/data \
  -e WIGOLO_API_TOKEN=a-long-random-secret \
  ghcr.io/knockoutez/wigolo serve --host 0.0.0.0
```

---

## Limitations and Caveats

### Documented Limitations

- **Search engine instability**: While rank fusion mitigates single-engine failures, public search engines can degrade or impose new restrictions. When this occurs, the result carries a degraded backend report ("any failing engines listed"), not a silent reduction in quality.

- **Anti-bot walls with IP reputation scoring**: Managed-challenge networks (Cloudflare IP-reputation, etc.) will not issue clearances to datacenter or fresh residential IPs. For those, users opt into a proxy, challenge-solver sidecar, or hosted reader (all off by default). Wigolo reports these as `blocked_by_challenge` failures, not content shells.

- **On-device model constraints**: Embeddings model (BAAI/bge-small-en-v1.5) is optimized for English and short sentences. Reranker (flashrank, optional) has latency overhead; off by default.

- **Disk footprint**: 1.5 GB is required for browser engine + models. This is a one-time cost that becomes zero-cost per query after download.

- **Research-grade volumes**: Designed for "one agent on one machine." At higher concurrency (multiple agents, many users), per-domain rate limits may trigger. Source: README "polite end of the spectrum" design statement and robots.txt respect by default.

- **Licensing for commercial use**: Open-source AGPL. Commercial use requires a commercial license or sponsorship. Source: LICENSING.md and README FAQ ("commercial licenses fund it, not gated features").

---

## Relevance to Claude Code Development

### Applications

- **Web Research and Information Gathering** → `.claude/skills/research-curator/SKILL.md`
  - Term: `research`
  - Today: "Orchestrate research entry creation, maintenance, and validation in `./research/`. Spawns `@research-curator` agents for content work"
  - Change: Integrate wigolo as an optional backend for research-curator agent's primary source gathering phase; replace manual web search/fetch steps with tool calls to wigolo's search, fetch, crawl, and extract tools for higher-fidelity, faster research entry generation.

- **MCP Server Integration and Configuration** → `plugins/plugin-creator/skills/mcp-integration/SKILL.md`
  - Term: `MCP server`
  - Today: "Model Context Protocol (MCP) enables Claude Code plugins to expose external service capabilities as tools. Use this skill when adding MCP server configuration to a plugin"
  - Change: Reference wigolo as a production MCP server example when documenting MCP configuration patterns, deployment methods (stdio, HTTP, Docker), and tool integration workflows.

- **Browser Automation and Headless Testing** → `.claude/skills/agent-browser/SKILL.md`
  - Term: `browser automation`
  - Today: "Every browser automation follows this pattern:"
  - Change: Consider wigolo's fetch escalation (HTTP → headless browser → explicit `blocked_by_challenge` failure)
    for the page-retrieval half of research tasks, where the goal is getting readable content off a site that
    resists plain HTTP. It does not replace `agent-browser` for interaction: wigolo's ten tools are
    search/fetch/crawl/extract/cache/find_similar/research/agent/diff/watch, none of which snapshots or acts on
    DOM elements, so anything that clicks, fills, or selects stays with `agent-browser`.

### Patterns Worth Adopting

None in scope — Local-First, Zero-Key Design patterns are out of scope for this repo; the term "keyless" appears only in code-signing contexts (Sigstore), not in API authentication design documentation.

### Integration Opportunities

- **Multi-page crawl and structured extraction for research gathering** → `.claude/agents/research-curator.md`
  - Term: `research`
  - Today: "Research and document a single tool, library, or resource into a structured research entry"
  - Change: wigolo's `crawl` and `extract` tools cover a gap in that agent's `<research_tools>` block, which has no
    route that follows links across a site within a page budget and no route that pulls structured records out of a
    page. Tracked as issue #3790; integration sketches in
    [2026-09-21-wigolo-utilization.md](../insights/2026-09-21-wigolo-utilization.md).

- **Local-first web lookup for claim verification** → `.claude/skills/fact-check/SKILL.md`
  - Term: `fact-check`
  - Today: "Verifies claims in backlog items, skill documentation, or plugin content against primary sources using web lookups"
  - Change: wigolo's `search`, `fetch` and `extract` are candidate replacements for that skill's WebFetch/WebSearch calls,
    and its `diff` tool adds staleness detection the skill currently has no route for. Proposal in
    [2026-09-21-wigolo-utilization.md](../insights/2026-09-21-wigolo-utilization.md).

---

## References

- [wigolo Repository](https://github.com/KnockOutEZ/wigolo) (accessed 2026-09-21)
- [wigolo npm Package](https://www.npmjs.com/package/wigolo) (accessed 2026-09-21)
- [wigolo README](https://github.com/KnockOutEZ/wigolo/blob/main/README.md) (accessed 2026-09-21)
- [wigolo SKILL.md Documentation](https://github.com/KnockOutEZ/wigolo/blob/main/SKILL.md) (accessed 2026-09-21)
- [wigolo CHANGELOG](https://github.com/KnockOutEZ/wigolo/blob/main/CHANGELOG.md) (accessed 2026-09-21)
- [wigolo Installation Guide](https://github.com/KnockOutEZ/wigolo/blob/main/docs/installation.md) (accessed 2026-09-21)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Browser MCP](./browsermcp-mcp.md) | mcp-ecosystem | browser automation layer enabling web intelligence collection for agent tools |
| [Docs MCP Server](./docs-mcp-server.md) | mcp-ecosystem | alternative MCP capability domain: documentation indexing vs web intelligence |
| [HomeButler](./homebutler.md) | mcp-ecosystem | peer MCP server for specialized agent capability extension |
| [MCPJam Inspector](./mcpjam.md) | mcp-ecosystem | development and debugging tooling for MCP servers like this |
| [Mimir MCP](./mimir-mcp.md) | mcp-ecosystem | persistent memory layer for augmenting agent tool decisions |
| [Narsil-MCP](./narsil-mcp.md) | mcp-ecosystem | parallel MCP domain: code intelligence analysis vs web intelligence |
| [Octocode-MCP](./octocode-mcp.md) | mcp-ecosystem | research-driven agent capability: code repositories vs web intelligence |
| [Perplexity MCP Server](./perplexity-mcp-server.md) | mcp-ecosystem | complementary web research: real-time search API vs web intelligence tools |

