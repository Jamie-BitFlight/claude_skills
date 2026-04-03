---
name: python3-data
description: Python data, ETL, analysis, and scientific workflows with maintainable module boundaries and explicit validation at ingress points. Activates on pandas, numpy, scipy, jupyter, notebooks, ETL pipelines, tabular data ingestion, or scientific processing code.
user-invocable: false
---

# Python Data

Load `python3-core` for standing defaults. Load `python3-typing` for boundary schemas. Load `python3-testing` for parser and edge-case tests.

## Quality Checklist

- [ ] Schema validated at first stable ingress point — not deep in transforms
- [ ] `dtype=` explicit in `pd.read_csv()` / `pd.read_excel()` — never rely on inference
- [ ] No raw `pd.DataFrame` crossing module boundaries without documented column contract
- [ ] Merge/join results checked for unexpected nulls and row count changes
- [ ] `model_config = {"strict": True}` on all Pydantic boundary models
- [ ] No `inplace=True` — deprecated, returns `None`, causes silent bugs
- [ ] Notebook logic that survived 3+ uses extracted into tested modules

## Gotchas

| Trap | What to do instead |
|---|---|
| `df["a"]["b"] = x` (chained indexing) | `df.loc[:, "b"] = x` — chained indexing silently fails |
| `.apply(lambda)` on large frames | Vectorized ops first; `.apply()` only when no vectorized path exists |
| `pd.merge()` without post-check | Assert no unexpected nulls or duplicate keys after merge |
| `df.drop(..., inplace=True)` | `df = df.drop(...)` — `inplace` is deprecated and returns `None` |
| Bare `pd.read_csv(path)` | Always pass `dtype=` to prevent silent type inference errors |

## Decision Table

| Task | Use | Not |
|---|---|---|
| Tabular < 1M rows | pandas | Polars (overhead not justified) |
| Tabular > 1M rows or need speed | Polars | pandas |
| SQL-like analytics on local files | DuckDB | Loading everything into pandas |
| Read-only TOML config | `tomllib` (stdlib, binary mode `"rb"`) | `tomlkit` |
| Read/write TOML preserving comments | `tomlkit` (text mode) | `tomllib` |

## Module Layout

```text
etl/
├── ingest.py      # raw data loading (boundary)
├── validate.py    # schema validation (boundary)
├── transform.py   # business logic (typed core)
├── load.py        # output writing (boundary)
└── types.py       # shared typed models
```
