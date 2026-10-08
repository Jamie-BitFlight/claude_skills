---
name: receiving-pr-reviews
description: Assess review feedback on GitHub PRs, GitLab MRs, or directly in conversation. Use to check reviews after a push, assess reviewer findings, address comments, or recheck approvals and change requests.
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

For feedback outside a PR or MR, apply the [technical review guidelines](./references/technical-review-guidelines.md), group shared causes, and report evidence-backed dispositions. The provider lifecycle and `REVIEW_COMPLETE` apply to PRs and MRs.

Use `scripts/pr_review_threads.py` to detect or select one target and provider. For a GitLab MR, read
[GitLab review operations](./references/gitlab-review-operations.md). If the bundled CLI cannot use
`gh` and a GitHub MCP connector is available, read the fail-closed
[GitHub MCP boundary](./references/github-mcp-fallback.md). The MCP route supplies diagnostics until the bundled CLI produces a complete canonical snapshot.

## Review cycle

1. Establish the target, current remote revision, intended outcome, repository instructions, and
   mutation authority. This step closes when those facts and authority classes are explicit.
2. Run `fetch --snapshot-file <path>` to persist one full canonical snapshot. Stdout contains only the
   live action view; the file retains complete reconciliation evidence. `SNAPSHOT_INCOMPLETE` stops
   assessment and all mutation.
3. Read the [review-cycle contract](./references/review-cycle-contract.md) for canonical state. Apply the [technical review guidelines](./references/technical-review-guidelines.md) to each assessment. Build an exact census of every inbound comment, question, approval, rejection/change request, bot summary, and other human, reviewer, or stakeholder input. Assess each once, preserve resolved history, and record unknowns. Exit when every canonical inbound ID has one evidence-bearing assessment.
4. Cluster the exact census by shared invariant, cause, owning component, requested outcome, or
   verification surface; use explicit singleton clusters for unrelated inputs. Form one evidence-
   bearing systemic outcome and verification plan per cluster before changing source. Exit when clusters form an exact cover of the census and each has an owning seam and verification plan.
5. When authorized, implement each accepted cluster at its owning seam, or record evidence for `no_change`, `superseded`, or `clarification_required`. Schedule accepted clusters by dependency, allowing independent ready work to proceed concurrently. Verify every cluster and repository-required gate. Push source changes to an inspectable current revision before citing them. Exit when each input has a verified implementation result or an evidence-backed non-change disposition.
6. Author the cycle state from the typed models. Use `validate-projection` for dry-run or check-only state and `validate-cycle` for action readiness. Apply the response guidance in the [technical review guidelines](./references/technical-review-guidelines.md). When authorized, communicate every disposition with provider-backed evidence, then resolve only where policy and capability permit. Clarifications remain open; unavailable resolution is recorded as unavailable. Exit when every input has a provider-backed reply or a documented clarification blocker and its resolution state is truthful.
7. Persist a new complete snapshot. New or changed inputs, revision, provider state, fingerprints, or
   communication evidence return the complete set to census, assessment, and clustering. Use bounded
   `watch --snapshot-file <path>` calls only to sample for later change; an elapsed call is not
   completion.
8. Run `complete-cycle` against current provider state. Only its successful persisted result emits
   `REVIEW_COMPLETE`.

## Recovery

- `SNAPSHOT_INCOMPLETE`: a required surface, page, conversation, schema, or transport observation is
  missing. Fetch a complete stable snapshot before proceeding.
- `clarification_required`: this disposition records that evidence cannot determine validity or
  relevance. Ask one focused question, keep the input open, and keep the cycle non-terminal.
- `BLOCKED`: required authority, capability, or external fact is absent. Report the exact blocker.
- `ERROR`: collection, validation, or provider operation failed. Preserve confirmed evidence and do
  not label stale state clean.
- `REVIEW_COMPLETE`: the complete current recheck is unchanged and has zero unresolved, outstanding,
  new, or changed inputs, while every contract gate is terminal. The persisted `complete-cycle` result establishes this terminal.

## Command source

Run `scripts/pr_review_threads.py <command> --help` for current arguments and supported operations. The Pydantic models own state fields and enums; validation commands own action and completion readiness.
