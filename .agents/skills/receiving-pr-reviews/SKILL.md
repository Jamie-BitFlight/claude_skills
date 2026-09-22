---
name: receiving-pr-reviews
description: Process reviewer feedback for GitHub PRs and GitLab MRs. Use after pushing a commit to recheck reviews, or when asked to check or address comments, questions, approvals, change requests, or bot findings.
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
`gh` and a GitHub MCP connector is available, read the fail-closed
[GitHub MCP boundary](./references/github-mcp-fallback.md). The current package cannot normalize MCP
evidence into action-ready canonical state. One snapshot uses one executable transport.

## Review cycle

1. Establish the target, current remote revision, intended outcome, repository instructions, and
   mutation authority. This step closes when those facts and authority classes are explicit.
2. Run `fetch --snapshot-file <path>` to persist one full canonical snapshot. Stdout contains only the
   live action view; the file retains complete reconciliation evidence. `SNAPSHOT_INCOMPLETE` stops
   assessment and all mutation.
3. Read the [review-cycle contract](./references/review-cycle-contract.md). Build an exact census of
   every inbound comment, question, approval, rejection/change request, bot summary, and other human,
   reviewer, or stakeholder input. Assess each once, preserve resolved history, and record unknowns.
4. Cluster the exact census by shared invariant, cause, owning component, requested outcome, or
   verification surface; use explicit singleton clusters for unrelated inputs. Form one evidence-
   bearing systemic outcome and verification plan per cluster before changing source.
5. When authorized, implement each accepted cluster at its owning seam, or record evidence for
   `no_change`, `superseded`, or `clarification_required`. Verify every cluster and repository-required
   gate. Push source changes to an inspectable current revision before citing them.
6. Author the cycle state from the typed models. Use `validate-projection` for dry-run or check-only
   state and `validate-cycle` for action readiness. When authorized, communicate every disposition
   with provider-backed evidence, then resolve only where policy and capability permit. Clarifications
   remain open; unavailable resolution is recorded as unavailable.
7. Persist a new complete snapshot. New or changed inputs, revision, provider state, fingerprints, or
   communication evidence return the complete set to census, assessment, and clustering. Use bounded
   `watch --snapshot-file <path>` calls only to sample for later change; an elapsed call is not
   completion.
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
stable operations are `fetch`, `watch`, `validate-projection`, `validate-cycle`, `complete-cycle`,
`reply`, `resolve`, `comment`, `reply-and-resolve`, and `reply-and-resolve-batch`. Default fetch and
watch output contains only live unanswered inputs and their complete action content; `--summary`
contains aggregate decision metadata only. Use focused provider commands for deeper inspection and
`--snapshot-file` for internal reconciliation evidence. Exact fields and enum values live in the
Pydantic models, while validation commands govern action and completion gates.
