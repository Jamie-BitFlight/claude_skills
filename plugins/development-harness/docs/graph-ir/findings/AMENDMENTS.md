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
