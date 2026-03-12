# Research Directory

This directory contains curated research on tools, repositories, and patterns relevant to agentic AI development with Claude Code.

**Purpose**: Provide reference material for developing Claude Code skills, agents, plugins, and workflows by documenting novel approaches from the community.

---

## Directory Structure

<eg>
research/
├── README.md                          # This index file
├── agent-frameworks/                  # Agent SDKs and orchestration frameworks
│   ├── ai-agents-frameworks.md        # 10-framework comparative benchmark study
│   ├── copilotkit.md                  # React-first agentic frontend framework with bi-directional state sync and AG-UI protocol (28.9K stars)
│   ├── liteagents.md                  # Multi-tool AI development toolkit with 11 agents and session memory
│   ├── micro-agent.md                 # Lightweight Python ReAct agent framework with MCP multi-server support (MIT)
│   ├── openfang.md                    # Rust Agent OS with autonomous Hands, 40 channel adapters, WASM sandbox, SKILL.md native (3.6K stars)
│   ├── superpowers.md                 # Agentic skills framework and dev methodology (40K+ stars)
│   ├── tersa.md                       # Next.js 15 + ReactFlow visual AI pipeline canvas; typed nodes wired via Vercel AI SDK Gateway (25+ providers); Tersa Agent creates workflows from natural language (927 stars)
│   └── everything-claude-code.md     # Comprehensive performance optimization system: 16 agents, 65+ skills, hook-based automation (50K+ stars)
├── claude-code-plugins/               # Claude Code plugin ecosystems and configuration repositories
│   └── claude-codex-settings.md      # Battle-tested Claude Code plugin ecosystem: 17 plugins, 9 MCP integrations, multi-LLM backend configs (Z.ai, Kimi K2, ccproxy) (452 stars)
├── agent-infrastructure/              # Infrastructure for agentic applications
│   ├── fly-io.md                      # Cloud platform for running apps globally in Firecracker microVMs; Sprites for AI agent sandboxes, first-class MCP support (18 regions)
│   ├── kernel-sh.md                   # Browsers-as-a-service: isolated VM-per-browser Chrome, MCP server, 5.8x faster than Browserbase (670 stars)
│   ├── plano.md                       # AI-native proxy and data plane for multi-agent orchestration
│   ├── tinyfish.md                    # Serverless web agent API: 1,000 parallel ops, AgentQL MCP, all-in pricing at $0.04/op (148 stars)
│   ├── picoclaw.md                    # Go AI assistant — <10MB RAM, 6 channels, runs on $10 RISC-V hardware, 18K stars
│   ├── pinchtab.md                    # Browser control for AI agents — 12MB Go binary, HTTP API, a11y tree snapshots at 800 tokens/page (2.3K stars)
│   └── zeroclaw.md                    # Rust AI assistant infrastructure — sub-5MB RAM, 28+ providers, trait-driven (14.9K stars)
├── api-frameworks/                    # High-performance API frameworks for backend services
│   ├── fastapi.md                     # Modern Python web framework with Pydantic (95K+ stars)
│   ├── motia.md                       # Unified backend framework replacing APIs/queues/workflows/AI agents with one Step primitive (15K+ stars)
│   ├── pocketbase.md                  # Open-source Go backend in 1 file: SQLite, realtime, auth, files, admin dashboard (56K+ stars)
│   └── tornado.md                     # Python web framework and async networking library (22K+ stars)
├── async-libraries/                   # Python async I/O libraries and concurrency frameworks
│   ├── anyio.md                       # Backend-agnostic async concurrency library (426M downloads/month)
│   ├── asyncssh.md                    # Asyncio-native SSH client/server — reverse tunnels, SFTP, jump hosts, pure-Python key management (1.7K stars)
│   └── trio.md                        # Structured concurrency async library for Python (7K+ stars)
├── llm-infrastructure/                # LLM inference and serving infrastructure
│   ├── localai.md                     # Free open-source local AI inference server, OpenAI-compatible API, no GPU required (43K+ stars)
│   └── tensorzero.md                  # Industrial-grade LLM gateway with <1ms latency, fine-tuning, and A/B testing (Rust)
├── ml-infrastructure/                 # ML compute engines and model serving platforms
│   ├── microgpt-playground.md         # Browser-native GPT training and inference, zero-dependency JS port of Karpathy's microgpt.py (65 stars)
│   └── ray.md                         # AI compute engine for scaling Python/ML workloads (41K+ stars)
├── python-runtimes/                   # Alternative Python interpreters and runtimes
│   └── rustpython.md                  # Python 3 interpreter written in Rust with WASM support (22K+ stars)
├── rust-python-bindings/              # Rust-Python interoperability and binding libraries
│   └── pyo3.md                        # Rust bindings for Python with maturin build tooling (15K+ stars)
├── ai-observability/                  # AI/LLM observability and debugging platforms
│   └── logfire.md                     # Pydantic Logfire - full-stack AI observability with MCP (4K+ stars)
├── code-auditing/                     # Code security and quality auditing tools
│   ├── hound.md                       # Autonomous AI security auditor with knowledge graphs
│   └── snyk-cli-cpp-scans.md          # Snyk CLI hash-based open-source vulnerability scanning for C/C++ unmanaged dependencies
├── ai-design-tools/                   # AI-powered visual creation and design platforms
│   ├── hedra.md                       # AI video/image/audio creation platform
│   ├── jimeng.md                      # ByteDance SeedDance 2.0 AI video/image generation with cinematic camera control
│   ├── ui-ux-pro-max-skill.md        # AI design skill for 16 coding assistants with BM25 search over 67 styles, 96 palettes, 57 font pairings (34.9K stars)
│   ├── google-stitch.md              # Google Stitch - AI UI design tool generating app frontends from text/images using Gemini 2.5
│   └── diode.md                      # Diode - Browser-based 3D hardware simulator for circuit building, programming, and simulation
├── ai-research-tools/                 # AI research tools and newsletters
│   └── the-unwind-ai.md              # AI builder newsletter with 95K+ star open-source companion repo
├── coding-agents/                     # Autonomous AI coding agent platforms
│   ├── accomplish.md                  # Local-first AI desktop agent with MCP tools, 15 providers, permission-gated execution (9K+ stars)
│   ├── cline.md                       # Open-source autonomous coding agent with human-in-the-loop approvals (Apache-2.0)
│   ├── openai-codex-cli.md            # OpenAI Codex CLI — Rust-based coding agent with OS sandbox, MCP server/client, Starlark exec policy (62.5K stars)
│   ├── openhands.md                   # Open platform for cloud coding agents (67K+ stars)
│   ├── pilot.md                       # Autonomous development pipeline wrapping Claude Code CLI (BSL 1.1)
│   └── tembo.md                       # Cloud AI coding agent orchestration (Claude Code, Codex, Cursor, Amp, OpenCode)
├── context-management/                # Memory, context window, and RAG tools
│   ├── claude-mem.md                  # Persistent memory compression for Claude Code (15K+ stars)
│   ├── jina-ai.md                     # Search foundation: Reader API, multilingual embeddings, rerankers (acquired by Elastic 2025)
│   ├── local-memory.md               # Persistent memory infrastructure for AI agents (MCP + REST + CLI)
│   └── sourcesyncai.md               # Managed RAG platform with auto-syncing connectors and hybrid search
├── data-infrastructure/               # Real-time data platforms for analytics
│   ├── cocoindex.md                   # Ultra-performant AI data transformation framework with Rust core, incremental processing, and dataflow model (Apache 2.0)
│   ├── dolt.md                        # MySQL-compatible version-controlled SQL database — branch, merge, diff, clone via SQL (20.3K stars)
│   ├── motherduck.md                  # Serverless cloud DuckDB warehouse with Dual Execution and native MCP integration (36K+ stars)
│   └── tinybird.md                    # Managed ClickHouse platform with MCP and analytics agents
├── documentation-tools/                # Architecture documentation and living docs
│   └── living-architecture.md         # Operational flow architecture extraction with Rivière schema (79 stars)
├── embedded-ui-libraries/              # Embedded graphics libraries for microcontrollers and MCUs
│   └── lvgl.md                         # LVGL - Light and Versatile Graphics Library (22.8K+ stars)
├── developer-tools/                   # Developer productivity and workflow tools
│   ├── biome.md                       # Rust-based web toolchain: formatter + linter + import organizer, 97% Prettier compat, ~35× faster (23.8K stars)
│   ├── byobu.md                       # Enhanced terminal multiplexer wrapper for tmux/screen — F-key layer, 40+ status plugins, XDG config (1.5K stars)
│   ├── animejs.md                     # Lightweight JavaScript animation engine (66K+ stars)
│   ├── claude-conductor.md            # Context-Driven Development plugin for Claude Code (9 commands, skill ecosystem)
│   ├── claude-openocd-spi-dump.md     # Claude Code plugin for SPI flash dumping via OpenOCD
│   ├── claude-pilot.md                # Quality-enforcement layer for Claude Code with 15 hooks, TDD enforcement, /spec workflow, and persistent memory (1,390 stars)
│   ├── claude-quickstarts.md          # Official Anthropic quickstart projects (14.7K stars)
│   ├── copier-astral.md               # Python project template with Astral toolchain (uv, ruff, ty)
│   ├── dtach.md                       # Minimal C detach/reattach tool — raw PTY via Unix sockets, scripted input injection (619 stars)
│   ├── git-cliff.md                   # Customizable changelog generator from Git history
│   ├── github-cli.md                  # Official GitHub CLI tool for PRs, issues, workflows (37.8K stars)
│   ├── google-ai-studio.md            # Google AI Studio — browser-based IDE and playground for Gemini API (1M-token context, free tier)
│   ├── grepai.md                      # Semantic code search and call graph analysis for AI agents (1.2K stars)
│   ├── jina-reader.md                 # Jina Reader — URL-to-Markdown API via r.jina.ai prefix, full SPA/PDF support, Apache 2.0 (~9.8K stars)
│   ├── jirajs.md                      # TypeScript Jira API client for Cloud, Server, and Data Center
│   ├── jscpd.md                       # Copy/paste detector for 150+ languages (5K+ stars)
│   ├── libtmux.md                     # Typed Python API for tmux — Server/Session/Window/Pane dataclasses, send_keys, capture_pane (1.1K stars)
│   ├── loguru.md                      # Python logging made simple with zero config (23K+ stars)
│   ├── kythe.md                       # Google's language-agnostic code intelligence platform (2.1K stars)
│   ├── lopaka.md                      # Graphics editor for embedded displays with C/C++ code generation (1.2K stars)
│   ├── niteni.md                      # AI-powered code review for GitLab CI pipelines
│   ├── off-grid-mobile.md             # Offline AI suite for iOS/Android with llama.cpp, Stable Diffusion, and Whisper (696 stars)
│   ├── orbstack.md                    # Fast Docker Desktop and Linux VM alternative for macOS
│   ├── paperdraw.md                   # Browser-based distributed systems simulator with chaos injection (Flutter web)
│   ├── piebald.md                     # Cross-platform agentic AI desktop client with parallel agents, session persistence, OAuth subscriptions (Free + Pro)
│   ├── pixel-agents.md                # VS Code extension rendering Claude Code terminals as pixel-art characters in a virtual office (3K+ stars)
│   ├── psmux.md                       # Native Windows tmux replacement in Rust — 76 commands, .tmux.conf compat, ConPTY (269 stars)
│   ├── shpool.md                      # Shell session pool daemon in Rust — raw PTY passthrough, VT100 reattach replay, autodaemon (1.7K stars)
│   ├── repomix.md                     # Pack codebase into AI-friendly formats (21K+ stars)
│   ├── tabz-browser-console-forwarder.md # Browser console to terminal forwarder for AI agent debugging (MIT)
│   ├── traycer.md                     # Spec-driven AI development orchestrator (commercial SaaS)
│   ├── tmuxp.md                      # Python tmux session manager — YAML/JSON workspace configs, plugin system, freeze/replay (4.4K stars)
│   ├── using-tmux-with-claude-code.md # tmux + Claude Code workflow guide: copy-mode, capture, multi-pane orchestration
│   ├── vert.md                        # WebAssembly-based file converter (13K+ stars)
│   └── yume.md                        # Native desktop GUI for Claude Code CLI (Tauri + Rust)
├── evaluation-testing/                # Agent evaluation, testing, and harness engineering
│   ├── harness-engineering-martin-fowler.md  # Harness engineering discipline for AI coding agents (Martin Fowler / Böckeler)
│   ├── harness-engineering-openai.md  # Harness engineering practices from OpenAI Codex team (1M lines, 3.5 PRs/day)
│   └── codex-harness-openai.md        # Codex App Server bidirectional JSON-RPC harness architecture (61K+ stars)
├── mcp-ecosystem/                     # MCP servers and integrations
│   ├── browsermcp-mcp.md              # Chrome browser automation MCP server via extension bridge (5.8K stars)
│   ├── docs-mcp-server.md             # Local documentation index (Grounded Docs)
│   ├── mcpjam.md                      # Local inspector for MCP servers and apps
│   ├── narsil-mcp.md                  # Comprehensive code intelligence MCP server
│   ├── saga-mcp.md                    # Jira-like SQLite project tracker MCP — 31 tools, Projects>Epics>Tasks>Subtasks (11 stars)
│   ├── ultra-mcp.md                   # Multi-model MCP server: OpenAI/Gemini/Azure/Grok through single interface with React dashboard (269 stars)
│   └── openspec-mcp.md                # Spec-driven development MCP — 50+ tools, approval state machine, WebSocket dashboard on port 3000
│   ├── octocode-mcp.md                # Research Driven Development platform
│   ├── perplexity-mcp-server.md       # Perplexity AI real-time web search and reasoning MCP server
│   ├── retio-pagemap.md               # MCP server compressing HTML to 2-5K token structured maps
│   ├── spec-workflow-mcp.md           # Spec-driven development workflow with approval gates and real-time dashboard (3.9K stars)
│   └── cocoindex-code.md             # Embedded MCP server for semantic code search via AST analysis and embeddings (Apache-2.0)
├── research-agent-patterns/           # Multi-agent architectures and orchestration
│   ├── claw-loop.md                   # Autonomous development orchestration via tmux + cron
│   ├── compound-engineering-plugin.md # Every Inc's Plan/Work/Review/Compound workflow plugin
│   ├── gastown.md                     # Gas Town — multi-agent workspace manager with tmux transport, Dolt ledger, TOML formula DAGs (10.7K stars)
│   ├── github-patterns.md             # Patterns from GitHub research agent implementations
│   ├── orchestrator-agent-creation-guide.md  # OpenCode orchestrator agent guide
│   ├── google-adk-context-engineering.md  # Google ADK context engineering: tiered storage, compiled views, scoped multi-agent handoffs (17.9K stars)
│   ├── tinyclaw.md                    # Multi-agent multi-channel 24/7 AI assistant with peer-to-peer handoffs
│   ├── ollama-subagents-web-search-claude-code.md  # Ollama native subagents and web search for Claude Code (163K+ stars)
│   └── oh-my-opencode.md              # code-yeongyu/oh-my-opencode — Production-scale Claude Code orchestration: Sisyphus/Atlas/Prometheus multi-agent architecture, category-based model routing, hash-anchored editing, demand-scoped MCP (37.5K stars in 4 months)
├── skill-generation-tools/            # Tools that create AI skills/prompts
│   ├── claude-code-skills-alirezarezvani.md # 170 modular skill packages for Claude Code, Codex, Gemini CLI across 9 domains (2.5K+ stars)
│   ├── clawhub.md                     # Skill registry for AI agents with vector search
│   ├── claude-code-templates.md       # 100+ Claude Code agents/commands/skills/MCPs/hooks via npx installer and aitmpl.com (21.8K stars)
│   ├── claude-skillz.md               # 18+ behavioral skills, 12 personas, Claude Launcher utility
│   ├── codex-skills.md                # 19-skill catalog for OpenAI Codex CLI with npx installer (116 stars)
│   ├── everything-claude-code.md      # Comprehensive agent harness performance system: 65+ skills, 16 agents, 40+ commands, hooks, AgentShield security scanner (61.7K stars)
│   ├── human-compiler.md              # Interview-to-agent plugin generator for Claude Code (MIT)
│   ├── mcpskills-cli.md               # MCP-to-skill converter via Streamable HTTP discovery
│   ├── skill-seekers.md               # Documentation-to-skill automation tool
│   ├── skillkit.md                    # Universal package manager for AI agent skills (32 agents)
│   ├── skillsmp.md                    # Open marketplace for 66,500+ AI agent skills (Claude Code, Codex CLI, ChatGPT; MIT)
│   ├── skrills.md                     # Rust skills support engine: validates, syncs, and analyzes skills across Claude Code, Codex CLI, and Copilot CLI (52 stars)
│   ├── softaworks-agent-toolkit.md    # 43 skills, 6 agents, 7 slash commands for Claude Code (621 stars)
│   └── vercel-labs-skills.md          # Universal skill installer for 40+ AI coding agents (6.3K stars)
├── prompt-engineering/                # Prompt optimization and testing platforms
│   ├── google-ai-studio.md            # Google AI Studio — browser-based Gemini IDE with 20+ models, function calling, grounding, and OpenAI-compatible API
│   ├── prompt-engine.md               # SaaS prompt generator converting plain-language to professional-grade prompts in <15s ($19/month)
│   └── system-prompts-ai-tools.md     # Leaked system prompts and model configs for 30+ AI tools including Claude Code, Cursor, Windsurf, Devin AI (117.9K stars)
└── task-management/                   # AI-powered task management for development
    └── claude-task-master.md          # Task management system for AI-driven development (25K+ stars)
</eg>

---

## Layer Mapping

Research entries can include SDLC layer metadata for discovery. See [.claude/docs/sdlc-layers/](../.claude/docs/sdlc-layers/) for the three-layer model.

| Layer | Scope | Example Entries |
|-------|-------|-----------------|
| **Layer 0** | SDLC-agnostic process | evaluation-testing/harness-engineering-*.md |
| **Layer 1** | Language-specific | developer-tools/copier-astral.md (Python toolchain) |
| **Layer 2** | Stack/Goal-specific | api-frameworks/fastapi.md, api-frameworks/tornado.md |

**Metadata** (optional, in frontmatter `metadata:` block):

- `layer`: `0` \| `1` \| `2`
- `language`: `python` \| `typescript` \| `rust` \| ...
- `stack`: `fastapi` \| `tornado` \| `python-cli` \| ...

**Filter by layer**: `uv run research/knowledge-explorer.py list --layer 2`

---

## Research Categories

### 1. Research Agent Patterns

**Location**: [./research-agent-patterns/](./research-agent-patterns/)

Research on multi-agent architectures, orchestration patterns, and research workflows.

| Document                                                                                               | Description                                                                                                            | Last Updated |
| ------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------- | ------------ |
| [claw-loop.md](./research-agent-patterns/claw-loop.md)                                                 | The Claw Loop v2.0 - autonomous development orchestration via tmux + cron with supervisor-worker pattern               | 2026-02-15   |
| [compound-engineering-plugin.md](./research-agent-patterns/compound-engineering-plugin.md)             | Every Inc's Claude Code plugin with 27 agents, 20 commands - Plan/Work/Review/Compound workflow (6.8K stars)           | 2026-01-31   |
| [gastown.md](./research-agent-patterns/gastown.md)                                                     | Gas Town v0.9.0 — Steve Yegge's multi-agent workspace manager coordinating 20-50+ Claude Code sessions via tmux transport, Dolt SQL ledger, TOML formula DAGs, witness zombie detection, convoy tracking, and Bors-style merge queue (10.7K stars, MIT) | 2026-03-01   |
| [github-patterns.md](./research-agent-patterns/github-patterns.md)                                     | Patterns from 40+ repositories including Chief of Staff model, 12-agent academic pipelines, Pydantic AI research loops | 2025-12-09   |
| [orchestrator-agent-creation-guide.md](./research-agent-patterns/orchestrator-agent-creation-guide.md) | Comprehensive guide for creating orchestrator agents in OpenCode - routing, chaining, parallel delegation patterns     | 2026-01-26   |
| [tinyclaw.md](./research-agent-patterns/tinyclaw.md)                                                   | TinyClaw - multi-agent multi-channel 24/7 AI assistant with peer-to-peer handoffs and file-based queue (2.1K stars)    | 2026-02-18   |
| [google-adk-context-engineering.md](./research-agent-patterns/google-adk-context-engineering.md)     | Google ADK context engineering: tiered storage model, compiler-style processor pipeline, scoped multi-agent handoffs (17.9K stars) | 2026-02-23   |
| [ollama-subagents-web-search-claude-code.md](./research-agent-patterns/ollama-subagents-web-search-claude-code.md) | Ollama v0.16.2 native subagents and web search for Claude Code with Anthropic API compatibility (163K+ stars) | 2026-02-19   |
| [ai-data-science-team.md](./research-agent-patterns/ai-data-science-team.md) | AI Data Science Team — LangGraph supervisor + 9 specialist agents (wrangling, cleaning, visualization, SQL, H2O ML, MLflow, EDA, feature engineering, loader) with sandboxed code execution and AI Pipeline Studio Streamlit app (5K+ stars, MIT) | 2026-03-04   |
| [oh-my-opencode.md](./research-agent-patterns/oh-my-opencode.md) | code-yeongyu/oh-my-opencode — Production-scale Claude Code orchestration: Sisyphus/Atlas/Prometheus multi-agent architecture, category-based model routing, hash-anchored editing, demand-scoped MCP (37.5K stars in 4 months) | 2026-03-06   |

**Key Topics**:

- Stateless agent coordination
- File-based context sharing
- Iterative research loops with exit criteria
- Citation and bibliography management
- Multi-phase synthesis without over-summarizing
- Orchestrator routing patterns and capability maps
- Sequential chaining vs parallel delegation
- Context hygiene and token management
- Plan/Work/Review/Compound workflow (80/20 planning-execution split)
- 14 parallel review agents for comprehensive code review
- Knowledge compounding via structured `docs/solutions/` documentation
- Smart research decision logic (risk-aware, context-aware)
- Git worktree integration for parallel development
- Claude Code plugin architecture patterns
- Supervisor-worker AI agent orchestration via tmux terminals
- Context engineering: tiered storage, compiled views, and processor pipelines for production agents
- Cron-based polling with one-action-per-cycle discipline
- Context clearing between phases for clean context windows
- State-file-driven workflow progression (not memory-based)
- Model switching per task type (Opus for reasoning, Sonnet for execution)
- Fail-gracefully design (crashes, rate limits as expected events)
- Peer-to-peer agent handoff via `[@teammate: message]` bracket tags
- File-based queue with atomic incoming/processing/outgoing state machine
- Isolated agent workspaces with per-agent provider, model, and personality
- Multi-channel routing (Discord, Telegram, WhatsApp) to shared agent pool
- SOUL.md declarative personality specification for consistent agent voice
- Heartbeat-driven proactive agent activation on schedule
- Sender pairing allowlist for access control
- Ollama native subagent support for parallel tasks in isolated context windows
- Zero-config Claude Code launch via `ollama launch claude`
- Anthropic API compatibility layer for local/cloud model swapping
- Built-in web search without MCP servers or API keys
- Model-level subagent and tool calling with streaming and vision support

---

### 2. MCP Ecosystem

**Location**: [./mcp-ecosystem/](./mcp-ecosystem/)

MCP servers, tools, and integrations for extending AI assistant capabilities.

| Document                                                 | Description                                                                                              | Last Updated |
| -------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- | ------------ |
| [browsermcp-mcp.md](./mcp-ecosystem/browsermcp-mcp.md)   | Browser MCP - Chrome browser automation via extension bridge, preserving auth sessions and real fingerprint (5.8K stars) | 2026-02-20   |
| [docs-mcp-server.md](./mcp-ecosystem/docs-mcp-server.md) | Grounded Docs - local documentation index with semantic search, open-source Context7 alternative         | 2026-01-26   |
| [mcpjam.md](./mcp-ecosystem/mcpjam.md)                   | Local inspector for MCP servers, ChatGPT apps, MCP Apps with LLM playground, OAuth debugger, E2E testing | 2026-01-26   |
| [mimir-mcp.md](./mcp-ecosystem/mimir-mcp.md)             | Git-backed AI memory system with 7 MCP tools, graph associations, and version-controlled persistence     | 2026-02-04   |
| [narsil-mcp.md](./mcp-ecosystem/narsil-mcp.md)           | Rust MCP server with 90 tools for code intelligence, security scanning, call graphs                      | 2026-01-26   |
| [octocode-mcp.md](./mcp-ecosystem/octocode-mcp.md)       | Research Driven Development platform with GitHub search, LSP, and GAN-inspired adversarial flow          | 2026-01-26   |
| [perplexity-mcp-server.md](./mcp-ecosystem/perplexity-mcp-server.md) | Perplexity API Platform MCP server with real-time web search, deep research, and reasoning via 4 Sonar tools (2K stars) | 2026-02-20   |
| [retio-pagemap.md](./mcp-ecosystem/retio-pagemap.md)     | Retio PageMap - MCP server compressing HTML pages to 2-5K token structured maps with 95.2% task success  | 2026-02-18   |
| [sourcesyncai-mcp.md](./mcp-ecosystem/sourcesyncai-mcp.md) | SourceSync.ai MCP Server - 28-tool MCP bridge for AI-ready knowledge bases with multi-source ingestion, hybrid search, and auto-sync | 2026-02-23   |
| [saga-mcp.md](./mcp-ecosystem/saga-mcp.md)                   | saga-mcp - SQLite-backed project tracker MCP (31 tools): Projects>Epics>Tasks>Subtasks, dependency auto-blocking, session diff, immutable activity log | 2026-03-02   |
| [ultra-mcp.md](./mcp-ecosystem/ultra-mcp.md)                 | Ultra MCP - single MCP interface routing to OpenAI/Gemini/Azure/Grok with cost tracking, vector search, React dashboard, 25 tools as prompts (269 stars) | 2026-03-02   |
| [openspec-mcp.md](./mcp-ecosystem/openspec-mcp.md)           | OpenSpec MCP - 50+ tool spec-driven workflow: approval state machine, threaded review, task tracking, Fastify+WebSocket dashboard on port 3000 | 2026-03-02   |
| [spec-workflow-mcp.md](./mcp-ecosystem/spec-workflow-mcp.md) | Spec Workflow MCP - spec-driven development with Requirements→Design→Tasks approval gates, real-time React dashboard on port 5000 (3.9K stars) | 2026-03-02   |
| [cocoindex-code.md](./mcp-ecosystem/cocoindex-code.md)       | CocoIndex Code — embedded MCP server for semantic code search via AST analysis and embeddings; zero-config, 30+ languages, ~70% token savings, incremental indexing (Apache-2.0) | 2026-03-10   |

**Key Topics**:

- Code intelligence and symbol analysis
- Security scanning (OWASP, CWE, taint analysis)
- Call graph and control flow analysis
- Neural semantic search
- Knowledge graphs (SPARQL, CCG)
- Token optimization with configurable presets
- Research Driven Development (RDD) methodology
- GAN-inspired adversarial verification workflows
- GitHub semantic code search
- LSP integration (go-to-definition, find-references)
- Cross-model validation patterns
- Documentation grounding and version-specific retrieval
- Hybrid search (vector + full-text) with RRF ranking
- Privacy-first local documentation indexing
- MCP server local development and testing
- ChatGPT Apps SDK widget emulation
- MCP Apps (SEP-1865) development tooling
- OAuth 2.1 debugging and multi-protocol support
- AI-powered test case generation
- E2E evaluation across MCP clients
- Multi-LLM playground testing
- Git-backed persistent memory for LLM applications
- Graph-based memory associations with typed relationships
- Human-aligned tool design (intent-based naming)
- Supersedes relationships for handling outdated information
- Multi-user memory isolation with SAML 2.0 support
- HTML-to-structured-map compression (97% token reduction for web browsing)
- 3-tier interactive element detection (ARIA roles, implicit HTML, CDP event listeners)
- Token-budget-aware output assembly with tiktoken enforcement
- Nonce-based prompt injection defense for untrusted web content
- SSRF protection with scheme whitelist and private IP blocking
- Multilingual web content extraction (Korean, English, Japanese, French, German)
- Chrome extension WebSocket bridge for live-profile browser automation (no new browser instance)
- ARIA accessibility tree snapshot as structured page perception (compact, token-efficient vs raw HTML)
- Post-action snapshot return pattern: updated page state appended automatically after every mutation tool
- Authentication and session preservation via user's existing Chrome profile (cookies, tokens intact)
- Stealth automation: extension API avoids `navigator.webdriver` flag and Playwright detection signals
- Zod-to-JSON-Schema tool definition pattern for type-safe MCP tool schemas
- Typed WebSocket message protocol (`SocketMessageMap`) shared between server and extension via monorepo
- `browser_get_console_logs` for AI-driven runtime error diagnosis of web applications
- Real-time web search via Perplexity Sonar models (search, ask, research, reason)
- Multi-transport MCP deployment (stdio for desktop, HTTP/Docker for cloud)
- Proxy cascade configuration for enterprise environments
- Token optimization via optional `strip_thinking` response filtering
- Tool specialization pattern (4 distinct tools for different query complexity levels)

---

### 3. Skill Generation Tools

**Location**: [./skill-generation-tools/](./skill-generation-tools/)

Tools and services that automate the creation of AI skills from documentation, code, and other sources.

| Document                                                            | Description                                                                                                    | Last Updated |
| ------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- | ------------ |
| [anthropics-skills.md](./skill-generation-tools/anthropics-skills.md) | Anthropic Agent Skills - official Anthropic skills repo with 17 skills in 3 plugins, A/B eval harness, description-driven triggering (84.9K stars) | 2026-03-06   |
| [claude-code-skills-alirezarezvani.md](./skill-generation-tools/claude-code-skills-alirezarezvani.md) | Claude Code Skills Library - 170 production-ready modular skill packages across 9 domains (engineering, marketing, C-level, compliance) for Claude Code, Codex, Gemini CLI, OpenClaw; 210+ stdlib-only Python tools, 18 marketplace plugins (2.5K+ stars) | 2026-03-10   |
| [clawhub.md](./skill-generation-tools/clawhub.md)                    | ClawHub - public skill registry for OpenClaw/Clawdbot agents; vector search, semver versioning, MIT CLI (3,286+ skills) | 2026-02-23   |
| [claude-code-templates.md](./skill-generation-tools/claude-code-templates.md) | Claude Code Templates - 100+ ready-to-use agents, commands, skills, MCPs, hooks, and settings for Claude Code; npx installer and aitmpl.com browser (21.8K stars) | 2026-03-03   |
| [claude-skillz.md](./skill-generation-tools/claude-skillz.md)       | Claude Skillz - 18+ behavioral skills, 12 personas, 10 plugins, and Claude Launcher for rapid persona switching (238 stars) | 2026-02-20   |
| [codex-skills.md](./skill-generation-tools/codex-skills.md)         | codex-skills - 19-skill catalog for OpenAI Codex CLI with npx installer, global ledger pattern, and prompt-injection hardening (116 stars) | 2026-02-20   |
| [everything-claude-code.md](./skill-generation-tools/everything-claude-code.md) | Everything Claude Code - comprehensive agent harness performance system: 65+ skills, 16 agents, 40+ commands, hooks, rules, and AgentShield security scanner for Claude Code, Codex, Cursor, OpenCode (61.7K stars) | 2026-03-06   |
| [human-compiler.md](./skill-generation-tools/human-compiler.md)     | HumanCompiler - interview-to-agent plugin generator that replicates human decision-making via 8-phase structured interviews (MIT) | 2026-02-19   |
| [mcpskills-cli.md](./skill-generation-tools/mcpskills-cli.md)       | mcpskills-cli - MCP-to-skill converter generating SKILL.md and polyglot call scripts from Streamable HTTP servers | 2026-02-15   |
| [skill-seekers.md](./skill-generation-tools/skill-seekers.md)       | Skill Seekers - converts docs, GitHub repos, and PDFs into Claude/Gemini/OpenAI skills                          | 2026-01-26   |
| [skillkit.md](./skill-generation-tools/skillkit.md)                  | SkillKit - universal package manager for AI agent skills with 15K+ skills, 32 agent support, and cross-format translation | 2026-02-08   |
| [skillsmp.md](./skill-generation-tools/skillsmp.md)                   | SkillsMP - open marketplace for 66,500+ AI agent skills (Claude Code, Codex CLI, ChatGPT); REST API, MCP server, SKILL.md standard (MIT) | 2026-02-23   |
| [skrills.md](./skill-generation-tools/skrills.md)                    | Skrills - Rust skills support engine validating and syncing skills across Claude Code, Codex CLI, and Copilot CLI with 40+ MCP tools (52 stars) | 2026-02-23   |
| [softaworks-agent-toolkit.md](./skill-generation-tools/softaworks-agent-toolkit.md) | Softaworks Agent Toolkit - 43 skills, 6 agents, 7 slash commands for Claude Code with multi-platform support (621 stars) | 2026-02-20   |
| [vercel-labs-skills.md](./skill-generation-tools/vercel-labs-skills.md) | Vercel Labs Skills - universal CLI for installing skills to 40+ AI coding agents with symlink-first design (6.3K stars) | 2026-02-20   |

**Key Topics**:

- Documentation scraping and extraction
- Multi-source analysis (docs + code + PDFs)
- Conflict detection between docs and implementation
- Three-Stream Architecture (Code/Docs/Insights)
- Multi-platform skill packaging
- MCP tool schema to SKILL.md conversion via Jinja2 templates
- Polyglot call script generation (bash, python, node, go, rust)
- Token optimization via on-demand skill loading vs all-at-once MCP tools
- Streamable HTTP transport for MCP server discovery
- Cross-agent skill format translation (32 agent formats)
- Git-based `.skills` manifest for team skill consistency
- AI-powered skill generation with multi-provider LLM support
- Skill security scanning for prompt injection and malicious patterns
- Smart recommendations based on codebase analysis
- 8-phase structured interview pipeline for capturing human expertise
- Interview-to-agent plugin generation via Handlebars templates
- Dual-mode agent output (autonomous + advisory) from single behavioral profile
- MCP-powered answer verification against real work artifacts (Notion, Asana)
- Phase-decomposed orchestrator with progressive state persistence
- Centralized skill registry with vector-based semantic search
- Claude Launcher utility for rapid persona/model switching via fuzzy search
- @ reference pre-processing to embed skills at launch time (avoiding 18K+ token overhead)
- Composable persona-skill separation (identity decoupled from behavioral skills)
- Hook-based automation (auto code review on session stop, 5 Whys verification)
- Instructive vs descriptive prompt writing patterns for skill authoring
- State machine governance for TDD and process-driven skill workflows
- Multi-CLI validation tiers (permissive Claude vs strict Codex/Copilot frontmatter rules)
- Bidirectional skill sync with file-hash protection against overwriting manual edits
- Token analysis with per-skill counting and reduction suggestions
- MCP server exposing 40+ tools for validation, sync, and project-aware skill generation
- Dependency resolution with cycle detection and semantic versioning constraints
- Session mining for usage-based skill recommendations
- `AgentAdapter` trait pattern for pluggable per-CLI sync adapters
- Multi-platform skill toolkit with 43 skills across 10 categories (AI, Meta, Docs, Design, Dev, Planning)
- Agent Skills format (agentskills.io) for cross-tool compatibility
- Specialized agent roles (security-hardener, researcher, git-master, ai-architect)
- Universal skill installer CLI supporting 40+ AI coding agents
- Symlink-first installation with copy mode fallback
- Auto-detection of installed agents and platform-specific path resolution
- Claude Code plugin manifest format compatibility
- Non-interactive CI/CD mode for automated skill deployment
- Drop-in SKILL.md skill folders auto-discovered by Codex CLI from `~/.agents/skills/`
- npx CLI for listing, searching, and installing individual skills or entire categories
- Global ledger pattern (`~/.codex/AGENTS.MD`) for cross-project cross-session agent context
- Prompt-injection hardening via invisible Unicode character scanner run in CI on every push/PR
- Stdlib-only SKILL.md validation (no PyYAML) for zero-dependency CI integration
- Registry-as-generated-artifact: `skills.json` regenerated from source, not hand-maintained
- User vs. repo-local install scope via `--dir` flag
- Minimal frontmatter constraints (name ≤100 chars, description ≤500 chars single-line)

---

### 4. Code Auditing

**Location**: [./code-auditing/](./code-auditing/)

Tools and frameworks for autonomous code security auditing and vulnerability detection.

| Document                             | Description                                                                                           | Last Updated |
| ------------------------------------ | ----------------------------------------------------------------------------------------------------- | ------------ |
| [hound.md](./code-auditing/hound.md) | Autonomous AI security auditor using knowledge graphs, belief systems, and hypothesis-driven analysis | 2026-01-26   |
| [snyk-cli-cpp-scans.md](./code-auditing/snyk-cli-cpp-scans.md) | Snyk CLI hash-based open-source vulnerability scanning for C/C++ unmanaged dependencies via `--unmanaged` flag | 2026-02-23   |

**Key Topics**:

- Knowledge graph-driven code analysis
- Hypothesis and belief systems for vulnerability tracking
- Scout/Strategist model switching for cost efficiency
- Coverage vs intuition planning balance
- Interactive steering via chatbot UI
- Session persistence and recovery
- Professional report generation with PoC integration
- Hash-based dependency fingerprinting for packageless C/C++ projects
- Confidence-scored dependency identification from source code
- CVE mapping for vendored open-source libraries

---

### 5. Agent Frameworks

**Location**: [./agent-frameworks/](./agent-frameworks/)

Agent SDKs, orchestration frameworks, and comparative studies of multi-agent architectures.

| Document                                                              | Description                                                                                                                            | Last Updated |
| --------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | ------------ |
| [ai-agents-frameworks.md](./agent-frameworks/ai-agents-frameworks.md) | Comparative learning repository for 10 AI agent frameworks with benchmarks for response time, memory, tokens, RAG, and API integration | 2026-01-31   |
| [copilotkit.md](./agent-frameworks/copilotkit.md)                     | React-first agentic frontend framework with bi-directional state sync, generative UI, AG-UI protocol, and human-in-the-loop (28.9K stars) | 2026-02-23   |
| [dify.md](./agent-frameworks/dify.md)                                 | Open-source LLM application platform with visual workflow builder, RAG pipelines, 100+ model providers, HITL, and LLMOps (130K+ stars)  | 2026-02-23   |
| [get-shit-done.md](./agent-frameworks/get-shit-done.md)               | Meta-prompting, context engineering, and spec-driven development system with 11 agents for Claude Code, OpenCode, Gemini (10K+ stars)  | 2026-02-01   |
| [liteagents.md](./agent-frameworks/liteagents.md)                     | Multi-tool AI development toolkit with 11 agents, 22 commands, Hot Memory pipeline, and session friction analysis for 4 AI coding tools | 2026-02-15   |
| [micro-agent.md](./agent-frameworks/micro-agent.md)                   | Micro-Agent - lightweight Python 3.12 ReAct agent framework with MCP multi-server support, token budget enforcement, and execution visualization (MIT) | 2026-02-20   |
| [openfang.md](./agent-frameworks/openfang.md)                         | OpenFang - Rust Agent OS with autonomous Hands, 40 channel adapters, WASM sandbox, 16-layer security, native SKILL.md support (Apache-2.0/MIT) | 2026-02-27   |
| [superpowers.md](./agent-frameworks/superpowers.md)                   | Agentic skills framework with 14 skills for TDD, debugging, and subagent-driven development - works with Claude Code, Codex, OpenCode  | 2026-01-31   |
| [tersa.md](./agent-frameworks/tersa.md)                               | vercel-labs/tersa — Next.js 15 + ReactFlow visual AI pipeline canvas; typed nodes wired via Vercel AI SDK Gateway (25+ providers); Tersa Agent creates workflows from natural language (927 stars) | 2026-03-06   |
| [everything-claude-code.md](./agent-frameworks/everything-claude-code.md) | Everything Claude Code — comprehensive performance optimization system: 16 specialized agents, 65+ skills, hook-based automation, token optimization, 6-language support (50K+ stars, MIT) | 2026-03-10   |

**Key Topics**:

- Framework comparison benchmarks (Agno, LangGraph, LlamaIndex, OpenAI, Pydantic-AI, CrewAI, etc.)
- Memory vs stateless agent performance
- RAG and API integration reliability metrics
- Token efficiency across frameworks
- Progressive example structures
- Subagent-driven development with two-stage review (spec compliance + code quality)
- Test-driven development enforcement for AI agents
- Skill triggering patterns and description optimization
- Fresh context per task to prevent pollution
- DOT flowcharts as executable specifications
- Context rot mitigation via subagent spawning
- XML-structured task specifications with explicit verification
- File-based state management (STATE.md, ROADMAP.md patterns)
- Parallel execution waves with dependency ordering
- Atomic git commits per completed task
- Model profile configuration (quality/balanced/budget)
- Orchestrator-worker separation pattern
- Spec-driven development with plan-verify loops
- Hot Memory pipeline (stash, friction analysis, remember consolidation)
- Session friction analysis with 14 weighted behavioral signals
- Multi-tool installer with format translation across 4 AI coding tools
- Auto-triggering skills for TDD enforcement and verification
- Intent-based agent routing with lazy frontmatter discovery
- ReAct (Reasoning + Acting) step loop with `think()` / `act()` separation and state machine (`IDLE`/`RUNNING`/`FINISHED`/`ERROR`)
- Callable service interface (`run_agent(task_name, prompt)`) for embedding agent logic in upstream applications
- Multi-server MCP aggregation via simultaneous stdio (subprocess) and SSE (HTTP) transports
- Tool schema refresh every N steps to handle dynamic MCP server state changes mid-task
- Token budget enforcement via `TokenLimitExceeded` before context overflow; tiktoken-based counting with image tile estimation
- Step-level `Record` persistence (thought + action + result + token_usage) as JSON + auto-generated HTML visualization report
- Duplicate-response detection (`duplicate_threshold`) preventing infinite agent loops
- TOML-based per-model LLM config for switching Claude models (opus/sonnet/haiku) per agent role without code changes
- Docker-first SSH-accessible sandbox for shell execution isolation

---

### 6. Agent Infrastructure

**Location**: [./agent-infrastructure/](./agent-infrastructure/)

Infrastructure tools and platforms for deploying, orchestrating, and managing agentic applications at scale.

| Document                                    | Description                                                                                                     | Last Updated |
| ------------------------------------------- | --------------------------------------------------------------------------------------------------------------- | ------------ |
| [fly-io.md](./agent-infrastructure/fly-io.md)     | Fly.io - cloud platform running apps in Firecracker microVMs across 18 regions; Sprites for AI agent sandboxes, first-class MCP deployment, Machines API for programmatic VM orchestration | 2026-02-23   |
| [kernel-sh.md](./agent-infrastructure/kernel-sh.md) | Kernel - browsers-as-a-service API with isolated VM-per-browser Chrome, 72h sessions, Playwright CDP passthrough, MCP server, and Browser Pools ($22M, 670 stars) | 2026-02-22   |
| [plano.md](./agent-infrastructure/plano.md)       | AI-native proxy and data plane built on Envoy - handles orchestration, model routing, observability, guardrails | 2026-01-26   |
| [tinyfish.md](./agent-infrastructure/tinyfish.md) | TinyFish - serverless web agent API for 1,000 parallel agentic ops, AgentQL MCP server, all-in pricing at $0.04/op (148 stars) | 2026-02-23   |
| [picoclaw.md](./agent-infrastructure/picoclaw.md) | PicoClaw - Go AI assistant by Sipeed, <10MB RAM, <1s startup, 6 messaging channels, runs on $10 RISC-V hardware, AI-bootstrapped (18.1K stars) | 2026-02-23   |
| [pinchtab.md](./agent-infrastructure/pinchtab.md) | PinchTab — 12MB Go binary HTTP server for AI agent browser control via a11y tree snapshots (~800 tokens/page, 5-13x cheaper than screenshots), multi-instance Chrome orchestration with isolated profiles, stealth injection (2.3K stars, MIT) | 2026-03-01   |
| [zeroclaw.md](./agent-infrastructure/zeroclaw.md) | Rust autonomous AI assistant — sub-5MB RAM, 28+ AI providers, 15+ channels, trait-driven swappable subsystems (14.9K stars) | 2026-02-19   |

**Key Topics**:

- Inner loop (agent logic) vs outer loop (orchestration) separation
- Declarative YAML-based agent routing configuration
- Purpose-built routing models (Plano-Orchestrator 4B)
- Unified LLM gateway with provider abstraction
- Zero-code OpenTelemetry tracing ("Agentic Signals")
- Filter chains for guardrails and moderation
- Prompt targets for deterministic API calls
- Sub-5MB RAM single-binary Rust AI agents for edge/embedded deployment
- Trait-driven swappable subsystems (Provider, Channel, Memory, Tool, Tunnel)
- SQLite hybrid search (FTS5 + cosine vector) with no external vector DB dependency
- Deny-by-default channel allowlists (empty = deny all; `"*"` = explicit open)
- SKILL.md + TOML manifest skill system (structural parallel to Claude Code skills)
- HEARTBEAT.md periodic task engine for proactive agent activation
- OpenAI Codex OAuth and Claude Code auth integration with encrypted profile store
- 6-digit one-time pairing code security with bearer token webhooks
- Docker runtime sandboxing for tool execution isolation
- Browsers-as-a-service with isolated VM-per-browser Chrome instances (no shared containers)
- CDP passthrough enabling drop-in Playwright/Puppeteer compatibility without code changes
- Browser Pools for pre-warming Chrome instances eliminating cold start latency
- Persistent Profiles for cross-session cookie/localStorage/auth state replay
- 72-hour session limits enabling human-in-the-loop pause-and-resume workflows
- Managed Auth credential vault for agent-driven OAuth and form-fill automation
- Web Bot Auth cryptographic request signing for improved bot-detection pass-through (10-20%)
- Per-second billing with idle time exclusion for cost-efficient automation
- MCP server integration (`onkernel/kernel-mcp-server`, MIT) for Claude Code browser tool access
- Playwright code execution inside VM for zero-CDP-round-trip complex interactions
- Batch action dispatch reducing network round-trips in tight automation loops
- Serverless agentic web automation with 1,000 simultaneous parallel operations
- All-in cost model: browser + proxy + LLM inference + anti-bot = single per-step price ($0.04/op)
- Goal-oriented natural language extraction without XPath/CSS selectors
- SSE streaming pattern for real-time agent task progress (no polling)
- AgentQL MCP server (`extract-web-data` tool) for Claude Code structured web data access
- Stealth browser profiles and geo-targeted residential proxies included by default
- Live data extraction from authenticated, form-gated, and JavaScript-heavy sites
- Accessibility tree (a11y) snapshots as token-efficient page representation (~800 tokens vs 5,000-13,000 for screenshots)
- Stable element ref caching (e0, e1...) avoiding redundant tree traversal on action calls
- Multi-instance Chrome orchestration with per-instance isolated profiles and auth state
- Stealth injection at CDP level: `navigator.webdriver` patching, Bezier mouse curves, keystroke timing simulation
- Prescriptive agent system prompts reducing token use by 14x for repetitive browser tasks
- Self-hosted 12MB Go binary with zero external dependencies; remote Chrome mode via `CDP_URL`
- Lazy Chrome initialization: Chrome process starts on first HTTP request, not at instance creation

---

### 7. API Frameworks

**Location**: [./api-frameworks/](./api-frameworks/)

High-performance API frameworks for building backend services, tool endpoints, and MCP server foundations.

| Document                                   | Description                                                                                               | Last Updated |
| ------------------------------------------ | --------------------------------------------------------------------------------------------------------- | ------------ |
| [fastapi.md](./api-frameworks/fastapi.md)  | Modern Python web framework with Pydantic validation, automatic OpenAPI docs, async support (95K+ stars)  | 2026-02-05   |
| [motia.md](./api-frameworks/motia.md)      | Motia - unified backend framework replacing APIs, queues, workflows, and AI agents with one Step primitive (15K+ stars) | 2026-02-23   |
| [pocketbase.md](./api-frameworks/pocketbase.md) | PocketBase - open-source Go backend in 1 file: embedded SQLite, realtime subscriptions, auth (password/OTP/OAuth2/MFA), file storage, admin dashboard (56K+ stars) | 2026-02-23   |
| [tornado.md](./api-frameworks/tornado.md)  | Python web framework and async networking library for WebSockets and long-polling (22K+ stars, 95M+ downloads/month) | 2026-02-05   |
| [modelence.md](./api-frameworks/modelence.md) | Modelence - AI-native TypeScript/Node.js backend framework with MongoDB, auth, real-time stores, WebSockets, observability, cron, rate limiting, and managed cloud deploy (YC-backed, Apache 2.0) | 2026-03-04   |

**Key Topics**:

- Python type hint-based API development
- Automatic OpenAPI/Swagger documentation generation
- Pydantic v2 data validation and serialization
- Async/await native support with Starlette ASGI
- Dependency injection patterns
- OAuth2/JWT security utilities
- FastMCP foundation for MCP servers
- Ray Serve integration for model serving
- WebSocket support for real-time communication
- Non-blocking network I/O for C10K concurrent connections
- Long polling and real-time streaming support
- Single-threaded event loop with asyncio integration
- Class-based request handlers with HTTP method dispatching
- WebSocket server/client with ping/pong and compression
- Built-in template engine with inheritance and escaping
- Jupyter notebook server foundation
- run_in_executor bridge for blocking operations
- Unified backend framework via single Step primitive (config + handler)
- Step trigger types: http, queue, cron, state, stream — all same pattern
- Auto-discovery of Step files by filename convention (`*.step.ts`, `*_step.py`)
- Emit/subscribe event-driven wiring between Steps without manual glue code
- Built-in key-value state management shared across flow Steps
- Multi-language Steps in one project (TypeScript, JavaScript, Python, Ruby)
- Visual Workbench debugger with flow diagrams, traces, and state inspection
- AGENTS.md bundled in scaffolded projects for AI coding tool context
- Core runtime rewritten in Rust for performance
- Single-binary Go backend (no Docker, no runtime) with embedded SQLite, auth, files, realtime, and admin UI
- SSE-based realtime subscriptions on any collection without external broker (no Redis/Pusher)
- 3 collection types: Base (app data), View (read-only SQL SELECT), Auth (users with built-in auth fields)
- Declarative access control via filter rule DSL (`@request.auth.id`, `&&`/`||`, nested relation traversal)
- Stateless JWT auth (no server-side sessions); password, OTP, OAuth2 (30+ providers), MFA
- File field type with local disk or S3 backend; single-call storage config switch
- Go hook system (`app.On*()`) for lifecycle event interception without forking core
- JS VM plugin (Goja) for extending PocketBase with JavaScript without recompiling
- `CGO_ENABLED=0 go build` produces statically linked binary for any target platform

---

### 8. Developer Tools

**Location**: [./developer-tools/](./developer-tools/)

Developer productivity tools and workflow automation for software engineering with AI assistance.

| Document                                               | Description                                                                                                                  | Last Updated |
| ------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------- | ------------ |
| [biome.md](./developer-tools/biome.md)                 | Biome - Rust-based web toolchain with formatter (97% Prettier compat, ~35× faster), linter (450+ rules), import organizer, and v2 type-aware linting without TypeScript compiler (23.8K stars) | 2026-02-23   |
| [byobu.md](./developer-tools/byobu.md)                 | Byobu v6.14 — enhanced terminal multiplexer wrapper for tmux/screen with unified F-key layer, 40+ status bar plugins, XDG config layering, and backend switching (1.5K stars) | 2026-03-01   |
| [animejs.md](./developer-tools/animejs.md)             | Lightweight JavaScript animation engine with declarative API, timelines, staggering, and 30+ easing functions                        | 2026-01-31   |
| [claude-conductor.md](./developer-tools/claude-conductor.md)       | Claude Conductor - Context-Driven Development plugin with 9 commands, skill ecosystem, pattern reference layer, and quality intelligence | 2026-02-17   |
| [claude-openocd-spi-dump.md](./developer-tools/claude-openocd-spi-dump.md) | Claude Code plugin for SPI flash dumping via OpenOCD with RAM-resident code and MCU register maps for 6 chip families | 2026-02-20   |
| [claude-pilot.md](./developer-tools/claude-pilot.md) | Claude Pilot — quality-enforcement layer for Claude Code CLI with 15 lifecycle hooks, TDD enforcement, /spec worktree workflow, and cross-session persistent memory (1,390 stars) | 2026-02-23   |
| [claude-quickstarts.md](./developer-tools/claude-quickstarts.md)   | Official Anthropic quickstart projects — computer use (Docker+VNC), browser automation, multi-session coding agent, minimal agent loop reference (<300 lines), Next.js UIs (14.7K stars) | 2026-02-19   |
| [copier-astral.md](./developer-tools/copier-astral.md) | Copier template for Python projects with Astral toolchain (uv, ruff, ty), pytest, MkDocs, Typer, GitHub Actions, Docker              | 2026-01-31   |
| [git-cliff.md](./developer-tools/git-cliff.md)         | Customizable changelog generator using conventional commits and regex parsers with GitHub/GitLab remote integration                  | 2026-01-26   |
| [github-cli.md](./developer-tools/github-cli.md)       | GitHub CLI (gh) - official CLI for PRs, issues, workflows, extensions with scriptable API access (37.8K stars)                        | 2026-02-20   |
| [google-ai-studio.md](./developer-tools/google-ai-studio.md) | Google AI Studio — free browser-based IDE and playground for Gemini API with 1M-token context, OpenAI compatibility, and built-in Google Search grounding | 2026-02-23   |
| [grepai.md](./developer-tools/grepai.md)               | Semantic code search and call graph analysis for AI agents with MCP server, 12-language trace, and embedding-based search (1.2K stars) | 2026-02-13   |
| [jina-reader.md](./developer-tools/jina-reader.md)     | Jina Reader - Apache 2.0 URL-to-Markdown API (`r.jina.ai` prefix), full SPA/PDF support via Puppeteer, web search grounding via `s.jina.ai` (~9.8K stars) | 2026-02-23   |
| [jirajs.md](./developer-tools/jirajs.md)               | jira.js - TypeScript Jira API client for Cloud, Server, and Data Center with full REST API coverage                                   | 2026-02-20   |
| [jscpd.md](./developer-tools/jscpd.md)                 | Copy/paste detector for 150+ programming languages using Rabin-Karp algorithm with CI/CD integration                                 | 2026-01-31   |
| [libtmux.md](./developer-tools/libtmux.md)             | libtmux v0.53.1 — typed Python API for tmux with Server/Session/Window/Pane dataclasses, send_keys/capture_pane methods, QueryList ORM filtering, and pytest fixtures (1.1K stars, MIT) | 2026-03-01   |
| [loguru.md](./developer-tools/loguru.md)               | Loguru - zero-config Python logging with rotation, structured output, exception catching, and contextvars support (23K+ stars)        | 2026-02-09   |
| [kythe.md](./developer-tools/kythe.md)                 | Kythe - Google's language-agnostic code intelligence platform with graph-based semantic indexing (2.1K stars)                          | 2026-02-20   |
| [lopaka.md](./developer-tools/lopaka.md)               | Lopaka - web-based graphics editor for embedded displays with multi-library C/C++ code generation (1.2K stars)                        | 2026-02-20   |
| [niteni.md](./developer-tools/niteni.md)               | Niteni - AI-powered code review for GitLab CI using Gemini with inline diff comments and severity classification                     | 2026-02-15   |
| [off-grid-mobile.md](./developer-tools/off-grid-mobile.md) | Off Grid Mobile — privacy-first offline AI suite for iOS/Android running llama.cpp, Stable Diffusion, and Whisper on-device with SoC constraint enforcement and tool calling (696 stars) | 2026-02-28   |
| [orbstack.md](./developer-tools/orbstack.md)           | Fast, lightweight Docker Desktop and Linux VM alternative for macOS with 2-second startup and dynamic memory                         | 2026-01-31   |
| [paperdraw.md](./developer-tools/paperdraw.md)         | PaperDraw - browser-based distributed systems simulator with 20+ backend components, chaos injection, and real-time metrics (Flutter web) | 2026-02-23   |
| [devenv.md](./developer-tools/devenv.md)               | devenv — Nix-backed declarative dev environment CLI (v1.11.2); typed modules for languages, services, tasks, git hooks; 30+ built-in service modules without Docker; sub-100ms activation; generates `.devcontainer.json` from same config (6.3K stars) | 2026-02-26   |
| [dtach.md](./developer-tools/dtach.md)                 | dtach — minimal C program emulating screen's detach feature; raw PTY passthrough via Unix-domain sockets, `-p` mode for scripted input injection, ~1,000 lines of C, GPL-2.0 (619 stars) | 2026-03-01   |
| [portless.md](./developer-tools/portless.md)           | Portless — replaces numeric port numbers with stable named `.localhost` URLs for local dev servers; targets both humans and AI coding agents; zero external proxy deps, HTTP/2 + TLS, loop detection (2,569 stars) | 2026-02-26   |
| [scrapling.md](./developer-tools/scrapling.md)         | Scrapling — adaptive Python web scraping framework with anti-bot bypass (Cloudflare Turnstile), auto-relocating element selectors, built-in MCP server for Claude agents, 784x faster than BeautifulSoup4 (15K+ stars) | 2026-02-26   |
| [surf-cli.md](./developer-tools/surf-cli.md)           | surf-cli — zero-config CLI for AI agent Chrome control via extension + Unix socket bridge; 50+ commands covering navigation, page reading, screenshots, network capture, and keyless AI model querying | 2026-02-26   |
| [tabz-browser-console-forwarder.md](./developer-tools/tabz-browser-console-forwarder.md) | Tabz — browser console to terminal forwarder; intercepts console.* methods, batches POSTs to backend, prefixes with [Browser:source:line], visible in tmux for AI agent debugging (MIT) | 2026-03-01   |
| [piebald.md](./developer-tools/piebald.md)             | Piebald - cross-platform agentic AI desktop client with parallel subagents, persistent sessions, OAuth AI subscriptions, and HTTP traffic inspector (Free + Pro) | 2026-02-23   |
| [pixel-agents.md](./developer-tools/pixel-agents.md)   | Pixel Agents — VS Code extension (v1.0.2) rendering Claude Code terminals as animated pixel-art characters in a virtual office; parses JSONL transcripts, visualizes sub-agent hierarchies, React 19 + Canvas 2D with BFS pathfinding (3K+ stars, MIT) | 2026-03-05   |
| [psmux.md](./developer-tools/psmux.md)                 | psmux — native Windows tmux replacement in Rust (v0.4.7); 76 commands, `.tmux.conf` compat, ConPTY, drop-in `tmux` alias, plugin ecosystem (269 stars) | 2026-03-01   |
| [shpool.md](./developer-tools/shpool.md)               | shpool — Rust shell session pool daemon (v0.9.3); raw PTY passthrough with VT100 reattach replay, autodaemonization, no multiplexing overhead (1.7K stars) | 2026-03-01   |
| [repomix.md](./developer-tools/repomix.md)             | Pack codebase into single AI-friendly file with token counting, Tree-sitter compression, MCP server, and Claude Code plugins         | 2026-01-31   |
| [traycer.md](./developer-tools/traycer.md)             | Traycer - spec-driven AI development orchestrator with multi-model ensemble, plan-execute-verify loop, and 6 agent handoffs          | 2026-02-15   |
| [tmuxp.md](./developer-tools/tmuxp.md)                 | tmuxp v1.64.0 — Python tmux session manager with YAML/JSON workspace configs, plugin lifecycle hooks, freeze/replay, and headless-safe WorkspaceBuilder API (4.4K stars, MIT) | 2026-03-01   |
| [using-tmux-with-claude-code.md](./developer-tools/using-tmux-with-claude-code.md) | Using tmux with Claude Code — practical guide for copy-mode scrollback, 10K-line buffer capture, control-key passthrough, and multi-pane agent orchestration (hboon.com, 2025-11-28) | 2026-03-01   |
| [vert.md](./developer-tools/vert.md)                   | VERT - WebAssembly-based file converter for 250+ formats with client-side processing and self-hostable video daemon (13K+ stars)     | 2026-02-08   |
| [everything-claude-code.md](./developer-tools/everything-claude-code.md) | everything-claude-code — largest community Claude Code config repo (52K stars, 39 days old); v1.6.0 ships 13 agents, 48+ skills, 31+ commands, 978 tests, 102 AgentShield security rules; continuous learning v2 instinct system with `/evolve`; Cerebral Valley x Anthropic hackathon winner | 2026-02-26   |
| [vercel-chatbot.md](./developer-tools/vercel-chatbot.md) | Vercel Chatbot — production-ready Next.js 16 chatbot template (v3.1.0) using AI SDK v6 with resumable streaming, Claude Haiku 4.5 as artifact model, ProseMirror/CodeMirror 6 artifact system, and `extractReasoningMiddleware` for chain-of-thought display (19.7K stars) | 2026-02-26   |
| [voxcii.md](./developer-tools/voxcii.md)               | voxcii — terminal-based ASCII 3D model viewer (C++17) rendering OBJ/STL files with Z-buffer depth sorting, surface-normal shading mapped to 12-char ASCII ramp, interactive rotation/zoom, and ANSI color via ncurses (81 stars) | 2026-02-28   |
| [yume.md](./developer-tools/yume.md)                   | Yume - native desktop GUI for Claude Code CLI with parallel agents, crash recovery, and multi-provider model support (Tauri + Rust)  | 2026-02-15   |
| [claudebin.md](./developer-tools/claudebin.md)         | Claudebin - minimalistic tool for publishing and sharing Claude Code sessions via /claudebin:share; generates shareable URLs with syntax highlighting and full conversation threads (MIT) | 2026-03-04   |
| [crawler-sh.md](./developer-tools/crawler-sh.md)       | Crawler.sh - local-first website crawler and SEO/AEO analysis CLI + desktop app; 16 automated SEO checks/page, Markdown extraction, NDJSON/JSON/Sitemap/CSV export, no account required (v0.2.3, proprietary) | 2026-03-04   |
| [superset-sh.md](./developer-tools/superset-sh.md)     | Superset - macOS Electron app running 10+ parallel AI coding agents via Git worktrees; agent-agnostic (Claude Code, Codex CLI, Cursor, Gemini CLI, OpenCode); branch-isolated conflict-free execution (v1.0.5, Apache 2.0) | 2026-03-04   |
| [capacitorjs.md](./developer-tools/capacitorjs.md)     | Capacitor v8.1.0 — cross-platform native runtime bridging web apps to iOS, Android, and PWA via WebView + native plugin layer; 37+ official plugins, source-artifact native projects, TypeScript async API (15.2K stars, MIT) | 2026-03-05   |

**Key Topics**:

- Declarative animation APIs for frontend code generation
- Composable building blocks pattern (animate, stagger, timeline)
- Conventional commits specification and parsing
- Customizable Tera templates for changelog output
- GitHub/GitLab/Gitea/Bitbucket remote metadata integration
- Monorepo support with path-based filtering
- Prepend mode for incremental changelog updates
- Semantic versioning correlation (feat→minor, fix→patch)
- Configuration hierarchy (global → project → environment)
- Copy/paste detection with Rabin-Karp algorithm
- Token-based code analysis across 150+ languages
- CI/CD integration with threshold-based quality gates
- SARIF output for GitHub Security tab integration
- Git blame integration for duplication attribution
- Docker Desktop alternative with native macOS performance
- Lightweight Linux VM architecture (similar to WSL 2)
- Dynamic memory allocation (returns unused to macOS)
- Kubernetes single-node cluster for local development
- Multi-distro Linux machine support (15 distributions)
- Zero-config container domains (\*.orb.local)
- Headless/CLI mode for CI automation
- Codebase-to-AI-file packaging for LLM consumption
- Token counting with Tree-sitter code compression (~70% reduction)
- Security scanning via Secretlint integration
- MCP server mode with 7 tools for AI assistant integration
- Claude Code plugins (repomix-mcp, repomix-commands, repomix-explorer)
- Agent Skills generation from local and remote repositories
- Multiple output formats (XML optimized for Claude, Markdown, JSON, Plain)
- Remote repository processing without local cloning
- Split output for large codebases exceeding context limits
- Copier template engine for Python project scaffolding
- Astral toolchain integration (uv, ruff, ty) for modern Python development
- Feature toggles for conditional file generation
- Copier update mechanism for propagating template improvements
- Hatch envs for multi-Python version matrix testing
- Makefile abstraction for complex uv/hatch commands
- Semantic code search via embedding-based cosine similarity
- Call graph tracing (callers, callees, dependency graphs) across 12 languages
- MCP server integration for AI agent semantic search
- Workspace-aware cross-project search and tracing
- Zero-config Python logging with automatic file rotation and compression
- Structured logging with JSON serialization and contextvars context injection
- Exception catching decorators with variable-value tracebacks
- AI-powered GitLab CI code review with inline diff comments
- Severity-classified review findings (CRITICAL, HIGH, MEDIUM, LOW)
- GitLab suggestion blocks for one-click fix application
- Spec-driven development with plan-execute-verify loop
- Multi-model ensemble architecture (different models for different tasks)
- Artifact decomposition hierarchy (Artifact, Epic, Ticket, Phase)
- WebAssembly file conversion in browser (FFmpeg, ImageMagick, Pandoc)
- Privacy-first local processing with self-hostable server fallback
- Native desktop GUI wrapping CLI with zero-flicker rendering
- Specialist agent roles (Architect, Explorer, Implementer, Guardian)
- Auto-compaction at 75% context window capacity
- CLI process spawning for full ecosystem compatibility
- Context-Driven Development (CDD) lifecycle: Context -> Spec & Plan -> Implement
- Skill activation scoring with weighted keyword/file/language/framework signals
- SKILL-SUMMARY lazy loading for 74% token reduction
- Universal File Resolution Protocol (UFRP) via index.md navigation files
- Dual-format documentation (AI Quick Reference + Human Documentation)
- Anti-pattern detection (god objects, mutable defaults, deep nesting, magic numbers)
- Architecture Decision Record logging per feature track
- Parallel sub-agents for code quality, security, and coverage analysis
- Two-agent multi-session orchestration pattern (initializer + coding agent; progress via feature_list.json + git)
- Minimal agent loop reference (<300 lines): raw Claude API tool loop with local tools + MCP server integration
- `computer_use_20251124` tool version with zoom actions and `str_replace_based_edit_tool` (authoritative beta reference)
- Security hook pattern: bash command allowlist as pre-execution gate (analogous to Claude Code PreToolUse hooks)
- Monorepo CLAUDE.md pattern: per-project headings with Setup, Testing, Code Style in single root file
- Feature list as session handoff: JSON file tracking cross-session progress without external state store
- Docker as isolation boundary for computer use agents (filesystem + network scoping)
- Claude Agent SDK (`claude-code-sdk`) programmatic session spawning reference
- AWS Bedrock and Google Vertex backends supported alongside Anthropic API for computer use
- Visual-to-code editor for embedded displays (TFT_eSPI, U8g2, AdafruitGFX, FlipperZero)
- Multi-library code generation from single visual interface
- Bitmap-to-C-array conversion for embedded graphics
- AI-assisted hardware reverse engineering via Claude Code plugin
- RAM-resident code loading for SPI flash dumping without dedicated programmers
- MCU register maps for 6 chip families (STM32, SAM, nRF, RP2040, ESP32, GD32)
- Progressive multi-phase guided workflows for complex hardware tasks
- Domain knowledge capture (register maps, troubleshooting tables, protocol details) for AI retrieval
- GitHub CLI (gh) for scriptable PR, issue, workflow, and API automation
- Extension ecosystem supporting any language with marketplace distribution
- `gh api` for REST/GraphQL access with pagination and JSON filtering
- AI agent integration patterns (automated PR creation, CI debugging, issue management)
- TypeScript Jira API client with full REST coverage across Cloud/Server/Data Center
- Agile board, sprint, backlog, and issue management automation
- Graph-based semantic code indexing with hub-and-spoke architecture (Kythe)
- Language-agnostic cross-reference and call graph generation
- VName-based extensible schema for custom semantic information
- Browser-based distributed systems simulation with drag-and-drop component canvas (PaperDraw)
- Chaos engineering playbook: traffic spike, cache crash, component failure, latency injection
- Real-time per-node metrics (latency, throughput, error rates, cache-hit ratios) in simulation
- Failure-first architecture thinking: discover failure modes before writing code
- LLM gateway and vector database as first-class system design components
- Cross-platform agentic AI desktop with native Windows support (no WSL), OAuth AI subscriptions, and persistent sessions (Piebald)
- Profile-based MCP tool isolation: named profiles with specific tool subsets switchable per chat
- Reboot-persistent tool approval gates: agentic loop state preserved across machine reboots
- Multi-provider OAuth bridging: consumer subscriptions (Claude Max, ChatGPT Plus, Google AI) without API keys
- HTTP wire-level traffic inspection for debugging LLM request/response cycles and SSE streams
- AgentSkills.io skill loading in GUI context: first-class compatibility with agentskills.io format
- Biome: single-binary Rust toolchain (format + lint + import organize) replacing ESLint + Prettier
- 97% Prettier formatting compatibility with ~35× speed advantage
- 450+ lint rules from ESLint, typescript-eslint, and other sources with safe-fix support
- v2 type inference engine: type-aware linting without TypeScript compiler (`tsc`)
- Multi-file project scanner for monorepo-aware type analysis (opt-in, no default perf impact)
- Nested biome.json configuration for per-package monorepo overrides
- `biome ci` command for zero-write CI enforcement with non-zero exit on violations
- Standalone binary deployment without Node.js
- First-party LSP editor extensions (VS Code, IntelliJ, Zed)

---

### 9. Documentation Tools

**Location**: [./documentation-tools/](./documentation-tools/)

Architecture documentation, living documentation, and code-to-architecture extraction tools.

| Document                                                          | Description                                                                                                                | Last Updated |
| ----------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- | ------------ |
| [living-architecture.md](./documentation-tools/living-architecture.md) | Living Architecture (Rivière) - operational flow architecture extraction from code with AI-assisted workflows (79 stars) | 2026-02-20   |

**Key Topics**:

- Operational flow-based architecture modeling (UI → API → UseCase → DomainOp → Event → EventHandler)
- Language-agnostic JSON schema (Rivière) for polyglot system documentation
- AI-assisted architecture extraction via CLAUDE.md integration
- Interactive visualization with click-through navigation to source code
- Living documentation that stays synchronized with codebase
- Domain terminology management and cross-domain analysis
- NX monorepo architecture with strict quality gates (100% test coverage)

---

### 10. Coding Agents

**Location**: [./coding-agents/](./coding-agents/)

Autonomous AI coding agent platforms and SDKs for building software development agents.

| Document                                     | Description                                                                                       | Last Updated |
| -------------------------------------------- | ------------------------------------------------------------------------------------------------- | ------------ |
| [accomplish.md](./coding-agents/accomplish.md) | Accomplish - local-first AI desktop agent (Electron + React) with MCP tools, 15 providers, permission-gated execution, CompletionEnforcer pattern (MIT) | 2026-02-27   |
| [cline.md](./coding-agents/cline.md)         | Cline - open-source autonomous coding agent (VS Code + CLI) with human-in-the-loop approvals, multi-provider LLM support, and enterprise governance (Apache-2.0) | 2026-02-23   |
| [openai-codex-cli.md](./coding-agents/openai-codex-cli.md) | OpenAI Codex CLI v0.106.0 — Rust-based coding agent with OS sandbox (Landlock/Seatbelt), dual MCP role (client+server), Starlark exec policy, AGENTS.md/Skills system, response_id bookmarking for conversation forking (62.5K stars, Apache-2.0) | 2026-03-01   |
| [openhands.md](./coding-agents/openhands.md) | OpenHands - open platform for cloud coding agents with 77.6% SWE-bench score, SDK, CLI, and cloud | 2026-01-26   |
| [pilot.md](./coding-agents/pilot.md)         | Pilot - autonomous development pipeline wrapping Claude Code CLI with ticket-to-PR automation (BSL 1.1) | 2026-02-19   |
| [tembo.md](./coding-agents/tembo.md)         | Tembo - cloud AI coding agent orchestration platform (Claude Code, Codex, Cursor, Amp, OpenCode) with multi-repo PRs, Sentry/Linear/Jira/Slack integrations, and event-driven automations | 2026-02-23   |
| [openai-symphony.md](./coding-agents/openai-symphony.md) | OpenAI Symphony — Elixir-based autonomous coding agent platform (Draft v1 spec) with 8-component architecture (Orchestrator, Workspace Manager, Agent Runner, etc.), issue-tracker-driven workflows, Codex stdio JSON-RPC protocol, and workspace sandboxing invariants (5.5K stars, Apache-2.0) | 2026-03-06   |

**Key Topics**:

- Model-agnostic agent architecture
- Python SDK for agent composition
- SWE-bench benchmark performance (77.6% verified)
- Inference-time scaling with critic models
- Docker/Kubernetes sandboxed execution
- REST-based agent server for scaling
- GitHub, GitLab, Slack, Jira integrations
- Open-source alternatives to proprietary coding agents
- Autonomous ticket-to-PR pipeline wrapping Claude Code CLI
- Multi-model routing (Haiku for triage, Opus for implementation)
- Three autopilot modes (dev/stage/prod) with trust escalation
- Epic decomposition with Haiku pre-planning before heavy-model execution
- GitHub/Linear/Jira/Asana ticket ingestion
- BSL 1.1 licensing with Apache 2.0 conversion after 4 years
- Human-in-the-loop approval gates for every agent action
- Plan & Act mode separation for safer task execution
- Multi-provider LLM support with bring-your-own-key model
- MCP extensibility with custom tools and data sources
- VS Code extension + CLI for headless/CI-CD workflows
- Cloud-hosted agent orchestration with event-driven automations
- Multi-repository PR generation in a single task
- Agent-agnostic backend (Claude Code, Codex, Cursor, Amp, OpenCode)
- Sentry integration for automatic error-to-PR workflows

---

### 11. Data Infrastructure

**Location**: [./data-infrastructure/](./data-infrastructure/)

Real-time data platforms and analytics infrastructure for powering AI applications and agentic workflows.

| Document                                                 | Description                                                                                                  | Last Updated |
| -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ | ------------ |
| [dolt.md](./data-infrastructure/dolt.md)                 | Dolt v1.83.0 — MySQL wire-protocol compatible version-controlled SQL database with Git semantics (branch, merge, diff, clone via SQL stored procedures), Prolly Tree O(d) diffs, and agentic memory via Beads (20.3K stars, Apache 2.0) | 2026-03-01   |
| [motherduck.md](./data-infrastructure/motherduck.md)     | Serverless cloud DuckDB warehouse with Dual Execution engine and native MCP integration for AI agents        | 2026-02-23   |
| [tinybird.md](./data-infrastructure/tinybird.md)         | Managed ClickHouse platform for real-time analytics APIs with native MCP server and analytics agents support | 2026-01-31   |

**Key Topics**:

- Serverless cloud DuckDB with Dual Execution (local + cloud hybrid query routing)
- Native MCP server integration for AI agents and Claude Code
- Managed ClickHouse with zero maintenance overhead
- SQL-to-API instant endpoint generation
- Incremental materialized views for 100x query speedup
- Events API for 1K+ RPS JSON streaming
- Native MCP server integration for AI agents
- Analytics Agents templates and best practices
- Data-as-code with Git-based version control
- Branch-based testing with isolated environments

---

### 12. Task Management

**Location**: [./task-management/](./task-management/)

AI-powered task management systems designed for AI-driven development workflows.

| Document                                                         | Description                                                                                     | Last Updated |
| ---------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- | ------------ |
| [claude-task-master.md](./task-management/claude-task-master.md) | Task Master - PRD parsing, task tracking, and MCP integration for Cursor, Windsurf, Claude Code | 2026-01-26   |
| [vibe-kanban.md](./task-management/vibe-kanban.md)               | Vibe Kanban - Kanban-style orchestration UI for parallel AI coding agent sessions with git worktree isolation | 2026-03-03   |

**Key Topics**:

- PRD-to-task automated decomposition
- MCP server with 36 tools (selective loading for context optimization)
- Multi-model architecture (main, research, fallback)
- Model-agnostic support (10+ AI providers)
- IDE integration (Cursor, Windsurf, VS Code, Q Developer)
- Persistent task state with dependencies
- Claude Code plugin patterns

---

### 13. Context Management

**Location**: [./context-management/](./context-management/)

Memory systems, context window optimization tools, and RAG solutions for maintaining state across AI sessions.

| Document                                                  | Description                                                                                                                    | Last Updated |
| --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ | ------------ |
| [claude-mem.md](./context-management/claude-mem.md)       | Claude-Mem - persistent memory compression plugin for Claude Code with 4 MCP tools and progressive disclosure                  | 2026-01-31   |
| [jina-ai.md](./context-management/jina-ai.md)             | Jina AI - search foundation platform with Reader API (URL→Markdown), multimodal embeddings, rerankers, and DeepSearch (acquired by Elastic 2025) | 2026-02-23   |
| [local-memory.md](./context-management/local-memory.md)   | Local Memory - persistent memory infrastructure with MCP, REST API, CLI, embedded Qdrant, and knowledge evolution (L0-L3)      | 2026-02-07   |
| [sourcesyncai.md](./context-management/sourcesyncai.md)   | SourceSync.ai - managed RAG platform with 15+ auto-syncing connectors, hybrid search, BYOC storage, and MCP integration       | 2026-02-23   |
| [straion.md](./context-management/straion.md)             | Straion - SaaS rules-management platform that dynamically injects relevant engineering standards into AI coding agents (Claude Code, Cursor, Copilot) at task time; validates agent plans against rules before code is written | 2026-03-04   |

**Key Topics**:

- URL-to-Markdown extraction via Reader API (r.jina.ai prefix pattern)
- Multimodal and multilingual embeddings for semantic search
- Two-stage retrieval: embed → shortlist → rerank pipeline
- Persistent memory across Claude Code sessions
- Progressive disclosure pattern (3-layer workflow for token efficiency)
- Lifecycle hooks architecture (SessionStart, PostToolUse, SessionEnd, etc.)
- Hybrid search (SQLite FTS5 + Chroma vector embeddings)
- MCP tools for memory search (search, timeline, get_observations)
- Privacy controls with `<private>` tags
- Web viewer UI for memory inspection
- Context injection strategies
- Four-level knowledge hierarchy (L0 Observations, L1 Learnings, L2 Patterns, L3 Schemas)
- Contradiction detection with five-layer heuristics
- Multi-provider AI backend with split embedding/chat providers
- Embedded Qdrant vector search with 10-57ms response times
- Agent attribution and hostname tracking for multi-device workflows
- Domain cascade resolution (explicit > config file > default)

---

### 14. Async Libraries

**Location**: [./async-libraries/](./async-libraries/)

Python async I/O libraries and concurrency frameworks for building concurrent applications.

| Document                               | Description                                                                                                              | Last Updated |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ | ------------ |
| [anyio.md](./async-libraries/anyio.md)     | AnyIO - backend-agnostic async concurrency library providing unified API across asyncio and Trio (426M downloads/month)  | 2026-02-04   |
| [asyncssh.md](./async-libraries/asyncssh.md) | asyncssh v2.22.0 — asyncio-native SSH client/server with reverse tunnels (`forward_remote_port`, `connect_reverse`), SFTP, jump-host chaining, and pure-Python key management (1.7K stars, EPL-2.0/GPL-2.0) | 2026-03-01   |
| [trio.md](./async-libraries/trio.md)       | Trio - structured concurrency async library for Python with nurseries, cancel scopes (7K+ stars, 218M downloads/month)   | 2026-02-04   |

**Key Topics**:

- Structured concurrency via nurseries (tasks complete within scope)
- Cancel scopes for unified timeout and cancellation handling
- Static checkpoint guarantees (predictable interleaving points)
- Natural exception propagation through nursery boundaries
- No callbacks, futures, or promises - pure async/await
- Composable timeouts with predictable nesting semantics
- Task completion guarantees preventing orphan operations
- anyio compatibility for asyncio/trio portability
- Backend-agnostic async API (asyncio + Trio unified)
- Level cancellation via cancel scopes (vs asyncio edge cancellation)
- Memory object streams with typed async communication
- Worker threads and process pools with capacity limiters
- Async file I/O and Path operations
- Task initialization with `TaskGroup.start()` readiness signaling

---

### 15. ML Infrastructure

**Location**: [./ml-infrastructure/](./ml-infrastructure/)

ML compute engines, model serving platforms, and distributed computing infrastructure for AI workloads.

| Document                           | Description                                                                                                | Last Updated |
| ---------------------------------- | ---------------------------------------------------------------------------------------------------------- | ------------ |
| [ray.md](./ml-infrastructure/ray.md) | Ray - AI compute engine for scaling Python/ML applications with LLM serving and MCP server deployment (41K+ stars) | 2026-02-05   |
| [microgpt-playground.md](./ml-infrastructure/microgpt-playground.md) | microgpt Playground - browser-native GPT training and inference demo, zero-dependency JavaScript port of Karpathy's microgpt.py (65 stars) | 2026-02-23   |

**Key Topics**:

- Distributed computing primitives (Tasks, Actors, Objects)
- Ray Serve for scalable model serving and LLM inference
- Native MCP server deployment (Streamable HTTP, STDIO conversion)
- Ray Data for streaming, distributed data processing
- Ray Train for distributed ML training (PyTorch, Transformers, XGBoost)
- Ray Tune for hyperparameter optimization at scale
- RLlib for reinforcement learning
- Kubernetes-native deployment with KubeRay
- GPU scheduling and placement groups
- Fault tolerance with lineage-based reconstruction
- vLLM integration for high-throughput LLM serving
- Zero-copy data sharing via plasma object store

---

### 16. Python Runtimes

**Location**: [./python-runtimes/](./python-runtimes/)

Alternative Python interpreters and runtime implementations for specialized use cases.

| Document                                   | Description                                                                                                         | Last Updated |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------- | ------------ |
| [rustpython.md](./python-runtimes/rustpython.md) | RustPython - Python 3 interpreter written in Rust with WASM support, JIT compiler, and Rust embedding (22K+ stars) | 2026-02-05   |

**Key Topics**:

- Python interpreter implementation in Rust
- WebAssembly (WASI) compilation for browser/portable execution
- Embedding Python scripting in Rust applications
- Experimental JIT compiler for native code generation
- Parser shared with Ruff linter (ruff_python_parser)
- CPython 3.14.0+ compatibility target
- Sandboxed code execution via WASM isolation
- Feature flag architecture for configurable builds
- pip and venv support for package management
- Cross-platform single-binary deployment

---

### 17. AI Observability

**Location**: [./ai-observability/](./ai-observability/)

AI-native observability platforms for monitoring, debugging, and optimizing LLM applications and agent systems.

| Document                                   | Description                                                                                                         | Last Updated |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------- | ------------ |
| [logfire.md](./ai-observability/logfire.md) | Pydantic Logfire - full-stack AI observability with OpenTelemetry, MCP server for SQL queries, token/cost tracking | 2026-02-05   |

**Key Topics**:

- Full-stack OpenTelemetry tracing (AI + backend combined)
- LLM conversation panels with tool call inspection
- Token tracking and cost monitoring across providers
- SQL-queryable telemetry (PostgreSQL-compatible syntax)
- MCP server for AI agents to query production data
- Native integrations: Pydantic AI, OpenAI, Anthropic, Claude Agent SDK, LangChain
- Streaming response debugging with chunk-level visibility
- Code-first evaluations via pydantic-evals (version-controlled, CI-integrated)
- Database/HTTP client/web framework instrumentation
- Real-time live view dashboard with natural language search

---

### 18. Rust-Python Bindings

**Location**: [./rust-python-bindings/](./rust-python-bindings/)

Rust-Python interoperability libraries for building high-performance Python extensions and embedding Python in Rust applications.

| Document                                   | Description                                                                                                         | Last Updated |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------- | ------------ |
| [pyo3.md](./rust-python-bindings/pyo3.md) | PyO3 - Rust bindings for Python with #[pyclass]/#[pyfunction] macros, maturin build tool, abi3 stable ABI (15K+ stars) | 2026-02-05   |

**Key Topics**:

- Native Python extension modules written in Rust
- Automatic type conversions via FromPyObject/IntoPy traits
- maturin for one-command wheel building and publishing
- abi3 stable ABI for single binary across Python versions
- GIL management with Python::with_gil and allow_threads
- Async support bridging Rust futures with Python asyncio
- Integration with chrono, serde, num-bigint, hashbrown, and more
- Embedding Python interpreter in Rust applications
- CPython 3.7+, PyPy 7.3+, GraalPy 25.0+ support
- Free-threaded Python 3.13t experimental support

---

### 19. AI Research Tools

**Location**: [./ai-research-tools/](./ai-research-tools/)

AI research newsletters, curated resource collections, and tools for staying current with AI development practices.

| Document                                                  | Description                                                                                                                    | Last Updated |
| --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ | ------------ |
| [the-unwind-ai.md](./ai-research-tools/the-unwind-ai.md) | The Unwind AI - AI builder newsletter with 740+ posts, companion awesome-llm-apps repo (95K+ stars, Apache 2.0)               | 2026-02-19   |

**Key Topics**:

- AI builder newsletter covering agents, RAG, and LLMs (~3 posts/week)
- Companion open-source repository with 500+ working Python AI agent examples
- Same-day analysis of model releases with practitioner perspective
- SOUL.md agent identity pattern coverage
- MCP ecosystem and Anthropic tooling coverage
- Multi-agent framework comparisons and implementation guides

---

### 20. AI Design Tools

**Location**: [./ai-design-tools/](./ai-design-tools/)

AI-powered visual creation platforms and design intelligence tools for video, image, audio, and UI/UX content generation.

| Document                                    | Description                                                                                                | Last Updated |
| ------------------------------------------- | ---------------------------------------------------------------------------------------------------------- | ------------ |
| [hedra.md](./ai-design-tools/hedra.md)      | Hedra - AI-powered visual creation platform for video, image, and audio with character animation            | 2026-02-20   |
| [jimeng.md](./ai-design-tools/jimeng.md)    | Jimeng AI (即梦AI) - ByteDance SeedDance 2.0 multimodal video/image generation with cinematic camera control | 2026-02-23   |
| [ui-ux-pro-max-skill.md](./ai-design-tools/ui-ux-pro-max-skill.md) | UI UX Pro Max - AI design skill injecting 67 styles, 96 palettes, 57 font pairings into 16 coding assistants via BM25+regex search (34.9K stars) | 2026-02-26   |
| [google-stitch.md](./ai-design-tools/google-stitch.md) | Google Stitch - AI-powered UI design tool generating app frontends (HTML/CSS, React) from text prompts or images using Gemini 2.5 models; launched Google I/O 2025 (proprietary) | 2026-03-04   |
| [diode.md](./ai-design-tools/diode.md) | Diode - Browser-based 3D hardware simulator for building, programming, and simulating circuits with Arduino support; shut down 2022, site still operational | 2026-03-12   |

**Key Topics**:

- AI video synthesis and character animation
- Audio-visual synchronization for content generation
- SaaS-based creative AI platform for non-technical users
- Commercial application of generative AI for marketing and content
- Cinematic camera control in AI video generation (dolly-in, orbit, crane shot)
- BM25+regex design database search for AI coding assistants
- Multi-assistant skill distribution (16 platforms via single CLI installer)
- Industry-specific design reasoning rules for domain-appropriate UI generation

---

### 21. Evaluation & Testing

**Location**: [./evaluation-testing/](./evaluation-testing/)

Harness engineering, evaluation infrastructure, and testing methodologies for AI coding agents.

| Document                                                                                          | Description                                                                                                                           | Last Updated |
| ------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- | ------------ |
| [harness-engineering-martin-fowler.md](./evaluation-testing/harness-engineering-martin-fowler.md) | Harness engineering discipline -- deterministic constraints + LLM agents to keep AI coding agents in check (Böckeler / Fowler, 2026)  | 2026-02-21   |
| [harness-engineering-openai.md](./evaluation-testing/harness-engineering-openai.md)               | OpenAI Codex harness engineering -- 3-7 engineers, 1M lines, 3.5 PRs/day via agent-first architecture with custom linters and CI      | 2026-02-21   |
| [codex-harness-openai.md](./evaluation-testing/codex-harness-openai.md)                           | Codex App Server -- bidirectional JSON-RPC protocol unifying all Codex client surfaces via single Rust core library (61K+ stars)      | 2026-02-21   |

**Key Topics**:

- Harness engineering as a discipline for constraining AI coding agents
- Three harness layers: Context Engineering, Architectural Constraints, Garbage Collection Agents
- AGENTS.md as table of contents pointing into structured `docs/` system of record
- Custom linters with error messages written as agent remediation instructions
- Strict layered architecture with validated dependency directions
- Recurring "garbage collection" Codex tasks for drift detection and cleanup PRs
- Agent-legibility requires mechanical enforcement, not documentation alone
- Iterative improvement loop: agent failure signals harness gap; agent writes fix
- Constraining solution space increases agent reliability (not expanding it)
- Bidirectional JSON-RPC "lite" protocol (JSONL over stdio) for agent harness integration
- Three conversation primitives: Item (typed I/O), Turn (unit of work), Thread (durable session)
- Schema-first protocol: Rust types generate TypeScript bindings and JSON Schema
- Repository-as-operating-environment pattern for agent development
- Harnesses predicted to replace service templates as "golden path" artifacts
- 1/10th development time via harness-constrained agent workflows

---

### 22. LLM Infrastructure

**Location**: [./llm-infrastructure/](./llm-infrastructure/)

Self-hosted LLM inference servers, multi-provider gateways, and LLMOps platforms for production AI applications.

| Document | Description | Last Updated |
| -------- | ----------- | ------------ |
| [localai.md](./llm-infrastructure/localai.md) | LocalAI - free open-source local AI inference server with OpenAI-compatible API, no GPU required, 40+ backends including llama.cpp, diffusers, whisper (43K+ stars) | 2026-02-22 |
| [tensorzero.md](./llm-infrastructure/tensorzero.md) | TensorZero - industrial-grade LLM gateway written in Rust with <1ms p99 latency, 20+ providers, fine-tuning, A/B testing, and observability (10.9K stars) | 2026-01-31 |

**Key Topics**:

- OpenAI-compatible REST API as local inference drop-in
- CPU-only inference without GPU requirement
- Plugin-style backend architecture with automatic hardware detection
- P2P distributed inference via libp2p
- MCP (Model Context Protocol) integration for agentic tool calling
- Multi-provider gateway with unified API surface
- Feedback-driven continuous prompt and model optimization
- Adaptive A/B testing with multi-armed bandits for variant selection
- Fine-tuning pipelines from production feedback (SFT, RLHF)
- Model gallery with declarative YAML configuration
- Drop-in API compatibility for zero-code migration of existing clients

---

### 23. Prompt Engineering

**Location**: [./prompt-engineering/](./prompt-engineering/)

Interactive prompt development platforms and tools for iterating on LLM prompts, system instructions, and model parameters.

| Document | Description | Last Updated |
| -------- | ----------- | ------------ |
| [claude-code-prompt-improver.md](./prompt-engineering/claude-code-prompt-improver.md) | claude-code-prompt-improver — Claude Code plugin that intercepts vague prompts via a lightweight hook (~70 lines), asks 1-6 grounded questions, and achieves 31% token reduction (v0.5.1, 1,198 stars, MIT) | 2026-03-07 |
| [google-ai-studio.md](./prompt-engineering/google-ai-studio.md) | Google AI Studio — free browser-based IDE for Gemini API with 20+ models, function calling, Google Search grounding, sandboxed code execution, and OpenAI-compatible endpoint | 2026-02-23 |
| [nano-banana-pro-prompting.md](./prompt-engineering/nano-banana-pro-prompting.md) | Nano-Banana Pro Prompting Guide — 10-category strategy guide for Google's `gemini-3-pro-image-preview` Thinking image model covering text rendering, character consistency, Search grounding, in-painting, 2D↔3D translation, 4K output, visual reasoning, storyboarding, and structural layout control | 2026-02-23 |
| [prompt-engine.md](./prompt-engineering/prompt-engine.md) | Prompt Engine — SaaS prompt generator and optimizer that converts plain-language descriptions into professional-grade prompts in < 15 seconds; includes library/tagging for reuse ($19/month) | 2026-02-23 |
| [system-prompts-ai-tools.md](./prompt-engineering/system-prompts-ai-tools.md) | x1xhlol/system-prompts-and-models-of-ai-tools — 30,000+ lines of leaked system prompts and model configs for 30+ AI tools including Claude Code, Cursor, Windsurf, Devin AI, Copilot, v0, Replit (117.9K stars, GPL-3.0) | 2026-02-23 |

**Key Topics**:

- Browser-based prompt playground with no local setup
- Adjustable generation parameters (temperature, top-P, top-K, max tokens)
- System instruction / user turn separation pattern
- One-click code export (Python, JS, Go, Java, C#, REST)
- Gemini model family access (text, image, video, audio, embeddings, robotics)
- Multimodal input support (images, PDFs, audio, video, URLs)
- Function calling with structured JSON tool dispatch
- Sandboxed Python code execution within prompt sessions
- Google Search grounding for real-time factual augmentation
- Deep Research for autonomous multi-step research workflows
- Context caching for repeated prompt prefixes to reduce cost
- Batch API (50% cost reduction) for bulk asynchronous inference
- OpenAI-compatible REST endpoint for drop-in SDK integration
- Live API (WebSockets) for real-time audio/video agent sessions
- Ephemeral token scoping for secure multi-user deployments
- Token counting API for pre-request cost estimation
- Tiered rate limits (Free → Tier 1 → Tier 2 → Tier 3) with dashboard visibility
- Comprehensive collection of 30,000+ lines of leaked/reverse-engineered AI system prompts
- Coverage of 30+ tools: Claude Code, Cursor, Windsurf, Devin AI, GitHub Copilot, v0, Replit, Lovable, Manus, Perplexity, and more
- Internal tool definitions (JSON function-call schemas) for production AI agents
- Model configuration details (model selection, temperature, context window) where disclosed
- Real-world examples of tool use protocols, safety constraints, and task decomposition strategies
- Community-maintained with active updates (last push: 2026-02-17; 117.9K stars, 30.6K forks)
- DeepWiki integration for AI-powered cross-collection search

---

### 24. AI Writing Tools

**Location**: [./ai-writing-tools/](./ai-writing-tools/)

Automated content generation tools that produce changelogs, release notes, blog posts, and social content from development activity.

| Document | Description | Last Updated |
| -------- | ----------- | ------------ |
| [notra.md](./ai-writing-tools/notra.md) | Notra - SaaS tool that auto-generates publish-ready changelogs, blog posts, and social updates by monitoring GitHub, Linear, and Slack activity; drafts content matching configured brand voice (proprietary SaaS) | 2026-03-04 |

**Key Topics**:

- Automated changelog and release note generation from merged PRs
- Multi-source activity monitoring (GitHub, Linear, Slack)
- Brand voice configuration for consistent content tone
- Eliminating manual effort in writing release announcements

---

### 25. Low-Code Platforms

**Location**: [./low-code-platforms/](./low-code-platforms/)

No-code and low-code AI workflow builders for creating AI-powered applications and automations without programming.

| Document | Description | Last Updated |
| -------- | ----------- | ------------ |
| [google-opal.md](./low-code-platforms/google-opal.md) | Google Opal - experimental no-code tool from Google Labs for building, sharing, and remixing AI-powered mini-apps via drag-and-drop workflow editor; supports agentic pipelines with memory, conditional routing, and interactive chat (Google Labs, proprietary) | 2026-03-04 |

**Key Topics**:

- Natural-language interface for workflow creation
- Visual drag-and-drop agentic pipeline builder
- Memory, conditional routing, and interactive chat in agent steps
- Prototyping and productivity automation without code

---

### 26. Claude Code Plugins

**Location**: [./claude-code-plugins/](./claude-code-plugins/)

Curated Claude Code plugin ecosystems, configuration repositories, and multi-plugin setups for extending Claude Code with skills, MCP integrations, and multi-LLM backends.

| Document | Description | Last Updated |
| -------- | ----------- | ------------ |
| [claude-codex-settings.md](./claude-code-plugins/claude-codex-settings.md) | fcakyon/claude-codex-settings — Battle-tested Claude Code plugin ecosystem: 17 plugins, 9 MCP integrations, multi-LLM backend configs (Z.ai, Kimi K2, ccproxy) (452 stars) | 2026-03-06 |

**Key Topics**:

- Multi-plugin Claude Code configuration ecosystems
- MCP server integration patterns and config management
- Multi-LLM backend routing (Z.ai, Kimi K2, ccproxy, OpenRouter)
- Battle-tested plugin selection and curated skill sets

---

## Planned Categories

The following categories are planned for future research:

| Category                | Description                                        | Status   |
| ----------------------- | -------------------------------------------------- | -------- |
| `prompt-engineering/`   | Prompt optimization tools and techniques           | **Done** |
| `context-management/`   | Memory, context window, and RAG tools              | **Done** |
| `mcp-ecosystem/`        | MCP servers and integrations                       | **Done** |
| `agent-frameworks/`     | Agent SDKs and orchestration frameworks            | **Done** |
| `agent-infrastructure/` | Infrastructure for deploying agentic apps at scale | **Done** |
| `api-frameworks/`       | High-performance API frameworks for backend services | **Done** |
| `async-libraries/`      | Python async I/O and concurrency frameworks        | **Done** |
| `data-infrastructure/`  | Real-time data platforms for analytics             | **Done** |
| `code-auditing/`        | Code security and quality auditing tools           | **Done** |
| `developer-tools/`      | Developer productivity and workflow tools          | **Done** |
| `coding-agents/`        | Autonomous AI coding agent platforms               | **Done** |
| `task-management/`      | AI-powered task management for development         | **Done** |
| `ml-infrastructure/`    | ML compute engines and model serving platforms     | **Done** |
| `python-runtimes/`      | Alternative Python interpreters and runtimes       | **Done** |
| `rust-python-bindings/` | Rust-Python interoperability and binding libraries | **Done** |
| `ai-observability/`     | AI/LLM observability and debugging platforms       | **Done** |
| `ai-research-tools/`   | AI research tools and newsletters                  | **Done** |
| `documentation-tools/`  | Architecture documentation and living docs         | **Done** |
| `ai-design-tools/`      | AI-powered visual creation and design platforms    | **Done** |
| `evaluation-testing/`   | Agent evaluation and testing tools                 | **Done** |
| `llm-infrastructure/`   | LLM inference servers and multi-provider gateways  | **Done** |

---

## Research Entry Format

Each research document should follow this structure:

```markdown
# [Tool/Repository Name]

**Research Date**: YYYY-MM-DD
**Source URL**: <https://...>
**GitHub Repository**: <https://github.com/...> (if applicable)
**Version at Research**: vX.Y.Z
**License**: [License type]

---

## Overview
[Brief description of what this tool/pattern does]

---

## Problem Addressed
[What problem does this solve?]

---

## Key Features
[Detailed feature breakdown]

---

## Technical Architecture
[How it works internally]

---

## Relevance to Claude Code Development
[How this applies to our work]

---

## References
[Cited sources with access dates]

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | YYYY-MM-DD |
| Version at Verification | vX.Y.Z |
| Next Review Recommended | YYYY-MM-DD |
```

---

## Freshness Policy

Research documents should be reviewed periodically to ensure accuracy:

| Document Age | Review Frequency              |
| ------------ | ----------------------------- |
| < 3 months   | Current                       |
| 3-6 months   | Review recommended            |
| 6-12 months  | Review required               |
| > 12 months  | Stale - requires verification |

**Freshness indicators to monitor**:

- Version changes (check GitHub releases, PyPI, npm)
- Star/fork changes (significant growth may indicate maturity)
- Breaking API changes
- New features that affect recommendations

---

## Contributing Research

When adding new research:

1. **Create appropriate subdirectory** if the category doesn't exist
2. **Follow the entry format** documented above
3. **Include freshness tracking** with specific dates
4. **Cite all sources** with access dates
5. **Update this README** with the new entry in the appropriate table

---

## Quick Reference Links

### External Resources

- [Awesome Claude Code](https://github.com/hesreallyhim/awesome-claude-code) - 17,825 stars
- [Awesome Claude Code Subagents](https://github.com/VoltAgent/awesome-claude-code-subagents) - 5,616 stars
- [Awesome MCP Servers](https://github.com/punkpeye/awesome-mcp-servers) - 76,332 stars
- [Compound Engineering Plugin](https://github.com/EveryInc/compound-engineering-plugin) - Plan/Work/Review/Compound workflow (6,830 stars)
- [Get Shit Done](https://github.com/glittercowboy/get-shit-done) - Meta-prompting and spec-driven development (10,193 stars)
- [Skill Seekers](https://skillseekersweb.com/) - Documentation to AI skills
- [OpenHands](https://openhands.dev) - Open platform for cloud coding agents (67,108 stars)
- [Claude Task Master](https://task-master.dev) - AI-powered task management (25,062 stars)
- [Tinybird](https://www.tinybird.co) - Real-time data platform with managed ClickHouse and MCP
- [Claude-Mem](https://claude-mem.ai) - Persistent memory compression for Claude Code (15,681 stars)
- [Repomix](https://repomix.com) - Pack codebase into AI-friendly formats (21,597 stars)
- [Superpowers](https://github.com/obra/superpowers) - Agentic skills framework and software development methodology (40,911 stars)
- [Trio](https://github.com/python-trio/trio) - Structured concurrency async library for Python (7,143 stars)
- [Ray](https://github.com/ray-project/ray) - AI compute engine for scaling Python/ML workloads (41,140 stars)
- [Pydantic Logfire](https://logfire.pydantic.dev/) - AI-native observability with full-stack tracing and MCP server (3,984 stars)
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework with automatic OpenAPI docs and Pydantic validation (94,804 stars)
- [RustPython](https://rustpython.github.io/) - Python 3 interpreter written in Rust with WASM support and JIT compiler (21,752 stars)
- [PyO3](https://pyo3.rs) - Rust bindings for Python with maturin build tool and abi3 stable ABI (15,268 stars)
- [Tornado](https://www.tornadoweb.org/) - Python web framework and async networking library for WebSockets and long-polling (22,437 stars)
- [AnyIO](https://github.com/agronholm/anyio) - Backend-agnostic async concurrency library for Python (2,374 stars, 426M downloads/month)
- [LiteAgents](https://github.com/hamr0/liteagents) - Multi-tool AI development toolkit with 11 agents and Hot Memory pipeline (npm)
- [Local Memory](https://www.localmemory.co/) - Persistent memory infrastructure for AI agents with embedded Qdrant vector search
- [GrepAI](https://github.com/yoanbernabeu/grepai) - Semantic code search and call graph analysis for AI agents (1,222 stars)
- [Loguru](https://github.com/Delgan/loguru) - Zero-config Python logging with structured output and exception catching (23,577 stars)
- [Niteni](https://gitlab.com/denyherianto/niteni) - AI-powered code review for GitLab CI with inline diff suggestions
- [Traycer](https://traycer.ai) - Spec-driven AI development orchestrator with multi-model ensemble architecture
- [VERT](https://vert.sh) - WebAssembly-based file converter for 250+ formats (13,809 stars)
- [Yume](https://aofp.github.io/yume/) - Native desktop GUI for Claude Code CLI with parallel agents (Tauri + Rust)
- [The Claw Loop](https://www.dontsleeponai.com/claw-loop) - Autonomous development orchestration via tmux + cron
- [mcpskills-cli](https://github.com/dhanababum/mcpskills-cli) - MCP-to-skill converter via Streamable HTTP discovery
- [SkillKit](https://github.com/rohitg00/skillkit) - Universal package manager for AI agent skills (32 agents, 15K+ skills)
- [Claude Conductor](https://github.com/rbarcante/claude-conductor) - Context-Driven Development plugin for Claude Code with skill ecosystem and quality intelligence (34 stars)
- [Retio PageMap](https://github.com/Retio-ai/Retio-pagemap) - MCP server compressing HTML pages to 2-5K token structured maps with 95.2% task success (14 stars)
- [TinyClaw](https://github.com/jlia0/tinyclaw) - Multi-agent multi-channel 24/7 AI assistant with peer-to-peer handoffs and file-based queue (2,124 stars)
- [Ollama](https://ollama.com) - Local LLM runtime with native Claude Code subagents, web search, and Anthropic API compatibility (162,863 stars)
- [Pilot](https://github.com/alekspetrov/pilot) - Autonomous development pipeline wrapping Claude Code CLI with ticket-to-PR automation (BSL 1.1)
- [The Unwind AI](https://www.theunwindai.com) - AI builder newsletter with 500+ Python AI agent examples (95,911 stars companion repo)
- [Claude Quickstarts](https://github.com/anthropics/claude-quickstarts) - Official Anthropic quickstart projects: computer use, browser automation, multi-session coding agent, minimal agent loop, Next.js UIs (14,681 stars)
- [HumanCompiler](https://github.com/Gerstep/HumanCompiler) - Interview-to-agent plugin generator for Claude Code (MIT)
- [Kernel](https://www.kernel.sh) - Browsers-as-a-service API with isolated VM-per-browser Chrome, 72h sessions, CDP passthrough, MCP server, and Browser Pools ($22M raised, 670 stars)
- [ZeroClaw](https://github.com/zeroclaw-labs/zeroclaw) - Rust autonomous AI assistant with sub-5MB RAM, 28+ AI providers, 15+ messaging channels, trait-driven architecture (14,966 stars)
- [Perplexity MCP Server](https://github.com/perplexityai/modelcontextprotocol) - Official Perplexity AI MCP server with real-time web search, deep research, and reasoning (1,959 stars)
- [ClawHub](https://www.clawhub.ai/skills) - Skill registry for AI agents with vector search capabilities
- [Claude Skillz](https://github.com/NTCoding/claude-skillz) - 18+ behavioral skills, 12 personas, 10 plugins, and Claude Launcher for Claude Code (238 stars)
- [Living Architecture](https://github.com/NTCoding/living-architecture) - Operational flow architecture extraction from code with Rivière schema and AI-assisted workflows (79 stars)
- [Lopaka](https://lopaka.app) - Web-based graphics editor for embedded displays with multi-library C/C++ code generation (1,150 stars)
- [claude-openocd-spi-dump](https://github.com/lukejenkins/claude-openocd-spi-dump) - Claude Code plugin for SPI flash dumping via OpenOCD with RAM-resident code for 6 MCU families
- [Softaworks Agent Toolkit](https://github.com/softaworks/agent-toolkit) - 43 skills, 6 agents, 7 slash commands for Claude Code with multi-platform support (621 stars)
- [Vercel Labs Skills](https://github.com/vercel-labs/skills) - Universal CLI for installing skills to 40+ AI coding agents (6,324 stars)
- [jira.js](https://mrrefactoring.github.io/jira.js/) - TypeScript Jira API client for Cloud, Server, and Data Center
- [Hedra](https://www.hedra.com) - AI-powered visual creation platform for video, image, and audio content
- [Kythe](https://kythe.io) - Google's language-agnostic code intelligence platform with graph-based semantic indexing (2,094 stars)
- [GitHub CLI](https://github.com/cli/cli) - Official GitHub CLI for PRs, issues, workflows, and extensions (37,800+ stars)
- [codex-skills](https://github.com/jMerta/codex-skills) - 19-skill catalog for OpenAI Codex CLI with npx installer, global ledger pattern, and prompt-injection hardening (116 stars)
- [Browser MCP](https://browsermcp.io) - Chrome browser automation MCP server via extension bridge, preserving auth sessions and real fingerprint (5,814 stars)
- [Micro-Agent](https://github.com/fdueblab/Micro-Agent) - Lightweight Python 3.12 ReAct agent framework with MCP multi-server support, token budget enforcement, and step-level execution visualization (MIT)
- [Harness Engineering (Fowler/Böckeler)](https://martinfowler.com/articles/exploring-gen-ai/harness-engineering.html) - Harness engineering discipline for constraining AI coding agents via deterministic + LLM infrastructure
- [Harness Engineering (OpenAI)](https://openai.com/index/harness-engineering/) - OpenAI Codex team's harness engineering practices: 1M lines, 3.5 PRs/engineer/day, agent-first architecture
- [Unlocking the Codex Harness (OpenAI)](https://openai.com/index/unlocking-the-codex-harness/) - Codex App Server bidirectional JSON-RPC protocol and Rust core library (61,233 stars)

### Internal References

- [Workflow Diagrams](../.claude/knowledge/workflow-diagrams/) - Agentic process flow visualizations
- [Plugin Development](../plugins/) - Claude Code plugins in this repository
- [Agent Definitions](../.claude/agents/) - Custom agent configurations
