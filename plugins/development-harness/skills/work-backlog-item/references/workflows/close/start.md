# Close / Resolve Procedure (Phase 5)

**Trigger:** <route/> is `close` or `resolve`.

- `close`: <item_ref/>+ = title, `#N`, number, or URL → dismiss without completion (reason required)
- `resolve`: <item_ref/>+ = title, `#N`, number, or URL → mark DONE with evidence trail (summary required)

## Step 5.2: Find Item

Call `backlog view --selector "<item_ref/>"` (accepts URLs, `#N`, bare numbers, and title substrings).

- If the returned dict contains an `error` key, report and stop.
- Extract `title` from the returned dict and use it as the working title.

The `backlog_view` response is the single source of truth for item lookup. Do not scan filesystem paths.

- If the returned dict contains an `error` key with "not found": report "No backlog item found matching: <item_ref/>" and stop.
- If multiple candidates are returned: list all matches and ask user to pick one.
- If the item `status` is `closed`, `done`, or `resolved`: report "Item is already {status}." and stop.

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

4. Call `mcp__plugin_dh_backlog__backlog_close`:

   - `selector`: `"{title}"` or `"#{N}"`
   - `reason`: `"{selected reason}"`
   - `reference`: `"{reference}"` (if provided)
   - `comment`: `"{comment}"` (if provided)

5. Check the returned dict for an `error` key.
   - If `error` starts with `Open PRs reference issue`, the item is not closed. The `warnings` list names each open PR. Report those PRs to the user. Use `AskUserQuestion` to ask: "Close the item anyway? The open PRs stay open." If the user confirms, call `mcp__plugin_dh_backlog__backlog_close` again with the same parameters and `force=True`. Report that result.
   - If `error` starts with `Open-PR search failed`, the item is not closed. The search could not reach GitHub, so the open PRs are unknown. The `error` message names the cause: unauthenticated (`GITHUB_TOKEN` is missing, invalid, or expired) does not retry away — fix the token first. Network blocked (a proxy or firewall blocks the request, or the connection times out) is retryable — try again. Report the cause text from `error` to the user. Use `AskUserQuestion` to ask: "Close the item without the open-PR check?" `force=True` skips the open-PR check completely. If the user confirms, call `mcp__plugin_dh_backlog__backlog_close` again with the same parameters and `force=True`. Report that result.
   - For any other `error`, report the error.
   - With no `error` key, report the result.

Then stop.

## Step 5.4: Resolve path — status:verified gate (SAM items only)

If operation is `resolve`:

1. Extract `**Plan**:` field from the matched item. If absent, skip this step entirely — non-SAM items have no verification gate.

2. If `**Plan**:` is present, check the GitHub Issue labels for `status:verified`:
   - Call `backlog view --selector "{title}"` and inspect the `labels` list in the returned dict.
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

2. Use the plan address from the matched item (the full filename stem, e.g., `Pe9f0a1b2-backlog-lifecycle-process-gaps`). Do not extract or truncate — the full stem IS the address. Call:

   ```bash
   plan status --plan-address "{address}"
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

4. Spawn a verification agent with subagent_type="dh:task-worker". Prompt must include: `item_ref`
   (the same selector used in Step 5.2), `section="Acceptance Criteria"`, plan address (e.g.,
   `P{id}`), and checklist status (100%). Instruct the agent to: call
   `mcp__plugin_dh_backlog__backlog_view(selector=item_ref, summary=False, sections=["Acceptance Criteria"])`
   — `summary=False` is required; `backlog_view` defaults to `summary=True`, which returns the
   compact routing manifest and ignores `sections` entirely — and parse each `-` line as a separate
   criterion itself, read the plan via
   `mcp__plugin_dh_sam__sam_plan(plan="{address}", config={"action": "read"})`, search
   `git log --oneline -20`, check relevant files for each criterion, and return per-criterion
   PASS/FAIL with file:line evidence. Do not parse or re-type the criteria text into the dispatch
   prompt — the agent has backlog MCP access and fetches the item's Acceptance Criteria section
   itself. Required return format:

   ```text
   [PASS] {criterion} — verified at {file}:{line} (or commit {sha})
   [FAIL] {criterion} — {gap description}
   Overall: PASS or FAIL (N/M criteria met)
   ```

   **If no acceptance criteria exist**: a filtered call for an absent section does not return an
   empty section — it returns an error dict with `section_filter_miss: true` and no `body` field.
   Instruct the agent: only when the response's `section_filter_miss` field is explicitly `true`,
   warn "No **Acceptance Criteria**: field found — falling back to description-based verification",
   then make a second `backlog_view(selector=item_ref, summary=False)` call (no `sections` filter) to
   fetch the item description, and verify against that instead. An `error` key present WITHOUT
   `section_filter_miss: true` is a different failure (transient backend error, ambiguous selector,
   etc.) — do not treat it as "no criteria"; report it as a block instead of silently falling back.

   **If the Acceptance Criteria section alone is oversized**: the same over-budget gate that applies
   to a whole-item fetch re-applies to a narrowed one — a criteria section large enough on its own
   still returns `_over_budget: true` with no criteria body, not an error. Instruct the agent: if the
   response contains `_over_budget: true`, do not treat it as "no criteria" — switch to EXTRACT-mode
   pagination instead. Call `backlog_view(selector=item_ref, map=True)` to find the Acceptance
   Criteria ordinal; if the map shows no children under it, page it directly with
   `navigate="{ordinal}", head=2000`, following `next_call` until `truncated=False`. If it has child
   ordinals (sub-heading structure), page each child individually the same way — recursing into any
   further nested children the same way, never stopping at the first level — and never the parent
   ordinal, which bounds only its child menu, not criteria text — until every leaf under the section
   has been read. Skip any ordinal the `map` response lists in `struck_ordinals`, and stop reading
   further into a branch the moment a `navigate` response returns `struck: true` — a struck criterion
   is retracted and must not be verified as if it were current.

5. Parse the agent verdict:

   ```text
   Acceptance Criteria Verification:

     [PASS] running X produces Y — verified at src/main.py:42
     [FAIL] file Z exists with field W — file exists but field W not found
     [PASS] test suite passes — confirmed via git log (commit abc123f)

   Overall: FAIL (2/3 criteria met)
   ```

6. Collect agent verdict:
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

7. `mcp__plugin_dh_backlog__backlog_resolve` searches for open PRs whose title or body contains the item's linked issue number. It refuses to resolve when the search finds one. It also refuses when the search fails. Step 11 handles both refusals. Commit messages in `git log` do not show open PRs, so use the resolve refusal as the open-PR check.

8. Use `AskUserQuestion` to ask: "Summarize what was done (1-2 sentences):" (free text — this is the required `summary` field).

9. Optionally gather additional evidence fields (can be skipped for trivial items):
    - `method` — "How was the work done?"
    - `notes` — "Any problems found or surprises?"
    - `follow_ups` — "Any follow-up tickets created?" (comma-separated refs)
    - `findings` — "Any retrospective learnings?"

10. Call `mcp__plugin_dh_backlog__backlog_resolve`. Leave `force` at its default of `false`:

    - `selector`: `"{title}"` or `"#{N}"`
    - `summary`: `"{summary}"`
    - `plan`: `"{plan_address}"` (if present — e.g., `"P{id}"`)
    - `method`: `"{method}"` (if provided)
    - `notes`: `"{notes}"` (if provided)
    - `follow_ups`: `"{follow_ups}"` (if provided)
    - `findings`: `"{findings}"` (if provided)

11. Check the returned dict for an `error` key.
    - If `error` starts with `Open PRs reference issue`, one or more open PRs contain the linked issue number in the title or body. The `warnings` list names each PR. A PR that mentions the issue does not always close it. Resolving now closes the issue and leaves those PRs pointing at a closed issue. Call `backlog update --selector "{title}" --status "in-progress"`. Report, pairing each `PR #{number}: {title}` line in `warnings` with the URL line immediately following it:

      ```text
      Backlog item "{title}" verified. Resolve stopped: these open PRs reference GitHub Issue #{N}:
      - PR #{number}: {PR title} ({PR url})
      Resolve the item again after these PRs merge or close.
      ```

      Then stop.
    - If `error` starts with `Open-PR search failed`, the item is not resolved. The search could not reach GitHub, so the open PRs are unknown. The `error` message names the cause: unauthenticated (`GITHUB_TOKEN` is missing, invalid, or expired) does not retry away — fix the token first. Network blocked (a proxy or firewall blocks the request, or the connection times out) is retryable — try again. Report the cause text from `error` to the user. Use `AskUserQuestion` to ask: "Resolve the item without the open-PR check?" `force=True` skips the open-PR check completely. If the user confirms, call `mcp__plugin_dh_backlog__backlog_resolve` again with the same parameters and `force=True`. Report that result. If the user does not confirm, stop.
    - For any other `error`, report the error and stop.
    - With no `error` key, report the result.

12. Before emitting Handoff E, determine whether all milestone issues are resolved:

    a. Read the `milestone` field from Step 5.2's `backlog_view` response (`backlog_resolve`'s own response carries no `milestone` field). If the item has no `milestone` value (null or empty), skip Handoff E — no milestone context exists.

    b. If a milestone is present, call:

       ```bash
       backlog list
       ```

       From the returned items, count those whose `milestone` field matches the resolved item's milestone AND whose `status` is NOT `done` or `resolved`. This is the `open_issues` count.

    c. Emit Handoff E only when `open_issues == 0`:

       ```text
       NEXT: skill="complete-milestone" args="{milestone number}" condition="all milestone issues status:done OR status:resolved AND open_issues == 0"
       ```

    d. If `open_issues > 0`, skip Handoff E — the milestone is not yet ready for completion.

## --force flag

The `--force` flag bypasses the Step 5.4 `status:verified` gate only. See Step 5.4 for the warning
text and when to use it. `force=True` on `backlog_resolve` is a separate switch: it skips the
open-PR search, and Step 11 sets it only after that search failed and the user confirmed the
resolve without it.

Usage:

```text
/work-backlog-item resolve {title} --force
/work-backlog-item resolve #{N} --force
```
