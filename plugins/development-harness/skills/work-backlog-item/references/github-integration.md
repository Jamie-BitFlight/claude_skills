# GitHub Integration — Detailed Steps and Examples

> **Repository**: OWNER/REPO is discovered via `discover_repo()` from `backlog_core.models`. Use MCP tools for all GitHub operations — no `gh` CLI required.

## Step 2.2: GitHub Issue Sync

<github_sync>

After extracting item fields (Step 2), check for an existing linked issue:

1. Search the matched item for `**Issue**: #N` field.
2. If found: issue already linked. Run:

   ```text
   MCP: backlog_view(selector="#N")
   ```

   Report the issue state. If open, proceed. If closed, warn the user before re-opening planning.

3. If not found AND priority is P0 or P1: offer to create a GitHub Issue:

   ```text
   This P1 item has no linked GitHub issue. Create one? (yes/no)
   ```

   If yes, proceed to 2.3.
   If no, skip GitHub sync; the per-item file remains the only local record.

4. If not found AND priority is P2 or Ideas: do not prompt; skip GitHub sync silently.

</github_sync>

## Step 2.3: Create GitHub Issue

Call the `mcp__plugin_dh_backlog__backlog_update` tool with `selector="{title}"`.

The tool creates the issue automatically when the item lacks one and writes `issue: '#N'` back to the per-item file frontmatter. Check the returned dict for an `error` key.

## Step 2.4: Set In-Progress Label

Call the `mcp__plugin_dh_backlog__backlog_update` tool with `selector="{title}"` and `status="in-progress"`. Check the returned dict for an `error` key.

If the item is in a milestone with other issues, also run `milestone start` to bulk-transition all open milestone issues to in-progress:

```text
MCP: backlog_update(selector="{title}", status="in-progress")
```

> **Note**: Bulk milestone start (transitioning all issues in a milestone) is not yet available as a single MCP tool call. Use `backlog_list_issues(milestone="{milestone_title}")` to enumerate milestone issues, then `backlog_update` each one individually.

## Step 9: Close — backlog tool

Call the `mcp__plugin_dh_backlog__backlog_close` tool with `selector="{title}"`, `plan="{plan path}"`, and `checklist_pass=true`.

The tool updates the per-item file status and closes the GitHub issue. Check the returned dict for an `error` key.

## setup-github Command

**Trigger:** `$ARGUMENTS` is exactly `setup-github`.

<setup_github>

1. Run label taxonomy setup:

   ```text
   MCP: backlog_sync()
   # backlog_sync creates missing labels as part of its sync operation.
   # To verify labels exist: MCP: backlog_list_labels()
   ```

2. Check for existing milestones:

   ```text
   MCP: backlog_list_milestones()
   ```

   If none exist, create the first milestone:

   ```text
   MCP: backlog_create_milestone(
     title="v1.0 — Skills Foundation",
     description="Initial stable milestone for {REPO} skills and plugins",
     due_on="2026-03-31T00:00:00Z"
   )
   ```

3. Check for existing projects:

   ```text
   MCP: backlog_list_projects()
   ```

   If none exist, prompt: "Create GitHub Project '{REPO} Backlog'? (yes/no)"
   If yes:

   ```text
   # OWNER/REPO is discovered dynamically via discover_repo() from backlog_core.models
   MCP: backlog_create_project(title="{REPO} Backlog")
   ```

4. Report setup summary:

   ```text
   GitHub setup complete:
   - Labels: N created
   - Milestone: #1 "v1.0 — Skills Foundation"
   - Project: #1 "{REPO} Backlog" (linked to repo)

   Next steps:
   - Add custom fields to the GitHub Project (manual step — not yet available via MCP tools)
   - Import existing backlog: /work-backlog-item <title> for each P0/P1 item
   ```

</setup_github>

---

## Commit Messages and PR Body — `Fixes #N` Restriction

`Fixes #N`, `Closes #N`, and `Resolves #N` commit trailers trigger automatic GitHub issue closure on merge. **These trailers are restricted to the `/complete-implementation` final commit step only.**

- **Task-level commits** (produced by `/start-task` during implementation) must NEVER include `Fixes #N`, `Closes #N`, or `Resolves #N`. Including them causes premature issue closure before quality gates in `/complete-implementation` have run.
- **The `/complete-implementation` final commit step** is the only place these trailers appear. After all quality gates pass, the final commit includes `Fixes #N` to close the issue on merge.
- **PR description**: do NOT add `Fixes #N` manually to the PR body during implementation. The `/complete-implementation` final commit carries the trailer — GitHub links the commit to the issue automatically.

This restriction ensures issues close only after the full pipeline (code review, feature verification, integration check, doc drift audit) has completed successfully.

---

## Example Sessions

### GitHub Issue Creation Flow

```text
> /work-backlog-item clang-format YAML frontmatter

Found: "clang-format: Fix broken YAML frontmatter" (P1)
No grooming manifest. Running groom-backlog-item first...

RT-ICA: APPROVED
This P1 item has no linked GitHub issue. Create one? yes

Creating issue...
  Title: fix: correct YAML frontmatter in clang-format SKILL.md
  Labels: priority:p1, type:bug, status:needs-grooming

Created: #59 — https://github.com/OWNER/REPO/issues/59
Updated per-item file: issue: '#59'

Setting status:in-progress...
  ✓ Added status:in-progress, removed status:needs-grooming

Composing feature request...
Invoking /add-new-feature...

[SAM phases run]

Updated per-item file with Plan: plan/tasks-3-clang-format-yaml.md
GitHub issue #59 — Plan added to issue body.

Next steps:
- To execute:      /implement-feature clang-format-yaml
- To close when done: /work-backlog-item close clang-format
```

### GitHub Setup Session

```text
> /work-backlog-item setup-github

Setting up GitHub project infrastructure...

1. Creating label taxonomy...
   created: priority:p0, priority:p1, priority:p2, priority:idea
   created: type:feature, type:bug, type:refactor, type:docs, type:chore
   created: status:in-progress, status:blocked, status:needs-grooming, status:needs-review
   Labels: 13 created, 0 skipped

2. Creating milestone: v1.0 — Skills Foundation
   Created milestone #1

3. Create GitHub Project '{REPO} Backlog'? yes
   Created project #1, linked to repo

GitHub setup complete.
```

---

## Field Mapping Reference

```text
~/.dh/projects/{slug}/backlog/    →  GitHub Issue
  metadata.priority →  priority:* label
  Description       →  Issue body (story format)
  metadata.status   →  status:* label
  metadata.plan     →  Issue body Notes
  metadata.issue    ←  written back after creation
  metadata.status   →  Issue closed
```

The issue body template is built into the `backlog_update` MCP tool — it generates the story format automatically from the per-item file fields.
