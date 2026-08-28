# SAM (Stateless Agent Methodology) — Definition

## What SAM Is

**SAM (Stateless Agent Methodology)** is a constraint-driven development framework that compensates for LLM limitations through architectural structure rather than behavioral instructions. It treats Claude as a **stateless computation engine**—not a knowledge worker—that receives complete context and returns verified artifacts.

**Core insight**: Claude is a pure function. Input: complete context (task record with all answers).
Output: verified result. No side effects: fresh context each time. No memory: everything is
externalized to provider-owned artifacts.

The **canonical SAM specification** lives in the [bitflight-devops/stateless-agent-methodology](https://github.com/bitflight-devops/stateless-agent-methodology) repository. The `work-backlog-item` skill and `development-harness` plugin in claude_skills implement SAM patterns for backlog-driven feature work. This file is the self-contained SAM definition for use within this repo. Flow experiments and learnings live in [sam-flow-experiments](https://github.com/Jamie-BitFlight/sam-flow-experiments).

---

## Core Principles

(Canonical spec: <https://github.com/bitflight-devops/stateless-agent-methodology> — stateless-software-engineering-framework.md Part 2.)

- **Stateless agents** — Each agent gets fresh context with exactly what it needs. Eliminates context pressure and accumulated errors.
- **Externalized memory** — All state lives in provider-owned artifacts, not in conversation. Survives session resets, enables verification.
- **Single responsibility** — Each agent does exactly one thing. Reduces complexity, enables specialization.
- **Message passing** — Agents communicate via artifacts, not shared context. Decouples stages, creates audit trail.
- **Verification at boundaries** — Every stage validates the previous stage's output. Catches errors before they propagate.
- **Deterministic backpressure** — Gate progress on deterministic checks (build/tests/lint/security scans) executed by tools, not "advice" in prompts. Converts non-deterministic generation into a measurable loop.
- **Embedded methodology** — The process IS the prompt, not instructions to follow. Cannot skip what structures the task.
- **No recall required** — Task records contain all answers needed for the task. Reduces reliance on unverified recall; verification still required for synthesis/logic.
- **RT-ICA gate** — Reverse Thinking - Information Completeness Assessment runs before planning. Prerequisites marked AVAILABLE | DERIVABLE | MISSING; BLOCK if any MISSING.
- **Semantic artifact tokens** — Storage-agnostic pattern `ARTIFACT:{TYPE}({SCOPE_OR_ID})` for DISCOVERY, PLAN, TASK, EXECUTION, REVIEW, VERIFICATION.
- **Structure over instruction** — Behavioral instructions cannot override architectural limitations. The pipeline structure enforces behavior.
- **AI cannot self-evaluate** — Independent verification required. Execution Agent and Forensic Review Agent are structurally separate.

---

## How work-backlog-item embodies SAM

`work-backlog-item` bridges a backlog item into SAM by invoking `dh:add-new-feature`
(Step 4.2) and, in `--auto` mode, `dh:implement-feature` afterward — the full
7-stage pipeline (Discovery through Final Verification), its artifact tokens, its per-stage
escalation rules, and its plan-creation mechanics are owned and executed by those invoked skills,
not by this one. What this skill itself must do:

- Gate on RT-ICA before invoking planning; do not proceed if BLOCKED (see [rt-ica-gate.md](./rt-ica-gate.md)).
- Retain the `plan_ref`/`plan_address` returned by planning and link it back to the backlog item (see [plan.md](./plan.md)).
- Commit once at the end of its own workflow (see `start.md`'s Commit step) — per-task commits inside the pipeline are `dh:implement-feature`'s concern.

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
| **Shared references** | `dh:dh-meta-docs` | Routes the default flow, artifact conventions, and human touchpoint model |
| **Work-backlog-item bridge** | `.claude/skills/work-backlog-item/SKILL.md` | Bridges backlog items into SAM planning |

---

*Access date: 2026-02-23*
