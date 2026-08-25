---
name: maintenance-creation
description: Fixture target skill exercising the MAINTENANCE.md creation branch. Use when the eval harness needs a skill with no MAINTENANCE.md but a non-obvious cross-cutting invariant buried in runtime prose.
---
# Eval2 Target

## Acquire the lock before writing

Acquire `locks/run.lock` before writing to the run directory. Both the cleanup script and the
archival job also read this same lock file path, and if the path ever changes those two callers
would silently stop coordinating with each other and could corrupt a run directory — this has
never been documented anywhere else, so if you're ever tempted to rename or relocate the lock
file, don't, without updating both callers.
