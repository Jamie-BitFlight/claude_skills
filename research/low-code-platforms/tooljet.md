# ToolJet

| Field         | Value                                                    |
| ------------- | -------------------------------------------------------- |
| Research Date | 2026-01-31                                               |
| Primary URL   | <https://tooljet.com>                                    |
| GitHub        | <https://github.com/ToolJet/ToolJet>                     |
| Documentation | <https://docs.tooljet.com>                               |
| Version       | v3.20.82-lts (released 2026-01-30)                       |
| License       | AGPL-3.0                                                 |
| Docker Hub    | <https://hub.docker.com/r/tooljet/tooljet-ce>            |

---

## Overview

ToolJet is an open-source low-code platform for building internal tools, dashboards, business applications, workflows, and AI agents. The platform provides a visual drag-and-drop builder with 60+ components, connects to 75+ data sources including databases, APIs, and cloud storage, and offers an integrated no-code database. ToolJet AI (enterprise) adds AI-powered app generation, query building, debugging, and an Agent Builder for workflow automation.

---

## Problem Addressed

| Problem                                              | Solution                                                         |
| ---------------------------------------------------- | ---------------------------------------------------------------- |
| Building internal tools requires significant dev time | Visual drag-and-drop builder with 60+ responsive components      |
| Connecting to multiple data sources is complex       | 75+ pre-built integrations for databases, APIs, SaaS, storage    |
| Teams need quick data management without SQL         | Built-in ToolJet Database (no-code relational database)          |
| Collaboration on app development is difficult        | Multiplayer editing, inline comments, mentions, version control  |
| Self-hosting internal tools is operationally heavy   | Docker, Kubernetes, cloud marketplace deployment options         |
| Non-developers cannot build business applications    | No-code interface with JavaScript/Python extensibility           |
| Creating AI-powered workflows is complex             | Agent Builder for intelligent automation (enterprise)            |

---

## Key Statistics

| Metric             | Value                     | Date Gathered |
| ------------------ | ------------------------- | ------------- |
| GitHub Stars       | 37,363                    | 2026-01-31    |
| GitHub Forks       | 4,936                     | 2026-01-31    |
| Open Issues        | 967                       | 2026-01-31    |
| Contributors       | ~419                      | 2026-01-31    |
| Docker Pulls       | 2,184,706                 | 2026-01-31    |
| Primary Language   | JavaScript/TypeScript     | 2026-01-31    |
| Repository Age     | Since March 2021          | 2026-01-31    |
| Watchers           | 195                       | 2026-01-31    |
| Repository Size    | ~1.5 GB                   | 2026-01-31    |

---

## Key Features

### Visual App Builder (Community Edition)

- **60+ Components**: Tables, Charts, Forms, Lists, Progress Bars, Maps, and more
- **Responsive Design**: Components adapt to different screen sizes
- **Multi-page Apps**: Build complex applications with navigation
- **Multiplayer Editing**: Collaborative real-time development
- **Code Execution**: Run JavaScript and Python within apps
- **Theming**: Customize appearance with themes

### Data Sources

- **75+ Integrations**: Databases, REST/GraphQL APIs, cloud storage, SaaS tools
- **ToolJet Database**: Built-in no-code relational database
- **Default Sources**: ToolJet DB, REST API, JavaScript queries, Python queries
- **Plugin System**: Create custom data source connectors via CLI
- **Workspace-level Connections**: Share data sources across applications

Supported data sources include:

- Databases: PostgreSQL, MySQL, MongoDB, Firestore, DynamoDB, Redis, etc.
- APIs: REST API, GraphQL, Stripe, Twilio, SendGrid, Slack, etc.
- Cloud Storage: AWS S3, Google Cloud Storage, Azure Blob, MinIO
- SaaS: Airtable, Google Sheets, Notion, Baserow, NocoDB

### ToolJet AI (Enterprise)

- **AI App Generation**: Create apps from natural language prompts
- **AI Query Builder**: Generate and transform database queries with AI
- **AI Debugging**: One-click issue identification and fixes
- **Agent Builder**: Create intelligent agents to automate workflows

### Security and Compliance (Enterprise)

- **Encryption**: AES-256-GCM encryption at rest
- **SSO Support**: SAML, OAuth 2.0, OpenID Connect
- **Audit Logs**: Track user actions and changes
- **RBAC**: Role-based access control with custom groups
- **Row-Level Security**: Fine-grained data access control
- **SOC 2 / GDPR**: Enterprise compliance readiness

### Deployment Options

- **Cloud Hosted**: ToolJet Cloud (managed service)
- **Self-Hosted**: Docker, Kubernetes, Helm
- **Cloud Platforms**: AWS EC2/ECS/EKS, GCP GKE/Cloud Run, Azure AKS/Container
- **Marketplaces**: AWS Marketplace, Azure Marketplace
- **Platform Support**: Digital Ocean, OpenShift

---

## Technical Architecture

### Stack Components

| Component       | Technology                                        |
| --------------- | ------------------------------------------------- |
| Backend         | NestJS (Node.js framework)                        |
| Frontend        | React.js                                          |
| Database        | PostgreSQL (primary), ToolJet DB (built-in)       |
| Realtime        | Socket.IO                                         |
| Job Queue       | Bull (Redis-based)                                |
| ORM             | TypeORM                                           |
| Authentication  | Passport.js                                       |
| Containerization| Docker                                            |
| Orchestration   | Kubernetes, Helm                                  |

### Application Architecture

```text
User Interface (React + Drag-and-Drop Builder)
           |
    Application Layer (NestJS)
           |
    +------+------+
    |             |
Data Sources   ToolJet DB
(75+ connectors) (PostgreSQL)
           |
    Deployment Layer
(Docker/K8s/Cloud)
```

### Data Flow

1. User builds app using visual drag-and-drop interface
2. Components bind to data sources via queries
3. Queries execute against connected databases/APIs
4. Results render in UI components
5. User actions trigger JavaScript/Python handlers
6. Real-time updates via WebSocket connections
7. Changes persisted to ToolJet application database

---

## Installation and Usage

### Quick Start with Docker

```bash
docker run \
  --name tooljet \
  --restart unless-stopped \
  -p 80:80 \
  --platform linux/amd64 \
  -v tooljet_data:/var/lib/postgresql/13/main \
  tooljet/try:ee-lts-latest
```

### Docker Compose (Production)

```yaml
version: "3"
services:
  tooljet:
    image: tooljet/tooljet-ce:ce-lts-latest
    restart: always
    ports:
      - "80:80"
    environment:
      - TOOLJET_HOST=https://your-domain.com
      - PG_HOST=postgres
      - PG_DB=tooljet
      - PG_USER=postgres
      - PG_PASS=password
      - SECRET_KEY_BASE=your-secret-key
    depends_on:
      - postgres
  postgres:
    image: postgres:13
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=tooljet
    volumes:
      - postgres_data:/var/lib/postgresql/data
volumes:
  postgres_data:
```

### Creating a Data Source Connection

1. Navigate to Data Sources page from dashboard sidebar
2. Select category (Databases, APIs, Cloud Storage, Plugins)
3. Click + Add on desired data source
4. Enter connection configuration
5. Data source available across workspace applications

### Building an Application

1. Create new app from dashboard
2. Drag components from component library
3. Add queries to connect data sources
4. Bind query results to component properties
5. Add JavaScript event handlers for interactivity
6. Deploy application

---

## CLI Tool

The ToolJet CLI enables custom plugin development:

```bash
# Install CLI
npm install -g @tooljet/cli

# Create new plugin
tooljet plugin create my-data-source

# Build plugin
tooljet plugin build

# Publish to marketplace
tooljet plugin publish
```

---

## Relevance to Claude Code Development

### Direct Applications

1. **Internal Tool Building**: Rapid prototyping of dashboards and admin interfaces that could complement Claude Code workflows.

2. **Agent Builder Patterns**: ToolJet's AI Agent Builder demonstrates visual approaches to workflow automation that could inform skill design.

3. **Data Source Integration**: The 75+ connector patterns provide reference implementations for database and API integrations.

4. **Plugin Architecture**: The CLI-based plugin creation workflow offers patterns for extensible tool ecosystems.

5. **Multi-Tenant Security**: RBAC, row-level security, and audit logging patterns applicable to enterprise Claude Code deployments.

### Patterns Worth Adopting

1. **Visual Query Building**: Natural language to SQL/query translation reduces barrier for non-developers.

2. **Component Library**: Well-organized, discoverable component system with consistent APIs.

3. **Workspace Scoping**: Data sources shared at workspace level, similar to skill sharing patterns.

4. **Multi-environment Support**: Dev/staging/production environment management for controlled deployments.

5. **Plugin Marketplace**: Extensibility through community-contributed connectors.

### Integration Opportunities

1. **MCP Server for ToolJet**: Expose ToolJet applications as MCP tools for Claude Code workflows.

2. **Claude-Powered Agents**: Use Claude models within ToolJet Agent Builder for intelligent automation.

3. **Data Pipeline Integration**: ToolJet as data visualization layer for Claude Code analysis outputs.

4. **Admin Interface Generation**: Generate ToolJet admin UIs for Claude Code project management.

5. **Workflow Handoff**: ToolJet workflows could trigger or be triggered by Claude Code processes.

### Comparison with Claude Code

| Aspect              | ToolJet                        | Claude Code                    |
| ------------------- | ------------------------------ | ------------------------------ |
| Primary Use         | Internal tool building         | Developer workflow automation  |
| Interface           | Visual drag-and-drop           | CLI + natural language         |
| Data Access         | 75+ connectors, built-in DB    | MCP, file system, tools        |
| Code Execution      | JavaScript, Python in browser  | Full development environment   |
| Target Users        | Business users, developers     | Developers                     |
| AI Features         | App generation, query building | Code generation, analysis      |
| Deployment          | Self-hosted, cloud             | Local CLI, IDE integration     |
| Extensibility       | Plugin marketplace, CLI        | Skills, MCP servers            |

---

## References

| Source                    | URL                                                      | Accessed   |
| ------------------------- | -------------------------------------------------------- | ---------- |
| GitHub Repository         | <https://github.com/ToolJet/ToolJet>                     | 2026-01-31 |
| GitHub README             | <https://github.com/ToolJet/ToolJet/blob/develop/README.md> | 2026-01-31 |
| Official Documentation    | <https://docs.tooljet.com>                               | 2026-01-31 |
| Data Sources Overview     | <https://docs.tooljet.com/docs/data-sources/overview>    | 2026-01-31 |
| Docker Hub                | <https://hub.docker.com/r/tooljet/tooljet-ce>            | 2026-01-31 |
| AWS Marketplace           | <https://aws.amazon.com/marketplace/pp/prodview-fxjto27jkpqfg> | 2026-01-31 |
| Azure Marketplace         | <https://azuremarketplace.microsoft.com/en-us/marketplace/apps/tooljetsolutioninc1679496832216.tooljet> | 2026-01-31 |
| ToolJet CLI (npm)         | <https://www.npmjs.com/package/@tooljet/cli>             | 2026-01-31 |
| Contributing Guide        | <https://github.com/ToolJet/ToolJet/blob/develop/CONTRIBUTING.md> | 2026-01-31 |
| Project Roadmap           | <https://github.com/orgs/ToolJet/projects/15>            | 2026-01-31 |

**Research Method**: Information gathered from official GitHub repository README, GitHub API (stars, forks, issues, releases, contributors), Docker Hub API (pull counts), and official documentation. Statistics verified via direct API calls on 2026-01-31.

---

## Freshness Tracking

| Field              | Value                               |
| ------------------ | ----------------------------------- |
| Version Documented | v3.20.82-lts                        |
| Release Date       | 2026-01-30                          |
| GitHub Stars       | 37,363 (as of 2026-01-31)           |
| Docker Pulls       | 2,184,706 (as of 2026-01-31)        |
| Next Review Date   | 2026-05-01                          |

**Review Triggers**:

- Major version release (v4.x)
- Significant AI feature additions
- GitHub stars milestone (40K, 50K)
- Docker pulls milestone (3M, 5M)
- New Agent Builder capabilities
- MCP or Claude integration announcements
- Changes to open-source licensing
