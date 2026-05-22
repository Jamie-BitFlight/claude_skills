# Create - backlog item - Scope boundary

## Step 0: Classify the item type

Classify the item before applying any strip rule. Classification determines which rule applies in Step 1.

```mermaid
flowchart TD
    Start([Incoming backlog item description]) --> Q1{Does the description primarily define what<br>an agent, system, workflow, or skill must do?}
    Q1 -->|Yes — behavioral/process semantics present| Q2{Are file-level or code-level prescriptions<br>also present alongside the behavioral spec?}
    Q1 -->|No — describes a user-visible gap, defect,<br>or capability without agent/process semantics| Product[PRODUCT/FEATURE<br>Apply the strip rule in Step 1]
    Q2 -->|No — purely behavioral| Behavioral[BEHAVIORAL/PROCESS<br>Preserve the full procedural description unchanged]
    Q2 -->|Yes — behavioral spec AND code prescriptions| Mixed[MIXED<br>Preserve the behavioral spec<br>Isolate code prescriptions as<br>'**User-provided context**: {verbatim text}']
```

**Behavioral item signals** — presence of any of these indicates BEHAVIORAL/PROCESS or MIXED:

- Subject is an agent, workflow, skill, or system component (not a human user)
- Contains: "must", "must not", "must load before", "ordering constraint", "guardrail", "policy", "agent must", "the system must", "the workflow must"

**Implementation prescription signals** — presence of any of these triggers the strip rule for that portion:

- "modify file X", "add function Z", "change line Y", "replace X with Y"
- Subject is a source file, configuration file, or code construct

## Rule: To create an excellent backlog item, describe the problem, not the solution

A **product or feature** backlog item must describe the reported problem or missing capability without prescribing how to implement a fix.

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

## Rule: Behavioral/process items — preserve the procedural description

A backlog item whose description defines what an agent, system, or workflow must do contains the requirement as procedural text. Preserve the full procedural description as written.

Reason:
For behavioral and process-design items, the procedural description IS the requirement specification. Stripping it removes intent that cannot be reconstructed without the original context. This is structurally different from product feature items where requirements and implementation are separable.
