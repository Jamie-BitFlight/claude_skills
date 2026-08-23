---
name: dispatch-contract
description: Which agent a dh workflow dispatches for a task, and where a dispatched agent's result goes. Use when planning or decomposing tasks and selecting the agent for one, when dispatching an agent for dh work, or when deciding where a result belongs.
user-invocable: false
---

# Dispatch Contract

Dispatch a `dh:` specialist that fits the task; otherwise dispatch `dh:task-worker`, naming the
specialist it loads as a profile — including any skill or agent from outside dh. Never dispatch
`general-purpose`, and never dispatch an outside agent by its own name.

Every artifact is consumed as an input by a later step. An artifact no step reads is a missing
consumer, not a redundant artifact.

Results go to the backend through a plan, task, or artifact operation — never a response message,
never a repo file.
