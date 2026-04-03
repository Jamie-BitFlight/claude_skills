# Fleet: Open-Source Device Management Platform

## Overview

Fleet is an open-source device management platform designed for IT and security teams managing thousands of computers. It provides APIs, GitOps, webhooks, YAML, and human-friendly interfaces for managing endpoints at scale. Fleet is built on osquery, nanoMDM, Nudge, and swiftDialog, and supports Windows, macOS, Linux, Chromebooks, cloud infrastructure (AWS, GCP, Azure), and containers.

**Repository**: <https://github.com/fleetdm/fleet>
**Primary Language**: Go (backend), TypeScript/React (frontend)
**Latest Version**: 4.82.1 (released Mar 18, 2026)
**License**: Mixed (MIT for open source, commercial license for premium features)

---

## Problem Addressed

Organizations managing large fleets of devices need consolidated visibility and control across heterogeneous environments. Traditional MDM solutions are often rigid, vendor-locked, or designed for smaller deployments. Fleet addresses this by:

1. **Data exploration at scale**: Provides access to raw osquery data for custom queries and ad-hoc investigations without predefined boundaries
2. **Cross-platform device management**: Single platform for Windows, macOS, Linux, Chromebooks, and cloud infrastructure management
3. **Security and compliance automation**: Detection engineering via policy queries, vulnerability scanning, CIS benchmark enforcement
4. **Lightweight and modular architecture**: Can be deployed and used for security independently of MDM, or vice versa
5. **Integration with existing tools**: Works with Splunk, Snowflake, GitHub Actions, Vanta, Elastic, Jira, Zendesk, Munki, Chef, Puppet, Ansible, CrowdStrike, SentinelOne

---

## Key Statistics

- **6,185 GitHub stars** (as of 2026-03-28)
- **818 forks** (as of 2026-03-28)
- **3,313 open issues** (as of 2026-03-28)
- **Used in production** by organizations like Fastly and Gusto
- **Production scale**: Many deployments support tens of thousands of hosts; large organizations manage as many as 400,000+ hosts
- **1,649 commits** in repository history

---

## Key Features

### Device Management (MDM)

- **Apple MDM**: Full enrollment, provisioning, and management of macOS, iOS, and iPadOS devices via DEP (Device Enrollment Program)
- **Windows MDM**: Enrollment via Intune integration, Windows Update policy management, disk encryption (BitLocker) control
- **Android MDM**: Support for fully managed and work-profile devices; app installation, removal, and managed Google Play store integration
- **Chromebook Management**: Device enrollment and policy enforcement on Chromebooks

### Security and Compliance

- **CIS Benchmarks**: Out-of-the-box support for all macOS and Windows CIS benchmark policies
- **Vulnerability Management**: Kernel vulnerability scanning on RHEL-based hosts; CVE alias tracking
- **Policy Enforcement**: Query-based policies with automated response (scripts, configuration changes)
- **Detection Engineering**: Live query interface for ad-hoc threat hunting and investigations

### Device Status and Health

- **Host Inventory**: Real-time visibility into host details (OS, software, hardware, network configuration)
- **Software Tracking**: Detection and management of installed applications; license usage reporting
- **Mobile Device Management Status**: Pending/active profiles for Apple MDM, Windows MDM, and Android
- **Conditional Access**: Compliance-based access control policies for Azure/Microsoft Entra ID

### Deployment and Automation

- **GitOps Support**: Define fleets, policies, queries, and scripts via YAML
- **Webhooks**: Event-driven integrations (vulnerability detected, policy violation, script completion)
- **fleetctl CLI**: Command-line tool for programmatic management
- **REST API**: Full API for custom integrations
- **Orbit Agent**: Lightweight osquery installer and autoupdater that connects to Fleet (can be used independently)

### Platform Support

Supported on: Linux (all distros), macOS, Windows, Chromebooks, AWS, GCP, Azure, data centers, containers (Kubernetes, etc.), Linux-based IoT devices.

---

## Technical Architecture

### Core Components

**1. Fleet Server** (`server/`)
- **Service Interface** (`server/service/service.go`): Core implementation of the Fleet API and HTTP endpoints
  - Implements `fleet.Service` interface
  - Handles osquery communication, host queries, policy enforcement, MDM commands
  - Manages activity logging, user authentication (SAML, OAuth), team-based access control

- **Configuration Manager** (`server/config/`): Loads configuration from YAML files or environment variables
  - Supports development, staging, and production profiles
  - Configures database, object storage, logging, OTEL, webhooks

**2. Datastore Layer** (`server/datastore/`)
- **MySQL Implementation** (`server/datastore/mysql/`): Primary persistent store
  - Uses `sqlx` for database interactions
  - OTEL-instrumented SQL wrapper (`otelsql`) for observability
  - Implements statement caching for performance
  - Schema migrations via Goose (database migration tool)

- **Redis Layer** (`server/datastore/redis/`): Optional read replica support and caching
  - Rate limiting store for enforcing API limits
  - Host aggregation queries for performance optimization

**3. MDM Services**
- **Apple MDM** (`server/mdm/apple/`): Handles APNS communication, DEP enrollment, profile management
- **Microsoft MDM** (`server/mdm/microsoft/`): Windows Intune integration, BitLocker, Azure CA proxy
- **Android MDM** (`server/mdm/android/`): Google Play Managed Services enrollment, app distribution
- **nanoMDM Storage** (`server/mdm/nanomdm/storage/`): Abstract storage for MDM profiles and commands
- **nanoDEP Storage** (`server/mdm/nanodep/storage/`): DEP token and profile management

**4. Command Interface** (`cmd/fleet/main.go`)
- **Cobra CLI** (`spf13/cobra`): Root command with subcommands:
  - `serve`: Start Fleet server
  - `prepare`: Database migration and initialization
  - `vuln-processing`: Vulnerability cron processing
  - `config-dump`: Output current configuration
  - `version`: Display build version

**5. Frontend** (`frontend/`)
- **React 18.3.1** for UI components
- **React Router** for navigation
- **Ace Editor** for query/script editing
- **React Query** for async state management
- **Node 24.10.0+** and Yarn for build tools

### Data Flow

1. **osquery Agent (Orbit)** → **Fleet Server** (`/api/osquery/enroll`, `/api/osquery/config`)
   - Agent enrolls with enroll secret
   - Receives distributed queries and policies

2. **Fleet Server** → **Datastore** (MySQL + optional Redis replica)
   - Persists host details, query results, policy violations
   - Queries for compliance enforcement, vulnerability scanning

3. **Fleet Server** → **MDM Services** (Apple/Windows/Android)
   - Sends management commands (profile installation, app distribution, disk encryption)
   - Tracks device enrollment status

4. **Fleet Web UI** → **Fleet Server REST API**
   - Manages policies, queries, scripts, fleets (teams), users
   - Returns real-time host inventory and compliance status

5. **Webhooks** ← **Fleet Server**
   - Triggers on policy violations, vulnerability detections, script completions
   - Integrates with Splunk, Slack, GitHub, custom HTTPS endpoints

### Extension Points

1. **Service Overrides** (`server/fleet/service.go`): Enterprise features are injected via `EnterpriseOverrides` struct
   - `HostFeatures()` – enterprise-only host capabilities
   - `TeamByIDOrName()` – team-scoped operations
   - `MDMAppleEnableFileVaultAndEscrow()` – premium feature for encryption key escrow
   - `DeleteMDMAppleSetupAssistant()` – custom setup experience

2. **Datastore Abstraction** (`server/fleet/`): The `Datastore` interface allows pluggable backends (MySQL is the current production implementation)

3. **Custom Integrations**: Via REST API and webhooks; external systems can:
   - Query hosts and policies programmatically
   - Receive real-time events (policy violations, vulnerabilities)
   - Manage fleets and reports via GitOps YAML

---

## Installation & Usage

### Deployment

**Hosted Option**: Fleet offers cloud-hosted deployments at <https://fleetdm.com/pricing> (premium tier)

**Self-Hosted Deployment**:
```bash
# 1. Database setup (MySQL 5.7+)
# 2. Configuration file (fleet.yml or environment variables)
# 3. Run database migrations
fleet prepare

# 4. Start Fleet server
fleet serve \
  --mysql_address=localhost:3306 \
  --mysql_database=fleet \
  --mysql_username=fleet \
  --mysql_password=YOUR_PASSWORD
```

### Using Orbit Agent

```bash
# Download and run Orbit with Fleet enrollment
go run github.com/fleetdm/fleet/v4/orbit/cmd/orbit \
    --fleet-url https://your-fleet-server.com \
    --enroll-secret YOUR_ENROLL_SECRET
```

### Key Configuration Options

From `cmd/fleet/main.go` and `server/config/`:

- `mysql.address`, `mysql.database` – MySQL connection details
- `s3.carves_bucket`, `s3.software_installers_bucket` – Object storage for file carves, software installers
- `prometheus.basic_auth` – OTEL metrics export
- `logging.json`, `logging.debug` – Structured logging configuration
- `server.certificate`, `server.key` – TLS certificates for HTTPS

---

## Relevance to Claude Code Development

Fleet demonstrates a sophisticated multi-component agent infrastructure with critical design patterns applicable to Claude Code plugin development:

1. **Plugin Architecture via Service Overrides**: Fleet's `EnterpriseOverrides` pattern shows how to extend core functionality without forking. This pattern is directly applicable to Claude Code's skill extension mechanism.

2. **Modular Component Design**: The separation of MDM services (Apple, Windows, Android) into independent modules shows how to manage heterogeneous subsystems at scale without tight coupling.

3. **Datastore Abstraction**: The pluggable datastore design (MySQL primary, Redis caching) demonstrates how to support multiple backend options while maintaining a consistent service interface — valuable for supporting multiple storage backends in Claude Code plugins.

4. **Event-Driven Integration**: Fleet's webhook system provides a reference implementation for event streaming (policy violations, vulnerabilities) to external systems — applicable to Claude Code's agent-to-agent communication patterns.

5. **Configuration Management**: The centralized configuration manager that reads from both YAML files and environment variables is a solid pattern for multi-environment deployment (dev, staging, production).

6. **Observability**: Fleet's use of OTEL (OpenTelemetry) for logs, traces, and metrics shows production-grade observability integration patterns.

---

## Limitations and Caveats

From reviewed sources:

1. **License Complexity**: Fleet uses a dual-license model. Premium features (team management, advanced MDM, compliance integrations) require commercial licensing; the free tier includes core MDM and vulnerability detection.

2. **Database Dependency**: Fleet requires MySQL 5.7+ for all deployments. No support for alternative relational databases (PostgreSQL support not documented). Redis is optional but recommended for scale.

3. **osquery Dependency**: The entire data gathering model depends on osquery. For unsupported platforms (e.g., devices without osquery agents), visibility is limited to what the MDM protocols provide (Apple, Windows, Android only).

4. **Scale Limitations**: While documented to support 400,000+ hosts in large deployments, production deployments at this scale require careful infrastructure planning (database tuning, read replicas, caching).

5. **MDM Platform Coverage**: While Apple, Windows, and Android MDM are comprehensive, Linux and Chromebook management is read-only (inventory only); no management agent controls comparable to the Apple/Windows MDM capabilities.

---

## References

- **Repository**: <https://github.com/fleetdm/fleet> (accessed 2026-03-28)
- **Official Website**: <https://fleetdm.com> (accessed 2026-03-28)
- **Documentation**: <https://fleetdm.com/docs> (accessed 2026-03-28)
- **Main README**: <https://github.com/fleetdm/fleet/blob/main/README.md> (accessed 2026-03-28)
- **Orbit README**: <https://github.com/fleetdm/fleet/blob/main/orbit/README.md> (accessed 2026-03-28)
- **Changelog 4.82.1**: <https://github.com/fleetdm/fleet/blob/main/CHANGELOG.md> (accessed 2026-03-28)
- **go.mod**: Fleet v4 module declaration (accessed 2026-03-28)
- **cmd/fleet/main.go**: CLI entrypoint and command structure (accessed 2026-03-28)
- **server/service/service.go**: Core service interface and implementation (accessed 2026-03-28)
- **server/datastore/mysql/mysql.go**: MySQL datastore implementation (accessed 2026-03-28)
- **server/fleet/service.go**: Enterprise overrides pattern (accessed 2026-03-28)

---

## Freshness Tracking

**Entry Created**: 2026-03-28
**Last Updated**: 2026-03-28
**Next Review**: 2026-06-28

### Confidence Summary

| Section | Confidence | Notes |
|---------|-----------|-------|
| Overview | high | Full README read, official website documentation |
| Problem Addressed | high | Extracted from README and official docs; organization use cases documented |
| Key Statistics | high | GitHub API data (stars, forks, issues); changelog for version info; commit history from local clone |
| Key Features | high | Extracted from README "What's it for?" section and changelog 4.82.0 and 4.82.1 |
| Technical Architecture | high | Code read from main.go, service.go, datastore/mysql/mysql.go; interface definitions from server/fleet/service.go |
| Installation & Usage | high | Extracted from orbit/README.md build instructions and cmd/fleet/main.go entrypoint |
| Relevance to Claude Code | medium | Inferred from architectural patterns observed in code; not explicitly documented by Fleet |
| Limitations | medium | Free tier constraints from README; scale caveats inferred from large organization mention; osquery dependency explicit in README |

**Data Sources**:
- Primary code analysis: `/home/user/claude_skills/.worktrees/fleet/` shallow clone
- Official documentation: <https://github.com/fleetdm/fleet/README.md>, CHANGELOG.md, orbit/README.md
- GitHub API: Repository metadata (stars, forks, license, language, topics)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Fly.io](../fly-io.md) | agent-infrastructure | shared concern: infrastructure patterns for orchestrating scaled deployments across multiple regions and cloud environments |
| [PocketBase](../api-frameworks/pocketbase.md) | api-frameworks | comparable modular backend design: service overrides via hooks and plugins; REST API with extensible architecture |
| [Dolt](../data-infrastructure/dolt.md) | data-infrastructure | shared pattern: version-controlled SQL database for audit trails and state management in distributed systems |
| [Gas Town](../research-agent-patterns/gastown.md) | research-agent-patterns | applies fleet/agent management principles: distributed work state, health monitoring (Witness zombie detection), persistent context across agent lifecycle |
| [PicoClaw](../picoclaw.md) | agent-infrastructure | lightweight edge deployment model: single-binary infrastructure deployable across heterogeneous hardware (RISC-V, ARM, x86) |
| [OpenFang](../agent-frameworks/openfang.md) | agent-frameworks | modular service architecture with autonomous Hands and extensible channel adapters; comparable to Fleet's pluggable MDM service components |
| [ZeroClaw](../zeroclaw.md) | agent-infrastructure | similar infrastructure constraint optimization: sub-5MB resource footprint for edge deployment scenarios |
| [Kernel.sh](../kernel-sh.md) | agent-infrastructure | complementary execution environment isolation: VM-per-browser model parallels Fleet's device isolation and MDM agent sandboxing |
| [Plano](../plano.md) | agent-infrastructure | multi-agent orchestration proxy with data plane abstraction; similar to Fleet's service router pattern for managing heterogeneous client types |
