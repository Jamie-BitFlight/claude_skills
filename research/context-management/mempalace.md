---
title: MemPalace
subtitle: AI Memory System — 96.6% LongMemEval Score, Zero API Calls
category: context-management
resource_type: library
github_url: https://github.com/milla-jovovich/mempalace
pypi_url: https://pypi.org/project/mempalace/
license: MIT
latest_version: 3.0.0
python_requirement: ">=3.9"
---

## Overview

MemPalace is an open-source AI memory system that stores verbatim conversation transcripts and code in a navigable palace structure without requiring API keys, cloud storage, or external summarization. It achieves 96.6% recall on the LongMemEval benchmark using only local ChromaDB and semantic search, making it the highest-published zero-API-cost memory system. The system runs entirely on the user's machine and provides both CLI and Model Context Protocol (MCP) server interfaces for integration with Claude, ChatGPT, Gemini, and local LLMs.

**Honest status (as of April 2026)**: The project's authors published a correction note directly addressing overclaimed metrics. The 96.6% score is from raw verbatim mode (not AAAK compression). AAAK itself regresses performance to 84.2% versus 96.6% raw mode. Contradiction detection is partially implemented. Palace structure provides documented +34% R@10 improvement but this is standard metadata filtering, not a novel retrieval mechanism.

---

## Problem Addressed

Multi-turn AI conversations are ephemeral. After each session ends, the accumulated context — decisions made, debugging insights, architectural discussions, code changes — is lost. A developer using Claude daily for 6 months generates approximately 19.5 million tokens of decision history. Conventional memory approaches either:

1. **Paste everything** — requires context window larger than all accumulated data
2. **LLM-extracted summaries** — costs $507/year and loses context during extraction (the "why" is discarded when the AI extracts "user prefers Postgres")

SOURCE: README.md lines 161–175 (<https://github.com/milla-jovovich/mempalace/blob/main/README.md#the-problem>), accessed 2026-04-08.

MemPalace inverts this: **store everything verbatim, then make it findable through structure.** The wake-up context loads only ~170 tokens of critical facts (identity, team, projects, preferences) and queries fire on demand, reducing annual cost to ~$10 while preserving exact language.

---

## Key Statistics

| Metric | Value | Source |
|--------|-------|--------|
| **LongMemEval R@5 (raw mode)** | 96.6% | 500 questions independently reproduced on M2 Ultra |
| **LongMemEval R@5 (hybrid + Haiku rerank)** | 100% | 500/500 questions, all 6 question types |
| **ConvoMem (Salesforce 75K+ QA pairs)** | 92.9% | Verbatim text, semantic search |
| **LoCoMo R@10 (bge-large + Haiku rerank)** | 96.3% | 1,986 multi-hop QA pairs |
| **Palace structure +34% boost** | +34% R@10 | Wing + room metadata filtering vs flat search |
| **AAAK compression regression** | 84.2% (vs 96.6% raw) | Lossy mode on LongMemEval R@5 |
| **Latest stable version** | 3.0.0 | Released 2026-03 |
| **API calls required (raw mode)** | 0 | Runs entirely offline; optional Haiku rerank ~$0.001/query |
| **Annual cost (raw mode + 5 searches)** | ~$10 | Versus $507/year for LLM-extracted summaries |

SOURCES: README.md lines 36–46, 169–175 (<https://github.com/milla-jovovich/mempalace/blob/main/README.md>); benchmarks/BENCHMARKS.md lines 23–61, 64–100 (<https://github.com/milla-jovovich/mempalace/blob/main/benchmarks/BENCHMARKS.md>); April 7 author note README lines 52–83 (<https://github.com/milla-jovovich/mempalace/blob/main/README.md#a-note-from-milla--ben--april-7-2026>), accessed 2026-04-08.

---

## Key Features

### 1. Palace Structure (Wings, Rooms, Halls, Closets, Drawers)

The core organizing principle is a metaphorical palace based on the ancient Method of Loci. Data is hierarchically organized:

- **Wings**: Top-level contexts (person or project). Example: "wing_kai" (team member), "wing_driftwood" (product project)
- **Rooms**: Specific topics within a wing. Example: "auth-migration", "graphql-switch", "ci-pipeline"
- **Halls**: Memory types that appear identically across all wings:
  - `hall_facts` — decisions locked in
  - `hall_events` — sessions, milestones, debugging
  - `hall_discoveries` — breakthroughs, insights
  - `hall_preferences` — habits, likes, opinions
  - `hall_advice` — recommendations, solutions
- **Closets**: Text summaries pointing to original content (plain text in v3.0.0; AAAK-encoded closets planned for v3.1)
- **Drawers**: Original verbatim files stored in ChromaDB without summarization
- **Tunnels**: Automatic cross-references when the same room appears in different wings

The structure improves retrieval from 60.9% (flat search) to 94.8% (wing + room filtering) on tested datasets.

SOURCE: README.md lines 180–262 (palace structure description and hierarchy diagram), pyproject.toml line 4 (version 3.0.0), benchmarks/BENCHMARKS.md lines 254–262 (retrieval improvement measurements).

### 2. Three Mining Modes

MemPalace automatically detects and organizes content from three types of inputs:

**Projects mode** — parses code and documentation:

```bash
mempalace mine ~/projects/myapp
```

Extracts code structure, documentation, notes into rooms inferred from directory structure or manually specified.

**Conversations mode** — normalizes 5 chat export formats:

```bash
mempalace mine ~/chats/ --mode convos
```

Handles Claude, ChatGPT, Slack, Gemini CLI, and custom JSON formats. Chunks by exchange pair (user message + assistant response).

**General mode** — auto-classifies conversations into memory types:

```bash
mempalace mine ~/chats/ --mode convos --extract general
```

Runs auto-extraction that categorizes each exchange into decisions, milestones, problems, preferences, or emotional context without using an LLM.

SOURCE: README.md lines 87–108 (quick start and three modes), mempalace/cli.py lines 66–100 (cmd_mine implementation), mempalace/convo_miner.py line 1.

### 3. MCP Server with 19 Tools

MemPalace exposes a Model Context Protocol server for Claude Code and compatible clients:

```bash
claude mcp add mempalace -- python -m mempalace.mcp_server
```

**Read tools (7)**: `mempalace_status`, `mempalace_list_wings`, `mempalace_list_rooms`, `mempalace_get_taxonomy`, `mempalace_search`, `mempalace_check_duplicate`, `mempalace_get_aaak_spec`

**Write tools (2)**: `mempalace_add_drawer`, `mempalace_delete_drawer`

**Knowledge graph tools (5)**: `mempalace_kg_query`, `mempalace_kg_add`, `mempalace_kg_invalidate`, `mempalace_kg_timeline`, `mempalace_kg_stats`

**Navigation tools (3)**: `mempalace_traverse`, `mempalace_find_tunnels`, `mempalace_graph_stats`

**Agent diary tools (2)**: `mempalace_diary_write`, `mempalace_diary_read`

The AI learns the AAAK dialect and memory protocol automatically from the `mempalace_status` response on first call.

SOURCE: README.md lines 439–491 (MCP server and 19 tools table), mempalace/mcp_server.py lines 1–18 (docstring listing tools).

### 4. AAAK Dialect (Lossy Entity Abbreviation)

AAAK is an experimental compression layer using entity codes, structural markers, and sentence truncation to pack repeated entities into fewer tokens at scale. It is readable by any LLM that reads text (Claude, GPT, Gemini, Llama, Mistral) without a decoder.

**Critical caveats (April 2026 author correction):**
- AAAK is **lossy**, not lossless — uses regex-based abbreviation, not reversible compression
- Does NOT save tokens at small scales — overhead (codes, separators) exceeds savings for short text
- **Can save tokens at scale** — when the same entity is mentioned hundreds of times, codes amortize
- **Regresses LongMemEval from 96.6% (raw) to 84.2% (AAAK)** — the 96.6% headline is from raw verbatim mode, not AAAK
- Storage default is raw verbatim text in ChromaDB; AAAK is a separate context-loading layer, not the storage format
- Initial token count example in README was incorrect (66 tokens vs 73 tokens claimed); rewrite in progress

The MemPalace storage model keeps everything in raw verbatim ChromaDB. AAAK is for compressing the critical facts layer (L1) when waking up a local LLM.

SOURCE: README.md lines 275–287 (AAAK honest status), April 7 author note lines 57–67 (error acknowledgments), benchmarks/BENCHMARKS.md lines 279–286 (AAAK regression details).

### 4. Temporal Knowledge Graph (SQLite)

MemPalace includes a temporal entity-relationship graph for tracking facts with validity windows:

```python
from mempalace.knowledge_graph import KnowledgeGraph

kg = KnowledgeGraph()
kg.add_triple("Kai", "works_on", "Orion", valid_from="2025-06-01")
kg.invalidate("Kai", "works_on", "Orion", ended="2026-03-01")
kg.query_entity("Kai")  # Returns current assignments
kg.query_entity("Kai", as_of="2026-01-20")  # Historical state
kg.timeline("Orion")  # Chronological story
```

Facts are stored with `valid_from` and optional `ended` timestamps. Historical queries use `as_of` parameter. Like Zep's Graphiti but using local SQLite instead of Neo4j cloud.

SOURCE: README.md lines 357–389 (knowledge graph examples and comparison table), mempalace/knowledge_graph.py lines 1–20 (docstring and imports).

### 5. Contradiction Detection (Experimental, Partially Wired)

A utility function (`fact_checker.py`) can validate assertions against entity facts, catching data inconsistencies:

```
Input:  "Soren finished the auth migration"
Output: 🔴 AUTH-MIGRATION: attribution conflict — Maya was assigned, not Soren

Input:  "Kai has been here 2 years"
Output: 🟡 KAI: wrong_tenure — records show 3 years (started 2023-04)
```

Ages, dates, and tenures are calculated dynamically from the knowledge graph. However, this is currently a separate utility and not automatically wired into knowledge graph operations. Integration is in progress (Issue #27).

SOURCE: README.md lines 289–304 (contradiction detection examples), April 7 author note line 64 ("wiring fact_checker.py into the KG ops").

### 6. Two Integration Paths

**With Claude, ChatGPT, Cursor, Gemini** — register the MCP server once and all AI queries trigger automatic tool calls. The AI discovers and uses MemPalace transparently.

**With local models (Llama, Mistral)** — two approaches:
1. Wake-up mode: `mempalace wake-up` outputs ~170 tokens of L0 + L1 context to paste into system prompt
2. CLI search: `mempalace search "query"` pipes results into local model context

Or use the Python API: `from mempalace.searcher import search_memories; results = search_memories("query")`.

SOURCE: README.md lines 111–159 (How You Actually Use It section).

### 7. Auto-Save Hooks for Claude Code

Two hooks automatically save memories during work:

- **Save Hook** — fires every 15 messages; triggers structured save of topics, decisions, quotes, code changes; regenerates L1 critical facts
- **PreCompact Hook** — fires before context compression; emergency save before window shrinks

Configured via `settings.json` or `.claude/hooks/` (project-specific).

SOURCE: README.md lines 495–510 (auto-save hooks with JSON config example).

---

## Technical Architecture

### Core Components

| File | Purpose |
|------|---------|
| `cli.py` (16.5 KB) | CLI entry point — handles init, mine, search, wake-up, status commands |
| `mcp_server.py` (29.4 KB) | MCP server exposing 19 tools; handles both read and write operations |
| `searcher.py` (9.9 KB) | Semantic search interface to ChromaDB collection |
| `miner.py` (20.4 KB) | Project file ingest — walks directories, parses code/docs |
| `convo_miner.py` (12.0 KB) | Conversation export ingest — normalizes 5 formats, chunks by exchange |
| `normalize.py` (10.9 KB) | Format normalization — converts Claude, ChatGPT, Slack, etc. to canonical transcript |
| `knowledge_graph.py` (14.8 KB) | Temporal entity-relationship graph using SQLite backend |
| `palace_graph.py` (7.2 KB) | Wing/room/hall navigation graph for structured retrieval |
| `layers.py` (17.2 KB) | Four-layer memory stack — L0 (identity), L1 (facts), L2 (rooms), L3 (deep search) |
| `dialect.py` (33.8 KB) | AAAK compression — entity codes, truncation, structural markers |
| `entity_detector.py` (21.9 KB) | Auto-detect people and projects from file content |
| `entity_registry.py` (23.1 KB) | Entity code generation and management |
| `general_extractor.py` (14.8 KB) | Auto-classify exchanges into memory types (decisions, problems, preferences, etc.) |
| `onboarding.py` (18.0 KB) | Guided setup — generates AAAK bootstrap and wing config |
| `room_detector_local.py` (9.9 KB) | Infer rooms from directory structure |
| `spellcheck.py` (10.4 KB) | Spell-check utility (optional dependency) |
| `split_mega_files.py` (10.3 KB) | Split concatenated transcript files into per-session files |

SOURCE: mempalace/ directory listing, file sizes, and mempalace/README.md file reference table lines 609–629.

### Data Flow

1. **Init** (`onboarding.py`): User runs `mempalace init ~/projects/myapp`. Entity detector scans files for people and projects. Room detector infers categories from directory structure. Generates `wing_config.json` and `identity.txt`.

2. **Mine** (`miner.py`, `convo_miner.py`): User runs `mempalace mine <dir> [--mode convos]`. Files or conversations are read, normalized to canonical format, split into room-tagged chunks, embedded via ChromaDB's default embeddings, and stored with metadata (wing, room, timestamp).

3. **Search** (`searcher.py`, `palace_graph.py`): Query is embedded. ChromaDB searches closets. Results are optionally filtered by wing/room metadata. Optional tunnels connect cross-wing results for the same room.

4. **Knowledge Graph** (`knowledge_graph.py`): Facts (triples with timestamps) are stored separately in SQLite. Queries can retrieve current state (`as_of=now`) or historical state (`as_of="2026-01-20"`). Invalidation marks facts as ended without deletion.

5. **Wake-up** (`layers.py`): On AI wake-up, L0 (identity) + L1 (critical facts) are generated, optionally compressed to AAAK, and injected into system prompt (~170 tokens). L2 and L3 load on demand via search.

SOURCE: README.md lines 179–273 (How It Works), mempalace/cli.py lines 37–150 (command implementations), mempalace/mcp_server.py lines 45–100 (collection and status initialization).

### Dependencies

**Runtime** (required):
- `chromadb>=0.5.0,<0.7` — vector database and embedding store
- `pyyaml>=6.0` — configuration file parsing

**Optional**:
- `pytest>=7.0` — test suite (dev)
- `ruff>=0.4.0` — linter (dev)
- `autocorrect>=2.0` — spell checking (spellcheck extra)

**Python requirement**: 3.9+ (tested on 3.9, 3.10, 3.11, 3.12)

SOURCE: pyproject.toml lines 27–45, 6.

### Storage

- **Palace data**: ChromaDB persistent collection at `~/.mempalace/palace/` (or custom path in `config.json`)
- **Configuration**: `~/.mempalace/config.json` (global), `~/.mempalace/wing_config.json` (wing mappings), `~/.mempalace/identity.txt` (L0 context)
- **Knowledge graph**: SQLite database at `~/.mempalace/palace/chroma.sqlite3` (embedded in ChromaDB path)
- **Agent diaries**: Per-agent AAAK-encoded files at `~/.mempalace/agents/{agent-name}.txt`

SOURCE: README.md lines 576–606 (Configuration and File Reference sections).

---

## Installation & Usage

### Install

```bash
pip install mempalace
```

Requires Python 3.9+. No API key. No cloud account. Everything runs locally.

### Quick Setup

```bash
# Initialize palace and detect rooms/people
mempalace init ~/projects/myapp

# Mine your project files (code, docs, notes)
mempalace mine ~/projects/myapp

# Mine conversations (Claude, ChatGPT, Slack, etc.)
mempalace mine ~/chats/ --mode convos

# Mine and auto-classify into decisions/problems/preferences
mempalace mine ~/chats/ --mode convos --extract general

# Search everything you've stored
mempalace search "why did we switch to GraphQL"

# Show what's been filed and memory protocol
mempalace status
```

### MCP Integration

```bash
# Register with Claude Code
claude mcp add mempalace -- python -m mempalace.mcp_server

# Now Claude can call all 19 tools automatically
# Example: "What did we decide about auth last month?"
# Claude calls mempalace_search automatically
```

### Python API

```python
from mempalace.searcher import search_memories
from mempalace.knowledge_graph import KnowledgeGraph

# Search
results = search_memories("auth decisions", palace_path="~/.mempalace/palace")

# Knowledge graph
kg = KnowledgeGraph()
kg.add_triple("Kai", "works_on", "Orion", valid_from="2025-06-01")
kg.query_entity("Kai")
```

SOURCE: README.md lines 87–159 (Quick Start, How You Actually Use It), mempalace/cli.py and mempalace/searcher.py for API examples.

---

## Relevance to Claude Code Development

### 1. Session Memory Persistence

MemPalace directly addresses Claude Code's session boundary problem: decisions and architectural insights made in one session evaporate when the session ends. Integrating MemPalace via MCP allows agents and orchestrators to:

- Query past decisions without manual copy-paste: `"What did we decide about authentication in February?"`
- Access project-specific context automatically: wake-up loads team names, key decisions, recent milestones
- Maintain agent expertise: specialist agents (reviewers, architects, ops) keep personal diaries across sessions

### 2. Multi-Agent Coordination

The palace structure (wings for people, rooms for topics, halls for memory types) maps naturally to multi-agent orchestration:

- Each agent can have a dedicated wing or shared rooms across wings
- Agents use `mempalace_diary_write` to record patterns they notice (e.g., reviewer remembers bug patterns)
- Agents use `mempalace_search` to find prior decisions affecting the current task
- Cross-agent learning: one agent reads another's diary via `mempalace_diary_read`

### 3. Benchmark Validation

The 96.6% LongMemEval R@5 score (raw mode, zero API calls) is the single highest published result for open-source memory systems requiring no cloud. This validates the architecture for storing verbatim work transcripts without loss.

### 4. Local-First Privacy

Everything runs on-machine. No conversation data leaves the user's device. No external API calls needed (optional Haiku rerank is ~$0.001/query, not required). Fits the privacy-first ethos of open development.

### 5. Integration Points

- **MCP Server**: 19 tools expose all functionality; Claude Code agents call tools directly
- **CLI**: Agents can shell out to `mempalace search` for one-off queries
- **Python API**: Orchestrators can call `search_memories()` in Python
- **Auto-save hooks**: Integrated into Claude Code `.claude/hooks/` workflow

### 6. Known Limitations

- **AAAK compression is lossy**: Reduces LongMemEval from 96.6% to 84.2%. Use raw mode for critical decisions.
- **Contradiction detection partial**: `fact_checker.py` exists but isn't wired into KG ops automatically yet (in progress, Issue #27).
- **Room auto-detection basic**: Infers rooms from directory structure; complex semantic classification requires `--extract general` (which doesn't use an LLM but is heuristic-based).
- **ChromaDB version pinning**: `chromadb>=0.5.0,<0.7` — newer versions may have breaking changes (Issue #100 notes pinning required).
- **macOS ARM64 segfault**: Known issue on M-series Macs (Issue #74, being addressed).

SOURCE: April 7 author note lines 52–83, GitHub issues #27, #74, #100, #110.

---

## Limitations and Caveats

1. **AAAK Regression**: The 96.6% headline score is from raw verbatim mode. AAAK compression trades fidelity for token density and regresses to 84.2% on LongMemEval. Use AAAK only when context budget is the constraint, not when accuracy matters most.

2. **Contradiction Detection Not Automatic**: The `fact_checker.py` utility can detect inconsistencies but is not currently called automatically by KG operations. Users must manually run or integrate the checking logic.

3. **Room Detection Heuristic-Based**: Automatic room detection from directory structure is simple pattern matching. Complex information hierarchies may require manual room specification via `--wing` flag.

4. **ChromaDB Dependency Lock**: Pinned to `chromadb>=0.5.0,<0.7`. Newer ChromaDB versions are not tested and may introduce breaking changes.

5. **Limited Format Support**: Conversation mining handles Claude, ChatGPT, Slack, Gemini CLI, and custom JSON. Custom formats require pre-processing to canonical JSON.

6. **No Built-In Deduplication Strategy**: The `mempalace_check_duplicate` tool exists for pre-filing checks, but no automatic merging of similar content into single drawers.

7. **Performance on Large Palaces Untested**: Benchmarks use 22,000+ memories. Behavior at 1M+ memories in a single ChromaDB collection is not documented.

8. **Memory Validity Window Not Enforced**: Knowledge graph tracks `valid_from` and `ended` timestamps but doesn't automatically invalidate stale facts during queries. Users must call `kg.invalidate()` explicitly.

SOURCES: April 7 author note (lines 52–83), README.md limitations section (not explicitly listed; inferred from AAAK and contradiction detection notes), GitHub issues #27, #74, #100, #110.

---

## References

- **GitHub Repository**: <https://github.com/milla-jovovich/mempalace> (accessed 2026-04-08)
- **PyPI Package**: <https://pypi.org/project/mempalace/> (version 3.0.0)
- **Official README**: <https://github.com/milla-jovovich/mempalace/blob/main/README.md> (accessed 2026-04-08)
- **Benchmark Results**: <https://github.com/milla-jovovich/mempalace/blob/main/benchmarks/BENCHMARKS.md> (accessed 2026-04-08)
- **Contributing Guide**: <https://github.com/milla-jovovich/mempalace/blob/main/CONTRIBUTING.md> (accessed 2026-04-08)
- **License**: MIT (<https://github.com/milla-jovovich/mempalace/blob/main/LICENSE>)

---

## Freshness Tracking

| Section | Confidence | Last Verified | Notes |
|---------|-----------|---------------|-------|
| **Identity/Metadata** | high | 2026-04-08 | pyproject.toml v3.0.0, MIT license confirmed |
| **Key Statistics** | high | 2026-04-08 | LongMemEval 96.6% independently reproduced (April note line 70); AAAK 84.2% from BENCHMARKS.md line 48 |
| **Features** | high | 2026-04-08 | All 5 major features extracted from README; MCP tools from mcp_server.py docstring |
| **Architecture** | high | 2026-04-08 | File structure and sizes from disk; data flow from cli.py and README How It Works section |
| **Installation** | high | 2026-04-08 | Commands from README Quick Start; Python API from searcher.py docstring |
| **Usage Examples** | high | 2026-04-08 | All examples extracted verbatim from README or source docstrings |
| **Relevance** | high | 2026-04-08 | Integration points from mcp_server.py and README MCP section; multi-agent applicability inferred from palace structure |
| **Limitations** | high | 2026-04-08 | AAAK regression from BENCHMARKS.md and author note; other limitations from April 7 author note and open GitHub issues |

**Next review recommended**: 2026-07-08 (3 months from verification date). Check for:
- AAAK dialect improvements (Issue #43, #27)
- Contradiction detection wiring (Issue #27)
- ChromaDB version compatibility updates (Issue #100)
- macOS ARM64 segfault fix status (Issue #74)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [claude-mem.md](./claude-mem.md) | context-management | Alternative persistent memory plugin; claude-mem uses progressive disclosure, mempalace uses palace structure for the same L0-L3 layering problem |
| [local-memory.md](./local-memory.md) | context-management | Overlapping problem domain: L0-L3 knowledge hierarchy, MCP integration, REST API for memory access |
| [simplemem-cross.md](./simplemem-cross.md) | context-management | Cross-conversation memory with LoCoMo scoring; both use semantic search + entity extraction for agent persistence |
| [sourcesyncai.md](./sourcesyncai.md) | context-management | Managed RAG platform; complementary transport layer for populating mempalace memory via 15+ auto-syncing connectors |
| [unblocked.md](./unblocked.md) | context-management | Context engine with org knowledge integration; both serve same role of injecting structured context into AI agents |
| [jina-ai.md](./jina-ai.md) | context-management | Reader API (URL→Markdown) feeds mempalace mining; URL enrichment layer for conversation and project ingest |
| [slimcontext.md](./slimcontext.md) | context-management | Chat history compression; mempalace AAAK dialect is mempalace's equivalent lossy compression for L1 critical facts |
| [straion.md](./straion.md) | context-management | Rules injection at task time; complements mempalace's decision history with engineering standards |
| [mimir-mcp.md](./mcp-ecosystem/mimir-mcp.md) | mcp-ecosystem | Git-backed memory with graph associations; similar version-controlled persistence, alternative to ChromaDB |
| [trustgraph.md](./agent-infrastructure/trustgraph.md) | agent-infrastructure | Event-driven knowledge graph platform; temporal triple model similar to mempalace temporal KG, both track entity validity windows |
| [sourcesyncai-mcp.md](./mcp-ecosystem/sourcesyncai-mcp.md) | mcp-ecosystem | 28-tool MCP bridge for knowledge bases; transport layer for multi-source data ingest into mempalace palace |

---

**Entry Created**: 2026-04-08 | **Resource**: MemPalace v3.0.0 | **Category**: context-management
