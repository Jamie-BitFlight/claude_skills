# Close / Resolve — Example Sessions

## Resolving a completed item (by title)

```text
> /work-backlog-item resolve validator UX

Found: "plugin-validator UX and coverage gaps" (P1)
Plan: plan/tasks-2-validator-ux-coverage.md
Checklist: 12/12 tasks complete

Spawning acceptance criteria verification agent...

Verdict: PASS
Evidence: Sub-issues 1-4 implemented in plugins/plugin-creator/scripts/auto_sync_manifests.py
          commit 4a2f1b3 — "fix(validator): report unique files, add hook validation"

Summarize what was done:
> Implemented all 4 sub-issues: unique file reporting, hook validation, coverage gaps filled.

Backlog item "plugin-validator UX and coverage gaps" resolved.
- Summary: Implemented all 4 sub-issues: unique file reporting, hook validation, coverage gaps filled.
- Checklist: 12/12 tasks complete
- Acceptance criteria: PASS
- GitHub Issue #131 closed with evidence trail
```

## Resolving a completed item (by issue number)

```text
> /work-backlog-item resolve #131

Fetching GitHub Issue #131...
  Title: plugin-validator UX and coverage gaps
  State: open

Found backlog item: "plugin-validator UX and coverage gaps" (P1)
Plan: plan/tasks-2-validator-ux-coverage.md
Checklist: 12/12 tasks complete

Spawning acceptance criteria verification agent...

Verdict: PASS
Evidence: commit 4a2f1b3 — "fix(validator): report unique files, add hook validation"

Summarize what was done:
> All validator sub-issues implemented and tested.

Backlog item "plugin-validator UX and coverage gaps" resolved.
- Summary: All validator sub-issues implemented and tested.
- GitHub Issue #131 closed with evidence trail
```

## Closing (dismissing) an item

```text
> /work-backlog-item close commitlint verify last flag

Found: "commitlint: Verify --last flag and exit codes against primary sources" (P1)
Why is this item being dismissed?
> out_of_scope
Any additional comment?
> REFUTED by fact-check: --last flag verified against commitlint source cli.ts. No fix needed.

Backlog item closed.
  Closed: 2026-02-21
  Reason: out_of_scope
  Comment: REFUTED by fact-check: --last flag verified against commitlint
           source cli.ts and official docs. No fix needed.
```
