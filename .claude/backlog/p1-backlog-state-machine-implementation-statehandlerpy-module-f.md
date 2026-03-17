---
name: Backlog state machine implementation — state_handler.py module for lifecycle transitions and backend sync
description: "The backlog state machine (documented in .claude/skills/backlog/references/state-machine.md) defines 8 lifecycle states: needs-grooming, groomed, blocked, in-milestone, in-progress, done, resolved, closed. The implementation in backlog.py does not enforce this state machine. Observed gaps:\n\n1. `backlog groom` / `backlog update --groomed` only removes `status:needs-grooming` GitHub label — never adds `status:groomed`. Local frontmatter `status` field is never updated. Items land in a stateless void after grooming.\n\n2. `open` is used as a status value in ~30+ backlog items but does not exist in the state machine. It predates the state machine definition and has no defined transitions.\n\n3. `status:groomed`, `status:in-milestone`, `status:done`, `status:closed` labels are defined in state-machine.md but missing from labels.md (the label taxonomy). Only 4 of 8 labels exist: needs-grooming, in-progress, blocked, needs-review. `needs-review` is in labels.md but NOT in the state machine.\n\n4. No code path updates local frontmatter `status` during any transition — GitHub labels and local status are disconnected.\n\n5. Missing transition: `blocked → in-progress` — when a work-blocked item gets unblocked, no path exists back to in-progress without cycling through needs-grooming.\n\nWhat success looks like: A `state_handler.py` module/class that (a) validates transitions against the state machine DAG, (b) rejects invalid transitions with a clear error, (c) updates both the GitHub issue label AND the local frontmatter `status` field atomically, (d) is called by all backlog commands (groom, update, close, resolve, work) instead of each command managing labels ad-hoc. The pluggable backend pattern allows the same state machine to drive GitHub labels, local file status, or future backends (Jira, Linear, etc.).\n\nHow you'll know it's working: After grooming an item, `status: groomed` appears in local frontmatter AND `status:groomed` label is on the GitHub issue. After `/group-items-to-milestone`, status is `in-milestone` in both places. No item can have `status: open` — that value is migrated to the correct state machine state. All 8 GitHub labels from state-machine.md exist in the repo."
metadata:
  topic: backlog-state-machine-implementation-statehandlerpy-module-f
  source: 'Session observation — state machine gap analysis during PR #418 rebase (2026-03-03)'
  added: '2026-03-03'
  priority: completed
  type: Feature
  status: done
  issue: '#426'
  last_synced: '2026-03-03T13:54:52Z'
  groomed: '2026-03-03'
---

## Fact-Check

**Claims Checked**: 7
**VERIFIED**: 5 | **REFUTED**: 1 | **INCONCLUSIVE**: 1

| Claim | Verdict | Evidence |
|-------|---------|---------|
| `backlog groom`/`update --groomed` only removes `status:needs-grooming` — never adds `status:groomed` | VERIFIED | backlog.py:1746-1747 — `issue.remove_from_labels("status:needs-grooming")` with no `add_to_labels("status:groomed")` |
| Local frontmatter `status` never updated by groom/update --groomed | VERIFIED | `_write_groomed_to_item_file` (line 1576) sets `groomed` date but never touches `status` field |
| `open` used in ~30+ backlog items but not in state machine | VERIFIED (count higher) | 58 backlog files have `status: open`. Origin: backlog.py:635 defaults to `open` when no `status:*` label exists on GitHub issue. State machine (state-machine.md:47-54) lists 8 states; `open` is not among them |
| `status:groomed`, `status:in-milestone`, `status:done`, `status:closed` missing from labels.md | VERIFIED | labels.md:40-43 defines only: `needs-grooming`, `in-progress`, `blocked`, `needs-review`. Four state-machine labels absent |
| `needs-review` is in labels.md but not in the state machine | VERIFIED | labels.md:43 defines `status:needs-review`. state-machine.md:47-54 lists 8 states — `needs-review` absent |
| No code path updates local frontmatter `status` during ANY transition | REFUTED | `close` sets `status: closed` (backlog.py:1208), `resolve` sets `status: done` (backlog.py:1306). Gap is specific to grooming (`needs-grooming → groomed`) and milestone (`groomed → in-milestone`) transitions — not all transitions |
| Missing `blocked → in-progress` transition | INCONCLUSIVE | state-machine.md shows `blocked → needs-grooming` and `blocked → resolved` only. Whether `blocked → in-progress` should exist is a design question — the current state machine intentionally requires re-grooming via `needs-grooming` before returning to work. May be correct by design |

**Citations**:
- backlog.py lines 635, 1208, 1306, 1576, 1746-1747 (direct file reads this session)
- .claude/skills/backlog/references/state-machine.md lines 47-54 (state definitions)
- .claude/skills/gh/references/labels.md lines 40-43 (label taxonomy)
- .claude/backlog/*.md — 58 files with `status: open` (grep count this session)

## RT-ICA

**Goal**: Implement a state_handler.py module that enforces the documented 8-state lifecycle, validates transitions against the DAG, and atomically updates both GitHub labels and local frontmatter status.

**Conditions**:
1. State machine document exists and defines all states/transitions | **AVAILABLE** | state-machine.md lines 13-38 (Mermaid DAG), lines 45-54 (state table), lines 58-156 (transition specs)
2. Current label management code identified for refactoring | **AVAILABLE** | backlog.py:1746 (groom label removal), :1755 (in-progress label set), :1208 (close status), :1306 (resolve status)
3. Gap between state-machine.md and labels.md quantified | **AVAILABLE** | Fact-check confirmed: 4 labels missing from labels.md; `needs-review` orphaned; `open` default at line 635 not in state machine
4. Local frontmatter update mechanism exists | **AVAILABLE** | `_update_item_metadata()` already used by close (line 1208) and resolve (line 1306) — same function can set status for other transitions
5. Count of items requiring migration from `open` to valid state | **AVAILABLE** | 58 files with `status: open` — each needs mapping to correct state based on `groomed` field presence and issue label state
6. `blocked → in-progress` transition design decision | **DERIVABLE** | Fact-check rated INCONCLUSIVE — current design may intentionally require re-grooming. Needs explicit decision: add direct path or document the intentional re-grooming requirement
7. Pluggable backend interface requirements | **DERIVABLE** | Current code uses PyGithub directly; abstraction boundary can be inferred from existing `_get_github()`, `_try_get_github()` patterns

**Decision**: APPROVED
**Missing**: None blocking. Condition 6 (blocked → in-progress) is a design choice to make during planning, not a blocker for grooming.

## Groomed (2026-03-03)

## Files

- `.claude/skills/backlog/references/state-machine.md` — canonical state machine DAG (8 states, transitions, preconditions)
- `.claude/skills/backlog/scripts/backlog.py` — implementation with ad-hoc label management (lines 635, 1208, 1306, 1576, 1746-1747, 1755)
- `.claude/skills/gh/references/labels.md` — label taxonomy (4 of 8 labels present; 4 missing, 1 orphaned)
- `.claude/backlog/*.md` — 58 items with `status: open` requiring migration

---

### Reproducibility

1. Run `/groom-backlog-item` on any `needs-grooming` item with a GitHub issue.
2. After grooming completes, inspect the local frontmatter: `status` field remains `needs-grooming` or whatever it was — never transitions to `groomed`.
3. Check the GitHub issue labels: `status:needs-grooming` was removed, but no `status:groomed` label was added. The issue has no status label.
4. Run `backlog list --with-status` — groomed items show no consistent state.
5. Count items with `status: open`: `grep -c "status: open" .claude/backlog/*.md` → 58 items in a state not defined by the state machine.

---

### Output / Evidence

- **Stateless void after grooming**: backlog.py:1746-1747 removes `status:needs-grooming` but adds nothing. `_write_groomed_to_item_file` (line 1576) sets `groomed` date but never touches `status`.
- **`open` as default**: backlog.py:635 assigns `status = "open"` when no `status:*` label exists on a GitHub issue. 58 backlog files have this value.
- **Label taxonomy gap**: labels.md defines 4 labels (`needs-grooming`, `in-progress`, `blocked`, `needs-review`). State machine defines 8 states. Missing from labels.md: `groomed`, `in-milestone`, `done`, `closed`. Orphaned in labels.md: `needs-review` (not in state machine).
- **Partial local updates**: `close` (line 1208) and `resolve` (line 1306) DO update local frontmatter status via `_update_item_metadata()`. Groom and milestone transitions do not use this pattern.
- **`blocked → in-progress`**: state-machine.md shows `blocked → needs-grooming` and `blocked → resolved` only. Whether a direct `blocked → in-progress` path should exist is a design decision (current design requires re-grooming).

---

### Priority

**9/10** — Blocks state consistency across the entire backlog system. Items enter undefined states after grooming; GitHub labels and local frontmatter desynchronize. Affects every backlog operation (groom, update, close, resolve, milestone grouping). The state machine DAG documented in state-machine.md remains aspirational, not enforced.

---

### Impact

- **Breaks**: Accurate filtering and reporting by lifecycle state — 58 items in invalid `open` state
- **Defeats**: The state machine document's purpose — it defines transitions that no code enforces
- **Affects**: Every backlog command that changes item state (groom, update, close, resolve, group-to-milestone)
- **Cascades to**: work-backlog-item RT-ICA gate (relies on state to determine readiness), milestone grouping automation, backlog analytics
- **Related**: `needs-review` label exists in labels.md but has no state machine definition — either add to state machine or remove from labels

---

### Benefits

- Enforces documented 8-state lifecycle across all transitions
- Eliminates stateless void after grooming (atomically sets local status AND GitHub label)
- Enables accurate filtering/reporting by state
- Unifies label/frontmatter updates: one code path, less maintenance
- Creates pluggable backend interface for future systems (Jira, Linear)
- Enables migration of 58 `open` items to correct states

---

### Expected Behavior

When a backlog command transitions an item (groom, update, close, resolve, group-to-milestone): the state handler validates the transition against the DAG, rejects invalid transitions with a clear error, and atomically updates both GitHub issue label AND local frontmatter status field. Callers never manage labels ad-hoc.

After grooming: `metadata.status: groomed` in frontmatter AND `status:groomed` label on GitHub issue.
After grouping to milestone: `metadata.status: in-milestone` in frontmatter AND `status:in-milestone` label on issue.
No item has `status: open` — that value is migrated to the correct state based on grooming status and issue labels.

---

### Acceptance Criteria

1. After grooming an item, local frontmatter shows `status: groomed` AND GitHub issue has `status:groomed` label.
2. Running `backlog list` on a groomed item shows state as `groomed`, not blank or `open`.
3. Invalid transitions (e.g., `closed → in-progress`) are rejected with an error naming the invalid path.
4. All 8 state machine labels exist in the GitHub repo (4 missing labels created: `groomed`, `in-milestone`, `done`, `closed`).
5. Zero items remain with `status: open` after migration — all 58 mapped to valid states.
6. No backlog command sets a label without going through the state handler (no ad-hoc label mutations).
7. `needs-review` label reconciled: either added to state machine with transitions or removed from labels.md.
8. State handler module is unit-testable in isolation (validation logic separated from GitHub API calls).

---

### Resources

| Type | Item |
|------|------|
| Reference | `.claude/skills/backlog/references/state-machine.md` — canonical state machine |
| Reference | `.claude/skills/gh/references/labels.md` — label taxonomy |
| Script | `.claude/skills/backlog/scripts/backlog.py` — current implementation |
| Prior work | `_update_item_metadata()` — existing function for local frontmatter updates |
| Prior work | `_apply_status_in_progress()` — existing ad-hoc label setter |

---

### Dependencies

- **Depends on**: None — all prerequisites available (RT-ICA APPROVED)
- **Unblocks**: work-backlog-item RT-ICA gate improvements, milestone grouping automation, backlog analytics/reporting by state, any workflow relying on item state consistency

---

### Effort

**Medium** — State handler module is ~300-500 lines (DAG class + validation + backend abstraction + migration utility). Integration with existing commands (groom, update, close, resolve) is ~20-30 line changes per command. Design decision on `blocked → in-progress` is a choice, not a blocker. No external dependencies.