# Groomer Output Validation

Pre-write validation gate (Step 8.7) — verifies groomer agent output contains all required
sections with minimum content before writing to the canonical item file.

SOURCE: Architect spec Issue #398, Section 7 (Groomer Output Validation AC3)

---

## Required Section Schema

All required sections must be present in the groomer output with minimum content (defined in finalize.md validation table). Section
names are exact string matches against `backlog_view(selector=title, summary=false).sections`.

| Section | Required | Minimum content |
|---|---|---|
| `RT-ICA` | Required | Contains `Decision: APPROVED` or `Decision: BLOCKED` and `Date: YYYY-MM-DD` |
| `Impact Radius` | Required | Contains at least one entry under `Systems Inventory` |
| `Fact-Check` | Required | Contains at least one claim with `verdict:` field |
| `Acceptance Criteria` | Required | Non-empty — at least one criterion listed |
| `Reproducibility` | Required | Non-empty — may be "N/A for feature items" but must be present |
| `Issue Classification` | Required | Contains `Type:` field with valid type value |
| `Priority` | Required | Contains `Effort:` field |
| `Design Intent Alignment` | Required | Contains `Alignment assessment:` field with ALIGNED/DIVERGENT/NOT_APPLICABLE |

## Optional Sections (Not Validated for Presence)

These sections are permitted but not required during validation:
`Root-Cause Analysis`, `Impact`, `Benefits`, `Expected Behavior`, `Files`, `Resources`,
`Dependencies`, `Scope`, `Decision`

---

## Scope Boundary Check

After presence check passes, scan groomer-produced sections for implementation-prescriptive
language. Apply these prohibited patterns (regex) to all sections except `Issue Classification`
and `Root-Cause Analysis`:

```text
use \w+ framework
implement \w+ using
architecture:
the solution (should|will|must) (use|implement|call)
```

**Exemption**: `Issue Classification` and `Root-Cause Analysis` may describe the problem in
implementation terms — classification of the problem is not the same as prescribing the solution.

**Scope violations do NOT block the write.** Violations are logged as notes via:

```text
backlog_groom(section="Grooming Notes", content="Scope violation: {pattern} in {section}")
```

---

## Validation Procedure (Step 8.7 — Pre-Write Validation Gate)

Located between end of Steps 4–8 swarm and the `backlog_groom(mark_groomed=True)` call in Step 9.

```mermaid
flowchart TD
    SwarmComplete(["Steps 4-8 swarm complete"]) --> GatherSections["Read backlog_view(selector=title, summary=false).sections"]

    GatherSections --> PresenceCheck["Check all required sections present (see finalize.md)<br>Apply minimum content checks per schema"]
    PresenceCheck --> PresenceResult{"All required sections present<br>with minimum content?"}

    PresenceResult -->|"Yes"| ScopeCheck["Scan groomer sections for prohibited patterns"]
    PresenceResult -->|"No — sections missing"| MissingList["Build list of missing section names"]
    MissingList --> AttemptCount{"Validation attempts so far?"}
    AttemptCount -->|"First attempt"| RetryHaiku1["Spawn haiku groomer with targeted prompt:<br>'Write ONLY these missing sections: {list}<br>Do not repeat existing content'<br>Return to GatherSections after completion"]
    AttemptCount -->|"Second attempt"| RetryHaiku2["Spawn haiku groomer again (second pass)<br>Same targeted prompt<br>Return to GatherSections after completion"]
    AttemptCount -->|"Third attempt"| RetrySonnet["Escalate to sonnet groomer<br>Same targeted prompt<br>Return to GatherSections after completion"]
    AttemptCount -->|"Fourth attempt"| Blocked(["backlog_update(status='blocked')<br>Report to user: grooming failed after 4 attempts<br>Missing: {list}<br>STOP — do not proceed to Step 9"])

    ScopeCheck --> ScopeResult{"Prohibited patterns found?"}
    ScopeResult -->|"No patterns"| ValidationPass(["VALIDATION PASS — proceed to Step 9 write"])
    ScopeResult -->|"Patterns found"| ScopeReport["backlog_groom(section='Grooming Notes',<br>content='Scope violation: {pattern} in {section}')"]
    ScopeReport --> ValidationPass
```

### Retry Model

Escalation follows design decision D3 (haiku → haiku retry → sonnet → blocked):

1. **First attempt** — haiku groomer, targeted prompt listing missing sections only
2. **Second attempt** — haiku groomer, same targeted prompt (second pass often resolves first-attempt gaps)
3. **Third attempt** — sonnet groomer, same targeted prompt
4. **Blocked** — `backlog_update(status='blocked')`, report to user, do not call `backlog_groom(mark_groomed=True)`

No graceful degradation. `blocked` is an explicit terminal state, not a fallback.

### Placement in groom-backlog-item Workflow

The SKILL.md workflow Mermaid diagram node sequence changes from:

```text
S48 to S85 to FinalDecision
```

to:

```text
S48 to S85 to FinalDecision(APPROVED path) to S87 to S9
```

Where S87 is: "Step 8.7 — Groomer Output Validation — Load references/groomer-output-validation.md"

Full procedure lives here. The SKILL.md diagram shows the S87 node; this file contains the detail.
