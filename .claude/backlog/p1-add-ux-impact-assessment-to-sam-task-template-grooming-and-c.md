---
name: Add Process Quality Discipline to SAM pipeline — issue classification, root-cause analysis, and proportional response
description: "The SAM pipeline treats every issue the same way: plan it, implement it, verify it works. But different issue types need fundamentally different treatment depths, and the pipeline never asks 'what scenario exposed this problem?' or 'what should we improve so this class of problem doesn't recur?'\n\nBoth human and AI are users of this pipeline. Quality of life for both means: the right analytical tool is applied to the right problem type, the scenario that caused the issue is what gets improved (not just the symptom), and the response is proportional to the problem.\n\n## Issue Classification Taxonomy\n\nThe pipeline needs to classify issues before choosing a response:\n\n1. **Procedural fix** (typo, spelling, naming inconsistency) — Fix the noted occurrence, search for similar patterns, update all references. No root-cause analysis needed. Bounded scope.\n2. **Defect with clear cause** (bug where the failure chain is traceable) — 5 Whys to find the root cause. Fix the cause, not just the symptom. Verify the scenario that exposed it.\n3. **Recurring defect pattern** (same class of bug keeps appearing) — 6 Sigma thinking: measure frequency, identify common factors, add guardrails/instructions to prevent the class. May need process change.\n4. **Missing guardrail** (the system allowed a bad outcome that should have been caught) — Improve the instruction or gate that should have prevented it. The scenario that exposed the problem IS the thing to improve.\n5. **Unbounded design problem** (no clear right answer, we need to choose what the outcome looks like) — Requires framing the decision space, selecting constraints, and designing the outcome. Cannot be reduced to a fix.\n\n## Root-Cause Analysis Integration\n\n### When to use 5 Whys\n- A specific failure occurred with a traceable chain\n- The symptom is clear but the cause isn't\n- Asking 'why did this happen?' repeatedly converges on an actionable root\n\n### When to use 6 Sigma thinking\n- The same class of defect has appeared 2+ times\n- Metrics exist or can be gathered (frequency, severity, affected scope)\n- The goal is reducing variation/recurrence, not just fixing one instance\n\n### When neither applies\n- Procedural fixes (type 1): just fix and sweep for siblings\n- Unbounded design (type 5): frame the problem space first, analysis comes after framing\n\n## Scenario-as-Target Principle\n\nEvery issue filed from a session observation should answer: 'What scenario exposed this, and is that scenario the thing we improve?' Examples:\n- Issue: 'backlog.py duplicate detection is lexical-only' → Scenario: user created near-duplicate items. Target: improve the detection algorithm (symptom IS the cause).\n- Issue: 'abort-only flow in backlog add' → Scenario: user wanted to modify before committing. Target: the interaction design lacks confirmation/edit step (missing guardrail).\n- Issue: '#311/#312 had 9 quality problems post-implementation' → Scenario: completion gates didn't evaluate experiential quality. Target: the gate process itself (recurring pattern — 6 Sigma territory).\n\n## Changes Needed\n\n### SAM Task Template (TASK_FILE_FORMAT.md)\n- Add 'Issue Classification' field to task metadata (procedural | defect | recurring-pattern | missing-guardrail | unbounded-design)\n- Add 'Scenario Target' field: what scenario exposed this, what specifically should improve\n- Add 'Analysis Method' field: none | 5-whys | 6-sigma | design-framing\n\n### Grooming (groom-backlog-item/SKILL.md)\n- Classify the issue type before planning the response\n- For types 2-3: require root-cause analysis output before marking groomed\n- For type 4: identify the guardrail/instruction gap\n- For type 5: require problem-space framing before planning\n\n### Completion Gates (complete-implementation/SKILL.md, verify/SKILL.md)\n- Verify the response was proportional to the issue type\n- For types 2-4: verify the scenario that exposed the problem was addressed, not just the symptom\n- For type 3 (recurring): verify a guardrail or process change was added to prevent recurrence\n\n### Feature Verifier (feature-verifier.md)\n- Check: did we improve the thing that caused the issue, or did we only patch the output?\n- Check: for both human and AI consumers, is the quality of life improved for this scenario?"
metadata:
  topic: add-ux-impact-assessment-to-sam-task-template-grooming-and-c
  source: 'Post-implementation critique of backlog #311/#312 + user refinement on process quality discipline — session 2026-03-01'
  added: '2026-03-01'
  priority: completed
  type: Feature
  status: done
  issue: '#314'
  last_synced: '2026-03-01T23:00:47Z'
  groomed: '2026-03-01'
  plan: plan/tasks-15-process-quality-discipline.md.original
---

## Story

As a **developer**, I want **The SAM pipeline treats every issue the same way: plan it, implement it, veri...** so that **backlog items are tracked in GitHub**.

## Description

The SAM pipeline treats every issue the same way: plan it, implement it, verify it works. But different issue types need fundamentally different treatment depths, and the pipeline never asks 'what scenario exposed this problem?' or 'what should we improve so this class of problem doesn't recur?'

Both human and AI are users of this pipeline. Quality of life for both means: the right analytical tool is applied to the right problem type, the scenario that caused the issue is what gets improved (not just the symptom), and the response is proportional to the problem.

## Issue Classification Taxonomy

The pipeline needs to classify issues before choosing a response:

1. **Procedural fix** (typo, spelling, naming inconsistency) — Fix the noted occurrence, search for similar patterns, update all references. No root-cause analysis needed. Bounded scope.
2. **Defect with clear cause** (bug where the failure chain is traceable) — 5 Whys to find the root cause. Fix the cause, not just the symptom. Verify the scenario that exposed it.
3. **Recurring defect pattern** (same class of bug keeps appearing) — 6 Sigma thinking: measure frequency, identify common factors, add guardrails/instructions to prevent the class. May need process change.
4. **Missing guardrail** (the system allowed a bad outcome that should have been caught) — Improve the instruction or gate that should have prevented it. The scenario that exposed the problem IS the thing to improve.
5. **Unbounded design problem** (no clear right answer, we need to choose what the outcome looks like) — Requires framing the decision space, selecting constraints, and designing the outcome. Cannot be reduced to a fix.

## Root-Cause Analysis Integration

### When to use 5 Whys
- A specific failure occurred with a traceable chain
- The symptom is clear but the cause isn't
- Asking 'why did this happen?' repeatedly converges on an actionable root

### When to use 6 Sigma thinking
- The same class of defect has appeared 2+ times
- Metrics exist or can be gathered (frequency, severity, affected scope)
- The goal is reducing variation/recurrence, not just fixing one instance

### When neither applies
- Procedural fixes (type 1): just fix and sweep for siblings
- Unbounded design (type 5): frame the problem space first, analysis comes after framing

## Scenario-as-Target Principle

Every issue filed from a session observation should answer: 'What scenario exposed this, and is that scenario the thing we improve?' Examples:
- Issue: 'backlog.py duplicate detection is lexical-only' → Scenario: user created near-duplicate items. Target: improve the detection algorithm (symptom IS the cause).
- Issue: 'abort-only flow in backlog add' → Scenario: user wanted to modify before committing. Target: the interaction design lacks confirmation/edit step (missing guardrail).
- Issue: '#311/#312 had 9 quality problems post-implementation' → Scenario: completion gates didn't evaluate experiential quality. Target: the gate process itself (recurring pattern — 6 Sigma territory).

## Changes Needed

### SAM Task Template (TASK_FILE_FORMAT.md)
- Add 'Issue Classification' field to task metadata (procedural | defect | recurring-pattern | missing-guardrail | unbounded-design)
- Add 'Scenario Target' field: what scenario exposed this, what specifically should improve
- Add 'Analysis Method' field: none | 5-whys | 6-sigma | design-framing

### Grooming (groom-backlog-item/SKILL.md)
- Classify the issue type before planning the response
- For types 2-3: require root-cause analysis output before marking groomed
- For type 4: identify the guardrail/instruction gap
- For type 5: require problem-space framing before planning

### Completion Gates (complete-implementation/SKILL.md, verify/SKILL.md)
- Verify the response was proportional to the issue type
- For types 2-4: verify the scenario that exposed the problem was addressed, not just the symptom
- For type 3 (recurring): verify a guardrail or process change was added to prevent recurrence

### Feature Verifier (feature-verifier.md)
- Check: did we improve the thing that caused the issue, or did we only patch the output?
- Check: for both human and AI consumers, is the quality of life improved for this scenario?

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Post-implementation critique of backlog #311/#312 + user refinement on process quality discipline — session 2026-03-01
- **Priority**: P1
- **Added**: 2026-03-01
- **Research questions**: None

**Research first**: How do 6 Sigma DMAIC and 5 Whys map to AI agent pipeline gates? How do GSD/BMAD-METHOD classify issue types before choosing response depth? What granularity of issue taxonomy works without becoming overhead?

## Fact-Check

**Date**: 2026-03-01 | **Claims checked**: 3

| Claim | Verdict |
|-------|---------|
| 5 Whys is a root-cause analysis technique for traceable failure chains | VERIFIED |
| 6 Sigma / DMAIC applies to recurring defect patterns via frequency measurement and guardrails | VERIFIED |
| GSD/BMAD-METHOD classify issue types before choosing response depth | REFUTED |

**REFUTED detail**: GSD offers binary mode selection (full workflow vs quick), not issue classification. BMAD-METHOD uses agent roles but has no documented issue taxonomy or response-depth routing. The research question assumed existing capability that does not exist.

**Citations**:
- Five Whys: FlowFuse (https://flowfuse.com/blog/2025/12/five-whys-root-cause-analysis-definition-examples/), Lean.org (https://www.lean.org/the-lean-post/articles/five-whys-animation/) — accessed 2026-03-01
- 6 Sigma: GoLeanSixSigma.com (https://goleansixsigma.com/dmaic-five-basic-phases-of-lean-six-sigma/), SixSigma.us (https://www.6sigma.us/six-sigma-in-focus/defect-management/) — accessed 2026-03-01
- GSD: GitHub repo (https://github.com/gsd-build/get-shit-done), BMAD docs (https://docs.bmad-method.org/) — accessed 2026-03-01

## RT-ICA

**Goal**: Add process quality discipline to the SAM pipeline so different issue types receive proportional analytical treatment (issue classification, root-cause analysis, scenario-as-target verification).

**Conditions**:
1. SAM Task Template (TASK_FILE_FORMAT.md) exists and is modifiable | AVAILABLE — file at .claude/docs/TASK_FILE_FORMAT.md
2. Grooming skill (groom-backlog-item/SKILL.md) exists and is modifiable | AVAILABLE — skill loaded in this session
3. Completion gates (complete-implementation/SKILL.md, verify/SKILL.md) exist | AVAILABLE — skills in .claude/skills/
4. Feature verifier agent (feature-verifier.md) exists | AVAILABLE — agent at plugins/python3-development/agents/feature-verifier.md
5. 5 Whys methodology is well-defined for traceable failures | AVAILABLE — VERIFIED by fact-check
6. 6 Sigma DMAIC is applicable for recurring defect patterns | AVAILABLE — VERIFIED by fact-check
7. GSD/BMAD-METHOD issue classification patterns as prior art | MISSING — REFUTED by fact-check; neither framework has issue type classification. This is novel design work, not adaptation of existing patterns.
8. Issue taxonomy granularity validated against real usage | DERIVABLE — the 5-type taxonomy (procedural/defect/recurring/guardrail/unbounded) is reasonable but needs validation against actual backlog items
9. Scenario-as-target principle has established methodology | DERIVABLE — concept is sound (similar to 'test the fix' in QA) but needs concrete gate criteria

**Decision**: APPROVED — 7 of 9 conditions are AVAILABLE or DERIVABLE. The MISSING condition (#7) was a research question, not a prerequisite — the issue already proposes its own taxonomy rather than adapting an external one. Proceed with the proposed 5-type classification as novel design.

**Assumptions to confirm**:
- The 5-type taxonomy covers the actual distribution of issues in this project (validate against recent backlog)
- Scenario-as-target verification can be expressed as concrete gate criteria for the feature verifier

## Groomed (2026-03-01)

### Priority

9/10 — Foundational quality discipline for the SAM pipeline; affects every implementation. Without issue classification and proportional response, the pipeline treats symptoms identically regardless of root cause, creating recurring defects and blocking learning.

### Impact

- Blocks: Root-cause analysis and defect prevention for backlog items; quality of life for both human operators and AI agents; long-term reliability of SAM outcomes
- Bottleneck: Every issue gets the same treatment depth regardless of type; scenarios that expose problems are not used as improvement targets

### Benefits

- Issues receive proportional analytical treatment matched to their type
- Root causes of defects are identified and fixed, not just symptoms
- Recurring patterns are prevented via guardrails and process improvements
- Scenarios that expose problems drive targeted improvements
- Both human and AI consumers have clearer, more efficient workflows

### Expected Behavior

The SAM pipeline should:

1. Classify issues before planning response (procedural | defect | recurring-pattern | missing-guardrail | unbounded-design)
2. Apply appropriate analysis methods based on type (none | 5-whys | 6-sigma | design-framing)
3. Identify and target the scenario that exposed the problem, not just the symptom
4. For recurring defects, add guardrails or process changes to prevent recurrence
5. Verification gates confirm proportional response and scenario improvement

### Desired Structure

Four artifact modifications implementing issue classification and proportional response:

1. **SAM Task Template** — Add metadata fields: `Issue Classification`, `Scenario Target`, `Analysis Method`
2. **Grooming Skill** — Classify issues during grooming; require root-cause analysis output for types 2-3; require guardrail identification for type 4; require problem framing for type 5
3. **Completion Gates** — Verify response proportionality, scenario improvement, guardrail presence for recurring patterns
4. **Feature Verifier** — Check if root cause improved (not just symptom patched); verify QoL improvement for both human and AI consumers

### Acceptance Criteria

1. Task metadata includes `Issue Classification` field with documented 5-type taxonomy
2. Task metadata includes `Scenario Target` field describing the scenario and what should improve
3. Task metadata includes `Analysis Method` field (none | 5-whys | 6-sigma | design-framing)
4. Grooming skill classifies issues before planning; requires root-cause analysis for types 2-3
5. Completion gates verify scenario was addressed (not just symptom), and proportional response occurred
6. Feature verifier checks root-cause vs symptom-only fix; checks QoL for human and AI users
7. At least 5 recent backlog items successfully classified using the new taxonomy to validate granularity

### Questions for Human

- **Taxonomy validation**: Review the 5-type taxonomy against 10 representative recent issues. Does it cover all cases? Are there cases that don't fit?
- **Scenario-as-target criteria**: What concrete questions should the groomer ask to identify "what scenario exposed this"?
- **Guardrail specificity**: For type 4 (missing guardrail), what level of specificity — process step, instruction, validation gate, or code-level check?

### Resources

| Type | Item |
|------|------|
| Skill | `/groom-backlog-item` |
| Skill | `/implement-feature` |
| Skill | `/complete-implementation` |
| Skill | `/verify` |
| Agent | @python3-development:feature-verifier |
| Agent | @development-harness:feature-verifier |
| Prior work | `.claude/rules/local-workflow.md` (SAM pipeline architecture) |
| Prior work | `.claude/docs/TASK_FILE_FORMAT.md` (task metadata schema) |
| Reference | 5 Whys — FlowFuse (https://flowfuse.com/blog/2025/12/five-whys-root-cause-analysis-definition-examples/), accessed 2026-03-01 |
| Reference | 6 Sigma DMAIC — GoLeanSixSigma.com (https://goleansixsigma.com/dmaic-five-basic-phases-of-lean-six-sigma/), accessed 2026-03-01 |

### Dependencies

- Depends on: None — this is foundational work that enables subsequent improvements
- Blocks: Root-cause analysis integration into SAM pipeline; quality discipline for backlog grooming; defect prevention workflows

### Effort

High — Modifies four critical pipeline components (task template, grooming skill, completion gates, feature verifier). Can be parallelized: task template, grooming integration, completion gates, feature verifier, validation.

### Decision

Proceed with planning. RT-ICA APPROVED. Research questions answered: 5 Whys verified for type 2, 6 Sigma verified for type 3, GSD/BMAD-METHOD do not classify issues (novel design). No blockers.