# Resume Report (Step R)

**Trigger:** <mode/> is `resume`.

1. Extract title from <item_ref/>+ joined. If <item_ref/> starts with `#`, fetch title from GitHub Issue (same logic as issue-first path).

2. Call `backlog_view(selector="{title or #N}", summary=false)`. Extract the `plan` field from the response. If absent or empty:

   ```text
   No plan file recorded for "{title}".
   Run /work-backlog-item {title} to create a plan first.
   ```

   Then stop.

3. Read the plan via the CLI: `uv run plugins/development-harness/sam_schema/cli.py plan read --address "{plan_address}"`,
   using the plan ID extracted from the item's `plan` field. Do not read the YAML file directly. Parse the task list from the JSON output:
   - `total_tasks` — count of all task entries
   - `checked_tasks` — count of tasks with `status: complete`
   - `last_checked` — title of the last task with `status: complete`
   - `first_unchecked` — title of the first task with `status: not-started` or `status: in-progress`

4. Compute `completion_pct = checked_tasks * 100 / total_tasks` (integer).

5. Report:

   ```text
   Resume: {title}
   Plan:   {plan_address}

   Progress: {checked_tasks}/{total_tasks} tasks ({completion_pct}%)

   Last completed:  {last_checked task text}
   Next to do:      {first_unchecked task text}

   To continue: /implement-feature {slug}
   To close:    /work-backlog-item close {title}
   ```

   If `checked_tasks == 0`, report "No tasks completed yet."
   If `checked_tasks == total_tasks`, report "All tasks complete — run /work-backlog-item close {title}."
