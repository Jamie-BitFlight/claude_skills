---
name: multi-perspective-review
argument-hint: "--diff <git-range> [--issue <N>]"
user-invocable: true
description: "Use when a diff needs four parallel perspective reviewers (Security, Performance, Quality, Accessibility). Creates an ephemeral SAM plan, collects structured verdicts, prints one summary line per perspective, and exits non-zero if any perspective returns REJECT. SKIP is a passing outcome."
---

# Multi-Perspective Review

## Role

Orchestrates four independent perspective reviewers in parallel against a diff. Each reviewer
specialises in a single dimension: Security, Performance, Quality, or Accessibility. The skill
creates an ephemeral SAM plan, dispatches four `dh:task-worker` teammates via `TeamCreate`,
collects structured verdict blocks via `SendMessage`, applies the gate logic, and prints one
canonical summary line per perspective.

This skill does NOT replace language-scoped code review (`dh:forensic-review`). It runs
alongside it as an orthogonal quality signal. It is an upstream dependency of #1430
(confidence-gate consolidation), which will replace the stub gate logic in Step 6 without
changing the caller interface.

## Argument Parsing

| Argument | Type | Description |
|----------|------|-------------|
| `--diff <git-range>` | **required** | Git range passed to `git diff --name-only`. Examples: `HEAD~1..HEAD`, `main..feature-branch`, `abc123..def456`. |
| `--issue <N>` | optional | GitHub issue number used for artifact registration and ephemeral plan linkage. |
| `--slug <str>` | optional | Explicit slug override. When omitted, derived from `--issue` or current git branch. |

Parse arguments from the invocation arguments string. Abort with usage message if `--diff` is
absent.

---

## Step 1: Resolve Changed Files

Run:

```bash
git diff --name-only <git-range>
```

Split stdout by newline. Trim empty lines. This is the `changed_files` list.

**Abort condition:** If `changed_files` is empty, print the following and stop:

```text
ERROR: No changed files found for diff range <git-range>. Nothing to review.
```

Do not create a team or a plan when `changed_files` is empty.

---

## Step 2: Derive Review Slug

Derive `review_slug` exactly once using the first matching rule:

1. `--slug` argument is provided → use its value directly
2. `--issue <N>` argument is provided → `review-{N}` (e.g., `review-2181`)
3. Neither provided → read current git branch name via `git rev-parse --abbrev-ref HEAD` and
   use `review-{branch-name}` (sanitize branch name: replace `/` with `-`)

Use `review_slug` unchanged in plan operations. Use `multi-{review_slug}` as the team name.

---

## Step 3: Create Ephemeral Review Plan (check-or-create)

**CRITICAL: check-or-create semantics are mandatory.** List matching plans before creating one so
repeated runs reuse the existing address.

### 3a: Check for Existing Plan

Call:

```python
mcp__plugin_dh_sam__sam_plan(config={"action": "list", "search": "{review_slug}"})
```

Inspect the returned `items` array. If any item has `feature` equal to `{review_slug}`:

- Store its non-empty `plan_ref` as `{PA}` (e.g., `#2181,P8a3f1b29`)
- Skip step 3b — do not create a new plan

If no matching plan is found, proceed to step 3b.

### 3b: Create the Ephemeral Plan

Build the changed-files body block:

```text
Changed files:
{each file on its own line}
```

Create all four tasks in one typed MCP call. Replace `{changed_files_block}` with the literal
newline-separated changed-files block. Omit `issue` when `--issue` was not provided.

```python
mcp__plugin_dh_sam__sam_plan(
    config={
        "action": "create",
        "slug": "{review_slug}",
        "goal": "Multi-perspective review for {review_slug}",
        "issue": <issue_number_or_omit_if_absent>,
        "tasks": [
            {
                "id": "T1",
                "title": "Security Review",
                "agent": "dh:reviewer-security",
                "priority": 1,
                "complexity": "medium",
                "dependencies": [],
                "body": "Review every changed file through the security lens.\n"
                "Return structured verdict per verdict-schema.md.\n\n{changed_files_block}",
            },
            {
                "id": "T2",
                "title": "Performance Review",
                "agent": "dh:reviewer-performance",
                "priority": 1,
                "complexity": "medium",
                "dependencies": [],
                "body": "Review every changed file through the performance lens.\n"
                "Return structured verdict per verdict-schema.md.\n\n{changed_files_block}",
            },
            {
                "id": "T3",
                "title": "Quality Review",
                "agent": "dh:reviewer-quality",
                "priority": 1,
                "complexity": "medium",
                "dependencies": [],
                "body": "Review every changed file through the quality lens.\n"
                "Return structured verdict per verdict-schema.md.\n\n{changed_files_block}",
            },
            {
                "id": "T4",
                "title": "Accessibility Review",
                "agent": "dh:reviewer-accessibility",
                "priority": 1,
                "complexity": "low",
                "dependencies": [],
                "body": "Apply the SKIP rule first. Otherwise review ARIA attributes, color-only "
                "signals, and keyboard parity. Return structured verdict per verdict-schema.md."
                "\n\n{changed_files_block}",
            },
        ],
    }
)
```

Store the returned `plan_ref` as `{PA}`. Completion criterion: `plan_ref` is non-empty and the
result has `task_count=4`.

---

## Step 4: TeamCreate and Dispatch Four Workers in Parallel

Create the team:

```text
TeamCreate(team_name="multi-{review_slug}")
```

Dispatch all four workers simultaneously. Do NOT wait between spawns — all four are independent
and must run in parallel. Each worker receives a minimal prompt that invokes `start-task`.
`start-task` owns claim, active-task registration, and execution. The `agent:` field in each
SAM task tells `dh:task-worker` which specialist profile to load via `profile_load` internally.

**Dispatch `dh:task-worker` exclusively; specialist behavior is loaded through each task's profile.**

```text
Agent(
  team_name="multi-{review_slug}",
  name="security-worker",
  subagent_type="dh:task-worker",
  prompt="Before starting work, load these skills: dh:subagent-contract\n\nYou are working on security review. Your task: {PA}/T1.\n\nSkill(skill=\"start-task\", args=\"{PA} --task T1\")"
)

Agent(
  team_name="multi-{review_slug}",
  name="performance-worker",
  subagent_type="dh:task-worker",
  prompt="Before starting work, load these skills: dh:subagent-contract\n\nYou are working on performance review. Your task: {PA}/T2.\n\nSkill(skill=\"start-task\", args=\"{PA} --task T2\")"
)

Agent(
  team_name="multi-{review_slug}",
  name="quality-worker",
  subagent_type="dh:task-worker",
  prompt="Before starting work, load these skills: dh:subagent-contract\n\nYou are working on quality review. Your task: {PA}/T3.\n\nSkill(skill=\"start-task\", args=\"{PA} --task T3\")"
)

Agent(
  team_name="multi-{review_slug}",
  name="accessibility-worker",
  subagent_type="dh:task-worker",
  prompt="Before starting work, load these skills: dh:subagent-contract\n\nYou are working on accessibility review. Your task: {PA}/T4.\n\nSkill(skill=\"start-task\", args=\"{PA} --task T4\")"
)
```

---

## Step 5: Collect Verdicts

Wait for four `SendMessage` arrivals from teammates. Each reviewer agent sends:

```text
SendMessage(
  to="team-lead",
  summary="{perspective}: {verdict} — {N} findings ({blocker_count} blockers)",
  message="<raw JSON verdict block per verdict-schema.md §2.1>"
)
```

For each received message, parse the `message` field as JSON:

```python
verdict_block = json.loads(msg.message)
```

The verdict block schema is defined in
[./references/verdict-schema.md](./references/verdict-schema.md) §2.1. Do not duplicate the
schema here.

**Missing verdict handling:** If any perspective does not send a `SendMessage` after all workers
complete, treat it as a `FAIL` condition:

```text
Perspective {X} did not return a verdict
```

Collect all four verdict blocks before proceeding to Step 6.

---

## Step 6: Apply Gate and Print Summary

### Gate Logic

The gate logic is the pre-#1430 stub. The full gate logic including the all-SKIP edge case is
defined in [./references/verdict-schema.md](./references/verdict-schema.md) §2.4.

Apply gate in this order:

1. **Check for missing verdicts.** If any perspective did not return a verdict, FAIL immediately
   with message `"Perspective {X} did not return a verdict"`.

2. **Check for REJECT.** If any verdict has `verdict == "REJECT"`, the gate FAILS. Collect all
   REJECT verdicts and their blocking findings for the summary.

3. **Check for all-SKIP edge case.** If all four verdicts are `SKIP`, the gate PASSES but the
   summary MUST include this exact warning line:

   ```text
   NOTE: No perspectives reviewed — all skipped
   ```

4. **All other combinations** (any APPROVE, remaining SKIP) → gate PASSES.

**#1430 compatibility contract:** The gate interface is stable:
`gate(verdicts: list[VerdictBlock]) -> GateResult` where `GateResult = {passed: bool,
summary_line: str, blocking_findings: list[Finding]}`. Issue #1430 replaces the gate function
body only — callers (this step) do not change.

### Summary Line Format

Print one canonical summary line. Format per
[./references/verdict-schema.md](./references/verdict-schema.md) §2.2:

```text
Security: {token} | Performance: {token} | Quality: {token} | Accessibility: {token}
```

Summary token mapping:

| Verdict | Findings | Summary token |
|---------|----------|---------------|
| `APPROVE` | 0 findings | `APPROVE (0 findings)` |
| `APPROVE` | N minor/info findings | `APPROVE ({N} minor)` |
| `REJECT` | 1 BLOCKER finding | `REJECT (1 finding)` |
| `REJECT` | N BLOCKER findings | `REJECT ({N} findings)` |
| `SKIP` | — | `SKIP ({skip_reason})` |

Example output:

```text
Security: APPROVE (0 findings) | Performance: REJECT (1 finding) | Quality: APPROVE (2 minor) | Accessibility: SKIP (no UI changes)
```

### Exit and Cleanup

1. If gate FAILED (any REJECT): print the summary line, then TeamDelete, then exit non-zero.
2. If gate PASSED (all-SKIP warning applies): print the summary line, then print the warning
   line `NOTE: No perspectives reviewed — all skipped`, then TeamDelete, then exit 0.
3. If gate PASSED (normal): print the summary line, then TeamDelete, then exit 0.

TeamDelete cleans up the team after all workers are done:

```text
TeamDelete(team_name="multi-{review_slug}")
```

---

## Dispatch Flow (Reference)

```mermaid
flowchart TD
    Start([dh:multi-perspective-review invoked]) --> Parse[Parse --diff and --issue args]
    Parse --> Files["git diff --name-only range → changed_files list"]
    Files --> Empty{changed_files empty?}
    Empty -->|Yes| Abort[ABORT — no changed files to review]
    Empty -->|No| Slug[Derive review_slug once]
    Slug --> CheckPlan["sam_plan(config: list + search)"]
    CheckPlan --> PlanExists{Plan with slug exists?}
    PlanExists -->|Yes — reuse| PlanAddr["Store existing plan address as {PA}"]
    PlanExists -->|No — create| CreatePlan["sam_plan(config: create + T1..T4)"]
    CreatePlan --> PlanAddr
    PlanAddr --> Team["TeamCreate(team_name='multi-{review_slug}')"]
    Team --> Parallel[Dispatch 4 workers in parallel — no wait between spawns]
    Parallel --> W1["Agent(name='security-worker', subagent_type='dh:task-worker')"]
    Parallel --> W2["Agent(name='performance-worker', subagent_type='dh:task-worker')"]
    Parallel --> W3["Agent(name='quality-worker', subagent_type='dh:task-worker')"]
    Parallel --> W4["Agent(name='accessibility-worker', subagent_type='dh:task-worker')"]
    W1 --> Collect[Wait for 4 SendMessage arrivals]
    W2 --> Collect
    W3 --> Collect
    W4 --> Collect
    Collect --> Gate{Any REJECT?}
    Gate -->|Missing verdict| Fail[FAIL — Perspective X did not return a verdict]
    Gate -->|Any REJECT| Fail2[Print summary. TeamDelete. Exit non-zero.]
    Gate -->|All SKIP| Warn[Print summary. Print all-SKIP warning. TeamDelete. Exit 0.]
    Gate -->|All APPROVE or APPROVE+SKIP| Pass[Print summary. TeamDelete. Exit 0.]
```

---

## Ephemeral Plan Task Structure

The ephemeral plan always has exactly four tasks:

| Task | Perspective | Agent field | dependencies |
|------|-------------|-------------|--------------|
| T1 | Security | `dh:reviewer-security` | `[]` |
| T2 | Performance | `dh:reviewer-performance` | `[]` |
| T3 | Quality | `dh:reviewer-quality` | `[]` |
| T4 | Accessibility | `dh:reviewer-accessibility` | `[]` |

All four tasks have `dependencies: []` — they are independent and run in parallel. The
`agent:` field is read internally by `dh:task-worker` via
`mcp__plugin_dh_sam__sam_task(plan="{PA}", task="T{N}", config={"action": "read"})` and passed
to `profile_load` to load the specialist reviewer behavior. The orchestrator always passes only
the task reference `{PA}/T{N}` to the worker prompt.

---

## Behavioral Rules

- **SKIP is a passing outcome.** A perspective that SKIPs is not a blocker.
- **All four verdicts must arrive before the gate runs.** Do not apply the gate on partial results.
- **Check-or-create prevents plan accumulation.** Always list by search before creating.
- **Dispatch uses `dh:task-worker` exclusively.** Specialist behavior is selected through the task profile.
- **Do not embed the verdict schema or UI pattern list.** Reference
  [./references/verdict-schema.md](./references/verdict-schema.md) for all schema definitions.
- **Each ephemeral task body must embed the newline-separated changed-files list.** Workers read
  their task body to obtain the scan target; they do not receive it via the prompt.
- **All-SKIP warning is mandatory** when all four perspectives return SKIP.
