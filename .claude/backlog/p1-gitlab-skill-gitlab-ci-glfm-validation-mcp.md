---
name: 'gitlab-skill: GitLab CI & GLFM Validation MCP'
description: 'Wrap `validate_glfm.py` and `sync_gitlab_docs.py` as MCP tools. Agents could validate GitLab Flavored Markdown compliance and sync documentation without shell access. Tools: `validate_glfm`, `sync_docs`, `list_glfm_errors`.'
metadata:
  topic: gitlab-skill-gitlab-ci-glfm-validation-mcp
  source: 'GitHub Issue #255'
  added: '2026-03-03'
  priority: P1
  type: Docs
  status: needs-grooming
  issue: '#255'
  last_synced: '2026-03-14T16:00:50Z'
---

## Story

As a **developer using Claude Code skills**, I want to **gitlab-skill: gitlab ci & glfm validation mcp** so that **the tooling becomes more capable and complete**.

## Description

Wrap `validate_glfm.py` and `sync_gitlab_docs.py` as MCP tools. Agents could validate GitLab Flavored Markdown compliance and sync documentation without shell access. Tools: `validate_glfm`, `sync_docs`, `list_glfm_errors`.

## Suggested Location

`plugins/gitlab-skill/mcp/server.py`

## Context

- **Source**: MCP backlog audit 2026-02-23
- **Priority**: Ideas
- **Added**: 2026-02-23
- **Research questions**: None
