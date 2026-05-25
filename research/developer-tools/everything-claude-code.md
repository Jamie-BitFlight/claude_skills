# Everything Claude Code

**Research Date**: 2026-03-06
**Source URL**: <https://github.com/affaan-m/everything-claude-code>
**GitHub Repository**: <https://github.com/affaan-m/everything-claude-code>
**Version at Research**: v1.8.0 (Harness Performance Release)
**License**: MIT

---

## Overview

Everything Claude Code (ECC) is an agent harness performance optimization system delivering 15 specialized sub-agents, 56+ skills, 33+ slash commands, a trigger-based hooks pipeline, multi-language rules, and MCP server configurations assembled over 10+ months of daily use. Originating as an Anthropic hackathon winner (Cerebral Valley x Anthropic, Feb 2026), it has reached 61K+ GitHub stars and 7.6K+ forks, making it the largest community-maintained Claude Code configuration library by engagement. As of v1.8.0 it repositions from "config bundle" to a practical agent harness performance system with reliable hooks, eval/quality controls, and tighter parity across five AI coding tools: Claude Code, Cursor, OpenCode, OpenAI Codex CLI, and Antigravity IDE.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| No standard starting point for Claude Code configuration | Ready-to-install plugin with 15 agents, 56 skills, 33 commands, and a hooks pipeline immediately available |
| Claude Code lacks memory between sessions | `hooks/memory-persistence/` hooks save and reload context at session start/end automatically |
| Configuring MCP servers for GitHub, Supabase, Vercel, Railway requires manual JSON editing | `mcp-configs/mcp-servers.json` ships pre-configured server definitions for common services |
| Code quality is advisory rather than enforced when using AI | Rules directory provides always-follow guidelines; PostToolUse hooks enforce linting and testing |
| Token budget wasted on language-agnostic rules in single-language projects | Rules restructured into `common/` + `typescript/` + `python/` + `golang/` — install only what applies |
| AI coding agents lack domain-specific knowledge (ClickHouse, Django, Spring Boot, Swift) | 56+ skills covering analytics, backend, frontend, mobile, databases, deployment, and security |
| Claude Code configuration is not portable across teams | Plugin marketplace integration: one command installs the full config for any team member |
| AI sessions generate insights that are immediately lost | Continuous learning v2 (`/learn`, `/evolve`) extracts instincts from sessions into reusable skill files |
| Hooks are unreliable in CI and non-interactive environments | `ECC_HOOK_PROFILE=minimal\|standard\|strict` + `ECC_DISABLED_HOOKS` env var for explicit hook control |
| Agent harness performance is not measurable or auditable | `/harness-audit` and `/quality-gate` commands baseline reliability and enforce quality controls |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 61,784 | 2026-03-06 |
| GitHub Forks | 7,646 | 2026-03-06 |
| Contributors | 50+ (paginated list) | 2026-02-26 |
| Watchers | 329 | 2026-03-06 |
| Open Issues | 20 | 2026-03-06 |
| Latest Release | v1.8.0 | 2026-03-05 |
| Repository Created | 2026-01-18 | 2026-02-26 |
| Last Push | 2026-03-05 | 2026-03-06 |
| Agents | 15 | 2026-03-05 (v1.8.0 release notes) |
| Skills | 56+ | 2026-02-27 (v1.7.0 release notes) |
| Commands | 33+ | 2026-02-27 (v1.7.0 release notes) |
| Internal Tests | 992 | 2026-02-27 (v1.7.0 release notes) |
| AgentShield Security Rules | 102 | 2026-02-24 (v1.6.0 release notes) |
| Community PRs Merged (v1.6.0 cycle) | 30 | 2026-02-24 (v1.6.0 release notes) |
| Primary Language | JavaScript | 2026-02-26 |
| Supported Languages | JavaScript, TypeScript, Shell, Python | 2026-02-26 |
| Supported AI Tools | 5 (Claude Code, Cursor, OpenCode, Codex CLI, Antigravity IDE) | 2026-03-05 (v1.8.0) |

---

## Key Features

### Agents (15 Specialized Sub-Agents)

Each agent is a Markdown file with YAML frontmatter declaring name, description, tools, and model. Claude Code delegates to these agents via the Agent tool.

- **planner.md** — Feature implementation planning; decomposes tasks into ordered steps
- **architect.md** — System design decisions; evaluates trade-offs across architecture options
- **tdd-guide.md** — Test-driven development enforcement; RED → GREEN → REFACTOR protocol
- **code-reviewer.md** — Quality and security review with specific checklist categories
- **security-reviewer.md** — Vulnerability analysis; OWASP categories, secret scanning, injection risks
- **build-error-resolver.md** — Root cause analysis and fix generation for build failures
- **e2e-runner.md** — Playwright E2E test generation and execution coordination
- **refactor-cleaner.md** — Dead code removal and structural cleanup
- **doc-updater.md** — Documentation synchronization with code changes
- **go-reviewer.md / go-build-resolver.md** — Go-specific code review and build error resolution
- **python-reviewer.md** — Python-specific code review (added v1.4.0+)
- **database-reviewer.md** — Database/Supabase pattern review (added v1.4.0+)
- **chief-of-staff.md** — Communication triage for coordination-heavy workflows (added v1.7.0)
- **harness-optimizer.md** — Agent harness performance auditing and tuning (added v1.8.0)
- **loop-operator.md** — Continuous agent loop management and monitoring (added v1.8.0)

### Skills (56+ Workflow Definitions)

Skills provide domain knowledge and workflow definitions. Coverage spans:

- **Language standards**: coding-standards, cpp-coding-standards, java-coding-standards, golang-patterns, python-patterns
- **Framework patterns**: frontend-patterns (React, Next.js), backend-patterns, django-patterns, springboot-patterns
- **Testing**: tdd-workflow, cpp-testing, django-tdd, golang-testing, python-testing, springboot-tdd, e2e-testing
- **Security**: security-review, django-security, springboot-security, security-scan (AgentShield integration)
- **Databases**: clickhouse-io, postgres-patterns, database-migrations, jpa-patterns
- **Infrastructure**: deployment-patterns, docker-patterns, api-design
- **LLM/AI cost**: cost-aware-llm-pipeline, regex-vs-llm-structured-text
- **Mobile/Apple**: swift-actor-persistence, swift-protocol-di-testing, liquid-glass-design, foundation-models-on-device, swift-concurrency-6-2, swiftui-patterns
- **Session learning**: continuous-learning, continuous-learning-v2, iterative-retrieval, strategic-compact, eval-harness, verification-loop
- **Content/Business (added v1.7.0)**: article-writing, content-engine, market-research, investor-materials, investor-outreach, frontend-slides, visa-doc-translate
- **Agent harness (added v1.8.0)**: agent-harness-construction, agentic-engineering, ralphinho-rfc-pipeline, ai-first-engineering, enterprise-agent-ops, nanoclaw-repl, continuous-agent-loop
- **Meta/tooling**: skill-stocktake, search-first, configure-ecc, project-guidelines-example

### Commands (33+ Slash Commands)

```text
/tdd            — Test-driven development workflow (RED → GREEN → REFACTOR)
/plan           — Feature implementation planning with clarifying questions
/e2e            — E2E test generation with Playwright
/code-review    — Quality and security code review
/build-fix      — Fix build errors via root cause analysis
/refactor-clean — Dead code and structural cleanup
/learn          — Extract patterns mid-session into reusable skills
/learn-eval     — Extract, evaluate, and save patterns with quality scoring
/checkpoint     — Save verification state for long-running tasks
/verify         — Run verification loop against saved checkpoint
/skill-create   — Generate SKILL.md files from git history analysis
/instinct-status  — View learned instincts with confidence scores
/instinct-import  — Import instincts from other sessions or contributors
/instinct-export  — Export instincts for team sharing
/evolve           — Cluster related instincts into higher-level skills
/pm2            — PM2 service lifecycle management
/multi-plan     — Multi-agent task decomposition
/multi-execute  — Orchestrated multi-agent workflow execution
/orchestrate    — Multi-agent coordination for complex workflows
/sessions       — Session history management
/security-scan  — AgentShield security auditor (102 rules, 1282 tests)
/codex-setup    — Generate codex.md for OpenAI Codex CLI compatibility
/setup-pm       — Configure package manager (npm/pnpm/yarn/bun detection)
/go-review / /go-test / /go-build  — Go language workflow commands
/python-review  — Python code review
/eval           — Evaluate implementation against criteria
/test-coverage  — Test coverage analysis
/update-docs    — Documentation sync with code
/update-codemaps — Auto-generate codebase maps
/harness-audit  — Baseline agent harness reliability and surface risks (added v1.8.0)
/loop-start     — Start a continuous agent loop (added v1.8.0)
/loop-status    — Query status of a running agent loop (added v1.8.0)
/quality-gate   — Enforce quality controls on active repos (added v1.8.0)
/model-route    — Route tasks to appropriate model via NanoClaw v2 (added v1.8.0)
```

### Hooks Pipeline

```text
hooks/hooks.json — JSON config with PreToolUse, PostToolUse, Stop event handlers
hooks/memory-persistence/
  session-start.js    — Load context from persistent storage at session start
  session-end.js      — Save state at session end
  pre-compact.js      — Snapshot active state before auto-compaction
  suggest-compact.js  — Strategic compaction timing suggestions
  evaluate-session.js — Auto-extract patterns from completed sessions
```

Hook environment controls (added v1.8.0):

- `ECC_HOOK_PROFILE=minimal|standard|strict` — tune hook aggressiveness
- `ECC_DISABLED_HOOKS=comma,separated,ids` — disable specific hooks by ID

### Multi-Language Rules Architecture

Rules are split into four directories, allowing selective installation:

```text
rules/
  common/           — Language-agnostic (coding-style, git-workflow, testing, security, patterns, agents, hooks)
  typescript/       — TypeScript/JavaScript specific
  python/           — Python specific
  golang/           — Go specific
```

Install via `./install.sh typescript python golang` (the installer script handles merge/overwrite detection).

### NanoClaw v2 (added v1.8.0)

NanoClaw is ECC's persistent session-aware CLI REPL. v2 adds:

- Model routing — route tasks to the appropriate model based on complexity and cost
- Skill hot-load — load and reload skills without restarting the session
- Session branch/search/export/compact/metrics — full session lifecycle management

Exposed via the `nanoclaw-repl` skill and `/model-route` command.

### Continuous Learning v2 (Instinct System)

The instinct system automatically extracts patterns from sessions:

- Instincts stored with confidence scores, evidence, and example sessions
- `/instinct-status` surfaces high-confidence patterns for review
- `/evolve` clusters related instincts into generalized skills via LLM analysis
- Import/export enables team-wide pattern sharing
- `continuous-learning-v2/` skill documents the full lifecycle

### AgentShield Security Auditor

Built at the Claude Code Hackathon (Cerebral Valley x Anthropic, Feb 2026). Scans Claude Code configuration for vulnerabilities.

```bash
npx ecc-agentshield scan         # Quick scan
npx ecc-agentshield scan --fix   # Auto-fix safe issues
npx ecc-agentshield scan --opus  # Deep analysis with three Opus 4.6 agents
```

Scans: CLAUDE.md, settings.json, MCP configs, hooks, agents, skills across 5 categories — secrets detection (14 patterns), permission auditing, hook injection analysis, MCP server risk profiling, and agent config review. Output formats: terminal (A-F grade), JSON, Markdown, HTML. Exit code 2 on critical findings for CI build gates.

### Cross-Platform Support

All hooks and scripts written in Node.js. Supports Windows, macOS, Linux. Package manager detection priority: `CLAUDE_PACKAGE_MANAGER` env → `.claude/package-manager.json` → `package.json` `packageManager` field → lock file detection → global config → fallback to first available.

v1.8.0 hardened Windows path handling for doc-warning/whitelist logic and replaced fragile inline one-liner hook commands with dedicated scripts for safer cross-platform behavior.

### Multi-Tool Support (v1.8.0)

Single config source for five AI coding tools:

- **Claude Code** — native via plugin marketplace
- **Cursor** — `/.cursor/` directory with rules and agents
- **OpenCode** — `/.opencode/` with plugin system, 20+ hook event types, 3 native custom tools
- **OpenAI Codex CLI** — `/.codex/` via `/codex-setup` command generating `codex.md`
- **Antigravity IDE** — added in v1.8.0 (5th supported tool)

### GitHub Marketplace App

Available at `github.com/marketplace/ecc-tools`. Free/Pro/Enterprise tiers. Provides `/skill-creator analyze` via issue comments and auto-triggers on push to default branch. Generates SKILL.md files, instinct collections, and pattern extraction from commit history.

---

## Technical Architecture

```text
everything-claude-code/
├── .claude-plugin/       — Plugin and marketplace manifests
│   ├── plugin.json         — Plugin metadata and component paths
│   └── marketplace.json    — Marketplace catalog
├── .claude/              — Claude Code native config (CLAUDE.md, settings)
├── .cursor/              — Cursor IDE config
├── .codex/               — OpenAI Codex CLI config
├── .opencode/            — OpenCode plugin config
├── agents/               — 15 agent Markdown files (YAML frontmatter)
├── skills/               — 56+ skill Markdown files organized by domain
├── commands/             — 33+ slash command Markdown files
├── rules/
│   ├── common/           — Language-agnostic guidelines (7 files)
│   ├── typescript/       — TS/JS rules
│   ├── python/           — Python rules
│   └── golang/           — Go rules
├── hooks/
│   ├── hooks.json        — All hooks config (auto-loaded by Claude Code v2.1+)
│   ├── memory-persistence/
│   └── strategic-compact/
├── scripts/
│   ├── lib/utils.js      — Cross-platform file/path/system utilities
│   ├── lib/package-manager.js — Package manager detection
│   └── hooks/            — Node.js hook implementations (dedicated scripts, v1.8.0+)
├── mcp-configs/
│   └── mcp-servers.json  — GitHub, Supabase, Vercel, Railway, etc.
├── contexts/             — Dynamic system prompt injection (dev/review/research)
├── docs/
│   └── releases/         — Per-release notes and launch assets (added v1.8.0)
├── examples/             — Real-world CLAUDE.md configs (SaaS, Go microservice, Django, Rust)
├── tests/                — 992-test suite (lib, hooks, cross-platform)
├── install.sh            — Language-selective installer with merge detection
├── package.json          — npm package metadata
├── CODE_OF_CONDUCT.md    — Added v1.8.0
├── the-shortform-guide.md — Setup and foundations guide
├── the-longform-guide.md  — Token optimization, memory, evals, parallelization
├── the-security-guide.md  — Security configuration guide
└── the-openclaw-guide.md  — OpenCode integration guide
```

**Installation mechanism**: Claude Code v2.1+ auto-loads `hooks/hooks.json` from any installed plugin by convention. Explicitly declaring it in `plugin.json` causes a duplicate detection error — the repo enforces this via a regression test.

**Plugin installation**:

```bash
/plugin marketplace add affaan-m/everything-claude-code
/plugin install everything-claude-code@everything-claude-code
```

Or manually add to `~/.claude/settings.json` under `extraKnownMarketplaces` and `enabledPlugins`.

**Rules require manual copy** (upstream Claude Code plugin limitation — rules cannot be distributed via plugins):

```bash
git clone https://github.com/affaan-m/everything-claude-code.git
./install.sh typescript    # or python or golang
```

---

## Version History

| Version | Date | Key Changes |
|---------|------|-------------|
| v1.8.0 | 2026-03-05 | Harness Performance Release — repositioned as "agent harness performance system"; new harness commands (/harness-audit, /loop-start, /loop-status, /quality-gate, /model-route); NanoClaw v2 (model routing, skill hot-load, session branch/search/export); 7 new harness skills; 2 new agents (harness-optimizer, loop-operator); hook reliability fixes (ECC_HOOK_PROFILE, ECC_DISABLED_HOOKS); Antigravity IDE support (5th tool); Code of Conduct added |
| v1.7.0 | 2026-02-27 | Cross-Platform Expansion & Presentation Builder — 992 tests, 56 skills, 33 commands, 14 agents; direct Codex support with AGENTS.md; chief-of-staff agent; frontend-slides skill; 5 new business/content skills (article-writing, content-engine, market-research, investor-materials, investor-outreach); 6 new Apple/Swift skills; Cowork marketplace compatibility; auto-detect formatter in post-edit hook |
| v1.6.0 | 2026-02-24 | Codex Edition — OpenAI Codex CLI support; AgentShield security auditor (npm package, 102 rules, 1282 tests); 978 tests; 13 agents, 48 skills, 31 commands; Hackathon winner (Cerebral Valley x Anthropic, Feb 2026) |

---

## Installation and Usage

```bash
# Option 1: Install as Claude Code plugin (recommended)
/plugin marketplace add affaan-m/everything-claude-code
/plugin install everything-claude-code@everything-claude-code

# Option 2: Manual rules installation after plugin install
git clone https://github.com/affaan-m/everything-claude-code.git
cd everything-claude-code
./install.sh typescript          # single language
./install.sh typescript python golang  # multiple languages
./install.sh --target cursor typescript  # for Cursor

# Option 3: Direct settings.json (headless/CI environments)
# Add to ~/.claude/settings.json:
# "extraKnownMarketplaces": { "everything-claude-code": { "source": { "source": "github", "repo": "affaan-m/everything-claude-code" } } }
# "enabledPlugins": { "everything-claude-code@everything-claude-code": true }

# Run tests
node tests/run-all.js

# AgentShield security scan
npx ecc-agentshield scan
npx ecc-agentshield scan --fix
npx ecc-agentshield scan --opus --stream

# Harness audit and quality gate (v1.8.0)
/harness-audit
/quality-gate . --strict

# Configure OpenAI Codex CLI compatibility
/codex-setup

# Continuous learning workflow
/learn                   # Extract patterns from current session
/instinct-status         # View learned instincts with confidence scores
/evolve                  # Cluster instincts into skills

# Multi-agent orchestration
/multi-plan "Build user auth with OAuth and JWT"
/multi-execute

# Tune hook behavior (v1.8.0)
ECC_HOOK_PROFILE=minimal claude   # minimal hooks for CI
ECC_DISABLED_HOOKS=doc-warning,observe claude  # disable specific hooks
```

---

## Relevance to Claude Code Development

### Direct Applicability

This repository is the closest peer project to `claude_skills` in the Claude Code ecosystem. Both organize configuration as plugins with agents, skills, commands, hooks, and rules. Reviewing ECC's structure surfaces patterns directly applicable to `claude_skills` development:

- **Continuous learning v2 (instinct system)**: Automatic session pattern extraction with confidence scoring and cluster-to-skill promotion — a novel architecture not present in `claude_skills` that could address the gap between ephemeral session knowledge and persistent skills.
- **Language-selective rules**: The `common/` + per-language directory split reduces context waste for single-language projects. `claude_skills` uses a flat rules structure.
- **Skill creator command (`/skill-create`)**: Generates SKILL.md files from git history via local analysis — a workflow that could complement `claude_skills`' `/plugin-creator:skill-creator`.
- **`contexts/` directory**: Dynamic system prompt injection modes (dev/review/research) provide lightweight context switching without separate skills or commands.
- **Real-world CLAUDE.md examples**: `examples/saas-nextjs-CLAUDE.md`, `examples/go-microservice-CLAUDE.md` etc. are concrete references for users setting up their own projects.
- **Hook reliability controls (v1.8.0)**: `ECC_HOOK_PROFILE` and `ECC_DISABLED_HOOKS` env vars are a concrete pattern for making hooks controllable in CI and non-interactive environments — directly applicable to `claude_skills` hooks.
- **Harness audit commands (v1.8.0)**: `/harness-audit` and `/quality-gate` commands address measurability of agent performance — a gap in `claude_skills`' current evaluation tooling.

### Patterns Worth Adopting

- **Blocking Stop hooks**: Prevent premature session end when a multi-phase workflow is in progress — applicable to `claude_skills` long-running agent workflows.
- **Pre/post-compact hooks**: `pre-compact.js` + session-start restore enables seamless continuation across context resets for any skill managing multi-phase state.
- **Regression test for plugin.json hooks field**: Auto-detecting a common misconfiguration (duplicate hooks declaration) via a test prevents repeated fix/revert cycles.
- **AgentShield scan in CI**: Running `npx ecc-agentshield scan` as a build gate (exit code 2 on critical findings) is a concrete security enforcement pattern for Claude Code plugin repositories.
- **Dedicated hook scripts (v1.8.0)**: Replacing inline one-liner hook commands with dedicated scripts reduces cross-platform failure modes — the pattern `claude_skills` should follow for any hook with conditional logic.

### Competitive Analysis

| Dimension | ECC (affaan-m) | claude_skills (this repo) |
|-----------|----------------|--------------------------|
| Primary focus | Agent harness performance system (repositioned v1.8.0) | Modular skills marketplace with plugin framework |
| Distribution | Plugin marketplace + git clone | Plugin marketplace (Claude Code native) |
| Rules distribution | Manual copy via install.sh (upstream limitation) | Same upstream limitation |
| Learning system | Continuous learning v2 (instinct-based, auto-extract) | No built-in equivalent |
| Security tooling | AgentShield (102 rules, npm package, CI-ready) | No built-in equivalent |
| Cross-tool support | Claude Code, Cursor, OpenCode, Codex CLI, Antigravity IDE | Claude Code only |
| Testing | 992 tests (Node.js) | Python-based validation scripts |
| Languages supported | JS, TS, Python, Go, C++, Java, Swift, Rust, Django | Language-agnostic |
| Stars at research | 61,784 | N/A (internal) |
| Agents | 15 | Varies by plugin |
| Skills | 56+ | Varies by plugin |
| License | MIT | Internal/proprietary |

### Integration Opportunities

- The `mcp-configs/mcp-servers.json` pre-configured MCP definitions (GitHub, Supabase, Vercel, Railway) are directly reusable as references when documenting MCP server configurations in `claude_skills`.
- ECC's `examples/` CLAUDE.md files for real-world stacks (SaaS Next.js, Go microservice, Django API, Rust API) are valuable research references for `claude_skills` documentation.
- The `/security-scan` skill wrapping AgentShield could be evaluated as a security audit step in `claude_skills` CI/pre-commit pipeline.
- ECC's `ECC_HOOK_PROFILE` pattern could be adapted for `claude_skills` hooks to allow per-environment tuning without code changes.

---

## References

- [affaan-m/everything-claude-code GitHub repository](https://github.com/affaan-m/everything-claude-code) (accessed 2026-03-06)
- [v1.8.0 release — Harness Performance & Cross-Platform Reliability](https://github.com/affaan-m/everything-claude-code/releases/tag/v1.8.0) (accessed 2026-03-06)
- [v1.7.0 release — Cross-Platform Expansion & Presentation Builder](https://github.com/affaan-m/everything-claude-code/releases/tag/v1.7.0) (accessed 2026-03-06)
- [v1.6.0 release — ECC Codex Edition + Github App](https://github.com/affaan-m/everything-claude-code/releases/tag/v1.6.0) (accessed 2026-02-26)
- [ECC GitHub Marketplace App](https://github.com/marketplace/ecc-tools) (accessed 2026-02-26)
- [AgentShield GitHub repository](https://github.com/affaan-m/agentshield) (accessed 2026-02-26)
- [ecc-agentshield npm package](https://www.npmjs.com/package/ecc-agentshield) (accessed 2026-02-26)
- [Repository README](https://github.com/affaan-m/everything-claude-code/blob/main/README.md) (accessed 2026-03-06)
- [Repository CLAUDE.md](https://github.com/affaan-m/everything-claude-code/blob/main/CLAUDE.md) (accessed 2026-02-26)

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | 2026-03-06 |
| Version at Verification | v1.8.0 |
| Next Review Recommended | 2026-06-06 |

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Claude Code Harness](../agent-frameworks/claude-code-harness.md) | agent-frameworks | referenced by Claude Code Harness (agent-frameworks) |
| [Claude CodePro](./../coding-agents/claude-codepro.md) | coding-agents | referenced by Claude CodePro (coding-agents) |
