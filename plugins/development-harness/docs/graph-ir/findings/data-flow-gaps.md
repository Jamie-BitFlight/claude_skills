# Findings: producers without consumers between grooming and the bookends

**Found-by:** hand
**Previously-known:** no
**Date:** 2026-09-07
**Assessed:** the pipeline from grooming and architecture through to the verification bookend, as
it exists in `skills/` and `agents/` today. Not the graph IR.

Recorded here so the IR cannot later report these as new. Under ADR-3460-1 the migration to
scenario A requires the IR to find a defect nobody had already found; these are found, by hand,
before the IR existed. A finding qualifies for that criterion only with `Found-by: IR` **and**
`Previously-known: no`, and these carry `Found-by: hand`.

## DF-1 — `File Impact Summary` is produced and consumed by nothing

**Predicate falsified:** a produced output has no consuming edge.
**Severity:** BROKEN.

`skills/context-integration/SKILL.md` Step 4 appends a `File Impact Summary` to the `architect`
artifact — files to create, files to modify, files unchanged. A grep of `skills/` and `agents/`
for `File Impact Summary` returns only the skill that writes it. No downstream step reads it.

The plan's own scope analysis, with file paths and line ranges, sits in the same artifact and is
equally unread.

## DF-2 — `Resource Map` reaches one consumer, for one of its four purposes

**Predicate falsified:** a produced output is unused in part.
**Severity:** BROKEN for the unread columns; the table declares utilities, patterns,
configuration and tests, and only patterns is consumed.

`skills/task-decomposition/SKILL.md:60` reads "Patterns to follow (from resource map)". Nothing
reads the utility, configuration or test rows.

## DF-3 — there is no documentation-check bookend

**Predicate falsified:** a required intent claim reaches no implementing path.
**Severity:** CONTRACT_UNSPECIFIED. The requirement is stated in
`docs/graph-ir/ASSESSOR-CONTRACT.md` as the target, not by the current system, so nothing here is
demonstrably false about the implementation — it simply has no such step to check.

`BookendType` in `sam_schema/core/models.py:121` admits exactly `t0-baseline` and
`tn-verification`. There is no review, validate or documentation-check bookend. A grep of
`skills/` and `agents/` for a documentation-check bookend returns nothing.

`agents/doc-drift-auditor.md` exists and is referenced from `skills/complete-implementation` and
`skills/create-artifact`, but not as a bookend on a plan's graph, so no plan structurally requires
a documentation check to have happened.

## DF-4 — the verification bookend cannot know which documents the diff should have updated

**Predicate falsified:** a required input has no producer reaching the consumer.
**Severity:** BROKEN, conditional on the intent in DF-3 being the requirement.

`agents/tn-verification-gate.md` Step 1 names exactly two inputs: the `T0-baseline` artifact and
the plan's `acceptance-criteria-structured`. It never reads the `File Impact Summary`, the
`Resource Map`, or any mapping of documents that mention the affected system.

So a bookend asked "which documents should this diff have updated" has no input that could answer
it, while the nearest producer (DF-1) emits an impact map that reaches nobody. Producer and
consumer both partially exist and are not connected.

## Why these were invisible

Each is a DATA edge defect: an output produced by one node and required — or that should be
required — by another. The system represents no DATA edges. `dependencies` carries CONTROL and
nothing else, so an artifact produced and never consumed is not a broken link in any structure the
system holds; it is simply a section in a markdown document that nobody opens.

This is the same root as the two authority defects ADR-3460-1 cites, in a different edge type.

## What this constrains in the IR

The contract's layer-2 bookends (review, validate, documentation-check) describe the target, not
the system. The IR must not record them as OBSERVED. Their `extraction_status` is the difference
between modelling what exists and modelling what was intended, and DF-3 is precisely where that
distinction decides whether a later finding is BROKEN or CONTRACT_UNSPECIFIED.
