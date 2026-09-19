---
name: find-cause
description: Investigate why something happens — confirm the question and success criteria with you, then trace the root cause with an evidence chain.
argument-hint: <what to investigate>
disable-model-invocation: true
---

<investigation_request>$ARGUMENTS</investigation_request>

# Find Cause

Rewrite the user's investigation request into one confirmed question with Step 1 below, then trace it with Step 2. The user's original request is in `<investigation_request/>`.

## Procedure

### Step 1 — Disambiguate the question and define success criteria

Read the user's request in `<investigation_request/>`. Perform two tasks:

#### A. Formulate distinct interpretations

Formulate 2 or more distinct interpretations of what they are asking. Present these interpretations to the user using the `AskUserQuestion` tool so the user can select the correct one or provide their own clarification.

Each interpretation MUST be a concrete, falsifiable question — not a vague restatement. Frame each as "Are you asking X?" where X is specific enough to investigate.

Example for the request "find out why the tests fail":

- **Interpretation A**: "Why do tests fail when run locally but pass in CI?"
- **Interpretation B**: "Why does a specific test case produce an unexpected assertion error?"
- **Interpretation C**: "Why did tests start failing after a recent change?"

Do NOT proceed until the user has confirmed which interpretation is correct or provided their own.

If the user selects "Other" and provides additional context, reformulate the interpretations and ask again. Only proceed when you have a single, unambiguous question to investigate.

#### B. Define success criteria

Load the `dh:root-cause-tracing-process` skill with the Skill tool now, for its Inputs format only. Its steps run at Step 2, after the user confirms. For the confirmed interpretation, write the QUESTION and SUCCESS CRITERIA block its Inputs section defines.

Present the success criteria to the user for confirmation. Adjust if the user's definition of "done" differs.

Do NOT proceed to Step 2 until both interpretation and success criteria are confirmed.

### Step 2 — Trace the root cause

Follow the loaded `dh:root-cause-tracing-process` skill from Step 0, with the confirmed QUESTION and SUCCESS CRITERIA as its Inputs, through its Step 5 report.
