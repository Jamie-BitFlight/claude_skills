---
name: TUI/Web interface for large interactive checklists and project tree editing
description: "AskUserQuestion is limited to 3-5 questions per screen, which is insufficient when Claude needs to present large option sets to the user — e.g., filling in project templates with selective add/remove of components, displaying a project tree where the user can append or remove entries, or presenting screenshots and gathered images as selectable options for feedback.\n\nProblem: No mechanism exists for Claude to present a scrollable, interactive checklist or tree view where users can toggle items on/off, add custom entries, or browse visual options. Current workaround is multiple rounds of AskUserQuestion which is slow and loses context.\n\nSuccess looks like: Claude can present a project scaffold tree (or similar large structured list) in a TUI or web panel, the user can check/uncheck items, add new entries, remove unwanted ones, and submit the result back to Claude in a single interaction. Images/screenshots can be displayed as option cards.\n\nHow to verify: A skill or tool can render 20+ items in a single interactive view, user can modify the selection, and the result is returned to Claude as structured data.\n\nResearch first:\n? How does CopilotKit (research/agent-frameworks/copilotkit.md) handle agent-driven UI rendering and user feedback loops?\n? How does JSON Render (research/agent-frameworks/json-render.md) handle dynamic form/tree generation from agent output?\n? What TUI frameworks (textual, rich, blessed) support checkbox trees with real-time agent communication?"
metadata:
  topic: tuiweb-interface-for-large-interactive-checklists-and-projec
  source: User request
  added: '2026-03-05'
  priority: P1
  type: Feature
  status: open
  issue: '#437'
  last_synced: '2026-03-10T06:56:17Z'
  groomed: '2026-03-05'
---

## Story

As a **developer**, I want **AskUserQuestion is limited to 3-5 questions per screen, which is insufficient...** so that **backlog items are tracked in GitHub**.

## Description

AskUserQuestion is limited to 3-5 questions per screen, which is insufficient when Claude needs to present large option sets to the user — e.g., filling in project templates with selective add/remove of components, displaying a project tree where the user can append or remove entries, or presenting screenshots and gathered images as selectable options for feedback.

Problem: No mechanism exists for Claude to present a scrollable, interactive checklist or tree view where users can toggle items on/off, add custom entries, or browse visual options. Current workaround is multiple rounds of AskUserQuestion which is slow and loses context.

Success looks like: Claude can present a project scaffold tree (or similar large structured list) in a TUI or web panel, the user can check/uncheck items, add new entries, remove unwanted ones, and submit the result back to Claude in a single interaction. Images/screenshots can be displayed as option cards.

How to verify: A skill or tool can render 20+ items in a single interactive view, user can modify the selection, and the result is returned to Claude as structured data.

Research first:
? How does CopilotKit (research/agent-frameworks/copilotkit.md) handle agent-driven UI rendering and user feedback loops?
? How does JSON Render (research/agent-frameworks/json-render.md) handle dynamic form/tree generation from agent output?
? What TUI frameworks (textual, rich, blessed) support checkbox trees with real-time agent communication?

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: User request
- **Priority**: P1
- **Added**: 2026-03-05
- **Research questions**: None

## Fact-Check

**Claims checked**: 5
**VERIFIED**: 3 | **REFUTED**: 0 | **INCONCLUSIVE**: 2

| Claim | Verdict | Source |
|-------|---------|--------|
| No native Claude Code mechanism exists for scrollable, interactive checklist/tree views | VERIFIED | Claude Code tool inventory (AskUserQuestion, Bash, Read, Write, Edit) — no interactive TUI component exists SOURCE: Claude Code tool definitions, 2026-03-05 |
| CopilotKit handles agent-driven UI rendering and user feedback loops | VERIFIED | `useCopilotAction` render pattern, human-in-the-loop checkpoints, bi-directional state sync SOURCE: research/agent-frameworks/copilotkit.md (accessed 2026-02-23) |
| JSON Render handles dynamic form/tree generation from agent output | VERIFIED | Catalog+Zod schema system constrains AI to a defined component vocabulary; `defineCatalog` + `@json-render/shadcn` (39 pre-built components) covers interactive form generation SOURCE: research/agent-frameworks/json-render.md (accessed 2026-02-26) |
| AskUserQuestion is limited to 3-5 questions per screen | INCONCLUSIVE | The practical limitation on option count is observed behavior; the exact "3-5" number is not documented in official Claude Code sources. The broader claim (insufficient for 20+ items) is consistent with observed behavior. |
| TUI frameworks (textual, rich, blessed) support checkbox trees with real-time agent communication | INCONCLUSIVE | Textual (Textualize) has documented Checkbox and Tree widget support for interactive terminals. Rich is display-only (not interactive). Blessed is JavaScript (not Python). The claim bundles mismatched tools. "Real-time agent communication" mechanism is unspecified — no research file confirms IPC pattern. |

**Refuted claims**: None
**Inconclusive claims**: "3-5 questions limit" (unverified number); "textual, rich, blessed" bundle (rich is not interactive; blessed is JS)

## RT-ICA

**Goal**: Enable Claude to present 20+ items in a single interactive view where users can toggle, add, remove, and submit results as structured data in one round-trip, with routing across desktop web, TUI, and phone contexts.

**Conditions**:

1. Claude Code's AskUserQuestion is insufficient for 20+ item interactive selection | **AVAILABLE** | Observed behavior; item description and fact-check confirm the problem
2. Claude Code's Bash tool can launch external processes (TUI or web server) | **AVAILABLE** | Bash tool launches any shell command
3. A Python TUI framework (e.g., Textual) supports checkbox trees and tree editing | **DERIVABLE** | Textual has documented Checkbox and Tree widget support; specific checkbox-tree + IPC pattern requires validation
4. A mechanism exists for returning structured JSON from TUI/web UI back to Claude | **MISSING** | No design covers the IPC return path. `cindy2000sh/claude-ntfy` (Shell, reply-from-phone) uses ntfy.sh subscribe loop — pattern worth studying, but Claude Code IPC contract undefined
5. CopilotKit or json-render could serve as the web UI layer | **DERIVABLE** | Both frameworks support interactive component rendering; neither is purpose-built for CLI-to-browser round-trip; integration pattern requires design
6. The solution integrates as a Claude Code skill/tool invocable from any skill | **MISSING** | No integration contract defined (tool name, invocation API, return schema)
7. Images and screenshots can be displayed as selectable option cards | **DERIVABLE** | Web renderer can display images natively; ntfy.sh supports image attachments; terminal rendering requires research
8. Phone notification backend (ntfy.sh or equivalent) is available and proven in Claude Code context | **AVAILABLE** | `cyanheads/ntfy-mcp-server` (MCP, 14 stars) and `cindy2000sh/claude-ntfy` (Shell, reply support) both exist and are active. Apprise provides unified API covering ntfy, Pushover, Slack, Teams SOURCE: GitHub API, 2026-03-05
9. TUI + Web dual-mode co-existence pattern has prior art in Claude Code ecosystem | **AVAILABLE** | `uppinote20/clavis` (Rust, TUI+Web, Claude Code admin) and `FlorianBruniaux/ccboard` (TUI 9 tabs + Web) demonstrate the pattern SOURCE: GitHub API, 2026-03-05
10. Routing layer context detection (desktop vs remote vs tmux) is feasible | **DERIVABLE** | Standard Unix env vars ($TMUX, $SSH_TTY, $DISPLAY) provide signal basis; heuristics have known edge cases; named profile override is the robust fallback. No existing tool provides this for Claude Code specifically
11. Apprise can serve as unified connection layer backend for non-interactive channels | **DERIVABLE** | README confirms broad multi-service coverage (Telegram, Discord, Slack, SNS, Gotify, etc.); Python library API suitable for embedding; exact backend count and ntfy-specific URL scheme require validation

**Decision**: APPROVED — conditions 4 and 6 remain MISSING but are planning-phase design decisions, not blockers to starting architecture work. New research (conditions 8, 9, 11) upgrades phone adapter and TUI+Web pattern from MISSING to AVAILABLE/DERIVABLE, reducing architecture phase risk.

**Missing inputs for planning** (unchanged + refined):
- (4) IPC return path: how structured JSON flows from renderer back to Claude Code session
- (6) Skill integration contract: tool name, invocation API, return schema, blocking behavior
- (10) Context detection: heuristic vs named profile — edge case coverage needs empirical testing

## Groomed (2026-03-05)

### Priority

8/10 — Unblocks large-scale interactive workflows that currently require 5+ sequential AskUserQuestion rounds. High impact on user experience for project scaffolding, template filling, and visual feedback loops. Currently no mechanism exists; workaround is slow and loses context across rounds.

### Impact

- Blocks: Any Claude Code skill that needs to present 20+ items for user selection/modification in a single interaction
- Bottleneck: Project template scaffolding, dependency selection, tree-based configuration, visual option browsing
- Affects: Skills built around structured decision-making (e.g., plugin-creator, project-init workflows)

### Benefits

- Single round-trip interaction for large option sets instead of 5+ sequential prompts
- Preserve full context across user selections
- Structured return value (JSON) integrates cleanly with Claude Code tools
- Enables visual feedback loops (screenshots, images as selectable cards)
- Foundation for interactive project tree editing workflows

### Expected Behavior

Claude can invoke an interactive UI component (TUI or web) from within a skill execution context. The component:
- Renders 20+ items in a scrollable view
- Allows user to toggle, add, remove, or reorder items
- Returns structured result (JSON or Python dict) to Claude automatically
- Blocks skill execution until user submits result (synchronous interaction model)
- Optionally displays images/screenshots as selectable cards alongside text options

### Desired Structure

A Claude Code skill or tool that acts as a bridge between Claude and an interactive UI system. Architecture decisions (TUI vs web, framework choice, IPC method) are open and will be determined during planning. Target outcome:
- **Tool invocation**: `Tool(tool: "interactive-select", items: [...], config: {...})` or `Skill(skill: "interactive-select", args: "...")`
- **Return contract**: Structured JSON result with selected items, added items, removed items, or reordered state
- **Integration**: Works from any skill context, returns data to Claude for further processing
- **State management**: No persistent state between invocations; each call is stateless

### Acceptance Criteria

1. Can render a list of 20+ items in a single view (not paginated via AskUserQuestion prompts)
2. User can toggle items on/off (checkbox interaction) without exiting the view
3. User can add custom entries to the list during interaction
4. User can remove entries from the list during interaction
5. Final result is returned to Claude as structured data (JSON dict or equivalent)
6. Result is deterministic and repeatable (same selections -> same output)
7. Interaction completes in under 30 seconds for typical 20-50 item lists
8. Tool/skill loads without external dependencies not already in Claude Code environment

### Questions for Human

- **Scope priority**: Would TUI (terminal-based, no browser) be acceptable, or is web UI required?
  - TUI enables faster integration but requires tmux/pty handling; web requires local HTTP server or WebSocket

- **Image support**: Must images/screenshots be displayed as option cards, or is text-only sufficient for first version?
  - Image support requires image loading and caching; adds complexity but unlocks visual feedback workflows

- **Return binding**: Should the result automatically resume skill execution, or does the skill need explicit code to parse and continue?
  - Automatic binding (tool blocks until result arrives) vs manual binding (skill polls for result) affects integration complexity

- **Persistence model**: Should the UI support "save and resume later" (with serialized state), or is session-scoped interaction sufficient?
  - Session-only is simpler; persistence enables multi-session workflows

### Resources

| Type | Item |
|------|------|
| Research | [CopilotKit](../../research/agent-frameworks/copilotkit.md) — React/TypeScript framework for agent-driven UI with bi-directional state sync |
| Research | [json-render](../../research/agent-frameworks/json-render.md) — Generative UI framework with catalog constraints and streaming support |
| Skill | agent-browser — existing skill for rendering and browser interaction |
| Prior work | plugins/development-harness/agents/service-docs-maintainer.md — example of complex UI workflows in SAM |

### Dependencies

- Depends on: None
- Blocks: Any P1/P2 items requiring interactive checklist workflows (future items, not yet backlogged)

### Blockers

None. RT-ICA decision is APPROVED. Missing inputs (IPC mechanism, skill integration contract, image display method) are planning-phase decisions, not prerequisites for grooming.

### Effort

Medium — Proof of concept (TUI with Textual + stdout capture) is achievable in 2-3 days. Full web UI variant (CopilotKit/json-render integration) requires Node.js setup and is 4-5 days. Image support adds 1-2 days. Integration as reusable skill adds 1-2 days. Effort scales with scope decisions.

### Issue Classification

**Type**: unbounded-design
**Rationale**: This is a capability gap with multiple valid implementation paths. No failure chain, no recurring defect, no missing guardrail. The problem is well-scoped but the solution space is open (TUI vs web vs hybrid).
**Analysis Method**: design-framing
**Scenario Target**: Claude needs to present 20+ item checklist/project tree for user selection → user completes interaction in one round-trip → structured result returned to Claude

### Decision

**Return binding model**: Background subagent pattern.

The interactive UI runs as a background subagent (`Agent(run_in_background=True)`). The subagent:
1. Launches the renderer backend via the routing layer
2. Blocks internally until the user submits
3. Returns structured JSON result to the orchestrator on completion

The orchestrating Claude instance is free to continue other work while the user interacts. Notification is automatic — no polling, no manual IPC.

---

**Renderer architecture**: Pluggable backend with connection + routing layers.

```
Claude (orchestrator)
    │
    └─ Interaction Agent (background subagent)
           │
    ┌──────▼──────────────────────────────────┐
    │         Routing Layer                   │
    │  selects renderer from config/context   │
    └──────┬──────────────────────────────────┘
           │
    ┌──────▼──────────────────────────────────┐
    │         Connection Layer                │
    │  transport adapters (stdio, HTTP, WS,   │
    │  Slack API, Teams webhook, notify.io)   │
    └──────┬──────────────────────────────────┘
           │
    ┌──────▼──────────────────────────────────┐
    │         Renderer Backends               │
    │  Web │ TUI │ Slack │ Teams │ Phone/Push │
    └─────────────────────────────────────────┘
```

**Renderer capability matrix** (confirmed by user, 2026-03-05):

| Feature | TUI | Web | Slack/Teams | notify.io/Push |
|---------|-----|-----|-------------|----------------|
| Interactive checklist (toggle) | ✓ | ✓ | ✓ (blocks/reactions) | - |
| Long list / fuzzy lookup | ✓ | ✓ | ~ (limited) | - |
| Long file presentation | ✓ | ✓ | - | - |
| Layout / layup design | ✓ | ✓ | - | - |
| Image / screenshot cards | - | ✓ | ✓ | ✓ |
| Inline add / remove entries | ✓ | ✓ | ~ | - |
| Push notification | - | - | ✓ | ✓ |
| Async / non-blocking response | - | ✓ | ✓ | ✓ |

**Image support**: Required in v1 (web renderer only). Screenshot/image display as selectable option cards.

---

**Implementation sequencing** (confirmed by user, 2026-03-05):

1. **Architecture phase first** — the pluggable connection + routing layer requires dedicated planning cycles before any renderer work begins. The connection contract must be stable before web or any future adapter is built against it.
2. **Web renderer (v1)** — implemented against the stable connection contract. Web-only; TUI deferred to v2.
3. **Additional adapters (v2+)** — Slack, Teams, TUI, notify.io/push — each a new connection adapter only, no routing changes.

The architecture phase is a hard prerequisite. Do not begin web renderer implementation until the connection contract is finalized.

---

**Remaining open questions for architecture phase**:
- Routing selection mechanism — config file, env var, auto-detect from context, or explicit Claude parameter?
- Connection layer serialization format — JSON over stdio, HTTP/SSE, or WebSocket?
- Slack/Teams adapter contract — specify in v1 architecture even if implementation is v2?
- Connection layer identity/session model — how does Claude correlate a submitted result to the originating request across async boundaries?

### Scope

**Phase 0 — Architecture (prerequisite, must complete before Phase 1)**:
- Design the pluggable connection + routing layer
- Define the renderer adapter contract/interface
- Define the serialization format and session/correlation model
- Specify the Slack/Teams connection contract (even if implementation is v2)
- Output: architecture spec consumed by all subsequent phases

**Phase 1 — v1 implementation (web renderer only)**:
- Routing layer — selects renderer; enforces adapter contract
- Connection layer — HTTP + WebSocket transport; JSON serialization
- Web renderer — interactive checklists, fuzzy lookup, long list/file presentation, image/screenshot option cards
- Background subagent integration — `Agent(run_in_background=True)`; structured JSON returned on submit

**Phase 2 — v2 adapters (designed-in, not implemented in v1)**:
- TUI renderer (terminal via tmux PTY) — checklist, fuzzy lookup, long file, layout
- Slack adapter — channel routing, blocks/reactions, approval flow
- MS Teams adapter — Teams webhook + Adaptive Cards
- notify.io / push adapter — async notification + response callback

**Out of scope (all phases)**:
- Authentication / access control between Claude and renderer backends
- Multi-user simultaneous interactions (single-user per session)
- Custom renderer plugin API for third parties (design-in only)
- Multi-session persistence (save/resume state)

### Routing Design

**Routing model**: Multi-endpoint with broadcast and agency (confirmed 2026-03-05)

The routing layer is NOT a single-selector. It supports:

1. **Named endpoint registry** — config file + env var define available endpoints:
   - `phone` — push notification → mobile response (notify.io or similar)
   - `tmux` — TUI in a new tmux pane (detected from `$TMUX` env or explicit)
   - `desktop` — local web renderer on a touch screen side panel
   - Any future adapter registered by name

2. **Default endpoint** — one endpoint designated as fallback when no context signal is present

3. **Claude agency** — Claude receives the endpoint registry and selects the appropriate endpoint based on context signals:
   - `$TMUX` set → prefer `tmux`
   - Running on a remote/headless session → prefer `phone`
   - Desktop context → prefer `desktop`
   - Claude may also **broadcast** to multiple endpoints simultaneously when appropriate (e.g. both phone and desktop when urgency is high)

4. **Explicit override** — caller can pass a specific endpoint name to force routing regardless of context

**Config structure** (provisional):

```yaml
# ~/.claude/interaction.yaml  (or $CLAUDE_INTERACTION_CONFIG)
default: desktop
endpoints:
  phone:
    adapter: notify.io
    token: ${NOTIFYIO_TOKEN}
    target: ${NOTIFYIO_DEVICE_ID}
  tmux:
    adapter: tui
    pane: new           # open new pane vs replace current
    session: current    # attach to current tmux session
  desktop:
    adapter: web
    port: 8742
    bind: 127.0.0.1
    open_browser: false  # side panel stays open persistently
```

**Presence use cases** (confirmed by user):

| Context | Expected behavior |
|---------|------------------|
| Away from desk | Question arrives on phone; user responds from mobile |
| tmux session | New pane opens with TUI; user responds in terminal |
| At desktop | Web renderer on dedicated touch screen side panel |
| Multiple active | Claude can broadcast; first response wins or all collected |

**Open questions for architecture phase:**
- How does Claude detect "desktop vs remote" context? Heuristic (`$DISPLAY`, `SSH_TTY`, etc.) or explicit profile flag?
- "First response wins" vs "collect all responses" — which is default for broadcast?
- Should endpoint health be checked before routing (e.g. is the web server running)?
- How is the endpoint registry exposed to Claude — as a tool parameter, injected context, or auto-read from config?

### Routing Design — Preliminary Research

> **Status**: Preliminary — findings below are first-pass research. Each question requires dedicated investigation and testing before architecture decisions are finalized.

### Existing solutions found (2026-03-05)

| Solution | Relevance | Action |
|----------|-----------|--------|
| [ntfy.sh](https://ntfy.sh) | Self-hosted HTTP push, Android/iOS apps, WebSocket subscribe | **Use as phone adapter backend — do not build** |
| [cyanheads/ntfy-mcp-server](https://github.com/cyanheads/ntfy-mcp-server) | MCP server wrapping ntfy.sh — Claude sends push natively | Evaluate as phone adapter implementation |
| [cindy2000sh/claude-ntfy](https://github.com/cindy2000sh/claude-ntfy) | Claude Code + ntfy.sh with phone reply support | Reference implementation for phone round-trip |
| [caronc/apprise](https://github.com/caronc/apprise) | Python lib, 80+ notification backends under one API | Use as connection layer backend — ntfy, Pushover, Slack, Teams, Gotify all covered |
| [FlorianBruniaux/ccboard](https://github.com/FlorianBruniaux/ccboard) | Rust: TUI (9 tabs) + Web dual-mode for Claude Code monitoring | Study architecture pattern for TUI+Web co-existence |
| [uppinote20/clavis](https://github.com/uppinote20/clavis) | Claude Code admin tool: TUI + Web interface | Second example of TUI+Web dual-mode pattern |
| [ClawHub](https://clawhub.io) | Skill marketplace/registry (`clawhub install <skill>`) | Distribution channel for this plugin post-ship; not relevant to architecture |

**Phone adapter recommendation**: Use Apprise as the connection layer backend. Apprise covers ntfy.sh, Pushover, Slack, Teams, Gotify in one interface. The `phone` adapter becomes an Apprise target URL (`ntfy://server/topic`, `pover://token@device`, etc.) — no custom HTTP code needed.

---

### Q1 — Context detection: heuristic vs explicit profile

**Preliminary finding**: Named profiles in config with env var heuristics as opt-in auto-detection fallback.

Standard Unix signals:

| Signal | Infers |
|--------|--------|
| `$TMUX` set | tmux adapter |
| `$SSH_TTY` set, no `$DISPLAY` | remote session → phone |
| `$DISPLAY` or `$WAYLAND_DISPLAY` set | desktop context |
| `CLAUDE_INTERACTION_PROFILE=<name>` | explicit override (highest priority) |

Heuristics break in edge cases (X11 forwarding over SSH sets `$DISPLAY` while remote). Named profiles allow precise user control:

```yaml
profiles:
  at-desk:
    when: {display: true, tmux: false}
    endpoint: desktop
  in-tmux:
    when: {tmux: true}
    endpoint: tmux
  away:
    when: {ssh: true, display: false}
    endpoint: phone
default: at-desk
```

**Still needs**: Testing against real SSH+tmux+X11-forwarding combinations before finalizing signal priority order.

---

### Q2 — First-response-wins vs collect-all for broadcast

**Preliminary finding**: Response model is determined by interaction *type*, not a global setting.

| Type | Model | Rationale |
|------|-------|-----------|
| `ask` / `choose` | First-response-wins, cancel others | Two answers to same question are contradictory |
| `approve` | First-response-wins + audit log | Safety-critical; log which device responded |
| `notify` | Broadcast-all, no wait | FYI on all devices |

Each interaction message carries a `type` field. Routing layer uses it to pick response model.

**Still needs**: Cancellation protocol design — how does the routing layer signal other endpoints that a first-response was received and the interaction is closed?

---

### Q3 — Endpoint health check before routing

**Preliminary finding**: Probe before routing with configurable timeout (default 500ms); walk fallback chain on failure. Phone/ntfy is terminal node (always available).

| Adapter | Probe method | Fallback |
|---------|-------------|---------|
| `web` | HTTP GET `/health` on configured port | → phone |
| `tmux` | `tmux has-session -t {session}` | → web |
| `phone` (ntfy) | Fire-and-forget (always available) | — terminal node |

**Still needs**: Config syntax for fallback chains; behavior when all probes fail (error vs. queue).

---

### Q4 — Endpoint registry exposure to Claude

**Preliminary finding**: MCP server owns routing; Claude calls one tool. Claude has zero routing logic.

```
Claude  →  ask_user(question, type="ask", hint=None)
              ↓
        Interaction MCP Server
        - reads ~/.claude/interaction.yaml
        - evaluates profile conditions
        - probes endpoint health
        - routes (or broadcasts per type)
        - blocks until response
        - returns structured JSON to Claude
```

The `hint` parameter lets Claude override when it has context the MCP server lacks (e.g. "user said they're away" → `hint="phone"`).

Alternative considered: inject endpoint registry into Claude's system prompt so Claude selects. Rejected (for now) because it couples routing logic into every skill prompt and makes the routing layer untestable independently.

**Still needs**: Confirm MCP server is the right process boundary vs. a local Python CLI the skill calls directly. MCP server adds setup friction; CLI is simpler but loses the tool-call ergonomics.

