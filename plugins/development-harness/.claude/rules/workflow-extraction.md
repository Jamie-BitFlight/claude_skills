---
paths:
- docs/workflow-layers/**
- docs/workflow-trace-methodology.md
---

# Workflow Extraction Rules

When running any workflow-mapping, trace collection, or gap-layer pass on the
development-harness plugin:

## Trust boundary — the core rule

**Single haiku worker output is never trusted directly.**
Unvalidated extraction data is equivalent to a guess — there is no way to tell which
fields are accurate and which are hallucinated. Data enters a layer JSON file only after:

1. 3 haiku workers extract independently with overlapping rule slices (2x coverage per rule)
2. `reduce.py --keep-threshold 2` corroborates — items found by only 1 worker are
   isolated as `unverified_items`, never promoted to the main data set
3. A sonnet reducer assembles the layer JSON and self-checks source citations

This is the ensemble pattern from `plugin-creator:ensemble-rule-review`. The full
methodology is in `docs/workflow-trace-methodology.md`.

## Agent roles

Extraction agents are pending redesign (see the PRD at [../../docs/plans/prd-workflow-extractor.md](../../docs/plans/prd-workflow-extractor.md)).
Do not use `general-purpose` for any extraction role.
Do not write worker output directly to a layer JSON without corroboration.

## Existing layer data (collected 2026-06-08)

The L0–G8 JSON files were collected by single-pass haiku agents without ensemble
validation. They are **unverified** by the standard above. Treat them as useful
starting hypotheses, not ground truth. Re-extract any layer where accuracy is
load-bearing for a task.

## Schema discipline

Do not write a schema before reading the source files. The correct order is:
1. Read source files (or use existing collected data in `docs/workflow-layers/`)
2. Observe what structure is actually present
3. Derive the schema from the observed structure
4. Extract into the derived schema

## Coverage manifest

Before any collection pass, read `docs/workflow-layers/COVERAGE.md`. It records what is
already collected, the update process for each tier of change, and how to scope gaps
without restarting the whole collection.

## Source structure

DH workflow files are a graph-of-graphs. A Mermaid node that says "Load X.md" is an
expansion link — follow it into the referenced file and continue reading. Do not record
it as a step and stop. The full methodology is in `docs/workflow-trace-methodology.md`.
