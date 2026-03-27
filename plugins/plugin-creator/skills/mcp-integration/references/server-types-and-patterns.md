# Server Types and Integration Patterns

Complete reference for MCP server type configuration and plugin integration patterns.

## stdio (Local Process)

Spawn a local MCP server as a child process. Claude Code manages the process lifecycle — communicates via stdin/stdout, terminates when Claude Code exits.

```json
{
  "filesystem": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/allowed/path"],
    "env": {
      "LOG_LEVEL": "debug"
    }
  }
}
```

Required fields: `command` (executable path or name).
Optional fields: `args` (array of string arguments), `env` (environment variable overrides).

Use `${CLAUDE_PLUGIN_ROOT}` for paths to bundled server binaries:

```json
{
  "custom-server": {
    "command": "${CLAUDE_PLUGIN_ROOT}/servers/my-server",
    "args": ["--config", "${CLAUDE_PLUGIN_ROOT}/config.json"]
  }
}
```

Best for: file system access, local database connections, custom MCP servers, NPM-packaged servers.

## SSE (Server-Sent Events)

Connect to a hosted MCP server over HTTP with Server-Sent Events. OAuth flows are handled automatically by Claude Code — the user is prompted in their browser on first use.

```json
{
  "asana": {
    "type": "sse",
    "url": "https://mcp.asana.com/sse"
  }
}
```

Required fields: `type` (must be `"sse"`), `url` (HTTPS endpoint).

Best for: official hosted MCP servers (Asana, GitHub), cloud services with MCP endpoints, OAuth-based authentication, zero local installation.

## HTTP (REST API)

Connect to a RESTful MCP server with token-based authentication via headers.

```json
{
  "api-service": {
    "type": "http",
    "url": "https://api.example.com/mcp",
    "headers": {
      "Authorization": "Bearer ${API_TOKEN}",
      "X-Custom-Header": "value"
    }
  }
}
```

Required fields: `type` (must be `"http"`), `url` (HTTPS endpoint).
Optional fields: `headers` (key-value pairs for authentication and custom headers).

Best for: REST API-based MCP servers, token-based authentication, custom API backends, stateless interactions.

## WebSocket (Real-time)

Connect to a WebSocket MCP server for persistent bidirectional communication with low latency.

```json
{
  "realtime-service": {
    "type": "ws",
    "url": "wss://mcp.example.com/ws",
    "headers": {
      "Authorization": "Bearer ${TOKEN}"
    }
  }
}
```

Required fields: `type` (must be `"ws"`), `url` (WSS endpoint).
Optional fields: `headers` (authentication and custom headers).

Best for: real-time data streaming, persistent connections, push notifications from server, low-latency requirements.

## Integration Patterns

### Pattern 1 — Simple Tool Wrapper

A skill or command pre-allows specific MCP tools and adds validation or preprocessing before calling them.

```markdown
---
name: create-item
description: Create an item with validation
allowed-tools: mcp__plugin_name_server__create_item
---

1. Gather item details from the user
2. Validate required fields
3. Call mcp__plugin_name_server__create_item
4. Confirm creation to the user
```

Use when: adding validation, user confirmation, or preprocessing before MCP tool calls.

### Pattern 2 — Autonomous Agent

An agent uses MCP tools autonomously across multiple steps without user interaction between calls.

```markdown
---
name: data-analyzer
description: Analyze data from connected sources
---

1. Query data via mcp__plugin_db_server__query
2. Process and analyze results
3. Generate insights report
```

Use when: multi-step MCP workflows where intermediate user interaction is unnecessary.

### Pattern 3 — Multi-Server Plugin

A single plugin integrates multiple MCP servers, each connecting to a different service.

```json
{
  "github": {
    "type": "sse",
    "url": "https://mcp.github.com/sse"
  },
  "jira": {
    "type": "sse",
    "url": "https://mcp.jira.com/sse"
  }
}
```

Use when: workflows span multiple external services and need coordinated tool access.

## Performance Considerations

MCP servers connect on-demand — not all servers connect at plugin startup. The first tool use triggers the connection. Connection pooling is managed automatically by Claude Code.

Batch similar requests when possible. Prefer a single query with filters over many individual lookups:

```text
# Preferred — single query with filters
search_tasks(project="X", assignee="me", limit=50)

# Avoid — N individual queries
for each id: get_task(id)
```

## Error Handling Guidance

**Connection failures** — provide fallback behavior in skills, inform the user of connection issues, verify server URL and configuration.

**Tool call errors** — validate inputs before calling MCP tools, provide clear error messages, check rate limiting and quotas.

**Configuration errors** — test server connectivity during development, validate JSON syntax, confirm required environment variables are set.

SOURCE: Adapted from Anthropic plugin-dev mcp-integration skill. Server type configurations, integration patterns, and error handling per Claude Code plugin documentation.
