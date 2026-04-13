# SAM (Stateless Agent Methodology) — Definition

## What SAM Is

**SAM (Stateless Agent Methodology)** is a constraint-driven development framework that compensates for LLM limitations through architectural structure rather than behavioral instructions. It treats Claude as a **stateless computation engine**—not a knowledge worker—that receives complete context and returns verified artifacts.

**Core insight**: Claude is a pure function. Input: complete context (task file with all answers). Output: verified result. No side effects: fresh context each time. No memory: everything externalized to artifact files.

The **canonical SAM specification** lives in the [bitflight-devops/stateless-agent-methodology](https://github.com/bitflight-devops/stateless-agent-methodology) repository. The `work-backlog-item` skill and `development-harness` plugin in claude_skills implement SAM patterns for backlog-driven feature work. This file is the self-contained SAM definition for use within this repo. Flow experiments and learnings live in [sam-flow-experiments](https://github.com/Jamie-BitFlight/sam-flow-experiments).

---

## Core Principles

(Canonical spec: <https://github.com/bitflight-devops/stateless-agent-methodology> — stateless-software-engineering-framework.md Part 2.)

- **Stateless agents** — Each agent gets fresh context with exactly what it needs. Eliminates context pressure and accumulated errors.
- **Externalized memory** — All state lives in artifact files, not in conversation. Survives session resets, enables verification.
- **Single responsibility** — Each agent does exactly one thing. Reduces complexity, enables specialization.
- **Message passing** — Agents communicate via artifacts, not shared context. Decouples stages, creates audit trail.
- **Verification at boundaries** — Every stage validates the previous stage's output. Catches errors before they propagate.
- **Deterministic backpressure** — Gate progress on deterministic checks (build/tests/lint/security scans) executed by tools, not "advice" in prompts. Converts non-deterministic generation into a measurable loop.
- **Embedded methodology** — The process IS the prompt, not instructions to follow. Cannot skip what structures the task.
- **No recall required** — Task files contain all answers needed for the task. Reduces reliance on unverified recall; verification still required for synthesis/logic.
- **RT-ICA gate** — Reverse Thinking - Information Completeness Assessment runs before planning. Prerequisites marked AVAILABLE | DERIVABLE | MISSING; BLOCK if any MISSING.
- **Semantic artifact tokens** — Storage-agnostic pattern `ARTIFACT:{TYPE}({SCOPE_OR_ID})` for DISCOVERY, PLAN, TASK, EXECUTION, REVIEW, VERIFICATION.
- **Structure over instruction** — Behavioral instructions cannot override architectural limitations. The pipeline structure enforces behavior.
- **AI cannot self-evaluate** — Independent verification required. Execution Agent and Forensic Review Agent are structurally separate.

---

## Pipeline Stages

(Canonical spec: <https://github.com/bitflight-devops/stateless-agent-methodology> — stateless-software-engineering-framework.md Part 2.2 and Part 3.)

| Stage | Name | Input | Output | Agent |
|-------|------|-------|--------|-------|
| S1 | Discovery | User request, problem statement | ARTIFACT:DISCOVERY(SCOPE:...) | Discovery Agent |
| S2 | Planning | Discovery artifacts | ARTIFACT:PLAN(SCOPE:...) | Planning Agent (with RT-ICA) |
| S3 | Context Integration | Plan + codebase | ARTIFACT:PLAN(SCOPE:...) contextualized | Context Integration Agent |
| S4 | Task Decomposition | Contextualized plan | ARTIFACT:TASK(TASK:...) per task | Task Decomposition Agent |
| S5 | Execution | Single task file (complete prompt) | ARTIFACT:EXECUTION(TASK:...) | Execution Agent (fresh session) |
| S6 | Forensic Review | Execution + task + plan | ARTIFACT:REVIEW(TASK:...) — COMPLETE / NEEDS_WORK | Forensic Review Agent |
| S7 | Final Verification | All completed tasks + original goals | ARTIFACT:VERIFICATION(SCOPE:...) — CERTIFIED / NOT_CERTIFIED | Final Verification Agent |

**Iteration loop**: If S6 returns NEEDS_WORK, Planner Agent creates new tasks; Orchestrator dispatches back to S5. Loop until COMPLETE, then S7.

---

## Artifact Flow

```text
User Request → DISCOVERY → PLAN → PLAN (contextualized) → TASK(s) → EXECUTION(s) → REVIEW(s) → VERIFICATION
```

Each artifact type uses the token pattern `ARTIFACT:{TYPE}({SCOPE_OR_ID})`. Storage is implementation-dependent (filesystem, SQL, etc.); the framework document gives example mappings (e.g. `.sam/artifacts/`).

---

## How to Embody SAM

### For Agents and Developers

1. **Use the SAM pipeline for feature work**
   - Canonical flow: Follow the 7-stage pipeline in the framework document.
   - In claude_skills: Invoke `/development-harness` or `/add-new-feature` for feature planning and implementation.
   - Bridge backlog items: Invoke `/work-backlog-item` to bring backlog items into SAM planning.

2. **Produce artifacts at every stage**
   - Use `ARTIFACT:{TYPE}({ID})` tokens in artifact headers; cross-reference predecessor/successor.
   - In claude_skills: Register via MCP — `artifact_register(issue_number, artifact_type, path, agent, content)` for discovery and plan artifacts. For task plans, choose a creation path based on plan size:

     **Monolithic path** (fewer than 16 tasks):

     ```text
     sam_plan(action='create', slug, goal, tasks=[{task_dict}, ...], issue)
     ```

     `tasks` is a list of task definition objects. Required fields: `id`, `title`. Optional: `status`, `agent`, `dependencies`, `priority`, `complexity`.

     **Incremental path** (16+ tasks — preferred for large plans):

     1. Create a drafting plan — passing an empty task list enters `state="drafting"`:

        ```text
        sam_plan(action='create', slug, goal, tasks=[], issue)
        ```

        While `state="drafting"`, `sam_plan status` and `sam_plan ready` return a drafting
        marker rather than task counts; the plan is not visible to the dispatch loop.

     2. Append tasks one at a time:

        ```text
        sam_plan(plan='P{N}', action='append_task', task={single_task_dict})
        ```

     3. Finalize — clears `state="drafting"` → `state="ready"`:

        ```text
        sam_plan(plan='P{N}', action='finalize')
        ```

     `append_task` is single-writer only — do not call it concurrently for the same plan.
     For the full contract, see the gotcha note in `plugins/development-harness/CLAUDE.md`.

   Artifacts are stored in the artifact manifest and accessible to all agents including worktree-isolated sessions.

3. **Apply structural gates, not instructions**
   - Run quality gates (format, lint, typecheck, test) after each stage.
   - Gate progression on artifact completion and validation.
   - Use RT-ICA before planning; do not proceed if BLOCKED.

4. **Separate producer from evaluator**
   - S5 Execution Agent implements; S6 Forensic Review Agent verifies. Do not rely on self-critique alone.
   - Forensic Review compares execution against acceptance criteria and returns COMPLETE or NEEDS_WORK.

5. **Escalate when constraints are unbound**
   - Gate 1 (after S1): Escalate if unbound constraints or domain knowledge gaps.
   - Gate 2 (after S4): Escalate if high complexity or novel architecture.
   - After 3 NEEDS_WORK loops on the same task, escalate to human.
   - After 2 NOT_CERTIFIED loops in S7, escalate to human.

6. **Commit atomically per task**
   - One atomic git commit per completed task for granular rollback.

---

## Source

### Canonical SAM (external repo)

Canonical spec: **<https://github.com/bitflight-devops/stateless-agent-methodology>**. Key documents: `stateless-agent-methodology.md`, `stateless-software-engineering-framework.md`, `README.md`, `docs/guides/sam-harness.md`.

**Fetch via git clone (when repo is not cloned locally):** Auth is provided by the `GITHUB_TOKEN` environment variable. Clone into a worktree and read from disk:

```bash
git clone --depth 1 https://github.com/bitflight-devops/stateless-agent-methodology.git \
  .claude/worktrees/stateless-agent-methodology
```

Then read:

- `.claude/worktrees/stateless-agent-methodology/stateless-agent-methodology.md`
- `.claude/worktrees/stateless-agent-methodology/stateless-software-engineering-framework.md`

### claude_skills implementation

| Component | Path | Purpose |
|-----------|------|---------|
| **Development harness** | `plugins/development-harness/` | SAM 7-stage pipeline, artifact conventions |
| **Default flow** | `plugins/development-harness/skills/development-harness/references/default-development-flow.md` | Default development flow |
| **Artifact conventions** | `plugins/development-harness/skills/development-harness/references/artifact-conventions.md` | Artifact naming and structure |
| **Human touchpoint model** | `plugins/development-harness/skills/development-harness/references/human-touchpoint-model.md` | Escalation and human gates |
| **Work-backlog-item bridge** | `.claude/skills/work-backlog-item/SKILL.md` | Bridges backlog items into SAM planning |

---

*Access date: 2026-02-23*
