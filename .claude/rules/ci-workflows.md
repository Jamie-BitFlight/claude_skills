---
paths:
- .github/workflows/**/*.yml
---

# GitHub Actions CI Workflow Modification Protocol

Follow this phase-gate checklist when creating/modifying/debugging GitHub Actions workflows. Each phase gates the next.

## Phase 1: Research

Before writing/modifying workflow YAML:

1. Read existing workflow file(s) in `.github/workflows/` to understand current state
2. Identify specific problem/requirement (broken, missing, needs change)
3. Research best practices for pattern needed (quality gates, caching, matrix builds)
4. Search established patterns in mature projects (CPython, Rust, TypeScript)
5. Document findings: patterns, trade-offs, scenario fit

**Gate**: State what pattern to use and why, citing at least one external reference.

## Phase 2: Plan

Write concrete plan before changes:

1. List every file to be modified/created
2. For each change, describe what will change and why
3. Identify interactions with branch protection, required status checks, quality gate job
4. Identify pre-existing failures to account for (do not silently mask)
5. State acceptance criteria: what does "done" look like? How to verify?

**Gate**: Plan written and covers all affected files and interactions.

## Phase 3: Review Plan

Before executing, review plan:

1. Does each change align with researched best practice?
2. Side effects not accounted for? (e.g., renaming job breaks branch protection required checks)
3. Does plan honestly represent failures? No masking exit codes, no `|| true` on checks that should report real status
4. Is plan minimal? Avoids unnecessary changes beyond stated requirement?

**Gate**: Plan verified against research findings, no gaps found.

## Phase 4: Execute

Implement plan:

1. Make changes to workflow YAML files
2. Validate workflow structure: `uv run prek run --files .github/workflows/<file>` (runs `actionlint` for schema validation and `check-yaml` for parsability)
3. Run `uv run prek run --files <file>` for non-workflow files if applicable
4. Commit with descriptive message explaining what changed and why

**Gate**: Changes committed and pass local validation.

## Phase 5: Verify

After execution, verify:

1. Re-read modified workflow file(s) and confirm match plan
2. Trace quality gate logic: which jobs required? Which advisory? Does gate correctly aggregate?
3. Confirm no exit codes swallowed (`|| true`, `|| echo`, bare `continue-on-error` without explanation)
4. If pre-existing failures exist, confirm handled via `alls-green` allowed-failures pattern (not masked)
5. Push and check workflow run if possible

**Gate**: State exactly what will pass, what will fail, what PR status will show — with no ambiguity.

## Quality Gate Pattern (Required)

Repository uses `alls-green` quality gate pattern (following CPython established practice).

**How it works:**

- Individual jobs run without `continue-on-error`, report real pass/fail status
- Quality gate job is ONLY required status check in branch protection
- Jobs with known pre-existing failures listed in `allowed-failures`
- Gate passes if all non-allowed jobs succeed and allowed jobs either succeed or fail

**Implementation:** Uses `re-actors/alls-green` action.

```yaml
quality-gate:
  name: Quality Gate
  if: always()
  needs: [lint, test, type-check, validate-plugins]
  runs-on: ubuntu-latest
  steps:
    - uses: re-actors/alls-green@v1.2.2
      with:
        allowed-failures: validate-plugins
        jobs: ${{ toJSON(needs) }}
```

**Promoting advisory check to blocking**: Remove from `allowed-failures`. One-line change.

## CI Step Review Decision

```mermaid
flowchart TD
    Start([Review CI step]) --> Q1{Does step use || true or || echo?}
    Q1 -->|Yes| Reject1[Remove — swallows exit code, masks real failure]
    Q1 -->|No| Q2{Does job have continue-on-error: true?}
    Q2 -->|Yes| Q3{Is this a quality check job?}
    Q3 -->|Yes| Reject2[Remove — needs.result reports success, gate blind to failure]
    Q3 -->|No — post-processing only: metrics, cache, coverage| Accept[Acceptable]
    Q2 -->|No| Q4{Is advisory job listed in gate needs?}
    Q4 -->|Yes| OK[Correct — gate has visibility]
    Q4 -->|No| Reject3[Add to needs — gate cannot wait for invisible jobs]
```

SOURCE: CPython `build.yml` quality gate pattern, GitHub Actions docs on `continue-on-error` behavior and branch protection interaction (2026-02-14)
