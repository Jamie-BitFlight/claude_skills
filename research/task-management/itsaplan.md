---
name: itsaplan
title: It's a Plan
subtitle: Self-hosted issue tracker where AI agents hold issues like teammates
research_date: 2026-10-17
source_url: https://github.com/croffasia/itsaplan
github_repository: https://github.com/croffasia/itsaplan
version_at_research: v1.5.0
license: AGPL-3.0-only (packages/runner is Apache-2.0)
freshness_tracking:
  last_verified: 2026-10-17
  version_at_verification: v1.5.0
  next_review: 2026-11-14
  confidence_map: "Overview: high, Problem Addressed: high, Key Features: high, Technical Architecture: medium (doc + code-read), Installation & Usage: high, Limitations and Caveats: medium"
---

# It's a Plan

## Overview

It's a Plan is a self-hosted, open-source project management and issue tracker. Its differentiator is that AI agents are project members: an agent has a role, permissions, and an assignee slot, and takes issues on the same board as people. The README describes it as an open-source alternative to Linear, Jira, Trello, and Plane, with AI agents built in, and states that everything is available over the REST API, webhooks, and MCP. Snapshot at v1.5.0 (CHANGELOG entry dated 2026-10-13; repository HEAD commit dated 2026-10-17, accessed 2026-10-17).

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Hosted trackers charge per seat and lock data in | "You run all of it on your own server, on your own database, with your own API keys — no per-seat fees, no lock-in." (README, About) |
| Coding and other AI agents have no place in the team's tracker | "An agent gets a role, permissions, and an assignee slot, and takes issues on the same board as your people." (README, About) |
| An agent needs to read and change issues without a custom integration | "MCP server, so an external assistant can read and change issues through the same API." (README, Platform) |
| Work done by an agent needs to be triggered and tracked from the tracker | "A run starts on an @mention in a comment, on an assignment, or on a schedule." (README, AI agents) |

---

## Key Features

### Product management

- Kanban, table, timeline, and calendar views, with per-view filters, display fields, and two-level grouping. Each view can be saved as a tab (README, Product management list).
- Cycles that time-box work: "Unfinished issues move to the next cycle." Configurable dashboards show throughput, burnup with a projected completion date, breakdown, and pulse (README).
- Per-project configuration of custom fields, labels, states, and issue types (README).
- Subtasks, checklists, attachments, and issue links of the types blocks, relates, and duplicates (README).
- Docs: shared Markdown pages in a tree, with revision history, private and locked pages, and embedded files. Freeform notes boards with sticky notes, colors, checklists, and connections (README).
- Public read-only links to a view or an issue, which need no sign-in (README).

### AI agents

- Internal agents run on the instance. The model, system prompt, tools, and reusable skills are configured per agent, and skills can be imported from a GitHub repository (docs/runner.md and README, AI agents list).
- External agents run on the operator's machine. The `@itsaplan/runner` package gives each queued task to a coding agent CLI. Its presets are `claude` (Claude Code), `codex` (Codex CLI), `opencode`, `antigravity` (Antigravity CLI), `copilot` (GitHub Copilot CLI), `pi`, and `omp` (Oh My Pi). A `command` setting runs any other command that reads stdin (packages/runner/README.md, "Which coding agent").
- The runner polls the instance per agent key. `concurrency` sets how many tasks run at once, per agent, with a default of `1` (packages/runner/README.md, Settings).
- Each preset passes the flags for an unattended run. Claude Code receives `--permission-mode auto`; Antigravity CLI receives `--dangerously-skip-permissions`; Copilot CLI receives `--allow-all-tools` and `--no-ask-user` (docs/runner.md, per-CLI sections).
- Each task run exposes the variables `ITSAPLAN_URL`, `ITSAPLAN_API_KEY`, `ITSAPLAN_TRIGGER`, `ITSAPLAN_RUN_ID`, `ITSAPLAN_ISSUE`, and `ITSAPLAN_ISSUE_ID` to the command. A chat message adds `ITSAPLAN_THREAD_ID`, `ITSAPLAN_MESSAGE_ID`, and `ITSAPLAN_SESSION_ID` (packages/runner/README.md, "The environment").
- Chat with each agent has its own history. For an external agent, each conversation resumes one coding agent session, and that session keeps its full context (packages/runner/README.md, Chat and Sessions).
- Tools for services outside the tracker: Notion, Telegram, Threads, Instagram, Jina, Firecrawl, and Gitea (README, AI agents list).

### Platform

- REST API with an OpenAPI reference and API keys (README, Platform list).
- MCP endpoint at `POST /mcp`. Auth accepts `Authorization: Bearer <key>` and `x-api-key`. The transport is stateless: "a fresh server and transport per request" (apps/api/src/mcp/mount.ts). MCP tools are generated from API routes that opt in with an `x-mcp` extension in their OpenAPI detail. Each generated tool forwards its call to the route through the app's own dispatch, so validation and permission guards are reused (apps/api/src/mcp/generate.ts).
- Outgoing webhooks with signed payloads, retries, and a delivery log (README, Platform list).
- Pull requests from GitHub, GitLab, Gitea, Forgejo, and Bitbucket. A "Fixes KEY-42" reference links the pull request to the issue, and the issue moves when the pull request opens and merges (README, Platform list).
- Sign-in with email and password, a passkey, or Google. Notifications by email (SMTP or Resend) and Telegram (README, Platform list).
- Interface in English, Ukrainian, Russian, Simplified Chinese, Arabic, French, Portuguese (Brazil), Bahasa Indonesia, Spanish (Spain), and Korean (README; CHANGELOG 1.5.0 "add Korean localization").

---

## Technical Architecture

The repository is a Bun and Turborepo monorepo. Backend is Elysia, frontend is Next.js (App Router, SSR) with shadcn/ui, auth is better-auth, and the ORM is Drizzle with PostgreSQL. Storage is an S3-compatible object store (RustFS in the reference compose files) (AGENTS.md, Layout; README, Built with).

**Workspace members** (AGENTS.md, Layout):

- `apps/api`: Elysia server on port 3000. Serves better-auth at `/api/auth/*`, agent runs, and the MCP endpoint.
- `apps/web`: Next.js App Router web app on port 3001.
- `apps/worker`: webhook and notification delivery, and agent schedules.
- `apps/bot`: Telegram bot using long polling. It must stay at one replica (AGENTS.md, Commands and Gotchas).
- `packages/db` (`@repo/db`): Drizzle client, schema, migrations, permission matrix, and shared config readers.
- `packages/auth` (`@repo/auth`): better-auth server instance.
- `packages/crypto` (`@repo/crypto`): AES-256-GCM encryption for secrets at rest.
- `packages/mailer`, `packages/net` (SSRF guard for server-side fetches of a supplied URL), `packages/storage`, and `packages/agent-tools` (tool definitions for the AI agent runtime).
- `packages/runner` (`@itsaplan/runner`): CLI that runs an external agent's queued tasks on the operator's machine.

**Dependencies and data flow.** The dependency graph is `api → @repo/auth → @repo/db → @repo/crypto`. The web app does not import workspace packages. It calls the API over HTTP through the better-auth client and fetch (AGENTS.md, Layout).

**Execution model for external agents.** The runner polls the instance for queued runs. It starts the configured CLI in the working directory and reads the result from the exit code: `0` is a success, and any other code is a failure. The agent reads and writes issue data through the MCP server at `$ITSAPLAN_URL/mcp`, authenticated with its own API key (packages/runner/README.md, "The result" and "The task text").

**Deployment topology.** Migrations run as a separate step before the apps start. In the compose files this is the one-shot `migrate` service that the api, worker, and bot wait for. `migrate.ts` writes a database dump to the `db-backups` volume first, and a failed dump stops the run (AGENTS.md, Compose files).

**Design decision with stated rationale.** The web app talks to the API only, and does not import packages directly (AGENTS.md, Layout). The stated reason for MCP over the same route layer is that "the route's own TypeBox schemas and permission guard stay the single source of truth" (apps/api/src/mcp/generate.ts).

**Extension points.**

- Custom agent tools: a tool is a `CustomToolEntry` with a `key`, a `label`, a `description`, an `inputSchema` (zod), and an `execute(credential, input)` function. An integration groups tools and declares a `credentialSchema`. A new integration is registered by adding it to the `INTEGRATIONS` array in `src/registry.ts` (packages/agent-tools/README.md, "Add a tool" and "Add a new integration").
- MCP tools: any API route can be exposed by adding an `x-mcp` extension to its OpenAPI detail (apps/api/src/mcp/generate.ts).
- Runner presets and custom commands: a new CLI runs through the `command` setting, which takes the task text on stdin (packages/runner/README.md, Settings).

---

## Limitations and Caveats

- **Pre-stable.** "It's a Plan is under active development. Expect breaking changes before the first stable release." (README, About)
- **TLS proxy required for production.** The session cookie is marked `Secure`. Over plain HTTP, "the sign-in request succeeds, but no session is kept". `http://localhost` is the exception in Chrome and Firefox; WebKit browsers such as Safari refuse it there too (docs/self-hosting.md).
- **Runner needs the coding agent installed and signed in on the same machine.** "The runner starts the CLI as you, but it cannot sign in for you." (packages/runner/README.md, Requirements)
- **Runner requirements.** Node 20 or later. The instance must be 0.10.0 or later, and "The chat needs 0.11.0. An older instance gives the runner only the queued runs." (packages/runner/README.md, Requirements)
- **Windows** requires WSL2. "`cmd.exe` and PowerShell have no `sh`." A custom `command` is run with `sh -c` and must be written as POSIX shell (packages/runner/README.md, Requirements).
- **Sessions stay on one machine.** "If you delete its files or move the runner, the answers fail. Start a new chat then." (packages/runner/README.md, Sessions)
- **Unattended runs.** The presets pass flags that skip or auto-approve tool prompts. Antigravity CLI: "Without the flag a denied tool call still exits `0`." Copilot CLI: "It still denies a path outside the working directory, and the run continues and exits `0`." (docs/runner.md)
- **One MCP key per machine for Antigravity CLI.** "`apiKeys` and `agents` still run several agents, but they all reach the instance as the agent whose key is in that file." (docs/runner.md)
- **Telemetry is on by default.** A self-hosted instance sends one daily snapshot of itself to the project. It is disabled by setting `TELEMETRY_DISABLED=1` or `DO_NOT_TRACK=1` (TELEMETRY.md).
- **Linear import omits data.** Not imported: "Estimates, SLAs, reactions, subscribers (watchers), and activity history", "Completed and canceled times", "Project milestones, project updates, documents, initiatives, and custom views", and "Deleted issues". "Start dates — Linear issues have none." (docs/importing-from-linear.md, "What is not imported")
- **Bot replica count.** `bot` runs Telegram long polling and must stay at one replica (AGENTS.md, Commands and Gotchas).
- Not mentioned in the reviewed sources: a documented load or scale figure for the API or the worker, and a documented limit on the number of agents or issues per project.

---

## Installation & Usage

Local try-out, from the README. Requires Docker and Bun:

```bash
git clone https://github.com/croffasia/itsaplan.git
cd itsaplan
bun install
bun run setup   # answer "Try it"
```

Production deployment is documented in docs/self-hosting.md. The stack refuses to start until the required variables are set, and `docker compose up -d` starts Postgres, RustFS, api, worker, bot, and web.

Connecting a coding agent, from docs/runner.md, the Claude Code section. The first file goes in the working directory as `.mcp.json`:

```json
{
  "mcpServers": {
    "itsaplan": {
      "type": "http",
      "url": "http://localhost:3000/mcp",
      "headers": { "Authorization": "Bearer ${ITSAPLAN_API_KEY}" }
    }
  }
}
```

The second file is `itsaplan-runner.json` in the same folder:

```json
{
  "url": "http://localhost:3000",
  "apiKey": "the key you copied on creation",
  "agent": "claude",
  "cwd": "/Users/me/work/my-repo"
}
```

Start the runner, from packages/runner/README.md:

```bash
npx -y @itsaplan/runner
```

---

## References

- [It's a Plan repository](https://github.com/croffasia/itsaplan) (accessed 2026-10-17, shallow clone at commit 1c8610530b8ae6a89a69ac58e18b07fdc2efd523)
- [README](https://github.com/croffasia/itsaplan/blob/main/README.md) (accessed 2026-10-17, clone file `README.md`)
- [package.json](https://github.com/croffasia/itsaplan/blob/main/package.json) (accessed 2026-10-17, version `1.5.0`, license `AGPL-3.0-only`)
- [CHANGELOG](https://github.com/croffasia/itsaplan/blob/main/CHANGELOG.md) (accessed 2026-10-17, entry `1.5.0` dated 2026-10-13)
- [AGENTS.md](https://github.com/croffasia/itsaplan/blob/main/AGENTS.md) (accessed 2026-10-17, layout, dependency graph, compose files)
- [Coding agent setup](https://github.com/croffasia/itsaplan/blob/main/docs/runner.md) (accessed 2026-10-17)
- [@itsaplan/runner README](https://github.com/croffasia/itsaplan/blob/main/packages/runner/README.md) (accessed 2026-10-17)
- [@repo/agent-tools README](https://github.com/croffasia/itsaplan/blob/main/packages/agent-tools/README.md) (accessed 2026-10-17)
- [Self-hosting](https://github.com/croffasia/itsaplan/blob/main/docs/self-hosting.md) (accessed 2026-10-17)
- [Telemetry](https://github.com/croffasia/itsaplan/blob/main/TELEMETRY.md) (accessed 2026-10-17)
- [Importing from Linear](https://github.com/croffasia/itsaplan/blob/main/docs/importing-from-linear.md) (accessed 2026-10-17)
- [MCP mount](https://github.com/croffasia/itsaplan/blob/main/apps/api/src/mcp/mount.ts) and [MCP tool generation](https://github.com/croffasia/itsaplan/blob/main/apps/api/src/mcp/generate.ts) (accessed 2026-10-17)
- [LICENSE](https://github.com/croffasia/itsaplan/blob/main/LICENSE) (accessed 2026-10-17, GNU AGPL v3)
- The project website (itsaplan.dev), linked from the README, was not fetched. No content in this entry is taken from it.

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Beads](./beads.md) | task-management | alternative agent-facing issue tracker: git-backed Dolt store, versus self-hosted Postgres with agents as board members |
| [Claude Task Master](./claude-task-master.md) | task-management | task tracking for AI coding agents via MCP, file-based rather than a self-hosted board with agent assignees |
| [Vibe Kanban](./vibe-kanban.md) | task-management | Kanban board that dispatches parallel coding agent sessions, overlapping this entry's agent assignee slots |
| [saga-mcp](../mcp-ecosystem/saga-mcp.md) | mcp-ecosystem | Jira-like tracker exposed to agents as MCP tools, an alternative to this entry's generated MCP endpoint |
| [OpenAI Symphony](../coding-agents/openai-symphony.md) | coding-agents | polls an issue tracker and dispatches a coding agent per issue, matching this entry's assignment- and mention-triggered runs |
| [xyOps](./xyops.md) | task-management | queued job dispatch to remote satellite agents, similar to this entry's runner polling the instance for queued runs |
