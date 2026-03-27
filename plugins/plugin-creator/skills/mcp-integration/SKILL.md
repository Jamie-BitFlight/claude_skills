---
name: mcp-integration
description: 'Integrate MCP servers into Claude Code plugins — covers .mcp.json configuration, plugin.json mcpServers field, server types (stdio, SSE, HTTP, WebSocket), environment variable expansion, tool naming conventions, OAuth and token authentication, security best practices, and testing workflows. Use when adding an MCP server to a plugin, configuring MCP authentication, debugging MCP tool discovery, setting up Model Context Protocol integration, or choosing between stdio and SSE transport types.'
---

# MCP Integration for Claude Code Plugins

Model Context Protocol (MCP) enables Claude Code plugins to expose external service capabilities as tools. Use this skill when adding MCP server configuration to a plugin, choosing transport types, or debugging MCP tool discovery.

## MCP Skill Routing

```mermaid
flowchart TD
    Start(["MCP-related task"]) --> Q1{What do you need?}
    Q1 -->|"Build a new FastMCP server<br>from scratch in Python"| FastMCP["Use /fastmcp-creator"]
    Q1 -->|"Write a CLI client that<br>talks to an MCP server"| ClientCLI["Use /fastmcp-client-cli"]
    Q1 -->|"Run, inspect, or debug<br>an MCP server from terminal"| MCPCLI["Use /mcp-cli"]
    Q1 -->|"Write pytest tests for<br>FastMCP server tools"| Tests["Use /fastmcp-python-tests"]
    Q1 -->|"General Python development<br>for MCP server code"| PyDev["Use /python3-development"]
    Q1 -->|"Configure an MCP server<br>inside a Claude Code plugin"| ThisSkill["Continue with this skill"]
```

For building FastMCP servers from scratch, use `/fastmcp-creator`. For writing CLI clients that communicate with MCP servers, use `/fastmcp-client-cli`. For terminal-based MCP server inspection and debugging, use `/mcp-cli`. For writing pytest test suites for FastMCP tools, use `/fastmcp-python-tests`. For general Python development of MCP server code, use `/python3-development`.

## Configuration Methods

Plugins bundle MCP servers via one of two methods.

```mermaid
flowchart TD
    Q{"How many MCP servers<br>does the plugin need?"}
    Q -->|"One server, simple setup"| Inline["Inline in plugin.json<br>Add mcpServers field"]
    Q -->|"Multiple servers or<br>complex configuration"| Dedicated["Dedicated .mcp.json<br>at plugin root"]
    Dedicated --> Benefit1["Separation of concerns<br>Easier maintenance<br>Clear ownership"]
    Inline --> Benefit2["Single config file<br>Good for minimal plugins"]
```

### Dedicated .mcp.json (Recommended)

Create `.mcp.json` at the plugin root directory. Each top-level key is a server name.

```json
{
  "database-tools": {
    "command": "${CLAUDE_PLUGIN_ROOT}/servers/db-server",
    "args": ["--config", "${CLAUDE_PLUGIN_ROOT}/config.json"],
    "env": {
      "DB_URL": "${DB_URL}"
    }
  }
}
```

### Inline in plugin.json

Add an `mcpServers` field to the existing `plugin.json`.

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "mcpServers": {
    "plugin-api": {
      "command": "${CLAUDE_PLUGIN_ROOT}/servers/api-server",
      "args": ["--port", "8080"]
    }
  }
}
```

## Server Types

```mermaid
flowchart TD
    Q{"Where does the<br>MCP server run?"}
    Q -->|"Local process<br>you control"| STDIO["stdio — spawns child process<br>Communicates via stdin/stdout<br>Claude Code manages lifecycle"]
    Q -->|"Hosted cloud service<br>with OAuth"| SSE["SSE — Server-Sent Events<br>OAuth handled automatically<br>No local install needed"]
    Q -->|"REST API backend<br>with token auth"| HTTP["HTTP — RESTful endpoint<br>Token-based authentication<br>Stateless interactions"]
    Q -->|"Real-time bidirectional<br>streaming needed"| WS["WebSocket — persistent connection<br>Low-latency push notifications<br>ws or wss protocol"]
```

For detailed configuration examples, type-specific fields, and advanced options for each server type, read [Server Types Reference](./references/server-types-and-patterns.md).

## Environment Variable Expansion

All MCP configurations support variable substitution.

`${CLAUDE_PLUGIN_ROOT}` resolves to the plugin's installed directory. Always use this for paths to bundled scripts and configs — never hardcode absolute paths.

```json
{
  "command": "${CLAUDE_PLUGIN_ROOT}/servers/my-server",
  "env": {
    "API_KEY": "${MY_API_KEY}",
    "DATABASE_URL": "${DB_URL}"
  }
}
```

User environment variables (from the user's shell) are available in the `env` block. Document all required environment variables in the plugin README.

## Tool Naming Convention

MCP tools are automatically prefixed when registered.

Format: `mcp__plugin_<plugin-name>_<server-name>__<tool-name>`

Example with plugin `asana`, server `asana`, tool `create_task`:

```text
mcp__plugin_asana_asana__asana_create_task
```

Pre-allow specific MCP tools in skill or command frontmatter:

```yaml
allowed-tools: mcp__plugin_asana_asana__asana_create_task, mcp__plugin_asana_asana__asana_search_tasks
```

Avoid wildcard patterns (`mcp__plugin_asana_asana__*`) — pre-allow specific tools for security.

## Authentication Patterns

```mermaid
flowchart TD
    Q{"Authentication<br>method?"}
    Q -->|"Cloud service<br>user authorizes in browser"| OAuth["OAuth — automatic<br>SSE or HTTP type<br>No config needed beyond URL<br>User prompted on first use"]
    Q -->|"API key or<br>bearer token"| Token["Token-based — headers block<br>Use env vars, never hardcode<br>Document required vars in README"]
    Q -->|"Local process<br>no external auth"| EnvVar["Environment variables<br>Pass config via env block<br>Credentials stay in user shell"]
```

OAuth example (SSE):

```json
{
  "type": "sse",
  "url": "https://mcp.example.com/sse"
}
```

Token example (HTTP):

```json
{
  "type": "http",
  "url": "https://api.example.com/mcp",
  "headers": {
    "Authorization": "Bearer ${API_TOKEN}"
  }
}
```

## Lifecycle and Testing

MCP servers start when the plugin loads. Connection is established before first tool use.

Lifecycle sequence: plugin loads, MCP configuration parsed, server process started (stdio) or connection established (SSE/HTTP/WS), tools discovered and registered, tools available as `mcp__plugin_...`.

### Testing Workflow

1. Configure MCP server in `.mcp.json`
2. Install plugin locally or use `claude --plugin-dir ./my-plugin`
3. Run `/mcp` to verify the server appears
4. Test tool calls from skills or commands
5. Use `claude --debug` to inspect connection attempts, tool discovery, and errors

### Debugging Common Issues

**Server not connecting** — verify URL, confirm server process is running (stdio), check network connectivity, review auth config.

**Tools not available** — verify server connected via `/mcp`, check tool names match exactly (including prefix), restart Claude Code after config changes.

**Authentication failing** — clear cached OAuth tokens and re-authenticate, verify environment variables are set, check token scopes and permissions.

## Security Checklist

- Use HTTPS/WSS for all remote connections — never HTTP/WS
- Store tokens in environment variables — never hardcode in config
- Pre-allow specific MCP tools — avoid wildcard `__*` patterns
- Document all required environment variables in the plugin README
- Test authentication flows during development, not after publishing

## Additional Resources

For complete server type configurations (stdio, SSE, HTTP, WebSocket) with full examples, integration patterns (tool wrappers, autonomous agents, multi-server plugins), and performance considerations, read [Server Types and Patterns Reference](./references/server-types-and-patterns.md).

SOURCE: Adapted from Anthropic plugin-dev mcp-integration skill (`../claude-plugins-official/plugins/plugin-dev/skills/mcp-integration/SKILL.md`). Tool naming format and environment variable expansion per Claude Code plugin documentation.
