---
name: meta-workflow-graph-refresh
description: Entry point for refreshing the DH workflow graph after changes to skills, agents, Mermaid flowcharts, MCP tools, or artifact flows. Use after any structural workflow change to keep docs/dh-workflow-graph.json current.
---

# Workflow Graph Refresh

The update process is fully documented in two files. Read them in order:

1. `${CLAUDE_SKILL_DIR}/../../docs/workflow-layers/COVERAGE.md` — identifies which layers are affected by your change type, the Tier 1 / Tier 2 update process, and what not to do

2. `${CLAUDE_SKILL_DIR}/../../docs/workflow-trace-methodology.md` — full extraction protocol including the ensemble pipeline, schema discipline, and collection phases
