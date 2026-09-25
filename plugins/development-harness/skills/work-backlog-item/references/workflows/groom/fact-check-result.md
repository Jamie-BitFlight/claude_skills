# Fact-Check result contract

This DH handoff is shared by the fact-checker, grooming swarm and finalizer. It owns
result serialization and claim identity, not the method used to research a claim.
Read it before producing, persisting or consuming a Fact-Check result.

## Result record

Emit one record per supplied claim with these literal lowercase field names. Select
one verdict token; do not emit the alternatives as a value.

```text
verdict: VERIFIED | REFUTED | INCONCLUSIVE
claim: {exact supplied claim}
evidence: {tool result citation and relevant observed content}
source: {URL, file:line, or exact command identifying that evidence}
```

This is plain text, not YAML: a claim can itself contain a colon. Keep field names
at the start of their lines; indent continuation lines belonging to a field. Keep
multiple records separate. A verdict belongs only to the claim in its own record.

Retain the supporting detail the producer collected: direct source excerpts,
retrieval dates, cross-check sources and findings, explanation connecting evidence
to verdict, verification method, and material version/environment limits. Include
that detail under the corresponding field or after the core record; a shorter
transport format is not permission to discard evidence. A source pointer alone is
not proof that its content supports the verdict.

`STATUS:` is the agent delivery envelope, not part of the persisted record. Emit it
according to `dh:subagent-contract`; do not embed it in `backlog_groom` content.

## Claim identity

Keep the exact supplied claim as the identity, even when analysis narrows a vague
assertion. Explain any narrower tested scope separately. Evidence for only that
narrower scope does not establish the entire original claim: return INCONCLUSIVE
when the supplied claim cannot be resolved as stated.

For a description line `**Hypothesis**: {text}`, the record's claim is exactly
`HYPOTHESIS: {text}`. Preserve the text after the marker verbatim, including case,
punctuation and whitespace. Do not paraphrase it, merge similar hypotheses, or add
a second `HYPOTHESIS:` prefix when the dispatcher already supplied one. Compare the
whole claim value, not a substring, position, or shared topic. Each hypothesis is
verified and matched independently.

## Unavailable evidence

When evidence or its source cannot be obtained, return INCONCLUSIVE. Keep the core
fields present and explicitly record what is unavailable and what was attempted;
do not invent a citation. For example:

```text
verdict: INCONCLUSIVE
claim: HYPOTHESIS: retries fail because the cache is stale
evidence: unavailable — source lookup failed; no claim-supporting result was obtained
source: unavailable — the requested repository evidence could not be read
```

## Validation and handoff

Before persistence, check each record against the supplied claim and this contract.
Missing or invalid verdicts, missing claim identity, duplicate core fields, or
conflicting unresolved verdicts for the same claim are not valid verification.
Correct the result or report the problem; do not publish it as successful evidence.
Missing evidence/source requires the explicit INCONCLUSIVE form above, not a
positive verdict with an empty citation.

When consuming stored results, inspect the active, non-struck entries and validate
each relevant record before using its verdict. A present section, `STATUS: DONE`,
or one valid sibling record does not validate malformed or missing results. Request
a corrected result from the fact-checker through the workflow's existing recovery
path; do not silently reinterpret unsupported output as VERIFIED or rewrite the
producer's evidence yourself. A well-formed INCONCLUSIVE result is usable evidence
of an unresolved question, not a failed delivery and not proof of the claim.

For RT-ICA, preserve the established mapping: REFUTED → MISSING and INCONCLUSIVE →
DERIVABLE. The finalizer owns hypothesis resolution, including single-hypothesis
RCA precedence and description write-back; this record does not change that policy.

The fact-checker persists only to the supplied item's Fact-Check section. Without
an item reference it returns the record without backlog writes. Persistence errors
follow the existing subagent failure contract; never claim a failed write succeeded.
