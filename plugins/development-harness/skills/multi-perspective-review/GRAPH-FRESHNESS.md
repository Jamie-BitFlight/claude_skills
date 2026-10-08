# Workflow graph freshness and review boundary

This source change introduces the SourceCheck decision and abort terminal in the multi-perspective review dispatch. The generated DH workflow layers and `docs/dh-workflow-graph.json` do not yet represent it. They also predate the T5 synthesis route from #3207 and grooming changes recorded in #3223.

**Status: known stale generated documentation, not a validated workflow graph.** Do not silently treat the assembled graph as complete or source-faithful. The source skill and its referenced dispatch flow are the current procedure. This notice does not satisfy the graph refresh acceptance criterion.

The current `/dh:meta-workflow-graph-refresh` entry point documents the extraction process, but the retired extraction workers have not been replaced with a verified, executable producer. The assembler can rebuild only the existing layer inputs and therefore cannot repair missing semantic relationships.

Issue #3223 owns the end-to-end outcome: source-faithful extraction from complete workflows (Mermaid, prose, references, implicit handoffs), independent evidence checking, freshness and coverage accounting, and verified publication. Draft PR #4101 is an unverified partial reducer and must not be considered a complete replacement.

## Release decision

A reviewer should evaluate whether the missing generated topology is a release blocker based on the graph's actual consumers and the repository's governing gate. A pre-existing graph defect does not automatically justify suppressing a new material regression. Record both the new SourceCheck delta and the pre-existing T5/grooming gaps, with links to #3223. If any required consumer depends on the graph for execution or validation, keep the gate blocked until the graph is refreshed. If the graph is non-executable documentation and policy permits deferral, retain the explicit stale-state warning and track the missing refresh in #3223.

Do not hand-edit generated layers, claim that deterministic assembly equals semantic extraction, or require a speculative parser as the solution. The extractor architecture must be evaluated against complete source-to-graph behavior before further production implementation.
