---
name: 'dasel: Structured Data Query MCP'
description: 'Wrap dasel CLI operations as MCP tools. Agents could query, transform, and convert structured data (JSON, YAML, TOML, XML, CSV) without shell piping. Tools: `query_data`, `transform_data`, `convert_format`, `install_dasel`.'
metadata:
  topic: dasel-structured-data-query-mcp
  source: 'GitHub Issue #262'
  added: '2026-03-03'
  priority: P1
  type: Feature
  status: needs-grooming
  issue: '#262'
  last_synced: '2026-03-21T08:08:39Z'
---

## Story

As a **developer using Claude Code skills**, I want to **dasel: structured data query mcp** so that **the tooling becomes more capable and complete**.

## Description

Wrap dasel CLI operations as MCP tools. Agents could query, transform, and convert structured data (JSON, YAML, TOML, XML, CSV) without shell piping. Tools: `query_data`, `transform_data`, `convert_format`, `install_dasel`.

## Suggested Location

`plugins/dasel/mcp/server.py`

## Context

- **Source**: MCP backlog audit 2026-02-23
- **Priority**: Ideas
- **Added**: 2026-02-23
- **Research questions**: Evaluate whether wrapping the dasel binary (subprocess) or reimplementing core operations in Python is better for MCP transport.
