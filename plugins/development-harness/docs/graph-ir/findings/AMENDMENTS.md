# Amendments to the findings files

The findings files in this directory are immutable. `ASSESSOR-CONTRACT.md` ("Validating the
report"): "The findings document is untrusted and immutable. A verifier issues amendments or
counter-findings and never silently rewrites it." So a finding that has since gone stale is
superseded here, not edited there.

## A-1 — the predicate counts in `predicates.md` and `completeness.md` are superseded

**Date:** 2026-09-07
**Cause:** commit `206b794f` added a bullet to the contract's "Falsified predicates to report"
list. Every sentence that tallied that list was written before it and is unchanged, so none of
them appears in that commit's diff.

Superseded, in `predicates.md`: the statement that the contract's bullets and `PREDICATES`
correspond one for one and the tally either side of it; the PREDICATES-1 heading's count of
predicates without a query; the quoted `contract lists N predicates` output, whose count and
message text both changed; and the claim that the correspondence "holds today", which was a claim
about 2026-09-06.

Superseded, in `completeness.md`: the tally of predicates carrying a `Graph` method.

Also superseded, in `predicates.md`: the observation that `docs/graph-ir/` contains exactly one
file. That was a fact about a `find` run on 2026-09-06 and the directory has since gained
`STAGE-INTENT.md` and this `findings/` subtree. The search was stated, which is what makes the
supersession checkable rather than a contradiction.

The findings themselves stand. What is superseded is arithmetic over a list that has since grown,
which is why none of it should have been written as a number in the first place — see
`.claude/CLAUDE.md`, "No Derived Data in Documentation".

**Recompute rather than reading a number from prose:**

```bash
uv run python -c "from dh_core.graph_ir.findings import PREDICATES; print(len(PREDICATES))"
uv run pytest plugins/development-harness/tests_sam/test_adr_3460_migration_trigger.py -q
```

The migration trigger now derives the comparison itself: `unexpressible_predicates()` reads the
contract's bullets and the enum's statements at call time and names any that do not correspond, so
criterion 2 cannot drift the way this prose did.

## A-2 — `fidelity.md`'s `ledger_spec.py` element counts are a 2026-09-06 measurement

**Date:** 2026-09-07
**Cause:** none — no change has invalidated them. Recorded because they are derived values with no
stated as-of, and a reader cannot tell that from the sentence.

The statuses, commands, event kinds, reason codes and transitions `fidelity.md` tallies are counts
of `dh_core/ledger_spec.py`'s tables as they stood on 2026-09-06. Read the tables, not the tally.
The finding they support — that none of those elements is a node in any of the defect graphs — does
not depend on the arithmetic.

## A-3 — the ADR these findings were scored against was withdrawn as an unreviewed draft

**Date:** 2026-09-07
**Cause:** the ADR these findings cite as their authority — a draft proposing that the graph IR
first own the edge types nothing else in the harness owns — was authored and cited on this branch
while under review, never merged, and was withdrawn and its file deleted before merge, per
`rules/adr-lifecycle.md`: an ADR on an unmerged branch may be withdrawn and deleted rather than
superseded, because nothing outside the branch had built on it. Per the repository owner's
standing instruction, no documentation, test, or code in this repository — including this
amendment — links to or depends on an ADR file; a decision, once settled, belongs in the code and
in a design document describing the outcome, not in the deliberation record. So this entry states
the substance the withdrawn draft's criteria rested on directly, rather than pointing anywhere for
it.

**The decision now in force, stated directly.** The graph is one multigraph, described as node
types and their permitted relations and executed as instances conforming to that description —
not, as the withdrawn draft framed it, a choice between a task lifecycle, a work graph and a
workflow modelled and joined separately. Execution state is a property of a node, not of a
separate graph: `ledger_spec.TRANSITIONS` is the lifecycle a node instance runs through, and the
ledger is the instance store, not something a graph derives by projection.

Superseded, in `predicates.md`: every citation of the withdrawn draft as the authority for the
expressibility obligation — the header's "Authority" line and its quoted sentence, each finding's
"Basis DECLARED — [that draft] ..." line, and the closing reference to the draft itself in the
out-of-scope grep. The predicates the contract lists, the IR's queries, and this document's
verdicts on each stand unchanged — a citation of the withdrawn draft's file path or line numbers is
what no longer resolves, not the finding it supports.

Superseded, in `fidelity.md`: every citation of one of the withdrawn draft's numbered exit criteria
as declaring the predicate a finding falsifies, the summary table's per-criterion verdicts, and the
references to the draft's "Decision" and "Decision C" in FIDELITY-10 and FIDELITY-13. One of those
criteria — that a control-flow projection reproduce `ledger_spec.TRANSITIONS` exactly — does not
merely go unmet now; per the decision stated above, it was ill-posed from the start, because
`TRANSITIONS` is an instance lifecycle rather than a projection a graph could ever reproduce.
FIDELITY-10's finding is scored against that criterion, which no longer stands as written. The
observations underneath every other finding — which fields are read, which edge types are inert,
which source spans are bare — stand independent of which draft is cited as authority; what is
superseded is the citation, not the observation.

Superseded, in `data-flow-gaps.md`: the statement that the withdrawn draft's staged migration
"requires the IR to find a defect nobody had already found" — that staged placement is withdrawn in
full, not only the projection criterion above — and the closing reference to "the two authority
defects [the draft] cites". The DF findings themselves, and their predicates and severities, stand.

What this does not settle: the withdrawn draft's other numbered exit criteria (defects
refused-or-detected, predicates expressible, model-fidelity, IR-found-something-new) are not
restated anywhere in a form addressed to a specific migration scenario, because the staged
placement that gated them is withdrawn along with the projection criterion. Whether a readiness
gate of that shape still has a subject, and what it should require, is open and is not decided
here.

**Recompute or re-read rather than trusting a citation in prose:**

```bash
uv run pytest plugins/development-harness/tests_sam/test_adr_3460_migration_trigger.py -q
```

That test still reads the withdrawn draft's file from disk and asserts it exists; deleting that
file without also deciding the test's fate is expected to fail it. See the commit or PR history
for this branch, not an ADR file, for the currently intended graph model and its rationale.
