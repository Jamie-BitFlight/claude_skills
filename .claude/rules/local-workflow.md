# SAM Feature Implementation Workflow

The SAM (Structured Agent-Managed) workflow converts a feature idea into executable task files, implements them via agent delegation, and validates the result through quality gates.

## Workflow Overview

```text
/add-new-feature  ──>  /implement-feature  ──>  /complete-implementation
   (planning)            (execution loop)         (quality gates)
```

## Skills (User-Invocable)

| Skill | Source File | Purpose |
|-------|------------|---------|
| `/add-new-feature` | [.claude/skills/add-new-feature/SKILL.md](./../skills/add-new-feature/SKILL.md) | Plan a feature: discovery, analysis, architecture, task decomposition |
| `/implement-feature` | [.claude/skills/implement-feature/SKILL.md](./../skills/implement-feature/SKILL.md) | Execute tasks from a SAM task file via agent delegation loop |
| `/start-task` | [.claude/skills/start-task/SKILL.md](./../skills/start-task/SKILL.md) | Start or complete a specific task inside a SAM task file |
| `/complete-implementation` | [.claude/skills/complete-implementation/SKILL.md](./../skills/complete-implementation/SKILL.md) | Quality gates after all tasks are COMPLETE |
| `/implementation-manager` | [.claude/skills/implementation-manager/SKILL.md](./../skills/implementation-manager/SKILL.md) | Query task status (not user-invocable, used by orchestrator) |

Plugin-level source copies exist at `plugins/python3-development/skills/development/` for each skill.

---

## Phase 1: Planning (`/add-new-feature`)

Converts a feature description into durable SAM artifacts.

### Artifacts Produced

| Artifact | Path | Created By | Artifact Type |
|----------|------|------------|---------------|
| Feature context | `plan/feature-context-{slug}.md` | `feature-researcher` agent | Generated |
| Codebase analysis | `plan/codebase/{FOCUS}.md` | `codebase-analyzer` agent (optional) | Generated (snapshot) |
| Architecture spec | `plan/architect-{slug}.md` | `python-cli-design-spec` agent | Generated |
| Task plan | `plan/tasks-{N}-{slug}.md` | `swarm-task-planner` agent | Generated |

### Agent Delegation Sequence

```text
Phase 1: feature-researcher        -> plan/feature-context-{slug}.md
Phase 2: codebase-analyzer          -> plan/codebase/{FOCUS}.md (optional)
Phase 3: python-cli-design-spec     -> plan/architect-{slug}.md
Phase 4: swarm-task-planner          -> plan/tasks-{N}-{slug}.md
Phase 5: plan-validator              -> PASS/BLOCKED gate
Phase 6: context-gathering           -> Context Manifest section in task file
```

When `acceptance-criteria-structured` is non-empty, `swarm-task-planner` also generates two bookend tasks: `T0` (baseline capture, Priority 1) and `T99`/`T{max+1}` (verification gate, Priority 5). See the "Bookend Tasks" section in Phase 2 below.

### Agent File Locations

| Agent | python3-development | development-harness |
|-------|-------------------|-------------------|
| `feature-researcher` | [plugins/python3-development/agents/feature-researcher.md](./../../plugins/python3-development/agents/feature-researcher.md) | [plugins/development-harness/agents/feature-researcher.md](./../../plugins/development-harness/agents/feature-researcher.md) |
| `codebase-analyzer` | [plugins/python3-development/agents/codebase-analyzer.md](./../../plugins/python3-development/agents/codebase-analyzer.md) | [plugins/development-harness/agents/codebase-analyzer.md](./../../plugins/development-harness/agents/codebase-analyzer.md) |
| `python-cli-design-spec` | [plugins/python3-development/agents/python-cli-design-spec.md](./../../plugins/python3-development/agents/python-cli-design-spec.md) | — |
| `swarm-task-planner` | [plugins/python3-development/agents/swarm-task-planner.md](./../../plugins/python3-development/agents/swarm-task-planner.md) | [plugins/development-harness/agents/swarm-task-planner.md](./../../plugins/development-harness/agents/swarm-task-planner.md) |
| `plan-validator` | [plugins/python3-development/agents/plan-validator.md](./../../plugins/python3-development/agents/plan-validator.md) | [plugins/development-harness/agents/plan-validator.md](./../../plugins/development-harness/agents/plan-validator.md) |
| `context-gathering` | [plugins/python3-development/agents/context-gathering.md](./../../plugins/python3-development/agents/context-gathering.md) | [plugins/development-harness/agents/context-gathering.md](./../../plugins/development-harness/agents/context-gathering.md) |
| `t0-baseline-capture` | [plugins/python3-development/agents/t0-baseline-capture.md](./../../plugins/python3-development/agents/t0-baseline-capture.md) | — |
| `tn-verification-gate` | [plugins/python3-development/agents/tn-verification-gate.md](./../../plugins/python3-development/agents/tn-verification-gate.md) | — |

### Task File Format

Each task in the plan file follows the format documented in [.claude/docs/TASK_FILE_FORMAT.md](./../docs/TASK_FILE_FORMAT.md). Key fields per task:

- `**Status**`: NOT STARTED | IN PROGRESS | COMPLETE | BLOCKED
- `**Dependencies**`: Task references (e.g., "Task 1.1, Task 1.2")
- `**Priority**`: 1-5 (1=critical)
- `**Complexity**`: Low | Medium | High
- `**Agent**`: Agent name to execute the task
- `**Skills**`: List of skill names for the sub-agent to load (e.g., `["fastmcp-python-tests", "python3-development"]`)
- `**Started**`: ISO timestamp (added by agent)
- `**Completed**`: ISO timestamp (added by hook)
- `**LastActivity**`: ISO timestamp (updated by hook)

Two formats are supported:

- **Legacy markdown**: Monolithic file with `## Task {ID}: {Name}` headers
- **YAML frontmatter**: Individual `.md` files with `---` delimited metadata per task

Two organizational structures:

- **Single file**: All tasks in one `plan/tasks-{N}-{slug}.md`
- **Directory**: One task per `.md` file in a `plan/tasks-{slug}/` directory

### Outcome

The user receives the feature slug, task file path, and is told to run `/implement-feature`.

---

## Plan Artifact Lifecycle

Plan artifacts fall into two categories based on their origin and mutability.

- **Human-decision artifacts** (backlog items, grooming output, interview transcripts) capture the human's original intent and are immutable. Agents must never modify them.
- **Generated artifacts** (feature context, architecture spec, task plan, codebase analysis) are produced by agents during planning phases. They are mutable but intent-bound: updates must stay within the intent established by the human-decision artifacts they serve.

For the full taxonomy, classification rules, divergence thresholds, and annotation format, see
[Plan Artifact Lifecycle Policy](./../docs/plan-artifact-lifecycle.md).

| Artifact Type | Mutability Rule |
|---------------|-----------------|
| Human-decision | Immutable. No agent may edit, append to, or rewrite. |
| Generated | Mutable but intent-bound. Annotations permitted; silent rewrites prohibited. |

Divergence between plan artifacts and implementation is detected during Phase 6 of `/complete-implementation`, where the `context-refinement` agent performs a plan artifact freshness check. Design refinements are auto-recorded as annotations. Intent divergences are flagged for human review via `DIVERGENCE_REQUIRING_REVIEW` in the agent's output.

---

## Phase 2: Execution (`/implement-feature`)

Loops through ready tasks, delegates each to its specified agent, and relies on hooks for status tracking.

### Hook Configuration

Declared in `/implement-feature` SKILL.md frontmatter:

```yaml
hooks:
  SubagentStop:
  - hooks:
    - type: command
      command: python3 "./plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py"
```

### Execution Loop

```text
1. Query status:
   uv run sam status P{N}

2. Query ready tasks:
   If parent story issue number is known, prefer the MCP tool:
     backlog_get_ready_sam_tasks(parent_issue_number=N)
     Output shape: {"feature": "...", "ready_tasks": [...], "count": N}
     Falls back to local cache if GitHub unavailable.
   If parent issue number is unknown (or MCP unavailable), use CLI fallback:
     uv run sam ready P{N}
   With GitHub flag (when parent issue is known but MCP unavailable):
     uv run sam ready P{N} --github --parent-issue N

3. For each ready task:
   Route to the agent named in the task's **Agent** field.
   If the task's `skills` list (from ready JSON) is non-empty,
   include skill-loading instructions in the delegation prompt:
     For each skill, instruct the sub-agent to call Skill(skill="{skill-name}").
   Launch the agent with:
     Skill(skill="start-task", args="{task_file_path} --task {task_id}")

4. Repeat until no tasks remain ready.

5. When all tasks COMPLETE:
   Skill(skill="complete-implementation", args="{task_file_path}")
```

### Bookend Tasks

When a plan contains `acceptance-criteria-structured` entries, `swarm-task-planner` generates two bookend tasks:

- **T0** (`t0-baseline-capture`, Priority 1, `dependencies: []`): Dispatched first by natural readiness — no dependencies and highest priority. Runs each `check_command` and records exit codes, stdout, and stderr to `plan/T0-baseline-{slug}.yaml`. Non-zero exits are expected and do not fail T0.
- **T99** / **T{max+1}** (`tn-verification-gate`, Priority 5, `dependencies: [all non-bookend task IDs]`): Dispatched last after all implementation tasks complete. Reads the T0 baseline YAML, re-runs each `check_command`, and classifies each criterion using the 4-cell matrix (passed / regressed / pre-existing-fail / newly-passing). Writes `plan/TN-verification-{slug}.yaml` as a list of per-criterion `BookendVerification` records — one per criterion, each with `criterion_id`, `check_command`, `t0_exit_code`, `tn_exit_code`, `status`, and `stdout_diff_summary`. There is no top-level `verdict` field; `/complete-implementation` aggregates the verdict by scanning all records for `status: regressed` before Phase 1.

No changes to the execution loop are needed — existing `DependencyGraph.get_ready_tasks()` handles T0/TN ordering automatically.

### Readiness Logic

A task is "ready" when:

1. Status is `NOT STARTED`
2. All dependency tasks have status `COMPLETE`

Readiness evaluation is performed by the `sam` CLI via `uv run sam ready P{N}` or the MCP tool `backlog_get_ready_sam_tasks`.

---

## Phase 2a: Task Execution (`/start-task`)

Invoked per-task by `/implement-feature`. Runs inside a sub-agent delegated to the task's specified agent type.

### Hook Configuration

Declared in `/start-task` SKILL.md frontmatter:

```yaml
hooks:
  PostToolUse:
  - matcher: Write|Edit|Bash
    hooks:
    - type: command
      command: python3 "./plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py"
```

### Actions

1. Read the task file and linked architecture spec.
2. Select the target task (by `--task {id}` or first ready task).
2a. Load skills from task metadata: read the `skills:` field from YAML frontmatter (or `**Skills**:` from legacy format). For each skill name, invoke `Skill(skill="{name}")`. If a skill fails to load, warn and continue with remaining skills. This is intentional redundancy with the orchestrator's skill-loading instructions, ensuring skills load even when the task is started manually or by an older orchestrator.
3. Claim the task via `claim-task` command (prevents duplicate dispatch). This is the ONLY permitted way to mark a task in-progress — do NOT edit status or started fields directly. Run `uv run sam claim P{N} {task_id}`; stop if exit code is non-zero (task already claimed or not found).
4. GitHub in-progress sync: if `parent_issue_number` is known and `github_issue` field is set in the task YAML, sync in-progress status to GitHub sub-issue (non-fatal on failure).
5. Write active-task context file:

   ```text
   .claude/context/active-task-{CLAUDE_SESSION_ID}.json
   ```

   Contents: `{"task_file_path": "...", "task_id": "...", "parent_issue_number": N}` — omit `parent_issue_number` if story issue number is unknown; hook treats absence as `None` and skips GitHub sync.

6. Divergence notes: if implementation deviates from the architect spec or feature-context in a way that affects observable behavior, append a `## Divergence Notes` section to the task file. See `.claude/skills/start-task/SKILL.md` for format.
7. Implement against acceptance criteria and run verification steps.

### Completion Marking

Two paths:

- **`--complete {task-id}` argument**: Agent explicitly marks task COMPLETE
- **SubagentStop hook** (on `/implement-feature`): When the sub-agent finishes, the hook script automatically marks the task COMPLETE and adds `**Completed**: {ISO timestamp}`

---

## Hook Script: task_status_hook.py

Script: [plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py](./../../plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py)

Shared utilities: [plugins/python3-development/skills/implementation-manager/scripts/task_format.py](./../../plugins/python3-development/skills/implementation-manager/scripts/task_format.py)

### Event Handling

| Hook Event | Trigger Context | Action |
|------------|----------------|--------|
| `SubagentStop` | `/implement-feature` finishes a sub-agent | Parse prompt for `/start-task` invocation, extract task file path and task ID, set status to COMPLETE, add `Completed` timestamp, delete context file, then call `sync_completion_to_github()` to sync completion to GitHub sub-issue (best-effort, exit 0 on failure) |
| `PostToolUse` (Write\|Edit\|Bash) | `/start-task` during task execution | Read `.claude/context/active-task-{session_id}.json`, update `LastActivity` timestamp in the task section |

### Timestamp Responsibilities

| Field | Written By | When |
|-------|-----------|------|
| `**Started**` | Agent (via `/start-task` skill logic) | When agent begins work on a task |
| `**Completed**` | Hook (`SubagentStop` in `task_status_hook.py`) | When sub-agent finishes |
| `**LastActivity**` | Hook (`PostToolUse` in `task_status_hook.py`) | On each Write, Edit, or Bash call during task execution |

---

## Phase 3: Quality Gates (`/complete-implementation`)

Invoked automatically by `/implement-feature` when all tasks show COMPLETE. Runs six validation phases.

### Phase Sequence

```text
Phase 1: code-reviewer          -> Code review of implemented changes
Phase 2: feature-verifier       -> Goal-backward feature verification
Phase 3: integration-checker    -> Integration check
Phase 4: doc-drift-auditor      -> Documentation drift audit (read-only)
Phase 5: service-docs-maintainer -> Documentation update (if drift found)
Phase 6: context-refinement     -> Update task file Context Manifest + plan artifact freshness check
Final:   commit + push          -> Stage and commit all remaining modified files
```

### Agent File Locations

| Agent | python3-development | development-harness |
|-------|-------------------|-------------------|
| `code-reviewer` | [plugins/python3-development/agents/code-reviewer.md](./../../plugins/python3-development/agents/code-reviewer.md) | — |
| `feature-verifier` | [plugins/python3-development/agents/feature-verifier.md](./../../plugins/python3-development/agents/feature-verifier.md) | [plugins/development-harness/agents/feature-verifier.md](./../../plugins/development-harness/agents/feature-verifier.md) |
| `integration-checker` | [plugins/python3-development/agents/integration-checker.md](./../../plugins/python3-development/agents/integration-checker.md) | [plugins/development-harness/agents/integration-checker.md](./../../plugins/development-harness/agents/integration-checker.md) |
| `doc-drift-auditor` | [plugins/python3-development/agents/doc-drift-auditor.md](./../../plugins/python3-development/agents/doc-drift-auditor.md) | [plugins/development-harness/agents/doc-drift-auditor.md](./../../plugins/development-harness/agents/doc-drift-auditor.md) |
| `service-docs-maintainer` | — | [plugins/development-harness/agents/service-docs-maintainer.md](./../../plugins/development-harness/agents/service-docs-maintainer.md) |
| `context-refinement` | [plugins/python3-development/agents/context-refinement.md](./../../plugins/python3-development/agents/context-refinement.md) | [plugins/development-harness/agents/context-refinement.md](./../../plugins/development-harness/agents/context-refinement.md) |
| `t0-baseline-capture` | [plugins/python3-development/agents/t0-baseline-capture.md](./../../plugins/python3-development/agents/t0-baseline-capture.md) | — |
| `tn-verification-gate` | [plugins/python3-development/agents/tn-verification-gate.md](./../../plugins/python3-development/agents/tn-verification-gate.md) | — |

### Cross-Plugin Dependency

`service-docs-maintainer` exists only in the `development-harness` plugin, not in `python3-development`. This is the only agent in the workflow with a single-plugin source.

### Recursive Follow-up

If Phase 1 (code review) creates follow-up task files (naming: `plan/tasks-{N}-{slug}-followup-{k}.md`), each follow-up is routed through a backlog-linking step before any recursion decision:

1. Follow-up files are detected from the code-reviewer's ARTIFACTS `Task files:` output. If the list is empty or absent, a confirmatory glob for `plan/tasks-*-{slug}-followup-*.md` is run as fallback.
2. For each follow-up, a search title is derived from the filename (strip prefix/suffix, convert hyphens to spaces) and searched against existing backlog items via `mcp__backlog__backlog_list`.
3. If a matching backlog item is found, the follow-up is attached as its plan via `mcp__backlog__backlog_update` with `plan=` parameter.
4. If no match is found, a new backlog item is created via `create-backlog-item --auto`, then the follow-up is attached via `mcp__backlog__backlog_update` with `plan=` parameter.
5. Recursion proceeds only when BOTH conditions are true: the follow-up file's feature slug matches the parent task file's slug (same session scope), AND the follow-up's `## Priority` section contains `High`.
6. Otherwise, the follow-up is deferred to backlog with no recursion. The follow-up path, backlog item title, priority, and scope match result are logged.

---

## CLI Tool: sam

The `sam` CLI is the canonical interface for all SAM task file operations. Use `uv run sam <command>` to query and update plan state.

### Commands

| Command | Usage | Output |
|---------|-------|--------|
| `list` | `uv run sam list` | JSON: `{features: [...], count: N}` |
| `status` | `uv run sam status P{N}` | JSON: task counts, ready tasks, all tasks with details |
| `ready` | `uv run sam ready P{N}` | JSON: `{ready_tasks: [...], count: N}` |
| `read` | `uv run sam read P{N} --format json` | JSON: full plan with task fields and context |
| `claim` | `uv run sam claim P{N} {task_id}` | Claims task in-progress; exits non-zero if already claimed |
| `update` | `uv run sam update P{N} --context "..."` | Updates plan context field |

---

## Supporting Scripts

| Script | Path | Purpose |
|--------|------|---------|
| `sam` CLI | `uv run sam` | Canonical interface for all task file I/O (status, ready, read, claim, update) |
| `task_status_hook.py` | [plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py](./../../plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py) | Hook script for automatic status/timestamp updates |
| `task_format.py` | [plugins/python3-development/skills/implementation-manager/scripts/task_format.py](./../../plugins/python3-development/skills/implementation-manager/scripts/task_format.py) | Shared YAML frontmatter utilities (internal to sam_schema) |
| `get_task_context.py` | [plugins/python3-development/skills/implementation-manager/scripts/get_task_context.py](./../../plugins/python3-development/skills/implementation-manager/scripts/get_task_context.py) | Dynamic context injection for implementation-manager skill |
| `split_task_file.py` | [plugins/python3-development/scripts/split_task_file.py](./../../plugins/python3-development/scripts/split_task_file.py) | Split monolithic task files into individual files |
| `migrate_task_format.py` | [plugins/python3-development/scripts/migrate_task_format.py](./../../plugins/python3-development/scripts/migrate_task_format.py) | Migrate legacy markdown to YAML frontmatter format |

---

## Runtime Context Files

| File | Created By | Read By | Lifetime |
|------|-----------|---------|----------|
| `.claude/context/active-task-{session_id}.json` | `/start-task` skill | `task_status_hook.py` (PostToolUse) | Deleted by `task_status_hook.py` (SubagentStop) |

---

## Data Flow Diagram

```text
User
  │
  ▼
/add-new-feature
  │
  ├─ feature-researcher        ──> plan/feature-context-{slug}.md
  ├─ codebase-analyzer         ──> plan/codebase/{FOCUS}.md (optional)
  ├─ python-cli-design-spec    ──> plan/architect-{slug}.md
  ├─ swarm-task-planner        ──> plan/tasks-{N}-{slug}.md
  ├─ plan-validator            ──> PASS / BLOCKED
  └─ context-gathering         ──> Context Manifest in task file
  │
  ▼
/implement-feature
  │
  ├─ sam status P{N}       ──> JSON status
  ├─ sam ready P{N}  ──> JSON ready list (includes skills per task)
  │
  │  ┌── T0 runs first (Priority 1, no dependencies) ───────┐
  │  │  t0-baseline-capture                                  │
  │  │    ├─ Read acceptance-criteria-structured             │
  │  │    ├─ Run each check_command, capture results         │
  │  │    └─ Write plan/T0-baseline-{slug}.yaml              │
  │  └───────────────────────────────────────────────────────┘
  │
  │  ┌── For each implementation task (after T0 completes) ─┐
  │  │                                                      │
  │  │  Orchestrator reads task skills from ready JSON │
  │  │  If skills non-empty: adds Skill() instructions to   │
  │  │    delegation prompt ──> sub-agent loads skills       │
  │  │                                                      │
  │  │  /start-task                                         │
  │  │    ├─ Set status: IN PROGRESS                        │
  │  │    ├─ Load skills from task metadata (step 2a)       │
  │  │    ├─ Add Started timestamp                          │
  │  │    ├─ Write .claude/context/active-task-{sid}.json   │
  │  │    ├─ Implement acceptance criteria                  │
  │  │    └─ [PostToolUse hook updates LastActivity]        │
  │  │                                                      │
  │  │  [SubagentStop hook]                                 │
  │  │    ├─ Set status: COMPLETE                           │
  │  │    ├─ Add Completed timestamp                        │
  │  │    └─ Delete context file                            │
  │  │                                                      │
  │  └──────────────────────── Loop until no ready tasks ───┘
  │
  │  ┌── TN runs last (Priority 5, all impl. tasks done) ───┐
  │  │  tn-verification-gate                                 │
  │  │    ├─ Read plan/T0-baseline-{slug}.yaml               │
  │  │    ├─ Re-run each check_command, compare vs T0        │
  │  │    ├─ Classify each criterion (4-cell matrix)         │
  │  │    │    T0 pass + TN pass  = passed                   │
  │  │    │    T0 pass + TN fail  = regressed (blocks)       │
  │  │    │    T0 fail + TN fail  = pre-existing-fail        │
  │  │    │    T0 fail + TN pass  = newly-passing            │
  │  │    └─ Write plan/TN-verification-{slug}.yaml          │
  │  │         verdict: PASS | FAIL                          │
  │  └───────────────────────────────────────────────────────┘
  │
  ▼
/complete-implementation
  │
  ├─ [Pre-Phase 1] Read plan/TN-verification-{slug}.yaml
  │    ├─ verdict: FAIL ──> report regressed criteria, STOP
  │    └─ verdict: PASS or file absent ──> continue
  │
  ├─ code-reviewer             ──> review findings
  ├─ feature-verifier          ──> goal verification (structural)
  │                                (TN provides behavioral complement)
  ├─ integration-checker       ──> integration check
  ├─ doc-drift-auditor         ──> drift findings
  ├─ service-docs-maintainer   ──> doc updates (if drift)
  └─ context-refinement        ──> updated Context Manifest
                                ──> plan artifact annotations (if divergence found)
                                ──> DIVERGENCE_REQUIRING_REVIEW (if intent divergence)
  │
  ├─ [If follow-up task files created by code-reviewer]
  │    ├─ Route each follow-up:
  │    │    ├─ Search backlog by title keywords from filename
  │    │    ├─ Match found: backlog_update(selector=..., plan={followup_path})
  │    │    └─ No match: create-backlog-item --auto, then backlog_update(selector=..., plan=...)
  │    └─ Gate: same slug AND High priority -> Recurse: /implement-feature + /complete-implementation
  │             otherwise -> Deferred to backlog (no recursion)
  │
  ├─ [Final Step: Commit and push remaining changes]
  │    └─ Stage modified files (task file, backlog items, plan annotations)
  │       ──> single commit + push
  │
  ▼
Done
```
