---
resource: Hoppscotch
category: developer-tools
created: 2026-04-11
updated: 2026-04-11
next-review: 2026-07-11
---

# Hoppscotch — Open Source API Development Ecosystem

## Overview

Hoppscotch is an open-source API development ecosystem offering a Postman/Insomnia alternative with support for web, desktop, CLI, and self-hosted deployments. It enables developers to design, test, and debug APIs across REST, GraphQL, WebSocket, Server-Sent Events, Socket.IO, and MQTT protocols. The project emphasizes lightweight UI design, real-time response feedback, and offline-first PWA capabilities.

**Official Description** (from GitHub): "Open-Source API Development Ecosystem • <https://hoppscotch.io> • Offline, On-Prem & Cloud • Web, Desktop & CLI • Open-Source Alternative to Postman, Insomnia"

SOURCE: GitHub repository description (accessed 2026-04-11)

## Problem Addressed

Proprietary API development tools (Postman, Insomnia) impose licensing constraints, data privacy concerns, and vendor lock-in. Hoppscotch provides a free, open-source alternative that runs entirely offline, supports self-hosting for on-premises deployments, and eliminates the need for external account dependencies. It addresses the need for quick API request composition, testing, and debugging without the overhead of heavyweight IDE integrations.

## Key Statistics

- **Stars**: 78,884 (GitHub, as of 2026-04-11)
- **Forks**: 5,788
- **Open Issues**: 753
- **Primary Language**: TypeScript
- **License**: MIT
- **Latest Version**: 3.0.1 (with CLI at v0.30.3)
- **Created**: 2019-08-21
- **Last Updated**: 2026-04-11

SOURCE: GitHub API repository metadata (accessed 2026-04-11)

## Key Features

### Request Building & HTTP Methods
- Lightweight, minimalistic UI supporting HTTP methods: GET, POST, PUT, PATCH, DELETE, HEAD, CONNECT, OPTIONS, TRACE, and custom methods
- Copy/share public URLs, generate request code snippets for 10+ languages and frameworks
- Import cURL commands directly

SOURCE: README.md features section (accessed 2026-04-11)

### Protocol Support
- **WebSocket**: Full-duplex communication channels over single TCP connection
- **Server-Sent Events (SSE)**: Stream updates from server over HTTP without polling
- **Socket.IO**: Send and receive data with SocketIO servers
- **MQTT**: Subscribe and publish to MQTT broker topics
- **GraphQL**: Endpoint configuration, schema introspection with multi-column docs, custom request headers, query execution

SOURCE: README.md features section (accessed 2026-04-11)

### Authentication & Authorization
Supports multiple auth schemes:
- None
- Basic Authentication
- Bearer Token
- OAuth 2.0
- OIDC Access Token/PKCE

SOURCE: README.md features section (accessed 2026-04-11)

### Request Management & Collections
- **Collections**: Unlimited collections, folders, and requests with nesting
- **Export/Import**: File-based or GitHub gist export/import
- **Request Body**: FormData, JSON, and multiple content types with key-value or RAW input modes
- **Pre-Request Scripts**: JavaScript snippets executed before request (set variables, add timestamps, dynamic parameters)
- **Post-Request Tests**: JavaScript-based assertions checking status codes, response headers, data parsing, variable setting
- **Environments**: Unlimited environment variables with initialization via pre-request script, export/import from GitHub gist

SOURCE: README.md features section (accessed 2026-04-11)

### Collaboration Features
- **Teams**: Unlimited teams, shared collections, members, role-based access control, cloud sync
- **Workspaces**: Organize personal and team collections/environments into workspaces with instant switching
- **Cloud Sync**: Real-time synchronization of workspaces, history, collections, environments, settings across devices
- **Multi-user Auth**: Sign in via GitHub, Google, Microsoft, Email, or SSO (Enterprise Edition)

SOURCE: README.md features section (accessed 2026-04-11)

### Response Handling
- Copy response to clipboard or download as file
- View response headers
- Preview HTML, image, JSON, and XML responses with raw view option

### Additional Features
- **History**: Request entries synced with cloud/local session storage
- **Theming**: Customizable light/dark/black themes with multiple accent colors; Zen mode
- **PWA**: Progressive Web App with Service Workers, offline support, low resource usage, desktop PWA installation
- **Proxy**: Proxy mode for accessing blocked APIs, hiding IP, fixing CORS issues, accessing non-HTTPS endpoints (official proxy via proxyscotch)
- **i18n**: Multi-language support with community translation contributions
- **Keyboard Shortcuts**: Optimized efficiency shortcuts
- **Bulk Edit**: Key-value pair editing with newline separation and line disabling

SOURCE: README.md features section (accessed 2026-04-11)

### Admin & Team Management
- Team admin dashboard with insights
- User and team member management
- Team invitation workflows

SOURCE: README.md features section (accessed 2026-04-11)

## Technical Architecture

### Architecture Pattern: Monorepo Microservices
Hoppscotch uses a monorepo structure with 13 specialized packages enabling modular development and independent deployment.

SOURCE: /packages/ directory listing in worktree (accessed 2026-04-11)

### Core Packages

**Backend (NestJS + Express)**
- Framework: NestJS microframework with Express.js HTTP server
- Key Components: GraphQL schema generation, Swagger/OpenAPI documentation, session management, cookie parsing, validation pipes
- Authentication Guards and Authorization Decorators
- Error handling with custom error definitions
- Admin dashboard module
- Health check endpoints
- Mock server capability
- Orchestration module for API automation

SOURCE: /packages/hoppscotch-backend/src/main.ts and directory structure (accessed 2026-04-11)

**Frontend (Vue 3 + Vite)**
- Framework: Vue 3 with Composition API
- Build Tool: Vite bundler for fast development and optimized builds
- Code Editors: CodeMirror for syntax highlighting across JSON, JavaScript, XML, GraphQL with language-specific modes
- Data Fetching: GraphQL code generation with automatic type binding
- UI Components: Monaco Editor integration (@guolao/vue-monaco-editor)
- Request Execution: Tauri integration for desktop client capabilities
- Sandbox: @hoppscotch/js-sandbox for safe pre/post-request script execution

SOURCE: /packages/hoppscotch-common/package.json (accessed 2026-04-11)

**CLI Package (@hoppscotch/cli)**
- CLI tool for running Hoppscotch test scripts in CI/CD environments
- Binary: `hopp` command
- Node.js Requirement: >=22
- Version: 0.30.3 (independent from main app v3.0.1)
- Enables automation of API tests in continuous integration pipelines

SOURCE: /packages/hoppscotch-cli/package.json (accessed 2026-04-11)

**Supporting Packages**
- `hoppscotch-kernel`: Core request execution engine
- `hoppscotch-relay`: Request relay/proxy functionality
- `hoppscotch-desktop`: Tauri-based desktop client
- `hoppscotch-selfhost-web`: Web version for self-hosted deployments
- `hoppscotch-data`: Data models and utilities shared across packages
- `hoppscotch-agent`: Request agent for diverse protocol support
- `hoppscotch-js-sandbox`: Isolated JavaScript execution environment for scripts
- `hoppscotch-sh-admin`: Admin interface for self-hosted instances
- `codemirror-lang-graphql`: Custom CodeMirror language support for GraphQL

SOURCE: /packages/ directory listing (accessed 2026-04-11)

### Data Flow

1. **Request Submission**: User composes request via Vue.js frontend UI
2. **Pre-Request Processing**: Pre-request scripts execute in isolated @hoppscotch/js-sandbox environment, setting variables/headers
3. **Request Execution**: hoppscotch-kernel executes HTTP/WebSocket/GraphQL/MQTT request via hoppscotch-agent
4. **Proxy Handling** (optional): Requests routed through CORS proxy if enabled
5. **Response Capture**: Response headers/body captured and returned to frontend
6. **Post-Request Processing**: Post-request tests execute against response data in sandbox
7. **Cloud Sync**: Collections, history, environments persisted via GraphQL mutations to NestJS backend
8. **GraphQL Generation**: Backend auto-generates GraphQL schema from database models via Prisma ORM

SOURCE: Architecture inference from package structure and dependencies (confidence: code-read)

### Deployment Options

- **Cloud**: Hosted at hoppscotch.io with auth (GitHub, Google, Microsoft, Email, SSO)
- **Self-Hosted**: Via hoppscotch-selfhost-web package with own authentication
- **Desktop**: Tauri-based native apps for Windows, macOS, Linux
- **CLI**: @hoppscotch/cli for CI/CD integration
- **PWA**: Progressive Web App for mobile/tablet devices

SOURCE: README.md deployment section and package structure (accessed 2026-04-11)

### Dependency Highlights
- **Package Manager**: pnpm@10.32.1 (enforced at install time)
- **Testing**: Vitest for unit tests
- **Linting**: ESLint with TypeScript support (vue-tsc type checking)
- **Code Quality**: Husky pre-commit hooks with lint-staged
- **API Documentation**: Swagger/OpenAPI generation from decorators

SOURCE: /package.json root and package.json files (accessed 2026-04-11)

## Installation & Usage

### Web Usage (Cloud or Self-Hosted)
1. Visit [hoppscotch.io](https://hoppscotch.io) or deploy self-hosted instance
2. Sign in or create account (cloud) / local session (self-hosted)
3. Provide API endpoint in URL field
4. Click "Send" to simulate request
5. View response in real-time

SOURCE: README.md usage section (accessed 2026-04-11)

### CLI Installation
```bash
npm install -g @hoppscotch/cli
# or with pnpm
pnpm add -g @hoppscotch/cli
```

### CLI Usage
```bash
hopp run <path-to-collection-file>
```

SOURCE: /packages/hoppscotch-cli/package.json (accessed 2026-04-11)

### Desktop Installation
- Download from [docs.hoppscotch.io/documentation/clients/desktop#download-hoppscotch-desktop-app](https://docs.hoppscotch.io/documentation/clients/desktop)
- Supports Windows, macOS, Linux

SOURCE: README.md demo section (accessed 2026-04-11)

### Development Setup
1. Clone repository
2. Install dependencies: `pnpm install` (enforced package manager)
3. Copy `.env.example` to `.env`
4. Start development server: `pnpm dev`
5. Backend and frontend start in parallel with hot-reload

SOURCE: /README.md developing section and configuration files (accessed 2026-04-11)

## Limitations and Caveats

### Not Documented in Reviewed Sources
No official limitations are documented in the README or public documentation. Common limitations in similar tools include:

- **Rate Limiting**: No mention of rate limiting on free cloud instances — enforcement level unknown
- **Storage Quotas**: No documented limits on collection/request counts or storage size
- **Request Size Limits**: No documented maximum payload size for requests/responses
- **Concurrent Request Limits**: No documented concurrent request limitation
- **Export Formats**: Collections export to Postman v2.1 format compatibility not documented

SOURCE: Not mentioned in documentation (confidence: low — absence of documented limitations does not confirm absence of actual limitations)

### Known Constraints

**Enterprise Features Behind Edition Gate**: SSO authentication is exclusive to Enterprise Edition self-hosted deployments. Free cloud version does not support SSO.

SOURCE: README.md footnote [^EE] and auth section (accessed 2026-04-11)

## Relevance to Claude Code Development

### Direct Applications

1. **API Testing Automation**: Hoppscotch CLI (@hoppscotch/cli) enables agents to run API test scripts in CI/CD pipelines, automating API quality gates for feature verification.

2. **Multi-Protocol Request Handling**: The architecture demonstrates patterns for supporting diverse API protocols (REST, GraphQL, WebSocket, MQTT, SSE) — a challenge agents face when testing modern backend systems with heterogeneous API types.

3. **Monorepo Organization Pattern**: The 13-package structure with clear separation (backend, frontend, CLI, desktop, core engine, sandbox) provides a model for organizing multi-purpose tools with different deployment targets.

4. **Pre/Post-Request Script Execution**: The JavaScript sandbox pattern for safe script execution mirrors challenges agents solve when needing to run untrusted code in controlled environments.

5. **GraphQL Schema Integration**: Automatic schema introspection and code generation from GraphQL endpoints is relevant to agents building dynamic API clients.

6. **Proxy Architecture**: The CORS proxy pattern and request relay mechanism (hoppscotch-relay) is applicable to agents working with restricted API access or bridging cross-origin request barriers.

### Indirect Learning Points

- **Cloud Sync Architecture**: Real-time synchronization of user data across devices without tight coupling suggests patterns for distributed state management agents might employ.
- **Team Collaboration Model**: Role-based access control and workspace organization provides insight into multi-agent team coordination structures.
- **Self-Hosting as Deployment Strategy**: Support for cloud, self-hosted, desktop, and CLI versions demonstrates a platform architecture suitable for various deployment contexts agents operate within.

### Not Directly Applicable

- **UI/UX Theming**: Desktop theme customization and Zen mode have limited relevance to agent development.
- **Non-Critical Features**: History syncing, request labeling, and bulk editing are user-facing productivity features with minimal agent-level impact.

## References

- GitHub Repository: [hoppscotch/hoppscotch](https://github.com/hoppscotch/hoppscotch) (accessed 2026-04-11)
- Official Website: [hoppscotch.io](https://hoppscotch.io) (accessed 2026-04-11)
- Documentation: [docs.hoppscotch.io](https://docs.hoppscotch.io) (accessed 2026-04-11)
- CLI Package: [@hoppscotch/cli on npm](https://www.npmjs.com/package/@hoppscotch/cli) (referenced from package.json)
- Proxy: [proxyscotch GitHub](https://github.com/hoppscotch/proxyscotch) (referenced in README)
- Browser Extensions: [hoppscotch-extension GitHub](https://github.com/hoppscotch/hoppscotch-extension) (referenced in README)

## Freshness Tracking

**Last Updated**: 2026-04-11
**Next Review**: 2026-07-11 (90 days)

### Confidence by Section

| Section | Confidence | Notes |
|---------|-----------|-------|
| Overview & Problem Addressed | high | Official description and GitHub metadata |
| Key Statistics | high | Retrieved from GitHub API on 2026-04-11 |
| Key Features | high | Extracted directly from official README.md |
| Technical Architecture | medium | Inferred from package structure and source files; backend confirmed via main.ts; frontend confirmed via package.json and dependencies |
| Installation & Usage | high | Direct quotes from README and package configuration |
| Limitations | low | Documented absence of limitations; actual constraints unknown |
| Relevance to Claude Code | medium | Based on architectural patterns observed; direct agent use cases hypothesized but not yet validated |

**Confidence Justification**:
- High: Full README read, GitHub API metadata, official package.json sources
- Medium: Architecture inferred from directory structure and partial source file reads (10 files examined, budget limit reached at Tier 2)
- Low: Limitations section relies on absence of documentation; actual feature limits unverified by testing

**Changes from Prior Entry** (if applicable): N/A — first entry

---

*Entry created via research-curator agent. All factual claims trace to primary sources listed above.*
