---
name: generate-task
description: Generates one worker task prompt conforming to the CLEAR + selective CoVe task design standard and swarm-task-planner structure. Use when creating or rewriting a single TASK file or task block inside a plan — providing a title and brief description as input.
argument-hint: '[task title and brief description]'
user-invocable: true
disable-model-invocation: false
---

<task_description>$ARGUMENTS</task_description>

# Generate Task (Worker Task Prompt)

You generate ONE worker task prompt that will be executed by a worker agent.

You MUST follow the existing canonical task writing standard and structure:

- CLEAR ordering (Context, Objective, Inputs, Requirements, Constraints, Expected Outputs, Acceptance Criteria, Verification Steps, CoVe Checks only if needed, Handoff).
- Task structure requirements and fields (task, title, status, agent, dependencies, priority, complexity, accuracy-risk, parallelize-with, reason, handoff, Required Inputs).

Do NOT add any new fields, sections, agents, or mechanisms beyond what is already defined in the referenced task standards.

## Inputs

When invoked, you will be given some combination of:

- a task title and brief description (in <task_description/>)
- optionally: dependencies, repo/file references, constraints, and verification expectations

If critical information is missing, you MUST keep the task executable by:

- stating assumptions under Required Inputs (and how to confirm them), and
- ensuring Verification Steps can confirm correctness, or explicitly indicate what blocks verification.

## Output

Output exactly ONE task prompt in this format:

````markdown
```yaml
---
task: [Task ID]
title: [Descriptive Name]
status: not-started
agent: [agent-name or "unassigned"]
dependencies: []
priority: [1-5 based on dependency depth]
complexity: [low/medium/high based on scope, not time]
accuracy-risk: [low/medium/high]
parallelize-with: []
reason: [Why parallelization is safe; avoid file conflicts]
handoff: [What the worker must report back: summary, evidence, blockers]
---
```

## Context
[Only what the worker needs; reference specific files/sections]

## Objective
[One sentence definition of success]

## Required Inputs
- [Files/links/artifacts the worker must read]
- [Assumptions and how to confirm them]

## Requirements
1. [Must do]
2. [Must do]

## Constraints
- [Must not do]
- [Guardrails, scope boundaries]

## Expected Outputs
- [Files created/modified with paths]
- [Artifacts produced]

## Acceptance Criteria
1. [Specific, measurable criterion]
2. [Another verifiable requirement]

## Verification Steps
1. [How to verify criterion 1]
2. [How to verify criterion 2]

## CoVe Checks (ONLY if accuracy-risk is medium or high)
- Key claims to verify:
  - [Claim 1]
- Verification questions:
  1. [Question 1]
- Evidence to collect:
  - [Commands, docs, code pointers]
- Revision rule:
  - If any check fails, revise and state what changed.
````

## Lint Before Final Output

Before returning the task prompt, you MUST lint it using the existing rules:

- Concise: no filler, no duplicated requirements
- Logical: sections in canonical order
- Explicit: objective, outputs, acceptance criteria, verification are concrete
- CoVe: included only when Accuracy Risk is Medium/High, and questions are falsifiable

If any lint check fails, revise the task prompt and re-lint.
