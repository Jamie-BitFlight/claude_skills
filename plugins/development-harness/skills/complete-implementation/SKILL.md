---
name: complete-implementation
argument-hint: <task-file-path-or-issue-number>
user-invocable: true
description: "Use when all tasks for a feature are marked COMPLETE — runs holistic quality gates including code review, feature verification, integration check, documentation drift audit and update, and context refinement. Creates follow-up task files when issues are found."
compatibility: Python 3.11+
metadata:
  version: 2.1.0
  last_updated: '2026-06-04'
---

# Complete Implementation (Quality Gates + Recursion)

You MUST validate that the implemented feature meets its goals and quality gates. If follow-up task files are created, route them to backlog items first, then recurse only when the follow-up matches the current scope and priority (see Recursive Follow-up Handling section).


<task_file>
$ARGUMENTS
</task_file>

<sam_cli>
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py"
</sam_cli>

The `references/recursive-follow-up-handling.md` file loaded by this skill is a plain file, not
substituted — it shows bare SAM CLI subcommands and args only (e.g. `backlog list --title "..."`),
never the invocation prefix. Prepend the command in <sam_cli/> above to every one of them.

---

> [!IMPORTANT]
> When provided a process map or Mermaid diagram, treat it as the authoritative procedure. Execute steps in the exact order shown, including branches, decision points, and stop conditions.
> A Mermaid process diagram is an executable instruction set. Follow it exactly as written: respect sequence, conditions, loops, parallel paths, and terminal states. Do not improvise, reorder, or skip steps. If any node is ambiguous or missing required detail, pause and ask a clarifying question before continuing.
> When interacting with a user, report before acting the interpreted path you will follow from the diagram, then execute.

---

## Input Format Detection

Parse `$ARGUMENTS` to determine the input type before proceeding:

The following diagram is the authoritative procedure for Input Format Detection. Execute steps in the exact order shown, including branches, decision points, and stop conditions.

```mermaid
flowchart TD
    Input["Read $ARGUMENTS"] --> Q1{"starts with 'plan/'<br>OR contains '.yaml'<br>OR contains '/'?"}
    Q1 -->|Yes| FilePath["FILE PATH format<br>→ proceed to 'Resolve Plan Address'<br>(existing flow, unchanged)"]
    Q1 -->|No| Q2{"starts with '#'?"}
    Q2 -->|Yes| IssueHash["Strip '#' → issue_number<br>→ proceed to 'Resolve Issue'"]
    Q2 -->|No| Q3{"matches ^[0-9]+$ ?"}
    Q3 -->|Yes| IssueBare["issue_number = input<br>→ proceed to 'Resolve Issue'"]
    Q3 -->|No| Q4{"contains '/issues/'?"}
    Q4 -->|Yes| IssueURL["Extract number from URL path<br>→ proceed to 'Resolve Issue'"]
    Q4 -->|No| Q5{"beads ID? e.g. bd-a3f8"}
    Q5 -->|Yes| IssueBeads["issue_id = input str<br>→ Resolve Issue"]
    Q5 -->|No| Err["ERROR: unrecognized format.<br>Expected: path, #N, number, URL, beads ID."]
```

---

## Resolve Issue

Entered when input is `#N`, bare `N`, GitHub URL, or beads ID (e.g. `bd-a3f8`). Skip for file path input.

**Step 1 -- Fetch issue data**:

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" backlog view --selector "#{issue_number}"
```

If the response contains an `error` key:

```text
ERROR: Issue #{issue_number} not found. Verify the issue number and try again.
```

Stop.

**Step 2 -- Check for linked plan**:

Read the `plan` field from the response.

The following diagram is the authoritative procedure for Resolve Issue Step 2 linked plan check. Execute steps in the exact order shown, including branches, decision points, and stop conditions.

```mermaid
flowchart TD
    Plan{plan field<br>present and non-empty?}
    Plan -->|Yes| AutoResolve["Extract plan file path from plan field<br>→ proceed to 'Resolve Plan Address'<br>(existing 7-phase flow)"]
    Plan -->|No| PropFlow["→ proceed to 'Proportional Quality Gates'"]
```

When auto-resolving to the SAM path, output:

```text
Issue #{issue_number} has linked plan: {plan_address}
Proceeding with full quality gates.
```

**Step 3 -- Extract context for proportional gates**:

From the `backlog_view` response, extract and store:

- `issue_number`: int
- `title`: str
- `body`: str (full issue body text)
- `labels`: list[str]

These values are used by the Proportional Quality Gates section below.

---

## Proportional Quality Gates

Entered only when the issue has no linked plan. Skip this section when input is a file path or when the issue has a linked plan (auto-resolved to SAM path).

**Step 1 -- Discover modified files**:

```bash
git log --all --grep="#${issue_number}" --format=%H
```

For each commit SHA returned:

```bash
git diff-tree --no-commit-id --name-only -r {sha}
```

Deduplicate the file list. If no commits reference the issue number, fall back to:

```bash
git diff --name-only main...HEAD
```

Store the deduplicated file list as `modified_files`.

If `modified_files` is empty after both strategies:

```text
WARNING: No modified files found for issue #{issue_number}.
Code review and test verification will run against the full working tree.
```

**Step 2 -- Extract acceptance criteria from issue body**:

Parse the `body` field for an acceptance criteria section. Search for these markers (case-insensitive, in order):

1. `## Acceptance Criteria` header -- extract all content until next `##` header
2. `**Acceptance Criteria**:` bold marker -- extract all content until next bold marker or `##` header
3. Lines starting with `- [ ]` (unchecked checkboxes) -- collect all such lines

Store as `acceptance_criteria` (string or None). If none found, set to None.

**Step 3 -- Build proportional quality gate plan**:

Create the SAM plan directly with 5 tasks. The documentation pass (T4 Documentation Drift Audit + T5 Documentation Update) is included on this direct/issue-only route exactly as it is on the full SAM path — a feature reached through proportional gates is held to the same documentation standard as one reached through a linked plan:

```text
mcp__plugin_dh_sam__sam_plan(
    config={"action": "create",
            "slug": "pqg-issue-{issue_number}",
            "goal": "Proportional quality gate verification for issue #{issue_number}",
            "issue": {issue_number},
            "tasks": [
                {"id": "T1", "title": "Code Review",        "agent": "code-reviewer",   "dependencies": [],    "priority": 1, "complexity": "medium",
                 "body": "Review files modified for issue #{issue_number}: {modified_files}. Check against acceptance criteria: {acceptance_criteria}"},
                {"id": "T2", "title": "Test Verification",  "agent": "feature-verifier","dependencies": ["T1"],"priority": 1, "complexity": "medium",
                 "body": "Verify issue #{issue_number} acceptance criteria are met. Files in scope: {modified_files}"},
                {"id": "T3", "title": "Acceptance Check",   "agent": "integration-checker","dependencies": ["T2"],"priority": 1, "complexity": "low",
                 "body": "Confirm acceptance criteria for issue #{issue_number} pass end-to-end: {acceptance_criteria}"},
                {"id": "T4", "title": "Documentation Drift Audit", "agent": "doc-drift-auditor","dependencies": ["T3"],"priority": 1, "complexity": "low",
                 "body": "Audit documentation for drift introduced by issue #{issue_number}. item_id={issue_number} (REQUIRED — register the audit-report artifact against it; block if absent). project_root is the repository root (your current working directory). Files in scope: {modified_files}. Report any docs that are now stale, missing, or contradicted by the change."},
                {"id": "T5", "title": "Documentation Update", "agent": "service-docs-maintainer","dependencies": ["T4"],"priority": 1, "complexity": "low",
                 "body": "Update documentation to resolve the drift found in T4 for issue #{issue_number}. item_id={issue_number} (read the audit-report artifact registered against it). project_root is the repository root (your current working directory). Files in scope: {modified_files}."}
            ]}
)
```

Note — `sam_plan(action='create')` has no full CLI equivalent for this call: the CLI's `plan create`
accepts only one inline task per call (vs MCP's `tasks=[...]` list), and this call's per-task
`dependencies`/`body` fields have no CLI flag confirmed in the verified mapping — converting would
require guessing flag names. Left as MCP pending flag verification (backlog item #2793, 2026-08-05).

The `pqg-` prefix (proportional quality gate) distinguishes from the `qg-` prefix used by full SAM gates. Store the returned plan ID as `{PQG}` for use throughout the dispatch loop.

**Step 4 -- SAM dispatch loop**:

Use the same SAM Dispatch Loop as the existing 7-phase flow (see "SAM Dispatch Loop (Phases T0-T6)" section). The loop operates identically — 5 tasks instead of 7 is the only structural difference. The proportional plan omits T0 (Multi-Perspective Review) and T6 (Context Refinement) to stay proportional, but retains the T4/T5 documentation pass.

**Phase-specific post-dispatch actions for proportional gates**:

The following diagram is the authoritative procedure for Proportional Quality Gates phase-specific post-dispatch actions. Execute steps in the exact order shown, including branches, decision points, and stop conditions.

```mermaid
flowchart TD
    Done{Which task<br>just completed?}
    Done -->|"T1 Code Review"| T1Post["No follow-up extraction<br>(proportional gates do not<br>generate follow-ups)"]
    Done -->|"T2 Test Verification"| T2Post["Check test results in agent output<br>If failures: log but do not block<br>(completion gate handles pass/fail)"]
    Done -->|"T3 Acceptance Check"| T3Post["No post-dispatch action"]
    Done -->|"T4 Drift Audit"| T4Post{"Read the Total findings count<br>from T4's ARTIFACTS return block<br>(full report is in the audit-report artifact)"}
    T4Post -->|"0 findings — no drift"| SkipT5["sam_task(plan='{PQG}', task='T5',<br>config={action=state, status=skipped})"]
    T4Post -->|"1 or more findings — drift"| T5Ready["T5 remains NOT_STARTED — will be<br>dispatched on next loop iteration"]
    Done -->|"T5 Documentation Update"| T5Post["No post-dispatch action"]
    T1Post --> Continue["Continue loop"]
    T2Post --> Continue
    T3Post --> Continue
    SkipT5 --> Continue
    T5Ready --> Continue
    T5Post --> Continue
```

**Detecting drift in T4 output**: The `@dh:doc-drift-auditor` agent returns a `Total findings: {count}` line in its `ARTIFACTS` block and registers the full drift report as the `audit-report` artifact. No drift = `Total findings: 0` → skip T5. Drift = `Total findings` of 1 or more → dispatch T5. If the count line is absent, read the `audit-report` artifact and treat a non-empty `## Findings by Category` as drift. This is the same drift-detection rule the full SAM path applies to its T4 phase.

**Step 5 -- Completion verification gate**:

After the dispatch loop exits, verify all 5 phases reached terminal status:

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" plan status --plan-address "{PQG}"
```

All 5 tasks must have `status == 'complete'`, with one exception: T5 (Documentation Update) may have `status == 'skipped'` when T4 found no drift. Any other task with `status == 'skipped'` is an unauthorized skip — treat as a failure. This skip whitelist matches the full SAM path's Completion Verification Gate.

The following diagram is the authoritative procedure for Proportional Quality Gates completion verification. Execute steps in the exact order shown, including branches, decision points, and stop conditions.

```mermaid
flowchart TD
    Status["sam_plan(action=status, plan='{PQG}')"] --> Iter["Iterate over all 5 tasks"]
    Iter --> Check{For each task:<br>check status}
    Check -->|"status == 'complete'"| PassTask["Task passes"]
    Check -->|"status == 'skipped' AND task_id == 'T5'"| PassTask
    Check -->|"status == 'skipped' AND task_id != 'T5'"| FailUnauth["FAIL — unauthorized skip"]
    Check -->|"any other status"| FailIncomplete["FAIL — task incomplete or blocked"]
    PassTask --> AllPassed{All 5 tasks<br>passed?}
    AllPassed -->|Yes| Proceed["Proceed to Step 6"]
    AllPassed -->|No| Stop["STOP — report failures, do NOT apply label"]
    FailUnauth --> AllPassed
    FailIncomplete --> AllPassed
```

On verification failure:

```text
COMPLETION BLOCKED — Proportional Quality Gate Incomplete

Failed tasks:
  {task_id} ({phase_name}): status={status}
  [repeat for each failing task]

To resume: re-run /complete-implementation #{issue_number}
BLOCKED tasks will be reset to NOT_STARTED automatically.
```

Stop. Do not apply the `status:verified` label.

**Step 6 -- Apply status:verified label**:

On verification success:

```text
mcp__plugin_dh_backlog__backlog_update(selector="#{issue_number}", verified=True)
```

Note — no CLI equivalent exists for `verified=True` as of 2026-08-05 (backlog item #2793): the
CLI's `backlog update` has no `--verified` flag. This call must stay MCP.

**Beads backend**: No `dh:state:verified` label — skip this call, continue.

On failure (GitHub only), output:

```text
COMPLETION BLOCKED — status:verified label could not be applied.

Error: {error}
Issue: #{issue_number}

Fix the error (check backend credentials and access), then re-run /complete-implementation #{issue_number}.
```

Stop. Do not proceed to the Final Step commit.

**Step 7 -- No recursive follow-up handling**:

The issue-only path does not produce follow-up task files. Skip directly to "Final Step: Commit and Push Remaining Changes", then "Team Shutdown", then "Resolve the Issue".

---

## Resolve Plan Address

Extract the plan address `P{N}` from the task file path:

- `plan/Pb3c4d5e6-integrate-sam-schema.yaml` → plan id `b3c4d5e6` → address `Pb3c4d5e6`
- Strip `plan/P` prefix, take the hex id, format as `P{id}`

Use `P{N}` in all `sam` CLI calls below.

---

## Pre-Phase 1: TN Verification Check

Before invoking Phase 1, check for a TN verification report produced by `tn-verification-gate` (which reads the T0 baseline written by `t0-baseline-capture`).

Extract `{slug}` from the task file path (`plan/P{id}-{slug}.yaml` — strip the `P{id}-` prefix and `.yaml` suffix).

Read the TN-verification artifact via `artifact_read(item_id={N}, artifact_type="TN-verification")`.

The file contains a list of per-criterion `BookendVerification` records — one per `acceptance-criteria-structured` entry. There is no top-level `verdict` field. Aggregate the verdict by scanning all records: the overall result is FAIL if any record has `status: regressed`; otherwise PASS.

The following diagram is the authoritative procedure for Pre-Phase 1 TN Verification Check. Execute steps in the exact order shown, including branches, decision points, and stop conditions.

```mermaid
flowchart TD
    Read["artifact_read(item_id, 'TN-verification')"] --> Exists{Artifact exists?}
    Exists -->|No| Proceed["No structured criteria — proceed to Phase 1"]
    Exists -->|Yes| Scan["Scan all per-criterion records<br>for status: regressed"]
    Scan --> AnyRegressed{Any criterion<br>has status: regressed?}
    AnyRegressed -->|No| Proceed
    AnyRegressed -->|Yes| Stop["STOP — report regressions and block completion"]
    Stop --> Report["Display each criterion with status: regressed<br>Show check_command, T0 stdout, TN stdout<br>Instruct: fix regressions before re-running"]
```

If any criterion has `status: regressed`:

1. List each criterion where `status: regressed` with its `check_command`, T0 captured stdout, and TN captured stdout.
2. Output:

```text
COMPLETION BLOCKED — TN Verification Failed

Regressed criteria:
  {criterion-id}: {description}
    command: {check_command}
    T0 result: exit {code}, stdout: {stdout}
    TN result: exit {code}, stdout: {stdout}

Fix the regressions, then re-run /complete-implementation.
```

3. Stop. Do not proceed to Phase 1.

---

## Pre-Phase 1a: Migration Fidelity Sign-Off

Before proceeding to Artifact Discovery, check for migration signals.

Execute the full gate procedure defined in [./references/migration-fidelity-gate.md](./references/migration-fidelity-gate.md).

**Summary of detection signals** (full evaluable criteria in the reference):

- Issue title or body contains: "migrat", "convert format", "replace .md", "format conversion", "move from", "transition from"
- Any task `acceptance_criteria` field contains: "delete", "remove source", "after migration complete", "drop the source"

If no signal found — skip gate, proceed to Artifact Discovery.

If signal found — confirm all four fidelity items from the reference before proceeding. If any unconfirmed, emit `COMPLETION BLOCKED — Migration Fidelity Gate` (format in reference) and stop.

---

## Pre-Phase: Artifact Discovery

When the parent story issue number is known (from the plan's `issue` field or the backlog item), query the artifact manifest to discover all plan artifacts for this feature:

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" artifact list --item-id N
```

If the response contains artifacts, pass the manifest to quality gate agents (Phases T0-T6) so they can access plan artifacts via `artifact_read` instead of filesystem paths. This is critical for worktree-isolated agents.

**Fallback**: If `artifact_list` returns an empty manifest or an error, quality gate agents use filesystem path conventions as before. This ensures backward compatibility with issues that predate the artifact manifest system.

---

## Pre-Phase 1b: Process Accumulated Concerns

Execute the full procedure defined in [./references/concerns-processing.md](./references/concerns-processing.md).

**Summary**: Read backlog item → if `## Concerns` has unchecked items, verify each (create backlog item if real; mark unconfirmed if not) → update section → proceed to Quality Gate Plan Creation. If no concerns section, proceed immediately.

---

## Quality Gate Plan Creation

After the pre-phases complete, set up the SAM-enforced quality gate plan.

Extract `{slug}` from the task file path (`plan/P{id}-{slug}.yaml` — strip the `P{id}-` prefix and `.yaml` suffix).

### Step 1: Check for existing QG plan

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" plan list --search "qg-{slug}"
```

The following diagram is the authoritative procedure for Quality Gate Plan Creation Step 1 check for existing QG plan. Execute steps in the exact order shown, including branches, decision points, and stop conditions.

```mermaid
flowchart TD
    List["sam_plan(action=list, search='qg-{slug}')"] --> Found{QG plan found?}
    Found -->|No| Create["sam_plan(action=create)<br>tasks list from phase mapping table"]
    Found -->|Yes| Check{All tasks terminal?}
    Check -->|"Yes — COMPLETE or SKIPPED"| Skip["Skip to Completion Verification Gate"]
    Check -->|"No — tasks remain"| Reset["Reset BLOCKED tasks to NOT_STARTED,<br>resume SAM dispatch loop"]
    Create --> Loop["Enter SAM Dispatch Loop"]
    Reset --> Loop
```

### Step 2: Create QG plan (if not found)

If no QG plan exists, create it directly using the phase mapping table above:

```text
mcp__plugin_dh_sam__sam_plan(
    config={"action": "create",
            "slug": "qg-{slug}",
            "goal": "Quality gate enforcement for {slug}",
            "issue": {issue_number},
            "tasks": [
                {"id": "T0", "title": "Multi-Perspective Review", "agent": "task-worker",     "dependencies": [],           "priority": 1, "complexity": "high"},
                {"id": "T1", "title": "Code Review",              "agent": "code-reviewer",   "dependencies": [],           "priority": 1, "complexity": "medium"},
                {"id": "T2", "title": "Feature Verification",     "agent": "feature-verifier","dependencies": ["T1"],       "priority": 1, "complexity": "medium"},
                {"id": "T3", "title": "Integration Check",        "agent": "integration-checker","dependencies": ["T2"],   "priority": 1, "complexity": "medium"},
                {"id": "T4", "title": "Documentation Drift Audit","agent": "doc-drift-auditor","dependencies": ["T3"],     "priority": 1, "complexity": "low",
                 "body": "Audit documentation for drift in {slug} (issue #{issue_number}). item_id={issue_number} (REQUIRED — register the audit-report artifact against it; block if absent). project_root is the repository root (your current working directory)."},
                {"id": "T5", "title": "Documentation Update",     "agent": "service-docs-maintainer","dependencies": ["T4"],"priority": 1, "complexity": "low",
                 "body": "Update documentation to resolve the drift found in T4 for {slug} (issue #{issue_number}). item_id={issue_number} (read the audit-report artifact registered against it). project_root is the repository root (your current working directory)."},
                {"id": "T6", "title": "Context Refinement",       "agent": "context-refinement","dependencies": ["T5"],    "priority": 1, "complexity": "medium"}
            ]}
)
```

Note — `sam_plan(action='create')` has no full CLI equivalent for this call: the CLI's `plan create`
accepts only one inline task per call (vs MCP's `tasks=[...]` list), and this call's per-task
`dependencies`/`body` fields have no CLI flag confirmed in the verified mapping — converting would
require guessing flag names. Left as MCP pending flag verification (backlog item #2793, 2026-08-05).

The response contains the QG plan ID (e.g., `Pdd73f3bd`). Store it as `{QG}` for use throughout the dispatch loop.

### Step 3: Reset BLOCKED tasks (on re-run)

If the QG plan already exists and has BLOCKED tasks, reset each to NOT_STARTED before entering the dispatch loop:

```text
For each task where status == "blocked":
    mcp__plugin_dh_sam__sam_state(plan="{QG}", task="{task_id}", status="not-started")
```

Note — `sam_state` is not a registered MCP tool (only `sam_plan`, `sam_task`, and `sam_active_task`
are registered per `sam_schema/server.py`, verified 2026-08-05). This call site references a stale
or incorrect tool name and needs correction as a separate fix (likely
`sam_task(config={"action": "state", ...})`) — left unchanged here rather than silently aliased
(backlog item #2793).

This allows re-running `complete-implementation` to resume from the blocked phase without re-executing completed phases.

---

## SAM Dispatch Loop (Phases T0-T6)

**Phase task mapping:**

| Task | Phase | Agent |
|------|-------|-------|
| T0 | Multi-Perspective Review | dh:multi-perspective-review (orchestrated) |
| T1 | Code Review | code-reviewer |
| T2 | Feature Verification | feature-verifier |
| T3 | Integration Check | integration-checker |
| T4 | Documentation Drift Audit | doc-drift-auditor |
| T5 | Documentation Update | service-docs-maintainer |
| T6 | Context Refinement | context-refinement |

### Team Setup

Check for an existing implementation team before dispatching QG agents:

- `team_name = "impl-{slug}"` (same team created by `implement-feature`)
- If the team exists (config at `~/.claude/teams/impl-{slug}/config.json`), reuse it for QG agent dispatch
- If no team exists, create one: `TeamCreate(team_name="impl-{slug}")`
- Store `team_name` for use in agent dispatch and the Team Shutdown step below

### Dispatch Loop

Repeat until `sam_plan(action='ready')` returns a `ReadyTasksResult` with an empty `ready_tasks` list:

**1. Get next ready task:**

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" plan ready --plan-address "{QG}"
```

If the result is empty, exit the loop and proceed to Completion Verification Gate.

**2. Load the start-task skill:**

```text
Skill(skill="start-task", args="{QG} --task {task_id}")
```

Pass `team_name="{team_name}"` when spawning QG agents so they join the existing implementation team.

`start-task` claims the task and marks it COMPLETE on finish via the SubagentStop hook. Do not call `sam_task(action='claim')` in the orchestrator before this step — claiming here causes a double-claim that causes `start-task` to receive `claimed: false` and stop without executing the task body.

**3. Phase-specific post-dispatch actions:**

After each dispatched phase completes, run the phase-specific processing before querying `sam_plan(action='ready')` again:

The following diagram is the authoritative procedure for SAM Dispatch Loop phase-specific post-dispatch actions. Execute steps in the exact order shown, including branches, decision points, and stop conditions.

```mermaid
flowchart TD
    Done{Which task<br>just completed?}
    Done -->|T0 Multi-Perspective Review| T0Post["Any REJECT — trigger Recursive Follow-up Handling<br>(same path as T1 NEEDS_WORK)."]
    Done -->|T1 Code Review| T1Post["Read codebase-analysis artifact.<br>Verdict drives Recursive Follow-up Handling<br>(Step 1 — fix loop or backlog routing)."]
    Done -->|T4 Drift Audit| T4Post{"Read the Total findings count<br>from T4's ARTIFACTS return block<br>(full report is in the audit-report artifact)"}
    T4Post -->|"0 findings — no drift"| SkipT5["sam_task(plan='{QG}', task='T5',<br>config={action=state, status=skipped})"]
    T4Post -->|"1 or more findings — drift"| T5Ready["T5 remains NOT_STARTED — will be<br>dispatched on next loop iteration"]
    Done -->|T6 Context Refinement| T6Post{"DIVERGENCE_REQUIRING_REVIEW block<br>present in T6 agent output?"}
    T6Post -->|"Yes"| StoreDiv["Store divergence block for final output"]
    T6Post -->|"No"| Continue["No phase-specific action — continue loop"]
    Done -->|"T2, T3, T5"| Continue
    T0Post --> Continue
    T1Post --> Continue
    SkipT5 --> Continue
    T5Ready --> Continue
    StoreDiv --> Continue
```

**Detecting drift in T4 output**: The `@dh:doc-drift-auditor` agent returns a `Total findings: {count}` line in its `ARTIFACTS` block and registers the full drift report as the `audit-report` artifact. No drift = `Total findings: 0`. Drift = `Total findings` of 1 or more. If the count line is absent, read the `audit-report` artifact and treat a non-empty `## Findings by Category` as drift.

---

## Completion Verification Gate

After the SAM dispatch loop exits, verify all phases reached terminal status before allowing label application.

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" plan status --plan-address "{QG}"
```

The following diagram is the authoritative procedure for Completion Verification Gate. Execute steps in the exact order shown, including branches, decision points, and stop conditions.

```mermaid
flowchart TD
    Status["sam_plan(action=status, plan='{QG}')"] --> Iter["Iterate over all tasks in the plan"]
    Iter --> Check{For each task:<br>check status}
    Check -->|"status == 'complete'"| PassTask["Task passes"]
    Check -->|"status == 'skipped' AND task_id == 'T5'"| PassTask
    Check -->|"status == 'skipped' AND task_id != 'T5'"| FailUnauth["FAIL — unauthorized skip"]
    Check -->|"status == 'not-started' OR 'in-progress'"| FailIncomplete["FAIL — incomplete phase"]
    Check -->|"status == 'blocked'"| FailBlocked["FAIL — blocked phase"]
    PassTask --> AllPassed{All tasks<br>passed?}
    AllPassed -->|Yes| Proceed["Proceed to Recursive Follow-up Handling"]
    AllPassed -->|No| Stop["STOP — report failures, do NOT apply label"]
    FailUnauth --> AllPassed
    FailIncomplete --> AllPassed
    FailBlocked --> AllPassed
```

**Skip whitelist**: ONLY T5 (Documentation Update) may have `status: skipped`. Any other task with `status: skipped` is an unauthorized skip — treat as a failure.

**On verification failure**, output:

```text
COMPLETION BLOCKED — Quality Gate Incomplete

Failed tasks:
  {task_id} ({phase_name}): status={status}
  [repeat for each failing task]

To resume: re-run /complete-implementation {task_file_path}
BLOCKED tasks will be reset to NOT_STARTED automatically.
```

Stop. Do not apply the `status:verified` label.

**On verification success**, proceed to Recursive Follow-up Handling.

---

## Post-Phase-6: Surface Divergence Findings

If the T6 (Context Refinement) sub-agent output contained a `DIVERGENCE_REQUIRING_REVIEW` block (collected in the dispatch loop), include in the final output to the human:

```text
Plan artifacts have intent divergences requiring your review.
See: [annotated artifact paths from agent output]
Divergences:
  [list from DIVERGENCE_REQUIRING_REVIEW block]
```

This is informational, not blocking. The human reviews at their discretion.
If absent, no additional output is needed — the feature proceeds normally.

---

## Recursive Follow-up Handling

## Constants

`DH_RECURSIVE_REVIEW_TASK_DEPTH = 5`

Maximum number of recursive review-implement-verify cycles permitted within a single
top-level `/complete-implementation` invocation. When `{recursion_depth}` reaches this
value, Guard 1 fires: all remaining in-scope follow-ups are routed to the backlog and
recursion stops.

Initialization: `{recursion_depth}` is set to `0` at skill invocation. It increments by 1
before each call to `Skill(skill="implement-feature")` in the recursion path. A re-run
of `/complete-implementation` on the same task file starts `{recursion_depth}` at `0`.

After all phases complete, route any follow-up task files created by Phase 1 (code-reviewer) to the backlog before deciding on recursion. This ensures no follow-up file is orphaned when the orchestrator skips recursion.

### Step 1: Detect Follow-up Files

Retrieve the review report registered by `@dh:code-reviewer` during Phase 1:

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" artifact read --item-id {issue_number} --artifact-type "codebase-analysis"
```

**If `artifact_read` returns an error**, discover before falling through to SAM search:
`artifact_list(item_id={issue_number})` → find entry matching `"code-review-{issue_number}-*"`
→ re-read with its actual type → emit WARNING if type differs from `"codebase-analysis"`.

Check the `verdict` field in the report:

- `PASS` — no blocking findings; skip the entire routing section (no follow-ups to route)
- `NEEDS-WORK` or `FAIL` — extract the "Required changes (blocking)" section; each blocking
  item becomes a follow-up to route. **When "Required changes (blocking)" is non-empty, run the
  fix loop first (max 3 cycles, `{fix_cycle}`=0):** `sam_plan(action='create', slug="fix-{slug}-blocking-N")`
  one task per entry (`agent: dh:task-worker`); dispatch via `subagent_type="dh:task-worker"`;
  reset T1 to `not-started`; re-dispatch T1; if verdict is `PASS` or blocking entries empty →
  proceed to Step 2; else `fix_cycle += 1`, repeat or BLOCKED at 3. **On BLOCKED** (exhausted
  or fix task `blocked`): report `COMPLETION BLOCKED — Blocking Code Review Findings Not
  Resolved`, do NOT route to backlog, stop, do not apply `status:verified`.

If `artifact_list` also finds no match, fall back to the SAM MCP search:

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" plan list --search "{slug}-followup"
```

Where `{slug}` is extracted from the parent task file path (`plan/P{id}-{slug}.yaml` — strip `P{id}-` prefix and `.yaml` suffix).

If both `artifact_read` and the SAM search return empty: skip the entire routing section (no follow-ups to route).

**Error handling**: If the SAM fallback returns plans from a different feature slug, filter results to only include plans matching the parent task file's slug.

### Steps 2–5: Route Follow-ups to Backlog

Execute the full follow-up routing procedure defined in [./references/recursive-follow-up-handling.md](./references/recursive-follow-up-handling.md).

**Summary**:
- Step 2: Derive a search slug from each follow-up filename; search backlog by title then topic
- Step 3: Classify scope (in-scope vs out-of-scope); route out-of-scope directly to backlog
- Step 4: Link follow-up plan to matched backlog item, or create a new item if no match
- Step 5: Recursion Gate — Guards (depth limit, RT-ICA BLOCKED) then Conditions (slug match + High priority)

---

## Apply status:verified Label

After all phases and follow-up routing complete, apply the `status:verified` GitHub label to the parent backlog issue.

**Beads backend**: No `dh:state:verified` label — skip this section, continue to Final Step.

### Step 1: Locate the backlog item

Derive the search slug from the task file path (same algorithm as Recursive Follow-up Handling). Search the backlog:

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" backlog list --title "{slug}"
```

If zero items match, skip this section — there is no issue to label.

### Step 2: Apply the label

Extract `issue_number` from the matched item returned by `backlog list` in Step 1 (read from the item's `issue` field, e.g. `"#2437"` → `issue_number = 2437`).

Call:

```text
mcp__plugin_dh_backlog__backlog_update(selector="#{issue_number}", verified=True)
```

Note — no CLI equivalent exists for `verified=True` as of 2026-08-05 (backlog item #2793): the
CLI's `backlog update` has no `--verified` flag. This call must stay MCP.

**Error handling**: If the call returns an `error` key, output:

```text
COMPLETION BLOCKED — status:verified label could not be applied.

Error: {error}
Backlog item: #{issue_number}

Fix the error (check backend credentials and access), then re-run /complete-implementation.
```

Stop. Do not proceed to the Final Step commit.

---

## Final Step: Commit and Push Remaining Changes

Check for uncommitted changes and commit any remaining modifications in a single commit.

```bash
git status
```

**Issue number in commit message**: Before committing, check the backlog item for the current feature slug:

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" backlog list --title "{slug}"
```

Check the `issue` field on the matching item. If present, append `Fixes #NNN` to the commit message body (NNN = GitHub integer issue number; omit for beads IDs). If no issue number is found, omit it.

Push after committing; skip if the working tree is clean.

---

## Team Shutdown

After commit+push, shut down all teammates in the implementation team:

1. Read `~/.claude/teams/{team_name}/config.json` to get the members list.
2. For each member name in the `members` array, send:

```text
SendMessage(to="{name}", message={"type": "shutdown_request"})
```

3. Note: broadcast to `"*"` does not support structured shutdown messages — send individually
   to each named member.

---

## Resolve the Issue

**PQG path (issue-only)**: Use `selector="#{issue_number}"`.

**SAM path (plan-linked)**: Use `selector="#{issue_number}"` from the Apply status:verified Label step. Skip this step if no backlog item was matched in that step.

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" backlog resolve --selector "<selector>" --summary "Implementation complete — AC verified PASS"
```

On failure: output `COMPLETION BLOCKED — backlog_resolve failed: {error}`. Stop.

---

## Final Handoff Output

Execute the full procedure defined in [./references/final-handoff.md](./references/final-handoff.md).
