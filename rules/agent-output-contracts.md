# Agent Output Contracts — Prohibited Instructions in Agent Definitions

Scope: persistent agent-definition files (`plugins/*/agents/*.md`) that an agent reloads on
every dispatch — not a one-off dispatch prompt. For prompt-level output requirements, see
`agent-orchestration:delegate`'s `sub-agent-contract.md`.

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
