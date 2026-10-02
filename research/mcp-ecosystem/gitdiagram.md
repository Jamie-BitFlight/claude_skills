---
name: gitdiagram
title: GitDiagram
subtitle: MCP server turning GitHub repositories into interactive architecture diagrams
research_date: 2026-10-02
source_url: https://github.com/ahmedkhaleel2004/gitdiagram
github_repository: https://github.com/ahmedkhaleel2004/gitdiagram
version_at_research: 0.1.0
license: MIT
freshness_tracking:
  last_verified: 2026-10-02
  version_at_verification: 0.1.0
  next_review: 2027-01-02
  confidence_map: "Overview: high, Problem Addressed: high, Key Features: high, Technical Architecture: high (code-read), Installation & Usage: high, Limitations: medium"
---

# GitDiagram

## Overview

GitDiagram turns any public or private GitHub repository into an interactive architecture diagram with a single click. The tool generates AI-powered visual representations of codebases using Mermaid, streams real-time explanations, and provides an MCP server interface for AI agents to analyze repositories programmatically. It also generates narrated video explanations of repositories in about one minute each.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Understanding large codebases quickly | AI-generated interactive architecture diagrams with clickable components linked to source files |
| Manual architecture documentation | Automated diagram generation from live repository structure, kept current without maintenance |
| Agent-driven code analysis | MCP server at `https://gitdiagram.com/mcp` exposing tools for agents to analyze repositories, search diagrams, and retrieve video explanations |
| Repository knowledge sharing | Markdown and video formats enable agents to access codebase structure without git access or large context windows |

---

## Key Features

### Architecture Diagram Generation

- **AI-powered visualization**: Generates interactive Mermaid diagrams showing components, relationships, and code structure
- **Streamed explanations**: Returns a real-time architecture explanation alongside the diagram via SSE
- **Component linking**: Each diagram element links to the actual source file or directory on GitHub
- **Source-grounded**: Diagram generation reads the top 12 files plus up to 28 additional files identified through import analysis within a 12-second deadline, and uses a SOURCE INDEX to track all read files and important unread paths

### Explainer Videos (Early Access)

- **Narrated codebase overview**: Generates ~1-minute video explaining what the project does, how the main parts fit together, and one key decision
- **Multiple formats**: Download as landscape 1280×720 (CRF 20) or vertical feed-cut 1080×1920 (CRF 14) MP4
- **AI narration**: Uses Claude Opus 5.5 for scriptwriting and Gemini 3.8 Flash TTS for voice
- **Scene-based generation**: Director writes script as continuous story, then cuts it into 12–16 beat script; each scene designed separately with free-form JSON shot language

### MCP Server Interface

- **Public, keyless access**: Remote MCP server at `https://gitdiagram.com/mcp` with no authentication required
- **Three core tools**: `get_repository_diagram` (explanation, components, connections, Mermaid source), `find_repository_diagrams` (search stored diagrams), `get_explainer_video` (retrieve narration transcript and watch link)
- **Agent integration**: Seamlessly integrates with Claude, Codex, Cursor, and other AI agents via standard MCP protocol
- **Markdown export**: Every diagram available as `gitdiagram.com/owner/repo.md` for agents to fetch via HTTP

### Private Repository Support

- **GitHub token-based access**: Sign in with GitHub to analyze private repositories
- **OAuth flow**: Separate public GitHub App ("GitDiagram Private Repos") handles OAuth securely without persisting tokens
- **Per-request credentials**: Each diagram generation uses the visitor's own GitHub token

### Export & Integration

- **PNG export**: Download diagrams as images with full resolution
- **Mermaid source**: Copy the raw Mermaid code for use in documentation or other tools
- **URL-based API**: Replace `hub` with `diagram` in any GitHub URL (e.g., `https://gitdiagram.com/owner/repo`)

---

## Technical Architecture

### Generation Pipeline

The core of GitDiagram is a multi-stage SSE streaming pipeline (`/api/generate/stream`, `runtime = "nodejs"`, `maxDuration = 300`):

1. **Ingestion** (`github.ts`) — Fetches repository metadata, default branch, recursive tree, and README via GitHub API. Maintains a partial tree with top-level folders read one level deep; only oversized READMEs (>750 KB) are rejected. Token limit (`MAX_GENERATION_INPUT_TOKENS` = 900k) stops requests the model would reject.

2. **Source Context and Explanation** (`repository-context.ts`, `source-context.ts`) — Ranks source files, excluding tests, e2e, demos, and generated code. Reads the top 12 plus up to 28 more in two rounds, following imports discovered in the first round, within a 12-second enrichment deadline. Bounds source text to 48k characters. Generates a SOURCE INDEX (each file read with its reference list, important unread files, and CORE MODULES checklist).

3. **Graph Generation** (`graph-planner.ts`) — Model returns a strict, size-bounded graph AST with groups, nodes, edges, labels, and paths. Validated against real repository structure. Each edge carries optional `evidencePath` (file where relationship is visible). Structural failures retried up to `MAX_GRAPH_ATTEMPTS`; graphs with only unresolvable paths are repaired in place. Evidence citations are dropped for files the model wasn't shown.

4. **Mermaid Compilation** (`compileDiagramGraph` in `graph.ts`) — Deterministic AST-to-Mermaid transpiler with total text escaping and GitHub-only link enforcement. Uses test-only parser in `mermaid-validator.ts` to validate output without bloating the server bundle.

5. **Client Rendering** (`src/components/mermaid-diagram.tsx`) — Sanitizes Mermaid source, renders with `securityLevel: "antiscript"`, sanitizes the resulting SVG with DOMPurify, and re-enforces GitHub-only link allowlist.

### Explainer Video Pipeline (Feature-Flagged)

When `VIDEO_EXPLAINER_ENABLED=1` and `NEXT_PUBLIC_VIDEO_EXPLAINER=1`:

- **Director-Designer split**: One model writes the narration and script (role changes by repo star count: Claude Opus 5.5 premium, GPT-6.1 Sol standard; Sol takes over if Opus fails non-fatally); another model designs each scene in parallel. Both share cached prompt prefix (OpenAI calls use explicit prompt caching; Claude calls cache tools and system prompt for one hour).

- **Shot-based visuals**: Each scene is a "shot" with free-form JSON specifying camera position, elements to show, actions, tone, and transitions. `SHOT_KINDS`, `SHOT_ACTIONS`, `SHOT_TONES` in `src/features/explainer/types.ts` are the single source for shot format.

- **Narration-to-timeline alignment**: OpenRouter Gemini 3.8 Flash TTS narrates while designers work. Whisper word timestamps are matched back onto the script; timing failures spread words by length rather than failing the run. A take heard poorly is recorded once more.

- **Rendering**: Headless Chromium renders frame-by-frame into ffmpeg via `/api/video/render/segment` (segments signed with HMAC). Jobs run with 700 s per segment, 240 s per attempt, 780 s total with join and mix. Landscape MP4 is 1280×720 (CRF 20); vertical feed-cut is 1080×1920 (CRF 14, 8 Mbps cap).

### Deployment Architecture

**Vercel** (current): Full Next.js app deployed on Vercel until DNS cutover.

**Cloudflare** (live, scaling to production):
- **Four Workers from one build**: `gitdiagram-edge` (25 KB, holds routes and static files; serves cached pages without R2), `gitdiagram` (site's routing and page cache), `gitdiagram-server` (32 MB Node.js server, placed, serves requests), `gitdiagram-server-local` (same server, runs where visitor is, for diagram runs and Mermaid sitemaps).
- **Caching layers**: Edge caches pages in Cache API; locations forward uncached requests to placed server with `x-gitdiagram-entry-wanted`; server reads R2 and asks Durable Object tag cache.
- **Render containers**: Cloudflare Container pool (5 instances, 2 vCPU / 6 GiB each, two Chromiums per instance) runs the same app to render MP4s and generate videos. Hand-off includes HMAC-signed segment jobs; busy instances 503, others retry.
- **Drain on deploy**: Server finishes renders and videos in flight before exit (triggered by `NEXT_MANUAL_SIG_HANDLE` in Dockerfile).

### Storage and State

- **Diagram artifacts**: R2 bucket `gitdiagram-next-cache` (7-day lifecycle). **Private namespace** derived from `CACHE_KEY_SECRET` for private repos; **public namespace** for public ones.
- **Video storage**: R2 `video/v1/{owner}/{repo}/` with version folders (immutable by `createdAt`). Holds narration clips, MP4s, `poster.jpg`, and `still.jpg`.
- **Quota and cancellation**: Upstash Redis tracks daily complimentary tokens, video budgets, voice balance, and distributed locks per repo.
- **MCP usage**: Redis hash `mcp:v1:calls:<UTC date>` (fields `tool:<name>`, `client:<name>`, error codes; kept 120 days) for per-network and per-tool counting.

### MCP Server

Located at `src/server/mcp/`, stateless HTTP endpoint at `https://gitdiagram.com/mcp`:

- **Handler** (`handler.ts`): Uses `@modelcontextprotocol/server` v2, streamable HTTP, JSON responses only, 64 KB bodies, CORS `*`, 2026-07-28 clients + legacy fallback.
- **Tools** (in `server.ts`):
  - `get_repository_diagram`: Read from public R2 namespace; returns explanation, components with paths, connections, Mermaid source, and links; never starts generation.
  - `find_repository_diagrams`: Browse index, most-starred first, ≤10 results.
  - `get_explainer_video`: Narration transcript and watch link (only when `NEXT_PUBLIC_VIDEO_EXPLAINER=1`).
- **MCP App**: Interactive diagram view (`ui://gitdiagram/diagram-view-v1.html`); shell bundles `src/mcp-app/diagram-view.ts` (esbuild) into `public/mcp-app/` with ChatGPT MCP Apps integration.
- **Rate limiting**: Per-network limiter (`MCP_RATE_LIMIT_MAX` = 120 per hour); fails open on Redis errors. OpenAI calls from shared addresses get 20× allowance per person (hashed from `_meta["openai/subject"]`).

### Operator Dashboard (`/admin`)

Live switches stored in Redis hash `admin:v1:controls` (1 s per-instance cache). Features:

- **Presence tracking** (Cloudflare Worker + Durable Object): Every tab holds a WebSocket reporting what's on screen. Counts updates batched every 250 ms; dead sockets closed every minute while dashboard is open.
- **Live feed**: Routes emit `emitLiveEvent` for diagram/video/MP4 start and finish, visitors held back, sign-ins, switch changes. Repository names only sent once ingestion confirms repo is public.
- **Video budget controls**: Set `LIMITED_COUNTRIES` share (10% by default), pause new videos, override daily per-person limits. Per-UTC-day budgets: public generations capped overall (`GENERATION_RATE_LIMIT_MAX` / window, default 8/hour), per person (default 1, or 3 in priority places), per premium person (default 1), per connection (default 10). Network attempt limit and slot cap for paid runs.
- **Voice balance display**: Reads cached balance (30 s) from OpenRouter; a run pauses for 10 minutes (`video:v1:voice:paused-until`) if balance is out.
- **Counters**: Video/MP4 budgets, voice balance, Claude credit (each with 3 s deadline), complimentary diagram tokens, agents' MCP calls per client.

---

## Installation & Usage

### Access as a User

1. **Web interface**: Visit [gitdiagram.com](https://gitdiagram.com/) and paste a GitHub repository URL, or replace `hub` with `diagram` in any GitHub URL (e.g., `https://gitdiagram.com/owner/repo`).

2. **Private repositories**: Click **Private Repos** in the header, sign in with GitHub, and use your own token for access.

3. **Export**: Click **Download PNG** or **Copy Mermaid** to export the diagram.

4. **Video**: Click **Video** (if enabled) to watch a narrated explanation; download landscape or vertical MP4.

### Access via MCP (for Agents)

Add the MCP server to your agent:

**Claude Code or Cursor**:

```bash
claude mcp add --transport http gitdiagram https://gitdiagram.com/mcp
# or via plugin
claude plugin marketplace add ahmedkhaleel2004/gitdiagram
```

**Codex**:

```bash
codex mcp add gitdiagram --url https://gitdiagram.com/mcp
```

**Other clients** (ChatGPT, Windsurf, Zed, LM Studio, Goose):
Add a remote MCP server with URL `https://gitdiagram.com/mcp`.

Then ask: "How is [owner]/[repo] structured?" to get the diagram, or "Find repositories with X pattern" to search.

### Run Locally

Requires [Bun](https://bun.sh/), Cloudflare R2, Upstash Redis, and an OpenAI or OpenRouter API key.

```bash
git clone https://github.com/ahmedkhaleel2004/gitdiagram.git
cd gitdiagram
bun install
cp .env.example .env
```

Fill in `.env` with API credentials (see [setup guide](https://github.com/ahmedkhaleel2004/gitdiagram/blob/main/docs/dev-setup.md)), then:

```bash
bun run dev  # Starts at localhost:3000
```

For explainer videos, add to `.env`:

```bash
VIDEO_EXPLAINER_ENABLED=1
NEXT_PUBLIC_VIDEO_EXPLAINER=1
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
OPENROUTER_API_KEY=...
```

### Development Commands

```bash
bun run test              # Run tests (vitest)
bun run test:watch       # Watch mode
bun run lint             # ESLint (0 warnings)
bun run typecheck        # TypeScript 7 check
bun run check            # lint + typecheck
bun run build            # Production build
bun run start            # Run production server
```

---

## Limitations and Caveats

**No limitations documented in the project's primary sources.** The README and architecture documentation do not explicitly state constraints or trade-offs. Implicit constraints inferred from architecture (not verified against documented design decisions):

- Repository ingestion has a 12-second enrichment deadline for file reading, which may truncate analysis of very large codebases.
- Only the top 12 + 28 additional source files are read due to token budgets; very deep import graphs may miss some connections.
- Oversized READMEs (>750 KB) are rejected entirely.
- Video generation is feature-flagged and in early access; availability may be limited by voice service balance.
- MCP server rate-limiting defaults to 120 requests/hour per network; sustained agent analysis of many repositories may hit limits.
- Private repositories require GitHub token-based authentication per visitor; tokens are used per-request and never persisted server-side.

---

## Relevance to Claude Code Development

### Applications

- **MCP server for codebase analysis** → `docs/mcp-architecture-analysis.md`
  - Term: `mcp server`
  - Today: "MCP servers extend agents in a modular, flexible way by exposing custom tools or data sources through a standardized interface — essentially acting as plugins."
  - Change: claude_skills could integrate GitDiagram's MCP server directly as a built-in connector, enabling agents to analyze external repositories without fetching them locally. This would provide codebase context for tasks like cross-repository analysis or pattern research.

- **Architecture diagram rendering via Mermaid** → `.claude/skills/mermaid-js/README.md`
  - Term: `mermaid`
  - Today: "19. **Architecture Diagram** — Cloud/infrastructure (v11.1.0+)"
  - Change: The mermaid-js skill already covers Mermaid syntax; GitDiagram's compilation pipeline (`compileDiagramGraph` in `graph.ts`) could serve as a reference for converting ASTs to Mermaid with full escaping and link enforcement, particularly for programmatic diagram generation from code.

- **AI-guided diagram generation pipeline** → `AGENTS.md`
  - Term: `agent`
  - Today: "When the user says 'can you', they mean 'orchestrate this via sub-agents' — delegate accordingly."
  - Change: none — out of scope (GitDiagram's multi-stage pipeline is domain-specific to codebase analysis and would not generalize to other agent-driven diagram tasks).

### Patterns Worth Adopting

- **Streamed SSE explanations alongside generated content** → `docs/mcp-architecture-analysis.md`
  - Term: `architecture`
  - Today: "**Goal:** Each plugin should provide a universal MCP interface for its tooling, enabling agents to access plugin capabilities programmatically through standardized tools."
  - Change: none — claude_skills agents that export MCP tools (like `backlog_core` in development-harness) already follow this pattern; GitDiagram demonstrates the same pattern at production scale across Vercel, Cloudflare, and multiple AI agents.

- **Deterministic graph validation and repair** → `rules/fact-verification-first.md` (implicit through project structure)
  - Term: `architecture`
  - Today: "Structural failures retried up to `MAX_GRAPH_ATTEMPTS`; graphs with only unresolvable paths are repaired in place."
  - Change: none — the repair-in-place approach after validation is already the design pattern used in research-curator's Phase 1c anchor pass (repairing unresolvable paths instead of failing the entry).

### Integration Opportunities

- **Explainer video generation with AI narration** → nothing in `/plugins/ :/.claude/skills/ :/.claude/agents/ :/rules/ :/docs/ :/AGENTS.md`
  - Today: `git grep --full-name -il "explainer video" -- :/plugins/ :/.claude/skills/ :/.claude/agents/ :/rules/ :/docs/ :/AGENTS.md` → 0 matches
  - Today: `git grep --full-name -il "narrated" -- :/plugins/ :/.claude/skills/ :/.claude/agents/ :/rules/ :/docs/ :/AGENTS.md` → 0 matches
  - Change: none — out of scope (video generation is a specialized feature; no skill currently generates narrated videos of codebases).

---

## References

- [GitDiagram GitHub Repository](https://github.com/ahmedkhaleel2004/gitdiagram) (accessed 2026-10-02)
- [GitDiagram Web Application](https://gitdiagram.com/) (accessed 2026-10-02)
- [README.md](https://github.com/ahmedkhaleel2004/gitdiagram/blob/main/README.md) (accessed 2026-10-02)
- [CLAUDE.md — Architecture Documentation](https://github.com/ahmedkhaleel2004/gitdiagram/blob/main/CLAUDE.md) (accessed 2026-10-02)
- [Development Setup Guide](https://github.com/ahmedkhaleel2004/gitdiagram/blob/main/docs/dev-setup.md) (accessed 2026-10-02)
- [Architecture Documentation](https://github.com/ahmedkhaleel2004/gitdiagram/blob/main/docs/architecture.md) (accessed 2026-10-02) — generation, storage, and deployment architecture; it has no MCP section (the MCP tools and rate limit are documented in the "MCP server" section of CLAUDE.md above)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Grounded Docs (docs-mcp-server)](./docs-mcp-server.md) | mcp-ecosystem | Both are MCP servers for code understanding; docs-mcp indexes local documentation while gitdiagram visualizes repository structure |
| [MCP Jam](./mcpjam.md) | mcp-ecosystem | Essential testing and debugging tool for MCP servers; required to validate gitdiagram's MCP server interface during development |
| [Narsil MCP](./narsil-mcp.md) | mcp-ecosystem | Complementary code intelligence tools; narsil provides call graphs and security scanning while gitdiagram generates architecture diagrams |
| [Mimir MCP](./mimir-mcp.md) | mcp-ecosystem | Both integrate Git repositories; mimir provides versioned memory storage for gitdiagram's diagram and video artifacts |
| [SourceSync.ai MCP](./sourcesyncai-mcp.md) | mcp-ecosystem | Knowledge base ingestion platform; can ingest and manage gitdiagram outputs as structured codebase documentation |
| [BrowserMCP](./browsermcp-mcp.md) | mcp-ecosystem | Complementary MCP servers; browsermcp provides browser automation for visualizing diagrams or monitoring deployment visualization |
| [HomeButler](./homebutler.md) | mcp-ecosystem | Alternative MCP server for infrastructure and service management; shares deployment and integration patterns with gitdiagram |
| [OctoCode MCP](./octocode-mcp.md) | mcp-ecosystem | Research-driven development platform with GitHub integration; both tools analyze repositories to support agent-driven code research |
