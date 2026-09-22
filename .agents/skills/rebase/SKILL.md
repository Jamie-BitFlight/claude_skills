---
name: rebase
description: "Start a local Git rebase when the user explicitly requests history replay for a named branch or ref, or continue or abort an active local rebase. Use for conflict-aware replay that requires an accounted plan and verified recovery. Do not use for merge-based branch updates, forge merge-method settings, pull-request or merge-request merging, or publishing rewritten history."
---

# Rebase

Rewrite local history only: no force-push, remote backup, merge, forge action, or publication.

Bind `<skill-dir>` to this loaded `SKILL.md`'s absolute directory.

Before mutation, require a named local ref, immutable target OID, authorized clean worktree, typed
plan, verified recovery ref, and validation hash. Require explicit approval for discard, topology
flattening, semantic change, publication impact, or ambiguous reconstruction. End with exactly one
canonical terminal; local success is `REBASE_COMPLETE_VERIFIED` and `not published`.

Before any Git command, choose one route and load only its reference:

- Start: read [start a rebase](./references/start-rebase.md).
- Continue or abort: read [active rebase](./references/active-rebase.md).

Tutorial, walkthrough, audit only: read [step-by-step](./references/step-by-step.md) and its
example; routine routes read neither.
