---
title: "Beads (bd)"
research_date: "2026-02-26"
source_url: "https://github.com/steveyegge/beads"
github_url: "https://github.com/steveyegge/beads"
version_at_research: "v0.56.1"
license: "MIT"
last_verified: "2026-02-26"
version_at_verification: "v0.56.1"
next_review: "2026-05-26"
---

## Overview

Beads (`bd`) is a distributed, git-backed graph issue tracker built specifically for AI coding agents. It replaces unstructured markdown task lists with a dependency-aware, version-controlled SQL database (powered by Dolt), enabling agents to manage long-horizon tasks without losing context across sessions. With 17,269 GitHub stars and 249 contributors as of 2026-02-26, it has become the dominant purpose-built task management tool for AI agent workflows.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| AI agents lose task context between sessions | Persistent Dolt SQL database stores all issues, history, and dependencies locally in `.beads/` |
| Sequential IDs collide when multiple agents work concurrently on branches | Hash-based IDs (`bd-a1b2`) derived from random UUIDs prevent all merge collisions |
| Unstructured markdown plans have no dependency graph | Typed dependency links: `blocks`, `parent-child`, `discovered-from`, `relates_to`, `duplicates`, `supersedes`, `replies_to` |
| Context window fills up with closed task history | Semantic "compaction" summarizes old closed tasks to reduce token consumption |
| Multi-agent work across git branches cannot be safely merged | Dolt cell-level 3-way merge resolves issue database conflicts automatically |
| Tool is editor/agent-specific, not portable | CLI-first design with `--json` output works with any agent framework or editor |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 17,269 | 2026-02-26 |
| GitHub Forks | 1,065 | 2026-02-26 |
| Contributors | 249 | 2026-02-26 |
| Open Issues | 86 | 2026-02-26 |
| Latest Release | v0.56.1 | 2026-02-23 |
| Repository Created | 2025-10-12 | 2026-02-26 |
| Last Commit | 2026-02-26 | 2026-02-26 |
| npm package | @beads/bd | 2026-02-26 |
| PyPI package | beads-mcp | 2026-02-26 |

SOURCE: [GitHub API](https://api.github.com/repos/steveyegge/beads) (accessed 2026-02-26)

---

## Key Features

### Agent-Optimized Task Graph

- All commands emit structured `--json` output for programmatic agent consumption
- `bd ready` returns tasks with no open blockers — the agent's entry point for finding work
- `bd update <id> --claim` atomically claims a task (sets assignee + in_progress in one operation), preventing race conditions with other agents
- `bd prime` command generates ~1-2k token workflow context summary for injection into agent sessions
- Hierarchical IDs for epics: `bd-a3f8` (epic) → `bd-a3f8.1` (task) → `bd-a3f8.1.1` (sub-task)

### Distributed Storage via Dolt

- Issues stored in Dolt, a version-controlled SQL database with native branching and cell-level merge
- Every write auto-commits to Dolt history, providing a full audit trail
- Push/pull to Dolt remotes (DoltHub, S3, GCS, filesystem) — no special sync server required
- Works offline; sync on demand via `bd dolt push` / `bd dolt pull`
- Multi-writer capable via Dolt's `sql-server` mode

### Hash-Based Collision Prevention

- IDs derived from random UUIDs (`bd-a1b2`) scaled from 4 to 6 chars as database grows
- Eliminates the sequential ID collision problem (`bd-10` created by two branches simultaneously)
- Import/merge deduplicates by ID+content hash: same ID + same content = skip, same ID + different content = update

### Compaction and Memory Management

- `bd compact` summarizes closed tasks using semantic compression
- Reduces context window consumption for long-running projects
- Preserves relationships and audit trail while collapsing completed work

### Dependency and Link Types

- `blocks` — prevents work from being started until dependency resolves
- `parent-child` — hierarchical task decomposition
- `discovered-from` — tracks tasks surfaced during implementation
- `relates_to`, `duplicates`, `supersedes`, `replies_to` — knowledge graph links
- `bd dep add <child> <parent>` creates links; `bd ready` respects all blocker types

### Messaging System

- `message` issue type with threading via `--thread`
- Ephemeral lifecycle and mail delegation between agents
- Enables async agent-to-agent coordination

### Workflow Automation

- Formula system for declarative workflow templates
- Molecule concept for representing work graphs with shared lifecycle
- Gates for async coordination: human approval, timer, GitHub trigger

### Editor and Agent Integration

- `bd setup claude` installs Claude Code SessionStart and PreCompact hooks
- `bd setup cursor`, `bd setup aider`, `bd setup codex`, `bd setup mux` for other editors
- MCP server (`beads-mcp`) for MCP-only environments (Claude Desktop, Sourcegraph Amp)
- Claude Code plugin available via marketplace (`steveyegge/beads`) for slash commands
- `bd hooks install` sets up git hooks for automatic Dolt sync on commit

### Stealth and Contributor Modes

- `bd init --stealth` stores database locally without committing files, for personal use on shared repos
- `bd init --contributor` routes planning issues to `~/.beads-planning` for forked repos
- Auto-detects maintainer role via SSH URLs or HTTPS with credentials

---

## Technical Architecture

Beads uses a two-layer architecture: a CLI layer and a Dolt database layer.

<eg>
CLI Layer (cmd/bd/)
  bd create, list, update, close, ready, show, dep, sync, ...
  All commands support --json for programmatic use
          |
          v
Dolt Database (.beads/dolt/)
  Version-controlled SQL with cell-level merge
  Server mode via dolt sql-server (multi-writer)
  Issues, dependencies, labels, comments, events tables
  Automatic Dolt commit on every write
          |
     Dolt push/pull
          |
          v
Remote (DoltHub, S3, GCS, filesystem)
  All collaborators share the same issue database
  Cell-level merge for conflict resolution
</eg>

**Write path**: CLI command → Dolt write (immediate) → Dolt commit (automatic). Sync to remote is explicit via `bd dolt push`.

**Read path**: CLI query → direct SQL query against local Dolt database. All reads are local and millisecond-fast.

**File layout**:

<eg>
beads/
  cmd/bd/              # CLI commands (Cobra)
  internal/
    types/             # Core data types
    storage/
      dolt/            # Dolt storage implementation
  examples/            # Integration examples
  integrations/
    beads-mcp/         # MCP server (Python/PyPI)
  npm-package/         # @beads/bd npm wrapper
</eg>

SOURCE: [ARCHITECTURE.md](https://github.com/steveyegge/beads/blob/main/docs/ARCHITECTURE.md) (accessed 2026-02-26)

---

## Installation & Usage

```bash
# Homebrew (recommended for macOS/Linux)
brew install beads

# npm
npm install -g @beads/bd

# Go
go install github.com/steveyegge/beads/cmd/bd@latest

# Install script (all platforms)
curl -fsSL https://raw.githubusercontent.com/steveyegge/beads/main/scripts/install.sh | bash

# Windows PowerShell
irm https://raw.githubusercontent.com/steveyegge/beads/main/install.ps1 | iex

# MCP server only (for Claude Desktop / MCP-only environments)
uv tool install beads-mcp
```

```bash
# Initialize in a project
cd your-project
bd init

# Setup Claude Code integration (installs SessionStart/PreCompact hooks)
bd setup claude

# Basic agent workflow
bd ready --json                          # Find available work
bd update bd-a1b2 --claim --json         # Atomically claim a task
bd create "Fix auth bug" -t bug -p 1 --json  # Create a task
bd dep add bd-a1b2 bd-f14c               # Link dependency
bd update bd-a1b2 --status done --json   # Close completed work
bd dolt push                             # Sync to remote

# Stealth mode (no project-level files committed)
bd init --stealth

# Contributor mode (fork workflows)
bd init --contributor
```

SOURCE: [README.md](https://github.com/steveyegge/beads/blob/main/README.md) (accessed 2026-02-26)
SOURCE: [INSTALLING.md](https://github.com/steveyegge/beads/blob/main/docs/INSTALLING.md) (accessed 2026-02-26)

---

## Relevance to Claude Code Development

### Applications

- Direct replacement for markdown-based task tracking in agent workflows (`BACKLOG.md`, `TODO.md` files)
- Enables multi-agent parallelism where several Claude Code instances work on the same project without task collision
- `bd prime` generates a compact (~1-2k token) workflow briefing for injection into CLAUDE.md or SessionStart hooks, replacing verbose manual context setup
- `bd setup claude` automates SessionStart and PreCompact hook installation, making persistent memory zero-config
- The `--contributor` mode is purpose-built for contributing to shared repos without polluting the upstream with agent planning artifacts

### Patterns Worth Adopting

- Hash-based IDs for any distributed state where sequential IDs would collide (applicable to agent coordination systems beyond task tracking)
- The `bd prime` pattern: a single command that generates a compact, structured context briefing — applicable to any stateful tool that needs to inject context into an agent session
- Atomic claim semantics (`--claim` flag) as the standard pattern for multi-agent work queue consumption
- Semantic compaction: summarizing completed work rather than deleting it preserves audit trail while managing context window size
- The CLI-first, MCP-optional design philosophy described in `docs/CLAUDE_INTEGRATION.md`: CLI + hooks adds 1-2k tokens overhead vs. 10-50k for MCP tool schemas

### Integration Opportunities

- Install `bd` as part of the project development environment and use `bd setup claude` to inject task context automatically into Claude Code sessions
- Use `bd ready --json` as the first command in complex multi-step agent workflows to orient the agent on outstanding work
- Adopt `bd create --deps discovered-from:<parent>` pattern to track emergent work found during implementation, keeping discovered tasks linked to their origin
- The beads Claude Code plugin (`steveyegge/beads`) provides `/beads:ready`, `/beads:create`, `/beads:show` slash commands for interactive use within Claude Code sessions

---

## References

- [GitHub Repository: steveyegge/beads](https://github.com/steveyegge/beads) (accessed 2026-02-26)
- [README.md](https://github.com/steveyegge/beads/blob/main/README.md) (accessed 2026-02-26)
- [AGENT_INSTRUCTIONS.md](https://github.com/steveyegge/beads/blob/main/AGENT_INSTRUCTIONS.md) (accessed 2026-02-26)
- [docs/ARCHITECTURE.md](https://github.com/steveyegge/beads/blob/main/docs/ARCHITECTURE.md) (accessed 2026-02-26)
- [docs/CLAUDE_INTEGRATION.md](https://github.com/steveyegge/beads/blob/main/docs/CLAUDE_INTEGRATION.md) (accessed 2026-02-26)
- [docs/INSTALLING.md](https://github.com/steveyegge/beads/blob/main/docs/INSTALLING.md) (accessed 2026-02-26)
- [docs/CLI_REFERENCE.md](https://github.com/steveyegge/beads/blob/main/docs/CLI_REFERENCE.md) (accessed 2026-02-26)
- [GitHub API: repo metadata](https://api.github.com/repos/steveyegge/beads) (accessed 2026-02-26)
- [GitHub API: latest release v0.56.1](https://api.github.com/repos/steveyegge/beads/releases/latest) (accessed 2026-02-26)
- [npm package @beads/bd](https://www.npmjs.com/package/@beads/bd) (accessed 2026-02-26)
- [PyPI package beads-mcp](https://pypi.org/project/beads-mcp/) (accessed 2026-02-26)

---
