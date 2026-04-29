# OpenSpec MCP (openspec-mcp)

**Research Date**: 2026-04-29
**Source URL**: <https://github.com/iflow-mcp/lumiaqian-openspec-mcp>
**Upstream Repository**: <https://github.com/Lumiaqian/openspec-mcp>
**npm Package**: <https://www.npmjs.com/package/openspec-mcp>
**Version at Research**: v0.4.2
**License**: MIT

---

## Overview

OpenSpec MCP is a Model Context Protocol server that enables spec-driven development workflows
by exposing the OpenSpec CLI as 50+ MCP tools for AI assistants. It provides a real-time web
dashboard, approval pipeline management, review comment threads, and cross-service design
document aggregation. The `iflow-mcp/lumiaqian-openspec-mcp` repository is a fork of the
upstream `Lumiaqian/openspec-mcp` created on 2026-02-28; all active development occurs in the
upstream repository.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| AI assistants lack structured awareness of in-flight specification changes | MCP tools expose full OpenSpec change lifecycle (create, validate, approve, archive) to the AI context |
| No feedback loop between reviewer comments and agent tasks | Review system (add, reply, resolve) lets agents act on human reviewer input without leaving the AI session |
| Spec progress tracking requires manual file inspection | Task parsing reads markdown task files and surfaces progress summaries via `openspec_get_progress_summary` |
| Multi-service architectures scatter design docs across repos | Cross-service document aggregation (`openspec_list_cross_service_docs`, `openspec_read_cross_service_doc`) unified through a single MCP interface |
| Approval handoffs between humans and agents have no structured state | Change state machine (draft → pending_approval → approved → implementing → completed → archived) enforced through MCP tools |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars (upstream Lumiaqian/openspec-mcp) | 20 | 2026-04-29 |
| GitHub Forks (upstream) | 3 | 2026-04-29 |
| GitHub Open Issues | 0 | 2026-04-29 |
| npm Weekly Downloads | 61 | 2026-04-29 |
| npm Total Versions | 15 | 2026-04-29 |
| Latest Release | v0.4.2 (2026-01-12) | 2026-04-29 |
| Days Since Latest Release | 107 days | 2026-04-29 |

SOURCE: [GitHub API - upstream repo](https://api.github.com/repos/Lumiaqian/openspec-mcp) (accessed 2026-04-29), [npm registry downloads](https://api.npmjs.org/downloads/point/last-week/openspec-mcp) (accessed 2026-04-29)

---

## Key Features

### MCP Tool Surface (50+ Tools)

- `openspec_get_instructions` -- reads AGENTS.md for workflow guidance
- `openspec_analyze_context` -- runs architecture analysis on the project
- `openspec_ai_analyze_context` -- AI-enhanced analysis with tech stack detection
- `openspec_list_changes` / `openspec_show_change` -- enumerate and inspect changes
- `openspec_create_change` / `openspec_validate_change` / `openspec_archive_change` -- change lifecycle
- `openspec_request_approval` / `openspec_approve_change` / `openspec_reject_change` -- approval pipeline
- `openspec_list_pending_approvals` -- queue visibility for reviewers
- `openspec_add_review` / `openspec_reply_review` / `openspec_resolve_review` / `openspec_list_reviews` -- threaded review system
- `openspec_get_tasks` / `openspec_update_task` / `openspec_batch_update_tasks` / `openspec_get_progress_summary` -- task tracking against spec
- `openspec_list_cross_service_docs` / `openspec_read_cross_service_doc` -- cross-service documentation aggregation

SOURCE: [README.md upstream](https://github.com/Lumiaqian/openspec-mcp/blob/main/README.md) (accessed 2026-03-02)

### Real-Time Web Dashboard

- Fastify-based HTTP server with WebSocket push for live updates on all pages
- Routes: overview, Kanban board, change listings, QA runner, context analysis, approval queue
- Drag-and-drop workflow state transitions, progress bars, status badges, Markdown rendering
- Auto-detects project name via Git remote > package.json > go.mod > current directory

### Approval Workflow State Machine

State progression: `draft` -> `pending_approval` -> `approved` -> `implementing` -> `completed` -> `archived`. Rejection cycles back to `draft` for revision, preserving the audit trail.

### Cross-Service Documentation Aggregation

Configured via YAML frontmatter in `proposal.md` with `crossService.rootPath`, document list,
and `archivePolicy` (snapshot or reference). Supports real-time WebSocket updates when
cross-service files change.

### MCP Prompts

- `analyze-project` -- architecture and technology stack analysis prompt
- `review-change` -- intelligent change review with spec linking

---

## Technical Architecture

```text
MCP Client (Claude / Cursor / Claude Desktop)
  |
  | stdio or HTTP transport
  v
openspec-mcp server (TypeScript, Node.js >= 20)
  |-- src/index.ts          Entry point, CLI argument parsing
  |-- src/server/           Fastify web server (dashboard, WebSocket)
  |-- src/api/              MCP tool handlers
  |-- src/core/             Business logic (change management, reviews, tasks)
  |-- src/types/            TypeScript type definitions
  |-- src/utils/            Shared utilities (file parsing, project detection)
  |-- web/                  Frontend dashboard assets (React/Vite)
  |
  v
Local filesystem (OpenSpec project directory)
  |-- openspec/changes/     Change proposal files (Markdown with YAML frontmatter)
  |-- openspec/specs/       Specification files
  |-- openspec/reviews/     Review comment storage
  |-- .cross-service/       Cross-service shared documents (configured externally)
```

Key dependencies (from package.json v0.4.2):

- `@modelcontextprotocol/sdk` ^1.13.3 -- MCP server SDK
- `@fastify/cors` ^9.0.0 -- CORS handling for Fastify
- `@fastify/static` ^7.0.0 -- Static file serving
- `@fastify/websocket` ^8.2.0 -- WebSocket support for real-time updates
- `fastify` ^4.24.0 -- HTTP server for dashboard and API
- `chokidar` ^3.5.3 -- filesystem watcher for real-time updates
- `commander` ^12.0.0 -- CLI argument parsing
- `zod` ^3.22.0 -- schema validation for MCP tool parameters
- `gray-matter` ^4.0.3 -- YAML frontmatter parsing for proposal files

SOURCE: [GitHub repo file tree](https://github.com/Lumiaqian/openspec-mcp/tree/main/src) (accessed 2026-04-29), [package.json](https://raw.githubusercontent.com/Lumiaqian/openspec-mcp/main/package.json) (accessed 2026-04-29)

---

## Installation & Usage

```bash
# Prerequisite: Install OpenSpec CLI
npm install -g @fission-ai/openspec

# Add to Claude Code (MCP server only)
claude mcp add openspec -- npx openspec-mcp

# Add with web dashboard enabled
claude mcp add openspec -- npx openspec-mcp --with-dashboard

# Claude Desktop / Cursor (manual config)
# Add to MCP servers config:
# { "command": "npx", "args": ["-y", "openspec-mcp"] }
```

```bash
# CLI options
npx openspec-mcp [path]           # Project directory (default: current)
npx openspec-mcp --dashboard      # Web UI only (no MCP server)
npx openspec-mcp --with-dashboard # MCP server + web UI
npx openspec-mcp --port 4000      # Custom port (default 3000, auto-increments on conflict)
```

```text
# Example natural language interactions via Claude
"List all openspec changes"
"Show me the add-user-auth change"
"Mark task 1.1 as done in add-user-auth"
"Request approval for add-user-auth from @reviewer"
```

SOURCE: [README.md upstream](https://github.com/Lumiaqian/openspec-mcp/blob/main/README.md) (accessed 2026-03-02)

---

## Relevance to Claude Code Development

### Applications

- Provides a reference implementation for spec-driven AI development workflows where agents
  read, create, and track specifications rather than directly implementing features without
  formal change records
- The `openspec_get_instructions` tool pattern -- loading an AGENTS.md file as the first MCP
  call -- mirrors the claude_skills approach of providing agent context via SKILL.md files
- Change approval pipeline matches the human-in-the-loop model used in this repository's
  backlog and PR review workflows

### Patterns Worth Adopting

- State machine enforcement via MCP tools: each state transition is a distinct named tool
  (e.g., `request_approval`, `approve_change`) rather than a generic "update status" call,
  making agent intent explicit and auditable
- Cross-service document aggregation via configurable rootPath and document list in frontmatter
  is directly applicable to multi-plugin documentation in claude_skills
- Real-time WebSocket dashboard for task progress is a concrete pattern for surfacing agent
  activity without polling

### Integration Opportunities

- Could serve as the MCP server layer for the `/add-new-feature` -> `/implement-feature`
  workflow: feature contexts and task plans stored as OpenSpec changes, with approval gates
  before implementation begins
- The review system (`add_review`, `reply_review`, `resolve_review`) maps well to the
  code-reviewer agent output model where findings need human acknowledgment before closure
- `openspec_get_progress_summary` replaces the need for manual inspection of task files during
  the `/implement-feature` execution loop

---

## References

- [iflow-mcp/lumiaqian-openspec-mcp (fork)](https://github.com/iflow-mcp/lumiaqian-openspec-mcp) (accessed 2026-04-29)
- [Lumiaqian/openspec-mcp (upstream)](https://github.com/Lumiaqian/openspec-mcp) (accessed 2026-04-29)
- [README.md upstream](https://github.com/Lumiaqian/openspec-mcp/blob/main/README.md) (accessed 2026-04-29)
- [npm package: openspec-mcp](https://www.npmjs.com/package/openspec-mcp) (accessed 2026-04-29)
- [GitHub API repo metadata](https://api.github.com/repos/Lumiaqian/openspec-mcp) (accessed 2026-04-29)
- [GitHub releases v0.4.2](https://github.com/Lumiaqian/openspec-mcp/releases/tag/v0.4.2) (accessed 2026-04-29)
- [npm downloads API](https://api.npmjs.org/downloads/point/last-week/openspec-mcp) (accessed 2026-04-29)

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | 2026-04-29 |
| Version at Verification | v0.4.2 |
| Days Since Last Release | 107 days (latest: 2026-01-12) |
| Confidence: Statistics | high |
| Confidence: Features | high |
| Confidence: Architecture | high |
| Confidence: Usage Examples | high |
| Confidence: Limitations | medium |
| Next Review Recommended | 2026-07-29 |

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Spec Workflow MCP](./spec-workflow-mcp.md) | mcp-ecosystem | alternative spec-driven workflow tool with Requirements→Design→Tasks gates and approval state machine |
| [Saga MCP](./saga-mcp.md) | mcp-ecosystem | shares hierarchical task tracking (Projects>Epics>Tasks) and immutable activity log audit trail |
| [GitNexus](./gitnexus.md) | mcp-ecosystem | provides code intelligence context that complements OpenSpec's spec management via graph-based impact analysis |
| [CodeGraphContext](./codegraphcontext.md) | mcp-ecosystem | MCP server with repository-to-graph tools for cross-service dependency analysis alongside spec changes |
| [Ultra MCP](./ultra-mcp.md) | mcp-ecosystem | provides multi-provider routing and unified dashboard model for aggregating tools across services |
| [SourceSync.ai MCP](./sourcesyncai-mcp.md) | mcp-ecosystem | shares multi-source document aggregation pattern for knowledge base ingestion and cross-service sync |
| [Everything Claude Code](../agent-frameworks/everything-claude-code.md) | agent-frameworks | 16-agent framework implementing spec-driven orchestration and approval workflows alongside code execution |
