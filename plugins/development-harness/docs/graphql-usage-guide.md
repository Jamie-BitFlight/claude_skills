# GraphQL Usage Guide — Backlog MCP Sync

Reference for implementers and agent authors working with GitHub issue fetching in the backlog MCP server.

## Entry Point: `sync_issues_graphql`

`sync_issues_graphql` in `backlog_core/gh_client.py` is the **only function to call for bulk issue fetching**. It handles cursor pagination, callback dispatch, and optional timestamp tracking internally.

Do not call `_fetch_issues_graphql` directly — it is an internal primitive called by `sync_issues_graphql`. Calling it directly bypasses pagination, callback dispatch, and timestamp tracking.

## Parameters

| Parameter | Type | Purpose |
|-----------|------|---------|
| `repo` | `github.Repository` | PyGithub repo object |
| `owner` | `str` | GitHub org or user name |
| `repo_name` | `str` | Repository name |
| `state` | `str` | `"open"`, `"closed"`, or `"all"` |
| `labels` | `list[str]` | Filter by label names (AND match) |
| `milestone_number` | `int \| None` | Filter by milestone; `None` = no filter |
| `since` | `str \| None` | ISO 8601 DateTime; returns only issues updated after this time |
| `callback` | `Callable[[dict], None] \| None` | Called once per issue as it arrives |
| `track_timestamp` | `bool` | Read/write `.last_sync` file for stateful incremental sync |

## Incremental Sync via `since`

Passing a `since` value (ISO 8601 DateTime string) instructs GitHub's GraphQL API to return only issues updated after that point. Typical performance:

- Full scan (no `since`): ~12s for 245 issues across 3 pages
- Incremental sync (recent `since`): ~0.7s

When `track_timestamp=True`, the function reads the timestamp from a `.last_sync` file before fetching and writes the new timestamp on success. This makes repeated calls automatically incremental without the caller managing timestamps.

```text
First call  (no .last_sync): full scan, writes .last_sync
Second call (.last_sync exists): incremental scan from that timestamp
```

## Per-Issue Callbacks

Pass a `callback` to process each issue as it arrives instead of accumulating all issues in memory then looping. This avoids building a large in-memory list before processing.

```text
# Preferred: callback processes each issue during fetch
sync_issues_graphql(..., callback=my_handler, ...)

# Avoid: fetch all, then loop — see Anti-Patterns below
issues = sync_issues_graphql(...)
for issue in issues: process(issue)
```

## Must-Stay-REST Operations

Two operations have no GraphQL mutation equivalent and remain on REST permanently (ADR-004):

- `create_milestone` — uses PyGithub REST
- `create_label` — uses PyGithub REST

Do not attempt to rewrite these as GraphQL mutations. When ADR-004 is revisited, update this document first.

## Cursor Pagination vs. GitLab Batch Aliases

GitHub's GraphQL API uses cursor-based pagination with `first: 100` and `endCursor`. This is the mechanism `_fetch_issues_graphql` uses internally — each page fetches up to 100 issues and advances via cursor until `hasNextPage` is false.

This differs from the GitLab aliased batch query pattern (used in the `jira-release-notes-ai` reference implementation) where multiple named aliases execute in a single request with per-alias complexity budgeting (~10 items per alias, ~19 complexity per item, 250 total limit). GitHub does not use this pattern.

## Anti-Patterns

**N+1 fetch loop** — do not call a per-issue fetch inside a loop over issues:

```text
# Wrong: one GraphQL request per issue
for issue_number in issue_numbers:
    fetch_single_issue(issue_number)  # N+1 requests

# Correct: one paginated bulk fetch
sync_issues_graphql(..., callback=process_issue, ...)
```

**Ignoring `since` when a timestamp exists** — always pass a `since` value when one is available. Performing a full scan on every call when `.last_sync` exists wastes ~12s per call and increases API quota consumption.

**Duplicating fetch-process-track logic** — use `track_timestamp=True` instead of manually reading/writing `.last_sync` around a `sync_issues_graphql` call. Duplicating this logic creates divergence when the timestamp format or file path changes.

**Calling `_fetch_issues_graphql` directly** — it fetches a single page and returns a raw response. It does not paginate, does not call callbacks, and does not track timestamps. Its only valid caller is `sync_issues_graphql`.

## Performance Reference

| Mode | Issues fetched | Pages | Duration |
|------|---------------|-------|----------|
| Full sync | 245 | 3 | ~12.4s |
| Incremental sync | varies | 1 (typical) | ~0.69s |

SOURCE: Observed during GraphQL migration (issues #916, #1018, #1020), 2026-03-22.

## References

- `backlog_core/gh_client.py` — `sync_issues_graphql` and `_fetch_issues_graphql` implementation
- `backlog_core/operations.py` — callers of `sync_issues_graphql`
- `backlog_core/server.py` — MCP tool wrappers
- [backend-providers.md](./backend-providers.md) — GitHub backend architecture and ADR-004 reference
- [backlog-lifecycle.draft.md](./backlog-lifecycle.draft.md) — full sync lifecycle and state machine
