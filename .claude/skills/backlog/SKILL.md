---
name: backlog
description: "Single interface for backlog items and GitHub Issues. GitHub Issues are the source of truth; .claude/backlog/ per-item files are the local cache. All backlog CRUD goes through MCP tools (mcp__backlog__*) in orchestrator sessions — no direct file edits. Use when creating, listing, viewing, updating, closing, resolving, grooming, or syncing backlog items and GitHub issues."
---

# Backlog

MCP tools are the **primary interface** for backlog items and GitHub Issues.
GitHub Issues are the source of truth; `.claude/backlog/` per-item files are the local cache.
Skills and agents invoke MCP tools or the CLI — no direct `Write`/`Edit` on per-item files.

## Primary Interface (MCP)

All 10 tools return a `dict`. On error the dict contains an `"error"` key. On success it
contains result data keys plus `messages: list[str]` and `warnings: list[str]` (always present,
may be empty). Always check for `"error"` before consuming result fields.

The MCP tool name prefix is `mcp__backlog__` followed by the tool name below.

### `backlog_add`

Create a new backlog item and optionally a GitHub issue.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `title` | `str` | required | Item title |
| `priority` | `str` | required | `P0`, `P1`, `P2`, or `Ideas` |
| `description` | `str` | required | Item description |
| `source` | `str` | `"Not specified"` | Where this item came from |
| `type` | `str` | `"Feature"` | `Feature`, `Bug`, `Refactor`, `Docs`, or `Chore` |
| `create_issue` | `bool` | `True` | Create a GitHub issue for this item |
| `force` | `bool` | `False` | Skip fuzzy duplicate check |

Returns `{filepath, filename, title, priority, issue_num?, messages, warnings}`.

Note — `research_first` has no MCP equivalent. Embed research questions in `description`.

### `backlog_list`

List open backlog items with optional filters.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `with_status` | `bool` | `False` | Include GitHub issue status for each item |
| `from_github` | `bool` | `False` | Refresh local cache from GitHub before listing |
| `label` | `str \| None` | `None` | Filter by GitHub label (e.g. `"priority:p1"`) |
| `section` | `str \| None` | `None` | Filter by priority section: `P0`, `P1`, `P2`, or `Ideas` |
| `status` | `str \| None` | `None` | Filter by status (e.g. `"needs-grooming"`, `"status:in-progress"`) |
| `title` | `str \| None` | `None` | Filter by title substring (case-insensitive) |

Returns `{items: [{title, priority, issue, plan}], messages, warnings}`.

Note — the CLI `--format text|json` flag has no MCP equivalent. MCP tools always return
structured dicts (equivalent to JSON). Use `backlog_view` for detailed single-item output.

### `backlog_view`

View a single backlog item in detail. Supports pagination for long bodies.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `selector` | `str` | required | GitHub issue URL, `#N`, bare number, or title substring |
| `offset` | `int` | `0` | Skip N entry blocks from body start (for pagination) |
| `limit` | `int` | `0` | Show at most N entry blocks (`0` = all, no truncation) |

Returns `{title, priority, issue, plan, file_path, body, groomed, messages, warnings}`.

### `backlog_sync`

Sync backlog items with GitHub — create missing issues and push groomed content.
Emits progress messages via MCP context during execution.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `dry_run` | `bool` | `False` | Preview changes without modifying anything |

Returns `{created, pushed, messages, warnings}`.

### `backlog_close`

Dismiss a backlog item without completing it and close its GitHub issue. ADR-9.

Use for duplicates, out-of-scope items, superseded items, wontfix, or permanently blocked.
For completed work, use `backlog_resolve` instead.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `selector` | `str` | required | Title substring, `#N`, bare number, or GitHub issue URL |
| `reason` | `str` | required | One of: `duplicate`, `out_of_scope`, `superseded`, `wontfix`, `blocked` |
| `reference` | `str` | `""` | Related item: `#N`, URL, or title of item this duplicates/is superseded by |
| `comment` | `str` | `""` | Additional context about why this item is being closed |
| `cleanup` | `bool` | `False` | Remove local file after close |
| `force` | `bool` | `False` | Close even if open PRs reference the issue |

Returns `{title, reason, closed, messages, warnings}`.

### `backlog_resolve`

Mark a backlog item as DONE (completed) and close its GitHub issue with an evidence trail.

Creates a structured completion record (summary, method, notes, follow-ups, findings) as an
audit/retrospective trail. Only `summary` is required — a one-liner suffices for trivial items.
For dismissals (duplicate, out of scope, etc.), use `backlog_close` instead.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `selector` | `str` | required | Title substring, `#N`, bare number, or GitHub issue URL |
| `summary` | `str` | required | What was done — 1-2 sentence completion summary |
| `plan` | `str \| None` | `None` | Plan path or completion reference |
| `method` | `str \| None` | `None` | How the work was done |
| `notes` | `str \| None` | `None` | Problems found, surprises, or other comments |
| `follow_ups` | `str \| None` | `None` | Created follow-up tickets (comma-separated refs) |
| `findings` | `str \| None` | `None` | Retrospective learnings from this work |
| `cleanup` | `bool` | `False` | Remove local file after resolve |
| `force` | `bool` | `False` | Resolve even if open PRs reference the issue |

Returns `{title, summary, resolved, messages, warnings}`.

### `backlog_update`

Update a backlog item — attach a plan, set status, create a GitHub issue, or write groomed content.

For groomed content: provide `groomed_content` for full replacement, or `section` + `content`
for incremental section update.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `selector` | `str` | required | Title substring, `#N`, bare number, or GitHub issue URL |
| `plan` | `str \| None` | `None` | Path to a plan file to attach |
| `status` | `str \| None` | `None` | Set item status (e.g. `"in-progress"`) |
| `create_issue` | `bool` | `False` | Create a GitHub issue if the item lacks one (P0/P1 only) |
| `groomed_content` | `str \| None` | `None` | Full groomed content (replaces entire groomed section) |
| `section` | `str \| None` | `None` | Section name for incremental update (use with `content`) |
| `content` | `str \| None` | `None` | Content for the named section (use with `section`) |
| `title` | `str \| None` | `None` | New title — updates local file and GitHub issue title |
| `description` | `str \| None` | `None` | New description (local file only, no GitHub sync) |

Returns `{title, changes, messages, warnings}`.

### `backlog_groom`

Write groomed content into a backlog item and sync to its GitHub issue.
Emits progress messages via MCP context during execution.

Provide either `groomed_content` (full replacement) or `section` + `content` (incremental).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `selector` | `str` | required | Title substring, `#N`, bare number, or GitHub issue URL |
| `groomed_content` | `str \| None` | `None` | Full groomed content (replaces entire groomed section) |
| `section` | `str \| None` | `None` | Section name for incremental update |
| `content` | `str \| None` | `None` | Content for the named section |

Returns `{title, synced, messages, warnings}`.

Note — `--groomed-file` and stdin pipe patterns have no MCP equivalent. Provide content inline.

### `backlog_normalize`

Normalize all per-item files to research-style metadata format and remove body duplication.
One-off maintenance operation. Emits progress messages via MCP context during execution.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `dry_run` | `bool` | `False` | Preview changes without modifying files |

Returns `{updated, dry_run?, messages, warnings}`.

### `backlog_pull`

Pull issue body content from GitHub into local per-item files. Auto-migrates P0/P1 items
lacking GitHub Issues by creating them. Merges by section, keeping the longer version unless
`force=True`. Emits progress messages via MCP context during execution.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `selector` | `str \| None` | `None` | Pull a single item: title substring, `#N`, bare number, or GitHub issue URL |
| `dry_run` | `bool` | `False` | Preview changes without modifying local files |
| `force` | `bool` | `False` | Overwrite local content even if local version is newer or longer |

Returns `{pulled, messages, warnings}` for bulk pull; `{file_path, messages, warnings}` for single-item pull.

## Return Value Contract

All tools return a `dict`. Callers must handle both shapes:

```text
Error:   {"error": "<message>", "messages": [...], "warnings": [...]}
Success: {<result fields>, "messages": [...], "warnings": [...]}
```

Always check for the `"error"` key before consuming result fields. Log `messages` and `warnings`
when non-empty.

## CI/CLI Interface

GitHub Actions and environments without an MCP client use the CLI script. This is the only
context where `uv run` invocations of `backlog.py` are appropriate.

```bash
uv run .claude/skills/backlog/scripts/backlog.py <subcommand> [options]
```

Available subcommands mirror the MCP tools: `add`, `list`, `view`, `sync`, `close`, `resolve`,
`update`, `groom`, `normalize`, `pull`.

## Environment

- `GITHUB_TOKEN` — Required for all GitHub issue operations (`add`, `sync`, `close`, `resolve`,
  `update --create-issue`, `pull`). Set in environment before invoking MCP tools or the CLI.

## Integration

- `/create-backlog-item` — calls `mcp__backlog__backlog_add` to create per-item files and issues
- `/work-backlog-item` — calls `backlog_list`, `backlog_view`, `backlog_close`, `backlog_resolve`,
  `backlog_update`
- `/groom-backlog-item` — calls `backlog_groom` and `backlog_update` for groomed content
- `/group-items-to-milestone` — calls `backlog_list` to enumerate items for milestone grouping
- **GitHub Action** — invokes `backlog sync` (CLI) on `.claude/backlog/` changes

Do not edit `.claude/backlog/*.md` files directly or use `gh issue edit` — both bypass sync logic.
If the MCP tools or CLI lack a needed operation, invoke `/backlog-tools-administrator` to close
the gap.
