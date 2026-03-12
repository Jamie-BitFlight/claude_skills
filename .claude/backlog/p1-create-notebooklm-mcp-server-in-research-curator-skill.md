---
name: Create NotebookLM MCP server in research-curator skill
description: 'The research-curator skill needs an MCP server that integrates the notebooklm-py library (https://github.com/teng-lin/notebooklm-py) to enable the research curator agent to access Google NotebookLM research systems. This would allow creating notebooks, adding sources, generating audio overviews, and querying NotebookLM content programmatically as part of the research curation workflow. Use /fastmcp-creator to build the MCP server inside the research-curator skill directory. Success: research-curator agent can create/manage NotebookLM notebooks and use them as research sources via MCP tools. Verification: MCP server starts, tools are callable, and NotebookLM operations complete successfully.'
metadata:
  topic: create-notebooklm-mcp-server-in-research-curator-skill
  source: User request
  added: '2026-03-05'
  priority: P1
  type: Feature
  status: needs-grooming
  issue: '#436'
  last_synced: '2026-03-12T12:48:25Z'
---

## Story

As a **developer using Claude Code skills**, I want to **create notebooklm mcp server in research-curator skill** so that **the tooling becomes more capable and complete**.

## Description

The research-curator skill needs an MCP server that integrates the notebooklm-py library (https://github.com/teng-lin/notebooklm-py) to enable the research curator agent to access Google NotebookLM research systems. This would allow creating notebooks, adding sources, generating audio overviews, and querying NotebookLM content programmatically as part of the research curation workflow. Use /fastmcp-creator to build the MCP server inside the research-curator skill directory. Success: research-curator agent can create/manage NotebookLM notebooks and use them as research sources via MCP tools. Verification: MCP server starts, tools are callable, and NotebookLM operations complete successfully.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: User request
- **Priority**: P1
- **Added**: 2026-03-05
- **Research questions**: None
