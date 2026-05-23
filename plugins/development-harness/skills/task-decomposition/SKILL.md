---
name: task-decomposition
description: Decomposes a contextualized plan into atomic, independently executable task files with complete embedded context. Use after SAM Stage 3 Context Integration produces the contextualized plan artifact — when the plan is ready for TASK file generation with CLEAR ordering, CoVe checks, and dependency graphs for parallel execution.
user-invocable: false
---

# SAM Stage 4 — Task Decomposition

## Role

You are the task decomposition agent for the SAM pipeline. You break a
contextualized plan into atomic tasks that can each be executed by a fresh,
stateless agent with zero prior context.

## When to Use

- After Stage 3 Context Integration produces a contextualized ARTIFACT:PLAN
- Before Stage 5 Execution dispatches tasks to agents
- When a plan needs to be split into parallelizable work units

## Process

```mermaid
flowchart TD
    Start([Contextualized ARTIFACT:PLAN]) --> A1[1. Identify atomic work units]
    A1 --> A2[2. Embed complete context per task]
    A2 --> A3[3. Apply CLEAR ordering]
    A3 --> A4{Accuracy risk medium/high?}
    A4 -->|Yes| CoVe[4a. Add CoVe checks]
    A4 -->|No| A5[4b. Skip CoVe]
    CoVe --> A5[5. Map dependencies]
    A5 --> A6[6. Assign roles]
    A6 --> Gate{Evaluate complexity}
    Gate -->|Manageable| Done([ARTIFACT:TASK files])
    Gate -->|High complexity or novel architecture| Escalate([Human touchpoint — confirm decomposition])
```

### Step 1 — Identify Atomic Work Units

Each task must be:

- **Atomic** — completes one logical change; cannot be meaningfully subdivided
- **Independent** — executable without asking clarifying questions
- **Verifiable** — has acceptance criteria provable by the executing agent
- **Bounded** — clear scope boundaries (what is in, what is out)

Split along natural seams:

- One file or tightly coupled file set per task
- One logical concern per task (do not mix creation with testing)
- Separate infrastructure changes from application logic

### Step 2 — Embed Complete Context

Each task file IS the complete prompt. The executing agent has NO memory of
previous stages. Embed everything needed:

- Relevant excerpts from ARTIFACT:PLAN (not "see plan" — inline it)
- File paths and line ranges from contextualization
- Patterns to follow (from resource map)
- Integration points to connect to
- Constraints and anti-goals that apply to this specific task

### Step 3 — Apply CLEAR Ordering

Follow the CLEAR task structure standard. Sections in order:

1. **Context** — what exists, what is changing, why
2. **Objective** — one-sentence definition of success
3. **Inputs** — files, artifacts, assumptions (with confirmation method)
4. **Requirements** — what the agent must do
5. **Constraints** — what the agent must not do
6. **Outputs** — files created or modified, artifacts produced
7. **Acceptance Criteria** — specific, measurable, verifiable
8. **Verification** — commands or procedures to prove completion
9. **Handoff** — what to report back

For full CLEAR + CoVe specification, reference `/dh:clear-cove-task-design`.

### Step 4 — Add CoVe Checks (Conditional)

Add Chain of Verification checks ONLY when accuracy risk is medium or high:

- Task depends on multiple independent facts
- Incorrect output would break builds or mislead downstream tasks
- Versions, API behavior, or standards matter
- Task involves claims that must be verified against sources

### Step 5 — Map Dependencies

Build the dependency graph:

- Identify which tasks must complete before others can start
- Identify which tasks can run in parallel (no shared file conflicts)
- Document WHY parallelization is safe for each parallel group

### Step 6 — Assign Roles

Assign abstract roles, NOT specific agents:

- `architect` — design decisions, structural changes
- `implementer` — write production code
- `test-designer` — write tests and fixtures
- `code-reviewer` — review and quality assessment
- `docs-writer` — documentation and comments

Role-to-agent resolution happens at execution time via the language manifest.

## Input

Retrieve the contextualized plan via MCP:

```text
artifact_read(item_id={issue}, artifact_type="architect")
```

Returns `{type, path, content, status, messages, warnings}`. The `content`
field contains the full contextualized ARTIFACT:PLAN markdown.

## Output

### Choosing a plan-creation path

| Plan size | Preferred path |
|-----------|----------------|
| Small (fewer than 16 tasks) | Monolithic — single `sam_plan create` call |
| Large (16+ tasks) | Incremental — `create` → N × `append_task` → `finalize` |

#### Monolithic path (small plans)

```text
sam_plan(config={"action": "create", "slug": "{feature-slug}", "goal": "{plan goal}", "tasks": [{task_dict}, ...], "issue": {issue_number}})
```

`tasks` is a list of task definition objects. Required fields: `id` (str), `title` (str). Optional: `status`, `agent`, `dependencies`, `priority`, `complexity`.

Passing `issue={issue_number}` auto-registers the task plan as
`artifact_type="task-plan"` in the artifact system, making it accessible
to worktree-isolated agents via `sam_task(action='read')`.

#### Incremental path (large plans — preferred when 16+ tasks)

Use three calls to avoid large single-call payloads:

1. Create a drafting plan (empty tasks list enters `state="drafting"`):

   ```text
   sam_plan(config={"action": "create", "slug": "{feature-slug}", "goal": "{plan goal}", "tasks": [], "issue": {issue_number}})
   ```

   The response includes the assigned plan number `P{N}`. While `state="drafting"`,
   `sam_plan status` and `sam_plan ready` return a drafting marker instead of task
   counts — the plan is not visible to the dispatch loop.

2. Append each task one at a time (repeat for every task):

   ```text
   sam_plan(plan="P{N}", config={"action": "append_task", "task": {single_task_dict}})
   ```

3. Finalize — clears `state="drafting"` and makes the plan ready for dispatch:

   ```text
   sam_plan(plan="P{N}", config={"action": "finalize"})
   ```

**Single-writer constraint**: `append_task` is NOT safe under concurrent writers. Do not
call `append_task` for the same plan from multiple agents or sessions simultaneously. For
the full single-writer contract, see the `CLAUDE.md` gotcha note in
`plugins/development-harness/CLAUDE.md`.

Each file contains YAML frontmatter followed by CLEAR-ordered sections:

```markdown
---
task: TASK-001
title: <descriptive imperative title>
status: not-started
role: <architect / implementer / test-designer / code-reviewer / docs-writer>
dependencies: []
priority: <1-5 based on dependency depth>
complexity: <low / medium / high>
accuracy-risk: <low / medium / high>
parallelize-with: []
parallel-rationale: <why parallelization is safe>
---

## Context

<embedded context from plan — NOT "see PLAN.md">

## Objective

<one sentence>

## Required Inputs

- <files to read with paths>
- <assumptions and how to confirm>

## Requirements

1. <must do>

## Constraints

- <must not do>
- <scope boundary>

## Expected Outputs

- <file paths created/modified>

## Acceptance Criteria

1. <verifiable criterion>

## Verification Steps

1. <command or procedure>
N. (When Expected Outputs lists file paths) Run: `git add <file1> [file2 ...]` then
   `git commit -m "<type>(<scope>): <task title>"` — scope is the primary affected module or
   directory (required by repo commit-msg hook); use files from Expected Outputs only, no
   `git add .` or `git add -A`, no `Fixes #N` / `Closes #N` / `Resolves #N` trailer.

## CoVe Checks (only if accuracy-risk is medium/high)

- Key claims to verify — <claim>
- Verification questions — <falsifiable question>
- Evidence to collect — <commands, docs, code pointers>

## Handoff

- Summary of changes
- Evidence from verification steps
- Anything blocked and what is needed
```

## Human Touchpoint Gate

After decomposition, evaluate whether escalation is needed:

```mermaid
flowchart TD
    Tasks([Task files generated]) --> Q1{Novel architecture pattern?}
    Q1 -->|Yes| Escalate[Present to user for confirmation]
    Q1 -->|No| Q2{High complexity tasks > 40% of total?}
    Q2 -->|Yes| Escalate
    Q2 -->|No| Q3{Circular or unclear dependencies?}
    Q3 -->|Yes| Escalate
    Q3 -->|No| Done([Proceed to Stage 5])
    Escalate --> Revise[User adjusts — regenerate affected tasks]
    Revise --> Done
```

## Behavioral Rules

- Every task must be self-contained — an agent reading ONLY the task file can execute it
- Never reference PLAN.md or DISCOVERY.md by "see X" — inline the relevant content
- Never assign specific agent names — use roles
- Tasks must not have circular dependencies
- Each acceptance criterion must be verifiable by the executing agent alone

## Success Criteria

- Each task is independently executable without clarifying questions
- Every plan component maps to at least one task
- Dependency graph has no cycles
- Parallel groups have no shared file conflicts
- Roles assigned (not agents) for every task
- CoVe checks present on medium/high accuracy-risk tasks only
