---
format_id: bullets
format_name: Bullet Points
description: Concise attributed findings with explicit gaps, uncertainty and source footer.
---

# Bullet Points Format

Use for bullet points, key points or quick highlights. No YAML frontmatter is required.

## Schema

```text
## Key Findings

- [Finding with exact counts and qualifications] (source: [location])

## Not Found

- [Searched item and inspected scope, or None]

## Uncertain

- [Ambiguous item and source, or None]

Source: [path or URL] | Confidence: [high|medium|low] | [actual access date]
```

## Fidelity constraints

Each factual finding needs a source reference; empty-category markers need no invented citation.
Keep all three sections. Preserve important counts, failure reasons and conditions. Distinguish
searched absence from inaccessible/unassessed scope. Keep the source/confidence/date footer last.
Apply the shared [fidelity rules](../references/fidelity-rules.md) for meaning and confidence.
