# file_cache_state.py — cache state store mechanics

`plugins/development-harness/backlog_core/file_cache_state.py`

## On-disk reality (as of the cache.yaml→cache.json rename, PR #3358)

`_STATE_FILE = "cache.json"`; `_LEGACY_STATE_FILE = "cache.yaml"`. `_save()` has
written pure JSON (`state.model_dump_json()`) since PR #3292
(`849ceda2c`, 2026-08-29) — the rename just fixed the filename to match. A
legacy `cache.yaml` (real YAML, or JSON still wearing the old extension) is
migrated to `cache.json` inside `transaction()`, under the lock; `load()` stays
read-only and never migrates (doing it there self-deadlocks — see
`_migrate_legacy_state_file`'s docstring). `FileCache._load_state()` also calls
`_CacheStateStore.ensure_migrated()` first, so every read accessor
(`pending_mutations`, `get_content`, reconciliation's `load_records`, ...) sees
migrated state immediately, not only after some unrelated `transaction()`
happens to run. Both files present (e.g. an older plugin copy recreating
`cache.yaml` after `cache.json` already exists) merges all five queue/
dead-letter fields into `cache.json` before superseding the legacy file to
`cache.yaml.superseded` — never deleted, so a crash or a corrupt legacy file
mid-migration is recoverable.

Files reach 2.3 MB single-line JSON. `cache.lock` (flock) sits beside it and its
name is unchanged across versions, so old and new code still mutually exclude.

## Idempotency keys ARE now checked, not just local join keys

`queue_write` computes
`sha256(json.dumps(rebased_write.model_dump(mode="json"), sort_keys=True, separators=(",",":")))`
via the shared `_content_mutation_key` helper; `_queue_work_item` computes
`sha256(f"{key}:{item_payload}")` via `_work_item_mutation_key`. On every load
(not just the salvage path — see `_verify_queue_keys`'s docstring for why a
forged-but-schema-complete entry needs this to run unconditionally), each
`pending`/`pending_work_items` entry's stored key is recomputed from its own
content and compared. A mismatch is **not** treated as harmless: the entry is
moved to `rejected`/`rejected_work_items` (inert, inspectable, never replayed)
rather than left in place or silently dropped.

This closes most of what used to be the real hand-edit hazard: `load_records()`
(`github_work_items.py`) still gives a queued `pending_work_items` mutation
precedence over the on-disk snapshot with no validation of its own, but a
hand-appended entry with a garbage key never reaches that code anymore — it's
dead-lettered at load time, before `reconcile()` ever sees it. `load_records()`
itself is unchanged; the defense moved upstream of it, not into it.

Known limitation, deliberately not built here (see backlog #2287): dead-lettering
is one-way. A version-skew false positive (an older reader dropping a field a
newer writer included, per pydantic's `extra="ignore"`, which changes the
recomputed hash for a legitimate entry) is preserved but never automatically
retried or promoted back to `pending` by a later-version load that could
resolve it correctly.

Schema-invalid entries (fails `model_validate`, not just a key mismatch) are
handled the same way, one level further: `pending`/`pending_work_items`/
`rejected`/`rejected_work_items` are all routed through
`_salvage_queue_list`, which preserves the raw, unvalidated payload in
`corrupt_queue_entries` (a `raw: Any` field — never itself fails validation,
so it's the terminal fallback with nothing further to preserve it from) rather
than dropping the entry. `reconcile()`'s `rejected_mutations` count includes
`corrupt_queue_entries` alongside both rejected buckets, so a dead-lettered
entry is never invisible in sync output.

Latent (tamper-only) bug, still present, unrelated to the above: `acknowledge_replay`
does `remaining = [e for e in state.pending if e.idempotency_key not in acknowledged_keys]`
— duplicate keys mean one successful replay silently drops the other entry.
Unreachable from normal code paths (keys are content-derived, one entry per
reference); worth knowing if it ever surfaces.

## Running the tests

`tests_backlog/` is NOT in root `pyproject.toml` testpaths (only in coverage
`omit`). Root addopts force `--cov`, so a bare `-p no:cov` fails; use:

```bash
uv run pytest plugins/development-harness/tests_backlog/test_file_cache.py -q --no-cov
```

`test_file_cache.py` covers the JSON/YAML dual-read matrix, migration (both
directions, both-files-present merge, cross-thread lock safety), per-entry and
per-collection dead-lettering (schema failure, key mismatch, version skew), and
the corrupt-file typed-error path — check the file directly for current test
names and counts rather than trusting a number here.
