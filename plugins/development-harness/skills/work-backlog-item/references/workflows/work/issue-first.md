# Issue-First Path (Step 1.2)

**Trigger:** <mode/> matches `#[0-9]+`, is a bare number, or is a GitHub issue URL (`https://github.com/.../issues/N`).

Fetch the issue using the `mcp__plugin_dh_backlog__backlog_view` tool (accepts URLs, `#N`, and bare numbers):

Call the `mcp__plugin_dh_backlog__backlog_view` tool with `selector="<mode/>"`.

If the tool returns a dict with an `error` key, report and stop.
If `state` is `closed`, run the **Completed Issue Discovery** procedure below and stop.

From the JSON response build the working item:

| Field | Source |
|---|---|
| `title` | `title` |
| `description` | `body` (full text) |
| `source` | `"GitHub Issue #N"` |
| `priority` | `priority` field (extracted from `priority:*` label) |
| `status` | `status` field (extracted from `status:*` label — canonical) |
| `milestone` | `milestone` |
| `plan` | `plan` field, or search `body` for `**Plan**:` line |

The `backlog_view` MCP tool operates in two modes depending on GitHub reachability (architect spec §5.2, ADR-002):

- **Connected**: sections and `sections_index` are derived from the live GitHub issue body (takes priority over local cache)
- **Offline**: sections and `sections_index` are derived from local YAML cache; the response `warnings` field contains `"backend unreachable"` indicating potentially stale data

All fields needed for subsequent steps are available in the response — do not read local files directly.

Note: The issue-first path skips Steps 2.1–2.3 because the item is resolved via GitHub Issue
number — it already has an issue (skips 2.2–2.3) and the `backlog_view` response includes
closed-state detection (substitutes 2.1). Proceed directly to Step 2.4.

---

## Completed Issue Discovery

When an issue is found to be already closed (`state: closed`), gather evidence before closing the local backlog item:

1. **Search for commits referencing the issue**:

   ```bash
   git log --oneline --all -20 --grep="#N"
   ```

2. **Search for merged PRs via git history**:

   ```bash
   git log --oneline --all -20 --grep="Fixes #N\|Closes #N"
   ```

3. **Report findings**:

   If commits or PRs are found:

   ```text
   Issue #{N} is already closed.

   Evidence of completion:
   - PR #{pr}: {title} (merged {date})
     URL: {url}
   - Commit {sha}: {message}

   Closing local backlog item with evidence.
   ```

   Call the `mcp__plugin_dh_backlog__backlog_resolve` tool with `selector="{title}"` and
   `summary="Completed via PR #{pr} / commit {sha}"`.

   If no commits or PRs reference the issue:

   ```text
   Issue #{N} is already closed but no commits or PRs reference it.
   The issue may have been closed manually or via external process.

   Options:
   - close: Close the local backlog item (with manual reason)
   - resolve: Mark as no longer applicable
   - reopen: If the work was not actually done, reopen the issue
   ```

   Use `AskUserQuestion` to ask which action to take. When <mode/> is `auto`, log
   `[AUTO] STOP — Issue #N closed, no commit/PR evidence found` and stop.
