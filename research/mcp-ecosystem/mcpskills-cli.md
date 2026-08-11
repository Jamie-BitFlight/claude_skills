---
name: mcpskills-cli
research_date: 2026-03-13
source_url: https://github.com/dhanababum/mcpskills-cli
github_repository: https://github.com/dhanababum/mcpskills-cli
version_at_research: v0.1.2
license: MIT
freshness_tracking:
  last_verified: 2026-03-13
  version_at_verification: v0.1.2
  next_review: 2026-06-13
  confidence_map: "Overview: high, Problem Addressed: high, Key Features: high, Technical Architecture: high, Installation & Usage: high, Relevance to Claude Code: medium"
---

# mcpskills-cli

## Overview

mcpskills-cli (v0.1.2) is a command-line tool that bridges Model Context Protocol (MCP) servers with AI agent skills by automatically discovering MCP tools and generating statically-hosted skill files in SKILL.md format. It transforms tool schemas from any Streamable HTTP MCP server into structured documentation with polyglot call scripts (bash, python, node, go, rust), enabling agents to access tools without loading all MCP tools into context. Solves token pollution from traditional MCP loading by converting on-demand discoverable tools into statically-referenced skills. (Accessed: <https://github.com/dhanababum/mcpskills-cli> README.md, 2026-03-13)

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| MCP servers load all tools into context, polluting token budgets | mcpskills-cli transforms MCP tools into statically-generated SKILL.md files that agents load only when needed (accessed 2026-03-13) |
| Agents cannot discover MCP tools without full tool list context cost | Tool discovery via Streamable HTTP protocol with automated schema extraction; skill generation produces documentation agents can reference (accessed 2026-03-13) |
| Manual skill creation from MCP tools requires tedious, error-prone documentation work | Automatic SKILL.md and polyglot call script generation from OpenAPI/JSON schemas via Jinja2 templates (accessed 2026-03-13) |
| Credential management requires manual setup in multiple files | Centralized credential storage in `~/.mcps/credentials` (INI format, chmod 600); skills reference server name, tokens can be rotated without skill regeneration (accessed 2026-03-13) |
| No standardized way to invoke MCP tools from skill scripts | Generated call scripts implement MCP protocol (JSON-RPC 2.0) with Bearer token auth; available in bash, python, node, go, rust (accessed 2026-03-13) |

---

## Key Features

### Automatic MCP Tool Discovery
- Connects to Streamable HTTP MCP server via fastmcp >= 2.3
- Calls `client.list_tools()` to fetch all available tools with schemas
- Extracts name, description, input parameters with types and required/optional flags
- No manual tool list creation required

### Dual-Mode Skill Generation
- **Single skill mode** (default): Generates one SKILL.md with all tools + single multi-tool call script
- **Multi-skills mode** (`--multi-skills`): Generates one SKILL.md per tool with separate call scripts
- Trade-off: Single-skill minimizes token consumption; multi-skills provides fine-grained skill selection

### Polyglot Call Script Generation
- Generates language-specific call scripts: bash, python, node, go, rust
- All scripts implement same workflow: read credentials, construct MCP protocol request, POST to server, parse streaming response
- Output as JSON for agent consumption
- Scripts executable from command line

### Credential Management
- Automatic credential storage in `~/.mcps/credentials` (INI format, chmod 0o600)
- Section per server: `[my-db]` contains `url` and `token` keys
- Token rotation by editing INI file; no skill regeneration needed
- Security: File permissions restrict access to owner only

---

## Technical Architecture

### Component Structure
```
mcpskills-cli (CLI entry)
├─ client.py — MCP communication via fastmcp StreamableHttpTransport
├─ credentials.py — Secure INI storage and retrieval
├─ generator.py — Skill template rendering with Jinja2
├─ templates/ — skill.md, call_bash.sh, call_python.py, etc.
└─ SCRIPT_LANG_MAP — Language configuration and template mapping
```

### Data Flow
1. **CLI parsing**: `--url`, `--token`, optional `--name`, `--output`, `--script`, `--multi-skills`
2. **Tool discovery**: Async MCP connection to server; `list_tools()` fetches schema
3. **Schema parsing**: Extract inputSchema per tool; build ToolParam dataclass with name/type/required/description
4. **Template rendering**: Load Jinja2 environment from `mcp_cli/templates/`; render SKILL.md and call script
5. **Credential storage**: Create INI section; write URL and token; chmod 0o600
6. **Output**: Write to `~/.cursor/skills/{server-name}/`; set execute bit on call script

### Dependencies
- **fastmcp >= 2.3**: MCP client with Streamable HTTP transport
- **jinja2 >= 3.1**: Template rendering
- **Python >= 3.10**: Standard library only beyond these two

(Source: pyproject.toml, src/mcp_cli/ files, accessed 2026-03-13)

---

## Installation & Usage

### Installation

Install via pip (requires Python >= 3.10):

```bash
pip install mcpskills-cli
```

Or development install from repository:

```bash
pip install -e .
```

### Quick Start

**Generate skills from an MCP server:**

```bash
mcpskills-cli --url http://localhost:8027/mcp/abc123 --token mytoken --name my-db
```

Output:

```
Credentials saved to ~/.mcps/credentials (chmod 600)
Skill generated at ~/.cursor/skills/my-db
  SKILL.md (N tools)
  scripts/call.sh
Usage: bash ~/.cursor/skills/my-db/scripts/call.sh <tool_name> '{}'
```

**Invoke a tool via generated script:**

```bash
bash ~/.cursor/skills/my-db/scripts/call.sh list_tables '{}'
```

**Multi-skills mode (one skill per tool):**

```bash
mcpskills-cli --url http://localhost:8027/mcp/abc123 --token mytoken --name my-db --multi-skills
```

**Choose call script language:**

```bash
mcpskills-cli --url http://localhost:8027/mcp/abc123 --token mytoken --name my-db --script python
```

Supported: bash, python, node, go, rust

**Rotate token later (no regeneration):**

Edit `~/.mcps/credentials` directly and update the `token` value for the server section.

### Command-Line Reference

| Argument | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `--url` | string | — | yes | MCP server endpoint (Streamable HTTP) |
| `--token` | string | — | yes | Bearer token for authentication |
| `--name` | string | Derived from URL | no | Server identifier (skill dir name, credentials key) |
| `--output` | path | `~/.cursor/skills` | no | Output directory for generated skills |
| `--script` | choice | bash | no | Call script language: bash, python, node, go, rust |
| `--multi-skills` | flag | false | no | Generate one skill per tool (default: one skill for all) |

---

## Relevance to Claude Code Development

mcpskills-cli is relevant to the claude_skills ecosystem in two specific areas:

### 1. MCP Skill Generation and Integration

**Direct relevance**: mcpskills-cli is a tool for converting MCP servers into agent skills. This aligns with the claude_skills repository's emphasis on modular, loadable skill definitions. A user operating both Claude Code and an MCP server could use mcpskills-cli to automatically generate skills from custom MCP tools, eliminating manual skill documentation.

**Use case**: If a user has a custom database MCP server or data retrieval MCP server, they can run `mcpskills-cli --url <mcp_endpoint> --token <token>` to generate a skill directory compatible with Claude Code's skill loader.

### 2. Token Optimization Patterns

**Secondary relevance**: The documentation's analysis of single-skill vs. multi-skills generation, and recommendations for tool design, provide patterns applicable to any AI skill architecture. The discussion of token costs for schema discovery (list → get_schema → query vs. direct high-level call) informs skill granularity decisions.

**Applicability**: Teams designing new MCP servers or skills could apply the same reasoning to minimize agent context overhead.

---

## References

- [Repository](https://github.com/dhanababum/mcpskills-cli) (accessed 2026-03-13)
- [README.md — Why bake MCP into skills?](https://raw.githubusercontent.com/dhanababum/mcpskills-cli/main/README.md) (accessed 2026-03-13)
- [pyproject.toml — Dependencies and version](https://raw.githubusercontent.com/dhanababum/mcpskills-cli/main/pyproject.toml) (accessed 2026-03-13)
- [src/mcp_cli/cli.py — CLI argument parsing and workflow](https://raw.githubusercontent.com/dhanababum/mcpskills-cli/main/src/mcp_cli/cli.py) (accessed 2026-03-13)
- [src/mcp_cli/client.py — MCP client implementation](https://raw.githubusercontent.com/dhanababum/mcpskills-cli/main/src/mcp_cli/client.py) (accessed 2026-03-13)
- [src/mcp_cli/credentials.py — Credential storage](https://raw.githubusercontent.com/dhanababum/mcpskills-cli/main/src/mcp_cli/credentials.py) (accessed 2026-03-13)
- [src/mcp_cli/generator.py — Skill template rendering](https://raw.githubusercontent.com/dhanababum/mcpskills-cli/main/src/mcp_cli/generator.py) (accessed 2026-03-13)
- [src/mcp_cli/templates/ — Jinja2 templates](https://raw.githubusercontent.com/dhanababum/mcpskills-cli/main/src/mcp_cli/templates/) (accessed 2026-03-13)
- [License — MIT](https://raw.githubusercontent.com/dhanababum/mcpskills-cli/main/LICENSE) (accessed 2026-03-13)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [SkillKit](../skill-generation-tools/skillkit.md) | skill-generation-tools | cross-format skill translation; both transform tool schemas into SKILL.md |
| [narsil-mcp](./narsil-mcp.md) | mcp-ecosystem | mcpskills-cli can auto-generate skills from narsil-mcp's 90 tools |
| [octocode-mcp](./octocode-mcp.md) | mcp-ecosystem | mcpskills-cli can auto-generate skills from octocode-mcp's research tools |
