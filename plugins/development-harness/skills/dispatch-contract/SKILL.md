---
name: dispatch-contract
description: Which agent a dh workflow dispatches, and the artifact consumer invariant.
user-invocable: false
---

# Dispatch Contract

Dispatch a `dh:` specialist that fits the task and whose declared tools reach every operation the
dispatch hands over. Otherwise dispatch `dh:task-worker`, naming that specialist as the profile it
loads. Never dispatch `general-purpose`, and never dispatch an agent from outside dh by its name.

An outside agent reaches the task as that profile; an outside skill reaches it through the task's
own `skills` list, since a profile resolves to an agent.

Every artifact is consumed as an input by a later step. An artifact no step reads is a missing
consumer, not a redundant artifact.
