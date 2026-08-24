---
name: receiving-pr-reviews
description: Work through every unresolved review thread on a PR to completion — validate, fix if warranted, reply, resolve, then re-check on a bounded schedule. Use after pushing a commit to a PR, or when asked to check or address PR reviews.
---

# Receiving PR Reviews

<workflow>

1. Fetch every unresolved thread and every review with a top-level body, filtered before the result reaches context — one command, auto-paginated so a PR with hundreds of threads or reviews is never silently truncated:

   ```bash
   uv run .agents/skills/receiving-pr-reviews/scripts/pr_review_threads.py fetch --pr <N>
   ```

   The command's own pagination (`gh api graphql --paginate --slurp` under the hood) re-issues the query until every thread page is fetched, so `threads_count` and `unresolved` cover every thread regardless of how many rounds of review the PR has been through — no thread-count cap. `reviews_count` and `threads_count` are the totals actually found — a `threads_count` of 0 means no reviews have landed yet (different from a nonzero `threads_count` with `unresolved_count: 0`, which means everything found was already resolved). Never treat an empty `unresolved` array as "nothing to do" without checking these counts first. Each unresolved thread carries its own `id` (for resolving, step 5) and each comment's `databaseId` (for replying, step 4) — no separate lookup needed. A thread's `comments_truncated: true` means that single thread has passed 100 comments in its own back-and-forth (rare, but real content is missing) — page that thread's `comments` connection directly before concluding anything about it. `reviews_with_body` surfaces reviews whose feedback lives in the review's own summary text rather than an inline comment (an approval note, or a reviewer who wrote general feedback with no line-level comment) — these have no thread at all and are otherwise invisible even when `unresolved_count` is 0; treat each as actionable input too. `reviews_truncated: true` means more than 100 reviews exist and some may be unseen. Auditing already-resolved review history (not checking for new work to address) is a different task: pass `--include-resolved` to see every thread.
2. For each unresolved thread or review body: read it, validate the claim locally, assess against the change goal and repository instructions.
3. Implement, commit, and push a fix only when it improves the product — push before replying, so the SHA named in the reply is inspectable and resolving the thread never outruns what is actually on the remote.
4. Reply on that thread with the disposition — conclusion, evidence, commit SHA, or why no change was warranted:

   ```bash
   uv run .agents/skills/receiving-pr-reviews/scripts/pr_review_threads.py reply --pr <N> --comment-id <databaseId> --body '...'
   ```
5. Resolve the thread:

   ```bash
   uv run .agents/skills/receiving-pr-reviews/scripts/pr_review_threads.py resolve --thread-id <id>
   ```
6. A decision spanning threads (PR sequencing, rebase disposition) goes on the PR itself via `gh pr comment <N> -R Jamie-BitFlight/claude_skills`, before the work it governs.
7. Once all current threads are resolved, check for additional reviews three times at 10-minute intervals via `/loop` (`/schedule`'s Cloud Routines have a 1-hour minimum interval — too coarse for this cadence). A new review restarts this skill from step 1 and cancels the remaining checks. A Codex thumbs-up with no comment, or an explicit "no reviews"/"no changes"/"0 comments" response, is that reviewer's completion signal.

</workflow>

<gotchas>

- All three commands default `--owner`/`--repo` to `Jamie-BitFlight`/`claude_skills`; pass them explicitly to target a different repository.
- `reply`'s `<comment_id>` is a comment's `databaseId` from step 1 (verified identical to the REST comment `id`). `resolve`'s `<id>` is a thread's `id` from step 1, not a comment id.
- A `reviews_with_body` entry has no `id`/`databaseId` at all — it's not a thread and can't be replied to or resolved through this script. Address it (fix, or note why not) and, if a response belongs on the PR itself, use `gh pr comment` per step 6.
- The script shells out to `gh` and relies on `gh`'s own authentication — it does not talk to the GitHub API directly and does not read or need a token itself.

</gotchas>
