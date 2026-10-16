---
name: assessment-reporting
description: Format and score completed plugin assessment findings, including whether evidence admits a finding to the requested outcome. Use when a plugin assessment or review needs the standard report structure, scoring criteria, severity breakdown, marketplace-readiness result, or finding admission.
---

# Plugin Assessment Reporting

<procedure>

1. Read [assessment-report-format.md](./references/assessment-report-format.md) and [scoring-criteria.md](./references/scoring-criteria.md).
2. Apply the report structure to the completed assessment findings.
3. Calculate each component and the overall score using the scoring criteria.
4. Return the marketplace-readiness determination and all required findings. Do not start or dispatch another assessment workflow.

</procedure>

## Finding Admission

Retain every finding with its evidence. Admit a finding to a remediation dispatch, tracking task,
extra validation, blocking recommendation, or design transformation only when the report records:

- the requested outcome, declared capability, or applicable source contract;
- observed evidence; and
- concrete impact on the outcome, safety, data, or contract.

The current task owner admits the candidate using the direct request, approved plan, backlog
criterion, or applicable contract. Reviewers provide evidence and recommendations; they do not add
task authority. Keep unrelated improvement opportunities advisory: preserve them in the report, but
do not create a patch, harness, subtask, or merge block. A source-contract, security, or data-loss
defect remains admissible when the applicable contract and observed impact are recorded.

Revisit an admitted claim only when a source change or new discriminating evidence can change its
disposition. Otherwise retain the convergence result and continue toward the requested outcome.
This scope decision leaves routine implementation choices with the task owner.
