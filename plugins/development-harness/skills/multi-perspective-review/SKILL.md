---
name: multi-perspective-review
argument-hint: "--diff <git-range> [--issue <N>]"
user-invocable: true
description: "Use when a diff needs four parallel perspective reviewers (Security, Performance, Quality, Accessibility). Creates an ephemeral SAM plan, collects structured verdicts, synthesizes them into one deduplicated cross-referenced punch list, prints one summary line per perspective, and exits non-zero if any perspective returns REJECT. SKIP is a passing outcome."
---

# Multi-Perspective Review

## Role

Orchestrates four independent perspective reviewers in parallel against a diff. Each reviewer
specialises in a single dimension: Security, Performance, Quality, or Accessibility. The skill
creates an ephemeral SAM plan, dispatches four `dh:task-worker` teammates via `TeamCreate`,
dispatches a fifth worker that reads the four verdict blocks back and synthesizes them into one
deduplicated punch list, applies the gate logic to that punch list, and prints one canonical
summary line per perspective.

This skill does NOT replace language-scoped code review (`dh:forensic-review`). It runs
alongside it as an orthogonal quality signal. #1430 replaces the stub gate logic in Step 7 without
changing the caller interface.

Activate `dh:review-verdict-contract` before the first verdict-schema operation.

## Argument Parsing

| Argument | Type | Description |
|----------|------|-------------|
| `--diff <git-range>` | **required** | Git range passed to `git diff --name-only`. Examples: `HEAD~1..HEAD`, `main..feature-branch`, `abc123..def456`. |
| `--issue <N>` | optional | GitHub issue number used for ephemeral plan linkage and slug derivation. |
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

Derive `review_base` exactly once using the first matching rule:

1. `--slug` argument is provided → use its value directly
2. `--issue <N>` argument is provided → `review-{N}` (e.g., `review-2181`)
3. Neither provided → read current git branch name via `git rev-parse --abbrev-ref HEAD` and
   use `review-{branch-name}` (sanitize branch name: replace `/` with `-`)

Run this command and capture its stdout as `run_stamp`:

```text
uv run --quiet --script "${CLAUDE_SKILL_DIR}/scripts/gen_run_stamp.py"
```

`review_slug` is `{review_base}-{run_stamp}`, for example
`review-2181-20260824T014233Z-3f9a2c7e1b804d56`.

Use `review_slug` unchanged in plan operations. Use `multi-{review_slug}` as the team name.

---

## Step 3: Create the Ephemeral Review Plan

**Create a new plan on every run.** Never search for and reuse an existing plan. `review_slug`
carries this run's stamp, so no earlier plan can match it and every run starts with tasks that are
`not-started`, bodies that describe this run's `changed_files`, and no `Review Results` section.

Reuse cannot be made safe by resetting task status alone. Resetting status makes a task claimable
again, but the task body still names the previous run's changed files, so workers would review the
wrong file set; and `Review Results` already exists on the task, so the next append lands inside
that heading rather than creating a second one, leaving a section that holds two concatenated
JSON documents and no longer parses.

### Create the Ephemeral Plan

Build the changed-files body block:

```text
Changed files:
{each file on its own line}
```

Create all five tasks in one typed MCP call. Replace `{changed_files_block}` with the literal
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
            {
                "id": "T5",
                "title": "Review Synthesis",
                "agent": "dh:review-synthesizer",
                "priority": 1,
                "complexity": "medium",
                "dependencies": ["T1", "T2", "T3", "T4"],
                "body": "Read the Review Results section of T1..T4 on this plan and synthesize "
                "them into one deduplicated, cross-referenced punch list.\n"
                "Write the punch-list block per verdict-schema.md §2.6 into this task's "
                "Punch List section.",
            },
        ],
    }
)
```

Store the returned `plan_ref` as `{PA}`. Completion criterion: `plan_ref` is non-empty and the
result has `task_count=5`.

---

## Step 4: TeamCreate and Dispatch Four Workers in Parallel

Create the team:

```text
TeamCreate(team_name="multi-{review_slug}")
```

Dispatch all four workers simultaneously. Do NOT wait between spawns — all four are independent
and must run in parallel. Each worker receives a minimal prompt that tells it to run the
`dh:start-task` skill against its own task reference. `dh:start-task` owns claim, active-task
registration, and execution. Name the skill in prose — a harness-specific invocation form
reaches only the harness that defines it, and a worker that never runs `dh:start-task` never
claims its task and writes nothing. The `agent:` field in each
SAM task tells `dh:task-worker` which specialist profile to load via `profile_load` internally.

Dispatch `dh:task-worker` for all four tasks: the four perspective reviewer agents declare
`sam_task` to write their verdict but not the rest of the SAM task lifecycle, so under
`dh:dispatch-contract` they cannot be the dispatch target and their behavior reaches the work as a
loaded profile instead. `dh:review-synthesizer` reaches the same one operation, so Step 6
dispatches it the same way.

Every prompt names the same output destination: the `Review Results` section of the worker's own
task. That section is the only channel the synthesizer reads in Step 6 — a reviewer that does not
write it is a missing verdict, and the punch list records it as one. The loaded profile — not the
dispatch prompt — performs that write: each reviewer agent's own SOP ends with a mandatory write
to `Review Results` as part of what `dh:start-task` executes. Do not instruct the worker to write
the section itself before running `dh:start-task`; a prompt that does both produces two
`append_section` calls against the same heading, and the second leaves the section holding two
concatenated JSON documents that no longer parse.

```text
Agent(
  team_name="multi-{review_slug}",
  name="{worker}",
  subagent_type="dh:task-worker",
  prompt="Before starting work, load these skills: dh:subagent-contract\n\nYou are working on {lens} review. Your task: {PA}/{task}.\n\nRun the dh:start-task skill against {PA} --task {task}. The loaded profile writes your structured verdict block into the task's Review Results section — that is where the punch list reads your verdict. Do not write that section yourself first; the profile's own SOP performs the single write."
)
```

Substitute one row per spawn:

| `{worker}` | `{lens}` | `{task}` |
|------------|----------|----------|
| `security-worker` | security | `T1` |
| `performance-worker` | performance | `T2` |
| `quality-worker` | quality | `T3` |
| `accessibility-worker` | accessibility | `T4` |

---

## Step 5: Wait for the Four Reviews to Finish

Wait until `T1`..`T4` have all reached a terminal status. Poll:

```python
mcp__plugin_dh_sam__sam_plan(plan="{PA}", config={"action": "status"})
```

A task is terminal at `complete`, `blocked`, `failed`, `skipped`, or `deferred`. `T5` stays
`not-started` throughout this step — it is dispatched in Step 6, and its dependencies keep
`sam_plan(action="ready")` from offering it before all four reviews land.

---

## Step 6: Synthesize the Punch List

Dispatch one more worker against `T5`. It reads the four `Review Results` sections, merges
findings that name the same defect across perspectives into single entries, and writes the
punch-list block into `T5`'s own `Punch List` section. As with the four reviewer workers, the
`dh:review-synthesizer` profile — loaded by `dh:start-task` — performs that write as its own Step
5; the dispatch prompt only tells the worker where to look and where its output is read, not to
write the section itself.

```text
Agent(
  team_name="multi-{review_slug}",
  name="synthesis-worker",
  subagent_type="dh:task-worker",
  prompt="Before starting work, load these skills: dh:subagent-contract\n\nYou are synthesizing the four perspective verdicts on plan {PA} into one punch list. Your task: {PA}/T5.\n\nRun the dh:start-task skill against {PA} --task T5. The loaded profile writes your punch-list block into the task's Punch List section — that is where the gate reads your output. Do not write that section yourself first; the profile's own SOP performs the single write."
)
```

Wait for `T5` to reach a terminal status, then read it and take its `Punch List` section:

```python
mcp__plugin_dh_sam__sam_task(plan="{PA}", task="T5", config={"action": "read"})
punch_list = json.loads(punch_list_section)
```

The block carries each perspective's §2.1 verdict block verbatim in `verdicts`, the perspectives
that returned nothing in `missing`, and the deduplicated findings in `entries`. It gives the gate
everything it needs to render the summary and entries, but not everything it needs to trust the
`verdict` token or the findings behind `entries` — see the reconciliation checks below.

`json.loads` succeeding proves the section is JSON, not that it is a punch list. Run the
`review-verdict-contract` §2.6 validity checks against the parsed
block before Step 7 reads any field, and take the `Punch list not produced` failure path below —
naming the check that failed — when any of them fails. Indexing a field the gate needs out of an
unvalidated block raises on `{}` and silently under-reports coverage on a block missing a
perspective, and a review that reports fewer perspectives than it ran is a false pass.

**Reconcile against source (§2.6 checks 6 and 7):** the synthesizer copies each `verdicts[i]` block
from its perspective's own `Review Results` section, but a copy is a claim, not a guarantee. Read
the four raw `Review Results` sections on `T1`..`T4` — comparing the punch list's own `verdicts`
and `entries` fields against each other is not enough, since both are the synthesizer's own output
and an internally-consistent alteration to both still passes. Confirm two things against those raw
sections directly:

- Check 6: each `verdicts[i].verdict` matches its source perspective's `verdict` field exactly. An
  LLM that alters a source `REJECT` to `APPROVE` while carrying its finding text forward still
  produces a block that passes every other check, because none of them compares `verdict` to its
  source.
- Check 7: each raw finding's `description` on `T1`..`T4` appears verbatim in some
  `entries[].descriptions`, at the index where that entry's `entries[].perspectives` names the
  finding's own perspective. An LLM that alters a finding's `file`, `severity`, `description`, or
  `rule` identically in both `verdicts[i].findings` and `entries`, or drops one while inventing a
  duplicate attribution to keep the total unchanged, still passes every check that compares the
  punch list only against itself.

A mismatch on either check is that check failing: take the `Punch list not produced` failure path
below and name the check and the perspective or finding it failed on — a punch list that silently
drops a REJECT, or silently misstates a finding, is a false pass, and the gate's entire correctness
rests on these two checks, so both run on every synthesis, not only when something looks wrong.

**Punch list not produced:** a terminal `T5` whose `Punch List` section is absent, does not
parse as JSON, or fails any validation check above is synthesis that did not happen. FAIL with
`Punch list not produced`, name the check that failed, report which perspectives did write a
`Review Results` section so the run is diagnosable, then run `TeamDelete(team_name="multi-{review_slug}")`
and exit non-zero — this failure happens before Step 7, so its own team cleanup and exit are the
only ones that will run for it.

---

## Step 7: Apply Gate and Print Summary

### Gate Logic

The gate logic is the pre-#1430 stub. The full gate logic including the all-SKIP edge case is
defined in `review-verdict-contract` §2.4. Both inputs come
from the punch list read in Step 6: `punch_list["verdicts"]` and `punch_list["missing"]`.

Apply gate in this order:

1. **Check for missing verdicts.** For each perspective named in `punch_list["missing"]`, FAIL
   immediately with message `"Perspective {X} did not return a verdict"`. A missing verdict is
   never an approval.

2. **Check for REJECT.** If any verdict has `verdict == "REJECT"`, the gate FAILS. Collect all
   REJECT verdicts and their blocking findings for the summary. Report the blocking findings from
   `punch_list["entries"]`, where a defect two perspectives raised appears once and names both.

3. **Check for all-SKIP edge case.** If all four verdicts are `SKIP`, the gate PASSES but the
   summary MUST include this exact warning line:

   ```text
   NOTE: No perspectives reviewed — all skipped
   ```

4. **All other combinations** (any APPROVE, remaining SKIP) → gate PASSES.

**Gate interface:** The gate interface is stable:
`gate(verdicts: list[VerdictBlock]) -> GateResult` where `GateResult = {passed: bool,
summary_line: str, blocking_findings: list[Finding]}`.

### Summary Line Format

Print one canonical summary line:

```text
Security: {token} | Performance: {token} | Quality: {token} | Accessibility: {token}
```

Take each `{token}` from the verdict-to-token mapping in
`review-verdict-contract` §2.2, which also shows a fully
rendered example line.

### Exit and Cleanup

1. If gate FAILED (missing verdict or any REJECT): print the summary line, then TeamDelete, then
   exit non-zero.
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
    Empty -->|No| Slug["Derive review_base, then<br>review_slug = review_base + run stamp"]
    Slug --> CreatePlan["sam_plan(config: create + T1..T5)<br>always a new plan — never reused"]
    CreatePlan --> PlanAddr["Store new plan address as {PA}"]
    PlanAddr --> Team["TeamCreate(team_name='multi-{review_slug}')"]
    Team --> Parallel[Dispatch 4 workers in parallel — no wait between spawns]
    Parallel --> W1["Agent(name='security-worker', subagent_type='dh:task-worker')"]
    Parallel --> W2["Agent(name='performance-worker', subagent_type='dh:task-worker')"]
    Parallel --> W3["Agent(name='quality-worker', subagent_type='dh:task-worker')"]
    Parallel --> W4["Agent(name='accessibility-worker', subagent_type='dh:task-worker')"]
    W1 --> Collect["Wait for T1..T4 terminal via sam_plan status"]
    W2 --> Collect
    W3 --> Collect
    W4 --> Collect
    Collect --> Synth["Dispatch synthesis worker on T5<br>Wait for T5 terminal<br>Read its Punch List section"]
    Synth --> NoList{"Punch List parses AND<br>validates against §2.6?"}
    NoList -->|No| FailSynth[FAIL — Punch list not produced.<br>TeamDelete. Exit non-zero.]
    NoList -->|Yes| Gate{Any REJECT?}
    Gate -->|Missing verdict| Fail[FAIL — Perspective X did not return a verdict.<br>Print summary. TeamDelete. Exit non-zero.]
    Gate -->|Any REJECT| Fail2[Print summary. TeamDelete. Exit non-zero.]
    Gate -->|All SKIP| Warn[Print summary. Print all-SKIP warning. TeamDelete. Exit 0.]
    Gate -->|All APPROVE or APPROVE+SKIP| Pass[Print summary. TeamDelete. Exit 0.]
```

---

## Ephemeral Plan Task Structure

The ephemeral plan always has exactly the five tasks the Step 3 create call defines — `T1`
security, `T2` performance, `T3` quality, `T4` accessibility, `T5` synthesis.

The four review tasks have `dependencies: []` — they are independent and run in parallel. T5
depends on all four, so `sam_plan(action="ready")` offers it only once every perspective has
finished. `dh:task-worker` reads the `agent:` field itself and passes it to `profile_load`; the
orchestrator passes only the task reference `{PA}/T{N}` to the worker prompt.

---

## Behavioral Rules

- **SKIP is a passing outcome.** A perspective that SKIPs is not a blocker. The punch list records
  it as coverage that was declined, with the reviewer's `skip_reason`.
- **All four verdicts must arrive before the gate runs.** Do not apply the gate on partial results.
- **Every run creates its own plan.** `review_slug` carries this run's stamp, so no earlier
  plan can match it and no run reads another run's results.
- Dispatch uses `dh:task-worker` because the perspective reviewer agents cannot claim or close a SAM task. Specialist behavior is selected through the task profile. See `dh:dispatch-contract`.
- **Do not embed the verdict or punch-list schema, or the UI pattern list.** Activate
  `dh:review-verdict-contract` for all schema definitions.
- **Each reviewer task body must embed the newline-separated changed-files list.** Reviewers read
  their task body to obtain the scan target; they do not receive it via the prompt. T5 reads the
  four verdict sections instead, so its body names those and carries no file list.
- **The punch list is the gate's input.** One defect two perspectives raised is one entry naming
  both, so a REJECT summary counts distinct defects rather than repeating one across lenses.
- **All-SKIP warning is mandatory** when all four perspectives return SKIP.
