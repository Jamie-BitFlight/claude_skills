# Trusted workflow extraction: deterministic frozen-evidence reducer

This is the first executable producer seam for [#3223](https://github.com/Jamie-BitFlight/claude_skills/issues/3223), not a completed refresh pipeline.

Run `uv run scripts/reduce_workflow_evidence.py --root REPO --manifest manifest.json --worker w1.json --worker w2.json --worker w3.json --output staged.json` from the development-harness plugin root.

The manifest contains `version: 1`, `sources: [{path, sha256}]`, and `assignments: {w1: [...], w2: [...], w3: [...]}`. Rules are `fork`, `branch`, `reference`, `dispatch`, `tool`, `artifact`; each must be assigned to exactly two workers. Each report contains `worker` and `findings`, with each finding specifying `rule`, `path`, `start`, `end` (UTF-8 byte offsets), `quote`, and `kind`.

A finding is corroborated only when two distinct assigned workers produce exactly the same source-backed tuple. Uncorroborated claims remain in `unverified_items`; no fuzzy quote matching or model-mediated promotion occurs. Re-running against identical frozen input bytes yields the same serialized output.

**Not implemented here:** live worker runtime admission, dispatch, immutable capture, independent semantic-equivalence checks between live ensembles, typed layer assembly, atomic publication, and graph freshness checks. Do not use this output directly as an authoritative workflow layer. A6-F remains the sole publisher. The previous extractor's Sonnet reducer and the plugin-creator location-only reducer are not substitutes for these gates.
