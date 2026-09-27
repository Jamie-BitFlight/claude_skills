---
name: evaluate-and-tighten-skills
description: Compatibility router for semantic skill tightening. Delegate goal recovery, authority, semantic conservation, evaluation contracts, and instruction optimization to Skill Lapidary rather than duplicating that system in Plugin Creator.
---

# Evaluate and Tighten Skills

Skill Lapidary owns semantic skill refinement. Plugin Creator does not implement a second goal-authority, pruning, conservation, or evaluation-contract system.

## Route

1. Check whether the `/skill-lapidary:skill-lapidary` skill is available in the current harness.
2. If available, activate it against the requested skill/directory and preserve its native contract, evidence, and result. Do not translate its goal authority into a Plugin Creator `SKILL-GOALS.md` convention or substitute Plugin Creator heuristics.
3. If unavailable and installation is permitted, install Skill Lapidary for the current harness as its [packaging README](https://github.com/Jamie-BitFlight/skill-lapidary/blob/main/packaging/README.md) documents.

4. After installation, activate `/skill-lapidary:skill-lapidary` and restart the requested refinement from that skill's entrypoint.
5. If Skill Lapidary cannot be loaded or installed, return `BLOCKED` for semantic tightening. Do not fall back to locally inferred goals or recreate its authority/refinement logic.

## Boundary

This compatibility skill exists so older Plugin Creator routes fail safely and point at the owning capability. It may be removed once all callers route directly to Skill Lapidary.

Plugin Creator may still perform work that does not depend on semantic refinement, such as packaging, schema validation, deterministic linting, or prose optimization after a Lapidary result establishes the surviving content.
