---
name: receiving-pr-reviews
description: Work through every unresolved review thread on a PR to completion — validate, fix if warranted, reply, resolve, then re-check on a bounded schedule. Use after pushing a commit to a PR, or when asked to check or address PR reviews.
---

# Receiving PR Reviews

<workflow>

1. Fetch every unresolved thread and every review with a top-level body, filtered before the result reaches context — one command, auto-paginated so a PR with hundreds of threads or reviews is never silently truncated:

   ```bash
   uv run ./.agents/skills/receiving-pr-reviews/scripts/pr_review_threads.py fetch --pr <N>
   ```

   `reviews_count` and `threads_count` are the totals actually found — a `threads_count` of 0 means no *inline review threads* landed, not that no review landed at all: a top-level approval or `COMMENTED` review with no inline comment produces `reviews_count > 0` with `threads_count: 0`, and its content surfaces only through `reviews_with_body` below. A nonzero `threads_count` with `unresolved_count: 0` means every thread found was already resolved. Never treat an empty `unresolved` array as "nothing to do" without checking `reviews_count`, `threads_count`, and `unresolved_count` together. Each unresolved thread carries its own `id` (for resolving, step 5) and each comment's `databaseId` (for replying, step 4) — no separate lookup needed. A thread's `comments_truncated: true` means that single thread alone has passed 100 comments in its own back-and-forth (rare, but real content is missing) — page that thread's `comments` connection directly before concluding anything about it. `reviews_with_body` surfaces reviews whose feedback lives in the review's own summary text rather than an inline comment (an approval note, or general feedback with no line-level comment) — these have no thread at all and are otherwise invisible even when `unresolved_count` is 0; treat each as actionable input too.
2. For each unresolved thread or review body: read it, validate the claim locally, assess against the change goal and repository instructions.
3. Implement, commit, and push a fix only when it improves the product — push before replying, so the SHA named in the reply is inspectable and resolving the thread never outruns what is actually on the remote.
4. Reply on that thread with the disposition — conclusion, evidence, commit SHA, or why no change was warranted:

   ```bash
   uv run ./.agents/skills/receiving-pr-reviews/scripts/pr_review_threads.py reply --pr <N> --comment-id <databaseId> --body '...'
   ```
5. Resolve the thread:

   ```bash
   uv run ./.agents/skills/receiving-pr-reviews/scripts/pr_review_threads.py resolve --thread-id <id>
   ```
6. A decision spanning threads (PR sequencing, rebase disposition) goes on the PR itself via `gh pr comment <N> -R <owner>/<repo>` — the same owner/repo this run selected in step 1 (default `Jamie-BitFlight/claude_skills`), not a different repository — before the work it governs.
7. Once all current threads are resolved, re-check for new reviews using the `watch` subcommand, in a loop of short calls rather than one long block — each call blocks for only its own default timeout (270s) and returns as soon as new activity appears or that call's own timeout elapses:

   ```bash
   uv run ./.agents/skills/receiving-pr-reviews/scripts/pr_review_threads.py watch --pr <N>
   ```

   Run it inline and block directly when there is no other work to advance right now. If other work is queued, run this call in the background using whatever backgrounding mechanism the current harness provides (a background-execution tool parameter, or a poll-by-session-id pattern) and continue that work instead — then, before reporting back or finishing, check the backgrounded call's own result yourself rather than waiting for a completion notification (see the gotcha below).

   Read each call's result the same way: `timed_out: false` means `new_thread_ids` or `new_reviews_with_body` is non-empty — stop the loop and restart this skill from step 1 against that new activity. `timed_out: true` means nothing new turned up inside that one call's window, not that watching is done — issue another `watch` call immediately to continue covering the total window you intend to watch for (each call's own baseline fetch picks up exactly where the previous call's left off, so consecutive calls never miss activity in between). Stop looping once new activity appears or once you've covered the total watching window you intend to cover. A Codex thumbs-up with no comment, or an explicit "no reviews"/"no changes"/"0 comments" response, is that reviewer's completion signal and does not itself count as new activity.

</workflow>

<gotchas>

- All commands default `--owner`/`--repo` to this checkout's own `Jamie-BitFlight`/`claude_skills`; pass them explicitly to target a different repository.
- `reply`'s `<comment_id>` is a comment's `databaseId` from step 1 (verified identical to the REST comment `id`). `resolve`'s `<id>` is a thread's `id` from step 1, not a comment id. A thread's `comments` array is in creation order — when a thread has more than one comment (a prior reply already landed on it), pass the first comment's `databaseId`, not a later one: GitHub's reply endpoint requires the top-level review comment and rejects a reply targeted at another reply.
- A `reviews_with_body` entry has no `id`/`databaseId` at all — it's not a thread and can't be replied to or resolved through this script. Address it (fix, or note why not) and, if a response belongs on the PR itself, use `gh pr comment` per step 6.
- The script shells out to `gh` and relies on `gh`'s own authentication — it does not talk to the GitHub API directly and does not read or need a token itself.
- `watch`'s defaults (90-second poll interval, 270-second total timeout per call) stay under the 5-minute prompt-cache TTL floor that applies in every Claude billing mode, so one call's turn always lands inside cache. Cover a longer watching window by looping short `watch` calls (step 7), not by raising `--timeout-seconds` — raising it narrows or removes that safety margin.
- `watch` detects new activity by diffing against the snapshot taken when the call started — a thread `id` absent from that first snapshot, or a `reviews_with_body` entry (compared by full author/state/body content, since reviews carry no id) absent from it. A review whose text or state changes after the call starts counts as new activity even if the same reviewer already had a `reviews_with_body` entry in the baseline.
- A backgrounded `watch` call produces no completion notification when it finishes, even though it keeps running after its dispatcher returns — poll for its own result directly before reporting back or finishing.
- `watch`'s baseline is its own first fetch, taken when the call starts — a thread or review body that appears in the narrow window before that first fetch (after step 5's last `resolve`, or between two consecutive `watch` calls) is folded into the baseline and never shows up in `new_thread_ids`/`new_reviews_with_body`. Both still show up in `state` on every subsequent result, though: read `state.unresolved_count` and `state.reviews_with_body` on every `watch` result, including a `timed_out: true` one, the same way step 1 requires reading them on `fetch` — do not rely on `new_thread_ids`/`new_reviews_with_body` alone to conclude nothing is outstanding.
- A `timed_out: true` result is only ever printed once at least one check since the baseline fetch actually succeeded (or the window ended before any re-poll was even attempted, which is honest — nothing to check again yet). If every re-poll this window attempted fails (a run of transient `gh` errors), `watch` exits non-zero with nothing on stdout instead of printing a `timed_out: true` result — a caller that only checks for a zero exit code and JSON on stdout will not mistake an unchecked window for a confirmed-clean one. Retry the `watch` call rather than treating the failure as "nothing new."

</gotchas>
