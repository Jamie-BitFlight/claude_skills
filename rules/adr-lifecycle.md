# ADR lifecycle

An ADR on an unmerged branch is a proposal, not a decision. The merge is the review event that
makes it one.

## Statuses

| status | means | who may write it | may it be rewritten or deleted |
|---|---|---|---|
| `Proposed` | authored on a branch, under review | anyone, including an agent | yes, freely, until it merges |
| `Accepted` | reviewed and merged to the trunk | conferred by the merge | no — supersede it instead |
| `Superseded by <ADR>` | was `Accepted`, now replaced | anyone, on the superseding change | no |
| `Withdrawn` | was `Proposed`, abandoned before merge | anyone | it may simply be deleted instead |

**An agent never writes `Accepted`.** Writing it asserts a review that did not happen, and it
converts a draft into a constraint the branch is then held to. Author every new ADR as `Proposed`.

## Why the draft state has to exist

Without it, an agent can manufacture binding architecture: write an ADR, write code citing it, and
the branch is now tied to a decision nobody reviewed and no requirement asked for. The
supersede-don't-edit convention then protects the wrong thing — it preserves a record of a decision
that was never in force, and each supersession adds a document a reader has to work through to reach
what is actually true.

Supersession earns its ceremony only when others built on the decision. Nothing outside the branch
has built on a `Proposed` ADR, so rewriting it loses no history worth keeping.

## Citing one

Cite a `Proposed` ADR only from inside its own branch, and carry the status at the citation site so
a reader can tell a proposal from a decision. Code, tests and documents that rest on a `Proposed`
ADR are draft to the same degree it is.

When a `Proposed` ADR is deleted or withdrawn, every referent to it must be repointed or removed in
the same change. A citation that stops resolving is the defect the decomposition-exit gate blocks,
and it is not excused by the target having been a draft.
