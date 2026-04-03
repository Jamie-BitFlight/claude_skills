# Improvement Proposals: Stop Slop

**Research entry**: ./research/ai-writing-tools/stop-slop.md
**Generated**: 2026-04-03
**Patterns assessed**: 8
**Backlog items created**: 0
**Deferred (low confidence)**: 4
**Skipped (already covered or tracked)**: 4

---

## Improvement 1: Add prose quality validation rule to research entry validator

**Source pattern**: "Scoring rubric as validation gate: The 5-dimensional rubric (Directness, Rhythm, Trust, Authenticity, Density) can be adapted for content quality gates." (Patterns Worth Adopting, item 2)
**Local system**: .claude/skills/research-curator/references/validation-rules.md
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred -- confidence Medium: The research-curator validation script checks structural completeness (9 required sections, header fields, empty sections) but has no prose quality checks. However, applying a 5-dimensional rubric programmatically would require an LLM pass during validation, not a script check. The validation-rules.md distinguishes script-handled (mechanical) vs agent-handled (content) issues. A prose quality check would fall into the agent category, but the current agent fix flow is designed for missing/stale content, not stylistic revision. It is unclear whether adding an LLM-based prose quality gate to the validate mode would produce consistent results or create noise.

### Current state

`validate_research.py` checks structure (section_completeness, header_fields, empty_sections), freshness (statistics_currency, freshness_tracking), and formatting (url_format, access_dates, formatting_suggestions). No check examines prose quality, AI writing patterns, or directness of language. File: `.claude/skills/research-curator/references/validation-rules.md` lines 9-26.

### Target state

A new warning-severity check `prose_quality` in validation-rules.md that flags entries containing high concentrations of throat-clearing openers, passive voice, or vague declaratives from the Stop Slop phrase catalog. Implementation would require either a keyword-matching script check (brittle but deterministic) or an agent-based review pass (accurate but expensive).

### Measurable signal

`uv run .claude/skills/research-curator/scripts/validate_research.py --json ./research/` output includes `prose_quality` check entries with severity `warning` for entries containing flagged phrases.

---

## Improvement 2: Add editorial quick-check step to skill-creator workflow

**Source pattern**: "Validation gate for SKILL.md creation: Before shipping a new skill, run Stop Slop checks on the SKILL.md file to catch throat-clearing, passive voice, and other AI tells that reduce credibility." (Integration Opportunities, item 1)
**Local system**: plugins/plugin-creator/skills/skill-creator/SKILL.md
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred -- confidence Medium: The skill-creator SKILL.md has a 7-step creation process (understand examples, plan resources, determine location, initialize, edit, package, iterate). There is no post-creation editorial review step. However, the skill-creator already emphasizes "Concise is Key" and "Challenge each piece of information" (lines 69-77). It is unclear whether adding a formal editorial checklist step would materially improve output quality beyond what the existing conciseness guidance already achieves. The skill-creator's guidance is structural ("does this paragraph justify its token cost?") rather than editorial ("does this sentence use passive voice?"), which is a different concern. A concrete gap exists but the improvement's incremental value over existing guidance needs validation.

### Current state

The skill-creator's quality guidance focuses on token budget and structural concerns: "Only add context Claude doesn't already have", "Challenge each piece of information: Does Claude really need this explanation?" (skill-creator/SKILL.md lines 69-77). No step in the workflow checks for AI writing patterns (throat-clearing, passive voice, false agency, vague declaratives). Validation is structural (frontmatter, file references, complexity tokens) via `uvx skilllint@latest check`.

### Target state

A post-edit review step in the skill-creator workflow that applies a subset of Stop Slop's quick checks relevant to AI-facing documentation: no throat-clearing openers in instructions, active voice for procedural steps, specific rather than vague declaratives. This could be a checklist in the skill-creator's "iterate" step or a reference file at `plugins/plugin-creator/skills/skill-creator/references/editorial-checklist.md`.

### Measurable signal

`plugins/plugin-creator/skills/skill-creator/SKILL.md` contains a section or reference link to an editorial checklist. The checklist includes at least 5 concrete patterns to check (e.g., "no sentences starting with 'Here's the thing'", "no passive voice in procedural steps").

---

## Improvement 3: Add before/after example format to skill documentation standards

**Source pattern**: "Before/after transformation format: The examples in references/examples.md demonstrate effective editorial teaching. Applicable to skill documentation (show the common mistake, show the fix)." (Patterns Worth Adopting, item 3)
**Local system**: plugins/plugin-creator/skills/skill-creator/SKILL.md
**Confidence**: Low
**Impact**: Low
**Backlog**: Deferred -- confidence Low: The skill-creator already uses wrong/right examples in the CLAUDE.md project instructions (delegation format, fix discipline, silent failure prevention rules all use Wrong/Right examples). The SKILL.md itself uses "WRONG/CORRECT" examples for YAML formatting (lines 119-135). The pattern is already present in the codebase. The research entry's suggestion to adopt this format is already covered in practice, though not formalized as a documentation standard.

### Current state

Wrong/Right examples already appear in CLAUDE.md rules (delegation-format.md, fix-delegation-discipline.md, silent-failure-prevention.md, large-file-write-strategy.md) and in the skill-creator SKILL.md itself (YAML multiline bug examples). The pattern is used ad-hoc rather than as a formal requirement.

### Target state

No change needed -- the pattern is already adopted. A formal requirement to include before/after examples in every rule file would add overhead without proportional value since the pattern is already used where it matters most (error-prone areas).

### Measurable signal

N/A -- pattern already present in codebase.

---

## Improvement 4: Create anti-pattern phrase catalog for agent prompts

**Source pattern**: "Comprehensive anti-pattern catalogs: The phrase and structure catalogs in references/phrases.md and references/structures.md provide a model for building reference materials that teach pattern recognition without lengthy explanations." (Patterns Worth Adopting, item 4) and "Prompt clarity audit: Use Stop Slop on agent prompts and orchestration task descriptions to eliminate rhetorical setups and vague declaratives that can cause agent misalignment." (Integration Opportunities, item 4)
**Local system**: .claude/agents/ and .claude/rules/
**Confidence**: Low
**Impact**: Medium
**Backlog**: Deferred -- confidence Low: Agent prompts in this repository are procedural and technical, not prose-heavy. The Stop Slop patterns target human-facing writing (essays, blog posts, documentation). Agent prompts use imperative instructions, mermaid diagrams, and structured formats that naturally avoid most AI writing tells. Throat-clearing and rhetorical setups are less common in agent prompts than in user-facing prose. The gap may exist in some agent files but would need a systematic audit to confirm -- the inference that agent prompts suffer from these patterns is not directly observed.

### Current state

Agent prompt files in `.claude/agents/` use structured formats (frontmatter, workflow steps, mermaid diagrams, decision trees). No catalog of prompt-specific anti-patterns exists. The CLAUDE.md rules cover delegation format, fix discipline, and silent failure prevention but not prose clarity in agent prompts specifically.

### Target state

A reference file (e.g., `.claude/rules/prompt-clarity.md`) listing prompt-specific anti-patterns adapted from Stop Slop: no rhetorical setups in task descriptions ("What if...?"), no vague declaratives in success criteria ("The implications are significant"), active voice for all instructions.

### Measurable signal

`.claude/rules/prompt-clarity.md` exists with at least 10 prompt-specific anti-patterns and concrete replacements.

---

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Scoring rubric as validation gate for research entries | Medium | Would need to validate that an LLM-based prose quality check produces consistent, actionable results during validate mode -- not just noise |
| Editorial quick-check step in skill-creator workflow | Medium | Existing "Concise is Key" guidance may already achieve the same goal; would need to audit recent skill outputs for AI writing patterns to confirm gap |
| Before/after transformation format as formal standard | Low | Pattern already adopted ad-hoc throughout codebase; formalizing it would add process overhead without evidence of current deficiency |
| Anti-pattern phrase catalog for agent prompts | Low | Agent prompts are procedural/technical and may not exhibit the prose patterns Stop Slop targets; systematic audit of agent files needed to confirm |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Quick checklist pattern (12-item diagnostic) | Too abstract to map to a single local system gap -- the concept of "checklist" is already used extensively in CLAUDE.md rules, validation-rules.md, and skill-creator SKILL.md |
| Skill documentation quality (applications item 1) | General observation, not a concrete pattern -- the research entry notes Stop Slop rules "directly apply" but does not identify a specific mechanism absent from the local system |
| Prose in research entries (applications item 2) | Research entries follow extractive methodology that naturally avoids AI writing patterns per the research entry itself ("direct quotes, specific claims") |
| Documentation linting extension (integration item 3) | Equivalent to Improvement 2 (skill-creator editorial step) -- not a separate pattern |
