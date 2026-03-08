# Accuracy Findings: frustration-analysis SKILL.md vs server.py

**Date:** 2026-03-08
**Session:** session_01AvukJDFipxCgYsoMEhiePE
**File audited:** `plugins/frustration-analyzer/skills/frustration-analysis/SKILL.md`
**Source of truth:** `plugins/frustration-analyzer/mcp/server.py`

---

## Critical Inaccuracies Found

### 1. DuckDB is NOT used during scanning

**SKILL.md implies:** DuckDB is involved in `scan_transcripts`
**Reality:** `_scan_transcripts_impl` reads JSONL files with pure Python (`_read_jsonl`). DuckDB is only used for indexed insult storage (`index_insult`, `list_insults`, `get_scenario`, `top_insults`).

**Fix required in Step 2:** Remove any implication that DuckDB is queried during scan. State explicitly: "Scanning reads JSONL files directly — no DuckDB involved at this stage."

---

### 2. `scan_transcripts` already bundles context — no lazy fetch exists

**User mental model:** Scan returns metadata only, then context is fetched lazily for spicy messages.
**Reality:** `_scan_transcripts_impl` calls `_extract_scenario(records, idx, context_window)` for EVERY message at scan time. Context is always bundled. There is no separate "fetch context for spicy ones" step during scanning.

**Actual two-phase workflow (what Claude does, not the server):**
1. `scan_transcripts` → returns messages WITH `context` already embedded
2. Claude reads `text` + `context` per message → decides if spicy → calls `index_insult` for qualifying ones

**Fix required:** Step 2 should state that context comes pre-bundled. The user's described pattern (metadata first, context only for spicy ones) does not exist server-side — that decision logic lives in Claude's classification step.

---

### 3. Wrong parameter name in `get_scenario` example

**SKILL.md line 98:**
```text
mcp__frustration-analyzer__get_scenario(insult_id={id}, context_n=10)
```
**Actual signature:** `get_scenario(insult_id: int, db_path: str = "")`

`context_n` does not exist. The context window size is fixed at index time (stored in `insult_scenarios.context_window_n`). Retrieval always returns whatever was captured.

**Fix:** Remove `context_n=10` from the example. Replace with `db_path=""` if a parameter example is needed, or just show `get_scenario(insult_id={id})`.

---

### 4. Wrong parameter names in `top_insults` example

**SKILL.md line 215:**
```text
mcp__frustration-analyzer__top_insults(dimension="humor", limit=5)
```
**Actual signature:** `top_insults(n: int = 10, sort_by: str = "composite", db_path: str = "")`

- `dimension` → should be `sort_by`
- `limit` → should be `n`

**Fix:** Update example to `top_insults(n=5, sort_by="humor")`

---

### 5. `sanitize_text` example has non-existent parameter

**SKILL.md line 154:**
```text
mcp__frustration-analyzer__sanitize_text(text="{text}", replace_profanity=true)
```
**Actual signature:** `sanitize_text(text: str)`

`replace_profanity` does not exist. The tool only strips PII patterns (email, IP, token, path, URL) — it does not touch profanity.

**Fix:** Remove `replace_profanity=true` from the example.

---

## Summary

| # | Location | Issue | Severity |
|---|----------|-------|---------|
| 1 | Step 2 description | DuckDB not used during scan | Conceptual |
| 2 | Step 2/5 description | Context bundled at scan time, not fetched lazily | Conceptual |
| 3 | Example line 98 | `context_n` parameter does not exist on `get_scenario` | Wrong API |
| 4 | Example line 215 | `dimension`/`limit` don't exist on `top_insults` | Wrong API |
| 5 | Example line 154 | `replace_profanity` doesn't exist on `sanitize_text` | Wrong API |

---

## Required SKILL.md Edits

1. Step 2 — Add: "Scanning reads JSONL files directly; DuckDB is not used at this stage."
2. Step 2 — Add: "Each returned message includes `context` (N preceding turns) already bundled."
3. Step 5 — Clarify: "`get_scenario` retrieves scenario data from DuckDB for an **already indexed** insult. The context window size was set when `index_insult` was called."
4. Example line 98 → `get_scenario(insult_id=42)`
5. Example line 215 → `top_insults(n=5, sort_by="humor")`
6. Example line 154 → `sanitize_text(text="{text}")`
