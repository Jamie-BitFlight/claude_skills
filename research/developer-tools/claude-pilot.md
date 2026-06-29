---
title: "Claude Pilot"
research_date: "2026-02-23"
source_url: "https://github.com/maxritter/claude-pilot"
github_url: "https://github.com/maxritter/claude-pilot"
version_at_research: "v6.10.2"
license: "Proprietary — Commercial (subscription required, 7-day free trial; source code viewable for inspection only, output belongs to the user)"
last_verified: "2026-02-23"
version_at_verification: "v6.10.2"
next_review: "2026-05-23"
---

## Overview

Claude Pilot is a quality-enforcement layer for Claude Code CLI that makes AI-generated code production-reliable without restructuring existing projects. It installs alongside any codebase via a single `curl` command and activates 15 lifecycle hooks that automatically lint, format, and type-check every file edit, enforce TDD (RED → GREEN → REFACTOR), preserve context across auto-compaction boundaries, and route planning phases to Opus and execution phases to Sonnet. The `/spec` command adds a structured Discuss → Plan → Approve → Implement → Verify loop with isolated git worktrees and parallel code-review sub-agents, enabling fully unattended feature delivery.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Claude Code skips tests, loses context, and produces inconsistent results on complex codebases | 15 lifecycle hooks enforce TDD, quality checks, and context preservation on every session |
| Quality guardrails are optional suggestions that Claude ignores when context gets tight | PostToolUse hooks (`file_checker.py`, `tdd_enforcer.py`) fire on every single file edit — enforcement is structural, not advisory |
| Context degrades mid-task during auto-compaction | `pre_compact.py` snapshots active plan and task state; `post_compact_restore.py` re-injects it seamlessly after compaction |
| Complex features need plan approval before implementation | `/spec` generates a plan file, runs a plan-verifier sub-agent, waits for human approval, then implements in an isolated worktree |
| Code review is manual and happens after the fact | Three parallel verifier sub-agents (compliance, quality, goal) run automatically in the verify phase before squash merge |
| Every session starts fresh with no memory of prior work | Pilot Console (localhost:41777) provides browsable persistent memory across sessions via `mem-search` MCP server |
| Model selection is one-size-fits-all, burning budget on the wrong phases | Smart model routing: Opus for planning/verification (reasoning), Sonnet for implementation (speed/cost) |
| Setting up language servers and MCP servers requires manual configuration | 8-step installer auto-configures basedpyright, vtsls, gopls, and 5 MCP servers; idempotent re-runs with rollback on failure |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 1,390 | 2026-02-23 |
| Latest Release | v6.10.2 | 2026-02-22 |
| Contributors | 1 (maxritter) | 2026-02-23 |
| Release Total Downloads | ~49 (v6.10.2 pilot script) | 2026-02-23 |
| Hooks in Pipeline | 15 | 2026-02-23 |
| Built-in Rules | 10 (3 core workflow, 3 dev practices, 3 tools, 1 collaboration) | 2026-02-23 |
| Built-in Coding Standards | 5 (Python, TypeScript, Go, Frontend, Backend) | 2026-02-23 |
| MCP Servers | 5 (lib-docs, mem-search, web-search, grep-mcp, web-fetch) | 2026-02-23 |
| Language Servers | 3 (basedpyright, vtsls, gopls) | 2026-02-23 |

---

## Key Features

### Hooks Pipeline (15 hooks across 6 lifecycle events)

- **SessionStart** — Memory loader (blocking) restores persistent context; `post_compact_restore.py` re-injects active plan and task state after auto-compaction; session tracker initializes user message tracking
- **PreToolUse** — `tool_redirect.py` blocks WebSearch/WebFetch (MCP alternatives exist), blocks `EnterPlanMode`/`ExitPlanMode` (conflicts with `/spec`), hints Vexor for semantic Grep patterns
- **PostToolUse (every file edit)** — `file_checker.py` dispatches to language-specific checkers: Python (ruff + basedpyright), TypeScript (Prettier + ESLint + tsc), Go (gofmt + golangci-lint) with auto-fix; `tdd_enforcer.py` checks if implementation files were modified without failing tests; `context_monitor.py` warns at ~80% and ~90% effective context; memory observer captures development observations
- **PreCompact** — `pre_compact.py` (blocking) captures active plan, task list, and key context to persistent memory before auto-compaction fires
- **Stop** — `spec_stop_guard.py` (blocking) prevents session from ending if an active spec has PENDING or COMPLETE status
- **SessionEnd** — `session_end.py` stops worker daemon when no other Pilot sessions are active; session summarizer persists observations

### Spec-Driven Development (`/spec`)

- Discuss → Plan → Approve → Implement → Verify → Done loop
- Plan phase: Vexor semantic search explores entire codebase, asks clarifying questions, writes spec to `docs/plans/`, plan-verifier sub-agent validates completeness, waits for human approval (editable before proceeding)
- Implement phase: creates isolated git worktree on dedicated branch; implements each task sequentially with strict TDD (RED → GREEN → REFACTOR); quality hooks fire on every edit; full test suite runs after each task
- Verify phase: full test suite (unit, integration, E2E) + type checking + linting + actual program execution; three parallel review sub-agents (compliance, quality, goal); auto-fixes findings and re-verifies until clean; offers squash merge on success
- Multiple `/spec` tasks can run in parallel in separate worktrees

### Smart Model Routing

- **Planning & Plan Verification**: Opus (deep reasoning required for architecture design and gap detection)
- **Implementation**: Sonnet (fast, cost-effective with a clear spec)
- **Code Verification**: Opus (independent review requires same reasoning depth as planning)
- Configurable per-component via Pilot Console settings; global 1M-token context toggle

### Quick Mode

- Direct execution with zero overhead — no plan files, no worktrees, no approval gates
- All quality hooks (lint, format, type-check, TDD) still enforce on every edit
- Natural language task description: `pilot > Fix the null pointer bug in user.py`

### Persistent Memory & Pilot Console

- Local web dashboard at `localhost:41777` with Dashboard, Specifications, Memories, Sessions, Usage, Vault, and Settings views
- Cross-session memory via `mem-search` MCP server (observations automatically captured as decisions, discoveries, bugfixes)
- Smart Notifications via SSE when Claude needs input or a spec phase completes
- Usage view shows daily token costs and model routing breakdown

### Context Preservation Across Compaction

- Effective context gauge rescales raw Claude context (which reserves ~16.5% as compaction buffer) to 0–100% display with `▓` buffer indicator
- Warns at ~80% effective (informational) and ~90%+ effective (caution)
- `pre_compact.py` + `post_compact_restore.py` enable seamless continuation across any number of compaction cycles

### Online Learning (`/learn`)

- Captures non-obvious discoveries as reusable skills (triggers automatically after 10+ minute investigations)
- Creates custom skill files in the project's `.claude/` directory
- Skills can be shared across the team via `/vault`

### Team Vault (`/vault`)

- Share rules, commands, and skills via any private git repository (GitHub, GitLab, Bitbucket)
- Pull shared assets, push custom rules, version assets automatically (v1, v2, v3...)

### `/sync` — Codebase Learning

- Builds a Vexor semantic search index (first run: 5–15 min; subsequent runs: incremental)
- Explores project structure, discovers conventions and undocumented patterns
- Updates `project.md`, syncs MCP server documentation, creates new custom skills via `/learn`

### Built-in Rules & Coding Standards

- 10 built-in rules: task-and-workflow, testing (TDD), verification, development-practices, context-continuation, pilot-memory, research-tools, cli-tools, playwright-cli, team-vault
- 5 conditional coding standards activated by file type: Python (`*.py`), TypeScript/JavaScript (`*.ts/*.tsx/*.js/*.jsx`), Go (`*.go`), Frontend (`*.tsx/*.jsx/*.html/*.vue/*.css`), Backend (`**/models/**`, `**/routes/**`, `**/api/**`)

---

## Technical Architecture

<eg>
Claude Pilot Architecture
├── pilot binary (~/.pilot/bin/pilot)   — main entry point (Cython-compiled)
│   ├── Session management (parallel sessions, independent state)
│   ├── Worktree lifecycle (create/detect/diff/sync/cleanup)
│   ├── License/trial management (7-day trial, subscription check)
│   └── Context monitoring (check-context --json)
├── .claude/ plugin folder (installed per-project)
│   ├── rules/
│   │   ├── task-and-workflow.md         — core workflow rule
│   │   ├── testing.md                   — TDD enforcement rule
│   │   ├── verification.md              — completion requirements
│   │   ├── development-practices.md     — git, debugging, policies
│   │   ├── context-continuation.md      — compaction protocol
│   │   ├── pilot-memory.md              — memory workflow
│   │   ├── research-tools.md            — Context7, grep-mcp, web
│   │   ├── cli-tools.md                 — Pilot CLI + Vexor
│   │   ├── playwright-cli.md            — E2E browser testing
│   │   └── team-vault.md               — vault sharing
│   ├── standards/                       — file-type conditional rules
│   │   ├── python.md (*.py)
│   │   ├── typescript.md (*.ts/*.tsx)
│   │   ├── go.md (*.go)
│   │   ├── frontend.md (*.tsx/*.html)
│   │   └── backend.md (**/api/**)
│   ├── commands/
│   │   ├── spec.md  — spec-driven development
│   │   ├── sync.md  — codebase learning
│   │   ├── learn.md — online skill capture
│   │   └── vault.md — team asset sharing
│   └── hooks/                           — 15 hooks across 6 lifecycle events
│       ├── file_checker.py              — language-specific quality on every edit
│       ├── tdd_enforcer.py              — RED→GREEN→REFACTOR gate
│       ├── context_monitor.py           — effective context gauge
│       ├── tool_redirect.py             — block conflicting tools
│       ├── pre_compact.py               — snapshot state pre-compaction
│       ├── post_compact_restore.py      — restore state post-compaction
│       └── spec_stop_guard.py           — prevent premature session end
├── Pilot Console (localhost:41777)
│   ├── Worker daemon (real-time SSE notifications)
│   └── Memory DB (browsable observations, cross-session)
├── MCP Servers (auto-configured in .mcp.json)
│   ├── lib-docs    — library documentation lookup
│   ├── mem-search  — persistent memory search
│   ├── web-search  — DuckDuckGo, Bing, Exa
│   ├── grep-mcp    — GitHub code search
│   └── web-fetch   — web page fetching
└── LSP Servers (auto-configured in .lsp.json, stdio transport)
    ├── basedpyright (Python, strict type checking)
    ├── vtsls (TypeScript/Vue)
    └── gopls (Go)
</eg>

Installer (8-step, idempotent, rollback on failure):

1. Prerequisites check (Homebrew, Node.js, Python 3.12+, uv, git)
2. Dependencies (Vexor, playwright-cli, Claude Code)
3. Shell integration (bash, fish, zsh — `pilot` alias)
4. Config & Claude files (.claude/ plugin, rules, commands, hooks, MCP servers)
5. VS Code extensions
6. Dev Container auto-setup
7. Automated updater (checks on launch, one-key upgrade)
8. Cross-platform (macOS, Linux, Windows WSL2)

---

## Installation & Usage

```bash
# Install Pilot (macOS, Linux, Windows WSL2)
curl -fsSL https://raw.githubusercontent.com/maxritter/claude-pilot/main/install.sh | bash

# Install a specific version
export VERSION=6.10.2
curl -fsSL https://raw.githubusercontent.com/maxritter/claude-pilot/main/install.sh | bash

# Start Claude with Pilot enhancements (in your project folder)
pilot
# or
ccp

# Skip update check
pilot run --skip-update-check
```

```bash
# First time setup: learn your codebase
pilot
> /sync

# Spec-driven feature development
pilot
> /spec "Add user authentication with OAuth and JWT tokens"

# Quick mode (direct execution, all hooks still active)
pilot
> Fix the null pointer bug in user.py

# Capture a reusable skill from a session discovery
pilot
> /learn "Extract the debugging workflow we used for the race condition"

# Share team assets via private git repo
pilot
> /vault

# Start/stop trial
pilot trial --start
pilot trial --check --json

# License management
pilot activate <key>
pilot status --json

# Worktree management (used internally by /spec)
pilot worktree create --json <slug>
pilot worktree diff --json <slug>
pilot worktree sync --json <slug>
pilot worktree cleanup --json <slug>

# Uninstall
curl -fsSL https://raw.githubusercontent.com/maxritter/claude-pilot/main/uninstall.sh | bash
```

---

## Relevance to Claude Code Development

### Applications

- Direct peer project to this repository: both enhance Claude Code with rules, commands, hooks, and skills organized under `.claude/`
- The hooks pipeline pattern (blocking `PostToolUse` hooks for quality enforcement) is directly applicable to adding quality gates in Claude Code plugin development workflows
- The `/spec` Discuss → Plan → Approve → Implement → Verify loop maps closely to the Plan/Work/Review/Compound workflow in `research-agent-patterns/compound-engineering-plugin.md`
- Context preservation via `pre_compact.py` + `post_compact_restore.py` is a novel technique for long-running agent workflows that need to survive context resets

### Patterns Worth Adopting

- **Blocking Stop hooks**: `spec_stop_guard.py` prevents premature session end when a spec is in flight — applicable to any workflow that needs completion guarantees
- **Effective context rescaling**: displaying 0–100% effective context (hiding the compaction buffer from users) improves UX for context-monitoring tools
- **File-type conditional rules**: `paths` frontmatter in rules to activate coding standards only for matching file types reduces context noise in large multi-language repos
- **Plan-then-approve gate**: writing spec to `docs/plans/` and waiting for explicit human approval before execution — a behavioral protocol worth encoding in orchestrator agent delegation prompts
- **Parallel verifier sub-agents**: three independent sub-agents (compliance, quality, goal) reviewing the same code from different lenses catches more issues than a single review pass
- **Smart model routing by phase**: documenting which phases get Opus vs Sonnet with the reasoning (not just the choice) is a template for model-routing rules

### Integration Opportunities

- The `file_checker.py` hook approach (dispatching to language-specific linters/formatters on every edit) could be adopted as a PostToolUse hook pattern in this repository's pre-commit / quality gate framework
- `post_compact_restore.py` technique (snapshot-then-restore across compaction) is directly usable in any Claude Code skill that manages long-running multi-phase workflows
- The `/vault` concept (sharing rules/skills via a private git repo) is a complementary distribution mechanism to the plugin marketplace in this repository

### Competitive Analysis

| Feature | Claude Pilot | This Repository (claude_skills) |
|---------|-------------|----------------------------------|
| Distribution | curl installer per-project | Plugin marketplace (npm-like) |
| Hook pipeline | 15 lifecycle hooks enforced | Pre-commit hooks (developer-facing) |
| Spec-driven dev | Built-in `/spec` command | Separate `compound-engineering-plugin` |
| Persistent memory | Pilot Console + mem-search MCP | No built-in equivalent |
| License | Proprietary, subscription | MIT |
| Target user | Individual developers / freelancers | Plugin developers / Claude Code users |

---

## References

- [maxritter/claude-pilot GitHub repository](https://github.com/maxritter/claude-pilot) (accessed 2026-02-23)
- [Claude Pilot website](https://claude-pilot.com) (accessed 2026-02-23)
- [Claude Pilot Changelog](https://pilot.openchangelog.com/) (accessed 2026-02-23)
- [v6.10.2 release](https://github.com/maxritter/claude-pilot/releases/tag/v6.10.2) (accessed 2026-02-23)
- [Claude Pilot License](https://github.com/maxritter/claude-pilot/blob/main/LICENSE) (accessed 2026-02-23)

---
