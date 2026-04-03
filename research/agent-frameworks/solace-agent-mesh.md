# Solace Agent Mesh

## Overview

Solace Agent Mesh (SAM) is an open-source framework for building event-driven, multi-agent AI systems where specialized agents collaborate to solve complex problems. The framework provides a standardized communication layer where AI agents can delegate tasks to peer agents, share data and artifacts, and connect with diverse user interfaces and external systems. It uses the event messaging of the Solace Platform for true scalability and reliability.

**Source**: README.md (<https://github.com/SolaceLabs/solace-agent-mesh>), accessed 2026-03-28

## Problem Addressed

Traditional multi-agent AI systems face challenges with coupling, scalability, and reliable communication between agents. Solace Agent Mesh solves this by providing an event-driven architecture that decouples agent logic from communication and orchestration. Agents can execute multi-step workflows with minimal coupling, allowing independent development, deployment, and scaling of agents without direct dependencies on their network location or implementation details.

**Source**: README.md and architecture.md (<https://github.com/SolaceLabs/solace-agent-mesh/docs/documentation/getting-started/architecture>), accessed 2026-03-28

## Key Statistics

- **License**: Apache 2.0
- **Python Support**: Python 3.10.16 – 3.13.x
- **Latest Update**: 2026-03-27
- **Primary Language**: Python
- **Package Manager**: PyPI (`solace-agent-mesh`)
- **Build System**: Hatchling

**Source**: pyproject.toml and LICENSE (<https://github.com/SolaceLabs/solace-agent-mesh>), accessed 2026-03-28

## Key Features

### Multi-Agent Event-Driven Architecture
Agents communicate via the Solace Event Mesh using an asynchronous, event-driven model. The Solace Event Broker serves as the central messaging fabric that routes Agent-to-Agent (A2A) protocol messages between components using a hierarchical topic structure, supporting patterns like request/reply, streaming updates, and publish/subscribe for agent discovery. This eliminates direct dependencies and enables horizontal scaling of Agent Hosts and Gateways.

**Source**: README.md (line 59) and architecture.md (lines 95-97), accessed 2026-03-28

### Agent Orchestration
Complex tasks are automatically broken down and delegated by the Orchestrator agent. The SamAgentComponent extracts scopes from incoming A2A messages and initiates ADK tasks. The ADK LlmAgent processes tasks using a before_model_callback that filters available tools based on user permission scopes before invoking the LLM.

**Source**: README.md (line 60) and architecture.md (lines 122-126), accessed 2026-03-28

### Flexible Interfaces
Gateways act as bridges between external systems and the agent mesh, handling protocol translation (HTTP, WebSockets, Slack RTM) into the standardized A2A protocol. The Gateway Development Kit (GDK) provides BaseGatewayApp and BaseGatewayComponent classes that abstract common gateway logic, including A2A protocol handling, agent discovery, and late-stage embed resolution. Integration options include REST API, web UI, Slack, or custom implementations.

**Source**: README.md (line 61) and architecture.md (lines 99-103), accessed 2026-03-28

### Extensibility
New agents, gateways, or services can be added with minimal code using a plugin architecture. The framework includes a plugin registry and automated tooling (sam plugin add, sam add agent --gui) to install existing plugins or create custom components.

**Source**: README.md (line 62) and quick-start guide, accessed 2026-03-28

### Agent-to-Agent Communication
Agents dynamically discover and delegate tasks to each other using the Agent-to-Agent (A2A) Protocol over Solace. Agent Hosts periodically publish AgentCards (JSON documents describing capabilities) to a well-known discovery topic. When Agent A delegates a subtask to Agent B, it constructs a new A2A task request that propagates the original user's permission scopes, maintaining security context throughout the delegation chain.

**Source**: README.md (line 63) and architecture.md (lines 128-145), accessed 2026-03-28

### Dynamic Embeds
Placeholder syntax allows responses to include dynamic content like real-time data, calculations, and file contents that are resolved with context-dependent information. The embed_resolving_mcp_toolset enables late-stage resolution of artifact_content embeds before forwarding responses to clients.

**Source**: README.md (line 64) and source code analysis, accessed 2026-03-28

### Built-In Tools
SAM provides built-in tools for artifact management, data analysis (SQL, JQ, and visualization), file operations, and image manipulation. These tools are available to agents and include automatic metadata injection for created artifacts.

**Source**: README.md and built-in-tools documentation, accessed 2026-03-28

## Technical Architecture

### Component Stack

Solace Agent Mesh provides a "Universal A2A Agent Host" built by integrating three primary technologies:

1. **Solace Event Broker**: Provides the messaging fabric for all asynchronous communication, utilizing topic-based routing for the A2A protocol. The broker ensures fault tolerance and guaranteed message delivery.

2. **Solace AI Connector (SAC)**: The runtime environment for hosting and managing the lifecycle of all system components. Handles broker connections, configuration loading (via YAML), and component lifecycle management. Specified version: `solace_ai_connector==3.3.4`

3. **Google Agent Development Kit (ADK)**: Provides the core logic for individual agents, including LLM interaction, tool execution, and state management. Specified version: `google-adk==1.18.0`

**Source**: README.md (line 46), architecture.md (lines 8-11, 139-150), and pyproject.toml (lines 24, 66), accessed 2026-03-28

### Architectural Principles

**Event-Driven Architecture (EDA)**: All interactions between major components are asynchronous and mediated by the Solace event broker. Components communicate through standardized A2A protocol messages, eliminating direct dependencies.

**Component Decoupling**: Gateways, Agent Hosts, and other services do not require knowledge of each other's network location, implementation language, or internal logic. Communication flows through the event mesh via a hierarchical topic structure.

**Scalability and Resilience**: The architecture supports horizontal scaling of Agent Hosts and Gateways. The Solace event broker provides fault tolerance and guaranteed message delivery, ensuring system resilience even if individual components fail or are restarted.

**Source**: architecture.md (lines 13-19), accessed 2026-03-28

### Key Components

**Agent Host (SamAgentApp)**: A SAC application that hosts a single ADK-based agent. It manages the lifecycle of the ADK Runner and LlmAgent, handles A2A protocol translation between incoming requests and ADK Task objects, enforces permission scopes by filtering available tools, and initializes ADK services like ArtifactService and MemoryService.

**Agent**: The logical entity within an Agent Host that performs tasks. Defined by configuration including instructions (persona and capabilities), LLM configuration (specifying which model to use), and a toolset containing built-in tools, custom Python functions, or MCP Toolsets.

**Gateways**: SAC applications that act as bridges between external systems and the agent mesh. They handle protocol translation, authenticate incoming requests, use a pluggable AuthorizationService to retrieve user permission scopes, manage external user sessions, and map them to A2A task lifecycles.

**A2A Protocol**: JSON-RPC 2.0 based protocol that defines message formats for all interactions between components. Communication is routed via a hierarchical topic structure on the Solace event broker.

**Source**: architecture.md (lines 99-150), accessed 2026-03-28

### Data Flow: User Task Processing

1. External client sends a request to a gateway
2. Gateway authenticates the request, retrieves permission scopes via its AuthorizationService, and translates it into an A2A task message, including scopes in Solace message user properties
3. Gateway publishes the message to the target agent's request topic on the Solace Broker
4. Agent Host receives the message; SamAgentComponent extracts the scopes and initiates an ADK task
5. ADK LlmAgent processes the task with a before_model_callback filtering available tools based on scopes before invoking the LLM
6. SamAgentComponent translates ADK events into A2A status and artifact update messages, publishing them to the originating gateway's status topic
7. Gateway receives streaming updates, performs late-stage processing (resolving artifact_content embeds), and forwards them to the client
8. Agent Host sends final A2A response message to the gateway, which delivers it to the client

**Source**: architecture.md (lines 115-127), accessed 2026-03-28

### Dependencies

Core dependencies include:
- `google-adk==1.18.0` — Agent runtime
- `a2a-sdk[http-server]==0.3.7` — A2A protocol implementation
- `solace_ai_connector==3.3.4` — SAC framework
- `pydantic==2.11.9` — Data validation
- `click==8.1.8` — CLI framework
- `fastapi==0.120.1` and `starlette==0.49.1` — Web server framework
- `pandas==2.3.2`, `numpy==2.2.6`, `plotly==6.3.0` — Data analysis and visualization
- `openai==1.99.9`, `google-genai==1.49.0`, `litellm==1.76.3` — LLM integrations
- `SQLAlchemy==2.0.40`, `alembic==1.16.5` — Database ORM and migrations
- `boto3==1.40.37`, `google-cloud-storage==3.9.0`, `azure-storage-blob==12.28.0` — Cloud storage integrations

**Source**: pyproject.toml (lines 23-92), accessed 2026-03-28

## Installation & Usage

### System Requirements

- **Python**: 3.10.16 through 3.13.x (not available for Python 3.10.0-3.10.15)
- **Package Manager**: pip
- **Operating System**: macOS, Linux, or Windows (with WSL)
- **LLM API Key**: Required for any major provider or custom endpoint

**Source**: README.md (lines 74-81), accessed 2026-03-28

### Quick Start (5 Minutes)

```bash
# 1. Create a directory for a new project
mkdir my-sam && cd my-sam

# 2. Create and activate a Python virtual environment
python3 -m venv .venv && source .venv/bin/activate

# 3. Install Solace Agent Mesh
pip3 install solace-agent-mesh

# 4. Initialize the new project via a GUI tool
sam init --gui
# Note: This initialization UI runs on port 5002

# 5. Run the project
sam run

# 6. Verify SAM is running
# Open the Web UI at http://localhost:8000 for the chat interface and ask a question
```

**Source**: README.md (lines 88-121), accessed 2026-03-28

### Adding New Agents

```bash
sam add agent --gui
```

**Source**: README.md (line 128), accessed 2026-03-28

### Installing Plugins

```bash
sam plugin add <your-component-name> --plugin <plugin-name>
```

**Source**: README.md (line 132), accessed 2026-03-28

### Running Tests

SAM uses pytest for testing and supports both hatch and direct pytest invocation:

```bash
# Using Hatch (recommended)
hatch test

# Using Pytest directly (requires pip install -e .[test])
pytest
```

**Source**: README.md (lines 193-217), accessed 2026-03-28

## Tutorials and Use Cases

The project provides hands-on tutorials for:

1. **Weather Agent** (~15 min) — Build an agent with real-time weather information
2. **SQL Database Integration** (~10–15 min) — Query a sample coffee company database
3. **MCP Integration** (~10–15 min) — Integrate Model Context Protocol (MCP) servers
4. **Slack Integration** (~20–30 min) — Chat with SAM directly from Slack
5. **Microsoft Teams Integration (Enterprise)** (~30–40 min) — Connect to Microsoft Teams with Azure AD authentication

**Source**: README.md (lines 164-172), accessed 2026-03-28

## Limitations and Caveats

1. **Version Upgrades Not Officially Supported**: "Optionally, you can try to upgrade versions but this action is not officially supported at this time." The recommended approach is to uninstall the earlier version and install from scratch.

2. **Python Version Constraints**: Requires Python 3.10.16 or higher and less than 3.14. Python 3.10.0-3.10.15 are not supported.

3. **Artifact Storage Limitations**: While the framework supports filesystem, S3, and Azure Blob Storage for artifacts, performance and scaling characteristics depend on the chosen storage backend.

4. **LLM Model Availability**: Functionality is constrained by available LLM models and API quotas from chosen providers (OpenAI, Google Vertex, etc.).

**Source**: README.md (line 105), pyproject.toml (line 10), and architecture documentation, accessed 2026-03-28

## Relevance to Claude Code Development

### Direct Applicability

1. **Multi-Agent Orchestration Pattern**: SAM demonstrates a production-grade pattern for agent-to-agent communication and task delegation that could inform multi-agent Claude Code workflows. The A2A protocol and permission scope propagation offer insights into secure peer-to-peer agent communication.

2. **Event-Driven Architecture**: The event broker pattern provides a model for decoupled, asynchronous agent coordination that scales beyond direct function calls. This could be leveraged for orchestrating multiple specialized Claude Code agents.

3. **Tool and Gateway Integration**: SAM's flexible gateway system for integrating external interfaces (REST, WebSockets, Slack) mirrors the extensibility requirements for Claude Code integrations with diverse platforms.

4. **MCP Integration**: SAM's support for Model Context Protocol (MCP) servers aligns directly with Claude Code's MCP ecosystem, demonstrating how to embed MCP toolsets into agent capabilities.

### Secondary Relevance

1. **Dynamic Content Resolution**: The dynamic embeds system (placeholder-based context resolution) could inform how Claude Code handles artifact generation and late-stage content substitution.

2. **Artifact Management**: SAM's built-in artifact service with metadata injection provides a reference model for structured artifact handling in multi-agent workflows.

3. **CLI-Driven Configuration**: The `sam init --gui` and `sam add agent --gui` patterns offer UX models for declarative agent configuration in Claude Code skill/plugin creation workflows.

**Source**: README.md, architecture.md, and tutorial documentation, accessed 2026-03-28

## References

- **Repository**: <https://github.com/SolaceLabs/solace-agent-mesh> (accessed 2026-03-28)
- **Documentation Site**: <https://solacelabs.github.io/solace-agent-mesh/> (referenced in README, accessed 2026-03-28)
- **PyPI**: <https://pypi.org/project/solace-agent-mesh> (referenced in README, accessed 2026-03-28)
- **Architecture Guide**: <https://solacelabs.github.io/solace-agent-mesh/docs/documentation/getting-started/architecture> (accessed 2026-03-28)
- **Source Code**: GitHub repository shallow clone to /tmp/.worktrees/solace-agent-mesh (accessed 2026-03-28)
- **License**: Apache 2.0 (<https://github.com/SolaceLabs/solace-agent-mesh/blob/main/LICENSE>, accessed 2026-03-28)

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Google Agent Development Kit (ADK)](./google-adk.md) | agent-frameworks | Core runtime dependency (google-adk==1.18.0 specified in pyproject.toml); ADK LlmAgent processes tasks with permission scope filtering |
| [AgentScope](./agentscope.md) | agent-frameworks | Peer multi-agent framework with A2A (Agent-to-Agent) protocol support; both enable decoupled inter-agent communication |
| [Ruflo](./ruflo.md) | agent-frameworks | Enterprise multi-agent orchestration with 215+ MCP tools; shares MCP ecosystem integration and swarm coordination patterns |
| [Micro-Agent](./micro-agent.md) | agent-frameworks | Lightweight Python agent framework with MCP multi-server support; same async streaming interface and ReAct agent pattern |
| [OpenFang](./openfang.md) | agent-frameworks | Rust-based Agent OS with 40 channel adapters and autonomous scheduling; parallels SAM's gateway-based architecture for external system integration |
| [LiteAgents](./liteagents.md) | agent-frameworks | Multi-agent toolkit with 11 specialized agents and orchestrator agent; shares task delegation and agent-to-agent workflow patterns |
| [CopilotKit](./copilotkit.md) | agent-frameworks | React frontend framework with AG-UI protocol for bi-directional agent-UI state sync; complements SAM's Gateway architecture for user interaction |
| [Plano](../agent-infrastructure/plano.md) | agent-infrastructure | AI-native proxy with unified agent orchestration and model routing; addresses similar infrastructure concerns for multi-agent coordination |

## Freshness Tracking

**Last Researched**: 2026-03-28
**Next Review**: 2026-06-28 (3 months)
**Repository Last Updated**: 2026-03-27

### Confidence Levels

- **Identity/Metadata**: high — Official pyproject.toml, README, and LICENSE files read in full
- **Key Features**: high — Extracted from README feature section and official architecture documentation
- **Technical Architecture**: high — Comprehensive architecture.md document read, core dependencies verified from pyproject.toml
- **Installation & Usage**: high — Quick start guide extracted verbatim from README with version verification
- **Limitations**: medium — Documented limitations extracted from README and pyproject.toml; performance characteristics inferred from architecture
- **Relevance to Claude Code**: medium — Based on alignment with Claude Code's multi-agent and MCP ecosystem; specific use case validation would require implementation experience

**Sources Inaccessible**: None — all primary sources successfully accessed and read.
