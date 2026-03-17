# Step Procedures Reference

Detailed procedure content for Steps 0, 1, 1b, 2.3, 5, Q, P, and R.

---

## Step 1: Find the Backlog Item — 3-Strategy Fallback Chain

**Bypass:** If `<mode/>` is `#N`, a bare number, or a GitHub issue URL — skip this step and go
to Step 1b. Those inputs resolve via `backlog_view` directly; no matching strategy is needed.

Apply the following 3-strategy fallback chain. Move to the next strategy only when the current
strategy returns zero matches.

```mermaid
flowchart TD
    Start([Title query]) --> S1

    S1["Strategy 1: Substring Match<br>backlog_list(title=query)"] --> R1{Results?}
    R1 -->|1 match| Done([Use matched item])
    R1 -->|Multiple matches| Pick[Present list to user<br>or pick first in AUTO_MODE]
    R1 -->|0 matches| S2

    S2["Strategy 2: Filter-First<br>Derive type_hint and topic_hint from query"] --> Call2["backlog_list(type=type_hint, topic=topic_hint)<br>then substring-match query against returned titles"]
    Call2 --> R2{Results?}
    R2 -->|1+ matches| Done2([Use best match])
    R2 -->|0 matches| S3

    S3["Strategy 3: LLM Semantic Match<br>backlog_list() — all open items"] --> Batch["Present all titles + types + topics to LLM<br>Token budget: 245 items x ~25 tokens/item = ~6125 tokens under 10K"]
    Batch --> LLM["LLM selects best semantic match<br>from candidate titles"]
    LLM --> R3{Match found?}
    R3 -->|Yes| Done3([Use LLM-selected item])
    R3 -->|No| NoMatch([No match — offer to create via /create-backlog-item])
```

### Strategy 1 — Substring Match

Call `backlog_list(title=query)`. The `title` parameter performs a case-insensitive substring
match server-side. If exactly one item is returned, use it. If multiple items are returned,
present a numbered list and ask the user to choose (in AUTO_MODE, pick the first). If zero
items are returned, proceed to Strategy 2.

### Strategy 2 — Filter-First

Derive filter hints from the query before calling `backlog_list`:

**`type_hint`**: scan query words for keyword groups (case-insensitive):

- `bug`, `fix`, `broken`, `error` → `Bug`
- `feature`, `add`, `new`, `implement` → `Feature`
- `refactor`, `clean`, `restructure` → `Refactor`
- no match → `None` (omit `type` parameter)

**`topic_hint`**: longest non-stop-word from the query, converted to kebab-case slug. If none
can be derived, omit the `topic` parameter.

Call `backlog_list(type=type_hint, topic=topic_hint)` (omit any `None` parameters). Then
perform a case-insensitive substring match of the original query against the `title` field of
each returned entry. Items whose titles contain the query substring are candidates.

The `type` and `topic` filters compose with AND logic. Items missing the filtered metadata field
are excluded when that filter is active.

### Strategy 3 — LLM Semantic Match

Call `backlog_list()` with no filters to load all open items. Each returned item includes
`title`, `type`, and `topic` fields. Read the full list in the current context and select the
item whose title, type, and topic best match the intent of the query. The token cost is bounded:
**245 items × ~25 tokens/item ≈ 6,125 tokens (under 10K budget)**. If two or more candidates
are plausible, read their per-item files via `backlog_view` before choosing.

### Zero-match handling after all 3 strategies

- **Interactive mode:** report "No backlog item found matching: {title}" and offer to create one
  via `/create-backlog-item`.
- **AUTO_MODE:** log `[AUTO] No item found — invoking create-backlog-item --auto {title}`,
  invoke `Skill(skill: "create-backlog-item", args: "--auto {title}")`, then re-run Step 1.

---

## Step 1b: Completed Issue Discovery

When an issue is found to be already closed (`state: closed`), gather evidence before closing the local backlog item:

1. **Search for commits referencing the issue**:

   ```bash
   git log --oneline --all -20 --grep="#N"
   ```

2. **Search for merged PRs via git history**:

   ```bash
   git log --oneline --all -20 --grep="Fixes #N\|Closes #N"
   ```

3. **Report findings**:

   If commits or PRs are found:

   ```text
   Issue #{N} is already closed.

   Evidence of completion:
   - PR #{pr}: {title} (merged {date})
     URL: {url}
   - Commit {sha}: {message}

   Closing local backlog item with evidence.
   ```

   Call the `mcp__backlog__backlog_resolve` tool with `selector="{title}"` and
   `summary="Completed via PR #{pr} / commit {sha}"`.

   If no commits or PRs reference the issue:

   ```text
   Issue #{N} is already closed but no commits or PRs reference it.
   The issue may have been closed manually or via external process.

   Options:
   - close: Close the local backlog item (with manual reason)
   - resolve: Mark as no longer applicable
   - reopen: If the work was not actually done, reopen the issue
   ```

   Use `AskUserQuestion` to ask which action to take. In AUTO_MODE, log
   `[AUTO] STOP — Issue #N closed, no commit/PR evidence found` and stop.

---

## Step 2.3: Already Implemented Check

Before planning work, verify the described feature/fix hasn't already been implemented:

1. **Search for commits and merged PRs matching the item's topic** (use keywords from the title):

   ```bash
   git log --oneline --all -30 --grep="{keyword from title}"
   git log --oneline --all -30 --merges --grep="{keyword from title}"
   ```

2. **Spot-check the codebase** — read the file(s) at the suggested location and verify whether the described behavior already exists.

If evidence shows the work is already done:

- Call the `mcp__backlog__backlog_resolve` tool with `selector="{title}"` and
  `summary="Already implemented via PR #{pr} / commit {sha}"`.
- Report to the user and stop — no planning needed.

In AUTO_MODE: log `[AUTO] Work already implemented — closing #{N} with evidence: {sha/PR}` and stop.

If no evidence, proceed to Step 2.5 (GitHub Issue Sync).

---

## Step 0: Interactive Browser

1. Call the `mcp__backlog__backlog_list` tool with `with_status=true`.

   Parse the returned dict. Each entry in `items` has `section`, `title`, `issue`, `plan`, `status`, `milestone`, `file_path` (index format), `groomed` (true if item has groomed content).

2. **Groomed** = item has `groomed: true` in JSON, or `## Groomed` section in its per-item file (`.claude/backlog/{priority}-{slug}.md`). Read the item file; if groomed sections present, use them.

3. Present a numbered list. Use these status indicators in user-visible output only:

   <eg>
   Backlog Items:

   P0
     1. ✅ SAM: Error Recovery / Rollback Procedures       [#12  status:in-progress  v1.0]
     2. 🔍 SAM: Regex False Positive Suppression           [#14  status:needs-grooming  v1.0]

   P1
     3. 📋 SAM: Validate Task File Schema                  [no issue]
     4. 📋 SAM: Implement Feature Dry-Run Mode             [no issue]

   P2
     5. 🔍 SAM: Context Window Budget Tracking             [#18  status:needs-grooming  —]

   Ideas
     6. 📋 SAM: Multi-Repo Support                         [no issue]

   Status: ✅ = planned/in-progress  🔍 = groomed/needs-grooming  📋 = not yet groomed

   Options:
     [number]   — Select item to work on
     G [number] — Groom a specific item
     G all      — Groom all ungroomed items
     D [number] — Show full details for an item
</eg>

4. Use `AskUserQuestion` to ask: "Which item would you like to work on next?"

5. Handle the response:
   - `[number]` — use that item's title as the working title and proceed to Step 1
   - `G [number]` — invoke `Skill(skill="groom-backlog-item", args="{item title}")` then re-display the list
   - `G all` — invoke `Skill(skill="groom-backlog-item", args="all")` then re-display the list
   - `D [number]` — display the full item description, research_first field, and groomed content (if present in the item file under `## Groomed`), then re-display the list
   - `C [number]` — proceed to Step 9 (close path) with that item's title
   - `R [number]` — proceed to Step 9 (resolve path) with that item's title

---

## Step 5: Feature Request Template

Build this string for `add-new-feature`:

<eg>
## Backlog Item: {title}

**Source**: {source}
**Priority**: {priority section — P0/P1/P2/Ideas}
**Added**: {added date}

### Description

{description text}

### Research Questions

{research_first text, or "None" if absent}

### Suggested Location

{suggested_location text, or "To be determined during architecture phase" if absent}

### RT-ICA Assessment

**Decision**: APPROVED
**Goal**: {goal statement}
**Verified conditions**: {list of AVAILABLE items}
**Assumptions to confirm**: {list of DERIVABLE items, or "None"}

### Grooming Context

{full context manifest from Step 3, if available}

### Impact Radius

{full content of the ## Impact Radius section from the groomed item file}

**Planner constraint**: Create tasks for every item listed above, or document the exclusion reason inline. The plan is incomplete if any row in the Impact Radius is unaddressed.

**Ecosystem Completeness Checklist** (must all be checked before the plan can be marked complete):
- [ ] Every upstream producer updated or verified compatible
- [ ] Every downstream consumer migrated to new interface
- [ ] Every stale document updated
- [ ] Old interface deprecated or removed (if replacing)
- [ ] CI/config files updated and validated

### Stack Profile (optional)

{stack profile name if --stack specified, e.g., python-fastapi}
</eg>

If `--stack` was specified, append a "Stack profile" line. If `--language` was specified and is not `python`, invoke the corresponding language plugin (e.g., `/typescript-development:add-new-feature` for `typescript`).

---

## Step Q: Quick Mode

**Trigger:** `$0` is `--quick`. Skips grooming, RT-ICA, and SAM planning. For one-file fixes, broken links, and typo patches where full pipeline overhead is disproportionate.

1. Extract title from `$1`+ joined. Build slug: title lowercased, spaces → hyphens.

2. Find the item in `.claude/backlog/` per-item files (same logic as Step 1). If not found, create a minimal item with the title.

3. Extract the item's description and acceptance criteria if available.

4. Write the plan to `plan/quick/{slug}.md` with frontmatter `type: quick`, fields: `title`, `priority`, `issue`, `created`. Body sections: `## Task` (description), `## Steps` (1-3 checklist items derived from description), `## Done When` (acceptance_criteria if present, else goal from description).

5. Call the `mcp__backlog__backlog_update` tool with `selector="{title}"` and `plan="plan/quick/{slug}.md"` to record the plan.

6. Report:

   <eg>
   Quick plan created: plan/quick/{slug}.md
   Steps: {N} tasks

   To execute: /implement-feature plan/quick/{slug}.md
   To close:   /work-backlog-item close {title}
   </eg>

---

## Step P: Progress Report

**Trigger:** `$0` is `progress`.

1. Scan `.claude/backlog/` per-item files. Count items by priority (P0, P1, P2, Ideas) and status (done, resolved, closed).

2. Query GitHub for the active milestone:

   ```bash
   gh api repos/Jamie-BitFlight/claude_skills/milestones --jq '[.[] | select(.state=="open")] | sort_by(.due_on) | first'
   ```

   Extract: milestone number, title, open_issues, closed_issues.

3. For items in the active milestone, identify the highest-priority groomed item with no `**Plan**:` field — that is the recommended next action.

4. Display:

   <eg>
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
     /work-backlog-item {title}  — {title} (P{x}, groomed, in active milestone)
   </eg>

   If no active milestone exists, omit the milestone section and show only Overall Backlog counts.

   If the backlog directory is empty, note: `(no backlog items found)`

---

## Step R: Resume Report

**Trigger:** `$0` is `resume`.

1. Extract title from `$1`+ joined. If `$1` starts with `#`, fetch title from GitHub Issue (same logic as Step 1b).

2. Find the item in `.claude/backlog/` per-item files. Extract `metadata.plan` field. If absent:

   <eg>
   No plan file recorded for "{title}".
   Run /work-backlog-item {title} to create a plan first.
   </eg>

   Then stop.

3. Read the plan file. Parse the checklist:
   - `total_tasks` — lines matching `- \[[ x]\]`
   - `checked_tasks` — lines matching `- \[x\]`
   - `last_checked` — last line matching `- \[x\]` (trim the `- [x]` prefix)
   - `first_unchecked` — first line matching `- \[ \]` (trim the `- [ ]` prefix)

4. Compute `completion_pct = checked_tasks * 100 / total_tasks` (integer).

5. Report:

   <eg>
   Resume: {title}
   Plan:   {plan file path}

   Progress: {checked_tasks}/{total_tasks} tasks ({completion_pct}%)

   Last completed:  {last_checked task text}
   Next to do:      {first_unchecked task text}

   To continue: /implement-feature {slug}
   To close:    /work-backlog-item close {title}
   </eg>

   If `checked_tasks == 0`, report "No tasks completed yet."
   If `checked_tasks == total_tasks`, report "All tasks complete — run /work-backlog-item close {title}."
