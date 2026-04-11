---
title: Coolify
resource: coolify
github: https://github.com/coollabsio/coolify
website: https://coolify.io
license: Apache 2.0
repository_type: GitHub
last_accessed: 2026-04-11
---

## Overview

Coolify is an open-source, self-hostable PaaS (Platform-as-a-Service) alternative to Heroku, Netlify, and Vercel. It enables developers to manage servers, applications, databases, and services through a web UI using only an SSH connection to target infrastructure. Supports VPS, bare metal, Raspberry Pi, and any SSH-accessible hardware. Version v4.0.0-beta.472 (released 2026-04-09).

**Key positioning**: "No vendor lock-in. All configurations saved to your server—you can manage running resources without Coolify if needed, losing only automation and UI conveniences."

## Problem Addressed

Developers and small teams face vendor lock-in when using commercial PaaS platforms (Heroku, Vercel, Netlify). These platforms abstract infrastructure but charge premium rates, restrict deployment targets, and make migration expensive. Coolify addresses this by providing:

1. **Infrastructure ownership**: Deploy to any server you control via SSH (VPS, bare metal, local hardware, Raspberry Pi). No vendor lock-in.
2. **Cost efficiency**: Manage your own servers (starting ~$4-5/month for a basic VPS) instead of paying PaaS platform markups.
3. **Feature parity with commercial PaaS**: One-click deployments, automated SSL, database provisioning, preview environments, scheduled deployments—all self-hosted.
4. **Open-source alternative**: Full source visibility, community-driven development, potential for self-contribution and customization.

## Key Statistics

- **52,907 GitHub stars** (as of 2026-04-11)
- **4,030 forks**
- **Created**: 2021-01-25 (nearly 5 years old)
- **Last updated**: 2026-04-11
- **Primary language**: PHP (Laravel 12)
- **License**: Apache License 2.0
- **Current version**: v4.0.0-beta.472 (2026-04-09)

## Key Features

**Application Deployment**:
- Deploy from Git repositories (GitHub, GitLab, Gitea, Bitbucket, custom Git servers)
- Deploy pre-built Docker images
- Support for Node.js, PHP, Python, Ruby, Go, Rust, Static sites (Next.js, Svelte, Vue, React, etc.)
- Automatic SSL certificates via Let's Encrypt
- GitHub Actions integration for CI/CD
- Pull request preview environments (automatic per-PR deployment with unique URLs)
- Scheduled deployments and manual trigger options
- Build pack detection (automatic build configuration based on app type)

**Database Support**:
- Standalone instances: PostgreSQL, MySQL, MariaDB, MongoDB, Redis, ClickHouse, KeyDB, Dragonfly
- Database service templates for quick provisioning
- Automatic backups
- Point-in-time recovery

**Server Management**:
- SSH-based server connectivity (no agent required)
- Multi-server deployments
- Server health monitoring (CPU, memory, disk, Docker stats)
- Server patching and updates
- Traefik reverse proxy management per server

**Advanced Features**:
- WebSocket support via Soketi for real-time UI updates
- Notifications via Slack, Telegram, Discord, Email (via Resend)
- Resource monitoring and alerting
- Team-based access control and multi-tenancy
- API tokens with granular abilities (read, write, deploy)
- Docker Compose support for complex service stacks
- File volume management for persistent storage
- Custom domains and subdomain routing

**Cloud Offering**:
- Paid managed cloud version (app.coolify.io) with high-availability, included email notifications, premium support, and zero maintenance.

## Technical Architecture

**Backend Stack (PHP/Laravel)**:

Core technologies:
- **PHP 8.4** with Laravel 12 framework (using Laravel 10 file structure—no migration to new streamlined structure)
- **Livewire 3**: Reactive UI components (real-time form validation, interactive dashboards) without writing JavaScript
- **Tailwind CSS 4.1.18** with form and typography plugins for styling
- **Laravel Horizon 5**: Queue job monitoring dashboard with supervisor-based worker management
- **Laravel Sanctum 4**: API token-based authentication with custom ability scoping (read, write, deploy)
- **Laravel Actions** (lorisleiva/laravel-actions): Reusable domain actions callable as objects, jobs, or controllers

**Key Components**:

1. **Models (Domain Entities)**:
   - `Server`: Managed host connected via SSH with destination configurations and proxy settings
   - `Application`: Deployed app from Git or Docker image with environment variables, previews, deployment queue
   - `Service`: Pre-configured service stacks from templates (Docker Compose templates)
   - `Project` / `Environment`: Organizational hierarchy (Team → Project → Environment → Resources)
   - Standalone databases: Individual instance models for PostgreSQL, MySQL, MariaDB, MongoDB, Redis, ClickHouse, KeyDB, Dragonfly
   - `Team`, `User`: Multi-tenancy with role-based access (MEMBER, ADMIN, OWNER)
   - All models extend `BaseModel` with auto-CUID2 UUID generation; use traits `HasConfiguration`, `HasMetrics`, `HasSafeStringAttribute`, `ClearsGlobalSearchCache`

2. **Actions** (Domain Logic):
   - Organized by area: `Application/`, `Database/`, `Docker/`, `Proxy/`, `Server/`, `Service/`, `Shared/`, `Stripe/`, `User/`, `CoolifyTask/`, `Fortify/`
   - Each action implements single responsibility (e.g., `DeployApplication`, `CreateDatabase`, `ConfigureProxy`)
   - Callable as objects, can be dispatched as jobs, or wired as controller handlers

3. **Services** (Complex Orchestration)**:
   - `ConfigurationGenerator`: Generates Docker Compose, proxy config, environment configs
   - `DockerImageParser`: Parses Docker images, extracts port and volume metadata
   - `ContainerStatusAggregator`: Aggregates Docker container status across servers
   - `HetznerService`, cloud provider integrations
   - Business logic separated from single-action operations

4. **Jobs (Queue Workers)**:
   - **Deployment**: `ApplicationDeploymentJob` queues deployments with reproducible Docker builds
   - **Monitoring**: `ServerCheckJob` (health checks), `CheckForUpdatesJob`, `ServerPatchCheckJob`
   - **Cleanup**: `DockerCleanupJob`, `CleanupOrphanedPreviewContainersJob`
   - **Notifications**: `SendMessageToSlackJob`, `SendMessageToTelegramJob`, `SendMessageToPushoverJob`, `SendWebhookJob`, `ApplicationPullRequestUpdateJob`
   - **Database**: `SyncStripeSubscriptionsJob` (for cloud subscriptions)
   - Redis queue with Horizon for persistent, monitored job processing

5. **Livewire Components (UI)**:
   - Page components organized by domain: Server, Project, Settings, Security, Notifications, Terminal, Subscription, SharedVariables
   - Real-time interactivity via Alpine.js for client-side enhancements
   - Blade templates in `resources/views/livewire/`
   - Components listen to private team channels for event-driven updates (ApplicationStatusChanged, ServiceStatusChanged, etc.)

6. **Event Broadcasting**:
   - Soketi WebSocket server (ports 6001-6002 in development) for real-time status updates
   - Status change events: `ApplicationStatusChanged`, `ServiceStatusChanged`, `DatabaseStatusChanged`, `ProxyStatusChanged`
   - Livewire components subscribe via `getListeners()` to team-private broadcast channels

7. **API Layer**:
   - REST API at `/api/v1/` with OpenAPI 3.0 attributes for auto-generated documentation
   - Custom `ApiAbility` middleware for token scoping (read, write, deploy abilities)
   - `ApiSensitiveData` middleware masks sensitive data in responses
   - Inline form validation using `Validator` facade (no Form Request classes)
   - `serializeApiResponse()` helper for consistent response serialization

8. **Authorization**:
   - Policy-based authorization (~15 model-to-policy mappings in `AuthServiceProvider`)
   - Custom gates: `createAnyResource`, `canAccessTerminal`
   - Role hierarchy: MEMBER (1) < ADMIN (2) < OWNER (3) with comparison methods
   - Multi-tenancy via Teams with automatic notification settings initialization

9. **Frontend**:
   - **Vite 7.3.2** for asset bundling with HMR
   - **Vue 3.5.26** for component framework (alongside Livewire)
   - **Laravel Echo 2.2.7** for WebSocket event subscriptions
   - **xterm.js 5.5.0** for terminal emulation (interactive SSH sessions)
   - **Axios 1.13.2** for HTTP requests (API calls)

10. **Database**:
    - PostgreSQL (primary database driver)
    - Doctrine DBAL for database abstraction
    - Eloquent ORM with auto-casting via `casts()` method

11. **Infrastructure**:
    - **Docker/Docker Compose**: Target servers must have Docker and Docker Compose
    - **Traefik**: Reverse proxy for routing, SSL termination, load balancing (managed per server)
    - **SSH**: Core connectivity mechanism (no agent required on target servers)

**Configuration & Extensibility**:
- Custom validation rules in `app/Rules/`: ValidGitRepositoryUrl, ValidServerIp, ValidHostname, DockerImageFormat, etc.
- Helpers organized in `bootstrap/helpers/`: shared.php, constants.php, versions.php, subscriptions.php, domains.php, docker.php, services.php, github.php, proxy.php, notifications.php
- Spatie Laravel Data DTOs for structured data transfer (e.g., ServerMetadata)
- PHP Enums (TitleCase keys): ProcessStatus, Role, BuildPackTypes, ProxyTypes, ContainerStatusTypes
- Service providers in `app/Providers/`: AuthServiceProvider (policies + gates), FortifyServiceProvider (auth routes), etc.

**Testing**:
- Pest 4 testing framework with browser testing plugin (`Laravel Dusk 8`)
- Database testing with `RefreshDatabase` trait
- Livewire component tests
- Architecture tests via `arch()` assertions

## Installation & Usage

**Self-Hosted Installation**:

```bash
curl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash
```

Installs Coolify Docker Compose stack with default services: coolify app, PostgreSQL, Redis, Soketi, Vite dev server, Mailpit, MinIO.

Start development environment:
```bash
spin up
# or: docker compose -f docker-compose.dev.yml up -d
```

Access at `localhost:8000`.

**Cloud Version**:

Hosted at [app.coolify.io](https://app.coolify.io) with subscription-based pricing. Includes high-availability, email notifications, priority support, zero maintenance.

**Configuration**:

1. Connect a server via SSH (provide hostname, port, username, private key or password)
2. Add applications (Git repository, Docker image, or service template)
3. Configure environment variables, domains, resources
4. Trigger deployments (automatic on Git push with webhooks, manual via UI, or scheduled)
5. Monitor logs, metrics, and status via Livewire dashboard

**API Usage**:

Generate API token from settings. Use with granular abilities (read, write, deploy):

```bash
curl -X GET https://your-coolify-instance/api/v1/servers \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

## Key Conventions & Patterns

- **Laravel Actions**: Single-responsibility domain operations using `lorisleiva/laravel-actions` with `AsAction` trait
- **Livewire-first UI**: Real-time reactivity without building a separate SPA
- **Trait-based composition**: Models use traits for shared behavior (HasConfiguration, HasMetrics, etc.)
- **Job-based async processing**: Deployments, backups, notifications queued via Redis with Horizon monitoring
- **Policy-based authorization**: All resource access controlled via Laravel policies + gates
- **Webhook-driven**: GitHub/GitLab webhooks trigger deployments, PR preview creation/deletion

## Limitations and Caveats

1. **Requires Docker on target servers**: All deployments and services run in Docker containers. Target servers must have Docker Engine and Docker Compose installed and configured.

2. **SSH connectivity required**: The entire architecture depends on SSH access to target servers. No firewall-friendly agent model—direct SSH connection is mandatory for deployment operations.

3. **Beta version**: v4.0.0-beta.472 indicates ongoing development. Production use carries stability risks not yet present in stable releases.

4. **Limited built-in CI/CD**: GitHub Actions integration exists, but broader CI/CD orchestration (e.g., GitLab CI, Jenkins) requires manual webhook configuration.

5. **No native Kubernetes support**: Deployments target Docker on individual servers or Docker Swarm clusters. Kubernetes clusters are not supported.

6. **Storage and backup complexity**: While standalone databases have built-in backup options, complex multi-server backup strategies and restore procedures require manual configuration.

7. **Self-hosted operational overhead**: Unlike managed cloud versions, self-hosted instances require ongoing maintenance: database backups, SSL certificate renewal, server security updates, Coolify itself updates, and monitoring setup.

8. **Scaling complexity**: Horizontal scaling requires manual configuration of multiple servers and load balancing (via Traefik). No auto-scaling policies.

9. **Limited monitoring and alerting**: Basic server metrics and logs available; advanced observability (structured logging, distributed tracing, metrics aggregation) not built-in.

## Relevance to Claude Code Development

**High relevance for infrastructure-aware AI agents**:

1. **Deployment automation tasks**: Coolify's API and webhook system enable agents to automate application deployment workflows—triggering builds, managing environment variables, monitoring deployment status.

2. **Infrastructure as code patterns**: The Coolify codebase exemplifies Laravel patterns for infrastructure management: Docker composition, configuration generation, remote command execution via SSH, and multi-server orchestration.

3. **Real-time status updates**: Soketi WebSocket integration and Livewire reactive components provide templates for building real-time monitoring dashboards in AI assistants—showing deployment progress, server health, application logs.

4. **Job queue orchestration**: Heavy use of Laravel Horizon and Redis queue jobs demonstrates production patterns for background task processing—ideal for long-running deployment jobs, backups, and notifications.

5. **API design and token-based auth**: Coolify's RESTful API with granular token abilities (read, write, deploy) provides a model for designing secure, scoped APIs that agents can safely consume with limited permissions.

6. **Multi-tenancy and authorization**: Role-based access control (MEMBER/ADMIN/OWNER) and team-based isolation patterns are directly applicable to building multi-user AI platforms.

7. **Error handling and observability**: Extensive use of Laravel actions, event broadcasting, and structured logging provides patterns for building observable, maintainable agent orchestration systems.

## References

- **GitHub repository**: <https://github.com/coollabsio/coolify> (accessed 2026-04-11)
- **Official website**: <https://coolify.io> (accessed 2026-04-11)
- **Installation documentation**: <https://coolify.io/docs/installation> (referenced in README)
- **API documentation**: <https://coolify.io/docs/api> (referenced in OpenAPI integration)
- **Cloud version**: <https://app.coolify.io> (accessed 2026-04-11)

API statistics from `curl https://api.github.com/repos/coollabsio/coolify` (2026-04-11):
- Stars: 52,907
- Forks: 4,030
- Primary language: PHP
- License: Apache License 2.0
- Topics: coolify, databases, deployment, docker, docker-compose, laravel, postgres, mysql, redis, nodejs, self-hosted, self-hosting, server, static-site, svelte, nextjs

Repository metadata:
- Created: 2021-01-25T20:54:01Z
- Last updated: 2026-04-11T14:00:54Z
- Current version: v4.0.0-beta.472 (2026-04-09)

Source code analysis: Direct file reads from shallow clone at `/home/user/claude_skills/.worktrees/coolify/` (2026-04-11):
- composer.json: PHP 8.4, Laravel 12, Livewire 3, Laravel Horizon 5, Laravel Sanctum 4, Pest 4
- package.json: Vite 7.3.2, Vue 3.5.26, Tailwind CSS 4.1.18, xterm.js 5.5.0, Laravel Echo 2.2.7
- Job files: ApplicationDeploymentJob, ServerCheckJob, DockerCleanupJob, notification jobs (Slack, Telegram, Pushover)
- CLAUDE.md: Development setup, architecture overview, Laravel conventions

## Freshness Tracking

| Section | Confidence | Last Verified |
|---------|-----------|---------------|
| Identity/Metadata | high | 2026-04-11 |
| Problem Addressed | high | 2026-04-11 |
| Key Statistics | high | 2026-04-11 |
| Key Features | high | 2026-04-11 |
| Technical Architecture | high | 2026-04-11 |
| Installation & Usage | high | 2026-04-11 |
| Limitations | medium | 2026-04-11 |
| Relevance | medium | 2026-04-11 |

**Next review date**: 2026-07-11 (3 months)

**Confidence notes**:
- Identity, statistics, and features: full primary source read (README, package manifests, GitHub API)
- Architecture: direct source code analysis of Jobs, Models, Services, Livewire components, API layer from CLAUDE.md and file reads
- Installation: official docs referenced in README
- Limitations: identified from architecture constraints (Docker requirement, SSH connectivity, beta version status, no Kubernetes support)
- Relevance: inferred from architecture patterns applicable to agent development
