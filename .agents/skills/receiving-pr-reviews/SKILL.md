---
name: receiving-pr-reviews
description: Process every GitHub PR or GitLab MR review input as one evidence-bound cycle. Use after pushing a commit to a PR or MR, or when asked to check or address review feedback.
---

# Receiving PR and MR Reviews

Treat every human, bot, reviewer, and stakeholder input as one evidence set. Assess the complete set
before acting; its shared patterns determine the systemic response.

## Authority

A check-only request authorizes fetch, assessment, validation, and reporting. Source edits, pushes,
provider replies/comments, and provider resolutions are separate mutation classes; each requires the
user's request or an explicit repository standing rule. Passing validation proves readiness, not
authority.

## Route

Use `scripts/pr_review_threads.py` to detect or select one target and provider. For a GitLab MR, read
[GitLab review operations](./references/gitlab-review-operations.md). If the bundled CLI cannot use
`gh` and a GitHub MCP connector is available, read the
[GitHub MCP fallback](./references/github-mcp-fallback.md) and use it for the whole snapshot. One
snapshot uses one transport.

## Review cycle

1. Establish the target, current remote revision, intended outcome, repository instructions, and
   mutation authority. This step closes when those facts and authority classes are explicit.
2. Fetch and save one full canonical snapshot. A complete snapshot has every required surface,
   pagination, and nested conversation accounted for. `SNAPSHOT_INCOMPLETE` stops assessment and all
   mutation.
3. Read the [review-cycle contract](./references/review-cycle-contract.md). Build an exact census of
   every inbound comment, question, approval, rejection/change request, bot summary, and other human,
   reviewer, or stakeholder input. Assess each once, preserve resolved history, and record unknowns.
4. Cluster the exact census by shared invariant, cause, owning component, requested outcome, or
   verification surface; use explicit singleton clusters for unrelated inputs. Form one evidence-
   bearing systemic outcome and verification plan per cluster before changing source.
5. When authorized, implement each accepted cluster at its owning seam, or record evidence for
   `no_change`, `superseded`, or `clarification_required`. Verify every cluster and repository-required
   gate. Push source changes to an inspectable current revision before citing them.
6. Author the cycle state from the typed models and run `validate-cycle`. When authorized, communicate
   every disposition with provider-backed evidence, then resolve only where the cluster policy and
   provider capability permit. Clarifications remain open; unavailable resolution is recorded as
   unavailable.
7. Fetch a new complete snapshot. New or changed inputs, revision, provider state, fingerprints, or
   communication evidence return the complete set to census, assessment, and clustering. Use bounded
   `watch` calls only to sample for later change; an elapsed call is not completion.
8. Run `complete-cycle` against current provider state. Only its successful persisted result emits
   `REVIEW_COMPLETE`.

## Stop conditions

- `SNAPSHOT_INCOMPLETE`: a required surface, page, conversation, schema, or transport observation is
  missing. Fetch a complete stable snapshot before proceeding.
- `clarification_required`: this disposition records that evidence cannot determine validity or
  relevance. Ask one focused question, keep the input open, and keep the cycle non-terminal.
- `BLOCKED`: required authority, capability, or external fact is absent. Report the exact blocker.
- `ERROR`: collection, validation, or provider operation failed. Preserve confirmed evidence and do
  not label stale state clean.
- `REVIEW_COMPLETE`: the complete current recheck is unchanged and has zero unresolved, outstanding,
  new, or changed inputs, while every contract gate is terminal. Approval, rejection, a clear initial
  snapshot, or a quiet watch window is an input or observation, never this terminal by itself.

## Command source

Run `scripts/pr_review_threads.py <command> --help` for current targets, arguments, and bounds. The
stable operations are `fetch`, `watch`, `validate-cycle`, `complete-cycle`, `reply`, `resolve`,
`comment`, `reply-and-resolve`, and `reply-and-resolve-batch`. Full output is action evidence;
`--summary` is inspection only. Exact fields and enum values live in the Pydantic models, while the
validation commands are the authority for action and completion gates.
