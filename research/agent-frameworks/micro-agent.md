---
name: Micro-Agent
description: Micro-Agent is a flexible, extensible Python agent framework designed to provide intelligent agent capabilities as a callable service layer for upstream applications. The "Micro" naming mirrors...
license: MIT
metadata:
  topic: micro-agent
  category: agent-frameworks
  source_url: https://github.com/fdueblab/Micro-Agent
  github: fdueblab/Micro-Agent
  version: "v1.0.0"
  verified: "2026-02-20"
  next_review: "2026-05-20"
---

## Overview

Micro-Agent is a flexible, extensible Python agent framework designed to provide intelligent agent capabilities as a callable service layer for upstream applications. The "Micro" naming mirrors microservices architecture: lightweight, modular components that expose a standardized async streaming interface. It implements the ReAct (Reasoning + Acting) pattern over an MCP tool ecosystem, with an integrated shell environment and web-based execution visualization.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Agents tightly coupled to specific tools or LLM providers | MCP protocol abstraction allows dynamic connection to multiple local (stdio) and remote (SSE) tool servers at runtime |
| No separation between agent logic and calling application | Standardized `run_agent(task_name, prompt)` async API isolates agent internals from upstream consumers |
| Agent execution is opaque and hard to debug | Execution records saved as JSON + auto-generated HTML visualization showing thought/action/result per step |
| Shell operations risk host system damage | Docker-first deployment with SSH access isolates agent shell execution in a container sandbox |
| Context window exhaustion in long-running agents | `TokenCounter` tracks cumulative input tokens against configurable `max_input_tokens` limit, raises `TokenLimitExceeded` before overflow |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 7 | 2026-02-20 |
| GitHub Forks | 9 | 2026-02-20 |
| Contributors | 3 | 2026-02-20 |
| Latest Release | No formal release (v1.0.0 in README badge) | 2026-02-20 |
| Open Issues | 0 | 2026-02-20 |
| Repo Created | 2025-03-25 | 2026-02-20 |
| Last Pushed | 2025-10-31 | 2026-02-20 |
| Primary Language | Python 3.12 | 2026-02-20 |

---

## Key Features

### ReAct Agent Architecture

- `BaseAgent` (Pydantic `BaseModel`) defines the step-based execution loop with state machine (`IDLE`, `RUNNING`, `FINISHED`, `ERROR`)
- `ReActAgent` extends `BaseAgent` with abstract `think()` and `act()` methods; each step returns a `Record` dict containing `thought`, `action`, `action_result`, and `token_usage`
- `max_steps` configurable (default 10 for base ReAct, 40 for `MCPAgent`); duplicate-response detection via `duplicate_threshold`
- `MCPAgent` extends `ToolCallAgent` and manages tool schema refresh every N steps (`_refresh_tools_interval = 5`)

### MCP Protocol Integration

- Connects to multiple MCP servers simultaneously via both SSE (HTTP/SSE for remote) and stdio (subprocess for local) transports
- Built-in MCP server (`app/mcp/server.py`) exposes: `bash`, `cmd` (Windows), `terminate`, `file_saver`, `json_saver`
- Additional built-in servers: `aml_server`, `deepseek_server`, `mysql_server`, `time_server`
- `config.json` declaratively lists external MCP server connections; auto-loaded at runtime by `MCPRunner`
- Tool list refreshed dynamically during agent runs to detect schema changes mid-task

### LLM Abstraction Layer

- Uses OpenAI-compatible API via `AsyncOpenAI`; supports any OpenAI-compatible endpoint including Claude models
- Explicitly supports reasoning models (`o1`, `o3-mini`) and multimodal models (`gpt-4o`, `claude-3-*` variants) with separate handling
- `TokenCounter` uses `tiktoken` for precise per-message token counting including image token estimation (low-detail: 85 tokens, high-detail tiles: 170 tokens each)
- Retry logic via `tenacity` with exponential backoff for `APIError`, `RateLimitError`
- Config loaded from TOML (`config/config.toml`) with per-model override support; singleton thread-safe `Config` class

### Execution Visualization

- Each agent run saves two artifacts to `visualization/`: `{task_name}_record.json` (structured execution log) and `{task_name}.html` (interactive HTML report)
- HTML report renders thought/action/result sequence for post-run inspection
- Web interface (`app.py`) on port 8010 using Flask + Flask-SocketIO + flask-restx

### Deployment

- Docker image based on `python:3.12-slim` with SSH server exposed on port 22 (agent shell execution isolation)
- Ports: 8010 (Web UI), 22 (SSH), 8000 (docs server)
- `docker-compose.yml` provided for single-command startup
- `meta_app.py` and `run_meta_app.py` provide a meta-agent mode for orchestrating multiple sub-agents

---

## Technical Architecture

<eg>
Upstream Application
        |
        v
  run_agent(task_name, prompt)  [main.py async entry point]
        |
        v
    MCPRunner
    - add_server() for each config.json entry + built-in server
        |
        v
    MCPAgent (ToolCallAgent -> ReActAgent -> BaseAgent)
    - state: IDLE -> RUNNING -> FINISHED/ERROR
    - max_steps: 40
    - loop: think() -> act() -> record step -> check duplicate/terminate
        |
     think()                    act()
    - LLM.ask() with tools      - Execute MCP tool call
    - Returns: should_act,      - Returns: tool result string
      thought, action,
      token_usage
        |
        v
    MCP Tool Ecosystem
    - stdio: local subprocess servers (built-in: bash, file_saver, json_saver, terminate)
    - SSE: remote HTTP servers (configured in config.json)
    - Tool schema refreshed every 5 steps
        |
        v
    Record Persistence
    - JSON execution log -> visualization/
    - HTML report generated from JSON
</eg>

The `app/` module hierarchy:

<eg>
app/
  agent/         # BaseAgent, ReActAgent, ToolCallAgent, MCPAgent, MetaApp agent
  llm.py         # AsyncOpenAI wrapper with TokenCounter and retry logic
  mcp/           # FastMCP-based built-in servers (bash, file tools, mysql, AML, time)
  prompt/        # System and next-step prompt templates for MCP agent
  schema.py      # Pydantic models: Message, Memory, Record, AgentState, TokenUsage
  config.py      # Singleton TOML config loader with per-model LLM settings
  tool/          # BaseTool + concrete tools: Bash, Cmd, Terminal, FileSaver, JsonSaver
  utils/         # Visualization HTML generator, record serializer
</eg>

---

## Installation & Usage

```bash
# Clone repository
git clone https://github.com/fdueblab/Micro-Agent
cd Micro-Agent

# Docker (recommended for shell isolation)
cp .env.example .env
cp config/config.example.toml config/config.toml
# Edit config.toml: set LLM model, base_url, api_key
docker-compose up -d
docker-compose exec micro_agent bash
python main.py

# Local (Python 3.12 via conda)
conda create -n micro-agent python=3.12
conda activate micro-agent
pip install -r requirements.txt
python main.py        # CLI agent run
python app.py         # Web UI on http://localhost:8010
```

Configuring external MCP servers in `config.json`:

```json
{
  "servers": [
    {
      "connection_type": "sse",
      "server_url": "http://your-mcp-server.com/sse",
      "server_id": "remote_tools"
    },
    {
      "connection_type": "stdio",
      "command": "python",
      "args": ["-m", "your_module.mcp_server"],
      "server_id": "local_tools"
    }
  ]
}
```

Invoking the agent programmatically:

```python
import asyncio
from main import run_agent

# task_name used for output filenames; prompt defines agent role and task
asyncio.run(
    run_agent(
        "code_analysis",
        """
You are a code analyst. Examine the project structure, identify main modules,
analyze dependencies, and generate a structured report.
""",
    )
)
# Output: visualization/code_analysis_record.json
#         visualization/code_analysis.html
```

---

## Relevance to Claude Code Development

### Applications

- Demonstrates a clean separation pattern between agent infrastructure and task-specific prompting: the `run_agent(task_name, prompt)` contract is directly applicable to how Claude Code could expose agent capabilities to orchestrators
- The `MCPAgent`'s multi-server connection management (simultaneous stdio + SSE) shows how to dynamically aggregate tools from heterogeneous MCP sources at runtime
- Token budget enforcement via `TokenLimitExceeded` exception prevents runaway API costs in long-running autonomous tasks

### Patterns Worth Adopting

- TOML-based LLM config with per-model overrides enables switching between Claude models (opus, sonnet, haiku) per agent role without code changes
- Step-level `Record` persistence (thought + action + action result + token usage) provides full audit trail for debugging agent failures
- Tool schema refresh every N steps compensates for dynamic MCP server state changes during long runs
- Duplicate-response detection (`duplicate_threshold`) prevents infinite loops when an agent repeatedly produces the same action

### Integration Opportunities

- The built-in MCP server (`FastMCP` wrapping `Bash`, `FileSaver`, `JsonSaver`) can be imported directly to extend Claude Code skill agents with shell execution capabilities
- The HTML visualization generator (`app/utils/visualize_record.py`) could be adapted for Claude Code skill audit reports
- `MCPRunner` multi-server aggregation pattern is directly applicable to Claude Code's MCP ecosystem management, particularly for routing tool calls across local and remote servers

---

## References

- [fdueblab/Micro-Agent GitHub Repository](https://github.com/fdueblab/Micro-Agent) (accessed 2026-02-20)
- [README.md - Micro-Agent](https://github.com/fdueblab/Micro-Agent/blob/master/README.md) (accessed 2026-02-20)
- [app/agent/react.py - ReActAgent implementation](https://github.com/fdueblab/Micro-Agent/blob/master/app/agent/react.py) (accessed 2026-02-20)
- [app/agent/mcp.py - MCPAgent implementation](https://github.com/fdueblab/Micro-Agent/blob/master/app/agent/mcp.py) (accessed 2026-02-20)
- [app/llm.py - LLM wrapper with TokenCounter](https://github.com/fdueblab/Micro-Agent/blob/master/app/llm.py) (accessed 2026-02-20)
- [app/mcp/server.py - Built-in MCP server](https://github.com/fdueblab/Micro-Agent/blob/master/app/mcp/server.py) (accessed 2026-02-20)
- [requirements.txt](https://github.com/fdueblab/Micro-Agent/blob/master/requirements.txt) (accessed 2026-02-20)
- [GitHub API - repos/fdueblab/Micro-Agent](https://api.github.com/repos/fdueblab/Micro-Agent) (accessed 2026-02-20)
