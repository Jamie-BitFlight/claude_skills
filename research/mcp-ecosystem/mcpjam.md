---
name: MCPJam Inspector - Local Development and Testing Tool for MCP Servers
description: MCPJam Inspector is a comprehensive local development and testing tool for MCP servers, ChatGPT apps, and MCP Apps (ext-apps/SEP-1865). It provides a full widget emulator for ChatGPT and Claude app...
license: Apache-2.0
metadata:
  topic: mcpjam
  category: mcp-ecosystem
  source_url: https://mcpjam.com
  github: MCPJam/inspector
  version: "v1.1.6"
  verified: "2026-01-26"
  next_review: "2026-04-26"
---

## Overview

MCPJam Inspector is a comprehensive local development and testing tool for MCP servers, ChatGPT apps, and MCP Apps (ext-apps/SEP-1865). It provides a full widget emulator for ChatGPT and Claude app development, an LLM playground with free access to frontier models (GPT-5, Claude Sonnet), OAuth debugging, test case management with AI generation, and E2E evaluation capabilities via CLI.

**Core Value Proposition**: Eliminates the need for ngrok or ChatGPT subscriptions during MCP server and app development by providing a complete local testing environment with multi-LLM support.

---

## Problem Addressed

| Problem                                               | How MCPJam Solves It                                             |
| ----------------------------------------------------- | ---------------------------------------------------------------- |
| Complex MCP server setup for local testing            | Single npx command starts full inspector with web UI             |
| ChatGPT app development requires ngrok + subscription | Full widget emulator runs locally with no external dependencies  |
| MCP Apps (Claude ext-apps) lack development tooling   | Complete SEP-1865 support with all JSON-RPC message types        |
| OAuth 2.1 implementation debugging is complex         | Visual step-by-step OAuth debugger with multi-protocol support   |
| Testing MCP tools across different LLMs is expensive  | Free access to GPT-5 and Claude Sonnet in playground             |
| Manual test case creation is time-consuming           | AI-powered test generation from tool definitions                 |
| E2E testing MCP servers across clients is fragmented  | CLI-based eval framework simulates different client environments |

---

## Key Statistics (as of January 26, 2026)

| Metric           | Value                 |
| ---------------- | --------------------- |
| GitHub Stars     | 1,598                 |
| Forks            | 177                   |
| Open Issues      | 14                    |
| Primary Language | TypeScript            |
| npm Package      | @mcpjam/inspector     |
| CLI Package      | @mcpjam/cli           |
| Latest Version   | v1.5.0 (Jan 20, 2026) |
| Created          | May 23, 2025          |
| Last Updated     | Jan 25, 2026          |

---

## Key Features

### 1. MCP Server Inspection

- **Multi-Server Connection**: Connect to multiple MCP servers simultaneously
- **Tool Testing**: Manually invoke tools with custom parameters, view JSON-RPC logs
- **Resource & Prompt Testing**: Test resources, resource templates, and prompts
- **Server Information**: View icons, versions, capabilities, and instructions
- **All JSON-RPC Logging**: Real-time protocol message inspection

### 2. ChatGPT Apps SDK Support

- **Full `window.openai` API**: Complete support for `widgetState`, `callTool`, `structuredContent`, `sendFollowUpMessage`, `displayMode`
- **Widget Emulator**: Preview widgets without ChatGPT subscription
- **Device Emulation**: Test across Desktop, Tablet, Mobile viewports
- **CSP Testing**: Validate Content Security Policy configurations
- **Theme/Locale Testing**: Light/dark modes, internationalization testing
- **Safe Area Insets**: Simulate device notches and gesture areas

### 3. MCP Apps (SEP-1865) Support

- **Full JSON-RPC Message Types**: `tools/call`, `ui/initialize`, `ui/message`, `ui/open-link`
- **Inline Widget Rendering**: Render `ui.resourceUri` components in chat
- **Display Modes**: Inline, Picture-in-Picture, Fullscreen support

### 4. OAuth Debugger

- **Visual Step-by-Step**: Interactive OAuth handshake walkthrough
- **Multi-Protocol Versions**: Supports specs 03-26, 06-18, and 11-25
- **Registration Methods**: Client pre-registration, DCR, and CIMD
- **Network Inspection**: View all HTTP requests/responses with headers
- **Sequence Diagrams**: Visual flow synchronized with progress

### 5. LLM Playground

- **Free Frontier Models**: GPT-5, Claude Sonnet, Gemini 2.5 at no cost
- **Multi-Provider Support**: OpenAI, Anthropic, Google, Deepseek, Mistral, Ollama, OpenRouter, LiteLLM
- **Split-Panel Interface**: Chat on left, JSON-RPC logs on right
- **MCP Prompts**: Use prompts directly via `/` command
- **Elicitation Support**: Handle interactive prompts from MCP servers
- **Customizable Agent**: System prompts, temperature settings

### 6. Test Cases

- **AI-Powered Generation**: Auto-generate tests from tool definitions using Claude Haiku
- **Positive/Negative Tests**: Test both tool triggering and non-triggering scenarios
- **Multi-Model Evaluation**: Run tests across different LLM providers
- **Accuracy Metrics**: Track pass rates, token consumption, duration
- **Run History**: Compare performance across runs and models
- **App Store Compliance**: Generate required test cases for ChatGPT app submission

### 7. MCP Evals (CLI)

- **E2E Testing**: Simulate end-user environments
- **Environment Simulation**: Test as Claude Desktop, Cursor, etc.
- **Multiple Servers**: Test against multiple MCP servers
- **CI/CD Integration**: JSON-based configuration for automation

---

## Technical Architecture

<eg>
                    MCPJam Inspector
                          |
     +--------------------+--------------------+
     |                    |                    |
  Web UI              CLI Tool            Desktop App
(localhost:6274)    (@mcpjam/cli)       (Mac/Windows)
     |                    |                    |
     +--------------------+--------------------+
                          |
            +-------------+-------------+
            |             |             |
       MCP Servers   ChatGPT Apps   MCP Apps
       (stdio/HTTP)  (window.openai) (SEP-1865)
            |             |             |
            +-------------+-------------+
                          |
              +------+----+----+------+
              |      |    |    |      |
           OpenAI Claude Gemini Ollama ...
           (GPT-5) (Sonnet)     (Local)
</eg>

### Deployment Options

**npx (Quick Start)**:

```bash
npx @mcpjam/inspector@latest
```

**Docker**:

```bash
docker run -p 127.0.0.1:6274:6274 mcpjam/mcp-inspector
```

**Desktop App**: Native Mac (.dmg) and Windows (.exe) installers available

**With MCP Server**:

```bash
npx @mcpjam/inspector@latest npx -y @modelcontextprotocol/server-everything
```

### Configuration

Supports Claude Desktop-style configuration files:

```json
{
  "mcpServers": {
    "weather-server": {
      "command": "python",
      "args": ["weather_server.py"],
      "env": {
        "WEATHER_API_KEY": "${WEATHER_API_KEY}"
      }
    }
  }
}
```

Launch with: `npx @mcpjam/inspector@latest --config path/to/config.json`

---

## Installation and Usage

### Quick Start

```bash
# Start inspector
npx @mcpjam/inspector@latest

# Open browser to http://localhost:6274
```

### Start with MCP Server

```bash
# Python FastMCP server
npx @mcpjam/inspector@latest uv run fastmcp run /path/to/server.py

# Node.js server
npx @mcpjam/inspector@latest npx -y your-mcp-package
```

### Start with Ollama

```bash
npx @mcpjam/inspector@latest --ollama llama3.2
```

### MCP Evals CLI

```bash
# Install CLI globally
npm install -g @mcpjam/cli

# Run evaluations
mcpjam evals run --tests tests.json --environment env.json
```

### Test File Format

```json
{
  "tests": [
    {
      "title": "Test weather tool",
      "query": "What's the weather in San Francisco?",
      "expectedTools": ["get_weather"],
      "model": { "id": "claude-3-5-sonnet-20241022", "provider": "anthropic" },
      "selectedServers": ["weather-server"]
    }
  ]
}
```

---

## Comparison with Alternatives

| Feature              | MCPJam            | Official MCP Inspector | Postman | Custom Testing     |
| -------------------- | ----------------- | ---------------------- | ------- | ------------------ |
| MCP Server Testing   | Yes               | Yes                    | Partial | Manual             |
| ChatGPT Apps Support | Yes               | No                     | No      | Manual             |
| MCP Apps (SEP-1865)  | Yes               | No                     | No      | Manual             |
| OAuth Debugger       | Yes (visual)      | Basic                  | Yes     | Manual             |
| LLM Playground       | Yes (free models) | No                     | No      | Requires API keys  |
| AI Test Generation   | Yes               | No                     | No      | No                 |
| E2E Evals CLI        | Yes               | No                     | No      | Manual             |
| Widget Emulator      | Full              | No                     | No      | Manual             |
| Multi-Provider LLMs  | 8+ providers      | N/A                    | N/A     | Per-provider setup |

---

## Relevance to Claude Code Development

### Direct Applications

1. **MCP Server Development**: Test custom MCP servers before integrating with Claude Code
2. **OAuth Flow Debugging**: Debug authentication for MCP servers requiring OAuth
3. **Tool Testing**: Manually invoke and verify tool behavior before deployment
4. **Multi-LLM Validation**: Verify MCP servers work across Claude, GPT, Gemini models

### Patterns Worth Adopting

1. **Visual OAuth Debugging**: Step-by-step handshake visualization pattern
2. **AI Test Generation**: Using LLMs to generate test cases from tool definitions
3. **E2E Eval Framework**: JSON-based test configuration for CI/CD integration
4. **Free Frontier Model Access**: Proxied access pattern for development tools
5. **Widget Emulation**: Iframe isolation with injected APIs for UI testing
6. **Multi-Protocol Support**: Backwards-compatible OAuth spec handling

### Integration Opportunities

1. **Claude Code Plugin**: Create plugin that launches MCPJam for connected MCP servers
2. **Pre-Deployment Testing**: Integrate MCPJam evals into plugin CI/CD pipelines
3. **OAuth Debugging Workflow**: Use MCPJam for debugging MCP OAuth implementations
4. **Test Case Library**: Generate and maintain test cases for Claude Code MCP integrations

### Complementary to Existing MCP Ecosystem Research

MCPJam fills a testing and development tooling gap:

- **Narsil MCP**: Code intelligence and security scanning (runtime)
- **OctoCode MCP**: Research Driven Development with GitHub search (research)
- **Docs MCP Server**: Documentation grounding and retrieval (knowledge)
- **MCPJam**: Development, testing, and evaluation (DevOps/QA)

---

## References

1. **Documentation**: <https://docs.mcpjam.com> (accessed 2026-01-26)
2. **GitHub Repository**: <https://github.com/MCPJam/inspector> (accessed 2026-01-26)
3. **npm Package (@mcpjam/inspector)**: <https://www.npmjs.com/package/@mcpjam/inspector> (accessed 2026-01-26)
4. **npm Package (@mcpjam/cli)**: <https://www.npmjs.com/package/@mcpjam/cli> (accessed 2026-01-26)
5. **Getting Started Guide**: <https://docs.mcpjam.com/getting-started.md> (accessed 2026-01-26)
6. **OAuth Debugger**: <https://docs.mcpjam.com/inspector/guided-oauth.md> (accessed 2026-01-26)
7. **App Builder**: <https://docs.mcpjam.com/inspector/app-builder.md> (accessed 2026-01-26)
8. **LLM Playground**: <https://docs.mcpjam.com/inspector/llm-playground.md> (accessed 2026-01-26)
9. **Test Cases**: <https://docs.mcpjam.com/inspector/test-cases.md> (accessed 2026-01-26)
10. **MCP Evals**: <https://docs.mcpjam.com/evals/overview.md> (accessed 2026-01-26)
11. **MCP Protocol Specification**: <https://modelcontextprotocol.io/> (accessed 2026-01-26)
12. **ChatGPT Apps SDK**: <https://developers.openai.com/apps-sdk/> (accessed 2026-01-26)
13. **MCP Apps SEP-1865**: <https://github.com/modelcontextprotocol/modelcontextprotocol/pull/1865> (accessed 2026-01-26)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [agentscope](../agent-frameworks/agentscope.md) | agent-frameworks | referenced by agentscope (agent-frameworks) |
| [samuraizer](../ai-research-tools/samuraizer.md) | ai-research-tools | referenced by samuraizer (ai-research-tools) |
| [wigolo](./wigolo.md) | mcp-ecosystem | referenced by wigolo (mcp-ecosystem) |
