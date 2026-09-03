---
name: receiving-pr-reviews
description: Work through every unresolved review thread on a PR to completion — validate, fix if warranted, reply, resolve, then re-check on a bounded schedule. Use after pushing a commit to a PR, or when asked to check or address PR reviews.
---

# Receiving PR Reviews

<workflow>

1. Fetch every unresolved thread, every unresponded review, and Codex's approval state. Prefer `--summary` — it already carries every id step 4/5 needs; drop it only when you need `reviews_with_body`'s full list or a thread's complete comment history:

   ```bash
   uv run ./.agents/skills/receiving-pr-reviews/scripts/pr_review_threads.py fetch --pr <N> --summary
   ```

   Read `reviews_count`, `threads_count`, `unresolved_count`, `unresponded_count`, and `blockers` together — never treat an empty `unresolved` array on its own as "nothing to do". A `threads_count` of 0 means no *inline* thread landed, not that no review landed. A non-empty `blockers` means the empty result set is expected and the fix is on the PR itself — undraft it, resolve the conflicts — not in the review queue. (Dropping `--summary` gets the same fields under `reviewability.blockers` instead of top-level `blockers`, plus the full `reviews_with_body` and each thread's complete `comments` list — a thread's `comments_truncated: true` there means it has passed 100 comments; page its `comments` connection directly before concluding anything about it. `unresponded_count` itself only exists on `--summary` output — the full form has no matching field, use `len(unresponded_reviews)` there instead.)

   `unresolved`/`unresponded_reviews` entries are this run's actionable input; treat every one as something to address. For `codex_approved`, see step 7. Checking several PRs at once: `--pr 41,42,44` prints one line (or, with `--summary`, one JSON block) per PR instead of one call each.

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

   Steps 4 and 5 combined — one thread or many in one process:

   ```bash
   uv run ./.agents/skills/receiving-pr-reviews/scripts/pr_review_threads.py reply-and-resolve \
     --pr <N> --thread-id <id> --comment-id <databaseId> --body '...'
   uv run ./.agents/skills/receiving-pr-reviews/scripts/pr_review_threads.py reply-and-resolve-batch \
     --pr <N> --input-file threads.json   # [{thread_id, comment_id, body}, ...]
   ```

   The batch form stops at the first failure and prints one JSON line per thread.
6. A decision spanning threads (PR sequencing, rebase disposition), or a response to a `reviews_with_body`/`unresponded_reviews` entry, goes on the PR itself via `gh pr comment <N> -R <owner>/<repo>` — the same owner/repo this run used in step 1 — before the work it governs. When answering a specific entry, quote that review's own `url` field from step 1's output in the comment body. That quoted `url`, postdating the review, is what clears the review out of `unresponded_reviews` on the next check; chronological order alone does not.
7. Once all current threads and reviews are addressed, re-check with `watch`, looping short calls rather than one long block:

   ```bash
   uv run ./.agents/skills/receiving-pr-reviews/scripts/pr_review_threads.py watch --pr <N>
   ```

   Block on it inline when there is no other work to advance. With other work queued, background the call using whatever mechanism the harness provides and continue that work — then poll the backgrounded call for its own result before reporting back or finishing, because it produces no completion notification.

   `timed_out: false` means `state.unresolved_count > 0`, `state.unresponded_reviews` is non-empty, or `state.codex_approved` is `true` — restart this skill from step 1 against whichever is true. `timed_out: true` means none of the three were true inside that one call's window, not that watching is done — issue another `watch` immediately to keep covering the window you intend to watch. Stop once one of the three conditions is met, or once the intended window is covered. `codex_approved: true` on its own, with `unresolved_count: 0` and `unresponded_reviews: []`, is a completion signal — do not re-enter step 1 for it.

</workflow>

<gotchas>

- `fetch`/`watch`/`reply` detect this checkout's own repository via `gh repo view`; pass `--github owner/repo` to target a different one, or when detection fails.
- `--gh-timeout-seconds` is unbounded by default on `fetch` and `watch`. One snapshot is seven sequential `gh api` calls, some of them paginating a large PR, so choose a bound against your own network. Inside `watch` it applies to the first fetch only; each poll is bounded by the time left before `--timeout-seconds`.
- `reply`'s `--comment-id` is a comment's `databaseId` and `resolve`'s `--thread-id` is a thread's `id` — both come straight from step 1's output. When a thread already has more than one comment, pass the *first* comment's `databaseId`: `comments` is in creation order, and GitHub rejects a reply targeted at another reply.
- A `reviews_with_body`/`unresponded_reviews` entry is not a thread, so it cannot be replied to or resolved through this script. Address it and post the response on the PR itself per step 6.
- `watch`'s defaults — a 90-second poll interval, a 270-second timeout per call — stay under the 5-minute prompt-cache TTL floor that applies in every Claude billing mode. Cover a longer window by looping calls, not by raising `--timeout-seconds`.
- `watch` stops polling once less than one interval remains before its deadline, so its last observed state can be up to one interval stale. The next call's own first fetch covers that stretch.
- Every check inside `watch` is a fresh `gh` snapshot with no baseline, so a call whose first fetch already has outstanding work returns immediately. Calling `watch` right after a `resolve` or a plain `fetch` is safe.
- `reviewability` is read fresh on every poll, so a `timed_out: true` result carries it too — check `state.reviewability.blockers` before issuing another `watch` rather than waiting out a window for reviews that cannot arrive. `mergeable: "UNKNOWN"` is never a blocker: GitHub computes mergeability in a background job, and it resolves on a later check.
- `watch` exits non-zero with nothing on stdout when the last re-poll of a window failed. Retry the call rather than reading it as "nothing new."
- `--summary` (step 1) also works on `watch`; `timed_out` sits alongside the summary fields there instead of nested under `state`. Add `--max-body N` to cut long bodies, visibly marked when cut; unlimited by default. Step 7's `state.X` field names (`state.unresolved_count`, `state.unresponded_reviews`, `state.codex_approved`, `state.reviewability.blockers`) describe the full (non-`--summary`) form only — with `--summary`, read the same signals without the `state.` prefix, and read `blockers` at the top level rather than under `reviewability`.
- Comma-separated `--pr` is `fetch`-only — `watch` polls one PR at a time.

</gotchas>
