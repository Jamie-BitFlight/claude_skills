---
title: PocketBase
category: data-infrastructure
created: 2026-03-28
freshness_review_due: 2026-06-28
resource_url: https://github.com/pocketbase/pocketbase
---

## Overview

PocketBase is an open-source backend framework written in Go that packages database, authentication, file management, and realtime subscriptions into a single self-contained executable. The project emphasizes simplicity and portability, requiring only Go 1.25+ for development and providing pre-built binaries for all major platforms.

**Extract**: "PocketBase is an open source Go backend that includes: embedded database (SQLite) with realtime subscriptions, built-in files and users management, convenient Admin dashboard UI, and simple REST-ish API" (README.md, accessed 2026-03-28)

**Extract**: "Open Source realtime backend in 1 file" (GitHub repository description, accessed 2026-03-28)

## Identity

- **Name**: PocketBase
- **Version**: v0.36.7 (current stable release, accessed 2026-03-28)
- **Language**: Go
- **License**: MIT License
- **Repository**: <https://github.com/pocketbase/pocketbase>
- **Created**: July 5, 2022 (repository created)
- **Last Updated**: March 28, 2026

## Key Statistics (as of March 28, 2026)

- **GitHub Stars**: 57,177 stars
- **Forks**: 3,222 community forks
- **Language**: Go (primary implementation language)
- **Repository Activity**: Active development with recent updates (v0.36.7 released with SQLite 3.51.3 updates and rate limiter improvements)

**Extract**: "Updated modernc.org/sqlite to v1.46.2 and SQLite 3.51.3. SQLite 3.51.3 fixed a database corruption bug that is very unlikely to happen (with PocketBase even more so because we queue on app level all writes and explicit transactions through a single db connection)" (CHANGELOG.md v0.36.7, accessed 2026-03-28)

## Problem Addressed

PocketBase solves the fragmentation problem of backend development by combining essential backend services into a single, portable application. Traditional backend stacks require coordinating separate services for database, authentication, file storage, and API hosting. PocketBase eliminates this by:

1. **Database Integration**: Bundles SQLite as an embedded, serverless database with no separate database server required
2. **Authentication Layer**: Provides built-in user management, OAuth2 provider integration, and session handling
3. **File Management**: Integrated file upload, storage, and serving capabilities
4. **Realtime Capabilities**: Built-in WebSocket-based realtime subscriptions and event streaming via Server-Sent Events (SSE)
5. **Developer Interface**: Admin dashboard for data management without custom UI

**Extract**: "PocketBase has a hook-based architecture that allows extending with either Go or JavaScript" (core/base.go, accessed 2026-03-28). The hooks exposed include model validation, creation, update, deletion hooks, and record-level hooks for fine-grained control.

## Key Features

### 1. Embedded SQLite Database
- Database runs in-process, eliminating separate database server setup
- "embedded database (SQLite) with realtime subscriptions" (README.md)
- Supports concurrent access through connection pooling (DataMaxOpenConns, DataMaxIdleConns configuration)
- Atomic transactions queued through a single connection for consistency
- Auto-migration system with both Go and JavaScript template support

**Extract**: "The min Go version in the go.mod of the package was also bumped to Go 1.25.0 because some of the newer dep versions require it" (CHANGELOG.md v0.36.7, accessed 2026-03-28)

### 2. Realtime Subscriptions via SSE
- Server-Sent Events (SSE) for push-based data updates to clients
- Client-side subscription management through REST endpoints
- Automatic cleanup of idle connections (5-minute default timeout)
- Collection and record-level subscription filtering with ListRule constraints

**Extract**: "bindRealtimeApi registers the realtime api endpoints. sub := rg.Group('/realtime'). sub.GET('', realtimeConnect). sub.POST('', realtimeSetSubscriptions)" (apis/realtime.go, accessed 2026-03-28)

### 3. Authentication and User Management
- Built-in user record management with role-based access control
- OAuth2 integration with configurable external providers
- Email-based authentication with verification and password reset flows
- Multi-factor authentication (MFA) and one-time password (OTP) support
- SuperUser and auth origin tracking for administrative users

**Extract**: "APIs include record_auth_with_oauth2, record_auth_with_password, record_auth_with_otp, with separate endpoints for email change confirmation, verification, and password reset" (apis/record_auth*.go files, accessed 2026-03-28)

### 4. File Upload and Management
- Integrated file storage with local filesystem or S3-compatible object storage backends
- Automatic MIME type detection
- File size management through request body limits and rate limiting
- Image processing capabilities (resize, crop, etc.)

**Extract**: "NewFilesystem creates a new local or S3 filesystem instance for managing regular app files (ex. record uploads) based on the current app settings" (core/app.go, accessed 2026-03-28)

### 5. Admin Dashboard UI
- Web-based admin interface for managing collections, records, users, and settings
- No custom admin interface required for basic data management
- Built-in visual schema editor for collections
- Real-time event log and activity tracking

### 6. REST-ish API
- Simple REST conventions for CRUD operations on records
- Collection-based resource organization
- Batch operations support for bulk creates, updates, and deletes
- Health check and logging endpoints

**Extract**: "The easiest way to interact with the PocketBase Web APIs is to use one of the official SDK clients: JavaScript (pocketbase/js-sdk) for Browser, Node.js, React Native; Dart (pocketbase/dart-sdk) for Web, Mobile, Desktop, CLI" (README.md, accessed 2026-03-28)

### 7. Extensibility
- Hook-based extension system with lifecycle hooks for models, records, and collections
- Two extension mechanisms: Go framework integration or JavaScript hooks via JSVM
- JavaScript VM (goja runtime) for server-side hooks without recompilation
- Migration system supporting both Go and JavaScript templates

**Extract**: "app.OnServe().BindFunc(func(se *core.ServeEvent) error { se.Router.GET('/hello', func(re*core.RequestEvent) error { return re.String(200, 'Hello world!') })" (examples/base/main.go, accessed 2026-03-28)

### 8. Rate Limiting and Middleware
- Built-in rate limiting middleware with fixed window strategy
- GZIP compression support
- CORS configuration
- Body size limiting for request protection

**Extract**: "Updated the rate limiter reset rules to follow a more traditional fixed window strategy (aka. to be more close to how it is presented in the UI - allow max X user requests under Ys)" (CHANGELOG.md v0.36.7, accessed 2026-03-28)

## Technical Architecture

### Core Components

**BaseApp**: The fundamental application structure that implements the App interface. Manages:
- SQLite database connections (concurrent and non-concurrent pools)
- Hook system with 30+ hook types for extensibility
- Settings persistence and encryption
- Subscription broker for realtime features
- Cron scheduler for background tasks

**Extract**: "BaseApp struct fields: concurrentDB, nonconcurrentDB (for sequential operations), logger, subscriptionsBroker, store (runtime key-value), cron (background tasks), settings (persistent app config), onBootstrap, onServe, onTerminate, onBackupCreate, onModelValidate, onRecordCreate, onCollectionValidate, onRealtimeConnectRequest" (core/base.go, accessed 2026-03-28)

### Hook System Architecture

PocketBase uses a comprehensive hook system for extensibility with the following categories:

1. **App Lifecycle Hooks**: OnBootstrap, OnServe, OnTerminate, OnBackupCreate, OnBackupRestore
2. **Model Hooks**: OnModelValidate, OnModelCreate, OnModelUpdate, OnModelDelete (with pre/post/error variants)
3. **Record Hooks**: OnRecordValidate, OnRecordCreate, OnRecordUpdate, OnRecordDelete (with pre/post/error variants)
4. **Collection Hooks**: OnCollectionValidate, OnCollectionCreate, OnCollectionUpdate, OnCollectionDelete
5. **Realtime Hooks**: OnRealtimeConnectRequest, OnRealtimeMessageSend
6. **Mailer Hooks**: OnMailerSend, OnMailerRecordPasswordResetSend, etc.

Each hook supports both synchronous binding and asynchronous processing.

### Data Flow

1. **Request Ingestion**: HTTP requests routed through middleware (CORS, rate limiting, body size limits)
2. **Record Operations**: Record CRUD operations trigger lifecycle hooks (validate → create → after success/error)
3. **Realtime Broadcasting**: Changes trigger SubscriptionsBroker.Publish() to SSE-connected clients
4. **Background Tasks**: Cron scheduler executes time-based tasks
5. **Persistence**: All writes go through single-connection queue to SQLite for consistency

**Extract**: "e.App.SubscriptionsBroker().Register(ce.Client) registers new subscription client for realtime events; SubscriptionsBroker.Unregister(ce.Client.Id()) on disconnect" (apis/realtime.go, accessed 2026-03-28)

### Extension Points

**Go Framework Usage**: Applications embed PocketBase as a library and extend with Go code:

```go
app := pocketbase.New()
app.OnServe().BindFunc(func(se *core.ServeEvent) error {
    se.Router.GET("/hello", func(re *core.RequestEvent) error {
        return re.String(200, "Hello world!")
    })
    return se.Next()
})
app.Start()
```

**JavaScript Hooks**: Server-side logic via JavaScript:
- jsvm plugin loads hooks from directory (default pb_hooks/)
- Hot-reload support with file watcher
- Pool of pre-warmed goja.Runtime instances (default 15, configurable)
- Bindings to PocketBase API (database operations, mailer, filesystem, etc.)

**Extract**: "jsvm.MustRegister(app, jsvm.Config{MigrationsDir, HooksDir, HooksWatch, HooksPoolSize})" (examples/base/main.go, accessed 2026-03-28)

## Installation & Usage

### Standalone Application

1. Download pre-built binary from <https://github.com/pocketbase/pocketbase/releases>
2. Extract archive
3. Run: `./pocketbase serve`

**Extract**: "You could download the prebuilt executable for your platform from the Releases page. Once downloaded, extract the archive and run ./pocketbase serve in the extracted directory" (README.md, accessed 2026-03-28)

### As Go Framework

1. Install Go 1.25+
2. Create project with `go mod init myapp && go mod tidy`
3. Import and use PocketBase:
   ```go
   import "github.com/pocketbase/pocketbase"
   app := pocketbase.New()
   ```
4. Run: `go run main.go serve` or build: `CGO_ENABLED=0 go build`

**Extract**: "To build a statically linked executable, you can run CGO_ENABLED=0 go build and then start the created executable with ./myapp serve" (README.md, accessed 2026-03-28)

### Supported Build Targets

PocketBase binaries compile for 19 platform/architecture combinations via the pure Go SQLite driver (modernc.org/sqlite):
- darwin: amd64, arm64
- freebsd: amd64, arm64
- linux: 386, amd64, arm, arm64, loong64, ppc64le, riscv64, s390x
- windows: 386, amd64, arm64

**Extract**: "The supported build targets by the pure Go SQLite driver at the moment are: darwin amd64, darwin arm64, freebsd amd64, freebsd arm64, linux 386, linux amd64, linux arm, linux arm64, linux loong64, linux ppc64le, linux riscv64, linux s390x, windows 386, windows amd64, windows arm64" (README.md, accessed 2026-03-28)

## Limitations and Caveats

1. **Pre-v1.0 Status**: "Please keep in mind that PocketBase is still under active development and therefore full backward compatibility is not guaranteed before reaching v1.0.0" (README.md, accessed 2026-03-28)

2. **SQLite Limitations**: Inherits SQLite's single-writer model. All writes queue through a single connection for consistency, which may limit horizontal write scaling. Not suitable for multi-region deployments without replication.

3. **Single-Process Design**: The realtime subscription broker and cron scheduler run in-process. Scaling to multiple instances requires external coordination mechanisms (not built-in).

4. **JavaScript VM Overhead**: JSVM hooks execute in a pre-warmed pool (default 15 instances) with interpretation overhead. Heavy computational hooks in JavaScript may be slower than compiled Go equivalents.

5. **PR Review Workflow**: "PRs for new features without previously discussing implementation details may be closed, even if well-executed and tested" (CONTRIBUTING.md, accessed 2026-03-28).

6. **Memory Usage**: Recent fixes in v0.36.7 addressed high memory usage with large file uploads, indicating memory constraints remain a consideration for large uploads.

**Extract**: "Fixed high memory usage with large file uploads ([#7572](https://github.com/pocketbase/pocketbase/discussions/7572))" (CHANGELOG.md v0.36.7, accessed 2026-03-28)

## Relevance to Claude Code Development

### Agent Infrastructure and Backend Services
PocketBase is highly relevant for Claude Code workflows that need to:

1. **Rapid Backend Prototyping**: Stand up a complete backend (database + API + auth) for agent validation and testing without infrastructure setup. A single `./pocketbase serve` command provides a fully functional backend for testing agent-generated API specs.

2. **Testing Agent-Generated APIs**: Agents that generate API specifications can validate them against a real running backend. PocketBase's simple REST API makes it ideal for verifying API contract generation, validation rule testing, and schema verification tasks.

3. **Realtime Collaboration Features**: The SSE-based realtime subscriptions enable Claude Code agents to build interactive features requiring server-pushed updates (e.g., collaborative editing, live task updates, real-time status dashboards).

4. **Hook-Based Extensibility**: The comprehensive hook system aligns with Claude Code's plugin architecture. Agents can extend PocketBase behavior through JavaScript hooks without recompilation, similar to how Claude Code plugins extend the main application.

5. **Lightweight Data Persistence**: For agent infrastructure handling task queues, intermediate results, or state management, PocketBase provides embedded persistence without requiring separate database infrastructure.

6. **Multi-SDK Support**: PocketBase provides official SDKs for JavaScript/TypeScript and Dart, covering the primary languages used by Claude Code agents. The JavaScript SDK integrates naturally with agent workflows operating in Node.js environments.

7. **Simple Testing Framework**: The built-in testing guide and isolation capabilities make PocketBase suitable for agent-driven test infrastructure where tests need real database semantics but without deployment complexity.

### Specific Use Cases

- **Agent Task Backends**: Store and retrieve agent task state, execution logs, and results using PocketBase's record system with automatic timestamps and user tracking
- **Real-time Status Dashboards**: Use SSE subscriptions to push task completion events to monitoring dashboards
- **Schema Validation Playground**: Generate, deploy, and test database schemas automatically via Go framework integration with agents
- **Multi-Provider Authentication Testing**: Test OAuth2 and OIDC provider integrations against a real backend with MFA/OTP capabilities

## References

- **README.md**: <https://github.com/pocketbase/pocketbase/blob/master/README.md> (accessed 2026-03-28)
- **CHANGELOG.md**: <https://github.com/pocketbase/pocketbase/blob/master/CHANGELOG.md> — v0.36.7, v0.36.6, v0.36.5 release notes (accessed 2026-03-28)
- **Official Documentation**: <https://pocketbase.io/docs> (not directly read; linked in README)
- **CONTRIBUTING.md**: <https://github.com/pocketbase/pocketbase/blob/master/CONTRIBUTING.md> (accessed 2026-03-28)
- **Examples**: <https://github.com/pocketbase/pocketbase/blob/master/examples/base/main.go> (accessed 2026-03-28)
- **Source Files**: core/base.go, core/app.go, apis/realtime.go, plugins/jsvm/jsvm.go (accessed 2026-03-28)
- **GitHub API**: Repository metadata via <https://api.github.com/repos/pocketbase/pocketbase> (accessed 2026-03-28)
- **Official SDKs**:
  - JavaScript: <https://github.com/pocketbase/js-sdk>
  - Dart: <https://github.com/pocketbase/dart-sdk>

## Freshness Tracking

**Last Reviewed**: 2026-03-28

**Next Review Due**: 2026-06-28

### Confidence Map

- **Identity/Metadata**: high — GitHub repository and version verified from primary sources
- **Key Statistics**: high — Star count, forks, language verified from live GitHub API (2026-03-28)
- **Features**: high — Extracted from README, source code, and CHANGELOG with specific examples
- **Architecture**: high — Extracted from source files (core/base.go, apis/realtime.go, examples/base/main.go) with specific component names and data flow
- **Installation & Usage**: high — Extracted verbatim from README.md with exact commands
- **Limitations**: medium — Some from explicit documentation; memory/scaling limits inferred from code patterns and recent changelog entries
- **Relevance to Claude Code**: medium — Inferred from architecture alignment and SDK availability; requires validation through proof-of-concept usage

### Changes Since Last Review

N/A — initial entry created 2026-03-28

### Data Sources Inaccessible

- <https://pocketbase.io/docs> — Official documentation site not directly read (linked from README; would provide extended API reference and guides)
- Full historical contributor statistics — shallow clone limits contributor history visibility

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Dolt](./dolt.md) | data-infrastructure | Git-like version control for SQL data with branch/merge semantics, complementary for schema-versioned multi-environment testing |
| [Motherduck](./motherduck.md) | data-infrastructure | Serverless cloud analytics layer; PocketBase records → DuckDB for OLAP queries and embedded analytics |
| [Tinybird](./tinybird.md) | data-infrastructure | Real-time analytics API builder; routes PocketBase event streams to SQL-queryable analytics endpoints |
| [FastAPI](../api-frameworks/fastapi.md) | api-frameworks | Alternative Python backend framework; FastAPI's Pydantic validation patterns complement PocketBase's declarative collection schema system |
| [Motia](../api-frameworks/motia.md) | api-frameworks | Unified backend abstraction using Step primitives; similar problem domain (consolidating APIs, queues, and workflows into single runtime) |
| [Modelence](../api-frameworks/modelence.md) | api-frameworks | AI-native TypeScript backend with MongoDB; MongoDB alternative to PocketBase for schema-less data, contrasts embedded SQLite with cloud database models |
| [Tornado](../api-frameworks/tornado.md) | api-frameworks | WebSocket and long-polling support; shares async networking approach for realtime subscriptions beyond SSE |
| [Local Memory](../context-management/local-memory.md) | context-management | Persistent agent memory infrastructure; uses SQLite + Qdrant similar to PocketBase's embedded-database-first philosophy for stateful agents |
