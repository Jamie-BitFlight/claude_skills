# ADR-3460-1: The graph IR first owns the edge types nothing owns, and becomes the domain model once it earns it

**Status:** Accepted
**Date:** 2026-09-06
**Issue:** [#3460](https://github.com/Jamie-BitFlight/claude_skills/issues/3460)
**Related:** Governed by
[ASSESSOR-CONTRACT.md](../graph-ir/ASSESSOR-CONTRACT.md). Constrains ADR 2 of
[#3449](https://github.com/Jamie-BitFlight/claude_skills/issues/3449), which is not yet written:
when it establishes the ledger as the source of truth for plan and task state, it must record
that `ledger_spec.TRANSITIONS` is a derived control-flow projection rather than a hand-maintained
source. Cross-link the two once that ADR exists.

## Context

The plan and task graph encodes relationships as node attributes. `dependencies` is CONTROL,
`conflict_group` is STATE mutual exclusion, `is_bookend`/`bookend_type` is EVIDENCE. A grep of
`dh_core`, `sam_schema` and `backlog_core` excluding tests, 2026-09-06, found `blocked_by` and
`parallelize_with` read only by models, writers, backends and `cli_inputs` — serialized
everywhere, deciding nothing. AUTHORITY, DATA, ERROR, RECOVERY and INVALIDATES have no
representation.

Four defects found on this branch trace to that flattening, and two of them were fixed as
separate bugs when they are one authority defect: `import` writing a judge's `accepted` over a
runner's `complete`, and `update --set status=complete` performing a control transition as a data
write. The other two are a DATA edge missing (`FILES_CHANGED` overlap is prose a judge must
eyeball) and an INVALIDATES edge missing (`--replace` deleting rows no event accounted for).

`ledger_spec.TRANSITIONS` answers reachability and guard coverage and nothing else. It is a
control-flow projection that was made the source of truth, which is why the review passes over it
could find structural drift and could not find two nodes agreeing on schema while disagreeing on
meaning.

Three placements were considered. **A**: the IR replaces `Task`/`Plan`, which moves 71 importing
files, 7 `TaskBackend` implementations across 10 backend modules, 3 MCP tools, 44 skill and agent
files, and every stored plan record. **B**: the IR is compiled above unchanged models, which moves
nothing but can only carry what the source records carry — AUTHORITY, DATA, EVIDENCE, ERROR,
RECOVERY and INVALIDATES would compile empty, so it answers the structural questions that were not
hurting and stays silent on the semantic class that was. **C**: the IR owns the six unowned edge
types inside the ledger while CONTROL and STATE keep their current homes.

## Decision

**C first. A once C is functional.**

C lives in the work ledger, which already has an event log, materialised tables and a conformance
suite. No backend, MCP schema, skill file or stored record moves. `ledger_spec.TRANSITIONS`
becomes derived from the IR rather than hand-maintained.

B is rejected outright, at either stage: a representation that cannot express authority cannot
find the defect class that motivated the work.

## The dual-home period, and how it ends

C deliberately accepts two homes for relationships — CONTROL on the node as `dependencies`, the
other six as edges. This is the duplication this branch has otherwise been removing, and without
an exit condition it becomes permanent.

A begins when all of the following hold, and the migration is not started before them:

1. Each of the four defects in the Context is either unrepresentable in the IR or detected by a
   named predicate, proven by a test that fails when the defect is reintroduced.
2. Every falsified predicate in the assessor contract is expressible against the IR, or is
   recorded there as out of scope with the reason.
3. The control-flow projection derived from the IR reproduces `ledger_spec.TRANSITIONS` exactly,
   so the hand-maintained table can be deleted rather than kept in sync.
4. A model-fidelity pass confirms the extractor neither repaired an ambiguity nor dropped a
   branch, per the contract's first validation activity.
5. The IR has caught at least one defect not already known — the evidence that it generalises
   rather than fitting the four cases it was built against.

Criterion 5 is the one that can fail quietly. If the IR only ever confirms defects already found
by hand, it has not earned the 71-file migration, and this ADR should be revisited rather than
proceeded from.

## Consequences

Accepted: two homes for relationships until the criteria are met; a second schema to keep
coherent with the ledger's tables; `blocked_by` and `parallelize_with` stay dead in the records
until A removes them, because C does not touch the models.

Gained at C: authority becomes checkable, so the two defects fixed separately become one
unrepresentable shape; the TN send-back's file overlap becomes computable rather than a prose
instruction; and the mechanical checks in the contract become available against real plans.

Deferred to A: the models, the backends, the MCP surface and the skills.
