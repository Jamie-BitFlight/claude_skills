# Improvement Proposals: Agent Skills

**Research entry**: ./research/skill-generation-tools/agent-skills.md
**Generated**: 2026-07-07
**Patterns assessed**: 5
**Backlog items created**: 1 (issues: #2722)
**Deferred (low confidence)**: 1
**Skipped (already covered or tracked)**: 3

---

## Improvement 1: Add anti-rationalization table pattern to skill-creator authoring guidance

**Source pattern**: "Anti-rationalization. Every skill includes a table of common excuses agents use to skip steps (e.g., 'I'll add tests later') with documented counter-arguments." (research entry, Key Features > Consistent Skill Anatomy; lines 127, 131) — paired with a "Red Flags" section of "signs something's wrong" in the standard skill anatomy.
**Local system**: plugins/plugin-creator/skills/skill-creator/SKILL.md and plugins/plugin-creator/skills/skill-creator/references/authoring-checklist.md
**Confidence**: High
**Impact**: Medium
**Backlog**: #2722 created

### Current state

The skill-creator authoring guidance provides no pattern for defending workflow-enforcing skills against agents skipping steps. The "Anatomy of a Skill" section of `plugins/plugin-creator/skills/skill-creator/SKILL.md` (lines 101-166) enumerates only frontmatter, body, and bundled resources — it does not mention a rationalization or red-flags component. The pre-publish `authoring-checklist.md` (Core Quality / Structure / Code and Scripts / Testing sections) has no checklist item for an anti-rationalization or Red Flags section. A grep of both files for "rationalization" and "red flag" returns zero matches. The repo cares intensely about this failure mode — CLAUDE.md and the rules directory repeatedly guard against agents "defaulting to the shortest path" and skipping verification/quality gates — but the defense lives only as ad-hoc prose in CLAUDE.md and rules, never as a reusable component that authored skills can embed.

### Target state

skill-creator documents an optional anti-rationalization component for workflow-enforcing skills: a two-column table (Rationalization | Counter-argument) plus an optional Red Flags list, with a short authoring rule for when to include it (skills that enforce a multi-step discipline containing skippable quality gates). The pre-publish `authoring-checklist.md` gains a checklist item covering it. Observable: `grep -ri "rationalization" plugins/plugin-creator/skills/skill-creator/` returns matches in both the SKILL.md (or a references file it links) and `authoring-checklist.md`.

### Measurable signal

1. `authoring-checklist.md` contains a checkbox line referencing an anti-rationalization / Common Rationalizations section for workflow-enforcing skills.
2. skill-creator SKILL.md or a linked references file documents the two-column table shape with at least one concrete example row (e.g. "I'll add tests later" → counter-argument).
3. `grep -ri "rationalization" plugins/plugin-creator/skills/skill-creator/` is non-empty.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Verification / evidence-requirements exit criterion — every process skill ends with explicit evidence requirements ("tests passing, build output, runtime data"), research lines 129, 153 | Medium | The local `authoring-checklist.md` already carries partial coverage ("Validation and verification steps present for critical operations" and "Feedback loops included for quality-critical tasks", lines 45-46). To raise confidence, would need to verify whether the intended stronger mechanism — a mandated per-skill "Verification" exit section distinct from script-level validation — is genuinely absent across the skill-creator anatomy and authoring guidance, versus already satisfied in spirit. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Consistent Skill Anatomy / "Process, not prose" (fixed sections: Overview, When to Use, Process, Rationalizations, Red Flags, Verification) | Too abstract as a whole — the local skill-creator deliberately favors progressive disclosure and conciseness over a fixed section template (SKILL.md Core Principles). The one concrete, novel, high-value sub-element (anti-rationalization table) is captured in Improvement 1; the rest is a philosophical difference, not an observable gap. |
| `using-agent-skills` meta-skill that maps incoming work to the right skill (research lines 104, 160) | Already covered — `plugin-creator:plugin-lifecycle` routing and `python-engineering:specialist-skill-routing` provide equivalent work-to-skill routing. |
| `/build auto` autonomous plan-generate-and-execute mode with pause-on-failure (research line 64) | Already covered — SAM dispatch (`dh:dispatch`, `dh:implement-feature`) and the wave/task execution model provide plan-then-execute with quality gates and stop conditions. |

