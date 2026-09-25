---
name: multi-source-synthesis
description: Integrate multiple source findings into an attributed synthesis or comparison. Use for combine these summaries, synthesize results, merge findings or multi-source analysis. Preserve claim-level provenance, coverage, qualifiers, conflicts and uncertainty rather than repeatedly compressing narrative summaries.
---

# Multi-Source Synthesis

Read [fidelity rules](../summarizer/references/fidelity-rules.md), the
[execution contract](../summarizer/references/execution-contract.md) and the
[evidence handoff](../summarizer/references/evidence-record.md).

## Establish inputs

Inventory every requested source and its acquisition outcome, including failures. Prefer evidence
records with original source locations. When given prose summaries, recover their evidence from
available source references. If originals cannot be accessed, treat the supplied summaries as the
sources being synthesized and state that limitation; do not imply independent original-source checks.
Do not reject user-requested synthesis merely because an input uses a different presentation format.

## Integrate

1. Compare findings by subject, predicate, conditions, units, time/version and scope. Deduplicate only
   equivalent claims; retain different support sets for different qualifications. For example, a
   source saying `100 requests/minute` does not support a second source's `per key` qualifier.
2. Group related findings by theme rather than producing an unintegrated source-by-source list.
   Preserve source-by-source distinctions when the user requests comparison or viewpoints differ.
3. Order themes by the user's question and relevant conceptual dependencies. Adjust presentation
   detail to the requested format/focus, not an invented finding-count threshold.
4. Keep conflicting claims and their provenance visible. Note differences in authority, currency or
   applicability without silently resolving an unresolved conflict. Do not count copied sources as
   independent corroboration.
5. Write the synthesis from the evidence. Reopen source passages when the handoff cannot resolve a
   qualification. Separate observations, attributed conclusions and your own explicit inferences.
6. Check for material evidence lost during selection, deduplication or formatting. Preserve exact
   counts/failure reasons and distinguish searched absence from unassessed/inaccessible scope.

For interactive teams, collect explicit terminal results and preserve each worker's evidence before
joining. Worker discussion does not replace this synthesis pass or an independent verifier. The
caller owns worker cleanup; do not infer completion from an idle notification alone.

## Deliver

Create a synthesis evidence record tied to the caller's complete source inventory and the final
output bytes. Record conflict links, qualifiers, selected findings and coverage gaps. Render the
requested template (default structured), with inline attribution to the sources supporting each
claim. In a multi-source presentation, retain all contributing source references and access dates.

Run the record and format checks after the final synthesis. A worker's checks do not validate this
new artifact. Report unsupported claims or missing raw evidence explicitly. Do not convert a valid
schema, agreement between workers, or an empty conflict list into a factual-verification claim.
