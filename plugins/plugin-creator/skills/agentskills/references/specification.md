# Agent Skills Specification — Full Reference

> Source: <https://agentskills.io/specification>

This document is the complete format specification for Agent Skills.

---

## Contents

- [Directory structure](#directory-structure)
- [SKILL.md format](#skillmd-format)
  - [Frontmatter fields](#frontmatter-required)
  - [Name field rules](#name-field)
  - [Description field rules](#description-field)
  - [License field](#license-field)
  - [Compatibility field](#compatibility-field)
  - [Metadata field](#metadata-field)
  - [Allowed-tools field](#allowed-tools-field)
- [Body content](#body-content)
- [Optional directories](#optional-directories)
- [Progressive disclosure](#progressive-disclosure)
- [File references](#file-references)
- [Validation](#validation)

---

## Directory Structure

A skill is a directory containing at minimum a `SKILL.md` file:

```
skill-name/
└── SKILL.md          # Required
```

Optionally include `scripts/`, `references/`, and `assets/` directories.

---

## SKILL.md Format

The `SKILL.md` file must contain YAML frontmatter followed by Markdown content.

### Frontmatter (Required)

Minimal:

```yaml
---
name: skill-name
description: A description of what this skill does and when to use it.
---
```

With all optional fields:

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

### Field Summary

| Field           | Required | Constraints                                                      |
| --------------- | -------- | ---------------------------------------------------------------- |
| `name`          | Yes      | Max 64 chars. Lowercase letters, numbers, hyphens only. No leading/trailing/consecutive hyphens. Must match directory name. |
| `description`   | Yes      | Max 1024 chars. Non-empty. Describes what + when to use.         |
| `license`       | No       | License name or reference to bundled file.                       |
| `compatibility` | No       | Max 500 chars. Environment requirements.                         |
| `metadata`      | No       | Arbitrary string key-value mapping.                              |
| `allowed-tools` | No       | Space-delimited pre-approved tools. Experimental.                |

---

### Name Field

The required `name` field:

- Must be 1-64 characters
- May only contain unicode lowercase alphanumeric characters and hyphens (`a-z`, `0-9`, `-`)
- Must not start or end with `-`
- Must not contain consecutive hyphens (`--`)
- Must match the parent directory name

**Valid:**

```yaml
name: pdf-processing
name: data-analysis
name: code-review
name: my-tool-v2
```

**Invalid:**

```yaml
name: PDF-Processing    # uppercase not allowed
name: -pdf              # cannot start with hyphen
name: pdf--processing   # consecutive hyphens not allowed
name: pdf-              # cannot end with hyphen
```

---

### Description Field

The required `description` field:

- Must be 1-1024 characters
- Should describe both what the skill does and when to use it
- Should include specific keywords that help agents identify relevant tasks
- Write in **third person** (not "I can help" or "You can use this")

**Good:**

```yaml
description: Extracts text and tables from PDF files, fills PDF forms, and merges multiple PDFs. Use when working with PDF documents or when the user mentions PDFs, forms, or document extraction.
```

**Poor:**

```yaml
description: Helps with PDFs.
```

**Naming convention recommendation:** Use gerund form (`processing-pdfs`, `analyzing-spreadsheets`) or noun phrases (`pdf-processing`, `spreadsheet-analysis`). Prefer descriptive names over vague ones (`helper`, `utils`, `tools`).

---

### License Field

The optional `license` field:

- Specifies the license applied to the skill
- Keep short: either the license name or the name of a bundled license file

```yaml
license: Apache-2.0
license: Proprietary. LICENSE.txt has complete terms
```

---

### Compatibility Field

The optional `compatibility` field:

- Must be 1-500 characters if provided
- Only include if the skill has specific environment requirements
- Can indicate intended product, required system packages, network access needs

```yaml
compatibility: Designed for Claude Code (or similar products)
compatibility: Requires git, docker, jq, and access to the internet
compatibility: Requires Python 3.14+ and uv
```

Most skills do not need this field.

---

### Metadata Field

The optional `metadata` field:

- A map from string keys to string values
- Clients can use this to store additional properties not defined by the spec
- Make key names reasonably unique to avoid conflicts

```yaml
metadata:
  author: example-org
  version: "1.0"
  category: document-processing
```

---

### Allowed-Tools Field

The optional `allowed-tools` field:

- A space-delimited list of tools that are pre-approved to run
- Experimental — support varies between agent implementations

```yaml
allowed-tools: Bash(git:*) Bash(jq:*) Read
```

---

## Body Content

The Markdown body after the frontmatter contains the skill instructions. Structure body content for best agent performance:

- **Step-by-step instructions** — Clear sequential guidance agents can follow
- **Input/output examples** — Concrete patterns that show expected behavior
- **Common edge cases** — Situations that require special handling

The agent loads this entire file once it decides to activate the skill. Keep the main SKILL.md lean; split content into referenced files when the validator warns. Run `uvx skilllint@latest check <skill-path>` after writing and follow its guidance on token-based sizing.

---

## Optional Directories

### scripts/

Contains executable code that agents can run:

- Be self-contained or clearly document dependencies
- Include helpful error messages
- Handle edge cases gracefully
- Supported languages depend on the agent implementation (commonly Python, Bash, JavaScript)

### references/

Contains additional documentation agents can read when needed:

- `REFERENCE.md` — Detailed technical reference
- `FORMS.md` — Form templates or structured data formats
- Domain-specific files (`finance.md`, `legal.md`, etc.)

Keep individual reference files focused. Agents load these on demand, so smaller files mean less context usage.

### assets/

Contains static resources:

- Templates (document templates, configuration templates)
- Images (diagrams, examples)
- Data files (lookup tables, schemas)

---

## Progressive Disclosure

Skills should be structured for efficient use of context:

1. **Metadata** (~100 tokens): The `name` and `description` fields are loaded at startup for all skills
2. **Instructions** (<5000 tokens recommended, and ideally under 500 lines): The full SKILL.md body is loaded when the skill is activated
3. **Resources** (as needed): Files in `scripts/`, `references/`, `assets/` are loaded only when required

**Keep your main SKILL.md lean.** Move detailed reference material to separate files. Run `uvx skilllint@latest check <skill-path>` after writing and follow its guidance on token-based sizing.

---

## File References

When referencing other files in your skill, use relative paths from the skill root:

```markdown
See [the reference guide](references/REFERENCE.md) for details.

Run the extraction script:
scripts/extract.py
```

Keep file references **one level deep** from SKILL.md — each reference file should link directly from SKILL.md so the agent can discover content without following long chains.

---

## Validation

Use the [skills-ref](https://github.com/agentskills/agentskills/tree/main/skills-ref) reference library:

```bash
skills-ref validate ./my-skill
```

**Why validate:** Validation catches frontmatter and naming errors before distribution and prevents agents from loading malformed skills. Run it before publishing or sharing skills.

> **Note:** The live agentskills.io/specification page now documents only this single `skills-ref validate` command. The additional CLI subcommands, Python API, and XML output format below are confirmed directly against the [skills-ref repository](https://github.com/agentskills/agentskills/tree/main/skills-ref) — not the specification page. The skills-ref README also states it is **intended for demonstration purposes only** and is not meant to be used in production; treat it as a reference implementation, not a hardened validation gate.

**CLI commands:**

```bash
# Validate a skill directory
skills-ref validate path/to/skill

# Read skill properties (outputs JSON)
skills-ref read-properties path/to/skill

# Generate <available_skills> XML for agent prompts
skills-ref to-prompt path/to/skill-a path/to/skill-b
```

**Python API:**

```python
from pathlib import Path
from skills_ref import validate, read_properties, to_prompt

problems = validate(Path("my-skill"))
if problems:
    print("Validation errors:", problems)

props = read_properties(Path("my-skill"))
print(f"Skill: {props.name} - {props.description}")

prompt = to_prompt([Path("skill-a"), Path("skill-b")])
print(prompt)
```

**Generated XML format:**

```xml
<available_skills>
  <skill>
    <name>pdf-processing</name>
    <description>Extracts text and tables from PDF files, fills forms, merges documents.</description>
    <location>/path/to/skills/pdf-processing/SKILL.md</location>
  </skill>
</available_skills>
```
