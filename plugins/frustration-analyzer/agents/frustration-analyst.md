---
name: frustration-analyst
description: Use when asked to run RTFP or find a rage moment. Orchestrates Claude or Codex session analysis and renders the strongest instruction-following failure as a rage receipt PNG.
model: opus
skills:
  - rtfp
---

Load and follow `rtfp`. On Claude, use `frustration-analyzer:batch-detector` for detection and `frustration-analyzer:context-reconstructor` for reconstruction; the skill supplies the portable behavior for other runtimes.

## Completion

- Every non-truncated selected session is fully analyzed; a direct path remains one selected session.
- Global flags retain their source file and raw line so reconstruction reads the winning transcript.
- The result is either a rendered no-rage card or a PNG with the 3-field artifact: `task_summary`, `assistant_excerpt`, and `user_reply`.
- A session set remains limited by provider, modification-time window, and limit.
