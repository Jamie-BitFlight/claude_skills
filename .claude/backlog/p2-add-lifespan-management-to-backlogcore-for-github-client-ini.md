---
name: Add lifespan management to backlog_core for GitHub client initialization
description: "backlog_core has no lifespan management. The GitHub client (`get_github()`) is instantiated per-call, which means token validation and connection setup are repeated on every tool invocation. Under load, this creates redundant API handshakes.\n\nFastMCP v3 provides a `@lifespan` decorator that runs setup once at server start and yields a context dict available via `ctx.lifespan_context`. This is the correct place to validate `GITHUB_TOKEN`, create the GitHub client, and fail fast if credentials are missing.\n\nFiles affected: `.claude/skills/backlog/backlog_core/server.py`, `.claude/skills/backlog/backlog_core/github.py`\n\nWork required:\n- Define a `@lifespan` that initializes the GitHub client and validates `GITHUB_TOKEN`\n- Pass the `FastMCP` instance `lifespan=app_lifespan`\n- Tools that use GitHub access `ctx.lifespan_context[\"github\"]` instead of calling `get_github()` per-request\n- `GitHubUnavailableError` surfaces at startup rather than first GitHub call\n\nSource: FastMCP v3 docs `servers/lifespan.mdx` — `@lifespan` yields a dict into `ctx.lifespan_context`; compose multiple lifespans with `|` operator."
metadata:
  topic: add-lifespan-management-to-backlogcore-for-github-client-ini
  source: 'GitHub Issue #468'
  added: '2026-03-06'
  priority: P2
  type: Refactor
  status: needs-grooming
  issue: '#468'
  last_synced: '2026-03-12T12:48:17Z'
---

## Story

As a **maintainer of the codebase**, I want to **add lifespan management to backlog_core for github client initialization** so that **the code is cleaner and more maintainable**.

## Description

backlog_core has no lifespan management. The GitHub client (`get_github()`) is instantiated per-call, which means token validation and connection setup are repeated on every tool invocation. Under load, this creates redundant API handshakes.

FastMCP v3 provides a `@lifespan` decorator that runs setup once at server start and yields a context dict available via `ctx.lifespan_context`. This is the correct place to validate `GITHUB_TOKEN`, create the GitHub client, and fail fast if credentials are missing.

Files affected: `.claude/skills/backlog/backlog_core/server.py`, `.claude/skills/backlog/backlog_core/github.py`

Work required:
- Define a `@lifespan` that initializes the GitHub client and validates `GITHUB_TOKEN`
- Pass the `FastMCP` instance `lifespan=app_lifespan`
- Tools that use GitHub access `ctx.lifespan_context["github"]` instead of calling `get_github()` per-request
- `GitHubUnavailableError` surfaces at startup rather than first GitHub call

Source: FastMCP v3 docs `servers/lifespan.mdx` — `@lifespan` yields a dict into `ctx.lifespan_context`; compose multiple lifespans with `|` operator.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: fastmcp-creator skill review of backlog_core/server.py
- **Priority**: P2
- **Added**: 2026-03-06
- **Research questions**: None
