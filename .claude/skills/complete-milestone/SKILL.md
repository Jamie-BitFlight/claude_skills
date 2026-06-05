---
name: complete-milestone
description: 'Close a completed GitHub milestone and generate a completion summary. Use when a sprint or release is finished and needs to be officially closed. Audits open and closed issues, offers to carry forward open items to a new or existing milestone, closes the milestone, updates Project V2 Status to Done for closed issues, and produces a completion report.'
argument-hint: '{milestone-number}'
user-invocable: true
---

<milestone_number>$ARGUMENTS</milestone_number>

# Complete Milestone

Verify completion state, handle stragglers, close the milestone, and generate a summary.

## Arguments

`<milestone_number/>` — milestone number (required).

```text
/complete-milestone 3
```

## Workflow

### Step 1: Resolve and Audit

Call `backlog_list_milestones(state="open")` and filter the returned list for the entry where `number == <milestone_number/>`. If not found in open milestones, call `backlog_list_milestones(state="all")` and filter again. Extract: `title`, `state`, `open_issues`, `closed_issues`, `due_on`.

If milestone already closed, report closed date and stop.

Fetch all issues:

```text
backlog_list_issues(milestone="{title}", state="open")
backlog_list_issues(milestone="{title}", state="closed")
```

### Step 2: Show State

```text
Milestone #{N}: {title}
Due: {due_on or "not set"}

  Closed: {closed_count} issues ✓
  Open:   {open_count} issues ✗

Closed:
  #12  SAM: Error Recovery      (closed 2026-02-20)
  #8   gitlab-skill: Remove URL (closed 2026-02-19)

Open (incomplete):
  #14  create-backlog-item skill  [status:in-progress]
  #17  start-milestone skill      [status:needs-grooming]
```

If `open_count == 0`: skip to Step 4.

### Step 3: Handle Open Issues

Ask: "What should happen to the {open_count} open issues?"

```text
A) Carry forward to a new milestone (create it now)
B) Carry forward to an existing open milestone
C) Remove from milestone (leave open, unassigned)
D) Close them as incomplete
```

**Option A — new milestone:**

Prompt for new milestone title and optional due date. Create via:

```text
backlog_create_milestone(title="{new title}", due_on="{YYYY-MM-DD or empty}", description="")
```

Reassign open issues one at a time:

```bash
uv run .claude/skills/gh/scripts/github_project_setup.py issue set-milestone --issue N --milestone {new_number}
```

**Option B — existing milestone:**

Call `backlog_list_milestones(state="open")` to list open milestones. User picks one; reassign open issues:

```bash
uv run .claude/skills/gh/scripts/github_project_setup.py issue set-milestone --issue N --milestone {chosen_number}
```

**Option C — unassign:**

```bash
uv run .claude/skills/gh/scripts/github_project_setup.py issue remove-milestone --issue N
```

**Option D — close:**

```bash
uv run .claude/skills/gh/scripts/github_project_setup.py issue close --number N --comment "Closed incomplete as part of milestone #{M} completion."
```

### Step 4: Close Milestone

Use the Python automation script (preferred — handles label transitions and milestone close atomically):

```bash
uv run .claude/skills/gh/scripts/github_project_setup.py milestone close \
  --number {number}
```

Or, to preview changes without applying them:

```bash
uv run .claude/skills/gh/scripts/github_project_setup.py milestone close \
  --number {number} --dry-run
```

The script transitions all remaining open issues to `status:done`, closes the milestone, and prints a completion summary. It exits non-zero if any issue label update fails.

### Step 5: Update Project V2

For all closed issues, update Project V2 Status to `Done`:

```bash
uv run .claude/skills/gh/scripts/github_project_setup.py project update-status \
  --issue N --status Done
```

### Step 6: Completion Report

```text
Milestone #{N} "{title}" — CLOSED

  Completed:       {closed_count}/{total_count} ({pct}%)
  Carried forward: {count} → milestone #{new_N} "{new_title}"
  Removed:         {count}
  Closed incomplete: {count}

{if carry_forward_count > 0}
Next steps:
  /group-items-to-milestone {new_N}  (add more items)
  /start-milestone {new_N}           (begin the new sprint)
```

## Error Handling

- Milestone not found: call `backlog_list_milestones(state="open")` to list open milestones and stop.
- Milestone already closed: report and stop.
- Issue reassignment fails: log per-item error, continue with remaining.
- No open milestones for Option B: fall back to Option A automatically.
