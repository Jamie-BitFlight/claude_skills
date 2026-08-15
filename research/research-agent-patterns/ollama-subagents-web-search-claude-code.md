---
name: Ollama Subagents and Web Search in Claude Code
description: Ollama v0.16.2 adds native subagent support and built-in web search to Claude Code without requiring MCP servers or external API keys. Subagents run parallel tasks (file search, code exploration,...
license: MIT
metadata:
  topic: ollama-subagents-web-search-claude-code
  category: research-agent-patterns
  source_url: https://ollama.com/blog/web-search-subagents-claude-code
  github: ollama/ollama
  version: "v0.16.2"
  verified: "2026-02-19"
  next_review: "2026-05-19"
---

## Overview

Ollama v0.16.2 adds native subagent support and built-in web search to Claude Code without requiring MCP servers or external API keys. Subagents run parallel tasks (file search, code exploration, research) in isolated context windows, preventing long coding sessions from accumulating noise. Web search is integrated directly into Ollama's Anthropic compatibility layer, so any model connecting via that layer can retrieve live web data.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Long Claude Code sessions accumulate context noise from side tasks | Subagents run each task in its own isolated context, keeping primary session clean |
| Web search requires MCP server setup and external API key management | Ollama's Anthropic compatibility layer handles web search natively with no additional config |
| Parallel research tasks execute serially, slowing complex workflows | Subagents execute file search, code exploration, and research in parallel simultaneously |
| Using Claude Code with open models requires manual env var configuration | `ollama launch claude` performs zero-config setup with model selection guidance |
| Models lack access to current information beyond training cutoff | Built-in web search returns live results that models can incorporate into responses |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 162,863 | 2026-02-19 |
| GitHub Forks | 14,610 | 2026-02-19 |
| Contributors | 587 | 2026-02-19 |
| Latest Release | v0.16.2 | 2026-02-19 |
| Open Issues | 2,434 | 2026-02-19 |
| Primary Language | Go | 2026-02-19 |

---

## Key Features

### Subagent Execution

- Subagents run tasks in parallel in isolated context windows, preventing context bleed between tasks
- Some models trigger subagents automatically: `minimax-m2.5`, `glm-5`, `kimi-k2.5`
- Manual triggering via natural language: "use/spawn/create subagents"
- Each subagent context is independent, so long coding sessions stay productive
- Supports compound research patterns: e.g., spawn 3 agents to research competitor pricing in parallel

### Built-in Web Search

- Integrated into Ollama's Anthropic API compatibility layer (no MCP, no additional config)
- Free tier for individuals via `OLLAMA_API_KEY`; higher rate limits via Ollama's cloud
- REST API endpoint: `POST https://ollama.com/api/web_search` with bearer auth
- Python library: `ollama.web_search(query)` (requires `ollama>=0.6.0`)
- JavaScript library: `client.webSearch({ query })` (requires `ollama@>=0.6.0`)
- Subagents can use web search to research topics in parallel and return actionable results
- Also supports `web_fetch` for fetching specific URLs as tool calls

### Zero-Config Claude Code Launch (`ollama launch`)

- Single command `ollama launch claude` sets up Claude Code with local or cloud Ollama models
- No environment variables or config files required
- Guides user through model selection interactively
- Supports local models (glm-4.7-flash, qwen3-coder, gpt-oss:20b) and cloud models
- Recommended: at least 64,000-token context length for coding sessions
- 5-hour coding session window on Ollama cloud; extended usage at free tier

### Anthropic API Compatibility Layer

- Ollama v0.14.0+ implements the Anthropic Messages API
- Drop-in replacement: set `ANTHROPIC_BASE_URL=http://localhost:11434`, `ANTHROPIC_AUTH_TOKEN=ollama`
- Supported features: messages, multi-turn, streaming, system prompts, tool calling, extended thinking, vision
- Enables Claude Code, Anthropic SDK, and any Anthropic-compatible tooling to use local or cloud Ollama models

### Recommended Cloud Models for Subagent/Search Workflows

- `minimax-m2.5:cloud` -- naturally triggers subagents
- `glm-5:cloud` -- naturally triggers subagents
- `kimi-k2.5:cloud` -- naturally triggers subagents

---

## Technical Architecture

<eg>
Claude Code CLI
    |
    | ANTHROPIC_BASE_URL=http://localhost:11434
    v
Ollama Anthropic Compatibility Layer (v0.14.0+)
    |-- Translates Anthropic Messages API -> Ollama internal format
    |-- Injects web_search tool calls when model requests web data
    |-- Routes subagent spawning to parallel context managers
    |
    +--> Local model inference (Go runtime, GGUF/MLX/CUDA)
    |
    +--> Ollama Cloud (cloud model tier, full context, 5-hour sessions)
    |
    +--> Web Search API (https://ollama.com/api/web_search)
             Returns: [{title, url, content}, ...]
</eg>

Subagent execution model: each subagent is an independent inference context. The orchestrator model (in Claude Code's primary session) spawns agents by issuing tool calls or natural language directives. Each subagent runs in isolation, preventing the orchestrator context from accumulating the subagent's working memory. Results are returned to the orchestrator as tool outputs.

Web search injection: when a model issues a `web_search` or `web_fetch` tool call, the Anthropic compatibility layer intercepts it, executes the search against Ollama's web search API, and returns the results as a tool result message before the model continues reasoning.

---

## Installation & Usage

```bash
# Install Ollama (macOS/Linux)
curl -fsSL https://ollama.com/install.sh | sh

# Zero-config Claude Code setup (Ollama v0.15+)
ollama launch claude

# Pull a recommended subagent-capable cloud model
ollama pull minimax-m2.5:cloud

# Manual Claude Code setup (alternative)
export ANTHROPIC_AUTH_TOKEN=ollama
export ANTHROPIC_BASE_URL=http://localhost:11434
claude --model minimax-m2.5:cloud
```

```python
# Standalone web search via Python library (ollama>=0.6.0)
import ollama

response = ollama.web_search("What is Ollama?")
print(response)
# Returns: results=[{title, url, content}, ...]

# Search agent pattern with tool calls
from ollama import chat, web_fetch, web_search

available_tools = {"web_search": web_search, "web_fetch": web_fetch}
messages = [{"role": "user", "content": "research the postgres 18 release notes"}]

while True:
    response = chat(model="minimax-m2.5:cloud", messages=messages, tools=[web_search, web_fetch], think=True)
    messages.append(response.message)
    if response.message.tool_calls:
        for tool_call in response.message.tool_calls:
            fn = available_tools.get(tool_call.function.name)
            if fn:
                result = fn(**tool_call.function.arguments)
                messages.append({"role": "tool", "content": str(result)[:8000], "tool_name": tool_call.function.name})
    else:
        break
```

```bash
# Example Claude Code subagent prompts
# Spawn parallel exploration agents
claude --model minimax-m2.5:cloud
# > spawn subagents to explore the auth flow, payment integration, and notification system

# Parallel competitive research
# > create 3 research agents to research how our top 3 competitors price their API tiers, compare against our current pricing, and draft recommendations

# Parallel audit with web search
# > research the postgres 18 release notes, audit our queries for deprecated patterns, and create migration tasks
```

---

## Relevance to Claude Code Development

### Applications

- Subagent spawning pattern is directly applicable to the `research-curator` skill: spawn multiple worker agents to research resources in parallel rather than serially
- The isolated-context-per-agent model mirrors how the Claude Agent SDK's Agent tool works -- each delegated task runs in its own context
- Built-in web search without MCP removes a significant configuration barrier for Claude Code workflows that need live data

### Patterns Worth Adopting

- **Natural language subagent triggering**: Prompt phrasing like "spawn subagents to explore X, Y, and Z" reliably triggers parallel execution in models that support it -- useful for orchestrator prompts in this repo's skills
- **Isolated context pattern**: Side research tasks should be delegated to subagents to prevent context pollution in the primary session -- validates the current pattern used by `research-curator` spawning worker agents via Agent tool
- **Web search as inline tool**: Integrating web search as a model tool call (not as a separate pipeline step) simplifies research workflows
- **5-hour session management**: Long multi-agent coding sessions require session window planning; the 64K token minimum context threshold is a useful baseline for skill development

### Integration Opportunities

- Skills that spawn Task-based research workers could reference Ollama-compatible models as a zero-cost alternative to Anthropic API for non-sensitive research tasks
- The `ollama launch` zero-config pattern could inspire a similar setup command for this repo's plugin workflows
- Ollama's web search API (`https://ollama.com/api/web_search`) could be wrapped as an MCP tool for use in sessions where `mcp__exa__web_search_exa` is unavailable

---

## References

- [Subagents and web search in Claude Code - Ollama Blog](https://ollama.com/blog/web-search-subagents-claude-code) (accessed 2026-02-19)
- [Web search - Ollama Blog](https://ollama.com/blog/web-search) (accessed 2026-02-19)
- [ollama launch - Ollama Blog](https://ollama.com/blog/launch) (accessed 2026-02-19)
- [Claude Code with Anthropic API compatibility - Ollama Blog](https://ollama.com/blog/claude) (accessed 2026-02-19)
- [ollama/ollama GitHub Repository](https://github.com/ollama/ollama) (accessed 2026-02-19)
