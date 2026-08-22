---
paths:
- '**/agents/**/*.md'
---

# Agent Output Contracts — Explicit Terminal Output Required

Every agent MUST emit an explicit terminal message as its final response. Silent completion is
indistinguishable from a crash, context-limit truncation, or mid-task abandonment — the
orchestrator cannot tell the difference.

## The Rule

**An agent that produces no output is broken from the orchestrator's perspective.**

This applies in ALL cases including:
- No findings (analysis agent found nothing)
- No changes (refactoring agent found nothing to change)
- Verification passed (no violations, no drift, no mismatches)
- No improvements generated (kaizen agent found nothing to improve)

## Required Pattern

Every agent must end with a STATUS block:

```
STATUS: DONE
{artifact path or key result}
{one-line summary}
```

Or for blocked/failed:

```
STATUS: BLOCKED
Reason: {specific reason}
```

A named agent's final response text does not reach its dispatcher. Whenever an agent was spawned
as a named teammate — via `TeamCreate`, or via an `Agent` call that gave it a name — the STATUS
block must also go out through `SendMessage`, or it is lost:

```
SendMessage(to="team-lead", summary="[brief]", message="[full STATUS block]")
```

`SendMessage` may be a deferred tool, absent from an agent's loaded schemas. An agent that cannot
see it must run `ToolSearch("select:SendMessage")` before calling it.

Findings requested as prose are covered by this too: the prose is the STATUS block, and it goes in
the `message` field. A report that exists only in an agent's final response text was never
delivered.

## The "Write to File" Anti-Pattern

"Write all output to files — never return large analysis as message text" means write a file
AND return STATUS. It does NOT mean return nothing. Writing to a file is not visible to the
orchestrator until the STATUS block confirms the file path.

## The "No Findings" Case

This is the most dangerous silent-exit case. When an analysis agent finds nothing, it must
say so explicitly:

```
STATUS: DONE
Findings: None — {reason why nothing was found, e.g. "all contracts satisfied", "no violations detected"}
```

NOT:
- Returning nothing
- Returning only the STATUS with no findings summary
- Omitting the section / block / response entirely

## Prohibited Instructions in Agent Files

Never write these as agent output instructions:

| Prohibited | Replace with |
|---|---|
| "Return nothing" | "Output: `[explicit success message]`" |
| "Return an empty response" | "Output: `STATUS: DONE — [what was verified]`" |
| "Omit this section if no X found" | "If no X found, include: `[explicit no-findings line]`" |
| "Silent success" | Explicit STATUS: DONE |
| "No output needed" | "Output: `STATUS: DONE — [why no action was needed]`" |

## Enforcement

When writing or reviewing agent files:
1. Check that a STATUS: DONE format exists in the agent's output section
2. Check that the "no findings" case produces explicit output — not silence
3. Check that "write to file" instructions are paired with STATUS output, not replacing it
4. Check `SendMessage` is present when the agent is used as a teammate
