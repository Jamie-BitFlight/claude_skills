---
name: fastmcp-creator plugin v3 overhaul — authoritative skill + meta-example MCP server
description: "Overhaul the fastmcp-creator plugin to be a comprehensive, authoritative FastMCP v3 skill with zero speculation, grounded entirely in the local v3 docs at `.worktrees/fastmcp/docs/` and real-world GitHub usage.\n\n## Context from brainstorming session (2026-03-05)\n\n**Scope decisions captured from user Q&A:**\n\n- **Reference structure**: Split into dedicated reference files per major topic (not monolithic, not hybrid). SKILL.md is dense capability map pointing to references.\n- **Coverage**: All three FastMCP v3 pillars — Servers, Clients, AND Apps. Authoritative on all three.\n- **SKILL.md style**: Dense with capabilities and the situations they should be used in, with references to read to enable them. Zero speculation. Every claim sourced from actual v3 docs or real-world GitHub usage.\n- **Research requirement**: Use agents to read the local docs, research online, find apps using FastMCP v3 on GitHub sorted by stars, check how they use it. Real-world patterns, not theory.\n- **Runnable MCP server**: YES — actual runnable Python source code at `plugins/fastmcp-creator/server/`. Not just examples in reference files.\n- **Why runnable**: FastMCP v3 can serve skills and prompts as MCP resources — so the server will serve the skill's own reference content as MCP resources and prompts. Self-documenting, self-teaching.\n- **Plugin registration**: Server registered in `plugin.json` via `mcpServers` field → auto-available in every user's Claude Code session on plugin install. No manual configuration.\n- **Sibling skills**: `fastmcp-creator` is the entrypoint. It should mention/link to `fastmcp-python-tests` and `fastmcp-client-cli`. Those are updated in a separate pass.\n- **Starting point**: Use `rwr:user-docs-to-ai-skill` FIRST on `.worktrees/fastmcp/docs/` to convert v3 docs into AI-optimized reference content. That is the correct starting point before any manual design.\n\n**What the v3 docs contain that the current skill is missing:**\n- `servers/` — providers (filesystem, proxy, local, skills, custom), transforms (namespacing, tool-search, resources-as-tools, prompts-as-tools, code-mode, tool-transformation), visibility, storage-backends, versioning, dependency-injection, lifespan, middleware, elicitation, sampling, pagination, progress, telemetry, testing, icons\n- `clients/` — full client SDK (transports, auth, sampling, elicitation, tasks, progress, roots, notifications)\n- `apps/` — prefab UI apps, patterns, low-level apps (brand new v3 concept)\n- `cli/` — running, inspecting, auth, generate-cli, install-mcp\n- `integrations/` — Anthropic, OpenAI, Gemini, FastAPI, GitHub, auth providers (Auth0, Azure, WorkOS, etc.)\n- `deployment/` — HTTP, server configuration, Prefect Horizon\n\n**Three deliverables:**\n\n1. **Runnable MCP server** (`plugins/fastmcp-creator/server/`) — A FastMCP v3 server that is itself the reference implementation. Serves its own reference files as MCP resources, exposes skill/prompt content as MCP prompts, provides helper tools (scaffold, validate, version-check, search-docs). Demonstrates every v3 feature it documents. Registered in `plugin.json` via `mcpServers`.\n\n2. **New reference files** — Generated via `rwr:user-docs-to-ai-skill` from local v3 docs, then enriched with real-world patterns from top-starred GitHub repos. Topics include: server-core, providers, transforms, auth, client-sdk, apps, advanced (visibility/versioning/storage/DI/middleware/telemetry), deployment, testing, integrations, migration (v2→v3), real-world-patterns.\n\n3. **Rewritten SKILL.md** — Dense capability map: trigger matrix (what user wants → which v3 feature → which reference), feature decision flowcharts, quick-start code grounded in v3 docs, meta-example callouts to the runnable server, links to sibling skills.\n\n**Process notes:**\n- Must follow full SAM process: groom → RT-ICA → `/add-new-feature` → SAM agents → plan-validator\n- Do NOT write plan manually as orchestrator\n- Start with `rwr:user-docs-to-ai-skill` on `.worktrees/fastmcp/docs/` as first research step\n\n**Out of scope this pass:** `fastmcp-python-tests` and `fastmcp-client-cli` skills (referenced from SKILL.md, updated separately). Evaluation harness scripts kept as-is."
metadata:
  topic: fastmcp-creator-plugin-v3-overhaul-authoritative-skill-meta-
  source: User request, brainstorming session 2026-03-05
  added: '2026-03-05'
  priority: completed
  type: Feature
  status: done
  issue: '#442'
  last_synced: '2026-03-05T20:37:16Z'
  plan: plan/tasks-1-fastmcp-creator-v3-overhaul.md
  groomed: '2026-03-05'
---

## Fact-Check

**Date**: 2026-03-05
**Claims checked**: 10
**VERIFIED**: 7 | **REFUTED**: 2 | **PARTIALLY REFUTED**: 1 | **INCONCLUSIVE**: 0

### Verified Claims
- FastMCP v3 docs contain: servers/, clients/, apps/, integrations/, deployment/ subdirectories (cli/ does NOT exist — CLI docs at docs/clients/cli.mdx and docs/python-sdk/)
- Apps concept (including low-level apps) is brand new to v3.0.0 — VersionBadge: 3.0.0, tag: NEW
- `rwr:user-docs-to-ai-skill` skill exists at plugins/the-rewrite-room/skills/user-docs-to-ai-skill/SKILL.md
- `mcpServers` field in plugin.json is valid and auto-starts on plugin enable (SOURCE: https://code.claude.com/docs/en/plugins-reference.md, 2026-03-05)
- All five providers documented: filesystem, proxy, local, skills, custom (docs/servers/providers/)
- Full client SDK documented: transports, auth, sampling, elicitation, tasks, progress, roots, notifications (docs/clients/)
- All named integrations documented: Anthropic, OpenAI, Gemini, FastAPI, GitHub, Auth0, Azure, WorkOS (docs/integrations/ — 26 total)

### Refuted / Corrected Claims
- **REFUTED**: `cli/` subdirectory — does NOT exist in docs/. CLI docs live at docs/clients/cli.mdx and docs/python-sdk/fastmcp-cli-*.mdx
- **REFUTED**: Transforms include `tool-search` and `code-mode` — these do NOT exist. Actual transforms: namespace, tool-transformation, resources-as-tools, prompts-as-tools, enabled (docs/servers/transforms/)
- **REFUTED**: CLI command `install-mcp` — does NOT exist. Actual: `install` group with subcommands: claude-code, claude-desktop, cursor, gemini-cli, goose, mcp-json, stdio
- **PARTIALLY REFUTED**: "prefab UI apps" — the Python-native app framework ships in FastMCP 3.1, NOT v3.0.0. v3.0.0 has the low-level HTML API only.
- **CORRECTED**: `testing` in docs/servers/ — actually at docs/patterns/testing.mdx. docs/servers/ contains 12 real features: visibility, storage-backends, versioning, dependency-injection, lifespan, middleware, elicitation, sampling, pagination, progress, telemetry, icons

## RT-ICA

**Decision**: APPROVED
**Goal**: Produce a comprehensive FastMCP v3 skill with authoritative reference files, a rewritten SKILL.md, and a runnable MCP server that auto-registers via plugin.json mcpServers field.

**Conditions**:
1. Local FastMCP v3 docs at .claude/worktrees/fastmcp/docs/ | AVAILABLE — 16 subdirectories confirmed
2. rwr:user-docs-to-ai-skill exists | AVAILABLE — plugins/the-rewrite-room/skills/user-docs-to-ai-skill/SKILL.md
3. Current fastmcp-creator plugin exists as baseline | AVAILABLE — plugins/fastmcp-creator/ with SKILL.md and 7 reference files
4. plugin.json mcpServers auto-registers servers | AVAILABLE — VERIFIED from official docs (2026-03-05)
5. FastMCP v3 actual feature set known (fact-checked) | AVAILABLE — corrected: no tool-search/code-mode, no install-mcp, prefab apps = v3.1, testing in patterns/
6. @python3-development:python-cli-architect agent available | AVAILABLE
7. GitHub research tools available for real-world patterns | AVAILABLE

**Missing**: None
**Assumptions to confirm**: None

## Groomed (2026-03-05)

### Priority

9/10 — Blocks authoritative FastMCP v3 guidance for plugin users. Current skill is v2-era with speculative content; v3 is production-ready with 16+ new features not documented. Unblocks downstream sibling skills (fastmcp-python-tests, fastmcp-client-cli) and plugin users building real-world servers.

### Impact

- Blocks: Plugin users, sibling skill completion, real-world FastMCP v3 adoption patterns
- Bottleneck: fastmcp-creator is the entrypoint skill; users get incomplete, speculative v2 content instead of authoritative v3 facts

### Benefits

- Authoritative v3 skill with zero speculation — every claim sourced from local v3 docs or GitHub real-world patterns
- Runnable MCP server that is itself a reference implementation — demonstrates every v3 feature it documents, self-teaching
- Dense SKILL.md capability map with trigger matrix, decision flowcharts, quick-start code
- Reference files generated from actual v3 docs via rwr:user-docs-to-ai-skill, enriched with real-world patterns from top-starred repos
- Server auto-registers via plugin.json mcpServers — available to every user on plugin install

### Expected Behavior

When user activates fastmcp-creator skill or explores its MCP server, they receive:
- Complete v3 feature coverage: servers (12 features), clients, apps (v3-new), CLI, 26 integrations, deployment patterns
- Authoritative facts backed by local v3 docs and GitHub examples
- Working code examples grounded in v3 docs, not theory
- Clear decision paths: when to use providers vs transforms, which features apply to their use case
- Links to sibling skills (fastmcp-python-tests, fastmcp-client-cli) for testing and client work

### Desired Structure

Three deliverables in one cohesive unit:

1. **Reference files** — Generated from `.claude/worktrees/fastmcp/docs/` via rwr:user-docs-to-ai-skill, grouped by topic (server-core, providers, transforms, auth, client-sdk, apps, advanced, deployment, testing, integrations, migration, patterns). Each file: atom extraction → thematic grouping → AI-optimized write, enriched with real-world GitHub usage.

2. **Rewritten SKILL.md** — Dense capability map: frontmatter (name, description, status), trigger matrix (what user wants → which v3 feature → which reference), feature decision flowcharts (Mermaid), quick-start code snippets grounded in v3 docs, meta-example callouts to runnable server, links to sibling skills.

3. **Runnable MCP server** — FastMCP v3 server at plugins/fastmcp-creator/server/ that serves its own reference files as MCP resources, exposes skill/prompt content as MCP prompts, provides helper tools (scaffold, validate, version-check, search-docs). Demonstrates every v3 feature documented. Registered in plugin.json via mcpServers field — auto-available on plugin install.

### Acceptance Criteria

1. rwr:user-docs-to-ai-skill successfully converts .claude/worktrees/fastmcp/docs/ → plugins/fastmcp-creator/skills/fastmcp-creator/references/
2. Reference files cover all 16 v3 docs subdirectories: servers, clients, apps, integrations, deployment, patterns, getting-started, development, tutorials, python-sdk, v2 (migration), plus testing at docs/patterns/
3. SKILL.md frontmatter valid; includes name, description (must mention v3 specialization)
4. SKILL.md body contains: 1+ trigger matrix or decision flowchart, 2+ quick-start code examples (FastMCP v3), links to all reference files, links to fastmcp-python-tests and fastmcp-client-cli
5. MCP server code at plugins/fastmcp-creator/server/ runs without error; implements: serve references as resources, expose skill content as prompts, provide helper tools
6. plugin.json mcpServers field includes server entry; validates via plugin_validator
7. All factual claims in SKILL.md and reference files have sources from .claude/worktrees/fastmcp/docs/ or cited GitHub repos
8. Fact-check verdicts from RT-ICA section integrated: v2→v3 corrections applied (no tool-search, no code-mode, no install-mcp, prefab-apps=v3.1, testing in patterns/)
9. No duplication: SKILL.md links to references, does not duplicate content
10. Linting: prek run passes on SKILL.md and all reference files

### Human Input

**From brainstorming session 2026-03-05:**

User confirmed three deliverables — runnable server required, not just examples. Confirmed v3 docs source at .claude/worktrees/fastmcp/docs/. Confirmed rwr:user-docs-to-ai-skill as first research step. Confirmed sibling skills (fastmcp-python-tests, fastmcp-client-cli) updated separately. Process: must follow full SAM path (groom → RT-ICA → /add-new-feature → agents → plan).

Fact-check verdicts provided in backlog item — confirm corrections are applied during planning:
- cli/ does NOT exist in docs/ — CLI docs at docs/clients/cli.mdx and docs/python-sdk/
- Transforms: namespace, tool-transformation, resources-as-tools, prompts-as-tools, enabled (NOT tool-search, NOT code-mode)
- No install-mcp command — actual install subcommands: claude-code, claude-desktop, cursor, gemini-cli, goose, mcp-json, stdio
- Prefab UI apps are v3.1, NOT v3.0.0 — v3.0.0 has low-level HTML API only
- Testing at docs/patterns/testing.mdx, NOT docs/servers/

### Resources

| Type | Item |
|------|------|
| Skill | /the-rewrite-room:user-docs-to-ai-skill |
| Skill | /fastmcp-creator (existing, to be replaced) |
| Skill | /fastmcp-python-tests (sibling, referenced, not updated this pass) |
| Skill | /fastmcp-client-cli (sibling, referenced, not updated this pass) |
| Source docs | .claude/worktrees/fastmcp/docs/ (16 subdirectories verified) |
| Agent | @plugin-creator:contextual-ai-documentation-optimizer |
| Agent | @python3-development:python-cli-architect (for MCP server code) |
| Agent | @development-harness:feature-researcher (for GitHub real-world patterns) |
| Prior work | plugins/fastmcp-creator/ (existing plugin, 7 reference files, v2-era) |
| Prior work | .claude/backlog/p1-fastmcp-creator-mcp-meta-tooling-mcp.md (sister item #260, MCP server patterns) |

### Dependencies

- Depends on: None (all source material available locally)
- Blocks: fastmcp-python-tests sibling skill refinement, fastmcp-client-cli sibling skill refinement, plugin users relying on v3 guidance

### Blockers

None. RT-ICA APPROVED — all conditions available: local v3 docs confirmed, rwr skill exists, current plugin baseline exists, mcpServers auto-registration verified, fact-check verdicts provided.

### Effort

High — Three separate deliverables (reference files via rwr, SKILL.md rewrite, MCP server implementation) with interdependencies. Estimated 3–5 days for planning + implementation phases if delegated via SAM workflow.

### Issue Classification

**Type**: unbounded-design
**Rationale**: Comprehensive plugin overhaul with three deliverables and open architecture decisions (reference file organization, SKILL.md structure, server feature set). Scope is defined but method is open to design exploration.
**Analysis Method**: design-framing
**Scenario Target**: Developer uses fastmcp-creator skill to build a FastMCP v3 server → they get accurate, complete v3 guidance with working examples instead of incomplete v2-era content

### Research

## MCP Ecosystem Context (Claude Code Integration)

The following Claude Code documentation URLs provide authoritative context on how MCP servers integrate with Claude Code agents, plugins, and the marketplace. These must be read during reference file generation to ensure the skill's guidance on MCP registration and configuration is accurate.

**Sub-agents and MCP** — how MCP gets configured when used on agents:
https://code.claude.com/docs/en/sub-agents.md

**Claude Code MCP overview** — the Claude Code writeup on MCP for Claude:
https://code.claude.com/docs/mcp.md

**Plugins and marketplace MCP configuration** — how plugins and marketplaces can be configured with MCP:
https://code.claude.com/docs/en/plugins.md

### Why This Matters

The runnable MCP server deliverable (Deliverable 1) registers via `plugin.json` `mcpServers` field. The skill's reference files must accurately describe:
- How MCP servers auto-start when a plugin is enabled
- How MCP tools appear in Claude Code agent tool lists
- How users can configure MCP servers manually vs. via plugin marketplace
- How sub-agents interact with MCP servers registered by plugins

These docs are the primary source for that guidance — not the FastMCP v3 worktree docs (which cover server implementation, not Claude Code integration).

### FastMCP Official LLM Context File

**FastMCP llms.txt** — the authoritative machine-readable list of FastMCP documentation for LLMs:
https://gofastmcp.com/llms.txt

This is the canonical index of FastMCP docs as intended for LLM consumption. It should be used during reference file generation as the primary source map — it lists every topic FastMCP considers documented and LLM-relevant, ensuring no significant v3 feature is missed and no deprecated content is included.

### Suggested Reference File Impact

- `real-world-patterns.md` — add Claude Code plugin MCP registration pattern
- `deployment.md` — add Claude Code as a deployment target alongside Prefect Horizon
- SKILL.md trigger matrix — add "register server in Claude Code" → `deployment.md` + plugin docs row
- All reference files — cross-check coverage against `gofastmcp.com/llms.txt` topic list before finalizing