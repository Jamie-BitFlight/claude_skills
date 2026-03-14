---
name: Fix missing _status key in backlog_item_to_display_dict adapter
description: 'The backlog_item_to_display_dict adapter in backlog.py omits the _status key, but _dict_to_backlog_item_fields reads d.get("_status"). This creates a latent data loss risk in round-trip conversions. Fix: add "_status": item.status to the output dict.'
metadata:
  topic: fix-missing-status-key-in-backlogitemtodisplaydict-adapter
  source: 'Code review followup from #611'
  added: '2026-03-12'
  priority: P2
  type: Bug
  status: needs-grooming
  issue: '#670'
  last_synced: '2026-03-14T15:59:42Z'
  plan: plan/tasks-36-backlog-cli-dedup-followup-2.md
  groomed: '2026-03-14'
---

## Story

As a **developer relying on this plugin**, I want to **fix missing _status key in backlog_item_to_display_dict adapter** so that **the tool works correctly and reliably**.

## Description

The backlog_item_to_display_dict adapter in backlog.py omits the _status key, but _dict_to_backlog_item_fields reads d.get("_status"). This creates a latent data loss risk in round-trip conversions. Fix: add "_status": item.status to the output dict.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Code review followup from #611
- **Priority**: P2
- **Added**: 2026-03-12
- **Research questions**: None

## Groomed (2026-03-14)

### Groomed

<div><sub>2026-03-14T03:21:12Z</sub>


### RT-ICA

- Decision: APPROVED
- All conditions AVAILABLE or DERIVABLE from codebase inspection.
- Fact-check: 2/2 claims VERIFIED against source.

### Reproducibility

1. Construct a `BacklogItem` with a non-empty `status` value (e.g., `status="in-progress"`).
2. Call `backlog_item_to_display_dict(item)` — observe the returned dict has no `_status` key.
3. Pass the dict to `_dict_to_backlog_item_fields(d)` — observe `status` silently defaults to `""` via `d.get("_status", "")`.
4. Call `BacklogItem.model_validate(_dict_to_backlog_item_fields(d))` — the reconstructed item has `status=""` regardless of the original value.

### Output / Evidence

- Grep `.claude/skills/backlog/scripts/backlog.py` function `backlog_item_to_display_dict`: `_status` is absent from return dict.
- Grep `.claude/skills/backlog/scripts/backlog.py` function `_dict_to_backlog_item_fields`: reads `d.get("_status", "")` — receives `None` on every round-trip.
- All call sites of `_dict_to_backlog_item_fields` in `backlog.py` silently lose `status` on items that passed through `backlog_item_to_display_dict`.
- No existing tests cover either adapter function (grep of test directory returned zero matches).

### Priority

7/10 — Latent data loss. Not currently user-visible because `status` is not yet widely written or read in round-trip paths, but any function that calls `_dict_to_backlog_item_fields` on items from `parse_backlog` silently resets status to `""`. Risk increases as the status field is used more broadly (see #612).

### Impact

- Blocks: Any call site that round-trips a `BacklogItem` through `backlog_item_to_display_dict` then `_dict_to_backlog_item_fields` loses the `status` field silently.
- Affected call sites: all functions in `backlog.py` that call `BacklogItem.model_validate(_dict_to_backlog_item_fields(d))`.
- Bottleneck: The asymmetry between the two adapter functions is the single point of failure.

### Benefits

- Eliminates silent data loss in all adapter round-trips.
- Establishes a parity test contract that will catch future adapter drift.
- Unblocks reliable use of `BacklogItem.status` in downstream logic (related: #612).

### Expected Behavior

After the fix, a `BacklogItem` with any `status` value survives a full round-trip through `backlog_item_to_display_dict` → `_dict_to_backlog_item_fields` with its `status` preserved exactly.

### Desired Structure

- `backlog_item_to_display_dict` includes `"_status": item.status` in its return dict.
- `BacklogItem.status` type: `str = ""` (no enum, no validation needed — plain string passthrough).
- A round-trip unit test in the test suite covers all fields output by `backlog_item_to_display_dict` and verifies they survive the inverse transformation without loss.

### Acceptance Criteria

1. `backlog_item_to_display_dict(item)["_status"]` equals `item.status` for any `BacklogItem`.
2. `_dict_to_backlog_item_fields(backlog_item_to_display_dict(item))["status"]` equals `item.status` for all status string values (including empty string and any label value).
3. A new test in `.claude/skills/backlog/tests/` covers the full round-trip for all fields including `_status` / `status`.
4. No existing tests are broken by the change.
5. `uv run prek run --files .claude/skills/backlog/scripts/backlog.py` passes with no new linting errors.

### Resources

| Type | Item |
|------|------|
| Prior work | `.claude/skills/backlog/scripts/backlog.py` — functions `backlog_item_to_display_dict`, `_dict_to_backlog_item_fields` |
| Prior work | `.claude/skills/backlog/backlog_core/models.py` — `BacklogItem.status: str = ""` |
| Prior work | `.claude/skills/backlog/tests/` — existing test files (no current adapter coverage) |

### Dependencies

- Depends on: None — fix is self-contained.
- Plan file: `plan/tasks-36-backlog-cli-dedup-followup-2.md`
- Related: #612 (backlog: add status field to BacklogItem model) — not a blocker, but this fix surfaces more value as #612 work lands.
- Blocks: None directly; enables reliable status field usage across all round-trip call sites.

### Effort

Small — single-line addition to `backlog_item_to_display_dict` plus one round-trip unit test covering all adapter fields. Scope is confined to one function and one new test file/case.

### Root-Cause Analysis

<div><sub>2026-03-12T00:00:00Z</sub>

5-Whys (defect classification):

1. `backlog_item_to_display_dict` omits `_status` because the status field was not present when the adapter was written.
2. The two adapter functions evolved asymmetrically — each modified independently without cross-checking the other.
3. No round-trip test existed to catch field parity violations between the two functions.
4. Adapter functions were added as internal helpers without test contracts.
5. Root cause: internal adapters evolved without enforced parity — fix requires BOTH the missing field AND a round-trip test to prevent recurrence.

</div>
</div>

<div><sub>2026-03-14T03:22:10Z</sub>

5-Whys:
1. Why missing? — status field was not added when the adapter was first written
2. Why not added? — backlog_item_to_display_dict and _dict_to_backlog_item_fields evolved asymmetrically as internal helpers
3. Why undetected? — no round-trip test enforces field parity between the two functions
4. Why no test? — adapter functions added as a quick bridge layer ("LOCAL adapter helper") without acceptance test gates
5. Root cause: adapter functions evolved without parity contracts

Fix requires: (a) add `"_status": item.status` to backlog_item_to_display_dict return dict AND (b) add a round-trip test asserting field identity.
</div>

### Issue Classification

<div><sub>2026-03-14T03:21:58Z</sub>

Type: defect
Analysis method: 5-whys

The defect is a specific omission in an adapter function causing silent data loss on every round-trip through the two adapter functions.
</div>



## Fact-Check

<div><sub>2026-03-14T03:21:42Z</sub>

Claims checked: 2
VERIFIED: 2 | REFUTED: 0 | INCONCLUSIVE: 0

- [VERIFIED] `_dict_to_backlog_item_fields` reads `d.get("_status", "")` — File: `.claude/skills/backlog/scripts/backlog.py` function `_dict_to_backlog_item_fields`
- [VERIFIED] `backlog_item_to_display_dict` does NOT include `"_status"` in its output dict — File: `.claude/skills/backlog/scripts/backlog.py` function `backlog_item_to_display_dict` (confirmed by groomer agent verification)
- [VERIFIED] `BacklogItem.status` is `str = ""` (plain string, no enum) — File: `.claude/skills/backlog/backlog_core/models.py` field `BacklogItem.status`
</div>

## RT-ICA

<div><sub>2026-03-12T00:00:00Z</sub>

- Decision: APPROVED
- All conditions AVAILABLE or DERIVABLE from codebase inspection.
- Fact-check: 2/2 claims VERIFIED against source.
</div>

<div><sub>2026-03-14T03:21:52Z</sub>

Goal: Eliminate latent data loss during round-trip dict conversions by ensuring _status is present in backlog_item_to_display_dict output.

Conditions:
1. backlog_item_to_display_dict omits _status | Status: AVAILABLE | Evidence: grep + groomer verification of function body
2. _dict_to_backlog_item_fields reads d.get("_status") | Status: AVAILABLE | Evidence: function body confirmed
3. Fix location is backlog_item_to_display_dict in backlog.py | Status: AVAILABLE | Evidence: function identified
4. item.status exists on BacklogItem model | Status: AVAILABLE | Evidence: BacklogItem.status field, str type
5. No tests currently cover this round-trip | Status: AVAILABLE | Evidence: groomer confirmed zero tests for either adapter

Decision: APPROVED
Missing: None
</div>