---
name: migrate backlog to mcp server system
description: "The backlog-mcp FastMCP server is implemented (10 tools, 382 tests passing) and a CLI-to-MCP migration map exists at .claude/skills/backlog/CLI_TO_MCP_MIGRATION.md identifying ~40 files and ~34 direct CLI invocations that need updating. Tasks: (1) register backlog-mcp in .mcp.json, (2) update CLAUDE.md Backlog Operations policy section, (3) update session hooks (session-start-backlog.cjs, stop-backlog-reminder.cjs), (4) update skill files — work-backlog-item (19 invocations), create-backlog-item, groom-backlog-item, group-items-to-milestone, (5) update agent files — backlog-item-groomer, (6) update backlog/SKILL.md and backlog-tools-administrator/SKILL.md docs, (7) close the idea item 'Convert backlog.py into MCP server'. GitHub Actions backlog-sync.yml stays as CLI — CI has no MCP client."
metadata:
  topic: migrate-backlog-to-mcp-server-system
  source: Agent task — auto-derived from backlog MCP server completion
  added: '2026-03-01'
  priority: completed
  type: Feature
  status: done
  issue: '#329'
  groomed: '2026-03-01'
  last_synced: '2026-03-01T07:20:54Z'
  plan: plan/tasks-17-backlog-mcp-migration.md
---

## Story

As a **developer**, I want **The backlog-mcp FastMCP server is implemented (10 tools, 382 tests passing) a...** so that **backlog items are tracked in GitHub**.

## Description

The backlog-mcp FastMCP server is implemented (10 tools, 382 tests passing) and a CLI-to-MCP migration map exists at .claude/skills/backlog/CLI_TO_MCP_MIGRATION.md identifying ~40 files and ~34 direct CLI invocations that need updating. Tasks: (1) register backlog-mcp in .mcp.json, (2) update CLAUDE.md Backlog Operations policy section, (3) update session hooks (session-start-backlog.cjs, stop-backlog-reminder.cjs), (4) update skill files — work-backlog-item (19 invocations), create-backlog-item, groom-backlog-item, group-items-to-milestone, (5) update agent files — backlog-item-groomer, (6) update backlog/SKILL.md and backlog-tools-administrator/SKILL.md docs, (7) close the idea item 'Convert backlog.py into MCP server'. GitHub Actions backlog-sync.yml stays as CLI — CI has no MCP client.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Agent task — auto-derived from backlog MCP server completion
- **Priority**: P1
- **Added**: 2026-03-01
- **Research questions**: None

## Groomed (2026-03-01)

### Priority

9/10 — Unblocks ~34 direct CLI invocations across skills and agents; establishes MCP as the primary interface for backlog operations. Supports strategic shift toward protocol-based agent-server interaction.

### Impact

- Blocks: All work-backlog-item, create-backlog-item, groom-backlog-item, group-items-to-milestone skill workflows until migration completes
- Bottleneck: Current dual system (CLI + hooks) increases cognitive load on skill maintainers

### Benefits

- Agents invoke backlog operations via protocol instead of subprocess shelling
- Reduces skill maintenance surface (single interface documentation)
- Unblocks downstream MCP-based tooling (MCP consolidation analysis, MCP meta-tooling)
- Enables GitHub Actions CI to remain CLI-based without inconsistency

### Expected Behavior

After migration:
1. Skills and agents call backlog tools via MCP (not `uv run backlog.py`)
2. `.mcp.json` registers the backlog server with 10 MCP tools
3. Policy documentation in CLAUDE.md reflects MCP as primary interface, CLI as fallback
4. Session hooks reference MCP tool names instead of CLI command names
5. GitHub Actions workflow (`backlog-sync.yml`) stays CLI-based (CI has no MCP client)
6. MCP server runs with all 10 tools; 382 tests remain passing

### Desired Structure

```text
.mcp.json                                     [backlog MCP server registered]
.claude/CLAUDE.md                             [policy updated: MCP primary, CLI fallback for CI]
.claude/hooks/session-start-backlog.cjs       [references MCP tool names]
.claude/hooks/stop-backlog-reminder.cjs       [references MCP tool names]
.claude/skills/work-backlog-item/SKILL.md     [19 invocations → MCP calls]
.claude/skills/create-backlog-item/SKILL.md   [1 invocation → MCP call]
.claude/skills/groom-backlog-item/SKILL.md    [6 invocations → MCP calls]
.claude/skills/group-items-to-milestone/SKILL.md [1 invocation → MCP call]
.claude/skills/backlog/SKILL.md               [rewritten: MCP primary, CLI fallback]
.claude/skills/backlog-tools-administrator/SKILL.md [updated: dual-mode extension process]
.claude/agents/backlog-item-groomer.md        [1 invocation → MCP call]
.github/workflows/backlog-sync.yml            [stays CLI — no change required]
```

### Acceptance Criteria

1. backlog-mcp FastMCP server registered in `.mcp.json` with stdio transport
2. All 10 MCP tools callable (`backlog_add`, `backlog_list`, `backlog_view`, `backlog_sync`, `backlog_close`, `backlog_resolve`, `backlog_update`, `backlog_groom`, `backlog_normalize`, `backlog_pull`)
3. CLAUDE.md Backlog Operations section updated to reference MCP tools as primary interface
4. Session hooks updated to reference MCP tool names
5. All Tier 1–3 skill and agent files have CLI calls replaced with MCP tool invocations
6. Reference files (step-procedures.md, github-integration.md, close-resolve-procedure.md) updated
7. backlog/SKILL.md and backlog-tools-administrator/SKILL.md rewritten
8. 382 tests remain passing after all migrations
9. Idea item closed with reference to this item

### Resources

| Type | Item |
|------|------|
| MCP Server | .claude/skills/backlog/backlog_core/server.py (10 @mcp.tool decorators) |
| Operations Layer | .claude/skills/backlog/backlog_core/operations.py (shared backend) |
| Migration Map | .claude/skills/backlog/CLI_TO_MCP_MIGRATION.md (Tiers 1–7 inventory) |
| Skills | /work-backlog-item, /create-backlog-item, /groom-backlog-item, /group-items-to-milestone |
| Agents | @backlog-item-groomer, @backlog-mcp-validator |
| Tests | .claude/skills/backlog/tests/ (382 tests) |

### Dependencies

- Depends on: MCP server implementation (DONE — 382 tests passing); CLI_TO_MCP_MIGRATION.md (DONE)
- Blocks: Closure of idea-convert-backlogpy-into-an-mcp-server-using-fastmcp-skill.md

### Blockers

None — RT-ICA APPROVED. All prerequisites AVAILABLE or DERIVABLE.

### Effort

High — 7 skill files, 1 agent file, 2 policy/hook files, ~34 direct CLI invocations. Sequential: policy → hooks → skills → agents. Estimated: 2–3 hours for Tier 1–3.

## Fact-Check

Claims checked: 6 | VERIFIED: 5 | REFUTED: 1 | INCONCLUSIVE: 0
Refuted: CLI_TO_MCP_MIGRATION.md line 12 says '55 tests' but actual count is 382 tests (stale doc).
Verified: 10 MCP tools in server.py, 382 tests collected, migration map exists with ~40 files and ~34 Tier 1-3 invocations.

## RT-ICA

Decision: APPROVED
Goal: Replace CLI shell-out invocations in skills/agents with MCP tool calls.
Conditions:
1. MCP server (10 tools) | AVAILABLE | server.py verified
2. Test suite (382 tests) | AVAILABLE | pytest verified
3. Migration map | AVAILABLE | CLI_TO_MCP_MIGRATION.md verified
4. Migration map test count | MISSING | Doc says 55, actual 382 (stale — cosmetic fix)
5. .mcp.json registration | DERIVABLE | Standard FastMCP registration
6. File locations mapped | AVAILABLE | Migration map Tiers 1-3
7. CI stays CLI | AVAILABLE | Documented decision
8. Dual-mode strategy | DERIVABLE | Default MCP-only with CI exception