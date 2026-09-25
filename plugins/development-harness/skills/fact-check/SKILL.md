---
name: fact-check
description: Verify multiple factual claims in backlog items, skill documentation, or plugin content. Extracts discrete claims, delegates each to the canonical factual-verification process, and aggregates VERIFIED/REFUTED/INCONCLUSIVE results. Use for "fact check", "verify claims", or a set of unverified factual assertions.
argument-hint: '[backlog-item-title | plugin-path | --all-unverified]'
user-invocable: true
---

# Fact Check

Coordinate verification of a set of factual claims. `dh:verify-factual-claim` owns the verification method and verdict semantics; do not restate or weaken them here.

1. Resolve the requested backlog item, file/path, or unverified set.
2. Extract discrete falsifiable claims. Exclude structural checks, code-logic defects, and open-ended research questions.
3. For each claim, identify its source location and any known version/environment conditions.
4. Dispatch independent verification work where parallelism is useful. Each worker MUST load `dh:verify-factual-claim` and return its complete verdict.
5. Aggregate verdicts without changing them. Preserve contradictory evidence and INCONCLUSIVE gaps.
6. Return a report containing scope, claims checked, verdict counts, each complete verdict, and unresolved evidence.

When a DH workflow requires backlog persistence, use the caller's established write contract rather than inventing lifecycle/status changes here. Do not automatically commit, close, relabel, or otherwise mutate backlog lifecycle state as a consequence of fact checking.
