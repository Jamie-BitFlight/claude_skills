# Quick Mode (Step Q)

**Trigger:** <mode/> is `--quick`. Skips grooming, RT-ICA, and SAM planning. For one-file fixes, broken links, and typo patches where full pipeline overhead is disproportionate.

1. Extract title from <item_ref/>+ joined. Build slug: title lowercased, spaces → hyphens.

2. Find the item via `backlog_view(selector="{title or #N}", summary=false)`. If not found (response contains `error` key), create a minimal item with `backlog_add(title="{title}", gate_token="problems-not-solutions")`. If found, extract description and acceptance criteria from `response["sections"]`.

3. Extract the item's description and acceptance criteria if available.

4. Create the quick plan using the SAM MCP tool:

   ```text
   mcp__plugin_dh_sam__sam_plan(
     config={
       "action": "create",
       "slug": "quick-{slug}",
       "goal": "{goal from description or acceptance_criteria}",
       "tasks": [{"id": "T1", "title": "{description}", "status": "not-started", "agent": "task-worker", "dependencies": [], "priority": 1, "complexity": "low"}]
     }
   )
   ```

   `sam_plan(action='create')` handles path resolution internally — do not resolve or pass a file path.

5. Call the `mcp__plugin_dh_backlog__backlog_update` tool with `selector="{title}"` and `plan="quick-{slug}"` to record the plan slug.

6. Report the path returned by `sam_plan(action='create')`:

   ```text
   Quick plan created: {path returned by sam_plan(action='create')}
   Steps: {N} tasks

   To execute: /implement-feature quick-{slug}
   To close:   /work-backlog-item close {title}
   ```
