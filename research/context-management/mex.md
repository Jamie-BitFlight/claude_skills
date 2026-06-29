---
title: mex — Persistent Project Memory for AI Agents
resource_name: mex
resource_url: https://github.com/theDakshJaitly/mex
category: context-management
type: npm-package
last_updated: 2026-06-18
---

## Overview

mex is a CLI-driven memory system that gives AI agents structured, task-routed project context across sessions. Rather than flooding context windows with giant instruction files, mex maintains a navigable scaffold (Markdown + YAML metadata) and runs zero-token drift detection to keep that scaffold aligned with the actual codebase.

**Primary claim** (extracted from README): "Persistent project memory for AI coding agents. Structured scaffold + drift detection CLI."

**Key identity metrics** (as of 2026-06-18):
- **Current version**: 0.6.1 (released 2026-06-14)
- **GitHub stars**: 866
- **Language**: TypeScript
- **License**: MIT
- **NPM package name**: `mex-agent` (command is still `mex`)
- **Node requirement**: >=20
- **TypeScript**: 5.7
- **Repository**: <https://github.com/theDakshJaitly/mex>

---

## Problem Addressed

**Problem statement** (from README): "Most agent memory setups become one giant instruction file. That works for a while, then it floods the context window, burns tokens, and drifts away from the real codebase."

The README presents a comparison table of typical problems:

| Without mex | With mex |
|-------------|----------|
| "Giant `CLAUDE.md` / rules files" | "Small anchor file plus routed context" |
| "Agents forget decisions and conventions" | "Decisions, patterns, and project state persist" |
| "Docs silently drift from code" | "`mex check` catches stale or broken scaffold claims" |
| "Every session starts cold" | "Agents load only the files relevant to the task" |
| "Repeated work stays tribal" | "New patterns grow from real tasks" |

**Real-world impact** (from independent community testing on OpenClaw): "Independently tested by a community member on **OpenClaw** across 10 structured homelab scenarios covering Ubuntu 24.04, Kubernetes, Docker, Ansible, Terraform, networking, and monitoring. 10/10 tests passed. Drift score: 100/100."

Token savings per session: ~60% average (range: 50-68% per scenario).

---

## Key Statistics

- **GitHub stars**: 866 (as of 2026-06-18)
- **GitHub forks**: 53
- **Open issues**: 26
- **Contributors**: Maintained by Daksh Jaitly
- **Repository created**: 2026-03-21
- **Last push**: 2026-06-14 (main branch)
- **NPM downloads**: Badge present in README; exact count not statically documented

---

## Key Features

### 1. Structured Scaffold Architecture

mex organizes project memory into a standardized directory structure:

- **`AGENTS.md` / `CLAUDE.md`** — "tiny tool-loaded anchor"
- **`ROUTER.md`** — routing table mapping tasks to context files
- **`context/` directory** — architecture, stack, setup, decisions, conventions (separate from root)
- **`patterns/` directory** — reusable task guides with gotchas and verification steps
- **`.mex/events/decisions.jsonl`** — append-only event log with `mex log` entries

**Extraction**: From README section "What It Does": "mex creates a structured markdown scaffold for agent memory: `AGENTS.md` / `CLAUDE.md` — tiny tool-loaded anchor; `ROUTER.md` — routing table for task-specific context; `context/` — architecture, stack, setup, decisions, conventions; `patterns/` — reusable task guides with gotchas and verification steps; `.mex/events/decisions.jsonl` — append-only notes through `mex log`"

### 2. Zero-Token Drift Detection

The `mex check` command runs 11 automated checkers on the scaffold without consuming AI tokens:

**The 11 checkers** (from README):

| Checker | What it catches |
|---------|----------------|
| **path** | "Referenced file paths that do not exist on disk" |
| **edges** | "YAML frontmatter edge targets pointing to missing files" |
| **index-sync** | "`patterns/INDEX.md` out of sync with actual pattern files" |
| **staleness** | "Scaffold files not updated in 30+ days or 50+ commits" |
| **command** | "`npm run X` / `make X` references scripts that do not exist" |
| **dependency** | "Claimed dependencies missing from `package.json`" |
| **cross-file** | "Same dependency with different versions across files" |
| **script-coverage** | "`package.json` scripts not mentioned in any scaffold file" |
| **tool-config-sync** | "Installed AI tool config files (e.g. `CLAUDE.md`, `.cursorrules`) out of sync with each other" |
| **todo-fixme** | "Unresolved `TODO` / `FIXME` markers left in scaffold markdown" |
| **broken-link** | "Markdown links to local files that do not exist on disk" |

**Scoring mechanism**: "Scoring starts at 100. mex deducts 10 per error, 3 per warning, and 1 per info."

### 3. AI-Driven Targeted Sync

When drift is detected, `mex sync` uses minimal, targeted AI prompts to fix only the stale pieces. From README: "The CLI keeps that scaffold honest. It checks paths, commands, dependencies, pattern indexes, staleness, and script coverage without spending AI tokens. When drift appears, `mex sync` builds targeted prompts so the agent fixes only the stale pieces."

### 4. Multi-Tool Support

mex integrates with multiple AI tools. From README section "Supported Tools":

| Tool | Config file |
|------|-------------|
| Claude Code | `CLAUDE.md` |
| Cursor | `.cursorrules` |
| Windsurf | `.windsurfrules` |
| GitHub Copilot | `.github/copilot-instructions.md` |
| OpenCode | `.opencode/opencode.json` |
| Codex | `AGENTS.md` |

Neovim/Vim users can integrate via [docs/vim-neovim.md](./docs/vim-neovim.md): "mex's scaffold is tool-agnostic — any AI plugin that can read a system prompt or config file can use it."

### 5. Agent Memory Mode

New in v0.3.5. From CHANGELOG: "`mex setup --mode agent-memory` creates templates for persistent-agent, homelab, OpenClaw-style, and operational-memory workspaces."

Features:
- `HEARTBEAT.md` contract for operational memory
- `ROUTER.md` tracks operational state
- Lightweight `mex heartbeat` checks (vs full `mex check`)
- `mex watch --interval` for persistent-agent loops

From README: "`mex heartbeat` is intentionally lighter than `mex check`: it reads `last_updated` frontmatter and memory cleanup metadata, prints `HEARTBEAT_OK` when clean, and reports only when the agent needs to review stale context or memory files."

### 6. Event Log and Timeline

New in v0.3.5. From CHANGELOG: "`mex log` appends notes, decisions, risks, and todos to `.mex/events/decisions.jsonl`."

v0.6.1 enhancement: "**Event log provenance/lifecycle fields** — `EventEntry` now accepts two optional, free-form string fields: `source` (where an event came from, e.g. `meeting`, `manual`, `agent`) and `status` (decision lifecycle, e.g. `decided`, `implemented`)."

### 7. Interactive Dashboard (TUI)

New in v0.3.5. From CHANGELOG: "**Interactive TUI** — bare `mex` and `mex tui` open an Ink terminal dashboard with drift score, heartbeat status, event activity, timeline/log actions, and a bordered action panel."

---

## Technical Architecture

### Core Components

**Entry point and config loading** (from src/cli.ts):
- Central config loader with scaffold identity backfill (silent UUID generation for existing scaffolds)
- Telemetry hooks on preAction (fires events at start of command, allowing async requests to complete even if command exits)
- Structured error handling for missing scaffolds

**Drift detection engine** (from src/drift/):
- `index.ts` orchestrates 11 independent checker modules
- `checkers/` directory contains modular verification logic:
  - `path.ts`, `edges.ts`, `index-sync.ts`, `staleness.ts`, `command.ts`, `dependency.ts`, `cross-file.ts`, `script-coverage.ts`, `tool-config-sync.ts`, `todo-fixme.ts`, `broken-link.ts`
- Each checker is composable: `DEFAULT_SCAFFOLD_PATTERNS` can be extended by embedders

**Public API contract** (from src/index.ts):

```typescript
// Config
export { findConfig, createConfig, getScaffoldIdentity } from "./config.js";
export type { CreateConfigInput } from "./config.js";

// Events (append-only JSONL log)
export { appendEvent, readEvents, eventLogPath, EVENT_KINDS } from "./events.js";
export type { EventEntry, EventKind, LogOpts } from "./events.js";

// Drift detection
export { runDriftCheck, DEFAULT_SCAFFOLD_PATTERNS } from "./drift/index.js";
export type { RunDriftCheckOpts } from "./drift/index.js";

// Heartbeat
export { checkHeartbeat, runHeartbeat, DEFAULT_HEARTBEAT_PATTERNS } from "./heartbeat.js";
export type { HeartbeatResult, HeartbeatOpts, CheckHeartbeatOpts } from "./heartbeat.js";
```

The README states: "Everything re-exported from this file is part of the package's compatibility contract. See COMPATIBILITY.md at the repo root for the versioning policy and what counts as a breaking change. Internal modules (`src/cli.ts`, `src/sync/`, `src/scanner/`, `src/setup/`, `src/tui.ts`, `src/watch.ts`, `src/doctor.ts`, etc.) are NOT part of the contract and may change without notice."

### Technology Stack

From package.json (v0.6.1):

**Runtime dependencies:**
- `chalk` 5.4.1 — terminal color/styling
- `commander` 13.1.0 — CLI argument parsing
- `glob` 11.0.1 — file pattern matching
- `ink` 7.0.3 — React-based terminal UI
- `posthog-node` 5.21.2 — anonymous telemetry client
- `react` 19.2.6 — UI component framework (used by Ink)
- `remark-frontmatter` 5.0.0 — YAML frontmatter parsing
- `remark-parse` 11.0.0 — Markdown AST parsing
- `simple-git` 3.27.0 — Git operations
- `unified` 11.0.5 — Syntax tree processor
- `unist-util-visit` 5.0.0 — AST traversal
- `yaml` 2.7.0 — YAML serialization/parsing

**Build tooling:**
- `tsup` 8.4.0 — TypeScript bundler
- `typescript` 5.7
- `vitest` 3.0.0 — test framework
- `ink-testing-library` 4.0.0 — TUI testing

### Execution Model

**Setup workflow** (from README):
1. `npx mex-agent setup` — interactive first-time setup
2. Pre-scans codebase and generates targeted prompts
3. Populates `.mex/` scaffold in ~5 minutes
4. User selects target AI tool (Claude Code, Cursor, Windsurf, Copilot, OpenCode, Codex)
5. Optional global install: `npm install -g mex-agent`

**Drift detection workflow** (from README):
1. `mex check` runs 11 checkers (path, edges, index-sync, staleness, command, dependency, cross-file, script-coverage, tool-config-sync, todo-fixme, broken-link)
2. Produces scored report (100 baseline, -10 per error, -3 per warning, -1 per info)
3. Output modes: console, `--quiet` (one-liner), `--json`, `--verbose`

**Sync workflow** (from README):
1. `mex sync` detects drift
2. Builds minimal targeted prompts for AI tool
3. User applies changes
4. Verifies and repeats if needed

**Event logging** (from README):
- `mex log <message>` appends to `.mex/events/decisions.jsonl`
- Supports `mex log --source` and `mex log --status` (v0.6.1)
- `mex timeline` displays recent entries with optional `--json`

---

## Installation & Usage

### Quick Start

From README:

```bash
npx mex-agent setup
```

Setup creates the `.mex/` scaffold, asks which AI tool you use, pre-scans your codebase, and generates a targeted prompt to populate the memory files.

Global install (optional):

```bash
npm install -g mex-agent
```

### Command Reference

From README:

```bash
mex                                    # Open interactive terminal dashboard
mex tui                                # Explicit dashboard launch
mex setup                              # First-time setup: create .mex/ scaffold
mex setup --mode agent-memory          # Setup for persistent-agent workspaces
mex setup --dry-run                    # Preview without making changes
mex check                              # Run drift checkers and output report
mex check --quiet                      # One-liner: "mex: drift score 92/100 (1 warning)"
mex check --json                       # Full report as JSON
mex check --fix                        # Check and jump to sync if errors found
mex sync                               # Detect drift, choose mode, let AI fix
mex sync --dry-run                     # Preview targeted prompts without executing
mex sync --warnings                    # Include warning-only files in sync
mex init                               # Pre-scan codebase, build structured brief
mex init --json                        # Raw scanner brief as JSON
mex log <message>                      # Append note, decision, risk, or todo
mex timeline                           # View recent event log entries
mex heartbeat                          # Run lightweight persistent-agent health checks once
mex doctor                             # Friendly scaffold health summary
mex watch                              # Install post-commit hook
mex watch --interval                   # Run heartbeat repeatedly in foreground
mex watch --uninstall                  # Remove the hook
mex completion <shell>                 # Print shell completions (bash|zsh|fish)
mex commands                           # List commands and scripts with descriptions
```

### Windows Compatibility

From README: "The recommended `npx mex-agent setup` flow runs in any terminal (Command Prompt, PowerShell, or WSL) and does not need bash, so most Windows users do not have to think about this section."

Legacy warning: "If you previously installed via the legacy `setup.sh` script, building inside WSL and then running the CLI from a native Windows terminal causes 'module not found' errors because `node_modules` and path resolution differ between the two filesystems."

### Configuration

From README section "Configuration": "Optional settings live in `.mex/config.json`. Missing values fall back to defaults."

Example config (src/config.ts):

```json
{
  "staleness": {
    "warnDays": 30,
    "errorDays": 90,
    "warnCommits": 50,
    "errorCommits": 200
  },
  "heartbeat": {
    "staleDays": 7,
    "memoryCleanupDays": 7,
    "dailyMemoryRetentionDays": 14
  },
  "watch": {
    "intervalMinutes": 30
  }
}
```

---

## Relevance to Claude Code Development

### 1. Agent Memory Infrastructure

mex directly addresses a core Claude Code use case: persistent context for agents across multiple sessions. The scaffold structure (ROUTER.md for task routing, patterns/ for reusable guides, events/ for decisions) aligns with how Claude Code sessions benefit from structured, task-routed memory.

**Evidence**: README states "Agents load only the files relevant to the task" and "New patterns grow from real tasks." This maps to Claude Code's session management model.

### 2. Drift Detection for Instruction Files

The 11 drift checkers (especially `tool-config-sync`, `broken-link`, `staleness`, `script-coverage`) are directly applicable to Claude Code's CLAUDE.md and .claude/rules/ ecosystem. mex's validation mechanisms prevent the documented-drift problem that plague instruction files over time.

**Evidence**: Drift checker `tool-config-sync` specifically "flags Installed AI tool config files (e.g. `CLAUDE.md`, `.cursorrules`) out of sync with each other."

### 3. Multi-Tool Integration

mex supports Claude Code (via CLAUDE.md) alongside Cursor, Windsurf, Copilot, OpenCode, and Codex. For teams or developers switching tools, mex's `tool-config-sync` checker ensures that all instruction files stay aligned.

**Evidence**: README table lists 6 supported tools with their config files.

### 4. Event Log for Decision Capture

The append-only `.mex/events/decisions.jsonl` with `mex log` is a lightweight alternative to backlog systems for recording session-scoped decisions and rationale. This integrates with Claude Code's session historian paradigm.

**Evidence**: v0.6.1 CHANGELOG: "Event log provenance/lifecycle fields" with `source` (meeting, manual, agent) and `status` (decided, implemented) fields.

### 5. Agent Memory Mode Validation

mex's new agent-memory mode (v0.3.5) and lightweight `mex heartbeat` checks are designed for persistent-agent workspaces. This directly supports homelab and OpenClaw-style setups where agents run repeatedly against operational memory rather than code repos.

**Evidence**: CHANGELOG: "`mex setup --mode agent-memory` creates templates for persistent-agent, homelab, OpenClaw-style, and operational-memory workspaces."

---

## Limitations and Caveats

### 1. Drift Detection vs. Drift Fixing

mex detects drift with 100% reliability (zero tokens) but _fixing_ drift requires AI intervention via `mex sync`. The sync process is manual — the user must review and apply generated prompts.

**Evidence**: README: "When drift appears, `mex sync` builds targeted prompts so the agent fixes only the stale pieces." This is not automation; it is an aid to human review.

### 2. Scaffold Structure Is Not Enforced

mex provides templates and patterns but does not enforce scaffold structure at runtime. Users can delete or ignore scaffold files without mex detecting the breakage until they run a command.

**Evidence**: Drift checkers catch _missing_ files (broken-link, path, edges) but do not prevent their deletion.

### 3. Telemetry Is Opt-Out, Not Opt-In

From README section "Telemetry": "mex collects anonymous, opt-out usage data (command name, version, OS — never paths, args, file contents, IP, or personal data) to understand how the tool is used."

Users must explicitly opt out with `DO_NOT_TRACK=1`, `MEX_TELEMETRY=0`, or `mex config set telemetry off`.

**Evidence**: README states collection is "opt-out" not "opt-in." The CHANGELOG (v0.6.0) notes anonymous collection via PostHog.

### 4. Staleness Thresholds Are Fixed by Default

Default staleness thresholds (30 days / 50 commits for warnings; 90 days / 200 commits for errors) may not suit all projects. While `.mex/config.json` allows tuning, the defaults are not universally appropriate.

**Evidence**: README shows hardcoded thresholds; config.json allows overrides.

### 5. Event Log Is Append-Only (No Mutations)

The `.mex/events/decisions.jsonl` is designed as an immutable log. Entries cannot be edited or deleted — only appended. This prevents accidental loss of rationale but makes correction of erroneous entries impossible without manual JSONL editing.

**Evidence**: Public API exports `appendEvent` and `readEvents`, not `updateEvent` or `deleteEvent`.

### 6. No Built-In Conflict Resolution

When `mex sync` generates targeted prompts and multiple team members apply them simultaneously, mex provides no conflict detection or merging strategy. The scaffold files (Markdown + YAML) are not transaction-aware.

**Evidence**: Not mentioned in README or documentation; users must use git/version control to resolve conflicts.

---

## References

- **GitHub Repository**: <https://github.com/theDakshJaitly/mex> (accessed 2026-06-18)
- **npm Package**: <https://www.npmjs.com/package/mex-agent> (accessed 2026-06-18)
- **Website**: <https://www.launchx.page/mex> (accessed 2026-06-18)
- **README.md**: <https://github.com/theDakshJaitly/mex/blob/main/README.md> (accessed 2026-06-18)
- **CHANGELOG.md**: <https://github.com/theDakshJaitly/mex/blob/main/CHANGELOG.md> (accessed 2026-06-18)
- **CONTRIBUTING.md**: <https://github.com/theDakshJaitly/mex/blob/main/CONTRIBUTING.md> (accessed 2026-06-18)
- **TELEMETRY.md**: <https://github.com/theDakshJaitly/mex/blob/main/TELEMETRY.md> (accessed 2026-06-18)
- **docs/vim-neovim.md**: <https://github.com/theDakshJaitly/mex/blob/main/docs/vim-neovim.md> (accessed 2026-06-18)
- **src/index.ts** (Public API contract): <https://github.com/theDakshJaitly/mex/blob/main/src/index.ts> (accessed 2026-06-18)
- **package.json**: <https://github.com/theDakshJaitly/mex/blob/main/package.json> (accessed 2026-06-18)

---

## Freshness Tracking

| Section | Confidence | Last Verified | Notes |
|---------|------------|---------------|-------|
| Identity/Metadata | high | 2026-06-18 | GitHub API snapshot + package.json (v0.6.1) |
| Problem Addressed | high | 2026-06-18 | Direct quotes from README |
| Key Statistics | high | 2026-06-18 | GitHub API + README badges |
| Key Features | high | 2026-06-18 | Feature descriptions extracted verbatim from README sections |
| Technical Architecture | high | 2026-06-18 | src/ file structure and exports read from repository |
| Installation & Usage | high | 2026-06-18 | Commands and workflows from README command table |
| Relevance to Claude Code | medium | 2026-06-18 | Alignment inferred from mex's tool support and drift detection features; requires validation against actual Claude Code usage patterns |
| Limitations | medium | 2026-06-18 | Inferred from architecture and documentation; some limitations (conflict resolution, mutation prevention) are design constraints not explicitly stated in docs |

**Next review**: 2026-09-18 (3 months). Check for v0.7.0+ releases, new drift checkers, agent-memory mode changes, and updated compatibility with Claude Code, Cursor, Windsurf.

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Local Memory](./local-memory.md) | context-management | Multi-interface persistent memory system (MCP/REST/CLI) with hybrid search and knowledge hierarchy — complementary persistence layer to mex's drift detection |
| [MemPalace](./mempalace.md) | context-management | Zero-API-cost verbatim memory with palace structure and semantic search — alternative memory organization to mex's scaffold approach |
| [SlimContext](./slimcontext.md) | context-management | Context compression via trimming and summarization strategies — solves the token-reduction problem mex scaffolding addresses |
| [SimpleMem-Cross](./simplemem-cross.md) | context-management | Persistent cross-conversation memory with automatic session lifecycle and context injection — shares heuristic observation extraction with mex's decision logging |
| [Claude-Mem](./claude-mem.md) | context-management | Claude Code plugin for session-scoped memory capture with hybrid search and progressive disclosure — implements mex's multi-tool integration pattern for Claude Code specifically |
| [Straion](./straion.md) | context-management | Dynamic, task-scoped rule injection platform replacing static instruction files — alternative to mex's static scaffold approach for drift-aware instruction delivery |
