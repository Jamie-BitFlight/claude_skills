# Layer 1: Language-Specific

Layer 1 extends Layer 0 with language-specific steps, conventions, and tooling. It does **not** redefine SAM stages, human touchpoints, or artifact conventions.

---

## What Belongs Here

| Content | Description |
|---------|-------------|
| **Language manifest** | Role fulfillment, quality gates, project detection |
| **Abstract roles** | architect, test-designer, code-reviewer, design-spec, linting |
| **Quality gate commands** | format, lint, typecheck, test, standards |
| **Project detection** | Markers, source/test patterns |
| **Language standards** | e.g., modernpython, stinkysnake for Python |
| **Conventions schema** | naming, structure, testing, documentation rules |

---

## What Does NOT Belong Here

- SAM 7-stage pipeline definition (Layer 0)
- Human touchpoint model (Layer 0)
- Artifact conventions (Layer 0)
- RT-ICA, verification protocol (Layer 0)

---

## Documents

| Document | Purpose |
|----------|---------|
| [layer-1-overview.md](./layer-1-overview.md) | Inheritance from Layer 0, Layer 1 ≠ Layer 0 boundary |
| [language-manifest-template.md](./language-manifest-template.md) | Canonical starting point for manifests |
| [linting-discovery-protocol.md](./linting-discovery-protocol.md) | Discovery sequence before quality gates |
| [workflow-pattern-taxonomy.md](./workflow-pattern-taxonomy.md) | TDD, Feature Addition, Code Review, etc. |
| [harness-role-mapping.md](./harness-role-mapping.md) | Abstract roles → agent archetypes |

---

## Sources

- [language-manifest-schema.md](../../../skills/dh-meta-docs/references/language-manifest-schema.md)
- [role-resolution-protocol.md](../../../skills/dh-meta-docs/references/role-resolution-protocol.md)
