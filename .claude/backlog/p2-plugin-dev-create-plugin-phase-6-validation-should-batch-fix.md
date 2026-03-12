---
name: '`/plugin-dev:create-plugin` Phase 6 validation should batch fixes by file, not by finding'
description: Phase 6 collected findings from 3 parallel review agents, then applied fixes one finding at a time. This resulted in SKILL.md being edited 3 separate times (description rewrite, SQL removal, MCP server name fix) when a single pass through the file would have applied all fixes together. The workflow should group all findings by file, then make one editing pass per file. Reduces Edit tool calls and context consumed by repeated reads.
metadata:
  topic: plugin-dev-create-plugin-phase-6-validation-should-batch-fix
  source: agentskill-kaizen plugin build Phase 6 (2026-02-18)
  added: '2026-02-18'
  priority: P2
  type: Feature
  status: needs-grooming
  issue: '#116'
  groomed: '2026-02-26'
  last_synced: '2026-03-12T12:48:45Z'
---

## Story

As a **developer**, I want **Phase 6 collected findings from 3 parallel review agents, then applied fixes ...** so that **backlog items are tracked in GitHub**.

## Description

Phase 6 collected findings from 3 parallel review agents, then applied fixes one finding at a time. This resulted in SKILL.md being edited 3 separate times (description rewrite, SQL removal, MCP server name fix) when a single pass through the file would have applied all fixes together. The workflow should group all findings by file, then make one editing pass per file. Reduces Edit tool calls and context consumed by repeated reads.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: agentskill-kaizen plugin build Phase 6 (2026-02-18)
- **Priority**: P2
- **Added**: 2026-02-18
- **Research questions**: None

## RT-ICA

**Goal**: Reduce Edit tool calls and context consumption by grouping Phase 6 validation fixes per-file instead of per-finding.

| # | Condition | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Phase 6 code location known | DERIVABLE | search plugins/plugin-creator/ for Phase 6 logic |
| 2 | Current behavior: one Edit per finding | AVAILABLE | VERIFIED by fact-checker (GitHub #116, grooming report, related backlog item) |
| 3 | Fix approach: group by file, apply once | AVAILABLE | Clearly described in issue |
| 4 | No external dependencies | AVAILABLE | Internal workflow change only |

**Decision**: APPROVED
**Missing**: None

## Fact-Check

Claims checked: 1
VERIFIED: 1 | REFUTED: 0 | INCONCLUSIVE: 0

1. Phase 6 applies fixes one-at-a-time per finding (SKILL.md edited 3 separate times for description rewrite, SQL removal, MCP server name fix) — **VERIFIED** (confirmed via GitHub Issue #116, grooming report 2026-02-21, and related backlog item p2-plugin-dev-create-plugin-workflow-lacks-intra-phase-parallel.md)

Citations: GitHub Issue #116 (accessed 2026-02-26), grooming-2026-02-21.md, p2-plugin-dev-create-plugin-workflow-lacks-intra-phase-parallel.md

## Groomed (2026-02-26)

### Reproducibility

1. Run `/plugin-dev:create-plugin` on any plugin that triggers Phase 6 validation
2. Observe Phase 6 spawns 3 parallel review agents
3. Each agent finds issues independently and applies Edit per finding
4. SKILL.md gets edited 3 separate times when a single pass would suffice
5. Fix: collect all findings from agents, group by file path, apply one Edit per file

### Priority

7/10 — Improves Phase 6 efficiency within plugin validation workflow. Not blocking but meaningful for large-scale plugin builds where repeated edits waste context budget.

### Impact

- Reduces Edit tool calls: 3 separate edits per file to 1 batched edit
- Decreases context consumption by avoiding redundant file reads
- Improves Phase 6 execution speed for multi-agent review scenarios
- Makes workflow more scalable for plugins with many issues per file

### Scope

Phase 6 workflow change only. Collect all findings from parallel review agents, group by target file path, apply all fixes for each file in a single Edit operation. No schema changes, no new tools or skills needed.

### Dependencies

- Depends on: None (internal workflow change)
- Blocks: None (P2 enhancement only)
- Related: p2-plugin-dev-create-plugin-workflow-lacks-intra-phase-parallel.md (complementary improvement)

### Files

- plugins/plugin-creator/skills/plugin-creator/SKILL.md (Phase 6 section)
- plugins/plugin-creator/agents/refactor-validator.md

### Decision

APPROVED — Small effort, clear fix, no blockers. Estimated 1-2 hours.
