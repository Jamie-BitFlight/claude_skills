# Architecture documentation, and where ADRs sit

Two different artifacts, and conflating them is what makes a deliberation binding.

**`ARCHITECTURE.md` states what is true now.** It is the formalized design of the system it
describes, or the entry point routing to the subsystem architecture document that lives with that
subsystem's code. It is rewritten in place as the design changes, it lives nearest the code it
describes — the touched module's own subtree before anything higher — and it is what documentation,
skills, agents, code and tests reference.

**An ADR records a deliberation**: the context, the options, why one was taken and what was
rejected. It is planning material. Many repositories never commit one at all.

## Nothing links to an ADR

Not a document, not a skill, not an agent, not a test, not code, and not `ARCHITECTURE.md` either.

A link makes the ADR load-bearing, and the repository owner must be able to dismiss an ADR that
turns out not to reflect the goal or the intent without the repository being stuck with it. The
citation is precisely what removes that right. Where an ADR's substance is needed, write the
substance into `ARCHITECTURE.md`; where its rationale is worth keeping, write that there too.

An ADR need not live in the repository at all. A decision record belongs equally in an issue
tracker or a project board, where an agent reading the code may have no access to it. So a citation
is not merely stale-prone — it can be unresolvable by construction for whoever reads the code next.
`ARCHITECTURE.md` lives with the code and is always readable by anyone who has the code.

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

**An ADR authored on a branch carries `Proposed`. The merge confers `Accepted`.** The merge is the
review, so the status follows it rather than being written by hand.

A draft state exists because otherwise an ADR written on a branch, with code citing it, binds the
branch to a decision nobody reviewed and no requirement asked for. The status keeps a proposal
legible as a proposal; citing `ARCHITECTURE.md` keeps everything else free of it.
