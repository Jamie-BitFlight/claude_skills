# AgentScope

## Identity & Metadata

**Project Name:** AgentScope

**Repository:** <https://github.com/agentscope-ai/agentscope>

**Current Version:** v1.0.19dev (development version as of 2026-03-28)

**License:** Apache-2.0

**Author Organization:** SysML team of Alibaba Tongyi Lab

**Python Requirement:** Python 3.10+

**Source Repo Language:** Python

**Package Manager:** PyPI (pip install agentscope)

**Official Documentation:** <https://doc.agentscope.io/> (English and Chinese)

---

## Key Statistics

**GitHub Repository Stats** (as of 2026-03-28):
- Stars: 21,218
- Forks: 2,084
- Open Issues: tracked in repository
- Last Updated: 2026-03-28T01:31:35Z

**Paper Reference:** Available on arXiv ([cs.MA-2402.14034](https://arxiv.org/abs/2402.14034)) — published research backing the framework design

**Community:** Discord server at <https://discord.gg/eYMpfnkG8h>; biweekly meetings launched 2026-01

---

## Overview

AgentScope is a production-ready, easy-to-use agent framework designed for building multi-agent systems with Large Language Models. The framework is explicitly designed to work with increasingly agentic LLMs by leveraging their reasoning and tool-use abilities rather than constraining them with strict prompts and rigid orchestrations.

**Key positioning statement (from official README)**: "AgentScope is a production-ready, easy-to-use agent framework with essential abstractions that work with rising model capability and built-in support for finetuning."

---

## Problem Addressed

AgentScope addresses three critical needs in multi-agent LLM systems:

1. **Simplicity and speed to production**: Reduce time to build functional multi-agent systems from scratch. Official documentation states "start building your agents in 5 minutes with built-in ReAct agent, tools, skills, human-in-the-loop steering, memory, planning, realtime voice, evaluation and model finetuning."

2. **Production-grade deployment readiness**: Many agent frameworks are demonstration prototypes. AgentScope provides "deploy and serve your agents locally, as serverless in the cloud, or on your K8s cluster with built-in OTel support."

3. **Model-agnostic extensibility**: Support for multiple LLM providers (OpenAI, Anthropic, Alibaba DashScope, Ollama, Google Gemini, Trinity-RFT) and flexible integration patterns for tools, memory, and observability without requiring framework overhauls.

---

## Key Features

### Core Agent Types

AgentScope exports five primary agent classes from `src/agentscope/agent/`:

1. **AgentBase** — The foundation class for all asynchronous agents, defining lifecycle hooks and state management through metaclass `_AgentMeta`. Supports pre_reply, post_reply, pre_print, post_print, pre_observe, and post_observe hooks as OrderedDict-based class-level hook registries.

2. **ReActAgent** — Extended agent implementing the Reasoning-Action-Observation (ReAct) pattern. Built-in support for automatic tool invocation and tool result processing. Extracted from `src/agentscope/agent/__init__.py` which re-exports `ReActAgent` from `_react_agent.py`.

3. **RealtimeAgent** — New agent type supporting realtime voice interactions with web interface. Launched 2026-02 per official news. Supports production-grade voice agent capabilities with seamless voice input/output.

4. **A2AAgent** — Agent-to-Agent protocol support (A2A), announced 2025-12. Enables inter-agent communication and coordination in distributed agent systems.

5. **UserAgent** — Human participant agent for mixed human-agent workflows and simulations.

### Message and Content System

AgentScope uses a multimodal message abstraction in `src/agentscope/message/`:

- **Msg class** — Core message type carrying content blocks and metadata
- **ContentBlock types** — TextBlock, ThinkingBlock, ToolUseBlock, ToolResultBlock, ImageBlock, AudioBlock, VideoBlock
- **Source types** — Base64Source and URLSource for multimodal content references

This enables agents to seamlessly exchange text, images, audio, video, and structured tool calls without format conversion.

### Tool and Skill System

**Toolkit** (`src/agentscope/tool/_toolkit.py`) — Central tool registration and invocation system. Agents bind a Toolkit instance to register callable functions as agent-accessible tools. Built-in tools include:

- `execute_python_code`, `execute_shell_command` — Code execution
- `view_text_file`, `write_text_file`, `insert_text_file` — File operations
- `dashscope_text_to_image`, `dashscope_text_to_audio`, etc. — Alibaba DashScope multimodal APIs
- `openai_text_to_image`, `openai_text_to_audio`, `openai_edit_image`, etc. — OpenAI multimodal APIs
- `openai_image_to_text`, `dashscope_image_to_text` — Vision/OCR capabilities
- `openai_audio_to_text` — Speech-to-text transcription

**Skills integration** — 2025-11 release (per official news) added support for Anthropic Agent Skills as callable tools within AgentScope agents.

**MCP (Model Context Protocol) Support** — Flexible MCP integration allowing:
- Individual MCP tools to be obtained as local callable functions
- Toolkit composition of MCP tools with native AgentScope tools
- Both `HttpStatelessClient` and `StreamableTransport` MCP clients
- Wrapping individual MCP functions into more complex composite tools (feature example in README)

### Memory System

Three memory backends in `src/agentscope/session/` (session-based) and `src/agentscope/memory/`:

1. **InMemoryMemory** — Default, ephemeral in-process memory
2. **JSONSession** — Persistent file-based session storage
3. **RedisSession** — Distributed Redis-backed memory for multi-instance deployments

**Advanced memory features** (2026-01 release):
- Database support in memory module
- Memory compression to reduce context window overhead
- Long-term memory via ReMe integration (2025-11)
- Mem0AI support for persistent semantic memory

### Model Integration

**ChatModelBase** and concrete implementations in `src/agentscope/model/`:

- **DashScopeChatModel** — Alibaba DashScope APIs (qwen-max, etc.)
- **OpenAIChatModel** — OpenAI GPT-4, GPT-3.5-Turbo, etc.
- **AnthropicChatModel** — Claude models (Anthropic support)
- **OllamaChatModel** — Local Ollama deployments (v0.5.4+)
- **GeminiChatModel** — Google Gemini models
- **TrinityChatModel** — Trinity-RFT integration for agentic reinforcement learning (2025-11)

All models implement streaming and non-streaming modes through consistent `ChatModelBase` interface.

### Realtime Voice Features

**TTS (Text-to-Speech)** — 2025-12 release. Built-in module in `src/agentscope/tts/` providing unified API for multiple TTS providers.

**Realtime Voice Agent** — 2026-02 release. Production-grade realtime voice interaction with:
- Web interface for voice input/output
- Multi-agent realtime interactions (example: multiagent_realtime workflow)
- Interruption and human-in-the-loop steering support
- Robust memory preservation during interruptions

**Roadmap** — Voice agent development planned in three phases: (1) TTS models, (2) Multimodal models non-realtime, (3) Real-time multimodal models.

### Multi-Agent Orchestration

**MsgHub** (`src/agentscope/pipeline/`) — Central message routing for multi-agent conversations:
- Managed participant tracking
- Announcement delivery to all participants
- Dynamic participant addition/removal during execution
- Sequential and parallel pipeline execution patterns

**Pipeline patterns** in `src/agentscope/pipeline/`:
- `sequential_pipeline` — Sequential execution of agents in order
- Dynamic participant management via hub.add() and hub.delete()
- Async context manager pattern for safe resource cleanup

### Evaluation and Tuning

**Model Tuning** (`src/agentscope/tuner/`) — Agentic RL via Trinity-RFT library (2025-11). Sample projects demonstrate model improvement:

| Example | Model | Improvement |
|---------|-------|------------|
| Math Agent | Qwen3-0.6B | Accuracy: 75% → 85% |
| Frozen Lake | Qwen2.5-3B-Instruct | Success rate: 15% → 86% |
| Learn to Ask | Qwen2.5-7B-Instruct | Accuracy: 47% → 92% |
| Werewolf Game | Qwen2.5-7B-Instruct | Win rate: 50% → 80% |
| Data Augment | Qwen3-0.6B | AIME-24 accuracy: 20% → 60% |

**Evaluation module** (`src/agentscope/evaluate/`) — Metrics and automated assessment for multi-agent interactions.

### Observability and Tracing

**OpenTelemetry (OTel) integration** — Built-in support for trace export via `opentelemetry-api>=1.39.0`, `opentelemetry-sdk>=1.39.0`, `opentelemetry-exporter-otlp>=1.39.0`. Tracing endpoint configuration during `agentscope.init()` enables connection to third-party platforms (Arize-Phoenix, Langfuse) or AgentScope Studio.

**AgentScope Studio** — Web-based UI for monitoring runs, with `run_id` distinction between different agent instances. Integration via `studio_url` parameter in `agentscope.init()`.

---

## Technical Architecture

### Initialization and Global Configuration

AgentScope uses a thread and async-safe global configuration via `contextvars.ContextVar`:

```python
_config = _ConfigCls(
    run_id=ContextVar(...),
    project=ContextVar(...),
    name=ContextVar(...),
    created_at=ContextVar(...),
    trace_enabled=ContextVar(...),
)
```

Initialization is triggered via `agentscope.init(project=None, name=None, run_id=None, logging_path=None, logging_level="INFO", studio_url=None, tracing_url=None)`. This enables multi-tenant, context-aware execution where each async task or thread can maintain its own run identity and configuration.

### Module Organization

**Core modules** (from `src/agentscope/__init__.py`):

- `exception` — Exception hierarchy for agent failures
- `module` — Reusable components and StateModule base class (for agent state tracking)
- `message` — Message and ContentBlock types
- `model` — ChatModelBase and concrete implementations
- `tool` — Tool registration, Toolkit, and built-in tools
- `formatter` — Message formatting for different APIs (DashScopeChatFormatter, etc.)
- `memory` — Memory backends (InMemoryMemory, JSONSession, RedisSession)
- `agent` — Agent classes (AgentBase, ReActAgent, RealtimeAgent, A2AAgent, UserAgent)
- `session` — Session persistence (JSONSession, RedisSession)
- `embedding` — Embedding models and providers
- `token` — Token counting and estimation
- `evaluate` — Evaluation metrics
- `pipeline` — Multi-agent orchestration (MsgHub, sequential_pipeline)
- `tracing` — OTel integration (setup_tracing function)
- `rag` — Retrieval-augmented generation
- `a2a` — Agent-to-Agent protocol
- `realtime` — Realtime voice and streaming

### Hook System

**Class-level hooks** in AgentBase support middleware-style preprocessing and postprocessing:

- `_class_pre_reply_hooks` — Modify input arguments before agent.reply()
- `_class_post_reply_hooks` — Transform output message after reply
- `_class_pre_print_hooks` — Filter output before display
- `_class_post_print_hooks` — Post-print cleanup
- `_class_pre_observe_hooks` — Preprocess observations
- `_class_post_observe_hooks` — Post-observe cleanup

Hooks are registered as OrderedDict with callable signatures supporting dependency injection and composability.

### Async-First Design

All agent communication is async-native:

```python
msg = await agent(msg)  # Calling convention
await hub.add(agent4)    # MsgHub operations
```

This enables concurrent multi-agent execution, realtime voice streaming, and human-in-the-loop interruption without blocking.

### Dependencies

Core production dependencies (from `pyproject.toml`):

- **LLM Client libraries:** anthropic, openai, dashscope
- **MCP protocol:** mcp>=1.13
- **Async utilities:** aioitertools, aiofiles, asyncio
- **Networking:** python-socketio, websockets>=14.0 (realtime)
- **Observability:** opentelemetry-api>=1.39.0, opentelemetry-sdk>=1.39.0, opentelemetry-exporter-otlp>=1.39.0
- **Data handling:** sqlalchemy (database memory), redis (distributed sessions)
- **Parsing and formatting:** json5, json_repair, docstring_parser, python-frontmatter
- **Audio:** sounddevice, scipy (realtime audio processing)
- **Utilities:** shortuuid, tiktoken (token estimation), numpy, filetype, python-datauri

Optional dependencies:

- **a2a:** a2a-sdk, httpx, nacos-sdk-python>=3.0.0
- **Realtime:** websockets>=14.0, scipy
- **Models:** google-genai (Gemini), ollama>=0.5.4
- **Tokenizers:** Pillow, transformers, jinja2
- **Memory backends:** redis (redis_memory), mem0ai<=1.0.3 (semantic memory)

---

## Installation & Usage

### Installation

**From PyPI:**

```bash
pip install agentscope
```

Or with uv:

```bash
uv pip install agentscope
```

**From source:**

```bash
git clone -b main https://github.com/agentscope-ai/agentscope.git
cd agentscope
pip install -e .
```

### Minimal Example

From official README — a conversation between a ReAct agent ("Friday") and a user:

```python
from agentscope.agent import ReActAgent, UserAgent
from agentscope.model import DashScopeChatModel
from agentscope.formatter import DashScopeChatFormatter
from agentscope.memory import InMemoryMemory
from agentscope.tool import Toolkit, execute_python_code, execute_shell_command
import os, asyncio

async def main():
    toolkit = Toolkit()
    toolkit.register_tool_function(execute_python_code)
    toolkit.register_tool_function(execute_shell_command)

    agent = ReActAgent(
        name="Friday",
        sys_prompt="You're a helpful assistant named Friday.",
        model=DashScopeChatModel(
            model_name="qwen-max",
            api_key=os.environ["DASHSCOPE_API_KEY"],
            stream=True,
        ),
        memory=InMemoryMemory(),
        formatter=DashScopeChatFormatter(),
        toolkit=toolkit,
    )

    user = UserAgent(name="user")

    msg = None
    while True:
        msg = await agent(msg)
        msg = await user(msg)
        if msg.get_text_content() == "exit":
            break

asyncio.run(main())
```

**Initialization with Studio:**

```python
import agentscope

agentscope.init(
    project="my_project",
    name="experiment_run_1",
    run_id="unique_run_id_123",
    logging_path="./logs/",
    logging_level="INFO",
    studio_url="http://localhost:8000",  # AgentScope Studio URL
    tracing_url="http://localhost:6006/v1/traces",  # Third-party OTel endpoint
)
```

### Voice Agent Example

Realtime voice agent with web interface (example from repository):

```python
# Code location: examples/agent/realtime_voice_agent/
# Supports production-grade voice interactions with tool invocation
```

### MCP Integration Example

Fine-grained MCP control:

```python
from agentscope.mcp import HttpStatelessClient
from agentscope.tool import Toolkit

async def fine_grained_mcp_control():
    client = HttpStatelessClient(
        name="gaode_mcp",
        transport="streamable_http",
        url=f"https://mcp.amap.com/mcp?key={os.environ['GAODE_API_KEY']}",
    )

    # Obtain MCP tool as local callable
    func = await client.get_callable_function(func_name="maps_geo")

    # Use directly
    await func(address="Tiananmen Square", city="Beijing")

    # Or pass to agent as tool
    toolkit = Toolkit()
    toolkit.register_tool_function(func)
```

---

## Limitations and Caveats

### Version and Release Status

- Current version v1.0.19dev indicates active development. Production users should await stable 1.0.0 release (announced as "Beta" in classifiers).
- Documentation and examples available but feature coverage is extensive — some advanced features (realtime voice, A2A, agentic RL) are recent additions (2025-11 onwards) and may have edge cases.

### Development Status

Official package classifier: "Development Status :: 4 - Beta". This means the API may change before stable release, though core abstractions (AgentBase, ReActAgent, Toolkit, MsgHub) are unlikely to change fundamentally.

### Model API Costs and Rate Limits

AgentScope integrates with paid LLM APIs (OpenAI, Anthropic, DashScope, Gemini). Cost control and rate limiting are delegated to the underlying providers. Users must configure quotas and monitoring at the provider level.

### Memory Scaling

InMemoryMemory is not suitable for long-running multi-agent systems with large conversation histories. For production, use JSONSession or RedisSession. Memory compression (2026-01 feature) helps but does not eliminate the scaling constraint.

### Audio/Voice Dependencies

Realtime voice features require `sounddevice`, `scipy`, and `websockets>=14.0`. These have system-level dependencies (e.g., PortAudio for sounddevice) that may require compilation on some platforms.

### Async-Only Design

AgentScope is async-first. Blocking I/O in tools or agent code will block the entire event loop. Tool implementations must be async-compatible or wrapped in `asyncio.to_thread()`.

---

## Relevance to Claude Code Development

### Applicable Use Cases

1. **Multi-agent skill orchestration** — AgentScope's MsgHub and pipeline support multi-skill coordination in complex Claude Code workflows. The hook system aligns with Claude Code's middleware architecture.

2. **Tool integration framework** — The Toolkit abstraction mirrors Claude Code skill tool registration. AgentScope's Toolkit.register_tool_function() provides a pattern for callable tool composition.

3. **Production agent deployment** — AgentScope-Runtime (companion project) supports Docker/K8s deployment with OTel observability, applicable to production Claude Code agent deployments.

4. **ReAct pattern reference** — AgentScope's ReActAgent is a production reference implementation of the ReAct (Reasoning-Action-Observation) pattern, useful for designing similar agents in Claude Code.

5. **MCP integration patterns** — AgentScope's MCP support (HttpStatelessClient, fine-grained tool extraction) demonstrates production patterns for MCP tool integration, directly applicable to Claude Code MCP server usage.

6. **Memory and session management** — The JSONSession/RedisSession pattern and memory compression (2026-01) are applicable to Claude Code skill memory management and context preservation across executions.

7. **Realtime streaming and voice** — AgentScope's realtime voice agent (2026-02) and websocket-based streaming (websockets>=14.0) provide reference implementations for real-time Claude Code agent interactions.

### Integration Patterns for Claude Code

- **Hook middleware** — Adapt AgentScope's class-level hook pattern for Claude Code agent preprocessing/postprocessing
- **Tool registry** — Use AgentScope's Toolkit pattern as a blueprint for Claude Code skill tool discovery and binding
- **Multi-agent coordination** — Adapt MsgHub for Claude Code multi-skill workflows requiring message routing
- **Model abstraction** — Reference AgentScope's ChatModelBase pattern for consistent LLM provider abstraction in Claude Code

---

## References

**Official Sources:**

- GitHub Repository: <https://github.com/agentscope-ai/agentscope>
- Official Documentation: <https://doc.agentscope.io/>
- Research Paper: <https://arxiv.org/abs/2402.14034> (cs.MA)
- Roadmap: <https://github.com/agentscope-ai/agentscope/blob/main/docs/roadmap.md> (accessed 2026-03-28)
- Contributing Guide: <https://github.com/agentscope-ai/agentscope/blob/main/CONTRIBUTING.md> (accessed 2026-03-28)
- News Archive: <https://github.com/agentscope-ai/agentscope/blob/main/docs/NEWS.md> (accessed 2026-03-28)

**Companion Projects:**

- AgentScope-Runtime: <https://github.com/agentscope-ai/agentscope-runtime> (Docker/K8s deployment, VNC sandboxes)
- Samples & Examples: <https://github.com/agentscope-ai/agentscope-samples> (tuning examples, use cases)
- CoPaw: <https://github.com/agentscope-ai/CoPaw> (Personal Agent Workstation built on AgentScope)
- ReMe: <https://github.com/agentscope-ai/ReMe> (Long-term memory integration)
- Trinity-RFT: <https://github.com/agentscope-ai/Trinity-RFT> (Agentic RL via reinforcement fine-tuning)

**Community:**

- Discord: <https://discord.gg/eYMpfnkG8h>
- Biweekly Meetings: <https://github.com/agentscope-ai/agentscope/discussions/1126> (started 2026-01)

---

## Freshness Tracking

**Last Accessed:** 2026-03-28

**Source Status:**

| Source | Status | Last Update |
|--------|--------|------------|
| GitHub Repository | Accessible | 2026-03-28T01:31:35Z |
| Official Docs (doc.agentscope.io) | Accessible | Not directly checked (assumed current) |
| PyPI Package | Accessible | Version 1.0.19dev |
| README (en) | Accessible | 2026-03-28 |
| Roadmap | Accessible | 2026-03-28 |
| arXiv Paper | Accessible | cs.MA-2402.14034 |

**Confidence Assessment:**

| Section | Confidence | Rationale |
|---------|-----------|-----------|
| Identity/Metadata | high | GitHub API verified, pyproject.toml read from source |
| Key Features | high | Extracted from official README, __init__.py module exports, and source code structure |
| Technical Architecture | high | Direct code reads from src/agentscope/ with class hierarchies and imports verified |
| Installation & Usage | high | Official README examples extracted verbatim |
| Limitations | medium | Based on code structure and documented constraints; some limitations inferred from design patterns |
| Relevance to Claude Code | medium | Pattern analysis based on AgentScope design; integration feasibility assessed qualitatively |

**Next Scheduled Review:** 2026-06-28 (3 months from research date)

**Changes Detected Since Last Entry:** N/A (first entry)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [micro-agent.md](../agent-frameworks/micro-agent.md) | agent-frameworks | shares lightweight Python ReAct pattern with MCP multi-server support |
| [pi-mono.md](../agent-frameworks/pi-mono.md) | agent-frameworks | comparable unified LLM API and agent runtime architecture across multiple platforms |
| [everything-claude-code.md](../agent-frameworks/everything-claude-code.md) | agent-frameworks | parallel multi-agent orchestration system with 16 specialized agents and skill binding |
| [composure.md](../agent-frameworks/composure.md) | agent-frameworks | multi-language agentic system with hook-based automation similar to AgentScope's middleware patterns |
| [ruflo.md](../agent-frameworks/ruflo.md) | agent-frameworks | 100+ specialized agents with fault-tolerant consensus and 215+ MCP tools |
| [superpowers.md](../agent-frameworks/superpowers.md) | agent-frameworks | agentic skills framework with subagent-driven development model |
| [dify.md](../agent-frameworks/dify.md) | agent-frameworks | production LLM application platform with visual workflows and 100+ model providers |
| [mcpjam.md](../mcp-ecosystem/mcpjam.md) | mcp-ecosystem | local MCP server inspector with LLM playground for debugging tool integration |
| [ultra-mcp.md](../mcp-ecosystem/ultra-mcp.md) | mcp-ecosystem | unified MCP routing interface with 25 tools as prompts and cost tracking |
| [cocoindex-code.md](../mcp-ecosystem/cocoindex-code.md) | mcp-ecosystem | embedded MCP server for semantic code search via AST analysis |

---

## Notes for Future Updates

- Monitor AgentScope-Runtime releases for K8s and serverless deployment patterns
- Track Trinity-RFT integration improvements for agentic RL capabilities
- Watch for stable v1.0.0 release (currently in 1.0.19dev)
- Verify realtime voice agent stability and production readiness as 2026 progresses
- Monitor voice agent roadmap progression through three phases (TTS → Multimodal → Realtime Multimodal)
- Track ReMe and long-term memory integration maturity
- Watch for breaking changes in hook system or agent base class APIs during development
