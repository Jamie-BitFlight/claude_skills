---
name: backlog_list MCP tool needs server-side filtering params (title, section, status)
description: "Agents pipe backlog_list JSON output through python3 -c to filter by title substring, section, or status — observed in work-backlog-item Step 0 (interactive browser), Step 1 (title search), and groom-backlog-item Step 1 (section filter). This is a design error: if the consumer must post-process to get useful results, the tool's interface is incomplete. Add optional filter params to backlog_list: title (case-insensitive substring match), section (P0|P1|P2|Ideas), status (open|closed|in-progress). Apply filters server-side in operations.list_items() before returning results. backlog_view already handles single-item lookup by selector — this gap is specifically the list-then-filter pattern for subsets. Also add the same params to the CLI (backlog.py list --title X --section P1 --status open) for parity."
metadata:
  topic: backloglist-mcp-tool-needs-server-side-filtering-params-titl
  source: Session observation — agents piping JSON through python3 -c
  added: '2026-03-01'
  priority: completed
  type: Feature
  status: done
  issue: '#330'
  last_synced: '2026-03-01T07:29:05Z'
---

## Story

As a **developer using Claude Code skills**, I want to **backlog_list mcp tool needs server-side filtering params (title, section, status)** so that **the tooling becomes more capable and complete**.

## Description

Agents pipe backlog_list JSON output through python3 -c to filter by title substring, section, or status — observed in work-backlog-item Step 0 (interactive browser), Step 1 (title search), and groom-backlog-item Step 1 (section filter). This is a design error: if the consumer must post-process to get useful results, the tool's interface is incomplete. Add optional filter params to backlog_list: title (case-insensitive substring match), section (P0|P1|P2|Ideas), status (open|closed|in-progress). Apply filters server-side in operations.list_items() before returning results. backlog_view already handles single-item lookup by selector — this gap is specifically the list-then-filter pattern for subsets. Also add the same params to the CLI (backlog.py list --title X --section P1 --status open) for parity.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Session observation — agents piping JSON through python3 -c
- **Priority**: P1
- **Added**: 2026-03-01
- **Research questions**: None