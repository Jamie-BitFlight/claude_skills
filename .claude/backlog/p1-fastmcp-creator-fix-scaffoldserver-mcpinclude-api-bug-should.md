---
name: 'fastmcp-creator: Fix scaffold_server() mcp.include() API bug — should use mcp.add_provider()'
description: 'The scaffold_server() tool in plugins/fastmcp-creator/server/server.py generates code using mcp.include(FileSystemProvider(...)) when the user requests the filesystem-provider feature. However, the correct v3 API is mcp.add_provider() — the server itself uses mcp.add_provider() on line 40, and providers.md documents mcp.add_provider() and mcp.mount() as the correct methods. mcp.include() does not appear in any v3 reference file. Any server scaffolded with the filesystem-provider feature will contain a broken API call. Fix: update the scaffold template string to use mcp.add_provider() instead of mcp.include().'
metadata:
  topic: fastmcp-creator-fix-scaffoldserver-mcpinclude-api-bug-should
  source: Code review — fastmcp-creator v3 overhaul (2026-03-05)
  added: '2026-03-05'
  priority: P1
  type: Bug
  status: needs-grooming
  plan: plan/tasks-22-fastmcp-creator-v3-overhaul-followup-1.md
  issue: '#514'
  last_synced: '2026-03-10T06:56:01Z'
---

## Story

As a **developer using Claude Code skills**, I want to **fastmcp-creator: fix scaffold_server() mcp.include() api bug — should use mcp.add_provider()** so that **the tooling becomes more capable and complete**.

## Description

The scaffold_server() tool in plugins/fastmcp-creator/server/server.py generates code using mcp.include(FileSystemProvider(...)) when the user requests the filesystem-provider feature. However, the correct v3 API is mcp.add_provider() — the server itself uses mcp.add_provider() on line 40, and providers.md documents mcp.add_provider() and mcp.mount() as the correct methods. mcp.include() does not appear in any v3 reference file. Any server scaffolded with the filesystem-provider feature will contain a broken API call. Fix: update the scaffold template string to use mcp.add_provider() instead of mcp.include().

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Code review — fastmcp-creator v3 overhaul (2026-03-05)
- **Priority**: P1
- **Added**: 2026-03-05
- **Research questions**: None
