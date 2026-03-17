---
name: Experiment protocol MCP server lacks content validation and enforcement
description: "The experiment-registry MCP server checks artefact key presence but never validates content, file existence, or artefact integrity. 8 gaps identified via /improve-processes analysis:\n\nCRITICAL — Gap 3: criteria_passed is a trust-based string self-report (state_manager.py:238). The iterate step completes when caller submits criteria_passed: 'true' — MCP does not independently verify rubric scores. Defeats the core anti-bias purpose.\n\nHIGH — Gap 1: No content validation. The validation field in experiment_core.json is decorative — never read or enforced. Empty artefacts pass.\n\nHIGH — Gap 4: No freeze enforcement on fixture/rubric/task-prompt. No content hashes tracked. Claude can silently modify frozen artefacts between iterations.\n\nHIGH — Gap 5: Rubric modifiable post-creation. Step ordering enforces rubric-before-baseline but content is not hash-locked. Post-hoc rubric modification is possible.\n\nMEDIUM — Gap 6: Iteration log content not validated. MCP cannot detect selective reporting.\n\nMEDIUM — Gap 7: No per-iteration output-iterN.md tracking. Iterate step requires only log.md, not output snapshots.\n\nLOW — Gap 2: No file existence check on artefact paths. Phantom paths reach retrospective-analyst.\n\nLOW — Gap 8: SKILL.md Phase 2 flowchart has no terminal-state guard before entering execution loop.\n\nSuccess: MCP mechanically enforces the methodology it claims to enforce — content validation, hash-based freeze, structured scoring instead of self-report.\n\nEvidence: Process gap analysis against state_manager.py, server.py, experiment_core.json, SKILL.md on branch feature/experiment-protocol-redesign."
metadata:
  topic: experiment-protocol-mcp-server-lacks-content-validation-and-
  source: Process analysis via /improve-processes
  added: '2026-03-04'
  priority: completed
  type: Bug
  status: done
  issue: '#431'
  last_synced: '2026-03-04T21:29:15Z'
  groomed: '2026-03-04'
  plan: plan/tasks-2-experiment-protocol-validation.md
---

## Groomed (2026-03-04)

### Issue Classification

**Type**: missing-guardrail
**Rationale**: The MCP server allows bad outcomes (empty artefacts pass, frozen content modifiable, criteria self-reported as passed) that validation gates should prevent. The system architecture permits these outcomes — no traceable failure chain exists because the gates were never built.
**Analysis Method**: none
**Scenario Target**: Experiment completes with self-reported "criteria_passed: true" while rubric scores are never verified -> MCP independently validates rubric scores before allowing iteration completion

### Priority

9/10 — Defeats core anti-bias purpose of experiment protocol by allowing self-reported criteria passing without MCP verification. Gap 3 (CRITICAL) alone makes methodology untrustworthy for scientific rigor.

### Impact

- Blocks: Any experiment claiming to enforce methodology — bias introduced when criteria_passed is never verified
- Bottleneck: Experiment results are unreliable; scientists using this protocol cannot trust iteration completion signals

**Benefits**:
- MCP enforces what it claims to enforce
- Criteria scoring becomes mechanically verified, not self-reported
- Frozen artefacts cannot drift silently between iterations
- Iteration logs cannot be selectively filtered
- Full auditability for post-hoc analysis

### Scope

**Expected Behavior**: MCP server validates on submission — all required artefacts present AND non-empty, artefact paths exist on disk, content passes declared validation rules, rubric and fixture remain frozen after baseline (hash-locked), rubric scores are verified against submitted criteria_passed (not trusted as self-report), iteration log captures all runs (not selective snapshots).

**Desired Structure**: Content validation gates in server.py on every artefact submission. Hash-based freeze mechanism for fixture/rubric/task-prompt after baseline step. Structured rubric scoring (parsed JSON or scored fields) instead of prose self-report. Per-iteration output capture tracked alongside log.md. File existence checks on all artefact paths. Validation error responses that list which checks failed.

### Output / Evidence

1. Running `complete_step(hypothesis)` with empty hypothesis.md → MCP rejects with "validation failed: content empty"
2. Running `complete_step(baseline)` → MCP verifies criteria are scored for iter0, not just claimed
3. Modifying fixture.md post-baseline and running `complete_step(iterate)` → MCP rejects with "fixture frozen since baseline"
4. Running `complete_step(iterate)` with log.md only (no output-iter1.md) → MCP either rejects or auto-captures output
5. Submitting `criteria_passed: 'true'` without actual rubric scores → MCP rejects, requires explicit per-criterion pass/fail
6. Phase 2 flowchart in SKILL.md has terminal state check before entering execution loop
7. All 8 gaps resolved: Gap 1-8 each have a corresponding fix in server.py or state_manager.py

### Dependencies

- Depends on: None (independent MCP validation work)
- Blocks: Any use of experiment-registry MCP until validation gates are added

### Files

- plugins/scientific-method/scripts/state_manager.py (criteria_passed trust-based check at line 238)
- plugins/scientific-method/scripts/server.py (MCP tool definitions, validation entry points)
- plugins/scientific-method/assets/experiment_core.json (validation field — decorative, never enforced)
- plugins/scientific-method/skills/scientific-thinking/SKILL.md (Phase 2 flowchart missing terminal-state guard)

### Skills

- /scientific-method:scientific-thinking (experiment protocol skill)
- /fastmcp-creator (MCP server patterns)

### Research

- Gap analysis source: Process analysis via /improve-processes on branch feature/experiment-protocol-redesign
- Experiment protocol design: experiment_core.json defines validation rules (currently unenforced)
- Effort: High — touches state_manager.py, server.py, experiment_core.json validation schema, and SKILL.md


## RT-ICA

**Decision**: APPROVED
**Goal**: MCP server mechanically enforces methodology — content validation, hash-based freeze, structured scoring instead of trust-based self-report.

**Conditions**:
1. Source files (state_manager.py, server.py, experiment_core.json, SKILL.md) | AVAILABLE | On branch feature/experiment-protocol-redesign
2. Gap descriptions with file:line references | AVAILABLE | 8 gaps documented in issue body
3. Understanding of experiment protocol design intent | DERIVABLE | From SKILL.md and registry JSON
4. Test infrastructure for MCP server | DERIVABLE | From existing test patterns
5. FastMCP patterns for validation | DERIVABLE | From existing server.py

**Missing**: None

## Fact-Check

**Claims checked**: 0 (web-verifiable)
All 8 gaps are code-internal claims referencing specific files and line numbers on branch feature/experiment-protocol-redesign. Web search cannot verify them. The groomer agent will verify each gap against the actual source files.
**VERIFIED**: N/A | **REFUTED**: N/A | **INCONCLUSIVE**: N/A