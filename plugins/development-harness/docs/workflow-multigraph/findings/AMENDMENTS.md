# Amendments to the findings files

The findings files in this directory are immutable — the same rule `dh_core/workflow_multigraph/findings.py`'s
module docstring states of a `Finding`: "the findings document is untrusted and immutable: a
verifier issues amendments or counter-findings and never silently rewrites it." So a finding that
has since gone stale is superseded here, not edited there.

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

Also superseded, in `predicates.md`: the observation that `docs/workflow-multigraph/` contains exactly one
file. That was a fact about a `find` run on 2026-09-06 and the directory has since gained
`STAGE-INTENT.md` and this `findings/` subtree. The search was stated, which is what makes the
supersession checkable rather than a contradiction.

The findings themselves stand. What is superseded is arithmetic over a list that has since grown,
which is why none of it should have been written as a number in the first place — see
`.claude/CLAUDE.md`, "No Derived Data in Documentation".

**Recompute rather than reading a number from prose:**

```bash
uv run python -c "from dh_core.workflow_multigraph.findings import PREDICATES; print(len(PREDICATES))"
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
gate of that shape still has a subject, and what it should require, was open when this entry was
first drafted; it has since been resolved by deleting `tests_sam/test_adr_3460_migration_trigger.py`
outright, on the grounds that it read the withdrawn ADR from disk and enforced its criteria as
tests, and parsed the markers above out of markdown by regex — coupling executable checks to a
deliberation document and to prose that could satisfy a marker by mentioning it. The criterion
worth keeping — that the IR must catch a defect nobody had already found — is no longer recorded
anywhere as a marker a findings file carries: the "Markers a findings file carries" table
(`Found-by:` / `Previously-known:`) was scaffolding for the one-off exercise and was dropped, not
moved, when `ASSESSOR-CONTRACT.md` was deleted (see A-5 below). It remains unstated until it is
re-recorded against structured data (`Finding` in `dh_core/workflow_multigraph/findings.py`) that a test can
assert on directly.

**Re-read rather than trusting a citation in prose:** see the commit or PR history for this branch,
not an ADR file, for the currently intended graph model and its rationale; and
`dh_core/workflow_multigraph/findings.py` for the structured form the deleted test's markers are meant to be
replaced by.

## A-4 — the findings assess a three-layer model the design has replaced

**Date:** 2026-09-07
**Cause:** the repository owner rejected the premise that the system is several graphs. There is one
multigraph, traceable end to end, whose parts loop back, branch on decisions and expand as detail is
needed, spanning grooming fan-out and report synthesis through to closure. `ASSESSOR-CONTRACT.md`
now states that model; the layers it stated when these findings were written are gone.

Every finding here scoped to the layer split — a task-lifecycle layer, a work-graph layer, a
workflow layer, and the cross-layer references between them — describes a structure that no longer
exists as a design. The findings may still hold as observations about the code at the date they were
made; their frame does not.

What replaced it, and what a re-run would be scored against:

- One graph, described as **types** and executed as **instances**. Expansion is instantiation of a
  declared type, which is what keeps a graph that grows at runtime checkable.
- The **actor** is an attribute of a node. **Execution state** is a property of a node, not a graph;
  `ledger_spec.py`'s transitions are a node's lifecycle, so no projection derives them from the work
  graph and any criterion asking for one is ill-posed.
- **Containment and precedence are different relations**; a single parent field destroys joins.
- **Guards sit on edges** over a declared output, not inside a node. n8n evaluates them inside the
  node and the consequence is recorded in `CLAIMS-REGISTER.md`: which edge is live cannot be read
  off the graph.
- **Graph mutation requires authority**, and **removal is an invalidation cascade**.

Two things these findings rest on are also gone. The `Found-by: IR` and `Previously-known: no`
markers satisfied a readiness criterion that no longer exists — it was invented during this work
rather than required, the ADR carrying it was withdrawn, and the test reading it is deleted. And the
package name `workflow_multigraph` is a misnomer: an intermediate representation is a form between a source and
a target, and this is the structure itself. A rename is pending and no target name is settled.

**Re-read rather than trusting the frame:** `plugins/development-harness/ARCHITECTURE.md`, "The
work graph" heading, for the model — and the same file's "The workflow" heading for the closure
checks the model must carry. (`ASSESSOR-CONTRACT.md`, cited here when this entry was written, has
since been deleted in full; see A-5 below for where its content went.)

## A-5 — `ASSESSOR-CONTRACT.md`, the authority these findings cite, has been deleted

**Date:** 2026-09-07
**Cause:** `ASSESSOR-CONTRACT.md` was an ephemeral brief written for a one-off subagent exercise
that was wrongly committed and then acquired dependents. It has been deleted outright, not
superseded by a successor document at the same path.

Every citation of `ASSESSOR-CONTRACT.md` in this directory — including A-4's own closing pointer
above, and every "Authority" line and inline quote throughout `predicates.md`, `fidelity.md`,
`completeness.md` and `data-flow-gaps.md` — now names a file that does not exist. The findings
themselves stand; what no longer resolves is the path cited as where to re-read their authority.

**Where its architecture content went.** The document's description of the model — one graph,
described as types and executed as instances; what belongs to a node and an edge; edge types; the
node record; provenance; the decomposition-exit gate and its tiers; falsified predicates; the
severity rule; projections; mechanical checks — now lives in
`plugins/development-harness/ARCHITECTURE.md` under the "The work graph" heading, in the
subsections named there. A citation of `ASSESSOR-CONTRACT.md` for any of that content should be
read as citing the matching subsection of "The work graph" instead.

**What was dropped rather than moved.** Two kinds of content had no destination:

- The document's own audit-process instructions for a verifier — how to trace, how to weigh a
  finding holistically, how to validate a report, and the marker table a findings file was to
  carry (`Found-by`, `Previously-known`, and the like). This was scaffolding for the one-off
  exercise the document was written for, not a statement about the system under assessment, and
  ARCHITECTURE.md carries no equivalent of it.
- The document's own bullet list of falsified predicates. It was a second encoding of
  `Predicate` and `PREDICATES` in `dh_core/workflow_multigraph/findings.py`, kept in sync by hand against the
  enum; `tests_sam/test_decomposition_gate.py` used to assert the two matched, which is the closure
  A-1 above concerns. That test and its parsing helper are deleted along with the list itself:
  `dh_core/workflow_multigraph/findings.py` is now the only place the predicates are named.

**Re-read rather than trusting a citation in prose:** `plugins/development-harness/ARCHITECTURE.md`,
"The work graph" heading, for the current model; `dh_core/workflow_multigraph/findings.py` for the predicates
a check may report.

## A-6 — the citations named in A-5 have now been repointed, not merely documented as broken

**Date:** 2026-09-07
**Cause:** A-5 recorded that every `ASSESSOR-CONTRACT.md` citation across this directory no longer
resolves, and where the content went, but left the citations themselves unedited on the reasoning
that findings files are immutable. That reasoning rested on a rule `ASSESSOR-CONTRACT.md` itself
declared ("Validating the report": findings are untrusted and immutable); with that document
deleted, the rule survives only where a successor states it — `dh_core/workflow_multigraph/findings.py`'s
module docstring, quoted at the top of this file — and nothing there extends immutability to a
citation's *target* once that target stops existing. A citation is a pointer, not a finding; fixing
where it points changes no observation, no basis, and no severity.

`predicates.md`, `fidelity.md`, `completeness.md` and `data-flow-gaps.md` have accordingly been
edited directly, following the routing A-5 already set out: a citation of moved content now names
the matching subsection of `plugins/development-harness/ARCHITECTURE.md`'s "The work graph" by
heading, never by line number; a citation of a specific falsified predicate now names the
`Predicate` member in `dh_core/workflow_multigraph/findings.py`; a citation of dropped content (traces,
holistic evaluation, the report-validation activities, the findings-marker table) has been replaced
by the substance stated inline, so the finding stands on its own without a file to point at. No
finding's observation, basis, or severity was changed in the process. Two findings whose citation
could not be repointed without changing what they claim were left as A-5 found them and are noted
in place: PREDICATES-1's `find docs/workflow-multigraph -type f` result (already separately superseded by
A-1's note that the directory has since gained files) and any citation naming the withdrawn
edge-ownership draft, which A-3 already covers and this entry does not reopen.
