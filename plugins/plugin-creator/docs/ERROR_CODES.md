# Plugin Validator Error Code Reference

This document provides detailed explanations, examples, and fixes for all error codes emitted by the skilllint tool.

**Quick Navigation**:

- [Frontmatter Errors (FM001-FM010)](#frontmatter-errors)
- [Skill Errors (SK001-SK007)](#skill-errors)
- [Link Errors (LK001)](#link-errors)
- [Progressive Disclosure (PD001-PD003)](#progressive-disclosure)
- [Plugin Errors (PL001-PL005)](#plugin-errors)
- [Namespace Reference Errors (NR001-NR002)](#namespace-reference-errors)
- [Symlink Errors (SL001)](#symlink-errors)

---

## Frontmatter Errors

### FM001

**Severity**: Error
**Auto-Fixable**: No
**Category**: Frontmatter

**Description**: Missing required field (name, description)

**When It Occurs**:
The frontmatter is missing a required field based on the file type:

- **Agents**: `name` and `description` are required
- **Commands**: `description` is required
- **Skills**: No fields are strictly required, but `name` and `description` are strongly recommended

**Example (Bad)**:

```yaml
---
model: sonnet
---
```

**Fix**:

```yaml
---
name: my-agent
description: Agent for processing files
model: sonnet
---
```

**Related Validators**: FrontmatterValidator

---

### FM002

**Severity**: Error
**Auto-Fixable**: No
**Category**: Frontmatter

**Description**: Invalid YAML syntax

**When It Occurs**:
The frontmatter block contains invalid YAML syntax that cannot be parsed.

**Example (Bad)**:

```yaml
---
name: my-skill
description: This is a skill: but the colon breaks YAML
tools: [Read, Write  # Missing closing bracket
---
```

**Fix**:

```yaml
---
name: my-skill
description: "This is a skill: colons in quotes are safe"
tools: Read, Write
---
```

**Common YAML Pitfalls**:

- Unquoted strings with colons (except URLs)
- Mismatched brackets or quotes
- Incorrect indentation
- Tab characters (use spaces only)

**Related Validators**: FrontmatterValidator

---

### FM003

**Severity**: Error
**Auto-Fixable**: No
**Category**: Frontmatter

**Description**: Frontmatter not closed with `---`

**When It Occurs**:
The frontmatter block starts with `---` but is not properly closed with a second `---`.

**Example (Bad)**:

```yaml
---
name: my-skill
description: My skill description

# Content starts here
```

**Fix**:

```yaml
---
name: my-skill
description: My skill description
---

# Content starts here
```

**Related Validators**: FrontmatterValidator

---

### FM004

**Severity**: Warning
**Auto-Fixable**: Yes
**Category**: Frontmatter

**Description**: Forbidden multiline indicator (`>-`, `|-`)

**When It Occurs**:
The frontmatter uses YAML multiline string indicators (`>-`, `|-`), which are not supported by Claude Code's frontmatter parser.

**Example (Bad)**:

```yaml
---
name: my-skill
description: >-
  This is a multiline
  description using YAML folded style
---
```

**Fix** (Auto-Fixed):

```yaml
---
name: my-skill
description: "This is a multiline description using YAML folded style"
---
```

**Why It's Forbidden**: Claude Code's frontmatter parser expects simple key-value pairs, not YAML's advanced multiline syntax.

**Related Validators**: FrontmatterValidator

---

### FM005

**Severity**: Error
**Auto-Fixable**: No
**Category**: Frontmatter

**Description**: Field type mismatch (expected string/bool)

**When It Occurs**:
A frontmatter field has a value of the wrong type (e.g., boolean when string expected, number when string expected).

**Example (Bad)**:

```yaml
---
name: my-skill
description: 12345  # Number instead of string
user-invocable: yes  # String instead of boolean
---
```

**Fix**:

```yaml
---
name: my-skill
description: "12345"  # String
user-invocable: true  # Boolean
---
```

**Field Types**:

- `name`: string
- `description`: string
- `model`: string (must be one of: sonnet, opus, haiku, inherit)
- `tools`: string (comma-separated)
- `skills`: string (comma-separated)
- `user-invocable`: boolean (true/false)

**Related Validators**: FrontmatterValidator

---

### FM006

**Severity**: Error
**Auto-Fixable**: No
**Category**: Frontmatter

**Description**: Invalid field value (model not in enum)

**When It Occurs**:
A field with a constrained set of valid values contains an invalid value.

**Example (Bad)**:

```yaml
---
name: my-agent
description: My agent
model: gpt-4  # Invalid model
---
```

**Fix**:

```yaml
---
name: my-agent
description: My agent
model: sonnet  # Valid: sonnet, opus, haiku, inherit
---
```

**Valid `model` Values**:

- `sonnet` - Claude 3.5 Sonnet (default)
- `opus` - Claude 3 Opus
- `haiku` - Claude 3 Haiku
- `inherit` - Use parent's model

**Related Validators**: FrontmatterValidator

---

### FM007

**Severity**: Warning
**Auto-Fixable**: Yes
**Category**: Frontmatter

**Description**: Tools field is YAML array (not CSV string)

**When It Occurs**:
The `tools` field is specified as a YAML array instead of a comma-separated string.

**Example (Bad)**:

```yaml
---
name: my-agent
description: My agent
tools:
  - Read
  - Write
  - Grep
---
```

**Fix** (Auto-Fixed):

```yaml
---
name: my-agent
description: My agent
tools: Read, Write, Grep
---
```

**Why It's Wrong**: Claude Code's frontmatter parser expects comma-separated strings, not YAML arrays.

**Related Validators**: FrontmatterValidator

---

### FM008

**Severity**: Warning
**Auto-Fixable**: Yes
**Category**: Frontmatter

**Description**: Skills field is YAML array (not CSV string)

**When It Occurs**:
The `skills` field is specified as a YAML array instead of a comma-separated string.

**Example (Bad)**:

```yaml
---
name: my-agent
description: My agent
skills:
  - python3-development
  - holistic-linting
---
```

**Fix** (Auto-Fixed):

```yaml
---
name: my-agent
description: My agent
skills: python3-development, holistic-linting
---
```

**Related Validators**: FrontmatterValidator

---

### FM009

**Severity**: Warning
**Auto-Fixable**: Yes
**Category**: Frontmatter

**Description**: Unquoted colons in description — breaks YAML parsing

**When It Occurs**:
The `description` field contains colons but is not quoted, which breaks YAML parsing.

**Example (Bad)**:

```yaml
---
name: my-skill
description: Use this when: processing files or analyzing code
---
```

**Fix**: Quote the description value or avoid colons. (Auto-Fixed):

```yaml
---
name: my-skill
description: "Use this when: processing files or analyzing code"
---
```

**Exception**: URLs with colons (`https://...`) are safe without quotes when they appear at the end of a description.

**Related Validators**: FrontmatterValidator

---

### FM010

**Severity**: Error
**Auto-Fixable**: No
**Category**: Frontmatter

**Description**: Name pattern invalid (not lowercase-hyphens)

**When It Occurs**:
The `name` field does not match the required pattern: lowercase letters, numbers, and hyphens only.

**Example (Bad)**:

```yaml
---
name: My_Skill_Name
description: My skill
---
```

**Fix**:

```yaml
---
name: my-skill-name
description: My skill
---
```

**Valid Name Pattern**: `^[a-z0-9][a-z0-9-]*[a-z0-9]$` or `^[a-z0-9]$`

**Rules**:

- Only lowercase letters (a-z)
- Only numbers (0-9)
- Only hyphens (-) as separators
- Must start and end with alphanumeric character
- No underscores, spaces, or special characters
- Maximum 40 characters (for skill directory names)

**Related Validators**: FrontmatterValidator, NameFormatValidator

---

## Skill Errors

### SK001

**Severity**: Error
**Auto-Fixable**: No
**Category**: Skill

**Description**: Name contains uppercase characters

**When It Occurs**:
The skill name field contains uppercase letters.

**Example (Bad)**:

```yaml
---
name: MySkillName
description: My skill
---
```

**Fix**:

```yaml
---
name: my-skill-name
description: My skill
---
```

**Why It Matters**: Skill names are used in slash commands, which are case-sensitive and conventionally lowercase.

**Related Validators**: NameFormatValidator

---

### SK002

**Severity**: Error
**Auto-Fixable**: No
**Category**: Skill

**Description**: Name contains underscores (use hyphens)

**When It Occurs**:
The skill name uses underscores instead of hyphens.

**Example (Bad)**:

```yaml
---
name: my_skill_name
description: My skill
---
```

**Fix**:

```yaml
---
name: my-skill-name
description: My skill
---
```

**Why It Matters**: Claude Code naming convention uses hyphens (kebab-case), not underscores (snake_case).

**Related Validators**: NameFormatValidator

---

### SK003

**Severity**: Error
**Auto-Fixable**: No
**Category**: Skill

**Description**: Name has leading/trailing/consecutive hyphens

**When It Occurs**:
The skill name has hyphens at the beginning or end, or multiple consecutive hyphens.

**Example (Bad)**:

```yaml
---
name: -my-skill-
description: My skill
---

# OR

---
name: my--skill
description: My skill
---
```

**Fix**:

```yaml
---
name: my-skill
description: My skill
---
```

**Related Validators**: NameFormatValidator

---

### SK004

**Severity**: Warning
**Auto-Fixable**: No
**Category**: Skill

**Description**: Description too short (minimum 20 characters)

**When It Occurs**:
The skill description is shorter than the recommended minimum of 20 characters.

**Example (Bad)**:

```yaml
---
name: my-skill
description: A skill
---
```

**Fix**:

```yaml
---
name: my-skill
description: "Use when processing files and analyzing code for quality issues"
---
```

**Why It Matters**: Short descriptions don't provide enough context for Claude to know when to use the skill.

**Related Validators**: DescriptionValidator

---

### SK005

**Severity**: Warning
**Auto-Fixable**: No
**Category**: Skill

**Description**: Description missing trigger phrases

**When It Occurs**:
The skill description doesn't contain any trigger phrases that indicate when the skill should be used.

**Example (Bad)**:

```yaml
---
name: my-skill
description: A skill that processes files and analyzes code
---
```

**Fix**:

```yaml
---
name: my-skill
description: "Use this when processing files and analyzing code. Activate for quality checks and linting tasks."
---
```

**Required Trigger Phrases** (include at least one):

- "use when"
- "use this"
- "used when"
- "used by"
- "when " (followed by a space, e.g., "When reading..." or "When setting up...")
- "trigger"
- "activate"

**Example (Good - "When" starter)**:

```yaml
---
description: "When reading or writing pyproject.toml files, this skill provides TOML-specific validation and formatting guidance."
---
```

**Why It Matters**: Trigger phrases help Claude understand the skill's activation conditions. Descriptions starting with "When..." or containing "used when"/"used by" naturally express activation context.

**Related Validators**: DescriptionValidator

---

### SK006

**Severity**: Warning
**Auto-Fixable**: No
**Category**: Skill

**Description**: Token count exceeds TOKEN_WARNING_THRESHOLD (consider splitting)

**When It Occurs**:
The skill body (excluding frontmatter) exceeds `TOKEN_WARNING_THRESHOLD` defined in `skilllint`.

**Example**: (Skill file exceeding warning threshold)

**Fix**: Consider splitting the skill into smaller, focused skills:

```
Original: large-skill (4500 tokens)

Split into:
- large-skill-core (1500 tokens) - Core functionality
- large-skill-advanced (1500 tokens) - Advanced features
- large-skill-reference (1500 tokens) - Reference documentation
```

**Why It Matters**: Large skills consume Claude's context window and make skills harder to maintain.

**Related Validators**: ComplexityValidator

---

### SK007

**Severity**: Error
**Auto-Fixable**: No
**Category**: Skill

**Description**: Token count exceeds TOKEN_ERROR_THRESHOLD (must split)

**When It Occurs**:
The skill body exceeds `TOKEN_ERROR_THRESHOLD` defined in `skilllint`.

**Example**: (Very large skill file with 7000 tokens)

**Fix**: Must split the skill - see SK006 for splitting strategy.

**Why It Matters**: Skills this large significantly impact Claude's performance and context window.

**Related Validators**: ComplexityValidator

---

## Link Errors

### LK001

**Severity**: Error
**Auto-Fixable**: No
**Category**: Links

**Description**: Broken internal link (file does not exist)

**When It Occurs**:
A markdown link with a relative path (starting with `./`) points to a file that doesn't exist.

**Example (Bad)**:

```markdown
See [the reference guide](./references/non-existent.md) for details.
```

**Fix**:

```bash
# Create the referenced file
mkdir -p references
touch references/non-existent.md

# OR update the link
```

```markdown
See [the reference guide](./references/existing-file.md) for details.
```

**Why It Matters**: Broken links prevent users from accessing referenced documentation.

**Related Validators**: InternalLinkValidator

---

## Progressive Disclosure

### PD001

**Severity**: Info
**Auto-Fixable**: No
**Category**: Progressive Disclosure

**Description**: No `references/` directory found

**When It Occurs**:
The skill doesn't have a `references/` directory for detailed documentation.

**Example**: Skill structure missing `references/`

```
my-skill/
├── SKILL.md
└── (no references/)
```

**Fix**:

```bash
mkdir -p my-skill/references
# Add detailed documentation files
```

**Why It Matters**: Progressive disclosure keeps SKILL.md focused while providing depth in separate files.

**Related Validators**: ProgressiveDisclosureValidator

---

### PD002

**Severity**: Info
**Auto-Fixable**: No
**Category**: Progressive Disclosure

**Description**: No `examples/` directory found

**When It Occurs**:
The skill doesn't have an `examples/` directory for example files.

**Example**: Skill structure missing `examples/`

**Fix**:

```bash
mkdir -p my-skill/examples
# Add example files demonstrating skill usage
```

**Related Validators**: ProgressiveDisclosureValidator

---

### PD003

**Severity**: Info
**Auto-Fixable**: No
**Category**: Progressive Disclosure

**Description**: No `scripts/` directory found

**When It Occurs**:
The skill doesn't have a `scripts/` directory for helper scripts.

**Example**: Skill structure missing `scripts/`

**Fix**:

```bash
mkdir -p my-skill/scripts
# Add helper scripts or tools
```

**Related Validators**: ProgressiveDisclosureValidator

---

## Plugin Errors

### PL001

**Severity**: Error
**Auto-Fixable**: No
**Category**: Plugin

**Description**: Missing `plugin.json` file

**When It Occurs**:
The plugin directory doesn't contain a `.claude-plugin/plugin.json` file.

**Example (Bad)**:

```
my-plugin/
├── skills/
└── (no .claude-plugin/plugin.json)
```

**Fix**:

```bash
mkdir -p my-plugin/.claude-plugin
cat > my-plugin/.claude-plugin/plugin.json << 'EOF'
{
  "name": "my-plugin",
  "version": "0.1.0",
  "description": "My plugin description",
  "skills": ["./skills/"],
  "agents": [],
  "commands": []
}
EOF
```

**Related Validators**: PluginStructureValidator

---

### PL002

**Severity**: Error
**Auto-Fixable**: No
**Category**: Plugin

**Description**: Invalid JSON syntax in `plugin.json`

**When It Occurs**:
The `plugin.json` file contains invalid JSON syntax.

**Example (Bad)**:

```json
{
  "name": "my-plugin",
  "version": "0.1.0",
  "skills": ["./skills/"]  // Comments not allowed in JSON
}
```

**Fix**:

```json
{
  "name": "my-plugin",
  "version": "0.1.0",
  "skills": ["./skills/"]
}
```

**Validation Command**:

```bash
python3 -m json.tool .claude-plugin/plugin.json
```

**Common JSON Errors**:

- Trailing commas
- Comments (use `//` or `/* */`)
- Single quotes instead of double quotes
- Missing commas between fields

**Related Validators**: PluginStructureValidator

---

### PL003

**Severity**: Error
**Auto-Fixable**: No
**Category**: Plugin

**Description**: Missing required field `name` in plugin.json

**When It Occurs**:
The `plugin.json` file is missing the required `name` field.

**Example (Bad)**:

```json
{
  "version": "0.1.0",
  "skills": ["./skills/"]
}
```

**Fix**:

```json
{
  "name": "my-plugin",
  "version": "0.1.0",
  "skills": ["./skills/"]
}
```

**Required Fields**:

- `name`: Plugin name (kebab-case)

**Related Validators**: PluginStructureValidator

---

### PL004

**Severity**: Error
**Auto-Fixable**: No
**Category**: Plugin

**Description**: Component path does not start with `./`

**When It Occurs**:
A component path in `plugin.json` doesn't start with `./`.

**Example (Bad)**:

```json
{
  "name": "my-plugin",
  "skills": ["skills/"],
  "agents": ["agents/worker.md"]
}
```

**Fix**:

```json
{
  "name": "my-plugin",
  "skills": ["./skills/"],
  "agents": ["./agents/worker.md"]
}
```

**Why It Matters**: Claude Code requires relative paths to start with `./` for security and consistency.

**Related Validators**: PluginStructureValidator

---

### PL005

**Severity**: Error
**Auto-Fixable**: No
**Category**: Plugin

**Description**: Referenced component file does not exist

**When It Occurs**:
A file or directory referenced in `plugin.json` doesn't exist.

**Example (Bad)**:

```json
{
  "name": "my-plugin",
  "agents": ["./agents/non-existent.md"]
}
```

**Fix**:

```bash
# Create the referenced file
mkdir -p agents
touch agents/non-existent.md

# OR remove the reference from plugin.json
```

**Related Validators**: PluginStructureValidator

---

## Namespace Reference Errors

### NR001

**Severity**: Error
**Auto-Fixable**: No
**Category**: Namespace References

**Description**: Namespace reference target does not exist

**When It Occurs**:
A namespace-qualified reference in the file body points to a skill, agent, or command that does not exist in the referenced plugin directory.

The validator checks these reference patterns:

- `Skill(skill: "plugin:skill-name")`
- `Skill(skill="plugin:skill-name")`
- `Agent(subagent_type="plugin:agent-name")`
- `@plugin:agent-name` (prose agent references)
- `/plugin:skill-name` (slash command references)

**Example (Bad)**:

```markdown
Activate the linting skill: Skill(skill: "holistic-linting:nonexistent-skill")
```

**Fix**: Create the missing target file or correct the reference.

```bash
# If the skill should exist, create it
mkdir -p plugins/holistic-linting/skills/nonexistent-skill
touch plugins/holistic-linting/skills/nonexistent-skill/SKILL.md

# OR fix the reference to point to an existing skill
# Change "nonexistent-skill" to the correct skill name
```

**Notes**:

- Only namespace-qualified references (containing `:`) are checked
- Built-in agent types (Explore, general-purpose, Plan, etc.) are skipped
- Template placeholders containing `{` or `}` are skipped
- References in YAML frontmatter are not checked (body only)

**Related Validators**: NamespaceReferenceValidator

---

### NR002

**Severity**: Error
**Auto-Fixable**: No
**Category**: Namespace References

**Description**: Namespace reference points outside plugin directory

**When It Occurs**:
Reserved for future use. Intended for cases where a namespace reference resolves to a path outside the expected plugin directory tree.

**Related Validators**: NamespaceReferenceValidator

---

## Symlink Errors

### SL001

**Severity**: Error
**Auto-Fixable**: Yes
**Category**: Symlink

**Description**: Symlink target has trailing whitespace or newlines

**When It Occurs**:
A symlink inside the validated directory tree has a target path that ends with
whitespace or newline characters (e.g. `os.readlink()` returns
`'../../other-plugin/skills/shared\n'`).

This commonly happens when symlinks are created by scripts that pass
newline-terminated strings to `os.symlink()` or shell redirects.  The extra
whitespace causes `Path.resolve()` and `is_file()`/`is_dir()` to fail silently,
producing false-positive NR001 errors in `NamespaceReferenceValidator`.

**Example (Bad)**:

```python
# Symlink created with trailing newline
os.symlink("../../other-plugin/skills/shared\n", "plugins/my-plugin/skills/shared")
# os.readlink() now returns '../../other-plugin/skills/shared\n'
# Path.resolve() appends '\n' to the resolved path -- file not found
```

**Fix** (Auto-Fixed):

```bash
# Run the validator with --fix to strip trailing whitespace and recreate the symlink
uvx skilllint@latest check --fix plugins/

# Manual fix:
python3 -c "
import os
p = 'plugins/my-plugin/skills/uv'
t = os.readlink(p).rstrip()
os.remove(p)
os.symlink(t, p)
"
```

**Safety**: The auto-fix only recreates symlinks whose cleaned target resolves
to an existing path.  Symlinks whose cleaned target does not exist are left
untouched.

**Related Validators**: SymlinkTargetValidator

---

## Suppressing Errors with validator.json

Some skills are intentionally large reference documents where SK006 warnings would be noise rather than signal. The validator supports a per-plugin ignore config that suppresses specific error codes for specific paths.

### Config File Location

Place a `validator.json` file inside the plugin's `.claude-plugin/` directory alongside `plugin.json`:

```text
plugins/my-plugin/
  .claude-plugin/
    plugin.json
    validator.json   ← ignore config
  skills/
    my-large-skill/
      SKILL.md
```

### Config File Format

The file contains an `ignore` object mapping relative path prefixes to arrays of error codes to suppress:

```json
{
  "ignore": {
    "skills/my-large-skill": ["SK006"],
    "skills/another-large-skill": ["SK006", "SK007"],
    "agents/my-agent": ["SK004"]
  }
}
```

### Path Matching Rules

- Path keys are **relative to the plugin root** (e.g., `plugins/my-plugin/`).
- Matching is by **prefix**: a key of `"skills/my-large-skill"` suppresses the listed codes for `skills/my-large-skill/SKILL.md` and any other file whose relative path starts with `skills/my-large-skill/`.
- An exact match also works: `"skills/my-large-skill"` matches a file at exactly that path.

### Suppression Behaviour

- Suppressed issues are **completely omitted** from output — not downgraded to INFO.
- `--fix` still auto-fixes issues even when they are suppressed (suppression controls reporting, not fixing).
- Plugins without a `validator.json` are unaffected.

### When to Use

Use `validator.json` suppression for intentionally dense reference skills where the size is a deliberate design decision (e.g., comprehensive API references, orchestration guides). Do not use it to silence warnings on skills that genuinely need splitting.

---

## See Also

- [Plugin Validator Architecture](../planning/plugin-validator-architecture.md) - Technical specification
- [CONTRIBUTING.md](../../../CONTRIBUTING.md) - Contribution guidelines
- [Official Claude Code Plugin Documentation](https://docs.anthropic.com/claude/docs/plugins) - Official documentation

---

**Last Updated**: 2026-02-25
**Plugin Validator Version**: 0.1.0 (planned)
