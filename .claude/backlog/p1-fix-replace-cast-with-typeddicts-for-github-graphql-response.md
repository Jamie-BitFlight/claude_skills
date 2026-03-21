---
name: 'fix: Replace cast() with TypedDicts for GitHub GraphQL response parsing in operations.py'
description: "7 remaining cast() calls in plugins/development-harness/backlog_core/operations.py (lines ~2937-3006) use cast() to narrow untyped GitHub GraphQL JSON responses. Per project policy, cast() is never acceptable over TypedDicts or Pydantic models. Each cast site represents a design gap: the GraphQL response shape is known but not modelled.\n\nAffected call sites:\n- cast(\"dict[str, object]\", data.get(\"repositoryOwner\") or {})\n- cast(\"dict[str, object]\", owner_node.get(\"projectsV2\") or {})\n- cast(\"list[dict[str, object] | None]\", projects_data.get(\"nodes\") or [])\n- cast(\"dict[str, object]\", owner_node_raw)\n- cast(\"dict[str, object]\", create_data.get(\"createProjectV2\") or {})\n- cast(\"dict[str, object]\", create_pv2.get(\"projectV2\") or {})\n- cast(\"int\", project_node.get(\"number\", 0))\n\nFix: define TypedDicts matching the GitHub GraphQL response shapes for projectsV2 query and createProjectV2 mutation. Use those TypedDicts to parse the response without cast(). Typing must get stronger — dict[str, object] is too broad."
metadata:
  topic: fix-replace-cast-with-typeddicts-for-github-graphql-response
  source: 'Code review during PR #953 (fix ty diagnostics)'
  added: '2026-03-21'
  priority: P1
  type: Bug
  status: needs-grooming
  issue: '#954'
  last_synced: '2026-03-21T08:07:17Z'
---

## Story

As a **developer relying on this plugin**, I want to **fix: replace cast() with typeddicts for github graphql response parsing in operations.py** so that **the tool works correctly and reliably**.

## Description

7 remaining cast() calls in plugins/development-harness/backlog_core/operations.py (lines ~2937-3006) use cast() to narrow untyped GitHub GraphQL JSON responses. Per project policy, cast() is never acceptable over TypedDicts or Pydantic models. Each cast site represents a design gap: the GraphQL response shape is known but not modelled.

Affected call sites:
- cast("dict[str, object]", data.get("repositoryOwner") or {})
- cast("dict[str, object]", owner_node.get("projectsV2") or {})
- cast("list[dict[str, object] | None]", projects_data.get("nodes") or [])
- cast("dict[str, object]", owner_node_raw)
- cast("dict[str, object]", create_data.get("createProjectV2") or {})
- cast("dict[str, object]", create_pv2.get("projectV2") or {})
- cast("int", project_node.get("number", 0))

Fix: define TypedDicts matching the GitHub GraphQL response shapes for projectsV2 query and createProjectV2 mutation. Use those TypedDicts to parse the response without cast(). Typing must get stronger — dict[str, object] is too broad.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Code review during PR #953 (fix ty diagnostics)
- **Priority**: P1
- **Added**: 2026-03-21
- **Research questions**: None
