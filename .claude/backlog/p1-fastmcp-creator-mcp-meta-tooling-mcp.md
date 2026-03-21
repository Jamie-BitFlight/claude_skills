---
name: 'fastmcp-creator: MCP Meta-Tooling MCP'
description: 'Wrap `connections.py`, `evaluation.py`, and `get_environment.py` as MCP tools. An MCP server that helps build MCP servers — agents could test connections, run evaluations, and inspect environments. Tools: `test_mcp_connection`, `run_evaluation`, `get_mcp_environment`, `validate_mcp_config`.'
metadata:
  topic: fastmcp-creator-mcp-meta-tooling-mcp
  source: 'GitHub Issue #260'
  added: '2026-03-03'
  priority: P1
  type: Feature
  status: needs-grooming
  issue: '#260'
  last_synced: '2026-03-21T03:46:23Z'
---

## Story

As a **developer**, I want **Wrap `connections** so that **backlog items are tracked in GitHub**.

## Description

Wrap `connections.py`, `evaluation.py`, and `get_environment.py` as MCP tools. An MCP server that helps build MCP servers — agents could test connections, run evaluations, and inspect environments. Tools: `test_mcp_connection`, `run_evaluation`, `get_mcp_environment`, `validate_mcp_config`.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: GitHub Issue #260
- **Priority**: P1
- **Added**: 2026-03-03
- **Research questions**: None

## Fact-Check

## Fact-Check Summary

**Item**: fastmcp-creator: MCP Meta-Tooling MCP
**Claims checked**: 4
**VERIFIED**: 1 | **REFUTED**: 2 | **INCONCLUSIVE**: 1

### Claim 1: "An MCP server that helps build MCP servers — agents could test connections, run evaluations, and inspect environments"
**Verdict**: VERIFIED (concept is valid)
- The source scripts exist: `connections.py`, `evaluation.py`, `get_environment.py` in `plugins/fastmcp-creator/skills/fastmcp-creator/scripts/`
- These scripts provide MCP connection management (stdio/SSE/HTTP), evaluation harness (QA-pair testing via Claude), and environment inspection
- SOURCE: Local codebase verification (2026-02-28)

### Claim 2: "No existing tool provides these capabilities" (implied by proposing to build it)
**Verdict**: REFUTED — Significant existing ecosystem tooling covers most proposed capabilities
- **MCP Inspector** (official Anthropic tool): Tests connections, inspects server tools/resources/prompts. Web UI + CLI. SOURCE: [modelcontextprotocol.io/docs/tools/inspector](https://modelcontextprotocol.io/docs/tools/inspector), [github.com/modelcontextprotocol/inspector](https://github.com/modelcontextprotocol/inspector)
- **mcp-validator** (Janix-ai): Protocol compliance testing, connection validation, tool schema validation. SOURCE: [github.com/Janix-ai/mcp-validator](https://github.com/Janix-ai/mcp-validator)
- **mcp-testing-framework** (haakco): Automated test generation, performance benchmarking, coverage analysis. SOURCE: [github.com/haakco/mcp-testing-framework](https://github.com/haakco/mcp-testing-framework)
- **MCP Server Creator** (GongRzhe): Meta-server that creates other MCP servers. SOURCE: [github.com/GongRzhe/MCP-Server-Creator](https://github.com/GongRzhe/MCP-Server-Creator)
- **mcp-cli / mcptools**: CLI tools for connection testing and server inspection. SOURCE: [github.com/apify/mcp-cli](https://github.com/apify/mcp-cli), [github.com/f/mcptools](https://github.com/f/mcptools)

### Claim 3: "validate_mcp_config" tool is novel
**Verdict**: REFUTED — mcp-validator already validates MCP protocol compliance; MCP Inspector validates server capabilities
- However, neither validates Claude Desktop/VS Code JSON configuration files specifically
- SOURCE: [github.com/Janix-ai/mcp-validator](https://github.com/Janix-ai/mcp-validator)

### Claim 4: The local evaluation.py provides unique value vs existing tools
**Verdict**: INCONCLUSIVE
- evaluation.py runs QA-pair evaluations using Claude as evaluator with tool-call metrics — this is a specific evaluation methodology
- mcp-testing-framework and mcp-evals provide different evaluation approaches
- Whether the local approach adds unique value over existing frameworks needs further analysis

## RT-ICA

## RT-ICA Assessment

**Goal**: Create an MCP server that wraps local fastmcp-creator scripts (connections.py, evaluation.py, get_environment.py) as MCP tools for meta-tooling

### Conditions

1. **Source scripts exist and are functional** | Status: AVAILABLE | The three scripts exist at `plugins/fastmcp-creator/skills/fastmcp-creator/scripts/` with well-defined interfaces
2. **No existing tool covers this exact use case** | Status: MISSING | Fact-check REFUTED this — MCP Inspector, mcp-validator, mcp-testing-framework, MCP Server Creator, and mcp-cli/mcptools collectively cover test_mcp_connection, run_evaluation, get_mcp_environment, and validate_mcp_config capabilities
3. **Unique value proposition defined** | Status: MISSING | The item does not articulate what this MCP adds beyond existing ecosystem tools. Wrapping local scripts as MCP tools is technically feasible but the differentiation from MCP Inspector + mcp-validator is unclear
4. **FastMCP 3.x framework available** | Status: AVAILABLE | The fastmcp-creator plugin already uses FastMCP for MCP server creation
5. **Target users identified** | Status: DERIVABLE | Implied: agents using Claude Code skills who build MCP servers. But existing tools (MCP Inspector CLI mode, mcptools) already serve this audience
6. **Evaluation methodology is unique** | Status: INCONCLUSIVE | evaluation.py uses Claude-as-evaluator with QA pairs — differs from mcp-testing-framework's approach, but whether this justifies a new MCP tool is unresolved

### Decision: UNBLOCKED

Human chose Option 2 (2026-02-28): Reframe as integration, no API keys. See ### Decision under ## Groomed for full details.

## Groomed (2026-02-28)

### Priority

3/10 — Generated from backlog audit without user demand signal; ecosystem overlap with MCP Inspector, mcp-validator, and mcp-testing-framework reduces novelty. Low priority until differentiation is clarified.

### Impact

- Blocks: Nothing (proposed tool does not unlock blocked work)
- Bottleneck: Ecosystem fragmentation — MCP tooling is dispersed; no single tool combines all four capabilities, but most individual capabilities already exist

### Scope

An MCP server that wraps `connections.py`, `evaluation.py`, and `get_environment.py` as callable MCP tools, allowing agents to programmatically test MCP server connections, run QA evaluations, inspect development environments, and validate MCP configuration.

### Output / Evidence

A FastMCP 3.x MCP server at `plugins/fastmcp-creator/mcp/server.py` with four tools:
- `test_mcp_connection`: Wraps `connections.py` logic to test server connectivity
- `run_evaluation`: Wraps `evaluation.py` to run Claude-as-evaluator QA pair testing
- `get_mcp_environment`: Wraps `get_environment.py` to inspect Python version, available servers, working directory
- `validate_mcp_config`: JSON schema validation for Claude Desktop/VS Code MCP configuration

### Dependencies

- Depends on: None
- Blocks: None (proposed meta-tooling does not unblock any committed work)

### Research

**Existing MCP meta-tooling ecosystem** (verified 2026-02-28):

| Tool | test_connection | run_evaluation | get_environment | validate_config |
|------|:---:|:---:|:---:|:---:|
| MCP Inspector (Anthropic) | Yes | Partial | Partial | No |
| mcp-validator (Janix-ai) | Yes | Yes | No | Yes |
| mcp-testing-framework (haakco) | Yes | Yes | No | No |
| MCP Server Creator (GongRzhe) | No | Implicit | No | No |
| mcp-cli / mcptools | Yes | Limited | Partial | No |

Sources: [MCP Inspector docs](https://modelcontextprotocol.io/docs/tools/inspector), [mcp-validator](https://github.com/Janix-ai/mcp-validator), [mcp-testing-framework](https://github.com/haakco/mcp-testing-framework), [MCP Server Creator](https://github.com/GongRzhe/MCP-Server-Creator), [awesome-mcp-devtools](https://github.com/punkpeye/awesome-mcp-devtools)

### Skills

- /fastmcp-creator — FastMCP server creation skill (contains the source scripts)

### Agents

- None identified

### Prior Work

- `plugins/fastmcp-creator/skills/fastmcp-creator/scripts/connections.py` — MCP connection management (stdio/SSE/HTTP)
- `plugins/fastmcp-creator/skills/fastmcp-creator/scripts/evaluation.py` — Claude-as-evaluator QA pair testing harness
- `plugins/fastmcp-creator/skills/fastmcp-creator/scripts/get_environment.py` — MCP development environment inspector

### Files

- `plugins/fastmcp-creator/skills/fastmcp-creator/scripts/connections.py`
- `plugins/fastmcp-creator/skills/fastmcp-creator/scripts/evaluation.py`
- `plugins/fastmcp-creator/skills/fastmcp-creator/scripts/get_environment.py`
- `plugins/fastmcp-creator/mcp/server.py` (proposed output location)

### Decision

**RT-ICA: UNBLOCKED** — Human provided direction (2026-02-28).

**Human decision**: Option 2 — Reframe as integration. Connect existing ecosystem MCP tools into the fastmcp-creator workflow. Do NOT build a new MCP server from scratch.

**Constraint**: No API keys required. All integrated tools must work without external API keys or authentication.

**Revised scope**: Instead of wrapping local scripts as a new MCP server, integrate existing no-auth-required tools into the fastmcp-creator skill workflow:
- **MCP Inspector** (npx @modelcontextprotocol/inspector) — test connections, inspect tools/resources/prompts. No API key needed.
- **mcp-validator** (Janix-ai) — protocol compliance testing. No API key needed.
- **mcptools** (f/mcptools) — CLI for connection testing and server inspection. No API key needed.

**Dropped from scope**:
- `run_evaluation` tool (evaluation.py uses Claude API as evaluator — requires ANTHROPIC_API_KEY, violates no-API-key constraint)
- Building a new FastMCP server at plugins/fastmcp-creator/mcp/server.py
- `validate_mcp_config` as a standalone MCP tool (mcp-validator already covers this)

**What remains**:
1. Add integration steps to the /fastmcp-creator skill that invoke MCP Inspector and mcp-validator after server creation
2. Add mcptools as a recommended dependency for agent-driven MCP server testing
3. Document the ecosystem tools in the fastmcp-creator skill references

**Next step**: Convert to a planning item via /work-backlog-item when ready to implement

### Effort

Medium — FastMCP implementation is straightforward (wrapping existing scripts), but blocked on strategic alignment. Once differentiation is clarified, implementation is ~2-3 days.
