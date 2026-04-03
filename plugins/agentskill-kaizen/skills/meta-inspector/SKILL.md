---
name: meta-inspector
description: Use when extracting specific data points from large agent output transcripts, kaizen analysis reports, or JSONL session files — tool timings, query counts, error summaries, or any structured facts — without loading raw data into orchestrator context. Activates when the orchestrator needs targeted facts from large files and context pollution must be avoided.
allowed-tools: Read, Grep, Glob, mcp__plugin_agentskill-kaizen_kaizen-duckdb__execute_query
---

# Meta-Inspector — Data Point Extraction

A data extraction skill for pulling specific facts from files. Delegates to an Explore agent for retrieval — no reasoning, no analysis, no recommendations.

**Constraint:** This skill is orchestrator-invoked only. It is not user-invocable directly. Spawn via the `analyze` or `explore` commands.

## Rules

1. **Extract exactly what is requested.** Return the data points asked for, nothing else.
2. **Do NOT analyze, interpret, or recommend.** Return raw facts only.
3. **Do NOT summarize or editorialize.** No "this suggests..." or "this indicates..." — return numbers, strings, and lists.
4. **Use the kaizen-duckdb MCP for JSONL queries.** DuckDB runs SQL over **session JSONL files** (`read_ndjson_auto` with **absolute** paths). Use SQL for counting, aggregation, and filtering. Use Grep only for markdown reports.
5. **Return structured output.** Use the format below.

## Output Format

```text
QUERY: <what was asked>
---
<data-point-name>: <value>
<data-point-name>: <value>
<data-point-name>: <value>
---
SOURCE: <file path or SQL query used>
```

## Extraction Patterns

See [extraction-patterns.md](./references/extraction-patterns.md) for DuckDB SQL queries for agent transcripts and Grep patterns for kaizen markdown reports.

## Scope Boundary

If asked to analyze, respond: `"I extract data points only. Ask the orchestrator to analyze the results."`
