---
name: complete-implementation
argument-hint: <task-file-path-or-issue-number>
user-invocable: true
description: "Holistic completion workflow after a feature's tasks are marked COMPLETE: code review, feature verification, integration check, documentation drift audit/update, and context refinement. Creates follow-up task files when issues are found."
compatibility: Python 3.11+
metadata:
  version: 2.0.0
  last_updated: '2026-03-22'
hooks:
  SubagentStop:
  - hooks:
    - type: command
      command: python3 "${CLAUDE_SKILL_DIR}/../../implementation-manager/scripts/task_status_hook.py"
---

# Complete Implementation (Quality Gates + Recursion)

You MUST validate that the implemented feature meets its goals and quality gates. If follow-up task files are created, route them to backlog items first, then recurse only when the follow-up matches the current scope and priority (see Recursive Follow-up Handling section).

<task_file>
$ARGUMENTS
</task_file>

---

## Input Format Detection

Parse `$ARGUMENTS` to determine the input type before proceeding:

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
    Q4 -->|No| Err["ERROR: Unrecognized input format.<br>Expected: plan file path, #N, bare number, or GitHub URL."]
```

---

## Resolve Issue

Entered when input is an issue number (`#N`, bare `N`, or GitHub URL). Skip this section when input is a file path.

**Step 1 -- Fetch issue data**:

```text
mcp__plugin_dh_backlog__backlog_view(selector="#{issue_number}")
```

If the response contains an `error` key:

```text
ERROR: Issue #{issue_number} not found. Verify the issue number and try again.
```

Stop.

**Step 2 -- Check for linked plan**:

Read the `plan` field from the response.

```mermaid
flowchart TD
    Plan{plan field<br>present and non-empty?}
    Plan -->|Yes| AutoResolve["Extract plan file path from plan field<br>→ proceed to 'Resolve Plan Address'<br>(existing 6-phase flow)"]
    Plan -->|No| PropFlow["→ proceed to 'Proportional Quality Gates'"]
```

When auto-resolving to the SAM path, output:

```text
Issue #{issue_number} has linked plan: {plan_path}
Proceeding with full 6-phase quality gates.
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

Call the pure function:

```python
tasks_yaml = build_proportional_quality_gate_plan(
    slug=f"issue-{issue_number}",
    issue=str(issue_number),
    modified_files=modified_files,
    acceptance_criteria=acceptance_criteria,
)
```

Create the SAM plan:

```text
mcp__plugin_dh_sam__sam_create(
    slug="pqg-issue-{issue_number}",
    goal="Proportional quality gate verification for issue #{issue_number}",
    tasks_yaml="{tasks_yaml}",
    issue="{issue_number}"
)
```

The `pqg-` prefix (proportional quality gate) distinguishes from the `qg-` prefix used by full SAM gates. Store the returned plan address as `{PQG}` for use throughout the dispatch loop.

**Step 4 -- SAM dispatch loop**:

Use the same SAM Dispatch Loop as the existing 6-phase flow (see "SAM Dispatch Loop (Phases 1-6)" section). The loop operates identically — 3 tasks instead of 6 is the only structural difference.

**Phase-specific post-dispatch actions for proportional gates**:

```mermaid
flowchart TD
    Done{Which task<br>just completed?}
    Done -->|"T1 Code Review"| T1Post["No follow-up extraction<br>(proportional gates do not<br>generate follow-ups)"]
    Done -->|"T2 Test Verification"| T2Post["Check test results in agent output<br>If failures: log but do not block<br>(completion gate handles pass/fail)"]
    Done -->|"T3 Acceptance Check"| T3Post["No post-dispatch action"]
    T1Post --> Continue["Continue loop"]
    T2Post --> Continue
    T3Post --> Continue
```

**Step 5 -- Completion verification gate**:

After the dispatch loop exits, verify all 3 phases reached terminal status:

```text
mcp__plugin_dh_sam__sam_status(plan="{PQG}")
```

All 3 tasks must have `status == 'complete'`. No skip whitelist — all 3 tasks are required.

```mermaid
flowchart TD
    Status["sam_status(plan='{PQG}')"] --> Iter["Iterate over all 3 tasks"]
    Iter --> Check{For each task:<br>check status}
    Check -->|"status == 'complete'"| PassTask["Task passes"]
    Check -->|"any other status"| FailTask["FAIL"]
    PassTask --> AllPassed{All 3 tasks<br>passed?}
    AllPassed -->|Yes| Proceed["Proceed to Step 6"]
    AllPassed -->|No| Stop["STOP — report failures, do NOT apply label"]
    FailTask --> AllPassed
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

On failure, output:

```text
COMPLETION BLOCKED — status:verified label could not be applied.

Error: {error}
Issue: #{issue_number}

Fix the error (check GitHub token, repo access), then re-run /complete-implementation #{issue_number}.
```

Stop. Do not proceed to the Final Step commit.

**Step 7 -- No recursive follow-up handling**:

The issue-only path does not produce follow-up task files. Skip directly to "Final Step: Commit and Push Remaining Changes".

---

## Resolve Plan Address

Extract the plan address `P{N}` from the task file path:

- `plan/P003-integrate-sam-schema.yaml` → plan number `003` → address `P003`
- Strip `plan/P` prefix, take the leading integer NNN, format as `P{NNN}`

Use `P{N}` in all `sam` CLI calls below.

---

## Pre-Phase 1: TN Verification Check

Before invoking Phase 1, check for a TN verification report produced by `tn-verification-gate` (which reads the T0 baseline written by `t0-baseline-capture`).

Extract `{slug}` from the task file path (`plan/P{NNN}-{slug}.yaml` — strip the `P{NNN}-` prefix and `.yaml` suffix).

Read the TN-verification artifact via `artifact_read(issue_number={N}, artifact_type="TN-verification")`. Fallback: if no artifact is registered, read `dh_paths.plan_dir() / "TN-verification-{slug}.yaml"`.

The file contains a list of per-criterion `BookendVerification` records — one per `acceptance-criteria-structured` entry. There is no top-level `verdict` field. Aggregate the verdict by scanning all records: the overall result is FAIL if any record has `status: regressed`; otherwise PASS.

```mermaid
flowchart TD
    Read["artifact_read(issue_number, 'TN-verification')<br>Fallback: dh_paths.plan_dir() / TN-verification-{slug}.yaml"] --> Exists{Artifact exists?}
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

**Detection: scan for migration signals**

Check:
1. Issue title — contains: "migrat", "convert format", "replace .md", "format conversion", "move from", "transition from"
2. Issue body / description section — same keywords
3. P{NNN}.yaml tasks — read each task's `acceptance_criteria` field for: "delete", "remove source", "after migration complete", "drop the source"

Note: `acceptance_criteria` is a dedicated `str` field on the Task model (`sam_schema/core/models.py`) — it can be read directly, not parsed out of a body blob.

If no signal found → skip this gate and proceed to Artifact Discovery.

If any signal found → gate activates.

**Gate logic (when activated)**

Before proceeding, confirm ALL four items. Read the plan artifacts and execution history to find evidence for each.

- [ ] **Fidelity check on real data**: evidence exists (file path or commit SHA) showing a content completeness assertion was run against real production records — not only synthetic fixtures — and passed with zero data loss
- [ ] **Content completeness verified**: the check verified field-by-field completeness, not only that output is structurally valid (loads without error)
- [ ] **Constrained field values enumerated**: all distinct values of constrained fields were enumerated from real data before migration and are all handled in the target model
- [ ] **Deletion deferred or confirmed**: if source files were deleted, deletion occurred after zero-data-loss confirmation

If any item is unconfirmed, emit:

```text
COMPLETION BLOCKED — Migration Fidelity Gate

Unconfirmed items:
- [list each unchecked item]

To unblock: run `uv run plugins/development-harness/scripts/verify_migration_fidelity.py`
against real production data and provide the path to the generated report in
`.tmp/scratch/reports/`. A passing report (zero data loss, all sections preserved) confirms
items 1 and 2. Alternatively, a commit SHA showing the completeness assertion was run on
real files is accepted.
```

Do NOT build the QG plan, dispatch T1, or apply any SAM state until all four items are confirmed.

If all confirmed → proceed to Artifact Discovery.

---

## Pre-Phase: Artifact Discovery

When the parent story issue number is known (from the plan's `issue` field or the backlog item), query the artifact manifest to discover all plan artifacts for this feature:

```text
mcp__plugin_dh_backlog__artifact_list(issue_number=N)
```

If the response contains artifacts, pass the manifest to quality gate agents (Phases 1-6) so they can access plan artifacts via `artifact_read` instead of filesystem paths. This is critical for worktree-isolated agents.

**Fallback**: If `artifact_list` returns an empty manifest or an error, quality gate agents use filesystem path conventions as before. This ensures backward compatibility with issues that predate the artifact manifest system.

---

## Pre-Phase 1b: Process Accumulated Concerns

Check the backlog item for a `## Concerns` section accumulated during `/implement-feature`:

```text
mcp__plugin_dh_backlog__backlog_view(selector="#{issue}")
```

If the item has a `## Concerns` section with unchecked items (`- [ ]`):

1. For each concern, verify whether it is a real issue:
   - Read the referenced file or run the referenced check
   - If verified: check it off (`- [x]`) and create a new backlog item via `mcp__plugin_dh_backlog__backlog_add` with the concern as the description, source as "Quality vigilance concern from #{issue}"
   - If not a real issue: check it off (`- [x] Not confirmed — {reason}`)
2. Update the concerns section via `mcp__plugin_dh_backlog__backlog_groom(selector="#{issue}", section="Concerns", content="{updated checklist}")`

If no concerns section exists, proceed to Phase 1.

---

## Quality Gate Plan Creation

After the pre-phases complete, set up the SAM-enforced quality gate plan for the 6 phases.

Extract `{slug}` from the task file path (`plan/P{NNN}-{slug}.yaml` — strip the `P{NNN}-` prefix and `.yaml` suffix).

### Step 1: Check for existing QG plan

```text
mcp__plugin_dh_sam__sam_list(search="qg-{slug}")
```

```mermaid
flowchart TD
    List["sam_list(search='qg-{slug}')"] --> Found{QG plan found?}
    Found -->|No| Create["Call build_quality_gate_plan,<br>then sam_create"]
    Found -->|Yes| Check{All tasks terminal?}
    Check -->|Yes — COMPLETE or SKIPPED| Skip["Skip to Completion Verification Gate"]
    Check -->|No — tasks remain| Reset["Reset BLOCKED tasks to NOT_STARTED,<br>resume SAM dispatch loop"]
    Create --> Loop["Enter SAM Dispatch Loop"]
    Reset --> Loop
```

### Step 2: Create QG plan (if not found)

If no QG plan exists, generate the 6-task plan YAML and create it via SAM:

```python
# Call the pure function (from sam_schema.core.quality_gates)
tasks_yaml = build_quality_gate_plan(
    slug="{slug}",
    issue="{issue_number}",       # from plan's issue field, if known
    impl_plan_address="P{N}",     # implementation plan address
)
```

Then create the plan:

```text
mcp__plugin_dh_sam__sam_create(
    slug="qg-{slug}",
    goal="Quality gate enforcement for {slug}",
    tasks_yaml="{tasks_yaml_string}",
    issue="{issue_number}"
)
```

The response contains the QG plan address (e.g., `QG003`). Store it as `{QG}` for use throughout the dispatch loop.

### Step 3: Reset BLOCKED tasks (on re-run)

If the QG plan already exists and has BLOCKED tasks, reset each to NOT_STARTED before entering the dispatch loop:

```text
For each task where status == "blocked":
    mcp__plugin_dh_sam__sam_state(plan="{QG}", task="{task_id}", status="not-started")
```

This allows re-running `complete-implementation` to resume from the blocked phase without re-executing completed phases.

---

## SAM Dispatch Loop (Phases 1-6)

The 6 quality gate phases are enforced via a SAM task loop. Each phase is a task in the QG plan. The dependency chain (T1 → T2 → T3 → T4 → T5 → T6) enforces ordered execution — a phase cannot start until the previous phase completes.

**Phase task mapping:**

| Task | Phase | Agent |
|------|-------|-------|
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

Repeat until `sam_ready` returns an empty list:

**1. Get next ready task:**

```text
mcp__plugin_dh_sam__sam_ready(plan="{QG}")
```

If the result is empty, exit the loop and proceed to Completion Verification Gate.

**2. Claim the task:**

```text
mcp__plugin_dh_sam__sam_claim(plan="{QG}", task="{task_id}")
```

If `"claimed": false`, stop — another agent is running this phase. Do not re-dispatch.

**3. Dispatch via start-task:**

```text
Skill(skill="start-task", args="plan/{QG}-qg-{slug}.yaml --task {task_id}")
```

Pass `team_name="{team_name}"` when spawning QG agents so they join the existing implementation team.

The SubagentStop hook marks the task COMPLETE after the sub-agent finishes.

**4. Phase-specific post-dispatch actions:**

After each dispatched phase completes, run the phase-specific processing before querying `sam_ready` again:

```mermaid
flowchart TD
    Done{Which task<br>just completed?}
    Done -->|T1 Code Review| T1Post["Extract follow-up task files<br>from code-reviewer ARTIFACTS output.<br>Store file paths for Step 4 of<br>Recursive Follow-up Handling."]
    Done -->|T4 Drift Audit| T4Post{Drift found<br>in T4 output?}
    T4Post -->|No drift| SkipT5["sam_state(plan='{QG}', task='T5', status='skipped')"]
    T4Post -->|Drift found| T5Ready["T5 remains NOT_STARTED — will be<br>dispatched on next loop iteration"]
    Done -->|T6 Context Refinement| T6Post["Check T6 agent output for<br>DIVERGENCE_REQUIRING_REVIEW block.<br>If present, store for final output."]
    Done -->|T2, T3, T5| Continue["No phase-specific action —<br>continue loop"]
    T1Post --> Continue
    SkipT5 --> Continue
    T5Ready --> Continue
    T6Post --> Continue
```

**Detecting drift in T4 output**: The doc-drift-auditor agent output contains a `## Findings` section. No drift found is indicated by a statement such as "No documentation drift detected" or an empty findings list. Presence of drift items (file paths, outdated sections) means drift was found.

---

## Completion Verification Gate

After the SAM dispatch loop exits (no ready tasks), verify all 6 phases reached terminal status before allowing label application.

```text
mcp__plugin_dh_sam__sam_status(plan="{QG}")
```

Examine each of the 6 tasks:

```mermaid
flowchart TD
    Status["sam_status(plan='{QG}')"] --> Iter["Iterate over all 6 tasks"]
    Iter --> Check{For each task:<br>check status}
    Check -->|"status == 'complete'"| PassTask["Task passes"]
    Check -->|"status == 'skipped' AND task_id == 'T5'"| PassTask
    Check -->|"status == 'skipped' AND task_id != 'T5'"| FailUnauth["FAIL — unauthorized skip"]
    Check -->|"status == 'not-started' OR 'in-progress'"| FailIncomplete["FAIL — incomplete phase"]
    Check -->|"status == 'blocked'"| FailBlocked["FAIL — blocked phase"]
    PassTask --> AllPassed{All 6 tasks<br>passed?}
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

After all six phases complete, route any follow-up task files created by Phase 1 (code-reviewer) to the backlog before deciding on recursion. This ensures no follow-up file is orphaned when the orchestrator skips recursion.

### Step 1: Detect Follow-up Files

Extract file paths from the `Task files:` list in the code-reviewer's ARTIFACTS output (the `STATUS: DONE` block from Phase 1).

If the `Task files:` list is empty or absent, search for follow-up plans via the SAM MCP:

```text
mcp__plugin_dh_sam__sam_list(search="{slug}-followup")
```

Where `{slug}` is extracted from the parent task file path (`plan/P{NNN}-{slug}.yaml` — strip `P{NNN}-` prefix and `.yaml` suffix).

If both ARTIFACTS and glob return empty: skip the entire routing section (no follow-ups to route).

**Error handling**: If a glob returns files from a different feature slug, filter results to only include files matching the parent task file's slug.

### Step 2: Search Backlog by Title Keywords

For each follow-up file, derive a search slug from the filename using this algorithm:

```text
Input:  plan/P008-data-validation-followup-1.yaml
Step 1: Strip directory prefix      --> P008-data-validation-followup-1.yaml
Step 2: Strip .yaml extension       --> P008-data-validation-followup-1
Step 3: Strip P{NNN}- prefix        --> data-validation-followup-1
Step 4: Strip -followup-{k} suffix  --> data-validation
Step 5: Replace hyphens with spaces --> data validation
Output: "data validation"
```

Search the backlog using a 2-strategy fallback chain. Strategy 3 (LLM semantic match) is
**explicitly excluded** from follow-up routing: follow-up filenames are machine-derived slugs,
not human semantic queries, so LLM semantic selection would have low fidelity against
human-authored backlog titles.

```mermaid
flowchart TD
    Derive["Derive slug from filename<br>(hyphens → spaces)"] --> S1["Strategy 1 — substring<br>backlog_list(title='{slug}')"]
    S1 --> R1{Results?}
    R1 -->|One or more matches| UseS1["Use Strategy 1 result"]
    R1 -->|Zero results| S2["Strategy 2 — filter-first<br>backlog_list(topic='{slug}')"]
    S2 --> R2{Results?}
    R2 -->|One or more matches| UseS2["Use Strategy 2 result"]
    R2 -->|Zero results| NoMatch["No match found<br>→ proceed to Step 4 (create new item)"]
    UseS1 --> Step4["Step 4: Link or Create"]
    UseS2 --> Step4
    NoMatch --> Step4
```

**Strategy 1 — substring via `title=`**

```text
mcp__plugin_dh_backlog__backlog_list(title="{derived_slug}")
```

Parse the JSON output. For each item, check if the derived slug appears (case-insensitive
substring match) in the item's `title` field. If one or more items match, use the first
match as the result and skip Strategy 2.

**Strategy 2 — filter-first via `topic=`**

If Strategy 1 returns zero matches, run:

```text
mcp__plugin_dh_backlog__backlog_list(topic="{derived_slug}")
```

The `topic` parameter performs a case-insensitive substring match against `metadata.topic`.
Follow-up slugs often correspond to the topic area recorded in backlog item metadata, making
this an effective second-pass filter when title substring fails.

If Strategy 2 returns one or more items, use the first match.

If both strategies return zero results, treat as "no match found" and proceed to Step 4.

**Error handling**: If either `mcp__plugin_dh_backlog__backlog_list` call fails, log the error, skip
that strategy, and continue to the next strategy (or to Step 4 as "no match found" if all
strategies fail). If the follow-up filename does not match the expected
`P{NNN}-{slug}-followup-{k}.yaml` pattern, log a warning and use the full filename (without
directory prefix and `.yaml` extension) as the derived slug.

### Step 3: Classify Follow-up Findings

For each follow-up file, read its `## Scope` field:

- If `## Scope` is absent: default to **in-scope** and emit:
  `WARNING: No ## Scope section in {followup_path}. Defaulting to in-scope.`
- If `## Scope: out-of-scope`: route immediately to backlog via `backlog_add` and
  continue to the next follow-up. Do NOT proceed to Step 4 for this follow-up.

```mermaid
flowchart TD
    Q{"Does the finding touch<br>the same design goals/intent/outcomes<br>as the current task?"}
    Q -->|"Yes — linting, tests, docs,<br>same design outcomes"| InScope["IN-SCOPE<br>Proceed to Step 4"]
    Q -->|"No — separate system/domain<br>OR perceived impact warrants<br>own grooming and research"| OutScope["OUT-OF-SCOPE<br>Route to backlog via backlog_add<br>Continue to next follow-up"]
```

Out-of-scope backlog_add call pattern:

```text
backlog_add(
    title="{derived_title}",
    body="Quality gate follow-up from #{issue_number}",
    labels=["type:task"],
    source="Quality gate follow-up from #{issue_number} — out-of-scope: {followup_path}"
)
```

Output: `Out-of-scope finding routed to backlog: {title}`

### Step 4: Link or Create Backlog Item

Based on Step 2 result, for each follow-up file:

**Match found** -- attach follow-up as plan to the existing backlog item:

```text
mcp__plugin_dh_backlog__backlog_update(selector="{matched_item_title}", plan="{followup_file_path}")
```

**No match found** -- create a new backlog item, then attach the follow-up as plan:

```text
Skill(skill: "dh:create-backlog-item", args: "--auto {derived_title}")
```

Then attach the follow-up file as the plan:

```text
mcp__plugin_dh_backlog__backlog_update(selector="{derived_title}", plan="{followup_file_path}")
```

**Error handling**:

- If `mcp__plugin_dh_backlog__backlog_update` fails after creation (title mismatch between what `dh:create-backlog-item` produced and what `update` searched for): re-invoke `mcp__plugin_dh_backlog__backlog_list()`, find the most recently added item, and retry `mcp__plugin_dh_backlog__backlog_update` with its exact title. If the retry also fails, log the error and continue to the next follow-up file.
- If `dh:create-backlog-item --auto` logs `[AUTO] STOP -- duplicate detected`: treat this as "match found" -- run `mcp__plugin_dh_backlog__backlog_update` on the duplicate's title to attach the plan.

### Step 5: Recursion Gate

### Guard 1: Depth check

Before evaluating conditions, check the recursion counter:

```text
If {recursion_depth} >= DH_RECURSIVE_REVIEW_TASK_DEPTH (5):

  Output:
  RECURSION DEPTH LIMIT REACHED — Systemic Design Issue Detected
  Follow-up task: {followup_task_file_path}
  Depth: {recursion_depth} (limit: {DH_RECURSIVE_REVIEW_TASK_DEPTH})

  For all remaining in-scope follow-ups (including this one):
    backlog_add(
        title="{derived_title}",
        body="Depth limit exceeded — review cycle stopped at depth {recursion_depth}",
        labels=["type:task"],
        source="Depth limit exceeded on #{issue_number} at depth {recursion_depth}"
    )

  Stop recursion. Proceed to the Apply status:verified Label step.
```

If `{recursion_depth}` < 5: continue to Guard 2.

### Guard 2: RT-ICA BLOCKED check

Check whether the follow-up's underlying planner-rt-ica output contains the BLOCKED signal.
The signal is the string `BLOCKED-FOR-PLANNING` in the planner-rt-ica output artifact
(NOT in implement-feature's direct output — implement-feature emits no BLOCKED signal).

To check: read the plan artifact linked to the follow-up's backlog item and search for
`BLOCKED-FOR-PLANNING`.

```text
If the planner-rt-ica artifact for this follow-up contains BLOCKED-FOR-PLANNING:

  Output:
  RECURSION STOPPED — RT-ICA BLOCKED
  Follow-up task: {followup_task_file_path}
  Depth: {recursion_depth}
  Blocking conditions: {blocking_conditions_from_artifact}
  Resume: /dh:work-backlog-item {followup_backlog_item_title}

  Stop for this follow-up. Continue to next follow-up if any remain.
  Do not apply status:verified label for the blocked follow-up.
```

If no BLOCKED-FOR-PLANNING signal: continue to Condition 1 (ADR-3).

**Evaluation order for each in-scope follow-up:**
1. Guard 1: depth check (`{recursion_depth} >= 5` → stop all)
2. Guard 2: RT-ICA BLOCKED check (`BLOCKED-FOR-PLANNING` in plan artifact → stop this follow-up)
3. Condition 1 (ADR-3): slug match
4. Condition 2 (ADR-2): High priority
5. Both Conditions 1 and 2 met → increment depth, recurse
6. Either not met → defer to backlog

For each follow-up file, evaluate two conditions. BOTH must be true for recursion.

**Condition 1 -- Same session scope (ADR-3)**: The follow-up file's slug matches the parent task file's slug. Extract the slug from each filename: strip the `P{NNN}-` prefix, then strip `-followup-{k}.yaml` for the follow-up or `.yaml` for the parent. Compare the two slugs.

**Condition 2 -- High priority (ADR-2)**: Read the follow-up file content and extract the `## Priority` section. Only `High` qualifies for immediate recursion.

**If BOTH conditions are met** -- recurse immediately:

Increment {recursion_depth} by 1 before invoking implement-feature.

```text
Skill(skill="implement-feature", args="{followup_task_file_path}")
```

Then re-run `complete-implementation` on the follow-up task file.

**If EITHER condition is NOT met** -- defer to backlog:

Log the deferral and output this line to the user:

```text
Follow-up deferred — to resume: /dh:work-backlog-item <title>
```

Where `<title>` is the backlog item title the follow-up was linked to in Step 3.

Do not recurse. The follow-up is tracked in the backlog.

**Error handling**: If the follow-up file has no `## Priority` section, default to `Medium` (defer). Log: `No priority found in {followup_path}, defaulting to Medium (deferred).`

---

## Apply status:verified Label

After all six phases and follow-up routing complete, apply the `status:verified` GitHub label to the parent backlog issue. This records durable completion evidence that `/dh:work-backlog-item resolve` requires before closing a SAM item.

### Step 1: Locate the backlog item

Derive the search slug from the task file path (same algorithm as Recursive Follow-up Handling):

```text
plan/P003-integrate-sam-schema.yaml → slug: integrate-sam-schema
```

Search the backlog:

```text
mcp__plugin_dh_backlog__backlog_list(title="{slug}")
```

If zero items match, skip this section — there is no issue to label.

### Step 2: Apply the label

Call:

```text
mcp__plugin_dh_backlog__backlog_update(selector="{matched_item_title}", verified=True)
```

**Error handling**: If the call returns an `error` key, output:

```text
COMPLETION BLOCKED — status:verified label could not be applied.

Error: {error}
Backlog item: {matched_item_title}

Fix the error (check GitHub token, repo access), then re-run /complete-implementation.
```

Stop. Do not proceed to the Final Step commit.

On success, continue to the Final Step.

---

## Final Step: Commit and Push Remaining Changes

After all phases and follow-up routing are complete, check for uncommitted changes. Phases 1-6 and the Recursive Follow-up Handling steps modify files (task file context manifests, backlog item files, plan annotations). Commit any remaining modifications in a single commit and push to the current branch.

```bash
git status
```

If there are staged or unstaged changes: stage the modified files and commit.

**Issue number in commit message**: Before committing, check the backlog item for the current feature slug:

```text
mcp__plugin_dh_backlog__backlog_list(title="{slug}")
```

Check the `issue` field on the matching item. If present and this commit resolves that issue, append `Fixes #NNN` to the commit message body (where NNN is the issue number). If no issue number is found, omit it.

Push after committing. If the working tree is clean, skip this step.

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

## Final Handoff Output

After the commit+push step, output this block to the user:

Call `mcp__plugin_dh_backlog__backlog_list()` and find the highest-priority open item whose
title contains the current feature slug. Check the `plan` field on that item.

```text
If item found AND item.plan is set (non-empty):
  Clear context and run:
    /dh:implement-feature {item.plan}

If item found AND item.plan is NOT set:
  Clear context and run:
    /dh:work-backlog-item {item.title}

If no item found:
  Clear context and run:
    /dh:work-backlog-item — nothing queued —
```
