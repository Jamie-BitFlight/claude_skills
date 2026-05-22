---
name: audit-skill-completeness
description: Evaluate a single skill's quality against its stated purpose. Classifies the skill's purpose type, then scores applicable quality categories — universal dimensions always apply; structural dimensions (scripts, references, assets) are scored only when warranted by the skill's purpose. A focused 20-line behavioral skill with no bundled resources scores fully on all applicable categories. Use when auditing skill quality, checking marketplace readiness, evaluating skill completeness, performing pre-publication evaluation.
argument-hint: <skill-path>
model: sonnet
user-invocable: true
---

If the user's intent does not match the purpose of this skill, load `plugin-lifecycle` to route to the right skill and process: `Skill(skill="plugin-creator:plugin-lifecycle")`.

# Audit Skill Completeness

## Core Principle

**The primary evaluation question is: "Does this skill have everything it needs to achieve its stated purpose reliably?"**

Scripts, references, and assets are extension patterns — each is warranted when the skill's purpose calls for it and unnecessary when it does not. Their absence is only a gap when the purpose requires them. A small, complete, purpose-aligned skill scores as complete; a skill with unused scripts and padding scores lower than one with clear, sufficient instructions.

## When to Use

- Pre-marketplace publication review — verify skill meets quality standards
- Post-creation quality check — evaluate newly created skills
- Skill improvement planning — identify specific quality gaps
- Marketplace readiness assessment — determine if skill is publication-ready

## Workflow

### Step 1: Discovery

Read the skill directory structure:

```text
skill-path/
├── SKILL.md          # Required - main skill definition
├── scripts/          # Optional - executable automation (when warranted)
├── references/       # Optional - supporting documentation (when warranted)
└── assets/           # Optional - reusable output resources (when warranted)
```

**Actions:**

1. Verify SKILL.md exists; report error and exit if missing
2. Read SKILL.md frontmatter and body
3. Note any scripts/, references/, assets/ directories and their contents

### Step 2: Classify purpose type

Classify the skill into one of these purpose types based on the frontmatter description and body:

| Purpose Type | Characteristics | Scripts | References | Assets |
|---|---|---|---|---|
| **Behavioral / enforcement** | Teaches Claude how to approach a problem; enforces standards or constraints through instructions | Not warranted — behavior is internalized, not scripted | Only if domain-specific lookup needed | Not warranted |
| **Tool / format wrapping** | Wraps fragile operations on file formats (DOCX, PDF, XLSX, images) | Warranted — fragile transforms benefit from deterministic scripts | Warranted — format specs, schemas | Often warranted — templates |
| **Workflow orchestration** | Multi-step process coordination; skill-creation, plugin lifecycle | Often warranted — scaffolding scripts useful | Often warranted — process patterns | Sometimes |
| **Reference / knowledge** | IS the reference material; provides domain knowledge | Not warranted | The reference files ARE the product | Not warranted |
| **Domain expertise** | Encodes expert conventions (financial modeling, legal drafting) | Not warranted | Warranted — lookup tables, standards | Not warranted |

If the skill spans multiple types, apply the union of warranted categories.

### Step 3: Evaluate quality categories

Five categories are **universal** (always scored). Three are **conditional** (scored only when warranted by purpose; marked N/A otherwise).

**Universal categories:**

| Category | Evaluates |
|----------|-----------|
| **Preparation** | Prerequisites met before work begins |
| **Progression** | Concrete steps with right level of control |
| **Verification** | Output correctness confirmed before declaring success |
| **Examples** | Teaching through demonstration |
| **Anti-Patterns** | Explicit "what NOT to do" documentation |

**Conditional categories — apply warranted test first:**

| Category | Warranted when... |
|----------|-------------------|
| **Scripts** | The skill involves operations that are fragile, error-prone, or would be rewritten by the agent each invocation; deterministic code improves reliability |
| **References** | The skill requires domain-specific knowledge (API formats, schemas, conventions, standards) that an AI cannot reliably generate from training data |
| **Assets** | The skill produces output that uses templates, fonts, images, or boilerplate that should be bundled for use (not read into context) |

If a conditional category is not warranted: record N/A. Do not count it in the score denominator. Do not list its absence as a gap. Do not recommend adding it.

For each applicable category:

1. Read the category definition from [./references/skill-completeness-checklist.md](./references/skill-completeness-checklist.md)
2. Review checklist items for that category
3. Search SKILL.md and supporting files for evidence
4. Score 0–3 based on rubric (below)
5. Document findings with file:line references

### Step 4: Score and report

Calculate overall score. Denominator = 15 (universal) + 3 × (number of applicable conditional categories).

Write report to `.claude/audits/completeness-report-{skill-slug}.md`.

**Report Structure:**

```markdown
# Skill Completeness Report: {skill-name}

**Evaluated:** {timestamp}
**Skill Path:** {path}
**Purpose type:** {type}
**Conditional categories applicable:** Scripts={Yes|No}, References={Yes|No}, Assets={Yes|No}

## Overall Score: {score}/{applicable-max} ({percentage}%)

| Category | Applicable | Score | Label | Findings |
|----------|-----------|-------|-------|----------|
| 1. Preparation | Yes | 2 | Adequate | Environment checks present |
| 2. Progression | Yes | 3 | Exemplary | Clear workflow, decision tree |
| 3. Verification | Yes | 2 | Adequate | Steps defined, no automation |
| 4. Scripts | No | N/A | — | Not warranted for this skill type |
| 5. Examples | Yes | 2 | Adequate | Working examples, common cases covered |
| 6. Anti-Patterns | Yes | 3 | Exemplary | Failure modes with corrections |
| 7. References | No | N/A | — | Not warranted for this skill type |
| 8. Assets | No | N/A | — | Not warranted for this skill type |

## Category Details

### 1. Preparation (2/3 - Adequate)

**Evidence found:**
- ✅ Environment check at SKILL.md:45-50
- ✅ Input validation at SKILL.md:65
- ❌ Missing: {specific gap}

**Recommendation:**
{Concrete recommendation}

### 4. Scripts (N/A — not warranted)

This skill enforces behavior through instructions Claude internalizes. Scripts are not warranted.
No gap. No recommendation.

...

## Recommendations for Improvement

Only list recommendations for applicable categories with scores below 3:

1. **High Priority:** {recommendation} (Category)
2. **Medium Priority:** {recommendation} (Category)
```

**Output Location:** `.claude/audits/completeness-report-{skill-slug}.md`. Create `.claude/audits/` if it does not exist.

## Scoring Rubric

Each **applicable** category is scored 0–3:

| Score | Label | Meaning |
|-------|-------|---------|
| **0** | None | Category not addressed — no evidence found |
| **1** | Minimal | Basic attempt, significant gaps |
| **2** | Adequate | Meets expectations, minor gaps |
| **3** | Exemplary | Fully addressed, matches Anthropic quality patterns |

**Universal category guidelines:**

- **Preparation (0-3):**
  - 0: No environment checks, no input validation
  - 1: Environment checks OR input validation present
  - 2: Both environment checks AND input validation present
  - 3: Full prerequisite verification, input inspection, structured pre-flight

- **Progression (0-3):**
  - 0: No clear workflow defined
  - 1: Workflow mentioned but steps are vague or incomplete
  - 2: Clear step sequence with decision points
  - 3: Clear steps, decision trees, degree-of-freedom calibration appropriate to task fragility

- **Verification (0-3):**
  - 0: No verification steps mentioned
  - 1: Manual verification suggested but not specified
  - 2: Verification steps defined with acceptance criteria
  - 3: Explicit error-correction loop (verify → fix → re-verify)

- **Examples (0-3):**
  - 0: No examples provided
  - 1: Abstract descriptions or pseudocode only
  - 2: Concrete examples covering common cases
  - 3: Examples covering common AND edge cases, with exact input→output pairs

- **Anti-Patterns (0-3):**
  - 0: No anti-patterns documented
  - 1: Anti-patterns mentioned but not demonstrated
  - 2: Anti-patterns shown with corrections
  - 3: Anti-patterns shown with corrections AND reasoning for why the wrong form fails

**Conditional category guidelines (only when warranted):**

- **Scripts (0-3, or N/A):**
  - N/A: Skill's purpose does not involve fragile or repetitive operations
  - 0: Warranted but no scripts provided
  - 1: 1-2 scripts, limited coverage of core operations
  - 2: Scripts cover core operations with error handling
  - 3: Comprehensive coverage; scripts self-document with --help; edge cases handled

- **References (0-3, or N/A):**
  - N/A: Skill's purpose does not require domain knowledge beyond training data
  - 0: Warranted but no reference material bundled
  - 1: External links only — not bundled for offline use
  - 2: Reference files bundled, organized by topic
  - 3: Reference files linked from the specific workflow steps where they're needed

- **Assets (0-3, or N/A):**
  - N/A: Skill does not produce output requiring bundled resources
  - 0: Warranted but no assets provided
  - 1: 1-2 asset files present
  - 2: Assets organized, cover the main output types
  - 3: Comprehensive asset library with clear usage instructions

## Quality Categories Reference

Detailed checklist items and Anthropic skill examples: [./references/skill-completeness-checklist.md](./references/skill-completeness-checklist.md)
