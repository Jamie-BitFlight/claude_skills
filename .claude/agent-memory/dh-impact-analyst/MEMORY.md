# Memory - DH Impact Analyst

## Project Patterns

- [project_plugin_creator_consumer_chains.md](./project_plugin_creator_consumer_chains.md) — plugin-creator agents are consumed by 3+ plugins; the-rewrite-room and development-harness are always impacted by plugin-creator agent changes
- [project_dh_beads_backend_patterns.md](./project_dh_beads_backend_patterns.md) — DH plugin backend factory pattern (3 factories), hook type risk at task_status_hook.py:807, prior beads removal constraint in server.py:107-111, GitHub-only MCP tools with no beads equivalent
- [project_dh_backlog_cache_coherence_patterns.md](./project_dh_backlog_cache_coherence_patterns.md) — view_item reads local YAML via parse_backlog(); sections/sections_index never refreshed from GitHub; view_enrich_from_github partial escape hatch; pull_items "keep longer" blocks fresh data; sync_items has no flush_only; finally.md references non-existent parameter
- [project_sam_plan_ready_tasks_key_risk.md](./project_sam_plan_ready_tasks_key_risk.md) — `ready_tasks` key in sam_plan ready response is consumed by 3 orchestration skills; _paginate_results uses `items` key; naive reuse breaks all consumers silently; test_paginate_results_boundary.py imports 3 private symbols from sam_schema.server that break on extraction
- [project_backlog_core_disclosure_pipeline.md](./project_backlog_core_disclosure_pipeline.md) — disclosure pipeline modules (ordinal_mapper, disclosure_handler, disclosure_types), ADR-2/ADR-5 constraints, MarkdownIndexer reuse target; backlog_core/tests/ now in root pyproject testpaths (line 403)
- [project_workflow_extractor_cross_plugin_pattern.md](./project_workflow_extractor_cross_plugin_pattern.md) — reduce.py/plan_ensemble.py live in plugin-creator not DH; cross-plugin invocation risk; workflow-extractor agents removed but still in KNOWN_ENTITIES; hooks.json ≠ git post-commit hook
