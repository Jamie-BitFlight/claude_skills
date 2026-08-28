# Quick Mode (Step Q)

**Trigger:** <mode/> is `--quick`. Skips grooming, RT-ICA, and SAM planning. For one-file fixes, broken links, and typo patches where full pipeline overhead is disproportionate.

**Entry point from proactive fix routing:** When an agent's pre-fix check classifies a discovered
issue as trivial and routes it to --quick, the agent invokes this workflow as:
  /dh:work-backlog-item --quick {item title or #N}

If no backlog item exists for the fix, the agent does NOT call backlog_add first. Instead it
passes the descriptive title directly to `--quick`, which creates a minimal item inline (Step 2
of this workflow). The gate, not the user, authorizes the --quick routing decision.

**Invocation form:** `flags.quick = true` in the coerced input. Not a registry command. The title
or issue reference is passed as `item_ref`. A caller with more detail than fits in a short title
(e.g. an error message, or what was already ruled out) can supply it after a `--` delimiter:
`--quick {title} -- {additional observations}` — see Step 1 for how this splits.

1. Extract title from <item_ref/>. Per `SKILL.md`'s quick-mode exception to the freetext-delimiter
   rule, this text is not yet split — if it contains a `--` delimiter, the portion before it is
   the title and the portion after it is `{observations}`, additional detail to include in the
   description rather than fold into the title. With no delimiter, there are no `{observations}`.

   If the title, or `{observations}` if present, states a cause for the problem (e.g. "X failing
   because Y", "X due to Y") that is not a confirmed observation, the persisted text must not
   assert it as fact either — the creation-time hypothesis-labeling rule (`create/scope.md`)
   applies here too, even though this path skips the rest of that workflow. Strip the causal
   clause from wherever it appears (title, `{observations}`, or both — check each independently)
   before any lookup or write, keeping only the symptom (e.g. "X failing"), and record every
   causal clause found as `{hypothesis}` (`**Hypothesis**: {cause}`, one line per clause if more
   than one) for use in the description if a new item is created. Build slug from the normalized
   title: lowercased, spaces → hyphens. Every step below — the lookup, `--slug`, selectors,
   reported handoffs — uses this normalized `{title}`/`{slug}`, so a repeat invocation of the same
   command matches the item this workflow already created instead of attempting to create a
   duplicate.

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

   Append the fix as a new task on the active plan. Set `description` the same way Step 3 builds
   the description for a new item — `{observations}` and `{hypothesis}` from Step 1, when present,
   go here too; this path must not discard them just because it isn't creating a new item:

   ```text
   mcp__plugin_dh_sam__sam_plan(
     plan="{active_plan_id}",
     config={
       "action": "append_task",
       "task": {
         "id": "T{next_available_id}",
         "title": "{title}",
         "description": "{title, plus observations and hypothesis if Step 1 recorded them}",
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

3. Find the item via the CLI: `backlog view --selector "{title or #N}"` (using the normalized `{title}` from Step 1). If not found (JSON output contains an `error` key), create a minimal item:

   The description starts as `{title}`, then appends each of `{observations}` and `{hypothesis}`
   that Step 1 recorded, each on its own paragraph, in that order (`{title}\n\n{observations}\n\n{hypothesis}`
   when both are present). With neither, the description matches the title exactly.

   ```bash
   backlog add \
     --title "{title}" \
     --priority P2 \
     --description "{description from above}"
   ```

   If found, extract description and acceptance criteria from the CLI's JSON output (`body`/`sections`).

4. Extract the item's description and acceptance criteria if available.

5. Create the quick plan via the CLI:

   ```bash
   plan create \
     --slug "quick-{slug}" \
     --goal "{goal from description or acceptance_criteria}" \
     --task-id T1 \
     --task-title "{description}" \
     --task-agent "task-worker" \
     --task-priority 1 \
     --task-complexity low
   ```

   `plan create` accepts only one inline task per call (use `plan append-task` for additional
   tasks) — sufficient here since the quick plan is always single-task. It handles path resolution
   internally — do not resolve or pass a file path. Read `plan_id` (e.g. `Pe71c7cb8-{slug}`) from the JSON
   output — that is the plan reference used in the next two steps, not the `quick-{slug}` string.

6. Call the CLI to record the plan reference: `backlog update --selector "{title}" --plan "{plan_id from step 5}"`.

7. Report the `plan_id` returned by `plan create`:

   ```text
   Quick plan created: {plan_id from step 5}
   Steps: {N} tasks

   To execute: /dh:implement-feature {plan_id}
   To close:   /dh:work-backlog-item close {title}
   ```
