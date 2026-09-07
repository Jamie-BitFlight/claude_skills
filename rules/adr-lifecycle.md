# Architecture documentation, and where ADRs sit

Two different artifacts, and conflating them is what makes a deliberation binding.

**`ARCHITECTURE.md` states what is true now.** It is rewritten in place as the design changes, it
lives nearest the code it describes — the touched module's own subtree before anything higher — and
it is what documentation, skills, agents, code and tests reference.

**An ADR records a deliberation**: the context, the options, why one was taken and what was
rejected. It is planning material. Many repositories never commit one at all.

## Nothing links to an ADR

Not a document, not a skill, not an agent, not a test, not code, and not `ARCHITECTURE.md` either.

A link makes the ADR load-bearing, and the repository owner must be able to dismiss an ADR that
turns out not to reflect the goal or the intent without the repository being stuck with it. The
citation is precisely what removes that right. Where an ADR's substance is needed, write the
substance into `ARCHITECTURE.md`; where its rationale is worth keeping, write that there too.

The consequence to watch for: a reader who must replay a chain of decisions and supersessions to
work out what is currently true is reading the deliberation because nothing else states the outcome.
That is the failure this rule prevents.

A test that reads an ADR and enforces its criteria is the extreme case — executable code coupled to
a deliberation document, which cannot then be dismissed without breaking the suite. If a criterion
is worth enforcing, it belongs in the architecture document or an executable specification, and the
test checks that.

## Plasticity by location

Inside a pull request an ADR is freely rewritable and deletable, and so is the architecture document
it feeds. On the trunk the architecture document is much less plastic, because work depends on it.
An ADR on the trunk stays dismissible whatever its status — dismissing it breaks nothing exactly
because nothing links to it.

## Statuses

| status | means | who may write it |
|---|---|---|
| `Proposed` | authored on a branch, under review | anyone, including an agent |
| `Accepted` | reviewed and merged to the trunk | conferred by the merge |
| `Superseded by <ADR>` | replaced by a later deliberation | anyone, on the superseding change |
| `Withdrawn` | abandoned, or found not to reflect the intent | anyone; deleting it is equally correct |

**An agent never writes `Accepted`.** Writing it asserts a review that did not happen, and it turns
a draft into a constraint the branch is then held to. Author every new ADR as `Proposed`.

Without a draft state an agent can manufacture binding architecture: write an ADR, write code citing
it, and the branch is bound to a decision nobody reviewed and no requirement asked for. Both halves
of this rule exist to close that path — the status, so a proposal cannot pass as a decision, and the
no-linking rule, so nothing becomes hostage to either.
