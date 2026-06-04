---
title: "DH GitHub Backlog System — Complete MCP Tool Reference"
date: 2026-05-14
scope: >
  Full documentation of the development-harness plugin's GitHub Issues backlog
  system: every MCP tool with parameters, GitHub Issues field mapping, backlog
  item file format, artifact manifest system, and dispatch/wave system.
  Purpose: design a beads-based replacement backend.
sources:
  - plugins/development-harness/backlog_core/server.py
  - plugins/development-harness/backlog_core/models.py
  - plugins/development-harness/CLAUDE.md
  - plugins/development-harness/docs/backlog-item-lifecycle.md
  - plugins/development-harness/docs/backend-providers.md
  - plugins/development-harness/skills/backlog/templates/item.md
  - plugins/development-harness/docs/backlog-item-groomed-schema.md
---

## Summary

The development-harness plugin exposes a FastMCP 3.x server (`backlog_core/server.py`) that
manages backlog items as both local markdown files and GitHub Issues. GitHub Issues is the
authoritative source of truth; local files at `~/.dh/projects/{slug}/backlog/*.md` are a cache.
The server provides three logical subsystems: backlog CRUD (`backlog_*`), artifact manifest
management (`artifact_*`), and dispatch/wave orchestration (`dispatch_*`). Every tool returns a
dict; failures include an `error` key.

---

## 1. Backlog Item File Format

Local cache files live at `~/.dh/projects/{slug}/backlog/<topic>.md`.
The canonical new-item template is at
`plugins/development-harness/skills/backlog/templates/item.md`.

```yaml
---
name: ITEM TITLE HERE
description: One-sentence summary of the problem or goal.
metadata:
  topic: item-title-slug-here
  source: Session observation | Code review | User request | Research finding
  added: YYYY-MM-DD
  priority: P1
  type: Feature
  status: needs-grooming
  # groomed: YYYY-MM-DD
  # issue: '#N'
  # milestone: N
  # plan: plan/slug.md
---
```

Body sections (added during grooming; defined in
`plugins/development-harness/docs/backlog-item-groomed-schema.md`):

```markdown
## Groomed YYYY-MM-DD

### Reproducibility
### Output/Evidence
### Priority
### Impact
### Benefits
### Expected Behavior
### Desired Structure
### Acceptance Criteria
### Human Input
### Questions for Human
### Resources
### Dependencies
### Blockers
### Effort
### Issue Classification
### Root-Cause Analysis
```

Entry blocks within sections use timestamp IDs (e.g. `2026-05-14T10:30:00Z`) so individual
entries can be struck or replaced without rewriting the whole section. Struck entries are
preserved in collapsed `<details>` blocks for audit.

### Valid Metadata Values

| Field | Valid values |
|---|---|
| `priority` | P0, P1, P2, Ideas, completed |
| `type` | Feature, Bug, Refactor, Docs, Chore |
| `status` | open, done, in-progress, needs-grooming, closed |

---

## 2. GitHub Issues Field Mapping

| Local field | GitHub representation |
|---|---|
| `name` / `title` | Issue title |
| `description` | Issue body preamble (before first `##`) |
| `metadata.priority` | Label: `priority:p0`, `priority:p1`, `priority:p2`, `priority:ideas` |
| `metadata.type` | Label: `type:feature`, `type:bug`, `type:refactor`, `type:docs`, `type:chore` |
| `metadata.status` | Label: `status:in-progress`, `status:needs-grooming`, `status:groomed`, `status:verified` |
| `metadata.issue` | Issue number `#N` |
| `metadata.milestone` | GitHub milestone number |
| `metadata.plan` | Referenced in issue body as `Plan: <path>` |
| `metadata.groomed` | Issue body groomed date heading `## Groomed YYYY-MM-DD` |
| Body sections (`## Heading`) | Mirrored to issue body verbatim |
| Entry blocks (timestamp IDs) | Preserved in issue body |
| Struck entries | `<details>` blocks in issue body |
| Artifact manifest | HTML comment block in issue body: `<!-- dh-artifact-manifest … -->` |
| Artifact content | GitHub issue comments (collapsible, identified by type+path) |
| SAM task sub-issues | GitHub sub-issues with `sam:task` YAML block in body |

The `backlog_sync` tool creates missing GitHub Issues and pushes groomed content. The
`backlog_pull` tool pulls issue body content back into local files using entry-aware merge
(keeps longer entries, preserves strikes).

---

## 3. MCP Tools Reference

The server name is `backlog`. MCP prefix: `mcp__plugin_dh_backlog__`.

### 3.1 Backlog CRUD Tools

#### `backlog_add`

Add a new item to the backlog. Creates a local file and a GitHub Issue.

**GATE**: Direct calls are not permitted. Use `/dh:work-backlog-item create` — the skill workflow provides the required authorization token. Direct calls without going through the skill are rejected.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `title` | str | required | Item title |
| `priority` | str | required | P0, P1, P2, or Ideas |
| `description` | str | required | Item description |
| `source` | str | `"Not specified"` | Where this item came from |
| `type` | str | `"Feature"` | Feature, Bug, Refactor, Docs, or Chore |
| `force` | bool | `False` | Skip fuzzy duplicate check |
| `gate_token` | str\|None | `None` | Required. Provided by the `/dh:work-backlog-item create` skill — do not call directly |

Returns: `{file_path, title, priority, issue (if created), messages, warnings}` or `{error}`.

---

#### `backlog_list`

List open backlog items with filtering, search, and auto-pagination.

Auto-pagination: when `limit=0`, binary-searches for the largest slice that fits within a
4,400-token budget (cl100k_base encoding).

| Parameter | Type | Default | Description |
|---|---|---|---|
| `from_github` | bool | `False` | Refresh local cache from GitHub before listing |
| `label` | str\|None | `None` | Filter by GitHub label (e.g. `'priority:p1'`, `'type:bug'`) |
| `section` | str\|None | `None` | Filter by priority section: P0, P1, P2, Ideas |
| `status` | str\|None | `None` | Filter by status value (e.g. `'needs-grooming'`, `'status:in-progress'`) |
| `title` | str\|None | `None` | Filter by title substring (case-insensitive) |
| `type` | str\|None | `None` | Filter by metadata.type exact match |
| `topic` | str\|None | `None` | Filter by metadata.topic substring |
| `include_closed` | bool | `False` | Include items with closed/done/resolved status |
| `search` | str\|None | `None` | Full-text search with OR/AND/NOT, regex, field-specific syntax |
| `offset` | int | `0` | Skip first N items (pagination) |
| `limit` | int | `0` | Max items to return; 0 = auto-paginate to 4,400-token budget |
| `count_only` | bool | `False` | Return only `{"count": N}` without fetching content |
| `match_context` | bool | `False` | Include match snippets showing where search terms were found |
| `snippet_context` | int | `1024` | Character budget for pre+post context around each match |
| `item_depth` | int | `0` | 0=compact, 1=+description_snippet+section_names, 2=+full_description+section_first_lines, 3=+full body |
| `page` | int | `1` | Page number for match_context pagination |
| `tokens_per_page` | int | `1000` | Max tokens of match_context output per page |
| `page_token_limit` | int | `4000` | Total token threshold that activates match_context pagination |
| `fields` | list[str]\|None | `None` | Return only listed fields: issue, title, section, topic, type, status, body |

Returns: `{items, count, available_fields, pagination, backend, messages, warnings}` or `{error}`.
`pagination`: `{offset, limit, total, has_more}`. When `has_more=True`: `next_call` is included.
Items are deduplicated by issue number (first occurrence wins).

**Search syntax**: OR/AND/NOT operators (case-insensitive), parenthetical grouping, `/regex/` or
`regex:pattern`, field-specific `field:value` (title, type, topic, section, body), plain
case-insensitive substring. Operator precedence: NOT > AND > OR.

---

#### `backlog_view`

View a single backlog item or GitHub Issue in detail.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `selector` | str | required | GitHub issue URL, #N, bare number, or title substring |
| `summary` | bool | `True` | True=compact manifest (sections_index, plan_path, _hint); False=full response |
| `include_content` | bool | `True` | False=metadata + section inventory only (no body content) |
| `offset` | int | `0` | Skip N entry blocks from body start |
| `limit` | int | `0` | Show at most N entry blocks (0=all) |
| `show` | str\|None | `None` | Entry filter: 'all', 'last', 'first', 'struck', or integer N |
| `since` | str\|None | `None` | ISO date; only entries at or after this timestamp |
| `section` | str\|None | `None` | Section filter: numeric index '2', comma-separated '0,2,4', regex '/pattern/', or substring |
| `sections` | list[str]\|None | `None` | Return only named sections plus identity fields |

Auto-compact: when `summary=False` and no section filter, if full response exceeds the
4,000-token budget, returns a compact `_over_budget` form with `sections_index` and usage hint
instead of the full response.

Progressive disclosure pattern:
1. `backlog_view(selector="...", summary=True)` — get `sections_index` and metadata
2. `backlog_view(selector="...", summary=False, section="Fact-Check")` — load specific section
3. `backlog_view(selector="...", summary=False, section="0,1,3")` — load by index
4. `backlog_view(selector="...", summary=False, section="/acceptance|plan/")` — load by regex

Returns when `summary=True`: `{issue_number, title, labels, status, plan_path, sections_index, _summary, _full_chars, _hint}`.
Returns when `summary=False`: `{title, priority, issue, plan, file_path, body, sections, messages, warnings}` or compact `_over_budget` form or `{error}`.

---

#### `backlog_sync`

Sync backlog items with GitHub: create missing issues and push groomed content.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `dry_run` | bool | `False` | Preview what would be synced without making changes |

Returns: `{created, pushed, messages, warnings}` or `{error}`.

---

#### `backlog_close`

Dismiss a backlog item without completing it and close its GitHub Issue. Use for duplicates,
out-of-scope, superseded, wontfix, or permanently blocked items. For completed work, use
`backlog_resolve` instead. (ADR-9 semantics: close = dismiss, resolve = complete.)

| Parameter | Type | Default | Description |
|---|---|---|---|
| `selector` | str | required | Item selector |
| `reason` | str | required | duplicate, out_of_scope, superseded, wontfix, blocked |
| `reference` | str | `""` | Related item reference (#N, URL, or title) |
| `comment` | str | `""` | Additional context |
| `cleanup` | bool | `False` | Remove local file after close |
| `force` | bool | `False` | Close even if open PRs reference the issue |

Returns: `{title, reason, messages, warnings}` or `{error}`.

---

#### `backlog_resolve`

Mark a backlog item as DONE (completed) and close its GitHub Issue. Creates a structured
completion record as an audit/retrospective trail.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `selector` | str | required | Item selector |
| `summary` | str | required | What was done — 1-2 sentence completion summary |
| `plan` | str\|None | `None` | Plan path or completion reference |
| `method` | str\|None | `None` | How the work was done |
| `notes` | str\|None | `None` | Problems found, surprises, or comments |
| `follow_ups` | str\|None | `None` | Created follow-up tickets (comma-separated refs) |
| `findings` | str\|None | `None` | Retrospective learnings |
| `cleanup` | bool | `False` | Remove local file after resolve |
| `force` | bool | `False` | Resolve even if open PRs reference the issue |

Returns: `{title, summary, messages, warnings}` or `{error}`.

---

#### `backlog_update`

Update a backlog item: attach a plan, set status, or write groomed content.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `selector` | str | required | Item selector |
| `plan` | str\|None | `None` | Path to a plan file to attach |
| `status` | str\|None | `None` | Set item status; updates GitHub labels when applicable |
| `section` | str\|None | `None` | Section name for groomed content update |
| `content` | str\|None | `None` | Content for the named section |
| `title` | str\|None | `None` | New title; updates local file and GitHub issue title |
| `description` | str\|None | `None` | New description text (local file only) |
| `entry_id` | str\|None | `None` | Timestamp ID of existing entry to replace |
| `replace_section` | bool | `False` | Strike all existing entries in section and append new content |
| `reason` | str\|None | `None` | Reason for striking (required when replace_section=True) |
| `verified` | bool | `False` | Apply status:verified label to GitHub Issue |

Returns: `{title, changes, messages, warnings}` or `{error}`.

---

#### `backlog_groom`

Write groomed content into a backlog item's per-item file and sync to GitHub Issue.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `selector` | str | required | Item selector |
| `section` | str\|None | `None` | Section name for incremental update |
| `content` | str\|None | `None` | Content for the named section |
| `entry_id` | str\|None | `None` | Timestamp ID of existing entry to replace |
| `replace_section` | bool | `False` | Strike all existing entries and append new content |
| `reason` | str\|None | `None` | Reason for striking (required when replace_section=True) |
| `append` | bool | `False` | Append after existing section content (no entry-block wrapping) |
| `sections` | dict[str,str]\|None | `None` | Batch section writes: section name → raw content. Mutually exclusive with other section params |
| `mark_groomed` | bool | `False` | Advance status to groomed (set local frontmatter + update GitHub labels) |

Returns: `{title, synced, messages, warnings}` or `{error}`.

---

#### `backlog_normalize`

Normalize all per-item files to research-style metadata format and remove body duplication.
One-off maintenance operation.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `dry_run` | bool | `False` | Preview normalization changes without modifying files |

Returns: `{updated, messages, warnings}` or `{error}`.

---

#### `backlog_pull`

Pull issue body content from GitHub into local per-item files. Merges by section using
entry-aware merge (keeps longer entries, preserves strikes). Auto-migrates P0/P1 items lacking
GitHub Issues by creating them.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `selector` | str\|None | `None` | Pull a single issue; omit to pull all |
| `dry_run` | bool | `False` | Preview what would be pulled |
| `force` | bool | `False` | Overwrite local content even if local version is newer or longer |
| `diff` | bool | `False` | Include entry-level diff output showing local vs remote changes |

Returns bulk: `{pulled, messages, warnings}` or single: `{file_path, messages, warnings}` or `{error}`.

---

### 3.2 SAM Task Tools

#### `backlog_create_sam_task`

Create a GitHub sub-issue for a SAM task under a parent story issue.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `parent_issue_number` | int | required | Parent story issue number (without #) |
| `task_id` | str | required | Feature-scoped task ID, e.g. 'T1' |
| `feature` | str | required | Feature slug, e.g. 'my-feature' |
| `task_type` | str | required | research \| implement \| review \| fix \| docs |
| `agent` | str | required | Agent name to execute this task |
| `priority` | int | `2` | Priority 1-5 (1=highest) |
| `skills` | list[str] | `[]` | Skill names for the executing agent |
| `dependencies` | list[str] | `[]` | Task IDs this task depends on |
| `description` | str | `""` | Human-readable description |
| `acceptance_criteria` | list[str]\|None | `None` | Acceptance criteria strings |
| `labels` | list[str]\|None | `None` | GitHub label names to apply |

Returns: `{issue_number, title, url, messages}` or `{error}`.

---

#### `backlog_get_sam_tasks`

Return all SAM task sub-issues for a parent story issue.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `parent_issue_number` | int | required | Parent story issue number (without #) |
| `refresh_cache` | bool | `True` | Write updated cache after fetching |

Returns: `{tasks: [{id, name, agent, skills, issue_number, issue_url, status, ...}], messages}` or `{error}`.

---

#### `backlog_update_sam_task_status`

Update the status field in a SAM task sub-issue. Patches the `sam:task` YAML block in the issue body.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `issue_number` | int | required | Task sub-issue number (without #) |
| `new_status` | str | required | not-started \| in-progress \| complete \| blocked |

Returns: `{updated, issue_number, new_status, messages}` or `{error}`.

---

#### `backlog_get_ready_sam_tasks`

Return SAM tasks ready for execution from GitHub sub-issues. Fetches sub-issues, resolves
dependency graph locally, returns tasks whose status is `not-started` and all dependencies are
terminal.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `parent_issue_number` | int | required | Parent story issue number (without #) |

Returns: `{feature, ready_tasks: [{id, name, agent, skills, issue_number}], count, messages}` or `{error}`.

---

### 3.3 Read-Only GitHub Tools

#### `backlog_strike_entry`

Strike (retract) an entry block within a backlog item. Wraps entry in a collapsed details block
with reason, preserving original content for audit. Syncs to GitHub Issue.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `selector` | str | required | Item selector |
| `entry_id` | str | required | Timestamp ID of the entry to strike |
| `reason` | str | required | Human-readable reason for striking |
| `section` | str\|None | `None` | Optional section name to scope the search |

Returns: `{strike results, messages, warnings}` or `{error}`.

---

#### `backlog_list_labels`

List repository labels (read-only).

| Parameter | Type | Default | Description |
|---|---|---|---|
| `limit` | int | `100` | Maximum labels to return |

Returns: `{labels: [{name, color, description}], count, messages}` or `{error}`.

---

#### `backlog_list_merged_prs`

List merged pull requests, optionally filtered.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `search` | str\|None | `None` | Substring filter against PR title and body (case-insensitive) |
| `limit` | int | `20` | Maximum PRs to return |

Returns: `{pull_requests: [{number, title, merged_at, author, url, head_branch}], count, messages}` or `{error}`.

---

#### `backlog_list_milestones`

List repository milestones filtered by state.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `state` | str | `"open"` | open \| closed \| all |

Returns: `{milestones: [{number, title, state, description, due_on, open_issues, closed_issues}], count, messages}` or `{error}`.

---

#### `backlog_get_soonest_milestone`

Return the open milestone with the earliest due date. Milestones without a due date are excluded.

No parameters.

Returns: `{milestone: {number, title, state, description, due_on, open_issues, closed_issues} | None, messages}` or `{error}`.

---

#### `backlog_create_milestone`

Create a new milestone on the repository.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `title` | str | required | Milestone title (must be non-empty) |
| `description` | str | `""` | Optional milestone description |
| `due_on` | str\|None | `None` | Optional due date as ISO 8601 string |

Returns: `{milestone: {number, title, state, description, due_on, open_issues, closed_issues}, messages}` or `{error}`.

---

#### `backlog_list_issues`

List GitHub issues with optional milestone, label, and state filters.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `milestone` | str\|None | `None` | Filter by milestone title |
| `labels` | str\|None | `None` | Comma-separated label names to filter by |
| `state` | str | `"open"` | open \| closed \| all |
| `limit` | int | `30` | Maximum issues to return |

Returns: `{issues, count, messages}` or `{error}`.

---

#### `backlog_comment_issue`

Add a comment to a GitHub Issue.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `issue_number` | int | required | GitHub issue number (without #) |
| `body` | str | required | Comment body (Markdown) |

Returns: `{issue_number, comment_id, comment_url, messages}` or `{error}`.

---

#### `backlog_list_comments`

List comments on a GitHub Issue.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `issue_number` | int | required | GitHub issue number (without #) |
| `limit` | int | `20` | Maximum comments to return |
| `offset` | int | `0` | Number of comments to skip |

Returns: `{comments: [{id, author, created_at, updated_at, preview}], count, has_more, messages}` or `{error}`.

---

#### `backlog_read_comment`

Read the full body of a single comment on a GitHub Issue.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `issue_number` | int | required | GitHub issue number (without #) |
| `comment_id` | int | required | REST comment database ID (integer) |

Returns: `{id, author, created_at, updated_at, body (full Markdown), messages}` or `{error}`.

---

#### `backlog_list_projects`

List GitHub Projects V2 for the repository owner via GraphQL.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `owner` | str\|None | `None` | GitHub owner (org or user); defaults to repo owner |
| `limit` | int | `20` | Maximum projects to return |

Returns: `{projects, count, messages}` or `{error}`.

---

#### `backlog_create_project`

Create a Projects V2 project under the repository owner.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `title` | str | required | Project title |
| `owner` | str\|None | `None` | GitHub owner; defaults to repo owner |

Returns: `{project_id, title, url, number, messages}` or `{error}`.

---

### 3.4 Artifact Management Tools

#### `artifact_register`

Upsert an artifact entry in the manifest for a GitHub Issue. Idempotent by (artifact_type, artifact_id).

Content upload — three-tier resolution:
1. Explicit `content=` provided → uploaded directly to GitHub issue comment.
2. `content=None` but local file exists at `artifact_id` → auto-read and uploaded.
3. `content=None` and no local file → manifest-only (warning emitted).

| Parameter | Type | Default | Description |
|---|---|---|---|
| `issue_number` | int | required | GitHub issue number |
| `artifact_type` | str | required | feature-context, architect, task-plan, T0-baseline, TN-verification, codebase-analysis, research |
| `artifact_id` | str | required | Logical identifier or repo-relative path |
| `status` | str | `"current"` | draft, current, superseded, archived |
| `agent` | str | `""` | Name of the producing agent |
| `content` | str\|None | `None` | Artifact content to store as GitHub issue comment |

Returns: `{registered, artifact_count, action, content_stored, messages, warnings}` or `{error}`.

---

#### `artifact_list`

Return all artifacts registered for a GitHub Issue.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `issue_number` | int | required | GitHub issue number |
| `artifact_type` | str\|None | `None` | Filter by artifact type (optional) |

Returns: `{artifacts: [{artifact_type, artifact_id, status, created_at, agent}], count, messages}` or `{error}`.

---

#### `artifact_get`

Return metadata for a specific artifact type on a GitHub Issue. Returns all artifacts of that
type if multiple exist.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `issue_number` | int | required | GitHub issue number |
| `artifact_type` | str | required | Artifact type to retrieve |

Returns: `{artifacts, count, messages}` or `{error}`.

---

#### `artifact_read`

Read artifact file content for a GitHub Issue. Content retrieval order:
1. GitHub issue comments (succeeds even from worktree-isolated agents).
2. Local filesystem fallback (path safety validation: must be under repo root).

| Parameter | Type | Default | Description |
|---|---|---|---|
| `issue_number` | int | required | GitHub issue number |
| `artifact_type` | str | required | Artifact type whose content to read |

Returns: `{type, path, content, status, messages, warnings}` or `{error}`.

---

#### `artifact_migrate`

Scan `plan/` and `research/` directories for artifact files, determine artifact type from
filename pattern, extract linked GitHub issue from YAML frontmatter (falling back to slug
matching against backlog items), and register each discovered file. Idempotent — upserts on
(artifact_type, path).

Filename patterns recognized:
- `feature-context-*.md` → feature-context
- `architect-*.md` → architect
- `P{N}-*.yaml` → task-plan
- `T0-baseline-*.yaml` → T0-baseline
- `TN-verification-*.yaml` → TN-verification
- `plan/codebase/*.md` → codebase-analysis
- `research/**/*.md` → research

| Parameter | Type | Default | Description |
|---|---|---|---|
| `issue_number` | int\|None | `None` | Migrate artifacts for a specific issue only; omit to scan all |
| `dry_run` | bool | `False` | Report what would be migrated without API calls |

Returns dry-run: `{dry_run, would_register, would_skip, details, verify}`.
Returns live: `{migrated, skipped, failed, details, verify}` or `{error}`.

---

### 3.5 Dispatch / Wave Orchestration Tools

State is persisted to SQLite at `~/.dh/projects/{slug}/dispatch-state.db`.
Dispatch plan files are at `plan/milestone-{N}-dispatch.yaml` in the repo root.

#### `dispatch_read`

Read an existing dispatch plan from `plan/milestone-{N}-dispatch.yaml`.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `milestone_number` | int | required | GitHub milestone number |

Returns: `{milestone_number, plan: {full plan as nested dict}}` or `{error}`.

---

#### `dispatch_validate`

Validate structural integrity of an existing dispatch plan. Checks: duplicate issues, conflict
group references, depends_on existence, wave ordering, conflict group wave placement.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `milestone_number` | int | required | GitHub milestone number |

Returns: `{milestone_number, is_valid, errors, warnings}` or `{error}`.

---

#### `dispatch_stale_check`

Check whether a dispatch plan is stale relative to the current milestone. Fetches open issues
assigned to the milestone from GitHub, compares their issue numbers against those in the plan.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `milestone_number` | int | required | GitHub milestone number |
| `repo` | str | `""` | Repository slug owner/name; defaults to project repo |

Returns: `{milestone_number, is_stale, added_issues, removed_issues, message}` or `{error}`.

---

#### `dispatch_create_plan`

Create or overwrite a dispatch plan YAML file for a milestone. Writes atomically to
`plan/milestone-{N}-dispatch.yaml`. Optionally validates structural integrity and auto-registers
as a `dispatch-plan` artifact.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `milestone_number` | int | required | GitHub milestone number |
| `plan` | DispatchPlan | required | The dispatch plan (typed model; `plan.milestone.number` must match `milestone_number`) |
| `overwrite` | bool | `False` | Allow overwriting existing plan file |
| `validate` | bool | `True` | Run structural validation after writing |
| `issue` | int\|None | `None` | Optional GitHub issue to auto-register dispatch-plan artifact against |

Returns: `{milestone_number, wave_count, item_count, is_valid, errors, warnings, messages}` or `{error}`.

---

#### `dispatch_conflicts`

Analyze Impact Radius conflicts for items in a milestone. Fetches open issues, extracts Impact
Radius section from each issue body, finds items sharing file paths.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `milestone_number` | int | required | GitHub milestone number |
| `repo` | str | `""` | Repository slug; defaults to project repo |

Returns: `{milestone_number, conflict_groups: [{group_id, reason, items}], count}` or `{error}`.

---

#### `dispatch_wave_start`

Record the start of a dispatch wave. Creates wave and item entries in the state database.
Items are initialized with status `pending`. Call before spawning processes.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `milestone` | int | required | GitHub milestone number |
| `wave_num` | int | required | Wave number from dispatch plan (1-based) |
| `items` | list[dict] | required | List of items, each with `'issue'` (int) and `'title'` (str) |

Returns: `{milestone, wave_num, items_count, status, messages, warnings}` or `{error}`.

---

#### `dispatch_item_status`

Record completion or failure of a dispatch item. Looks up item by milestone + issue across all
waves.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `milestone` | int | required | GitHub milestone number |
| `issue` | int | required | Issue number of the item |
| `status` | str | required | complete \| failed \| skipped |
| `result` | str | `""` | Result summary or JSON from result file |
| `error` | str | `""` | Error details on failure |
| `cost` | float\|None | `None` | USD cost if available from claude output |

Returns: `{milestone, issue, wave_num, status, messages, warnings}` or `{error}`.

---

#### `dispatch_wave_status`

Query the current status of a dispatch wave. Checks PIDs for in-progress items and marks dead
ones as failed before returning.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `milestone` | int | required | GitHub milestone number |
| `wave_num` | int | required | Wave number to query (1-based) |

Returns: `{milestone, wave_num, status, total_items, pending, in_progress, complete, failed, skipped, started_at, completed_at, elapsed_seconds, items, messages, warnings, accumulated_usage}` or `{error}`.

---

#### `dispatch_spawn`

Background task (`task=True`) that calls `dispatch_wave_start` then spawns one `claude -p`
kage-bunshin process per wave item. Runs the starting wave and all subsequent waves
sequentially. Polls each item until its result file appears or its PID dies.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `milestone` | int | required | GitHub milestone number |
| `wave_num` | int | required | Starting wave number (1-based) |
| `max_concurrent` | int | `3` | Maximum concurrent spawned sessions |
| `model` | str | `"sonnet"` | Model identifier for spawned sessions |
| `phase` | str | `"work"` | groom (no worktree) \| work (with worktree) |
| `effort` | str\|None | `None` | low \| medium \| high \| max; None uses model default |

Returns: dispatch wave summary dict or `{error}`.

Spawn command structure per item:
```text
uv run spawn.py --model <model> --name dispatch-<milestone>-<issue> [--effort <level>] [--worktree] [--branch <branch>] "Work on issue #<issue>: <title>"
```

---

### 3.6 Profile Tool

#### `profile_load`

Load a named agent profile to specialize task-worker behavior at dispatch time.
Profile definitions live in the backlog server configuration.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `agent_name` | str | required | Name of the agent profile to load |

---

## 4. Artifact Manifest System

### Storage Location

The manifest is stored as an HTML comment in the GitHub Issue body:

```html
<!-- dh-artifact-manifest
{"artifacts": [...]}
-->
```

The manifest is the discovery mechanism. Consumers call `artifact_list` then `artifact_read`
rather than accessing the filesystem directly. This allows worktree-isolated agents and CI
environments to read artifacts from any location.

### Artifact Types (`ArtifactType` enum)

| Value | Purpose |
|---|---|
| `feature-context` | S1 Discovery output — feature requirements and codebase context |
| `architect` | S2/S3 Architecture output |
| `task-plan` | S4 Task decomposition plan (P{N}-slug.yaml) |
| `codebase-analysis` | Codebase structure analysis |
| `T0-baseline` | Pre-implementation baseline capture |
| `TN-verification` | Post-implementation verification |
| `dispatch-plan` | Milestone dispatch plan YAML |
| `audit-report` | S6 Forensic review output |
| `research` | Research documents under `research/` |

### Artifact Status (`ArtifactStatus` enum)

| Value | Meaning |
|---|---|
| `draft` | Work in progress |
| `current` | Active artifact |
| `superseded` | Replaced by a newer artifact of the same type |
| `archived` | Retained for reference but no longer active |

### Content Storage

Artifact content is stored in GitHub Issue comments as collapsible blocks identified by
`(artifact_type, artifact_id)`. The `artifact_read` tool tries GitHub comment storage first,
then falls back to the local filesystem. This means content is accessible even from isolated
worktrees or CI.

### `ArtifactEntry` Model

```python
artifact_type: ArtifactType
artifact_id: str           # repo-relative path or logical ID
status: ArtifactStatus
created_at: str            # ISO 8601 datetime
agent: str                 # producing agent name
```

### MCP-Native Rule for Agents

Agents store system artifacts exclusively via `artifact_register(content=...)`. The `Write`
tool is only for repo-relative deliverables (source code, tests, documentation). Direct
filesystem writes to `~/.dh/` are prohibited for artifact content.

---

## 5. Dispatch / Wave System

### Architecture

Wave-based parallel execution for milestone work. The orchestrator (`/dh:groom-milestone`,
`/dh:work-milestone`) manages the lifecycle:

1. `/dh:groom-milestone` calls `dispatch_create_plan` — writes `plan/milestone-{N}-dispatch.yaml`
2. `/dh:work-milestone` calls `dispatch_wave_start` — initializes wave state in SQLite
3. `/dh:work-milestone` calls `dispatch_spawn` — launches `claude -p` kage-bunshin processes per wave item
4. Spawned sessions call `dispatch_item_status` on completion
5. `/dh:work-milestone` polls `dispatch_wave_status` to monitor progress
6. Waves execute sequentially; items within a wave are concurrent (controlled by `max_concurrent`)

### State Storage

SQLite database at `~/.dh/projects/{slug}/dispatch-state.db`. The `DispatchStateManager` class
manages the database. The slug is derived from the repo root path: `/home/user/repos/my_project`
→ `home-user-repos-my_project`.

### `DispatchItemRecord` Model

```python
milestone: int
wave_num: int
issue: int
title: str
status: str           # pending, in-progress, complete, failed, skipped
pid: int | None       # OS process ID of spawned session
session_id: str | None
result: str           # JSON result or summary
error: str
cost: float | None    # USD cost
started_at: str | None
completed_at: str | None
```

### `DispatchWaveRecord` Model

```python
milestone: int
wave_num: int
status: str           # pending, in-progress, complete, failed
items: list[DispatchItemRecord]
started_at: str | None
completed_at: str | None
```

### Dispatch Plan YAML Structure

```yaml
milestone:
  number: N
  title: "Milestone Title"
waves:
  - wave_num: 1
    items:
      - issue: 123
        title: "Item title"
        depends_on: []
        conflict_group: null
  - wave_num: 2
    items: [...]
```

Structural integrity checks (via `dispatch_validate`): duplicate issues, conflict group
references, depends_on existence, wave ordering, conflict group wave placement.

---

## 6. Backend Architecture

The `BacklogBackend` Protocol (`backlog_core/backend_protocol.py`) decouples all operations
from any specific storage platform.

### Available Backends

| Backend | Description | Credentials |
|---|---|---|
| `github` | Default. GitHub Issues via GraphQL + PyGithub REST | `GITHUB_TOKEN` |
| `sqlite` | Local 6-table SQLite schema, WAL mode | None |
| `memory` | In-memory test double, no persistence | None |

### Backend Selection

1. `BACKLOG_BACKEND` environment variable
2. `[backend] name` in `backend.toml` (project root or `~/.dh/`)
3. Default: `github`

### Backend Availability States (`BackendAvailability` enum)

| Value | Meaning |
|---|---|
| `reachable` | Backend is reachable and authenticated |
| `not_checked` | Status probe not yet run |
| `needs_authentication` | Credentials missing or invalid |
| `rate_limited` | API rate limit exceeded |
| `error` | Other error condition |

The `BackendStatus` is included in `backlog_list` responses as the `backend` field.

### Three-Primitive Storage Model

| Primitive | Interface | Purpose |
|---|---|---|
| Work Item | `IssueBackend` | Backlog items / GitHub Issues |
| Sub-item | `TaskBackend` | SAM tasks / sub-issues |
| Document | `DocumentBackend` | Artifact content / issue comments |

---

## 7. State Path Conventions

| Path | Contents |
|---|---|
| `~/.dh/projects/{slug}/backlog/*.md` | Local backlog item cache |
| `~/.dh/projects/{slug}/plan/*.yaml` | SAM task plan YAML files |
| `~/.dh/projects/{slug}/dispatch-state.db` | Dispatch wave/item SQLite state |
| `{repo_root}/plan/milestone-{N}-dispatch.yaml` | Dispatch plan YAML |
| `{repo_root}/plan/feature-context-{slug}.md` | S1 artifact |
| `{repo_root}/plan/architect-{slug}.md` | Architecture artifact |
| `{repo_root}/plan/P{id}-{slug}.yaml` | Task plan artifact |
| `{repo_root}/plan/T0-baseline-{slug}.yaml` | Pre-implementation baseline |
| `{repo_root}/plan/TN-verification-{slug}.yaml` | Post-implementation verification |
| `{repo_root}/plan/codebase/*.md` | Codebase analysis artifacts |
| `{repo_root}/research/**/*.md` | Research artifacts |

Slug derivation: absolute project path with `/` replaced by `-` (leading `-` included).
Example: `/home/user/repos/claude_skills` → `-home-user-repos-claude_skills`.

---

## 8. Capability Inventory

| Capability | DH GitHub Backlog | Notes |
|---|---|---|
| Create backlog item | Yes | `backlog_add` with gate_token |
| List backlog items | Yes | `backlog_list` with filtering, search, auto-pagination |
| View single item | Yes | `backlog_view` with progressive disclosure |
| Full-text search | Yes | OR/AND/NOT, regex, field-specific, body sections |
| Match context snippets | Yes | `match_context=True` with section attribution |
| Auto-pagination by token budget | Yes | 4,400 tokens (list), 4,000 tokens (view) |
| Update item (plan, status, content) | Yes | `backlog_update` |
| Write groomed content | Yes | `backlog_groom` with entry-block tracking |
| Batch section writes | Yes | `backlog_groom(sections={...})` |
| Strike/retract entries | Yes | `backlog_strike_entry`, `replace_section=True` |
| Audit trail of strikes | Yes | Preserved in `<details>` blocks |
| Close item (dismiss) | Yes | `backlog_close` with reason |
| Resolve item (complete) | Yes | `backlog_resolve` with completion record |
| Sync local → GitHub | Yes | `backlog_sync` (create issues + push groomed content) |
| Sync GitHub → local | Yes | `backlog_pull` (entry-aware merge) |
| Dry-run for sync/pull | Yes | `dry_run=True` on both |
| Normalize metadata format | Yes | `backlog_normalize` |
| Deduplication by issue number | Yes | Applied automatically in `backlog_list` |
| GitHub label management | Yes | Status, priority, type labels via state transitions |
| Milestone management | Yes | List, create, get soonest |
| Issue listing (direct GitHub) | Yes | `backlog_list_issues` |
| Comment on issues | Yes | `backlog_comment_issue` |
| Read comments | Yes | `backlog_list_comments`, `backlog_read_comment` |
| List/create GitHub Projects V2 | Yes | `backlog_list_projects`, `backlog_create_project` |
| List merged PRs | Yes | `backlog_list_merged_prs` |
| List labels | Yes | `backlog_list_labels` |
| SAM task sub-issues | Yes | `backlog_create_sam_task`, `backlog_get_sam_tasks`, `backlog_update_sam_task_status`, `backlog_get_ready_sam_tasks` |
| Dependency resolution for SAM tasks | Yes | `backlog_get_ready_sam_tasks` resolves dependency graph |
| Artifact manifest (register) | Yes | `artifact_register` with 3-tier content upload |
| Artifact manifest (list/get) | Yes | `artifact_list`, `artifact_get` |
| Artifact content retrieval | Yes | `artifact_read` (GitHub comments first, filesystem fallback) |
| Bulk artifact migration | Yes | `artifact_migrate` with filename pattern classification |
| Dispatch plan validation | Yes | `dispatch_validate` (5 structural checks) |
| Dispatch plan staleness check | Yes | `dispatch_stale_check` vs live GitHub milestone |
| Dispatch conflict analysis | Yes | `dispatch_conflicts` (Impact Radius file overlap) |
| Wave-based parallel execution | Yes | `dispatch_spawn` with max_concurrent throttle |
| Wave state tracking (SQLite) | Yes | `dispatch_wave_start`, `dispatch_wave_status`, `dispatch_item_status` |
| Dead PID detection | Yes | `dispatch_wave_status` auto-marks dead processes failed |
| Stale PID tracking | Yes | `dispatch_stale_check` |
| Cost tracking per dispatch item | Yes | `dispatch_item_status(cost=...)` |
| Profile loading for task-worker | Yes | `profile_load` |
| Backend pluggability | Yes | GitHub, SQLite, InMemory — Protocol-based |
| Backend availability status | Yes | Included in `backlog_list` responses |
| Gate-protected item creation | Yes | `backlog_add` requires authorization via `/dh:work-backlog-item create` skill |
| Cross-worktree artifact access | Yes | GitHub comment storage, no local filesystem dependency |
| Item lifecycle tracking | Yes | 7-phase: Capture→Grooming→Research/Architecture→Planning→Execution→Quality Gates→Closure |
| Offline fallback | Partial | Local cache used when GitHub unavailable; not all tools degrade gracefully |
| Multi-project support | Yes | Slug-based path isolation per project root |
| Configurable via env vars | Yes | `BACKLOG_BACKEND`, `DH_STATE_HOME`, `GITHUB_TOKEN`, `CLAUDE_PROJECT_DIR` |

---

## What Was NOT Found

- No beads integration currently present. A comment in `server.py` (line 107-111) explicitly
  states: "Beads integration removed — was auto-installing @beads/bd via npm during the FastMCP
  lifespan hook, blocking MCP initialization for 20+ seconds when the download hung."
- No webhook or event-driven sync mechanism. All GitHub sync is pull-based (explicit tool calls).
- No issue template enforcement at the MCP level (templates live in the GitHub repo as `.github/ISSUE_TEMPLATE/`).
- No rate-limit backoff logic visible in server.py tool handlers (delegated to PyGithub/GitHub API).
- No batch close/resolve tool (each item closed individually).

---

## Uncertain

- `profile_load` tool: its full parameter list and response shape are not defined in `server.py`
  directly — it is referenced as an agent profile tool in CLAUDE.md and backend-providers.md but
  its implementation was not read. The tool exists as an MCP tool on the backlog server.
- `dispatch_spawn` integration branch parameter: `integration_branch` is referenced in
  `_build_spawn_cmd` but not exposed as an explicit `dispatch_spawn` parameter in the read
  portion of server.py. The last 300 lines (after line 4393) were not read. This may be an
  undocumented internal parameter or a later addition.
- SQLite dispatch state schema: exact table definitions are in `dispatch_state.py` which was not
  read. The model fields above are inferred from `DispatchItemRecord` and `DispatchWaveRecord`
  Pydantic models in `models.py`.

---

## Sources

| File | Read timestamp |
|---|---|
| `plugins/development-harness/backlog_core/server.py` | 2026-05-14 (lines 0–4395) |
| `plugins/development-harness/backlog_core/models.py` | 2026-05-14 (lines 0–120) |
| `plugins/development-harness/CLAUDE.md` | 2026-05-14 (via system-reminder context) |
| `plugins/development-harness/docs/backlog-item-lifecycle.md` | 2026-05-14 (prior session) |
| `plugins/development-harness/docs/backend-providers.md` | 2026-05-14 (prior session) |
| `plugins/development-harness/skills/backlog/templates/item.md` | 2026-05-14 (prior session) |
| `plugins/development-harness/docs/backlog-item-groomed-schema.md` | 2026-05-14 (prior session) |
