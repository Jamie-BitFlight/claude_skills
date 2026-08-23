---
name: subagent-contract
description: How a dh workflow step takes its inputs, stores its results, and reports completion. Use when executing any step dispatched in a development-harness workflow.
user-invocable: false
---

# Subagent Contract

Take each input the workflow carries into your step, and store each result it carries onward,
through the plan, task, artifact, or section operation your dispatch names — under the identifier
or section name it gives you. Never a response message, never a repo file. Reading repo source to
do the work is unaffected; this governs what moves between steps.

Report completion as `STATUS: DONE` or `STATUS: BLOCKED`. The report says what happened; the
result itself is already stored.

Return BLOCKED when a required input is missing, rather than inferring it.
