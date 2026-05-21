---
name: verify-done
description: Rigorous self-assessment checklist before marking any task as complete. Use when about to claim task completion, before final commit, when user asks "is it done?", or when transitioning from implementation to reporting. Prevents premature completion claims by requiring evidence for every assertion.
user-invocable: true
---

# Verification Protocol

**STOP.** You are NOT done yet. Generate this checklist and provide **EVIDENCE** for every item.

---

## 1. Task Type & Strategy

- [ ] **Type:** FIX / FEATURE / REFACTOR / DOCS / INVESTIGATION
- [ ] **Strategy:** Executable verification vs. Static verification?

---

> [!IMPORTANT]
> When provided a process map or Mermaid diagram, treat it as the authoritative procedure. Execute steps in the exact order shown, including branches, decision points, and stop conditions.
> A Mermaid process diagram is an executable instruction set. Follow it exactly as written: respect sequence, conditions, loops, parallel paths, and terminal states. Do not improvise, reorder, or skip steps. If any node is ambiguous or missing required detail, pause and ask a clarifying question before continuing.
> When interacting with a user, report before acting the interpreted path you will follow from the diagram, then execute.

## 2. The "WORKS" Check

<!-- Converted from prose branch instruction: "Choose A or B based on task type" -->

The following diagram is the authoritative procedure for WORKS Check — determining whether the task output is verified as working. Execute steps in the exact order shown, including branches, decision points, and stop conditions.

```mermaid
flowchart TD
    Start(["Begin WORKS Check -- Section 2"]) --> Q{"Task type?"}
    Q -->|"Executable code -- compiled, scripted, or CLI-run"| A1["Execution check<br>Terminal output showing successful run<br>(exit code 0 is NOT enough)"]
    Q -->|"Static asset -- docs, configs, analysis"| B1["Accuracy check<br>Verified against source code or schema?"]
    A1 --> A2["Real data check<br>Ran changed code path against real data<br>not just read the diff?"]
    A2 --> A3["Regression check<br>Evidence that existing tests still pass?"]
    A3 --> A4["Edge case check<br>Evidence of testing failure scenarios?"]
    A4 --> AEvidence["Record code evidence<br>execution output, real data test,<br>test results, edge case result"]
    B1 --> B2["Clarity check<br>Follows the established format?"]
    B2 --> B3["Validity check<br>Links and references resolve?"]
    B3 --> BEvidence["Record static evidence<br>accuracy check method,<br>format standard, link validation method"]
    AEvidence --> Done(["WORKS Check complete -- proceed to Section 3"])
    BEvidence --> Done
```

### A. For Code (Executable)

- [ ] **Execution:** Terminal output showing successful run? (Exit code 0 is NOT enough)
- [ ] **Real data:** Ran the changed code path against real data, not just read the diff?
- [ ] **Regression:** Evidence that existing tests still pass?
- [ ] **Edge Cases:** Evidence of testing failure scenarios?

```text
EVIDENCE:
- Execution output: [paste actual output]
- Real data test: [command run, input used, output observed]
- Test results: [paste test output]
- Edge case tested: [describe scenario and result]
```

### B. For Static Assets (Docs, Configs, Analysis)

- [ ] **Accuracy:** Verified against source code/schema?
- [ ] **Clarity:** Does it follow the established format?
- [ ] **Validity:** Do links/references resolve?

```text
EVIDENCE:
- Accuracy check: [how verified]
- Format compliance: [standard followed]
- Links validated: [method used]
```

---

## 3. The "FIXED" Check

For bug fixes specifically:

- [ ] **Reproduction:** Did I observe the pre-fix state?
- [ ] **Resolution:** Does the original problem NO LONGER occur?

```text
EVIDENCE:
- Pre-fix behavior: [what was observed]
- Post-fix behavior: [what is now observed]
- Regression test added: [yes/no, location]
```

---

## 4. Quality Gates

- [ ] Pre-commit hooks passed?
- [ ] Linting passed? (Necessary, but not sufficient)
- [ ] Type checking passed? (if applicable)

```text
EVIDENCE:
- Pre-commit: [output or "not configured"]
- Linting: [tool and result]
- Type check: [tool and result]
```

---

## 5. Proportional Response Check

If the task has an `issue-classification` field in its metadata, verify the response matched the issue type. If no `issue-classification` is present, mark N/A and proceed.

The following diagram is the authoritative procedure for Proportional Response Check — verifying that the response scope matched the issue classification. Execute steps in the exact order shown, including branches, decision points, and stop conditions.

```mermaid
flowchart TD
    Start(["Begin Proportional Response Check"]) --> Q1{"issue-classification<br>present in task metadata?"}
    Q1 -->|"absent"| Skip["SKIP -- existing WORKS/FIXED/Quality Gates apply"]
    Q1 -->|"present"| Q2{"Classification type?"}
    Q2 -->|"procedural"| P["Sweep completeness<br>Codebase search returns zero<br>remaining instances of the pattern"]
    Q2 -->|"defect"| D["Root cause addressed<br>Fix targets root cause from evidence chain<br>+ scenario in scenario-target succeeds"]
    Q2 -->|"recurring-pattern"| R["Guardrail added<br>New gate/check exists AND<br>covers the defect CLASS not just instance"]
    Q2 -->|"missing-guardrail"| M["Gate gap filled<br>Guardrail triggers in the<br>exposing scenario"]
    Q2 -->|"unbounded-design"| U["Design implemented<br>Matches chosen direction +<br>trade-offs documented"]
    P --> Evidence
    D --> Evidence
    R --> Evidence
    M --> Evidence
    U --> Evidence
    Skip --> Done(["Proportional Check complete"])
    Evidence["Record proportional evidence"] --> Done
```

```text
EVIDENCE:
- Issue Classification: [type or "not classified"]
- Scenario Target: [scenario -> improvement, or "not specified"]
- Proportional Check: [PASS/FAIL/N/A]
- Check detail: [what was verified and result]
```

---

## 6. Agent Delegation Verification

When work was delegated to a sub-agent, the agent's success report is NOT evidence.

- [ ] **VCS diff reviewed:** `git diff` shows the expected changes?
- [ ] **Changes verified:** Read the modified files — content matches intent?
- [ ] **Tests run independently:** Ran the verification command yourself, not trusting the agent's claim?

```text
EVIDENCE:
- Agent report: [what agent claimed]
- VCS diff: [files changed, scope matches expectation]
- Independent verification: [command run, output observed]
```

If no agents were used, mark N/A and proceed.

---

## 7. Honesty Check

- [ ] Did I verify the _full scope_?
- [ ] Am I distinguishing between "should work" and "verified to work"?
- [ ] **Destination check:** Did I read the target state after writing? (Tool output claiming success is not evidence — the state of the destination is.)
- [ ] Can I answer YES to: "I have VALIDATED this output in its intended context"?

### Rationalization Prevention

If any of these thoughts occur, STOP and run the verification command:

| Rationalization | Response |
|----------------|----------|
| "Should work now" | Run the verification command |
| "I'm confident" | Confidence is not evidence |
| "Just this once" | No exceptions |
| "Linter passed so build passes" | Linter does not check compilation |
| "Agent said success" | Verify independently (Section 6) |
| "I'm tired" | Exhaustion is not an excuse |
| "Partial check is enough" | Partial check proves nothing about the whole |
| "Different words so rule doesn't apply" | Spirit over letter |

**Red flags in your own output** — if you catch yourself writing any of these, the gate has not been passed:
- "should", "seems to", "looks correct"
- Expressions of satisfaction before verification ("Done!", "Perfect!")
- About to commit/push/PR without fresh command output in this message

---

## The Golden Rule

**If you cannot demonstrate it working in practice with evidence, it is NOT done.**

| Claim           | Required Evidence                                        |
| --------------- | -------------------------------------------------------- |
| "Code works"    | Terminal output showing execution against real data      |
| "Tests pass"    | Actual test output, not assumption                       |
| "Bug fixed"     | Before/after comparison                                  |
| "Data synced"   | Read the destination after writing — not the tool output |
| "Docs accurate" | Cross-reference with source                              |
| "Config valid"  | Validation command output                                |
| "Root cause fixed" | Evidence chain from grooming + fix addresses root cause claim |
| "Guardrail added"  | New gate/check exists and triggers in exposing scenario       |
| "Agent completed"  | VCS diff reviewed + independent verification command run     |

---

## 8. Observations, Gaps, and Backlog Capture

Review the task just completed and list every instance of:

- **Workflow gaps** — steps that were missing, unclear, or required guessing to proceed
- **Workarounds** — anything done as a workaround rather than the correct approach
- **Process concerns** — agent behaviors or system interactions that indicate a systemic problem
- **Improvement observations** — things noticed that could be better if addressed, even if not blocking

The following diagram is the authoritative procedure for Observations, Gaps, and Backlog Capture — triaging observations from the completed task into backlog items or recorded notes. Execute steps in the exact order shown, including branches, decision points, and stop conditions.

```mermaid
flowchart TD
    List["List all instances across the four categories above"] --> Q{"Any items listed?"}
    Q -->|"None"| None["Record: No observations"]
    Q -->|"Yes"| Gate{"Any item is contextually significant<br>OR was already flagged during the task<br>as needing a bug or backlog entry?"}
    Gate -->|"No — minor, not worth a ticket"| ObsOnly["Record as observation only<br>Include in summary below"]
    Gate -->|"Yes — significant"| Detect{"Which issue system does this project use?"}
    Detect -->|".beads/dh-backend marker exists"| Beads["bd create --title='...' --description='...' --type=bug --priority=2"]
    Detect -->|"GitHub remote / dh plugin present"| DH["Skill(skill='dh:work-backlog-item', args='create -- \"...\"')"]
    Detect -->|"Other"| Other["Create entry in whatever issue system the project uses"]
    Beads --> Ref["Record issue reference in summary"]
    DH --> Ref
    Other --> Ref
    Ref --> Done(["Observations Check complete"])
    None --> Done
    ObsOnly --> Done
```

```text
OBSERVATIONS:
- Workflow gaps:    [list or "none"]
- Workarounds:      [list or "none"]
- Process concerns: [list or "none"]
- Improvements:     [list or "none"]
- Issues logged:    [issue refs or "none"]
```

---

## Quick Reference

```text
VERIFICATION SUMMARY:
Task Type: [FIX/FEATURE/REFACTOR/DOCS/INVESTIGATION]
Works Check: [PASS/FAIL] - Evidence: ___
Fixed Check: [PASS/FAIL/N/A] - Evidence: ___
Proportional Check: [PASS/FAIL/N/A] - Evidence: ___
Quality Gates: [PASS/FAIL] - Evidence: ___
Agent Delegation: [PASS/FAIL/N/A] - Evidence: ___
Honesty Check: [PASS/FAIL]
Observations: [issue refs logged, or "none"]

VERDICT: [COMPLETE / NOT COMPLETE - reason]
```
