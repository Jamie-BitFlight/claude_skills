# Layer 1 Overview

Layer 1 specializes the SDLC framework for a specific programming language. It inherits from Layer 0 and extends it with language-specific behavior only.

---

## Inheritance from Layer 0

**Layer 0 gates apply before role resolution.** Before the harness resolves language manifests:

1. RT-ICA prerequisite gate (AVAILABLE | DERIVABLE | MISSING)
2. Human touchpoint model (escalation triggers, loop limits)
3. Artifact conventions (ARTIFACT:{TYPE}({SCOPE}))
4. Verification protocol (producer vs evaluator, CERTIFIED/NOT_CERTIFIED)
5. Orchestrator discipline (delegation, no investigation escalation)

Language manifests **declare specialists and gates**. They do **not** redefine process.

---

## Layer 1 ≠ Layer 0 Boundary

| Layer 0 (Do not duplicate) | Layer 1 (Extend only) |
|----------------------------|------------------------|
| SAM 7-stage pipeline | Process Flow Override (optional, rare) |
| Human touchpoint model | — |
| Artifact conventions | — |
| RT-ICA, verification | — |
| SAM task schema (`models.py`) | — |
| Subagent contract | — |
| — | Role Fulfillment (architect, test-designer, etc.) |
| — | Quality Gates (format, lint, typecheck, test, standards) |
| — | Project Detection (markers, source/test patterns) |
| — | Conventions (naming, structure, testing, documentation) |
| — | Language standards (e.g., modernpython) |

---

## CoVe Bypass Anti-Pattern

Orchestrators pass paths and outcomes; agents discover and verify. Do not pre-gather data for agents. Layer 1 skills must not instruct orchestrators to read source files for agents.

---

## Non-Typed Languages

For languages without static typing (e.g., Bash, Perl without strict typing), use `typecheck: (none)` in Quality Gates. The harness skips the typecheck gate when `(none)` is declared.
