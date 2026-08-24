---
name: receiving-pr-reviews
description: Work through every unresolved review thread on a PR to completion — validate, fix if warranted, reply, resolve, then re-check on a bounded schedule. Use after pushing a commit to a PR, or when asked to check or address PR reviews.
---

# Receiving PR Reviews

1. `gh pr view <N> -R Jamie-BitFlight/claude_skills --json reviews,reviewDecision` and `gh api repos/Jamie-BitFlight/claude_skills/pulls/<N>/comments --jq '[.[] | {id, path, line, body}]'`. Empty `reviewDecision` + `state: COMMENTED` does not mean no findings.
2. For each unresolved thread: read it, validate the claim locally, assess against the change goal and repository instructions.
3. Implement and commit a fix only when it improves the product.
4. Reply on that thread with the disposition — conclusion, evidence, commit SHA, or why no change was warranted.
5. Resolve the thread.
6. A decision spanning threads (PR sequencing, rebase disposition) goes on the PR itself via `gh pr comment <N> -R Jamie-BitFlight/claude_skills`, before the work it governs.
7. Once all current threads are resolved, check for additional reviews three times at 10-minute intervals via `/loop` or `/schedule`. A new review restarts this skill from step 1 and cancels the remaining checks. A Codex thumbs-up with no comment, or an explicit "no reviews"/"no changes"/"0 comments" response, is that reviewer's completion signal.

## Gotchas

- Step 2's `id` field is required — the reply endpoint needs `comment_id` and there's no other way to get it.
- Reply: `gh api -X POST repos/Jamie-BitFlight/claude_skills/pulls/<N>/comments/<comment_id>/replies -f body='...'`
- Resolve: `gh api graphql -f query='mutation($threadId:ID!){resolveReviewThread(input:{threadId:$threadId}){thread{isResolved}}}' -f threadId='<thread_id>'` — `<thread_id>` comes from a GraphQL `reviewThreads` query on the PR, not the REST comments endpoint in step 1.
