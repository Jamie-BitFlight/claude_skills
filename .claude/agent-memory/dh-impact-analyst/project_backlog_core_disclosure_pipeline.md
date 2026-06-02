---
name: project_backlog_core_disclosure_pipeline
description: Disclosure pipeline architecture — ordinal_mapper, disclosure_handler, types, test coverage gaps for backlog_view progressive disclosure
metadata:
  type: project
---

## backlog_core Disclosure Pipeline — Architecture and Risk Patterns

**Key modules** (all in `plugins/development-harness/backlog_core/`):
- `ordinal_mapper.py` — `OrdinalPathMapper.build_map()` emits 2-level ordinals only today (`"N"`, `"N.M"`). Ordinal regex `^(\d+\.)*\d+$` is already in `disclosure_handler.py` parser and accepts arbitrary depth.
- `disclosure_handler.py` — `BacklogViewDisclosureHandler.handle()` dispatches MAP/NAVIGATE/EXTRACT. ADR-5: calls `operations.view_item()` via module reference, not direct import.
- `disclosure_types.py` — exports: `DisclosureMode`, `MapResponse`, `NavigateResponse`, `BoundedContent`, `BoundedResponse`, `DisclosureParamError`, `OrdinalNotFoundError`.
- `content_normalizer.py` — `NormalizedEntry.content: str` is always a flat raw markdown string; can contain `##`/`###` headings and code fences.

**ADRs to remember:**
- ADR-2: All token counting via `ENCODING` singleton from `progressive_markdown.list_navigator` (cl100k_base).
- ADR-5: `BacklogViewDisclosureHandler.handle()` calls `operations.view_item()` via module reference.
- `total_est_tokens` in `MapResponse` sums LEVEL-1 only (architect spec §5.2, #2495 regression guard).

**Reuse target for sub-heading parsing:**
- `progressive_markdown/indexer.py::MarkdownIndexer` — recursive heading-tree builder with code-fence extraction. Factory: `ProgressiveMarkdownNavigator.from_markdown(markdown: str)` in `navigator.py` lines 113–131.

**NOTE**: `backlog_core/tests/` is included in root `pyproject.toml` testpaths (line 403: `"plugins/development-harness/backlog_core/tests"`). DH's own `pyproject.toml` does NOT include it (`testpaths = ["tests", "tests_sam", "tests_backlog"]`), so running pytest from within `plugins/development-harness/` directly misses these tests — use root pyproject.

**Test coverage gaps as of 2026-06-01:**
- No level-3 ordinal assertions in `test_ordinal_mapper.py` (fixture groomed_body_doc lines 128–169 already has `### Concerns`, `### RT-ICA` sub-headings in section [4]).
- TC-H1–H5 in `test_disclosure_handler.py` cover MAP/NAVIGATE/EXTRACT at 2-level only.

**Consumer chain:**
- `server.py` imports `BacklogViewDisclosureHandler`, `DisclosureRequest`, `DisclosureRequestParser` from `disclosure_handler`; `DisclosureMode`, `DisclosureParamError`, `OrdinalNotFoundError` from `disclosure_types`.

**Why:** Needed for #2529 impact analysis (2026-06-01). [[project_dh_backlog_cache_coherence_patterns]]
