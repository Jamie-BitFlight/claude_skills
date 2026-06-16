---
name: project_workflow_extractor_cross_plugin_pattern
description: DH workflow extractor system uses plan_ensemble.py and reduce.py from plugin-creator plugin — cross-plugin dependency risk; reduce.py output schema change affects both plugins
metadata:
  type: project
---

plan_ensemble.py and reduce.py live in `plugins/plugin-creator/skills/ensemble-rule-review/scripts/`, NOT in the DH plugin. The DH workflow extractor invokes them as shared infrastructure.

**Why:** ensemble-rule-review is the canonical source of these deterministic bookend scripts. DH reuses them rather than duplicating.

**How to apply:** When assessing changes to reduce.py or plan_ensemble.py, always check both plugin-creator (owner) and DH (consumer) for compatibility. A schema change to reduce.py output breaks both. The cross-plugin path must also resolve correctly in headless `-p` context where `CLAUDE_PLUGIN_ROOT` differs from session context.

Key structural facts (verified 2026-06-16):
- workflow-extractor-worker.md, workflow-extractor-reducer.md, workflow-extractor.md do NOT exist in agents/; removed by commit `fix(dh): remove fabricated workflow-extractor agents`
- KNOWN_ENTITIES.md still lists all three as canonical agents — inconsistency is a known gap
- workflows/ directory does not exist in the DH plugin — JS workflow must be created
- hooks/hooks.json handles Claude Code lifecycle events only; post-commit git hook must go in prek or .git/hooks separately
- assemble_graph.py is in docs/ not scripts/ — unconventional placement; reads only JSON, no markdown parsing capability yet
- dh-workflow-explorer.html renders dh-workflow-graph.json via Cytoscape.js and requires UI changes for new node/edge types

See [[project_plugin_creator_consumer_chains]] for broader plugin-creator consumer chain context.
