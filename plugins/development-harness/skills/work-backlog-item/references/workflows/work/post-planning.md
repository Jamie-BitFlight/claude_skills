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

3. After completion, proceed to close/resolve path to mark the item done.

Do not stop for user input at any point.

## Interactive mode (Step 4.5)

```text
Backlog item "{title}" is now planned.

- Plan: accessible via `sam_plan(action='read', plan="{slug}")` MCP tool
- To execute:      /implement-feature {slug}
- To check status: /implementation-manager status . {slug}
- To close when done: /work-backlog-item close {title}
```

**Do NOT close the GitHub Issue directly.** Do NOT include `Fixes #N`, `Closes #N`, or `Resolves #N` in task-level commit messages or PR bodies — issue closure is handled exclusively by `/complete-implementation` in its final commit step. Only use `/work-backlog-item resolve` for post-merge verification and local bookkeeping. Use `/work-backlog-item close` only for dismissals (duplicate, out_of_scope, etc.). Never call `mcp__plugin_dh_backlog__backlog_resolve` before the PR has merged.
