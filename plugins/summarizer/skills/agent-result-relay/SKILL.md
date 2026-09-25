---
name: agent-result-relay
description: Relay agent results without corrupting exact counts, failure reasons, source scope or status. Use when receiving agent output or handing results to another actor; distinguish observations from attributed conclusions and reference complete artifacts.
---

# Agent Result Relay

Read [fidelity rules](../summarizer/references/fidelity-rules.md) and the
[execution contract](../summarizer/references/execution-contract.md).

Preserve the caller's return vocabulary and structure. Relay exact counts/denominators, material
warnings, failure reasons and artifact paths: `7 of 10 found; 3 requests timed out`, not `most found`
or `the rest do not exist`. Missing results or idle workers do not establish completion.

If a worker wrote an artifact, name the exact accessible artifact reference rather than replacing
it with a shortened retelling. Keep observations separate from conclusions: an absent timeout
field and an agent's asserted default of 30 seconds are two different claims.

Summarize a result only when requested, when combining workers for the caller's decision, or when
selecting the relevant portion of a larger result. Preserve all material counts, reasons, scope and
qualifiers, and reference the complete result. Use [multi-source-synthesis](../multi-source-synthesis/SKILL.md)
for genuine integration rather than silently strengthening or merging claims during relay.

For retained evidence handoffs, follow the [evidence record](../summarizer/references/evidence-record.md).
Validate the actual final artifact after any transformation. Unchanged verbatim relay may reuse
validation only when the evidence still describes the exact delivered bytes and source/request
identity. Keep failed and unperformed checks visible; never interpret `NOT_VALIDATED` as success.
