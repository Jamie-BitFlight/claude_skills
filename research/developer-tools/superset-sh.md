---
title: "Superset"
research_date: "2026-03-04"
source_url: "https://superset.sh"
github_url: "https://github.com/superset-sh/superset"
version_at_research: "v1.0.5 (desktop-v1.0.5)"
license: "Apache 2.0"
last_verified: "2026-03-04"
version_at_verification: "desktop-v1.0.5"
next_review: "2026-06-04"
---

## Overview

Superset is a macOS desktop application (Electron-based) that enables developers to run 10+ parallel AI coding agents simultaneously on their local machine. It uses Git worktrees as its core isolation mechanism — each agent session operates in a separate branch and working directory, preventing conflicts. Superset is agent-agnostic, supporting Claude Code, OpenAI Codex CLI, Cursor Agent, Gemini CLI, OpenCode, and any CLI-based agent.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Running multiple AI coding agents concurrently causes Git conflicts and context collisions | Isolates each agent in its own Git worktree — separate directory, separate branch, shared history |
| Switching between many agent terminals is cognitively expensive | Unified dashboard showing all agent sessions with status, diff counts, and notification when attention is needed |
| Agent outputs are scattered across terminal windows with no structured review workflow | Built-in diff viewer and editor for inspecting and editing agent-generated changes without leaving the app |
| Workspace setup (env vars, dependencies) must be repeated for every new agent branch | `.superset/setup.sh` scripts automate environment initialization per worktree |
| AI agents are locked to specific IDEs or tools | Universal compatibility — works with any CLI agent; IDE integration lets you open any worktree in VS Code, Cursor, Xcode, JetBrains, or terminal |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 4,175 | 2026-03-04 |
| GitHub Forks | 270 | 2026-03-04 |
| Contributors | 30 | 2026-03-04 |
| Open Issues | 248 | 2026-03-04 |
| Latest Release | desktop-v1.0.5 | 2026-03-03 |
| Repository Created | 2025-10-21 | 2026-03-04 |
| Total Commits | 1,728 | 2026-03-04 |
| Primary Language | TypeScript | 2026-03-04 |

SOURCE: [superset-sh/superset GitHub API](https://github.com/superset-sh/superset) (accessed 2026-03-04)

---

## Key Features

### Parallel Agent Execution

- Run 10+ coding agents simultaneously from a single interface
- Each workspace maps to one agent session in its own Git worktree
- Agent monitoring dashboard shows status (Generating, Ready for Review, In Progress) across all active sessions
- Notifications when an agent completes or requires attention, eliminating polling

### Worktree Isolation

- Each task spawns a new Git worktree — a separate directory sharing Git history with the main repo
- Agents on different tasks never share working directories, eliminating file-level conflicts
- Branch naming is configurable; each worktree checks out an independent branch

### Agent Compatibility

- Works with any CLI-based coding agent: Claude Code, OpenAI Codex CLI, Cursor Agent, Gemini CLI, OpenCode, GitHub Copilot
- No vendor lock-in: agent choice is fully user-controlled
- Tested against `.agents/commands`, `.claude`, `.codex`, `.cursor`, `.mastracode` configuration directories (all present in the repo itself)

### Built-in Diff Viewer and Editor

- Inspect agent-generated changes without leaving Superset
- Edit changes directly in the diff viewer before committing
- Port management and in-app browser for reviewing running services spawned by agents

### Workspace Automation

- `.superset/setup.sh` script runs automatically when a new worktree is created
- Scripts receive `SUPERSET_WORKSPACE_NAME` and `SUPERSET_ROOT_PATH` environment variables
- Supports copying `.env` files, installing dependencies, and arbitrary setup tasks
- Teardown scripts also supported for cleanup

### IDE Integration

- One-click "Open in" for VS Code, Cursor, Xcode, JetBrains IDEs, Sublime Text, Finder, Terminal, and Windsurf
- Worktrees appear as independent project roots in any IDE
- Port forwarding panel surfaces running services per workspace

### MCP Server

- Superset exposes an MCP server that agents can connect to
- Enables agents to query workspace context and coordinate through the MCP protocol
- MCP config scoped at user level (`~/.claude.json`), project level (`.mcp.json`), and local level

### Privacy and Telemetry

- Zero telemetry — no data collection, no analytics
- API calls go directly to model providers; Superset does not proxy them
- Full source available under Apache 2.0

---

## Technical Architecture

Superset is an Electron desktop application written in TypeScript with a Bun runtime. The monorepo contains:

- `apps/desktop` — Electron app (renderer: React/TypeScript)
- `apps/api` — tRPC backend for workspace and SSH management
- `apps/docs` — Documentation site (Next.js MDX)
- `packages/db` — Database schema (cloud workspaces, enums)

The core data model is a **workspace** — a Git worktree checked out from a repository. The desktop app manages worktree lifecycle (create, teardown, status), monitors agent processes running inside each worktree, and presents a unified review interface.

The development server uses Caddy as a reverse proxy for Electric SQL streams. The production desktop binary is an arm64 or x86 DMG distributed via GitHub Releases.

```text
User Repository (Git)
        │
        ├── main branch (root worktree)
        │
        ├── worktree-1/ ← Agent 1 (Claude Code) → feature/auth
        ├── worktree-2/ ← Agent 2 (Codex CLI)   → fix/header-bug
        └── worktree-3/ ← Agent 3 (Cursor Agent) → refactor/db-layer

Superset Desktop App
  ├── Workspace Dashboard (status: Generating / Ready / In Progress)
  ├── Diff Viewer (inspect + edit agent output)
  ├── Terminal Panel (per-worktree shell)
  ├── Port Manager (forward service ports per workspace)
  └── MCP Server (agent coordination protocol)
```

SOURCE: [superset-sh/superset GitHub README](https://github.com/superset-sh/superset) (accessed 2026-03-04)

---

## Installation & Usage

```bash
# Option 1: Download macOS DMG (Apple Silicon)
# https://github.com/superset-sh/superset/releases/latest/download/Superset-arm64.dmg

# Option 2: Build from source
git clone https://github.com/superset-sh/superset.git
cd superset
cp .env.example .env
echo 'SKIP_ENV_VALIDATION=1' >> .env
bun install
bun run dev

# Build desktop app
bun run build
open apps/desktop/release
```

```bash
# Requirements:
# - macOS (Apple Silicon or Intel); Windows/Linux: coming soon
# - Bun v1.0+
# - Git 2.20+
# - GitHub CLI (gh) authenticated
# - Caddy (for dev server reverse proxy)
```

```bash
# Workspace automation: add .superset/setup.sh to your repo
#!/bin/bash
# .superset/setup.sh

# Copy environment variables from parent worktree
cp ../.env .env

# Install dependencies
bun install

echo "Workspace ready for agent: $SUPERSET_WORKSPACE_NAME"
```

SOURCE: [Superset Installation Docs](https://superset.sh/docs) (accessed 2026-03-04)

---

## Relevance to Claude Code Development

### Applications

- Directly relevant: Superset is built for Claude Code — the repo contains `.claude/` configuration and the product is demonstrated with Claude Code as the primary agent
- Running multiple Claude Code sessions in parallel on different tasks (feature branches, bug fixes, refactors) with isolated worktrees matches exactly how this skill repository operates
- The workspace automation pattern (`.superset/setup.sh`) mirrors the SAM feature implementation workflow's task isolation requirements

### Patterns Worth Adopting

- **Worktree-per-task isolation**: The Git worktree pattern is architecture-level task isolation — each task gets its own filesystem state, eliminating cross-task interference. This is a stronger guarantee than branch switching alone
- **Agent status dashboard**: The status model (Generating / Ready for Review / In Progress) maps directly to the SAM task states (NOT STARTED / IN PROGRESS / COMPLETE / BLOCKED). A unified status view reduces monitoring overhead for multi-agent workflows
- **Setup/teardown scripts**: The `.superset/setup.sh` convention for automating environment init per worktree is directly applicable to any multi-branch development workflow

### Integration Opportunities

- Superset exposes an MCP server — Claude Code instances running inside Superset worktrees can connect to it, enabling agent-to-agent coordination through the MCP protocol
- The `/implement-feature` workflow in this repository delegates tasks to sub-agents sequentially; Superset would enable parallelizing independent tasks across worktrees, then reviewing diffs through its built-in viewer
- Superset's "Open in IDE" feature means each worktree can be opened in a separate Claude Code session with its own CLAUDE.md context, enabling true parallel feature development

---

## References

- [superset.sh — Official Website](https://superset.sh) (accessed 2026-03-04)
- [superset-sh/superset — GitHub Repository](https://github.com/superset-sh/superset) (accessed 2026-03-04)
- [Superset Installation Docs](https://superset.sh/docs) (accessed 2026-03-04)
- [Superset on Product Hunt](https://www.producthunt.com/products/superset-5) (accessed 2026-03-04)
- [Show HN: Superset — Run 10 parallel coding agents on your machine](https://news.ycombinator.com/item?id=46109015) (accessed 2026-03-04)
- [GitHub Releases — superset-sh/superset](https://github.com/superset-sh/superset/releases) (accessed 2026-03-04)

---
