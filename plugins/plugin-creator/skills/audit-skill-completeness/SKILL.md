---
name: audit-skill-completeness
description: Evaluate a single skill's quality against 8 completeness categories derived from Anthropic's official skills repository. Scores preparation, progression, verification, scripts, examples, anti-patterns, references, and assets. Generates scored report to .claude/audits/. Use when auditing skill quality, checking marketplace readiness, evaluating skill completeness score, performing pre-publication evaluation, or comparing to Anthropic skills.
argument-hint: <skill-path>
model: sonnet
user-invocable: true
---
If the user's intent does not match the purpose of this skill, load `plugin-lifecycle` to route to the right skill and process: `Skill(skill="plugin-creator:plugin-lifecycle")`.


# Audit Skill Completeness

## Purpose

Evaluates a single skill directory against 8 quality categories derived from Anthropic's official skills repository. Each category is scored 0-3, producing an overall completeness percentage and actionable recommendations for improvement.

## When to Use

Invoke this skill when:

- Pre-marketplace publication review - verify skill meets quality standards
- Post-creation quality check - evaluate newly created skills
- Skill improvement planning - identify specific quality gaps
- Comparing local skills to Anthropic patterns - benchmark against official standards
- Marketplace readiness assessment - determine if skill is publication-ready

## Workflow

### Step 1: Discovery

Read the skill directory structure:

```
skill-path/
├── SKILL.md          # Required - main skill definition
├── scripts/          # Optional - executable automation
├── references/       # Optional - supporting documentation
└── assets/           # Optional - reusable output resources
```

**Actions:**

1. Verify SKILL.md exists
2. Check for scripts/, references/, assets/ directories
3. Read SKILL.md frontmatter and body
4. List all files in each directory

**Validation:**

- If SKILL.md missing, report error and exit
- If path is not a directory, report error and exit

### Step 2: Evaluate Quality Categories

Run through each of the 8 categories using the detailed checklist in `references/skill-completeness-checklist.md`.

**Quality Categories:**

| Category | Evaluates | Key Indicators |
|----------|-----------|----------------|
| **1. Preparation** | Prerequisites met before work begins | Environment verification, input inspection, metadata extraction scripts |
| **2. Progression** | Concrete steps with right level of control | Clear sequence, deterministic scripts, working examples, decision trees |
| **3. Verification** | Output correctness confirmed before success | Explicit verification steps, automated checks, error-correction loops, acceptance criteria |
| **4. Scripts** | Executable automation for core operations | Repetitive operations scripted, --help support, edge case handling, tested output |
| **5. Examples** | Teaching through demonstration | Working code with imports, exact input→output pairs, common cases, edge case handling |
| **6. Anti-Patterns** | Explicit "what NOT to do" | Known failure modes documented, bad output shown, corrections side-by-side |
| **7. References** | Domain knowledge AI cannot generate | API/schema/format documentation, organized sections, linked from workflow steps |
| **8. Assets** | Reusable output resources bundled | Templates, fonts, images, boilerplate the AI uses (not reads) |

**Evaluation Process:**

For each category:

1. Read the category definition from `references/skill-completeness-checklist.md`
2. Review checklist items for that category
3. Search SKILL.md and supporting files for evidence
4. Score 0-3 based on rubric (below)
5. Document findings with file:line references

### Step 3: Score and Report

Calculate overall score and write report to `.claude/audits/completeness-report-{skill-slug}.md`.

**Report Structure:**

```markdown
# Skill Completeness Report: {skill-name}

**Evaluated:** {timestamp}
**Skill Path:** {absolute-path}

## Overall Score: {percentage}% ({score}/24)

| Category | Score | Label | Findings |
|----------|-------|-------|----------|
| 1. Preparation | 2 | Adequate | Environment checks present, missing metadata extraction |
| 2. Progression | 3 | Exemplary | Clear workflow, deterministic scripts, decision tree |
| ... | ... | ... | ... |

## Category Details

### 1. Preparation (2/3 - Adequate)

**What was evaluated:**
- Environment verification before starting
- Input inspection before acting
- Metadata extraction scripts

**Evidence found:**
- ✅ Environment check at SKILL.md:45-50
- ✅ Input validation at SKILL.md:65
- ❌ No metadata extraction script in scripts/

**Recommendation:**
Add a script to extract structured metadata from inputs so the AI operates on verified data instead of assumptions.

### 2. Progression (3/3 - Exemplary)

...

## Recommendations for Improvement

1. **High Priority:** Add metadata extraction script (Preparation)
2. **Medium Priority:** Include anti-pattern examples (Anti-Patterns)
3. **Low Priority:** Add visual validation examples (Verification)

## Reference

This audit follows patterns from Anthropic's official skills repository:
- https://github.com/anthropics/skills

Checklist: [Skill Completeness Checklist](./references/skill-completeness-checklist.md)
```

**Output Location:**

Report written to `.claude/audits/completeness-report-{skill-slug}.md`

If `.claude/audits/` does not exist, create it.

## Scoring Rubric

Each category is scored 0-3 based on presence and quality of evidence:

| Score | Label | Meaning | Criteria |
|-------|-------|---------|----------|
| **0** | None | Category not addressed | No evidence found for any checklist items |
| **1** | Minimal | Basic attempt, significant gaps | 1-2 checklist items present, core patterns missing |
| **2** | Adequate | Meets expectations, minor gaps | 3-4 checklist items present, core patterns followed |
| **3** | Exemplary | Exceeds expectations, Anthropic patterns | All or most checklist items present, matches Anthropic quality |

**Overall Score Calculation:**

```
Sum of category scores / 24 * 100 = percentage
```

**Scoring Guidelines:**

- **Preparation (0-3):**
  - 0: No environment checks, no input validation, no metadata extraction
  - 1: Environment checks OR input validation present
  - 2: Environment checks AND input validation present
  - 3: Environment checks, input validation, AND metadata extraction scripts

- **Progression (0-3):**
  - 0: No clear workflow, AI must generate all code
  - 1: Workflow defined but no scripts or examples
  - 2: Workflow defined with scripts OR examples
  - 3: Workflow defined with scripts AND examples AND decision trees

- **Verification (0-3):**
  - 0: No verification steps mentioned
  - 1: Manual verification suggested but not enforced
  - 2: Verification steps defined with acceptance criteria
  - 3: Automated verification scripts with error-correction loops

- **Scripts (0-3):**
  - 0: No scripts provided
  - 1: 1-2 scripts, limited functionality
  - 2: 3-5 scripts covering core operations
  - 3: 6+ scripts, --help support, comprehensive coverage

- **Examples (0-3):**
  - 0: No examples provided
  - 1: Abstract examples or pseudocode only
  - 2: Working examples with imports and realistic data
  - 3: Working examples covering common AND edge cases

- **Anti-Patterns (0-3):**
  - 0: No anti-patterns documented
  - 1: Anti-patterns mentioned but not shown
  - 2: Anti-patterns shown with corrections
  - 3: Anti-patterns shown with corrections AND reasoning

- **References (0-3):**
  - 0: No reference material
  - 1: External links only (not bundled)
  - 2: 1-2 reference files in references/
  - 3: 3+ reference files, organized by topic, linked from workflow

- **Assets (0-3):**
  - 0: No assets provided
  - 1: 1-2 asset files
  - 2: 3-5 asset files, organized
  - 3: 6+ asset files or comprehensive asset library

## Output Format

Report filename: `completeness-report-{skill-slug}.md`

Where `{skill-slug}` is the skill directory name (e.g., `audit-skill-completeness` → `completeness-report-audit-skill-completeness.md`)

Report sections:

1. **Header** - skill name, path, timestamp
2. **Overall Score** - percentage and raw score
3. **Summary Table** - all categories with scores
4. **Category Details** - for each category:
   - Score and label
   - What was evaluated (checklist items)
   - Evidence found (file:line references)
   - Recommendations for improvement
5. **Recommendations Summary** - prioritized list
6. **Reference** - link to checklist and Anthropic repository

## Quality Categories Reference

All 8 categories are detailed in `references/skill-completeness-checklist.md` with:

- Checklist items for each category
- Examples from Anthropic's official skills
- Patterns observed across creative, document, and developer skills
- Rationale for why each pattern matters

## Additional Resources

- `references/skill-completeness-checklist.md` - detailed quality categories, checklist items, and examples from Anthropic's official skills repository
