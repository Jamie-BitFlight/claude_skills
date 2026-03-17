# Improvement Proposals: Claude Scientific Skills

**Research entry**: ./research/skill-generation-tools/claude-scientific-skills.md
**Generated**: 2026-03-16
**Patterns assessed**: 7
**Backlog items created**: 1 (issues: #750)
**Deferred (low confidence)**: 2
**Skipped (already covered or tracked)**: 4

---

## Improvement 1: Add skill composition templates to skill-creator

**Source pattern**: "Bundled cross-domain examples: Providing multi-step workflow examples that span domains (drug discovery combining genomics + cheminformatics + clinical data) demonstrates integration patterns to agents" (Patterns Worth Adopting, item 3) and "Skill composition templates: Document patterns for agents to combine related skills" (Integration Opportunities, item 2) and "Multi-step example library: Adapt the 'Quick Examples' pattern from this repository as a reference for providing complex workflow templates" (Integration Opportunities, item 4)
**Local system**: plugins/plugin-creator/skills/skill-creator/SKILL.md
**Confidence**: High
**Impact**: Medium
**Backlog**: #750 created

### Current state

The skill-creator skill documents how to create individual skills (anatomy, frontmatter, progressive disclosure, bundled resources) but contains no guidance on composing multiple skills into compound workflows. Grep for "skill-composition", "cross-domain", and "compound workflow" across `.claude/` and `plugins/plugin-creator/skills/skill-creator/` returned zero results. The external-pattern-integrator skill handles integrating external patterns into local skills but does not address composing local skills together. Agents that need to chain skill invocations (e.g., research-curator into backlog into implement-feature) have no documented pattern to follow.

### Target state

The skill-creator skill directory contains a `references/skill-composition-patterns.md` file (or a new section in SKILL.md) with:

1. A "Skill Composition Patterns" section with 2-3 concrete examples showing how to invoke multiple skills in sequence within a single agent workflow
2. Each example names specific skills from this repo (not hypothetical ones) and shows the `Skill()` invocation sequence
3. Guidance on when to compose skills vs. create a new monolithic skill

### Measurable signal

Run: `Grep "Skill Composition" plugins/plugin-creator/skills/skill-creator/` -- at least one match. The matched file contains at least 2 concrete multi-skill workflow examples using `Skill()` invocations with real skill names from this repo.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Extended frontmatter metadata fields (license, skill-author) | Medium | The research entry's SKILL.md frontmatter includes `license` and `metadata.skill-author` per agentskills.io spec. The local system deliberately uses a minimal frontmatter set (name, description, user-invocable). Would need to verify whether agentskills.io compliance is a goal — the existing `.claude/audits/completeness-report-agentskills.md` scored 50% but no backlog item tracks closing the gap on these specific fields. The local `skilllint` validator does not enforce `license` or `skill-author`. Adding these fields to 15+ plugins would be a large change with unclear benefit for internal-only skills. |
| Centralized open-source attribution file | Low | The research entry describes a centralized `open-source-sponsors.md` acknowledging 50+ upstream projects. The local repo has no equivalent. However, this is a community/governance practice rather than a functional gap — no agent workflow fails without it, no observable behavior changes. Would need to verify whether the repo's LICENSE and per-skill citations already satisfy attribution requirements before concluding this is needed. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Comprehensive domain coverage through modular skills | Already covered — the local repo already uses self-contained skill directories with SKILL.md + references/ + scripts/ structure. Each skill is independently discoverable. |
| Skill frontmatter-based metadata (name, description) | Already covered — `name` and `description` fields are documented in skill-creator SKILL.md lines 160-173, enforced by `skilllint`, and required per local conventions. |
| Dependency isolation via uv | Already covered — the local repo uses `uv` as the primary package manager (documented in CLAUDE.md Session Start, `.claude/rules/uv-run-fallback.md`). All Python scripts run via `uv run`. |
| Documentation-as-skill pattern | Already covered — the local skill-creator explicitly documents the "references/" directory pattern for embedding curated documentation in skill files (SKILL.md lines 187-196). Progressive disclosure is a core principle. |
