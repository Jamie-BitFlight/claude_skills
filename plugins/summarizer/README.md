<p align="center">
  <img src="./assets/hero.png" alt="summarizer" width="800" />
</p>

# summarizer

Summarize inspected files, URLs, images and source collections while preserving evidence, exact
material counts, qualifications, acquisition failures and uncertainty.

## Installation and entrypoints

```text
/plugin install summarizer@jamie-bitflight-skills
/summarizer:summarizer "src/api/routes.ts"
/summarizer:file-summarization "src/api/routes.ts"
/summarizer:url-summarization "https://example.com/documentation"
/summarizer:image-summarization "screenshots/dashboard.png"
/summarizer:multi-source-synthesis
/summarizer:agent-result-relay
```

The main skill routes by source scope, transport and media type. Source skills also work directly.
The file, URL and image agents load those same canonical methods for autonomous delegated work.
A host without native agents uses the direct path rather than pretending delegation occurred.

## Formats and evidence

Request structured Markdown, bullets, TL;DR, JSON, table or outline. The default is structured;
JSON is raw parseable JSON, not Markdown with a JSON block. A short presentation still preserves
critical qualifications, failures and uncertainty. Templates control presentation, not truth rules.

Delegated, chunked, multi-source and audit-requested work retains a caller-bound evidence sidecar:
source inventory and coverage, findings with support locations, selected findings, gaps, conflicts,
confidence rationale and the hash of the actual delivered summary. Short inline tasks can retain
these distinctions in context without writing an artifact.

See the [execution contract](./skills/summarizer/references/execution-contract.md) for caller format
controls and STATUS-envelope handling, and the [evidence record](./skills/summarizer/references/evidence-record.md)
for the schema and producer/consumer procedure.

## Mechanical tools

Run from a checkout, or replace paths with the installed plugin location:

```bash
uv run --script plugins/summarizer/scripts/file_metrics.py source.md --json --no-excerpt
uv run --script plugins/summarizer/scripts/source_tools.py profile data.csv
uv run --script plugins/summarizer/scripts/summary_record.py schema
node plugins/summarizer/hooks/output-contract.cjs --format json --input summary.json
```

[Source acquisition](./skills/summarizer/references/source-acquisition.md) documents caller-budgeted
chunk planning, stable offsets, source-bound receipts and coverage reconciliation. CSV/TSV profiling
uses every parsed record and handles quoted newlines; it does not infer dataset-wide properties
from a small sample. The implementation uses in-memory snapshots, not a streaming/low-memory engine.
PDF, office documents and other media require an available appropriate reader; no bundled parser or
host capability is claimed merely because a filename is recognized.

## Validation limits

The output validator checks structure. The evidence validator checks schema, source/reference
consistency, caller identity and output bytes. Neither establishes that a source was actually read
or that a claim follows from it. The Claude stop hook is a convenience adapter: missing metadata,
unavailable artifacts or an exhausted correction emit NOT_VALIDATED, never evidence of success.
The caller validates the final result after synthesis or other transformations.

See [evaluation instructions](./evals/README.md) for deterministic commands, behavioral cases,
independent verification and live-host smoke tests. Authored cases are not passing model runs.
Current scope and ownership are in [PURPOSE.md](./PURPOSE.md) and [ARCHITECTURE.md](./ARCHITECTURE.md).
