# Post-Planning Output (Steps 4.5 + 4.5a)

## When <mode/> is `auto` (Step 4.5a)

Skip the interactive report. Instead, continue directly to implementation:

1. Invoke implementation:

   ```text
   Skill(skill: "dh:implement-feature", args: "{plan_address}")
   ```

2. When all tasks complete, invoke quality gates:

   ```text
   Skill(skill: "dh:complete-implementation", args: "{plan_address}")
   ```

3. `/dh:complete-implementation` calls `backlog_resolve` as its terminal step — the issue is closed automatically.

Do not stop for user input at any point.

## Interactive mode (Step 4.5)

```text
Backlog item "{title}" is now planned.

- Plan: accessible via `sam_plan(action='read', plan="{slug}")` MCP tool
- To execute:      /implement-feature {slug}
- To check status: /implementation-manager status . {slug}
- To close when done: /work-backlog-item close {title}
```

**Do NOT close the GitHub Issue directly.** Do NOT include `Fixes #N`, `Closes #N`, or `Resolves #N` in task-level commit messages or PR bodies — issue closure is handled exclusively by `/dh:complete-implementation` as its terminal step (via `backlog_resolve` after all quality gates pass). Do not call `mcp__plugin_dh_backlog__backlog_resolve` during implementation work — it is only correct as the final step in `/dh:complete-implementation`. Use `/work-backlog-item close` only for dismissals (duplicate, out_of_scope, etc.). Use `/work-backlog-item resolve` only when `/dh:complete-implementation` was interrupted before the resolve step and manual resolution is required.
