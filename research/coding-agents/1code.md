# 1Code

**Research Date**: 2026-03-17
**Source URL**: <https://1code.dev>
**GitHub Repository**: <https://github.com/21st-dev/1code>
**Version at Research**: v0.0.84
**License**: Apache License 2.0

---

## Overview

1Code is an open-source Electron desktop application that acts as an orchestration layer for coding agents, enabling users to run Claude Code, OpenAI Codex, and other AI agents locally or in the cloud. It provides a Cursor-like visual UI with diff previews, real-time tool execution display, git worktree isolation per chat session, MCP server management, and a REST API for programmatic agent invocation. Created by the 21st.dev team and first published January 2026, it reached 5,236 GitHub stars within approximately two months of creation.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Running coding agents risks polluting the main branch with in-progress or failed agent work | Git Worktree Isolation: each chat session runs in its own isolated worktree on a separate branch, with `worktreePath`, `branch`, and `baseBranch` fields tracked in the SQLite schema |
| No unified UI for multiple agent backends (Claude Code, Codex) | Multi-agent client: Claude Code (via `@anthropic-ai/claude-agent-sdk` v0.2.45) and Codex (via `@zed-industries/codex-acp` v0.9.3) are bundled as downloaded binaries, switchable from the UI |
| Agent sessions end when the developer closes their laptop | Background Agents: cloud sandbox execution that continues when the local machine is offline (hosted tier, requires Pro/Max subscription) |
| No structured way to review agent-proposed changes before they land | Diff Previews and Plan Mode: agents can ask clarifying questions, produce structured plans for user review, and stream real-time tool execution before committing |
| Triggering agents from external events (GitHub PRs, CI failures, Linear issues) requires custom automation glue | Built-in Automations: `@1code` mention triggers in GitHub, Linear, and Slack; git event triggers for push/PR |
| Invoking an agent programmatically requires managing the agent SDK directly | REST API: `POST https://1code.dev/api/v1/tasks` accepts a repository URL and prompt, runs in a cloud sandbox, and delivers a PR |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 5,236 | 2026-03-17 |
| Forks | 561 | 2026-03-17 |
| Watchers/subscribers | 30 | 2026-03-17 |
| Contributors | 19 (first 100-per-page result) | 2026-03-17 |
| Latest Release | v0.0.84 | 2026-03-17 |
| Release Date | 2026-03-06 | 2026-03-17 |
| Repository Created | 2026-01-14 | 2026-03-17 |
| Open Issues | 24 | 2026-03-17 |
| Primary Language | TypeScript | 2026-03-17 |

---

## Key Features

### Agent Execution and Isolation

- **Git Worktree Isolation**: each chat session creates a new git worktree on its own branch; the schema tracks `worktreePath`, `branch`, `baseBranch`, `prUrl`, and `prNumber` per chat, preventing accidental commits to main
- **Multi-Agent Support**: Claude Code and Codex run in the same application, switchable at any time; agent binaries are downloaded at build time (`bun run claude:download --version=2.1.45`, `bun run codex:download --version=0.98.0`)
- **Background Agents**: cloud sandbox sessions that run when the local machine is offline; requires Pro or Max subscription at `1code.dev/pro`
- **Plan Mode**: the agent asks clarifying questions, builds a structured step-by-step plan displayed as markdown, and waits for user review before executing; activated via `/plan` slash command
- **Extended Thinking**: enabled by default for supported models with a visual gradient indicator

### Visual UI and Developer Experience

- **Diff Previews**: real-time display of file changes as the agent edits, using `@git-diff-view/react` and `@pierre/diffs`
- **Built-in Git Client**: visual staging, commit, push to GitHub, branch management, and rollback from any user message bubble; uses `simple-git` and a custom `GitRouter` (exposed as the `changes` namespace in the tRPC router)
- **Integrated Terminal**: sidebar or bottom panel with `Cmd+J` toggle, implemented via `node-pty` and `@xterm/*` addons; supports shared terminal sessions across local-mode workspaces
- **File Viewer**: file preview with `Cmd+P` search, syntax highlighting via Shiki, and image viewer
- **Chat Forking**: fork a sub-chat from any assistant message to explore alternatives, backed by the `subChats` table with `sessionId` for Claude SDK session resume
- **Message Queue**: queue prompts while an agent is working
- **Kanban Board**: visualize agent sessions

### MCP and Plugin Ecosystem

- **MCP Server Management**: toggle, configure, and delete MCP servers from the UI without editing config files; managed by `pluginsRouter` (Source: `src/main/lib/trpc/routers/plugins.ts`)
- **Plugin Marketplace**: browse and install plugins with one click
- **Rich Tool Display**: see MCP tool calls with formatted inputs and outputs in the chat stream
- **`@` Mentions**: reference MCP servers directly in chat input

### Automations and API

- **`@1code` Triggers**: tag `@1code` in GitHub, Linear, or Slack to start agents; supports conditions, filters, and silent mode
- **Git Event Triggers**: run automations on push, PR creation, or any git event
- **REST API**: `POST https://1code.dev/api/v1/tasks` with repository URL and prompt runs the agent in an isolated cloud sandbox, commits changes, pushes a branch, and opens a PR automatically; supports async polling and follow-up messages
- **PWA**: start and monitor background agents from a mobile browser

### Skills, Slash Commands, and Memory

- **Skills & Slash Commands**: custom skills and `/plan`, `/agent`, `/clear` built-in commands; managed by `skillsRouter` (Source: `src/main/lib/trpc/routers/skills.ts`)
- **Memory**: `CLAUDE.md` and `AGENTS.md` file support for persistent project context
- **Voice Input**: hold-to-talk dictation requiring microphone permission (`NSMicrophoneUsageDescription` declared in macOS entitlements)

### Multi-Account Authentication

- **Multiple Anthropic Accounts**: the `anthropicAccounts` SQLite table stores multiple OAuth tokens (encrypted via Electron's `safeStorage` API) with a `activeAccountId` in `anthropicSettings` for quick switching (Source: `src/main/lib/db/schema/index.ts`)
- **BYOK (Bring Your Own Key)**: custom models and API providers configurable without subscribing to the hosted tier

---

## Technical Architecture

### Process Model

1Code follows the standard Electron three-process architecture:

- **`src/main/`** (Electron main process): app entry (`index.ts`), window lifecycle, OAuth flow (`auth-manager.ts`), encrypted credential storage (`auth-store.ts` using `safeStorage`), and all backend logic via tRPC routers.
- **`src/preload/`** (IPC bridge with context isolation): exposes `window.desktopApi` for native features (window controls, clipboard, notifications) and a tRPC bridge to the renderer.
- **`src/renderer/`** (React 19 UI): built with Vite, Tailwind CSS, Radix UI components, and the following state management layers:
  - **Jotai** for UI state (selected chat, sidebar open, preview settings)
  - **Zustand** for sub-chat tabs and pinned state (persisted to localStorage)
  - **React Query** for server state via tRPC (auto-caching, refetch)

Source: CLAUDE.md Architecture section.

### Communication Layer: tRPC over Electron IPC

All renderer-to-main communication uses `tRPC` with `trpc-electron`, providing type-safe RPC without raw IPC. The `createAppRouter()` function assembles 20 named routers:

```text
projects | chats | claude | claudeCode | claudeSettings | anthropicAccounts
ollama | codex | terminal | external | files | debug | skills | agents
worktreeConfig | sandboxImport | commands | voice | plugins | changes (git)
```

Source: `src/main/lib/trpc/routers/index.ts` — `createAppRouter()`.

### Database: Drizzle ORM + SQLite

Local state is stored in a SQLite file at `{userData}/data/agents.db`, managed by Drizzle ORM with auto-migration on startup from the `drizzle/` folder (dev) or `resources/migrations` (packaged). The schema defines five tables:

- `projects` — id, name, path (unique), git remote info (url, provider, owner, repo), icon path
- `chats` — id, name, projectId (FK cascade), worktreePath (indexed), branch, baseBranch, prUrl, prNumber, archivedAt
- `sub_chats` — id, chatId (FK cascade), sessionId (Claude SDK resume token), streamId, mode ("plan" | "agent"), messages (JSON array)
- `anthropicAccounts` — encrypted OAuth token per Anthropic account, email, displayName, lastUsedAt
- `anthropicSettings` — singleton row tracking `activeAccountId` for account switching

Source: `src/main/lib/db/schema/index.ts`.

### Claude SDK Integration

The main process dynamically imports `@anthropic-ai/claude-agent-sdk` (v0.2.45 pinned in package.json). Two execution modes are supported:

- **"plan" mode**: read-only, agent plans but does not execute file changes
- **"agent" mode**: full permissions, agent executes bash, edits files, runs web searches

Sessions are resumed via `sessionId` stored in the `subChats` table. Message streaming is delivered to the renderer via a tRPC subscription: `claude.onMessage`. The Claude binary itself is a pre-built CLI downloaded at build time via `scripts/download-claude-binary.mjs --version=2.1.45`.

Source: CLAUDE.md Claude Integration section; `package.json` scripts.

### Build and Packaging

- **Build tool**: `electron-vite` (Vite-based, with separate main/preload/renderer entry points)
- **Packager**: `electron-builder` targeting macOS (DMG + ZIP for arm64 and x64), Windows (NSIS + portable), Linux (AppImage + DEB)
- **Native modules**: `better-sqlite3` and `node-pty` are rebuilt via `electron-rebuild` in the `postinstall` script and unpacked from ASAR for runtime access
- **Auto-update**: checks `https://cdn.21st.dev/releases/desktop/latest-mac.yml` on startup and window focus (1-minute cooldown); hosted tier only

---

## Installation & Usage

### Build from Source (open source, free)

```bash
# Prerequisites: Bun, Python 3.11, setuptools, Xcode Command Line Tools (macOS)
bun install
bun run claude:download  # Downloads Claude CLI binary v2.1.45 (required)
bun run codex:download   # Downloads Codex binary v0.98.0 (required)
bun run build
bun run package:mac      # or package:win, package:linux
```

Important: the `claude:download` and `codex:download` steps are required; skipping them produces a build that starts but has non-functional agent execution.

### Development with Hot Reload

```bash
bun install
bun run claude:download  # First time only
bun run codex:download   # First time only
bun run dev
```

### REST API (programmatic agent invocation, hosted tier)

```bash
curl -X POST https://1code.dev/api/v1/tasks \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "repository": "https://github.com/your-org/your-repo",
    "prompt": "Fix the failing CI tests"
  }'
```

The agent runs in an isolated cloud sandbox: the repository is cloned, dependencies are installed, the agent executes the prompt, commits changes, pushes a branch, and opens a PR. The call is fire-and-forget; status is available by polling or webhook.

Source: README.md API section.

### Subscribing for Hosted Features

Pre-built releases and background agent support require a subscription at `https://1code.dev`.

---

## Relevance to Claude Code Development

### Applications

- **Parallel agent sessions model**: the git worktree-per-chat isolation pattern is directly applicable to multi-agent workflows in Claude Code — each agent task can operate in its own worktree on its own branch, preventing interference between concurrent tasks.
- **MCP server lifecycle management**: 1Code's `pluginsRouter` approach (toggle/configure servers from UI without config file editing) demonstrates a pattern for managing MCP server registrations dynamically.
- **Sub-chat forking for exploration**: the `subChats` table with `sessionId` resume tokens shows how to implement branching conversation trees while preserving the ability to resume any branch from its exact Claude SDK session state.
- **BYOK multi-account pattern**: the `anthropicAccounts` schema (multiple encrypted OAuth tokens, singleton `activeAccountId`) is a reference implementation for supporting account switching in Claude Code environments with multiple API keys.

### Patterns Worth Adopting

- **Plan mode before agent mode**: requiring the agent to produce and surface a structured plan for review before executing destructive operations (file edits, bash commands) reduces irreversible mistakes — directly applicable to skill design.
- **tRPC for type-safe IPC**: using tRPC over Electron IPC provides compile-time safety for all renderer-to-main calls; the pattern generalizes to any multi-process agent architecture needing typed message passing.
- **Worktree path indexed in DB**: indexing `worktreePath` in the `chats` table (`index("chats_worktree_path_idx").on(table.worktreePath)`) shows that worktree lookups are a hot path — relevant for any tool that maps sessions to file system paths.
- **Pinned binary versions for agent CLIs**: downloading exact CLI binary versions at build time (rather than relying on system-installed versions) ensures reproducible agent behavior — applicable to any tool that wraps the Claude or Codex CLIs.

### Integration Opportunities

- 1Code's plugin marketplace could distribute Claude Code Marketplace plugins, providing a GUI installation surface for skills created in this repository.
- The `@1code` trigger pattern (GitHub/Linear/Slack mentions starting agents) is a model for how automated agent dispatch could work for Claude Code skill workflows triggered by external events.
- The REST API (`POST /api/v1/tasks`) could be used by CI/CD pipelines to trigger Claude Code agents on PR creation or CI failures, with the result delivered as a GitHub PR — complementing the SAM workflow defined in this repository.

---

## References

- [21st-dev/1code README](https://github.com/21st-dev/1code/blob/main/README.md) (accessed 2026-03-17)
- [21st-dev/1code CONTRIBUTING.md](https://github.com/21st-dev/1code/blob/main/CONTRIBUTING.md) (accessed 2026-03-17)
- [21st-dev/1code CLAUDE.md](https://github.com/21st-dev/1code/blob/main/CLAUDE.md) (accessed 2026-03-17)
- [GitHub API repos/21st-dev/1code](https://api.github.com/repos/21st-dev/1code) (accessed 2026-03-17)
- [GitHub API repos/21st-dev/1code/releases/latest](https://api.github.com/repos/21st-dev/1code/releases/latest) (accessed 2026-03-17)
- [1code.dev homepage](https://1code.dev) — not fetched directly; claims sourced from README and API only
- Local worktree code analysis: `.worktrees/1code/src/main/lib/db/schema/index.ts`, `.worktrees/1code/src/main/lib/trpc/routers/index.ts`, `.worktrees/1code/package.json` (accessed 2026-03-17)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Accomplish](./accomplish.md) | coding-agents | alternative Electron+React desktop agent UI with MCP tools and permission-gated execution |
| [OpenAI Codex CLI](./openai-codex-cli.md) | coding-agents | Codex binary bundled inside 1Code; shares dual MCP client+server role and AGENTS.md context |
| [Tembo](./tembo.md) | coding-agents | overlapping multi-agent orchestration use case (Claude Code, Codex, Cursor) with event-driven automation triggers |
| [Superset](../developer-tools/superset-sh.md) | developer-tools | alternative Electron app running parallel agents via git worktrees — same isolation pattern, agent-agnostic |
| [Cline](./cline.md) | coding-agents | alternative open-source coding agent with human-in-the-loop approvals and multi-provider LLM support |
| [OpenHands](./openhands.md) | coding-agents | alternative cloud coding agent platform addressing same goal of autonomous software development |
| [Pilot](./pilot.md) | coding-agents | alternative Claude Code wrapper with ticket-to-PR automation and autonomous development pipeline |
| [OpenAI Symphony](./openai-symphony.md) | coding-agents | alternative autonomous coding agent platform with workspace sandboxing and issue-tracker-driven workflows |

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | 2026-03-17 |
| Version at Verification | v0.0.84 |
| Next Review Recommended | 2026-04-17 |
| Confidence Map | Overview: high; Key Statistics: high; Key Features: high; Technical Architecture: high (doc + code-read); Installation & Usage: high; Limitations: high; Relevance: medium |

Note on review interval: 1Code is in rapid development (v0.0.72 in package.json vs v0.0.84 latest release, 12 releases in the git tag listing, repository only 2 months old). A 4-week review cadence is recommended over the standard 3-month baseline.
