---
name: backlog
description: Use when structured backlog operations are needed through MCP or the provider-neutral CLI. For Beads-native issue and dependency work, use bd directly.
---

# Backlog

<sam_cli>
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py"
</sam_cli>

The `references/mcp-connection-check.md` file loaded by this skill is a plain file, not
substituted — it shows bare SAM CLI subcommands and args only (e.g. `plan list`), never the
invocation prefix. Prepend the command in <sam_cli/> above to every one of them. `README.md`'s CLI
equivalents follow the same convention.

MCP tools are the primary structured interface for provider-neutral backlog operations. They are not a universal proxy for backend-native tools.
The selected backend provider is authoritative; `~/.dh/projects/{slug}/backlog/` per-item files are the local cache or working state according to that backend.
For Beads-backed projects, use `bd` directly for issue creation, inspection, status, dependencies, readiness, labels, notes, and metadata. Use MCP or the CLI for structured plans, artifacts, dispatch, validation, and other operations Beads does not provide. Do not edit derived per-item files directly.

## Primary Interface (MCP)

**Server availability**: If any `mcp__plugin_dh_backlog__*` tool is unavailable, see [mcp-connection-check.md](./references/mcp-connection-check.md) for troubleshooting. In normal operation Claude Code handles server connection waiting automatically (no manual retry needed).

All 12 tools return a `dict`. On error the dict contains an `"error"` key. On success it
contains result data keys plus `messages: list[str]` and `warnings: list[str]` (always present,
may be empty). Always check for `"error"` before consuming result fields.

The MCP tool name prefix is `mcp__plugin_dh_backlog__` followed by the tool name below.

### `backlog_add`

Create a new backlog item and a GitHub issue.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `title` | `str` | required | Item title |
| `priority` | `str` | required | `P0`, `P1`, `P2`, or `Ideas` |
| `description` | `str` | required | Item description |
| `source` | `str` | `"Not specified"` | Where this item came from |
| `type` | `str` | `"Feature"` | `Feature`, `Bug`, `Refactor`, `Docs`, or `Chore` |
| `force` | `bool` | `False` | Skip fuzzy duplicate check |

Returns `{filepath, filename, title, priority, issue_num?, messages, warnings}`.

Note — `research_first` has no MCP equivalent. Embed research questions in `description`.

### `backlog_list`

List open backlog items with optional filters.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `from_github` | `bool` | `False` | Refresh local cache from GitHub before listing |
| `label` | `str \| None` | `None` | Filter by GitHub label (e.g. `"priority:p1"`) |
| `section` | `str \| None` | `None` | Filter by priority section: `P0`, `P1`, `P2`, or `Ideas` |
| `status` | `str \| None` | `None` | Filter by status (e.g. `"needs-grooming"`, `"status:in-progress"`) |
| `title` | `str \| None` | `None` | Filter by title substring (case-insensitive) |
| `type` | `str \| None` | `None` | Filter by metadata.type — case-insensitive exact match (e.g. `"Bug"`, `"Feature"`). Items without metadata.type are excluded when active. |
| `topic` | `str \| None` | `None` | Filter by metadata.topic — case-insensitive substring match. Items without metadata.topic are excluded when active. |
| `include_closed` | `bool` | `False` | Include items with closed/done/resolved status (excluded by default) |
| `search` | `str \| None` | `None` | Full-text search across title, section, topic, and type simultaneously. Supports OR/AND operators (e.g. `"auth OR deploy"`), regex patterns (`/pattern/` or `regex:pattern`), field-specific search (`title:auth`, `type:bug`, `topic:devops`, `section:P1`), and plain case-insensitive substring matching. OR/AND are whitespace-delimited and case-insensitive. Mixed AND/OR in a single query is not supported; AND takes precedence. Combine with other filters to narrow results further. |
| `offset` | `int` | `0` | Skip the first N items from the filtered result set (for pagination) |
| `limit` | `int` | `0` | Maximum items to return. `0` = auto-paginate within 4400 token budget (cl100k_base). When `has_more=true` in the response, call again with the `offset` from `next_call`. |

Every response item includes `state` (open/closed) and `status` (workflow status from `status:*` labels).
Returns `{items: [{title, priority, issue, plan, state, status, milestone}], backend: {...}, messages, warnings}`.

The backend dict is always present. It reports availability from the selected backend provider;
the status is reported on every call regardless of the refresh parameter. No automatic sync is triggered.

| `backend` field | Type | Description |
|----------------|------|-------------|
| `name` | `str` | Selected backend provider name |
| `availability` | `str` | `"reachable"` \| `"not_checked"` \| `"needs_authentication"` \| `"rate_limited"` \| `"error"` |
| `open_count` | `int` | Live open issue count (0 when not reachable) |
| `total_count` | `int` | Live total issue count (0 when not reachable) |
| `cache_open_count` | `int` | Open count from local cache, same filters as `items` |
| `cache_total_count` | `int` | Total count from local cache |
| `last_sync` | `str` | ISO timestamp of most recent sync, empty string if never synced |
| `error` | `str` | Error detail when availability is not `"reachable"`, otherwise `""` |

Note — the CLI has no selectable format flag; compact JSON is always emitted and has no MCP equivalent. MCP tools always return
structured dicts (equivalent to JSON). Use `backlog_view` for detailed single-item output.

### `backlog_view`

View a single backlog item in detail. Supports pagination for long bodies.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `selector` | `str` | required | GitHub issue URL, `#N`, bare number, or title substring |
| `include_content` | `bool` | `True` | When True (default), returns full body and section entries. When False, returns metadata and section inventory only (section names with entry counts, no body or entry content). |
| `offset` | `int` | `0` | Skip N entry blocks from body start (for pagination) |
| `limit` | `int` | `0` | Show at most N entry blocks (`0` = all, no truncation) |

Returns `{title, priority, issue, plan, file_path, body, groomed, messages, warnings}` when
`include_content=True` (default). When `include_content=False`, returns compact metadata:
`{title, priority, issue, plan, file_path, groomed, sections_metadata, messages, warnings}` where
`sections_metadata` is a list of `{name, num_entries, num_struck}` dicts — no `body` or `sections` keys.

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

### `backlog_list_comments`

List comments on a GitHub issue with pagination. Returns a `preview` (first 200 characters)
per comment — use `backlog_read_comment` to fetch the full body of a specific comment.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `issue_number` | `int` | required | GitHub issue number (without `#`) |
| `limit` | `int` | `20` | Maximum comments to return |
| `offset` | `int` | `0` | Number of comments to skip (for pagination) |

Returns `{comments: [{id, author, created_at, updated_at, preview}], count, has_more, messages, warnings}`.

When `has_more=True`, call again with `offset += limit` to retrieve the next page.

### `backlog_read_comment`

Read the full body of a single comment. The `id` field from `backlog_list_comments` is the
integer REST comment ID to pass here.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `issue_number` | `int` | required | GitHub issue number (without `#`) |
| `comment_id` | `int` | required | REST comment database ID (integer from `backlog_list_comments`) |

Returns `{id, author, created_at, updated_at, body, messages, warnings}`.

`body` is the full Markdown comment — no truncation.

## Return Value Contract

All tools return a `dict`. Callers must handle both shapes:

```text
Error:   {"error": "<message>", "messages": [...], "warnings": [...]}
Success: {<result fields>, "messages": [...], "warnings": [...]}
```

Always check for the `"error"` key before consuming result fields. Log `messages` and `warnings`
when non-empty.

## CI/CLI Interface

GitHub Actions and environments without an MCP client use `fastmcp call` against the MCP server.

```bash
uv run fastmcp call plugins/development-harness/.mcp.json <tool_name> [key=value ...]
```

The CLI exposes the provider-neutral `sam backlog` domain group. Its 26 leaves are:

`add`, `list`, `view`, `update`, `close`, `resolve`, `link-followup`, `list-followups`, `groom`, `sync`, `pull`, `pull-all`, `normalize`, `strike`, `refresh`, `labels`, `merged-prs`, `milestones`, `soonest-milestone`, `create-milestone`, `issues`, `comment-issue`, `comments`, `read-comment`, `projects`, and `create-project`.

Use them as `uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" backlog <leaf>`. The CLI does not select a provider; backend selection is resolved from project configuration. The full, authoritative CLI-vs-MCP capability list is in [backend-providers.md](../../docs/backend-providers.md) "CLI vs MCP Capability Surface".

## Environment

- `GITHUB_TOKEN` — Required when the selected backend provider is GitHub and the operation reaches
  GitHub APIs. Set it in the environment before invoking those MCP tools or CLI operations.

## Integration

- `/create-backlog-item` — calls `mcp__plugin_dh_backlog__backlog_add` to create per-item files and issues
- `/work-backlog-item` — calls `backlog_list`, `backlog_view`, `backlog_close`, `backlog_resolve`,
  `backlog_update`
- `/groom-backlog-item` — calls `backlog_groom` and `backlog_update` for groomed content
- `/group-items-to-milestone` — calls `backlog_list` to enumerate items for milestone grouping
- **GitHub Action** — invokes `fastmcp call backlog_sync` on `~/.dh/projects/{slug}/backlog/` changes

Do not edit `~/.dh/projects/{slug}/backlog/*.md` files directly or use `gh issue edit` — both bypass sync logic. Use `backlog_update` MCP tool for all item modifications.
If the MCP tools or CLI lack a needed operation, invoke `/backlog-tools-administrator` to close
the gap.
