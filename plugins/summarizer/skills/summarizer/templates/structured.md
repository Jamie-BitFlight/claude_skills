---
format_id: structured
format_name: Structured Summary
description: Default structured summary with YAML metadata, source attribution, gaps and uncertainty.
---

# Structured Summary Format

Use when no format was requested or the caller requests a detailed structured summary.
The [fidelity rules](../references/fidelity-rules.md) own meaning and confidence;
the [execution contract](../references/execution-contract.md) owns validation.

## Schema

Output starts with YAML frontmatter, not a Markdown code fence:

```yaml
---
source_type: file
source_path: "<exact path, URL, inline identity, or list of sources>"
summarized_at: "<actual ISO 8601 timestamp>"
method: hybrid
word_count_source: null
word_count_summary: 0
confidence: high
confidence_notes: "<inspection scope, support and unresolved uncertainty>"
---
```

Replace example values with the actual result. `source_type` is `file`, `url`, `image`,
`inline`, or `multi-source`. `method` is `extractive`, `abstractive`, or `hybrid`.
Use a YAML list for multiple source paths. Source word count is an integer or null when
unavailable/not applicable. Summary word count measures the Summary section only.
`compression_ratio` is optional: summary/source words, or null when not meaningful (including
an empty source). Do not invent measurements. Confidence is `high`, `medium`, or `low` with
rationale; source credibility is not identical to faithfulness of the summary.

## Body sections

Use these headings in order:

1. `## Summary` — lead with the answer, preserving the source's terminology and qualifications.
2. `## What Was Found` — findings with source locations and exact material counts/identifiers.
3. `## What Was NOT Found` — items actually searched for within a stated scope; distinguish
   inaccessible and unassessed scope explicitly rather than implying a negative finding.
4. `## Uncertain` — ambiguity, conflicts and explicitly marked interpretations.
5. `## Sources` — exact source references and actual access dates.

Keep empty categories explicit as `None` or `N/A`; that does not imply an unperformed search.
Every factual claim needs recoverable supporting evidence. Preserve sourced negative statements
without turning silence into a claim of nonexistence. Critical limitations stay in the Summary
as well as their detailed category. A total acquisition failure is a caller error result, not
a successful empty structured summary.
