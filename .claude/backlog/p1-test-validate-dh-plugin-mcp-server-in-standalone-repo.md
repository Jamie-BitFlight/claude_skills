---
name: 'test: Validate dh plugin MCP server in standalone repo'
description: "Verify that the bundled backlog MCP server starts correctly when the dh plugin is installed on a project that has no pre-existing backlog_core workspace entry. The .mcp.json uses ${CLAUDE_PLUGIN_ROOT} — this must be validated outside the development repo.\n\nTest steps:\n1. Use a separate repo with no .claude/skills/backlog/ and no uv workspace entry for backlog_core\n2. Install the dh plugin via /plugin install\n3. Verify mcp__backlog__* tools appear in the session\n4. Call backlog_list and confirm it returns successfully"
metadata:
  topic: test-validate-dh-plugin-mcp-server-in-standalone-repo
  source: User request
  added: '2026-03-19'
  priority: P1
  type: Feature
  status: needs-grooming
  issue: '#851'
  last_synced: '2026-03-21T08:07:30Z'
---

## Story

As a **developer using Claude Code skills**, I want to **test: validate dh plugin mcp server in standalone repo** so that **the tooling becomes more capable and complete**.

## Description

Verify that the bundled backlog MCP server starts correctly when the dh plugin is installed on a project that has no pre-existing backlog_core workspace entry. The .mcp.json uses ${CLAUDE_PLUGIN_ROOT} — this must be validated outside the development repo.

Test steps:
1. Use a separate repo with no .claude/skills/backlog/ and no uv workspace entry for backlog_core
2. Install the dh plugin via /plugin install
3. Verify mcp__backlog__* tools appear in the session
4. Call backlog_list and confirm it returns successfully

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: User request
- **Priority**: P1
- **Added**: 2026-03-19
- **Research questions**: None
