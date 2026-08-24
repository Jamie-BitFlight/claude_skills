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

   The command's own pagination (`gh api graphql --paginate --slurp` under the hood, run once for review threads and once more for top-level reviews — each connection paginates independently since `--paginate` follows one cursor per call) re-issues each query until every page is fetched, so `threads_count`, `reviews_count`, and `unresolved` cover everything regardless of how many rounds of review the PR has been through — no thread-count or review-count cap. `reviews_count` and `threads_count` are the totals actually found — a `threads_count` of 0 means no reviews have landed yet (different from a nonzero `threads_count` with `unresolved_count: 0`, which means everything found was already resolved). Never treat an empty `unresolved` array as "nothing to do" without checking these counts first. Each unresolved thread carries its own `id` (for resolving, step 5) and each comment's `databaseId` (for replying, step 4) — no separate lookup needed. A thread's `comments_truncated: true` means that single thread has passed 100 comments in its own back-and-forth (rare, but real content is missing) — page that thread's `comments` connection directly before concluding anything about it. `reviews_with_body` surfaces reviews whose feedback lives in the review's own summary text rather than an inline comment (an approval note, or a reviewer who wrote general feedback with no line-level comment) — these have no thread at all and are otherwise invisible even when `unresolved_count` is 0; treat each as actionable input too. Auditing already-resolved review history (not checking for new work to address) is a different task: pass `--include-resolved` to see every thread.
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
7. Once all current threads are resolved, re-check for new reviews using the `watch` subcommand — it blocks its own process on an internal polling loop and returns as soon as new activity appears or its timeout elapses, so no separate resumption mechanism (scheduling, wakeups) is needed to check again later:

   ```bash
   uv run .agents/skills/receiving-pr-reviews/scripts/pr_review_threads.py watch --pr <N>
   ```

   How to run it depends on whether there is other work left to do right now, not on what kind of session or agent this is:

   - **Other tasks queued** — background `watch` via a backgrounded Bash call (`run_in_background: true`) and continue that other work instead of stalling on the wait. Before reporting back or finishing, check the backgrounded call's result yourself — poll for it rather than assuming a completion notification will arrive (see the gotcha below on why that check is required, not optional).
   - **Nothing else queued** — run `watch` inline and block on it directly. Nothing is lost by waiting when there is no other work to advance in the meantime.

   Either way, read the result the same way: `timed_out: false` means `new_thread_ids` or `new_reviews_with_body` is non-empty — restart this skill from step 1 against that new activity. `timed_out: true` means nothing new turned up inside the call's window; end the workflow, or issue another `watch` call for a further window if continued checking is warranted. A Codex thumbs-up with no comment, or an explicit "no reviews"/"no changes"/"0 comments" response, is that reviewer's completion signal and does not itself count as new activity.

</workflow>

<gotchas>

- All commands default `--owner`/`--repo` to `Jamie-BitFlight`/`claude_skills`; pass them explicitly to target a different repository.
- `reply`'s `<comment_id>` is a comment's `databaseId` from step 1 (verified identical to the REST comment `id`). `resolve`'s `<id>` is a thread's `id` from step 1, not a comment id.
- A `reviews_with_body` entry has no `id`/`databaseId` at all — it's not a thread and can't be replied to or resolved through this script. Address it (fix, or note why not) and, if a response belongs on the PR itself, use `gh pr comment` per step 6.
- The script shells out to `gh` and relies on `gh`'s own authentication — it does not talk to the GitHub API directly and does not read or need a token itself.
- `watch`'s defaults (5-minute poll interval, 9-minute total timeout) keep one call safely under Claude Code's 600-second Bash tool-call cap. Raising `--timeout-seconds` past that requires the caller's own tool-call timeout to be raised to match, or the harness kills the process before it returns anything.
- `watch` detects new activity by diffing against the snapshot taken when the call started — a thread `id` absent from that first snapshot, or a `reviews_with_body` entry (compared by full author/state/body content, since reviews carry no id) absent from it. A review whose text or state changes after the call starts counts as new activity even if the same reviewer already had a `reviews_with_body` entry in the baseline.
- Never background `watch` and then finish or report back without checking its result directly. Tested directly: a sub-agent dispatched a `sleep 20 && echo done >> file` job with `run_in_background: true`, then returned its own final result immediately (~7s later, well before the sleep finished) without waiting. The job kept running and the file held the expected output after the full 20s — the backgrounded process does survive its dispatcher's termination. But no notification of any kind arrived when that job finished; every `Agent`/`Task` dispatch that same session generated an automatic completion notification, while the orphaned background job generated none — its result was only found by manually checking the file afterward. This is why step 7's backgrounding branch requires polling for the backgrounded `watch` call's own result before reporting back or finishing, rather than assuming a completion notification will surface it.

</gotchas>
