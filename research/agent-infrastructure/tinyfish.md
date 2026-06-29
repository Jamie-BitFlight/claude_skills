---
title: "TinyFish"
research_date: "2026-02-23"
source_url: "https://www.tinyfish.ai"
github_url: "<https://github.com/tinyfish-io/agentql-mcp> (AgentQL MCP server, MIT)"
version_at_research: "No versioned releases; API at `https://agent.tinyfish.ai/v1` (current as of 2026-02-23)"
license: "Commercial SaaS (AgentQL MCP server: MIT)"
last_verified: "2026-02-23"
version_at_verification: "API v1 (no versioned SDK release)"
next_review: "2026-05-23"
---

## Overview

TinyFish is an enterprise serverless web agent API platform that enables AI agents to navigate, authenticate, extract, and transact on live websites at production scale. It eliminates the need to manage browser infrastructure, proxy configuration, or anti-bot evasion by bundling all costs — remote browsers, residential proxies, LLM inference, and anti-bot protection — into a single per-step price. The platform integrates natively with Claude and other LLM toolchains via an AgentQL MCP server, enabling agentic web scraping with a single API call.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Traditional web automation is too slow and can't scale | Serverless parallel execution of up to 1,000 simultaneous agents |
| Search/index tools return stale cached data | Live extraction directly from dynamic sites at sub-minute speed |
| Browser, proxy, and LLM costs are billed separately with hidden fees | All-in pricing: browsers at $0/hour, residential proxies at $0/GB, LLM costs included |
| Authenticated/form-based sites block automated access | Built-in form filling, login flows, and stealth browser profiles |
| Bot detection defeats standard automation | Anti-bot protection and stealth mode included in every plan |
| Real-time progress visibility is unavailable in async workflows | Server-Sent Events (SSE) stream live progress without polling |
| LLM agents lack native web access tools | AgentQL MCP server gives Claude and Cursor direct `extract-web-data` tool access |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars (agentql-mcp) | 148 | 2026-02-23 |
| GitHub Forks (agentql-mcp) | 33 | 2026-02-23 |
| Claimed success rate | 98.7% | 2026-02-23 |
| Cost per operation | $0.04 all-in | 2026-02-23 |
| Speed (50 portals) | 2m 14s | 2026-02-23 |
| Traditional automation (50 portals) | 45m+ | 2026-02-23 |
| Enterprise customers | Google, DoorDash, Amazon, ClassPass, NextEra | 2026-02-23 |
| Pay-as-you-go step price | $0.015/step | 2026-02-23 |

---

## Key Features

### Agentic Web Automation API

- Single REST endpoint: `POST https://agent.tinyfish.ai/v1/automation/run-sse`
- Natural-language `goal` parameter describes what to extract or do — no XPath or CSS selectors required
- Returns structured JSON (`resultJson`) automatically parsed from the live page
- Real-time progress streamed via Server-Sent Events (SSE); no polling required
- `browser_profile: "stealth"` parameter bypasses common anti-bot mechanisms

### Parallel Execution at Scale

- Up to 1,000 simultaneous operations in a single plan tier
- Agent concurrency: 2 (free), 4 (Standard), 20 (Pro), unlimited (Enterprise)
- No cold start penalty — serverless infrastructure provisions on demand

### Authentication and Form Handling

- Navigates behind logins, OAuth flows, and multi-step forms
- Residential proxy routing via `proxy_config.country_code` parameter for geo-restricted content
- Handles paywalls, CAPTCHA-challenged flows, and dynamic SPAs

### AgentQL MCP Server

- Open-source MCP server (`tinyfish-io/agentql-mcp`, MIT license, 148 stars)
- Provides `extract-web-data` tool: structured data extraction from any URL using a natural-language prompt
- Compatible with Claude Desktop, Claude Code, VS Code, Cursor, and Windsurf
- Installed via `npm install -g agentql-mcp`; authentication via `AGENTQL_API_KEY`

### Visual Workflow Builder (Workbench)

- No-code visual builder for defining multi-step agent workflows
- Agent observability with screenshots at each automation step
- Full run history with query and pagination options via `list_runs` API

### Inclusive All-in Pricing

- Remote browser infrastructure: $0/hour
- Residential proxy bandwidth: $0/GB
- LLM inference costs included — no separate AI API bill
- Anti-bot protection included in every plan tier

---

## Technical Architecture

<eg>
Claude Code / Agent
       |
       v
AgentQL MCP Server (npx agentql-mcp)          OR       Direct REST API
  tool: extract-web-data                                POST /v1/automation/run-sse
       |                                                        |
       v                                                        v
TinyFish Web Agent API  (https://agent.tinyfish.ai/v1)
  - Serverless browser provisioning
  - Anti-bot evasion / stealth profiles
  - Residential proxy routing
  - LLM-driven navigation and extraction
  - Structured JSON result assembly
       |
       v
SSE Stream  (real-time event progress)
  data: { "type": "PROGRESS", ... }
  data: { "type": "COMPLETE", "status": "COMPLETED", "resultJson": {...} }
</eg>

Key design decisions:

- **Bundled cost model**: eliminates the "browser + proxy + LLM = three bills" problem common to DIY stacks
- **SSE over polling**: progress events arrive continuously without client polling loops
- **Goal-oriented API**: agent describes the desired data in plain English; TinyFish handles DOM traversal, clicks, and form fills internally
- **MCP-first integration**: the AgentQL MCP server is first-class, not an afterthought — directly usable from Claude without any REST client code

---

## Installation & Usage

### AgentQL MCP Server (Claude Code / Claude Desktop)

```bash
npm install -g agentql-mcp
```

Claude Desktop configuration (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "agentql": {
      "command": "npx",
      "args": ["-y", "agentql-mcp"],
      "env": {
        "AGENTQL_API_KEY": "YOUR_API_KEY"
      }
    }
  }
}
```

### Direct REST API (JavaScript)

```javascript
const response = await fetch("https://agent.tinyfish.ai/v1/automation/run-sse", {
  method: "POST",
  headers: {
    "X-API-Key": process.env.TINYFISH_API_KEY,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    url: "https://example.com/products/",
    goal: "Extract all products: name, price, and stock status",
  }),
});

for await (const line of response.body) {
  const text = new TextDecoder().decode(line);
  if (text.startsWith("data: ")) {
    const event = JSON.parse(text.slice(6));
    if (event.type === "COMPLETE") console.log(event.resultJson);
  }
}
```

### Direct REST API with Stealth and Proxy

```javascript
body: JSON.stringify({
  url: "https://geo-restricted-site.com",
  goal: "Extract pricing data",
  browser_profile: "stealth",
  proxy_config: { enabled: true, country_code: "US" },
})
```

### cURL (quick test)

```bash
curl --location 'https://agent.tinyfish.ai/v1/automation/run-sse' \
  --header 'Content-Type: application/json' \
  --header "X-API-Key: $TINYFISH_API_KEY" \
  --data '{"url": "https://amazon.com", "goal": "Find the price of AirPods Pro 3"}'
```

---

## Relevance to Claude Code Development

### Applications

- Claude Code research skills that need live data from dynamic or authenticated sites can use TinyFish instead of `WebFetch`, which cannot handle JavaScript-heavy pages or login walls
- Skills performing competitive analysis, price monitoring, or regulatory filing extraction can run hundreds of parallel site queries without managing browser infrastructure
- The AgentQL MCP server (`extract-web-data` tool) can be added to any Claude Code plugin, instantly enabling structured web data extraction without custom REST client code

### Patterns Worth Adopting

- **Goal-oriented extraction over selector-based scraping**: passing a plain-English `goal` rather than CSS/XPath selectors is resilient to DOM changes and transfers directly to agent skill prompts
- **SSE streaming for long-running agent tasks**: the SSE event pattern (`PROGRESS` → `COMPLETE`) is a clean model for any skill that needs to surface intermediate results during multi-step agent workflows
- **All-in cost bundling**: designing agent infrastructure with bundled costs (browser + proxy + inference = one bill) reduces operational complexity and surprise overages — a pattern worth considering when building Claude Code plugins that consume external paid APIs
- **MCP tool as first-class integration**: the MCP server model with a single `extract-web-data` tool is a minimal, focused API surface that works cleanly with Claude's tool-use patterns

### Integration Opportunities

- **Web research skill**: a `web-research` Claude Code skill could wrap the AgentQL MCP `extract-web-data` tool for structured extraction from any URL — replacing brittle regex-over-HTML approaches
- **Competitive intelligence agent**: an agent skill that runs parallel TinyFish operations against a list of competitor URLs and returns a structured comparison — enabled by the 1,000-concurrent-op ceiling
- **Authenticated data agent**: skills requiring session-based access to dashboards (analytics portals, SaaS admin pages) could use TinyFish's login handling rather than maintaining credential state manually
- **Agentic form-filling workflow**: a skill pattern for submitting structured data through multi-step web forms (insurance quotes, government portals, job applications) at scale

---

## References

- [TinyFish homepage](https://www.tinyfish.ai) (accessed 2026-02-23)
- [TinyFish documentation](https://docs.tinyfish.ai) (accessed 2026-02-23)
- [TinyFish scraping examples](https://docs.tinyfish.ai/examples/scraping) (accessed 2026-02-23)
- [TinyFish pricing](https://www.tinyfish.ai/pricing) (accessed 2026-02-23)
- [agentql-mcp GitHub repository](https://github.com/tinyfish-io/agentql-mcp) (accessed 2026-02-23)
- [TinyFish Cookbook GitHub repository](https://github.com/tinyfish-io/TinyFish-cookbook) (accessed 2026-02-23)
- [AgentQL MCP Server on MCP Server Hub](https://mcpserverhub.net/server/agentql-mcp-tinyfish-io) (accessed 2026-02-23)

---
