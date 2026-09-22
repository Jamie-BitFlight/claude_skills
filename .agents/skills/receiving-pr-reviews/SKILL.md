---
name: receiving-pr-reviews
description: Assess every PR review input as a complete set, implement systemic warranted changes, communicate dispositions, resolve eligible threads, and re-check on a bounded schedule. Use after pushing a commit to a PR, or when asked to check or address PR reviews.
---

# Receiving PR Reviews

Treat a review cycle as one evidence-bound system change. Comments, questions, approvals,
rejections, and bot signals are inputs to assess together—not isolated instructions to patch in
arrival order.

## Workflow

1. Fetch one full snapshot and preserve it as the mutation evidence:

   ```bash
   uv run ./.agents/skills/receiving-pr-reviews/scripts/pr_review_threads.py fetch \
     --pr <N> --github <owner/repo> > review-snapshot.json
   ```

   Use the full form for action work. It contains all normalized `review_inputs`, including
   resolved history used for pattern analysis, plus target, revision, fingerprint, completeness,
   capabilities, and stable references. A false `snapshot_complete` stops the cycle: fetch the
   truncated/unavailable surface before assessing or acting.

   If `gh` is unavailable and GitHub MCP tools are available, use the
   [GitHub MCP fallback](./references/github-mcp-fallback.md) for the entire snapshot. One snapshot
   uses one transport.

2. Assess the complete inbound census before editing. Validate each claim against the change goal,
   repository instructions, current code, and other review inputs. Cluster repeated symptoms by
   shared cause; make a singleton explicit when an input has no related input. Record observed
   actor/revision unknowns instead of guessing them.

3. Implement warranted clusters at their owning design seam. Verify the complete affected surface,
   then push an inspectable revision. Fetch a new full snapshot at that remote revision; this is
   the recheck snapshot that actions bind to.

4. Write `review-cycle.json` as `ReviewCycleState` from `pr_review_state_models.py`. Completion
   requires:

   - an exact, duplicate-free inbound `input_census`, one assessment per input, and clusters that
     cover every input exactly once;
   - concrete assessment scope/evidence/verification surfaces and cluster verification commands;
   - explicit decisions for every assessment unknown, including keys
     `revision_relation:<input-id>`, `actor_classification:<input-id>`, and
     `actor_role:<input-id>` when those provider facts are unknown;
   - implementation and verification evidence, the inspectable remote revision, and the recheck
     snapshot fingerprint;
   - exact per-input communication and resolution states; and
   - `cycle_state: READY_FOR_ACTION` with `cycle_terminal: action_pending`.

   Validate without mutating:

   ```bash
   uv run ./.agents/skills/receiving-pr-reviews/scripts/pr_review_threads.py validate-cycle \
     --snapshot-file review-snapshot.json --state-file review-cycle.json
   ```

5. Communicate each disposition before resolving. Every mutation requires the same snapshot and
   cycle evidence:

   ```bash
   uv run ./.agents/skills/receiving-pr-reviews/scripts/pr_review_threads.py reply \
     --pr <N> --github <owner/repo> --input-id <input-id> --body '<evidence and disposition>' \
     --snapshot-file review-snapshot.json --state-file review-cycle.json

   uv run ./.agents/skills/receiving-pr-reviews/scripts/pr_review_threads.py comment \
     --pr <N> --github <owner/repo> --input-id <input-id> --body '<evidence and disposition>' \
     --reference '<stable-reference>' \
     --snapshot-file review-snapshot.json --state-file review-cycle.json

   uv run ./.agents/skills/receiving-pr-reviews/scripts/pr_review_threads.py reply-and-resolve \
     --pr <N> --github <owner/repo> --input-id <input-id> --body '<evidence and disposition>' \
     --snapshot-file review-snapshot.json --state-file review-cycle.json
   ```

   `resolve` alone is recovery for communication already recorded as `completed` in the cycle.
   Clarification-required inputs remain open. Provider capabilities and the cluster resolution
   policy must authorize the requested action. Successful commands atomically advance the local
   communication/resolution state; a failed resolution retains completed communication for safe
   resolve-only recovery.

   Batch combined actions use complete canonical input IDs and stop at the first failed action:

   ```bash
   uv run ./.agents/skills/receiving-pr-reviews/scripts/pr_review_threads.py reply-and-resolve-batch \
     --pr <N> --github <owner/repo> --input-file actions.json \
     --snapshot-file review-snapshot.json --state-file review-cycle.json
   ```

   `actions.json` is `[{"input_id": "...", "body": "..."}, ...]`.

6. Re-check with short bounded calls after current inputs are communicated:

   ```bash
   uv run ./.agents/skills/receiving-pr-reviews/scripts/pr_review_threads.py watch \
     --pr <N> --github <owner/repo>
   ```

   A call stops on outstanding work or its window/attempt bound. `timed_out: true` means no stop
   signal appeared in that sampled window; issue another call to cover a longer intended window.
   Full watch output preserves the canonical snapshot under `state`.

## Operational bounds

- Every `gh` subprocess has a 30-second default process-tree bound. Set `--gh-timeout-seconds` to a
  smaller positive bound when needed; watch uses the tighter caller bound or remaining deadline.
- `watch` defaults to a 90-second interval, 270-second window, and four complete snapshots.
- `--summary` is for status inspection, not action evidence. `--max-body` visibly truncates only
  when the caller requests it.
- Comma-separated `--pr` is fetch-only and emits lightweight board entries; action cycles use one
  target and revision.
