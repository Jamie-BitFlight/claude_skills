---
name: auto-sync-version-bump-refactor-review
description: Code review findings for auto_sync_manifests.py version-bump refactor (2026-05-29) — key patterns and follow-ups created
metadata:
  type: project
---

Version-bump refactor in `plugins/plugin-creator/scripts/auto_sync_manifests.py` reviewed 2026-05-29.

**Core change:** `resolve_base()` → `_update_from_base_ref()` chain replaces HEAD-only comparison with origin/main → main → HEAD fallback, so concurrent PR branches bump from base instead of working-copy version.

**Logic verdict:** PASS — the arithmetic and routing are correct; `_read_ref_json("HEAD")` delegates to `_read_head_json` intentionally to keep existing monkeypatches live (84 tests pass).

**Key gaps that generated follow-ups:**
- `_read_ref_json` real I/O path (lines 355-368) has zero test coverage — all TestWorkingBehindBase tests monkeypatch it → P1665
- `explicit` param in `resolve_base()` and `ref` param in `_is_ahead_of_ref()` are dead generalizations; `_update_from_base_ref` inlines the comparison instead of calling `_is_ahead_of_ref` → P1666
- File is 1753 lines / 1252 LOC — HIGH file-size policy violation, pre-existing, out-of-scope → P1667

**Why:** Test-authorship independence: all new `working < base` scenario tests share the same mock — they verify routing but not the real git I/O. The 60% coverage / 271-miss number exposes this.
