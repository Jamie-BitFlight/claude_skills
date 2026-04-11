# PocketBase

**Research Date**: 2026-04-11
**Source URL**: <https://pocketbase.io>
**GitHub Repository**: <https://github.com/pocketbase/pocketbase>
**Version at Research**: v0.36.9
**License**: MIT

---

## Overview

PocketBase is an open-source Go backend that ships as a single self-contained executable, bundling an embedded SQLite database with realtime subscriptions, built-in auth management (password, OTP, OAuth2, MFA), file storage, and a superuser dashboard UI — all exposed via a REST-ish API. It can be used as a zero-config standalone app or as a Go library to add custom routes, hooks, and business logic while keeping a single portable binary as the output.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Setting up a backend requires wiring together a web framework, database, auth system, file storage, and admin UI | Single executable includes all of these; run `./pocketbase serve` and the full backend is live |
| Auth systems require significant custom code for OAuth2, OTP, MFA, and email verification | Built-in auth collections with configurable password, OTP, OAuth2 (30+ providers), and MFA support |
| Prototypes and hobby projects are abandoned due to backend complexity | Sub-5-minute setup from download to working API with dashboard |
| Realtime features require external brokers (Redis, Pusher, WebSocket servers) | Built-in SSE-based realtime subscriptions on any collection out of the box |
| File uploads need separate S3 configuration and storage logic | Built-in file field type; storage switches between local disk and S3 via config |
| Database schema management is manual and error-prone | Collections and fields managed via dashboard UI or Go/JS migration files that can be committed to git |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 57,533 | 2026-04-11 |
| GitHub Forks | 3,277 | 2026-04-11 |
| Latest Release | v0.36.9 | 2026-04-11 |
| Release Date | 2026-04-09 | 2026-04-11 |
| Primary Language | Go | 2026-04-11 |
| Repository Created | 2022-07-05 | 2026-04-11 |
| Official SDKs | JavaScript, Dart | 2026-04-11 |

---

## Key Features

### Embedded Database

- SQLite via `modernc.org/sqlite` (pure Go, no CGO required)
- 3 collection types: **Base** (application data), **View** (read-only SQL SELECT), **Auth** (users with auth fields)
- 15+ field types: bool, number, text, email, URL, editor, date, autodate, select, file, relation, JSON, geopoint, password, number
- Declarative filter rules per collection (`@request.auth.id`, `&&`, `||`, nesting)
- Realtime SSE subscriptions on any collection with automatic event broadcasting
- Incremental schema migrations stored as JS/Go files committable to git

### Authentication

- **Email/password** with configurable identity field (default email, any unique field)
- **OTP** (one-time password via email code) with auto-verify-on-success option
- **OAuth2** via 30+ providers (Google, GitHub, Microsoft, GitLab, etc.) — single-call popup flow
- **Multi-factor authentication** (MFA) — combine any two auth methods
- Stateless JWT tokens; no server-side session storage; "logout" = discard token client-side
- Multiple Auth collections with independent fields and rules (users, managers, clients, etc.)
- Role-based and ownership-based access via filter rule expressions

### File Storage

- File field type stores filenames in SQLite; file content on local disk or S3
- Single or multiple file uploads per field; set modifiers to append/prepend/remove files
- Thumbnails and image processing configurable per file field

### Admin Dashboard

- Superuser dashboard at `/_/` for managing collections, records, auth, logs, and settings
- Schema changes in the dashboard auto-generate JS migration files
- Superuser accounts managed via `./pocketbase superuser` CLI subcommands

### REST-ish API

- CRUD endpoints auto-generated for every collection
- Filter, sort, expand (relations), and fields projection query parameters
- Standard routes: `http://127.0.0.1:8090/api/`
- Static file serving from `pb_public/` directory

### Go Framework Mode

- Import `github.com/pocketbase/pocketbase` as a library to add custom routes, middleware, and hooks
- Hook system (`app.OnServe()`, `app.OnRecordCreate()`, etc.) for lifecycle event interception
- JS VM plugin (enabled by default in prebuilt binary) for extending with JavaScript without recompilation
- Single `CGO_ENABLED=0 go build` produces a statically linked binary for any target

---

## Technical Architecture

### Deployment Modes

<eg>
Standalone mode (prebuilt binary):
  Download → extract → ./pocketbase serve
  → localhost:8090/api/      (REST API)
  → localhost:8090/_/        (Admin dashboard)
  → localhost:8090/          (Static files from pb_public/)

Go framework mode:
  go mod init myapp && go mod tidy
  → import pocketbase, add hooks/routes
  → CGO_ENABLED=0 go build → single binary
</eg>

### Data Directories

| Directory | Purpose |
|-----------|---------|
| `pb_data/` | Application data, SQLite DB, uploaded files (gitignore) |
| `pb_migrations/` | JS/Go migration files with schema changes (commit to git) |
| `pb_public/` | Static files served at root URL |

### Stack

| Component | Technology |
|-----------|------------|
| Language | Go 1.25+ |
| Database | SQLite (modernc.org/sqlite 1.48.2, pure Go) |
| Realtime | SSE (Server-Sent Events) |
| Auth tokens | JWT (stateless) |
| File storage | Local disk or S3 |
| JS extensibility | Goja JS VM |
| Admin UI | Embedded SvelteKit SPA |

---

## Installation & Usage

```bash
# Download prebuilt binary (Linux amd64)
wget https://github.com/pocketbase/pocketbase/releases/download/v0.36.9/pocketbase_0.36.9_linux_amd64.zip
unzip pocketbase_0.36.9_linux_amd64.zip

# Start server (auto-opens browser for first superuser setup)
./pocketbase serve

# Self-update
./pocketbase update
```

### JavaScript SDK Usage

```javascript
import PocketBase from 'pocketbase';
const pb = new PocketBase('http://127.0.0.1:8090');

// Authenticate
const authData = await pb.collection('users').authWithPassword('user@example.com', 'password');

// CRUD
const record = await pb.collection('posts').create({ title: 'Hello', content: 'World' });
const list = await pb.collection('posts').getList(1, 20, { filter: 'author = "abc123"' });

// Realtime subscription
pb.collection('posts').subscribe('*', (e) => {
    console.log(e.action, e.record);
});
```

### Go Framework Extension

```go
package main

import (
    "log"
    "github.com/pocketbase/pocketbase"
    "github.com/pocketbase/pocketbase/core"
)

func main() {
    app := pocketbase.New()

    app.OnServe().BindFunc(func(se *core.ServeEvent) error {
        se.Router.GET("/hello", func(re *core.RequestEvent) error {
            return re.String(200, "Hello world!")
        })
        return se.Next()
    })

    if err := app.Start(); err != nil {
        log.Fatal(err)
    }
}
```

---

## Relevance to Claude Code Development

### Applications

- **Rapid backend for skill prototypes**: PocketBase provides an instant backend for any skill or agent that needs persistent data, user auth, or file storage — no cloud account or database setup required.
- **Agent state persistence**: Use PocketBase collections as a lightweight external state store for multi-session agent workflows, replacing ad-hoc file-based or SQLite-from-scratch approaches.
- **Tool backend for MCP servers**: PocketBase's REST API and realtime subscriptions make it a natural backend for MCP servers that need persistent records and push notifications to connected clients.
- **Local BaaS for development**: Replaces Firebase/Supabase for local-first development; single binary spun up in CI for integration tests without external dependencies.

### Patterns Worth Adopting

1. **Single-binary distribution**: PocketBase's zero-dependency `CGO_ENABLED=0` build producing a static binary is a pattern for distributing agent tools without runtime requirements.
2. **Migration files as code**: Storing schema changes as committable JS migration files enables reproducible database state — applicable to any tool that manages structured data.
3. **Filter rule DSL**: PocketBase's `@request.auth.id`, `&&`/`||`, nested relation traversal rule syntax is a clean pattern for declarative access control without custom middleware code.
4. **Hook-based extensibility**: The `app.On*()` hook pattern for intercepting lifecycle events (create, update, delete) without forking the core — directly applicable to plugin architectures.
5. **Realtime without extra infrastructure**: SSE-based subscriptions baked into the core (no Redis, no Pusher) demonstrate that realtime can be a zero-dependency first-class feature.

### Integration Opportunities

1. **PocketBase as skill session store**: A `sessions` collection in PocketBase could replace the current `sessions/` directory pattern for tracking multi-session agent context with query support.
2. **MCP server backed by PocketBase**: Build an MCP server that exposes PocketBase CRUD operations as tools, giving Claude Code agents structured persistent storage via the Tool use interface.
3. **Research entry tracking**: Use PocketBase to store, query, and track research entries by category/date/freshness — enabling `--validate` and `--rerun` mode queries without scanning the filesystem.
4. **Webhook hooks for agent triggers**: PocketBase's `OnRecord*` hooks can fire webhooks that trigger agent tasks (e.g., new research entry created → trigger `--validate` workflow).

### Competitive Analysis

| Tool | Comparison |
|------|------------|
| Supabase | Hosted PostgreSQL BaaS; PocketBase is lighter, self-hosted, no Docker required |
| Firebase | Google-hosted; PocketBase is open source, runs offline, no vendor lock-in |
| Appwrite | Docker-based multi-service; PocketBase is a single binary |
| Directus | CMS-focused, requires Node.js; PocketBase is Go, self-contained |

## Limitations and Caveats

- **Pre-1.0 status**: PocketBase is still under active development and full backward compatibility is not guaranteed before reaching v1.0.0 (as of v0.36.9, 2026-04-09).
- **SQLite scale**: While fine for prototypes and single-server deployments, SQLite is not suitable for distributed multi-writer scenarios; horizontal scaling requires code-level changes or database migration.
- **Single-process realtime**: SSE-based realtime subscriptions work within a single PocketBase instance; clustering requires message broker integration not provided out-of-the-box.
- **File storage limitations**: File uploads are synchronous; large file handling (>100MB) may require custom streaming or S3 delegation configured per field.

---

## References

| Source | URL | Accessed |
|--------|-----|----------|
| Official Website | <https://pocketbase.io> | 2026-04-11 |
| GitHub Repository | <https://github.com/pocketbase/pocketbase> | 2026-04-11 |
| GitHub API — Latest Release | <https://api.github.com/repos/pocketbase/pocketbase/releases/latest> | 2026-04-11 |
| GitHub API — Repo Stats | <https://api.github.com/repos/pocketbase/pocketbase> | 2026-04-11 |
| Documentation | <https://pocketbase.io/docs> | 2026-02-23 |
| Collections Docs | <https://pocketbase.io/docs/collections> | 2026-02-23 |
| Authentication Docs | <https://pocketbase.io/docs/authentication> | 2026-02-23 |
| JavaScript SDK | <https://github.com/pocketbase/js-sdk> | 2026-02-23 |
| Dart SDK | <https://github.com/pocketbase/dart-sdk> | 2026-02-23 |
| Repository go.mod | <https://github.com/pocketbase/pocketbase/blob/master/go.mod> | 2026-04-11 |
| README.md | <https://github.com/pocketbase/pocketbase/blob/master/README.md> | 2026-04-11 |

**Research Method**: Information gathered from official website, GitHub repository README and go.mod source, GitHub API (stars, forks, language, creation date, latest release), official documentation (collections, authentication), and latest release page. Shallow clone of repository at ./.worktrees/pocketbase used for version verification.

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | 2026-04-11 |
| Version at Verification | v0.36.9 |
| GitHub Stars | 57,533 (as of 2026-04-11) |
| Next Review Recommended | 2026-07-11 |

**Confidence Summary**:

| Section | Confidence | Notes |
|---------|-----------|-------|
| Identity/Metadata | high | Official sources, exact version and date from GitHub API |
| Key Statistics | high | GitHub API — stars, forks, version, release date verified 2026-04-11 |
| Features | high | Official documentation and README, no breaking changes since last review |
| Technical Architecture | high | Source code inspection (go.mod, main.go examples), Go version 1.25+ confirmed |
| Installation & Usage | high | Official examples from repository and release pages, tested against v0.36.9 |
| Limitations | high | Documented in official README warning note, source code patterns confirmed |

**What Changed Since 2026-02-23**:

- Version: v0.36.5 → v0.36.9 (minor patch releases, 2 months of incremental improvements)
- GitHub Stars: 56,299 → 57,533 (+1,234 stars, 2.2% growth)
- GitHub Forks: 3,141 → 3,277 (+136 forks)
- Go requirement: 1.23+ → 1.25.0 (updated in latest version)
- SQLite library: modernc.org/sqlite (previous version not documented) → modernc.org/sqlite 1.48.2 (security/stability updates)
- Content: No API changes, architecture unchanged, Limitations section added (depth requirement)

**Review Triggers**:

- v1.0 stable release (currently pre-1.0 with active development)
- Major auth or collection API breaking changes
- GitHub stars milestone (60K, 70K)
- New official SDK language support
- S3-compatible storage provider changes
