# Improvement Proposals: HyperAgents

**Research entry**: ./research/coding-agents/hyperagents.md
**Generated**: 2026-03-29
**Patterns assessed**: 4
**Backlog items created**: 0
**Deferred (low confidence)**: 1
**Skipped (already covered or tracked)**: 3

---

## Improvement 1: Staged evaluation cascade with early-exit gates for quality gate dispatch

**Source pattern**: "Evaluation cascade: Staged evaluation for efficiency (small->medium->large test sets with pass/fail gates)" and "Staged evaluation with small/medium subset progression (pass threshold: 0.4 on small subset triggers medium subset eval)" -- Evolutionary Loop and Key Features sections
**Local system**: plugins/development-harness/skills/complete-implementation/SKILL.md
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred -- confidence Medium: the local quality gate system already implements a two-tier approach (proportional 3-task gates vs full 6-task SAM gates) which is a form of staged evaluation. Whether adding an explicit early-exit threshold within the 6-task SAM gates would improve efficiency requires measurement data that does not exist yet.

### Current state

The complete-implementation skill dispatches either 3 tasks (proportional quality gates for issues without a plan) or 6 tasks (full SAM quality gates). Within the 6-task SAM path, all 6 phases must reach terminal status sequentially (T1 code review, T2 feature verification, T3 integration check, T4 doc drift audit, T5 doc update, T6 context refinement). There is no early-exit mechanism -- if T1 code review finds critical issues, T2-T6 still dispatch and run. File: plugins/development-harness/skills/complete-implementation/SKILL.md, "SAM Path -- Phase Task Mapping" section.

### Target state

The 6-task SAM quality gate dispatch includes an early-exit gate after T1 (code review). If T1 reports critical findings (severity >= HIGH), the remaining phases are skipped and the plan is marked as BLOCKED with a reference to the T1 findings. T2-T6 only dispatch when T1 passes without critical findings. This mirrors HyperAgents' staged evaluation where a small subset must pass a threshold before the full evaluation runs.

### Measurable signal

After T1 completes with critical findings, `sam_status` for the quality gate plan shows tasks T2-T6 with status `skipped` rather than `complete` or `in_progress`. The total time for a failed quality gate run decreases by approximately the time of T2-T6 execution (currently 4-5 agent dispatches).

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Staged evaluation cascade with early-exit gates | Medium | The local system already has two-tier quality gates (proportional vs full SAM). Whether adding early-exit within the 6-task flow would materially improve efficiency requires timing data from actual QG runs. The gap is real but the benefit magnitude is unverified. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Self-improving agent architecture (MetaAgent modifying codebase) | Incompatible with local architecture -- this repo uses curated SKILL.md instructions and agent definitions that are version-controlled. Self-modifying agent code would bypass the plugin lifecycle, version control, and quality gates. The local system is designed for reproducibility via static skill definitions, not evolutionary self-modification. |
| Tool-use protocol standardization (JSON tool format with retry logic) | Already covered by a superior mechanism -- Claude Code uses native tool_use protocol with built-in retry and validation handled by the runtime. Custom JSON parsing with `<json>` markers and boundary-detection retry logic (as in HyperAgents' `llm_withtools.py`) would be a regression from the native protocol. |
| Domain-driven evaluation (modular domain architecture) | Already covered in plugins/development-harness/CLAUDE.md -- the Voltron-style composition model with language manifests, role resolution, and the Layer 0/1/2 separation provides equivalent modular extensibility. New task domains are added via language plugin manifests without modifying core harness logic. |
