# Issue Classification and Root-Cause Analysis

## Table of Contents

- [Classification Flowchart](#classification-flowchart)
- [Classification Types](#classification-types)
- [Writing Classification to Backlog Item](#writing-classification-to-backlog-item)
- [Root-Cause Analysis](#root-cause-analysis)
  - [defect — 5-whys](#defect--5-whys)
  - [recurring-pattern — 6-sigma](#recurring-pattern--6-sigma)

---

## Classification Flowchart

```mermaid
flowchart TD
    Start(["Classify issue type"]) --> Q1{"Is this a typo/naming/<br>formatting/surface fix?"}
    Q1 -->|"YES"| Procedural["procedural<br>Analysis method = none"]
    Q1 -->|"NO"| Q2{"Has this same problem class<br>appeared 2+ times?"}
    Q2 -->|"YES"| Recurring["recurring-pattern<br>Analysis method = 6-sigma"]
    Q2 -->|"NO"| Q3{"Is there a traceable failure<br>with identifiable cause chain?"}
    Q3 -->|"YES"| Defect["defect<br>Analysis method = 5-whys"]
    Q3 -->|"NO"| Q4{"Did the system allow a bad outcome<br>that a gate should have prevented?"}
    Q4 -->|"YES"| MissingGuardrail["missing-guardrail<br>Analysis method = none"]
    Q4 -->|"NO"| UnboundedDesign["unbounded-design<br>Analysis method = design-framing"]
```

## Classification Types

| Type | Analysis Method | When |
|------|----------------|------|
| `procedural` | none | Typo, naming, formatting, surface fix |
| `recurring-pattern` | 6-sigma | Same problem class appeared 2+ times |
| `defect` | 5-whys | Traceable failure with identifiable cause chain |
| `missing-guardrail` | none | System allowed bad outcome that a gate should have prevented |
| `unbounded-design` | design-framing | None of the above |

## Writing Classification to Backlog Item

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" backlog groom \
  --selector "{title}" \
  --section "Issue Classification" \
  --content "**Type**: {classification}
**Rationale**: {1-2 sentence explanation}
**Analysis Method**: {method}
**Scenario Target**: {what scenario exposed this} -> {what should improve}"
```

`scenario-target` captures the specific scenario that exposed the problem and what should improve after the fix.

---

## Root-Cause Analysis

**Only runs for `defect` or `recurring-pattern` classifications.** Skip entirely for `procedural`, `missing-guardrail`, and `unbounded-design`.

### defect — 5-whys

Invoke `/find-cause` to build an evidence chain from symptom to root cause:

```text
Skill(skill="find-cause", args="{description of the defect}")
```

Write the evidence chain:

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" backlog groom \
  --selector "{title}" \
  --section "Root-Cause Analysis" \
  --content "**Method**: 5-whys
**Classification**: defect

#### Evidence Chain

{evidence chain from /find-cause}

**Root Cause**: {single actionable statement}
**Scenario Target**: {what scenario exposed this} -> {what should improve}"
```

### recurring-pattern — 6-sigma

Call `uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" backlog list --status "resolved"` (the CLI's `backlog list` has no `--search` full-text flag, but `--status` used here is fully supported), filter by keywords related to this defect class, count matches, and write the measurement section:

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" backlog groom \
  --selector "{title}" \
  --section "Root-Cause Analysis" \
  --content "**Method**: 6-sigma
**Classification**: recurring-pattern

#### Measurement

- **Frequency**: {N occurrences in {time period or batch}}
- **Common factors**: {what the occurrences share}
- **Affected scope**: {what parts of the system are impacted}

#### Analysis

- **Root cause pattern**: {why this class of defect recurs}
- **Missing guardrail**: {what gate or instruction should prevent this}

#### Improvement

- **Proposed guardrail**: {specific instruction, gate, or check to add}
- **Verification**: {how to confirm the guardrail works}"
```

**Note**: If the human has already identified the recurrence pattern, skip the search and use the human's assessment.
