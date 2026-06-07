# Claude Code MCP Integration Reference

How Claude Code discovers, configures, and connects to MCP servers — the deployment target for every server you build with this skill.

**Why read this**: Your MCP server doesn't exist in isolation. It runs inside Claude Code, where configuration scoping, transport selection, permission rules, agent-scoped servers, tool disambiguation, and output limits determine whether your server works seamlessly or breaks silently. Understanding the host environment prevents the #1 class of MCP server bugs: "works in testing, fails in production." [1]

---

## Configuration Methods

### CLI (`claude mcp add`)

```bash
# HTTP (recommended for remote servers)
claude mcp add --transport http <name> <url>

# SSE (deprecated — use HTTP where available)
claude mcp add --transport sse <name> <url>

# Stdio (local processes)
claude mcp add --transport stdio --env KEY=value <name> -- <command> [args...]

# From JSON
claude mcp add-json <name> '<json>'

# Import from Claude Desktop
claude mcp add-from-claude-desktop
```

**Option ordering**: All flags (`--transport`, `--env`, `--scope`, `--header`) come **before** the server name. `--` separates the name from the command/args.

### `.mcp.json` (project-scoped, git-tracked)

```json
{
  "mcpServers": {
    "my-server": {
      "command": "uv",
      "args": ["run", "python", "-m", "my_server"],
      "cwd": "path/to/server",
      "env": {
        "API_KEY": "${API_KEY}"
      }
    }
  }
}
```

Supports `${VAR}` and `${VAR:-default}` environment variable expansion in `command`, `args`, `env`, `url`, and `headers`.

### Agent frontmatter (agent-scoped)

```yaml
---
name: my-agent
mcpServers:
  my-server:
    command: uv
    args:
      - run
      - python
      - -m
      - my_server
    cwd: path/to/server
---
```

Agent-scoped servers start when the agent is spawned and are only available to that agent. Reference an already-configured server by name instead of inline definition:

```yaml
mcpServers:
  - slack
```

### Plugin-bundled

Plugins define MCP servers in `.mcp.json` at plugin root or inline in `plugin.json`. Use `${CLAUDE_PLUGIN_ROOT}` for plugin-relative paths. Servers start automatically when the plugin is enabled.

---

## Scoping and Precedence

| Scope | Storage | Shared | Use Case |
|-------|---------|--------|----------|
| **local** (default) | `~/.claude.json` under project path | No | Personal dev servers, sensitive credentials |
| **project** | `.mcp.json` in project root | Yes (git) | Team-shared servers |
| **user** | `~/.claude.json` global | No | Cross-project personal utilities |

**Precedence**: local > project > user. Same-name servers at higher scope override lower.

```bash
# Specify scope explicitly
claude mcp add --transport http my-api --scope project https://api.example.com/mcp
```

---

## Transport Selection

| Transport | Use Case | Command |
|-----------|----------|---------|
| **HTTP** (Streamable) | Remote cloud services (recommended) | `--transport http` |
| **SSE** | Remote (deprecated, use HTTP) | `--transport sse` |
| **stdio** | Local processes, custom scripts | `--transport stdio` |

**Design implication**: If your server will be used locally by the developer who built it, use stdio. If it's a cloud service or shared API, use HTTP.

---

## Authentication

### OAuth 2.0 (remote servers)

```bash
# Server supports dynamic client registration
claude mcp add --transport http my-server https://mcp.example.com/mcp
# Then authenticate:
> /mcp
```

### Pre-configured OAuth (no dynamic registration)

```bash
claude mcp add --transport http \
  --client-id your-client-id --client-secret --callback-port 8080 \
  my-server https://mcp.example.com/mcp
```

### API key / Bearer token

```bash
claude mcp add --transport http my-api https://api.example.com/mcp \
  --header "Authorization: Bearer your-token"
```

### Environment variables (stdio servers)

```bash
claude mcp add --transport stdio --env API_KEY=value my-server -- npx my-package
```

---

## Output Limits

- **Warning threshold**: 10,000 tokens per tool output
- **Default max**: 25,000 tokens per tool output
- **Override**: `MAX_MCP_OUTPUT_TOKENS=50000 claude`

**Design implication**: If your tool returns large datasets, implement pagination or filtering parameters. Returning unbounded data triggers warnings and may hit limits.

---

## Tool Search (Dynamic Loading)

When many MCP tools are configured, Claude Code defers tool loading and uses search-based discovery instead of preloading all tool definitions.

- **Auto threshold**: Activates when MCP tool definitions exceed 10% of context window
- **Override**: `ENABLE_TOOL_SEARCH=auto:5` (custom 5% threshold), `true` (always), `false` (disabled)
- **Requires**: Sonnet 4+ or Opus 4+ (Haiku does not support tool search)

**Design implication**: Write clear, descriptive tool names and docstrings. When tool search is active, Claude discovers your tools by searching — vague names reduce discoverability.

---

## MCP Resources (@-mentions)

Servers can expose resources that users reference with `@server:protocol://path`:

```text
> Can you analyze @github:issue://123 and suggest a fix?
> Compare @postgres:schema://users with @docs:file://database/user-model
```

Resources are fetched and included as attachments when referenced.

---

## MCP Prompts (slash commands)

Servers can expose prompts that become commands: `/mcp__servername__promptname [args]`.

```text
> /mcp__github__pr_review 456
```

---

## Server Management

```bash
claude mcp list              # List all configured servers
claude mcp get <name>        # Get details for a server
claude mcp remove <name>     # Remove a server
```

Within Claude Code: `/mcp` — interactive server status, authentication, and management.

**Dynamic updates**: Claude Code supports MCP `list_changed` notifications — servers can update their available tools without reconnection.

---

## Server Lifecycle Notes

- Servers configured in `.mcp.json` or `~/.claude.json` start at **session start**
- Agent-scoped servers (frontmatter `mcpServers`) start when the **agent is spawned**
- Adding a server mid-session requires **restarting Claude Code** or using `/agents` for agent-scoped servers
- Plugin MCP servers start when the plugin is **enabled** (restart required for changes)
- `MCP_TIMEOUT` environment variable controls startup timeout (e.g., `MCP_TIMEOUT=10000`)

---

## Managed Configuration (Enterprise)

Organizations can deploy `managed-mcp.json` to system directories for exclusive control, or use `allowedMcpServers`/`deniedMcpServers` in managed settings for policy-based restrictions.

- macOS: `/Library/Application Support/ClaudeCode/managed-mcp.json`
- Linux: `/etc/claude-code/managed-mcp.json`

---

## Claude Code as MCP Server

Claude Code itself can serve as an MCP server for other applications:

```bash
claude mcp serve
```

Exposes Claude Code's tools (Read, Edit, Bash, etc.) over stdio transport.

---

## Design Checklist for Server Authors

When building an MCP server that will run in Claude Code:

- [ ] Choose transport based on deployment (stdio for local, HTTP for remote)
- [ ] Keep tool output under 10,000 tokens — add pagination/filtering if larger
- [ ] Write descriptive tool names and docstrings (tool search relies on them)
- [ ] Support `${VAR}` in `.mcp.json` for credentials — never hardcode secrets
- [ ] Test with `claude mcp add` then `/mcp` to verify connection
- [ ] If bundling in a plugin, use `${CLAUDE_PLUGIN_ROOT}` for paths
- [ ] If agent-scoped, verify the `cwd` resolves correctly relative to project root
- [ ] Handle `list_changed` notifications if tools are dynamic

## References

1. [Connect Claude Code to tools via MCP](https://code.claude.com/docs/en/mcp.md) (accessed 2026-03-01)
