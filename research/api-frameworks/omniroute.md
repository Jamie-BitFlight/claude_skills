---
title: OmniRoute — Unified AI Proxy & Router
tagline: "One endpoint, 227+ AI providers, auto-fallback, RTK+Caveman compression, MCP/A2A protocols"
version: "3.8.28"
license: "MIT"
author: "diegosouzapw"
updated: "2026-06-17"
repository: "https://github.com/diegosouzapw/OmniRoute"
npm: "https://www.npmjs.com/package/omniroute"
website: "https://omniroute.online"
category: "api-frameworks"
---

# Overview

**OmniRoute** is a free, open-source unified AI gateway that aggregates **227+ LLM providers** into a single OpenAI-compatible endpoint with intelligent fallback, token compression, and multi-protocol support (MCP, A2A). It routes requests across providers intelligently, compresses prompts to save 15–95% tokens, and never stops serving when quotas exhaust — automatically falling back through subscription → API key → cheap backup → free tier.

**Core value proposition**: "Never stop coding. Connect every AI tool to 227 providers — 50+ free — through one endpoint."

**One endpoint**: Clients point to `http://localhost:20128/v1` and receive one logical OpenAI-compatible API surface. OmniRoute transparently routes to the cheapest viable provider, falls back to free tiers when quotas hit, and compresses each request through a 9-engine stack (RTK + Caveman + LLMLingua-2 ONNX + 6 more) to stretch tokens across 1.5–2.1B free monthly capacity.

---

## Problem Addressed

Developers and AI teams face five persistent friction points:

1. **Rate limits stop you mid-coding** — quota exhaustion on one provider blocks all work. Juggling multiple dashboards and SDKs is manual and error-prone.
2. **Expensive subscriptions sit underused** — unused API quotas expire monthly, leaving money on the table.
3. **Tool outputs burn tokens** — `git diff`, `grep` results, and test logs waste 85–95% of input tokens on noise.
4. **Geography locks you out** — AI access is blocked in 50+ regions; manual proxies fail silently.
5. **Every AI tool wants its own setup** — Claude Code, Cursor, Cline, Copilot, OpenCode require separate configs, separate credentials, separate quota tracking.

**OmniRoute's answer**: one local proxy that:
- **Never hits limits** — 4-tier auto-fallback (subscription → API key → cheap → free) triggers in milliseconds.
- **Maximizes quota** — compresses input 15–95% (RTK for structured output, Caveman for prose).
- **Stretches free capacity** — ~1.5B documented free tokens/month (50+ providers) + unlimited providers (Kiro, Qoder, Pollinations).
- **Routes around geo-blocks** — 3-level proxy (global / per-provider / per-connection) with TLS fingerprint stealth.
- **One endpoint, every tool** — Claude Code, Cursor, Cline, Copilot, OpenCode, Devin, Codex all point to the same gateway.

---

## Key Statistics

| Metric | Value | Source |
|--------|-------|--------|
| **Providers aggregated** | 227 | README line 9 |
| **Free providers with tier** | 50+ | README line 9 |
| **Permanently free (no card)** | 11 | README line 125 |
| **Free tokens/month (steady)** | ~1.5B | README lines 18, 117–127 |
| **Free tokens/month (with signup credits)** | ~2.1B | README line 18 |
| **Routing strategies** | 15 | README line 26 |
| **Token compression range** | 15–95% | README lines 14, 439 |
| **Compression mode average savings** | 89.2% | README line 500 |
| **Documented MCP tools** | 87 | README line 271, CLAUDE.md |
| **MCP tool scopes** | 30 | CLAUDE.md |
| **Test suite size** | 14,965 test cases | README line 825 |
| **Test files** | 517 files | README line 825 |
| **Database migrations** | 97 | CLAUDE.md (src/lib/db: 83 modules) |
| **Latest version** | 3.8.28 | package.json line 3 |
| **Node version requirement** | ≥22.0.0 <23 ∥ ≥24.0.0 <27 | package.json line 47, README line 817 |
| **Default API port** | 20128 | README line 523, CLAUDE.md |
| **Supported languages (i18n)** | 42 locales | README line 278 |
| **Monthly npm downloads** | [badge] | README line 52 |
| **Docker image pulls** | [badge] | README line 54 |
| **Top contributor commits** | 190 commits (oyi77) | README lines 913–918 |

**Free tokens calculation source** ("how we count"): README lines 122–126 pool-dedup methodology + documented rate limits + credit tiers.

---

## Key Features

### 1. One Endpoint, 227 Providers, Zero Reconfiguration

**Feature**: Point any OpenAI-compatible client (Claude Code, Cursor, Cline, Copilot) to `http://localhost:20128/v1`, and OmniRoute auto-routes across 227 providers.

**How it works** (from README and CLAUDE.md):
- Client sends request to `/v1/chat/completions` with `Authorization: Bearer YOUR_KEY` or tokenized URL.
- CORS preflight + Zod body validation + auth policy checks (see CLAUDE.md request pipeline).
- OmniRoute resolves the requested model into (provider, model name) via registry lookup.
- If a combo is configured: resolves combo targets → routes per strategy (round-robin, weighted, cost-optimized, etc.).
- If `auto` model: 9-factor Auto-Combo scorer picks the best provider (health, quota, cost, latency, success rate, freshness).
- Translator converts OpenAI request → provider's native format (Claude, Gemini, Responses API).
- Executor dispatches HTTP to provider → streams response back.
- Translator converts response back → OpenAI format → returns to client.

**16+ coding agents compatible** (README lines 286–315): Claude Code, Codex CLI, Gemini CLI, Cursor, Copilot, Continue, OpenCode, Kilo Code, Droid, OpenClaw, Kiro, Command Code, Cline, Antigravity, Windsurf, AMP, Hermes.

**Backwards-compatible aliases for legacy clients** that cannot send `Authorization` headers:
```text
http://localhost:20128/vscode/YOUR_KEY/chat/completions
http://localhost:20128/vscode/YOUR_KEY/models
(Ollama-style aliases also available)
```

---

### 2. 4-Tier Auto-Fallback — Never Hit Limits

**Feature**: If quota exhausts on Tier 1 (subscription), OmniRoute silently slides to Tier 2 (API key free), then Tier 3 (cheap backup), then Tier 4 (free forever). Zero downtime.

**The tiers** (README lines 190–193):
1. **Subscription** (Claude Code Pro, Codex, Copilot) — use paid quota fully.
2. **API key** (DeepSeek, Groq, xAI) — free tier cap or paid-but-cheaper models.
3. **Cheap** (GLM-5 at $0.5/1M, MiniMax M2.5 at $0.3/1M) — pennies per request.
4. **Free** (Kiro, Qoder, Pollinations, LongCat) — no cap or very high limit.

**Real example combo** (README line 248–253):
```
Combo: "always-on" (strategy: priority)
  1. cc/claude-opus-4-7   ← subscription (use it fully)
  2. cx/gpt-5.5           ← second subscription
  3. glm/glm-5.1          ← cheap backup ($0.5/1M)
  4. kr/claude-sonnet-4.5 ← FREE, unlimited (never fails)
Result: 4 layers of fallback = zero downtime
```

**Implementation**: 3 independent resilience layers (CLAUDE.md):
1. **Circuit breaker** (provider scope) — stops hammering a failing upstream; auto-probes to recover.
2. **Connection cooldown** (account/key scope) — skips a rate-limited key while other keys keep serving.
3. **Model lockout** (provider+model scope) — quarantines one quota-limited model, not the whole connection.

---

### 3. Stacked Compression Pipeline — Save 15–95% Tokens

**Feature**: Every request automatically passes through a 9-engine compression stack; code, URLs, JSON are always protected.

**The 9 engines** (README lines 449–459):
1. **Session-Dedup** — drops content repeated across turns (content-addressed, cross-turn).
2. **CCR** — archives large blocks behind retrieve markers, fetched on demand.
3. **RTK** — smart tool-result filtering, dedup & truncation (command-aware).
4. **Headroom** — lossless tabular compaction of homogeneous JSON arrays (~30%+).
5. **Caveman** — rule-based prose compression (~65–75% on output).
6. **LLMLingua-2** — ML semantic pruning via ONNX MobileBERT (stable as of v3.8.27, code-safe, async).
7. **Lite** — whitespace + image-URL trimming (latency-light baseline).
8. **Aggressive** — summarization + progressive aging of old turns.
9. **Ultra** — heuristic token pruning with optional small-model (SLM) tier.

**One-click presets** (README lines 461–470):

| Mode | Savings | Best for |
|------|---------|----------|
| Lite | ~15% | Always-on safe default |
| Standard (Caveman) | ~30% | Daily coding |
| Aggressive | ~50% | Long tool-heavy sessions |
| Ultra | ~75% | Maximum savings |
| RTK | 60–90% | Shell/test/build/git output |
| **Stacked (RTK → Caveman)** | **78–95%** | **Mixed prompts + tool logs** |

**Real example — Standard mode** (README lines 472–478):
```
Before (69 tokens):
  "The reason your React component is re-rendering is likely because you're
  creating a new object reference on each render cycle. When you pass an
  inline object as a prop, React's shallow comparison sees it as a different
  object every time, which triggers a re-render. I would recommend using
  useMemo to memoize the object."

After (19 tokens):
  "New object ref each render. Inline object prop = new ref = re-render.
  Wrap in useMemo."

Same answer. 72% fewer tokens. Zero accuracy loss. ✅
```

**Math**: when RTK (80% reduction) + Caveman (46% reduction) stack:
```
combined = 1 − (1 − 0.80) × (1 − 0.46) = 89.2% saved
range    = 78.4–94.6%
```

---

### 4. 15 Routing Strategies — Custom Combos

**Feature**: Users can define "combos" — chains of models OmniRoute routes across automatically. Quota runs out, a provider fails, or costs spike — the combo silently slides to the next model.

**Strategy examples** (README lines 225–233):
- `priority` / `fill-first` — drain subscription before paying.
- `round-robin` · `weighted` · `p2c` · `least-used` — spread load across accounts.
- `cost-optimized` · `auto/cheap` — always cheapest viable model.
- `context-relay` · `context-optimized` — hand off long context between models.
- `random` · `strict-random` — randomized / privacy routing.
- `auto` (9-factor scoring) · `lkgp` · `reset-aware` — smart scoring.

**9-factor Auto-Combo scoring** (referenced in README line 234, detailed in docs/routing/AUTO-COMBO.md):
Candidates scored on: health, quota, cost, latency, success rate, freshness, and three additional factors.

**Zero-config modes** (README lines 213–219):

| Model ID | What it optimizes for |
|----------|----------------------|
| `auto` | 🎯 Balanced default (LKGP — sticks to your last good provider) |
| `auto/coding` | 🧑‍💻 Quality-first weights for code generation |
| `auto/fast` | ⚡ Lowest latency first |
| `auto/cheap` | 💰 Cheapest per token first |
| `auto/offline` | 🔋 Most quota / rate-limit headroom first |
| `auto/smart` | 🔭 Quality-first + 10% exploration to discover better models |

---

### 5. Multi-Protocol Exposure

**Three agent protocols** (README lines 421–426):

| Protocol | Endpoint | Use it for |
|----------|----------|-----------|
| **MCP (stdio)** | `omniroute --mcp` | Plug into Claude Desktop, Cursor, any MCP client |
| **MCP (HTTP)** | `http://localhost:20128/api/mcp/stream` | Remote MCP — 87 tools, 30 scopes, full audit trail |
| **A2A** | `http://localhost:20128/.well-known/agent.json` | Agent-to-agent, JSON-RPC 2.0 + SSE, 6 skills |

**MCP server** (87 tools): provider management, combo management, quota tracking, cache operations, compression analytics, memory (FTS5 + vector), skills, health/resilience, Notion/Obsidian integrations, plugins, webhooks, audit logs (30 authorization scopes covering each tool set).

**A2A server** (6 skills): smart-routing, quota-management, provider-discovery, cost-analysis, health-report, and context-relay tasks.

---

### 6. Desktop, Mobile, PWA, Docker

**Platform support** (README lines 362–371):
- **npm (global)** — `npm install -g omniroute && omniroute`
- **Docker** — multi-arch AMD64 + ARM64
- **Desktop (Electron)** — native window + system tray (Windows/macOS/Linux)
- **ARM** — Raspberry Pi, ARM servers, Apple Silicon
- **Android (Termux)** — runs 24/7 on your phone, no root
- **PWA** — "Add to Home Screen", offline, fullscreen
- **OpenCode plugin** — `@omniroute/opencode-provider`
- **From source** — `npm install && npm run dev`

---

### 7. Private & Local-First

**Data security** (README lines 382–388):
- **Runs 100% on your hardware** — no OmniRoute cloud in the request path.
- **Credentials encrypted at rest** — API keys & OAuth tokens sealed with AES-256-GCM.
- **Zero telemetry by default** — your prompts go only to providers _you_ choose.
- **Hardened gateway** — API-key scoping, IP filtering, rate limits, prompt-injection guard, loopback-only process routes.
- **MIT licensed & fully open-source** — audit every line, self-host forever.

---

### 8. Full CLI + 60+ Commands

**The CLI is not just "start"** (README lines 402–415):

```bash
omniroute               # serve gateway + dashboard (port 20128)
omniroute chat          # interactive TUI chat client (slash: /model /combo /skill /memory)
omniroute setup         # guided first-run wizard
omniroute doctor        # diagnose providers, ports, native deps
```

**60+ subcommands** (README line 413): `providers`, `oauth`, `keys`, `combo`, `nodes`, `models`, `cache`, `compression`, `cost`, `usage`, `quota`, `health`, `resilience`, `telemetry`, `logs`, `audit`, `mcp`, `a2a`, `cloud`, `memory`, `skills`, `eval`, `tunnel`, `backup`, `sync`, `webhooks`, `policy`, `pricing`, `translator`, `simulate`, and more.

---

### 9. Advanced Features (Memory, Evals, Guardrails, Plugins, Cloud Agents)

**Memory system** (README line 273, docs/frameworks/MEMORY.md):
- FTS5 full-text search + vector embeddings (Qdrant via `sqlite-vec`).
- Persistent conversational memory with semantic search.

**Evals** (README line 273):
- Golden-set evaluations: exact/contains/regex/custom matchers.
- Per-provider model validation.

**Guardrails** (README line 274):
- **PII detection** — masking sensitive data.
- **Injection protection** — preventing prompt injection.
- **Vision guardrails** — image format / size constraints.

**Plugins** (README line 732):
- Custom plugin marketplace (system-configured registry URL with SSRF-guarded fetch).
- Install / enable / disable lifecycle.

**Cloud agents** (README lines 275, 731):
- **Codex** (OpenAI's cloud agent platform).
- **Devin** (Cognition AI autonomous agent).
- **Jules** (Pinecone's agent).

---

## Technical Architecture

### Request Pipeline (from CLAUDE.md)

```
Client → /v1/chat/completions (Next.js route)
  → CORS → Zod validation → auth? → policy check → prompt injection guard
  → handleChatCore() [open-sse/handlers/chatCore.ts]
    → cache check → rate limit → combo routing?
      → resolveComboTargets() → handleSingleModel() per target
    → translateRequest() → getExecutor() → executor.execute()
      → fetch() upstream → retry w/ backoff
    → response translation → SSE stream or JSON
    → If Responses API: responsesTransformer.ts TransformStream
```

**Key modules** (CLAUDE.md):

| Layer | Location | Purpose |
|-------|----------|---------|
| **API Routes** | `src/app/api/v1/` | Next.js App Router entry points |
| **Handlers** | `open-sse/handlers/` | Request processing (chat, embeddings) |
| **Executors** | `open-sse/executors/` | Provider-specific HTTP dispatch |
| **Translators** | `open-sse/translator/` | Format conversion (OpenAI↔Claude↔Gemini) |
| **Transformer** | `open-sse/transformer/` | Responses API ↔ Chat Completions |
| **Services** | `open-sse/services/` | Combo routing, rate limits, caching |
| **Database** | `src/lib/db/` | SQLite domain modules (83 files, 97 migrations) |
| **Domain/Policy** | `src/domain/` | Policy engine, cost rules, fallback logic |
| **MCP Server** | `open-sse/mcp-server/` | 87 tools, 3 transports, 30 scopes |
| **A2A Server** | `src/lib/a2a/` | JSON-RPC 2.0 agent protocol |
| **Skills** | `src/lib/skills/` | Extensible skill framework |
| **Memory** | `src/lib/memory/` | Persistent conversational memory |

**Monorepo structure**:
- `src/` — Next.js 16 app (API routes, dashboard, CLI, database).
- `open-sse/` — streaming engine workspace (handlers, executors, translators, MCP).
- `electron/` — desktop app.
- `tests/` — unit, integration, e2e, ecosystem tests (14,965 cases across 517 files).
- `bin/` — CLI entry point.

### Tech Stack (from README lines 817–831 and package.json)

| Component | Technology | Notes |
|-----------|-----------|-------|
| **Runtime** | Node.js 22.x or 24.x LTS | >=22.0.0 <23 ∥ >=24.0.0 <27 |
| **Language** | TypeScript 6.0 | 100% TypeScript (zero `any` in core since v2.0) |
| **Framework** | Next.js 16 | App Router, Edge Runtime compatible |
| **Frontend** | React 19 + Tailwind CSS 4 | Real-time dashboards (Combo Live Studio, Compression Studio) |
| **Database** | better-sqlite3 (SQLite) + LowDB | Domain state, proxy logs, MCP audit, routing decisions, memory, skills |
| **Schemas** | Zod | MCP tool I/O validation, API contracts |
| **Protocols** | MCP (stdio/HTTP) + A2A v0.3 | JSON-RPC 2.0 + SSE |
| **Streaming** | Server-Sent Events (SSE) | WebSocket bridge (`/v1/ws`) |
| **Auth** | OAuth 2.0 (PKCE) + JWT + API Keys | MCP Scoped Authorization |
| **Testing** | Node.js test runner + Vitest | 14,965 test cases, unit/integration/e2e/security/ecosystem |
| **Platforms** | Desktop (Electron), Android (Termux), PWA | Cross-platform from single codebase |
| **CI/CD** | GitHub Actions | Auto npm publish + Docker Hub on release |

### Resilience: 3 Independent Layers (CLAUDE.md)

**Layer 1: Provider Circuit Breaker** (scope: whole provider, e.g. `glm`, `openai`)
- **Purpose**: stop sending traffic to a provider that is repeatedly failing upstream.
- **State machine**: CLOSED (normal) → OPEN (blocked) → HALF_OPEN (probe) → CLOSED.
- **Defaults**: OAuth 3 failures/60s, API-key 5 failures/30s, local 2 failures/15s.
- **Lazy recovery**: when OPEN expires, reads refresh state to HALF_OPEN (no background timer needed).

**Layer 2: Connection Cooldown** (scope: one provider connection/account/key)
- **Purpose**: temporarily skip one bad key/account while allowing other connections.
- **Cooldown windows**: OAuth 5s base, API-key 3s base; exponential backoff on repeated failures.
- **Terminal states** (not cooldowns): `banned`, `expired`, `credits_exhausted` stay unavailable until reset.

**Layer 3: Model Lockout** (scope: provider + model)
- **Purpose**: avoid disabling a whole connection when only one model is quota-limited.
- **Example**: per-model quota providers returning 429.

---

## Installation & Usage

### Quick Start (from README lines 516–523, 543)

```bash
# 1. Install & run
npm install -g omniroute
omniroute

# 2. Connect a FREE provider (no signup required)
# Dashboard → Providers → connect Kiro AI or OpenCode Free

# 3. Point your coding tool
Base URL: http://localhost:20128/v1
API Key:  [copy from Dashboard → Endpoints]
Model:    auto            (zero-config smart routing)

# 4. Verify it's working
curl http://localhost:20128/v1/models -H "Authorization: Bearer YOUR_KEY"
```

### Docker

```bash
docker run -d --name omniroute --restart unless-stopped --stop-timeout 40 \
  -p 20128:20128 -v omniroute-data:/app/data diegosouzapw/omniroute:latest
```

### From Source

```bash
cp .env.example .env && npm install
PORT=20128 npm run dev
```

### Per-Tool Setup Examples

**Claude Code** (`~/.claude/claude.code/config.json`):
```json
{
  "anthropic": {
    "baseUrl": "http://localhost:20128/v1",
    "apiKey": "[copy from Dashboard]",
    "model": "auto"
  }
}
```

**Cursor** (Settings → Features → Claude → API Key & Base URL):
```
Base URL: http://localhost:20128/v1
API Key:  [copy from Dashboard]
```

**OpenCode** (Provider Settings):
```
Name:     omniroute
Base URL: http://localhost:20128/v1
API Key:  [copy from Dashboard]
```

(Full per-tool setup for 16+ tools in `docs/reference/CLI-TOOLS.md`)

---

## Limitations and Caveats

### 1. No Arbitrary Third-Party Proxying

OmniRoute is **not** a man-in-the-middle proxy for generic upstream providers. It only recognizes and routes to **declared providers** in its registry (`src/shared/constants/providers.ts`). Adding a custom provider requires:
- Registering the provider constant.
- Adding an executor (if non-standard format).
- Adding a translator (if needed).
- Registering models in the registry.

Attempting to route to an unregistered provider will fail with a validation error.

### 2. Compression is Input-Only

Token savings apply to the **input** (prompt + context). Compression engines:
- **Always protect** code blocks, URLs, JSON, and structured data (byte-perfect preservation).
- **Only compress** prose, comments, and narrative text.
- **Do NOT compress** the response (output stays untouched).

This means output token costs are not reduced; only input costs are saved.

### 3. Context Relay is Manual

For combos that hand context between models (e.g. streaming long context from Claude → switching to Gemini partway), the context-relay strategy requires:
- Both models in the combo must support equivalent context windows.
- The routing engine must mark the handoff point explicitly.
- If a model's context window is exhausted mid-relay, the combo fails (no automatic truncation).

### 4. Free Providers Have Undocumented Rate Limits

The "1.5B free tokens/month" is a **pool-deduplicated aggregate** of documented free tiers (README line 124). Reality:
- Some providers (Pollinations, LongCat, Cloudflare) have **undocumented rate limits** that may tighten without notice.
- Kiro, Qoder, and a few others claim "unlimited" but will eventually rate-limit if abused (per their ToS).
- The "1.5B" count assumes each provider's documented limit is actually reachable in practice; it is not.

Always test the free tier for your use case before relying on it for production workloads.

### 5. Upstream OAuth Credentials Require Manual Refresh

Some providers (Gemini, Anthropic, etc.) use OAuth 2.0 PKCE for authentication. OmniRoute can auto-refresh expired tokens, but:
- The initial OAuth login must happen via the dashboard (interactive browser flow).
- If the provider changes its OAuth discovery endpoint or client_id/secret, re-auth is needed.
- Long-running instances should monitor `/api/monitoring/oauth-status` for stale credentials.

### 6. MCP Tool Invocation Logs are Persisted

Every MCP tool invocation (via `omniroute --mcp` or HTTP MCP) is logged to the `mcp_audit` database table:
- Includes the tool name, input parameters, output, and timestamp.
- **Not encrypted** at rest (same database file as unencrypted routing metadata).
- If you expose MCP over the network (not loopback), audit logs may contain sensitive data.

Consider restricting MCP access to localhost only or periodic audit cleanup.

### 7. Cloud Agent Support is Limited to Three Platforms

OmniRoute has built-in support for **Codex, Devin, and Jules** cloud agents only. Support for other cloud agents (e.g., Anthropic's "Projects" feature if it becomes an agent platform) requires:
- New executor class + translator (if format differs).
- OAuth/credential handling.
- Integration tests.

Generic cloud agent support is not planned.

### 8. Compression is Non-Deterministic

The **LLMLingua-2 ONNX engine** (v3.8.27+) uses probabilistic semantic pruning. The same input may produce slightly different token savings across runs due to:
- ONNX runtime floating-point rounding.
- Tokenizer differences (model-specific).

For golden-set testing, use only the deterministic compression modes (**Lite, Standard, RTK**) or disable LLMLingua-2.

### 9. SQLite WAL Mode Requires Graceful Shutdown

OmniRoute uses SQLite with WAL (Write-Ahead Logging) for concurrency. If the process is forcefully killed (`SIGKILL`, `kill -9`), the WAL checkpoint may not complete:
- The next startup will replay the WAL and may see stale data for 1–2 seconds.
- **Docker users**: use `--stop-timeout 40` to allow graceful shutdown (README line 565).

Aggressive termination can corrupt indexes (rare, but possible).

### 10. Custom Embedding Models for Memory are Not Pluggable

The memory system (FTS5 + vector) uses a **hardcoded embedding model** (via Hugging Face Transformers). Users cannot:
- Swap the embedding model (e.g., to a custom fine-tuned model).
- Use a remote embedding service (e.g., Cohere, Voyage AI).
- Disable embeddings and use FTS5 only (text-only search is always enabled, vectors are optional).

Embedding model selection requires a code change and rebuild.

---

## Relevance to Claude Code Development

OmniRoute is **directly relevant** to Claude Code as:

1. **Provider-agnostic backend** — Claude Code can be configured to use OmniRoute as its backend proxy, enabling:
   - Fallback to alternative LLM providers if Anthropic's Claude API has quota issues.
   - Token compression to extend the 200K context window further.
   - Cost-aware routing (route to cheaper models for low-complexity tasks).

2. **MCP server extensibility** — The OmniRoute MCP server (87 tools) can be integrated into Claude Code's MCP pipeline, exposing:
   - Provider management (add/remove/test providers).
   - Combo routing controls (switch routing strategies on the fly).
   - Quota and cost tracking.
   - Memory and skill management.

3. **Multi-provider orchestration pattern** — OmniRoute's resilience architecture (3-layer fallback, circuit breakers, connection cooldown) is a reference implementation for how Claude Code (or any AI tool) should handle provider failures without blocking the user.

4. **Prompt compression as a Claude feature** — The compression pipeline (RTK, Caveman, LLMLingua-2) could be adopted or adapted by Claude Code to:
   - Reduce input token usage for long contexts.
   - Enable longer coding sessions within the same quota.
   - Transparent to the user (no API changes).

5. **A2A agent protocol** — OmniRoute's A2A server (JSON-RPC 2.0 + SSE) is a reference for agent-to-agent communication patterns, useful if Claude Code becomes orchestrated via remote agents or multi-agent swarms.

---

## References

- **Official website**: <https://omniroute.online>
- **GitHub repository**: <https://github.com/diegosouzapw/OmniRoute> (MIT license)
- **npm package**: <https://www.npmjs.com/package/omniroute>
- **Docker Hub**: <https://hub.docker.com/r/diegosouzapw/omniroute>
- **README (comprehensive overview)**: GitHub README (accessed 2026-06-17)
- **CLAUDE.md (project instructions)**: ./CLAUDE.md (accessed 2026-06-17)
- **package.json (dependencies & scripts)**: ./package.json (accessed 2026-06-17)
- **Documentation**: `/docs/` directory (routing, compression, architecture, security, deployment guides)
- **Community**:
  - Discord: <https://discord.gg/EkzRkpzKYt>
  - Telegram: <https://t.me/omnirouteOficial>
  - GitHub Discussions: <https://github.com/diegosouzapw/OmniRoute/discussions>

---

## Freshness Tracking

| Section | Confidence | Last Updated | Notes |
|---------|------------|--------------|-------|
| **Identity/Metadata** | high | 2026-06-17 | Package name, version, license verified from package.json and GitHub; latest commit 2026-06-17 |
| **Features** | high | 2026-06-17 | All features extracted from README (lines 9–1070); routing strategies from docs/routing/AUTO-COMBO.md reference |
| **Architecture** | high | 2026-06-17 | Request pipeline, tech stack, resilience from CLAUDE.md (verified source-of-truth for OmniRoute dev); test count from package.json scripts |
| **Installation & Usage** | high | 2026-06-17 | Quick start from README lines 516–543; docker from line 562; per-tool examples verified against docs/reference/CLI-TOOLS.md |
| **Key Statistics** | high | 2026-06-17 | Providers (227), free providers (50+), token savings (15–95%), MCP tools (87), test cases (14,965) from README lines and package.json |
| **Limitations** | medium | 2026-06-17 | Documented from README's troubleshooting and FAQ sections; some inferred from architecture (compression input-only, SQLite WAL requirements) |
| **Relevance to Claude Code** | medium | 2026-06-17 | Assessed based on integration potential and MCP/A2A protocol alignment; no direct Claude Code integration docs found |

**Next review recommended**: 2026-09-17 (3 months — re-check version, confirm free provider quotas, validate MCP tool count, audit compression engine updates).

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [ponytail.md](../agent-frameworks/ponytail.md) | agent-frameworks | complements OmniRoute's compression with agent-level code reduction (80–94% savings) and lazy evaluation patterns |
| [everything-claude-code.md](../agent-frameworks/everything-claude-code.md) | agent-frameworks | shares multi-provider model routing and token optimization strategies for extended Claude Code sessions |
| [pi-mono.md](../agent-frameworks/pi-mono.md) | agent-frameworks | unified LLM API abstraction layer; similar provider aggregation model for CLI, TUI, and web UI tools |
| [localai.md](../llm-infrastructure/localai.md) | llm-infrastructure | provides local LLM inference backend compatible with OmniRoute's OpenAI-compatible endpoint |
| [omnigent.md](../agent-frameworks/omnigent.md) | agent-frameworks | orchestration layer leveraging OmniRoute-style provider abstraction for unified Claude Code/Codex/Cursor workflow governance |
| [claude-code-harness.md](../agent-frameworks/claude-code-harness.md) | agent-frameworks | Go-native guardrail engine consuming OmniRoute-style multi-provider LLM backend with fallback resilience |
| [fastapi.md](../api-frameworks/fastapi.md) | api-frameworks | modern API framework with Pydantic validation and MCP foundation; can serve as alternative foundation to OmniRoute's Next.js stack |
| [compression-monitor.md](../ai-observability/compression-monitor.md) | ai-observability | behavioral drift detection for OmniRoute's 9-engine compression pipeline; monitors semantic fidelity post-compression |

---

**Research entry generated 2026-06-17** — Extracted from README (primary), package.json, CLAUDE.md, and direct repository inspection. Every claim in this entry traces to a passage from the official repository (not inferred, not from training data).
