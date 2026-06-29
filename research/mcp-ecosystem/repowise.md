# repowise — Codebase Intelligence Layer for AI Agents

**Research Date**: 2026-06-18
**Source URL**: <https://github.com/repowise-dev/repowise>
**Version at Research**: 0.20.0
**License**: AGPL-3.0-only

---

## Overview

repowise is a Python-based codebase intelligence platform that indexes source code into five composable intelligence layers — dependency graph, git history, auto-generated documentation, architectural decisions, and code health metrics — then exposes them to Claude Code, Cursor, and other MCP-compatible agents through nine task-shaped tools. The system operates entirely locally with zero LLM dependencies for core analysis, using tree-sitter for AST parsing and git for behavioral signals.

**Headline claim**: "The codebase intelligence layer for the AI era. Context your AI agent can use, and the health, risk, and ownership signals your team can trust." Agents reading through repowise's MCP tools achieve up to **−96% tokens to load context, −89% file reads, −70% fewer tool calls** compared to raw exploration (verified on Flask and scikit-learn benchmarks).

---

## Problem Addressed

AI coding agents currently rely on raw file exploration — grepping for symbols, reading candidate files, re-reading as context expands. This is expensive both in tokens and latency. Additionally, teams shipping AI-generated code lack trust signals: they cannot see how much of the codebase an AI wrote, whether that code is maintainable, or which files carry hidden technical risk.

repowise addresses two customer problems:

1. **Agent efficiency** — Do the codebase exploration work once, offline, so the agent skips it on every query.
2. **Human oversight** — Provide defect-calibrated code-health scoring, change-risk assessment, and agent provenance so humans trust what ships.

---

## Key Statistics

- **Languages supported**: 15 total; 9 at "Full tier" with complete biomarker support (Python, TypeScript, JavaScript, Java, Kotlin, Go, Rust, C++, C#); 6 at "Good tier" (C, Ruby, Swift, Scala, PHP); remainder Git-blame only.
- **Biomarkers**: 25 deterministic indicators of code quality (McCabe complexity, LCOM4 cohesion, brain methods, god classes, clone detection, untested hotspots, churn volatility, ownership dispersion, co-change scatter, prior-defect history, and more).
- **Initial index time**: Minutes on 3,000-file repos (zero LLM calls for graph/git/health layers; docs layer can run in background).
- **Update time**: <30 seconds per commit (incremental, touches only changed files).
- **MCP tools**: Nine queryable interfaces (`get_overview`, `get_answer`, `get_context`, `get_symbol`, `search_codebase`, `get_risk`, `get_why`, `get_dead_code`, `get_health`).
- **Code health AUC**: 0.731 (defect prediction) across 21 open-source repositories; **2.3× more defects surfaced under a fixed review budget** than leading commercial code-health tool (paired statistical test, p = 0.003).
- **Graph size**: Tested on 2,000+ node repositories; supports multi-repo workspaces with cross-repo co-change and contract analysis.

---

## Key Features

### 1. Five Composable Intelligence Layers

Each layer is built once, kept in sync on every commit, and queryable independently or in combination.

**Graph Intelligence**
- Tree-sitter AST parsing across 15 languages
- Two-tier dependency graph (file and symbol nodes)
- Three-tier call resolver with confidence scoring (handles import aliases, barrel re-exports, namespace imports)
- Heritage extraction (extends, implements, trait impls, derive macros, mixins, extension conformance)
- Leiden community detection to identify logical modules even when directory structure doesn't reflect them
- Graph metrics: PageRank, betweenness centrality, SCC analysis, execution-flow tracing
- Framework-aware edges (Django, FastAPI, Flask, ASP.NET, Spring Boot, Express/NestJS, Gin/Echo/Chi, Axum/Actix, Rails, Laravel, and more)

**Git Intelligence**
- Hotspots: files in top 25% of both churn AND complexity (empirically where bugs live)
- Ownership aggregation from git blame into percentages per author
- Co-change pairs: files changing together without import links (hidden coupling invisible to AST)
- Bus factor: files owned >80% by single author, flagged as knowledge risk
- Significant commits: last 10 meaningful commits per file (filtered: no merges, bumps, lint), feed generation prompts
- Contributor profiles: per-author pages with owned modules, top files, co-authors, commit category distribution, silo analysis
- Module health: composite 0–100 score per top-level module from silo penalty, hotspot density, dead-code %, churn, doc coverage, bus factor
- Reviewer suggestions: ranked by direct authorship (×1.0), co-change (×0.5), recency (×0.4)

**Documentation Intelligence**
- LLM-generated wiki for every module and file, rebuilt incrementally on every commit
- Coverage tracking: what's documented and what isn't
- Freshness scoring: confidence scores show how current each page is relative to underlying code
- Semantic search via RAG: hybrid retrieval (full-text + vector via Reciprocal Rank Fusion) with PageRank bias and 1-hop graph expansion
- Typical single-commit update touches 3–10 pages, completes in under 30 seconds

**Decision Intelligence** (unique to repowise)
- Architectural decisions mined from eight sources: ADR files (Nygard/MADR), CHANGELOG, PR/squash bodies, inline markers (`# WHY:`, `# DECISION:`, `# TRADEOFF:`), git archaeology, README, code comments, LLM doc pass
- Evidence-backed: each rationale traces to verbatim source span
- Anti-hallucination: decisions stamped as verified/fuzzy/unverified; corroborating sources raise confidence
- Decision graph: typed edges (supersedes, refines, relates_to, conflicts_with)
- Staleness tracking and conflict detection as code evolves
- Surfaces everywhere: `get_why()` for full archaeology, governing decisions in `get_context()`, `governance_risk` flag in `get_risk()` PR review, Key Decisions in `get_overview()`, warnings for ungoverned hotspots and stale/contradictory decisions in code-health

**Code Health Intelligence** (defect-validated)
- 1–10 score per file from 25 deterministic biomarkers
- Zero LLM calls, zero cloud requirement, pure Python over tree-sitter + git
- Biomarker weights calibrated offline against real defect corpus via L2-logistic regression (not hand-tuned)
- Finishes in under 30 seconds on 3,000-file repos
- Three health bands: Healthy (≥8.0), Warning (4.0–8.0), Alert (<4.0)
- Alert files carry ~17× the per-file defect rate of Healthy files (empirically defensible cutoffs)
- Supports coverage ingestion (LCOV, Cobertura, Clover) to light up untested-hotspot biomarkers
- Rolling snapshot history for trend tracking and declining/predicted-decline alerts
- Deterministic refactoring suggestions ranked by impact/effort
- Per-file overrides via `.repowise/health-rules.json`

### 2. Nine MCP Tools

All tasks-shaped: pass multiple targets in one call, get complete context back.

| Tool | Purpose | Key capability |
|---|---|---|
| `get_overview()` | Architecture summary | First call on unfamiliar codebase; returns module map, entry points, hotspots, knowledge silos |
| `get_answer(question)` | One-call RAG Q&A | Collapses search → read → reason into one round-trip with confidence labels |
| `get_context(targets, include?)` | Rich context for files/modules/symbols | Triage cards with docs, signatures, hotspot bits, governing decisions, `symbol_id`s; batch many targets |
| `get_symbol("path::Name")` | Raw source bytes for one symbol | Exact line bounds, cheaper than Read + offset math |
| `search_codebase(query, kind?)` | Semantic search over wiki | Hybrid retrieval, filterable by kind (implementation/test/config/doc) |
| `get_risk(targets, changed_files?)` | Hotspot scores, dependents, co-change | PR mode → directive block (will_break, missing_cochanges, missing_tests, governance_risk) |
| `get_why(query?, targets?)` | Architectural decision lineage | Supersession chains, git archaeology fallback |
| `get_dead_code(...)` | Unreachable code by confidence tier | Cleanup-impact estimates; cross-repo consumer detection in workspace mode |
| `get_health(targets?, include?)` | 25-biomarker scores | Dashboard mode (KPIs + lowest files + findings) or targeted (per-file); include coverage, refactoring, trend |

Every response carries `_meta` envelope with `index_age_days`, `indexed_commit`, `stale_warning` (fires when indexed HEAD diverges from live `.git/HEAD`). Token-budgeted responses use reversible truncation: dropped content stored in omission store, marked with `[repowise#<ref>]` in response, recoverable via `repowise expand <ref>` (CLI) or `get_symbol("repowise#<ref>", query?)` (MCP).

### 3. Change Risk & Agent Provenance

- **Change risk**: score any commit or `base..HEAD` range 0–10 for defect risk from diff shape (Kamei-style just-in-time metrics), with PR-mode directives
- **Agent provenance**: attribute commits to AI agents straight from git history, showing code volume and health of AI-generated code

Both are zero-LLM and reproducible.

### 4. Local Dashboard

`repowise serve` starts full web UI alongside MCP server.

Views: Chat (NL Q&A) · Docs (wiki with Mermaid + graph sidebar) · Graph (interactive, 2,000+ nodes, community coloring, path finder) · C4 Architecture (Context → Containers → Components) · Risk (hotspots, ownership heatmap, module health, dead code, blast radius) · Contributors (per-author profiles) · Decisions (evidence drawer, evolution timeline, decision-graph) · Health (biomarker scores, coverage, trends) · Security (local pattern scan) · Costs (tokens/dollars saved) · Workspace (cross-repo contracts & co-changes).

### 5. Multi-Repo Workspace Support

- `repowise init .` scans parent directory for git repos, indexes each, runs cross-repo analysis
- Workspace dashboard with per-repo pages
- Cross-repo co-change detection and contract analysis
- Federated MCP endpoint for multiple repos

### 6. Command Distillation

`repowise distill <cmd>` compresses shell command output before agent reads it — errors-first, exit code preserved, every omission reversible via `[repowise#<ref>]` marker.

Example savings:
- `pytest -q` (11 failures): 3,374 → 1,317 tokens (61% saved)
- `git log -50`: 3,064 → 331 tokens (89% saved)
- `git diff` (30 commits): 62,833 → 8,635 tokens (86% saved)

Small outputs pass through untouched. Opt-in Claude Code hook rewrites noisy commands automatically. `repowise saved` tracks tokens and dollars saved.

---

## Technical Architecture

### Component Structure

**Core Analysis Pipeline**
- tree-sitter parser (AST → symbol nodes)
- Import resolver (3-tier: direct, alias, namespace)
- Call graph builder with confidence scoring
- Git blame aggregator
- Community detector (Leiden algorithm)
- Health biomarker calculator

**Data Persistence**
- NetworkX graph (serialized)
- LanceDB embeddings (for semantic search via RAG)
- Git history index
- Health snapshots (rolling 50-row history)
- Generated wiki pages (markdown)
- Decision records (structured JSON)

**Query Layer (MCP Server)**
- 9 tools with task-oriented design
- Hybrid retrieval (FTS + vector via RRF)
- PageRank bias and 1-hop graph expansion
- Token-budgeted responses with reversible truncation
- Omission store for truncated content
- Cross-repo contract analysis (workspace mode)

**CLI Interface**
- `repowise init` — full index (configurable depth)
- `repowise update` — incremental (<30s)
- `repowise serve` — MCP server + local dashboard
- `repowise query "<q>"` — terminal Q&A
- `repowise health` — KPI report
- `repowise risk` — change-risk scoring
- `repowise dead-code` — unreachable-code analysis
- `repowise decision` — decision capture and health
- `repowise distill` — command output compression
- `repowise doctor` — setup validation

**Framework-Aware Module Detection**
Django, FastAPI, Flask, ASP.NET, Spring Boot, Express/NestJS, Gin/Echo/Chi, Axum/Actix, Rails, Laravel — routes → handlers edges automatically extracted.

### Language Coverage Decision Tree

| Tier | Languages | Coverage |
|------|-----------|----------|
| Full | Python, TS/JS, Java, Kotlin, Go, Rust, C++, C# | AST, imports, bindings, call resolution, heritage, docstrings, biomarkers, multi-project resolvers, framework edges |
| Good | C, Ruby, Swift, Scala, PHP | AST, imports, bindings, call resolution, heritage, docstrings, workspace resolvers, framework edges (Rails/Laravel/TYPO3) |
| Config/Data | OpenAPI, Protobuf, GraphQL, Dockerfile, Makefile, YAML, JSON, TOML, SQL, Terraform, Markdown, Shell | Included in file tree, special handlers extract endpoints/targets |
| Git-blame only | 30+ languages (Objective-C, Elixir, Erlang, Dart, Zig, Julia, etc.) | Tracked in git history (blame, hotspots, co-change); no AST parsing yet |

Adding a language: **one `.scm` query file and one config entry** — no core parser changes.

---

## Installation & Usage

### Single Repository

```bash
pip install repowise          # or: uv tool install repowise
cd your-project
repowise init                 # builds all five layers (one-time)
repowise serve                # starts MCP server + local dashboard
```

### Multi-Repo Workspace

```bash
cd my-workspace/              # parent dir with backend/, frontend/, shared-libs/
repowise init .               # scans for repos, indexes each, cross-repo analysis
repowise serve                # workspace dashboard + per-repo pages
```

### Claude Code Integration

Option A: Plugin (one-command setup)

```
/plugin marketplace add repowise-dev/repowise
/plugin install repowise@repowise
```

Then use `/repowise:init`, `/repowise:health`, `/repowise:risk`, etc.

Option B: Manual MCP registration

```json
{
  "mcpServers": {
    "repowise": { "command": "repowise", "args": ["mcp", "/path/to/your/project"] }
  }
}
```

Option C: Codex editor

```bash
repowise init --codex         # writes .codex/config.toml, hooks.json, AGENTS.md
```

`repowise init` also:
- Registers MCP server (auto-detects Claude Code, Codex, or manual `.mcp.json`)
- Installs PostToolUse hook in `~/.claude/settings.json`
- Generates `.mcp.json` at project root
- Offers post-commit hook for auto-sync

### Benchmark Query Example

**Goal**: Add rate limiting to all API endpoints (realistic SWE-QA task)

**repowise approach** (5 tool calls):
1. `get_overview()` — understand architecture
2. `search_codebase("API endpoint definitions")` — find patterns
3. `get_context(["src/api/routes.ts"], include=["callers"])` — endpoint definitions + callers
4. `get_risk(["src/api/middleware.ts"], changed_files=[...])` — PR-mode risk assessment
5. `get_why("Why is auth stateless?")` — decision context

**Raw exploration** (~30 greps + reads): grep for routes, read files, ask agent to map endpoints, manually trace dependencies.

---

## Relevance to Claude Code Development

### Direct Integration Points

1. **MCP Server Delivery** — repowise is an MCP-native tool expressly built for Claude Code and other MCP-compatible agents. The `/plugin marketplace` integration and PostToolUse hooks are Claude Code-specific.

2. **Token Efficiency** — Agents using repowise's MCP tools achieve documented **−96% tokens for context loading** compared to raw exploration. For long-running multi-step investigations, this compounds to **−41% context re-read across whole session**.

3. **Agent Provenance** — As Claude Code agents generate more code, teams need trust signals. repowise's agent-provenance feature (attribute commits to AI agents, score their code health) directly addresses this.

4. **Change Risk Before Merge** — The `get_risk()` tool with PR-mode directives (`will_break`, `missing_cochanges`, `missing_tests`, `governance_risk`) helps Claude Code instances and human reviewers assess defect risk before merging.

5. **Architectural Decision Context** — The Decision Intelligence layer (`get_why()`) surfaces the "why" behind structural choices, enabling Claude Code to understand design constraints before refactoring.

6. **Health-Guided Refactoring** — The 25-biomarker health scores (calibrated against real defects, validated via 0.731 AUC) let Claude Code prioritize refactoring targets by impact/effort, not arbitrary heuristics.

### Extensibility

The codebase is open-source (AGPL-3.0) and plugin-extensible:
- New languages can be added with one `.scm` query file + one config entry
- Biomarker weights can be retrained offline against custom defect corpuses
- The local dashboard can be extended with custom views
- The MCP tool set is fixed at nine, but each accepts rich parameter payloads and batch queries

---

## Limitations and Caveats

1. **AGPL-3.0 license** — Free for individual developers, teams, and internal company use. Commercial embedding or proprietary distribution requires a commercial license. No implicit IP indemnification.

2. **LLM dependencies for docs layer only** — Graph, git, and health layers are zero-LLM and fully deterministic. Documentation and decision intelligence require LLM API calls (Anthropic, OpenAI, Ollama). Both are optional; `repowise init --index-only` skips them.

3. **First-time indexing cost** — Initial graph/git/health build takes minutes on 3,000-file repos (zero-LLM, fast). Docs layer can run in background. After that, incremental updates are <30 seconds.

4. **Language tier variation** — Nine languages at Full tier (all biomarkers). Six at Good tier (no health scoring). Remainder Git-blame only. Code-health biomarkers depend on Full-tier language support.

5. **Deterministic biomarker weights are corpus-trained** — Weights are fixed constants learned offline from a defect corpus. They cannot be dynamically tuned per-repo at runtime. Per-file overrides are supported via `.repowise/health-rules.json`.

6. **No built-in secrets scanning** — Local pattern scan view exists in dashboard, but not integrated into health scoring or risk assessment. Enterprises using hosted version get CVE-aware security layer.

7. **Multi-repo workspace requires shared parent directory** — Workspace mode scans all git repos under a parent; no arbitrary cross-directory support (yet).

8. **Team/enterprise features limited to commercial tier** — Hosted repowise.dev, PR Bot (free GitHub App), SSO/SCIM/RBAC, cross-repo at scale, Slack/Jira/Confluence integrations, commercial support are on-prem or managed service only.

---

## References

- **Homepage**: <https://www.repowise.dev> (accessed 2026-06-18)
- **GitHub repository**: <https://github.com/repowise-dev/repowise> (accessed 2026-06-18)
- **Documentation site**: <https://docs.repowise.dev> (accessed 2026-06-18)
- **PyPI package**: <https://pypi.org/project/repowise/> (accessed 2026-06-18)
- **Benchmarks & methodology**: <https://github.com/repowise-dev/repowise-bench> (accessed 2026-06-18)
- **Code health defect prediction report**: <https://github.com/repowise-dev/repowise-bench/blob/master/health-defect/BENCHMARK_REPORT.md> (accessed 2026-06-18)
- **Agent efficiency reports**: Flask v0.12.3 (48 files, 2,391 vs 64,039 tokens), Flask v3.0, scikit-learn v0.24.8 (accessed 2026-06-18)
- **Discord community**: <https://discord.gg/cQVpuDB6rh> (accessed 2026-06-18)
- **License**: <https://www.gnu.org/licenses/agpl-3.0> (accessed 2026-06-18, AGPL-3.0-only)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [narsil-mcp.md](./narsil-mcp.md) | mcp-ecosystem | complementary code intelligence MCP: Rust-based with 90 tools for call graphs and security scanning |
| [gitnexus.md](./gitnexus.md) | mcp-ecosystem | graph-based code intelligence alternative: 7-tool MCP with Cypher queries and precomputed clustering |
| [codegraphcontext.md](./codegraphcontext.md) | mcp-ecosystem | repository-to-graph competitor: 20+ MCP tools with KùzuDB graphs and 14-language Tree-Sitter support |
| [cocoindex-code.md](./cocoindex-code.md) | mcp-ecosystem | semantic code search complement: embedded MCP for AST analysis and embeddings with ~70% token savings |
| [kythe.md](../developer-tools/kythe.md) | developer-tools | language-agnostic code intelligence platform: Google's research foundation for symbol resolution and cross-reference analysis |
| [grepai.md](../developer-tools/grepai.md) | developer-tools | semantic code search and call graph analysis: AI-native search over code with graph visualization |
| [docs-mcp-server.md](./docs-mcp-server.md) | mcp-ecosystem | documentation indexing complement: local semantic search alternative for RAG and knowledge bases |
| [oh-my-opencode.md](../research-agent-patterns/oh-my-opencode.md) | research-agent-patterns | production-scale MCP orchestration: 37.5K-star multi-agent harness consuming repowise-like code intelligence |

---

## Freshness Tracking

**Last Verified**: 2026-06-18
**Version at Verification**: 0.20.0
**Index age at verification**: 0 days (at HEAD commit 69d5a90, v0.20.0)

### Confidence Summary

| Section | Confidence | Notes |
|---------|-----------|-------|
| **Identity & Metadata** | high | README, pyproject.toml, git history, homepage all corroborate version, license, language support |
| **Five Intelligence Layers** | high | Detailed in INTELLIGENCE_LAYERS.md, fully verified across docs. Feature descriptions extracted verbatim. |
| **Code Health Biomarkers** | high | CODE_HEALTH.md provides per-biomarker definitions, calibration methodology, defect-prediction validation (AUC 0.731 across 21 repos, reproducible benchmark). |
| **Nine MCP Tools** | high | MCP_TOOLS.md specifies all tool signatures, parameters, return types, and use cases. Fully documented API surface. |
| **Benchmarks** | high | Reproducible benchmark reports on public repos (Flask, scikit-learn) available at repowise-bench; token/file/tool call savings verified. |
| **Technical Architecture** | medium | Inferred from code structure, documentation, CLI reference. Core components identified from file structure and tool flow. |
| **Limitations** | medium | License verified (AGPL-3.0). Feature gaps inferred from docs absence, not from explicit "not supported" statements. Enterprise features confirmed as commercial-tier-only. |
| **Commercial Licensing** | high | docs/COMMERCIAL.md and website cross-reference; no AGPL obligation for proprietary embeddings, SSO/SCIM/RBAC, on-prem. |

**Next Review Recommended**: 2026-09-18

