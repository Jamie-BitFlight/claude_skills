# Improvement Proposals: Maverick

**Research entry**: ./research/coding-agents/maverick.md
**Generated**: 2026-03-23
**Patterns assessed**: 5
**Backlog items created**: 0
**Deferred (low confidence)**: 2
**Skipped (already covered or tracked)**: 3

---

## Improvement 1: Automated Project-Specific Skill Generation (Upskill System)

**Source pattern**: "The separation of best-practice skills (universal standards) from project skills (stack-specific implementations) is directly applicable to Claude Code skill design. The upskill system demonstrates automated skill generation and project customization." (Relevance section, point 2)
**Local system**: /home/user/claude_skills/plugins/plugin-creator/skills/skill-creator/SKILL.md
**Confidence**: Low
**Impact**: Medium
**Backlog**: Deferred -- confidence Low: the skill-creator already supports project-level skills and the `/init` step scans the environment. Whether Maverick's specific upskill mechanism (scan codebase for existing implementations of logging/testing/CI patterns and auto-generate compliant project skills) would produce better outcomes than the current manual skill-creation workflow is unclear without experimentation. The local system may already achieve equivalent results through the combination of `/skill-creator` and `/add-doc-updater`.

### Current state

The `/plugin-creator:skill-creator` skill creates new skills from scratch via a 10-step interactive process. There is no mechanism that automatically scans a project's codebase, detects which practices (logging, testing, linting, CI/CD) are already implemented, and generates project-specific skill files documenting those implementations. Skill creation is always manual and user-initiated.

### Target state

A `/plugin-creator:upskill` or `/dh:upskill` skill that scans a project for a configurable set of topics (defined in a `topics.json` or equivalent), detects existing implementations (e.g., pytest configured, ruff configured, structured logging present), and generates project-specific skills under `.claude/skills/<topic>/SKILL.md` documenting both the detected implementation and any gaps relative to best-practice skills.

### Measurable signal

Running `/upskill` on a Python project with pytest and ruff configured produces `.claude/skills/unit-testing/SKILL.md` and `.claude/skills/linting/SKILL.md` containing project-specific configuration details extracted from `pyproject.toml` and existing test files. Skills reference both the detected implementation and the relevant best-practice standard.

---

## Improvement 2: Layered Enforcement Chain with Hook-Based Practice Verification

**Source pattern**: "Enforcement Chain: 1. Best-practice skill -- prevents anti-patterns (console.log vs structured logger) 2. Project skill -- ensures project-specific implementation (Pino with CloudWatch) 3. Local verification -- catches syntax, lint, test failures before push 4. CI pipeline -- catches environment-specific, dependency, cross-platform issues 5. Agent review -- catches spec violations, missing tests, security issues, convention drift 6. Human review -- final gate for production-bound code" (Key Features section 5, from docs/overview.md)
**Local system**: /home/user/claude_skills/plugins/development-harness/skills/start-task/SKILL.md and /home/user/claude_skills/plugins/development-harness/skills/implementation-manager/scripts/task_status_hook.py
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred -- confidence Medium: the local system has hooks (PostToolUse, SubagentStop) that update task status and timestamps, and the complete-implementation skill runs a 6-phase quality gate chain (code review, feature verification, integration check, doc drift audit, doc update, context refinement). However, the local hooks do not enforce practice-specific rules at the tool-call boundary (e.g., blocking a Write that introduces console.log instead of structured logging). Whether adding practice-enforcement hooks at the PreToolUse boundary would improve outcomes or just add latency is unclear without measuring current failure rates from practice violations.

### Current state

The `task_status_hook.py` script handles two events: SubagentStop (marks task complete, syncs to GitHub) and PostToolUse for Write|Edit|Bash (updates LastActivity timestamp). No hook validates the content of what is being written against practice standards. The enforcement chain in the local system is: skills (loaded at session start) -> agent review (code-reviewer in Phase 1 of complete-implementation) -> human review. There is no local verification layer between agent writing code and agent review that catches practice violations in real-time.

### Target state

A PreToolUse hook on Write|Edit operations during `/start-task` execution that checks the content being written against project-level practice rules (e.g., no `print()` when structured logging is configured, no `import yaml` when `ruamel.yaml` is the project standard). The hook returns exit code 2 to block the write and show the violation to Claude, who can then self-correct before the write lands. Practice rules are defined in a machine-readable format under `.claude/rules/` or project skills.

### Measurable signal

A PreToolUse hook script exists that reads practice rules from a configurable path. When Claude writes `import yaml` to a Python file in this repository, the hook exits with code 2 and stderr contains "Use ruamel.yaml per .claude/rules/yaml-toml-libraries.md". Claude then rewrites the import before proceeding.

---

## Improvement 3: Supervised Workflow Mode with Human Checkpoint Gates

**Source pattern**: "do-issue-guided -- Supervised Development with Checkpoints: Human approval gates at four decision points: 1. After solution design (before task creation) 2. After task breakdown (before execution) 3. After implementation + agent review (before PR) 4. After PR creation (before merge)" (Key Features section 4)
**Local system**: /home/user/claude_skills/plugins/development-harness/skills/add-new-feature/SKILL.md and /home/user/claude_skills/plugins/development-harness/skills/implement-feature/SKILL.md
**Confidence**: Medium
**Impact**: Low
**Backlog**: Deferred -- confidence Medium: the local system already has the ARL (Adaptive Resource Level) human touchpoint model documented in the development harness CLAUDE.md, which uses constraint analysis to decide when to escalate rather than fixed checkpoints. Whether adding a fixed-checkpoint "guided" mode alongside the ARL-based model would improve outcomes or create confusion is unclear. The ARL approach may be architecturally superior (escalates based on risk, not phase boundaries).

### Current state

The `/dh:add-new-feature` skill runs Phases 1-6 (discovery, codebase analysis, architecture spec, task decomposition, plan validation, context manifest) without mandatory human approval gates between phases. The development harness CLAUDE.md documents ARL human touchpoints that escalate based on constraint analysis (unbound constraints, domain knowledge gaps, high-risk irreversible changes, novel architecture decisions). The `/dh:implement-feature` skill similarly runs the progress loop without fixed human checkpoints.

### Target state

An optional `--guided` flag on `/dh:add-new-feature` and `/dh:implement-feature` that inserts mandatory human approval gates at phase boundaries (after discovery, after task decomposition, after implementation, before PR). When `--guided` is passed, Claude pauses and presents a summary at each gate, waiting for explicit user approval before proceeding.

### Measurable signal

Running `/dh:add-new-feature --guided "feature description"` pauses after Phase 1 (discovery) and outputs "Phase 1 complete. Review feature-context-{slug}.md. Approve to continue? [y/n]". User must respond before Phase 2 begins. Same pattern at Phase 3 and Phase 4 boundaries.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Automated project-specific skill generation (upskill system) | Low | Would need experimentation to determine if auto-generating project skills from codebase scans produces better outcomes than the existing manual skill-creation workflow. The local system may already cover this need through `/skill-creator` + `/add-doc-updater`. |
| Layered enforcement chain with hook-based practice verification | Medium | The local system already has a 6-phase quality gate chain and ARL-based human touchpoints. Whether adding real-time practice-enforcement hooks at the PreToolUse boundary would reduce defects enough to justify the per-tool-call latency cost requires measuring current practice-violation rates in agent output. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Agent-Based Review Architecture (isolated context windows) | Already covered: the local system uses isolated context windows for code review (code-reviewer agent in Phase 1 of complete-implementation) and all verification agents (feature-verifier, integration-checker, doc-drift-auditor). The complete-implementation SKILL.md dispatches each quality gate phase via a separate Agent call with `context: fork` isolation. Maverick's "marking your own homework" prevention is already implemented. |
| Workflow Decomposition (solution design -> create tasks -> execute with checkpoint gating) | Already covered: the local SAM workflow implements the same three-layer decomposition -- `/dh:add-new-feature` (discovery -> analysis -> architecture -> task decomposition -> validation -> context manifest) followed by `/dh:implement-feature` (execution loop) followed by `/dh:complete-implementation` (6-phase quality gates). The local system is more granular (6 planning phases vs Maverick's 3, plus 6 quality gate phases). |
| Multi-Platform Support (platform-agnostic practices with platform-specific skills) | Already covered: the local development harness uses a Voltron-style composition model where language plugins provide specialist agents via manifests. The role resolution protocol (documented in CLAUDE.md) detects project language from marker files (pyproject.toml, package.json, Cargo.toml) and resolves roles to language-specific agents. This is architecturally equivalent to Maverick's platform-specific skills approach. |
