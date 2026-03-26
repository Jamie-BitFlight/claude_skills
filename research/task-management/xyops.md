---
# Research Entry: xyOps
# Generated: 2026-03-26
resource_name: xyOps
resource_type: workflow_automation_platform
github_url: https://github.com/pixlcore/xyops
---

# xyOps — Workflow Automation and Server Monitoring Platform

## Overview

"xyOps™ is a next-generation system for job scheduling, workflow automation, server monitoring, alerting, and incident response -- all combined into a single, cohesive platform. It's built for developers and operations teams who want to control their automation stack without surrendering data, freedom, or visibility."

xyOps is licensed under the **BSD-3-Clause** license and positioned as a comprehensive operations platform that integrates job scheduling, monitoring, alerts, and incident response into a single system. The project is actively maintained and publicly available on GitHub.

**Key Statistics** (as of 2026-03-26):
- Repository: `github.com/pixlcore/xyops`
- GitHub stars: 3,641 (accessed 2026-03-26)
- GitHub forks: 361 (accessed 2026-03-26)
- License: BSD-3-Clause (accessed via API)
- Current version: v1.0.40 (released 2026-03-24)
- Primary language: JavaScript (Node.js)
- Status: Active development (last pushed 2026-03-25)

## Problem Addressed

"Most automation platforms focus on workflow orchestration -- they run tasks, but they don't really help you see what's happening behind them. xyOps takes it further. It doesn't just schedule jobs; it connects them to real-time monitoring, alerts, server snapshots, and ticketing, creating a single, integrated feedback loop. When an alert fires, the email includes the running jobs on that server. One click opens a snapshot showing every process, CPU load, and network connection. If a job fails, xyOps can open a ticket with full context -- logs, history, and linked metrics."

xyOps addresses the fragmentation of operations workflows by consolidating scheduling, monitoring, alerting, and incident management into a unified system. Rather than requiring operators to switch between multiple tools, xyOps creates integrated feedback loops between job execution and system state monitoring.

## Key Features

**Job Scheduling and Workflow Automation**
- "Schedule jobs across your fleet, track performance, set alerts, and view everything live, all in one place"
- Visual workflow editor: "Use the graphical workflow editor to connect events, triggers, actions, and monitors into meaningful pipelines"
- Beyond basic cron: "xyOps brings superpowers to job scheduling, way beyond cron"

**Monitoring and Alerting**
- "Define exactly what you want to monitor, and get notified the moment things go wrong"
- Rich alerting system: "Rich alerting with full customization and complex triggers"
- Server snapshots: On alert trigger, users can view running processes, CPU load, and network connections

**Multi-Server Fleet Management**
- "Whether you have five servers or five thousand, xyOps adapts to your needs"
- Distributed agent system for managing geographically dispersed infrastructure

**Developer and Operations Focus**
- "Designed with you in mind. Yes, **you!**"
- Simple setup: "From download to deployment in minutes"

## Technical Architecture

### Core Components

xyOps runs as a component system built on the **pixl-server** framework. The main application loads the following core server components (referenced in loader.js):

1. **Storage Component** (`pixl-server-storage`) — Key/value/list data persistence
2. **Unbase Component** (`pixl-server-unbase`) — Database layer
3. **Web Server** (`pixl-server-web`) — HTTP server and static file serving
4. **API Component** (`pixl-server-api`) — REST API routing and handlers
5. **User Management** (`pixl-server-user`) — User authentication and sessions
6. **Debug Component** (`pixl-server-debug`) — Chrome DevTools integration
7. **xyOps Engine** (local `engine.js`) — Job scheduling, workflow execution, monitoring, and alerting logic

### Architecture Model

The architecture follows a plugin-based model: "xyOps is built on the PixlCore software stack, with first-party modules handling HTTP, API routing, storage, user auth, and the SPA client framework."

**Key Engine Responsibilities** (from engine.js):
- Active job tracking and lifecycle management (`activeJobs`, `jobDetails` collections)
- Alert state management (`activeAlerts`, `warmAlerts`)
- Job queueing and workflow execution
- Integration with satellite agents (`xysat`) for remote execution
- Configuration validation for required properties: `base_app_url`, `secret_key`, `log_dir`, `log_filename`, `temp_dir`

### Primary Library Modules

Key functional modules within the xyOps codebase (observed from lib/ directory):

| Module | Purpose |
|--------|---------|
| `action.js` | Workflow action execution and orchestration |
| `job.js` | Job lifecycle, execution state, and status tracking |
| `workflow.js` | Workflow definition, triggering, and execution control |
| `schedule.js` | Job scheduling and cron expression handling |
| `monitor.js` | Server and metric monitoring, alert evaluation |
| `alert.js` | Alert state management, notification dispatch |
| `multi.js` | Multi-server coordination and fleet management |
| `ticket.js` | Incident ticketing system integration |
| `api.js` | REST API endpoint handlers |
| `comm.js` | Communication with remote satellite agents |
| `sso.js` | Single Sign-On integration and authentication |
| `secret.js` | Secret and credential management |
| `mailer.js` | Email notification delivery |

### Data Model

Configuration is loaded from multiple files:
- `conf/config.json` — main application configuration
- `conf/sso.json` — SSO configuration
- `internal/unbase.json` — database configuration
- `internal/ui.json` — UI/frontend configuration
- `internal/intl.json` — internationalization settings

### Client-Side Framework

The web UI is built on **pixl-xyapp**, described as "A client-side JavaScript framework, designed to be a base for web applications." The UI handles workflow visualization, server management, monitoring dashboards, and job/alert management.

## Installation & Usage

### Docker Quick Start

"Just want to test out xyOps locally really quick? One-liner Docker command:"

```bash
docker run --detach --init --restart unless-stopped \
  -v xy-data:/opt/xyops/data \
  -v /local/path/to/xyops-conf:/opt/xyops/conf \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e TZ="America/Los_Angeles" \
  -e XYOPS_xysat_local="true" \
  -p 5522:5522 \
  -p 5523:5523 \
  --name "xyops01" \
  --hostname "xyops01" \
  ghcr.io/pixlcore/xyops:latest
```

"Then open <http://localhost:5522> in your browser, and use username `admin` and password `admin`."

Note: Replace `/local/path/to/xyops-conf` with a suitable location for the xyOps configuration on the host machine.

### Manual Development Installation

"Here is how you can download the very latest xyOps dev build and install it manually (may contain bugs!):"

```bash
git clone https://github.com/pixlcore/xyops.git
cd xyops
npm install
node bin/build.js dev
echo '{ "secret_key": "test" }' > conf/overrides.json
bin/debug.sh
```

"Passing `dev` to the build script means it will keep all JS and CSS unobfuscated (original source served as separate files)."

### Requirements

- **Node.js**: Requires version 16 or later. "You are using an incompatible version of Node.js (< v16). Please upgrade to v16 or later."
- **Build Dependencies**: For systems where better-sqlite3 must compile from source (Debian/Ubuntu: `build-essential python3-setuptools`; RedHat/Fedora: `gcc-c++ make`; macOS: Xcode command-line tools)

## Limitations and Caveats

xyOps is "not built on a conventional Node.js web stack. It does not use Express, Passport, React, TypeScript, or standard off-the-shelf session middleware." This design choice means:

- Standard Node.js framework assumptions do not apply when extending xyOps
- Auditors and developers must familiarize themselves with the PixlCore module stack rather than relying on common Node.js patterns
- The custom architecture requires understanding the pixl-server component model, storage layer, and first-party framework modules

**Licensing and Commercial Support**:
- Free tier: All app features with community support
- Professional tier: Private ticketing, 24-hour support turnaround
- Enterprise tier: SSO setup, air-gapped installation, 1-hour support turnaround, live chat

**Feature Restrictions** (from CONTRIBUTING.md):
"We do not accept feature PRs, but there are **lots** of other ways you can contribute!" Contributors can submit bug fixes and improvements but feature design is managed by the xyOps team.

## Relevance to Claude Code Development

xyOps provides a comprehensive reference implementation for building distributed, multi-tenant operations platforms. Relevant to Claude Code development in these areas:

1. **Workflow Orchestration Systems** — Demonstrates visual workflow definition, event-driven triggering, and multi-step job orchestration using a component-based architecture

2. **Distributed Agent Patterns** — The remote satellite agent system (`xysat`) shows patterns for coordinating work across distributed systems with secure communication and state management

3. **Real-Time Monitoring Integration** — Consolidates monitoring, alerting, and incident response without requiring operators to context-switch between systems

4. **Enterprise Operations Patterns** — Multi-tenancy, role-based access control, fleet management, and audit logging are built-in, not retrofitted

5. **Custom Framework Development** — Demonstrates building a production-grade application on a custom, non-Express stack, useful for teams prioritizing architectural control over framework conventions

6. **Security and Operations** — SSO integration, secret management, air-gapped deployment support, and threat modeling documentation provide enterprise-grade security patterns

## References

- **Repository**: <https://github.com/pixlcore/xyops> (accessed 2026-03-26)
- **Official Documentation**: <https://docs.xyops.io/> (referenced in README)
- **GitHub API Metadata**: Retrieved via `gh api repos/pixlcore/xyops` (2026-03-26)
- **Development Guide**: `docs/dev.md` in repository
- **Threat Model**: `THREAT_MODEL.md` in repository (comprehensive security architecture documentation)
- **Security Guide**: <https://docs.xyops.io/security> (referenced in README)
- **Governance Model**: <https://docs.xyops.io/governance> (referenced in README)
- **Longevity Pledge**: `LONGEVITY.md` in repository
- **Contributing Guide**: `CONTRIBUTING.md` in repository

## Freshness Tracking

**Last updated**: 2026-03-26
**Last verified**: 2026-03-26 (repository clone, GitHub API, documentation review)
**Next review**: 2026-06-26

### Confidence Levels

| Section | Confidence | Notes |
|---------|-----------|-------|
| Identity/Metadata | high | Extracted from GitHub API and official package.json |
| Key Statistics | high | GitHub API star count, fork count, version from package.json |
| Features | high | Extracted from official README and developer documentation |
| Technical Architecture | high | Verified through loader.js, engine.js, lib/ module inspection, and development guide |
| Installation & Usage | high | Verbatim from official README and development guide |
| Limitations | medium | Some limitations inferred from development guide and CONTRIBUTING.md; not exhaustively documented |
| Relevance | medium | Assessment of relevance to Claude Code development based on architectural review |

### Data Sources Accessed

1. **GitHub API** (`gh api repos/pixlcore/xyops`) — Repository metadata, star count, fork count, license
2. **Local worktree clone** (`/tmp/.worktrees/xyops/`) — README.md, package.json, source files, documentation
3. **Source files analyzed**:
   - `lib/loader.js` — Component initialization and dependency wiring
   - `lib/main.js` — Entry point and version requirements
   - `lib/engine.js` — Core engine lifecycle and job/alert management
   - `package.json` — Dependencies, version, metadata
   - `docs/dev.md` — Development setup and framework documentation
   - `THREAT_MODEL.md` — Security architecture context
   - `CHANGELOG.md` — Recent releases and version history

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Beads](./beads.md) | task-management | Distributed task graph database with Git-backed storage for long-horizon AI agent workflows |
| [Claude Task Master](./claude-task-master.md) | task-management | PRD-to-task transformation and structured task orchestration for AI agents via MCP |
| [Vibe Kanban](./vibe-kanban.md) | task-management | Multi-agent orchestration UI with git worktree isolation and parallel execution tracking |
| [Plano](../agent-infrastructure/plano.md) | agent-infrastructure | AI-native proxy orchestration with unified routing, observability, and guardrails for multi-agent systems |
| [Everything Claude Code](../agent-frameworks/everything-claude-code.md) | agent-frameworks | Comprehensive agent automation framework with hook-based session persistence and multi-service orchestration |
| [Fly.io](../agent-infrastructure/fly-io.md) | agent-infrastructure | Cloud platform with Firecracker isolation and Sprites for distributed agent execution and stateful sandboxes |
| [OpenHands](../coding-agents/openhands.md) | coding-agents | Cloud infrastructure for scaling AI agents with model-agnostic SDK and orchestration patterns |

