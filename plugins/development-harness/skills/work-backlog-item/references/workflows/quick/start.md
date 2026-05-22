# Quick Mode (Step Q)

**Trigger:** <mode/> is `--quick`. Skips grooming, RT-ICA, and SAM planning. For one-file fixes, broken links, and typo patches where full pipeline overhead is disproportionate.

**Entry point from proactive fix gate:** When the Proactive Fix Gate (CLAUDE.md) routes a fix
to --quick, the agent invokes this workflow as:
  /dh:work-backlog-item --quick {item title or #N}

If no backlog item exists for the fix, the agent does NOT call backlog_add first. Instead it
passes the descriptive title directly to `--quick`, which creates a minimal item inline (Step 2
of this workflow). The gate, not the user, authorizes the --quick routing decision.

**Invocation form:** `flags.quick = true` (parser flag). Not a registry command. The title
or issue reference is passed as `item_ref`.

1. Extract title from <item_ref/>+ joined. Build slug: title lowercased, spaces → hyphens.

2. **In-Progress Relevance Check** — Before creating a new backlog item, determine whether this fix belongs to work already in progress. If it does, add it to the active plan instead of opening a new item.

   **a. Discover active work:**

   - Call `mcp__plugin_dh_sam__sam_active_task(config={"action": "get"})` — returns the currently claimed SAM task for this agent session (look for `plan` and `task_id` fields). Record as `active_task`.
   - Call `mcp__plugin_dh_backlog__backlog_list(status="in-progress")` — lists items currently being worked. Record as `in_progress_items`.

   **b. Relevance checklist** (evaluate all three):

   - [ ] Is there active work? (`active_task` is non-empty OR `in_progress_items` is non-empty)
   - [ ] Does the fix title or description overlap in scope, subject, or affected files with the active issue's goal, acceptance criteria, or description?
   - [ ] Would addressing this fix be required — or directly unblock — the active work to be considered complete?

   **c. Decision:**

   If ALL three checklist items pass → Route to **step 2a** (Plan Integration Path). Skip steps 3–7.

   Otherwise → Continue to step 3 (create a new backlog item as usual).

2a. **Plan Integration Path** (all relevance checks passed):

   Resolve the active plan ID:
   - If `active_task` is non-empty: use its `plan` field as `active_plan_id`.
   - Else: call `mcp__plugin_dh_backlog__backlog_view(selector="{first in_progress_items title}", summary=false)` and read the item's `plan` field as `active_plan_id`.
   - If neither yields a plan ID: fall through to step 3 (cannot integrate without a plan reference).

   Append the fix as a new task on the active plan:

   ```text
   mcp__plugin_dh_sam__sam_plan(
     config={
       "action": "append_task",
       "plan": "{active_plan_id}",
       "task": {
         "id": "T{next_available_id}",
         "title": "{title}",
         "status": "not-started",
         "agent": "task-worker",
         "dependencies": [],
         "priority": 1,
         "complexity": "low"
       }
     }
   )
   ```

   Report to the user:

   ```text
   Fix added to active plan: {active_plan_id}
   Task: {title}

   The fix is included in the current implementation cycle.
   To execute immediately: /dh:start-task {active_plan_id} {task_id}
   ```

   Stop — do not continue to step 3 or create a new backlog item.

3. Find the item via `mcp__plugin_dh_backlog__backlog_view(selector="{title or #N}", summary=false)`. If not found (response contains `error` key), create a minimal item:

   ```text
   mcp__plugin_dh_backlog__backlog_add(
     title="{title}",
     priority="P2",
     description="{title}",
     gate_token="<gate_token>"
   )
   ```

   `<gate_token>` is the session token injected by the skill at load time from the `<gate_token>` block in SKILL.md. It is not a literal placeholder — the skill resolves it to the actual token value before these instructions are read.

   Note: When arriving via the proactive fix gate with no prior backlog item, this creation step
   is the correct path. The gate's complexity classification already confirmed the fix is trivial —
   no grooming or RT-ICA is needed.

   If found, extract description and acceptance criteria from `response["sections"]`.

4. Extract the item's description and acceptance criteria if available.

5. Create the quick plan using the SAM MCP tool:

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

6. Call the `mcp__plugin_dh_backlog__backlog_update` tool with `selector="{title}"` and `plan="quick-{slug}"` to record the plan slug.

7. Report the path returned by `sam_plan(action='create')`:

   ```text
   Quick plan created: {path returned by sam_plan(action='create')}
   Steps: {N} tasks

   To execute: /implement-feature quick-{slug}
   To close:   /work-backlog-item close {title}
   ```
