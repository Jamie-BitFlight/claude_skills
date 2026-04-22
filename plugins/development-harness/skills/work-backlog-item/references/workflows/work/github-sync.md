# Issue Sync (Steps 2.2–2.4)

> **Backend provider abstraction**: Use MCP tools for all issue operations — the backlog MCP server handles backend provider details (GitHub, GitLab, Linear, etc.). Do not call any provider CLI or API directly.

## Step 2.2: Issue Link Check

After extracting item fields, check for an existing linked issue:

1. Search the matched item for `**Issue**: #N` field.
2. If found: issue already linked. Run:

   ```text
   MCP: backlog_view(selector="#N")
   ```

   Report the issue state. If open, proceed. If closed, warn the user before re-opening planning.

3. If not found AND priority is P0 or P1: offer to create a linked issue:

   ```text
   This P1 item has no linked issue. Create one? (yes/no)
   ```

   If yes, proceed to Step 2.3.
   If no, skip issue sync; the backlog item remains without a linked issue.

4. If not found AND priority is P2 or Ideas: do not prompt; skip issue sync silently.

## Step 2.3: Create Linked Issue

Call the `mcp__plugin_dh_backlog__backlog_update` tool with `selector="{title}"`.

The tool creates the linked issue automatically when the item lacks one and records the `issue: '#N'` link in the backend. Check the returned dict for an `error` key.

## Step 2.4: Set In-Progress

Call the `mcp__plugin_dh_backlog__backlog_update` tool with `selector="{title}"` and `status="in-progress"`. Check the returned dict for an `error` key.

If the item is in a milestone with other issues, also run `milestone start` to bulk-transition all open milestone issues to in-progress:

```text
MCP: backlog_update(selector="{title}", status="in-progress")
```

> **Note**: Bulk milestone start (transitioning all issues in a milestone) is not yet available as a single MCP tool call. Use `backlog_list_issues(milestone="{milestone_title}")` to enumerate milestone issues, then `backlog_update` each one individually.
