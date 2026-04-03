# Example Sessions

## Issue-first planning (`#N`)

```text
> /work-backlog-item #131

Loading GitHub Issue #131...
  Title:     plugin-validator: UX and coverage gaps
  Labels:    priority:p1, status:needs-grooming
  Milestone: v1.1 — Quality Gates
  State:     open

Matched per-item file for additional context: ✓
No groomed content in item file. Running groom-backlog-item first...

[groomed content written to item file]

RT-ICA: APPROVED — all conditions available.
Setting status:in-progress on issue #131...
  ✓ status:needs-grooming → status:in-progress

Composing feature request...
Invoking /add-new-feature...

[SAM phases run]

Updated per-item file with Plan: plan/tasks-2-validator-ux-coverage.md

Next steps:
- To execute:      /implement-feature validator-ux-coverage
- To close when done: /work-backlog-item close plugin-validator UX and coverage gaps
```

## Planning (with title substring)

```text
> /work-backlog-item Error Recovery

Found: "SAM: Error Recovery / Rollback Procedures" (P1)
No groomed content in item file. Running groom-backlog-item first...

[groomed content written to item file]

RT-ICA: APPROVED — all conditions available.
Composing feature request...
Invoking /add-new-feature...

[SAM phases run]

Updated per-item file with Plan: plan/tasks-2-error-recovery.md

Next steps:
- To execute:      /implement-feature error-recovery
- To check status: /implementation-manager status . error-recovery
- To close when done: /work-backlog-item close error-recovery
```

## Resolving a completed item (by title)

```text
> /work-backlog-item resolve validator UX

Found: "plugin-validator UX and coverage gaps" (P1)
Plan: plan/tasks-2-validator-ux-coverage.md
Checklist: 12/12 tasks complete

Spawning acceptance criteria verification agent...

Verdict: PASS
Evidence: Sub-issues 1-4 implemented in plugins/plugin-creator/scripts/plugin_validator.py
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

Found per-item file match: "plugin-validator UX and coverage gaps" (P1)
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

## Step 3.1 Staleness Detection Examples

### COSMETIC_ONLY — zero functional commits, cached content used

```text
> /work-backlog-item Improve error messages in validator

Found: "Improve error messages in validator" (P1)
  Groomed: 2026-03-15
  Impact Radius: plugins/plugin-creator/scripts/plugin_validator.py,
                 plugins/plugin-creator/skills/lint/SKILL.md

[STALENESS] Phase 1: checking git log since 2026-03-15 for impact radius files...
  Found 2 commits total, 0 after functional filter (docs/chore only).
[STALENESS] Phase 1: 0 functional commits since 2026-03-15 — using cached groom content.

RT-ICA: APPROVED — all conditions available.
Composing feature request...
Invoking /add-new-feature...

[SAM phases run]
```

### FUNCTIONAL_DRIFT — re-groom triggered by codebase changes

```text
> /work-backlog-item --auto

[AUTO] No title — auto-selected: "Add retry logic to API client"
  Groomed: 2026-03-10
  Impact Radius: src/api/client.py, src/api/retry.py, tests/test_client.py

[STALENESS] Phase 1: checking git log since 2026-03-10 for impact radius files...
  Found 5 commits total, 3 after functional filter.
  Qualifying: fix(api): handle timeout in client.py, refactor(api): extract retry module,
              feat(api): add circuit breaker to retry.py

[STALENESS] Phase 2: spawning drift-assessment agent...
  Agent input: item description + acceptance criteria + git diff 3a1b2c..HEAD -- src/api/client.py src/api/retry.py tests/test_client.py
  Agent returned: FUNCTIONAL_DRIFT

[AUTO] STALENESS: FUNCTIONAL_DRIFT — retry module extracted to separate file; circuit breaker added changes approach

Writing staleness context via backlog_groom...
  backlog_groom(selector="Add retry logic to API client",
    section="staleness context",
    content="Staleness detected 2026-03-28: functional commits since 2026-03-10...")
Invoking groom-backlog-item to re-groom with updated context...
  Skill(skill: "groom-backlog-item", args: "Add retry logic to API client")

[re-groom completes, fresh sections retrieved via backlog_view]

RT-ICA: re-running (updated_at > RT-ICA date)...
RT-ICA: APPROVED — all conditions available.
Composing feature request...
Invoking /add-new-feature...

[SAM phases run]
```

### SUPERSEDED — work already done, item closed

```text
> /work-backlog-item --auto

[AUTO] No title — auto-selected: "Extract config parsing into dedicated module"
  Groomed: 2026-03-05
  Impact Radius: src/config.py, src/main.py

[STALENESS] Phase 1: checking git log since 2026-03-05 for impact radius files...
  Found 4 commits total, 2 after functional filter.
  Qualifying: refactor(config): extract ConfigParser class,
              feat(config): add config module with YAML support

[STALENESS] Phase 2: spawning drift-assessment agent...
  Agent input: item description + acceptance criteria + git diff 7f8e9d..HEAD -- src/config.py src/main.py
  Agent returned: SUPERSEDED

[AUTO] STALENESS: SUPERSEDED — refactor(config) commits 7f8e9d, a1b2c3 implement the requested extraction

backlog_close(selector="Extract config parsing into dedicated module",
  reason="superseded",
  comment="Goal already implemented by commits since groom date: 7f8e9d, a1b2c3")

Backlog item closed (superseded). Workflow stopped — no planning needed.
```

## GitHub Issue creation flow and setup-github examples

See [github-integration.md](./github-integration.md) for the GitHub Issue creation flow and setup-github session examples.
