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

A plain `Agent()` call already returns this STATUS block straight back to whoever dispatched
it — no `SendMessage` needed to report completion. Put anything a later step reads in a named
destination that step can read back — a task section, an artifact, a review thread — never only
in the STATUS message.

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

When writing or reviewing an agent file, and when launching one:
1. Check that a STATUS: DONE format exists in the agent's output section
2. Check that the "no findings" case produces explicit output — not silence
3. Check that "write to file" instructions are paired with STATUS output, not replacing it
4. Do not instruct an agent to report completion via `SendMessage` — a plain `Agent()` call's
   return value already carries the STATUS block to the dispatcher.
5. Check that any result a later step reads is written to a named destination, not only messaged
