---
name: start-milestone
description: "Transitions a GitHub milestone from planning to active execution. Use when the team is ready to begin a sprint or release cycle — bulk-transitions open issue labels from status:needs-grooming to status:in-progress, updates GitHub Projects V2 Status to In Progress, and confirms before applying changes. Requires milestone number as argument. Use after /group-items-to-milestone."
argument-hint: '{milestone-number}'
user-invocable: true
---

<milestone_number>$ARGUMENTS</milestone_number>

# Start Milestone

Transition a milestone from planning to active: bulk-update labels and Project board status.

API references: [milestones.md](../gh/references/milestones.md) | [projects-v2.md](../gh/references/projects-v2.md)

## Arguments

`<milestone_number/>` — milestone number (required).

```text
/start-milestone 3
```

## Workflow

### Step 1: Resolve Milestone

Call `mcp__plugin_dh_backlog__backlog_list_milestones(state="open")`.

From the returned list, find the entry where `number == <milestone_number/>`.

If not found in the open list, call `mcp__plugin_dh_backlog__backlog_list_milestones(state="all")` and filter again.

If milestone is closed, report and stop.

If `open_issues == 0`, warn: "No open issues. Add items first with `/group-items-to-milestone {number}`"

### Step 2: List Issues

Call `mcp__plugin_dh_backlog__backlog_list_issues(milestone="{title}", state="open")`.

The response contains a list of issues with `number`, `title`, `state`, and `labels` fields.

### Step 3: Confirm

```text
Start milestone "{title}" — {N} open issues

Issues to transition (status:needs-grooming → status:in-progress):
  #12  SAM: Error Recovery        [priority:p1, status:needs-grooming]
  #8   gitlab-skill: Remove URL   [priority:p1, status:needs-grooming]
  #14  create-backlog-item skill  [priority:p2, status:needs-grooming]

Proceed?
```

Use `AskUserQuestion` with Yes / No options. Stop without changes if No.

### Step 4: Bulk Label Transition

Use the Python automation script (preferred — avoids per-issue bash loops):

```bash
uv run .claude/skills/gh/scripts/github_project_setup.py milestone start \
  --number {number}
```

Or, to preview changes without applying them:

```bash
uv run .claude/skills/gh/scripts/github_project_setup.py milestone start \
  --number {number} --dry-run
```

The script removes `status:needs-grooming` and adds `status:in-progress` to each
open issue, creates the label if missing, reports per-issue results, and exits
non-zero if any issue fails.

### Step 5: Update Project V2

Run:

```bash
uv run .claude/skills/gh/scripts/github_project_setup.py project update-status \
  --milestone {number} --status "In Progress"
```

See [projects-v2.md](../gh/references/projects-v2.md) for details.

### Step 6: Report

```text
Milestone #{N} "{title}" started.

  {count} issues transitioned to status:in-progress
  {failed_count} issues failed (see details above)

Work on individual items:
  /work-backlog-item {title}
```

## Error Handling

- Milestone not found: list open milestones and stop.
- Milestone already closed: report closed date and stop.
- Label edit fails for specific issue: log and continue; report failures at end.
- User declines confirmation: stop without changes.
