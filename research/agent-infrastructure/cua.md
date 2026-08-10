---
title: "CUA (Computer-Use Agents)"
---

## Key Statistics

**GitHub Repository Stats** (as of 2026-05-03):
- Stars: 15,500
- Forks: 958
- Releases: 476
- Latest Release: cua-driver-v0.1.2 (May 2, 2026)
- Last Updated: Active development

**Community:** Discord server for discussions and collaboration

---

## Overview

CUA is an open-source infrastructure platform for building, benchmarking, and deploying AI agents capable of autonomous computer interaction. The platform enables agents to perceive visual interfaces, interact with GUI elements, and complete tasks autonomously across multiple operating systems including macOS, Linux, Windows, and Android.

**Core positioning:** "Open-source infrastructure for Computer-Use Agents. Sandboxes, SDKs, and benchmarks to train and evaluate AI agents that can control full desktops."

---

## Problem Addressed

CUA addresses three critical needs in autonomous agent development:

1. **Cross-platform agent deployment**: Unified infrastructure for running agents across heterogeneous environments (macOS, Linux, Windows, Android) without custom implementation for each platform.

2. **Agent evaluation and benchmarking**: Standardized evaluation framework for measuring agent capability and performance on real-world tasks using datasets like OSWorld, ScreenSpot, and Windows Arena.

3. **Non-disruptive automation**: Background computer-use automation that operates without interrupting user workflows or requiring accessibility surface modifications, enabling seamless integration of autonomous agents with human users.

---

## Key Features

### Core Components

1. **Cua Driver** — Background automation for macOS native applications. Agents operate on non-accessibility surfaces including Chromium content and canvas-based tools without interfering with user interaction.

2. **Cua Sandbox** — Unified API supporting multiple runtime environments:
   - Linux containers
   - Linux/Windows/macOS virtual machines
   - Android environments
   - Bring-your-own-image capability
   - Standardized interface across platforms

3. **CuaBot** — Desktop integration layer providing:
   - Native window support for agent sandboxes
   - H.265 video encoding for efficient screen transmission
   - Clipboard sharing between agent and host
   - Audio support for multimodal interactions

4. **Cua-Bench** — Evaluation and benchmarking framework featuring:
   - Integration with OSWorld, ScreenSpot, and Windows Arena datasets
   - Trajectory export for analysis
   - RL environment support for agent training

5. **Lume** — Apple Silicon virtual machine management using macOS Virtualization.Framework for near-native performance on Apple Silicon hardware.

### SDK & Integration

- **Python SDK:** Primary interface via `pip install cua` (Python 3.11+)
- **JavaScript SDK:** CuaBot interface via `npx cuabot`
- **Installation automation:** Shell script installation for Cua Driver via curl

---

## Installation & Usage

```bash
# Cua Sandbox (Python SDK)
pip install cua

# CuaBot (Desktop Integration)
npx cuabot

# Cua Driver (macOS only)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/trycua/cua/main/libs/cua-driver/scripts/install.sh)"
```

---

## Technical Architecture

CUA follows a modular architecture with clear separation of concerns:

- **Agent execution layer** — Handles agent lifecycle and task orchestration
- **Environment abstraction** — Unified interface over heterogeneous runtimes (containers, VMs, physical systems)
- **Perception layer** — Visual screen capture and GUI element detection
- **Action layer** — Screen interaction primitives (clicks, keyboard input, scrolling)
- **Evaluation layer** — Benchmarking and trajectory analysis infrastructure

The platform emphasizes interoperability, allowing agents built with CUA to run across different environments with minimal code changes.

---

## Use Cases

1. **Autonomous task completion** — Agents that interact with web applications, desktop software, and native mobile apps to complete user-defined objectives.

2. **UI/UX testing** — Automated interaction with user interfaces for regression testing, compatibility verification, and usability validation.

3. **Agent research & benchmarking** — Standardized evaluation of agent architectures and approaches using curated datasets and task suites.

4. **Cross-platform automation** — Scripts and workflows that adapt to different operating systems through CUA's unified environment API.

5. **Human-agent collaboration** — Background agents operating on systems without interrupting user workflows or requiring accessibility modifications.

---

## Integration Points

**LLM Providers:** Agent-agnostic design supports integration with any LLM provider (Claude, GPT, open-source models)

**Environment Support:**
- Docker containers (Linux)
- QEMU/KVM (Linux)
- Parallels Desktop (macOS)
- VirtualBox (cross-platform)
- Native Android (via Android SDK)
- Bring-your-own images

**Data Pipelines:**
- OSWorld dataset integration
- ScreenSpot benchmark support
- Windows Arena task suites
- Custom trajectory export for analysis

---

## Notable Characteristics

1. **High star count (15.5k)** — Strong community adoption and interest in computer-use agent research.

2. **Active development** — 476 releases indicate rapid iteration and feature addition.

3. **Multi-language implementation** — Mix of HTML, Python, Swift, and TypeScript reflects diverse component needs (web UI, core logic, platform-specific functionality, JavaScript bindings).

4. **Platform diversity** — Support for major operating systems (macOS, Linux, Windows) plus Android and virtualization technologies.

5. **Evaluation-first design** — Benchmarking and trajectory export capabilities suggest research and measurement are first-class concerns.

---

## Related Projects & Ecosystem

CUA integrates with and builds upon:

- **OSWorld dataset** — For benchmarking agent performance on realistic tasks
- **ScreenSpot** — Visual grounding and screen interaction evaluation
- **Windows Arena** — Windows-specific task evaluation suite
- **OmniParser (CC-BY-4.0)** — Screen parsing and UI element detection
- **Kasm (MIT)** — Container-based isolation and KVM virtualization

---

## Relevance to Claude Code Development

### Direct Applications

1. **Multi-OS Agent Execution**: Claude Code agents that need to automate GUI interactions across macOS, Windows, Linux, and Android can leverage CUA's unified sandbox API without OS-specific implementation branches.

2. **Benchmarking Agent Behavior**: CUA's integration with OSWorld, ScreenSpot, and Windows Arena datasets enables standardized evaluation of agent capabilities — valuable for Claude Code plugin developers testing agent-driven workflows.

3. **Non-Disruptive Automation**: The non-accessibility-surface approach enables agents to interact with applications (Chromium, canvas tools) without triggering accessibility APIs, useful for automation that must coexist with user workflows.

### Patterns Worth Adopting

1. **Sandbox Abstraction Layer**: CUA's unified environment interface across Linux, VMs, Android, and bring-your-own-images demonstrates effective abstraction for heterogeneous execution environments — applicable to Claude Code's own execution layer.

2. **Evaluation-First Design**: First-class benchmarking and trajectory export show how agent evaluation can be a core concern, not an afterthought — useful for Claude Code plugin quality assurance.

### Integration Opportunities

1. **Claude Code Agent Sandbox Backend**: Use CUA's sandboxes for safe execution of Claude Code agents that interact with GUI applications.

2. **Cross-Platform Agent Development**: Agents could test behavior across all supported OSes via CUA's unified API before deployment.

---

## References

- [GitHub - trycua/cua](https://github.com/trycua/cua) (accessed 2026-08-10)
- [CUA Official Documentation](https://cua.ai/docs) (accessed 2026-08-10)
- [CUA Community Discord](https://discord.gg/cua) (accessed 2026-08-10)
- [OSWorld Benchmark Dataset](https://www.osworld.dev) (accessed 2026-08-10)
- [ScreenSpot Evaluation Framework](https://www.screenspot.dev) (accessed 2026-08-10)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Empirica](./empirica.md) | agent-infrastructure | Both address autonomous agent reliability: CUA provides sandboxed computer-use execution, empirica provides epistemic measurement and confidence gating before agents take actions. CUA's benchmarking + empirica's calibration framework = stronger evaluation methodology |
| [HappyCapy](./happycapy.md) | agent-infrastructure | Browser-based alternative to CUA's desktop/mobile focus: HappyCapy eliminates local installation via cloud sandbox, CUA emphasizes cross-platform support. Both solve the "agent needs isolated execution environment" problem from different angles |
| [PinchTab](./pinchtab.md) | agent-infrastructure | Token-efficient browser automation for agents: CUA uses vision-based screen interaction, PinchTab uses accessibility tree snapshots. Complementary approaches — PinchTab's token efficiency could enhance CUA's perception layer for web-based tasks |
| [TinyFish](./tinyfish.md) | agent-infrastructure | Serverless web automation at scale: CUA manages desktop/mobile environments, TinyFish manages web-specific tasks. Both eliminate infrastructure management; integration would enable multi-modal agent (desktop + web) coordination |
| [AutoResearchClaw](./AutoResearchClaw.md) | agent-infrastructure | Multi-agent orchestration with iterative repair: both systems spawn specialized agents for complex tasks and recover from failures. CUA's multi-OS environment could serve as execution layer for AutoResearchClaw's code generation experiments |
| [Kernel](./kernel-sh.md) | agent-infrastructure | Shared problem: providing isolated browser instances for agent automation. CUA covers full desktop; Kernel focuses on headless Chrome. Different scopes, same architectural principle (environment abstraction) |
| [Fly.io](./fly-io.md) | agent-infrastructure | Cloud deployment platform for agents: CUA provides the sandbox/runtime layer; Fly.io provides the deployment/scaling infrastructure. Complementary — CUA agents could be containerized and deployed on Fly.io for multi-region execution |

---
