---
name: mermaid-js
description: Use when selecting a Mermaid diagram type, looking up Mermaid syntax, adapting a Mermaid example, or locating a Mermaid reference for a flowchart, sequence, UML, architecture, chart, or other diagram.
---

# Mermaid.js Reference Router

Use this skill to navigate the bundled Mermaid reference snapshot. It supplies syntax and examples; choose the diagram semantics from the request and keep architecture or process-modeling decisions with their owning skill.

## Reference status

The bundled documents are a dated snapshot of Mermaid v11.12.3, recorded on 2026-03-07. They are not evidence of the latest Mermaid syntax or renderer behavior. For a current-version question, a renderer-specific issue, or a claim about present support, consult the [official Mermaid documentation](https://mermaid.js.org) and the target renderer's documentation before answering.

## Route the request

| Need | Read |
| --- | --- |
| Declaration, common edges, styling, or a compact example | [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) |
| Choose a diagram type or compare diagram capabilities | [DIAGRAM_INDEX.md](./DIAGRAM_INDEX.md) |
| Full syntax, configuration, or versioned feature details | [mermaid-diagram-reference.md](./mermaid-diagram-reference.md) |
| Adapt a domain example for API, project, data, architecture, UX, testing, database, or decision work | [COOKBOOK.md](./COOKBOOK.md) |
| Snapshot scope, navigation, and primary-source links | [README.md](./README.md) |

Load only the reference needed for the request. Do not copy reference material into this router.

## Related ownership

Use an architecture or process skill to decide what the diagram should represent; this skill only routes Mermaid reference material. The existing `process-siren:mermaids-treasure` material remains a specialized companion for constructing or debugging Mermaid diagrams, especially flowchart constraints. It does not replace this bundle's cross-diagram routing, cookbook, or dated snapshot references.
