---
name: Kernel
description: Kernel is a browsers-as-a-service (BaaS) API platform that provisions cloud-based Chrome browser instances for AI agents and web automations. It solves the infrastructure burden of managing...
license: Apache-2.0 (kernel-images), MIT (kernel-mcp-server)
metadata:
  topic: kernel-sh
  category: agent-infrastructure
  source_url: https://www.kernel.sh
  github: kernel/kernel-images> (core infra, Apache-2.0)
  version: "No versioned SDK release; kernel-images last commit 2026-02-22"
  verified: "2026-02-22"
  next_review: "2026-05-22"
---

## Overview

Kernel is a browsers-as-a-service (BaaS) API platform that provisions cloud-based Chrome browser instances for AI agents and web automations. It solves the infrastructure burden of managing headful/headless browser fleets at scale by providing serverless, isolated VM-per-browser execution with millisecond cold starts. Kernel's primary differentiators versus competitors like Browserbase are 5.8x faster cold starts, 72-hour session limits (vs. 6 hours), per-second billing, and an open-source MCP server enabling direct integration with Claude Code and other LLM toolchains.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Managing browser infrastructure for agents is operationally complex | Serverless cloud browsers with no infrastructure to manage; connect via CDP URL |
| Cold start latency kills real-time agent workflows | Kernel Browser Pools pre-warm instances for sub-second acquisition |
| Session state lost between agent runs (cookies, auth tokens) | Profiles feature persists browser state (cookies, localStorage) across sessions |
| Agent workflows need human review at checkpoints | 72-hour session limits support pause-and-resume human-in-the-loop patterns |
| Bot detection blocks agent web access | Headful browser support plus Web Bot Auth (cryptographically signed requests) improve pass-through rates by 10-20% |
| Per-minute billing wastes budget on idle time | Per-second billing; idle time excluded from charges |
| No secure credential handoff to agents | Managed Auth feature: credential storage with automated login flows |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars (kernel-images) | 670 | 2026-02-22 |
| GitHub Forks (kernel-images) | 41 | 2026-02-22 |
| Contributors (kernel-images) | 19 | 2026-02-22 |
| GitHub Stars (kernel-mcp-server) | 26 | 2026-02-22 |
| Funding raised | $22M (Seed + Series A, Accel lead) | 2025-10-15 |
| Series A announced | 2025-10-15 | 2026-02-22 |
| Primary language (kernel-images) | Go | 2026-02-22 |
| Primary language (kernel-mcp-server) | TypeScript | 2026-02-22 |

---

## Key Features

### Browser Provisioning

- Serverless Chrome instances launched on demand via REST API or SDK
- Individual VM isolation per browser session (not shared containers)
- Headless and headful modes supported
- Browser Pools: pre-configured warm instance pools for immediate acquisition without cold start latency
- SSH access to browser VMs for debugging

### Session Management

- Profiles: persist and replay browser state (cookies, localStorage, IndexedDB) across sessions
- Session duration configurable up to 72 hours (vs. 6-hour industry norm)
- Managed Auth: credential vault with automated login flows for agent-driven authentication
- Web Bot Auth: cryptographically signed requests to prove human-controlled intent

### Developer Experience

- Chrome DevTools Protocol (CDP) endpoint provided per session -- drop-in for Playwright and Puppeteer
- Live view via WebRTC client (read/write, window resize, copy/paste; faster than VNC)
- Session replay as MP4 video recordings
- Browser playground at `dashboard.onkernel.com/playground` requiring no local install

### Computer Control API

- Mouse: click, drag, move cursor, scroll wheel
- Keyboard: key presses, text input
- Screenshot capture
- Batch action execution to reduce network round-trips
- File I/O: upload/download, filesystem watch with SSE streaming

### Playwright Code Execution

- Execute arbitrary Playwright/TypeScript code inside the same VM as the browser
- Access to `page`, `context`, and `browser` variables directly
- Eliminates CDP round-trip overhead for complex interactions

### Proxy and Anti-Detection

- Built-in proxy support: datacenter, residential, ISP, custom
- Stealth mode via headful browser (avoids headless fingerprinting)
- 10-20% better bot detection pass-through rate vs. Browserbase (customer benchmark, Oct 2025)

### Extensions

- Load unpacked Chrome extensions into browser sessions

### MCP Server Integration

- Open-source MCP server (`onkernel/kernel-mcp-server`, MIT) enables Claude Code to provision and control browsers as tools
- Real-time event streaming via SSE for agent-driven workflows

---

## Technical Architecture

<eg>
Agent / Claude Code
       |
       v
Kernel REST API  ──────────────────────────────────────────────────────────
       |                                                                    |
       v                                                                    v
Browser Session (VM)                                           MCP Server (SSE)
  - Isolated Chrome instance                                    kernel-mcp-server
  - CDP endpoint exposed                                        connects Claude to
  - Playwright executor inside VM                               browser tools
  - File system / process access
  - SSH access
       |
       v
Playwright / Puppeteer (agent-side)
  connectOverCDP(cdp_ws_url)
</eg>

Key design decisions:
- One VM per browser session: strong isolation, no cross-session interference
- CDP passthrough means any existing Playwright/Puppeteer automation is compatible without code changes
- Profiles stored server-side and reattached to new sessions by reference
- Browser Pools decouple cold start from agent request path

---

## Installation & Usage

### Node.js SDK

```bash
npm install @onkernel/sdk
```

### Python SDK

```bash
uv pip install kernel
```

### MCP Server (for Claude Code)

```bash
npm install -g @onkernel/mcp-server
```

### Basic Playwright integration (Node.js)

```javascript
import { chromium } from "playwright";
import Kernel from "@onkernel/sdk";

const kernel = new Kernel({ apiKey: process.env.KERNEL_API_KEY });
const kernelBrowser = await kernel.browsers.launch({ headless: false });

const browser = await chromium.connectOverCDP(kernelBrowser.cdp_ws_url);
const page = await browser.newPage();
await page.goto("https://example.com");
// ... automation logic ...
await kernel.browsers.stop(kernelBrowser.id);
```

### Session with persistent profile

```javascript
const profile = await kernel.profiles.create({ name: "my-auth-session" });
const kernelBrowser = await kernel.browsers.launch({
  headless: false,
  profile_id: profile.id,
});
// Perform login -- state saved to profile
await kernel.browsers.stop(kernelBrowser.id);

// Later session reuses cookies/auth state
const newBrowser = await kernel.browsers.launch({ profile_id: profile.id });
```

### CLI

```bash
# Deploy an automation action
kernel deploy ./my-action.ts

# Invoke deployed action
kernel invoke my-action --payload '{"url": "https://example.com"}'

# Stream logs
kernel logs my-action --follow
```

---

## Relevance to Claude Code Development

### Applications

- Claude Code skills that perform web research, data extraction, or form-filling workflows need reliable browser automation infrastructure; Kernel eliminates the need to manage local Chrome instances
- Human-in-the-loop skills (pause agent, let human review, resume) map directly to Kernel's 72-hour session model
- Skills requiring authenticated web access (accessing dashboards, submitting forms on behalf of users) can use Kernel Managed Auth to avoid credential exposure in prompts

### Patterns Worth Adopting

- **Browser Pool pre-warming**: For skills with latency-sensitive browser needs, pre-warm a pool and acquire rather than cold-launch; reduces agent perceived latency
- **Profile-per-user pattern**: Bind a Kernel Profile to each user/workspace identity; agents resume sessions without re-authenticating
- **Batch action dispatch**: Group sequential computer actions into a single API call to reduce round-trips in tight automation loops
- **CDP passthrough**: Existing Playwright test suites require zero code changes to run on Kernel -- enables reuse of automation code in agent context

### Integration Opportunities

- **MCP tool for browser control**: The open-source `kernel-mcp-server` (MIT) can be added to a Claude Code plugin as an MCP server, giving skills native access to `browser_launch`, `browser_screenshot`, `browser_click`, and related tools without custom CDP integration
- **Research skills**: A web-research skill could use Kernel to handle JavaScript-heavy sites and authenticated pages that `WebFetch` cannot access
- **Form-filling agent**: Credential-holding agent pattern using Kernel Managed Auth to complete OAuth flows or fill multi-step forms on behalf of a user
- **CI browser testing**: Skills that validate web UIs in a pipeline can provision ephemeral Kernel browsers rather than maintaining local Selenium/Playwright infrastructure

---

## References

- [Kernel homepage](https://www.kernel.sh) (accessed 2026-02-22)
- [Kernel documentation introduction](https://www.kernel.sh/docs/introduction) (accessed 2026-02-22)
- [Kernel llms.txt (full technical reference)](https://www.kernel.sh/docs/llms.txt) (accessed 2026-02-22)
- [Kernel vs Browserbase performance blog post](https://www.kernel.sh/blog/fast) (accessed 2026-02-22)
- [Kernel $22M Series A announcement](https://www.kernel.sh/blog/series-a-announcement) (accessed 2026-02-22)
- [kernel/kernel-images GitHub repository](https://github.com/kernel/kernel-images) (accessed 2026-02-22)
- [onkernel/kernel-mcp-server GitHub repository](https://github.com/onkernel/kernel-mcp-server) (accessed 2026-02-22)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [browser-harness-js](../agent-frameworks/browser-harness-js.md) | agent-frameworks | referenced by browser-harness-js (agent-frameworks) |
| [gstack](../agent-frameworks/gstack.md) | agent-frameworks | referenced by gstack (agent-frameworks) |
| [cmux](./cmux.md) | agent-infrastructure | referenced by cmux (agent-infrastructure) |
| [cua](./cua.md) | agent-infrastructure | referenced by cua (agent-infrastructure) |
| [happycapy](./happycapy.md) | agent-infrastructure | referenced by happycapy (agent-infrastructure) |
| [holyclaude](./holyclaude.md) | agent-infrastructure | referenced by holyclaude (agent-infrastructure) |
| [vibium](./vibium.md) | agent-infrastructure | referenced by vibium (agent-infrastructure) |
| [scrapling-skill](../developer-tools/scrapling-skill.md) | developer-tools | referenced by scrapling-skill (developer-tools) |
