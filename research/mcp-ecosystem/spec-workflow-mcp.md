---
title: "Spec Workflow MCP"
research_date: "2026-03-02"
source_url: "https://github.com/Pimzino/spec-workflow-mcp"
github_url: "https://github.com/Pimzino/spec-workflow-mcp"
version_at_research: "v2.2.5 (tag v0.0.28 is the latest git tag; npm package version is 2.2.5)"
license: "GPL-3.0"
last_verified: "2026-03-02"
version_at_verification: "2.2.5 (npm), v0.0.28 (git tag)"
next_review: "2026-06-02"
---

## Overview

Spec Workflow MCP is a Model Context Protocol server that provides structured, spec-driven development workflow tools for AI-assisted software development. It enforces a sequential document creation process (Requirements → Design → Tasks) with a human-in-the-loop approval gate between each phase. The server ships with a real-time web dashboard on port 5000 and a VSCode extension, giving developers visual oversight of spec progress and a UI for reviewing and approving AI-generated documents.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| AI coding agents write code without structured upfront requirements, leading to misaligned implementations | Enforces a Requirements → Design → Tasks sequence before any implementation begins |
| No human review point exists between AI-generated specs and implementation | Approval workflow requires explicit human sign-off on each document type before the next phase |
| Progress across multiple specs and tasks is invisible to developers | Real-time web dashboard aggregates all specs, approval queues, task completion, and implementation logs |
| Steering context (product goals, tech constraints) is not consistently available to AI agents | `get-steering-context` and `create-steering-doc` tools load project-level guidance into the AI's context |
| Task implementation logs are untracked and unsearchable | Implementation logs with code statistics are stored and exposed via the dashboard |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 3,936 | 2026-03-02 |
| Forks | 321 | 2026-03-02 |
| npm Downloads (last month) | 18,733 | 2026-03-02 |
| Latest npm Version | 2.2.5 | 2026-03-02 |
| Latest Git Tag | v0.0.28 | 2026-03-02 |
| Repository Created | 2025-08-07 | 2026-03-02 |
| Open Issues | 4 | 2026-03-02 |
| Primary Language | TypeScript | 2026-03-02 |
| Supported UI Languages | 11 | 2026-03-02 |

SOURCE: [GitHub API repos/Pimzino/spec-workflow-mcp](https://api.github.com/repos/Pimzino/spec-workflow-mcp) (accessed 2026-03-02)

SOURCE: [npm downloads API](https://api.npmjs.org/downloads/point/last-month/@pimzino/spec-workflow-mcp) (accessed 2026-03-02)

---

## Key Features

### Structured Spec Workflow

- Sequential three-phase document creation: requirements.md → design.md → tasks.md, each gated by approval
- Specs stored under `.spec-workflow/specs/{spec-name}/` in the project directory
- Spec naming uses kebab-case identifiers; each spec is a self-contained directory
- Steering documents (product, tech, structure) are created first and loaded into AI context for every subsequent operation

### MCP Tool Set (13 tools)

**Workflow guides** — read-only context injection:

- `spec-workflow-guide` — returns full workflow documentation as markdown
- `steering-guide` — returns guidance for creating steering documents

**Spec management**:

- `create-spec-doc` — creates or updates a requirements/design/tasks document; auto-requests approval on creation
- `spec-list` — returns all specs with status, progress percentage, and per-document approval state
- `spec-status` — returns detailed status for one spec including task counts and current phase
- `manage-tasks` — CRUD for task status (`update`, `complete`, `list`, `progress` actions)

**Context retrieval**:

- `get-template-context` — returns all document templates (requirements, design, tasks, steering types)
- `get-steering-context` — returns project steering document content filtered by type
- `get-spec-context` — returns complete spec content including document text and task statistics

**Steering documents**:

- `create-steering-doc` — creates product/tech/structure steering documents (no approval required)

**Approval workflow**:

- `request-approval` — creates an approval record; surfaces in dashboard for human review
- `get-approval-status` — polls approval state: `pending | approved | rejected | changes-requested`
- `delete-approval` — removes completed/rejected approval records from the queue

### Real-Time Web Dashboard

- Runs on port 5000 (`127.0.0.1` by default, preventing network exposure)
- Displays all specs, task progress bars, and per-document approval status
- Provides human UI for approving, rejecting, or requesting changes on documents
- Implementation logs with code statistics searchable through dashboard UI
- Single dashboard instance serves all projects simultaneously

### VSCode Extension

- Sidebar panel replicates dashboard functionality inside VSCode
- Installed from VSCode Marketplace (`Pimzino.spec-workflow-mcp`)
- Dashboard and extension are alternative interfaces; only one is needed per session

### Security Controls

- Rate limiting: 120 requests/minute per client with automatic cleanup
- Audit logging: structured JSON logs with timestamp, actor, action, and result
- Security headers: `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `CSP`, `Referrer-Policy`
- CORS restricted to localhost origins by default
- Docker hardening: non-root user, read-only filesystem, dropped capabilities, resource limits
- HTTPS/TLS and user authentication require an external reverse proxy (not built-in)

### Deployment Options

- npx (zero-install): `npx -y @pimzino/spec-workflow-mcp@latest /path/to/project`
- Docker Compose with volume mount for `.spec-workflow/` state persistence
- `SPEC_WORKFLOW_HOME` env var for redirecting global state in sandboxed environments (e.g., Codex CLI `sandbox_mode=workspace-write`)

---

## Technical Architecture

```text
AI Client (Claude Code, Cursor, etc.)
        |
        | MCP (stdio transport)
        v
  spec-workflow-mcp server (TypeScript, Fastify)
        |
        +---> Tool handlers
        |          |
        |          +---> File system (.spec-workflow/ directory tree)
        |          |         approvals/, specs/, steering/, templates/, archive/
        |          |
        |          +---> Approval state machine
        |                    pending → approved | rejected | changes-requested
        |
        +---> HTTP/WebSocket server (port 5000)
                   |
                   +---> Web dashboard (React + Vite + Tailwind, served as static files)
                   +---> VSCode Extension WebView (connects to same HTTP endpoint)
```

The MCP server and dashboard share the same Fastify process. State is stored as markdown files in `.spec-workflow/` within the target project directory, with TOML configuration (`config.example.toml`). File watching via `chokidar` pushes live updates to dashboard WebSocket clients.

The tool workflow enforces ordering: `create-spec-doc` calls `request-approval` internally for requirements and design documents, and the AI agent must poll `get-approval-status` before proceeding to the next document type. Tasks documents require an approved design to exist first.

SOURCE: [package.json via GitHub API](https://api.github.com/repos/Pimzino/spec-workflow-mcp/contents/package.json) (accessed 2026-03-02) — dependency list confirms Fastify 5, React 18, MCP SDK 1.24.3, chokidar 3, simple-git 3, zod 3

---

## Installation & Usage

### Add to Claude Code CLI

```bash
claude mcp add spec-workflow npx @pimzino/spec-workflow-mcp@latest -- /path/to/your/project
```

### Add to MCP config (any client)

```json
{
  "mcpServers": {
    "spec-workflow": {
      "command": "npx",
      "args": ["-y", "@pimzino/spec-workflow-mcp@latest", "/path/to/your/project"]
    }
  }
}
```

### Start the dashboard separately

```bash
npx -y @pimzino/spec-workflow-mcp@latest --dashboard
```

Dashboard runs at `http://localhost:5000`.

### Docker deployment

```bash
cd containers
docker-compose up --build
```

### Sandboxed environments (Codex CLI)

```bash
SPEC_WORKFLOW_HOME=/workspace/.spec-workflow-mcp npx -y @pimzino/spec-workflow-mcp@latest /workspace
```

### Typical AI conversation prompts

```text
"Create a spec for user authentication"
"List my specs"
"Execute task 1.2 in spec user-auth"
"Check approval status for user-auth requirements"
```

---

## Relevance to Claude Code Development

### Applications

- Directly installable as an MCP server into Claude Code CLI via `claude mcp add` — documented in the README with exact command syntax
- The spec-driven workflow maps to the `add-new-feature` → `implement-feature` pattern already in this repository, but operates via MCP tools rather than skill files
- Approval gates align with the human-decision artifact immutability principle in the local workflow documentation — requirements and design docs require explicit human approval before AI can proceed

### Patterns Worth Adopting

- The `request-approval` / `get-approval-status` polling pattern is a clean primitive for human-in-the-loop gates that does not require synchronous interaction; an AI agent creates the approval record, the human reviews in the dashboard UI at their own pace, and the agent polls until resolved
- Steering document types (product, tech, structure) as distinct context categories loaded before every spec operation is a well-structured way to inject project-level constraints into AI context
- File-based state storage under `.spec-workflow/` in the project directory (not a database) makes state auditable via git and portable across environments
- The `SPEC_WORKFLOW_HOME` env var for redirecting state in sandboxed environments is directly applicable to CI environments where `$HOME` is read-only

### Integration Opportunities

- Could be used alongside the SAM workflow: run spec-workflow-mcp for requirements/design approval, then pass the approved design document path to `add-new-feature` skill for task decomposition
- The `get-steering-context` tool could supplement the `context-gathering` agent in the `add-new-feature` phase by injecting project-level steering docs
- The dashboard WebSocket architecture is a reference for building real-time monitoring UIs for agent workflows — the pattern (Fastify + chokidar + React) applies to any file-based agent state

---

## References

- [GitHub Repository: Pimzino/spec-workflow-mcp](https://github.com/Pimzino/spec-workflow-mcp) (accessed 2026-03-02)
- [npm Package: @pimzino/spec-workflow-mcp](https://www.npmjs.com/package/@pimzino/spec-workflow-mcp) (accessed 2026-03-02)
- [VSCode Marketplace Extension](https://marketplace.visualstudio.com/items?itemName=Pimzino.spec-workflow-mcp) (accessed 2026-03-02)
- [GitHub API repo metadata](https://api.github.com/repos/Pimzino/spec-workflow-mcp) (accessed 2026-03-02)
- [npm Downloads API](https://api.npmjs.org/downloads/point/last-month/@pimzino/spec-workflow-mcp) (accessed 2026-03-02)
- [TOOLS-REFERENCE.md via GitHub API](https://api.github.com/repos/Pimzino/spec-workflow-mcp/contents/docs/TOOLS-REFERENCE.md) (accessed 2026-03-02)
- [package.json via GitHub API](https://api.github.com/repos/Pimzino/spec-workflow-mcp/contents/package.json) (accessed 2026-03-02)

---
