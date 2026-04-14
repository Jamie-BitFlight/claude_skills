---
name: create-backlog-item
description: "Creates a new backlog item and routes through the work-backlog-item create workflow. Use when the user asks to add a backlog item, log a task, capture a feature request, or track a work item."
argument-hint: '[--auto {title} | {title} | <empty for guided intake>]'
user-invocable: true
---

Invoke `/dh:work-backlog-item create $ARGUMENTS` and follow its instructions.
