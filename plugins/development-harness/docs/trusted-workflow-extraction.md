# Trusted workflow extraction: deterministic frozen-evidence reducer

Use this reducer to create a deterministic staging record from three frozen worker reports.

Run `uv run scripts/reduce_workflow_evidence.py --root REPO --manifest manifest.json --worker w1.json --worker w2.json --worker w3.json --output staged.json` from the development-harness plugin root. The output destination must be fresh: the reducer creates it and rejects an existing path rather than overwriting it.

The manifest contains `version: 1`, `sources: [{path, sha256}]`, and `assignments: {w1: [...], w2: [...], w3: [...]}`. Rules are `fork`, `branch`, `reference`, `dispatch`, `tool`, `artifact`; each must be assigned to exactly two workers. Source paths are relative to `--root`, cannot escape it or traverse symlinks, and must match the recorded SHA-256 digest. Each report contains `worker` and `findings`, with each finding specifying `rule`, `path`, `start`, `end` (UTF-8 byte offsets), `quote`, and `kind`.

A `verified` finding is an exact source-backed tuple reported by two distinct workers assigned to its rule. Findings below that agreement threshold remain in `unverified_items`. Re-running against identical frozen input bytes yields the same serialized output. This corroborates an occurrence at the stated source span; it does not establish semantic meaning. An independent meaning check is required before authoritative use.
