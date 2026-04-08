---
title: graphify v0.3.11
resourceType: AI Coding Assistant Skill
category: skill-generation-tools
resourceName: graphify
url: "https://github.com/safishamsi/graphify/tree/v3"
dateAccessed: "2026-04-08"
---

## Overview

graphify is an AI coding assistant skill that converts any folder of code, documentation, papers, or images into a queryable knowledge graph. Available as `/graphify` command for Claude Code, Codex, OpenCode, OpenClaw, and Factory Droid, it reads files and extracts structural and semantic relationships, producing an interactive HTML graph, a plain-language audit report, and a persistent JSON representation of the knowledge graph. The tool supports 19 programming languages via tree-sitter AST and fully multimodal input (code, PDFs, markdown, screenshots, diagrams, images in other languages via Claude vision).

SOURCE: README.md lines 9, 11 (accessed 2026-04-08)

## Problem Addressed

Developers working with large codebases, research papers, or mixed corpora of documentation and code struggle to understand architectural relationships, design patterns, and implicit connections between components. Traditional search-based navigation (grepping through files) scales poorly with corpus size and misses cross-domain connections. graphify addresses this by extracting all structural and semantic relationships into a single queryable graph, reducing token consumption for subsequent queries by 71.5x on large mixed corpora (52 files, code + papers + images).

SOURCE: README.md line 13, worked examples line 211 (accessed 2026-04-08)

## Key Statistics

| Metric | Value |
|--------|-------|
| Current version | 0.3.11 (released 2026-04-07) |
| Latest language support | 19 languages (Python, JS, TS, Go, Rust, Java, C, C++, Ruby, C#, Kotlin, Scala, PHP, Swift, Lua, Zig, PowerShell, Elixir, Objective-C) |
| Token reduction (Karpathy corpus) | 71.5x fewer tokens per query vs reading raw files |
| Python requirement | 3.10+ |
| License | MIT |
| Primary dependency | NetworkX + tree-sitter + Leiden/Louvain + vis.js |

SOURCE: pyproject.toml line 7, README.md lines 11, 13, 49-50, LICENSE file (accessed 2026-04-08)

## Key Features

**Multimodal input**: Processes code (19 languages via AST), documentation (markdown, reStructuredText, plain text), academic papers (PDF with citation mining), Microsoft Office documents (Word, Excel via optional dependency), and images (screenshots, diagrams, whiteboard photos in any language via Claude vision). Each modality extracts different relationship types.

SOURCE: README.md lines 11, 175-182 (accessed 2026-04-08)

**Relationship classification**: Every edge is tagged with confidence level:
- `EXTRACTED` — relationship found directly in source (direct call, import statement, explicit reference)
- `INFERRED` — reasonable deduction with confidence score (0.0-1.0) assigned by Claude
- `AMBIGUOUS` — uncertain relationships flagged for human review in the report

SOURCE: README.md line 45, ARCHITECTURE.md lines 49-56 (accessed 2026-04-08)

**Knowledge graph outputs**:
- `graph.html` — interactive visualization (node size by degree, click-to-inspect details, full-text search, filter by community)
- `GRAPH_REPORT.md` — one-page summary listing god nodes (highest-degree concepts), surprising connections (ranked by composite score), suggested questions the graph can answer, and the "why" behind design decisions (from docstrings, rationale comments marked `# NOTE:`, `# IMPORTANT:`, `# HACK:`, `# WHY:`)
- `graph.json` — persistent, queryable representation; can be re-used across sessions without re-extraction
- `cache/` — SHA256-keyed semantic and AST cache; re-runs only re-process changed files

SOURCE: README.md lines 20-24, 190-202 (accessed 2026-04-08)

**Hyperedges**: Groups relationships connecting 3+ nodes that pairwise edges cannot express (e.g., all classes implementing a shared protocol, all functions in an authentication flow, all concepts from a paper section forming one cohesive idea). Enables higher-order pattern detection.

SOURCE: README.md line 197 (accessed 2026-04-08)

**Always-on assistant integration**: After building a graph, `graphify claude install` writes a PreToolUse hook to Claude Code's `settings.json`. Before every Glob or Grep call, Claude sees a message: "graphify: Knowledge graph exists. Read GRAPH_REPORT.md for god nodes and community structure before searching raw files." This surfaces the graph summary automatically, allowing the assistant to navigate by structure rather than keyword matching. Other platforms (Codex, OpenCode, OpenClaw, Factory Droid) write rules to `AGENTS.md` in the project root as an always-on mechanism.

SOURCE: README.md lines 84-93 (accessed 2026-04-08)

**Watch mode** (`--watch`): Runs in a background terminal and automatically syncs the graph as the codebase changes. Code file saves trigger instant rebuild (AST only, no LLM cost). Doc/image changes notify the user to run `--update` for the LLM re-pass.

SOURCE: README.md line 145, 201 (accessed 2026-04-08)

**Git hooks**: `graphify hook install` adds post-commit and post-checkout hooks that rebuild the graph automatically after every commit and branch switch. If a rebuild fails, the hook exits with non-zero code so git surfaces the error instead of silently continuing. No background process required.

SOURCE: README.md line 154, 203 (accessed 2026-04-08)

**Extended output formats**:
- `--wiki` — generates Wikipedia-style markdown articles per community and god node, with a navigable `index.md`
- `--obsidian` / `--obsidian-dir <path>` — exports to Obsidian vault format for integration with personal knowledge management systems
- `--svg` — static SVG export of the graph topology
- `--graphml` — Gephi/yEd-compatible export
- `--neo4j` / `--neo4j-push` — generates or pushes Cypher statements to Neo4j for graph database integration
- `--mcp` — starts an MCP stdio server, enabling the graph to be consumed by other AI tools

SOURCE: README.md lines 146-151 (accessed 2026-04-08)

**Query interface**: `graphify query "question"`, `graphify path NODE1 NODE2`, and `graphify explain NODE` provide hop-by-hop traversal of the graph.json with optional `--dfs` (depth-first search for specific paths) and `--budget N` (cap at N tokens) flags. Queries run offline from graph.json without invoking Claude again.

SOURCE: README.md lines 139-144, 167-170 (accessed 2026-04-08)

**Incremental updates** (`--update`): Re-extracts only changed files, merges with existing graph, regenerates wiki if present. SHA256 cache ensures unchanged files are never re-processed.

SOURCE: README.md line 128 (accessed 2026-04-08)

## Technical Architecture

**Two-pass extraction pipeline** (`detect() → extract() → build_graph() → cluster() → analyze() → report() → export()`):

Pass 1 — Deterministic AST extraction (no LLM cost): tree-sitter parses code files, walks AST nodes, extracts classes/functions/imports with their source locations, builds a call graph by analyzing function bodies for explicit calls. All code extraction is syntax-based; no semantic inference occurs in this pass.

Pass 2 — Parallel semantic extraction: Claude subagents (or GPT-4 for Codex users) process docs, papers, and images in parallel batches (chunked 12-25 files per subagent). Each subagent extracts concepts, relationships, and design rationale from non-code sources, returning edges tagged `INFERRED` with confidence scores. Results are cached via SHA256 so re-runs only re-extract changed files.

SOURCE: README.md lines 40-41, ARCHITECTURE.md lines 6-9 (accessed 2026-04-08)

**Community detection**: Uses Leiden algorithm (graspologic library) by default for highest-quality community detection based on edge density. Falls back to Louvain (NetworkX built-in, available since 2.7) if graspologic is not installed. Fallback includes `max_level=10` and `threshold=1e-4` parameters to prevent indefinite hangs on large sparse graphs while preserving community quality.

SOURCE: README.md line 43, cluster.py lines 13-21 (accessed 2026-04-08)

**Clustering is topology-based**: The graph structure itself is the similarity signal. Semantic similarity edges extracted by Claude (marked `INFERRED`) are already in the graph, so they directly influence community detection. No separate embedding step or vector database required.

SOURCE: README.md line 43 (accessed 2026-04-08)

**Node deduplication across three layers**:
1. Within a file (AST): Each extractor tracks a `seen_ids` set; duplicate class/function definitions in the same source file are collapsed to the first occurrence.
2. Between files (graph build): NetworkX `G.add_node()` is idempotent; calling it twice with the same ID overwrites the attributes. AST results are added before semantic results, so semantic nodes (richer labels, cross-file context) overwrite AST nodes (precise source locations).
3. Semantic merge (skill-level): Before calling `build()`, the skill merges cached and new semantic results using an explicit `seen` set keyed on node ID, resolving duplicates across cache hits and new extractions before graph construction.

SOURCE: build.py lines 1-21, ARCHITECTURE.md (accessed 2026-04-08)

**Extraction output schema** (normalized across all extractors):
```json
{
  "nodes": [
    {"id": "unique_string", "label": "human name", "source_file": "path", "source_location": "L42"}
  ],
  "edges": [
    {"source": "id_a", "target": "id_b", "relation": "calls|imports|uses|...", "confidence": "EXTRACTED|INFERRED|AMBIGUOUS"}
  ]
}
```

SOURCE: ARCHITECTURE.md lines 32-44 (accessed 2026-04-08)

**Module structure** (7 core modules, 6 utility modules):
- `detect.py`: `collect_files(root)` — directory traversal with `.graphifyignore` support
- `extract.py`: `extract(path)` — dispatches to language-specific AST handlers; uses `LanguageConfig` dataclass to support 19 languages without code duplication
- `build.py`: `build_graph(extractions)` — merges multiple extraction dicts into NetworkX graph
- `cluster.py`: `cluster(G)` — runs community detection, adds `community` attribute to each node
- `analyze.py`: `analyze(G)` — computes god nodes (highest-degree nodes), surprising connections, suggested questions
- `report.py`: `render_report(G, analysis)` — generates GRAPH_REPORT.md markdown
- `export.py`: `export(G, out_dir, ...)` — writes graph.json, graph.html, graph.svg, graph.graphml
- Utilities: `ingest.py` (fetch URLs), `cache.py` (SHA256-keyed semantic cache), `validate.py` (extraction schema validation), `security.py` (URL validation, size caps, HTML escaping), `serve.py` (MCP stdio server), `watch.py` (file monitoring), `wiki.py` (Wikipedia-style exports), `benchmark.py` (token reduction measurement)

SOURCE: ARCHITECTURE.md lines 13-30 (accessed 2026-04-08)

**Language support via LanguageConfig**: A single `_extract_generic()` function accepts a `LanguageConfig` dataclass that specifies tree-sitter module name, AST node type filters for classes/functions/imports/calls, field names for name extraction and body detection, and optional custom import handlers. This refactoring reduced `extract.py` from 2527 lines to 1588 lines while maintaining support for all 19 languages.

SOURCE: extract.py lines 21-60, CHANGELOG.md line 43 (accessed 2026-04-08)

**Visualization**: Custom vis.js HTML renderer (replaces pyvis as of v0.1.4). Nodes sized by degree (high-degree nodes appear larger). Click-to-inspect panel shows node details and clickable neighbors. Search box enables full-text search of node labels. Community filter allows hiding all but selected community. Physics engine clusters nodes spatially.

SOURCE: README.md line 221, CHANGELOG.md line 86 (accessed 2026-04-08)

## Installation & Usage

**PyPI installation**:
```bash
pip install graphifyy && graphify install
```

Note: The PyPI package is named `graphifyy` (temporary) while the `graphify` name is being reclaimed. The CLI command and skill command remain `graphify`.

SOURCE: README.md lines 52-55 (accessed 2026-04-08)

**Basic usage**:
```bash
/graphify .                           # run on current directory (skill command)
/graphify ./raw                       # run on specific folder
/graphify ./raw --mode deep           # aggressive INFERRED edge extraction
/graphify ./raw --update              # re-extract changed files, merge into existing graph
/graphify ./raw --cluster-only        # rerun clustering without re-extraction
/graphify ./raw --no-viz              # skip HTML, produce report + JSON only
/graphify ./raw --watch               # auto-sync as files change
/graphify ./raw --wiki                # generate Wikipedia-style articles per community
/graphify ./raw --obsidian            # generate Obsidian vault
/graphify ./raw --obsidian-dir ~/vaults/myproject  # vault to custom directory
```

SOURCE: README.md lines 124-133 (accessed 2026-04-08)

**URL ingestion**:
```bash
/graphify add https://arxiv.org/abs/1706.03762  # fetch paper, save, update graph
/graphify add https://x.com/karpathy/status/... # fetch tweet
/graphify add https://... --author "Name"        # tag original author
/graphify add https://... --contributor "Name"  # tag who added it
```

SOURCE: README.md lines 134-137 (accessed 2026-04-08)

**Query commands** (offline, no LLM cost):
```bash
/graphify query "what connects attention to the optimizer?"
/graphify query "..." --dfs              # depth-first for specific path
/graphify query "..." --budget 1500      # cap at N tokens
/graphify path "DigestAuth" "Response"   # trace specific path
/graphify explain "SwinTransformer"      # explain single node
```

SOURCE: README.md lines 139-144 (accessed 2026-04-08)

**Git hooks** (platform-agnostic):
```bash
graphify hook install                  # post-commit, post-checkout hooks
graphify hook uninstall
graphify hook status
```

SOURCE: README.md lines 154-156 (accessed 2026-04-08)

**Always-on assistant integration** (platform-specific):
```bash
graphify claude install                # CLAUDE.md + PreToolUse hook (Claude Code)
graphify codex install                 # AGENTS.md (Codex)
graphify opencode install              # AGENTS.md (OpenCode)
graphify claw install                  # AGENTS.md (OpenClaw)
graphify droid install                 # AGENTS.md (Factory Droid)
```

SOURCE: README.md lines 159-164 (accessed 2026-04-08)

**Platform-specific requirements**:
- Claude Code (Linux/Mac): `graphify install`
- Claude Code (Windows): `graphify install` (auto-detected) or `graphify install --platform windows`
- Codex: `graphify install --platform codex` + `multi_agent = true` in `~/.codex/config.toml` for parallel extraction
- OpenCode: `graphify install --platform opencode`
- OpenClaw: `graphify install --platform claw` (sequential extraction; parallel support pending)
- Factory Droid: `graphify install --platform droid` (uses Task tool for parallel dispatch)

SOURCE: README.md lines 59-68 (accessed 2026-04-08)

## Relevance to Claude Code Development

**Knowledge graph as persistent skill context**: In Claude Code workflows, graphify solves the "large codebase orientation" problem. After running `/graphify` once, every subsequent query reads from `GRAPH_REPORT.md` and `graph.json` instead of grepping raw files. This reduces token consumption by 71.5x on large mixed corpora, enabling faster, cheaper interactions with the assistant.

The PreToolUse hook means Claude automatically reads the graph summary before searching files, making the assistant structure-aware without explicit prompting. For codebases larger than the context window, this enables effective navigation at scale.

**Multimodal understanding**: Claude Code's vision capabilities are leveraged for diagrams, screenshots, whiteboard photos, and images in non-English languages. A mixed corpus of code, architecture diagrams, research papers, and design photos all feed into the same graph, creating connections across modalities that single-domain analysis cannot.

**Agent-crawlable wiki**: The `--wiki` output produces an index.md that other agents or tools can navigate without parsing JSON. This enables secondary agents (document generators, automated architecture reviewers, test planners) to answer questions directly from the wiki without re-analyzing the source.

**Multi-platform skill**: By supporting Claude Code, Codex, OpenCode, OpenClaw, and Factory Droid simultaneously, graphify enables consistent knowledge graph workflows across different AI coding assistant platforms. A developer can switch platforms and re-use their existing graphs.

SOURCE: README.md lines 9, 13, 84-102, 146 (accessed 2026-04-08)

## Limitations and Caveats

**Extraction confidence is model-dependent**: `INFERRED` edges depend on Claude's (or GPT-4's) semantic understanding. Confidence scores (0.0-1.0) reflect model uncertainty, but do not guarantee accuracy. Hallucinations can produce plausible-sounding but incorrect edges, especially in domains the training data did not cover well.

**Large sparse graph instability**: Very large, sparsely connected graphs (thousands of nodes, few edges) can cause community detection to hang indefinitely if parameters are not tuned. v0.3.11 added `max_level=10` and `threshold=1e-4` to prevent hangs, but extremely sparse graphs may still produce unexpected community structures.

**Semantic cache does not expire**: The SHA256 cache in `graphify-out/cache/` only invalidates on file content change. If a project updates documentation without changing file contents (e.g., rearranging sections), the cached extraction will not be updated. Manual cache deletion is required to force re-extraction.

**Clustering is deterministic but globally sensitive**: Community detection results depend on the complete graph topology. Adding a single new file with new relationships can shift community assignments for existing nodes, making community IDs unstable across incremental updates. Within a single run, community assignments are stable (seeded with `seed=42`).

**No built-in knowledge graph versioning**: `graph.json` is overwritten on every run. To preserve historical snapshots, users must manually copy `graphify-out/` to dated directories or commit the output to git.

**Performance on binary files**: Attempting to extract from binary-like text files (minified JavaScript, compiled bytecode representations) can cause tree-sitter to produce malformed ASTs or timeouts. `.graphifyignore` is required to exclude these.

**LLM cost for semantic pass**: The second pass (semantic extraction) invokes the underlying model API for every doc, paper, and image file. For large corpora, this can be expensive. The `--no-viz` flag and the ability to run `--cluster-only` on an existing graph can reduce costs, but semantic pass is always charged by the API.

SOURCE: README.md lines 217-219 (accessed 2026-04-08) + inferred from code structure

## References

- README.md — Main documentation, usage guide, worked examples (accessed 2026-04-08)
- ARCHITECTURE.md — Module responsibilities, extraction schema, language support (accessed 2026-04-08)
- CHANGELOG.md — Version history from 0.1.3 to 0.3.11 (accessed 2026-04-08)
- pyproject.toml — Package metadata, version 0.3.11, dependencies (accessed 2026-04-08)
- LICENSE — MIT license (accessed 2026-04-08)
- Source code: `graphify/extract.py`, `graphify/build.py`, `graphify/cluster.py` — module implementations (accessed 2026-04-08)

## Freshness Tracking

| Section | Confidence | Notes |
|---------|-----------|-------|
| Identity/Metadata | high | Version 0.3.11 extracted directly from pyproject.toml, release date from CHANGELOG |
| Overview | high | Direct quotes from README.md |
| Problem Addressed | high | Stated in README with 71.5x metric sourced from worked examples |
| Key Statistics | high | Version, language count, token reduction from primary sources; Python requirement from pyproject.toml |
| Key Features | high | All features extracted verbatim from README.md lines 120-202 |
| Technical Architecture | high | Pipeline diagram, module table, extraction schema from ARCHITECTURE.md; cluster.py implementation reviewed |
| Installation & Usage | high | All commands extracted verbatim from README.md usage sections |
| Relevance to Claude Code | high | Derived from README architecture, integration, and feature sections |
| Limitations | medium | Most caveats inferred from feature limitations documented in README and ARCHITECTURE (caching, clustering sensitivity); some inferred from code structure |

**Next review**: 2026-07-08 (3 months from access date)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Microsoft GraphRAG](../context-management/microsoft-graphrag.md) | context-management | knowledge graph extraction and community detection for semantic relationship discovery |
| [Samuraizer](../ai-research-tools/samuraizer.md) | ai-research-tools | semantic knowledge base with D3.js graph visualization and cross-document relationship mapping |
| [Living Architecture](../documentation-tools/living-architecture.md) | documentation-tools | extracts operational flow architecture from code; shared AST-to-visualization pipeline |
| [Anthropic Agent Skills Repository](./anthropics-skills.md) | skill-generation-tools | official skill specification and multimodal capabilities for autonomous code understanding |
| [SkillKit](./skillkit.md) | skill-generation-tools | universal package manager translating skills across 32 agents; shared architecture for multi-platform deployment |
| [Claude Code Skills Library (alirezarezvani)](./claude-code-skills-alirezarezvani.md) | skill-generation-tools | production skill ecosystem; 9-phase quality gates and stdlib-only Python validation matching graphify's multimodal approach |
| [Rope](../code-auditing/rope.md) | code-auditing | AST-based Python refactoring library; shared tree-sitter foundation and scope-aware symbol resolution patterns |
