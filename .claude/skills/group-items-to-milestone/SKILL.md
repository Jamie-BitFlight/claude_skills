---
name: group-items-to-milestone
description: 'Use when assigning backlog items to a GitHub milestone. Args: {milestone-number} [P0|P1|P2|title-filter]. Uses backlog list to load items, shows items with GitHub Issue status, lets user select which to assign. Creates missing GitHub Issues for selected P0/P1 items, assigns all to the milestone, updates Project V2 Status to Backlog. Use after create-milestone to populate a sprint or release.'
argument-hint: '{milestone-number} [P0|P1|P2|title-filter]'
user-invocable: true
---

# Group Items to Milestone

Assign backlog items to a GitHub milestone. Bridges .claude/backlog/ per-item files → GitHub Issues → milestone assignment.

API references: [milestones.md](../gh/references/milestones.md) | [issue-stories.md](../gh/references/issue-stories.md) | [projects-v2.md](../gh/references/projects-v2.md)

## Arguments

- `{milestone-number}` — required
- Optional filter: `P0`, `P1`, `P2`, or title substring to pre-filter the list

```text
/group-items-to-milestone 3
/group-items-to-milestone 3 P1
/group-items-to-milestone 3 github
```

## Workflow

### Step 1: Resolve Milestone

Call `backlog_list_milestones(state="open")` and filter the returned list for the entry where `number == {number}`. If not found, call `backlog_list_milestones(state="all")` and filter again. Extract `title`, `state`, `open_issues`, `closed_issues` from the matching entry.

If milestone not found or closed, report and stop.

### Step 2: Load Backlog Items

Call the `mcp__plugin_dh_backlog__backlog_list` tool. Parse the returned dict — each entry in `items` has `title`, `priority`, `issue`, `plan`, `status`, `milestone`, `file_path`, `groomed`. Filter items by section (P0, P1, P2, Ideas). Apply any title filter.

For each item determine status:

- **Has issue** — `**Issue**: #N` field present → verify state via `backlog_list_issues(state="open")` — check if issue number appears in the returned list
- **No issue** — P0/P1 item without issue → flagged for creation offer
- **Already in milestone** — issue already assigned to this milestone → shown pre-checked

### Step 3: Present Selection

```text
Milestone #{N}: {title}

P0
  1. [✓] SAM: Error Recovery — Issue #12 (open)
  2. [ ] bash-development: Fix inaccuracies — no issue yet

P1
  3. [✓] gitlab-skill: Remove URL — Issue #8 (open)
  4. [ ] create-backlog-item skill — no issue yet
  5. [~] commitlint verify flag — Issue #5 (already in this milestone)

Legend: [✓] has issue  [ ] needs issue created  [~] already assigned
```

Use `AskUserQuestion`: "Which items to add? (comma-separated numbers, or 'all', or 'P0', 'P1')"

### Step 4: Create Missing Issues

For each selected item with no `**Issue**: #N`:

Build story-format body (Story / Description / Acceptance Criteria / Context). Create issue using the Python script (preferred — handles label creation automatically):

```bash
uv run .claude/skills/gh/scripts/github_project_setup.py issue create \
  --title "{type}: {title}" \
  --body "{story body}" \
  --priority-label "priority:{p0|p1|p2|idea}" \
  --type-label "type:{feature|bug|refactor|docs|chore}" \
  --milestone {number}
```

The backlog script automatically writes `issue: '#N'` back to the item's metadata.

Skip issue creation for P2/Ideas items — assign by milestone number only if they already have an issue.

### Step 5: Assign Existing Issues

For selected items that already have issues but are not yet in this milestone:

```bash
uv run .claude/skills/gh/scripts/github_project_setup.py issue set-milestone \
  --issue {issue_number} \
  --milestone {milestone_number}
```

### Step 6: Update Project V2 Status

Set Status = `Backlog` for each newly assigned item:

```bash
uv run .claude/skills/gh/scripts/github_project_setup.py project update-status \
  --issue {issue_number} \
  --status Backlog
```

### Step 7: Report

```text
Milestone #{N}: {title}

Assigned {count} items:
  Issue #12: SAM: Error Recovery (existing issue)
  Issue #14: create-backlog-item skill (new issue created)
  Issue #5:  commitlint verify flag (already assigned — skipped)

Per-item files updated with {created_count} new issue numbers.

Next step: /dh:groom-milestone {number}
```

## Error Handling

- Milestone not found: call `backlog_list_milestones(state="open")` and list available milestones, then stop.
- Issue creation fails: log error per item, continue with remaining.
- No items match filter: report and show available sections.
- Label not found: `github_project_setup.py issue create` handles label creation automatically via `_ensure_label()`.
