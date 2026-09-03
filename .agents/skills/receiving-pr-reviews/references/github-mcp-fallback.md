# GitHub MCP fallback

Use this path only when the bundled helper cannot use `gh` and GitHub MCP tools are available. Preserve the main workflow's decisions and stopping conditions; this is a transport fallback, not a different review policy.

## Fetch one snapshot

Batch the independent read calls concurrently when the host permits it. Use the available tools whose names end with:

- `github_get_pr_info` for state, draft status, mergeability, base, and exact head;
- `github_list_pull_request_review_threads` for every thread and its resolved state;
- `github_list_pull_request_reviews` for every submitted review and body;
- `github_fetch_issue_comments` for PR-level responses;
- `github_get_pr_reactions` for Codex's `+1` approval reaction;
- `github_get_user_login` only when the authenticated comment author cannot otherwise be identified.

Derive the same summary as `fetch --summary`:

- `reviews_count`: all submitted reviews;
- `threads_count`: all inline threads;
- `unresolved`: every thread where `is_resolved` is false, and `unresolved_count` is its length;
- `blockers`: closed or draft PR state, merge conflicts, or another explicit reviewability blocker. Treat unknown/pending mergeability as non-blocking;
- `reviews_with_body`: submitted reviews with non-empty top-level bodies;
- `unresponded_reviews`: each `reviews_with_body` entry not covered by the response rule below;
- `codex_approved`: a current-revision Codex `+1` as defined below.

Do not treat counts from only one endpoint as the complete snapshot.

### Unresponded reviews

Exclude Codex's exact fixed no-findings review wrapper; real Codex findings arrive as inline threads. Every other non-empty submitted review remains unresponded until a later PR-level comment by the authenticated user quotes that review's exact permalink. If the normalized review result lacks its permalink or timestamps, call `github_fetch_pr_comments` only for those missing fields. A response must postdate the later of the review's submission and edit timestamps.

### Codex approval

A `+1` counts only when its author is the exact Codex bot account and its timestamp is not older than the current head revision. When a Codex `+1` exists, use the general GitHub fetch tool to check the head commit timestamp and the latest force-push event; require the reaction to postdate both. Do not carry approval forward from an older revision.

## Reply and resolve

Keep the main workflow's validate-before-fix and push-before-reply rules.

- Reply to an inline thread with `github_reply_to_review_comment`, targeting the first comment's numeric database ID.
- Resolve it with `github_resolve_review_thread`, using the thread node ID.
- Respond to a top-level review with `github_add_comment_to_issue` on the PR. Include the review's exact permalink so the next snapshot clears it from `unresponded_reviews`.

Use the connector's equivalent tool when its exposed prefix differs; do not broaden beyond the current repository and PR.

## Watch

Re-run the same lightweight snapshot on a bounded short polling schedule. Stop and restart the main workflow when an unresolved thread or unresponded review appears. With neither present, `codex_approved: true` is completion. If no work and no approval appear during one window, begin another window only when the intended watch period has not yet been covered. Re-check blockers on every snapshot.
