---
name: mcpskills-cli - MCP-to-Skill Converter via Streamable HTTP Discovery
description: mcpskills-cli is a Python CLI tool that connects to MCP (Model Context Protocol) servers via Streamable HTTP transport, discovers available tools, and generates agent skill files (SKILL.md + call...
license: MIT (Copyright 2026 Dhana Babu)
metadata:
  topic: mcpskills-cli
  category: skill-generation-tools
  source_url: https://github.com/mcpskills-cli
  github: dhanababum/mcpskills-cli
  version: "0.1.2"
  verified: "2026-02-15"
  next_review: "2026-05-15"
---

## Overview

mcpskills-cli is a Python CLI tool that connects to MCP (Model Context Protocol) servers via Streamable HTTP transport, discovers available tools, and generates agent skill files (SKILL.md + call scripts) from those tools. The core thesis is that skills are more token-efficient than loading all MCP tools into agent context — skills are loaded on-demand while MCP tools all load at once. It uses fastmcp's Client and StreamableHttpTransport to enumerate tools, then renders Jinja2 templates to produce documented skill files and polyglot call scripts.

---

## Problem Addressed

| Problem | mcpskills-cli Solution |
|---------|------------------------|
| MCP tools all load into agent context simultaneously, consuming tokens | Converts MCP tools to on-demand skill files; agents load only relevant skills |
| MCP tool schemas are machine-readable JSON, not agent-friendly documentation | Generates SKILL.md files with parameter tables, usage examples, and descriptions |
| Calling MCP tools requires boilerplate HTTP/auth code per language | Generates call scripts in 5 languages (bash, python, node, go, rust) with credential handling |
| MCP server credentials are managed manually and insecurely | Stores credentials in `~/.mcps/credentials` (INI format, chmod 600) |
| Multi-tool servers force all-or-nothing context loading | `--multi-skills` mode generates separate skill directory per tool for granular loading |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Repository | dhanababum/mcpskills-cli | 2026-02-15 |
| PyPI Package | mcpskills-cli | 2026-02-15 |
| Version | 0.1.2 | 2026-02-15 |
| License | MIT | 2026-02-15 |
| Python Requirement | >= 3.10 | 2026-02-15 |
| Build System | hatchling | 2026-02-15 |
| Core Dependencies | fastmcp>=2.3, jinja2>=3.1 | 2026-02-15 |
| Supported Call Script Languages | 5 (bash, python, node, go, rust) | 2026-02-15 |
| Jinja2 Templates | 7 (2 skill + 5 call script) | 2026-02-15 |

---

## Key Features

### MCP Server Discovery

- **Streamable HTTP Transport**: Connects to MCP servers via fastmcp Client + StreamableHttpTransport
- **Bearer Token Auth**: Authenticates with `--token` flag; credentials stored in `~/.mcps/credentials` (INI format, chmod 600)
- **Tool Enumeration**: Lists all tools from connected MCP server with full schema extraction (parameters, types, descriptions)

### Skill File Generation

- **SKILL.md Output**: Generates documented skill files with tool descriptions, parameter tables, and usage guidance
- **Single Skill Mode**: All tools from a server consolidated into one SKILL.md (default; lowest token cost)
- **Multi-Skills Mode**: `--multi-skills` flag generates separate skill directory per tool (highest granularity, higher token cost)
- **Template-Based**: Uses Jinja2 templates (`skill.md.j2`, `skill_single.md.j2`) for consistent, customizable output

### Polyglot Call Scripts

- **5 Languages**: Generates call scripts in bash, python, node, go, and rust via `--script` flag
- **Unified Interface**: All scripts follow same invocation pattern: `./call.<ext> <tool_name> '{"key":"val"}'`
- **Template-Driven**: Each language has a dedicated Jinja2 template (`call_bash.sh.j2`, `call_python.py.j2`, `call_node.js.j2`, `call_go.go.j2`, `call_rust.rs.j2`)

### Token Optimization

- **Single Skill Consolidation**: Reduces SKILL.md reads from N (one per tool) to 1 (one per server)
- **On-Demand Loading**: Skills loaded only when relevant, unlike MCP tools which all load into context
- **Usage Guidance**: Generated SKILL.md includes usage patterns so agents can skip discovery calls
- **Server Design Recommendations**: Documentation advises MCP servers expose high-level composite tools to minimize round-trips

### CLI Interface

- **`--url`** (required): MCP server endpoint URL
- **`--token`** (required): Bearer token for authentication
- **`--name`**: Server name (default: derived from URL hostname)
- **`--output`**: Skills output directory (default: `~/.cursor/skills`)
- **`--script`**: Call script language selection (bash, python, node, go, rust)
- **`--multi-skills`**: Generate separate skill per tool instead of consolidated

---

## Technical Architecture

### Project Structure

<eg>
mcpskills-cli/
├── src/mcpskills_cli/
│   ├── cli.py            # CLI entry point (argparse)
│   ├── client.py         # fastmcp Client + StreamableHttpTransport
│   ├── credentials.py    # ~/.mcps/credentials (INI, chmod 600)
│   ├── generator.py      # Schema parsing + Jinja2 template rendering
│   └── templates/         # Jinja2 templates
│       ├── skill.md.j2         # Consolidated skill (all tools)
│       ├── skill_single.md.j2  # Per-tool skill
│       ├── call_bash.sh.j2     # Bash call script
│       ├── call_python.py.j2   # Python call script
│       ├── call_node.js.j2     # Node.js call script
│       ├── call_go.go.j2       # Go call script
│       └── call_rust.rs.j2     # Rust call script
└── docs/
    └── LOW_TOKEN_SKILLS.md     # Token optimization guidance
</eg>

### Generation Pipeline

<eg>
MCP Server (Streamable HTTP)
       │
       ├── fastmcp Client connects via StreamableHttpTransport
       │   └── Bearer token from --token or ~/.mcps/credentials
       │
       ├── client.list_tools() → tool schemas (name, params, types)
       │
       ├── generator.py parses schemas into template context
       │
       ├── Jinja2 renders templates
       │   ├── skill.md.j2 or skill_single.md.j2 → SKILL.md
       │   └── call_<lang>.<ext>.j2 → scripts/call.<ext>
       │
       └── Output to --output directory
           └── Default: ~/.cursor/skills/<server-name>/
               ├── SKILL.md
               └── scripts/
                   └── call.<ext>
</eg>

### Generated Output Structure

<eg>
# Single skill mode (default)
~/.cursor/skills/<server-name>/
├── SKILL.md              # Documents all tools with parameters
└── scripts/
    └── call.<ext>        # Calls any tool: ./call.<ext> <tool_name> '{"key":"val"}'

# Multi-skills mode (--multi-skills)
~/.cursor/skills/<server-name>/
├── <tool-1>/
│   ├── SKILL.md
│   └── scripts/call.<ext>
├── <tool-2>/
│   ├── SKILL.md
│   └── scripts/call.<ext>
└── ...
</eg>

### Key Dependencies

| Dependency | Purpose |
|------------|---------|
| fastmcp >= 2.3 | MCP client, StreamableHttpTransport for server connection |
| jinja2 >= 3.1 | Template rendering for SKILL.md and call scripts |
| hatchling | Build system (PEP 517) |

---

## Installation and Usage

### Installation

```bash
pip install mcpskills-cli
```

### Basic Usage

```bash
# Generate skills from an MCP server (single skill mode)
mcpskills --url https://mcp.example.com/sse --token <bearer-token>

# Specify server name and output directory
mcpskills --url https://mcp.example.com/sse --token <token> \
  --name my-server --output ~/.claude/skills

# Generate Python call scripts
mcpskills --url https://mcp.example.com/sse --token <token> --script python

# Generate separate skill per tool
mcpskills --url https://mcp.example.com/sse --token <token> --multi-skills
```

### Using Generated Call Scripts

```bash
# Bash call script
./scripts/call.sh <tool_name> '{"param1": "value1"}'

# Python call script
./scripts/call.py <tool_name> '{"param1": "value1"}'

# Node.js call script
./scripts/call.js <tool_name> '{"param1": "value1"}'
```

---

## Relevance to Claude Code Development

### Applications

1. **MCP-to-Skill Conversion Pattern**: Demonstrates a concrete pipeline for converting MCP server tool schemas into documented skill files. This pattern could be adapted to generate Claude Code-compatible skills from any MCP server.

2. **Token Optimization Reference**: The project's core thesis (skills are more token-efficient than MCP tools in agent context) aligns with Claude Code's on-demand skill loading model. The `docs/LOW_TOKEN_SKILLS.md` provides quantitative reasoning for this approach.

3. **Template-Based Skill Generation**: The Jinja2 template approach for generating SKILL.md files is a pattern applicable to our skill-creator workflow — templates ensure consistent structure while allowing customization per tool.

### Patterns Worth Adopting

1. **Credential Store with File Permissions**: The `~/.mcps/credentials` pattern (INI format, chmod 600) is a minimal but secure approach to MCP server credential management.

2. **Consolidated vs. Granular Skill Modes**: The single-skill vs. multi-skills trade-off (token cost vs. granularity) is a design decision worth codifying in skill generation guidance.

3. **Polyglot Call Script Templates**: Generating call scripts in multiple languages from templates ensures consistent interfaces regardless of the agent's runtime environment.

4. **fastmcp Client Usage**: The `client.py` module is a reference implementation for connecting to MCP servers programmatically via Streamable HTTP transport with bearer token authentication.

### Integration Opportunities

1. **Output Directory Adaptation**: Default output targets `~/.cursor/skills`. Changing `--output` to `~/.claude/skills` makes generated skills immediately available to Claude Code.

2. **Skill-Creator Pipeline Extension**: mcpskills-cli's template-based generation could feed into or complement the plugin-creator skill's workflow for producing validated skills from MCP server discovery.

3. **fastmcp Client Reuse**: The fastmcp Client + StreamableHttpTransport pattern could be reused in Claude Code hooks or scripts that need to interact with MCP servers for tool discovery.

### Considerations

1. **Early Version (0.1.2)**: The project is in early development. API stability and feature completeness are not guaranteed.

2. **Cursor-Centric Defaults**: Default output directory is `~/.cursor/skills`, indicating primary target is Cursor IDE. Claude Code usage requires explicit `--output` override.

3. **Streamable HTTP Only**: Only supports Streamable HTTP transport. MCP servers using stdio or SSE transport are not supported by this tool.

4. **Minimal Dependency Footprint**: Only two runtime dependencies (fastmcp, jinja2), making integration lightweight. However, fastmcp >= 2.3 is a specific version requirement that may conflict with other fastmcp consumers.

5. **No Skill Validation**: Generated SKILL.md files are not validated against any schema. Output quality depends entirely on template correctness and input tool schema completeness.

6. **MIT License**: Permissive license with no copyleft requirements. Suitable for integration, modification, and redistribution.

---

## References

1. **mcpskills-cli GitHub Repository** - <https://github.com/dhanababum/mcpskills-cli> (accessed 2026-02-15)
2. **mcpskills-cli PyPI Package** - <https://pypi.org/project/mcpskills-cli/> (accessed 2026-02-15)
3. **mcpskills-cli README** - <https://github.com/dhanababum/mcpskills-cli/blob/main/README.md> (accessed 2026-02-15)
4. **mcpskills-cli Token Optimization Docs** - <https://github.com/dhanababum/mcpskills-cli/blob/main/docs/LOW_TOKEN_SKILLS.md> (accessed 2026-02-15)
5. **fastmcp Documentation** - <https://github.com/jlowin/fastmcp> (accessed 2026-02-15)
6. **MCP Protocol Specification** - <https://modelcontextprotocol.io/llms-full.txt> (accessed 2026-02-15)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [prompt-optimizer](../prompt-engineering/prompt-optimizer.md) | prompt-engineering | referenced by prompt-optimizer (prompt-engineering) |
| [claude-scientific-skills](./claude-scientific-skills.md) | skill-generation-tools | referenced by claude-scientific-skills (skill-generation-tools) |
| [mattpocock-skills](./mattpocock-skills.md) | skill-generation-tools | referenced by mattpocock-skills (skill-generation-tools) |
