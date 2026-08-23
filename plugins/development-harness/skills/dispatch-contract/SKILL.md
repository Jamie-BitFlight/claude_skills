---
name: dispatch-contract
description: Which agent a dh workflow dispatches, and the artifact consumer invariant.
user-invocable: false
---

# Dispatch Contract

Dispatch a `dh:` specialist that fits the task and whose declared tools reach every operation the
dispatch hands over. Otherwise dispatch `dh:task-worker` — it is this plugin's general-purpose
worker, and it arrives carrying dh's tools and hooks.

Outside capability reaches the task through `dh:task-worker`: an outside agent as the profile it
loads, an outside skill through the task's own `skills` list, since a profile resolves to an agent.

Every artifact is consumed as an input by a later step. An artifact no step reads is a missing
consumer, not a redundant artifact.
