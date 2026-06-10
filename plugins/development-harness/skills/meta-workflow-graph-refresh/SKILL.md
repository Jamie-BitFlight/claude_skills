---
name: meta-workflow-graph-refresh
description: Refreshes the DH workflow graph after changes to skills, agents, Mermaid flowcharts, agent dispatch patterns, MCP tool calls, or artifact flows. Use when docs/dh-workflow-graph.json needs to be brought up to date after structural workflow changes.
---

# Workflow Graph Refresh

The DH plugin maintains a machine-readable graph of its own workflow in
`docs/dh-workflow-graph.json`. Run this process after any change that affects
workflow structure.

## When to run

- New skill or agent added
- Mermaid diamond node (decision fork) added or changed in any skill or reference file
- Agent dispatch pattern changed (new `subagent_type`, new `TeamCreate`)
- MCP tool added, removed, or renamed
- Artifact type added or changed

## Steps

**1. Check what's stale**
Read [COVERAGE.md](../../docs/workflow-layers/COVERAGE.md) — records which
layers are current and which source files have changed since last extraction.

**2. Identify the affected layer**

| Change type | Layer |
|---|---|
| Decision fork in Mermaid | L0, L1 |
| Artifact produced or consumed | G2 |
| Agent dispatched (TeamCreate / subagent_type) | G4 |
| MCP tool called | G8 |

**3. Run extraction**
Use `dh:workflow-extractor` for each stale source file and layer type.
The ensemble runs 3 haiku workers + 1 sonnet reducer — do not write layer
JSON directly. Provide `SOURCE_FILE`, `LAYER_TYPE`, `OUTFILE`, and `REPORT_DIR`.

**4. Rebuild the graph**

```bash
uv run plugins/development-harness/docs/assemble_graph.py
```

**5. Update COVERAGE.md**
Record the files refreshed, date, and layer type.

## Reference files

- [COVERAGE.md](../../docs/workflow-layers/COVERAGE.md) — current extraction state; read before starting
- [workflow-extractor agent](../../agents/workflow-extractor.md) — ensemble orchestrator; the only way to run extraction
- [workflow-trace-methodology.md](../../docs/workflow-trace-methodology.md) — full ensemble protocol and trust model
- [graph-schema.md](../../docs/graph-schema.md) — node and edge type definitions
- [extraction-rules.json](../../docs/workflow-layers/extraction-rules.json) — 6 rule groups given to haiku workers
