# Improvement Proposals: Screenpipe

**Research entry**: ./research/mcp-ecosystem/screenpipe.md
**Generated**: 2026-05-02
**Patterns assessed**: 5
**Backlog items created**: 0
**Deferred (low confidence)**: 2
**Skipped (already covered or tracked)**: 3

---

## Improvement 1: Document transport-aware tool exposure (HTTP subset vs stdio full toolset) in fastmcp-creator

**Source pattern**: "demonstrates progressive disclosure (basic tools in HTTP, full toolset in stdio)" — § Relevance to Claude Code Development > 3. MCP server design and integration. Also: "The HTTP server exposes `search_content` only. Full toolset (export-video, list-meetings, activity-summary, search-elements, frame-context) is available in stdio mode." — § Limitations > 6. MCP HTTP transport feature parity.
**Local system**: plugins/fastmcp-creator/skills/fastmcp-creator/references/deployment.md (and references/transforms.md for tag-based exposure)
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred — confidence Medium: pattern present in spirit via tag-based access control (`mcp.disable(tags={"admin"})` in transforms.md:270, `Visibility(False, tags={"admin"})` in transforms.md:623), but the specific "different toolsets per transport" recipe is not codified

### Current state

deployment.md describes transport selection (`stdio`, `http`, `sse`, `streamable-http`) at lines 399, 536, 546, and transforms.md:261-291 documents tag-based enable/disable mechanisms. Neither file explicitly demonstrates how to gate a tool by transport — e.g., "expose `read` tools over HTTP, but only expose `write` tools over stdio". A FastMCP author building a remote-friendly server today must combine fragments from three reference files and infer the integration pattern. Search for "transport-specific\|tool subset\|expose.*differently\|tool exposure" across fastmcp-creator references returns zero hits.

### Target state

deployment.md (or a new "Transport-Specific Tool Exposure" subsection) contains a worked example: register all tools with tags, then conditionally apply `mcp.disable(tags={...})` based on the active transport at startup. Example demonstrates a stdio entrypoint that keeps all tools enabled vs an http entrypoint that disables `tags={"local-only"}`. The transforms.md cross-reference points back to deployment.md for the transport-aware variant.

### Measurable signal

Run: `grep -l "transport.*tool\|tool.*transport\|stdio.*subset\|http.*subset" plugins/fastmcp-creator/skills/fastmcp-creator/references/deployment.md` returns at least one match. The deployment.md file contains a Python code block where the same `FastMCP` instance is conditionally configured based on detected transport (env var or CLI flag), and a comment block citing screenpipe-mcp as the inspiration.

---

## Improvement 2: Document multi-layer enforcement pattern for MCP data-permission middleware

**Source pattern**: "Three-layer enforcement (skill gating, agent interception, server middleware with cryptographic tokens) prevents compromised agents from accessing denied data." — § Key Features > 5. Plugin system — Pipes. Also: "How to enforce data access boundaries at enforcement layers (skill gating, agent interception, middleware tokens)" and "let admins control what AI can access without trusting the AI to 'behave' — three-layer enforcement prevents circumvention even if an agent is compromised" — § Relevance to Claude Code Development > 2. Privacy-first AI automation.
**Local system**: plugins/fastmcp-creator/skills/fastmcp-creator/references/middleware.md
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred — confidence Medium: middleware.md:173 mentions "tag-based auth" via execution hooks but does not demonstrate the pattern of layered enforcement (component decoration + middleware token verification + downstream server validation) needed to defend against a compromised agent. Specific threat model (compromised agent re-invoking denied tools) is not addressed in the existing reference

### Current state

middleware.md documents tag-based access control using component metadata lookup at execution time (single layer). auth.md documents bearer-token verification at HTTP transport (single layer). Neither file shows how to compose these into a defense-in-depth chain where: (1) the component declares its required scope, (2) the middleware verifies a per-request signed token bearing the caller's permitted scopes, and (3) a downstream provider validates the same token before forwarding the call. There is no threat model section describing what each layer defends against.

### Target state

middleware.md gains a "Layered Enforcement" subsection citing screenpipe's three-layer model. The subsection enumerates: (1) declarative component-level guards (`@mcp.tool(tags={"sensitive"})`), (2) request-level middleware that validates a signed token whose claims include the permitted tag set, (3) provider-level guard that re-validates the same token at proxy/mount boundaries. Includes a worked example showing how a compromised agent that bypasses layer 1 by direct tool call is still blocked by layers 2 and 3.

### Measurable signal

Run: `grep -n "layered\|defense.in.depth\|three.layer\|compromised agent" plugins/fastmcp-creator/skills/fastmcp-creator/references/middleware.md` returns at least one match. middleware.md contains a Python code example that registers a `Middleware` subclass which calls `verify_signed_scopes(ctx)` and rejects mismatched scope claims with a structured error.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Transport-aware tool subsetting | Medium | Pattern exists in spirit via tag-based exposure; need to verify whether a worked example would add load-bearing value or just restate combinable primitives |
| Multi-layer enforcement model | Medium | middleware.md may already imply this via tag-based auth + bearer auth composition; would need verification that the existing examples leave the threat model unaddressed before adding a dedicated section |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Bearer token auth on HTTP with stdio fallback | Already covered: auth.md:11 explicitly states "Authentication applies only to FastMCP's HTTP-based transports (`http` and `sse`). STDIO transport inherits security from its local execution environment". The screenpipe pattern matches the existing FastMCP guidance. |
| Event-driven architecture / hash-based deduplication | Not actionable in this repo's plugin architecture. Screenpipe's pattern (OS event hooks + frame hashing) is for continuous-capture desktop applications, not Claude Code plugins. swarm-patterns.md:514 already documents the inbox-based "no polling" pattern for this repo's use case (agent coordination). |
| Pipe markdown files with YAML frontmatter for AI agent definitions | Already covered with a different mechanism. Claude Code agents already use frontmatter (`name`, `description`, `model`, `tools`) per .claude/rules/frontmatter-requirements.md. The `tools:` field provides the equivalent of screenpipe's `allow-apps`/`deny-apps` scope-restriction at the tool level. Agent runtime difference makes the screenpipe pipe-scheduling pattern non-portable. |
