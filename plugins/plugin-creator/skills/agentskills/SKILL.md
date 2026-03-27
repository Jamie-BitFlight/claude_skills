---
name: agentskills
description: Agent Skills Open Standard reference (agentskills.io). Use when creating portable skills for Claude Code, Cursor, Gemini CLI, OpenAI Codex, VS Code, Roo Code, and 20+ compatible agents. Covers frontmatter schema, naming rules, directory structure, progressive disclosure, validation, and authoring. Load before creating cross-agent skills.
user-invocable: true
---

# Agent Skills Open Standard

The Agent Skills format is an open standard for extending AI agent capabilities with specialized knowledge and workflows. Originally developed by Anthropic, adopted by 25+ agent products.

**Source:** <https://agentskills.io>

**When to use this skill:** Before creating any skill that should be portable across multiple agent products. For Claude Code-specific features (hooks, context fork, model selection, invocation control), see `../claude-skills-overview-2026/SKILL.md` instead.

---

## SKILL.md Format

Every skill is a directory containing a `SKILL.md` file with YAML frontmatter and Markdown body:

```
skill-name/
├── SKILL.md          # Required: metadata + instructions
├── scripts/          # Optional: executable code
├── references/       # Optional: documentation loaded on demand
└── assets/           # Optional: templates, images, data files
```

### Required Frontmatter

```yaml
---
name: skill-name
description: What this skill does and when to use it.
---
```

### Optional Frontmatter Fields

```yaml
---
name: pdf-processing
description: Extract text and tables from PDF files, fill forms, merge documents.
license: Apache-2.0
compatibility: Requires git, docker, jq, and access to the internet
metadata:
  author: example-org
  version: "1.0"
allowed-tools: Bash(git:*) Bash(jq:*) Read
---
```

### Field Reference

| Field           | Required | Max Length | Constraints                                                      |
| --------------- | -------- | ---------- | ---------------------------------------------------------------- |
| `name`          | Yes      | 64 chars   | Lowercase alphanumeric + hyphens. No leading/trailing/consecutive hyphens. Must match directory name. |
| `description`   | Yes      | 1024 chars | Non-empty. Describe what + when to use. Include trigger keywords. |
| `license`       | No       | —          | License name or reference to bundled file.                       |
| `compatibility` | No       | 500 chars  | Environment requirements (products, packages, network).          |
| `metadata`      | No       | —          | Arbitrary string key-value pairs.                                |
| `allowed-tools` | No       | —          | Space-delimited pre-approved tools. Experimental.                |

### Name Validation Rules

- 1-64 characters
- Unicode lowercase alphanumeric and hyphens only (`a-z`, `0-9`, `-`)
- Must not start or end with `-`
- Must not contain consecutive hyphens (`--`)
- Must match the parent directory name

Valid: `pdf-processing`, `data-analysis`, `code-review`
Invalid: `PDF-Processing` (uppercase), `-pdf` (leading hyphen), `pdf--processing` (consecutive)

### Description Guidelines

Write in **third person**. Include both what the skill does and when to use it.

```yaml
# Good — specific, includes triggers
description: Extract text and tables from PDF files, fill forms, merge documents. Use when working with PDF files or when the user mentions PDFs, forms, or document extraction.

# Weak — vague, no triggers
description: Helps with PDFs.
```

**Preferred patterns:** Use gerund form (`processing-pdfs`) or noun phrases (`pdf-processing`). Prefer descriptive names like `pdf-processing` over generic names like `helper` or `utils`.

---

## Progressive Disclosure

Skills use three-level loading to manage context efficiently:

1. **Metadata** (~100 tokens): `name` + `description` loaded at startup for all skills
2. **Instructions** (<5000 tokens recommended): Full SKILL.md body loaded on activation
3. **Resources** (as needed): Files in `scripts/`, `references/`, `assets/` loaded on demand

**Keep SKILL.md body lean.** Move detailed reference material to separate files. Run `uvx skilllint@latest check <skill-path>` after writing and follow its guidance on token-based sizing.

### Disclosure Patterns

**Pattern 1 — High-level guide with references:**

```markdown
# PDF Processing

## Quick start
[core example]

## Advanced features
- **Form filling**: See [references/forms.md](references/forms.md)
- **API reference**: See [references/api.md](references/api.md)
```

**Pattern 2 — Domain-specific organization:**

```
bigquery-skill/
├── SKILL.md (overview + navigation)
└── references/
    ├── finance.md
    ├── sales.md
    └── product.md
```

**Pattern 3 — Conditional details:**

```markdown
For simple edits, modify XML directly.
**For tracked changes**: See [references/redlining.md](references/redlining.md)
```

**Rules:**
- Keep file references **one level deep** from SKILL.md — link directly from SKILL.md so the agent can discover content without following long chains
- For files >100 lines, include a table of contents at the top

---

## Directory Contents

### scripts/

Executable code agents can run. Should be self-contained, include helpful error messages, handle edge cases. Scripts save tokens (no code generation needed) and ensure consistency.

Make execution intent clear:
- "Run `scripts/extract.py` to extract fields" (execute)
- "See `scripts/extract.py` for the algorithm" (read as reference)

### references/

Documentation loaded on demand. Keep individual files focused — smaller files mean less context usage. Structure files >100 lines with a table of contents.

### assets/

Static resources used in output (templates, images, data files). Not loaded into context — used by the agent in its output.

---

## Authoring Best Practices

For the complete Anthropic authoring guide, see `references/best-practices.md`.

Key principles:

1. **Concise is key** — **Reason:** Claude is already smart. Include only context it doesn't have. Prefer concise examples over verbose explanations to keep the skill discoverable and efficient.
2. **Set appropriate degrees of freedom** — **Reason:** Match specificity to task fragility. High freedom for open-ended tasks; low freedom for fragile operations.
3. **Use workflows for complex tasks** — **Reason:** Clear sequential steps with checklists help agents track progress and complete multi-step work reliably.
4. **Implement feedback loops** — **Reason:** Run validator, fix errors, repeat. Validators surface issues early so agents correct before proceeding.
5. **Test with all target models** — **Reason:** Haiku may need more detail than Opus; testing across models ensures the skill works for all targets.
6. **Build evaluations first** — **Reason:** Evaluations identify real gaps before documentation. Create them before writing extensively so the skill addresses actual failures.

### What to Include

Focus skill content on:

- Instructions the agent needs to perform the task
- Step-by-step workflows, examples, and edge cases
- References to `scripts/`, `references/`, and `assets/` for details

Place user-facing docs (README, CHANGELOG, INSTALLATION_GUIDE), setup procedures, and time-sensitive details in a separate "Legacy patterns" section or external docs. Claude already knows general concepts — include only skill-specific information.

---

## Validation

Use the `skills-ref` reference library to validate:

```bash
# Validate a skill directory
skills-ref validate ./my-skill

# Read skill properties as JSON
skills-ref read-properties ./my-skill

# Generate <available_skills> XML for agent prompts
skills-ref to-prompt ./skill-a ./skill-b
```

**Python API:**

```python
from pathlib import Path
from skills_ref import validate, read_properties, to_prompt

problems = validate(Path("my-skill"))
props = read_properties(Path("my-skill"))
prompt = to_prompt([Path("skill-a"), Path("skill-b")])
```

Install: `pip install -e .` from the [skills-ref](https://github.com/agentskills/agentskills/tree/main/skills-ref) directory.

---

## Portable vs Claude Code-Specific

The open standard defines a **portable subset**. Claude Code extends it with additional frontmatter fields.

| Feature                  | Open Standard | Claude Code Extension |
| ------------------------ | ------------- | --------------------- |
| `name`                   | Yes           | Yes                   |
| `description`            | Yes           | Yes                   |
| `license`                | Yes           | Yes                   |
| `compatibility`          | Yes           | Yes                   |
| `metadata`               | Yes           | Yes                   |
| `allowed-tools`          | Yes (experimental) | Yes (extended syntax) |
| `argument-hint`          | No            | Yes                   |
| `model`                  | No            | Yes                   |
| `context: fork`          | No            | Yes                   |
| `agent`                  | No            | Yes                   |
| `user-invocable`         | No            | Yes                   |
| `disable-model-invocation` | No          | Yes                   |
| `hooks`                  | No            | Yes                   |

**For portable skills:** Use only the open standard fields. Other agents will ignore unknown fields, but keeping frontmatter clean improves compatibility.

**For Claude Code skills:** See `../claude-skills-overview-2026/SKILL.md` for the full extended schema.

---

## Detailed References

- **Full specification details**: See `references/specification.md`
- **Authoring best practices**: See `references/best-practices.md`
- **Agent integration guide**: See `references/integration.md`

## External Links

- Specification: <https://agentskills.io/specification>
- Best practices: <https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices>
- Example skills: <https://github.com/anthropics/skills>
- Reference library: <https://github.com/agentskills/agentskills/tree/main/skills-ref>
- GitHub org: <https://github.com/agentskills/agentskills>
