# Improvement Proposals: Obsidian Skills

**Research entry**: ./research/skill-generation-tools/obsidian-skills.md
**Generated**: 2026-03-12
**Patterns assessed**: 5
**Backlog items created**: 0
**Deferred (low confidence)**: 1
**Skipped (already covered or tracked)**: 4

---

## Improvement 1: Explicit Assumed Knowledge Declaration in Skill Template

**Source pattern**: obsidian-markdown SKILL.md states "This skill covers only Obsidian-specific extensions -- standard Markdown (headings, bold, italic, lists, quotes, code blocks, tables) is assumed knowledge." (Section: Architecture > Core Design Pattern; Section: Features > 1. Obsidian Markdown Skill)
**Local system**: plugins/plugin-creator/skills/skill-creator/SKILL.md
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred -- confidence medium: the local skill-creator's "Concise is Key" section provides equivalent philosophical guidance ("Only add context Claude doesn't already have") but lacks the specific mechanism of a declared scope boundary. The init_skill.py template does not generate an "Assumed Knowledge" or "Scope Boundary" section. However, it is unclear whether adding such a template section would measurably reduce token usage in practice, since skill authors who follow the existing guidance already achieve the same effect implicitly. Verifying this would require measuring token counts of skills created with vs. without explicit assumed-knowledge statements.

### Current state

The skill-creator SKILL.md (section "Concise is Key", line ~70) instructs skill authors: "Default assumption: Claude is already very smart. Only add context Claude doesn't already have. Challenge each piece of information: 'Does Claude really need this explanation?'" The init_skill.py template generates section headers like "## Overview", "## Workflow Decision Tree", and step-based sections, but does not include an "Assumed Knowledge" or "Scope Boundary" section. As a result, skill authors receive philosophical guidance to be concise but no concrete template mechanism for declaring what the agent already knows and what the skill explicitly does NOT cover.

### Target state

The init_skill.py SKILL.md template includes an optional "## Scope" or "## Assumed Knowledge" section with a TODO placeholder. The skill-creator SKILL.md guidance recommends that domain-specific skills include an explicit statement of what knowledge the agent already possesses (e.g., "This skill covers only X-specific extensions -- standard Y is assumed knowledge"). This section is present in the template but marked optional, so skill authors can remove it if not applicable.

### Measurable signal

Read the init_skill.py generated SKILL.md template output -- it contains an "## Assumed Knowledge" or "## Scope" section with a TODO placeholder. At least 1 existing skill in the repository includes an explicit assumed-knowledge statement. The skill-creator SKILL.md body contains guidance recommending explicit scope boundary declarations for domain-specific skills.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Explicit assumed knowledge declaration in skill template | Medium | Local skill-creator provides equivalent philosophical guidance ("Only add context Claude doesn't already have") but lacks the specific template mechanism. Would need to measure token impact of explicit vs. implicit assumed-knowledge statements to confirm the gap is material. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Atomic skill decomposition by feature domain | Already covered in skill-creator SKILL.md "Anatomy of a Skill" section and init_skill.py template which generates structured section headers (Overview, Workflow Decision Tree, Steps). The Obsidian approach (Workflow, Syntax, Examples, References) is a domain-specific instantiation of the same pattern. |
| Multi-format document handling (Markdown/YAML/JSON/CLI) | Too abstract -- this describes an application-domain feature of Obsidian, not an agent infrastructure pattern applicable to the local skill system. |
| Multi-platform installation and distribution | Already covered by the local plugin system: marketplace installation (`/plugin marketplace add`), manual installation, and plugin.json-based distribution with version bumping. |
| Reference documentation on-demand loading | Already covered in skill-creator SKILL.md (lines 187-196) which extensively documents the references/ subdirectory pattern for keeping SKILL.md lean while making detailed information discoverable on demand. |
