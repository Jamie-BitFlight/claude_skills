---
name: Backlog lifecycle process gaps — 10 findings from improve-processes audit
description: "Process audit of the full backlog item lifecycle (create → groom → discuss → research → validate → feasibility → plan → implement → close/resolve) using the /improve-processes excellence checklist and triage protocol. 10 findings identified across 3 severity levels. 2 HIGH: (F1) no feasibility gate between RT-ICA APPROVED and SAM planning, (F9) 6 implied handoffs that break autonomous execution. 5 MEDIUM: (F2) no discussion/interview step, (F4) vague 'is job valid' condition, (F5) non-sequential step numbering, (F6) no groomer output validation, (F10) draft lifecycle doc not promoted. 3 LOW: (F3) RT-ICA staleness, (F7) auto-mode P1 default, (F8) fact-check auto-push. Full report: .claude/docs/process-audit-backlog-lifecycle-2026-03-02.md"
metadata:
  topic: backlog-lifecycle-process-gaps-10-findings-from-improve-proc
  source: Session observation — /improve-processes audit
  added: '2026-03-02'
  priority: P1
  type: Feature
  status: open
  issue: '#398'
  last_synced: '2026-03-21T08:08:35Z'
  plan: .claude/docs/process-audit-backlog-lifecycle-2026-03-02.md
  groomed: '2026-03-06'
---

## Story

As a **developer using Claude Code skills**, I want to **backlog lifecycle process gaps — 10 findings from improve-processes audit** so that **the tooling becomes more capable and complete**.

## Description

Process audit of the full backlog item lifecycle (create → groom → discuss → research → validate → feasibility → plan → implement → close/resolve) using the /improve-processes excellence checklist and triage protocol. 10 findings identified across 3 severity levels. 2 HIGH: (F1) no feasibility gate between RT-ICA APPROVED and SAM planning, (F9) 6 implied handoffs that break autonomous execution. 5 MEDIUM: (F2) no discussion/interview step, (F4) vague 'is job valid' condition, (F5) non-sequential step numbering, (F6) no groomer output validation, (F10) draft lifecycle doc not promoted. 3 LOW: (F3) RT-ICA staleness, (F7) auto-mode P1 default, (F8) fact-check auto-push. Full report: .claude/docs/process-audit-backlog-lifecycle-2026-03-02.md

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Session observation — /improve-processes audit
- **Priority**: P1
- **Added**: 2026-03-02
- **Research questions**: None

## Groomed (2026-03-03)

### Fact-Check

**Date**: 2026-03-03
**Claims checked**: 5

| # | Claim | Verdict | Repository evidence |
|---|---|---|---|
| 1 | Audit report exists with Finding 1..10 headings | VERIFIED | `.claude/docs/process-audit-backlog-lifecycle-2026-03-02.md` |
| 2 | Two HIGH findings are feasibility gate gap and implied handoffs | VERIFIED | Finding 1 (**Severity: High**), Finding 9 (**Severity: High**) in `.claude/docs/process-audit-backlog-lifecycle-2026-03-02.md` |
| 3 | Five MEDIUM findings include F2/F4/F5/F6/F10 | VERIFIED | Findings 2, 4, 5, 6, 10 marked **Medium** in `.claude/docs/process-audit-backlog-lifecycle-2026-03-02.md` |
| 4 | Three LOW findings claimed | INCONCLUSIVE | F7/F8 are **Low**; F3 is **Low-Medium** in `.claude/docs/process-audit-backlog-lifecycle-2026-03-02.md` |
| 5 | Backlog MCP server lacks safety annotations and F11-F17 capabilities | VERIFIED | `.claude/skills/backlog/backlog_core/server.py` has 10 `@mcp.tool()` decorators without annotation args; no `backlog_session_diff`, `backlog_dashboard`, `backlog_batch_update`, `backlog_start`, `backlog_block`, `backlog_unblock` tools |

**Totals**: VERIFIED 4 | REFUTED 0 | INCONCLUSIVE 1

### RT-ICA

**Goal**: Establish a complete, explicit, and autonomous backlog lifecycle process that closes identified process-control gaps before planning/execution.

| # | Condition | Status | Info needed |
|---|---|---|---|
| 1 | Canonical list of process gaps and evidence source is available | AVAILABLE | none |
| 2 | Current backlog tooling/workflow lacks explicit gates/handoff mechanisms identified in findings | AVAILABLE | none |
| 3 | Prioritized outcome definition for what should improve is present | DERIVABLE | explicit success signals across lifecycle stages |
| 4 | Exact low-severity distribution from original claim is settled | DERIVABLE | decide whether Low-Medium counts as Low for reporting |

**Decision**: APPROVED
**Missing**: None

### Priority

9/10 — High-leverage process-control work that affects all backlog throughput by adding explicit feasibility gating and autonomous handoff continuity.

### Impact

- **Blocks**: reliable autonomous create→groom→work→plan→implement→close/resolve flow
- **Bottlenecks**: ungated RT-ICA→planning transition; implied cross-skill handoffs requiring manual operator memory
- **Risk if unchanged**: wasted planning cycles on infeasible items, stalled auto mode, inconsistent lifecycle execution

### Expected Behavior

The backlog lifecycle should run end-to-end with explicit, auditable gates and transitions:

1. Feasibility gate exists after RT-ICA APPROVED and before SAM planning.
2. Cross-skill handoffs are explicit and machine-followable (not implied in prose only).
3. Groomed outputs are validated before persistence.
4. Lifecycle documentation is canonical, referenced, and consistent across skills.
5. Severity reporting is internally consistent (including Low vs Low-Medium handling policy).

### Acceptance Criteria

1. Lifecycle includes an explicit feasibility decision gate between RT-ICA APPROVED and `add-new-feature` invocation.
2. All identified handoffs in Finding 9 are represented as explicit next-step contract(s) in skill outputs and/or a canonical lifecycle state machine.
3. `groom-backlog-item` includes a deterministic validation check for groomer output sections before write/sync.
4. Ambiguous decision conditions (e.g., "is job valid") are replaced by observable checks and clear escalation paths.
5. `work-backlog-item` step numbering/phase model is normalized for deterministic navigation.
6. `.claude/docs/backlog-lifecycle.draft.md` is validated, promoted (or superseded), and referenced by relevant backlog lifecycle skills.
7. A policy is documented for treating **Low-Medium** findings in severity totals to eliminate reporting ambiguity.

### Issue Classification

**Type**: missing-guardrail
**Rationale**: The workflow allowed undesirable outcomes (autonomous flow breaks, no quality gate, no feasibility gate) that explicit process gates should have prevented.
**Analysis Method**: none
**Scenario Target**: Running backlog lifecycle end-to-end in auto mode reveals broken handoffs and ungated transitions -> lifecycle includes explicit, auditable gates and handoff rules.

### Root-Cause Analysis

N/A - not applicable for this issue type.

### Resources

| Type | Path | Relevance |
|---|---|---|
| Prior work | `.claude/docs/process-audit-backlog-lifecycle-2026-03-02.md` | Source audit with Findings 1-10 and severities |
| Prior work | `.claude/docs/backlog-lifecycle.draft.md` | Draft canonical lifecycle doc referenced by Finding 10 |
| Skill | `.claude/skills/improve-processes/SKILL.md` | Audit checklist/triage method source |
| Skill | `.claude/skills/groom-backlog-item/SKILL.md` | RT-ICA + groomer flow and write pipeline |
| Skill | `.claude/skills/work-backlog-item/SKILL.md` | RT-ICA gate, step structure, close/resolve routing |
| Skill | `.claude/skills/create-backlog-item/SKILL.md` | auto-mode priority derivation behavior (Finding 7 context) |
| Skill | `.claude/skills/fact-check/SKILL.md` | post-actions commit/push behavior (Finding 8 context) |
| Skill | `.claude/skills/add-new-feature/SKILL.md` | downstream SAM planning entrypoint after lifecycle gates |
| MCP server | `.claude/skills/backlog/backlog_core/server.py` | current tool surface; no safety annotations; missing F11-F17 tools |
| Agent | `.claude/agents/backlog-item-groomer.md` | groomer output producer requiring validation guard |

### Dependencies

- **Depends on**: alignment updates across `create-backlog-item`, `groom-backlog-item`, `work-backlog-item`, and lifecycle docs.
- **Blocks**: reliable autonomous backlog orchestration and downstream planning efficiency.

### Effort

Medium-High — mostly workflow/spec and tool-contract changes across multiple backlog lifecycle artifacts with moderate validation overhead.

### Decision

Proceed with planning. RT-ICA APPROVED; treat severity-count ambiguity as a documentation/policy deliverable during implementation.
