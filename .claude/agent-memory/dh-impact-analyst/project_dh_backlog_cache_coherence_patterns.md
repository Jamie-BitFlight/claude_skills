---
name: project_dh_backlog_cache_coherence_patterns
description: DH backlog_core cache coherence architecture — how view_item, pull_items, sync_items interact with local YAML cache vs GitHub; key functions and risk patterns
metadata:
  type: project
---

## backlog_core cache coherence architecture (observed 2026-05-24, item #2452)

**Key finding**: `view_item` (operations.py:2750) seeds from `parse_backlog()` (local YAML cache) then calls `view_enrich_from_github()` for the raw body only. For YAML items (most items), `result.sections` and `result.sections_index` are populated from the local in-memory `BacklogItem` — never refreshed from GitHub. `backlog_view(summary=True)` returns stale `sections_index` because `_build_compact_manifest` → `_sections_index_from_result` reads these local-YAML-derived fields.

**`parse_backlog()`** is the central cache-read primitive. Called from: `view_item`, `list_items`, `sync_items`, `pull_items`, `close_item`, `find_or_create_issue`, and several others. Any fix to live-read policy changes all callers.

**`view_enrich_from_github`** (operations.py:190) — partial escape hatch; enriches raw body from GitHub when issue_num is present, but NOT structured sections or sections_index. The likely extension point for a Failure 1 fix.

**`pull_items` "keep longer section" merge**: `_pull_item` keeps the longer version of each section. A stale-but-longer local section blocks GitHub-fresh data even after `backlog_pull` is called. This is a secondary reinforcement of the stale cache bug.

**`sync_items`** (operations.py:2964): no `flush_only` parameter. Always runs `sync_create_missing_issues` + `sync_push_groomed_content` — full two-phase sweep. `backlog_sync` MCP tool (server.py:1882) exposes only `dry_run: bool`.

**finally.md** (skills/work-backlog-item/references/workflows/groom/finally.md) — references `backlog_sync(flush_only=true)` which does not exist. Every groom exit triggers a full sweep (~321 issues fetched).

**Fix path split**: (A) implement `flush_only` — changes server.py, operations.py, backend_protocol.py, all 4 backends; (B) update finally.md only — docs change only, but original intent of cheap local flush is lost.

**Zero test coverage** for: cache coherence after groom write, summary=True freshness, flush_only semantics.

**Why:** Identified during impact analysis for backlog item #2452 (stale cache + missing flush_only).
**How to apply:** When analyzing backlog_view/backlog_sync/backlog_pull interactions, start with parse_backlog() as the central dependency node and view_enrich_from_github() as the partial live-data path.
