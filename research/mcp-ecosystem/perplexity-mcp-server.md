---
name: Perplexity API Platform MCP Server
description: The official MCP server implementation from Perplexity AI provides AI assistants with real-time web search, deep research, and advanced reasoning capabilities through the Perplexity API Platform....
license: MIT
metadata:
  topic: perplexity-mcp-server
  category: mcp-ecosystem
  source_url: https://docs.perplexity.ai/guides/mcp-server
  github: perplexityai/modelcontextprotocol
  version: "v0.8.2"
  verified: "2026-02-20"
  next_review: "2026-05-20"
---

## Overview

The official MCP server implementation from Perplexity AI provides AI assistants with real-time web search, deep research, and advanced reasoning capabilities through the Perplexity API Platform. This server integrates Perplexity's Sonar models and Search API directly into MCP-compatible tools like Claude Code, Cursor, Claude Desktop, and other AI assistants, enabling them to access current web information and perform complex analytical tasks.

**Core Value Proposition**: Production-ready MCP integration that extends AI assistants with real-time internet access and specialized reasoning models from a leading AI search company.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| AI models lack access to current information | Provides real-time web search through Perplexity Search API |
| Simple queries don't need deep research overhead | Offers `sonar-pro` for quick conversational queries |
| Complex research requires thorough analysis | Enables `sonar-deep-research` for comprehensive reports |
| Advanced reasoning tasks need specialized models | Integrates `sonar-reasoning-pro` for analytical problem-solving |
| Context token waste from reasoning traces | Optional `strip_thinking` parameter removes `<think>` tags |
| Corporate firewall and proxy restrictions | Full proxy support via `PERPLEXITY_PROXY` or standard env vars |
| Cloud deployment requirements | HTTP server mode with Docker support and CORS configuration |
| Installation output pollution in strict MCP clients | Documented `npx -yq` workaround for silent installation |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 1,959 | 2026-02-20 |
| GitHub Forks | 277 | 2026-02-20 |
| Contributors | 13 | 2026-02-20 |
| npm Downloads (last month) | 29,095 | 2026-02-17 |
| Latest Version | v0.8.2 | 2026-02-20 |
| Repository Created | 2025-03-10 | 2026-02-20 |
| Last Updated | 2026-02-19 | 2026-02-20 |
| Open Issues | 0 | 2026-02-20 |
| Primary Language | TypeScript | 2026-02-20 |

---

## Key Features

### 1. Four Distinct Tools for Different Use Cases

#### `perplexity_search`
- Direct web search using Perplexity Search API
- Returns ranked search results with metadata
- Optimized for finding current information
- Lower cost than full conversational models

#### `perplexity_ask`
- General-purpose conversational AI with real-time web search
- Powered by `sonar-pro` model
- Suitable for quick questions and everyday searches
- Balances speed and accuracy

#### `perplexity_research`
- Deep, comprehensive research capabilities
- Powered by `sonar-deep-research` model
- Ideal for thorough analysis and detailed reports
- Extended processing time for quality results

#### `perplexity_reason`
- Advanced reasoning and problem-solving
- Powered by `sonar-reasoning-pro` model
- Perfect for complex analytical tasks
- Optional `strip_thinking` parameter to remove reasoning traces

### 2. Multiple Deployment Modes

#### Stdio Mode (Default)
- Direct integration with Claude Code, Cursor, Windsurf
- Process-based communication
- Suitable for local development and desktop clients

#### HTTP Server Mode
- Cloud and shared deployments
- RESTful endpoint at `/mcp`
- CORS support for browser-based clients
- Docker containerization support

### 3. Enterprise Network Support

#### Proxy Configuration
- `PERPLEXITY_PROXY` environment variable (primary)
- Fallback to standard `HTTPS_PROXY` and `HTTP_PROXY`
- Username/password authentication support
- Essential for corporate firewall environments

#### Custom Base URL
- `PERPLEXITY_BASE_URL` for custom API endpoints
- Supports internal proxies and mirrors
- Default: `https://api.perplexity.ai`

### 4. Operational Controls

#### Timeout Configuration
- `PERPLEXITY_TIMEOUT_MS` environment variable
- Default: 5 minutes (300,000ms)
- Configurable for long-running research tasks

#### Logging
- `PERPLEXITY_LOG_LEVEL`: DEBUG, INFO, WARN, ERROR
- Default: ERROR (minimal noise)
- Helpful for troubleshooting integration issues

### 5. One-Click Installation

- Install badges for Cursor and VS Code
- Pre-configured MCP JSON snippets
- Automatic dependency resolution via npx
- Plugin marketplace support in Claude Code

---

## Technical Architecture

### Component Structure

<eg>
┌─────────────────────────────────────┐
│    MCP Client (Claude Code, etc)   │
└──────────────┬──────────────────────┘
               │ stdio/http
               v
┌─────────────────────────────────────┐
│   Perplexity MCP Server             │
│   - Tool routing                    │
│   - Parameter validation (Zod)     │
│   - Response formatting             │
└──────────────┬──────────────────────┘
               │
               v
┌─────────────────────────────────────┐
│   Perplexity API Client (undici)   │
│   - HTTP/2 support                  │
│   - Proxy handling                  │
│   - Timeout management              │
└──────────────┬──────────────────────┘
               │
               v
┌─────────────────────────────────────┐
│   Perplexity API Platform           │
│   - Search API                      │
│   - sonar-pro (chat)                │
│   - sonar-deep-research             │
│   - sonar-reasoning-pro             │
└─────────────────────────────────────┘
</eg>

### Technology Stack

**Runtime**: Node.js 18+
**Language**: TypeScript 5.9+
**HTTP Client**: undici 6.20+ (HTTP/2, proxy support)
**MCP SDK**: @modelcontextprotocol/sdk 1.21+
**Validation**: Zod 3.25+
**HTTP Server**: Express 4.21+ with CORS 2.8+

### Deployment Architectures

**Local Desktop (stdio)**:
<eg>
Claude Code → npx @perplexity-ai/mcp-server → Perplexity API
</eg>

**HTTP Server (cloud)**:
<eg>
Browser/Client → HTTP :8080/mcp → Express Server → Perplexity API
</eg>

**Docker Container**:
<eg>
Docker Host → Container :8080 → Express Server → Perplexity API
</eg>

---

## Installation & Usage

### Claude Code

```bash
# Quick add via mcp command
claude mcp add perplexity \
  --env PERPLEXITY_API_KEY="your_key_here" \
  -- npx -y @perplexity-ai/mcp-server

# Or via plugin marketplace
export PERPLEXITY_API_KEY="your_key_here"
claude
# /plugin marketplace add perplexityai/modelcontextprotocol
# /plugin install perplexity
```

### Cursor (Manual Configuration)

Edit `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "perplexity": {
      "command": "npx",
      "args": ["-y", "@perplexity-ai/mcp-server"],
      "env": {
        "PERPLEXITY_API_KEY": "your_key_here"
      }
    }
  }
}
```

### VS Code

Edit `.vscode/mcp.json`:

```json
{
  "servers": {
    "perplexity": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@perplexity-ai/mcp-server"],
      "env": {
        "PERPLEXITY_API_KEY": "your_key_here"
      }
    }
  }
}
```

### HTTP Server Deployment

#### Docker

```bash
docker build -t perplexity-mcp-server .
docker run -p 8080:8080 \
  -e PERPLEXITY_API_KEY=your_key_here \
  perplexity-mcp-server
```

#### Node.js

```bash
export PERPLEXITY_API_KEY=your_key_here
npm install && npm run build && npm run start:http
```

Server available at `http://localhost:8080/mcp`

### Configuration Examples

#### With Proxy

```bash
export PERPLEXITY_API_KEY="your_key_here"
export PERPLEXITY_PROXY="https://proxy.company.com:8080"
# or with auth
export PERPLEXITY_PROXY="https://username:password@proxy.company.com:8080"
```

#### Extended Timeout

```bash
export PERPLEXITY_TIMEOUT_MS=600000  # 10 minutes for deep research
```

#### Debug Logging

```bash
export PERPLEXITY_LOG_LEVEL=DEBUG
```

---

## Usage Patterns

### Quick Web Search

Use `perplexity_search` for current information lookup:

<eg>
User: "Latest TypeScript 5.7 features"
Assistant: [calls perplexity_search]
Result: Ranked search results with metadata
</eg>

### Conversational Query

Use `perplexity_ask` for general questions:

<eg>
User: "What are the performance implications of async generators?"
Assistant: [calls perplexity_ask with sonar-pro]
Result: Conversational answer with web sources
</eg>

### Deep Research

Use `perplexity_research` for comprehensive analysis:

<eg>
User: "Compare Rust async runtimes: tokio, async-std, smol"
Assistant: [calls perplexity_research with sonar-deep-research]
Result: Detailed comparative report with citations
</eg>

### Advanced Reasoning

Use `perplexity_reason` for complex problems:

<eg>
User: "Design a distributed caching strategy for microservices"
Assistant: [calls perplexity_reason with sonar-reasoning-pro]
Result: Analytical solution with reasoning (optional strip_thinking=true)
</eg>

---

## Relevance to Claude Code Development

### Applications

1. **Real-Time Information Access**: Extend Claude Code with current web knowledge without context pollution
2. **Research Workflows**: Enable deep research tasks within coding sessions
3. **Technical Problem-Solving**: Leverage reasoning models for architectural decisions
4. **Version-Specific Queries**: Combine with local documentation servers for comprehensive context
5. **Corporate Deployment**: Proxy support enables use in enterprise environments

### Patterns Worth Adopting

1. **Tool Specialization**: Four distinct tools optimized for specific use cases (search vs research vs reasoning)
2. **Optional Response Filtering**: `strip_thinking` parameter demonstrates token optimization strategy
3. **Multi-Transport Support**: stdio for desktop, HTTP for cloud—automatic protocol selection
4. **Proxy Cascade**: `PERPLEXITY_PROXY` → `HTTPS_PROXY` → `HTTP_PROXY` fallback chain
5. **Silent Installation**: `npx -yq` pattern for strict MCP clients that fail on stdout pollution
6. **Environment-Based Configuration**: Zero-config defaults with full override capability

### Integration Opportunities

1. **Hybrid Documentation Strategy**: Combine with docs-mcp-server for local + web knowledge
   - docs-mcp-server for project dependencies (fast, versioned)
   - perplexity for current web information (fresh, comprehensive)

2. **Research-Driven Development**: Integrate perplexity_research into skill workflows
   - Automated research phase before implementation
   - Competitive analysis for feature planning
   - Best practice discovery for new technologies

3. **Reasoning Enhancement**: Apply sonar-reasoning-pro to complex Claude Code tasks
   - Architecture design decisions
   - Debugging complex system interactions
   - Trade-off analysis for technical choices

4. **Enterprise MCP Stack**: Reference implementation for corporate deployment patterns
   - Proxy configuration examples
   - Docker containerization approach
   - CORS and security considerations

### Comparison with MCP Ecosystem Peers

| MCP Server | Primary Function | Data Source | Best For |
|------------|------------------|-------------|----------|
| **Perplexity** | Real-time web search, reasoning | Perplexity API (web) | Current information, research |
| **Docs MCP Server** | Local documentation index | GitHub, npm, local files | Version-specific docs |
| **Narsil MCP** | Code intelligence, security | GitHub API, static analysis | Code quality, security auditing |
| **OctoCode MCP** | Research-driven development | GitHub search | Finding code examples |

**Complementary Use**: Perplexity provides web-current information while other servers focus on static documentation and code.

---

## Known Issues and Workarounds

### EOF / Initialize Errors in Strict Clients

**Problem**: Some MCP clients fail when `npx` writes installation messages to stdout

**Solution**: Use `-yq` flag instead of `-y`

```json
"args": ["-yq", "@perplexity-ai/mcp-server"]
```

### Proxy Authentication

**Problem**: Corporate proxies require username/password

**Solution**: Embed credentials in proxy URL

```bash
export PERPLEXITY_PROXY="https://user:pass@proxy:8080"
```

### Timeout on Deep Research

**Problem**: `sonar-deep-research` may exceed default 5-minute timeout

**Solution**: Increase timeout for research-heavy workloads

```bash
export PERPLEXITY_TIMEOUT_MS=900000  # 15 minutes
```

---

## References

1. **Official Documentation**: <https://docs.perplexity.ai/guides/mcp-server> (accessed 2026-02-20)
2. **GitHub Repository**: <https://github.com/perplexityai/modelcontextprotocol> (accessed 2026-02-20)
3. **npm Package**: <https://www.npmjs.com/package/@perplexity-ai/mcp-server> (accessed 2026-02-20)
4. **Perplexity API Portal**: <https://www.perplexity.ai/account/api/group> (accessed 2026-02-20)
5. **Perplexity Community Forum**: <https://community.perplexity.ai> (accessed 2026-02-20)
6. **MCP Protocol Specification**: <https://modelcontextprotocol.io/> (accessed 2026-02-20)
