---
name: local-ownership
description: Fixture target skill exercising the MOVE-LOCAL branch. Use when the eval harness needs a skill with maintenance reasoning scoped to exactly one script.
---
# Eval3 Target

## Regenerate the cache

Run `scripts/rebuild_cache.py`. This script writes its output using a fixed random seed
(`--seed 7`) so its output is byte-for-byte reproducible across runs — changing the seed value
would break the script's own snapshot tests, which compare output to a checked-in fixture.
