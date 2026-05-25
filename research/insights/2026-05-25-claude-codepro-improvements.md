# Improvement Proposals: Claude CodePro

**Research entry**: ./research/coding-agents/claude-codepro.md
**Generated**: 2026-05-25
**Patterns assessed**: 5
**Backlog items created**: 0
**Deferred (low confidence)**: 1
**Skipped (already covered or tracked)**: 4

---

## Improvement 1: MCP server lazy-loading guidance in mcp-integration skill

**Source pattern**: "Relevance to Claude Code Development > Context Window Optimization" — "The MCP Lazy Loading mechanism addresses a fundamental constraint in Claude Code workflows — context window limits. Intelligent server lazy loading allows developers to maintain extensive capabilities without constantly exhausting available context space." Also "Key Features > Enhanced Context and Capabilities via MCP Servers" — "MCP Lazy Loading — Intelligently reduces context usage by lazy loading MCP servers."
**Local system**: ./plugins/plugin-creator/skills/mcp-integration/SKILL.md
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred — confidence medium: research entry describes the pattern at README level only; the specific lazy-loading mechanism (how the upstream defers server startup, what triggers loading, how tools remain discoverable) is not documented in the entry. To raise to High, a follow-up research pass would need to read the upstream Claude CodePro source for the lazy-loading implementation (mentioned in `installer/steps/claude_files.py` per the entry's architecture table) and verify the mechanism is reproducible as Claude Code plugin guidance.

### Current state

`./plugins/plugin-creator/skills/mcp-integration/SKILL.md` covers four transport types (stdio,
SSE, HTTP, WebSocket), authentication patterns, environment variable expansion, tool naming
prefixes, and a "Lifecycle and Testing" section. The Lifecycle section states "MCP servers
start when the plugin loads. Connection is established before first tool use." There is no
mention of lazy loading, deferred server startup, or context-window cost as a selection
criterion. A grep for "lazy" returns zero matches in `SKILL.md` and zero matches in
`references/server-types-and-patterns.md`. Plugin authors with many MCP servers receive no
guidance on managing context cost from server-tool discovery being eager.

### Target state

`./plugins/plugin-creator/skills/mcp-integration/SKILL.md` includes a "Context Cost and Lazy
Loading" section (or equivalent reference file) that:

- Names eager tool discovery at plugin load as a context-window cost amplifier when multiple
  MCP servers are configured
- Describes the lazy-loading pattern: defer server startup until first tool invocation, OR
  use a router/proxy MCP server that fans out to multiple backend servers on demand
- States when to prefer lazy loading: plugin bundles 3+ MCP servers, or any single server
  exposes more than ~10 tools, or aggregate tool count would exhaust a meaningful fraction of
  context on session start
- Links to the Claude CodePro implementation (`installer/steps/claude_files.py` and
  related lazy-loader configuration) as a reference example

### Measurable signal

Run: `grep -c "lazy" ./plugins/plugin-creator/skills/mcp-integration/SKILL.md
./plugins/plugin-creator/skills/mcp-integration/references/server-types-and-patterns.md` —
returns a non-zero count after the change. Section heading "Context Cost and Lazy Loading"
(or equivalent) is present in the skill. The skill names at least one decision criterion
(server count or tool count) that triggers the lazy-loading recommendation.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| MCP server lazy-loading guidance | medium | Upstream mechanism not documented in research entry; needs follow-up read of `installer/steps/claude_files.py` in claude-codepro repo to confirm the specific lazy-loading pattern before authoring skill guidance. Without that, the skill update would be vague ("consider lazy loading") rather than actionable. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Development Environment as Code (dev container with one-command install) | Architectural incompatibility — this repo is a marketplace of plugins, not a single project consuming a dev container. The dev-container pattern targets developers who set up a workspace for one project; the marketplace pattern targets plugin distribution across many user projects. No translation is meaningful without rebuilding the repo's distribution model. |
| Two-phase Bootstrap Installation (outside container → inside container) | Architectural incompatibility — Claude Code plugins use `claude plugin install` and marketplace.json for distribution; there is no bootstrap-then-install phase. The pattern solves a problem (container setup) that does not exist in this distribution model. |
| Modular Rules System with `/context` verification | Already covered — `.claude/rules/*.md` files + `CLAUDE.md` Required Reading sections already implement a modular rules system. `/context` is a Claude Code built-in command for context verification and is not skill-owned. Adding skill documentation about a built-in verification command would duplicate behavior the user already has access to natively. |
| Spec-Driven `/setup` and `/plan` slash commands | Already covered — the development-harness plugin provides `/dh:add-new-feature` (Discovery + Planning + Architecture), `/dh:planning`, `/dh:planner-rt-ica`, `/dh:work-backlog-item`, and `/dh:discovery`. The local SAM 7-stage pipeline supersedes the upstream's two-command pattern with materially more depth (artifact registration, ARL touchpoints, voltron-style language composition). No gap. |
| Configuration verification commands (`/config`, `/ide`, `/context`) | Not skill-owned — these are Claude Code built-in commands. No local skill needs to document them as a new behavior. |
