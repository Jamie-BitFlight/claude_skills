---
name: rebase
description: "Start a local Git rebase when the user explicitly requests history replay for a named branch or ref, or continue or abort an active local rebase. Use for conflict-aware replay that requires an accounted plan and verified recovery. Do not use for merge-based branch updates, forge merge-method settings, pull-request or merge-request merging, or publishing rewritten history."
---

# Rebase

Replay every intentionally retained commit and change from an explicitly named local branch onto an
immutable target commit. Finish only when ancestry, branch intent, repository checks, clean state,
and recovery information are observable.

The executing agent owns every step. This workflow rewrites local history only. A verified local
rebase authorizes neither force-push nor merge.

Bind `<skill-dir>` to the absolute directory containing this loaded `SKILL.md`, using the exact
injected skill path supplied by the harness. Substitute that absolute path directly in every
bundled-script command.

Choose one route before any mutation and load only its reference:

- To start a named rebase, read [Start a rebase](./references/start-rebase.md) and follow it to a
  terminal.
- To continue or abort, read [Active rebase](./references/active-rebase.md) and follow it to a
  terminal.
