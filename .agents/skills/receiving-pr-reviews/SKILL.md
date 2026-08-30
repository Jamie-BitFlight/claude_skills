---
name: receiving-pr-reviews
description: Work through every unresolved review thread on a PR to completion — validate, fix if warranted, reply, resolve, then re-check on a bounded schedule. Use after pushing a commit to a PR, or when asked to check or address PR reviews.
---

# Receiving PR Reviews

<workflow>

1. Fetch every unresolved thread, every unresponded review, and Codex's approval state, filtered before the result reaches context — one command, auto-paginated so a PR with hundreds of threads or reviews is never silently truncated:

   ```bash
   uv run ./.agents/skills/receiving-pr-reviews/scripts/pr_review_threads.py fetch --pr <N>
   ```

   `reviews_count` and `threads_count` are the totals actually found — a `threads_count` of 0 means no *inline review threads* landed, not that no review landed at all: a top-level approval or `COMMENTED` review with no inline comment produces `reviews_count > 0` with `threads_count: 0`, and its content surfaces only through `reviews_with_body` below. A nonzero `threads_count` with `unresolved_count: 0` means every thread found was already resolved. Never treat an empty `unresolved` array as "nothing to do" without checking `reviews_count`, `threads_count`, and `unresolved_count` together. Each unresolved thread carries its own `id` (for resolving, step 5) and each comment's `databaseId` (for replying, step 4) — no separate lookup needed. A thread's `comments_truncated: true` means that single thread alone has passed 100 comments in its own back-and-forth (rare, but real content is missing) — page that thread's `comments` connection directly before concluding anything about it. `reviews_with_body` surfaces every review whose feedback lives in the review's own summary text rather than an inline comment (an approval note, or general feedback with no line-level comment) — these have no thread at all and are otherwise invisible even when `unresolved_count` is 0. `unresponded_reviews` narrows that list to the ones this run has not explicitly answered yet — a bodied review counts as responded-to only once a PR-level comment (posted via `gh pr comment`, step 6) both quotes that review's own `url` field and postdates it, so treat every entry still in `unresponded_reviews` as actionable input; a comment that merely postdates a review without quoting its `url` (an unrelated administrative note, for instance) does not clear it. `codex_approved` is `true` when Codex's own thumbs-up reaction is currently on the PR (see the `watch` step below for what it means as a stop condition).
2. For each unresolved thread or unresponded review: read it, validate the claim locally, assess against the change goal and repository instructions.
3. Implement, commit, and push a fix only when it improves the product — push before replying, so the SHA named in the reply is inspectable and resolving the thread never outruns what is actually on the remote.
4. Reply on that thread with the disposition — conclusion, evidence, commit SHA, or why no change was warranted:

   ```bash
   uv run ./.agents/skills/receiving-pr-reviews/scripts/pr_review_threads.py reply --pr <N> --comment-id <databaseId> --body '...'
   ```
5. Resolve the thread:

   ```bash
   uv run ./.agents/skills/receiving-pr-reviews/scripts/pr_review_threads.py resolve --thread-id <id>
   ```
6. A decision spanning threads (PR sequencing, rebase disposition), or a response to a `reviews_with_body`/`unresponded_reviews` entry (which has no thread to reply on), goes on the PR itself via `gh pr comment <N> -R <owner>/<repo>` — the same owner/repo this run selected in step 1 (default `Jamie-BitFlight/claude_skills`), not a different repository — before the work it governs. When the comment is answering a specific `reviews_with_body`/`unresponded_reviews` entry, quote that review's own `url` field (from step 1's output) somewhere in the comment body — that quoted `url`, not just chronological order, is what `fetch`/`watch` require to clear that specific review out of `unresponded_reviews` on the next check, so an unrelated administrative comment (like the sequencing/decision comment this same step also covers) never gets mistaken for a response to whichever review happens to be outstanding at the time.
7. Once all current threads and reviews are addressed, re-check for new activity using the `watch` subcommand, in a loop of short calls rather than one long block — each call blocks for only its own default timeout (270s) and returns as soon as there is outstanding work to act on or that call's own timeout elapses:

   ```bash
   uv run ./.agents/skills/receiving-pr-reviews/scripts/pr_review_threads.py watch --pr <N>
   ```

   Run it inline and block directly when there is no other work to advance right now. If other work is queued, run this call in the background using whatever backgrounding mechanism the current harness provides (a background-execution tool parameter, or a poll-by-session-id pattern) and continue that work instead — then, before reporting back or finishing, check the backgrounded call's own result yourself rather than waiting for a completion notification (see the gotcha below).

   Read each call's result the same way: `timed_out: false` means `state.unresolved_count > 0`, `state.unresponded_reviews` is non-empty, or `state.codex_approved` is `true` — stop the loop and restart this skill from step 1 against whichever of those is true. `timed_out: true` means none of those three were ever true inside that one call's window, not that watching is done — issue another `watch` call immediately to continue covering the total window you intend to watch for (each call's own first fetch is a fresh snapshot, not a diff against the previous call's, so consecutive calls never miss activity in between). Stop looping once one of the three conditions is met, or once you've covered the total watching window you intend to cover. `codex_approved: true` on its own (with `unresolved_count: 0` and `unresponded_reviews: []`) means Codex reacted with its approval thumbs-up and left no further feedback — this is a completion signal, not something to act on further; do not re-enter the loop from step 1 for it alone.

</workflow>

<gotchas>

- All commands default `--owner`/`--repo` to this checkout's own `Jamie-BitFlight`/`claude_skills`; pass them explicitly to target a different repository.
- `reply`'s `<comment_id>` is a comment's `databaseId` from step 1 (verified identical to the REST comment `id`). `resolve`'s `<id>` is a thread's `id` from step 1, not a comment id. A thread's `comments` array is in creation order — when a thread has more than one comment (a prior reply already landed on it), pass the first comment's `databaseId`, not a later one: GitHub's reply endpoint requires the top-level review comment and rejects a reply targeted at another reply.
- A `reviews_with_body`/`unresponded_reviews` entry has no `id`/`databaseId` at all — it's not a thread and can't be replied to or resolved through this script. Address it (fix, or note why not) and post the response on the PR itself via `gh pr comment` per step 6, quoting that review's own `url` field in the comment body — that quoted `url`, postdating the review's `submittedAt`/`lastEditedAt`, is what clears it out of `unresponded_reviews` on the next `fetch`/`watch`; a comment that merely postdates the review without quoting its `url` does not.
- The script shells out to `gh` and relies on `gh`'s own authentication — it does not talk to the GitHub API directly and does not read or need a token itself.
- `watch`'s defaults (90-second poll interval, 270-second total timeout per call) stay under the 5-minute prompt-cache TTL floor that applies in every Claude billing mode, so one call's turn always lands inside cache. Cover a longer watching window by looping short `watch` calls (step 7), not by raising `--timeout-seconds` — raising it narrows or removes that safety margin.
- `watch` reserves a few seconds before `deadline` for one final poll rather than sleeping all the way to `deadline` and skipping it — under the default settings the whole window through shortly before `deadline` gets checked, not just up through the second-to-last interval. Only a pathologically short `--timeout-seconds`, or a poll that overran its own interval, leaves no room for that final attempt and produces the "no re-poll attempted" case described below.
- `watch` makes an entirely fresh `gh` snapshot on every single check — its own first fetch and every re-poll — and compares nothing against what an earlier check or an earlier `watch` call saw. If the very first fetch inside a `watch` call already has outstanding work (a thread was already unresolved, a review already unresponded, or Codex had already reacted before this call started), `watch` returns immediately without sleeping at all — there is nothing to wait for that the first fetch would have missed. This is what makes it safe to call `watch` again immediately after resolving something, or right after a plain `fetch`: neither call can desync from an in-memory baseline, because neither one keeps a baseline.
- A backgrounded `watch` call produces no completion notification when it finishes, even though it keeps running after its dispatcher returns — poll for its own result directly before reporting back or finishing.
- A `timed_out: true` result is only ever printed when the *most recent* check succeeded — the first fetch, or the last re-poll if one was attempted (or the window ended before any re-poll was even attempted, which is honest — nothing to check again yet). An earlier success in the same window does not offset a later failure: if the last re-poll attempted before the window ended failed (a transient `gh` error), `watch` exits non-zero with nothing on stdout instead of printing a `timed_out: true` result, even if some earlier poll in the same window succeeded — a caller that only checks for a zero exit code and JSON on stdout will not mistake an unconfirmed final stretch for a confirmed-clean one. Retry the `watch` call rather than treating the failure as "nothing new."

</gotchas>
