# NVIDIA NemoClaw

## Overview

NVIDIA NemoClaw is an open source reference stack that simplifies running OpenClaw always-on assistants more safely within containerized sandbox environments. Released in alpha on March 16, 2026, NemoClaw combines the NVIDIA OpenShell runtime with OpenClaw agents, providing policy-enforced isolation, managed inference routing, and declarative security controls.

**Source**: README.md (<https://github.com/NVIDIA/NemoClaw>, accessed 2026-03-28) — states "NVIDIA NemoClaw is an open source reference stack that simplifies running OpenClaw always-on assistants more safely."

## Problem Addressed

Autonomous AI agents like OpenClaw present significant operational risks when deployed without guardrails. Agents can make arbitrary network requests, access host filesystems, and call any inference endpoint, which creates security, cost, and compliance risks that grow as agents run unattended. Organizations need sandboxed execution with controlled access to external resources and infrastructure.

**Source**: About NemoClaw documentation (<https://github.com/NVIDIA/NemoClaw/blob/main/docs/about/overview.md>, accessed 2026-03-28) — states "Autonomous AI agents like OpenClaw can make arbitrary network requests, access the host filesystem, and call any inference endpoint. Without guardrails, this creates security, cost, and compliance risks..."

## Key Statistics

- **Repository Stars**: 17,312 (as of 2026-03-28)
- **Forks**: 1,962 (as of 2026-03-28)
- **Latest Commit**: 2026-03-27 (eb4ba8c, "fix: restore routed inference and connect UX")
- **Project Status**: Alpha (<https://github.com/NVIDIA/NemoClaw/blob/main/docs/about/release-notes.md>)
- **License**: Apache License 2.0
- **Primary Language**: JavaScript/TypeScript
- **Supported Platforms**: Linux (Ubuntu 22.04 LTS+), macOS (Apple Silicon via Colima/Docker Desktop), Windows WSL with Docker Desktop
- **Hardware Requirements**:
  - **Minimum**: 4 vCPU, 8 GB RAM, 20 GB disk free
  - **Recommended**: 4+ vCPU, 16 GB RAM, 40 GB disk free

**Source**: GitHub API response (<https://api.github.com/repos/NVIDIA/NemoClaw>, accessed 2026-03-28) — `"stargazers_count": 17312, "forks_count": 1962, "license": {"name": "Apache License 2.0"}`; package.json version "0.1.0"; README.md hardware tables.

## Key Features

**1. Sandboxed OpenClaw Execution**
Creates isolated OpenShell containers with Landlock, seccomp, and network namespace isolation. Agents run without default access to host resources; permissions are explicitly granted through policy.

**Source**: Overview documentation — "Every agent runs inside an OpenShell sandbox with Landlock, seccomp, and network namespace isolation. No access is granted by default."

**2. Routed Inference Management**
Inference requests from agents never leave the sandbox directly. OpenShell intercepts every inference call and routes it to the configured provider (NVIDIA Endpoints, OpenAI, Anthropic, Google Gemini, local Ollama, or compatible custom endpoints). Provider credentials remain on the host; the sandbox only sees `inference.local`.

**Source**: How It Works documentation — "Inference requests from the agent never leave the sandbox directly. OpenShell intercepts every inference call and routes it to the configured provider."

**3. Declarative Network Policy**
Egress rules are defined in YAML. The default policy in `nemoclaw-blueprint/policies/openclaw-sandbox.yaml` blocks all network egress except explicitly listed endpoints. Unknown hosts are blocked and surfaced to the operator for approval via the OpenShell TUI.

**Source**: README.md — "The sandbox starts with a default policy defined in `openclaw-sandbox.yaml`. This policy controls which network endpoints the agent can reach and which filesystem paths it can access."

**4. Unified CLI Interface**
The `nemoclaw` command orchestrates the full stack: gateway, sandbox, inference provider, and network policy. Installation via single command (`curl -fsSL https://www.nvidia.com/nemoclaw.sh | bash`).

**Source**: README.md — "The `nemoclaw` CLI orchestrates the full stack: OpenShell gateway, sandbox, inference provider, and network policy."

**5. Blueprint Versioning and Supply Chain Safety**
Blueprints are versioned Python artifacts with immutable release streams. The plugin resolves, verifies digest, and executes blueprints as subprocesses. Version compatibility is checked against `min_openshell_version` and `min_openclaw_version` constraints.

**Source**: Architecture documentation — "Blueprint artifacts are immutable, versioned, and digest-verified before execution" and "The blueprint determines which OpenShell resources to create or update..."

**6. Supported Inference Providers**
- NVIDIA Endpoints (hosted Nemotron 3 Super 120B on `integrate.api.nvidia.com`)
- OpenAI (native and OpenAI-compatible)
- Anthropic (native and Anthropic-compatible)
- Google Gemini (OpenAI-compatible)
- Local Ollama (with model auto-pull and validation)
- Experimental: Local NVIDIA NIM, local vLLM

**Source**: README.md — "Supported non-experimental onboarding paths: NVIDIA Endpoints, OpenAI, Other OpenAI-compatible endpoint, Anthropic, Other Anthropic-compatible endpoint, Google Gemini" and Inference Profiles documentation.

## Technical Architecture

**Component Structure:**

1. **Plugin (TypeScript)**
   - Thin, stable interface registered with OpenClaw CLI
   - TypeScript package in `nemoclaw/` directory
   - Registers `/nemoclaw` slash command and inference provider
   - Handles version resolution, digest verification, subprocess execution of blueprint
   - Operates in-process with OpenClaw gateway inside the sandbox

2. **Blueprint (Python)**
   - Versioned artifact with independent release cadence
   - Orchestrates OpenShell resource creation: gateway, inference providers, sandbox, network policy
   - Drives all interactions with OpenShell CLI
   - Defined in `nemoclaw-blueprint/` directory with manifest `blueprint.yaml`
   - Includes default policy: `nemoclaw-blueprint/policies/openclaw-sandbox.yaml`

3. **Sandbox Environment**
   - Runs container image `ghcr.io/nvidia/openshell-community/sandboxes/openclaw`
   - OpenClaw runs with NemoClaw plugin pre-installed
   - Filesystem isolation: `/sandbox` and `/tmp` writable; system paths read-only
   - Network isolation via default policy; approved endpoints persist for session

**Inference Flow:**
```
Agent (sandbox) → OpenShell gateway (host) → Provider (NVIDIA/OpenAI/Anthropic/etc)
```

**Blueprint Lifecycle (5 stages):**
1. **Resolve** — locate blueprint artifact, check version constraints
2. **Verify** — validate artifact digest
3. **Plan** — determine OpenShell resources to create/update
4. **Apply** — execute plan via OpenShell CLI commands
5. **Status** — report current state

**Source**: Architecture documentation section "NemoClaw Plugin" and "NemoClaw Blueprint"; How It Works documentation describing inference flow.

## Installation & Usage

### Prerequisites

**Software Requirements:**
- Linux: Ubuntu 22.04 LTS or later
- Node.js: v22.16.0 or later
- npm: v10 or later
- Container runtime: Docker (primary), Colima, or Docker Desktop

**Optional:**
- OpenShell CLI (installed by NemoClaw)
- Ollama (for local inference)

**Source**: README.md quickstart section — lists Node.js 22.16, npm 10, and container runtime requirements.

### Installation Steps

```bash
# Download and run installer
curl -fsSL https://www.nvidia.com/nemoclaw.sh | bash
```

The installer:
1. Installs Node.js if not present
2. Runs interactive onboarding wizard
3. Creates sandbox, configures inference, applies security policies
4. Installs `nemoclaw` CLI globally

If using nvm or fnm: `source ~/.bashrc` (or `~/.zshrc` for zsh) after install to update PATH.

**Source**: README.md "Install NemoClaw and Onboard OpenClaw Agent" section.

### Basic Commands

```bash
# Interactive setup (creates sandbox and configures inference)
nemoclaw onboard

# Connect to sandbox shell
nemoclaw my-assistant connect

# Open OpenClaw TUI (interactive chat)
openclaw tui

# Send single message via CLI
openclaw agent --agent main --local -m "hello" --session-id test

# Check sandbox status
nemoclaw my-assistant status

# View logs
nemoclaw my-assistant logs --follow

# Uninstall NemoClaw and all resources
curl -fsSL https://raw.githubusercontent.com/NVIDIA/NemoClaw/refs/heads/main/uninstall.sh | bash
```

**Source**: README.md quickstart section — "Chat with the Agent" and "Key Commands" subsections.

### Configuration

**Host-Side State Files:**
- `~/.nemoclaw/credentials.json` — provider credentials (saved during onboarding)
- `~/.nemoclaw/sandboxes.json` — sandbox metadata and default selection
- `~/.openclaw/openclaw.json` — host OpenClaw config (snapshots/restores during migration)

**Sandbox Policy Customization:**
- **Static**: Edit `openclaw-sandbox.yaml` and re-run `nemoclaw onboard` (persists)
- **Dynamic**: Run `openshell policy set <policy-file>` on running sandbox (session only)
- Preset policies available in `nemoclaw-blueprint/policies/presets/` for common integrations (PyPI, Docker Hub, Slack, Jira)

**Source**: README.md "Host-Side State and Config" and "Configuring Sandbox Policy" sections.

## Relevance to Claude Code Development

NemoClaw is relevant for Claude Code in three principal areas:

1. **Agent Sandbox Reference Implementation** — Provides a working model for sandboxed agent execution with policy-enforced isolation, applicable to designing secure agent deployment systems.

2. **Inference Routing Patterns** — Demonstrates transparent credential isolation and provider routing architecture, useful for multi-provider LLM infrastructure in Claude Code extensions.

3. **Supply Chain and Versioning** — Illustrates blueprint versioning, digest verification, and reproducible setup patterns applicable to plugin lifecycle management and security-critical artifact deployment.

**For active development**: NemoClaw is built on OpenClaw and OpenShell. If Claude Code needs to integrate with OpenClaw agents or deploy agents to OpenShell sandboxes, NemoClaw provides the production reference implementation.

## Limitations and Caveats

**1. Alpha Status**
NemoClaw is available in early preview (released March 16, 2026). Interfaces, APIs, and behavior may change without notice. Not production-ready.

**Source**: README.md alpha statement — "Alpha software... This software is not production-ready. Interfaces, APIs, and behavior may change without notice as we iterate on the design."

**2. Platform Support Gaps**
- macOS: Podman not yet supported (depends on OpenShell Podman support)
- macOS: Local host-routed inference remains experimental, depends on OpenShell host-routing support
- Experimental local providers (NVIDIA NIM, vLLM) require environment variable `NEMOCLAW_EXPERIMENTAL=1`

**Source**: README.md container runtime support table and Inference Profiles documentation.

**3. Memory Requirements on Resource-Constrained Systems**
Machines with less than 8 GB RAM may trigger OOM killer during sandbox image push. Workaround: configure at least 8 GB swap (at cost of slower performance).

**Source**: README.md hardware section — "On machines with less than 8 GB of RAM, this combined usage can trigger the OOM killer. If you cannot add memory, configuring at least 8 GB of swap can work around the issue..."

**4. Sandbox Image Size**
Sandbox image is approximately 2.4 GB compressed. Requires sufficient disk space and bandwidth for pull during first run.

**Source**: README.md prerequisites.

**5. Approval Flow Not Automated**
Network egress approvals for unknown hosts require operator interaction via OpenShell TUI. Not suitable for fully autonomous unattended operation without pre-configured policy that covers all required endpoints.

**Source**: README.md protection layers — "When the agent tries to reach an unlisted host, OpenShell blocks the request and surfaces it in the TUI for operator approval."

## References

- [NVIDIA NemoClaw GitHub Repository](https://github.com/NVIDIA/NemoClaw) — source code, issues, discussions (accessed 2026-03-28)
- [NemoClaw Official Documentation](https://docs.nvidia.com/nemoclaw/latest/) — comprehensive guides and reference
- [NemoClaw Quick Start](https://github.com/NVIDIA/NemoClaw/blob/main/README.md) — installation and basic usage
- [NVIDIA OpenShell](https://github.com/NVIDIA/OpenShell) — underlying sandbox runtime
- [OpenClaw Project](https://openclaw.ai) — agent framework NemoClaw integrates
- [NVIDIA Build Platform](https://build.nvidia.com) — Nemotron 3 endpoint inference
- [Community Discord](https://discord.gg/XFpfPv9Uvx) — support and discussion channel
- [Release Notes](https://github.com/NVIDIA/NemoClaw/blob/main/docs/about/release-notes.md) — alpha status and changelog

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [ZeroClaw](./zeroclaw.md) | agent-infrastructure | Parallel lightweight agent runtime; both enable policy-enforced execution with trait-driven architecture |
| [Zeroboot](./zeroboot.md) | agent-infrastructure | Complementary sandbox technology; Zeroboot provides sub-millisecond VM fork isolation while NemoClaw provides policy layers on top |
| [Fly.io](./fly-io.md) | agent-infrastructure | Alternative infrastructure platform for agent deployment; Sprites provide persistent VM sandboxes similar to NemoClaw's sandboxed OpenClaw model |
| [Plano](./plano.md) | agent-infrastructure | Overlapping orchestration concern; Plano handles LLM inference routing via proxy pattern while NemoClaw routes inference within sandbox boundary |
| [PicoClaw](./picoclaw.md) | agent-infrastructure | Sibling project in the Claw ecosystem; ultra-lightweight agent design vs NemoClaw's reference stack approach |
| [AutoResearchClaw](./AutoResearchClaw.md) | agent-infrastructure | Advanced Claw variant; extends autonomous agent patterns with multi-stage pipeline and self-healing capabilities |
| [OpenAI Codex CLI](../coding-agents/openai-codex-cli.md) | coding-agents | Shared security design pattern; both implement OS sandbox isolation plus policy-enforced approval model for untrusted code execution |

## Freshness Tracking

**Last Reviewed**: 2026-03-28

**Latest Commit in Repository**: 2026-03-27 20:36:26 UTC (commit eb4ba8c)

**Next Review**: 2026-06-28 (3 months)

### Confidence Summary

| Section | Confidence | Notes |
|---------|-----------|-------|
| Overview | high | Official documentation, README, recently updated repository |
| Problem Addressed | high | Stated in official overview documentation |
| Key Statistics | high | Verified from GitHub API and package.json |
| Key Features | high | Extracted from official documentation with verbatim quotes |
| Technical Architecture | high | Architecture documentation provides detailed component structure |
| Installation & Usage | high | Official quickstart guide with exact command reproduction |
| Limitations | high | Explicitly documented in README and reference docs |
| Relevance to Claude Code | medium | Inferred from architecture and patterns; not explicitly stated by project |

**Data Freshness Notes**:
- Repository created 2026-03-15, latest commit 2026-03-27 (very recent)
- Package version 0.1.0 reflects alpha status
- GitHub stars count reflects early adoption interest (17,312 in first ~2 weeks)
- All documentation accessed directly from primary sources (official repo, docs site)
- No external summaries or secondhand sources relied upon
