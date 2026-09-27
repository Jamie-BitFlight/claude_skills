---
name: skill-goal-extractor
description: Compatibility router for skill goal recovery and authority assessment. Delegate to Skill Lapidary's establish-validatable-goals capability rather than maintaining a second goal-contract system in Plugin Creator.
---

# Skill Goal Extractor

Goal recovery, provenance, approval status, invariants, non-goals, and validation readiness are owned by Skill Lapidary's `/skill-lapidary:establish-validatable-goals` skill.

## Route

1. If `/skill-lapidary:establish-validatable-goals` is available, activate it against the requested target.
2. Preserve its native assessment and authority semantics. Do not promote recovered goals or manufacture Plugin Creator approval metadata.
3. If unavailable and installation is permitted, install Skill Lapidary for the current harness as its [packaging README](https://github.com/Jamie-BitFlight/skill-lapidary/blob/main/packaging/README.md) documents.

4. Retry by activating `/skill-lapidary:establish-validatable-goals`.
5. If it cannot be loaded or installed, return `BLOCKED`. Do not infer an authoritative goal contract as a fallback.

This wrapper is transitional. New Plugin Creator workflows should route directly to Skill Lapidary.
