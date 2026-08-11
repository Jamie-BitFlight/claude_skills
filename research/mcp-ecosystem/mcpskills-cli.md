---
resource: mcpskills-cli
url: https://github.com/dhanababum/mcpskills-cli
license: MIT
version: 0.1.2
release_date: 2026-02-26
repository: GitHub
language: Python
status: active
---

# mcpskills-cli

## Identity

**Name**: mcpskills-cli
**Version**: 0.1.2 (as of 2026-02-26)
**License**: MIT
**Repository**: <https://github.com/dhanababum/mcpskills-cli>
**Author**: dhanababu (GitHub: @dhanababum, joined 2018)
**Primary Language**: Python
**Package**: Available via pip (`pip install mcpskills-cli`)
**Python Requirement**: Python >= 3.10

## Purpose and Context

mcpskills-cli is a command-line tool that bridges Model Context Protocol (MCP) servers with AI agent skills. Its core function is discovered in the README:

> "Generate Agent Skills from MCP server tools. Connects via Streamable HTTP, discovers tools, and outputs a skill with schema docs and a call script in the language of your choice."

The tool solves a specific problem in AI agent architecture: MCP servers expose tools directly to agents, which causes token pollution because agents load all available tools into context. mcpskills-cli transforms tools from Streamable HTTP MCP endpoints into statically-generated skill files, which agents load only when needed, reducing token consumption.

**Design rationale** (from README):

> "Skills are easy to understand, static, edit, and most coding and non-coding agents are adopting them. Traditional MCPs load all tools into context and pollute the agent; token penalty is also costly because of loading every tool. This is why we transform MCP into skills: skills reduce token consumption because the agent does not load all skills into context—it only loads them when necessary."

## Features and Capabilities

### 1. MCP Tool Discovery

The tool connects to a running MCP server via Streamable HTTP (fastmcp protocol) and automatically discovers all available tools.

**Implementation**: Uses `fastmcp >= 2.3` library with `StreamableHttpTransport`:
- Connects to MCP server endpoint (e.g., `http://localhost:8027/mcp/abc123`)
- Authenticates via Bearer token (passed as command-line argument)
- Calls `client.list_tools()` async method to fetch tool metadata
- Returns structured tool definitions including name, description, and JSON schema for input parameters

**Source**: `src/mcp_cli/client.py` implements `list_tools(url, token)` which wraps async `_list_tools()` and executes via `asyncio.run()`.

### 2. Skill Generation

mcpskills-cli generates two output formats from discovered MCP tools:

#### Single Skill Mode (Default)

Generates one SKILL.md file documenting all MCP tools plus a multi-tool call script.

**Output structure**:

```
~/.cursor/skills/<server-name>/
  SKILL.md              # Frontmatter (YAML name/description) + tool documentation
  scripts/
    call.<ext>          # Executable call script (language varies: .sh, .py, .js, .go, .rs)
```

**SKILL.md template** (from `skill.md.j2`):
- YAML frontmatter with server name and comma-separated tool list
- Section for each tool with:
  - Tool name as heading
  - Tool description extracted from MCP schema
  - Parameter list with type, required/optional status, and description
  - Execute example showing invocation command

#### Multi-Skills Mode

With `--multi-skills` flag, generates one SKILL.md per tool:

**Output structure**:

```
~/.cursor/skills/<server-name>-<tool-name-1>/
  SKILL.md
  scripts/call.<ext>

~/.cursor/skills/<server-name>-<tool-name-2>/
  SKILL.md
  scripts/call.<ext>
```

Each skill documents a single MCP tool.

**Trade-off**: Multi-skills increases disk footprint and agent skill-load count but allows fine-grained skill selection. Documentation recommends single-skill mode to minimize token consumption.

### 3. Polyglot Call Script Generation

Generated call scripts invoke MCP tools via Streamable HTTP protocol in the agent's preferred language.

**Supported languages**: bash, python, node, go, rust

**Template mapping**:
- bash: `call_bash.sh.j2` → `call.sh`
- python: `call_python.py.j2` → `call.py`
- node: `call_node.js.j2` → `call.js`
- go: `call_go.go.j2` → `call.go`
- rust: `call_rust.rs.j2` → `call.rs`

**Call script pattern** (bash example, `call_bash.sh.j2`):
1. Reads credentials from `~/.mcps/credentials` INI file
2. Extracts server URL and Bearer token from credentials by section name
3. Accepts tool name and JSON arguments as command-line parameters
4. Constructs MCP protocol request (JSON-RPC 2.0 format):

   ```json
   {
     "jsonrpc": "2.0",
     "method": "tools/call",
     "params": {"name": "<tool_name>", "arguments": <json_args>},
     "id": 1
   }
   ```

5. POSTs to MCP server with:
   - Authorization header: `Bearer <token>`
   - Content-Type: `application/json`
   - Accept: `application/json, text/event-stream`
   - MCP-Protocol-Version: `2025-06-18`
6. Parses streaming response, extracts result/error, and outputs as JSON

**Invocation pattern**:

```bash
bash ~/.cursor/skills/my-db/scripts/call.sh <tool_name> '{"key":"value"}'
```

Each language template implements the same logic adapted to language idioms.

### 4. Credential Management

MCP server credentials (URL and bearer token) are stored securely in `~/.mcps/credentials` using INI format.

**Credential handling** (from `src/mcp_cli/credentials.py`):
- Directory created at `~/.mcps` with mode `0o700` (owner read/write/execute only)
- File `~/.mcps/credentials` written with mode `0o600` (owner read/write only)
- INI sections by server name: `[my-db]` contains `url` and `token` keys
- Credentials saved automatically during skill generation
- Token rotation supported by direct INI file editing

**Design**: Separates credential storage from skill generation. Skills reference the credentials section name (`server_name`), allowing tokens to be rotated without regenerating skills.

## Architecture

### Component Structure

```
mcpskills-cli (CLI entry point)
├─ client.py (MCP communication)
│  └─ fastmcp.Client + StreamableHttpTransport
├─ credentials.py (Credential storage/retrieval)
│  └─ ~/.mcps/credentials (INI format, chmod 600)
├─ generator.py (Skill template rendering)
│  ├─ SCRIPT_LANG_MAP (language config)
│  ├─ ToolParam + ToolInfo (dataclasses)
│  ├─ parse_tool() (schema extraction)
│  ├─ jinja2.Environment (template loading)
│  └─ generate_skill() (orchestration)
└─ templates/ (Jinja2 templates)
   ├─ skill.md.j2 (multi-tool skill)
   ├─ skill_single.md.j2 (single-tool skill)
   └─ call_*.j2 (language-specific call scripts)
```

### Data Flow

1. **CLI argument parsing** (`cli.py::main()`):
   - Required: `--url` (MCP server endpoint), `--token` (bearer token)
   - Optional: `--name` (server identifier, default: derived from URL), `--output` (skill directory, default: `~/.cursor/skills`), `--script` (language, default: bash), `--multi-skills` (flag)
   - Server name sanitized via regex: `[^a-z0-9]+` → `-`, lowercase

2. **Tool discovery** (`client.py::list_tools()`):
   - Async connection to MCP server via Streamable HTTP
   - Fetches tool list as structured objects
   - Returns list of dicts with name, description, inputSchema

3. **Schema parsing** (`generator.py::parse_tool()`):
   - Extracts inputSchema from each tool
   - Maps schema properties to ToolParam dataclass (name, type, required/optional, description)
   - Builds example JSON args from required parameters

4. **Template rendering** (`generator.py::generate_skill()`):
   - Loads Jinja2 environment from `mcp_cli/templates/`
   - Renders SKILL.md template with tool metadata
   - Renders call script template (language-specific)
   - Writes to output directory, sets execute bit (`0o755`) on call script

5. **Credential storage** (`credentials.py::save()`):
   - Creates INI section for server name
   - Writes URL and token
   - Sets file mode `0o600`

## Command-Line Interface

```bash
mcpskills-cli --url <MCP_SERVER_URL> --token <TOKEN> [--name <NAME>] [--output <DIR>] [--script <LANG>] [--multi-skills]
```

**Arguments**:

| Argument | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `--url` | string | — | yes | MCP server endpoint (Streamable HTTP protocol) |
| `--token` | string | — | yes | Bearer token for authentication |
| `--name` | string | Derived from URL | no | Server identifier (used as skill dir name and credentials key) |
| `--output` | path | `~/.cursor/skills` | no | Output directory for generated skills |
| `--script` | choice | `bash` | no | Call script language: `bash`, `python`, `node`, `go`, `rust` |
| `--multi-skills` | flag | false | no | Generate one skill per tool (default: one skill for all tools) |

**Examples** (from README):

```bash
# Default: single skill with all tools, bash call script
mcpskills-cli --url http://localhost:8027/mcp/abc123 --token mytoken --name my-db

# Multi-skills mode: separate skill per tool
mcpskills-cli --url http://localhost:8027/mcp/abc123 --token mytoken --name my-db --multi-skills

# Python call script
mcpskills-cli --url http://localhost:8027/mcp/abc123 --token mytoken --name my-db --script python

# Node.js call script
mcpskills-cli --url http://localhost:8027/mcp/abc123 --token mytoken --name my-db --script node
```

## Dependencies

**Core dependencies** (from `pyproject.toml`):

| Package | Version | Purpose |
|---------|---------|---------|
| `fastmcp` | >= 2.3 | MCP client library with Streamable HTTP transport |
| `jinja2` | >= 3.1 | Template rendering for skill and call script generation |

**Python version**: >= 3.10

No other external dependencies. Build system is `hatchling`.

## Installation and Usage

### Installation

Via pip (requires Python >= 3.10):

```bash
pip install mcpskills-cli
```

Development install (from repository):

```bash
pip install -e .
```

### Basic Workflow

1. **Generate skills** from an MCP server:

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

2. **Invoke a tool** via generated script:

   ```bash
   bash ~/.cursor/skills/my-db/scripts/call.sh list_tables '{}'
   ```

3. **Rotate token** (if needed):
   - Edit `~/.mcps/credentials` directly
   - Update the token value for the server section
   - No skill regeneration needed

## Token Consumption Optimization

The documentation file `docs/Auto-Generated Skills for Low Token Consumption` provides guidance on reducing token usage when MCP tools are converted to skills. Key recommendations:

1. **Generate a single skill** (omit `--multi-skills`) so the agent loads one SKILL.md instead of multiple files
2. **Add usage guidance** in the skill to help agents choose the most direct tool without exploration (e.g., use `execute_query` directly for known tables instead of `list_tables` + `get_schema` + `execute_query`)
3. **Optional: embed schema at generation time** with a new flag like `--include-schema` (not yet implemented) to pre-populate table/column information in SKILL.md
4. **MCP server design**: expose high-level tools (e.g., `get_products(limit, offset, category)`) instead of low-level tools (e.g., `list_tables`, `get_schema`, `execute_query`)

**Quantified example** (from documentation):

For a query like "show me top 10 products":
- Multi-skills (current): 3 skill reads, 3 tool calls (list_tables + schema + query) = high token cost
- Single skill + guidance: 1 skill read, 1 tool call (execute_query only) = low token cost

## Statistics and Community

**Repository statistics** (as of 2026-02-26):
- **Stars**: 14
- **Forks**: 2
- **Open issues**: 0
- **Created**: 2026-02-14
- **Last updated**: 2026-02-26
- **Primary language**: Python

**Activity**: Single commit in git history (recent). Repository is actively maintained by author dhanababu.

## Limitations and Caveats

### No Limitations Documented

The official documentation does not explicitly document limitations. The following inferred constraints apply:

1. **MCP server requirement**: Requires a running MCP server accessible via HTTP with Streamable HTTP transport. Standard MCP servers over stdin/stdout are not supported (fastmcp client requires an HTTP endpoint).

2. **Bearer token requirement**: Authentication is bearer-token only. Other MCP authentication schemes (if any) are not supported.

3. **Credentials storage**: All credentials stored in plaintext INI file (encrypted storage not supported). Relies on filesystem permissions (`chmod 600`) for security.

4. **One-way transformation**: Generated skills are static snapshots of MCP tools at generation time. Tool schema changes require skill regeneration.

5. **Schema documentation completeness**: Skill quality depends on completeness of MCP tool metadata (descriptions, parameter types). Sparse or missing schema in MCP server results in minimal skill documentation.

6. **Network-dependent**: Call scripts require runtime network access to MCP server. Offline or disconnected environments cannot invoke tools.

No other limitations are documented in reviewed sources (README.md, docs/, or source code comments).

## Relevance to Claude Code Development

mcpskills-cli is relevant to the claude_skills ecosystem in two specific areas:

### 1. MCP Skill Generation and Integration

**Direct relevance**: mcpskills-cli is a tool for converting MCP servers into agent skills. This aligns with the claude_skills repository's emphasis on modular, loadable skill definitions. A user operating both Claude Code and an MCP server could use mcpskills-cli to automatically generate skills from custom MCP tools, eliminating manual skill documentation.

**Use case**: If a user has a custom database MCP server or data retrieval MCP server, they can run `mcpskills-cli --url <mcp_endpoint> --token <token>` to generate a skill directory compatible with Claude Code's skill loader.

### 2. Token Optimization Patterns

**Secondary relevance**: The documentation's analysis of single-skill vs. multi-skills generation, and recommendations for tool design, provide patterns applicable to any AI skill architecture. The discussion of token costs for schema discovery (list → get_schema → query vs. direct high-level call) informs skill granularity decisions.

**Applicability**: Teams designing new MCP servers or skills could apply the same reasoning to minimize agent context overhead.

## References

- **Repository**: <https://github.com/dhanababum/mcpskills-cli> (accessed 2026-03-13)
- **README.md**: `Why bake MCP into skills?` section, purpose and rationale (accessed 2026-03-13)
- **Installation and Usage**: Command-line examples and output structure (README.md, accessed 2026-03-13)
- **Source code**:
  - `pyproject.toml` — dependencies, version, entry point (accessed 2026-03-13)
  - `src/mcp_cli/cli.py` — CLI argument parsing, workflow (accessed 2026-03-13)
  - `src/mcp_cli/client.py` — MCP client implementation via fastmcp (accessed 2026-03-13)
  - `src/mcp_cli/credentials.py` — credential storage and retrieval (accessed 2026-03-13)
  - `src/mcp_cli/generator.py` — tool parsing and skill template rendering (accessed 2026-03-13)
  - `src/mcp_cli/templates/` — Jinja2 templates for skill and call scripts (accessed 2026-03-13)
- **Documentation**: `docs/Auto-Generated Skills for Low Token Consumption` — token optimization guidance (accessed 2026-03-13)
- **GitHub API metadata**: Repository stats (stargazers, forks, created/updated dates) (accessed 2026-03-13)
- **LICENSE**: MIT License, copyright 2026 Dhana Babu (accessed 2026-03-13)

## Freshness Tracking

**Entry created**: 2026-03-13
**Last source review**: 2026-03-13
**Next review recommended**: 2026-06-13 (3 months)

### Confidence by Section

| Section | Confidence | Notes |
|---------|-----------|-------|
| Identity/Metadata | high | Direct from pyproject.toml and GitHub API |
| Purpose | high | Official README documentation |
| Features | high | Complete source code review and template examination |
| Architecture | high | Full source code inspection with data flow traced |
| Command-line Interface | high | Source code (cli.py) and README examples verified |
| Dependencies | high | Direct from pyproject.toml |
| Installation and Usage | high | README and source code examples |
| Token Consumption Optimization | high | Complete documentation file reviewed |
| Statistics and Community | high | GitHub API metadata verified |
| Limitations | medium | No explicit limitations documented; inferred from implementation details |
| Relevance to Claude Code | medium | Assessed based on MCP ecosystem alignment and skill architecture overlap |

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [SkillKit](../skill-generation-tools/skillkit.md) | skill-generation-tools | cross-format skill translation and aggregation; SkillKit auto-translates generated skills between 32 agent formats |
| [Skill Seekers](../skill-generation-tools/skill-seekers.md) | skill-generation-tools | complementary documentation-to-skill automation; both transform external sources into SKILL.md format |
| [SkillsMP](../skill-generation-tools/skillsmp.md) | skill-generation-tools | unified SKILL.md marketplace; mcpskills-cli output targets the SKILL.md standard that SkillsMP indexes |
