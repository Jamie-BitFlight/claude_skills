---
name: 'backlog_sync and backlog_pull: add task=True background execution with ctx.report_progress()'
description: "backlog_sync and backlog_pull block the MCP client for the duration of all GitHub API calls (one per item). FastMCP v3 supports task=True on @mcp.tool which executes the tool as a background task — the client receives a task handle immediately and can poll status. Combined with ctx.report_progress(i, total), clients get a progress bar during batch operations.\n\nFiles affected: .claude/skills/backlog/backlog_core/server.py, pyproject.toml (add fastmcp[tasks] extra)\n\nChanges required:\n1. Add fastmcp[tasks] to optional dependencies in pyproject.toml\n2. Change @mcp.tool() to @mcp.tool(task=True) on backlog_sync and backlog_pull\n3. Add Progress dependency injection and emit ctx.report_progress(i, total) at each item iteration\n\nSource: fastmcp v3 docs servers/tasks.mdx — task=True + Progress injection for background tools"
metadata:
  topic: backlogsync-and-backlogpull-add-tasktrue-background-executio
  source: fastmcp-creator skill analysis of backlog_core/server.py
  added: '2026-03-07'
  priority: P2
  type: Feature
  status: needs-grooming
  issue: '#511'
  last_synced: '2026-03-12T12:48:09Z'
---

## Story

As a **developer using Claude Code skills**, I want to **backlog_sync and backlog_pull: add task=true background execution with ctx.report_progress()** so that **the tooling becomes more capable and complete**.

## Description

backlog_sync and backlog_pull block the MCP client for the duration of all GitHub API calls (one per item). FastMCP v3 supports task=True on @mcp.tool which executes the tool as a background task — the client receives a task handle immediately and can poll status. Combined with ctx.report_progress(i, total), clients get a progress bar during batch operations.

Files affected: .claude/skills/backlog/backlog_core/server.py, pyproject.toml (add fastmcp[tasks] extra)

Changes required:
1. Add fastmcp[tasks] to optional dependencies in pyproject.toml
2. Change @mcp.tool() to @mcp.tool(task=True) on backlog_sync and backlog_pull
3. Add Progress dependency injection and emit ctx.report_progress(i, total) at each item iteration

Source: fastmcp v3 docs servers/tasks.mdx — task=True + Progress injection for background tools

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: fastmcp-creator skill analysis of backlog_core/server.py
- **Priority**: P2
- **Added**: 2026-03-07
- **Research questions**: None
