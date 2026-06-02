---
name: project-auto-sync-manifests
description: Seam contracts and implementation patterns for auto_sync_manifests.py base-ref refactor
metadata:
  type: project
---

# auto_sync_manifests.py — Base-Ref Refactor Patterns

**Why:** Concurrent PR branches both starting from the same base version would collide on the same bumped version. Fix: resolve base ref (origin/main → main → None/HEAD-fallback) and bump from base, not from working copy.

## Key Seam Contracts (test-binding)

1. `_read_head_json` MUST remain the real HEAD reader. `_read_ref_json` delegates TO it when `ref == "HEAD"`. Direction is inverted from the naive spec reading — tests mock `_read_head_json` by name, so the HEAD path must flow through it.

2. `resolve_base` uses bare ref strings as argv elements — NOT `ref^{commit}`. Tests assert `"origin/main" in cmd` (exact list membership). Adding `^{commit}` suffix breaks the assertion.

3. `bump_version` takes a raw version string. Use `_extract_str_version` (not `_parse_version_tuple`) to get the base version for bumping. `_parse_version_tuple` returns a tuple for comparison only.

## New Functions Added (2026-05-29)

- `resolve_base(explicit=None) -> str | None` — ref resolution: origin/main → main → None
- `_read_ref_json(ref, filepath) -> object | None` — reads JSON at any ref; delegates to `_read_head_json` for "HEAD"
- `_is_ahead_of_ref(filepath, version_key_path, ref) -> bool` — parameterised version comparison
- `_version_already_bumped(filepath, version_key_path)` — alias calling `_is_ahead_of_ref(..., "HEAD")`
- `_determine_bump_type(changes) -> Literal[...]` — DRY bump type from change lists
- `_write_plugin_version(path, data, from_version, bump_type, current_version)` — write helper
- `_extract_str_version(json_data, key) -> str | None` — extract top-level string version field
- `_update_from_base_ref(...)  -> tuple | None` — base-ref path, returns None when plugin absent at base
- `_update_from_head(...)` — HEAD-fallback path (pre-refactor behaviour)

## File Location

`plugins/plugin-creator/scripts/auto_sync_manifests.py` (stdlib-only, ~1753 lines)

**Why:** Large pre-existing script; 500-line policy pre-dates this file.
