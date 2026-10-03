---
name: gentle-ai
title: Gentle-AI™
subtitle: Deterministic engineering environment for AI coding agents with persistent memory and workflow
research_date: 2026-10-02
source_url: https://github.com/Gentleman-Programming/gentle-ai
github_repository: https://github.com/Gentleman-Programming/gentle-ai
version_at_research: v4.0.0
license: MIT
freshness_tracking:
  last_verified: 2026-10-03
  version_at_verification: v4.0.0
  next_review: 2026-12-02
  confidence_map: "Overview: medium (several claims appear only in PRD.md, a design document: port 7437, 8+ providers, SHA256 two-level cache, 30+ skill files, installer phases, persona) | Problem Addressed: medium (same PRD-only basis) | Key Features: medium (same PRD-only basis) | Technical Architecture: medium (doc-derived; no source files are listed in References) | Installation & Usage: medium (install flags checked against docs/non-interactive.md and docs/usage.md at clone 5140c5f, 2026-10-03) | Limitations and Caveats: medium (docs clone; partial coverage) | Relevance to Claude Code Development: high"
---

# Gentle-AI™

## Overview

Gentle-AI is a deterministic engineering environment that enhances AI coding agents with persistent memory, structured workflows, and code review integration. Rather than installing a new AI agent, Gentle-AI configures an agent the user already has (Claude Code, OpenCode, Cursor, VS Code, Gemini CLI, Codex, or 11 others) by injecting the Gentleman ecosystem: persistent session memory through Engram, structured development workflows (ODD and RDD), pre-commit code review (GGA), curated coding skills, and MCP server integrations.

The problem it solves is that AI agents by default forget everything between sessions and have no opinion about workflow or code quality. Gentle-AI gives agents memory, a deterministic workflow, and evidence-based review.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| **Session amnesia** — AI agents forget decisions, bugs, and conventions every time a session ends | **Engram** — Persistent cross-session memory system (SQLite + FTS5) that saves discoveries, decisions, and file locations so the agent resumes with full context next session |
| **No development workflow** — Agents write code on demand without planning, authorization, or verification gates | **ODD (Organic Driven Development)** — Lightweight workflow that explores before changing code, creates persistent task artifacts for substantial work, and verifies implementation against requirements |
| **No code review** — Code written by agents has no pre-commit validation against team standards | **GGA (Guardian Angel)** — AI-powered code review tool that blocks commits violating team standards (configured in AGENTS.md), with smart caching and support for 8+ AI providers (Claude, Gemini, Ollama, LM Studio, GitHub Models, etc.) |
| **Fragmented configuration** — Each AI coding agent has different config paths, formats, and capabilities; setting up one agent takes days and doesn't transfer to others | **Multi-agent installer** — Single `gentle-ai install` command configures 17 agents with identical ecosystem components: Engram, SDD skills, GGA, MCP servers, persona, and theme |
| **Limited skill library** — No curated patterns for modern stacks (React 19, Next.js 15, TypeScript, Tailwind 4, Zod 4, etc.) | **Skills library** — Project-aware coding patterns installed automatically and selectable by category; skills are loaded based on file context |
| **No long-term learning** — No way for multiple sessions or multiple agents to share what they learned | **Cross-session + cross-agent memory** — Engram syncs memories across all agents a developer uses, so switching from Claude Code to OpenCode preserves context |

---

## Key Features

### Engram™ — Persistent Cross-Session Memory

Engram saves project decisions and discoveries to a local SQLite database and makes them searchable via full-text search (FTS5). When a new session starts, the agent queries Engram before querying the user, so context accumulates instead of resetting.

- **Memory types**: Decisions, bugs, conventions, file locations, architecture notes
- **Search**: FTS5 full-text search across all saved observations
- **Sync**: Git sync for teams; shared memories across agents
- **Integration**: Automatic plugins for Claude Code (native hooks + MCP), OpenCode (TypeScript plugin), Gemini CLI (system.md), Codex
- **Server**: Runs on localhost:7437 and can auto-start on system boot

### ODD (Organic Driven Development) — Lightweight Workflow

ODD authorizes changes before implementation and keeps small work small. For substantial changes, it creates a persistent task artifact (`odd/tasks/<feature-name>.md`) with scope, tasks, evidence, and next steps. The agent explores existing code in read-only mode, asks only about decisions it cannot safely make, and implements authorized work with applicable checks (Strict TDD when enabled).

- **Scope tracking**: Persistent task documents for features that span multiple sessions
- **Authorization gate**: Explicit decision required before implementation
- **TDD support**: Runs configured test suite in RED-GREEN-REFACTOR cycle when enabled
- **Work units**: Final commits follow ODD protocol for resumable progress

### RDD (Receipt-Driven Development) — Deterministic Review

RDD freezes a code change candidate to a specific revision before review, ensuring evidence belongs to the exact version being committed. It is enabled by default but opt-out via `gentle-ai review mode disable`.

- **Frozen candidate**: Change is locked to a lineage, revision, and target before any lens is applied
- **Risk-based depth**: Passive review (structural readback, zero reviewer lenses) → Medium (one focused lens) → High (canonical 4R: Risk, Resilience, Readability, Reliability)
- **Bounded correction**: At most one correction is allowed; delivery remains human-owned
- **Deterministic**: `gentle-ai` binary reads state from disk and returns only the valid next transition (Working, Checking, Ready, or Needs your decision)

### GGA (Guardian Angel) — AI Code Review

Pre-commit hook that validates staged files against team standards defined in `AGENTS.md`. Supports 8+ AI providers with smart SHA256-based caching (only PASSED files cached).

- **Multi-provider**: Claude Code, Gemini CLI, Codex, OpenCode, Ollama, LM Studio, GitHub Models
- **Standard rules**: Single `AGENTS.md` file per project defines team coding standards (version control friendly)
- **Caching**: Two-level SHA256 invalidation (metadata + file content)
- **Modes**: Pre-commit hook, PR mode (`--pr-mode`), CI mode (`--ci`)

### Multi-Agent Support — 17 Integrations

Gentle-AI configures any of 17 AI coding agents with identical ecosystem components. Each integration uses the agent's native capabilities, so available features (delegation, RDD review) differ by agent.

**Supported agents** (the 17 listed in `docs/agents.md` lines 12-28): Claude Code, OpenCode, Kilo Code, Gemini CLI, Cursor, VS Code Copilot, Codex, Windsurf, Antigravity, Kimi Code, Qwen Code, Kiro IDE, OpenClaw, Trae, Pi, Hermes, Conductor

**Ecosystem support tiers**:
- **Full** (Claude Code, OpenCode): Engram plugin, MCP servers, skills, SDD orchestrator, GGA integration, persona, theme, permissions, statusline, hooks
- **Good** (Cursor, VS Code): Skills, MCP servers, SDD (inline mode), GGA as review provider, persona rules
- **Partial** (Gemini CLI, Codex, Windsurf): Skills via system instructions, MCP where supported, GGA provider config, persona
- **Minimal** (Antigravity, emerging agents): Persona and coding conventions via project/workspace rules

Tier labels come from `PRD.md` lines 225-237 (a design document, which also lists Xcode as a planned P2 Minimal item; Xcode is not among the 17 integrations in `README.md` or `docs/agents.md`). `docs/agents.md` lists the 17 agents with per-agent integration notes and defines no tiers, so treat the tiers as PRD-level design intent.

### SDD (Spec-Driven Development) Skills — 9 Skills

Integration with the separate `sdd-agent-team` repository. Nine skills cover the complete workflow from exploration through implementation, verification, and archival.

- **Skills**: sdd-init, sdd-explore, sdd-propose, sdd-spec, sdd-design, sdd-tasks, sdd-apply, sdd-verify, sdd-archive
- **Auto-invocation**: OpenCode automatically offers SDD phases when it detects a substantial change
- **Orchestrator**: Configuration injected into agent global config (CLAUDE.md, opencode agents, .cursorrules)

### Skills Library — Curated Coding Patterns

Automatically loaded based on file context (React detected → load react-19 skill, TypeScript file → load typescript-strict skill).

**Skills available**: React 19, Next.js 15, Tailwind 4, Zod 4, AI SDK 5 (Vercel), TypeScript (strict), Testing (Playwright, Pytest, Go), Django + DRF, Claude Developer Platform, PR review, Homebrew release

### MCP Servers Integration

Configures MCP (Model Context Protocol) servers for each selected agent, providing live access to documentation and project management tools.

- **Context7**: Up-to-date library documentation (no auth required, enabled by default)
- **Notion**: Project management integration
- **Jira/Atlassian**: Issue tracking integration
- **Custom**: User-defined MCP servers

### Persona & Configuration — "Your Own Gentleman!"

Optional persona mode (selected during install, not forced).

- **Gentleman Mode**: Senior Architect mentor who teaches, challenges, and pushes toward understanding. Spanish input (Rioplatense) when available. Analogies reference Tony Stark/JARVIS.
- **Neutral Mode**: Professional, helpful, no personality overlay; security permissions still applied
- **Custom Mode**: Bring your own persona description
- **Security-first**: Permissions are not optional — deny `.env` access, require confirmation for destructive git operations regardless of persona choice
- **Theme**: Custom dark theme (navy/steel/gold) available; default also supported
- **Thinking verbs**: Custom spinner text with Rioplatense phrases (Gentleman mode only)

### Also Included

| Component | What it does |
|-----------|-------------|
| **Config backups** | Snapshotted before every single write; restore via `gentle-ai restore latest` (Source: `docs/rollback.md` line 68) |
| **Doctor** | `gentle-ai doctor` — read-only health report on installation state and dependencies |
| **Skill registry** | Auto-discovered at startup; manually refresh with `gentle-ai skill-registry refresh --force` |
| **Self-update** | `gentle-ai update` checks and upgrades the binary |
| **Sync** | `gentle-ai sync` refreshes managed agent assets; dry-run available with `--dry-run` |
| **Uninstall** | Removes managed configuration; inspect scope before confirming |

---

## Technical Architecture

### Installation Pipeline

The installer (`gentle-ai install`) runs seven phases:

1. **System Detection**: Detects OS, architecture, WSL/Termux, installed agents, dependencies, existing configs
2. **User Choices**: Persona (Gentleman/Neutral/Custom), preset (Dev Stack + Polish / Dev Stack / Memory Only / Custom), component selection
3. **Backup**: Snapshots existing configs to `~/.gentle-ai-backup-TIMESTAMP/` before any changes
4. **Dependencies**: Installs base tools (Homebrew, Node.js 20+, git) — shows full dependency tree before installing
5. **Core Components**: Installs Engram binary, GGA binary, missing agents
6. **Agent Configuration**: For each selected agent, injects Engram plugin/MCP, copies skills, configures SDD orchestrator, applies persona and theme
7. **Verification**: Health checks (Engram port 7437, skills files, MCP configs, GGA binary) before completion

Source repositories fetched at install time:
- `Gentleman-Programming/sdd-agent-team` — SDD skills
- `Gentleman-Programming/engram` — Engram binary and plugins
- `Gentleman-Programming/gentleman-guardian-angel` — GGA binary
- Skills Registry — 30+ skill files

### Agent Configuration Strategy

Configuration is **agent-agnostic** after installation: the same Engram database, skills directory, and rules file (AGENTS.md) are used by all 17 agents.

**Per-agent injection points**:
- **Claude Code** (`~/.claude/`): CLAUDE.md (persona + SDD orchestrator), settings.json (permissions, theme), skills/, plugins/ (Engram plugin), ~/.claude.json (MCP servers)
- **OpenCode** (`~/.config/opencode/`): opencode.json (agents, MCP, Engram plugin, theme), skill/ (SDD + coding skills), commands/ (SDD slash commands), plugins/ (engram.ts)
- **Cursor** (`~/.cursor/`): .cursorrules (persona + SDD inline), skills/, MCP config
- **Gemini CLI** (`~/.gemini/`): settings.json (MCP: Engram), system.md (memory protocol + persona)
- **GGA** (`~/.config/gga/`): config (provider selection, timeout)

### Engram Memory System

**Components**:
- **Engram server** (Go binary): Runs on localhost:7437, handles mem_session_start, mem_search, mem_save, mem_session_summary
- **SQLite + FTS5**: `~/.engram/engram.db` stores observations with full-text indexing
- **Agent plugins**: Claude Code (hooks + MCP), OpenCode (TS plugin), Gemini CLI (MCP), others (MCP)

**Data flow**:
1. Agent session starts → Plugin calls `mem_session_start(project_name)`
2. Engram returns previous context (recent sessions, decisions, bugs)
3. Agent works, periodically calls `mem_search(topic)` for related past work
4. Agent calls `mem_save(observation, type: decision|bug|pattern)`
5. Session ends → Plugin calls `mem_session_summary(goal, discoveries, accomplished, files)`

**Cross-agent sync**: All 17 agents read/write the same `~/.engram/engram.db`, so context flows freely between Claude Code, OpenCode, Cursor, etc.

### Component Ownership

- **Installer**: Dependency resolution, binary installation, config generation, skill file copying, backup/restore, health verification
- **Engram**: Memory persistence, session tracking, FTS5 search, cross-agent sync, git sync for teams
- **GGA**: Pre-commit review, file caching, multi-provider routing, PR/CI modes
- **Agent**: Code generation, skill interpretation, SDD orchestration, MCP tool usage, persona behavior
- **User**: API keys & auth, AGENTS.md rules, project-level .gga config, which agents to use

---

## Installation & Usage

### Install

```bash
# macOS (Homebrew)
brew install gentleman-programming/tap/gentle-ai

# macOS / Linux (curl)
curl -fsSL https://raw.githubusercontent.com/Gentleman-Programming/gentle-ai/main/scripts/install.sh | bash

# Windows (PowerShell) — Go 1.25.10+ required for source install
go install github.com/gentleman-programming/gentle-ai/v4/cmd/gentle-ai@v4.0.0
```

### Interactive Setup

```bash
gentle-ai              # TUI walks through agent, persona, preset, components
gentle-ai doctor       # Verify installation (read-only)
```

### Non-Interactive (CI/Automation)

```bash
gentle-ai install \
  --agent claude-code,opencode \
  --component engram,skills \
  --skill go-testing \
  --persona gentleman \
  --preset full-gentleman \
  --dry-run
```

Source: `docs/non-interactive.md` lines 50-57 (shown there as `go run ./cmd/gentle-ai install ...`; `docs/usage.md` lines 152-156 shows the `gentle-ai install --agent ... --preset full-gentleman` form). `--dry-run` renders the plan without executing; drop it to apply. `--preset` values per `docs/usage.md` line 355: `full-gentleman`, `ecosystem-only`, `minimal`, `custom`; `--persona` values: `gentleman`, `neutral`, `custom`. Neither `docs/non-interactive.md` nor `docs/usage.md` documents a `--non-interactive` or `--mcp` flag, so the earlier example's `--non-interactive`, `--mcp` and `--skills full-stack` (found only in `PRD.md`, a design document) are not used. Accessed 2026-10-03.

### Typical Workflow (After Installation)

**Small change (ODD read-only)**:

```text
describe task → agent explores → asks clarifying questions → implements
(no persistent task file for small changes)
```

**Large feature (ODD with task artifact)**:

```text
gentle-ai skill-registry refresh --force
describe feature → agent creates odd/tasks/feature-name.md → explores → proposes → spec → design → tasks → implements → verifies → archives
(context resumes across sessions via Engram)
```

**On commit**:

```text
git commit → GGA pre-hook runs → validates against AGENTS.md rules → allows or blocks
```

**Review**:

```text
gentle-ai review mode enable      # Enable RDD
(on suitable changes, agent documents risk assessment)
gentle-ai review mode disable     # Turn off RDD if not needed
```

**Maintenance**:

```bash
gentle-ai update                  # Check and upgrade the binary
gentle-ai sync --dry-run          # Preview managed asset updates
gentle-ai sync                    # Refresh skills, MCP, agent config
gentle-ai uninstall               # Remove managed configuration
```

---

## Limitations and Caveats

- **RDD review lifecycle is runtime-limited**: "This lifecycle is available only to Claude Code, Codex, OpenCode, and Pi. Unsupported runtimes fail before repository or authority mutation." (Source: `docs/review-integration.md` line 45, shallow clone of Gentleman-Programming/gentle-ai at commit 5140c5f, accessed 2026-10-03)
- **OpenCode background jobs are non-durable**: "Optional background jobs are process-local and non-durable; do not use them for dependent work or parallel writers in one worktree." (Source: `docs/agents.md` line 39, same clone)
- **Pi runtime behavior is not owned by this binary**: "Installing or updating this binary does not itself establish Pi behavior parity." (Source: `README.md` line 171, same clone)
- **Feature availability differs per agent**: the support tiers in Key Features (Full, Good, Partial, Minimal) mean delegation and RDD review are not uniform across the 17 integrations.
- Not mentioned in documentation: measured performance, memory-store size limits, or concurrency guarantees for the shared `~/.engram/engram.db` across simultaneously running agents; none were found in the files read.

---

## Relevance to Claude Code Development

### Applications

- **Multi-session context preservation** -> `plugins/development-harness/agents/backlog-item-groomer.md`
  - Term: `cross-session`
  - Today: "Your `memory: project` frontmatter field gives you a persistent, cross-session memory directory (see the platform's standard memory-directory conventions — do not hardcode its path here)."
  - Change: none — `plugins/development-harness/agents/backlog-item-groomer.md` already gives this agent a persistent cross-session memory directory; Engram would add only a full-text-searchable store shared across harnesses, mapped under Integration Opportunities

- **Deterministic workflow state machine** -> `plugins/development-harness/docs/backlog-lifecycle.md`
  - Term: `item statuses`
  - Today: "This document defines the desired item statuses, the route that writes each status, and the gates"
  - Change: none — out of scope (this document already defines the statuses, the route that writes each status and the gates; ODD's authorization gate would duplicate it, and the entry documents no transition API that dh could call)

- **Agent memory and skill management** -> `plugins/python-engineering/agents/code-reviewer.md`
  - Term: `agent memory`
  - Today: "Update your agent memory as you discover codepaths, patterns, library"
  - Change: none — `plugins/python-engineering/agents/code-reviewer.md` already instructs per-agent memory updates; Engram's cross-agent SQLite + FTS5 store has no counterpart in that file

- **Cross-agent skill synchronization** -> `AGENTS.md`
  - Term: `cross-harness`
  - Today: "Plugins are expected to be developed cross-harness compatible (claude-code, codex, hermes, kimi)."
  - Change: none — `scripts/generate_harness_compatibility.py` and `AGENTS.md` line 94 already cover cross-harness generation, so gentle-ai's single-installer approach to 17 agents adds no missing mechanism here

### Patterns Worth Adopting

- **Pre-commit validation as a gate, not a suggestion** -> `.claude/agents/code-review.md`
  - Term: `code review`
  - Today: "You are a senior code reviewer ensuring high code quality, security, and consistency with established codebase/project patterns."
  - Change: edit `.pre-commit-config.yaml` to add a local hook that runs an AI review of staged files against `AGENTS.md`; today `.claude/agents/code-review.md` is invoked only on request (its description reads "DO NOT use proactively"). The GGA invocation is not documented in this entry, so the hook's `entry:` command is unconfirmed

### Integration Opportunities

- **Persistent project memory across Claude Code sessions** -> `plugins/plugin-creator/skills/memory-and-rules/SKILL.md`
  - Term: `persistent memory`
  - Today: "Claude Code has two kinds of persistent memory:"
  - Change: edit `plugins/development-harness/backlog_core/` to store architectural decisions and design rationale alongside task tracking, queryable like Engram's `mem_search`; Engram itself parallels the memory layers documented in this file but adds a full-text-searchable store

- **Cross-session context preservation across agents** -> `plugins/development-harness/agents/classifier.md`
  - Term: `cross-session`
  - Today: "Your `memory: project` frontmatter field gives you a persistent, cross-session memory directory (see the platform's standard memory-directory conventions — do not hardcode its path here)."
  - Change: none — dh agents already use `memory: project` for cross-session context; Engram would add only a shared database searchable across Claude Code, OpenCode and Cursor

---

## References

- [Gentle-AI GitHub Repository](https://github.com/Gentleman-Programming/gentle-ai) (accessed 2026-10-02)
- [Gentle-AI README.md](https://github.com/Gentleman-Programming/gentle-ai/blob/main/README.md) (accessed 2026-10-02)
- [Intended Usage Documentation](https://github.com/Gentleman-Programming/gentle-ai/blob/main/docs/intended-usage.md) (accessed 2026-10-02)
- [Architecture Documentation](https://github.com/Gentleman-Programming/gentle-ai/blob/main/docs/architecture.md) (accessed 2026-10-02)
- [Review Integration (RDD)](https://github.com/Gentleman-Programming/gentle-ai/blob/main/docs/review-integration.md) (accessed 2026-10-02)
- [Engram Memory System](https://github.com/Gentleman-Programming/gentle-ai/blob/main/docs/engram.md) (accessed 2026-10-02)
- [Agents Matrix (17 Integrations)](https://github.com/Gentleman-Programming/gentle-ai/blob/main/docs/agents.md) (accessed 2026-10-02)
- [Product Requirements Document (PRD)](https://github.com/Gentleman-Programming/gentle-ai/blob/main/PRD.md) (accessed 2026-10-02)
- [Non-interactive install documentation](https://github.com/Gentleman-Programming/gentle-ai/blob/main/docs/non-interactive.md) (accessed 2026-10-03)
- [Usage documentation](https://github.com/Gentleman-Programming/gentle-ai/blob/main/docs/usage.md) (accessed 2026-10-03)
- [Rollback documentation](https://github.com/Gentleman-Programming/gentle-ai/blob/main/docs/rollback.md) (accessed 2026-10-03)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Flue](./flue.md) | agent-frameworks | Both provide comprehensive agent execution frameworks; gentle-ai emphasizes multi-agent configuration and memory while flue provides durable-first runtime and sandboxing |
| [Everything Claude Code](./everything-claude-code.md) | agent-frameworks | Both optimize Claude Code agent workflows through integrated harnesses; gentle-ai provides ecosystem orchestration and memory while everything-claude-code adds performance optimization |
| [SimpleMem Cross](../context-management/simplemem-cross.md) | context-management | Both implement persistent memory for AI agents; Engram emphasizes cross-session project discoveries while simplemem-cross focuses on cross-conversation LLM context preservation |
| [Pi Mono](./pi-mono.md) | agent-frameworks | Both unify multi-agent infrastructure; gentle-ai handles configuration and workflow determinism across 17 agents while pi-mono provides runtime infrastructure and API layers |
| [Micro Agent](./micro-agent.md) | agent-frameworks | Both support MCP-driven agent development with deterministic workflows; micro-agent is lightweight while gentle-ai adds production-scale orchestration and memory |
| [LiteAgents](./liteagents.md) | agent-frameworks | Both provide multi-agent toolkits with persistent session memory; liteagents emphasizes rapid development while gentle-ai adds workflow gates and code review |
| [Superpowers](./superpowers.md) | agent-frameworks | Both provide agentic skill frameworks; gentle-ai's SDD orchestration and pre-commit GGA align with superpowers' methodology-driven skill approach |
| [Claude Code Harness](./claude-code-harness.md) | agent-frameworks | Both enhance Claude Code workflows; gentle-ai provides ecosystem configuration and cross-session memory while claude-code-harness provides runtime verification and guardrails |
