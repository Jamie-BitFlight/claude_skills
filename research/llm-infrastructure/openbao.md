---
title: OpenBao — Open-Source Secrets and Encryption Management
description: OpenBao is an identity-based secrets and encryption management system for managing API keys, passwords, and certificates with centralized access control and audit trails.
keywords:
  - secrets management
  - encryption
  - access control
  - audit trails
  - authentication
  - HashiCorp Vault fork
  - open source
---

# OpenBao

## Overview

**OpenBao is an identity-based secrets and encryption management system for managing, storing, and distributing sensitive data including secrets, certificates, and keys.** OpenBao "exists to provide a software solution to manage, store, and distribute sensitive data including secrets, certificates, and keys. The OpenBao community intends to provide this software under an OSI-approved open-source license, led by a community run under open governance principles."

The problem OpenBao addresses: "A modern system requires access to a multitude of secrets: database credentials, API keys for external services, credentials for service-oriented architecture communication, etc. Understanding who is accessing what secrets is already very difficult and platform-specific. Adding on key rolling, secure storage, and detailed audit logs is almost impossible without a custom solution."

OpenBao solves this by "centralizing credentials so that they are defined in one location, which reduces unwanted exposure to credentials" while ensuring "users, apps, and systems are authenticated and explicitly authorized to access resources, while also providing an audit trail that captures and preserves a history of clients' actions."

## Problem Addressed

OpenBao addresses the credential sprawl and access control problem that enterprises face. Passwords, API keys, and credentials are commonly stored in plain text, app source code, and config files scattered across an organization, making it difficult to know who has access to what. OpenBao centralizes secret management with:

- Unified credential repository instead of credentials spread across the organization
- Authentication and authorization enforcement before any secret access
- Detailed audit trails of all secret access and operations
- Automatic key rolling and revocation capabilities for key management

## Key Statistics

- **Current Version**: 2.5.2 (released March 25, 2026)
- **License**: Mozilla Public License, version 2.0 (MPL-2.0)
- **Implementation Language**: Go 1.25.6
- **Public Libraries**: Two importable libraries are published:
  - `github.com/openbao/openbao/api/v2` — HTTP client for OpenBao API
  - `github.com/openbao/openbao/sdk/v2` — SDK for plugin and extension development
- **Latest Security Update**: v2.5.2 includes fixes for CVE-2026-33758 (XSS prevention in JWT auth callback) and CVE-2026-33757 (confirmation prompt in JWT direct callback mode)
- **Organization**: Community-led project under open governance, coordinated via OpenSSF with public Zulip chat channels and GitHub Discussions

## Key Features

### 1. Secure Secret Storage

**Feature**: "Arbitrary key/value secrets can be stored in OpenBao. OpenBao encrypts these secrets prior to writing them to persistent storage, so gaining access to the raw storage isn't enough to access your secrets. OpenBao can write to disk, PostgreSQL, and more."

Mechanism: All secrets written to persistent storage are encrypted using OpenBao's security barrier before reaching the physical storage backend. The barrier encryption is independent of the storage medium — gaining access to raw disk or database does not expose unencrypted secrets.

### 2. Dynamic Secrets

**Feature**: "OpenBao can generate secrets on-demand for some systems, such as AWS or SQL databases. For example, when an application needs to access an S3 bucket, it asks OpenBao for credentials, and OpenBao will generate an AWS keypair with valid permissions on demand. After creating these dynamic secrets, OpenBao will also automatically revoke them after the lease is up."

Mechanism: Instead of storing long-lived credentials, applications request temporary credentials from OpenBao, which generates them dynamically using configured backend integrations. The generated credentials automatically expire and are revoked after their lease period ends.

### 3. Data Encryption

**Feature**: "OpenBao can encrypt and decrypt data without storing it. This allows security teams to define encryption parameters and developers to store encrypted data in a location such as a SQL database without having to design their own encryption methods."

Mechanism: The Transit secret engine provides encryption-as-a-service capability — applications send plaintext data to OpenBao for encryption, receive the ciphertext back, and can store it anywhere. OpenBao never stores the plaintext or ciphertext, only performs the cryptographic operations.

### 4. Leasing and Renewal

**Feature**: "All secrets in OpenBao have a _lease_ associated with them. At the end of the lease, OpenBao will automatically revoke that secret. Clients are able to renew leases via built-in renew APIs."

Mechanism: Every secret (both static and dynamic) has a time-to-live (TTL) and lease ID. OpenBao automatically tracks lease expiration and revokes secrets when their lease expires. Clients can request lease renewal before expiration to extend the secret's lifetime.

### 5. Secret Revocation

**Feature**: "OpenBao has built-in support for secret revocation. OpenBao can revoke not only single secrets, but a tree of secrets, for example, all secrets read by a specific user, or all secrets of a particular type. Revocation assists in key rolling as well as locking down systems in the case of an intrusion."

Mechanism: Revocation can be performed granularly (individual secrets), hierarchically (all secrets issued to a specific user), or by type (all secrets of a particular engine type). This enables rapid incident response and planned key rotation across an entire organization.

## Technical Architecture

### Core Components

OpenBao's architecture centers on the **Core struct**, which is the "central manager of Vault activity and primary point of interface for API handlers, responsible for managing the logical and physical backends, router, security barrier, and audit trails."

The architecture consists of five primary layers:

1. **API Layer** — HTTP/gRPC handlers that process client requests and route them through authentication, authorization, and secret access pipelines

2. **Routing and Mount Layer** — The Router manages mount tables (auth methods, secret engines, audit backends) and directs requests to the appropriate backend based on the request path. Mounts are stored in protected configuration loaded after unseal.

3. **Security Barrier** — Encryption layer that encrypts all data written to persistent storage. The barrier wraps the physical backend and ensures that even direct access to storage yields only encrypted data.

4. **Physical Backend** — Un-trusted storage layer that can be disk, PostgreSQL, Raft, or other backends configured in the storage stanza. The physical backend has no knowledge of encryption — all data reaches it pre-encrypted from the barrier.

5. **Audit Broker** — Receives all operations and fans them out to configured audit backends (file, syslog, socket) for audit logging and compliance tracking.

### Builtin Components

**Authentication Methods** (9 built-in):
- AppRole — for application authentication without human interaction
- Certificate (Cert) — mutual TLS certificate authentication
- JWT — JSON Web Token validation from OIDC providers
- Kerberos — Windows Kerberos authentication
- Kubernetes — K8s service account token validation
- LDAP — directory service authentication
- RADIUS — RADIUS protocol authentication
- Token — manual token creation and management
- UserPass — username/password authentication

**Secret Engines** (9 built-in):
- KV (Key-Value) — static secret storage with versioning support
- PKI — dynamic X.509 certificate generation and revocation
- Database — dynamic database credential generation for multiple database types
- Kubernetes — dynamic Kubernetes service account tokens
- SSH — dynamic SSH key generation and OTP validation
- Transit — encryption-as-a-service (encrypt/decrypt/sign/verify without storage)
- TOTP — time-based one-time password generation
- OpenLDAP — dynamic OpenLDAP user and password management
- RabbitMQ — dynamic RabbitMQ user credential generation

### Core Workflow

"The core OpenBao workflow consists of four stages: Authenticate, Validation, Authorize, Access":

1. **Authenticate** — The client supplies authentication information (credentials, certificates, tokens) to an auth method. The auth method validates the information and, on success, generates a token associated with a policy.

2. **Validation** — OpenBao validates the client against third-party trusted sources (GitHub, LDAP, AppRole, Kubernetes service account, etc.) as configured by the auth method.

3. **Authorize** — The generated token is matched against OpenBao's security policy. Policies are path-based rules that constrain what actions (read, write, delete, list) are permitted on which API paths for each client.

4. **Access** — OpenBao grants the client access to secrets, keys, and encryption capabilities by issuing the token. The client uses this token for all future operations, and OpenBao enforces the associated policy on each request.

### Extensibility

OpenBao supports plugin-based extension of auth methods, secret engines, and audit backends. Two libraries are published for plugin development:

- **`github.com/openbao/openbao/sdk/v2`** — Provides `logical.Factory` interface for implementing custom backends, `framework.Backend` for common backend patterns, and helper utilities for plugin development.

- **`github.com/openbao/openbao/api/v2`** — HTTP client library for integrating OpenBao into applications; supports automatic token renewal, secret lease tracking, and operation retries.

## Installation & Usage

### Building from Source

OpenBao requires Go 1.25.6 or later. To build a development version:

```bash
make bootstrap    # Download build tools
make dev          # Compile development binary
bin/bao          # Run OpenBao
```

To compile with the web UI:

```bash
make static-dist dev-ui
bin/bao
```

### Running Tests

OpenBao has comprehensive acceptance tests covering secret and auth methods. To run unit tests:

```bash
make test
```

To run acceptance tests for a specific backend (requires cloud credentials and real resources):

```bash
make testacc TEST=./builtin/logical/pki
```

### Docker-based Testing

OpenBao provides a Docker-based test cluster API for integration testing:

```go
import "github.com/openbao/openbao/sdk/v2/helper/testcluster/docker"

opts := &docker.DockerClusterOptions{
  ImageRepo: "openbao/openbao",
  ImageTag:  "latest",
}
cluster := docker.NewTestDockerCluster(t, opts)
defer cluster.Cleanup()

client := cluster.Nodes()[0].APIClient()
secret, err := client.Logical().Read("sys/storage/raft/configuration")
```

### HTTP API Example

```bash
# Initialize OpenBao
$ curl -X POST http://localhost:8200/v1/sys/init \
  -d '{"secret_shares":5, "secret_threshold":3}'

# Authenticate with token
$ curl -X POST http://localhost:8200/v1/auth/userpass/login/username \
  -d '{"password":"mypassword"}'

# Read a secret
$ curl --header "X-Vault-Token: s.xxxxxxxx" \
  http://localhost:8200/v1/secret/data/my-secret
```

## Relevance to Claude Code Development

OpenBao is relevant to Claude Code development in these scenarios:

1. **AI Agent Secret Management** — Claude Code agents that need to interact with external APIs (AWS, GitHub, Kubernetes, databases) can request temporary credentials from an OpenBao instance, eliminating the need to embed long-lived API keys in agent configurations.

2. **Development Environment Secrets** — When implementing multi-agent systems or distributed agents, OpenBao provides a centralized secret store for sharing database credentials, SSH keys, and API tokens across agent instances without storing them in git or configuration management tools.

3. **Audit and Compliance** — OpenBao's detailed audit trails enable tracking which agents accessed which secrets and when, supporting compliance requirements and security investigations in production environments.

4. **Plugin Development** — OpenBao's plugin SDK (sdk/v2) enables building custom auth methods or secret engines tailored to Claude Code agent workflows — for example, a custom auth method that validates agent identity using signed JWTs from the agent orchestration system.

5. **Encryption-as-a-Service** — The Transit engine can be integrated into Claude Code backends to provide transparent encryption for sensitive data without requiring custom key management — agents call the Transit endpoint to encrypt/decrypt data stored in databases or caches.

## Limitations and Caveats

**Unseal Requirement** — OpenBao must be explicitly unsealed before it can serve requests. This is intentional (provides resilience against memory dumps) but requires administrative intervention after restarts or machine reboots. In production, Auto Unseal (using cloud KMS) eliminates this operational burden, but adds a cloud provider dependency.

**Seal Migration Complexity** — Migrating between seal types (e.g., Shamir to AWS KMS) or changing KMS providers requires careful orchestration and can fail if the migration state is not properly tracked. v2.5.1 fixed a regression in auto-unseal upgrade/downgrade, indicating this remains a sensitive operational area.

**Namespace Hierarchy Constraints** — Some group policy application modes and OIDC operations exhibit bugs in non-root namespaces (see v2.5.2 changelog fixes for OIDC key rotation and namespace prefix doubling). Nested namespaces require testing of custom auth/secret workflows.

**Performance at Scale** — High-volume lease expiration and concurrent secret generation can trigger deadlocks in JobManager and cause mount deletion timeouts (fixed in v2.5.2). This requires tuning lease TTLs and load testing in high-concurrency environments.

**Dynamic Secret Provider Dependencies** — Dynamic secrets require the target system (AWS, databases, Kubernetes, LDAP) to be accessible and properly configured. If the target system is unreachable, credential generation fails, affecting application availability.

**Audit Backend Performance** — High-volume audit logging to slower backends (e.g., syslog, HTTP endpoints) can introduce latency in the critical path. Audit I/O errors can cause request failures if audit is configured as a required sink.

## References

- [OpenBao Official Website](https://www.openbao.org) — Project homepage with documentation and guides (accessed 2026-03-28)
- [OpenBao GitHub Repository](https://github.com/openbao/openbao) — Source code, issue tracking, and releases (accessed 2026-03-28)
- [GitHub Repository — README.md](https://github.com/openbao/openbao/blob/main/README.md) — Project overview and development guide (accessed 2026-03-28)
- [GitHub Repository — CHANGELOG.md](https://github.com/openbao/openbao/blob/main/CHANGELOG.md) — Version history and feature changes (accessed 2026-03-28)
- [OpenBao — "What is OpenBao?" Documentation](https://www.openbao.org/docs/) — Comprehensive introduction to concepts and workflows (accessed 2026-03-28)
- [OpenBao Mailing List](https://lists.openssf.org/g/openbao) — Community discussion forum (accessed 2026-03-28)
- [OpenBao GitHub Discussions](https://github.com/openbao/openbao/discussions) — Q&A and feature discussions (accessed 2026-03-28)
- [OpenBao Zulip Chat Server](https://linuxfoundation.zulipchat.com/) — Real-time community support and working group coordination (accessed 2026-03-28)

## Freshness Tracking

| Section | Confidence | Last Verified | Next Review |
|---------|-----------|---------------|------------|
| Identity & Metadata | high | 2026-03-28 | 2026-06-28 |
| Features | high | 2026-03-28 | 2026-06-28 |
| Architecture | high | 2026-03-28 | 2026-06-28 |
| Installation & Usage | high | 2026-03-28 | 2026-06-28 |
| Limitations | medium | 2026-03-28 | 2026-06-28 |
| Relevance to Claude Code | high | 2026-03-28 | 2026-06-28 |

**Confidence Rationale**:
- Identity, Features, Architecture: Full reads of README, CHANGELOG, documentation, and source code (core.go, builtin components). Version 2.5.2 is official release with detailed changelog.
- Installation & Usage: Verified against README and website documentation with working code examples.
- Limitations: Extracted from official CHANGELOG bug fix descriptions. Some limitations noted in code (deadlock in JobManager, mount deletion timeouts) are documented in official release notes.
- Relevance: Reasoned from architecture and capabilities; not extracted from a primary source. Medium confidence appropriate for inferred relevance.

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Bifrost](../llm-infrastructure/bifrost.md) | llm-infrastructure | integrates with HashiCorp Vault for governance and access control |
| [TensorZero](../llm-infrastructure/tensorzero.md) | llm-infrastructure | multi-provider LLM gateway with auth component architecture |
| [LocalAI](../llm-infrastructure/localai.md) | llm-infrastructure | self-hosted inference requiring credential management for API providers |
| [NemoClaw](../agent-infrastructure/nemoclaw.md) | agent-infrastructure | isolates provider credentials from agents via routed inference management |
| [Stakpak-Agent](../coding-agents/stakpak-agent.md) | coding-agents | includes secret substitution and mTLS credential handling for DevOps workflows |
| [Dify](../agent-frameworks/dify.md) | agent-frameworks | provides per-workspace access control and tool permission management |
| [Fleet](../agent-infrastructure/fleet.md) | agent-infrastructure | device management platform requiring authentication and authorization mechanisms |
