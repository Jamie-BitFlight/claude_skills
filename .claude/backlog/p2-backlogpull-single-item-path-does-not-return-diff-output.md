---
name: backlog_pull single-item path does not return diff output
description: The `backlog_pull` tool's single-item path (`pull_by_selector`) does not return diff output showing what changed when pulling a specific item from GitHub. The batch pull path does return diff information. The spec for the timestamped entry blocks feature (#583) intended that all pull operations surface a diff so callers can see exactly what entries were added or updated. The single-item path silently succeeds without indicating what changed.
metadata:
  topic: backlogpull-single-item-path-does-not-return-diff-output
  source: 'Spec gap discovered during #583 (Backlog MCP: Timestamped entry blocks) resolution — feature-researcher audit 2026-03-14'
  added: '2026-03-14'
  priority: P2
  type: Bug
  status: open
  issue: '#694'
  last_synced: '2026-03-14T04:50:34Z'
  groomed: '2026-03-14'
  plan: plan/tasks-694-backlog-pull-diff-gap.md
---

## Groomed (2026-03-14)

### Groomed

<div><sub>2026-03-14T04:50:34Z</sub>

### RT-ICA

**Goal**: `backlog_pull` with a `selector` argument surfaces diff output (when `diff=True`) matching what the bulk pull path returns.

**Reverse prerequisites**:

1. `pull_by_selector` must accept a `diff: bool` parameter — AVAILABLE (gap confirmed: function signature at operations.py:1869 has no `diff` param)
2. `pull_single_issue` must accept `diff_mode` and call `generate_diff` — AVAILABLE (gap confirmed: function at operations.py:1802 has no `diff_mode` param and never calls `generate_diff`)
3. `server.py backlog_pull` must forward `diff` to the single-item path — AVAILABLE (gap confirmed: server.py:454 calls `pull_by_selector` without forwarding `diff`)
4. The return dict from the single-item path must include a `diff` key when diff output exists — AVAILABLE (bulk path returns `result["diff"]` at operations.py:1962; single-item path returns only `file_path`)

**Decision**: APPROVED — all conditions are observable from codebase.

---

### Reproducibility

1. Start the backlog MCP server.
2. Call `backlog_pull(selector="#694", diff=True)` via the MCP tool.
3. Observe the returned dict: it contains only `file_path`, `messages`, and `warnings`. No `diff` key is present regardless of whether the local and remote content differ.
4. Call `backlog_pull(diff=True)` (bulk, no selector). Observe the returned dict: it contains a `diff` key with entry-level diff output when changes exist.

### Output / Evidence

- Single-item call returns `{"file_path": "...", "messages": [...], "warnings": [...]}` — no `diff` key.
- Bulk call returns `{"pulled": N, "diff": "...", "messages": [...], "warnings": [...]}` when `diff=True` and changes exist.
- The asymmetry is visible by comparing `operations.pull_by_selector` (returns `dict[str, str | list[str] | None]`, no diff) against `operations.pull_items` (returns dict with optional `"diff"` key).

### Priority

5/10 — Spec gap. Callers passing `diff=True` with a selector silently receive no diff. The parameter is accepted by the server but produces no effect on the single-item path. No data is lost or corrupted; the issue is missing feedback only.

### Impact

- Bottleneck: callers who rely on `diff=True` to audit what changed after a single-item pull receive no information.
- The `diff` parameter on `backlog_pull` is documented identically for both paths but behaves differently.

### Benefits

- Callers can see exactly which entry blocks were added or updated when pulling a single item, matching the behaviour they get from bulk pull.
- Closes the spec gap documented in #583 (Timestamped entry blocks feature).

### Expected Behavior

When `backlog_pull(selector="#N", diff=True)` is called and the GitHub issue body differs from the local cache, the returned dict includes a `diff` key whose value is the entry-level diff string. When there is no difference, the key is absent or empty. This matches the behaviour of the bulk path.

### Desired Structure

The single-item pull path (`pull_by_selector` + `pull_single_issue`) accepts `diff_mode: bool` and returns diff output in the same dict key (`"diff"`) as the bulk path when changes are detected. The `backlog_pull` MCP handler forwards the `diff` argument to the single-item path.

### Acceptance Criteria

1. `backlog_pull(selector="#N", diff=True)` returns a dict containing a `diff` key when local and remote content differ for that item.
2. `backlog_pull(selector="#N", diff=True)` returns a dict without a `diff` key (or with an empty value) when local and remote content are identical.
3. `backlog_pull(selector="#N", diff=False)` continues to return only `file_path`, `messages`, and `warnings` (no regression).
4. `backlog_pull(diff=True)` (bulk, no selector) behaviour is unchanged.

### Resources

| Type | Item |
|------|------|
| Prior work | `.claude/skills/backlog/backlog_core/operations.py` — `pull_by_selector` (line 1869), `pull_single_issue` (line 1802), `_pull_item_update_existing` (line 683), `pull_items` (line 1910) |
| Prior work | `.claude/skills/backlog/backlog_core/server.py` — `backlog_pull` handler (line 422) |
| Prior work | `.claude/skills/backlog/backlog_core/entry_blocks.py` — `generate_diff` function |

### Dependencies

- Depends on: None (standalone bug fix; #583 is already resolved and this is a follow-up spec gap)
- Blocks: None

### Effort

Small — three touch points in two files. `pull_by_selector` needs a `diff` parameter forwarded to `pull_single_issue`, which needs to call `generate_diff` when `diff_mode=True` and return the result. The server handler needs to pass `diff` to the single-item path. No new infrastructure required; the diff generation and return pattern already exists in the bulk path.
</div>