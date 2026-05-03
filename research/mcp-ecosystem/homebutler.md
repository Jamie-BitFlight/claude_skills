# HomeButler

**Research Date**: 2026-05-03
**Source URL**: <https://github.com/Higangssh/homebutler>
**GitHub Repository**: <https://github.com/Higangssh/homebutler>
**Version at Research**: v0.18.1
**License**: MIT

---

## Overview

HomeButler is a single Go binary MCP server that enables management and monitoring of homelabs and self-hosted infrastructure through AI interfaces (Claude, Cursor, Claude Code). It provides operational visibility and automation for homelab environments without requiring a daemon, database, or always-on web service—just deploy the binary and connect it to your AI tools via the Model Context Protocol.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Manual container and service management in homelabs | Provides CLI and MCP interface to query running services, container status, and port mappings without SSH |
| Lack of unified visibility into homelab infrastructure | Single binary aggregates information about running processes, containers, backups, and system state |
| Complex app deployment and configuration | Simplifies installation of self-hosted apps without hand-writing Docker Compose files |
| AI tools cannot interact with homelab infrastructure | MCP server integration exposes homelab operations to Claude, Cursor, and Claude Code for chatops workflows |
| Difficulty diagnosing failures and outages | Provides service restart logs, status tracking, and backup validation from natural language queries |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 135 | 2026-05-03 |
| Forks | 11 | 2026-05-03 |
| Open Issues | 4 | 2026-05-03 |
| Latest Release | v0.18.1 | 2026-05-03 |
| Primary Language | Go | 2026-05-03 |
| Created | 2026-02-23 | 2026-05-03 |
| Last Updated | 2026-05-03 | 2026-05-03 |

---

## Key Features

### MCP Server Integration

- Full Model Context Protocol server implementation, enabling seamless integration with Claude Desktop, Cursor, and Claude Code
- Installable via npm, Homebrew, or direct script installation
- Zero configuration required—works out of the box with AI tools

### Infrastructure Introspection

- Query running processes, systemd services, and container status (Docker, Podman support)
- Port mapping and service ownership detection
- System metrics and resource utilization queries
- Service restart history and diagnostic logs

### Application Deployment

- Simplified app installation workflows without manual Docker Compose authoring
- Pre-built templates for common self-hosted applications
- Configuration management through the MCP interface

### Operational Visibility

- Backup status and restorability validation
- Service health monitoring and alerting
- SSH command execution and remote management
- Wake-on-LAN support for hardware management

### Multi-Platform Support

- Linux (primary), Raspberry Pi, Docker, and MacOS compatibility
- Single binary distribution with no external dependencies
- Cross-platform build support via goreleaser

---

## Technical Architecture

HomeButler is a Go application structured as:

- **MCP Server Core**: Implements the Model Context Protocol for AI integration, exposing homelab operations as tools
- **CLI Interface**: Local command-line interface for direct operations
- **Infrastructure Layer**: Communicates with system APIs (systemd, Docker socket, SSH) to query and manage infrastructure
- **Single Binary Distribution**: Compiled Go program with no runtime dependencies, enabling lightweight deployment across platforms

Architecture flows from the MCP protocol handler through command routing to infrastructure adapters, allowing both AI agents and direct CLI usage to interact with the same underlying operational logic.

---

## Installation & Usage

### Installation via Homebrew

```bash
brew install Higangssh/homebutler/homebutler
homebutler upgrade  # For existing installations
```

### Installation via npm

```bash
npm install -g homebutler
```

### Installation via script

```bash
curl -fsSL https://raw.githubusercontent.com/Higangssh/homebutler/main/install.sh | sh
```

### MCP Configuration (Claude Desktop / Cursor / Claude Code)

```json
{
  "mcpServers": {
    "homebutler": {
      "command": "npx",
      "args": ["-y", "homebutler@latest"]
    }
  }
}
```

### CLI Usage Examples

```bash
# Query running containers
homebutler containers

# Check service status
homebutler services

# Query listening ports
homebutler ports

# View service restart logs
homebutler logs <service-name>

# Install a self-hosted app
homebutler install <app-template>
```

---

## Relevance to Claude Code Development

### Applications

- Enables Claude Code agents to interact directly with homelab infrastructure, containers, and services via natural language queries
- Provides operational context and visibility for automated deployment and configuration workflows
- Supports chatops patterns where AI tools manage self-hosted applications and infrastructure

### Patterns Worth Adopting

- MCP server design for exposing operational systems to AI tools—demonstrates how to bridge infrastructure and AI capabilities
- Single-binary distribution pattern for zero-dependency deployment
- CLI-first design that extends to protocol-based interfaces (a model for skill/agent tool design)

### Integration Opportunities

- Direct integration as an MCP server in Claude Code environments for homelab management workflows
- Collaboration with development-harness for infrastructure-as-code and deployment automation
- Use in agent workflows that require infrastructure visibility (deployment validation, resource monitoring)

---

## References

- [HomeButler GitHub Repository](https://github.com/Higangssh/homebutler) (accessed 2026-05-03)
- [HomeButler Official Website](https://homebutler.dev) (referenced in README, accessed 2026-05-03)
- [Model Context Protocol Documentation](https://modelcontextprotocol.io/) (accessed 2026-05-03)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Model Context Protocol](./model-context-protocol.md) | mcp-ecosystem | Core protocol implementation |

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | 2026-05-03 |
| Version at Verification | v0.18.1 |
| Next Review Recommended | 2026-08-03 |
| Confidence Map | `Overview: high (README + release notes)`, `Features: high (README + API reference)`, `Architecture: medium (code-read from go.mod and cmd/)`, `Statistics: high (GitHub API)` |
