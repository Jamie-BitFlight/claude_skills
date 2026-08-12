# Backlog Sync and Pull Trace

> **Audience: contributor/developer.** This is a historical implementation trace and target-boundary
> handoff, not consumer setup or usage guidance.

Date: 2026-08-12

## Scope and evidence

This report traces the GitHub-backed backlog paths used by the live E2E test and the source at the failing run's SHA `6a75caf17c4c739e5bfd007e5aa7b2f1b31af702`. The six traced files have no diff between that SHA and the current checkout. It distinguishes observed behaviour from the requested target design. It does not attribute network latency to a particular external service because no request-level timing trace was captured.

Evidence consulted:

- `plugins/development-harness/tests/helpers.py`
- `plugins/development-harness/tests/test_live_validation.py`
- `plugins/development-harness/backlog_core/server.py`
- `plugins/development-harness/backlog_core/sync_engine.py`
- `plugins/development-harness/backlog_core/operations.py`
- `plugins/development-harness/backlog_core/gh_client.py`
- GitHub Actions run `31546987899`
- A read-only GitHub GraphQL `totalCount` query on 2026-08-12.

## Ownership boundary

The observations below describe the legacy implementation at the recorded SHA. In the accepted
target architecture, the selected remote-capable backend privately owns `FileCache`, cache records,
checkpoints, the durable idempotent pending-mutation queue, and partial-replay retention. The
reconciliation engine remains pure policy: it classifies and merges snapshots and returns actions;
the backend applies those actions through its private cache. Beads, SQLite, and Memory use native
storage only and never read backlog YAML or instantiate `FileCache`.

## Observed result

The main CI run `31546987899` at SHA `6a75caf17c4c739e5bfd007e5aa7b2f1b31af702` failed only in `Python / E2E live tests`. The job started at `23:34:28Z`, the E2E command step started at `23:34:39Z`, pytest first emitted session output at `23:34:56Z`, L8 completed at `23:41:11Z`, and the job timed out at `23:44:51Z`. L2 failed before L8; L9 did not emit a completion line before timeout. The research-validation job, regular Python tests, and Quality Gate succeeded in that run.

The repository had 368 open and 1,888 closed GitHub issues when counted on 2026-08-12: 2,256 total. The counts are repository-wide, not the number of items created by the E2E fixture.

## Observed data flow

### One live-test tool call

`call_mcp_tool()` creates and closes a new in-memory FastMCP `Client` for every `_call` ([helpers.py](../plugins/development-harness/tests/helpers.py#L21-L39)). The live lifecycle uses `_call` for each L1 through L11 step ([test_live_validation.py](../plugins/development-harness/tests/test_live_validation.py#L214-L343)).

The server lifespan starts a background sync only when startup sync is enabled and `SyncState.try_start()` acquires the shared sync slot. Enabled is the default when no configuration value is present ([server.py](../plugins/development-harness/backlog_core/server.py#L1517-L1531)); a second lifespan while the state is `RUNNING` reuses the active task rather than creating another ([server.py](../plugins/development-harness/backlog_core/server.py#L1534-L1573); [sync_state.py](../plugins/development-harness/backlog_core/sync_state.py#L117-L133)).

The sync loop runs `refresh_local_cache_from_github()` in `asyncio.to_thread` ([sync_engine.py](../plugins/development-harness/backlog_core/sync_engine.py#L92-L111)). Lifespan teardown cancels and waits for the asyncio task for up to five seconds ([server.py](../plugins/development-harness/backlog_core/server.py#L1564-L1573)). The report establishes that the remote refresh work is executed in a worker thread; it does not establish the completion time of any individual cancelled worker-thread call.

### Cache refresh

`refresh_local_cache_from_github()` reads `.last_sync` from the legacy state root. If the file is absent it calls `_sync_full`; if present it calls `_sync_incremental`; and it writes `.last_sync` after the fetch ([operations.py](../plugins/development-harness/backlog_core/operations.py#L2256-L2327)). The target backend owns this checkpoint through its private `FileCache`. The live fixture sets a fresh `DH_STATE_HOME` ([test_live_validation.py](../plugins/development-harness/tests/test_live_validation.py#L90-L105)), so the first refresh in that fixture has no pre-existing `.last_sync`.

`_sync_full` fetches open issues, writes their cache records, and then calls closed-issue reconciliation ([operations.py](../plugins/development-harness/backlog_core/operations.py#L2208-L2253)). The GraphQL list function fetches 100 issue nodes per request and follows `endCursor` in a loop ([gh_client.py](../plugins/development-harness/backlog_core/gh_client.py#L564-L627)). Its query includes each issue's ID, number, title, state, body, timestamps, labels, milestone, and assignees ([gh_client.py](../plugins/development-harness/backlog_core/gh_client.py#L184-L207)).

At the observed repository counts, a full refresh requires at least four open-issue pages and nineteen closed-issue pages. The implementation issues those pages serially because the next request's cursor is read from the preceding response. The source does not issue parallel page requests. Closed-issue reconciliation fetches all closed issues and applies its cutoff only after retrieval ([operations.py](../plugins/development-harness/backlog_core/operations.py#L2096-L2149)).

### Explicit `backlog_sync`

`sync_push_groomed_content()` collects locally groomed items, bulk-fetches all open issue nodes when no list was supplied, maps them by issue number, renders an updated issue body for every matched groomed item, then dispatches the generated updates ([operations.py](../plugins/development-harness/backlog_core/operations.py#L3828-L3905); [operations.py](../plugins/development-harness/backlog_core/operations.py#L3750-L3792)). In the observed source, `_build_groomed_update_list()` appends the rendered update without a body-equality check against the fetched body.

For the GitHub backend, body updates are grouped into GraphQL requests of at most 25 aliased `updateIssue` mutations ([gh_client.py](../plugins/development-harness/backlog_core/gh_client.py#L780-L824)). A failed batch falls back to individual mutations for that batch. The batch capability is enabled for the GitHub backend ([github_backend.py](../plugins/development-harness/backlog_core/backends/github_backend.py#L49-L56)).

### Explicit bulk `backlog_pull`

`pull_items()` parses local items, selects every item with an issue reference, obtains a repository object, and calls `_pull_item()` once for each candidate ([operations.py](../plugins/development-harness/backlog_core/operations.py#L4821-L4883)). `_pull_item()` calls `fetch_github_issue_body()` before its local merge/write logic ([operations.py](../plugins/development-harness/backlog_core/operations.py#L1707-L1743)). The single-issue GraphQL helper executes one issue-by-number GraphQL request ([gh_client.py](../plugins/development-harness/backlog_core/gh_client.py#L540-L561)).

Therefore, bulk `backlog_pull` does not use the existing paginated issue-list primitive. It has one issue-body request per selected local item.

## Comparison with the requested design

| Requested property | Observed implementation |
| --- | --- |
| Fetch a provider snapshot containing issue text, state, and labels | The GraphQL list query has all of these fields. Cache refresh and groomed-content sync use it; bulk pull does not. |
| Paginate provider data in batches of 100 | The list primitive uses `first: 100`. It follows cursor pages serially. |
| Compare the snapshot with local state before changing either side | Cache refresh writes fetched open records. Groomed-content sync builds updates for matched groomed items without a body-equality check. Bulk pull fetches and merges one item at a time. |
| Push only the local changes that require an upstream patch | GitHub body mutations are batched in groups of 25, but the current groomed-content builder does not first omit equal bodies. |
| Keep lifecycle test steps but avoid an unnecessary full production-repository refresh | Each `_call` creates a client lifespan; startup sync defaults to enabled; the fixture uses a fresh state root. A shared `SyncState` permits at most one running startup task, so this trace does not establish one full refresh per call. |
| Treat provider implementations agnostically | The current operation layer uses `GitHubExtras` for bulk listing and body access, while `pull_items()` obtains a GitHub repository directly. The existing batch mutation implementation is GitHub-specific. |

## Proposed target design

The accepted target model is a reconciliation pass with these stages:

1. Obtain a provider snapshot of item identity, text, state, labels, and provider timestamps, using the provider's highest practical page size and a defined high-water mark or deduplication rule.
2. The selected backend loads its native records or, for a remote provider, records from its private `FileCache`.
3. Compare the two snapshots locally and form a directional patch set: local-cache updates and provider updates.
4. Apply only the provider patches whose local record is newer or whose reconciled content differs according to the chosen conflict rule.
5. The selected backend persists provider snapshots and reconciliation watermarks through its private `FileCache` only
   after the relevant operations complete; local providers persist through native storage.

For backend agnosticism, the provider contract can describe snapshot retrieval, stable identity, revision/timestamp metadata, and patch application without requiring GraphQL. A GitHub backend can implement snapshot retrieval with GraphQL; another backend can use its own paginated API. Provider-specific batching remains behind the provider capability, while patch selection and conflict rules remain local and backend-neutral. Reaching that boundary requires replacing the current operation-layer `GitHubExtras` and direct repository dependencies.

## Facts not established by this trace

- The number of E2E cache-refresh threads that remained active at any individual lifecycle step.
- Per-request GitHub latency, GraphQL rate-limit state, or retry count.
- The number of startup synchronizations begun across the full E2E lifecycle; `SyncState.try_start()` prevents concurrent startup tasks but this trace did not record each state transition.
- A conflict-resolution rule for simultaneous local and provider edits was not specified at the traced SHA. The accepted
  target now uses the existing entry-aware merge and retains remote provider state and labels.

## Duplication and Ponytail review

An independent read-only review of the current clean worktree found no blocker in the exploratory repeated `MagicMock.full_name` setup shown during investigation: that edit is not present in the current source.

One production duplication is present. `_sync_incremental` uses `_reconcile_single_closed_issue()` ([operations.py](../plugins/development-harness/backlog_core/operations.py#L2064-L2093)), while `_reconcile_closed_issues()` repeats the local-file status-update sequence after its full-sync-specific cutoff and open-issue guards ([operations.py](../plugins/development-harness/backlog_core/operations.py#L2135-L2148)). The reviewer identified the smallest correction as keeping the full-sync-specific guards and calling the existing helper for the shared update.

The review found repeated `MagicMock` setup in refresh-related tests but classified it as low-impact readability debt. The closest helpers are private to other test modules; the root `mock_github` fixture patches unrelated operations and defaults `try_get_github` to `None`. The reviewer found no safe existing fixture to reuse without changing test semantics. A global fixture or broader test-fixture consolidation was therefore not recommended.

The reviewer ran `uv run pytest plugins/development-harness/tests/test_backlog_core_operations.py -k 'RefreshClosedIssueReconciliation or RefreshLocalCacheIncrementalSync or SyncIncrementalParseBacklogCallCount' -q`: `9 passed`.
