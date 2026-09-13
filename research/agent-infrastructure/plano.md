---
name: Plano - AI-Native Proxy and Data Plane for Agentic Apps
description: Plano is an AI-native proxy server and data plane that offloads infrastructure concerns from agentic applications. Built on Envoy by its core contributors, Plano provides unified orchestration, model...
license: Apache-2.0
metadata:
  topic: plano
  category: agent-infrastructure
  source_url: https://planoai.dev
  github: katanemo/plano
  version: "v0.4.3"
  verified: "2026-01-26"
  next_review: "2026-04-26"
---

## Overview

Plano is an AI-native proxy server and data plane that offloads infrastructure concerns from agentic applications. Built on Envoy by its core contributors, Plano provides unified orchestration, model routing, observability, and guardrails so developers can focus on agent business logic rather than delivery infrastructure.

**Core Value Proposition**: Move "hidden middleware" concerns (routing logic, model management, tracing, guardrails) out of application code into a unified, out-of-process data plane.

---

## Problem Addressed

| Problem                                            | How Plano Solves It                                                                 |
| -------------------------------------------------- | ----------------------------------------------------------------------------------- |
| Building routing logic to reach the right agent    | Declarative YAML configuration with Plano-Orchestrator (4B parameter routing model) |
| Handling each LLM provider's API quirks            | Unified OpenAI-compatible API with automatic model routing                          |
| Instrumenting every service with OTEL for tracing  | Zero-code capture of traces, metrics, and "Agentic Signals" across all agents       |
| Building guardrail hooks for safety and moderation | Filter Chains for jailbreak protection, moderation policies, and memory hooks       |
| Updating routing code when adding new agents       | Add to YAML config and restart - no code changes required                           |
| Managing model fallbacks and provider failures     | Automatic fallback routing with preference-based selection                          |

---

## Key Statistics (as of January 26, 2026)

| Metric           | Value                     |
| ---------------- | ------------------------- |
| GitHub Stars     | 4,872                     |
| Forks            | 274                       |
| Contributors     | 25                        |
| Open Issues      | 96                        |
| Primary Language | Rust                      |
| Created          | July 2024                 |
| Latest Release   | v0.4.3 (January 18, 2026) |

---

## Key Features

### 1. Agent Orchestration

- **Plano-Orchestrator**: Purpose-built 4B parameter routing model for intent analysis
- **Natural Language Routing**: Route based on agent descriptions, not hardcoded logic
- **Multi-Agent Sequencing**: Automatic determination of which agents collaborate and in what order
- **Zero Code Changes**: Add new agents via YAML configuration

### 2. Model Agility (LLM Gateway)

- **Unified API**: OpenAI-compatible interface for all LLM providers
- **Routing Modes**:
  - Model name routing (explicit model selection)
  - Alias routing (semantic names like "fast" or "accurate")
  - Preference-based routing (automatic selection based on cost/performance)
- **Provider Support**: OpenAI, Anthropic, Azure OpenAI, and OpenAI-compatible providers
- **Automatic Failover**: Fallback to alternative models/providers on failure

### 3. Observability (Agentic Signals)

- **Zero-Code Tracing**: Automatic OpenTelemetry traces across all agents
- **Function Call Capture**: Track tool usage, reasoning steps, model behavior
- **Centralized Logging**: Unified view of multi-agent request flows
- **Metrics Export**: Performance metrics without instrumentation code

### 4. Filter Chains (Guardrails)

- **Jailbreak Protection**: Built-in content filtering
- **Moderation Policies**: Configurable content moderation
- **Memory Hooks**: Consistent memory management across agents
- **Custom Filters**: Extensible filter chain architecture

### 5. Prompt Targets (Deterministic API Calls)

- **Natural Language to API**: Convert prompts into structured, validated API calls
- **Parameter Extraction**: Automatic extraction from natural language
- **Schema Validation**: Type-safe parameter handling
- **Endpoint Mapping**: Direct mapping from intent to backend APIs

---

## Technical Architecture

<eg>
                     User Request
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Plano Gateway                             │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐   │
│  │ Filter Chains │  │  Orchestrator │  │  LLM Gateway  │   │
│  │ (Guardrails)  │  │   (Routing)   │  │ (Model Proxy) │   │
│  └───────────────┘  └───────────────┘  └───────────────┘   │
│                          │                                   │
│  ┌───────────────────────┴───────────────────────┐         │
│  │              Agentic Signals                   │         │
│  │         (Zero-code OTEL Tracing)              │         │
│  └───────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
    ┌──────────┐   ┌──────────┐   ┌──────────┐
    │ Agent A  │   │ Agent B  │   │ Agent C  │
    │ (HTTP)   │   │ (HTTP)   │   │ (HTTP)   │
    └──────────┘   └──────────┘   └──────────┘
</eg>

**Inner Loop vs Outer Loop Design**:

- **Inner Loop (Agent Logic)**: Business logic, tool calls, reasoning - implemented in any language/framework
- **Outer Loop (Orchestration)**: Routing, sequencing, lifecycle management - handled by Plano

---

## Installation & Usage

### Prerequisites

- Docker v24+
- Docker Compose v2.29+
- Python v3.10+

### Installation

```bash
# Using uv (recommended)
uv tool install planoai==0.4.3

# Using pip
pip install planoai==0.4.3
```

### Basic Configuration

```yaml
# plano_config.yaml
version: v0.3.0

agents:
  - id: weather_agent
    url: http://localhost:10510
  - id: flight_agent
    url: http://localhost:10520

model_providers:
  - model: openai/gpt-4o
    access_key: $OPENAI_API_KEY
    default: true
  - model: anthropic/claude-3-5-sonnet
    access_key: $ANTHROPIC_API_KEY

listeners:
  - type: agent
    name: travel_assistant
    port: 8001
    router: plano_orchestrator_v1
    agents:
      - id: weather_agent
        description: |
          Gets real-time weather and forecasts for any city.
      - id: flight_agent
        description: |
          Searches flights between airports with schedules.

tracing:
  random_sampling: 100
```

### Start Plano

```bash
planoai up plano_config.yaml
# Or with uv: uvx planoai up plano_config.yaml
```

### Query

```bash
curl http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [
      {"role": "user", "content": "Find flights from NYC to Paris and check the weather there"}
    ]
  }'
```

---

## Relevance to Claude Code Development

### Direct Applications

1. **Multi-Agent Orchestration**: Pattern for coordinating specialized Claude Code sub-agents
2. **Model Routing**: Strategy for selecting between different models (Haiku/Sonnet/Opus) based on task requirements
3. **Observability Patterns**: Zero-code tracing approach applicable to agent workflows
4. **Guardrail Architecture**: Filter chain design for input validation and safety checks

### Patterns Worth Adopting

1. **Inner/Outer Loop Separation**: Clear boundary between agent logic and orchestration
2. **Declarative Routing**: YAML-based agent configuration with natural language descriptions
3. **Unified Model Interface**: Abstraction layer over multiple LLM providers
4. **Agentic Signals**: Structured capture of agent behavior for debugging and improvement
5. **Purpose-Built Routing Models**: Lightweight, specialized models for routing decisions

### Integration Opportunities

1. Could inform design of Claude Code plugin orchestration layer
2. Filter chain patterns applicable to hook system design
3. Tracing approach could enhance Claude Code's built-in observability
4. Agent description format could influence skill/agent frontmatter design

### Key Insight

Plano's use of a purpose-built 4B parameter routing model demonstrates that specialized, lightweight models can outperform heavyweight general-purpose models for specific infrastructure tasks like routing - a pattern applicable to Claude Code's agent delegation decisions.

---

## References

1. **Official Documentation**: <https://docs.planoai.dev> (accessed 2026-01-26)
2. **GitHub Repository**: <https://github.com/katanemo/plano> (accessed 2026-01-26)
3. **Quickstart Guide**: <https://docs.planoai.dev/get_started/quickstart.html> (accessed 2026-01-26)
4. **Agent Concepts**: <https://docs.planoai.dev/concepts/agents.html> (accessed 2026-01-26)
5. **Orchestration Guide**: <https://docs.planoai.dev/guides/orchestration.html>
6. **Filter Chains Documentation**: <https://docs.planoai.dev/concepts/filter_chain.html>
7. **Research Publications**: <https://planoai.dev/research>

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [octogent](../agent-frameworks/octogent.md) | agent-frameworks | referenced by octogent (agent-frameworks) |
| [solace-agent-mesh](../agent-frameworks/solace-agent-mesh.md) | agent-frameworks | referenced by solace-agent-mesh (agent-frameworks) |
| [iii](./iii.md) | agent-infrastructure | referenced by iii (agent-infrastructure) |
| [nemoclaw](./nemoclaw.md) | agent-infrastructure | referenced by nemoclaw (agent-infrastructure) |
| [xyops](../task-management/xyops.md) | task-management | referenced by xyops (task-management) |
