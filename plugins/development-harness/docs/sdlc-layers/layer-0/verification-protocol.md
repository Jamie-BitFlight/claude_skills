# Verification Protocol

Producer vs evaluator separation. S5 Execution implements; S6 Forensic Review verifies. Do not rely on self-critique alone.

---

## Verdicts

| Stage | Verdicts |
|-------|----------|
| S6 Forensic Review | COMPLETE / NEEDS_WORK |
| S7 Final Verification | CERTIFIED / NOT_CERTIFIED |

---

## verification-gate (Pre-S5)

Before S5 Execution self-verification, run 4 checkpoints before any Bash/Write/Edit/NotebookEdit:

1. **Hypothesis Stated** — Explicitly state what system/component the issue affects
2. **Hypothesis Verified** — Gather evidence (Read, Grep, MCP tools)
3. **Hypothesis-Action Alignment** — Action targets same system as hypothesis
4. **Pattern-Matching Detection** — Verified against project reality, not training data

---

## verify Skill (Completion Checklist)

Before claiming task complete:

- Task type & strategy
- "WORKS" check (executable or static)
- "FIXED" check (for bug fixes)
- Quality gates (pre-commit, lint, typecheck)
- Honesty check

**Golden rule**: If you cannot demonstrate it working with evidence, it is NOT done.

---

## Sources

- [verify-done SKILL.md](../../../skills/verify-done/SKILL.md)
- `verification-gate:verification-gate` skill (separate plugin; load it when installed)
