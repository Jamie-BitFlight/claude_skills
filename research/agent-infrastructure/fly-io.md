---
title: "Fly.io"
research_date: "2026-02-23"
source_url: "https://fly.io/"
github_url: "<https://github.com/superfly> (organization)"
version_at_research: "flyctl v0.4.14 (latest at research date)"
license: "Apache-2.0 (open-source components: flyctl, fly-go) / Proprietary (platform)"
last_verified: "2026-02-23"
version_at_verification: "flyctl v0.4.14"
next_review: "2026-05-23"
---

## Overview

Fly.io is a developer-focused cloud platform that runs application code inside Firecracker microVMs, providing hardware-level isolation, sub-second startup times, and global anycast networking across 18 regions. It positions itself as compute that "gets out of the way" — deploy any container or binary with `fly launch`, pay per-second for actual usage, and get globally-distributed infrastructure without managing Kubernetes or Terraform. In 2025-2026 Fly.io extended the platform with **Sprites** (`sprites.dev`), persistent stateful sandboxes purpose-built for running AI coding agents like Claude Code at scale.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Cold-start latency kills serverless apps | Firecracker microVMs boot in < 1 second, fast enough to handle HTTP requests |
| "Noisy neighbor" on shared runtimes | KVM hardware isolation; CPU cores dedicated to one microVM at a time |
| Complex global distribution | BGP anycast + 18 regions; traffic routed to closest available VM automatically |
| Stateless-only serverless platforms | Fly Volumes (persistent NVMe), Fly Postgres, and Sprite checkpointing for stateful workloads |
| AI agents need isolated execution environments | Sprites provide per-agent VMs with private filesystems, checkpoints, and rollback |
| Unsafe execution of AI-generated code | Hardware-isolated sandboxes (Sprites) let untrusted code run in complete safety |
| Complex multi-service private networking | Automatic WireGuard mesh (6PN); apps resolve peers via `.internal` DNS, zero config |
| Expensive always-on compute | Per-second billing, Machines stop when idle, minimum 6.25% CPU granularity |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| Global regions | 18 (Sydney to São Paulo) | 2026-02-23 |
| flyctl GitHub stars | ~1,600 | 2026-02-23 |
| flyctl latest version | v0.4.14 | 2026-02-23 |
| Sprites CPU billing | $0.07 / CPU-hour | 2026-02-23 |
| Sprites Memory billing | $0.04375 / GB-hour | 2026-02-23 |
| Sprites 4-hr coding session (example) | ~$0.44 total | 2026-02-23 |
| Sprites 30-hr/month (5 concurrent users) | ~$1.89 / month | 2026-02-23 |
| Support plans start at | $29 / month | 2026-02-23 |
| Machines API rate limit | 1 req/sec per action (burst capacity available) | 2026-02-23 |
| Stack languages | Rust (fly-proxy) + Go (flyctl, orchestration) | 2026-02-23 |

---

## Key Features

### Fly Machines (Core Compute)

- Firecracker-based microVMs; hardware-isolated via KVM
- Sub-second start/stop; suitable for handling individual HTTP requests
- Full lifecycle control via REST API (`https://api.machines.dev`) or `flyctl`
- Configure CPU (shared or dedicated), RAM, region, and environment variables per Machine
- Autoscale to tens of thousands of instances programmatically
- Per-second billing — machines stopped when idle cost nothing

### Sprites (Agent Sandboxes)

- Persistent, stateful Linux environments backed by Firecracker microVMs
- Designed for AI coding agents (Claude Code, reasoning LLMs) and untrusted code execution
- Checkpoint & restore: snapshot full VM state; roll back if anything breaks
- Fast startup: 1–12 seconds; auto-shutoff when idle
- HTTP endpoint per Sprite for webhooks, serving APIs, and public sharing
- CLI (`sprite`), REST API (`api.sprites.dev`), TypeScript SDK (`@fly/sprites`), Go SDK
- Non-Docker storage stack with NVMe for durability and performance

### Global Networking (BGP Anycast + WireGuard)

- BGP anycast: IPs broadcast from all datacenters; connections routed to closest VM
- `fly-proxy`: Rust-based proxy on every server handles TLS termination, backhaul, routing
- WireGuard backhaul between datacenters; connections traverse minimal additional latency
- **6PN (IPv6 Private Network)**: automatic encrypted mesh across all apps in an org
- `.internal` DNS: apps resolve each other by name without public exposure
- Flycast: internal load balancing and traffic steering for multi-region topologies
- Connect external nodes (laptops, other clouds) to the private network via `fly wireguard create`

### Persistent Storage

- **Fly Volumes**: regional NVMe-backed persistent disks; attach to Machines for stateful apps
- **Fly Postgres (Managed)**: HA Postgres with automatic failover, daily backups, replication
- **Fly Postgres (Unmanaged)**: self-managed Postgres running as a Fly app on volumes
- Object storage available through Tigris (S3-compatible, globally distributed)
- Sprite storage: hot NVMe cache ($0.000683/GB-hour) + durable bucket storage ($0.000027/GB-hour)

### Model Context Protocol (MCP)

- Fly.io has first-class MCP documentation and tooling at `fly.io/docs/mcp/`
- `fly mcp launch`: one-command deployment of `npx`, `uv`, `go run`, or Docker stdio MCP servers
- Fly MCP server (`fly-mcp`): community Go server to manage Fly.io infrastructure via Claude
- Remote MCP servers on Fly.io connect to Claude via `mcp_servers` array in the Messages API
- MCP servers run as single-Machine apps (non-HA) to preserve stateful protocol sessions
- Transport options: stdio (local), SSE, and Streamable HTTP (for remote Fly-hosted servers)

### Developer Experience

- `fly launch`: auto-detects frameworks, generates `fly.toml`, builds image, deploys
- `fly deploy`: rebuild and redeploy with zero downtime rolling updates
- `fly ssh console`: SSH into any running Machine
- `fly logs`, `fly status`, `fly scale`: observability and scaling commands
- CI/CD integration supported; deploy tokens scoped per environment
- SOC2 Type 2 attested; Single Sign-On for enterprise

---

## Technical Architecture

```
User Traffic
     │
     ▼
BGP Anycast (18 regions)
     │
     ▼
fly-proxy (Rust, on every server)
  ├─ TLS termination
  ├─ App/Machine routing
  └─ WireGuard backhaul to nearest Machine
          │
          ▼
     Firecracker microVM
     ├─ KVM hardware isolation
     ├─ Dedicated CPU cores (best-effort)
     ├─ 32–256 GB RAM host servers
     ├─ Fly Volume (NVMe persistent storage)
     └─ 6PN (WireGuard IPv6 private mesh)
              │
              ▼
         Other apps / Postgres
         via .internal DNS
```

**Key components**:

- **fly-proxy**: Rust-based, runs on every physical server; handles all ingress/egress
- **Firecracker**: AWS-developed open-source VMM; provides microVM isolation via KVM
- **6PN**: Per-organization WireGuard mesh; auto-provisioned, zero configuration
- **flyctl / fly-go**: Go-based CLI and SDK; open source on GitHub (`superfly/flyctl`, `superfly/fly-go`)
- **Machines API**: REST API at `api.machines.dev`; OpenAPI 3.0 spec at `docs.machines.dev`
- **Sprites API**: REST API at `api.sprites.dev`; separate product built on same Fly infrastructure

---

## Installation & Usage

```bash
# Install flyctl (macOS)
brew install flyctl

# Install flyctl (Linux/Windows)
curl -L https://fly.io/install.sh | sh

# Install Sprites CLI
curl https://sprites.dev/install.sh | bash

# Authenticate
fly auth login
sprite login

# Deploy any app
fly launch       # auto-detect, configure, and deploy
fly deploy       # redeploy on changes

# Fly Machines API - create a machine
export FLY_API_TOKEN=$(fly tokens deploy)
export FLY_API_HOSTNAME="https://api.machines.dev"

curl -X POST "${FLY_API_HOSTNAME}/v1/apps/my-app/machines" \
  -H "Authorization: Bearer ${FLY_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "config": {
      "image": "registry.fly.io/my-app:latest",
      "guest": { "cpu_kind": "shared", "cpus": 1, "memory_mb": 256 }
    }
  }'

# Sprites - create and use a sandbox
sprite create my-agent-sandbox
sprite exec -s my-agent-sandbox -- python agent.py
sprite console -s my-agent-sandbox   # interactive shell

# Fly MCP - deploy a stdio MCP server
fly mcp launch --image my-mcp-server:latest

# Private networking - connect from local machine
fly wireguard create personal my-peer > peer.conf
# Import peer.conf into any WireGuard client
```

---

## Relevance to Claude Code Development

### Applications

- **Run Claude Code as an agent on Sprites**: Sprites are explicitly designed for AI coding agents like Claude Code; each gets an isolated VM with persistent filesystem, checkpointing, and rollback
- **Deploy MCP servers**: Host any MCP server on Fly.io with `fly mcp launch`; connect Claude to it via the Messages API `mcp_servers` field
- **Safe code execution sandbox**: Execute AI-generated or user-provided code in hardware-isolated Sprite VMs — prevents prompt injection from compromising host systems
- **Deploy skills/agent backends globally**: Fly.io's 18-region deployment means Claude-powered APIs respond with sub-100ms latency to users worldwide
- **Persistent agent state**: Use Fly Volumes or Sprite storage for agents that need to remember context across sessions, build SQLite databases, or maintain project state
- **Orchestrate multi-agent swarms**: Machines API allows programmatic creation/destruction of thousands of ephemeral VMs — each agent gets its own isolated compute

### Patterns Worth Adopting

- **Checkpoint/restore for reproducibility**: Sprite checkpoints enable saving a known-good state before risky agent operations and rolling back on failure
- **Per-agent VM isolation**: Instead of shared runtimes, give each agent instance its own microVM to eliminate noisy-neighbor interference and security cross-contamination
- **MCP-over-HTTP**: Deploy Claude Code skills as stateful MCP servers on Fly.io for remote team access; use SSE transport for persistent connections
- **Internal DNS for service discovery**: Use `.internal` addresses to wire together agent components (coordinator, executor, storage) without exposing them publicly
- **Per-second billing for burst workloads**: Agent workloads are often bursty; Fly's billing model ensures idle agents cost nothing while allowing rapid scale-up

### Integration Opportunities

- **fly-mcp**: Deploy the open-source `fly-mcp` Go server to allow Claude to manage Fly.io infrastructure via natural language (provision apps, check stats, scale services)
- **Claude Code + Sprites REST API**: Use `@fly/sprites` TypeScript SDK or `api.sprites.dev` REST API to programmatically provision sandboxes for each Claude Code task
- **FLAME pattern on Fly.io**: Fly.io's documentation references Elixir FLAME for spawning function-level VMs; the same pattern applies to spawning Claude sub-agents in isolated Machines
- **Fly Postgres as agent memory**: Use Fly Postgres with pgvector for long-term semantic memory stores accessible to agents via the private 6PN network
- **GitHub Actions → Fly Deploy**: CI/CD workflow where Claude Code generates code, tests pass, and `flyctl` deploys automatically to Fly.io

---

## References

- [Fly.io homepage](https://fly.io/) (accessed 2026-02-23)
- [Fly.io Architecture docs](https://fly.io/docs/reference/architecture/) (accessed 2026-02-23)
- [Fly Machines documentation](https://fly.io/docs/machines/) (accessed 2026-02-23)
- [Machines REST API](https://fly.io/docs/machines/api/) (accessed 2026-02-23)
- [Machines API OpenAPI spec](https://docs.machines.dev/) (accessed 2026-02-23)
- [Model Context Protocol on Fly.io](https://fly.io/docs/mcp/) (accessed 2026-02-23)
- [Sprites — stateful agent sandboxes](https://sprites.dev/) (accessed 2026-02-23)
- [Fly.io Private Networking (6PN)](https://fly.io/docs/networking/private-networking/) (accessed 2026-02-23)
- [Fly Postgres (Managed)](https://fly.io/docs/mpg/) (accessed 2026-02-23)
- [flyctl GitHub repository](https://github.com/superfly/flyctl) (accessed 2026-02-23)
- [fly-go SDK](https://github.com/superfly/fly-go) (accessed 2026-02-23)
- [fly-mcp: MCP server for Fly.io infrastructure](https://github.com/brannn/fly-mcp) (accessed 2026-02-23)
- [Fly.io introduces Sprites for agentic AI (devclass)](https://www.devclass.com/ai-ml/2026/01/13/flyio-introduces-sprites-lightweight-persistent-vms-to-isolate-agentic-ai/4079557) (accessed 2026-02-23)
- [Fly.io pricing](https://fly.io/pricing/) (accessed 2026-02-23)
- [WireGuard private network access](https://fly.io/docs/blueprints/connect-private-network-wireguard/) (accessed 2026-02-23)

---
