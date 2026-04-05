# SoulForge

**Research Date**: 2026-04-05
**Source URL**: <https://github.com/ProxySoul/soulforge>
**GitHub Repository**: <https://github.com/ProxySoul/soulforge>
**Version at Research**: v2.4.0 (released 2026-04-05)
**License**: Business Source License 1.1 (converts to Apache 2.0 on March 15, 2030)

---

## Overview

SoulForge is a graph-powered AI coding agent that combines multi-agent orchestration with codebase awareness. Unlike tools that start blind and build a mental model through file reads and grep operations, SoulForge builds a live SQLite-backed dependency graph on startup with PageRank importance ranking, git co-change history, and real-time updates. The agent routes different task types (exploration, code implementation, web research) to specialized subagents with task-specific models, enabling faster, more accurate code changes at lower cost than single-model approaches.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| AI agents waste context window orienting to codebase structure | Live Soul Map: SQLite-backed graph with PageRank, blast radius, clone detection, FTS5 search. Updated in real-time as files change. |
| Reading entire files wastes tokens; agents don't know which symbols matter | Surgical reads: extract only the function or class needed by name. 500-line file becomes 20-line symbol extraction. 4-tier fallback: LSP → ts-morph → tree-sitter → regex. |
| Context management is manual or generic | Instant compaction: working state extracted incrementally during conversation. When context grows long, compaction fires from pre-built state. Rich enough state skips the LLM entirely. |
| Single model routes all tasks inefficiently | Task router: per-task model assignment. Spark agents (exploration) get Haiku or Sonnet. Ember agents (code) get Opus or higher. Web search, cleanup, verification each get their own slot. |
| Parallel agents create file conflicts and cache redundancy | AgentBus: in-process coordination with file caching (deduplicated reads across agents), tool result caching (persists across dispatches), edit coordination (serialized writes per file with ownership tracking). |
| Multi-tab sessions create git conflicts and context confusion | Cross-tab coordination: per-tab models and file claims. Agents see cross-tab edits, get warnings on contested files, git ops coordinate automatically. |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 93 | 2026-04-05 |
| GitHub Forks | 10 | 2026-04-05 |
| GitHub Watchers | 93 | 2026-04-05 |
| Latest Release | v2.4.0 | 2026-04-05 |
| Repository Created | 2026-03-01 | 2026-04-05 |
| Last Updated | 2026-04-05 | 2026-04-05 |

---

## Key Features

### Codebase Intelligence

- **Live Soul Map**: SQLite-backed index of every file, symbol, import, and export. "PageRank ranking blends structural importance (PageRank over the import graph) with conversational relevance (edited files, mentioned files, FTS matches on conversation terms, git co-change partners)" (from docs/repo-map.md). Supports 33 languages with convention-based visibility detection (name-based for Go, keyword-based for Rust/Java, file-based for C/C++).
- **Surgical symbol extraction**: Instead of reading files line-by-line, the agent extracts exactly the function or class by name through a 4-tier fallback chain: "LSP, ts-morph, tree-sitter, regex" (from README.md). A 500-line file becomes a 20-line symbol extraction.
- **Blast radius scoring**: "[R:N]" tags on each file show how many files import it, revealing impact of edits before they're made.
- **Clone detection**: AST shape hash + MinHash to identify duplicated code patterns across the codebase.
- **Dead code tracking**: Distinguishes unused exports (dead code) from merely unnecessary code.

### Multi-Agent Architecture

- **Spark/Ember dispatch**: Task classification routes work to specialized agents. "Sparks" (tier 1) handle read-only exploration and investigation, sharing the forge's system prompt for cache prefix hits. "Embers" (tier 2) handle code implementation with their own model and context. "WebSearch" agents (specialized tier) do multi-step web research with scraping.
- **AgentBus coordination**: "In-process coordination layer for parallel subagents. Handles file caching (deduplicated reads across agents), tool result caching (persists across dispatches), edit coordination (serialized writes per file with ownership tracking), and real-time peer findings" (from docs/architecture.md).
- **Task router**: Per-task model assignment with slots for spark, ember, webSearch, desloppify, verify, compact, semantic, default. Supports mix-and-match models: Opus for planning, Sonnet for coding, Haiku for cleanup.

### Code Intelligence (4-Tier Router)

- **Tier 1 — LSP (Language Server Protocol)**: Definitions, references, rename, diagnostics, code actions, call hierarchy, type info, formatting.
- **Tier 2 — ts-morph**: TypeScript/JavaScript AST definitions, references, rename, extract function/variable, unused detection.
- **Tier 2 — tree-sitter**: 33 languages via WASM grammars. Symbol extraction, imports/exports, scopes, outlines.
- **Tier 3 — Regex**: Universal fallback for symbol search and simple definitions.
- **Dual LSP architecture**: Routes requests through Neovim's running servers when the editor is open (zero startup cost). Spawns standalone servers when the editor is closed. Both modes stay synchronized.

### Compound Tools

- **`read` with batch + surgical extraction**: Read multiple files in parallel, extract only the symbols needed by name.
- **`multi_edit` with atomic writes**: Multiple file edits in a single tool call, guaranteed atomic.
- **`rename_symbol`, `move_symbol`**: Compiler-guaranteed cross-file refactoring.
- **`refactor`**: Targeted refactoring within a function or class.
- **`project` tool**: Auto-detects 25+ ecosystems, runs lint/test/build/typecheck with pre-commit hooks and monorepo discovery.

### Multi-Provider Support

19 providers supported: "Anthropic, OpenAI, Google, xAI, Groq, DeepSeek, Mistral, Bedrock, Fireworks, MiniMax, Copilot, GitHub Models, Ollama, LM Studio, OpenRouter, LLM Gateway, Vercel AI Gateway, Proxy, any OpenAI-compatible" (from README.md). Custom OpenAI-compatible providers via config.

### Context Management

- **Compaction**: "Working state is extracted incrementally as the conversation happens: files touched, decisions made, errors hit. When context gets long, compaction fires instantly from this pre-built state. Rich enough state skips the LLM entirely" (from README.md).
- **Prompt caching**: Soul Map is stable across turns, stays cached. On Anthropic, the system prompt costs a fraction of normal.
- **Budget scaling**: "The repo map's token budget scales inversely with conversation length. Min + (Max - Min) × max(0, 1 - conversationTokens / 100,000). Start of conversation: 2,500 tokens; mid conversation (~50K tokens): ~2,000 tokens; late conversation (~100K+ tokens): 1,500 tokens" (from docs/repo-map.md).

### Embedded Neovim

- "Your config, plugins, LSP servers. The AI works through the same editor you use" (from README.md).
- Msgpack-RPC integration with live editor state.
- Neovim 0.11+ required. First launch auto-installs Mason language servers.

### Operational Modes

- **default**: Full agent with all tools available.
- **auto**: Executes immediately without confirmation.
- **architect**: Read-only analysis and review.
- **socratic**: Guided learning through questions.
- **challenge**: Pushes back on assumptions.
- **plan**: Planning only, no code changes.

### Headless Mode

- Non-interactive CLI operation with streaming output.
- `--headless --json`: Structured JSON output after completion.
- `--headless --events`: Real-time JSONL event stream.
- `--headless --model`: Override default model per invocation.
- `--headless --mode`: Set operational mode.
- Multi-turn chat support with session persistence.

### Skills and Gates

- Installable skills for domain-specific work.
- Destructive actions require user confirmation (toggleable).
- Auto mode for full autonomy.
- Scans `~/.soulforge/skills/`, `~/.agents/skills/`, `~/.claude/skills/` plus project-local skills.

### User Steering

"Type while the agent works. Messages queue and arrive at the next step" (from README.md). Enables mid-stream user input without blocking agent execution.

### Configuration

- Layered: global (`~/.soulforge/config.json`) + project (`.soulforge/config.json`).
- Instruction file loading: SOULFORGE.md, CLAUDE.md, .cursorrules, AGENTS.md.
- Per-task model routing via taskRouter config.
- Thinking mode configuration (adaptive, extended, disabled).
- Performance tuning: effort, speed, parallel tool use.

---

## Technical Architecture

### System Overview

User input flows through an InputBox (OpenTUI React component) to the useChat hook (Vercel AI SDK) to the Forge Agent orchestrator. The Forge Agent dispatches work to Spark agents (exploration), Ember agents (code), and WebSearch agents in parallel through an AgentBus coordination layer.

The AgentBus manages a file cache (deduplicated reads across agents), tool result cache (persists across dispatches), findings aggregation, and an edit mutex (serialized per-file writes with ownership tracking). All agents access shared Tools (35+ tools), an Intelligence Router (LSP → ts-morph → tree-sitter → regex fallback), and a Neovim instance (msgpack-RPC).

### Runtime and Language

- **Runtime**: Bun (not Node.js). Requires Bun >= 1.2.0.
- **Language**: TypeScript in strict mode.
- **Database**: SQLite with bun:sqlite for repo map, memory, and sessions.

### Core Modules (from SOULFORGE.md)

- **`src/boot.tsx`**: Main entry, splash animation, headless detection, dependency setup.
- **`src/index.tsx`**: TUI renderer setup (OpenTUI + React).
- **`src/headless/`**: Headless CLI (parse, run, providers, output, types, constants).
- **`src/components/App.tsx`**: Main React component.
- **`src/core/agents/forge.ts`**: Main Forge agent (createForgeAgent).
- **`src/core/context/manager.ts`**: ContextManager (system prompt, repo map, memory).
- **`src/core/tools/`**: All 30+ tools (read, edit_file, shell, soul_*, etc.).
- **`src/core/llm/`**: Provider registry, model resolution, provider options.
- **`src/core/intelligence/`**: LSP, ts-morph, tree-sitter, regex fallback chain.
- **`src/core/instructions.ts`**: SOULFORGE.md / CLAUDE.md / .cursorrules loader.
- **`src/core/sessions/`**: Session save/restore (JSONL files with crash-resilient incremental saves).

### Repo Map Internals

The Repo Map follows a six-phase process:

1. **Index Phase**: Walk file tree, parse with tree-sitter, extract symbols, imports, and references, build cross-file edges, store in SQLite.
2. **Graph Phase**: Run PageRank (20 iterations, damping factor 0.85) over file→file edge graph.
3. **Co-Change Phase**: Parse `git log --name-only` for last 300 commits. Record pairwise file combinations in commits with 2–20 files (filters >20 as noise).
4. **Ranking Phase**: "PageRank with personalized restart vector: Edited files 5x base weight, Mentioned files 3x, Active editor file 2x, Co-change partners proportional" (from docs/repo-map.md). Plus post-hoc signals: FTS match +0.5, graph neighbor +1.0, co-change partner +min(count/5, 3.0).
5. **Rendering Phase**: Binary search to maximize file blocks within token budget. Shows exported symbols with `[R:N]` blast radius tags and LLM-generated semantic summaries.
6. **Semantic Summaries**: Top symbols by PageRank get one-line LLM-generated descriptions, cached by file mtime.

### LLM Layer

Built on Vercel AI SDK with provider abstraction. Each provider has an SDK: `@ai-sdk/anthropic`, `@ai-sdk/openai`, `@ai-sdk/google`, etc. Model family detection (`detectModelFamily()`) handles direct providers, gateways, and proxy routing.

Per-family system prompts (`src/core/prompts/families/`) optimized for Claude, OpenAI, Google, and default models. Mode overlays (`architect`, `plan`, `auto`, `socratic`, `challenge`) apply task-specific guidance.

Soul Map injected as user→assistant message pair (aider-style pattern) for prompt cache efficiency.

### Agent Loop

Fully decoupled from TUI. Works headless via `createForgeAgent().stream()`. All approval callbacks optional — omitting them auto-allows (headless behavior).

### Custom Providers

Use `createOpenAI({ baseURL, apiKey })` pattern same as Ollama. Config-driven custom provider builder in `src/core/llm/providers/custom.ts`. Conflicts auto-suffix to `{id}-custom`.

---

## Installation & Usage

### Homebrew (Recommended)

```bash
brew tap proxysoul/tap
brew install soulforge
```

### Bun (Global)

Requires Bun >= 1.0:

```bash
curl -fsSL https://bun.sh/install | bash
bun install -g @proxysoul/soulforge
soulforge
```

### Prebuilt Binary

Download from [Releases](https://github.com/ProxySoul/soulforge/releases/latest):

```bash
tar xzf soulforge-*.tar.gz && cd soulforge-*/ && ./install.sh
```

Installs to `~/.soulforge/`, adds to PATH.

### Build from Source

Requires Bun >= 1.0 and Neovim >= 0.11:

```bash
git clone https://github.com/ProxySoul/soulforge.git && cd soulforge && bun install
bun run dev          # development mode
# or
bun run build && bun link && soulforge
```

### TUI Usage

```bash
soulforge                                # Launch, pick model with Ctrl+L
soulforge --set-key anthropic sk-ant-... # Save API key
soulforge --headless "prompt here"       # Non-interactive
```

### Headless Mode

```bash
soulforge --headless "your prompt"               # Stream to stdout
soulforge --headless --json "prompt"             # Structured JSON
soulforge --headless --chat                      # Multi-turn
soulforge --headless --model provider/model      # Override model
soulforge --headless --mode architect            # Read-only
soulforge --headless --diff "fix the bug"        # Show changed files
```

### Configuration

Global config: `~/.soulforge/config.json`
Project config: `.soulforge/config.json`

Example with task router:

```json
{
  "defaultModel": "anthropic/claude-sonnet-4-6",
  "thinking": { "mode": "adaptive" },
  "repoMap": true,
  "taskRouter": {
    "spark": "anthropic/claude-sonnet-4-6",
    "ember": "anthropic/claude-opus-4-6",
    "webSearch": "anthropic/claude-haiku-4-5",
    "desloppify": "anthropic/claude-haiku-4-5",
    "compact": "google/gemini-2.0-flash"
  },
  "instructionFiles": ["soulforge", "claude", "cursorrules"]
}
```

Drop a `SOULFORGE.md` in project root for conventions, architecture notes, preferences.

---

## Relevance to Claude Code Development

### Applications

- **Codebase awareness patterns**: SoulForge's repo map demonstrates how to build a persistent, updatable codebase index with PageRank + personalization. The strategy of building a graph on startup and maintaining it incrementally is directly applicable to Claude Code's file caching and context management.
- **Multi-agent coordination**: The AgentBus pattern (file caching, tool result caching, edit coordination with ownership tracking) shows how to parallelize agents without conflicts. Directly relevant to Claude Code's subagent and team coordination.
- **Surgical code reading**: The 4-tier intelligence router (LSP → ts-morph → tree-sitter → regex) demonstrates robust fallback chains for symbol extraction. Claude Code could adopt similar fallbacks for cross-language symbol lookup.
- **Task routing**: Per-task model assignment (spark/ember/webSearch) shows how to route different cognitive tasks to different models cost-effectively. Relevant to Claude Code's model selection for different agent types.
- **Headless integration**: SoulForge's headless CLI with structured JSON output and streaming JSONL events demonstrates patterns for CI/CD integration and programmatic usage. Applicable to Claude Code's agent use in automation workflows.

### Patterns Worth Adopting

- **Live repo graphs with incremental updates**: Maintain a SQLite-backed codebase index. Update on file edits (debounced). Adapt ranking per-turn based on conversation context.
- **Budget scaling**: Token budget for codebase context scales inversely with conversation length. Prevents wasting space early in conversations on comprehensive maps while leaving room for actual work later.
- **Semantic summaries cached by mtime**: Generate one-line descriptions of top symbols, cache by file modification time. Refreshes only when files change.
- **Cochange analysis**: Parse git log to find files always edited together. Captures implicit coupling that import graphs miss.
- **Dual-backend architecture for LSP**: When an editor is available, route through its running servers. When not, spawn standalone servers. Avoids startup cost while maintaining server warmth.
- **Schema enforcement for dispatch**: Require explicit targetFiles with real paths on subagent dispatch. Prevents hallucinated file paths.

### Integration Opportunities

- **MCP server extraction**: SoulForge is extracting its intelligence layer as reusable packages. Roadmap includes `@soulforge/mcp` as MCP servers for Claude Code, Cursor, Copilot, and other MCP clients.
- **Prompt caching strategy**: Adopt SoulForge's system prompt + repo map caching via user→assistant message pairs. Reduces token cost on supported providers.
- **Real-time project detection**: Auto-detect 25+ project ecosystems (npm, Python, Rust, Go, Java, etc.). SoulForge's project tool demonstrates comprehensive ecosystem detection.
- **Thinking mode configuration**: SoulForge's configurable thinking (adaptive, extended, disabled) per provider is relevant as Claude Code considers thinking support across model families.

---

## References

- [SoulForge GitHub Repository](https://github.com/ProxySoul/soulforge) (accessed 2026-04-05)
- [SoulForge README.md](https://github.com/ProxySoul/soulforge/blob/main/README.md) (accessed 2026-04-05)
- [SoulForge SOULFORGE.md](https://github.com/ProxySoul/soulforge/blob/main/SOULFORGE.md) (accessed 2026-04-05)
- [SoulForge Architecture Documentation](https://github.com/ProxySoul/soulforge/blob/main/docs/architecture.md) (accessed 2026-04-05)
- [SoulForge Repo Map Documentation](https://github.com/ProxySoul/soulforge/blob/main/docs/repo-map.md) (accessed 2026-04-05)
- [SoulForge Getting Started Guide](https://github.com/ProxySoul/soulforge/blob/main/GETTING_STARTED.md) (accessed 2026-04-05)
- [SoulForge CHANGELOG](https://github.com/ProxySoul/soulforge/blob/main/CHANGELOG.md) (accessed 2026-04-05)
- [SoulForge LICENSE (Business Source License 1.1)](https://github.com/ProxySoul/soulforge/blob/main/LICENSE) (accessed 2026-04-05)
- [SoulForge package.json](https://github.com/ProxySoul/soulforge/blob/main/package.json) (accessed 2026-04-05)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Aider](../coding-agents/aider.md) | coding-agents | Inspiration source: tree-sitter repo maps with PageRank; SoulForge adds cochange, blast radius, clone detection, live updates |
| [oh-my-opencode](../research-agent-patterns/oh-my-opencode.md) | research-agent-patterns | Production-scale multi-agent orchestration: shares Sisyphus/Atlas/Prometheus agent pools, category-based model routing, hash-anchored editing patterns |
| [oh-my-claudecode](../agent-orchestration/oh-my-claudecode.md) | agent-orchestration | 32-agent orchestration with natural language routing; parallels SoulForge's Spark/Ember/WebSearch dispatch and per-task model assignment |
| [Gastown](../research-agent-patterns/gastown.md) | research-agent-patterns | Multi-agent workspace coordination via tmux; shares supervisor-worker parallelism and persistent state management across agent sessions |
| [Everything Claude Code](../agent-frameworks/everything-claude-code.md) | agent-frameworks | 16-agent orchestration system with 65+ skills; comparable multi-agent architecture with hook-based automation and token optimization |
| [pi-mono](../agent-frameworks/pi-mono.md) | agent-frameworks | TypeScript monorepo with unified LLM API and multiple UI runtimes (CLI, TUI, web); shares SoulForge's multi-interface approach and provider abstraction |
| [Tersa](../agent-frameworks/tersa.md) | agent-frameworks | Visual AI pipeline orchestration with 25+ LLM providers via Vercel AI SDK Gateway; shares provider-agnostic routing and multi-model support |
| [Claude-Mem](../context-management/claude-mem.md) | context-management | Persistent memory compression for Claude Code agents; complements SoulForge's context compaction strategy with progressive disclosure patterns |
| [LocalAI](../llm-infrastructure/localai.md) | llm-infrastructure | Multi-provider local inference with OpenAI-compatible API; enables SoulForge's provider abstraction for offline and on-prem deployments |
| [Google ADK Context Engineering](../research-agent-patterns/google-adk-context-engineering.md) | research-agent-patterns | Tiered storage and compiled views for multi-agent handoffs; overlaps with SoulForge's budget-scaled repo map and context extraction patterns |

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | 2026-04-05 |
| Version at Verification | v2.4.0 |
| Next Review Recommended | 2026-07-05 |
| Confidence Map | `Overview: high (direct read)`, `Problem Addressed: high (direct read)`, `Key Statistics: high (gh api)`, `Key Features: high (direct read)`, `Technical Architecture: high (direct read + code analysis)`, `Installation & Usage: high (direct read)`, `Relevance to Claude Code: medium (inferred from feature set)` |
