---
paths:
- docs/workflow-layers/**
- agents/workflow-extractor.md
- docs/workflow-trace-methodology.md
---

# Workflow Extraction Rules

When running any workflow-mapping, trace collection, or gap-layer pass on the
development-harness plugin:

## Agent selection

Use `subagent_type="dh:workflow-extractor"` for ALL extraction agents.
NEVER use `subagent_type="general-purpose"` for this work.

**Reason:** `general-purpose` agents carry ~100k tokens of tool/skill/MCP descriptions
that add noise and cost for every agent invoked. workflow-extractor is haiku model with
`Read, Grep, Glob, Write, Edit, Bash` — enough for any extraction task at a fraction of
the cost.

## Schema discipline

Do not write a schema before reading the source files. The correct order is:
1. Read source files (or use existing collected data in `docs/workflow-layers/`)
2. Observe what structure is actually present
3. Derive the schema from the observed structure
4. Extract into the derived schema

A schema written before reading source encodes the author's beliefs, not the system's
structure. Both pre-2026-06-08 collection passes made this mistake.

## Coverage manifest

Before any collection pass, read `docs/workflow-layers/COVERAGE.md`. It records what is
already collected. A follow-up question maps to a layer in the manifest:
- COLLECTED → query that layer's JSON file, answer with citations
- GAP → scope the missing pass; do not restart everything

## Source structure

DH workflow files are a graph-of-graphs. A Mermaid node that says "Load X.md" is an
expansion link — follow it into the referenced file and continue reading. Do not record
it as a step and stop. The full methodology is in `docs/workflow-trace-methodology.md`.
