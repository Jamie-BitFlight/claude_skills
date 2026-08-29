---
name: dispatch-contract
description: Which agent a dh workflow dispatches, and the artifact consumer invariant.
user-invocable: false
---

# Dispatch Contract

<dispatch_selection>

A dispatch that hands over no dh operation — an independent review, say — has no dh-roster
requirement to reach: any specialist that fits runs it, dh roster or not. Where its finding goes is
never decided here, for that or any dispatch — it is governed by `subagent-contract`'s
`<result_destination>` clause, every time, including for review-only dispatches.

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

<dispatch_prompt_scope>

A dispatch prompt for an agent that can reach the backlog item's own content (see that agent's
`dh:subagent-contract` `<dispatch_input>` rule) carries an item reference and whatever a peer
teammate computed this run that no `item_ref` lookup can retrieve — never content pasted from the
item's own sections.

Never write a speculative conclusion, a pre-formed verdict, or hedged language ("likely",
"probably", "seems") into a dispatch prompt for an agent whose value is independent judgement.
``"this is very likely `defect` — confirm this classification yourself"`` is a violation: it hands
the receiving agent a conclusion to ratify, not a problem to classify. Give the agent the item
reference and let it reach its own verdict.

</dispatch_prompt_scope>
