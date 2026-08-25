---
name: eval4-target
description: Fixture target skill exercising the MOVE-ADR branch. Use when the eval harness needs a skill with a hard-to-reverse, surprising, genuine-trade-off decision, nested under a component that has its own ADR convention.
---

# Eval4 Target

## Use polling instead of a webhook

Poll the status endpoint every 30 seconds instead of registering a webhook. Webhooks were
considered and rejected: the vendor's webhook delivery has no retry guarantee and silently drops
events during their maintenance windows, which happened three times in the six weeks the team ran
it in production, each time causing a stuck run that only manual intervention could clear.
Switching back to webhooks later would require re-plumbing the entire completion-detection path
across three other skills that all assume polling today, so this was not a decision taken lightly.
