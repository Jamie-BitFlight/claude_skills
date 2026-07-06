---
title: "surf-cli"
research_date: "2026-02-26"
source_url: "https://github.com/nicobailon/surf-cli"
github_url: "https://github.com/nicobailon/surf-cli"
version_at_research: "v2.6.0"
license: "MIT"
last_verified: "2026-02-26"
version_at_verification: "v2.6.0"
next_review: "2026-05-26"
---

## Overview

surf-cli is a zero-config CLI tool that enables AI agents to control Chrome (and other Chromium-based browsers) via a Chrome extension and native host bridge over a Unix socket. It is agent-agnostic -- any tool that can run shell commands can use it -- and ships 50+ commands covering navigation, page reading, interaction, screenshot capture, network capture, device emulation, workflow execution, and keyless AI model querying via browser sessions.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Browser automation tools require specific AI provider lock-in (Manus, Claude Extension) | Pure CLI over Unix socket; works with any agent that can run shell commands |
| MCP-based browser tools require relay process setup and configuration | Zero-config install: npm install, load extension, run `surf install <id>` |
| Screenshots consume excessive LLM tokens at full resolution | Auto-resize to 1200px by default; actions auto-capture without extra round-trips |
| Network request interception requires manual setup | Passive capture of all network requests; filter/replay via `surf network` commands |
| Querying frontier AI models requires API keys and billing setup | `surf chatgpt`, `surf gemini`, `surf grok`, `surf perplexity`, `surf aistudio` use existing browser sessions |
| Multi-step automation requires multiple LLM round-trips per step | `surf do` workflow executor runs pipe-separated steps deterministically with auto-waits |
| Agent and user share the same browser window causing interference | `surf window.new` creates isolated agent windows; `--window-id` targets specific windows |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 281 | 2026-02-26 |
| GitHub Forks | 23 | 2026-02-26 |
| npm Downloads/month | 586 | 2026-02-26 |
| Contributors | 5 (pages 1-5 per paginated API) | 2026-02-26 |
| Latest Release | v2.6.0 | 2026-02-26 |
| Open Issues | 7 | 2026-02-26 |
| Commit Activity (52 weeks) | 129 commits | 2026-02-26 |
| Created | 2025-12-28 | 2026-02-26 |

SOURCE: [GitHub API repos/nicobailon/surf-cli](https://api.github.com/repos/nicobailon/surf-cli) (accessed 2026-02-26), [npm API downloads/point/last-month/surf-cli](https://api.npmjs.org/downloads/point/last-month/surf-cli) (accessed 2026-02-26)

---

## Key Features

### Navigation and Page Reading

- `surf go <url>` -- navigate to URL; `surf back`, `surf forward`, `surf tab.reload --hard`
- `surf read` -- returns accessibility tree + visible text; supports `--depth`, `--compact`, `--no-text` flags for token reduction (60% smaller output with both flags)
- Element refs (`e1`, `e2`...) are stable accessibility-tree identifiers, resilient to DOM changes
- `surf page.text` for raw text; `surf page.state` for modal/loading/scroll state

### Semantic Interaction

- `surf locate.role`, `surf locate.text`, `surf locate.label` -- find elements by ARIA role, text content, or form label without CSS selectors
- `--action click|fill` parameter directly executes action on matched element
- `surf click`, `surf type`, `surf key`, `surf scroll.bottom` -- full interaction surface
- `surf select` for dropdowns -- by value, label, or index; multi-select supported

### Iframe Support

- `surf frame.list`, `surf frame.switch` (by index, name, or CSS selector)
- All commands target active frame after switch; `surf frame.main` returns to top-level

### Screenshot and Visual

- Auto-saves to `/tmp/surf-snap-*.png`; auto-resize to 1200px (configurable via `surf.json`)
- `surf screenshot --annotate` renders element labels on screenshot for agent reference
- `surf screenshot --fullpage`, `--full` for HD, `--no-save` for base64 only
- Actions (`click`, `type`, `scroll`) auto-capture post-action screenshots by default

### Network Capture

- Passive capture of all network requests while surf is active -- no start command needed
- `surf network` -- compact table of recent requests; `--format curl` emits curl commands
- Filter by origin, method, response type, status code, time window, exclude static assets
- `surf network.get <id>`, `surf network.body <id>`, `surf network.curl <id>` -- drill-down per request
- Storage at `/tmp/surf/`; 24-hour TTL, 200MB max; configurable via `SURF_NETWORK_PATH`

### Workflow Execution (`surf do`)

- Inline pipe syntax: `surf do 'go "url" | click e5 | screenshot'`
- JSON workflow files with named args, loops (`repeat`, `each`), step output capture (`as:`), and exit conditions (`until:`)
- Auto-waits after navigation and DOM-mutating actions (configurable `--step-delay`)
- `--dry-run` validates without executing; `--on-error stop|continue`
- Stored in `~/.surf/workflows/` (user) or `./.surf/workflows/` (project)

### AI Query Without API Keys

- `surf chatgpt`, `surf gemini`, `surf grok`, `surf perplexity`, `surf aistudio` -- query AI using browser session cookies
- `--with-page` includes current tab content as context; `--file` attaches local file
- `--model` flag for best-effort model selection where supported
- `surf gemini --generate-image`, `--edit-image`, `--youtube` for multimodal tasks
- `surf aistudio.build "prompt" --output ./dir` -- generates and extracts full web app from AI Studio App Builder

### Device Emulation and Performance

- `surf emulate.device "iPhone 14"` -- 15+ device presets (iPhone, iPad, Pixel, Galaxy, etc.)
- `surf emulate.viewport`, `surf emulate.touch`
- `surf perf.metrics`, `surf perf.start`, `surf perf.stop` -- Chrome DevTools performance tracing

### Window and Tab Management

- `surf window.new`, `surf window.list`, `surf window.focus`, `surf window.close`
- `--window-id` on any command targets specific window -- isolates agent browsing from user
- `surf tab.name "label"`, `surf tab.switch "label"` -- named tab bookmarks for multi-tab workflows

### MCP Server Mode

- Ships `native/mcp-server.cjs` -- can be run as an MCP server exposing surf commands as tools
- Dependency on `@modelcontextprotocol/sdk ^1.26.0` in `package.json`

---

## Technical Architecture

<eg>
┌──────────────────────────────────────────────────────┐
│  AI Agent (Claude Code, GPT, shell script, etc.)      │
│  runs: surf click e5                                   │
└─────────────────┬────────────────────────────────────┘
                  │ Unix socket (SURF_SOCKET_PATH)
                  │
┌─────────────────▼────────────────────────────────────┐
│  native/cli.cjs  (Node.js CLI entry point)            │
│  ├── do-parser.cjs / do-executor.cjs  (workflows)     │
│  ├── *-client.cjs  (AI provider clients)              │
│  ├── network-store.cjs  (network capture)             │
│  └── mcp-server.cjs  (MCP server mode)                │
└─────────────────┬────────────────────────────────────┘
                  │ Chrome Native Messaging (stdio)
                  │ host.cjs / host.sh / host-wrapper.py
                  │
┌─────────────────▼────────────────────────────────────┐
│  Chrome Extension (manifest.json + dist/)             │
│  ├── service-worker/  (background message routing)    │
│  ├── content/         (page interaction, a11y tree)   │
│  ├── cdp/             (Chrome DevTools Protocol)      │
│  └── options/         (extension settings UI)         │
└──────────────────────────────────────────────────────┘
         │
         │ Chrome DevTools Protocol (CDP)
         ▼
    Chrome / Brave / Edge / Arc / Helium
</eg>

Communication path: CLI sends JSON commands over a Unix socket to the native host, which relays to the Chrome extension via Chrome Native Messaging. The extension executes actions via CDP and DOM APIs, returning JSON results. The native host also writes network capture logs to `/tmp/surf/` for async retrieval.

Build: TypeScript source compiled with Vite 7; extension bundle at `dist/`; native host at `native/*.cjs` (CommonJS for Node compatibility). Biome for lint/format; Vitest for tests.

---

## Installation & Usage

```bash
# Install globally
npm install -g surf-cli

# Load extension: chrome://extensions → Developer mode → Load unpacked → paste surf extension-path output
surf extension-path

# Register native host (requires extension ID from chrome://extensions)
surf install <extension-id>

# Brave, Edge, Arc, or all browsers
surf install <extension-id> --browser brave
surf install <extension-id> --browser all

# Verify
surf tab.list
```

```bash
# Basic navigation and reading
surf go "https://example.com"
surf read --depth 3 --compact
surf snap

# Click element by accessibility tree ref
surf click e5

# Semantic locator (no ref needed)
surf locate.role button --name "Submit" --action click
surf locate.label "Email" --action fill --value "user@example.com"

# Network inspection
surf network --method POST --type json
surf network.body r_001 | jq .

# Workflow (inline)
surf do 'go "https://example.com/login" | type "user@example.com" --selector "#email" | type "pass" --selector "#password" | click --selector "button[type=submit]"'

# AI query (no API key -- uses browser session)
surf gemini "summarize this page" --with-page
surf chatgpt "explain this code" --file ./src/main.ts

# Isolated agent window
surf window.new "https://app.example.com"
surf read --window-id 123456
```

```bash
# Package manager installs (Nix, Homebrew) -- set overrides before surf install
export SURF_NODE_PATH=/nix/store/.../bin/node
export SURF_HOST_PATH=/nix/store/.../native/host.cjs
export SURF_EXTENSION_PATH=/nix/store/.../dist
surf install <extension-id>
```

---

## Relevance to Claude Code Development

### Applications

- Direct integration path for Claude Code agents performing web research, form filling, UI testing, or scraping tasks -- `surf` commands are shell commands, no MCP configuration required
- `surf aistudio "prompt"` and `surf gemini "prompt" --with-page` enable multi-model consultation in agent workflows without API key management
- `surf do` workflows reduce LLM round-trips for repetitive multi-step browser sequences (login, paginate, extract)
- `surf network` captures API shapes from live web applications -- useful for reverse-engineering integration targets

### Patterns Worth Adopting

- **Auto-screenshot after actions**: surf captures a screenshot after every mutating command, eliminating "verify state" round-trips -- a pattern applicable to any agent tool that modifies external state
- **Accessibility tree as primary page representation**: element refs from `surf read` are more token-efficient and LLM-friendly than full HTML; this DOM abstraction pattern is applicable to other tools
- **Compact/depth flags for token budget**: `--depth N --compact` produces 60% smaller output -- progressive disclosure flags are a general good practice for agent-facing CLIs
- **Workflow DSL with auto-waits**: `surf do` deterministic pipe-execution with built-in DOM stability waits outperforms LLM-orchestrated step-by-step sequences for predictable multi-step tasks
- **Window isolation pattern**: `--window-id` flag isolates agent operations from user browsing -- relevant for any tool that shares state between human and automated sessions

### Integration Opportunities

- Add a `/surf` skill to the claude_skills repository wrapping surf commands with usage examples for common agent browser tasks
- Use `surf do` workflow JSON format as a template for deterministic task runner DSLs in other skill domains
- `surf network` output piped to `jq` is a lightweight API exploration workflow for skill development (no Postman or manual DevTools needed)
- MCP server mode (`native/mcp-server.cjs`) allows surf to be registered as an MCP tool server, exposing all 50+ commands as structured tool calls to Claude Code

---

## References

- [surf-cli GitHub Repository](https://github.com/nicobailon/surf-cli) (accessed 2026-02-26)
- [surf-cli README](https://github.com/nicobailon/surf-cli/blob/main/README.md) (accessed 2026-02-26)
- [surf-cli npm package](https://www.npmjs.com/package/surf-cli) (accessed 2026-02-26)
- [v2.6.0 Release Notes](https://github.com/nicobailon/surf-cli/releases/tag/v2.6.0) (accessed 2026-02-26)
- [GitHub API -- repo metadata](https://api.github.com/repos/nicobailon/surf-cli) (accessed 2026-02-26)
- [npm Downloads API](https://api.npmjs.org/downloads/point/last-month/surf-cli) (accessed 2026-02-26)

---
