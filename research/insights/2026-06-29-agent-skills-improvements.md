---
title: "Improvement Proposals: Agent Skills"
---

## Improvement 1: Add anti-rationalization, red-flag, and evidence-verification sections to skill anatomy

**Source pattern**: "Every skill includes a 'Common Rationalizations' section — excuses agents use to skip important steps, paired with factual rebuttals." (Key Features #1, line 119-122); "Red Flags — Observable behavioral patterns indicating the skill is being violated" (Technical Architecture skill anatomy, line 87); "No skill is complete until verification passes. Every skill ends with a checklist of evidence requirements ... 'Seems right' is never sufficient." (Key Features #3, lines 127-128). Direct Relevance #1 (line 240): "The anti-rationalization table, progressive disclosure, and verification-first design patterns are directly applicable."
**Local system**: plugins/plugin-creator/skills/skill-creator/SKILL.md ("Anatomy of a Skill", lines 101-166) and plugins/plugin-creator/skills/skill-creator/references/authoring-checklist.md
**Confidence**: High
**Impact**: High
**Backlog**: #created (local-only `p1-add-anti-rationalization-red-flag-and-evidence-verification-.yaml`) — GitHub sync pending

### Current state

The skill-creator system documents skill anatomy as structural only — frontmatter, `scripts/`, `references/`, `assets/` (SKILL.md lines 101-166). The pre-publish checklist (`references/authoring-checklist.md`) covers Core Quality, Structure, Code/Scripts, and Testing, but has no item requiring a skill to anticipate and rebut the consuming agent's excuses for skipping steps, no requirement for observable violation signals, and no requirement for per-step evidence-of-completion. A Grep of `plugins/plugin-creator/skills/skill-creator` for `rationaliz|red flag|battle-tested|excuse` returns no matches. The only adjacent element is the "human-facing drift" anti-pattern table in SKILL.md Step 5 (lines 471-480), which governs the SKILL author's authoring hygiene — not content structures that stop the *consuming* agent from taking the shortest path.

### Target state

The "Anatomy of a Skill" section in SKILL.md documents three optional-but-recommended body sections for workflow/process skills: "Common Rationalizations" (excuse-to-rebuttal table), "Red Flags" (observable violation signals), and "Verification" (exit checklist with evidence requirements, not self-assessment). `references/authoring-checklist.md` gains a "Process-Skill Discipline" subsection with checklist items for each of the three structures, applicable when the skill encodes a multi-step workflow with skippable steps. Each item cites agent-skills as SOURCE.

### Measurable signal

- Grep SKILL.md for "Common Rationalizations" and "Red Flags" each returns at least one match in the Anatomy section.
- `references/authoring-checklist.md` contains a subsection (e.g. "Process-Skill Discipline") with at least three checklist items covering rationalization rebuttals, red-flag signals, and evidence-based verification.
- The new checklist items carry a SOURCE citation referencing agent-skills.

---

## Improvement 2: Add Specific/Verifiable/Battle-tested/Minimal quality bars to skill authoring checklist

**Source pattern**: "The CONTRIBUTING.md establishes clear quality bars (Specific, Verifiable, Battle-tested, Minimal) and skill format validation — directly applicable to Claude Code's skill governance." (Indirect Relevance #4, line 256).
**Local system**: plugins/plugin-creator/skills/skill-creator/references/authoring-checklist.md
**Confidence**: High
**Impact**: Medium
**Backlog**: #created (local-only `p2-add-specificverifiablebattle-testedminimal-quality-bars-to-s.yaml`) — GitHub sync pending

### Current state

`references/authoring-checklist.md` groups items under Core Quality, Structure, Code and Scripts, and Testing. The items are concrete failure-mode checks but there is no top-level set of named acceptance bars a skill must clear to be publishable. Agent Skills establishes four explicit named bars in CONTRIBUTING.md — Specific, Verifiable, Battle-tested, Minimal. The local checklist contains adjacent items (e.g. "Tested with real usage scenarios, not synthetic ones" maps to Battle-tested; "Every instruction justifies its token cost" maps to Minimal) but they are scattered and unnamed, so no single governance gate exists.

### Target state

`references/authoring-checklist.md` opens with a "Quality Bars" section listing the four named bars — Specific, Verifiable, Battle-tested, Minimal — each with a one-line definition and a pointer to the existing detailed checklist items that satisfy it. The section cites agent-skills CONTRIBUTING.md as SOURCE. Existing items are not removed; the bars provide a named index over them.

### Measurable signal

- `references/authoring-checklist.md` contains a "Quality Bars" section naming all four bars: Specific, Verifiable, Battle-tested, Minimal.
- Each bar has a one-line definition and references at least one existing checklist item that evidences it.
- The section carries a SOURCE citation to agent-skills CONTRIBUTING.md.

---

## Deferred Proposals (confidence too low to backlog)

None.

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Quality Gate Model — five-phase gating workflow (Specify → Plan → Tasks → Implement) (Direct Relevance #2) | Already covered. The DH SAM pipeline (`work-backlog-item` → groom → SAM plan → task decomposition → implement → verify) plus the skill-creator 10-step process (SKILL.md lines 290-309, including T0 baseline / TN verification gates) implement an equivalent or stronger phase-gated model. |
| Lifecycle-Aware Routing — meta-skill decision tree mapping work to the right skill (Direct Relevance #3) | Already covered by `python-engineering:specialist-skill-routing` and `plugin-creator:plugin-lifecycle` (SKILL.md line 7 routes mismatched intent to plugin-lifecycle), which provide the same incoming-work-to-skill routing function. |
| Slash Command Entry Points — phase-named commands (/spec, /plan, /build, etc.) (Direct Relevance #4) | Already covered. Skills ARE commands in this repo (a skill with `user-invocable: true` creates a slash command — plugin-creator CLAUDE.md), and DH already exposes phase commands (`/dh:planning`, `/dh:execution`, `/dh:discovery`, `/dh:complete-implementation`). |
| Specialist Personas — code-reviewer, test-engineer, security-auditor review agents (Indirect Relevance #2) | Already covered by `plugin-creator:agent-creator` (role archetypes / templates) and existing review specialists (`dh:reviewer-security`, `dh:reviewer-quality`, `dh:reviewer-performance`, `dh:reviewer-accessibility`, `python-engineering:code-reviewer`). The persona-per-perspective template already exists locally. |
