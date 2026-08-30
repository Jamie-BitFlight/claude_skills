---
name: dh-meta-docs
description: Development harness plugin documentation index. Use when looking up SAM pipeline, backlog lifecycle, SDLC layers, task/plan schema, plan artifacts, quality gates, or dispatch schema documentation.
user-invocable: false
---

# Development Harness Documentation

<sam_cli>
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py"
</sam_cli>

<shared_reference_routing>
Load the smallest reference matching the task. This skill routes shared documentation; it does not
own or run the development-harness lifecycle.

- [Artifact Conventions](./references/artifact-conventions.md) — artifact naming, logical storage, and cross-reference tokens.
- [Default Development Flow](./references/default-development-flow.md) — S1–S7 sequencing, stage handoffs, and ARL gates.
- [DH CLI Usage Guide](./references/dh-cli-usage-guide.md) — grouped-command reference for the DH CLI adapter.
- [Human Touchpoint Model](./references/human-touchpoint-model.md) — whether a constraint requires human escalation.
- [Language Manifest Schema](./references/language-manifest-schema.md) — create or validate a language-plugin manifest.
- [Role Resolution Protocol](./references/role-resolution-protocol.md) — resolve abstract harness roles to language-plugin agents.
- [SDLC Stage Taxonomy](./references/sdlc-stage-taxonomy.md) — choose canonical stage names and `{domain}-{sdlc-stage}` identifiers.
- Severity Workflow-Continuity Lens, at ${CLAUDE_PLUGIN_ROOT}/docs/severity-workflow-continuity-lens.md — worked examples of the continuity lens for defect classification and impact analysis.
- Backlog Item Groomed Schema, at ${CLAUDE_PLUGIN_ROOT}/docs/backlog-item-groomed-schema.md — content rules and required Groomed-section structure for backlog-item-groomer output.
</shared_reference_routing>

Read any file above to learn about that topic. CLI examples in those docs use bare
grouped commands (e.g. `plan list`, `backlog groom`) — prefix them with the
`<sam_cli>` value above.
