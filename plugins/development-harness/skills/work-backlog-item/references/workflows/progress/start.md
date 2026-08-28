# Progress Report (Step P)

**Trigger:** <mode/> is `progress`.

1. Call `backlog_list()` to retrieve all open items. Count items by priority (P0, P1, P2, Ideas) and status from the returned `items` list. Each entry has `priority`, `status`, `title`, `issue`, `milestone`, and `groomed` fields.

2. Query GitHub for the active milestone:

   ```text
   # Use MCP: backlog_get_soonest_milestone()
   ```

   Extract: milestone number, title, open_issues, closed_issues.

3. For items in the active milestone, identify the highest-priority groomed item with no `**Plan**:` field — that is the recommended next action.

4. Display:

   ```text
   Backlog Health — {YYYY-MM-DD}

   Active Milestone: #{N} {title}
     Closed:      {closed_issues} items
     Open:        {open_issues} items
     Progress:    [{####......}] {pct}%

   Overall Backlog:
     P0:    {n} items ({m} in milestone)
     P1:    {n} items ({m} in milestone, {k} groomed but unassigned)
     P2:    {n} items
     Ideas: {n} items

   Next recommended action:
     /dh:work-backlog-item {title}  — {title} (P{x}, groomed, in active milestone)
   ```

   If no active milestone exists, omit the milestone section and show only Overall Backlog counts.

   If the backlog directory is empty, note: `(no backlog items found)`
