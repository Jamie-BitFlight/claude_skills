---
name: Backlog state reconciliation — detect and resolve local/remote divergence with transition-aware sync
description: "When backlog_list or backlog_view reads items, local cache (.claude/backlog/*.md) and GitHub issue state can disagree silently. Closed issues appear as open, in-progress labels persist on closed issues, and groomed items show no status. No mechanism detects or resolves these divergences.\n\nWhat's needed: a reconciliation layer that (1) detects state divergence between local frontmatter, GitHub issue state (open/closed), and GitHub status:* labels on every read operation, (2) determines sync direction using the state machine DAG — valid transitions auto-apply, invalid ones flag for human review, (3) checks for active local work (plan files, in-progress tasks, uncommitted changes) before accepting a 'closed' state from GitHub, and (4) surfaces divergence clearly in list/view output instead of silently showing stale data.\n\nExample scenario: issue #300 was closed on GitHub but backlog_list showed it as open because local cache was never updated. The reconciliation layer would detect state=closed on GitHub, check for local work-in-progress, find none, and auto-transition the local cache to match.\n\nDepends on #426 (state machine implementation) for the DAG validation and atomic transition functions. This item adds the divergence-detection and auto-reconciliation logic on top.\n\nAnalysis report with full state inventory, transition matrix, and 6 identified sync gaps: .claude/reports/backlog-state-machine-analysis-20260314.md"
metadata:
  topic: backlog-state-reconciliation-detect-and-resolve-localremote-
  source: 'Session observation — #300 appeared as open in backlog_list despite being closed on GitHub (2026-03-14)'
  added: '2026-03-14'
  priority: completed
  type: Feature
  status: done
  issue: '#714'
  last_synced: '2026-03-14T21:57:27Z'
  groomed: '2026-03-14'
  plan: plan/tasks-1-backlog-state-reconciliation.yaml
---

## Fact-Check

<div><sub>2026-03-14T21:54:33Z</sub>

**Claims Checked**: 5
**VERIFIED**: 5 | **REFUTED**: 0 | **INCONCLUSIVE**: 0

| Claim | Verdict | Evidence |
|-------|---------|----------|
| backlog_list returns closed issues as open | VERIFIED | Code: backlog.py:860-886 — `_refresh_local_cache_from_github()` calls `repo_obj.get_issues(state="open")`, never fetches closed. Local cache files persist after closure. Observed: #300 closed on GitHub, appeared in backlog_list output. |
| Only 4 of 8 transitions use `apply_github_transition()` | VERIFIED | Code: backlog.py:1623 (in-progress), :1188 (done), :1299 (resolved), :1074 (closed) use it. Groom (:1746), block, milestone transitions do not. |
| Grooming removes label but never adds replacement | VERIFIED | Code: backlog.py:1746-1747 — `issue.remove_from_labels("status:needs-grooming")` with no subsequent `add_to_labels("status:groomed")` |
| 58 items stuck in `status: open` (undefined state) | VERIFIED | Code: backlog.py:683 defaults to `status: open`. `open` not in `VALID_TRANSITIONS` DAG at state_handler.py:54-63 |
| No mechanism syncs closed state from GitHub back to local cache | VERIFIED | Code: `_batch_fetch_statuses()` at backlog.py:755-783 only queries `state="open"` issues. No code path writes closure state to local frontmatter. |

**Method**: All claims verified via direct codebase-analyzer agent reads of source files with file:line citations. Analysis report: `.claude/reports/backlog-state-machine-analysis-20260314.md`
</div>

## RT-ICA

<div><sub>2026-03-14T21:54:52Z</sub>

**Goal**: Implement a reconciliation layer that detects state divergence between local backlog cache and GitHub, determines sync direction via the state machine DAG, and auto-resolves or flags divergences.

**Conditions**:
1. State machine DAG with valid transitions defined | **AVAILABLE** | state_handler.py:54-63 defines `VALID_TRANSITIONS` dict
2. `apply_github_transition()` function for atomic state changes | **AVAILABLE** | state_handler.py:138-177
3. GitHub API access for reading issue state and labels | **AVAILABLE** | PyGithub via `_get_github()` / `_try_get_github()` in backlog.py
4. Local frontmatter read/write for status field | **AVAILABLE** | `_update_item_metadata()` used by close/resolve already
5. #426 state machine enforcement complete (all transitions use state_handler) | **MISSING** | #426 is closed on GitHub but labeled `status:in-progress` — ironically demonstrating the bug this item fixes. Early transitions (groom, block, milestone) still bypass state_handler.
6. Work-in-progress detection signals (plan files, active tasks, uncommitted changes) | **DERIVABLE** | Plan files discoverable via `plan/tasks-*-{slug}*` glob. Active tasks via `.claude/context/active-task-*.json`. Uncommitted changes via `git status`. No unified "is this item being worked on" function exists yet.
7. Batch reconciliation performance (fetching all issues including closed) | **DERIVABLE** | PyGithub `get_issues(state="all")` exists but may be slow for large repos. Pagination and rate limits need consideration.

**Decision**: APPROVED — #426 dependency is soft. Reconciliation can detect divergence and flag it even without all transitions using state_handler. The reconciliation layer can call `apply_github_transition()` for transitions that already work, and report-only for those that don't.

**Assumptions to confirm**:
- Condition 6: Need to define what constitutes "active local work" — is a plan file enough, or must there be an in-progress task?
- Condition 7: Need to measure GitHub API cost of fetching all issues (open + closed) vs. current open-only approach
</div>

## Groomed (2026-03-14)

### Issue Classification

<div><sub>2026-03-14T21:55:03Z</sub>

**Type**: `missing-guardrail`

**Rationale**: The system has no mechanism to detect or reconcile state divergence between local cache and GitHub. This is not a defect in existing logic (the code does what it was written to do — fetch open issues only) and not a recurring pattern (it's a permanent gap). It's a missing guardrail: the system silently presents stale data because no validation layer exists to catch the inconsistency.

**Scenario-target**: When any backlog read operation (list, view) encounters an item whose local state differs from GitHub state, the divergence is detected and either auto-resolved (if the transition is valid per the DAG) or flagged for human review (if invalid or work-in-progress detected).

**Analysis method**: None required (missing-guardrail type). Proceed directly to grooming.
</div>

### Reproducibility

<div><sub>2026-03-14T21:55:51Z</sub>


1. Ensure issue #300 is closed on GitHub (it is — verified as the trigger case).
2. Run `backlog list` (without `--from-github`). Observe: #300 appears in the output as an open backlog item.
3. Run `backlog list --with-status`. Observe: #300 still appears, with a blank status field (not marked closed).
4. Run `backlog list --from-github`. Observe: the local cache is refreshed from GitHub open issues only; #300 remains in the list because `_refresh_local_cache_from_github()` calls `repo_obj.get_issues(state="open")` and the closed issue is excluded from that result, so the local file is never updated.
5. Inspect `.claude/backlog/p0-streamline-backlog-urlissue-number-handling-to-use-backlogpy.md` — the local file still exists with `status: open` in frontmatter.
6. Run `backlog groom` on any `needs-grooming` item and approve it. Check the GitHub issue: the `status:needs-grooming` label is removed but no `status:groomed` label is added. The item is now in a "stateless void" — no `status:*` label on GitHub and local `status` field unchanged.

</div>

### Output / Evidence

<div><sub>2026-03-14T21:56:04Z</sub>


- Verified in code at `backlog.py — _refresh_local_cache_from_github()`: only fetches `state="open"` issues; closed issues are never fetched.
- Verified in code at `backlog.py — _batch_fetch_statuses()`: returns empty status for closed issues because the query is `get_issues(state="open")` only.
- Verified in code at `backlog.py — _build_backlog_frontmatter()`: newly created items default to `status: open`, which is not a state in the `VALID_TRANSITIONS` DAG (`state_handler.py — VALID_TRANSITIONS`).
- Verified in code at `backlog.py — backlog_groom()` (lines 1746-1747): `issue.remove_from_labels("status:needs-grooming")` executes with no subsequent `issue.add_to_labels("status:groomed")` call. Local `status` field is never updated.
- Observed: 58 local backlog files contain `status: open`, a state not in the state machine DAG.
- Observed: #426 is closed on GitHub but carries a `status:in-progress` label — an item that demonstrates the exact divergence this ticket is meant to fix.
- Analysis report with full transition matrix and sync gap inventory: `.claude/reports/backlog-state-machine-analysis-20260314.md`

</div>

### Priority

<div><sub>2026-03-14T21:56:13Z</sub>

8/10 — Every backlog read operation (`backlog list`, `backlog view`, `backlog list --from-github`, `backlog list --with-status`) returns stale or incorrect data. Closed items appear open. Groomed items lose their status label. 58 items are stuck in `status: open`, an undefined state that cannot transition within the documented lifecycle. The backlog is the primary planning surface for the project; unreliable state in every read operation erodes trust in the entire system.
</div>

### Impact

<div><sub>2026-03-14T21:56:23Z</sub>


- Blocks: `backlog list` cannot be used as a reliable source of active work — closed items pollute every listing.
- Blocks: `backlog list --with-status` returns blank status for any issue that GitHub considers closed, making status-based filtering meaningless.
- Blocks: `backlog groom` leaves items in a "stateless void" after every successful grooming — no `status:*` label, stale local `status` field — preventing downstream milestone assignment and work-tracking.
- Bottleneck: The 58 items with `status: open` cannot enter the documented lifecycle at all; `/work-backlog-item` and `/implement-feature` depend on valid state to route work correctly.
- Cascades into #426 (state machine implementation): the state machine DAG exists in `state_handler.py` but is bypassed in 4 of 8 transition points; reconciliation cannot be fully automated until those transitions use `apply_github_transition()`.
- Misleads planning: any count-based reporting on open/in-progress items is inflated by closed items that were never removed from the local cache.

</div>

### Benefits

<div><sub>2026-03-14T21:56:32Z</sub>


- `backlog list` output becomes accurate: only genuinely open items appear by default, closed items are detectable on request.
- Groomed items retain their `status:groomed` label after grooming — no more stateless void entries.
- The 58 items with `status: open` can be migrated to valid lifecycle states, unblocking milestone assignment and work routing.
- Divergence surfaces visibly in list/view output instead of silently returning stale data — operators know when local cache is out of sync.
- Work-in-progress items (plan files, active tasks) are protected from incorrect auto-closure when GitHub closes an issue that still has local active work.
- Enables accurate count-based planning metrics: items in-progress, groomed, or blocked reflect actual state.

</div>

### Expected Behavior

<div><sub>2026-03-14T21:56:43Z</sub>


When a backlog item's local frontmatter state differs from its GitHub issue state or `status:*` label, the system detects the divergence at read time and resolves it transparently or reports it explicitly:

- If GitHub shows an issue as `closed` and no local work-in-progress is detected (no active plan file, no in-progress task context, no uncommitted changes tied to the item), the local cache is updated to reflect the closed state and the item is excluded from default list output.
- If GitHub shows an issue as `closed` but local work-in-progress is detected, the divergence is surfaced as a warning in list/view output rather than silently auto-resolving.
- If a `status:*` label on GitHub differs from the local `status` field and the transition between them is valid per `VALID_TRANSITIONS`, the local cache is updated to match GitHub and the corrected state is shown.
- If the transition is invalid per `VALID_TRANSITIONS`, the divergence is flagged for human review and shown in list/view output.
- After grooming, an item carries a `status:groomed` label on GitHub and `status: groomed` in local frontmatter — no intermediate stateless state.
- `backlog list` shows only genuinely open items by default; an `--include-closed` flag makes closed items visible.
- `backlog list --with-status` returns accurate status for every item, including items that were closed since the last local cache refresh.

</div>

### Acceptance Criteria

<div><sub>2026-03-14T21:56:59Z</sub>


1. `backlog list` does not include items whose GitHub issues have `state=closed` unless `--include-closed` is passed.
2. `backlog list --from-github` fetches both open and closed issues; closed issues update their local cache files with closed state and are excluded from default output.
3. `backlog list --with-status` returns a non-blank status for every item that has a GitHub issue, including items closed since the last local refresh.
4. Running `backlog groom` on an item with `status:needs-grooming` and approving it results in: GitHub label transitions from `status:needs-grooming` to `status:groomed` (both removed and added atomically); local frontmatter `status` field updates to `groomed`. No intermediate stateless state exists.
5. If an item's local `status` differs from its GitHub `status:*` label and the transition is valid per `VALID_TRANSITIONS`, `backlog list --from-github` or `backlog view` auto-corrects the local file and reports the correction in output.
6. If an item's local `status` differs from GitHub and the transition is invalid per `VALID_TRANSITIONS`, the divergence is reported as a warning in `backlog list` and `backlog view` output — not silently discarded.
7. If a GitHub issue is `closed` but the item has a local plan file (`plan/tasks-*-{slug}*.md`) or active task context (`.claude/context/active-task-*.json`), auto-closure is blocked and a warning is emitted instead of silently updating local state.
8. `backlog list` output with no flags reflects zero closed items from the 58 items currently stuck in `status: open`, after migration to valid states.
9. Running `backlog list --with-status` on the repository produces no item with a blank `status` field that has a linked GitHub issue — every linked item shows its canonical `status:*` label value or explicitly shows `closed`.
10. The reconciliation behavior is exercised by a test that: creates a mock item with `status: open` locally and `state=closed` on a mock GitHub issue, runs a read operation, and asserts the local file is updated and the item excluded from default list output.

</div>

### Resources

<div><sub>2026-03-14T21:57:10Z</sub>


| Type | Item |
|------|------|
| Source file | `.claude/skills/backlog/scripts/backlog.py` — `_refresh_local_cache_from_github()`, `_batch_fetch_statuses()`, `_build_backlog_frontmatter()`, `backlog_groom()` |
| Source file | `.claude/skills/backlog/scripts/state_handler.py` — `VALID_TRANSITIONS` DAG, `apply_github_transition()` |
| Source file | `plugins/python3-development/skills/backlog/scripts/backlog_core.py` — MCP server |
| Reference | `.claude/skills/backlog/references/state-machine.md` — canonical state machine documentation |
| Analysis report | `.claude/reports/backlog-state-machine-analysis-20260314.md` — full transition matrix and 6 sync gap findings |
| Related item | #426 — Backlog state machine implementation (soft dependency; DAG already available in state_handler.py) |
| Related item | #282 — Backlog system redesign: GitHub Issues as source of truth |
| Related item | #300 — Original trigger case: issue closed on GitHub, appeared open in backlog_list |

</div>

### Dependencies

<div><sub>2026-03-14T21:57:18Z</sub>


- Depends on: #426 (soft) — `VALID_TRANSITIONS` DAG and `apply_github_transition()` already exist in `state_handler.py`; reconciliation can detect and flag divergence even before #426 completes all 8 transitions. Auto-resolution of divergences via DAG-valid transitions is fully available for the 4 transitions that already use `apply_github_transition()`.
- Blocks: #282 — GitHub-as-source-of-truth redesign depends on divergence being detectable and resolvable.
- Unblocks: `backlog list --with-status` accurate filtering, milestone assignment for the 58 `status: open` items, and any planning tool that reads item counts.

</div>

### Effort

<div><sub>2026-03-14T21:57:27Z</sub>

Medium — Three distinct changes of known scope:

1. Fix `_refresh_local_cache_from_github()` to fetch `state="all"` and mark closed items in local frontmatter (estimated: 50-70 lines including `--include-closed` flag and default filter).
2. Fix `backlog_groom()` to call `apply_github_transition()` atomically and update local `status` field (estimated: 20-30 lines; function already exists).
3. Add divergence-detection pass to `backlog list` and `backlog view` — compare local `status` field against GitHub `status:*` label, apply DAG-valid corrections, flag invalid ones (estimated: 80-120 lines).

Work-in-progress detection (plan file glob, active task context file check) adds complexity but each signal is a straightforward file existence check. The main risk is GitHub API rate limits when fetching closed issues for a large repo.
</div>