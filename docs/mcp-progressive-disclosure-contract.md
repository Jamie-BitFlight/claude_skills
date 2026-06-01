# MCP Progressive Disclosure Contract

This document defines the three-layer progressive disclosure contract for MCP data-returning
interfaces. `backlog_view` is the **reference implementation**. Any compliant tool may implement
this contract to provide the same three-layer interaction model.

**Status**: Released — #2515 (`sam_plan read/ready` implementation) may proceed against this
contract without waiting for further changes. All four contract layers are implemented and covered
by acceptance tests.

---

## Contents

- [Overview](#overview)
- [Layer 1 — Map](#layer-1--map)
- [Layer 2 — Navigate](#layer-2--navigate)
- [Layer 3 — Extract](#layer-3--extract)
- [Error-on-Miss Invariant](#error-on-miss-invariant)
- [Token Budget Targets](#token-budget-targets)
- [Parameter Reference](#parameter-reference)
- [Complete Workflow Example](#complete-workflow-example)

---

## Overview

Without this contract, an agent calling an MCP data-returning tool receives the **complete item**
in a single response. For large items this overflows the agent's token budget and forces either
blind full-fetch or trial-and-error section guessing.

The progressive disclosure contract provides three orthogonal capabilities:

| Layer | Parameter(s) | Returns | Size guarantee |
|-------|-------------|---------|---------------|
| Map | `map=True` | Flat ordinal structure of the document | < 2,000 tokens |
| Navigate | `navigate="4.0"` | Full content at that ordinal | Item-dependent |
| Extract | `navigate="4.0"`, `head=4000` | First 4,000-token window + continuation hint | ≤ `head` tokens |

All four parameters are optional with safe defaults. Existing calls without these parameters route
to **PASSTHROUGH** mode and execute the unchanged legacy code path.

---

## Layer 1 — Map

Call `backlog_view` with `map=True` to receive the item's ordinal structure.

```text
backlog_view(selector="#2515", map=True)
```

### Map response fields

```text
{
  "selector": "#2515",
  "total_sections": <count of level-1 sections>,
  "total_est_tokens": <sum of level-1 section estimates>,
  "over_budget": <true when total exceeds the tool token budget>,
  "map_text": "<formatted map, always < 2,000 tokens>"
}
```

### Map line format

Each line in `map_text` uses this exact format:

```text
{ordinal} {title} ({est_tokens}t) [— "{preview}"]
```

Where:

- `{ordinal}` — dot-path key, digits and dots only (e.g. `0`, `4.0`, `4.0.1`)
- `{title}` — section or entry heading, capped at 50 chars (truncated with `…` when longer)
- `{est_tokens}t` — tiktoken cl100k_base token count for this node
- `— "{preview}"` — first non-empty content line, capped at 60 chars; omitted when absent

Example map output (illustrative):

```text
0 Story (42t) — "As a developer using Claude Code skills, I want to"
1 Description (1420t) — "The development harness has multiple MCP interfaces"
2 Acceptance Criteria (380t) — "AC-1: Map of large item under 2,000 tokens"
3 Concerns (312t) — "Pre-existing concerns in progressive_markdown/"
4 RT-ICA (4250t) — "RT-ICA Final: MCP progressive disclosure contract"
4.0 RT-ICA entry (4250t) — "RT-ICA Final: MCP progressive disclosure contract"
```

### Level-2 emission rule

Level-2 lines (e.g. `4.0`) are emitted only when a section has more than one entry **or** its
token estimate exceeds the tool token budget. This keeps the map under 2,000 tokens even for
documents with many sections.

Empty sections (0 entries) appear at level-1 with `0t` and no level-2 children.

---

## Layer 2 — Navigate

Call `backlog_view` with `navigate=<ordinal>` to retrieve the full content at that position.

```text
backlog_view(selector="#2515", navigate="4.0")
```

The ordinal must exactly match one of the dot-path keys in the map. Obtain valid ordinals by
calling with `map=True` first.

### Navigate response fields

```text
{
  "ordinal": "4.0",
  "title": "RT-ICA entry",
  "content": "<full section/entry content>",
  "total_tokens": <exact cl100k_base count>,
  "truncated": false
}
```

`truncated` is always `false` for navigate-without-head responses. To paginate large content,
add `head=N` to activate Extract mode.

### Ordinal format

Valid ordinals match the pattern `^(\d+\.)*\d+$` — digits and dots only, one or more
digit-groups separated by single dots. Examples:

| Ordinal | Meaning |
|---------|---------|
| `"0"` | First level-1 section |
| `"4"` | Fifth level-1 section (0-based) |
| `"4.0"` | First entry within the fifth section |
| `"4.0.1"` | Second sub-heading within that entry (rare) |

---

## Layer 3 — Extract

Add `head=N` to a navigate call to request a token-bounded window.

```text
backlog_view(selector="#2515", navigate="4.0", head=4000)
```

### Extract response fields

```text
{
  "ordinal": "4.0",
  "title": "RT-ICA entry",
  "content": "<first 4,000 tokens of content>",
  "total_tokens": <exact count of full content before truncation>,
  "returned_tokens": <tokens actually returned in this window>,
  "truncated": true,
  "next_call": "backlog_view(selector=\"#2515\", navigate=\"4.0\", head=4000, skip_tokens=4000)"
}
```

When `truncated` is `false`, `next_call` is `null` and all content has been delivered.

### Pagination with skip_tokens

Page through large content by repeating the call with the `skip_tokens` value from the previous
`next_call` hint:

```text
# Window 1 — first 4,000 tokens
backlog_view(selector="#2515", navigate="4.0", head=4000)
# → truncated=true, next_call="...skip_tokens=4000"

# Window 2 — next 4,000 tokens
backlog_view(selector="#2515", navigate="4.0", head=4000, skip_tokens=4000)
# → truncated=true, next_call="...skip_tokens=8000"

# Window 3 — remainder
backlog_view(selector="#2515", navigate="4.0", head=4000, skip_tokens=8000)
# → truncated=false, next_call=null
```

The `next_call` hint is advisory — an agent may choose a different `head` size or `skip_tokens`
offset. The hint uses `skip_tokens=` (a within-content token offset), **not** `offset=`.

### offset vs skip_tokens distinction

These two parameters address different concerns and must not be substituted for each other:

| Parameter | Type | Meaning |
|-----------|------|---------|
| `offset` | entry-block index | Skip N complete entry blocks from the body start |
| `skip_tokens` | token offset (cl100k_base) | Skip the first N tokens within a single content unit |

`offset` is a coarse pagination mechanism for entry blocks. `skip_tokens` is a fine-grained
pagination mechanism for token-bounded extraction within a single ordinal unit.

---

## Error-on-Miss Invariant

Missing ordinals and missing sections both return explicit errors — never silent fallback.

### Navigate miss

When the requested ordinal does not exist in the document map, the call returns an error:

```text
{
  "error": "Ordinal '9.0' not found. Valid ordinals: ['0', '1', '2', '3', '4', '4.0']"
}
```

The error message includes all valid ordinals, which are identical to the keys visible in
the `map_text`. Use `map=True` first to avoid invalid ordinal requests.

### Section filter miss (legacy `section=` / `sections=[]` parameters)

When a `section` or `sections` filter matches no section in the item, the response is an
error dict with **no `body` field**:

```text
{
  "error": "Section not found: 'NonExistent'",
  "valid_sections": ["Acceptance Criteria", "Concerns", "RT-ICA", "Description"],
  "section_filter_miss": true,
  "suggestion": "Did you mean: 'Description'?"   ← only present when a close match exists
}
```

The `suggestion` key is present only when difflib finds a close match (SequenceMatcher ratio ≥
0.6). The absence of a `body` key distinguishes this error from a content response.

**Before this contract**: missing sections silently returned the full unchanged body. That silent
fallback is removed. Callers that previously relied on approximate section names should use
`map=True` to discover exact section names or use `sections_index` from a summary-mode response.

---

## Token Budget Targets

Token counts are computed with tiktoken cl100k_base throughout this contract (ADR-2). All limits
and estimates use this encoding; character-count approximations are not used.

| Limit | Value | Applies to |
|-------|-------|-----------|
| Map response | < 2,000 tokens | All `map=True` responses, regardless of item size |
| Default tool budget | `MAX_MCP_OUTPUT_TOKENS − 500`, else 9,500 | Full-fetch PASSTHROUGH responses |
| `head` maximum | 25,000 tokens | Any single EXTRACT window |
| `head` minimum | 1 token | Any single EXTRACT window |

The tool budget (9,500 token default) is computed at import from the `MAX_MCP_OUTPUT_TOKENS`
environment variable minus a 500-token envelope. This budget governs the existing summary/full
PASSTHROUGH path; progressive disclosure layers bypass it — agents control the window size
explicitly with `head=N`.

The 2,000-token map guarantee holds for any document regardless of size because level-2 lines
are emitted only when necessary (see [Layer 1 — Map](#layer-1--map)).

---

## Parameter Reference

All four parameters are optional. Absent parameters default to PASSTHROUGH mode (existing
behavior).

| Parameter | Type | Default | Constraints |
|-----------|------|---------|-------------|
| `map` | bool | `False` | Mutually exclusive with `navigate` |
| `navigate` | str \| None | `None` | Must match `^(\d+\.)*\d+$` |
| `head` | int \| None | `None` | 1–25,000; requires `navigate` |
| `skip_tokens` | int | `0` | ≥ 0; requires `head` and `navigate` |

### Valid combinations

| `map` | `navigate` | `head` | `skip_tokens` | Mode |
|-------|-----------|--------|--------------|------|
| — | — | — | — | PASSTHROUGH |
| `True` | — | — | — | MAP |
| — | `"4.0"` | — | — | NAVIGATE |
| — | `"4.0"` | `4000` | — | EXTRACT (window 1) |
| — | `"4.0"` | `4000` | `4000` | EXTRACT (continuation) |

### Invalid combinations that raise errors

| Combination | Error |
|-------------|-------|
| `map=True, navigate=…` | `map` and `navigate` are mutually exclusive |
| `map=True, head=…` | `map` is incompatible with `head` |
| `head=…` without `navigate` | `head` requires `navigate` |
| `skip_tokens>0` without `head` | `skip_tokens` requires `head` |
| Invalid ordinal format | Ordinal must match `^(\d+\.)*\d+$` |

---

## Complete Workflow Example

```text
# Step 1 — Map: discover ordinal structure (always < 2,000 tokens)
backlog_view(selector="#2515", map=True)

# Step 2 — Navigate: fetch the RT-ICA section (may be large)
backlog_view(selector="#2515", navigate="4.0")
# If total_tokens > budget, proceed to Step 3

# Step 3 — Extract: page through in 4,000-token windows
backlog_view(selector="#2515", navigate="4.0", head=4000)
# Read content; if truncated=true, continue:
backlog_view(selector="#2515", navigate="4.0", head=4000, skip_tokens=4000)
# Repeat using next_call hint until truncated=false
```

---

## Implementing This Contract in Other Tools

`backlog_view` is the reference implementation. To add progressive disclosure to another
data-returning tool (e.g. `sam_plan read`, `sam_plan ready`):

1. Add the same four optional parameters (`map`, `navigate`, `head`, `skip_tokens`) with the
   same defaults and validation rules as documented in [Parameter Reference](#parameter-reference).
2. On PASSTHROUGH (no disclosure params), execute the existing code path unchanged.
3. On MAP: normalize the tool's response into an ordered section list, assign dot-path ordinals,
   and produce `map_text` using the line format defined in [Layer 1 — Map](#layer-1--map).
4. On NAVIGATE: resolve the ordinal to its content and return the navigate response shape.
5. On EXTRACT: apply the token-bounded extractor and assemble the `next_call` hint using
   `skip_tokens=` continuation (not `offset=`).
6. On ordinal miss: raise an error listing all valid ordinals (see
   [Error-on-Miss Invariant](#error-on-miss-invariant)).

The token encoding and budget derivation are defined in the reference implementation at
[`../plugins/development-harness/progressive_markdown/models.py`](../plugins/development-harness/progressive_markdown/models.py)
and
[`../plugins/development-harness/backlog_core/disclosure_types.py`](../plugins/development-harness/backlog_core/disclosure_types.py).

---

## Related Files

- [`../plugins/development-harness/backlog_core/disclosure_handler.py`](../plugins/development-harness/backlog_core/disclosure_handler.py) — reference implementation: `DisclosureRequestParser`, `BacklogViewDisclosureHandler`, `TokenBoundedExtractor`
- [`../plugins/development-harness/backlog_core/ordinal_mapper.py`](../plugins/development-harness/backlog_core/ordinal_mapper.py) — `OrdinalPathMapper`, `format_map_line`, `OrdinalEntry`
- [`../plugins/development-harness/backlog_core/disclosure_types.py`](../plugins/development-harness/backlog_core/disclosure_types.py) — `MapResponse`, `NavigateResponse`, `BoundedResponse`, `OrdinalNotFoundError`, `DisclosureParamError`
- [`../plugins/development-harness/backlog_core/content_normalizer.py`](../plugins/development-harness/backlog_core/content_normalizer.py) — `ItemContentNormalizer`
