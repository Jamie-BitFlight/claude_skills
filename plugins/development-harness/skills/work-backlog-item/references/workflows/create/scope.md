# Create - backlog item - Scope boundary

## Rule: To create an excellent backlog item, describe the problem, not the solution

A backlog item created at intake must describe the reported problem or missing capability without prescribing how to implement a fix.

Do NOT include any of the following in the creation-stage backlog item:
- a "Required changes" section
- a "Potential approaches" or "Suggested fixes" section
- implementation instructions such as "replace X with Y" or "add function Z"
- scope additions that were not explicitly requested by the user
- file-level or code-level prescriptions such as "modify file X" or "change line Y"

Reason:
Prescriptive fix content at creation time bypasses grooming, RT-ICA, and architecture review by turning unvalidated assumptions into apparent requirements.

A creation-stage backlog item should contain only:
- what is broken, missing, or requested
- where it was observed
- the user or business impact

Allowed content at creation time:
- user-reported symptoms
- observed behavior
- expected behavior, if stated
- reproduction context, if stated
- direct evidence or references supplied by the user

Not allowed at creation time:
- proposed implementation
- design decisions
- technical solutioning
- extra work not requested by the user

If the user supplies a possible fix, preserve it as user-provided context or hypothesis, not as a requirement or implementation instruction.

Solutions belong to later stages:
- grooming may investigate causes, constraints, and candidate directions
- planning may define architecture, decomposition, and implementation approach
