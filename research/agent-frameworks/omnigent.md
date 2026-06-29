# Omnigent

**Research Date**: 2026-06-18
**Source URL**: <https://github.com/omnigent-ai/omnigent>
**Version at Research**: 0.1.0
**License**: see repository

---

## Overview

Omnigent is an open-source **AI agent framework** and meta-harness that gives you a common orchestration layer over Claude Code, Codex, Cursor, Pi, and custom agents you write yourself. It enables you to swap or combine harnesses without rewriting, enforce policies and sandboxing, and collaborate in real time from any device.

**Source**: Omnigent README (accessed 2026-06-18)

Omnigent is authored by Databricks, Inc. and released as version 0.1.0 (currently in alpha status: Development Status :: 3 - Alpha).

**Source**: omnigent pyproject.toml (accessed 2026-06-18)

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| Latest Version | 0.1.0 | 2026-06-18 |
| Development Status | Alpha (Development Status :: 3 - Alpha) | 2026-06-18 |
| Python Requirement | 3.12+ | 2026-06-18 |
| Supported Harnesses | 4 (Claude Code, Codex, Pi, custom YAML agents) | 2026-06-18 |
| Built-in Policies | 4 (cost_budget, max_tool_calls_per_session, ask_on_os_tools, block_directory_change) | 2026-06-18 |
| GitHub Releases Published | 0 (install from git only) | 2026-06-18 |
| Author Organization | Databricks, Inc. | 2026-06-18 |

**Source**: omnigent pyproject.toml and GitHub releases API (accessed 2026-06-18)

## Problem Addressed

Most organizations managing AI agents face fragmentation: different harnesses (Claude Code, Codex, Cursor, Pi) require separate integration points, policies cannot be enforced uniformly, and teams cannot collaborate across devices or harnesses without rewriting orchestration logic. Omnigent solves this by providing a unified meta-harness layer that:

1. Abstracts multiple agent harnesses behind a consistent interface
2. Enables real-time multi-user collaboration from any device
3. Enforces declarative policies across all agents without harness-specific changes
4. Allows agents to interact and review each other's work in a single session

## Key Features

**Multi-agent orchestration**: "Supervise multiple agents. Use Claude Code, Codex, Pi, and custom agents (defined in YAML) together in the same session. Ask one agent to review another's work, or split a task across agents that are each good at different things."

**Source**: omnigent README (accessed 2026-06-18)

**Cross-device collaboration**: "Work with agents from any device, including your phone. Sessions follow you: start in your terminal, continue in the browser, pick it up on your phone. Messages, sub-agents, terminals, and files stay in sync."

**Source**: omnigent README (accessed 2026-06-18)

**Model flexibility**: "Use any model. A first-party API key, a Claude/ChatGPT subscription, or any compatible gateway. All first-class."

**Source**: omnigent README (accessed 2026-06-18)

**Multi-user support**: Omnigent supports multi-user accounts, controlled by one environment variable, enabling team-based workflows and shared sessions.

**Source**: omnigent README (accessed 2026-06-18)

**Declarative policy enforcement**: Policies are declarative gates that enforce rules on agent behavior. They evaluate agent actions at specific enforcement points and return one of three verdicts:
- **ALLOW** — the action proceeds
- **DENY** — the action is blocked; the agent receives an error
- **ASK** — the action is paused for user approval; approved becomes ALLOW, refused becomes DENY

Policies support three types: function-based (Python callables), conditional expressions (CEL), and declarative YAML configurations.

**Source**: omnigent POLICIES documentation (accessed 2026-06-18)

**Custom agent definition**: Users can define their own agents in YAML format and run them alongside built-in harnesses using `omnigent run path/to/agent.yaml`.

**Source**: omnigent README (accessed 2026-06-18)

## Technical Architecture

Omnigent's architecture is organized around three core layers:

1. **Harness abstractions** (`claude_native.py`, `codex_native.py`, `pi_native.py`): Native integrations with Claude Code, OpenAI Codex, and Pi. Each harness implements a bridge and forwarder pattern to map framework operations to harness-specific APIs.

2. **Runtime and policy engine** (`omnigent/runtime/`, `omnigent/policies/`): The runtime executes agents with support for policy enforcement at specific hooks (tool calls, shell commands, file operations, cost tracking). The policy engine evaluates declarative rules using function handlers, CEL expressions, or custom Python code.

3. **Server and persistence layer** (`omnigent/server/`, `omnigent/stores/`): A FastAPI server provides the web UI (ap-web), persistent session storage via SQLAlchemy ORM, and real-time message sync using WebSocket connections. Terminal management uses `pyte` (terminal emulator) for rendering and `pexpect` for subprocess control.

**Components**: `cli.py` (main entry point), `chat.py` (session/message logic), `claude_native_bridge.py` / `codex_native_forwarder.py` (harness routing), `policies/` (policy evaluation and builtins), `server/` (FastAPI app and WebSocket handlers), `stores/` (database schemas and session persistence).

**Data flow**: User CLI commands → CLI router → harness abstraction layer → native harness (Claude Code/Codex/Pi) or custom agent runner → policy engine (gate enforcement) → tool/shell/file execution → response routing back through harness bridge → WebSocket push to connected clients (browser/phone/other terminals).

**Source**: omnigent source tree examination (accessed 2026-06-18)

### Dependency Stack

**Core runtime**:
- `pyyaml>=6.0` — YAML parsing for agent definitions and policies
- `pydantic>=2.0` — data validation and serialization
- `sqlalchemy>=2.0` — ORM for session and conversation persistence
- `alembic>=1.0` — database migrations

**Server**:
- `fastapi>=0.100` — HTTP API and routing
- `starlette>=0.27` — ASGI server framework
- `uvicorn[standard]>=0.30` — ASGI server runtime
- `httpx>=0.27` — async HTTP client for agent API calls

**Model integration**:
- `openai>=1.0` — OpenAI API client (Codex, ChatGPT, gateways)
- `mcp>=1.0` — Model Context Protocol support for tool and resource sharing

**UI and interaction**:
- `rich>=14` — terminal UI, tables, syntax highlighting
- `prompt_toolkit>=3.0` — interactive terminal experience
- `pexpect>=4.9` — subprocess spawning and terminal control
- `pyte>=0.8` — terminal emulation for rendering shell output

**Policy and security**:
- `cel-expr-python>=0.1` — CEL (Common Expression Language) for side-effect-free policy evaluation
- `keyring>=24` — OS keychain integration for API key storage
- `tomlkit>=0.12` — TOML parsing with comment preservation

**Monitoring and telemetry**:
- `opentelemetry-exporter-otlp-proto-grpc>=1.20` — OTEL gRPC exporter
- `opentelemetry-instrumentation-fastapi` — FastAPI instrumentation
- `opentelemetry-instrumentation-httpx` — HTTP client instrumentation

**Source**: omnigent pyproject.toml lines 23–77 (accessed 2026-06-18)

## Installation & Usage

**System requirements**: Python 3.12 or higher.

"Omnigent needs **Python 3.12+**. Install the `omnigent` package: `uv tool install -q --python 3.12 git+https://github.com/omnigent-ai/omnigent.git`"

**Source**: omnigent README (accessed 2026-06-18)

**Initial setup**:

```bash
omnigent setup
```

On first run, Omnigent picks up model credentials already in your environment (ANTHROPIC_API_KEY, OPENAI_API_KEY, or a logged-in claude/codex CLI) and offers one as the default.

**Running agents**:

```bash
omnigent claude                      # Claude Code, in a session your team can join
omnigent codex                       # Codex
omnigent run path/to/agent.yaml      # your own agent
```

**Starting the server and web UI**:

```bash
omnigent server start                # start local server and web UI in background
omnigent host                        # (separate terminal) register this machine as a host
```

**Joining a session from another device**:

```bash
omnigent attach <session_id>
```

**Credential management**:

```bash
omnigent auth list                   # list configured credentials
omnigent auth set-default <agent> <cred>  # set default for an agent
omnigent auth remove <agent> <cred>  # remove a credential
```

Omnigent supports four credential types:
- Direct API keys (Anthropic, OpenAI)
- Claude/Codex CLI credentials (when logged in)
- Gateway credentials (custom base URL + key)
- Enterprise/SSO credentials (varies by deployment)

**Upgrading**:

```bash
omni upgrade            # detect install method, drain/stop local server, run matching upgrade
omni upgrade --check    # just report whether a newer release is available
```

**Source**: omnigent README and CLI help (accessed 2026-06-18)

### Custom Agent Definition (YAML)

Users define custom agents in YAML:

```yaml
name: my_agent
prompt: You are a helpful data analyst.
```

The agent can then be run with `omnigent run path/to/agent.yaml`.

**Source**: omnigent README (accessed 2026-06-18)

### Policy Configuration

Policies are defined in `server_config.yaml` (or programmatically) and evaluated at runtime:

```yaml
policies:
  approve_shell:
    type: function
    handler: omnigent.policies.builtins.safety.ask_on_os_tools   # ask before shell / file writes
  cap_calls:
    type: function
    handler: omnigent.policies.builtins.safety.max_tool_calls_per_session
    factory_params:
      limit: 50                    # cap how many tools one session can call
  budget:
    type: function
    handler: omnigent.policies.builtins.cost.cost_budget
    factory_params:
      max_cost_usd: 5.00           # hard spend cap...
      ask_thresholds_usd: [3.00]   # ...with a soft warning on the way
```

Built-in policies include:

- `cost_budget` — enforce per-session spend limits with warnings
- `max_tool_calls_per_session` — cap tool invocations
- `ask_on_os_tools` — require approval before shell/file operations
- `block_directory_change` — restrict directory navigation

**Source**: omnigent README and POLICIES.md (accessed 2026-06-18)

## Relevance to Claude Code Development

Omnigent is highly relevant to Claude Code and AI coding agents because:

1. **Harness abstraction**: It demonstrates how to build a meta-layer that abstracts multiple agent runtimes (Claude Code, Codex, Cursor, Pi) without duplicating orchestration logic. This is applicable when building systems that support multiple AI coding agents.

2. **Policy-based governance**: The declarative policy system (ALLOW/DENY/ASK) with support for function handlers, CEL expressions, and custom logic can inform how Claude Code could enforce safety guardrails, cost limits, or audit requirements in multi-agent or team environments.

3. **Cross-device session sync**: The architecture for synchronizing sessions, terminals, and files across devices (CLI, web, mobile) is relevant for building Claude Code integrations that work across multiple platforms.

4. **Real-time collaboration**: Multi-user accounts and shared sessions enable team workflows where agents can interact and review each other's work—a pattern that could enhance Claude Code's multi-agent capabilities.

5. **Custom agent authoring**: The YAML-based agent definition system shows a pattern for allowing users to extend Omnigent with custom agents, similar to how Claude Code could support user-defined agents or automation workflows.

6. **Model flexibility**: Support for Claude, OpenAI, and gateway-based models demonstrates how to maintain harness-agnostic APIs while still integrating multiple providers—relevant as Claude Code evolves to support more model options.

## Limitations and Caveats

1. **Early-stage (alpha)**: Omnigent is at Development Status :: 3 - Alpha. The API and behavior are subject to breaking changes, and production usage should be approached cautiously.

   **Source**: omnigent pyproject.toml (accessed 2026-06-18)

2. **Platform-specific constraints**: CEL policy evaluation is not available on Linux aarch64 or macOS x86_64 (Intel) due to missing wheel distributions. The policy module degrades gracefully when the library is absent, falling back to other evaluation methods.

   **Source**: omnigent pyproject.toml line 49 (accessed 2026-06-18)

3. **No official releases yet**: The latest release endpoint returns null, indicating that while version 0.1.0 exists, there are no GitHub Releases published yet. Installation requires installing from the git repository.

   **Source**: GitHub API query for omnigent/releases/latest (accessed 2026-06-18)

4. **Limited documentation of internal APIs**: While README and POLICIES.md cover main user workflows, detailed documentation of the harness bridge API, policy extension points, and custom agent runtime contracts is not evident in the reviewed sources. Users extending Omnigent with custom harnesses or policies may need to rely on source code inspection.

5. **Terminal UI limitations**: The terminal UI is built with `prompt_toolkit` and `rich`, which provide good interactivity but may not support all terminal capabilities or edge cases (e.g., complex ANSI sequences, non-standard terminals).

## References

- **GitHub repository**: <https://github.com/omnigent-ai/omnigent> (accessed 2026-06-18)
- **README**: <https://raw.githubusercontent.com/omnigent-ai/omnigent/main/README.md> (accessed 2026-06-18)
- **POLICIES documentation**: <https://raw.githubusercontent.com/omnigent-ai/omnigent/main/docs/POLICIES.md> (accessed 2026-06-18)
- **CONTRIBUTING guide**: <https://raw.githubusercontent.com/omnigent-ai/omnigent/main/CONTRIBUTING.md> (accessed 2026-06-18)
- **Source tree**: omnigent/ directory (accessed 2026-06-18)
- **Project metadata**: pyproject.toml, setup.py (accessed 2026-06-18)

## Freshness Tracking

**Last Verified**: 2026-06-18
**Version at Verification**: 0.1.0
**Next Review Recommended**: 2026-09-18

**Confidence summary**:
- **Identity/Metadata**: high — version, authorship, Python requirements extracted from official pyproject.toml
- **Features**: high — all features verified against README and POLICIES.md with exact quotes
- **Architecture**: high — component names and data flow verified via source tree inspection; dependencies verified from pyproject.toml
- **Usage Examples**: high — commands and YAML examples extracted verbatim from README
- **Limitations**: medium — early-stage status confirmed from classifiers; platform constraints from pyproject.toml; lack of official GitHub Releases from API query; internal API documentation limitations inferred from source review but not explicitly stated in docs

**Changes since last research**: Initial entry created.

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Claude Code Harness](./claude-code-harness.md) | agent-frameworks | Go-native guardrail engine alternative to Omnigent's declarative policy system; both enforce ALLOW/DENY decision gates on tool execution |
| [Everything Claude Code](./everything-claude-code.md) | agent-frameworks | Similar multi-agent harness scope: 16 agents + 65+ skills vs. Omnigent's unified interface; both address Claude Code orchestration and cross-platform consistency |
| [TAKT](../research-agent-patterns/takt.md) | research-agent-patterns | YAML-defined multi-agent state machine overlaps with Omnigent's declarative policy approach; both route agents through plan→work→review→release cycles |
| [gstack](./gstack.md) | agent-frameworks | Role-specific cognitive switching for Claude Code similar to Omnigent's multi-harness support; both enable agent personas to vary by task phase |
| [Trellis](./Trellis.md) | agent-frameworks | Multi-platform AI coding framework abstracting Claude Code, Cursor, OpenCode—shares Omnigent's core goal of unified harness abstraction across tools |
| [AutoResearchClaw](./AutoResearchClaw.md) | agent-frameworks | 23-stage multi-agent research pipeline demonstrates advanced Omnigent use case: orchestrating parallel agents with policy gates and self-healing execution |
| [Google ADK](./google-adk.md) | agent-frameworks | Python multi-agent framework with sub_agents hierarchy and LLM-driven routing; alternative approach to Omnigent's unified policy-based orchestration layer |
| [Agno](./agno.md) | agent-frameworks | Stateful multi-agent system with persistent user profiles; complementary to Omnigent's cross-device session sync and real-time collaboration model |
