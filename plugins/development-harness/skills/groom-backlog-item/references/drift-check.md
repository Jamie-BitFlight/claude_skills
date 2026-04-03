# Drift Check Reference

Detailed procedures and output format templates for Step 2.5 drift checks.

## Mode A: Plan Drift (item has a plan file)

**Precondition**: `plan` field is set and points to an existing file.

**Purpose**: Detect what changed in the codebase since the plan was written, so tasks reflect current reality before execution.

Spawn a haiku-model agent (`subagent_type="general-purpose"`, model=haiku) with this task:

1. Read the plan file at the `plan` path
2. Extract all file paths mentioned in the plan (task descriptions, files-to-modify sections, context manifest)
3. Get the plan file's last commit date: `git log -1 --format=%aI -- {plan_path}`
4. For each referenced file, find commits since that date: `git log --oneline --since={date} -- {file_path}`
5. For each commit found, get the diff summary: `git show --stat {sha} -- {file_path}` and `git log -1 --format=%s {sha}` for the commit message
6. Analyze whether each commit changes what the plan expected to find in that file. Categories:
   - **Scope change** — file now does more or less than the plan assumed
   - **Partial fix** — the issue the plan addresses was partially resolved by another commit
   - **New callers** — other files now depend on this file that the plan did not account for
   - **File moved/renamed** — file is at a different path
   - **No impact** — commit is unrelated to the plan's goals for this file
7. Write findings to the backlog item via `mcp__plugin_dh_backlog__backlog_groom(selector="{title}", section="Plan Drift", content="...")`

**Plan Drift output format when drift is detected:**

```markdown
## Plan Drift

**Plan**: {plan_path}
**Plan last modified**: {date}
**Files checked**: {count}
**Files with drift**: {count}

### {file_path}

**Commits since plan** ({count}):
- `{sha_short}` ({date}): {commit_message}

**Impact on plan**:
When first planned, this file {description of expected state}.
In commit {sha} on {date}, {description of what changed}.
{New callers / scope changes / partial fixes discovered}.
Review {specific task IDs} against this change during execution.

### {next file}
...
```

**Plan Drift output format when no drift is detected:**

```markdown
## Plan Drift

**Plan**: {plan_path}
**Plan last modified**: {date}
**Files checked**: {count}
**No drift detected** — all referenced files unchanged since plan creation.
```

---

## Mode B: Grooming Drift (item groomed but no plan file)

**Precondition**: Item is groomed (has groomed sections) but `plan` field is absent or empty.

**Purpose**: Detect what changed in the codebase since the item was groomed, so the groomed content reflects current reality before planning begins.

Spawn a haiku-model agent (`subagent_type="general-purpose"`, model=haiku) with this task:

1. Call `mcp__plugin_dh_backlog__backlog_view(selector="{title}")` to retrieve the full item
2. Extract file paths from the groomed sections:
   - **Impact Radius** section — file paths listed under Code, Documentation, Configuration/CI, Agent Instructions
   - **Files** section — explicit file paths listed by the groomer
   - **Output / Evidence** section — file paths cited as evidence
3. Get the item's groomed date from the frontmatter `groomed` field (format: `YYYY-MM-DD`)
4. For each extracted file path, find commits since that date: `git log --oneline --since={groomed_date} -- {file_path}`
5. For each commit found, get the diff summary: `git show --stat {sha} -- {file_path}` and `git log -1 --format=%s {sha}` for the commit message
6. Analyze whether each commit changes what the groomed content describes. Same categories as Mode A:
   - **Scope change** — file now does more or less than the groomed content assumed
   - **Partial fix** — the issue the item describes was partially resolved by another commit
   - **New callers** — other files now depend on this file that the groomed content did not account for
   - **File moved/renamed** — file is at a different path
   - **No impact** — commit is unrelated to the item's scope for this file
7. Write findings to the backlog item via `mcp__plugin_dh_backlog__backlog_groom(selector="{title}", section="Grooming Drift", content="...")`

**Grooming Drift output format when drift is detected:**

```markdown
## Grooming Drift

**Groomed date**: {groomed_date}
**Files checked**: {count}
**Files with drift**: {count}

### {file_path}

**Commits since grooming** ({count}):
- `{sha_short}` ({date}): {commit_message}

**Impact on groomed content**:
When groomed on {groomed_date}, this file {description of expected state}.
In commit {sha} on {date}, {description of what changed}.
{New callers / scope changes / partial fixes discovered}.
Re-groom or update the affected sections before planning.

### {next file}
...
```

**Grooming Drift output format when no drift is detected:**

```markdown
## Grooming Drift

**Groomed date**: {groomed_date}
**Files checked**: {count}
**No drift detected** — all referenced files unchanged since grooming.
```
