---
name: dispatch-contract
description: Which agent a dh workflow dispatches, and the artifact consumer invariant.
user-invocable: false
---

# Dispatch Contract

<dispatch_selection>

A dispatch that hands over no dh operation — an independent review whose finding is its response —
has nothing here to reach: any specialist that fits runs it, dh roster or not.

Once a dispatch hands over one, dispatch a `dh:` specialist that fits the task and whose declared
tools reach every operation handed over; failing that, `dh:task-worker` — this plugin's
general-purpose worker, arriving with dh's tools and hooks. Outside capability reaches such a task
through it: an outside agent as the profile it loads, an outside skill through the task's own
`skills` list, since a profile resolves to an agent.

</dispatch_selection>

<artifact_consumption>

Every artifact is consumed as an input by a later step. An artifact no step reads is a missing
consumer, not a redundant artifact.

</artifact_consumption>
