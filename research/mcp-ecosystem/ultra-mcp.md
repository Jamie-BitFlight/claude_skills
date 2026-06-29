---
title: "Ultra MCP"
research_date: "2026-03-02"
source_url: "https://github.com/RealMikeChong/ultra-mcp"
github_url: "https://github.com/RealMikeChong/ultra-mcp"
version_at_research: "v0.8.1"
license: "MIT"
last_verified: "2026-03-02"
version_at_verification: "v0.8.1"
next_review: "2026-06-02"
---

## Overview

Ultra MCP is a Model Context Protocol server that exposes OpenAI (GPT-5), Google Gemini (2.5 Pro), Azure OpenAI, and xAI Grok AI models through a single MCP interface for use with Claude Code and Cursor. It differentiates from similar tools by shipping zero-friction setup (`npx ultra-mcp`), built-in vector search via libSQL, real-time usage analytics with pricing data sourced from LiteLLM, and a React web dashboard — all without requiring repository cloning or manual configuration.

SOURCE: [GitHub README - RealMikeChong/ultra-mcp](https://github.com/RealMikeChong/ultra-mcp) (accessed 2026-03-02)

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Switching between multiple AI provider APIs requires separate integrations and tooling | Single MCP interface routes to OpenAI, Gemini, Azure OpenAI, and xAI Grok via one server |
| No visibility into AI usage costs across providers | Built-in SQLite usage tracking with LiteLLM pricing data; dashboard shows cost by provider |
| Semantic code search requires separate embedding pipeline setup | Built-in vector search using libSQL + OpenAI/Gemini embeddings; index codebase with `npx ultra-mcp index` |
| Multi-model MCP servers require cloning and manual configuration | Ships as npm package; zero-config guided setup with `npx ultra-mcp config` |
| 25 MCP tools are not discoverable as prompts in Claude Code | All 25 tools also exposed as discoverable prompts in Claude Code (v0.7.0+) |

SOURCE: [GitHub README - RealMikeChong/ultra-mcp](https://github.com/RealMikeChong/ultra-mcp) (accessed 2026-03-02)

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 269 | 2026-03-02 |
| GitHub Forks | 18 | 2026-03-02 |
| Open Issues | 3 | 2026-03-02 |
| Contributors | ~5 (5 pages of 1 in API) | 2026-03-02 |
| Latest Version | v0.8.1 | 2026-03-02 |
| npm Weekly Downloads | ~29 (declining from peak 1,809/week in Aug 2025) | 2026-03-02 |
| npm Total Versions | 79 releases | 2026-03-02 |
| Repository Created | 2025-06-28 | 2026-03-02 |
| Last Push | 2025-08-25 | 2026-03-02 |
| Primary Language | TypeScript | 2026-03-02 |

SOURCE: [GitHub API - RealMikeChong/ultra-mcp](https://api.github.com/repos/RealMikeChong/ultra-mcp) (accessed 2026-03-02)
SOURCE: [npm - ultra-mcp](https://www.npmjs.com/package/ultra-mcp) (accessed 2026-03-02)

---

## Key Features

### Multi-Provider Model Access

- Supports OpenAI (GPT-5), Google Gemini 2.5 Pro, Azure OpenAI, and xAI Grok through a unified MCP interface
- Vercel AI SDK provides the unified model provider abstraction and real-time streaming
- OpenAI-compatible endpoint support enables Ollama (local) and OpenRouter (400+ models) integration

### Discoverable MCP Prompts

- All 25 tools are also exposed as discoverable prompts in Claude Code (introduced in v0.7.0)
- Each prompt template includes parameter guidance built in
- Enables point-and-click tool invocation without knowing tool names in advance

### Built-in Vector Search

- Semantic code search via `npx ultra-mcp index` (indexes entire codebase) and `npx ultra-mcp search "query"`
- Embeddings via OpenAI text-embedding-3-small (default, $0.02/1M tokens), text-embedding-3-large, or Gemini text-embedding-004
- Local libSQL SQLite database with vector extension for similarity search
- LangChain text splitters for smart chunking with configurable overlap

### Usage Analytics and Cost Dashboard

- Every LLM request stored in local SQLite (libSQL) with token counts and cost estimates
- Pricing data fetched from LiteLLM's GitHub repository with 1-hour file-based cache TTL
- Supports tiered pricing (e.g., Gemini long-context tiers)
- React + Tailwind CSS dashboard accessible via `npx ultra-mcp dashboard`
- CLI commands: `npx ultra-mcp db:stats`, `npx ultra-mcp db:view` (Drizzle Studio)
- Pricing lookup: `npx ultra-mcp pricing show gpt-4o`

### Zero-Friction Setup

- No repository cloning required; run directly via `npx ultra-mcp`
- Interactive guided configuration with `npx ultra-mcp config` (provider-first menu, model selection)
- Auto-installs as Claude Code MCP server with `npx ultra-mcp install`
- Health check and API connection test: `npx ultra-mcp doctor --test`
- Max 4 parameters per tool (vs. zen-mcp's 10-15) for simpler Claude Code integration

### CLI Commands

- `config` — interactive API key and model configuration
- `dashboard` — launch React web dashboard (supports `--port`, `--dev`)
- `install` — automatic Claude Code MCP server registration
- `doctor` — installation health check and API connectivity test
- `chat` — interactive CLI chat with model/provider flags
- `db:show`, `db:stats`, `db:view` — database info and usage statistics
- `index`, `search` — vector indexing and semantic search

SOURCE: [GitHub README - RealMikeChong/ultra-mcp](https://github.com/RealMikeChong/ultra-mcp) (accessed 2026-03-02)
SOURCE: [package.json - RealMikeChong/ultra-mcp](https://github.com/RealMikeChong/ultra-mcp/blob/main/package.json) (accessed 2026-03-02)

---

## Technical Architecture

Ultra MCP is a TypeScript MCP server built on the `@modelcontextprotocol/sdk` v1.17.1. It acts as a bridge between MCP clients (Claude Code, Cursor) and multiple AI provider APIs.

**Layer Stack:**

```text
MCP Client (Claude Code / Cursor)
        |
        | MCP Protocol (stdio)
        v
ultra-mcp MCP Server (Node.js, TypeScript)
  ├── src/cli.ts        -- CLI entry point (commander v14)
  ├── src/server.ts     -- MCP server implementation
  ├── src/config/       -- Conf-based local config with schema validation
  ├── src/handlers/     -- MCP protocol request handlers
  ├── src/providers/    -- Vercel AI SDK provider wrappers (OpenAI, Gemini, Azure, xAI)
  └── src/utils/        -- Streaming, error handling, token counting (tiktoken)
        |
        | Vercel AI SDK (@ai-sdk/openai, @ai-sdk/google, @ai-sdk/azure, @ai-sdk/xai)
        v
  Provider APIs (OpenAI, Google, Azure OpenAI, xAI Grok)

Local SQLite (libSQL + Drizzle ORM)
  -- Usage records, vector embeddings, pricing cache

Web Dashboard (Express server + React + Tailwind CSS)
  -- Served via tRPC API, accessible at localhost
```

**Configuration storage locations:**

- macOS: `~/Library/Preferences/ultra-mcp-nodejs/`
- Linux: `~/.config/ultra-mcp/`
- Windows: `%APPDATA%\ultra-mcp-nodejs\`

Configuration file takes precedence over environment variables (`OPENAI_API_KEY`, `GOOGLE_API_KEY`, `AZURE_API_KEY`, `XAI_API_KEY`).

SOURCE: [GitHub README - RealMikeChong/ultra-mcp](https://github.com/RealMikeChong/ultra-mcp) (accessed 2026-03-02)
SOURCE: [package.json - RealMikeChong/ultra-mcp](https://github.com/RealMikeChong/ultra-mcp/blob/main/package.json) (accessed 2026-03-02)

---

## Installation & Usage

```bash
# Install globally
npm install -g ultra-mcp

# Or use directly without installing
npx -y ultra-mcp config
```

```bash
# Step 1: Configure API keys interactively
npx -y ultra-mcp config

# Step 2: Auto-install as Claude Code MCP server
npx -y ultra-mcp install

# Step 3: Run the server (Claude Code manages this automatically after install)
npx -y ultra-mcp
```

```bash
# Check installation health
npx -y ultra-mcp doctor --test

# View usage dashboard
npx -y ultra-mcp dashboard

# CLI chat with specific model
npx -y ultra-mcp chat -m gpt-5 -p openai
npx -y ultra-mcp chat -m grok-4 -p grok

# Semantic code search
npx -y ultra-mcp index          # index current directory
npx -y ultra-mcp search "authentication logic"

# Usage statistics
npx -y ultra-mcp db:stats
npx -y ultra-mcp pricing show gpt-4o
```

```json
{
  "mcpServers": {
    "ultra-mcp": {
      "command": "npx",
      "args": ["-y", "ultra-mcp"]
    }
  }
}
```

SOURCE: [GitHub README - RealMikeChong/ultra-mcp](https://github.com/RealMikeChong/ultra-mcp) (accessed 2026-03-02)

---

## Relevance to Claude Code Development

### Applications

- **Multi-model consultation within Claude Code sessions**: Ultra MCP allows Claude Code to consult GPT-5, Gemini 2.5 Pro, or Grok during a session — enabling cross-model reasoning, second opinions, or using models with different strengths (e.g., Gemini's Google Search integration for real-time research)
- **Cost monitoring for AI-heavy workflows**: The SQLite usage tracking and dashboard directly address a pain point in Claude Code-heavy development where API costs are opaque
- **Semantic code search as an MCP tool**: The vector search capability (index + search) gives Claude Code an MCP-native way to find relevant code using natural language

### Patterns Worth Adopting

- **Discoverable prompts pattern**: Exposing all tools simultaneously as MCP prompts (v0.7.0 pattern) reduces friction — users can discover capabilities without reading documentation. This pattern is applicable to any MCP server built for Claude Code
- **Guided interactive setup with `conf`**: Using the `conf` npm library for schema-validated config stored in OS-appropriate paths avoids `.env` file proliferation and is replicable in TypeScript MCP server projects
- **LiteLLM pricing integration**: Fetching pricing from LiteLLM's centrally-maintained data with local file-based caching (1-hour TTL) is a clean pattern for any tool that needs model cost awareness
- **4-parameter tool limit**: Constraining MCP tools to max 4 parameters improves Claude Code usability — tool calls become predictable and less error-prone

### Integration Opportunities

- Ultra MCP can be added as a dependency MCP server in Claude Code settings alongside other project-specific MCP servers, providing immediate access to alternative LLM reasoning without custom integration work
- The vector search feature (`ultra-mcp index`) could complement codebase context injection in Claude Code workflows, particularly for large repos where context window limits apply
- The tRPC + Express API architecture for the dashboard is reusable as a pattern for building local web UIs for other Claude Code companion tools

---

## References

- [GitHub Repository - RealMikeChong/ultra-mcp](https://github.com/RealMikeChong/ultra-mcp) (accessed 2026-03-02)
- [npm Package - ultra-mcp](https://www.npmjs.com/package/ultra-mcp) (accessed 2026-03-02)
- [GitHub API - Repository Metadata](https://api.github.com/repos/RealMikeChong/ultra-mcp) (accessed 2026-03-02)
- [Zen MCP Server - BeehiveInnovations](https://github.com/BeehiveInnovations/zen-mcp-server) (accessed 2026-03-02)
- [Agent2Agent Protocol - Google](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/) (accessed 2026-03-02)
- [Vercel AI SDK](https://sdk.vercel.ai/) (accessed 2026-03-02)
- [LiteLLM Pricing Data](https://github.com/BerriAI/litellm) (accessed 2026-03-02)

---
