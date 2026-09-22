---
name: receiving-pr-reviews
description: Assess every PR review input as a complete set, implement systemic warranted changes, communicate dispositions, resolve eligible threads, and re-check on a bounded schedule. Use after pushing a commit to a PR, or when asked to check or address PR reviews.
---

# Receiving PR Reviews

Treat a review cycle as one evidence-bound system change. Comments, questions, approvals,
rejections, and bot signals are inputs to assess together—not isolated instructions to patch in
arrival order.

## Workflow

1. Fetch one full snapshot and preserve it as the mutation evidence. For a GitLab merge request,
   first read [GitLab review operations](./references/gitlab-review-operations.md), then select the
   GitLab provider and target; the remaining review-cycle gates are shared:

   ```bash
   ./.agents/skills/receiving-pr-reviews/scripts/pr_review_threads.py fetch \
     --pr <N> --github <owner/repo> > review-snapshot.json
   ```

   Use the full form for action work. It contains all normalized `review_inputs`, including
   resolved history used for pattern analysis, plus target, revision, fingerprint, completeness,
   capabilities, and stable references. A false `snapshot_complete` stops the cycle: fetch the
   truncated/unavailable surface before assessing or acting. Completion is one saved snapshot
   with `snapshot_complete: true`. According to lines 135–229 of
   [pr_review_gh.py](./scripts/pr_review_gh.py), GitHub normalization retains resolved history and
   derives the snapshot completeness evidence; lines 110–197 of
   [pr_review_github_transport.py](./scripts/pr_review_github_transport.py) fetch both outer and
   nested thread pages.

   If `gh` is unavailable and GitHub MCP tools are available, use the
   [GitHub MCP fallback](./references/github-mcp-fallback.md) for the entire snapshot. One snapshot
   uses one transport.

2. Assess the complete inbound census before editing. Validate each claim against the change goal,
   repository instructions, current code, and other review inputs. Cluster repeated symptoms by
   shared cause; make a singleton explicit when an input has no related input. Record observed
   actor/revision unknowns instead of guessing them. A comment may be classified as a question
   during assessment while retaining its normalized comment kind. Completion is one assessment per
   inbound input and cluster membership covering that same set exactly once. According to lines
   106–192 of [pr_review_state.py](./scripts/pr_review_state.py), the gate enforces that coverage,
   unknown decisions, and semantic classification.

3. Implement warranted clusters at their owning design seam. Verify the complete affected surface,
   then push an inspectable revision. Fetch a new full snapshot at that remote revision; this is
   the recheck snapshot that actions bind to. Completion is a verified remote revision whose new
   complete snapshot fingerprint is recorded in the cycle.

4. Write `review-cycle.json` as `ReviewCycleState` from `pr_review_state_models.py`. Completion
   requires:

   - an exact, duplicate-free inbound `input_census`, one assessment per input, and clusters that
     cover every input exactly once;
   - `assessed_inputs` mapping every inbound ID to the complete canonical input state that was
     assessed;
   - concrete assessment scope/evidence/verification surfaces and cluster verification commands;
   - explicit decisions for every assessment unknown, including keys
     `revision_relation:<input-id>`, `actor_classification:<input-id>`, and
     `actor_role:<input-id>` when those provider facts are unknown;
   - implementation and verification evidence, the inspectable remote revision, the recheck
     snapshot fingerprint, and exact per-input implementation states;
   - exact per-input communication and resolution states; and
   - one terminal annotation per input before completion; and
   - `cycle_state: READY_FOR_ACTION` with `cycle_terminal: action_pending`.

   Validate without mutating:

   ```bash
   ./.agents/skills/receiving-pr-reviews/scripts/pr_review_threads.py validate-cycle \
     --snapshot-file review-snapshot.json --state-file review-cycle.json
   ```

   Completion is a zero exit from `validate-cycle`. According to lines 61–192 of
   [pr_review_state.py](./scripts/pr_review_state.py), validation binds completeness, revision,
   fingerprint, evidence, census, assessed input state, assessments, clusters, unknown decisions,
   and action state. The `assessed_inputs` field is defined at lines 257–276 of
   [pr_review_state_models.py](./scripts/pr_review_state_models.py).

5. Communicate each disposition before resolving. Every mutation requires the same snapshot and
   cycle evidence:

   ```bash
   ./.agents/skills/receiving-pr-reviews/scripts/pr_review_threads.py reply \
     --pr <N> --github <owner/repo> --input-id <input-id> --body '<evidence and disposition>' \
     --snapshot-file review-snapshot.json --state-file review-cycle.json

   ./.agents/skills/receiving-pr-reviews/scripts/pr_review_threads.py comment \
     --pr <N> --github <owner/repo> --input-id <input-id> --body '<evidence and disposition>' \
     --reference '<stable-reference>' \
     --snapshot-file review-snapshot.json --state-file review-cycle.json

   ./.agents/skills/receiving-pr-reviews/scripts/pr_review_threads.py reply-and-resolve \
     --pr <N> --github <owner/repo> --input-id <input-id> --body '<evidence and disposition>' \
     --snapshot-file review-snapshot.json --state-file review-cycle.json
   ```

   `resolve` alone is recovery for communication already recorded as `completed` in the cycle.
   Clarification-required inputs remain open. Provider capabilities and the cluster resolution
   policy must authorize the requested action. Successful commands atomically advance the local
   communication/resolution state; a failed resolution retains completed communication for safe
   resolve-only recovery. Combined and batch actions pre-authorize every reply and resolution
   before their first provider call. According to lines 195–242 of
   [pr_review_state.py](./scripts/pr_review_state.py), action authorization checks capabilities,
   communication, resolution, policy, and stable references; lines 148–316 and 330–382 of
   [pr_review_cli_mutations.py](./scripts/pr_review_cli_mutations.py) refresh remote state before
   acting and persist only provider-confirmed progress.

   Batch combined actions use complete canonical input IDs and stop at the first failed action:

   ```bash
   ./.agents/skills/receiving-pr-reviews/scripts/pr_review_threads.py reply-and-resolve-batch \
     --pr <N> --github <owner/repo> --input-file actions.json \
     --snapshot-file review-snapshot.json --state-file review-cycle.json
   ```

   `actions.json` is `[{"input_id": "...", "body": "..."}, ...]`. Completion requires provider-backed
   communication state `completed` for every inbound input, with each resolvable input resolved;
   clarification-required input keeps the cycle non-terminal.

6. Re-check with short bounded calls after current inputs are communicated:

   ```bash
   ./.agents/skills/receiving-pr-reviews/scripts/pr_review_threads.py fetch \
     --pr <N> --github <owner/repo> > watch-baseline.json

   ./.agents/skills/receiving-pr-reviews/scripts/pr_review_threads.py watch \
     --pr <N> --github <owner/repo> --baseline-snapshot-file watch-baseline.json
   ```

   Save the complete post-communication snapshot as the watch baseline. A call stops on outstanding
   work, any canonical provider-state change, or its window/attempt bound. Any change returns the
   cycle to census and assessment; replace `assessed_inputs` only after assessing the changed
   canonical inputs. `timed_out: true` means no stop signal appeared in that sampled window; issue
   another call with the same baseline to cover a longer intended window. Full watch output preserves
   the canonical snapshot under `state`. Completion is a final complete provider snapshot with no
   unresolved, outstanding, new, or changed input. Record the final per-input lifecycle evidence,
   then evaluate the only successful terminal:

   ```bash
   ./.agents/skills/receiving-pr-reviews/scripts/pr_review_threads.py complete-cycle \
     --pr <N> --github <owner/repo> \
     --snapshot-file review-snapshot.json --state-file review-cycle.json
   ```

   According to lines 253–320 of [pr_review_state.py](./scripts/pr_review_state.py), completion
   requires current canonical snapshot identity, no provider outstanding work, unchanged assessed
   input state, exhaustive coverage, terminal per-input implementation/communication/resolution
   state, provider-backed communication, and terminal annotations. According to lines 224–308 of
   [pr_review_threads.py](./scripts/pr_review_threads.py), watch compares the full canonical
   fingerprint with its baseline and reports attempts, bound exhaustion, timeout state, and the
   final canonical snapshot.

## Command reference

Run `./.agents/skills/receiving-pr-reviews/scripts/pr_review_threads.py <command> --help` for the
current provider, target, operation, and timeout options. Use full output for action evidence; use
`--summary` only for status
inspection. According to lines 67–97 of
[pr_review_subprocess.py](./scripts/pr_review_subprocess.py), every provider subprocess has a
mandatory positive bound and process-tree cleanup before a timeout is raised.
