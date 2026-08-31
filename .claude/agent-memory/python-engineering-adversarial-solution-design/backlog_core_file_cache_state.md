# file_cache_state.py — cache state store mechanics

`plugins/development-harness/backlog_core/file_cache_state.py`

## On-disk reality (verified 2026-08-31 against `~/.dh/projects/*/github-cache/`)

`_STATE_FILE = "cache.yaml"` but `_save()` writes `state.model_dump_json()` since
PR #3292 (`849ceda2c`, 2026-08-29, "replace ruamel YAML codec with JSON in cache
state store"). Live user dirs on this machine are a **mix**: some `cache.yaml`
files start `{"records":[...` (post-#3292 JSON), others start `checkpoints: []\n`
(real ruamel-emitted YAML, last saved before #3292 or by an older installed
plugin copy). The YAML fallback in `load()` is **live, not dead legacy** — any
rename/migration must carry it.

Files reach 2.3 MB single-line JSON. `cache.lock` (flock) sits beside it and its
name is unchanged across versions, so old and new code still mutually exclude.

## Idempotency keys are LOCAL join keys, not remote dedup tokens

Never sent to GitHub. `queue_write` computes
`sha256(json.dumps(rebased_write.model_dump(mode="json"), sort_keys=True, separators=(",",":")))`;
`_queue_work_item` computes `sha256(f"{key}:{item_payload}")`. Both are
re-derivable purely from the stored entry. Consumed only within one in-process
replay pass (`acknowledge_replay`, `reject_pending`, `_acknowledge_work_items`)
to match acknowledgements back to queue entries. A garbage key is
self-consistent and harmless.

Real hazard from a hand-edit is NOT the key — it is
`github_work_items.py:557-564` `load_records()`, which gives a queued
`pending_work_items` mutation **precedence over the on-disk snapshot**. A
hand-appended entry becomes the winning local view and is pushed to GitHub as a
patch on the next `reconcile()`.

Latent (tamper-only) bug: `acknowledge_replay` does
`remaining = [e for e in state.pending if e.idempotency_key not in acknowledged_keys]`
— duplicate keys mean one successful replay silently drops the other entry.
Unreachable from code paths (keys are content-derived, one entry per reference).

## Robustness gap

`load()` catches only `pydantic.ValidationError` before falling back to
`YAML(typ="safe")`. A truncated/corrupt file raises an uncaught
`ruamel.yaml.YAMLError` out of every cache read.

## Running the tests

`tests_backlog/` is NOT in root `pyproject.toml` testpaths (only in coverage
`omit`). Root addopts force `--cov`, so a bare `-p no:cov` fails; use:

```bash
uv run pytest plugins/development-harness/tests_backlog/test_file_cache.py -q --no-cov
```

25 tests, ~7s. `test_file_cache.py:434-554` already covers the JSON/YAML dual-read
matrix (legacy YAML read, new JSON read, JSON-is-valid-YAML forward compat,
save-emits-JSON, missing file, corrupt file raises).
