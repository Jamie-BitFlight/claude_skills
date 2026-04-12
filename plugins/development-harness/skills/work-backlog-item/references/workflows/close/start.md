# Close / Resolve Procedure (Phase 5)

**Trigger:** <mode/> is `close` or `resolve`.

- `close`: <item_ref/>+ = title, `#N`, number, or URL → dismiss without completion (reason required)
- `resolve`: <item_ref/>+ = title, `#N`, number, or URL → mark DONE with evidence trail (summary required)

## Step 5.2: Find Item

Call the `mcp__plugin_dh_backlog__backlog_view` tool with `selector="<item_ref/>"` (accepts URLs, `#N`, bare numbers, and title substrings).

- If the returned dict contains an `error` key, report and stop.
- Extract `title` from the returned dict and use it as the working title.

The `backlog_view` response is the single source of truth for item lookup. Do not scan filesystem paths.

- If the returned dict contains an `error` key with "not found": report "No backlog item found matching: <item_ref/>" and stop.
- If multiple candidates are returned: list all matches and ask user to pick one.
- If the item status is already `completed`: report "Item already closed on {Completed date}" and stop.

## Step 5.3: Close path — dismiss without completion

If operation is `close`:

1. Use `AskUserQuestion` to ask: "Why is this item being dismissed?" with options:
   - `duplicate` — Another item covers the same work
   - `out_of_scope` — Doesn't belong in this project
   - `superseded` — Replaced by a different item or approach
   - `wontfix` — Deliberate decision not to do this
   - `blocked` — Permanently blocked, cannot proceed

2. If the user selected `duplicate` or `superseded`, ask for a reference: "Which item does this duplicate / is this superseded by?" (free text — accepts `#N`, URL, or title).

3. Optionally ask for additional context: "Any additional comment?" (free text, can be skipped).

4. Call the `mcp__plugin_dh_backlog__backlog_close` tool:

   - `selector`: `"{title}"` or `"#{N}"`
   - `reason`: `"{selected reason}"`
   - `reference`: `"{reference}"` (if provided)
   - `comment`: `"{comment}"` (if provided)

5. Check the returned dict for an `error` key. Report the result to the user.

Then stop.

## Step 5.4: Resolve path — status:verified gate (SAM items only)

If operation is `resolve`:

1. Extract `**Plan**:` field from the matched item. If absent, skip this step entirely — non-SAM items have no verification gate.

2. If `**Plan**:` is present, check the GitHub Issue labels for `status:verified`:
   - Use `mcp__plugin_dh_backlog__backlog_view` with `selector="{title}"` and inspect the `labels` list in the returned dict.
   - If `status:verified` is present in `labels`, proceed to Step 5.5.
   - If `status:verified` is absent:
     - If `--force` flag was passed, print a warning and proceed to Step 5.5:

       ```text
       Warning: status:verified label is absent for "{title}". Proceeding with --force.
       The /complete-implementation quality gates have not been confirmed for this item.
       ```

     - Otherwise, block resolve and report:

       ```text
       Resolve blocked for "{title}".

       This item has a SAM plan but the status:verified label is absent on GitHub Issue #{N}.
       The label is applied automatically when /complete-implementation quality gates pass.

       Options:
         1. Run /complete-implementation {plan-file-path} to run quality gates and apply the label.
         2. Re-run /work-backlog-item resolve {title} --force to bypass this gate with a warning.
         3. Run /work-backlog-item close {title} to dismiss without completion.
       ```

       Then stop.

## Step 5.5: Resolve path — checklist verification

If operation is `resolve`:

1. Extract `**Plan**:` field from the matched item. If absent, skip to Step 5.7 (no plan = simple resolve with summary only).

2. Extract the plan address from the plan path (e.g., `plan/Pe9f0a1b2-backlog-lifecycle-process-gaps.yaml` → `Pe9f0a1b2`). Call:

   ```text
   mcp__plugin_dh_sam__sam_plan(config={"action": "status"}, plan="{address}")
   ```

   From the response, read `status_counts`. A plan is complete when `status_counts.not_started == 0` and `status_counts.in_progress == 0` and `status_counts.blocked == 0`.

3. If any tasks are not complete (`not_started > 0` or `in_progress > 0` or `blocked > 0`):

   ```text
   Plan incomplete: {status_counts.complete}/{total} tasks done.
   Not started: {not_started} | In progress: {in_progress} | Blocked: {blocked}

   Complete all tasks before resolving, or use /work-backlog-item close {title} to dismiss.
   ```

   Then stop.

## Step 5.6: Resolve path — typed acceptance-criteria verification

4. Extract acceptance criteria from the `backlog_view` response. Call `mcp__plugin_dh_backlog__backlog_view` with `selector="{title}"` and `summary=false`, then read `response["sections"]["Acceptance Criteria"]`. The field format is a bullet list:

   ```markdown
   **Acceptance Criteria**:
   - {criterion 1}
   - {criterion 2}
   - {criterion 3}
   ```

   Parse each `-` line as a separate criterion.

5. Spawn a verification agent with subagent_type="dh:task-worker". Prompt must include: item title, plan address (e.g., `P{id}`), checklist status (100%), and each criterion listed individually as "Criterion N: {text}". Instruct the agent to: read the plan via `sam_plan(action='read')`, search `git log --oneline -20`, check relevant files for each criterion, and return per-criterion PASS/FAIL with file:line evidence. Required return format:

   ```text
   [PASS] {criterion} — verified at {file}:{line} (or commit {sha})
   [FAIL] {criterion} — {gap description}
   Overall: PASS or FAIL (N/M criteria met)
   ```

   **If no acceptance criteria exist**: warn "No **Acceptance Criteria**: field found — falling back to description-based verification" and spawn agent with the description as the goal instead.

6. Parse the agent verdict:

   ```text
   Acceptance Criteria Verification:

     [PASS] running X produces Y — verified at src/main.py:42
     [FAIL] file Z exists with field W — file exists but field W not found
     [PASS] test suite passes — confirmed via git log (commit abc123f)

   Overall: FAIL (2/3 criteria met)
   ```

7. Collect agent verdict:
   - **Overall PASS** (all criteria met): proceed to Step 5.7
   - **Overall FAIL** (any criterion failed): report gaps, do not resolve:

     ```text
     Verification FAILED for "{title}".

     Per-criterion results:
     {agent findings}

     Address the failing criteria before resolving, or use /work-backlog-item close {title} to dismiss.
     ```

     Then stop.

## Step 5.7: Invoke backlog resolve

8. If the item has a linked GitHub Issue (`#N`), check whether an open PR already references it:

   ```bash
   git log --oneline -20 --grep="Fixes #N\|Closes #N"
   ```

   - **Open PR found**: The PR body contains `Fixes #N` — the issue will auto-close on merge. Update only the backlog item status (do NOT close the GitHub Issue):

     Call the `mcp__plugin_dh_backlog__backlog_update` tool with `selector="{title}"` and `status="in-progress"`.

     Report:

     ```text
     Backlog item "{title}" verified. GitHub Issue #{N} will auto-close when PR #{pr_number} merges.
     ```

     Then stop.

   - **No open PR / no linked issue**: proceed to invoke backlog resolve below.

9. Use `AskUserQuestion` to ask: "Summarize what was done (1-2 sentences):" (free text — this is the required `summary` field).

10. Optionally gather additional evidence fields (can be skipped for trivial items):
    - `method` — "How was the work done?"
    - `notes` — "Any problems found or surprises?"
    - `follow_ups` — "Any follow-up tickets created?" (comma-separated refs)
    - `findings` — "Any retrospective learnings?"

11. Call the `mcp__plugin_dh_backlog__backlog_resolve` tool:

    - `selector`: `"{title}"` or `"#{N}"`
    - `summary`: `"{summary}"`
    - `plan`: `"{plan_address}"` (if present — e.g., `"P{id}"`)
    - `method`: `"{method}"` (if provided)
    - `notes`: `"{notes}"` (if provided)
    - `follow_ups`: `"{follow_ups}"` (if provided)
    - `findings`: `"{findings}"` (if provided)

12. Check the returned dict for an `error` key. Report the result to the user.

13. Before emitting Handoff E, determine whether all milestone issues are resolved:

    a. Read the `milestone` field from the `backlog_resolve` response. If the resolved item has no `milestone` field (or `milestone` is null/empty), skip Handoff E — no milestone context exists.

    b. If a milestone is present, call:

       ```text
       mcp__plugin_dh_backlog__backlog_list()
       ```

       From the returned items, count those whose `milestone` field matches the resolved item's milestone AND whose `status` is NOT `done` or `resolved`. This is the `open_issues` count.

    c. Emit Handoff E only when `open_issues == 0`:

       ```text
       NEXT: skill="complete-milestone" args="{milestone number}" condition="all milestone issues status:done OR status:resolved AND open_issues == 0"
       ```

    d. If `open_issues > 0`, skip Handoff E — the milestone is not yet ready for completion.

## --force flag

The `--force` flag bypasses two gates in the resolve path:

- **Step 5.4** (`status:verified` gate): Skips the check that `status:verified` is present on the GitHub Issue. Use when you are confident quality gates have passed but the label was not applied automatically (e.g., the `/complete-implementation` hook failed to apply it).
- **Step 5.7** (open PR check): Bypasses the check for an open PR with `Fixes #N`. Use when you want to resolve the local cache entry immediately even though a PR is still open.

In both cases `--force` prints a warning before proceeding so the bypass is visible in the session transcript.

Usage:

```text
/work-backlog-item resolve {title} --force
/work-backlog-item resolve #{N} --force
```
