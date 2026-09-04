# RT-ICA Gate

Mandatory pre-planning checkpoint — see `dh:rt-ica` or `dh:dh-glossary` for the reverse-thinking method definition. **BLOCK** if any required condition is MISSING.

---

## Status Values

| Status | Meaning |
|--------|---------|
| **AVAILABLE** | Explicitly present in input |
| **DERIVABLE** | Inferred with high confidence (must show basis) |
| **MISSING** | Not present, not safely inferable |

---

## Decision Rule

```text
IF any condition is MISSING:
    DECISION = BLOCKED
ELSE:
    DECISION = APPROVED
```

---

## planner-rt-ica vs rt-ica

- **planner-rt-ica**: Allows planning under uncertainty (APPROVED-WITH-GAPS)
- **rt-ica**: Blocks on missing. Any task under APPROVED-WITH-GAPS MUST pass rt-ica before execution

---

## Fact-Check Integration

**REFUTED → MISSING**: If fact-check returns REFUTED on a claim, RT-ICA treats it as MISSING.

---

## Condition Categories

Functional requirements, non-functional requirements, interfaces, environment, data, access, operational, delivery, verification, risks.

---

## Source

- [rt-ica SKILL.md](../../../skills/rt-ica/SKILL.md)
