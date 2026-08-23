# Agent Skills Authoring Best Practices

> Source: <https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices>

This document covers practical authoring guidance for writing effective skills that agents can discover and use successfully.

---

## Contents

- [Core principles](#core-principles)
- [Skill structure](#skill-structure)
- [Workflows and feedback loops](#workflows-and-feedback-loops)
- [Content guidelines](#content-guidelines)
- [Common patterns](#common-patterns)
- [Evaluation and iteration](#evaluation-and-iteration)
- [Advanced: executable code](#advanced-executable-code)
- [Checklist for effective skills](#checklist-for-effective-skills)

---

## Core Principles

### Concise Is Key

The context window is a public good. **Include only what the agent doesn't already know.** Prefer short examples over long explanations.

Apply these heuristics when drafting content:
- Include only skill-specific information — omit general concepts the agent already knows
- Each paragraph should justify its token cost with actionable guidance
- When in doubt, use a compact example instead of prose

**Good** (~50 tokens):

````markdown
## Extract PDF text

Use pdfplumber for text extraction:

```python
import pdfplumber
with pdfplumber.open("file.pdf") as pdf:
    text = pdf.pages[0].extract_text()
```
````

**Bad** (~150 tokens):

````markdown
## Extract PDF text

PDF (Portable Document Format) files are a common file format that contains
text, images, and other content. To extract text from a PDF, you'll need to
use a library. There are many libraries available...
````

### Set Appropriate Degrees of Freedom

Match specificity to the task's fragility:

**High freedom** (text-based instructions) — Multiple approaches valid, decisions depend on context:

```markdown
## Code review process
1. Analyze the code structure and organization
2. Check for potential bugs or edge cases
3. Suggest improvements for readability
4. Verify adherence to project conventions
```

**Medium freedom** (pseudocode/scripts with parameters) — Preferred pattern exists, some variation acceptable:

```python
def generate_report(data, format="markdown", include_charts=True):
    # Process data
    # Generate output in specified format
```

**Low freedom** (specific scripts, few parameters) — Operations fragile, consistency critical:

````markdown
## Database migration

Run exactly this script:
```bash
python scripts/migrate.py --verify --backup
```
Do not modify the command or add additional flags.
````

**Analogy:** Narrow bridge with cliffs = low freedom (exact instructions). Open field = high freedom (general direction).

### Test with All Target Models

Skills act as additions to models, so effectiveness depends on the underlying model. Test with all models you plan to use.

- **Haiku** (fast, economical): Does the skill provide enough guidance? Haiku may need more detail.
- **Sonnet** (balanced): Is the skill clear and efficient?
- **Opus** (powerful reasoning): Does the skill avoid over-explaining? Opus may find verbose skills redundant.

What works perfectly for Opus might need more detail for Haiku. If your skill will be used across multiple models, aim for instructions that work well with all of them.

---

## Skill Structure

### Naming Conventions

Use consistent naming patterns. **Gerund form** (verb + -ing) is the recommended style because it clearly describes the activity the skill provides.

- Good (gerund): `processing-pdfs`, `analyzing-spreadsheets`, `managing-databases`, `testing-code`
- Acceptable alternatives: noun phrases (`pdf-processing`) or action-oriented (`process-pdfs`)
- Avoid: vague names (`helper`, `utils`, `tools`), overly generic names (`documents`, `data`), reserved words (`anthropic-helper`, `claude-tools`)

Consistent naming makes it easier to reference skills in documentation, understand what a skill does at a glance, and maintain a cohesive skill library.

### Writing Effective Descriptions

The `description` field enables skill discovery. Include both what the skill does and when to use it.

**Write in third person.** The description is injected into the system prompt.

- Prefer: "Processes Excel files and generates reports"
- Prefer: "Extract text from PDFs. Use when the user mentions PDFs or document extraction"
- Instead of first/second person: use "Processes…" rather than "I can help you…" or "You can use this to…"

**Examples:**

```yaml
# PDF Processing
description: Extract text and tables from PDF files, fill forms, merge documents. Use when working with PDF files or when the user mentions PDFs, forms, or document extraction.

# Excel Analysis
description: Analyze Excel spreadsheets, create pivot tables, generate charts. Use when analyzing Excel files, spreadsheets, tabular data, or .xlsx files.

# Git Commit Helper
description: Generate descriptive commit messages by analyzing git diffs. Use when the user asks for help writing commit messages or reviewing staged changes.
```

### Progressive Disclosure Patterns

Keep SKILL.md body lean — aim for under 500 lines, in addition to the token-based limit. Split content into separate files when the validator warns. Run `uvx skilllint@latest check <skill-path>` after writing and follow its guidance on token-based sizing.

**Pattern 1 — High-level guide with references:**

```markdown
# PDF Processing

## Quick start
[core example]

## Advanced features
- **Form filling**: See [FORMS.md](FORMS.md)
- **API reference**: See [REFERENCE.md](REFERENCE.md)
```

**Pattern 2 — Domain-specific organization:**

```
bigquery-skill/
├── SKILL.md (overview + navigation)
└── reference/
    ├── finance.md
    ├── sales.md
    └── product.md
```

**Pattern 3 — Conditional details:**

```markdown
For simple edits, modify XML directly.
**For tracked changes**: See [REDLINING.md](REDLINING.md)
```

### Keep References One Level Deep

Link each reference file directly from SKILL.md so the agent can discover content without following long chains.

**Prefer** (one level):

```
SKILL.md → advanced.md
SKILL.md → reference.md
SKILL.md → examples.md
```

**Instead of** (too deep):

```
SKILL.md → advanced.md → details.md → actual info
```

### Structure Longer Reference Files

For files >100 lines, include a table of contents at the top so the agent can see the full scope when previewing.

---

## Workflows and Feedback Loops

### Use Workflows for Complex Tasks

Break complex operations into clear, sequential steps. Provide a checklist the agent can track:

```markdown
## PDF form filling workflow

Task Progress:
- [ ] Step 1: Analyze the form (run analyze_form.py)
- [ ] Step 2: Create field mapping (edit fields.json)
- [ ] Step 3: Validate mapping (run validate_fields.py)
- [ ] Step 4: Fill the form (run fill_form.py)
- [ ] Step 5: Verify output (run verify_output.py)
```

### Implement Feedback Loops

Common pattern: Run validator, fix errors, repeat.

```markdown
## Document editing process

1. Make edits to `word/document.xml`
2. **Validate immediately**: `python scripts/validate.py unpacked_dir/`
3. If validation fails:
   - Review the error message
   - Fix the issues
   - Run validation again
4. **Only proceed when validation passes**
5. Rebuild: `python scripts/pack.py unpacked_dir/ output.docx`
```

---

## Content Guidelines

### Use Current Patterns; Preserve Legacy in Labeled Sections

Use current methods as the default. When documenting deprecated approaches, keep them in a clearly labeled legacy section so agents know not to prefer them:

```markdown
## Current method
Use the v2 API endpoint: `api.example.com/v2/messages`

## Old patterns
<details>
<summary>Legacy v1 API (deprecated 2025-08)</summary>
The v1 API used: `api.example.com/v1/messages`
</details>
```

### Use Consistent Terminology

Choose one term and use it throughout:

- Good: Always "API endpoint", always "field", always "extract"
- Bad: Mix "API endpoint" / "URL" / "API route" / "path"
- Bad: Mix "field" / "box" / "element" / "control"

### Cross-Client Compatibility: Handling Unquoted Colons in YAML

The most common YAML parse failure when sharing skills across clients is unquoted values containing colons. A colon followed by a space is a YAML key-value separator; an unquoted value containing `:` breaks parsing.

**Symptom:** Skill fails to load in some clients but not others; frontmatter is silently ignored.

**Fix:** Quote any value that contains a colon, or use a YAML block scalar:

```yaml
# Broken — colon in value breaks YAML parsing
description: Use when working with HTTP: requests, responses, and headers.

# Fixed — quoted value
description: "Use when working with HTTP: requests, responses, and headers."

# Also valid — block scalar
description: >-
  Use when working with HTTP: requests, responses, and headers.
```

Apply this check before sharing or publishing a skill that targets multiple clients.

SOURCE: [agentskills.io integration guide](https://agentskills.io/integrate-skills.md) (accessed 2026-08-24)

---

## Common Patterns

### Template Pattern

**Strict requirements:**

```markdown
## Report structure

ALWAYS use this exact template:

# [Analysis Title]
## Executive summary
[One-paragraph overview]
## Key findings
- Finding 1 with data
## Recommendations
1. Specific recommendation
```

**Flexible guidance:**

```markdown
## Report structure

Sensible default format — adapt as needed:

# [Analysis Title]
## Executive summary
[Overview]
## Key findings
[Adapt sections based on discovery]
```

### Examples Pattern

Provide input/output pairs:

```markdown
## Commit message format

**Example 1:**
Input: Added user authentication with JWT tokens
Output:
feat(auth): implement JWT-based authentication
Add login endpoint and token validation middleware

**Example 2:**
Input: Fixed bug where dates displayed incorrectly
Output:
fix(reports): correct date formatting in timezone conversion
Use UTC timestamps consistently
```

### Conditional Workflow Pattern

```markdown
## Document modification

1. Determine type:
   **Creating new?** → Follow "Creation workflow"
   **Editing existing?** → Follow "Editing workflow"

2. Creation workflow:
   - Use docx-js library
   - Build from scratch
   - Export to .docx

3. Editing workflow:
   - Unpack existing document
   - Modify XML directly
   - Validate after each change
   - Repack when complete
```

---

## Evaluation and Iteration

### Build Evaluations First

Create evaluations BEFORE writing extensive documentation:

1. **Identify gaps**: Run agent on tasks without a skill. Document failures.
2. **Create evaluations**: Build three scenarios testing those gaps.
3. **Establish baseline**: Measure performance without the skill.
4. **Write minimal instructions**: Just enough to address gaps and pass evaluations.
5. **Iterate**: Execute evaluations, compare against baseline, refine.

**Evaluation structure:**

```json
{
  "skills": ["pdf-processing"],
  "query": "Extract all text from this PDF file and save it to output.txt",
  "files": ["test-files/document.pdf"],
  "expected_behavior": [
    "Successfully reads the PDF file",
    "Extracts text from all pages",
    "Saves extracted text to output.txt"
  ]
}
```

### Iterative Development with Two Instances

1. Work through a task with **Claude A** (the skill author)
2. Identify reusable patterns from the session
3. Ask Claude A to create a skill capturing those patterns
4. Test with **Claude B** (fresh instance with skill loaded)
5. Observe Claude B's behavior — note struggles or missed context
6. Return to Claude A with specifics to refine
7. Repeat the observe-refine-test cycle

> Claude models understand the Skill format natively. You don't need a special "writing skills" skill. Simply ask Claude to create a Skill and it will generate properly structured SKILL.md content.

### Observe How Claude Navigates Skills

As you iterate, watch how Claude actually uses your skill in practice:

- **Unexpected exploration paths**: Does Claude read files in an order you didn't expect? Your structure may not be intuitive.
- **Missed connections**: Does Claude fail to follow references? Your links may need to be more explicit or prominent.
- **Overreliance on certain sections**: If Claude repeatedly reads the same file, consider whether that content belongs in the main SKILL.md instead.
- **Ignored content**: If Claude never accesses a bundled file, it might be unnecessary or poorly signaled.

Iterate based on these observations. The `name` and `description` metadata are particularly critical — Claude uses them when deciding whether to trigger the skill at all.

---

## Advanced: Executable Code

### Solve, Don't Punt

Handle errors explicitly in scripts:

```python
def process_file(path):
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        print(f"File {path} not found, creating default")
        with open(path, "w") as f:
            f.write("")
        return ""
```

### Document Constants

```python
# HTTP requests typically complete within 30 seconds
REQUEST_TIMEOUT = 30

# Three retries balances reliability vs speed
MAX_RETRIES = 3
```

### Provide Utility Scripts

Pre-made scripts are more reliable, save tokens, save time, and ensure consistency. Make execution intent clear:

- "Run `analyze_form.py` to extract fields" (execute)
- "See `analyze_form.py` for the algorithm" (read as reference)

### Create Verifiable Intermediate Outputs

For complex tasks, use plan-validate-execute:

1. Analyze input
2. **Create plan file** (e.g., `changes.json`)
3. **Validate plan** with a script
4. Execute only if validation passes
5. Verify output

### Package Dependencies

List required packages in SKILL.md. Verify availability in the target environment.

### MCP Tool References

Use fully qualified names: `ServerName:tool_name`

```markdown
Use the BigQuery:bigquery_schema tool to retrieve table schemas.
```

---

---

## Anti-Patterns to Avoid

| Anti-pattern | Problem | Instead |
|---|---|---|
| Windows-style paths (`scripts\helper.py`) | Fails on Unix | Always use forward slashes: `scripts/helper.py` |
| Too many options without a default | Confuses Claude | Provide one preferred approach with optional alternatives |
| Assuming tools/packages are installed | Silent failures | List required packages; verify availability |
| Vague descriptions ("Helps with documents") | Poor discovery | Specific with triggers: "Extracts text from PDFs. Use when…" |
| Deeply nested references (SKILL → A → B → C) | Claude may partially read and miss info | Flat structure: SKILL links directly to each reference |
| Date-conditional logic ("If before Aug 2025…") | Becomes wrong over time | Current method as default; legacy in labeled `<details>` section |
| Mixed terminology ("endpoint" / "URL" / "route") | Claude infers equivalence incorrectly | One term per concept throughout |

---

## Checklist for Effective Skills

### Core Quality

- [ ] Description is specific and includes key terms
- [ ] Description includes both what the skill does and when to use it
- [ ] Description written in third person
- [ ] SKILL.md body passes token-count validation (run `uvx skilllint@latest check <skill-path>` and follow its sizing guidance)
- [ ] Additional details in separate files (if needed)
- [ ] Current patterns as default; legacy in clearly labeled section
- [ ] Consistent terminology throughout
- [ ] Examples are concrete, not abstract
- [ ] File references one level deep
- [ ] Progressive disclosure used appropriately
- [ ] Workflows have clear steps

### Code and Scripts

- [ ] Scripts solve problems rather than punt to agent
- [ ] Error handling is explicit and helpful
- [ ] No magic constants (all values justified)
- [ ] Required packages listed and verified
- [ ] Forward slashes for paths (e.g., `scripts/helper.py`)
- [ ] Validation/verification steps for critical operations
- [ ] Feedback loops for quality-critical tasks

### Testing

- [ ] At least three evaluations created
- [ ] Tested with Haiku, Sonnet, and Opus
- [ ] Tested with real usage scenarios
- [ ] Team feedback incorporated (if applicable)

### Preferred Alternatives

| Instead of | Use |
|------------|-----|
| Windows-style paths (`scripts\helper.py`) | Forward slashes: `scripts/helper.py` (portable) |
| Too many options without a default | One preferred approach with optional alternatives |
| Assuming tools are installed | List required packages in SKILL.md; verify availability |
| Vague descriptions ("Helps with documents") | Specific descriptions with triggers: "Extracts text from PDFs. Use when…" |
| Deeply nested references (SKILL → A → B → C) | Flat structure: SKILL links directly to each reference |
| Conditional logic on dates/versions | Current method as default; legacy in labeled section |
| Mixed terminology | One term per concept throughout |
