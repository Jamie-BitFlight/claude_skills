---
name: Complete GraphQL migration for backlog MCP server
description: 'The backlog MCP server (backlog_core/) uses PyGitHub REST API for milestones, issues, PRs, and most operations. Only label lookups (commits 32e5597c, 7280a8ff) and Projects V2 operations use GraphQL. PR #455 (github-graphql-migration branch) only migrated daily-releases scripts, not the backlog server.'
metadata:
  topic: complete-graphql-migration-for-backlog-mcp-server
  source: 'Session 2026-03-20: discovered milestones, issues, PRs still use PyGitHub REST API. Only labels and Projects V2 were migrated to GraphQL.'
  added: '2026-03-20'
  priority: P1
  type: Refactor
  status: open
  issue: '#916'
  last_synced: '2026-03-21T03:45:08Z'
---

## Description

The backlog MCP server (backlog_core/) uses PyGitHub REST API for milestones, issues, PRs, and most operations. Only label lookups (commits 32e5597c, 7280a8ff) and Projects V2 operations use GraphQL. PR #455 (github-graphql-migration branch) only migrated daily-releases scripts, not the backlog server.

## Operations still on REST (PyGitHub)

- `repository.get_milestones()`
- `repository.get_issues()`
- Issue creation, editing, commenting
- PR listing
- Label CRUD (partially — lookup migrated, CRUD not verified)

## Source

Session 2026-03-20: discovered milestones, issues, PRs still use PyGitHub REST API.
