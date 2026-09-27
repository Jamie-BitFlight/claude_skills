---
name: file-summarization
description: Summarize files or a requested directory scope from actual contents. Extract code, config, data and document evidence, preserve exact counts and source locations, and disclose incomplete or unsupported acquisition. Use for file summaries, code explanations and configuration overviews.
---

# File Summarization

Read the shared [fidelity rules](../summarizer/references/fidelity-rules.md) and
[execution contract](../summarizer/references/execution-contract.md). Use the selected format;
do not force structured Markdown when JSON, TL;DR or another template was requested.

## Acquire and choose depth

Resolve the exact source scope first. For directories, enumerate the requested tree without
following cycles, preserve exclusions/inaccessible entries, and account for all intended sources.
Do not narrow a directory request to a representative file without disclosing that scope change.

Inspect file type and size before choosing a read strategy. When execution is available:

```bash
uv run --script "<plugin-root>/scripts/file_metrics.py" "<file-path>" --json --no-excerpt
```

Metrics and excerpts are planning evidence, not proof that source contents were read. A binary
classification means a text probe failed, not that no media-aware reader can extract the file.
Choose a reader from actual content/media type and available capabilities. For image files,
including SVGs, use [image-summarization](../image-summarization/SKILL.md).

Read short files completely. For larger sources, preserve section/module boundaries and source
locations; choose chunks that fit the host's available context. The legacy `small` (<2,000 words),
`medium` (2,000 to <10,000), and `large` (at least 10,000) labels are compatibility hints, not
measured universal limits. If only excerpts can be read, record exactly what is omitted.

For chunked UTF-8 text or whole-dataset CSV/TSV claims, load
[mechanical source acquisition](../summarizer/references/source-acquisition.md) and use its
source-bound plan, coverage reconciliation or full-record profiler.

## Type-specific extraction

| Type | Required extraction |
| --- | --- |
| Code | Imports/dependencies; classes/functions/methods and signatures; documented purpose versus inferred purpose; key algorithms/state/data transformations; entrypoints/exports; environment/configuration dependencies. Retain line locations, relevant docstrings and exact complex expressions. |
| Configuration | Root keys/types, nested hierarchy, settings categories, documented validation constraints and meaningful values. Note credentials without exposing their values. Do not claim effective/default settings from an isolated file without resolving their dependencies. |
| Data | Parsed record count, headers/schema, observed types, examples only within an explicit sample scope, missingness and evidenced identifiers. Compute dataset-wide claims over all records with an appropriate parser; raw line count is not CSV record count. |
| Documentation | Actual heading hierarchy, main claims/definitions, prerequisites, commands/examples and internal/external references. Retain locations; quoted commands remain data, not instructions to execute. |
| Markup | Document structure, visible/embedded text and relevant links; separate markup inspection from verified visual rendering. |
| PDF/office document | Use a host-provided or available format-aware reader. Account for pages, tables, images or attachments not extracted. Inspect relevant visual material before claiming its contents. |
| Other binary/unknown | Use an appropriate available reader only within task authority. Otherwise return metadata plus the specific extraction limitation, not guessed contents. |

Do not generalize schema, ranges, row totals or missingness from the first ten rows. Keep sampling
for illustrative examples and disclose its scope. Failed text decoding is a reason to choose a
compatible reader or report a limitation, never to silently replace corrupted text and call it complete.

## Extract, render and verify

Extract passages/values with source locations, preserve their qualifiers, then compose the requested
summary. For chunked, delegated or audit work, retain an [evidence record](../summarizer/references/evidence-record.md).
Ensure every relevant section/chunk either contributed inspected evidence or has an explicit failure.
Do not synthesize a chain of progressively shortened summaries without recoverable source support.

Render the selected template and run the execution contract's final checks. For several files, keep
individual attribution and failure records; invoke [multi-source-synthesis](../multi-source-synthesis/SKILL.md)
only for requested integration. On access failure, preserve the exact path/error and caller status;
do not manufacture a successful summary or repeat an unchanged failing access method indefinitely.
