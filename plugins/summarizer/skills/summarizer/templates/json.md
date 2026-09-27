---
format_id: json
format_name: JSON
description: Raw machine-readable summary with metadata, findings, gaps, uncertainty and sources.
---

# JSON Format

Use when the caller requests JSON or machine-readable output. Return one raw JSON object,
without Markdown fences, introductory prose or a caller STATUS envelope. The example below
illustrates the shape; do not copy its placeholder claims or measurements.

## Schema

```json
{
  "metadata": {
    "source_type": "file",
    "source_path": "source.txt",
    "summarized_at": "<actual ISO 8601 timestamp>",
    "method": "hybrid",
    "word_count_source": null,
    "word_count_summary": 0,
    "confidence": "medium",
    "confidence_notes": "<inspection scope, claim support and uncertainty>"
  },
  "summary": "<nonempty summary>",
  "findings": [{"item": "<claim>", "source_ref": "<source identity and location>"}],
  "not_found": [],
  "uncertain": [],
  "sources": [{"path": "source.txt", "accessed": "<actual access date>"}]
}
```

All shown top-level keys are required. Findings and sources contain the shown nonempty string
fields. `not_found` and `uncertain` are arrays of strings, even when empty. Metadata fields
follow [structured format definitions](./structured.md#schema), including nullable source word
counts and optional `compression_ratio`; source_path may be a list for multiple sources.
Do not wrap numbers in strings when the field represents a measurement.

## Fidelity constraints

Every finding carries source support, exact material numbers and qualifications. Keep searched
absence distinct from inaccessible/unassessed scope. Preserve critical limitations in summary
text and appropriate gap/uncertainty entries. Use the shared
[fidelity rules](../references/fidelity-rules.md), not an independent confidence policy.

This presentation is not the [evidence record](../references/evidence-record.md). Keep a required
sidecar separate; validate both the final presentation and the caller-bound record.
