---
name: OpenHands - Open Platform for Cloud Coding Agents
description: OpenHands is an open-source, model-agnostic platform for building and deploying AI coding agents. It provides a composable Python SDK, CLI, and cloud infrastructure for running agents that write...
license: MIT (core), Source-Available (enterprise)
metadata:
  topic: openhands
  category: coding-agents
  source_url: https://openhands.dev
  github: OpenHands/OpenHands
  version: "v1.2.1"
  verified: "2026-01-26"
  next_review: "2026-04-26"
---

## Overview

OpenHands is an open-source, model-agnostic platform for building and deploying AI coding agents. It provides a composable Python SDK, CLI, and cloud infrastructure for running agents that write software - from simple tasks like README generation to complex multi-agent refactors. The platform achieves state-of-the-art performance on SWE-bench Verified (77.6%) and serves as the preferred evaluation harness for LLM coding benchmarks.

**Core Value Proposition**: Scale from a single task to thousands of parallel agents with full control over model selection, deployment, and security.

---

## Problem Addressed

| Problem                                                               | How OpenHands Solves It                                                          |
| --------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| Proprietary AI coding tools lock you into specific models             | Model-agnostic architecture works with Claude, GPT, Qwen, Devstral, or any LLM   |
| Scaling from laptop to production requires re-architecture            | Single Python API runs locally or scales to 1000s of agents in the cloud         |
| AI agents lack access to real development environments                | Secure, sandboxed Docker/Kubernetes runtime with file system, shell, and browser |
| Evaluating and improving AI coding agents is slow and expensive       | 30x speedup on SWE-bench evaluation with cloud-based infrastructure              |
| Integrating AI agents into existing workflows requires custom tooling | Native integrations with GitHub, GitLab, Slack, Jira, Linear, and CI/CD          |

---

## Key Statistics (as of January 26, 2026)

| Metric                   | Value                                     |
| ------------------------ | ----------------------------------------- |
| GitHub Stars             | 67,108                                    |
| Forks                    | 8,347                                     |
| Open Issues              | 252                                       |
| Contributors             | 30+                                       |
| SWE-Bench Verified Score | 77.6%                                     |
| SWE-Bench Lite Score     | 41.7%                                     |
| Languages Supported      | Python (primary), Any (via Docker)        |
| License                  | MIT (core), Source-Available (enterprise) |
| Created                  | March 13, 2024                            |

---

## Key Features

### Model-Agnostic Agent Framework

- Works with Claude, GPT, or any other LLM (locally or via API) — the CLI docs state "You can power it with Claude, GPT, or any other LLM"
- Unified Python SDK plus integrated REST/WebSocket services for agent definition and execution
- SWE-bench badge score of 77.6 in the project README (raised from 72.8 in December 2025); the README attributes this to OpenHands as a whole, not to a named agent version. The separately published CodeAct 2.1 agent scored 53% on SWE-Bench Verified when announced in November 2024.

### Multiple Deployment Modes

- **Local**: Python SDK for laptop/local development
- **CLI**: Terminal-based interface for interactive agent interaction
- **Cloud**: Hosted deployment; README lists Slack, Jira, and Linear integrations, multi-user support, RBAC and permissions, and conversation sharing. Sign-in is via a GitHub or GitLab account.
- **Enterprise**: Source-available self-hosted option for VPC/Kubernetes

### Rich Tool Integration

- Pre-defined tools: Bash execution, file editing, web browsing, MCP client support
- Custom tool creation via Python
- Docker/Kubernetes sandboxed execution for safe code testing
- Native file system, shell, and browser access

### Production-Ready Features

- Context compression via the SDK's condenser, for long-running tasks
- Built-in security analysis (named in the SDK tech report as a differentiator vs. the OpenAI, Claude, and Google SDKs)
- Task planning and decomposition, via the SDK's `task_tracker` and `planning_file_editor` tools
- Evaluation tooling: an OpenHands blog post reports "speedups of 30x or more" on agent evaluation by running SWE-Bench Lite 32x parallel in the cloud. This is an evaluation-harness result, not a runtime feature of the agent itself.

**Sources**:

- README as of 2026-01-08 (commit `adfabe7659`, the state at the 2026-01-26 access date): SWE-bench 77.6 badge, deployment modes, Cloud/Enterprise feature lists — <https://github.com/OpenHands/OpenHands/blob/adfabe7659/README.md>
- SDK tech report, arXiv 2511.03690: sandboxed execution, multi-LLM routing, built-in security analysis, REST/WebSocket services — <https://arxiv.org/abs/2511.03690>
- SDK tool inventory (`terminal`, `file_editor`, `browser_use`, `task_tracker`, `planning_file_editor`, condenser) — <https://github.com/OpenHands/software-agent-sdk>
- CodeAct 2.1 53% SWE-Bench Verified score (2024-11-01) — <https://www.openhands.dev/blog/openhands-codeact-21-an-open-state-of-the-art-software-development-agent>
- 30x evaluation speedup (2024-10-04) — <https://www.openhands.dev/blog/evaluation-of-llms-as-coding-agents-on-swe-bench-at-30x-speed>

All re-verified against primary sources 2026-08-11.

---

## Product Offerings

### 1. Software Agent SDK

The core Python library powering all OpenHands products.

**Features**:

- Unified Python API for local and cloud execution
- Pre-defined tools for Bash, file editing, web browsing, MCP
- REST-based Agent Server for Docker/Kubernetes deployment
- Custom agent definition and tool creation
- Automatic context compression
- Task planning and decomposition

**Usage**:

```python
from openhands import Agent, Tool

# Define custom agent
agent = Agent(model="claude-3-5-sonnet", tools=[Tool.bash, Tool.file_edit, Tool.web_browse])

# Run on code task
result = agent.run("Fix the authentication bug in login.py")
```

### 2. OpenHands CLI

Terminal-based interface similar to Claude Code or Codex.

**Installation**:

```bash
pip install openhands-cli
openhands --model claude-3-5-sonnet
```

**Features**:

- Works with any LLM (Claude, GPT, open-source models)
- Familiar terminal experience
- Full file system access within sandbox

### 3. OpenHands Local GUI

Desktop application with REST API and React frontend.

**Features**:

- Similar experience to Devin or Jules
- REST API for integration
- Single-page React application
- Local laptop execution

### 4. OpenHands Cloud

Hosted deployment with enterprise features.

**Features**:

- Free $10 credit to start
- GitHub/GitLab/Bitbucket integrations
- Slack, Jira, Linear integrations
- Multi-user support with RBAC
- Conversation sharing and collaboration
- Usage reporting and budgeting

### 5. OpenHands Enterprise

Self-hosted deployment for VPC/Kubernetes environments.

**Features**:

- Source-available (enterprise/ directory)
- Extended support and research team access
- Works with CLI and SDK
- Full control over data and infrastructure

---

## Technical Architecture

<eg>
┌─────────────────────────────────────────────────────────────────┐
│                     OpenHands Platform                           │
└─────────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  Software Agent │  │   Agent Server   │  │    Workspace     │
│      SDK        │  │  (REST API)      │  │   (Sandbox)      │
│                 │  │                  │  │                  │
│ - Agent logic   │  │ - Task queue     │  │ - Docker/K8s     │
│ - Tool registry │  │ - Scaling        │  │ - File system    │
│ - LLM interface │  │ - Auth/RBAC      │  │ - Shell access   │
│ - State mgmt    │  │ - Integrations   │  │ - Browser        │
└─────────────────┘  └─────────────────┘  └─────────────────┘
         │                    │                    │
         └────────────────────┼────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   CLI Interface │  │   Local GUI      │  │   Cloud/Enterprise│
│                 │  │                  │  │                   │
│ - Terminal UX   │  │ - React SPA      │  │ - Multi-tenant    │
│ - Any LLM       │  │ - REST API       │  │ - Integrations    │
│ - Local exec    │  │ - Devin-like     │  │ - Scaling         │
└─────────────────┘  └─────────────────┘  └─────────────────┘
</eg>

---

## State-of-the-Art Agent: CodeAct 2.1

OpenHands includes CodeAct 2.1, an open-source agent achieving top benchmark performance:

**Key Innovations**:

- **Inference-Time Scaling**: Multiple solution attempts with critic model selection
- **Automatic Context Compression**: Manages long-running tasks
- **Security Analysis**: Built-in code safety checks
- **Strong Agent-Computer Interfaces**: Reliable tool execution

**OpenHands LM 32B**: Open coding model (available on Hugging Face):

- 32B parameters (runs on single 3090 GPU)
- 37.2% on SWE-Bench Verified
- No API calls required

---

## Installation & Usage

### SDK Installation

```bash
pip install openhands-sdk
```

### CLI Installation

```bash
pip install openhands-cli
```

### Local GUI (Docker)

```bash
docker pull openhands/openhands:latest
docker run -p 3000:3000 openhands/openhands
```

### Cloud Signup

1. Visit <https://app.all-hands.dev>
2. Sign in with GitHub or GitLab
3. Get free $10 credit

---

## Benchmark Performance

| Benchmark            | Score     | Notes                       |
| -------------------- | --------- | --------------------------- |
| SWE-Bench Verified   | 77.6%     | State-of-the-art (Jan 2026) |
| SWE-Bench Lite       | 41.7%     | Open-source leader          |
| SWE-Bench Full       | Top tier  | 2,294 instances             |
| SWE-Bench Multimodal | Supported | 517 instances with visuals  |

**Evaluation Infrastructure**: <https://github.com/OpenHands/benchmarks>

---

## Community & Ecosystem

### Related Projects

- **Software Agent SDK**: <https://github.com/OpenHands/software-agent-sdk>
- **OpenHands CLI**: <https://github.com/OpenHands/OpenHands-CLI>
- **Chrome Extension**: <https://github.com/OpenHands/openhands-chrome-extension>
- **Theory-of-Mind Module**: <https://github.com/OpenHands/ToM-SWE>
- **Benchmarks**: <https://github.com/OpenHands/benchmarks>

### Community Resources

- **Slack**: <https://openhands.dev/joinslack>
- **Product Roadmap**: <https://github.com/orgs/openhands/projects/1>
- **Research Paper**: <https://arxiv.org/abs/2511.03690>

---

## Relevance to Claude Code Development

### Direct Applications

1. **Alternative Agent Framework**: OpenHands SDK provides patterns for agent composition that could inform Claude Code plugin development
2. **Evaluation Infrastructure**: SWE-bench harness could evaluate Claude Code agent performance
3. **Tool Design Patterns**: Pre-built tools for file editing, shell, and web browsing demonstrate effective tool interfaces
4. **Model-Agnostic Architecture**: Patterns for supporting multiple LLM backends

### Patterns Worth Adopting

1. **Workspace Isolation**: Docker/Kubernetes sandboxing for safe code execution
2. **CodeAct Interface**: Combining code and natural language in single turns
3. **Inference-Time Scaling**: Multiple attempts with critic model selection
4. **Context Compression**: Automatic management of long conversations
5. **REST-Based Agent Server**: Scalable deployment pattern

### Integration Opportunities

1. **MCP Integration**: OpenHands supports MCP tools - potential for shared tool ecosystem
2. **Benchmark Suite**: Could evaluate Claude Code agents using OpenHands infrastructure
3. **Open Model Testing**: OpenHands LM 32B provides baseline for local model performance
4. **Enterprise Patterns**: Source-available enterprise features provide deployment blueprints

### Competitive Analysis

| Feature                | OpenHands          | Claude Code         |
| ---------------------- | ------------------ | ------------------- |
| Model Lock-in          | None (any LLM)     | Claude only         |
| Open Source            | Yes (MIT core)     | No                  |
| Cloud Offering         | Yes                | Yes (via Anthropic) |
| Self-Hosted Enterprise | Yes                | No                  |
| SWE-Bench Performance  | 77.6%              | Not published       |
| MCP Support            | Yes                | Native              |
| Local Model Support    | Yes (OpenHands LM) | No                  |

---

## References

1. **Official Website**: <https://openhands.dev> (accessed 2026-01-26)
2. **GitHub Repository**: <https://github.com/OpenHands/OpenHands> (accessed 2026-01-26)
3. **SDK Documentation**: <https://docs.openhands.dev/sdk> (accessed 2026-01-26)
4. **SWE-Bench Leaderboard**: <https://www.swebench.com/> (accessed 2026-01-26)
5. **CodeAct 2.1 Announcement**: <https://openhands.dev/blog/openhands-codeact-21-an-open-state-of-the-art-software-development-agent> (accessed 2026-01-26)
6. **OpenHands LM 32B Announcement**: <https://openhands.dev/blog/introducing-openhands-lm-32b-a-strong-open-coding-agent-model> (accessed 2026-01-26)
7. **Research Paper**: <https://arxiv.org/abs/2511.03690> (accessed 2026-01-26)
