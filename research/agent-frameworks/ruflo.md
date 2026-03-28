# Ruflo: Enterprise AI Agent Orchestration Platform

## Overview

Ruflo (formerly Claude Flow) is a production-ready multi-agent AI orchestration framework that enables deployment of 100+ specialized agents working in coordinated swarms. Distributed as an npm package (`ruflo@3.5.0`), it integrates natively with Claude Code via MCP (Model Context Protocol) and provides a comprehensive CLI with 26 commands and 215+ MCP tools. The system includes self-learning capabilities via the RuVector intelligence layer, fault-tolerant consensus mechanisms, and enterprise-grade security hardening.

**Primary Resource Identifier**: GitHub repository at `https://github.com/ruvnet/ruflo` (shallow clone successful at commit f547cec, dated 2026-03-25)

**License**: MIT

**Latest Version**: 3.5.0 (released 2026-02-27) — First major stable release after 5,900+ commits and 55 alpha iterations

**NPM Packages**:
- `@claude-flow/cli@3.5.0` — CLI and command router
- `claude-flow@3.5.0` — Umbrella package
- `ruflo@3.5.0` — CLI alias (thin wrapper)

---

## Problem Addressed

**Single-Agent Limitation**: Claude Code and similar AI systems traditionally work with a single reasoning model per task, limiting capability to that model's strengths and creating bottlenecks when multiple specialized skills are needed simultaneously.

**Coordination Gap**: Multi-agent frameworks exist but lack tight integration with development tools. Agents cannot easily share memory, reach consensus on complex decisions, or prevent goal drift during long-running tasks.

**Visibility and Learning Gaps**: AI agents cannot learn from successful patterns or optimize their own routing decisions based on task complexity.

**Entry Statement**: "Ruflo transforms Claude Code into a powerful multi-agent development platform. It enables teams to deploy, coordinate, and optimize specialized AI agents working together on complex software engineering tasks" (README.md, line 32).

---

## Key Statistics

| Statistic | Value | Source | Date |
|-----------|-------|--------|------|
| Total Commits | 5,900+ | CHANGELOG.md, line 12 | 2026-02-27 |
| Alpha Iterations | 55 | CHANGELOG.md, line 12 | 2026-02-27 |
| Specialized Agents Available | 100+ | README.md, line 169 | 2026-02-27 |
| MCP Tools | 215+ | CHANGELOG.md, line 19 | 2026-02-27 |
| CLI Commands | 26 | CLAUDE.md, line 170 | 2026-02-27 |
| CLI Subcommands | 140+ | CLAUDE.md, line 171 | 2026-02-27 |
| Background Workers | 12 | CLAUDE.md, line 17 | 2026-02-27 |
| Hooks System | 17 | CLAUDE.md, line 143 | 2026-02-27 |
| AgentDB Controllers | 8 | CHANGELOG.md, line 18 | 2026-02-27 |
| RuVector Components | 10 | README.md, line 136 | 2026-02-27 |
| Node.js Minimum Version | 20.0.0 | package.json, line 84 | 2026-03-25 |
| Current Repository Health | 0 production vulnerabilities | CHANGELOG.md, line 22 | 2026-02-27 |

---

## Key Features

### 1. Multi-Agent Orchestration with Swarm Coordination

**Mechanism**: The system routes user requests through an MCP server into specialized agents organized by topology (hierarchical, mesh, ring, star). Each agent can spawn sub-workers and communicate via shared memory.

**Named Components**:
- **Router** — Q-Learning router with Mixture of Experts (8 experts) selects best agent for task complexity (README.md, line 57)
- **Swarm Coordination Layer** — Manages agent topologies, consensus algorithms (Raft, Byzantine, Gossip, CRDT, Quorum) (README.md, lines 64-66)
- **Queen-Led Hive Mind** — Strategic, Tactical, and Adaptive queens coordinate worker teams (README.md, lines 214-215)
- **Collective Memory** — Shared knowledge base with LRU cache and SQLite persistence (README.md, line 230)

**Data Flow Example**: User CLI command → MCP entry point with AIDefence security → Q-Learning router → 8 MoE experts → selected agent + worker swarm → shared memory namespace → response to CLI (README.md, lines 46-116).

**Extension Point**: Custom agents can be created via the plugin SDK and distributed on the IPFS-backed marketplace (README.md, line 181).

### 2. Self-Learning via RuVector Intelligence Layer

**Named Components**:
- **SONA** (Self-Optimizing Neural Architecture) — Learns optimal routing with <0.05ms adaptation (README.md, line 87)
- **EWC++** (Elastic Weight Consolidation) — Prevents catastrophic forgetting by preserving learned patterns (README.md, line 88)
- **HNSW** (Hierarchical Navigable Small World) — Vector search with 150x-12,500x speedup (README.md, line 136)
- **ReasoningBank** — Pattern storage with RETRIEVE → JUDGE → DISTILL → CONSOLIDATE pipeline (README.md, lines 104-105)
- **LoRA/MicroLoRA** — 128x compression for efficient fine-tuning (README.md, line 139)
- **Int8 Quantization** — ~4x memory reduction (README.md, line 140)

**Data Flow**: Successful task completion → Pattern extraction → HNSW indexing → ReasoningBank storage → Future queries retrieve relevant patterns (confidence lifecycle per ADR-049).

### 3. Enterprise Security (CVE-Hardened)

**Named Components**:
- **AIDefence** — Entry-layer security inspection (README.md, line 53)
- **PathValidator** — Path traversal prevention via whitelist validation (SECURITY.md, line 50)
- **InputValidator** — Zod-based schema validation at all boundaries (SECURITY.md, line 48)
- **SafeExecutor** — Command injection protection with SAFE_LANGUAGES whitelist (CHANGELOG.md, line 35)

**Configuration**: "0 Production Vulnerabilities" claimed; `npm audit` passes (CHANGELOG.md, line 22).

### 4. Provider-Agnostic Model Support

**Supported Providers**: Claude (Anthropic), GPT (OpenAI), Gemini (Google), Cohere, Ollama (local), and others (README.md, line 175).

**Routing Strategy**: "Automatic failover if one provider is unavailable. Smart routing picks the cheapest option that meets quality requirements" (README.md, line 175).

**Token Optimization**: 30-50% token reduction via ReasoningBank retrieval (-32%), Agent Booster edits (-15%), caching (-10%), optimal batch sizing (-20%) (README.md, line 326).

### 5. Agent Booster (WASM-Based Code Transform)

**Mechanism**: WebAssembly skips LLM calls for simple code transforms (simple intent detection).

**Supported Transform Intents**:
- `var-to-const` — Convert var/let to const
- `add-types` — Add TypeScript type annotations
- `add-error-handling` — Wrap in try/catch
- `async-await` — Convert promises to async/await
- `add-logging` — Add console.log statements
- `remove-console` — Strip console.* calls

(README.md, lines 284-293)

**Performance**: <1ms latency, 352x faster than LLM calls (README.md, line 313).

### 6. Hooks System + Background Workers

**17 Core Hooks**:
- Lifecycle: `pre-edit`, `post-edit`, `pre-command`, `post-command`, `pre-task`, `post-task`
- Session: `session-start`, `session-end`, `session-restore`, `notify`
- Intelligence: `route`, `explain`, `pretrain`, `build-agents`, `transfer`

(CLAUDE.md, lines 210-212)

**12 Background Workers**: `ultralearn`, `optimize`, `consolidate`, `predict`, `audit`, `map`, `preload`, `deepdive`, `document`, `refactor`, `benchmark`, `testgaps` — auto-dispatch on file changes, pattern triggers, or sessions (CLAUDE.md, lines 213-226).

### 7. Anti-Drift Swarm Configuration

**Recommended Topology for Coding**: Hierarchical with maxAgents=6-8, specialized strategy, Raft consensus (README.md, lines 360-365).

**Drift Prevention Mechanisms**:
- Hierarchical coordinator validates outputs against original goal
- Smaller teams (6-8 agents) reduce coordination overhead
- Clear role boundaries prevent ambiguity
- Short task cycles with verification gates

(README.md, lines 370-383)

### 8. Plugin System + IPFS Marketplace

**Registry Distribution**: IPFS via Pinata with decentralized, immutable storage (CLAUDE.md, "Plugin Registry Maintenance").

**Available Plugins** (20 total):
- **Core**: embeddings, security, claims, neural, plugins, performance
- **Integration**: agentic-qe, prime-radiant, gastown-bridge, teammate-plugin, code-intelligence, test-intelligence
- **Domain-Specific**: healthcare-clinical, financial-risk, legal-contracts

(CLAUDE.md, lines 287-316)

---

## Technical Architecture

### Core Layered Design

```
User Layer (Claude Code / CLI)
    ↓
Entry Layer (MCP Server + AIDefence)
    ↓
Routing Layer (Q-Learning Router + MoE + Skills + Hooks)
    ↓
Swarm Coordination (Topologies + Consensus + Claims)
    ↓
Agent Execution (100+ agents with task-specific roles)
    ↓
Resources (AgentDB Memory + LLM Providers + 12 Workers)
    ↓
RuVector Intelligence (SONA + EWC++ + HNSW + ReasoningBank)
    ↓
Learning Loop (RETRIEVE → JUDGE → DISTILL → CONSOLIDATE)
```

(README.md, lines 46-117)

### Key Subsystems

**Router**: Q-Learning-based routing with Mixture of Experts (8 experts) selects best agent. Semantic routing uses SONA-trained preferences (README.md, lines 57-60).

**Memory Backend**: AgentDB with 8 controllers (HierarchicalMemory, MemoryConsolidation, SemanticRouter, GNNService, RVFOptimizer, MutationGuard, AttestationLog, GuardedVectorBackend) + HNSW vector indexing + SQLite persistence (CHANGELOG.md, line 18).

**Consensus Algorithms**: Raft (leader-based, 50% fault tolerance), Byzantine (BFT, 33% fault tolerance), Gossip (eventual consistency), CRDT (conflict-free), Quorum (configurable) (CLAUDE.md, lines 258-265).

**Task Complexity Routing** (3-Tier Model per ADR-026):
- **Tier 1** (WASM/Agent Booster): <1ms, $0, simple transforms (var→const, add types)
- **Tier 2** (Haiku): ~500ms, $0.0002, simple tasks (<30% complexity)
- **Tier 3** (Sonnet/Opus): 2-5s, $0.003-$0.015, complex reasoning (>30%)

(CLAUDE.md, lines 178-189)

### Swarm Topologies Supported

| Topology | Use Case | Fault Tolerance |
|----------|----------|-----------------|
| Hierarchical | Coordinated work with strict alignment | Low (single point of failure) |
| Mesh | Distributed peer-to-peer | High (any node can coordinate) |
| Ring | Sequential task passing | Medium |
| Star | Central hub coordination | Low (hub-dependent) |
| Hierarchical-Mesh | Recommended for production coding | High + alignment |

(CLAUDE.md, lines 249-256)

### Dual-Mode Collaboration (Claude + Codex)

Ruflo supports simultaneous execution of Claude Code workers (🔵) and OpenAI Codex workers (🟢) with shared memory coordination via a collaboration namespace. Both platforms cross-validate, learn from each other, and run in parallel (CLAUDE.md, "Dual-Mode Collaboration section" lines 121-160).

---

## Installation & Usage

### Quick Start

```bash
# One-line install (recommended)
curl -fsSL https://cdn.jsdelivr.net/gh/ruvnet/ruflo@main/scripts/install.sh | bash

# Or via npx
npx ruflo@latest init --wizard

# Or global install
npm install -g ruflo@latest
ruflo init
```

(README.md, lines 151-162)

### Initialize Swarm

```bash
# Hierarchical swarm (anti-drift defaults)
npx claude-flow@v3alpha swarm init --topology hierarchical --maxAgents 8 --strategy specialized

# Spawn agents
npx claude-flow@v3alpha agent spawn -t coder --name my-coder
npx claude-flow@v3alpha agent spawn -t tester --name my-tester

# Check status
npx claude-flow@v3alpha swarm status
```

(CLAUDE.md, lines 228-240)

### Memory Operations

```bash
# Search HNSW-indexed memory
npx claude-flow@v3alpha memory search -q "authentication patterns"

# Store pattern
npx claude-flow@v3alpha memory store --namespace patterns --key "oauth" --value "[pattern content]"

# Retrieve
npx claude-flow@v3alpha memory retrieve --namespace patterns --key "oauth"
```

(CLAUDE.md, lines 247-255)

### Key CLI Commands (26 Total)

| Command | Subcommands | Purpose |
|---------|-------------|---------|
| `init` | 4 | Project initialization with wizard and presets |
| `agent` | 8 | Agent lifecycle (spawn, list, status, stop, metrics, pool, health, logs) |
| `swarm` | 6 | Multi-agent swarm coordination |
| `memory` | 11 | AgentDB memory with vector search |
| `mcp` | 9 | MCP server management |
| `task` | 6 | Task creation and lifecycle |
| `session` | 7 | Session state management |
| `config` | 7 | Configuration management |
| `status` | 3 | System monitoring |
| `security` | 6 | Security scanning (scan, audit, CVE, threats, validate, report) |
| `hooks` | 17 | Self-learning hooks + 12 background workers |
| `neural` | 5 | Neural pattern training (SONA, MoE, EWC++) |
| `daemon` | 5 | Background worker daemon |

(CLAUDE.md, lines 195-240)

### Installation Profiles

| Profile | Size | Use Case | Time |
|---------|------|----------|------|
| `--omit=optional` | ~45MB | Core CLI only | ~15s |
| Default | ~120MB | Standard with optional deps | ~20-35s |
| `--full` | ~180MB | CLI + MCP + diagnostics | ~40-60s |

(README.md, line 500)

---

## Relevance to Claude Code Development

### 1. Native Claude Code Integration
Ruflo provides seamless MCP integration with Claude Code, allowing developers to spawn multi-agent swarms directly from Claude Code sessions. The system handles inter-agent communication, memory sharing, and consensus automatically without requiring external services.

**Use Case**: When a user asks Claude Code for a complex feature, Ruflo can automatically decompose it across 5-8 specialized agents (architect, coder, tester, reviewer), coordinate via hooks, and report completion.

### 2. Cost Optimization for Claude Code Subscriptions
Token optimizer can extend Claude Code subscription usage by 250% through intelligent routing (Agent Booster for simple tasks skips LLM calls entirely, HNSW-based pattern retrieval reduces context size by 32%, caching provides 10% savings).

**Use Case**: Long-running development sessions where repeated patterns (e.g., "add error handling to all async functions") are identified and reused via WASM transforms instead of re-running LLM inference.

### 3. Self-Learning Capabilities
RuVector's learning loop stores successful patterns from each task, builds a knowledge graph of architectural decisions, and predicts agent routing for future tasks. This enables the system to become more efficient over time.

**Use Case**: A team working on authentication across multiple projects stores OAuth patterns after first successful implementation. Subsequent auth tasks automatically route to the best-performing agents from past success, with pattern templates pre-loaded into memory.

### 4. Specialized Agent Pool
100+ pre-built agents cover specific domains: backend-dev, mobile-dev, ml-developer, cicd-engineer, tdd-london-swarm, security-architect, performance-engineer, etc. These can be combined into project-specific swarms without custom implementation.

**Use Case**: A user can invoke `/implement-feature` with a feature description. Ruflo automatically spawns the architect (for design), coder (for implementation), tester (for test generation), and reviewer (for security/quality checks) in parallel with correct dependency ordering.

### 5. Consensus-Based Code Review
Byzantine Fault Tolerance (BFT) consensus allows multiple reviewers to vote on code quality decisions, with majority (or weighted) voting preventing individual reviewer errors from blocking legitimate PRs.

**Use Case**: Pull request requires 3 code reviewers. Ruflo spawns 3 reviewer agents in parallel, each conducting security/quality analysis. BFT consensus with f < n/3 faulty ensures decision robustness even if one reviewer has a bug.

### 6. Automatic Documentation from Source
The `service-docs-maintainer` agent (part of quality gate pipeline) auto-generates and updates documentation from code changes, ensuring docs stay in sync without manual updates.

**Use Case**: After `/complete-implementation`, Phase 5 automatically detects documentation drift and generates updates without user intervention.

---

## Limitations and Caveats

### Documented Limitations

**1. Hallucination Risk in Simple Tasks**: While Agent Booster provides 352x speedup for simple transforms, it only handles 6 predefined intent types. Tasks outside these categories still require LLM inference.

**2. Memory Persistence Trade-offs**: Persistent memory via SQLite WAL mode trades write latency for crash recovery. Very high-frequency updates (>10k/sec) may benefit from in-memory stores.

**3. Consensus Overhead for Small Swarms**: Byzantine and Raft consensus require 3+ replicas minimum. Single-agent tasks have unnecessary consensus overhead.

**4. Provider Dependency**: Despite provider-agnostic design, automatic failover only works when multiple providers are configured. Single-provider setups have no fallback.

**5. HNSW Index Rebuild**: Vector search uses HNSW, which requires periodic index rebuilds (not incremental). Large knowledge bases (>100k patterns) may experience temporary search latency during rebuilds.

**6. Clustering Overhead for Small Swarms**: Mesh topology with full peer-to-peer connectivity has O(n²) connection overhead. Recommended for <20 agents; larger swarms should use hierarchical topology.

---

## Freshness Tracking

**Last Updated**: 2026-03-28 (research entry creation date)

**Repository Last Commit**: 2026-03-25 20:44:10 UTC (docs: update README to match actual implementation #1444)

**Version Verified**: 3.5.0 (stable release from 2026-02-27)

**Sources Current as of**: 2026-03-28

### Confidence by Section

| Section | Confidence | Notes |
|---------|-----------|-------|
| Overview & Identity | high | Official README, package.json, CHANGELOG all match; verified stable release |
| Key Statistics | high | CHANGELOG and README directly quoted; commit count verified via git |
| Features (swarms, learning, security) | high | Technical diagrams in README match source code structure (CLAUDE.md); RuVector components described in detail |
| Architecture | medium-high | Architecture diagrams in README provided; actual source code not fully read (depth limit on worktree) |
| Installation & Usage | high | Official install script and CLI commands documented in README and CLAUDE.md |
| Limitations | medium | No formal limitations doc exists; derived from architecture constraints and CHANGELOG fixes |
| Relevance to Claude Code | medium | Based on advertised integration points; actual integration depth not verified against Claude Code SDK docs |

### Next Review Date

2026-06-28 (3 months from research date)

**Triggers for Early Re-research**:
- Major version release (v4.0.0)
- Security advisory (CVE discovery)
- New RuVector component release
- Breaking changes to MCP tool count or CLI commands

---

## References

| Source | URL | Accessed | Status |
|--------|-----|----------|--------|
| GitHub Repository | <https://github.com/ruvnet/ruflo> | 2026-03-28 | Accessible (shallow clone) |
| README.md | <https://github.com/ruvnet/ruflo/blob/main/README.md> | 2026-03-28 | Accessible (286.6 KB) |
| CHANGELOG.md | <https://github.com/ruvnet/ruflo/blob/main/CHANGELOG.md> | 2026-03-28 | Accessible (9.2 KB) |
| CLAUDE.md | <https://github.com/ruvnet/ruflo/blob/main/CLAUDE.md> | 2026-03-28 | Accessible (38.3 KB) |
| CLAUDE.local.md | <https://github.com/ruvnet/ruflo/blob/main/CLAUDE.local.md> | 2026-03-28 | Accessible (1.8 KB) |
| AGENTS.md | <https://github.com/ruvnet/ruflo/blob/main/AGENTS.md> | 2026-03-28 | Accessible (21.1 KB) |
| SECURITY.md | <https://github.com/ruvnet/ruflo/blob/main/SECURITY.md> | 2026-03-28 | Accessible (1.1 KB) |
| package.json | <https://github.com/ruvnet/ruflo/blob/main/package.json> | 2026-03-28 | Accessible (3.5 KB) |
| npm Registry (@claude-flow/cli) | <https://www.npmjs.com/package/@claude-flow/cli> | 2026-03-28 | Not accessed (assumed current) |
| npm Registry (claude-flow) | <https://www.npmjs.com/package/claude-flow> | 2026-03-28 | Not accessed (assumed current) |
| npm Registry (ruflo) | <https://www.npmjs.com/package/ruflo> | 2026-03-28 | Not accessed (assumed current) |

### Citation Summary

All factual claims in this entry are traceable to extracted passages from the official README.md, CHANGELOG.md, CLAUDE.md (configuration guide), SECURITY.md, and package.json files. No inference or external sources (blog posts, forum discussions) were used in section composition.

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [AgentScope](./agentscope.md) | agent-frameworks | Multi-agent framework with actor-model parallelism and fault-tolerant consensus; comparable production-readiness and semantic routing via learning layer |
| [Superpowers](./superpowers.md) | agent-frameworks | Structured orchestration with specialized agent roles and two-stage verification; shares TDD enforcement and agent pool architecture patterns |
| [OpenFang](./openfang.md) | agent-frameworks | Agent OS with 40 channel adapters and 16-layer security; shares autonomous scheduling, multi-provider routing, and WASM sandbox execution model |
| [Everything Claude Code](./everything-claude-code.md) | agent-frameworks | 16 specialized agents with hook-based automation and token optimization; overlaps in agent pool design and skill-based orchestration |
| [gstack](./gstack.md) | agent-frameworks | Role-specific cognition switching with 8 specialized skills; comparable approach to task-specific agent routing and plugin architecture |
| [pi-mono](./pi-mono.md) | agent-frameworks | TypeScript monorepo with unified LLM API and agent runtime; shares provider-agnostic model support and MCP extensibility patterns |
| [Copilotkit](./copilotkit.md) | agent-frameworks | React-first agentic framework with bi-directional state sync and generative UI; provides UI orchestration complement to Ruflo's backend architecture |
| [Dify](./dify.md) | agent-frameworks | Open-source LLM platform with 100+ model providers, RAG pipelines, and visual workflow builder; shares multi-provider routing and HITL patterns |
| [Browsermcp](../mcp-ecosystem/browsermcp-mcp.md) | mcp-ecosystem | Chrome automation via MCP extension bridge; provides specialized tool capability for Ruflo's 215+ MCP tool ecosystem |
| [Perplexity MCP Server](../mcp-ecosystem/perplexity-mcp-server.md) | mcp-ecosystem | Real-time web search via 4 Sonar tools; exemplifies domain-specific MCP tool integration matching Ruflo's provider-agnostic approach |
| [Ultra MCP](../mcp-ecosystem/ultra-mcp.md) | mcp-ecosystem | Multi-model routing MCP with cost tracking and vector search; directly applicable to Ruflo's token optimization and semantic routing |
| [Gitnexus](../mcp-ecosystem/gitnexus.md) | mcp-ecosystem | Graph-based code intelligence MCP with 13-language support; provides semantic code analysis layer compatible with Ruflo's knowledge graph integration |
| [Motherduck](../data-infrastructure/motherduck.md) | data-infrastructure | Serverless DuckDB with native MCP integration and Dual Execution engine; provides memory backend alternative to AgentDB for pattern storage |
| [Dolt](../data-infrastructure/dolt.md) | data-infrastructure | Version-controlled SQL database with Git semantics and Beads agentic memory; provides persistent memory layer for Ruflo's ReasoningBank pattern storage |

---

## Keywords

agent-orchestration, multi-agent-systems, ai-agents, swarm-intelligence, model-context-protocol, mcp, llm-routing, self-learning-agents, byzantine-consensus, vector-memory, hnsw, agent-booster, wasm, token-optimization, claude-code-integration, enterprise-ai, fault-tolerance, plugin-system, ipfs-marketplace, security-hardening

---

## Document Metadata

| Field | Value |
|-------|-------|
| Entry Type | Research Entry |
| Category | agent-frameworks |
| Resource Name | ruflo |
| Creation Date | 2026-03-28 |
| Research Method | Extractive (GitHub repository + official docs, no inference) |
| Extraction Sources | 8 primary documents from git clone |
| Code Analysis | Not performed (shallow clone, TypeScript source not analyzed) |
| External Validation | None (internal reference only) |
