---
name: receiving-pr-reviews
description: Work through every unresolved review thread on a PR to completion — validate, fix if warranted, reply, resolve, then re-check on a bounded schedule. Use after pushing a commit to a PR, or when asked to check or address PR reviews.
---

# Receiving PR Reviews

1. Fetch only unresolved threads, filtered before the result reaches context — one query, not three:
   `gh api graphql -f query='query($o:String!,$r:String!,$pr:Int!){repository(owner:$o,name:$r){pullRequest(number:$pr){reviewThreads(first:50){nodes{id isResolved path comments(first:5){nodes{databaseId body}}}}}}}' -f o=Jamie-BitFlight -f r=claude_skills -F pr=<N> --jq '[.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false)]'`
   Each returned thread carries its own `id` (for resolving, step 5) and each comment's `databaseId` (for replying, step 4) — no separate lookup needed. Empty result means no unresolved threads; stop here.
2. For each unresolved thread: read it, validate the claim locally, assess against the change goal and repository instructions.
3. Implement, commit, and push a fix only when it improves the product — push before replying, so the SHA named in the reply is inspectable and resolving the thread never outruns what is actually on the remote.
4. Reply on that thread with the disposition — conclusion, evidence, commit SHA, or why no change was warranted.
5. Resolve the thread.
6. A decision spanning threads (PR sequencing, rebase disposition) goes on the PR itself via `gh pr comment <N> -R Jamie-BitFlight/claude_skills`, before the work it governs.
7. Once all current threads are resolved, check for additional reviews three times at 10-minute intervals via `/loop` (`/schedule`'s Cloud Routines have a 1-hour minimum interval — too coarse for this cadence). A new review restarts this skill from step 1 and cancels the remaining checks. A Codex thumbs-up with no comment, or an explicit "no reviews"/"no changes"/"0 comments" response, is that reviewer's completion signal.

## Gotchas

- Reply: `gh api -X POST repos/Jamie-BitFlight/claude_skills/pulls/<N>/comments/<comment_id>/replies -f body='...'` — `<comment_id>` is a comment's `databaseId` from step 1 (verified identical to the REST comment `id`).
- Resolve: `gh api graphql -f query='mutation($threadId:ID!){resolveReviewThread(input:{threadId:$threadId}){thread{isResolved}}}' -f threadId='<thread_id>'` — `<thread_id>` is a thread's `id` from step 1.
- Auditing already-resolved review history (not checking for new work to address) is a different task: drop `select(.isResolved == false)` from step 1's query to see every thread.
