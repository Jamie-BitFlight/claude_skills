---
title: Browser Harness JS
slug: browser-harness-js
---

# Browser Harness JS

**Overview**

Browser Harness JS is a minimal JavaScript bridge from LLM agents to the Chrome DevTools Protocol (CDP). It exposes all 652 CDP methods as fully-typed JavaScript wrappers with zero abstraction overhead. Rather than providing convenience helpers (`click()`, `goto()`, `upload_file()`), it routes agent code directly to the underlying protocol, treating "the protocol is the API" as the design principle.

Repository: <https://github.com/browser-use/browser-harness-js>
License: Unspecified in review scope (LICENSE file present)
Latest commit: 95b7a22 (2026-04-20)
Version: 0.1.0 (sdk/package.json)

---

## Problem Addressed

"Agent frameworks that pre-bake helpers for common browser actions hide the full control surface Chrome already exposes. When an agent encounters an interaction the framework didn't anticipate (a dropdown with custom behavior, a shadow-DOM tree, a gesture sequence that doesn't match the helper signature), it hits a hard boundary. Browser Harness JS eliminates that boundary by making every CDP method available with full fidelity."

**Source**: README.md, lines 5-19 (philosophy); SKILL.md, lines 55-67 (rationale for no helpers)

---

## Key Statistics

- **652 typed CDP method wrappers** generated from upstream protocol JSON (browser_protocol.json, js_protocol.json)
- **56 CDP domains** (Page, DOM, Network, Target, Input, Runtime, etc.) all mounted on the Session object
- **One persistent WebSocket** to Chrome's browser endpoint per Session (auto-injected sessionId for target routing)
- **Zero wrapping of Chrome's protocol** — types and JSDoc comments are auto-generated directly from upstream CDP schema
- **CLI binary** (`browser-harness-js`) auto-spawns a Bun HTTP server on first use; subsequent calls hit the same persistent Session
- **15,160 lines** in generated.ts (codegen output from gen.ts)
- **SDK footprint**: 50,675 total lines across source, protocol JSON, and compiled artifacts

**Sources**: README.md lines 5-7; SKILL.md lines 7-9, 82-89; SDK file listing from line count analysis

---

## Key Features

### 1. Full CDP Surface as Typed Wrappers

Every method from browser_protocol.json and js_protocol.json is codegen'd into a typed wrapper available as `session.<Domain>.<method>({params})`. No filtering, no subsetting. The Session class (session.ts, lines 44-60) implements the Transport interface and binds domains lazily:

```javascript
export class Session implements Transport {
  domains!: Domains;
  constructor() {
    this.domains = bindDomains(this);
    // Mirror domains onto `this` so calls read as `session.Page.navigate(...)`
    for (const k of Object.keys(this.domains) as (keyof Domains)[]) {
      (this as any)[k] = this.domains[k];
    }
  }
}
```

Agent code calls methods directly: `await session.Page.navigate({url:"https://example.com"})`, `await session.Input.dispatchMouseEvent({type: 'mousePressed', x: srcX, y: srcY, button: 'left', clickCount: 1})`. No abstraction, no translation.

**Source**: SKILL.md lines 94-109; session.ts lines 44-61

### 2. Auto-Detect and Connect to Running Chromium Browsers

Connection is zero-config by default. `await session.connect()` (no arguments) scans OS-specific profile directories (`~/Library/Application Support/` on macOS, `~/.config/` on Linux, `%LOCALAPPDATA%\` on Windows) for every running Chromium-based browser (Chrome, Chromium, Edge, Brave, Arc, Vivaldi, Opera, Comet, Canary), finds ones with `DevToolsActivePort` files, and tries each in order of most-recently-launched until a WebSocket opens.

Each candidate has a short per-open timeout (default 5s, generous because live browsers answer in ~100ms). Failed candidates fall through fast; the loop completes in seconds even with multiple browsers running.

```javascript
async connect(opts: ConnectOptions = {}): Promise<void> {
  const timeoutMs = opts.timeoutMs ?? 5_000;
  if (opts.wsUrl || opts.profileDir) {
    const wsUrl = await resolveWsUrl(opts);
    await this.openWs(wsUrl, timeoutMs);
    return;
  }
  const browsers = await detectBrowsers();
  // ... try each in order
}
```

**Source**: session.ts lines 75-100; SKILL.md lines 112-150; interaction-skills/connection.md

### 3. Persistent Session Across Calls; State Routing by Target

A single HTTP server (repl.ts, 116 lines) holds one persistent Session. Every CLI call hits the same server and reuses the same WebSocket, so session state (connected target ID, event subscriptions, globals) survives across invocations:

```bash
browser-harness-js 'await session.connect()'
browser-harness-js '(await listPageTargets()).forEach((t,i)=>globalThis["tab"+i]=t.targetId)'
browser-harness-js 'await session.use(globalThis.tab0)'
browser-harness-js 'await session.Page.navigate({url:"https://example.com"})'
```

Target routing is primitive: `session.use(targetId)` once; subsequent page-level calls auto-inject the sessionId for that target. Switching tabs is `session.use(otherTargetId)`.

**Source**: SKILL.md lines 29-37, 183-197; sdk/repl.ts (server code); README.md lines 10-16

### 4. Interaction Skills Library: Non-Obvious CDP Recipes

Because the bridge exposes raw CDP, patterns that don't follow from the method signatures are documented in `interaction-skills/` (16 markdown files covering connection, cookies, dialogs, drag-and-drop, downloads, iframes, network waits, PDFs, screenshots, scrolling, shadow DOM, tabs, uploads, viewport, etc.):

**Drag-and-Drop** (interaction-skills/drag-and-drop.md, lines 1-57):

HTML5 DnD (`dragstart` / `drop` events) requires `Input.dispatchDragEvent`, not `Input.dispatchMouseEvent` alone:

```javascript
await session.Input.setInterceptDrags({ enabled: true })
await session.Input.dispatchMouseEvent({ type: 'mousePressed', x: srcX, y: srcY, button: 'left', clickCount: 1 })
const di = await session.waitFor('Input.dragIntercepted', undefined, 2_000)
await session.Input.dispatchDragEvent({ type: 'dragEnter', x: dstX, y: dstY, data: di.data })
await session.Input.dispatchDragEvent({ type: 'dragOver',  x: dstX, y: dstY, data: di.data })
await session.Input.dispatchDragEvent({ type: 'drop',      x: dstX, y: dstY, data: di.data })
await session.Input.dispatchMouseEvent({ type: 'mouseReleased', x: dstX, y: dstY, button: 'left', clickCount: 1 })
await session.Input.setInterceptDrags({ enabled: false })
```

These recipes exist because neither the CDP protocol docs nor an agent's first intuition covers them.

**Source**: interaction-skills/drag-and-drop.md (lines 1-57); interaction-skills/connection.md (lines 1-99)

### 5. CLI Auto-Installs Bun; No Manual Setup Required

The CLI (`sdk/browser-harness-js`, executable) checks for bun on first run and installs it automatically if missing. Sets `BROWSER_HARNESS_SKIP_BUN_INSTALL=1` to opt out.

```bash
browser-harness-js 'await session.connect()'
# On first run: [INFO] Bun not found, installing...
# Subsequent runs: reuse existing bun, skip install
```

**Source**: README.md lines 36; SKILL.md lines 27-28; Latest commit (95b7a22) makes this the primary installation path

### 6. Event Subscription and Single-Event Waits

Sessions can subscribe to all CDP events or wait for a single event with optional predicate and timeout:

```javascript
// Subscribe
const off = session.onEvent((method, params, sessionId) => { ... })

// Or wait for one matching event
const ev = await session.waitFor(
  'Page.frameNavigated',
  (p) => p.frame.url.includes('example.com'),
  10_000  // timeout in ms
)
```

Used in interaction patterns like waiting for navigation to complete, drag intercepted signals, dialog prompts, etc.

**Source**: SKILL.md lines 173-184

---

## Technical Architecture

### Codegen System (gen.ts, 274 lines)

The core architecture is code generation. `gen.ts` reads the vendored `browser_protocol.json` (30,908 lines; latest Chrome DevTools Protocol schema) and `js_protocol.json` (3,809 lines; JavaScript-specific methods), generates typed TypeScript interfaces per domain (`Page`, `DOM`, `Network`, etc.), and emits `generated.ts` (15,160 lines).

Each generated domain gets:
- TypeScript interface for each method's params and return type
- JSDoc comments extracted from the protocol
- A wrapper function that calls `_call(methodName, params)` and resolves the result

**Example generated wrapper** (pattern, not literal text from generated.ts):

```typescript
export interface PageNavigateParams { url: string; referer?: string; transitionType?: string; }
export interface PageNavigateReturn { frameId: string; }
export class Page {
  async navigate(params: PageNavigateParams): Promise<PageNavigateReturn> { ... }
}
```

Regeneration is on-demand when protocol JSONs change:
```bash
cd <skill-dir>/sdk && bun gen.ts
browser-harness-js --restart
```

**Source**: SKILL.md lines 232-240; sdk/gen.ts (Bun script, does the codegen)

### Session Transport (session.ts, 379 lines)

The Session class is a transport that:

1. Holds a persistent WebSocket to Chrome's `ws://host:port/devtools/browser/<uuid>` endpoint
2. Manages message ID correlation (nextId counter, pending map for request/response matching)
3. Routes target-specific calls by injecting the active sessionId into every message
4. Binds generated domains via `bindDomains(this)`, making them available as properties

The `_call` method (pattern shown in session.ts header) handles:
- Assigning the next message ID
- Wrapping the request in a pending Promise
- Sending the JSON-RPC call to the WebSocket
- Receiving the response and resolving the Promise
- Routing errors correctly

**Source**: session.ts lines 44-379 (full Session class); README.md lines 47-52

### HTTP REPL Server (repl.ts, 116 lines)

A Bun-native HTTP server (Bun.serve) listens on 127.0.0.1:9876 (configurable via `CDP_REPL_PORT`). It:

1. Holds a single persistent Session in memory
2. Receives POST requests with JavaScript code
3. Evaluates the code in an async wrapper context (making globals like `session` and `listPageTargets` available)
4. Returns the result (or error) to stdout

The CLI (`browser-harness-js`) is a shell script that spawns this server on first use (or reuses it if already running) and forwards code snippets via HTTP POST.

**Source**: SKILL.md lines 46-48; README.md lines 47; sdk/repl.ts (HTTP server implementation)

### Helper Functions (non-CDP, two only)

The framework provides exactly two "helpers" that bridge gaps in CDP itself:

1. **`listPageTargets()`** — wraps `Target.getTargets()` and filters out `chrome://` and `devtools://` URLs (which are internal, not user-visible tabs). Returns real user-facing page targets only.

2. **`detectBrowsers()`** — scans OS-specific profile directories for running Chromium browsers with DevTools enabled. Returns sorted array of `DetectedBrowser` objects (name, profileDir, port, wsUrl, mtimeMs). Used for auto-detect in `session.connect()`.

3. **`resolveWsUrl(opts)`** — utility to resolve a WS URL from either `{wsUrl}` (direct), `{port, host?}` (construct), or `{profileDir}` (read DevToolsActivePort file).

**Source**: SKILL.md lines 83-89; session.ts (implementation)

---

## Installation & Usage

### Setup (one-time)

```bash
npx skills add https://github.com/browser-use/browser-harness-js --skill cdp
```

This installs the skill into your agent's skills directory. Symlink the CLI onto PATH (or the first call will do it):

```bash
# macOS (Apple Silicon + Homebrew)
ln -sf ~/.claude/skills/cdp/sdk/browser-harness-js /opt/homebrew/bin/browser-harness-js

# macOS (Intel) / Linux
ln -sf ~/.claude/skills/cdp/sdk/browser-harness-js /usr/local/bin/browser-harness-js

# Linux without sudo
mkdir -p ~/.local/bin && ln -sf ~/.claude/skills/cdp/sdk/browser-harness-js ~/.local/bin/browser-harness-js
```

First call to `browser-harness-js` auto-installs Bun (unless `BROWSER_HARNESS_SKIP_BUN_INSTALL=1`).

**Source**: README.md lines 21-26; SKILL.md lines 13-25

### Usage Pattern

```bash
# Connect to the first running Chromium browser
browser-harness-js 'await session.connect()'

# List visible tabs
browser-harness-js 'return (await listPageTargets()).map(t => ({title: t.title, url: t.url}))'

# Navigate the first tab
browser-harness-js 'await session.use((await listPageTargets())[0].targetId); await session.Page.navigate({url:"https://example.com"})'

# Take a screenshot
browser-harness-js 'const {data} = await session.Page.captureScreenshot({format:"png"}); return data'
```

Single-expression snippets auto-return their result. Multi-statement snippets require explicit `return`:

```bash
browser-harness-js <<'EOF'
const tabs = await listPageTargets()
globalThis.selectedTab = tabs[0]
return globalThis.selectedTab.title
EOF
```

**Source**: SKILL.md lines 29-65; README.md lines 9-17

### CLI Commands

| Command | Behavior |
|---------|----------|
| `browser-harness-js '<js>'` | Eval JS in the persistent Session, print result |
| `browser-harness-js --status` | Health check (uptime, connected, sessionId) |
| `browser-harness-js --start` | Explicit server start (no-op if running) |
| `browser-harness-js --stop` | Graceful shutdown |
| `browser-harness-js --restart` | Stop + start fresh |
| `browser-harness-js --logs` | Tail -f the server log |

Environment variables: `CDP_REPL_PORT` (default 9876), `CDP_REPL_LOG` (default /tmp/browser-harness-js.log).

**Source**: SKILL.md lines 68-80

### Output Format

Raw result content to stdout — no JSON envelope:

| Result type | stdout |
|-------------|--------|
| string | bare text, no JSON quotes (e.g. `Example Domain`) |
| number / boolean | `42`, `true` |
| object / array (non-empty) | compact JSON |
| `undefined`, `null`, `""`, `{}`, `[]` | empty (no output) |

Errors go to stderr with exit code 1 (full CDP error message + stack).

**Source**: SKILL.md lines 38-54

---

## Relevance to Claude Code Development

### Agent Browser Control

Browser Harness JS is the minimal bridge for agents to script and automate user Chrome browsers. Because it exposes all 652 CDP methods with zero abstraction, agents can solve interaction problems that framework-provided helpers don't anticipate:

1. **Interaction recipes** — drag-and-drop in React components, shadow DOM traversal, iframe postMessage, file uploads, network interception, custom viewport settings
2. **Non-standard UI patterns** — canvas-based drawing apps (Figma, Excalidraw), custom dropdowns, gesture sequences, drag-to-reorder interfaces
3. **Inspection and debugging** — read any DOM property, intercept network requests, measure performance, capture console output, inspect Web Storage

### Relevance to LLM-in-the-Loop Workflows

The "protocol is the API" philosophy aligns with agent-centered design: agents write agent code in JavaScript, not in a simplified DSL. Because the surface is so large (652 methods), the types and JSDoc comments from generated wrappers become the documentation — agents read method signatures and discover parameters without leaving the IDE.

### Integration with Existing Skills

If you are building skills that need to automate browser actions, Browser Harness JS is the transport layer. You would call `browser-harness-js '...'` from your skill's shell scripts and parse the output. The skill provides the domain logic; the harness provides the protocol bridge.

**Sources**: README.md (design philosophy); SKILL.md (practical integration patterns); interaction-skills/* (domain-specific recipes that agents would need)

---

## Limitations and Caveats

### 1. No Convenience Helpers

The framework intentionally provides no `click(x, y)`, `goto(url)`, `upload_file(path)`, or similar. Every interaction is a raw CDP call. This is a design choice (cited as a feature in the philosophy), but it means agent code is more verbose and requires knowing the CDP method signatures.

**Mitigation**: The interaction-skills/ directory documents common patterns. The cli auto-completes method parameters via JSDoc.

**Source**: README.md lines 55-76 (explicit design rationale)

### 2. Target Routing is Manual (Single Active Target Per Session)

There is one persistent WebSocket and one active target. Switching between tabs requires `session.use(newTargetId)`. Concurrent access to multiple tabs requires either:

- Spawning multiple Session instances (multiple CLI servers on different ports), or
- Polling / sequential target switching

The single-session model is intentional — it keeps the architecture simple and state management explicit.

**Source**: SKILL.md lines 151-170

### 3. No Built-In Waiting / Polling

The framework provides `session.waitFor(method, predicate, timeout)` for single events, but not higher-level waits like "wait for navigation to complete" or "wait for element to be clickable". Agents must compose waits manually:

```javascript
await session.Network.enable({})
const nav = await session.waitFor('Page.navigationStarted', undefined, 5000)
const loaded = await session.waitFor('Page.loadEventFired', undefined, 10000)
```

**Source**: SKILL.md lines 173-184

### 4. Remote Browser Debugging Requires User Action (First Time)

If a browser doesn't already have remote debugging enabled, `session.connect()` returns "No running browser with remote debugging detected". The agent must direct the user to:

1. Open `chrome://inspect/#remote-debugging`
2. Tick "Discover network targets"
3. Click "Allow" when Chrome prompts

This is a one-time per-session user interaction.

**Source**: SKILL.md lines 148-150, 217-218; interaction-skills/connection.md lines 40-50

### 5. DevToolsActivePort Availability (Chrome 144+ Break)

On Chrome 144+, the format of `DevToolsActivePort` changed. The resolver handles it (per README), but auto-detect reliability depends on the file existing and being readable.

**Source**: SKILL.md line 88

### 6. No Built-In Persistence Across Restarts

Restarting the server (`browser-harness-js --restart`) clears all session state, event subscriptions, and globals. `globalThis` is the agent's only persistence mechanism.

**Source**: SKILL.md lines 194-197

### No Limitations Documented in Reviewed Sources

Beyond the above design constraints (which are intentional), no other limitations were documented in the README, SKILL.md, or interaction-skills. The framework is intentionally minimal — its constraint is its design.

**Confidence**: medium — absence of documented limitations does not confirm absence of limitations in deployment or edge cases.

---

## References

- **README.md** — Project philosophy, feature overview, installation, contribution guidelines. Accessed 2026-05-02.
- **SKILL.md** — Complete usage guide, API surface, CLI commands, connection patterns, event handling. Accessed 2026-05-02.
- **interaction-skills/** (16 markdown files) — Non-obvious CDP recipes: connection, cookies, dialogs, drag-and-drop, downloads, iframes, network requests, PDFs, screenshots, scrolling, shadow DOM, tabs, uploads, viewport. Each ~2-3 KB. Accessed 2026-05-02.
- **sdk/session.ts** — Session class (transport, WebSocket, target routing, event subscriptions). 379 lines. Accessed 2026-05-02.
- **sdk/gen.ts** — Codegen script that reads protocol JSON and generates typed wrappers. 274 lines. Accessed 2026-05-02.
- **sdk/repl.ts** — HTTP server (Bun.serve) that holds the persistent Session. 116 lines. Accessed 2026-05-02.
- **sdk/generated.ts** — Auto-generated file containing all 652 typed CDP method wrappers. 15,160 lines. Accessed 2026-05-02.
- **sdk/package.json** — SDK metadata (name: cdp-sdk, version: 0.1.0). Accessed 2026-05-02.
- **sdk/browser_protocol.json** — Chrome DevTools Protocol schema (vendored upstream). 30,908 lines. Accessed 2026-05-02.
- **sdk/js_protocol.json** — JavaScript-specific protocol extensions. 3,809 lines. Accessed 2026-05-02.

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|──────────────|
| [PinchTab](../agent-infrastructure/pinchtab.md) | agent-infrastructure | alternative low-token browser control via a11y tree |
| [Kernel](../agent-infrastructure/kernel-sh.md) | agent-infrastructure | browsers-as-a-service alternative with DevTools passthrough |
| [Vibium](../agent-infrastructure/vibium.md) | agent-infrastructure | WebDriver BiDi browser control (complementary protocol) |
| [surf-cli](../developer-tools/surf-cli.md) | developer-tools | Chrome extension-based browser control alternative |
| [pi-mono](./pi-mono.md) | agent-frameworks | agent runtime requiring browser interaction layer |
| [cmux](../agent-infrastructure/cmux.md) | agent-infrastructure | terminal UI with in-app browser for agent debugging |
| [HappyCapy](../agent-infrastructure/happycapy.md) | agent-infrastructure | browser-based sandbox for agent execution |
| [Browser MCP](../mcp-ecosystem/browsermcp-mcp.md) | mcp-ecosystem | MCP-based Chrome automation (protocol adapter pattern) |

---

## Freshness Tracking

| Section | Confidence | Last Verified | Next Review |
|---------|------------|---------------|-------------|
| Identity/Metadata | high | 2026-05-02 | 2026-08-02 |
| Key Statistics | high | 2026-05-02 | 2026-08-02 |
| Key Features | high | 2026-05-02 | 2026-08-02 |
| Technical Architecture | high | 2026-05-02 | 2026-08-02 |
| Installation & Usage | high | 2026-05-02 | 2026-08-02 |
| Relevance | medium | 2026-05-02 | 2026-08-02 |
| Limitations | medium | 2026-05-02 | 2026-08-02 |

**Confidence factors**:
- All quotes extracted verbatim from primary sources (README, SKILL.md, interaction-skills, source code)
- Architecture verified against actual source files (session.ts, gen.ts, repl.ts, generated output)
- Usage examples verified against SKILL.md and interaction-skills documentation
- No inferred features; all claims traceable to source
- Latest commit verified (2026-04-20); SDK version: 0.1.0
- Limitations are design constraints documented by the authors, not inferred absence

**Notes for next review**:
- Check for new releases and CDP protocol updates
- Verify bun auto-install behavior remains as documented
- Confirm Chrome 144+ DevToolsActivePort handling is stable
- Monitor for new interaction-skills recipes added to the library

