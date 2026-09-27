---
format_id: table
format_name: Table
description: Attributed findings in a Markdown table with explicit finding status.
---

# Table Format

Use for tabular or comparison requests. Apply shared [fidelity rules](../references/fidelity-rules.md).

## Schema

```text
## Summary

[Lead with the answer and any critical limitation.]

| Finding | Detail | Source | Status |
| --- | --- | --- | --- |
| [item] | [claim with exact counts/qualifiers] | [source location] | Found |
| [searched item] | [inspected scope and absence] | [scope] | Not Found |
| [ambiguous item] | [uncertainty] | [source location] | Uncertain |

Source: [path or URL] | Confidence: [high|medium|low] | [actual access date]
```

## Fidelity constraints

All four named columns are required; an optional numbering column is permitted. Every `Found`
row needs a meaningful Source reference. Status values are exactly `Found`, `Not Found` or
`Uncertain`. Preserve one row for each empty Not Found or Uncertain category, using `None
identified` as the finding and that category as its status. Do not invent a missing feature
just to populate a row. State inaccessible/unassessed scope as such, not searched absence.

Escape literal pipe characters in cells. Keep the footer last, with source, confidence and
access date. Material numbers, conditions and failures must survive tabulation; source locations
must support the actual detail, not merely mention the same topic.
