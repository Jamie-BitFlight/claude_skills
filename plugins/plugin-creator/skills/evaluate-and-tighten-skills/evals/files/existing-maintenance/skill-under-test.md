---
name: existing-maintenance
description: Fixture target skill exercising the existing-MAINTENANCE.md branch. Use when the eval harness needs a skill that already has a MAINTENANCE.md file.
---
# Eval1 Target

## Run the stamp script

Run `scripts/gen_run_stamp.py` to obtain a run address. The run-stamp is always emitted as a
fixed-length hex string, a detail this skill has relied on since the run-stamp format was
standardized (see MAINTENANCE.md for why other components depend on this).

## Configure retries

Set `retries: 3` in config.yaml if not already present. This exact requirement is also recorded
in MAINTENANCE.md's Invariants section.
