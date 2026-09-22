---
name: Browser MCP
description: Browser MCP is an MCP server that connects AI applications (Claude, Cursor, VS Code, Windsurf) to the user's existing Chrome browser via a WebSocket bridge to a Chrome extension. Unlike...
license: Apache License 2.0
metadata:
  topic: browsermcp-mcp
  category: mcp-ecosystem
  source_url: https://browsermcp.io
  github: BrowserMCP/mcp
  version: "v0.1.3"
  verified: "2026-02-20"
  next_review: "2026-05-20"
---

## Overview

Browser MCP is an MCP server that connects AI applications (Claude, Cursor, VS Code, Windsurf) to the user's existing Chrome browser via a WebSocket bridge to a Chrome extension. Unlike Playwright-based automation that spawns new browser instances, Browser MCP controls the user's live browser profile, preserving authentication sessions and real browser fingerprints. It exposes browser interactions as MCP tools following the Model Context Protocol specification.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| AI browser automation requires a fresh browser instance, losing authentication state | Uses the user's existing Chrome profile via extension bridge, preserving all logged-in sessions |
| Playwright-based automation is detectable as a bot and blocked by CAPTCHAs | Uses the real browser fingerprint through the extension, evading basic bot detection |
| Remote browser automation adds network latency | Automation runs locally on the user's machine via localhost WebSocket, eliminating external round-trips |
| AI tools cannot inspect live page state for decision-making | ARIA snapshot tool captures the accessibility tree of the live tab and returns it as structured text |
| AI tools have no standardized interface to drive browsers | MCP tool definitions expose browser actions as first-class MCP tools consumable by any MCP-capable AI client |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 5,814 | 2026-02-20 |
| Forks | 448 | 2026-02-20 |
| Contributors | 1 | 2026-02-20 |
| Latest Release | v0.1.3 | 2025-04-24 |
| Open Issues | 115 | 2026-02-20 |
| Watchers | 17 | 2026-02-20 |
| Language | TypeScript | 2026-02-20 |
| npm package | @browsermcp/mcp | 2026-02-20 |

---

## Key Features

### Browser Interaction Tools

Eleven MCP tools are exposed, each communicating with the Chrome extension via a typed WebSocket message protocol:

- `browser_snapshot` -- captures the ARIA accessibility tree of the active tab; primary perception input for the AI
- `browser_click` -- clicks an element identified by ARIA label or role
- `browser_hover` -- hovers over a named element
- `browser_type` -- types text into a named input element
- `browser_select_option` -- selects a dropdown option by element and value
- `browser_drag` -- drags from one named element to another
- `browser_navigate` -- navigates the active tab to a URL, returns ARIA snapshot after load
- `browser_go_back` / `browser_go_forward` -- browser history navigation with optional ARIA snapshot
- `browser_press_key` -- sends a key event (e.g., Enter, Escape, Tab) to the active tab
- `browser_wait` -- waits a specified number of seconds
- `browser_screenshot` -- captures a full-page screenshot and returns it as a base64 PNG MCP image resource
- `browser_get_console_logs` -- retrieves JavaScript console output from the active tab

### ARIA-Based Perception Model

Page state is represented as an ARIA accessibility tree snapshot rather than raw HTML or screenshots. This is a structured, compact representation of interactive elements, suitable for token-efficient context injection and unambiguous element identification by name and role.

### Local WebSocket Architecture

The MCP server creates a local `WebSocketServer` (using the `ws` library) on a configured port. The Chrome extension connects to this server when the user clicks "Connect" in the extension popup. All browser commands are sent as typed JSON messages over this persistent connection using a request/response message protocol (`SocketMessageMap`).

### Authentication and Profile Preservation

The server never launches a new browser. All actions execute in the user's live Chrome profile, meaning all cookies, session tokens, and browser-stored credentials remain active during automation sessions. This enables automating authenticated web applications without credential management or session replay.

### Stealth Automation

Because automation occurs through the Chrome extension API rather than through Playwright's DevTools Protocol bindings, the browser's `navigator.webdriver` flag is not set and other automation signals are absent. The user's real browser fingerprint is retained.

### MCP SDK Integration

Implements the MCP server using `@modelcontextprotocol/sdk` v1.8.0 with `StdioServerTransport`, making it compatible with all MCP-capable clients. Tool schemas are generated from Zod schemas using `zod-to-json-schema`, ensuring type-safe tool definitions and automatic JSON Schema generation.

---

## Technical Architecture

<eg>
AI Client (Claude Code / Cursor / VS Code)
     |
     | stdio (MCP protocol)
     v
@browsermcp/mcp (Node.js MCP Server)
     |
     | localhost WebSocket (ws library)
     | typed SocketMessageMap messages
     v
Browser MCP Chrome Extension
     |
     | Chrome Extension APIs
     v
User's Active Chrome Tab
</eg>

The MCP server process (`src/index.ts`) registers all browser tools and starts both:

1. An MCP `StdioServerTransport` for AI client communication.
2. A local `WebSocketServer` that listens for the Chrome extension connection.

The `Context` class (`src/context.ts`) holds the active WebSocket connection. When a tool is invoked, it calls `context.sendSocketMessage(type, payload)` with a 30-second timeout. The message is forwarded to the extension, which executes the corresponding Chrome API operation on the active tab and replies with the result.

After most interaction tools (click, hover, type, navigate, etc.) the server automatically captures a fresh ARIA snapshot via `captureAriaSnapshot(context)` and appends it to the tool result, giving the AI updated page state after every action.

Tool schemas are defined in a shared monorepo package (`@repo/types/mcp/tool`) using Zod, then converted to JSON Schema at runtime with `zod-to-json-schema`. This keeps type definitions canonical in one location across the extension and server.

---

## Installation & Usage

```bash
# Install globally via npm
npm install -g @browsermcp/mcp

# Or run directly with npx
npx @browsermcp/mcp
```

```json
{
  "mcpServers": {
    "browsermcp": {
      "command": "npx",
      "args": ["@browsermcp/mcp"]
    }
  }
}
```

The Chrome extension must be installed separately from the Chrome Web Store. After adding the MCP server config to the AI client, the user clicks the Browser MCP extension icon and presses "Connect" to establish the WebSocket bridge. The MCP server then becomes functional for the connected tab.

```typescript
// The MCP server exposes tools via stdio transport
// Tool invocation example (handled internally by MCP SDK):
// AI sends: { method: "tools/call", params: { name: "browser_navigate", arguments: { url: "https://example.com" } } }
// Server sends: { type: "browser_navigate", payload: { url: "https://example.com" } } over WebSocket to extension
// Extension navigates the tab and replies with ARIA snapshot
```

---

## Relevance to Claude Code Development

### Applications

- Claude Code can control a browser for web-based tasks: form submission, scraping authenticated content, UI testing workflows, without managing browser credentials separately.
- Enables Claude agents to perform multi-step web research workflows that require authentication (GitHub PRs, internal dashboards, CI systems) using the developer's existing sessions.
- The ARIA snapshot return pattern is a useful model for giving AI structured page perception with minimal token overhead compared to full HTML or screenshot-only approaches.

### Patterns Worth Adopting

- **ARIA snapshot as structured perception**: Returning accessibility trees rather than raw HTML provides a compact, semantically rich representation of page state. Adoptable for any tool that needs to convey UI state to an LLM.
- **Post-action snapshot return**: Automatically appending page state after every mutation tool (click, type, navigate) eliminates the need for the AI to explicitly call a separate "get state" tool. This reduces round-trips and simplifies agent loops.
- **Typed WebSocket message protocol**: Using a shared `SocketMessageMap` type with Zod schemas ensures end-to-end type safety between the MCP server and the browser extension without runtime schema drift.
- **Zod-to-JSON-Schema tool definitions**: Defining tool input schemas in Zod and converting to JSON Schema at runtime is a clean pattern for keeping tool definitions type-safe and self-documenting.

### Integration Opportunities

- Claude Code agents researching web resources (documentation, GitHub issues, npm packages) could use Browser MCP to access authenticated internal tools or sites that block automation user-agents.
- The `browser_get_console_logs` tool provides a debugging channel: Claude Code could navigate to a web app, trigger an action, and retrieve console output to diagnose runtime errors.
- Browser MCP could be combined with Claude Code's file tools to capture screenshots of rendered UI components and compare against design artifacts during code review workflows.
- The local WebSocket architecture could serve as a reference for building other local-bridge MCP servers that proxy between AI clients and native desktop applications.

---

## References

- [BrowserMCP/mcp GitHub Repository](https://github.com/BrowserMCP/mcp) (accessed 2026-02-20)
- [Browser MCP Website](https://browsermcp.io) (accessed 2026-02-20)
- [Browser MCP Documentation](https://docs.browsermcp.io) (accessed 2026-02-20)
- [npm: @browsermcp/mcp](https://www.npmjs.com/package/@browsermcp/mcp) (accessed 2026-02-20)
- [Playwright MCP Server (upstream)](https://github.com/microsoft/playwright-mcp) (accessed 2026-02-20)
- [GitHub API: repos/BrowserMCP/mcp](https://api.github.com/repos/BrowserMCP/mcp) (accessed 2026-02-20)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [browser-harness-js](../agent-frameworks/browser-harness-js.md) | agent-frameworks | referenced by browser-harness-js (agent-frameworks) |
| [gstack](../agent-frameworks/gstack.md) | agent-frameworks | referenced by gstack (agent-frameworks) |
| [ruflo](../agent-frameworks/ruflo.md) | agent-frameworks | referenced by ruflo (agent-frameworks) |
| [holyclaude](../agent-infrastructure/holyclaude.md) | agent-infrastructure | referenced by holyclaude (agent-infrastructure) |
| [vibium](../agent-infrastructure/vibium.md) | agent-infrastructure | referenced by vibium (agent-infrastructure) |
| [open-pencil](../ai-design-tools/open-pencil.md) | ai-design-tools | referenced by open-pencil (ai-design-tools) |
| [scrapling-skill](../developer-tools/scrapling-skill.md) | developer-tools | referenced by scrapling-skill (developer-tools) |
| [screenpipe](./screenpipe.md) | mcp-ecosystem | referenced by screenpipe (mcp-ecosystem) |
| [wigolo](./wigolo.md) | mcp-ecosystem | referenced by wigolo (mcp-ecosystem) |
