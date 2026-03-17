# Feature Context: Backlog State Reconciliation

## Document Metadata

- **Generated**: 2026-03-14
- **Input Type**: existing_document
- **Source**: Issue #714, groomed backlog item `.claude/backlog/p1-backlog-state-reconciliation-detect-and-resolve-localremote-.md`, analysis report `.claude/reports/backlog-state-machine-analysis-20260314.md`
- **Status**: DISCOVERY_COMPLETE

---

## Original Request

When backlog_list or backlog_view reads items, local cache (`.claude/backlog/*.md`) and GitHub issue state can disagree silently. Closed issues appear as open, in-progress labels persist on closed issues, and groomed items show no status. No mechanism detects or resolves these divergences.

What is needed: a reconciliation layer that (1) detects state divergence between local frontmatter, GitHub issue state (open/closed), and GitHub `status:*` labels on every read operation, (2) determines sync direction using the state machine DAG (valid transitions auto-apply, invalid ones flag for human review), (3) checks for active local work (plan files, in-progress tasks, uncommitted changes) before accepting a "closed" state from GitHub, and (4) surfaces divergence clearly in list/view output instead of silently showing stale data.

---

## Core Intent Analysis

### WHO (Target Users)

- **Primary**: The orchestrator agent and human operators who use `backlog list`, `backlog view`, `backlog list --with-status`, and `backlog list --from-github` to plan, prioritize, and route work.
- **Secondary**: Downstream skills (`/work-backlog-item`, `/implement-feature`, `/complete-implementation`) that depend on accurate backlog state to route tasks correctly.
- **Tertiary**: MCP consumers calling `backlog_list`, `backlog_view`, and `backlog_groom` via the FastMCP server at `.claude/skills/backlog/backlog_core/server.py`.

### WHAT (Desired Outcome)

Every backlog read operation returns accurate, current state. Specifically:

1. Items whose GitHub issues are closed do not appear in default list output.
2. Items with GitHub `status:*` labels that differ from local `status` frontmatter are detected and either auto-corrected (if DAG-valid) or flagged (if invalid).
3. Grooming does not leave items in a "stateless void" (no label, stale frontmatter).
4. `--with-status` returns a non-blank status for every item with a linked GitHub issue.
5. Work-in-progress items are protected from incorrect auto-closure when GitHub closes an issue that still has active local work.
6. Divergences are surfaced visibly in output, not silently swallowed.

### WHEN (Trigger Conditions)

- Every `backlog list` invocation (default, `--from-github`, `--with-status`).
- Every `backlog view` invocation for a specific item.
- Every `backlog groom` invocation that transitions an item's state.
- MCP equivalents: `backlog_list()`, `backlog_view()`, `backlog_groom()`.

### WHY (Problem Being Solved)

The backlog is the primary planning surface for the project. Every read operation currently returns stale or incorrect data:

- Closed items pollute listings (58 items stuck in undefined `status: open` state).
- `--with-status` returns blank status for any closed issue (GitHub API query is open-only).
- Grooming removes the `status:needs-grooming` label but never adds `status:groomed`, leaving items in a stateless void.
- No code path writes closure state from GitHub back to local frontmatter.
- Count-based planning metrics (open items, in-progress items) are inflated by stale entries.

This erodes trust in the entire backlog system and makes automated work routing unreliable.

---

## Codebase Research

### Similar Patterns Found

#### Pattern 1: Staleness Check (`_check_item_staleness`)

- **Location**: `.claude/skills/backlog/scripts/backlog.py:601-622`
- **Relevance**: An existing function that compares `last_synced` timestamp against GitHub `updated_at`. It detects temporal staleness but does NOT compare state values (open/closed, status labels). It returns a boolean but no caller acts on state divergence.
- **Reusable**: The pattern of comparing local metadata against GitHub issue fields is directly relevant. The function could be extended or a sibling function created for state-level divergence detection.

#### Pattern 2: `apply_github_transition()` in state_handler

- **Location**: `.claude/skills/backlog/scripts/state_handler.py:138-177`
- **Relevance**: The atomic label-swap function that removes old `status:*` label and adds new one. Already used by 4 of 8 transitions (in-progress, done, resolved, closed). The reconciliation layer needs this for auto-correcting DAG-valid divergences.
- **Reusable**: The function and `VALID_TRANSITIONS` DAG at `state_handler.py:54-63` are the core validation mechanism. Reconciliation can call `validate_transition()` at `state_handler.py:99-130` to check if a detected divergence is DAG-valid before auto-applying.

#### Pattern 3: `_batch_fetch_statuses()` (open-only query)

- **Location**: `.claude/skills/backlog/scripts/backlog.py:755-783`
- **Relevance**: This is the function that queries GitHub for status labels, but only for `state="open"` issues. Closed issues are invisible to it. This is the root cause of blank statuses for closed items.
- **Reusable**: The batch-fetch pattern (query GitHub once, build a map, iterate local items) is efficient and should be preserved. The query parameter needs to change from `state="open"` to `state="all"` or a two-pass approach.

#### Pattern 4: `_refresh_local_cache_from_github()` (open-only refresh)

- **Location**: `.claude/skills/backlog/scripts/backlog.py:860-886`
- **Relevance**: This is the `--from-github` code path. It fetches only open issues, so closed issues are never refreshed in local cache. This is the other root cause of stale data.
- **Reusable**: The refresh-then-list pattern is correct; the query scope is the problem.

#### Pattern 5: MCP Server Delegation

- **Location**: `.claude/skills/backlog/backlog_core/server.py:65-105`
- **Relevance**: The MCP `backlog_list` tool delegates to `operations.list_items()` via `asyncio.to_thread`. Currently has no `include_closed` parameter. Any new CLI flags need corresponding MCP tool parameters.
- **Reusable**: The delegation pattern is standard. New parameters propagate through this layer.

### Existing Infrastructure

- **State machine DAG**: `VALID_TRANSITIONS` at `state_handler.py:54-63` — fully defined, maps all 8 states to their valid target states.
- **`validate_transition()`**: `state_handler.py:99-130` — validates whether a from_state to to_state transition is allowed.
- **`apply_github_transition()`**: `state_handler.py:138-177` — atomically swaps GitHub labels.
- **`_update_item_metadata()`**: Used by close/resolve to update local frontmatter fields.
- **`_check_item_staleness()`**: `backlog.py:601-622` — temporal staleness detection (exists but does not detect state divergence).
- **Active task context files**: `.claude/context/active-task-{session_id}.json` — written by `/start-task`, indicates work in progress. Backlog scripts do not currently read these.
- **Plan file discovery**: Plan files follow `plan/tasks-*-{slug}*.md` naming convention. Backlog scripts do not currently check for their existence.

### Code References

- `backlog.py:683` — default `status: open` on item creation (not a valid state machine state)
- `backlog.py:755-783` — `_batch_fetch_statuses()` queries `state="open"` only
- `backlog.py:860-886` — `_refresh_local_cache_from_github()` queries `state="open"` only
- `backlog.py:1746-1747` — grooming removes label but never adds replacement
- `backlog.py:1576` — `_write_groomed_to_item_file()` updates `groomed` date but not `status`
- `state_handler.py:54-63` — `VALID_TRANSITIONS` DAG definition
- `state_handler.py:138-177` — `apply_github_transition()` atomic label swap
- `server.py:65-105` — MCP `backlog_list` tool (no `include_closed` parameter)

---

## Use Scenarios

### Scenario 1: Operator Lists Backlog and Sees Only Active Items

**Actor**: Human operator or orchestrator agent
**Trigger**: Runs `backlog list` to see current work
**Goal**: Get an accurate list of items that are genuinely open and actionable
**Expected Outcome**: Items whose GitHub issues are closed are excluded from output. Only items in active lifecycle states (needs-grooming, groomed, in-milestone, in-progress, blocked) appear. The operator trusts the count and can make planning decisions based on it.

### Scenario 2: Operator Requests Status and Gets Non-Blank Values

**Actor**: Human operator or orchestrator agent
**Trigger**: Runs `backlog list --with-status` to see where items stand in the lifecycle
**Goal**: Every item with a linked GitHub issue shows its current status
**Expected Outcome**: No blank status fields. Closed items show `closed` or `done`/`resolved`. Active items show their current `status:*` label value. The operator can filter and sort by status reliably.

### Scenario 3: Auto-Correction of DAG-Valid Divergence

**Actor**: System (automatic, triggered by read operation)
**Trigger**: `backlog list --from-github` encounters an item where local status is `needs-grooming` but GitHub has `status:groomed` label
**Goal**: Transparently correct the local cache to match GitHub
**Expected Outcome**: The local frontmatter `status` field is updated to `groomed`. The correction is reported in output (e.g., "Auto-corrected: #427 needs-grooming -> groomed"). The item appears with the correct status in the listing.

### Scenario 4: Flagging Invalid Divergence

**Actor**: System (automatic, triggered by read operation)
**Trigger**: `backlog list --from-github` encounters an item where local status is `done` but GitHub has `status:needs-grooming` label (an invalid backward transition)
**Goal**: Surface the invalid divergence for human review instead of silently applying it
**Expected Outcome**: A warning is emitted in the output (e.g., "WARNING: #427 divergence: local=done, GitHub=needs-grooming (invalid transition)"). The local cache is NOT modified. The item appears with its local status plus a divergence flag.

### Scenario 5: WIP Protection Against Premature Closure

**Actor**: System (automatic, triggered by read operation)
**Trigger**: `backlog list --from-github` detects a GitHub issue is `state=closed`, but a `plan/tasks-*-{slug}*.md` file exists or `.claude/context/active-task-*.json` references this item
**Goal**: Prevent auto-closure of local cache when active work is detected
**Expected Outcome**: A warning is emitted (e.g., "WARNING: #427 closed on GitHub but has active plan file plan/tasks-3-my-feature.md"). The local cache is NOT updated to closed. The item remains visible in the default listing.

### Scenario 6: Grooming Produces Consistent State

**Actor**: Human operator running `backlog groom`
**Trigger**: Grooming an item with `status:needs-grooming` and RT-ICA approves
**Goal**: After grooming, the item has a consistent state across local and GitHub
**Expected Outcome**: GitHub label transitions atomically from `status:needs-grooming` to `status:groomed`. Local frontmatter `status` updates to `groomed`. No intermediate stateless state.

### Scenario 7: Discovering Closed Items on Demand

**Actor**: Human operator
**Trigger**: Runs `backlog list --include-closed` to see all items including closed ones
**Goal**: Review historical items, check what was resolved, audit completeness
**Expected Outcome**: All items appear, with closed items clearly marked. Status column shows `done`, `resolved`, or `closed` for terminal items.

---

## Gap Analysis

### Identified Gaps

| # | Category | Gap Description | Impact |
|---|----------|-----------------|--------|
| 1 | Scope | "Every read operation" reconciliation vs. "on-demand" reconciliation — should default `backlog list` (no `--from-github`) trigger GitHub API calls for divergence detection, or only when `--from-github` is passed? | Determines API call frequency, rate limit impact, and offline behavior |
| 2 | Behavior | What constitutes "active local work" for WIP protection — plan file existence alone, or must there be an in-progress task within that plan file? | Over-broad definition blocks valid closures; too narrow misses active work |
| 3 | Behavior | When a DAG-valid divergence is auto-corrected, should the correction persist (write to local file) or be transient (display-only for that invocation)? | Persistent correction prevents re-detection on every read; transient means every read re-checks |
| 4 | Scope | The 58 items with `status: open` (undefined state) — is migrating them to valid states part of this feature or a separate task? | Blocks AC#8; migration logic exists at `backlog.py:2021-2062` but may need verification |
| 5 | Integration | The MCP server (`server.py`) needs new parameters (`include_closed`) — is updating the MCP interface in scope? | MCP consumers cannot access closed items until server parameters are added |
| 6 | Behavior | GitHub API rate limits when fetching `state="all"` — the repository has 100+ issues. Should reconciliation batch all issues or only check items present in local cache? | Full fetch may hit rate limits; targeted fetch may miss items created externally |
| 7 | Scope | Should `backlog view` for a single item also trigger reconciliation (check GitHub state for that one item), or only `backlog list`? | AC#5 and AC#6 mention `backlog view`; single-item reconciliation is cheaper than batch |
| 8 | Integration | `backlog_groom()` grooming fix (AC#4) — is this a prerequisite that should be done first, or part of this reconciliation feature? | The grooming bug is a root cause of divergence; fixing it prevents new divergences |

---

## Questions Requiring Resolution

### Q1: Reconciliation trigger scope

- **Category**: Scope
- **Gap**: Gap #1 — "every read" vs. "on-demand"
- **Question**: Should the default `backlog list` (without `--from-github`) trigger GitHub API calls to detect divergences? Or should divergence detection only activate when `--from-github` is explicitly passed?
- **Options**:
  - A) Default `backlog list` stays local-only (fast, offline-capable); `--from-github` triggers full reconciliation including divergence detection
  - B) Default `backlog list` does lightweight divergence detection (compare local `status` against cached GitHub state from last sync); `--from-github` triggers full remote reconciliation
  - C) All read operations always query GitHub (consistent but slow, requires network)
- **Why It Matters**: Option A preserves current offline behavior but means divergences persist until explicit refresh. Option C may cause unacceptable latency and rate-limit issues. Option B is a middle ground but adds complexity.
- **Resolution**: _pending_

### Q2: WIP protection definition

- **Category**: Behavior
- **Gap**: Gap #2 — what counts as "active local work"
- **Question**: What signals should block auto-closure when GitHub shows an issue as closed? Specifically: (a) any `plan/tasks-*-{slug}*.md` file exists, (b) a plan file exists AND contains at least one task with status IN PROGRESS, (c) `.claude/context/active-task-*.json` references this item, (d) uncommitted changes in files related to this item?
- **Options**:
  - A) Plan file existence alone is sufficient to block auto-closure
  - B) Plan file must have at least one IN PROGRESS task
  - C) Either plan file with IN PROGRESS task OR active-task context file
  - D) All of the above plus uncommitted changes check
- **Why It Matters**: Option A is safest but may block legitimate closures of items with completed plan files. Option D is most comprehensive but requires git status checks on every reconciliation.
- **Resolution**: _pending_

### Q3: Auto-correction persistence

- **Category**: Behavior
- **Gap**: Gap #3 — persist corrections or display-only
- **Question**: When a DAG-valid divergence is detected and auto-corrected, should the correction be written to the local `.claude/backlog/*.md` file, or should it only be reflected in the current output?
- **Options**:
  - A) Persist to local file (write frontmatter) — divergence is fixed permanently
  - B) Display-only — local file unchanged, divergence re-detected on each read
- **Why It Matters**: Option A prevents redundant re-detection but modifies files that git may track. Option B is safer but means every `--from-github` invocation re-runs the same corrections.
- **Resolution**: _pending_

### Q4: Migration of 58 "status: open" items

- **Category**: Scope
- **Gap**: Gap #4 — in-scope or separate task
- **Question**: Is migrating the 58 items currently stuck in `status: open` (an undefined state) part of this feature, or should it be handled as a separate task? AC#8 references this migration.
- **Options**:
  - A) In scope — the reconciliation feature includes a migration pass
  - B) Separate task — reconciliation handles detection and flagging; migration is a one-time cleanup
- **Why It Matters**: Including migration adds scope but satisfies AC#8. Excluding it means AC#8 is deferred.
- **Resolution**: _pending_

### Q5: Grooming fix as prerequisite or co-delivery

- **Category**: Integration
- **Gap**: Gap #8 — grooming bug relationship
- **Question**: The grooming bug (removes `status:needs-grooming` label without adding `status:groomed`) is a root cause of divergence. Should fixing it (AC#4) be a prerequisite task done first, or delivered as part of the reconciliation feature?
- **Options**:
  - A) Prerequisite — fix grooming first in a separate PR, then build reconciliation
  - B) Co-delivery — fix grooming as part of the reconciliation feature
- **Why It Matters**: Option A reduces the reconciliation PR scope and prevents new divergences during development. Option B keeps all state-consistency work in one deliverable.
- **Resolution**: _pending_

---

## Goals (Pending Resolution)

_These goals will be finalized after questions are resolved._

1. Divergence detection: on read operations, compare local frontmatter `status` against GitHub issue state and `status:*` labels; report mismatches.
2. Auto-correction: for DAG-valid divergences, update local state to match GitHub (sync direction and persistence TBD per Q1, Q3).
3. Invalid divergence flagging: for transitions not in `VALID_TRANSITIONS`, emit warnings in output without modifying local state.
4. WIP protection: before accepting GitHub `state=closed`, check for active local work signals (definition TBD per Q2) and block auto-closure if detected.
5. Closed-item exclusion: default `backlog list` excludes items whose GitHub issues are closed; `--include-closed` flag to override.
6. Grooming consistency: grooming atomically transitions labels and updates local frontmatter (co-delivery vs. prerequisite TBD per Q5).
7. Non-blank status guarantee: `--with-status` returns a status value for every item with a linked GitHub issue.
8. Migration of undefined states: 58 items with `status: open` mapped to valid lifecycle states (in-scope vs. separate TBD per Q4).
9. MCP interface update: new parameters (`include_closed`) added to MCP server tools.
10. Test coverage: reconciliation behavior exercised by tests with mock GitHub state.

---

## Next Steps

After questions are resolved:

1. Update "Resolution" fields in Questions section
2. Finalize Goals section
3. Proceed to RT-ICA assessment
4. Then proceed to architecture design via `@python3-development:python-cli-design-spec`
