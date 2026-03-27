---
name: refactor-skill
description: Assess and refactor oversized or multi-domain skills. First determines whether splitting or references/ extraction is appropriate — then executes the correct action. Use when a skill exceeds token thresholds (SK006/SK007) or covers multiple independent domains. Performs candidate assessment before any structural changes; cohesive single-intent skills are redirected to references/ extraction instead of splitting. When splitting is warranted — domain analysis gate, split plan, new SKILL.md generation, validation, and backwards-compatible facade conversion.
argument-hint: path to skill directory (or plugin) to refactor
model: opus
user-invocable: true
---

Refactoring LLM resources and prompts is the intentional restructuring of prompt content, tool definitions, and supporting context (e.g., skills, instructions, examples, guardrails) to improve composability, clarity, reuse, and invocation precision without changing the underlying capabilities, knowledge coverage, or output semantics of the original monolithic prompt.

At the architecture level, this refactoring decomposes a monolithic LLM skill into smaller, purpose-built, independently invocable skills with well-defined responsibilities, inputs, and outputs—reducing coupling and cognitive load, enabling targeted reuse and testing, and preserving behavioral parity through explicit contracts, shared primitives, and regression validation against the original monolith.

## Refactoring Workflow

You are focused on refactoring the skill found at the path: <path>$ARGUMENTS</path>

If no path is provided STOP and say: "No path provided. Please provide a path to a skill or plugin to refactor."
If the path points to a claude code plugin load the Skill `claude-plugins-reference-2026` which provides the current spec and details for how a plugin is defined, when provided a plugin path, you will be refactoring the skills found within the plugin skills/ directory.

The paths provided below, like `references/` are relative to the skill directory.

<workflow>

### Phase 0: Candidate Assessment (GATE)

Before analyzing for a split, determine whether skill splitting is the appropriate action at all.

**Step 1 — Measure size and read the skill:**

1. Run the plugin validator to get the token count and any error codes:
   `uvx skilllint@latest check <skill-path>`
2. Read the complete SKILL.md — every line, every section.

**Step 2 — Determine the correct path:**

```mermaid
flowchart TD
    Start([Skill flagged for review]) --> Q1{Validator reports SK007 error?}
    Q1 -->|Yes — token error threshold exceeded| Split[Proceed to Phase 1 - Domain Analysis]
    Q1 -->|No — SK006 warning or below| Q2{Is content cohesive?<br>Single user intent, sequential workflow,<br>phases that depend on each other}
    Q2 -->|Yes — cohesive single-intent skill| Refs[References/ Extraction Path<br>Move detailed reference content to ./references/<br>Link from main skill — STOP here]
    Q2 -->|No — multiple independent intents| Q3{Count domain signals<br>from Phase 1 criteria<br>How many are genuinely present?}
    Q3 -->|Fewer than 2 signals present| NotCandidate[OUTPUT: Not a candidate for skill splitting<br>Recommend references/ extraction instead<br>STOP — do not proceed to Phase 1]
    Q3 -->|2 or more signals present| Split
```

**SK006 vs SK007 threshold distinction:**

The plugin validator defines two token thresholds (see `TOKEN_WARNING_THRESHOLD` and `TOKEN_ERROR_THRESHOLD` in `skilllint`):

- **SK006 (warning):** Token count exceeds warning threshold. First action is `references/` extraction. Only proceed to skill splitting if content covers genuinely independent domains with separate invocation triggers.
- **SK007 (error):** Token count exceeds error threshold. Skill splitting is required — proceed directly to Phase 1.

If the skill is at SK006 but not SK007, exhaust `references/` extraction options before proceeding to skill splitting.

**References/ extraction path (when content is cohesive):**

When the only issue is token count (SK006) and the skill covers a single user intent:

1. Identify sections with detailed reference content — large tables, comprehensive examples, multi-step procedures that are consulted rather than executed sequentially.
2. Move each such section to `./references/<topic>.md`.
3. Replace the section in SKILL.md with a brief summary and a markdown link: ``references/topic.md``.
4. Re-run the validator to confirm token count is now below the warning threshold.
5. Report the token reduction achieved and STOP — do not proceed to skill splitting.

**STOP condition:** If the Phase 0 assessment concludes that skill splitting is not warranted, output the finding, recommend the appropriate alternative (references/ extraction or no action), and STOP. Do not proceed to Phase 1.

---

### Phase 1: Domain Analysis (GATE)

ANALYZE the source skill thoroughly to determine whether splitting is warranted:

1. **Read the complete SKILL.md** - every line, every section
2. **Read all reference files** in `references/` subdirectory
3. **Identify domains** - distinct topics, use cases, or tool patterns
4. **Map dependencies** - which sections reference others
5. **Assess size** - token counts per section (via validator), total complexity
6. **Note frontmatter** - tools, hooks, model requirements per domain

**Domain Identification Criteria:**

Evaluate each signal explicitly. Document each as PRESENT or ABSENT with evidence before proceeding.

| Signal | Indicates Separate Skill | Notes |
| --- | --- | --- |
| Different tool requirements | `tools` would differ between sections | Must be actual tool divergence, not task delegation |
| Different invocation triggers | Description keywords diverge | Sections serve different user intents at the point of invocation |
| Independent use cases | Can be used without the other | Each section must be meaningful when invoked alone |
| Different expertise domains | Distinct knowledge areas | Sections require different reference knowledge, not just different phases |
| Section size >200 lines with distinct trigger | Large AND has its own invocation trigger | A large section with detailed reference content is a candidate for `references/` extraction, not skill splitting. This signal applies only when the section also has an independent invocation trigger. |
| Different hook requirements | Lifecycle needs differ | |

**GATE: Evaluate the signal count before proceeding.**

- Document each criterion as PRESENT or ABSENT with a one-sentence evidence statement.
- If fewer than 2 signals are PRESENT: this skill does not meet the criteria for splitting. Output the signal evaluation, state "Not a candidate for skill splitting," recommend `references/` extraction if token count warrants action, and STOP.
- If 2 or more signals are PRESENT: proceed to Phase 2.

### Phase 2: Planning

PROPOSE a refactoring plan before executing:

```markdown
## Refactoring Plan: {original-skill-name}

### Current State
- Total lines: N
- Domains identified: N
- Reference files: N

### Proposed Skills

#### 1. {new-skill-name-1}
- **Focus**: {single sentence describing what can be achieved with this skill}
- **Sections to include**: {list}
- **Tools needed**: {list or "none"}
- **Estimated lines**: N
- **Dependencies**: {other new skills it references}

#### 2. {new-skill-name-2}
...

### Cross-Reference Strategy
- {skill-1} will reference {skill-2} for {topic}
- Shared concepts will be in {skill-name}

### Migration Notes
- Original monolithic skill will be: converted to facade/meta-skill that loads all new specialists
- Existing references will: continue to work via the facade (backwards compatible)

### Fidelity Checklist
- [ ] All sections accounted for
- [ ] All reference files (if any) are assigned
- [ ] All tools (if any) are covered
- [ ] All hooks (if any) are migrated
- [ ] No orphaned content
```

**STOP and present plan to user before proceeding.**

### Phase 3: Execution

AFTER user approval, create new skills:

#### 3a. Create Directory Structure

For each new skill:

```
{new-skill-name}/
├── SKILL.md
└── references/
    └── {migrated-files}.md
```

#### 3b. Write SKILL.md Files

Each new SKILL.md MUST have:

**Frontmatter:**

```yaml
---
description: {focused description with trigger keywords}
allowed-tools: {only tools this skill needs}
model: {inherit or specific if needed}
user-invocable: true
---
```

**Content Structure:**

```markdown
# {Skill Title}

{One paragraph: what this skill does and when to use it}

## Related Skills

For {topic}, activate `Skill(skill: "{plugin-name}:{related-skill-name}")`.

## {Main Sections}

{Content migrated from original skill}

## References

{Links to ./references/*.md files}
```

#### 3c. Migrate Reference Files

- MOVE relevant reference files to new skill's `references/`
- UPDATE internal links to use correct relative paths
- ADD back-links to parent SKILL.md
- SPLIT shared references if needed (copy with attribution)

#### 3d. Create Cross-References

Between new skills, use skill activation syntax:

```markdown
For advanced {topic}, activate the {skill-name} skill:
Skill(skill: "{plugin-name}:{skill-name}")
```

Within same skill, use relative links:

```markdown
See [Topic Details](./references/topic.md)
```

### Phase 4: Validation

VERIFY refactoring completeness:

#### 4a. Coverage Check

Create a coverage matrix:

| Original Section | New Skill | New Location | Verified |
| ---------------- | --------- | ------------ | -------- |
| {section-name}   | {skill}   | {file:line}  | Y/N      |

**Every original section MUST appear in exactly one new skill.**

#### 4b. Fidelity Validation

For each new skill:

- [ ] Frontmatter valid (name, description present)
- [ ] Description includes trigger keywords
- [ ] Tools match content requirements
- [ ] All internal links resolve
- [ ] Reference files properly linked
- [ ] Cross-references to related skills present
- [ ] Token count within threshold (run `uvx skilllint@latest check <skill-path>` and follow its guidance on sizing)

#### 4c. No-Loss Verification

Compare capabilities:

```
ORIGINAL SKILL CAPABILITIES:
- {capability 1}
- {capability 2}
...

NEW SKILLS COMBINED CAPABILITIES:
- {capability 1} -> {skill-name}
- {capability 2} -> {skill-name}
...

MISSING: {none or list}
DUPLICATED: {none or list with justification}
```

### Phase 5: Backwards-Compatible Conversion (MANDATORY)

CONVERT the original skill to a facade/meta-skill that loads all new specialist skills:

**CRITICAL: This step is NOT optional. Deleting the original skill is a breaking change.**

1. **Convert original to meta-skill** - REPLACE content with facade that loads all new skills:

```yaml
---
description:"{Original description}. Loads focused specialist skills: {skill-1}, {skill-2}, {skill-3}."
user-invocable: true
---

# {Original Name}

This skill loads focused specialist components for comprehensive coverage:

## Specialist Skills

- **{skill-1}**: {description} - `Skill(skill: "{plugin-name}:{skill-1}")` for {use case}
- **{skill-2}**: {description} - `Skill(skill: "{plugin-name}:{skill-2}")` for {use case}
- **{skill-3}**: {description} - `Skill(skill: "{plugin-name}:{skill-3}")` for {use case}

## Usage

**Full coverage**: `Skill(skill: "{plugin-name}:{original-name}")` loads all specialist skills
**Focused work**: Activate specific specialist skill for targeted context

## Quick Reference

{Brief summary of when to use which specialist skill}
```

2. **Verify backwards compatibility**:

   - Search for all references: `grep -r "Skill(skill: \"{plugin-name}:{original-name}\")" .`
   - Search for all slash command invocations: `grep -r "/{original-name}" .`
   - Confirm all existing references will continue to work

3. **Update external references** - other skills/commands can optionally point to specific specialists, but MUST NOT be required to change

</workflow>

## Frontmatter Best Practices

<frontmatter_rules>

### Name Field

- Lowercase letters, numbers, hyphens only
- Max 64 characters
- Descriptive but concise: `python-async`, `git-workflow`, `api-design`

### Description Field

Follow the official Anthropic guidance in the `write-frontmatter-description` skill.

**Key requirements:**

- Max 1024 characters (first 1024 chars are critical)
- Single-line only (no YAML multiline indicators)
- Complete and informative explanation of what it does and when to use it
- Include trigger scenarios, file types, or tasks

**Example:**

```yaml
description: 'Debug Python async code, identify race conditions, fix deadlocks. Handles asyncio, aiohttp, and concurrent Python code. Helps with coroutines, event loops, and async context managers.'
```

### allowed-tools Field

When making single task skills include tools the skill actually needs to help reduce context noise:
This includes MCP servers, Bash commands, and whatever other tools this skill needs to perform its task.

```yaml
allowed-tools: Read, Grep, Glob, mcp__sequential_thinking__*, mcp__git-forensics__*, mcp__ref__*, mcp__context7__*         # Read-only analysis with web based fact checking
allowed-tools: Bash(pytest:*), Bash(uv run pytest:*)             # Specific command patterns for testing
```

</frontmatter_rules>

## Splitting Strategies

<strategies>

### By Use Case

Split when skill serves multiple distinct user needs:

```
python-development -> python-testing
                   -> python-packaging
                   -> python-async
                   -> python-typing
```

### By Tool Requirements

Split when sections need different tool access:

```
code-review -> code-review-read-only (Read, Grep, Glob, mcp__git-forensics__*, Bash(ruff:*), Bash(pytest:*), Bash(uv run ruff:*), Bash(uv run pytest:*))
            -> code-review-with-fixes (Read, Write, Edit, Bash(ruff:*), Bash(pytest:*), Bash(uv run ruff:*), Bash(uv run pytest:*))
```

### By Expertise Domain

Split when skill covers distinct knowledge areas:

```
web-development -> frontend-react
                -> backend-api
                -> database-design
                -> deployment-docker
```

### By Complexity Level

Split when skill has beginner and advanced content:

```
git-workflow -> git-basics
             -> git-advanced
             -> git-team-workflows
```

### By Lifecycle Phase

Split when skill covers different project phases:

```
project-setup -> project-init
              -> project-config
              -> project-ci-cd
```

</strategies>

## Quality Standards

<quality>

### Each New Skill MUST

1. Have a single, clear focus
2. Be usable independently (or document dependencies)
3. Have description with trigger keywords
4. Pass token-count validation (run `uvx skilllint@latest check <skill-path>` and follow its guidance on sizing)
5. Use progressive disclosure (link to references)
6. Cross-reference related skills appropriately

### Refactoring MUST NOT

1. Lose any information from original
2. Create orphaned reference files
3. Break existing workflows
4. Duplicate content without justification
5. Create circular dependencies
6. Over-fragment (don't create skills too small to be independently useful — at least a few meaningful instructions)
7. **DELETE the original skill** - it MUST become a facade/meta-skill that loads all new specialist skills
8. **INTRODUCE breaking changes** - existing references to the original skill (e.g., `Skill(skill: "python3-development:python3-development")` or `/python3-development`) MUST continue to work

### Minimum Viable Skill Size

A skill should have enough substance to be useful alone:

- Enough meaningful content to be independently useful (at least 2-3 distinct instructions)
- At least 2-3 distinct instructions or rules
- Clear value proposition in description

</quality>

## Report Format

<report>

After completing refactoring, produce:

```markdown
# Skill Refactoring Report: {original-skill-name}

## Summary
- **Original**: {lines} lines, {sections} sections
- **Result**: {N} new skills
- **Coverage**: 100% (all content migrated)

## New Skills Created

| Skill | Lines | Focus | Location |
|-------|-------|-------|----------|
| {name} | N | {focus} | `skills/{name}/` |

## Cross-Reference Map

```

{skill-1} <---> {skill-2} (shared: {topic})
{skill-2} ----> {skill-3} (references: {topic})

```

## Migration Details

### {new-skill-1}
- **Source sections**: {list from original}
- **Reference files**: {list}
- **New content added**: {if any}

### {new-skill-2}
...

## Validation Results

| Check | Status |
|-------|--------|
| All sections migrated | PASS/FAIL |
| No orphaned references | PASS/FAIL |
| All links valid | PASS/FAIL |
| Frontmatter valid | PASS/FAIL |
| Size limits respected | PASS/FAIL |

## Action Items

- [ ] Review new skills for accuracy
- [ ] Test skill activation triggers
- [ ] Verify facade/meta-skill loads all new specialists
- [ ] Test backwards compatibility with existing references
- [ ] Test with `claude --plugin-dir ./plugins/plugin-name`
```

</report>

## Example Invocations

```
Agent(
  agent="plugin-creator:refactor-skill",
  prompt="Refactor ./plugins/python3-development/skills/python3/SKILL.md into focused skills for testing, async, and packaging"
)
```

```
Agent(
  agent="plugin-creator:refactor-skill",
  prompt="The fastmcp-creator skill is too large. Analyze it and propose how to split it into smaller skills"
)
```

```
Agent(
  agent="plugin-creator:refactor-skill",
  prompt="Split the git-workflow skill by expertise level: basics, advanced, and team workflows"
)
```

## Interaction Protocol

<interaction>

### Starting Refactoring

WHEN invoked:

1. CONFIRM the skill path
2. RUN validator and READ the complete skill and all references (Phase 0)
3. ASSESS candidate status — output finding and STOP if not a split candidate
4. ANALYZE for domain signals with explicit PRESENT/ABSENT evaluation (Phase 1)
5. STOP if fewer than 2 signals are PRESENT — output finding and recommend alternative
6. PRESENT refactoring plan only if Phase 1 gate passes (Phase 2)

### During Execution

AS you create skills:

- ANNOUNCE each skill: "Creating skill: {name}..."
- SHOW frontmatter for validation
- REPORT reference file migrations
- FLAG any decisions made

### Completion

WHEN finished:

- PRESENT refactoring report
- HIGHLIGHT any concerns or edge cases
- REMIND to test with `claude --plugin-dir ./plugins/plugin-name`
- OFFER to adjust if needed

</interaction>
