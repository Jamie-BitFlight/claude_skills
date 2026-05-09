---
name: Everything Claude Code
description: Comprehensive agent harness performance system providing 65+ skills, 16 agents, 40+ commands, hooks, rules, and security scanning for Claude Code and cross-platform AI harnesses (Codex, Cursor, OpenCode).
license: MIT
metadata:
  topic: everything-claude-code
  category: skill-generation-tools
  source_url: https://github.com/affaan-m/everything-claude-code
  github: affaan-m/everything-claude-code
  version: "1.8.0"
  verified: "2026-03-06"
  next_review: "2026-06-06"
---

# Everything Claude Code

**Research Date**: 2026-03-06
**Source URL**: <https://github.com/affaan-m/everything-claude-code>
**GitHub Repository**: <https://github.com/affaan-m/everything-claude-code>
**npm (universal)**: <https://npmjs.com/package/ecc-universal>
**npm (security)**: <https://npmjs.com/package/ecc-agentshield>
**GitHub App**: <https://github.com/marketplace/ecc-tools>
**Version at Research**: v1.8.0
**License**: MIT

---

## Overview

Everything Claude Code (ECC) is a production-grade agent harness performance system evolved over 10+ months of intensive daily use building real products. It provides 65+ skills, 16 agents, 40+ commands, structured hooks, rules, and an integrated security scanner (AgentShield) for Claude Code. The system ships cross-platform support for Claude Code, OpenAI Codex, Cursor, and OpenCode through a single Claude Code plugin install, and was recognized as an Anthropic Hackathon winner.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| AI agents lack structured memory and context continuity across sessions | SessionStart/Stop hooks save and restore context automatically via `scripts/hooks/session-start.js` and `session-end.js` |
| No standard way to encode team coding standards into agent behavior | Multi-language rules architecture (`common/`, `typescript/`, `python/`, `golang/`) installable per-language via `./install.sh` |
| Claude Code configurations become stale and untested | `/skill-stocktake` command audits skills and commands for quality; 997 internal tests cover the full suite |
| Agent orchestration for complex multi-service workflows is ad-hoc | Six `/multi-*` commands (`/multi-plan`, `/multi-execute`, `/multi-backend`, `/multi-frontend`, `/multi-workflow`) for structured multi-agent coordination |
| Security vulnerabilities in Claude Code configs go undetected | AgentShield scans CLAUDE.md, settings.json, MCP configs, hooks, agents, and skills across 102 static rules with optional red-team/blue-team Opus pipeline |
| Pattern learning from sessions is manual and ephemeral | Continuous learning v2 with instinct-based learning, confidence scoring, and `/evolve` to cluster instincts into reusable skills |
| Cross-harness setup (Claude Code, Codex, Cursor) requires duplication | Single plugin install distributes skills, commands, and agents; `./install.sh` targets specific harnesses |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 61,773 | 2026-03-06 |
| Forks | 7,645 | 2026-03-06 |
| Open Issues | 20 | 2026-03-06 |
| Contributors | 30+ | 2026-03-06 |
| Latest Release | v1.8.0 | 2026-03-06 |
| Internal Tests | 997 | 2026-03-06 |
| Skills | 65+ | 2026-03-06 |
| Agents | 16 | 2026-03-06 |
| Commands | 40+ | 2026-03-06 |
| npm weekly downloads (ecc-universal) | Published | 2026-03-06 |
| GitHub App installs | 150+ | 2026-03-06 |
| Languages supported | 6 | 2026-03-06 |
| Created | 2026-01-18 | 2026-03-06 |

---

## Key Features

### Skills Library (65+)

- **Coding standards** — language best practices (TypeScript, Python, Go, Java, C++, Swift)
- **Backend patterns** — API, database, caching, migration patterns (Prisma, Drizzle, Django, Go)
- **Frontend patterns** — React, Next.js, HTML slide decks (`frontend-slides`)
- **TDD workflows** — test-driven development for all supported languages
- **Verification loops** — continuous verification with checkpoint/eval harness
- **Continuous learning v2** — instinct-based pattern extraction with confidence scoring
- **Security** — security review checklists and AgentShield integration
- **Iterative retrieval** — progressive context refinement for subagents
- **Strategic compact** — manual compaction suggestions for long sessions
- **Business skills** — article-writing, content-engine, market-research, investor-materials
- **Autonomous loops** — sequential pipelines, PR loops, DAG orchestration patterns
- **Plankton code quality** — write-time enforcement via PostToolUse hooks

### Agents (16)

- `planner.md` — feature implementation planning
- `architect.md` — system design decisions
- `tdd-guide.md` — test-driven development guidance
- `code-reviewer.md` — quality and security review
- `security-reviewer.md` — vulnerability analysis
- `build-error-resolver.md` — automated build fix
- `e2e-runner.md` — Playwright E2E testing
- `refactor-cleaner.md` — dead code cleanup
- `doc-updater.md` — documentation sync
- `go-reviewer.md`, `go-build-resolver.md` — Go-specific agents
- `python-reviewer.md` — Python code review
- `database-reviewer.md` — Database/Supabase review

### Commands (40+)

- `/plan` — implementation planning
- `/tdd` — test-driven development
- `/code-review` — quality review
- `/orchestrate` — multi-agent coordination
- `/multi-plan`, `/multi-execute`, `/multi-backend`, `/multi-frontend`, `/multi-workflow` — multi-service orchestration
- `/pm2` — PM2 service lifecycle management
- `/learn`, `/learn-eval`, `/evolve` — continuous learning pipeline
- `/instinct-status`, `/instinct-import`, `/instinct-export` — instinct management
- `/checkpoint`, `/verify`, `/eval` — verification loop
- `/security-scan` — AgentShield security auditor
- `/skill-create` — generate skills from git history
- `/skill-stocktake` — audit skill and command quality
- `/harness-audit`, `/loop-start`, `/loop-status`, `/quality-gate`, `/model-route` — harness controls (v1.8.0)
- `/sessions` — session history management

### Hooks System

- **SessionStart** — load context from previous session on startup
- **Stop-phase** — session summaries saved on agent stop
- **PreCompact** — state saving before context compaction
- **PostToolUse** — write-time code quality enforcement
- **Hook runtime controls** — `ECC_HOOK_PROFILE=minimal|standard|strict` and `ECC_DISABLED_HOOKS=...` for runtime gating without file edits
- **Script-based hooks** — Node.js scripts replacing fragile inline one-liners for cross-platform reliability

### Rules Architecture

- `common/` — language-agnostic principles: coding-style, git-workflow, testing (80% coverage), performance, patterns, hooks, agents, security
- `typescript/`, `python/`, `golang/` — language-specific rule sets
- Per-language installation: `./install.sh typescript` (or `python`, `golang`, or multiple)
- Multi-target support: `./install.sh --target cursor typescript`

### AgentShield Security Scanner

- 1,282 tests, 98% coverage, 102 static analysis rules
- Scans: CLAUDE.md, settings.json, MCP configs, hooks, agents, skills
- 5 scan categories: secrets detection (14 patterns), permission auditing, hook injection analysis, MCP server risk profiling, agent config review
- `--opus` flag runs red-team/blue-team/auditor pipeline using Claude Opus 4.6
- Output formats: terminal (A–F grading), JSON, Markdown, HTML
- Exit code 2 on critical findings for CI build gates

### Cross-Platform Support

- **Claude Code** — primary target; plugin distributed via `/plugin install`
- **OpenAI Codex** — `AGENTS.md`-based support with installer targeting
- **Cursor** — `--target cursor` install flag
- **OpenCode** — full integration (12 agents, 24 commands, 16 skills, 20+ hook event types)
- **Package manager detection** — auto-detects npm/pnpm/yarn/bun; configurable via env var or project config

---

## Technical Architecture

ECC follows a layered Claude Code plugin structure with Node.js scripts for cross-platform hook reliability:

```text
everything-claude-code/
├── .claude-plugin/          # Plugin and marketplace manifests
├── agents/                  # 16 specialized subagents
├── skills/                  # 65+ domain skill directories
├── commands/                # 40+ slash command definitions
├── rules/                   # common/ + per-language rule sets
├── hooks/
│   ├── hooks.json           # All hook event bindings
│   └── memory-persistence/  # Session lifecycle hooks
├── scripts/
│   ├── lib/                 # Shared utilities (cross-platform file, path, PM detection)
│   └── hooks/               # Node.js hook implementations
├── tests/                   # 997-test suite (lib + hooks)
├── contexts/                # Dynamic system prompt injection (dev, review, research)
├── examples/                # Real-world CLAUDE.md examples (SaaS, Go, Django, Rust)
└── mcp-configs/             # MCP server configurations (GitHub, Supabase, Vercel, Railway)
```

**Key architectural patterns**:

- **Hook runtime gating** — `ECC_HOOK_PROFILE` and `ECC_DISABLED_HOOKS` env vars allow runtime strictness tuning without editing hook files
- **Script-based hooks** — all hooks implemented as Node.js scripts (`scripts/hooks/*.js`) for Windows/macOS/Linux compatibility
- **Shared lib layer** — `scripts/lib/utils.js` and `package-manager.js` provide cross-platform primitives reused by all scripts
- **Instinct learning pipeline** — sessions → `/learn` extract → confidence scoring → `/evolve` cluster → SKILL.md output
- **AgentShield red-team pipeline** — attacker agent finds exploit chains → defender evaluates protections → auditor synthesizes into prioritized risk assessment

---

## Installation & Usage

```bash
# Add ECC marketplace to Claude Code
/plugin marketplace add affaan-m/everything-claude-code

# Install the plugin
/plugin install everything-claude-code@everything-claude-code

# Clone for rules installation (rules cannot be distributed via plugin)
git clone https://github.com/affaan-m/everything-claude-code.git
cd everything-claude-code

# Install rules for your languages
./install.sh typescript python  # or golang, or multiple

# Target a specific harness
./install.sh --target cursor typescript

# Configure package manager preference
export CLAUDE_PACKAGE_MANAGER=pnpm
# or via project config
node scripts/setup-package-manager.js --project bun
```

```bash
# Quick security scan (no install needed)
npx ecc-agentshield scan

# Deep analysis with Opus red-team pipeline
npx ecc-agentshield scan --opus --stream

# Auto-fix safe issues
npx ecc-agentshield scan --fix

# Generate secure config from scratch
npx ecc-agentshield init
```

```bash
# Hook strictness control at runtime
export ECC_HOOK_PROFILE=minimal          # or standard (default) or strict
export ECC_DISABLED_HOOKS="pre:bash:tmux-reminder,post:edit:typecheck"

# Harness audit (v1.8.0)
/harness-audit

# Loop controls (v1.8.0)
/loop-start
/loop-status
/quality-gate
/model-route
```

---

## Relevance to Claude Code Development

### Applications

- **Baseline skills library** — adopt ECC's 65+ skills as a reference for Claude Code enhancement; the continuous-learning and iterative-retrieval skills directly apply to this repository's skill collection
- **Hook patterns** — ECC's script-based hook architecture (Node.js, cross-platform, runtime-gatable) is a model for robust hook design in any Claude Code project
- **Multi-language rules** — the `common/` + per-language directory structure is a reusable pattern for distributing coding standards via Claude Code rules
- **AgentShield integration** — use `/security-scan` to audit this repository's CLAUDE.md, settings.json, MCP configs, and agent definitions for security issues
- **Harness audit commands** — `/harness-audit`, `/quality-gate`, and `/model-route` provide operational visibility into agent harness performance

### Patterns Worth Adopting

- **`ECC_HOOK_PROFILE` runtime gating** — decoupling hook strictness from config files via env vars prevents hook breakage during development; applicable to any hook-heavy project
- **Script-based hooks over inline one-liners** — Node.js scripts in `scripts/hooks/` are testable, versioned, and cross-platform; inline bash hooks break on Windows and are hard to debug
- **Confidence-scored instinct learning** — the `continuous-learning-v2` skill's confidence scoring prevents low-quality patterns from polluting skill libraries
- **997-test coverage for configuration** — testing skills, hooks, commands, and agents as code prevents configuration drift and regression
- **Red-team/blue-team security pipeline** — the AgentShield `--opus` flag pattern is applicable whenever adversarial analysis of AI configuration is needed

### Integration Opportunities

- **Add AgentShield to CI** — run `npx ecc-agentshield scan` in `.github/workflows/code-quality.yml` to continuously audit Claude Code configuration for security regressions
- **Adopt `continuous-learning-v2` skill** — integrate ECC's instinct-based learning pipeline to extract patterns from this repository's development sessions
- **Cross-reference skill libraries** — compare this repository's skill collection against ECC's 65+ skills to identify coverage gaps or duplication
- **Use ECC's `examples/` as CLAUDE.md templates** — ECC's real-world CLAUDE.md examples (SaaS, Go microservice, Django, Rust API) are directly reusable as starting points for project configurations

### Competitive Analysis

| Tool | Skills | Agents | Commands | Hooks | Security | Languages | Stars |
|------|--------|--------|----------|-------|----------|-----------|-------|
| Everything Claude Code | 65+ | 16 | 40+ | Yes (Node.js) | AgentShield (102 rules) | 6 | 61.7K |
| Softaworks Agent Toolkit | 43 | 6 | 7 | No | No | 1 | 621 |
| Claude Code Templates | 100+ | Yes | Yes | Yes | No | 1 | 21.8K |
| Skrills | 0 (validates) | 0 | 39 CLI | No | No | Rust | 52 |
| SkillKit | 15K+ (registry) | 32 | No | No | No | Universal | — |

---

## References

- [GitHub Repository](https://github.com/affaan-m/everything-claude-code) (accessed 2026-03-06)
- [GitHub API — Repository Metadata](https://api.github.com/repos/affaan-m/everything-claude-code) (accessed 2026-03-06)
- [npm — ecc-universal](https://npmjs.com/package/ecc-universal) (accessed 2026-03-06)
- [npm — ecc-agentshield](https://npmjs.com/package/ecc-agentshield) (accessed 2026-03-06)
- [GitHub App — ECC Tools](https://github.com/marketplace/ecc-tools) (accessed 2026-03-06)
- [AgentShield Repository](https://github.com/affaan-m/agentshield) (accessed 2026-03-06)
- [v1.8.0 Release Notes](https://github.com/affaan-m/everything-claude-code/releases) (accessed 2026-03-06)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Agent Skills Eval](../evaluation-testing/agent-skills-eval.md) | evaluation-testing | referenced by Agent Skills Eval (evaluation-testing) |

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | 2026-03-06 |
| Version at Verification | v1.8.0 |
| Next Review Recommended | 2026-06-06 |
