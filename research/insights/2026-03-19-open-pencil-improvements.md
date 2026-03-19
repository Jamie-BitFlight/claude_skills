# Improvement Proposals: OpenPencil

**Research entry**: ./research/ai-design-tools/open-pencil.md
**Generated**: 2026-03-19
**Patterns assessed**: 6
**Backlog items created**: 0
**Deferred (low confidence)**: 0
**Skipped (already covered or tracked)**: 6

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| MCP Server Implementation Example (dual transport stdio+HTTP, Zod validation, 90 tools) | Already covered by `plugins/fastmcp-creator/skills/fastmcp-creator/SKILL.md` which provides comprehensive MCP server creation guidance for FastMCP v3.1 including stdio and HTTP transports, Pydantic validation (equivalent to Zod), and declarative tool definitions. The local system is more mature and Python-native. |
| Structured Tool Definitions for AI (declarative specs, provider-agnostic, input schemas) | Already covered by `plugins/fastmcp-creator/skills/fastmcp-creator/SKILL.md` (`@mcp.tool` decorator with type-inferred schemas) and `plugins/plugin-creator/skills/skill-creator/SKILL.md` (structured skill definitions with frontmatter). OpenPencil's `tools.ts` pattern is equivalent to FastMCP's tool registration. |
| Multi-Provider LLM Integration (4 AI SDK providers, bring-your-own-key) | Already tracked in backlog as "SAM: Multi-Model Strategy" (#108, P2). The pattern of supporting multiple LLM providers is recognized but this repo operates within the Claude Code ecosystem where Anthropic is the primary provider. |
| P2P Collaboration via WebRTC (Trystero + Yjs CRDT, serverless co-editing) | Incompatible with this repo's architecture. This repository builds Claude Code skills, agents, and MCP servers -- not real-time collaborative editors. The CRDT-based co-editing pattern has no mapping to any local system. Agent concurrency is handled by SAM task orchestration, not real-time document sync. |
| Agent-Friendly File Format Access (CLI/MCP for .fig files without vendor APIs) | This is a usage recommendation (use OpenPencil's MCP server from Claude Code agents) rather than an adoptable design pattern. No local system gap exists -- the research entry describes how to consume OpenPencil, not a pattern to replicate. |
| Headless Automation (CLI + MCP for CI/CD design operations) | Same as above -- a usage pattern for consuming OpenPencil's tooling, not a design pattern to adopt into local systems. The repo already has headless CLI tools (sam CLI, backlog CLI) and MCP servers (backlog MCP). |

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| (none) | -- | All patterns were skipped rather than deferred |
