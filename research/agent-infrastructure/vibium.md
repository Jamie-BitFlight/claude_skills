# Vibium

## Overview

Vibium is a browser automation framework designed specifically for AI agents and developers. It provides unified access to browser control through multiple interfaces: a command-line skill, an MCP (Model Context Protocol) server, and client libraries for JavaScript/TypeScript, Python, and Java. Built in Go, Vibium uses WebDriver BiDi as its standardized browser protocol, enabling cross-browser compatibility while maintaining simplicity and performance.

**Source**: <https://github.com/VibiumDev/vibium> README.md (accessed 2026-03-24)

## Problem Addressed

Traditional browser automation tools (Selenium, Puppeteer) control browsers through either proprietary protocols (Chrome DevTools Protocol) or outdated HTTP request-response models. These approaches create several problems for AI agents:

1. **Protocol lock-in**: CDP is Chrome-specific and controlled by Google. Playwright is controlled by Microsoft. Both change without notice.
2. **One-directional communication**: Legacy WebDriver only allows request-response — the browser cannot push events to the client unprompted.
3. **Complex setup**: Most tools require manual browser downloads and complex configuration.
4. **Non-standard interfaces**: No unified standard across tools makes learning and integration difficult.

Vibium addresses these problems by building on WebDriver BiDi, a W3C standard for browser automation that is bidirectional (WebSocket-based for real-time events), standards-governed (not proprietary), and cross-browser by design (Chrome, Firefox, Safari, Edge all support it).

**Source**: docs/explanation/webdriver-bidi.md (accessed 2026-03-24)

## Key Statistics

- **GitHub Stars**: 2,726 (as of 2026-03-24)
- **License**: Apache License 2.0
- **Language**: Go (core binary)
- **Repository**: VibiumDev/vibium
- **Latest Release**: v26.3.18 (referenced in Maven/Java docs, 2026-03-24)
- **Forks**: 156
- **Open Issues**: 29
- **Contributors**: Organization-based (VibiumDev)

**Source**: GitHub API repository metadata (accessed 2026-03-24)

## Key Features

### Browser Control via Unified CLI

Vibium exposes a single command-line interface with semantic (non-CSS) element finding:

```bash
vibium go https://example.com           # Navigate to URL
vibium map                              # Map interactive elements → @e1, @e2, etc.
vibium find text "Sign In"              # Find by visible text
vibium find label "Email"               # Find by form label
vibium find role button                 # Find by ARIA role
vibium click @e1                        # Click using element reference
vibium fill @e2 "hello@example.com"     # Fill input field
vibium screenshot -o page.png           # Capture screenshot
vibium wait text "Success"              # Wait for text to appear
```

The `map` command returns an interactive element reference set (`@e1`, `@e2`, etc.), which are then used in subsequent commands. This reference model enables agents to reason about page state without needing CSS selectors.

**Source**: README.md "CLI Quick Reference" section (accessed 2026-03-24)

### Multi-Modal Client Libraries

Vibium provides client libraries for three languages, each with both async and sync APIs:

**JavaScript/TypeScript**:
```javascript
import { browser } from 'vibium'
const bro = await browser.start()
const vibe = await bro.page()
await vibe.go('https://example.com')
const png = await vibe.screenshot()
await bro.stop()
```

Or synchronous version:
```javascript
const { browser } = require('vibium/sync')
const bro = browser.start()
const vibe = bro.page()
vibe.go('https://example.com')
```

**Python** (async and sync):
```python
from vibium.async_api import browser
bro = await browser.start()
vibe = await bro.page()
await vibe.go("https://example.com")
```

**Java**:
```java
var bro = Vibium.start();
var vibe = bro.page();
vibe.go("https://example.com");
```

All three follow the same API shape and semantics, enabling code portability across languages.

**Source**: README.md "Language APIs" and client examples (accessed 2026-03-24)

### MCP Server for Claude Integration

Vibium ships as an MCP server for use with Claude Code and Gemini:

```bash
claude mcp add vibium -- npx -y vibium mcp
gemini mcp add vibium npx -y vibium mcp
```

This allows AI agents to invoke Vibium commands through the MCP tool interface, integrating browser automation into agent workflows.

**Source**: README.md "Alternative: MCP server" section (accessed 2026-03-24)

### Zero-Config Browser Management

Vibium downloads and manages Chrome automatically. Installation is declarative:

```bash
npm install vibium  # JavaScript
pip install vibium  # Python
# Maven/Gradle for Java
```

The browser cache is platform-specific:
- Linux: `~/.cache/vibium/`
- macOS: `~/Library/Caches/vibium/`
- Windows: `%LOCALAPPDATA%\vibium\`

Users can skip the download if managing Chrome separately:
```bash
VIBIUM_SKIP_BROWSER_DOWNLOAD=1 npm install vibium
```

**Source**: docs/tutorials/getting-started-js.md (accessed 2026-03-24)

### Page Recording and Capture

Vibium supports recording sessions and exporting page state:

```bash
vibium record start                   # Record session with screenshots
vibium record stop                    # Save to record.zip
vibium pdf -o page.pdf                # Export as PDF
vibium eval "document.title"          # Execute JavaScript
```

**Source**: README.md "CLI Quick Reference" (accessed 2026-03-24)

## Technical Architecture

### WebDriver BiDi Protocol Foundation

Vibium builds on WebDriver BiDi, a W3C standardized protocol that combines:

- **Bidirectional communication**: WebSocket-based JSON messaging (not request-response)
- **Real-time events**: Console logs, network requests, DOM changes pushed to the client as they occur
- **Cross-browser support**: Chrome, Firefox, Safari, and Edge all support BiDi through standards-based implementations

The protocol message format:

```json
{"id": 1, "method": "browsingContext.navigate", "params": {"url": "https://example.com"}}
```

The browser responds with results and pushes events:

```json
{"id": 1, "result": {"navigation": "123", "url": "https://example.com"}}
{"method": "log.entryAdded", "params": {"level": "error", "text": "Uncaught TypeError..."}}
```

Browser support status:
- Chrome/Chromium: Supported via chromedriver
- Firefox: Native support (no separate driver)
- Safari: In development
- Edge: Supported (Chromium-based)

**Source**: docs/explanation/webdriver-bidi.md (accessed 2026-03-24)

### Component Architecture

```
┌──────────────────────────────────┐
│      LLM / Agent                 │
│ (Claude Code, Gemini, etc.)      │
└──────────────────────────────────┘
    ▲                  ▲
    │ CLI (Bash)       │ MCP (stdio)
    ▼                  ▼
┌───────────────────────────────┐
│      Vibium binary (Go)       │
│                               │
│  ┌──────────────┐ ┌────────┐  │
│  │ CLI Commands │ │ MCP    │  │
│  │ (Cobra)      │ │ Server │  │
│  └─────┬────────┘ └──┬─────┘  │        ┌──────────────┐
│        └───────▲─────┘        │        │              │
│                │              │        │              │
│         ┌──────▼───────┐      │  BiDi  │ Chrome       │
│         │  BiDi Proxy  │      │◄──────►│ Browser      │
│         └──────────────┘      │        │              │
└───────────────────────────────┘        │              │
      ▲                                  └──────────────┘
      │ WebSocket BiDi :9515
      ▼
┌─────────────────────────────┐
│ Client Libraries            │
│ (js/ts | python | java)     │
│                             │
│ ┌────────────┐ ┌─────────┐  │
│ │ Async API  │ │ Sync    │  │
│ │await vibe. │ │ API     │  │
│ │go()        │ │vibe.go()│  │
│ └────────────┘ └─────────┘  │
└─────────────────────────────┘
```

**Core Go components**:
- `clicker/cmd/clicker/main.go`: Cobra-based CLI dispatcher registering 40+ commands (navigate, screenshot, find, click, fill, etc.)
- `clicker/internal/agent/server.go`: MCP server implementation
- `clicker/internal/api/`: HTTP API handlers for each command category (navigation, capture, elements, input, interaction, etc.)
- `clicker/internal/bidi/`: BiDi protocol client

**Source**: Glob results showing Go source structure, main.go function registrations (accessed 2026-03-24)

### JavaScript Client: Sync/Async Duality via SharedArrayBuffer

The JavaScript client provides both async (`await`) and sync (blocking) APIs using a sophisticated worker-thread + SharedArrayBuffer pattern. This enables synchronous code in scripts run by AI agents while the underlying implementation uses async WebSocket communication.

**Pattern**:
1. Main thread calls sync method: `bro.page()` → calls `SyncBridge.call('browser.page')`
2. Bridge creates a per-call `MessageChannel` and sends command to worker thread
3. Main thread blocks with `Atomics.wait(signal, 0, 0)` — sleeps until worker signals
4. Worker runs async code: `await browser.page()`
5. Worker posts result to per-call port and sets `signal[0] = 1`, calls `Atomics.notify`
6. Main thread wakes, reads result, returns it
7. User code: `const page = bro.page()` — no `await` needed

Signal protocol (2-slot `SharedArrayBuffer`):
- `signal[0]`: worker → main (`0` = idle, `1` = result ready, `2` = callback needed)
- `signal[1]`: reserved for future use

The bridge supports callbacks: when the worker needs main-thread decisions (e.g., route handlers deciding to abort requests), it sets `signal[0] = 2` and the main thread handles the callback before continuing.

**Source**: docs/explanation/sync-async-client-architecture.md (accessed 2026-03-24)

### Stateless CLI, Stateful API

The CLI (`vibium go ...`, `vibium click @e1`, etc.) can operate either:
1. **Daemon mode** (recommended for agents): Start once (`vibium start`), then send commands to a local HTTP API
2. **Direct mode** (for scripting): Each command launches a new process, but this incurs startup overhead

The API maintains session state (browser instance, pages, elements) indexed by integer IDs. Elements found by `vibium map` are stored and returned as references (`@e1`, `@e2`, etc.), which subsequent commands use.

**Source**: Glob results showing `daemon_cmd.go`, `daemon_client.go`, session management (accessed 2026-03-24)

## Installation & Usage

### Quick Start (JavaScript)

```bash
npm install vibium
node hello.js  # Run script using sync API
```

Full script:
```javascript
const fs = require('fs')
const { browser } = require('vibium/sync')

const bro = browser.start()
const vibe = bro.page()
vibe.go('https://example.com')

const png = vibe.screenshot()
fs.writeFileSync('screenshot.png', png)

const link = vibe.find('a')
link.click()

bro.stop()
```

### Agent Setup

```bash
npm install -g vibium
npx skills add https://github.com/VibiumDev/vibium --skill vibe-check
```

This installs the Vibium binary and downloads Chrome. The skill CLI reference is at `skills/vibe-check/SKILL.md` in the repo.

### MCP Server

```bash
claude mcp add vibium -- npx -y vibium mcp
```

### Python Installation

```bash
pip install vibium

# Async
from vibium.async_api import browser

# Sync (default)
from vibium import browser
```

### Java (Maven)

```xml
<dependency>
    <groupId>com.vibium</groupId>
    <artifactId>vibium</artifactId>
    <version>26.3.18</version>
</dependency>
```

All installations automatically download Chrome. No manual browser setup required.

**Source**: README.md "Agent Setup", "Language APIs", docs/tutorials/getting-started-js.md (accessed 2026-03-24)

## Platform Support

| Platform | Architecture | Status |
|----------|--------------|--------|
| Linux | x64 | Supported |
| macOS | x64 (Intel) | Supported |
| macOS | arm64 (Apple Silicon) | Supported |
| Windows | x64 | Supported |

**Source**: README.md "Platform Support" (accessed 2026-03-24)

## Relevance to Claude Code Development

### 1. Agent Browser Integration

Vibium enables Claude Code agents to:
- Navigate websites and extract information
- Fill forms and interact with web applications
- Capture screenshots for visual debugging
- Record interactions for replay or audit trails

The semantic finding (`find text "Sign In"`) is particularly relevant for agents because it requires no CSS selector knowledge — agents can reason about the page by visible text, labels, and ARIA roles.

**Source**: README.md "Why Vibium?" section emphasizing "AI-native" design (accessed 2026-03-24)

### 2. Skill-Based Architecture

Vibium is distributed as a Claude Code skill, making browser automation instantly available to agents once installed. The skill CLI interface (`vibium map`, `vibium click @e1`, etc.) is designed for shell-based agent workflows where commands are chained in bash scripts.

**Source**: README.md "Agent Setup" and skills/vibe-check/SKILL.md (accessed 2026-03-24)

### 3. MCP Server Pattern

The MCP server interface demonstrates how browser automation can be exposed via Model Context Protocol, enabling structured tool use and better LLM grounding than pure bash CLI commands. This is directly applicable to Claude Code's tool integration model.

**Source**: README.md "Alternative: MCP server" (accessed 2026-03-24)

### 4. Standards-Based Protocol

By using WebDriver BiDi instead of proprietary protocols, Vibium shows a path toward sustainable, vendor-neutral browser automation that won't be locked to Google or Microsoft. This aligns with Claude's emphasis on open standards.

**Source**: docs/explanation/webdriver-bidi.md (accessed 2026-03-24)

## Limitations and Caveats

### 1. WebDriver BiDi Coverage

While W3C-standardized, WebDriver BiDi is not yet complete. Firefox has native support, but Safari implementation is still in development. Advanced features (network interception, performance profiling) are less mature than CDP equivalents.

**Source**: docs/explanation/webdriver-bidi.md "Current Status" section (accessed 2026-03-24)

### 2. AI-Powered Locators Not Yet Available

The roadmap lists "AI-powered locators" as a future feature (3-6 weeks estimated effort after V1), noting that natural language element finding (`await vibe.do("click the login button")`) requires integration with a vision model (local like Qwen-VL or API like Claude vision), which adds complexity and cost.

**Source**: ROADMAP.md "AI-Powered Locators" section (accessed 2026-03-24)

### 3. No Persistent Navigation Memory

The roadmap defers "Cortex" (a SQLite-backed memory layer) as potentially YAGNI, since agents using Claude Code have conversation context. It's unclear if persistent app maps provide value over replaying interactions.

**Source**: ROADMAP.md "Cortex — Think Layer" section (accessed 2026-03-24)

### 4. Video Recording Deferred

Built-in screen recording is not yet implemented (deferred to avoid FFmpeg dependency complexity). Screenshots are the primary capture mechanism.

**Source**: ROADMAP.md "Video Recording" section (accessed 2026-03-24)

### 5. Recent Project (Early Production)

Vibium v1 was announced on 2025-12-11. The project is under active development with frequent releases (v26.3.18 as of 2026-03-24). Early adoption users should expect API stability improvements and potential breaking changes as the project matures.

**Source**: docs/updates/2025-12-11-v1-announcement.md (accessed 2026-03-24)

### 6. No Documented Limitations in Source

No official documentation explicitly lists performance limitations, browser compatibility edge cases, or known issues. The GitHub issues page lists 29 open issues (as of 2026-03-24) which may contain real-world constraints not documented in the README or tutorials.

**Source**: GitHub API repository metadata (accessed 2026-03-24)

## References

- [Vibium GitHub Repository](https://github.com/VibiumDev/vibium) — accessed 2026-03-24
- [README.md](https://github.com/VibiumDev/vibium/blob/main/README.md) — Overview, CLI reference, language APIs — accessed 2026-03-24
- [ROADMAP.md](https://github.com/VibiumDev/vibium/blob/main/ROADMAP.md) — Future features (Cortex, Retina, video recording, AI locators) — accessed 2026-03-24
- [docs/explanation/webdriver-bidi.md](https://github.com/VibiumDev/vibium/blob/main/docs/explanation/webdriver-bidi.md) — Protocol rationale and browser support matrix — accessed 2026-03-24
- [docs/tutorials/getting-started-js.md](https://github.com/VibiumDev/vibium/blob/main/docs/tutorials/getting-started-js.md) — JavaScript quick start — accessed 2026-03-24
- [docs/explanation/sync-async-client-architecture.md](https://github.com/VibiumDev/vibium/blob/main/docs/explanation/sync-async-client-architecture.md) — SharedArrayBuffer sync/async duality pattern — accessed 2026-03-24
- [clicker/cmd/clicker/main.go](https://github.com/VibiumDev/vibium/blob/main/clicker/cmd/clicker/main.go) — CLI command registration (Cobra) — accessed 2026-03-24

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [browsermcp-mcp.md](../mcp-ecosystem/browsermcp-mcp.md) | mcp-ecosystem | alternative MCP server approach: uses Chrome extension bridge vs WebDriver BiDi |
| [kernel-sh.md](./kernel-sh.md) | agent-infrastructure | competing browser-as-a-service: isolated VM instances vs local CLI/library approach |
| [tinyfish.md](./tinyfish.md) | agent-infrastructure | overlapping use case: serverless web agent API with AgentQL locators vs semantic text/label finding |
| [pinchtab.md](./pinchtab.md) | agent-infrastructure | alternative interaction model: accessibility tree snapshots vs full DOM and screenshot capture |
| [happycapy.md](./happycapy.md) | agent-infrastructure | shares agent-native browser interaction patterns; agent-computer interface vs browser automation |
| [claude-quickstarts.md](../developer-tools/claude-quickstarts.md) | developer-tools | reference implementation for browser automation with Claude; overlapping use case in agent workflows |
| [retio-pagemap.md](../mcp-ecosystem/retio-pagemap.md) | mcp-ecosystem | complements browser automation: token-efficient page representation for LLM processing |
| [gstack.md](../agent-frameworks/gstack.md) | agent-frameworks | similar element selection pattern: accessibility-based vs semantic text/label finding for agent browser QA |

## Freshness Tracking

**Last Reviewed**: 2026-03-24
**Next Review**: 2026-06-24 (3 months)

### Confidence by Section

- **Overview**: high — Full repository read, official documentation
- **Problem Addressed**: high — Detailed explanation in webdriver-bidi.md with historical context
- **Key Statistics**: high — Retrieved from GitHub API, dated 2026-03-24
- **Key Features**: high — Extracted directly from README CLI quick reference, code examples verified in documentation
- **Technical Architecture**: high — Full diagram and component structure from README, Go source structure confirmed via Glob
- **Installation & Usage**: high — Official tutorials read (getting-started-js.md)
- **Platform Support**: high — Official matrix from README
- **Relevance to Claude Code**: medium-high — Inferred from problem statement and architecture, explicit MCP reference in README
- **Limitations and Caveats**: medium — Roadmap deferred features are explicit, but GitHub issue list (29 items) not fully examined; early project status confirmed from release date
