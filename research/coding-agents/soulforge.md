# SoulForge

**Research Date**: 2026-04-05
**Source URL**: <https://github.com/ProxySoul/soulforge>
**GitHub Repository**: <https://github.com/ProxySoul/soulforge>
**Version at Research**: 2.4.0
**License**: Business Source License 1.1 (converts to Apache 2.0 on March 15, 2030)

---

## Overview

SoulForge is a graph-powered multi-agent coding assistant that builds a live SQLite-backed dependency graph of entire codebases on startup. Instead of performing naive file reads and grep operations like traditional AI coding tools, SoulForge indexes every file, symbol, import, and export with PageRank importance ranking, git co-change history, and real-time updates. The system dispatches parallel explore (Spark), code (Ember), and web search agents with shared caching and atomic multi-file edits, supporting 19 LLM providers and embedded Neovim with LSP integration.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| AI coding tools start blind, wasting time orienting themselves | Live Soul Map (SQLite graph) indexes entire codebase with PageRank ranking, blast radius scoring, and FTS5 search — agent knows what matters before first turn |
| Large files waste token budget for small edits | Surgical reads extract individual functions/classes by name across 33 languages via 4-tier fallback (LSP → ts-morph → tree-sitter → regex) |
| Context window fills quickly with repetitive information | Instant compaction extracts working state incrementally (files touched, decisions made, errors) for fast context recovery without full LLM processing |
| Multiple agents duplicating reads and conflicting on edits | AgentBus with shared file cache, tool result cache, and serialized write coordination with ownership tracking |
| Cost of running agents — multiple context windows, repeated work | Model mixing (Opus for planning, Sonnet for coding, Haiku for cleanup), prompt caching (Soul Map stays cached), shared agent cache, compaction to skip LLM entirely |
| Single model inadequate for all task types | Task router assigns per-task models: spark (explore), ember (code), webSearch, desloppify, verify, compact, semantic, default |
| Multi-tab workflows with file conflicts and unclear state | Per-tab models, per-tab mode, file claims, cross-tab git coordination, warnings on contested files |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Repository | 1 commit visible (shallow clone depth) | 2026-04-05 |
| Latest Release | 2.4.0 (released 2026-04-05) | 2026-04-05 |
| License | Business Source License 1.1 (BSL 1.1) | 2026-04-05 |
| Runtime | Bun >= 1.2.0 (not Node.js) | 2026-04-05 |
| TypeScript | Strict mode enabled | 2026-04-05 |

*Note: Star count and contributor count data could not be gathered from the shallow clone; these metrics should be obtained from GitHub API on next research cycle.*

---

## Key Features

### Codebase Intelligence

- **Live Soul Map**: SQLite-backed graph with PageRank file ranking (PageRank algorithm, 20 iterations, damping factor 0.85), blast radius scoring, clone detection via MinHash, FTS5 symbol search, and unused export detection
- **Real-time Updates**: Files re-indexed when modified (debounced), PageRank recomputed, edges updated
- **33-Language Support**: tree-sitter AST parsing with convention-based visibility detection (capitalized in Go, underscore prefix in Python, keyword-based in Rust/Java, etc.)
- **Co-change Analysis**: Git log parsed for last 300 commits, pairwise co-change patterns recorded to identify implicit coupling between files without direct imports
- **Semantic Summaries**: Top symbols get LLM-generated one-line descriptions, cached by file mtime, configurable summary model via task router

### Code Intelligence Router

- **4-Tier Fallback**: LSP (tier 1) → ts-morph (tier 2) → tree-sitter (tier 2) → regex (tier 3)
- **Dual LSP Backend**: Bridges to Neovim's running servers when editor open (zero startup cost); spawns standalone servers when editor closed (full protocol support)
- **Multi-Language Coverage**: All 33 supported repo map languages
- **Operations Supported**: Symbol extraction, definitions, references, rename, diagnostics, code actions, call hierarchy, type info, formatting
- **Post-Edit Diagnostics**: LSP diagnostics diffed against pre-edit state to surface new errors, resolved errors, and cross-file impact

### Multi-Agent Orchestration

- **Three Agent Tiers**: Forge (orchestrator, main model), Spark (read-only explore/investigate, shared cache), Ember (code editing, own model)
- **Parallel Dispatch**: All three agent types run concurrently with AgentBus coordination
- **Shared Cache Strategy**: Sparks share forge's system prompt + tool definitions for cache prefix hits; Embers use fresh context
- **Edit Coordination**: File writes serialized per-file with ownership tracking, preventing conflicts
- **Optional Post-Dispatch Passes**: De-sloppify (cleanup agent reviews edits) and verify (checks correctness), both configurable
- **Step Limits**: Sparks capped at 28 steps (explore) or 18 steps (code); Embers uncapped

### Compound Tools

- **read**: Batch + surgical reads in parallel (only first read expensive; subsequent reads get compact stub)
- **multi_edit**: Atomic multi-file edits
- **rename_symbol**, **move_symbol**, **rename_file**: Compiler-guaranteed cross-file operations
- **refactor**: Guided code transformation
- **project**: Auto-detects 25+ ecosystems (package.json, pyproject.toml, Cargo.toml, go.mod, pom.xml, build.gradle, etc.); runs lint/test/build/typecheck commands
- **memory_write**, **memory_search**, **memory_list**, **memory_delete**: Persistent working memory

### LLM Provider Ecosystem

- **19 Providers**: Anthropic, OpenAI, Google, xAI, Groq, DeepSeek, Mistral, Amazon Bedrock, Fireworks, MiniMax, GitHub Copilot, GitHub Models, Ollama, LM Studio, OpenRouter, LLM Gateway, Vercel AI Gateway, Proxy, custom OpenAI-compatible
- **Task Router**: Per-task model assignment (spark, ember, webSearch, desloppify, verify, compact, semantic, default); resolution: slot → default → active model
- **Config-Driven Custom Providers**: Any OpenAI-compatible API via `providers` array in config; auto-suffixes conflicts to `{id}-custom`
- **Prompt Caching**: Soul Map stable across turns, stays cached on Anthropic

### User Interfaces

- **TUI (OpenTUI + React)**: Real-time chat, live tool call progress, markdown rendering, syntax-highlighted code, slash commands
- **Headless CLI**: `--headless` for non-interactive, `--json` for structured output, `--events` for JSONL stream, piped input support
- **Embedded Neovim**: Your config, plugins, LSP servers; split-pane editor ↔ chat via Ctrl+E
- **Lock-in Mode** (`/lock-in`): Hides narration, shows only tool activity and final answer
- **Multiple Editor Modes**: default (full agent), auto (no questions), architect (read-only), plan (planning only), socratic (guided learning), challenge (pushback)

### Context Management

- **Instant Compaction**: Working state extracted incrementally as conversation happens (files touched, decisions made, errors); compaction fires instantly from pre-built state, skipping LLM entirely when possible
- **Layered Config**: Global (`~/.soulforge/config.json`) + project (`.soulforge/config.json`)
- **Instruction Files**: Loads SOULFORGE.md, CLAUDE.md, .cursorrules, AGENTS.md from 10 sources; toggleable via `/instructions` or config
- **Conversation Tracking**: Edited files, mentioned files, conversation terms flow into repo map personalization; system prompt evolves as conversation progresses
- **Session Persistence**: JSONL-based incremental saves with crash recovery; sessions restorable to mid-conversation

### Code Execution

- **Sandboxed Python via Anthropic**: Optional code_execution tool for processing data, calculations, batch tool calls programmatically

---

## Technical Architecture

### System Overview

The system dispatches three concurrent agent types: Forge (main orchestrator), Spark (read-only explore/investigate agents with shared cache), and Ember (code editing agents with dedicated models). All three coordinate through AgentBus, which handles file caching, tool result caching, edit serialization with ownership tracking, and findings sharing.

Core components:

- **Forge Agent** (`src/core/agents/forge.ts`): Main orchestrator dispatching subagents, managing dispatch loop, calling done tools, handling user approvals
- **AgentBus** (`src/core/agents/agent-bus.ts`): In-process coordination for file caching (deduplicated reads), tool result caching (persists across dispatches), edit coordination (serialized writes with ownership), real-time peer findings
- **Intelligence Router** (`src/core/intelligence/router.ts`): Routes code intelligence operations via 4-tier fallback (LSP tier 1 → ts-morph tier 2 → tree-sitter tier 2 → regex tier 3)
- **ContextManager** (`src/core/context/manager.ts`): Assembles system prompt from mode instructions, project info, git context, repo map, persistent memory, forbidden file patterns, skills
- **Tool Suite**: 35+ tools across intelligence, editing, project, memory, and dispatch domains
- **Provider Registry** (`src/core/llm/providers/`): Multi-provider abstraction via Vercel AI SDK, per-family system prompts, task router for model assignment

Data flows as: User input → Forge classifies task → Dispatch subagent → AgentBus coordinates caching/writes → Compaction (optional) → Output (TUI/JSON/JSONL) → Session JSONL save.

### Repo Map Ranking

Files ranked by blending structural importance (PageRank over import graph) with conversational relevance:

- **PageRank personalization**: Edited files (5x weight), mentioned files (3x), active editor file (2x), co-change partners (proportional, capped 2x)
- **Post-hoc signals**: FTS match on conversation terms (+0.5), graph neighbor (+1.0), co-change partner (+min(count/5, 3.0))
- **Budget scaling**: MAX (2,500 tokens at start) → MIN (1,500 tokens late conversation) inversely proportional to conversation tokens
- **Semantic summaries**: LLM-generated per symbol, cached by file mtime, regenerated on edit

### LSP Integration

**When Neovim editor is open:**
- Routes all LSP requests through Neovim's running servers (zero startup cost)
- Standalone servers warm as hot standby

**When Neovim editor is closed:**
- Spawns LSP servers directly (full protocol support)
- Multi-language warmup on boot
- Mason servers auto-installed on first editor launch

---

## Installation & Usage

### Installation Methods

**Homebrew (recommended):**

```bash
brew tap proxysoul/tap
brew install soulforge
```

**Bun global install:**

```bash
bun install -g @proxysoul/soulforge
soulforge
```

**Prebuilt binary:**

```bash
tar xzf soulforge-*.tar.gz && cd soulforge-*/ && ./install.sh
```

**Build from source:**

```bash
git clone https://github.com/ProxySoul/soulforge.git
cd soulforge && bun install
bun run dev          # development mode
```

### Basic Usage

```bash
soulforge                                    # TUI mode
soulforge --headless "fix the bug"          # Stream to stdout
soulforge --headless --json "prompt"        # Structured JSON
soulforge --headless --model openai/gpt-4o  # Override model
soulforge --headless --mode architect       # Read-only analysis
soulforge --set-key anthropic sk-ant-...    # Save API key
```

### Configuration Example

Global config at `~/.soulforge/config.json`:

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

Project config (`.soulforge/config.json`) overrides global settings.

---

## Relevance to Claude Code Development

### Applications

1. **Codebase Orientation**: SoulForge builds live dependency graph with PageRank; Claude Code uses file reads + grep. Applicable patterns: PageRank ranking, git co-change analysis for implicit coupling, blast radius scoring.

2. **Multi-Agent Coordination**: SoulForge's AgentBus coordinates Spark/Ember/WebSearch agents with shared caching and serialized writes. Applicable to Claude Code subagent delegation — file mutex and write coordination prevent conflicts.

3. **Surgical Code Reads**: SoulForge extracts specific functions/classes by name (500-line file → 20-line symbol) via 4-tier fallback. Directly applicable for context window optimization.

4. **Context Compaction**: SoulForge extracts working state incrementally (files touched, decisions, errors) for fast recovery. Applicable when Claude Code context fills — pre-built compaction state skips LLM re-processing.

5. **Task Routing by Model**: SoulForge maps tasks to specific models (Opus planning, Sonnet coding, Haiku cleanup) via `taskRouter`. Applicable to Claude Code multi-model strategy — per-task assignment reduces cost while improving quality.

### Patterns Worth Adopting

- Dual LSP architecture (Neovim bridge when open, standalone when closed)
- Real-time repo indexing with debounced re-scans
- Provider-agnostic prompt system (per-family specialization)
- Config layering (global + project + per-agent overrides)
- Semantic summaries cached by mtime (reduces token spend on repo map)

### Integration Opportunities

- SoulForge roadmap includes `@soulforge/mcp` — Soul Map tools as MCP servers for Claude Code, Cursor, Copilot
- Compaction working state extraction could become Claude Code skill for context management
- Task router pattern applicable to Claude Code model selection strategy
- Blast radius tags `[R:N]` usable as Claude Code analysis tool to warn of unintended side effects

---

## Limitations and Caveats

### Documented Limitations

1. **Business Source License (BSL 1.1)**: Free for personal and internal use. Commercial use (hosting, embedding, managed service) requires license. Converts to Apache 2.0 on March 15, 2030.

2. **Neovim Dependency**: Embeds Neovim only (no VS Code, Vim, other editors). Requires Neovim >= 0.11.

3. **Nerd Font Requirement**: UI requires Nerd Font for icons; blank squares appear without it.

4. **Bun Runtime Only**: Requires Bun >= 1.2.0, not Node.js.

5. **SQLite Performance**: Repo map uses in-memory + on-disk SQLite. Indexing time scales with codebase size; no public benchmarks available.

### Undocumented Gaps

- Monorepo support listed as "planned" in roadmap; current behavior undefined
- No published benchmarks for indexing time, memory, or graph performance at scale
- 33 languages listed; no tier breakdown (full vs. best-effort support)
- LLM thinking mode behavior and cost implications undocumented
- Clone detection via MinHash — exact algorithm parameters and false-positive rates not documented

---

## References

- [SoulForge README](https://github.com/ProxySoul/soulforge/blob/main/README.md) (accessed 2026-04-05)
- [SoulForge GETTING_STARTED.md](https://github.com/ProxySoul/soulforge/blob/main/GETTING_STARTED.md) (accessed 2026-04-05)
- [SoulForge SOULFORGE.md](https://github.com/ProxySoul/soulforge/blob/main/SOULFORGE.md) (accessed 2026-04-05)
- [SoulForge docs/architecture.md](https://github.com/ProxySoul/soulforge/blob/main/docs/architecture.md) (accessed 2026-04-05)
- [SoulForge docs/repo-map.md](https://github.com/ProxySoul/soulforge/blob/main/docs/repo-map.md) (accessed 2026-04-05)
- [SoulForge package.json](https://github.com/ProxySoul/soulforge/blob/main/package.json) (accessed 2026-04-05)
- [SoulForge LICENSE](https://github.com/ProxySoul/soulforge/blob/main/LICENSE) (accessed 2026-04-05)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| Claude Code | coding-agents | Competing agent framework; SoulForge differentiates via live graph, multi-provider support, embedded editor |
| Aider | coding-agents | Inspirational source; SoulForge extends tree-sitter repo maps with cochange, blast radius, clone detection, live updates |

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | 2026-04-05 |
| Version at Verification | 2.4.0 |
| Next Review Recommended | 2026-07-05 |
| Confidence Map | Overview: high; Problem Addressed: high; Key Statistics: medium (star/contributor counts unavailable from shallow clone); Key Features: high; Technical Architecture: high (doc + code-read); Installation & Usage: high; Relevance to Claude Code: high; Limitations: high (documented), medium (undocumented gaps); References: high |
