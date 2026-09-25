---
name: summarizer
description: Route requests to summarize files, URLs, images, inline text, or multiple sources. Select the requested format and preserve evidence, exact counts, uncertainty and source coverage through summarization, synthesis and agent-result relay.
---

# Summarizer

Read the [fidelity rules](./references/fidelity-rules.md) and
[execution contract](./references/execution-contract.md). They govern all routes below.

## Resolve the request

Identify the requested operation (summary, synthesis, comparison or relay), source scope, format
and any explicit length/focus requirement. Preserve user-provided directory scope; do not silently
replace a directory with one file. Enumerate readable sources and report omissions. Do not turn a
summary request into implementation, external research or code execution without authorization.

Select and read one template:

| Signal | Format | Template |
| --- | --- | --- |
| No format specified; full/detailed summary | structured | [structured](./templates/structured.md) |
| Bullet points, key points | bullets | [bullets](./templates/bullets.md) |
| TL;DR, one-liner, nutshell | tldr | [TL;DR](./templates/tldr.md) |
| JSON, machine-readable data | json | [JSON](./templates/json.md) |
| Table, tabular, grid | table | [table](./templates/table.md) |
| Outline, hierarchy, table of contents | outline | [outline](./templates/outline.md) |

The selected format overrides legacy structured-only requirements in source skills. In particular,
raw JSON has no Markdown envelope and TL;DR has no mandatory What Was NOT Found section.

## Route sources

Resolve cardinality first, then transport (local, URL, inline) and actual media type. A local
image is not ordinary text just because it has a file path; a URL can return an image or PDF.
Inspect content/type evidence rather than relying solely on extensions.

| Input | Method |
| --- | --- |
| Text/code/config/data/document file | [file-summarization](../file-summarization/SKILL.md) |
| URL | [url-summarization](../url-summarization/SKILL.md); route acquired visual content to the image method |
| Image or screenshot | [image-summarization](../image-summarization/SKILL.md) |
| Inline text | Extract passages directly, then apply fidelity and the selected template |
| Multiple sources | Apply the appropriate method to each; synthesize only when requested |
| Existing agent result | [agent-result-relay](../agent-result-relay/SKILL.md) |

For requested integration, load [multi-source-synthesis](../multi-source-synthesis/SKILL.md).
Otherwise keep individual summaries separately attributable. Record failed sources alongside the
successful ones rather than dropping them from the input set.

## Delegate when useful

Use `summarizer:file-summarizer`, `summarizer:url-summarizer`, or `summarizer:image-summarizer` for
an autonomous task when the host supports delegation. For an interactive conversation, or when
agents are unavailable, run the same source skill directly.

Forward the format, source scope, focus, assigned output path and caller return contract. Supply
the exact initial-task controls defined in the execution contract. Workers read their own skills
and sources. Preserve context isolation instead of assuming parent-loaded instructions carry over.

For multiple independent sources, choose parallel extraction only when available capacity and
source cost justify it. Use sequential execution when sources depend on earlier results. Interactive
teams are appropriate only when workers need communication, not simply because there are three
sources. If teams are used, collect explicit terminal results, retain each source's provenance,
perform the full synthesis step and release workers. Worker agreement is not independent verification.

## Deliver

Check support and coverage, render the selected template, then validate the final delivered result
under the execution contract. A worker's validation does not cover a later rewritten synthesis.
Preserve caller status envelopes separately from summary artifacts. Relay exact counts and failure
reasons, name full result artifacts, and keep unverified behavior explicit.
