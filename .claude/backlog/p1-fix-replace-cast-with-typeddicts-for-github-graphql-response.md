---
name: 'fix: Replace cast() with TypedDicts for GitHub GraphQL response parsing in operations.py'
description: "7 remaining cast() calls in plugins/development-harness/backlog_core/operations.py (lines ~2937-3006) use cast() to narrow untyped GitHub GraphQL JSON responses. Per project policy, cast() is never acceptable over TypedDicts or Pydantic models. Each cast site represents a design gap: the GraphQL response shape is known but not modelled.\n\nAffected call sites:\n- cast('dict[str, object]', data.get('repositoryOwner') or {})\n- cast('dict[str, object]', owner_node.get('projectsV2') or {})\n- cast('list[dict[str, object] | None]', projects_data.get('nodes') or [])\n- cast('dict[str, object]', owner_node_raw)\n- cast('dict[str, object]', create_data.get('createProjectV2') or {})\n- cast('dict[str, object]', create_pv2.get('projectV2') or {})\n- cast('int', project_node.get('number', 0))\n\nFix: define TypedDicts matching the GitHub GraphQL response shapes for projectsV2 query and createProjectV2 mutation. Use those TypedDicts to parse the response without cast(). Typing must get stronger — dict[str, object] is too broad."
metadata:
  topic: fix-replace-cast-with-typeddicts-for-github-graphql-response
  source: 'Code review during PR #953 (fix ty diagnostics)'
  added: '2026-03-21'
  priority: P1
  type: Bug
  status: open
  issue: '#954'
  last_synced: '2026-03-21T04:59:25Z'
---