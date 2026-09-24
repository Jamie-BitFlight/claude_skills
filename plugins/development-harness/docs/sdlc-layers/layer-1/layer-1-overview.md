# Layer 1 Overview

Layer 1 specializes the SDLC framework for a specific programming language. It inherits from Layer 0 and extends it with language-specific behavior only.

---

## Inheritance from Layer 0

**Layer 0 gates apply before role resolution.** Before the harness resolves roles:

1. RT-ICA prerequisite gate (AVAILABLE | DERIVABLE | MISSING)
2. Human touchpoint model (escalation triggers, loop limits)
3. Artifact conventions (ARTIFACT:{TYPE}({SCOPE}))
4. Verification protocol (producer vs evaluator, CERTIFIED/NOT_CERTIFIED)
5. Orchestrator discipline (delegation, no investigation escalation)

Layer 1 plugins provide language-specific agents and skills. The harness finds their agents at
runtime with `mcp__plugin_dh_backlog__profile_list()`. Layer 1 plugins do **not** redefine process.

---

## Layer 1 ≠ Layer 0 Boundary

| Layer 0 (Do not duplicate) | Layer 1 (Extend only) |
|----------------------------|------------------------|
| SAM 7-stage pipeline | — |
| Human touchpoint model | — |
| Artifact conventions | — |
| RT-ICA, verification | — |
| SAM task schema (`models.py`) | — |
| Subagent contract | — |
| — | Specialist agents (found by `profile_list()`) |
| — | Stack review skills (`dh:code-review-{stack}`) |
| — | Quality gate commands (found in the repository's pre-commit config, CI workflow, or build config) |
| — | Language engineering entrypoints (e.g., `python-engineering:orchestrate`; broad Python quality/modernization audits use `python-engineering:python-quality-audit`) |

---

## CoVe Bypass Anti-Pattern

Orchestrators pass paths and outcomes; agents discover and verify. Do not pre-gather data for agents. Layer 1 skills must not instruct orchestrators to read source files for agents.

---

## Non-Typed Languages

Languages without static typing (e.g., Bash, Perl without strict typing) have no typecheck gate. Skip the typecheck gate for these languages.
