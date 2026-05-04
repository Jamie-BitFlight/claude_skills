# Plugin Validator Error Codes

Complete reference for all error codes emitted by `skilllint`.

**Total Error Codes**: 23 across 9 validator classes

**Error Code Format**: `[CATEGORY][NUMBER]`
- **FM**: Frontmatter errors (001-010)
- **SK**: Skill errors (001-007)
- **LK**: Link errors (001-002)
- **PD**: Progressive Disclosure info (001-003)
- **PL**: Plugin structure errors (001-005)

**Documentation URL**: Each error code links to this document via `https://github.com/jamie-bitflight/claude_skills/blob/main/plugins/plugin-creator/references/ERROR_CODES.md#[code]`

---

## Frontmatter Errors (FM001-FM010)

Validator: `FrontmatterValidator`
Auto-fixable: Partial (FM004, FM007, FM008, FM009)

### FM001 - Missing Required Field

**Severity**: ERROR
**Auto-fix**: No

**Description**: Required field is missing from frontmatter.

**Required fields by file type**:
- **Skills**: None (name and description are optional)
- **Agents**: `name`, `description`
- **Commands**: `description`

**Example violation**:

```yaml
---
# Missing 'name' field in agent file
description: Performs analysis tasks
model: sonnet
---
```

**Fix**:

```yaml
---
name: analysis-agent
description: Performs analysis tasks
model: sonnet
---
```

### FM002 - Invalid YAML Syntax

**Severity**: ERROR
**Auto-fix**: No

**Description**: Frontmatter contains invalid YAML syntax.

**Example violation**:

```yaml
---
name: test-skill
description: Missing closing quote
tools: Read, Grep
---
```

**Fix**: Ensure valid YAML syntax - properly quoted strings, correct indentation, no syntax errors.

### FM003 - Frontmatter Not Closed

**Severity**: ERROR
**Auto-fix**: No

**Description**: Frontmatter missing closing `---` delimiter.

**Example violation**:

```markdown
---
name: test-skill
description: Example skill

# Missing closing ---

Content starts here...
```

**Fix**:

```markdown
---
name: test-skill
description: Example skill
---

Content starts here...
```

### FM004 - Forbidden Multiline Indicator

**Severity**: ERROR
**Auto-fix**: Yes

**Description**: Frontmatter uses YAML multiline indicators (`>-`, `|-`) which are not supported.

**Example violation**:

```yaml
---
name: test-skill
description: >-
  This is a multiline
  description that will fail
---
```

**Auto-fix result**:

```yaml
---
name: test-skill
description: "This is a multiline description that will fail"
---
```

### FM005 - Field Type Mismatch

**Severity**: ERROR
**Auto-fix**: No

**Description**: Field value type does not match expected type.

**Example violation**:

```yaml
---
name: test-skill
description: Valid description
user-invocable: "yes"  # Should be boolean, not string
---
```

**Fix**:

```yaml
---
name: test-skill
description: Valid description
user-invocable: true
---
```

### FM006 - Invalid Field Value

**Severity**: ERROR
**Auto-fix**: No

**Description**: Field value is not in the allowed set of values.

**Example violation**:

```yaml
---
name: test-agent
description: Example agent
model: gpt-4  # Invalid model name
---
```

**Valid model values**: `sonnet`, `opus`, `haiku`, `inherit`

**Fix**:

```yaml
---
name: test-agent
description: Example agent
model: sonnet
---
```

### FM007 - Tools Field Is YAML Array

**Severity**: ERROR
**Auto-fix**: Yes

**Description**: `tools` field is a YAML array instead of comma-separated string.

**Example violation**:

```yaml
---
name: test-skill
description: Example skill
tools:
  - Read
  - Grep
  - Glob
---
```

**Auto-fix result**:

```yaml
---
name: test-skill
description: Example skill
tools: Read, Grep, Glob
---
```

### FM008 - Skills Field Is YAML Array

**Severity**: ERROR
**Auto-fix**: Yes

**Description**: `skills` field is a YAML array instead of comma-separated string.

**Example violation**:

```yaml
---
name: test-agent
description: Example agent
skills:
  - skill-one
  - skill-two
---
```

**Auto-fix result**:

```yaml
---
name: test-agent
description: Example agent
skills: skill-one, skill-two
---
```

### FM009 - Unquoted Colons in Description

**Severity**: ERROR
**Auto-fix**: Yes

**Description**: Unquoted colons in description — breaks YAML parsing.

**Example violation**:

```yaml
---
name: test-skill
description: Use when: analyzing logs  # Colon causes parse error
---
```

**Fix**: Quote the description value or avoid colons.

**Ecosystem exemption**: Sub-keys of ecosystem-owned top-level frontmatter fields are exempt from FM009 rewriting. For example, lines nested under `mcp:` (owned by OpenCode) are not rewritten even if they contain colons. The currently known ecosystem-owned key is `mcp:` (OpenCode).

**Auto-fix result**:

```yaml
---
name: test-skill
description: "Use when: analyzing logs"
---
```

### FM010 - Invalid Name Pattern

**Severity**: ERROR
**Auto-fix**: No

**Description**: Name field does not match required pattern: lowercase, hyphens only, no leading/trailing hyphens, no consecutive hyphens.

**Valid pattern**: `^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$`

**Example violations**:

```yaml
# Uppercase characters
name: Test-Skill

# Underscores
name: test_skill

# Leading hyphen
name: -test-skill

# Trailing hyphen
name: test-skill-

# Consecutive hyphens
name: test--skill
```

**Valid names**:

```yaml
name: test-skill
name: a
name: test-123
name: my-agent-v2
```

---

## Skill Errors (SK001-SK007)

Validators: `NameFormatValidator`, `DescriptionValidator`, `ComplexityValidator`
Auto-fixable: None

### SK001 - Name Contains Uppercase

**Severity**: ERROR
**Auto-fix**: No
**Validator**: `NameFormatValidator`

**Description**: Skill/agent name contains uppercase characters.

**Example violation**:

```yaml
name: MyTestSkill
```

**Fix**:

```yaml
name: my-test-skill
```

### SK002 - Name Contains Underscores

**Severity**: ERROR
**Auto-fix**: No
**Validator**: `NameFormatValidator`

**Description**: Skill/agent name contains underscores instead of hyphens.

**Example violation**:

```yaml
name: test_skill
```

**Fix**:

```yaml
name: test-skill
```

### SK003 - Name Has Invalid Hyphens

**Severity**: ERROR
**Auto-fix**: No
**Validator**: `NameFormatValidator`

**Description**: Name has leading hyphens, trailing hyphens, or consecutive hyphens.

**Example violations**:

```yaml
name: -test  # Leading
name: test-  # Trailing
name: test--skill  # Consecutive
```

**Fix**:

```yaml
name: test
name: test
name: test-skill
```

### SK004 - Description Too Short

**Severity**: WARNING
**Auto-fix**: No
**Validator**: `DescriptionValidator`

**Description**: Description is less than 20 characters (minimum recommended length).

**Example violation**:

```yaml
description: Test skill
```

**Length**: 10 characters (minimum 20)

**Fix**:

```yaml
description: "Test skill for analyzing and processing data files"
```

### SK005 - Missing Trigger Phrases

**Severity**: WARNING
**Auto-fix**: No
**Validator**: `DescriptionValidator`

**Description**: Description does not contain recommended trigger phrases that help AI understand when to use the skill.

**Required trigger phrases** (at least one):
- "use when"
- "use this"
- "trigger"
- "activate"

**Example violation**:

```yaml
description: "Analyzes log files and generates reports"
```

**Fix**:

```yaml
description: "Use when analyzing log files to generate detailed reports"
```

### SK006 - Token Count Warning

**Severity**: WARNING
**Auto-fix**: No
**Validator**: `ComplexityValidator`

**Description**: Skill body content exceeds `TOKEN_WARNING_THRESHOLD`. Consider splitting into smaller, focused skills.

**Threshold**: Defined in `skilllint` as `TOKEN_WARNING_THRESHOLD`

**Recommendation**: Split skill using progressive disclosure:
1. Keep high-level guidance in main SKILL.md
2. Move detailed reference material to `./references/` directory
3. Move examples to `./examples/` directory
4. Move implementation scripts to `./scripts/` directory

**Example**:

```
skill-name/
├── SKILL.md (2500 tokens - high-level workflow)
├── references/
│   ├── detailed-guide.md (reference material)
│   └── api-reference.md (technical details)
├── examples/
│   └── common-patterns.md (code examples)
└── scripts/
    └── helper.py (implementation)
```

### SK007 - Token Count Error

**Severity**: ERROR
**Auto-fix**: No
**Validator**: `ComplexityValidator`

**Description**: Skill body content exceeds `TOKEN_ERROR_THRESHOLD`. Skill MUST be split.

**Threshold**: Defined in `skilllint` as `TOKEN_ERROR_THRESHOLD`

**Reason**: Skills exceeding this threshold cause:
- Slow Claude Code loading
- Reduced comprehension
- Context window waste
- Poor user experience

**Action required**: Split skill immediately using progressive disclosure pattern (see SK006).

---

## Link Errors (LK001-LK002)

Validator: `InternalLinkValidator`
Auto-fixable: None

### LK001 - Broken Internal Link

**Severity**: ERROR
**Auto-fix**: No

**Description**: Markdown link points to a file that does not exist.

**Example violation**:

```markdown
See [detailed guide](./references/missing-file.md) for more information.
```

**File check**: `./references/missing-file.md` does not exist relative to SKILL.md

**Fix**:
1. Create the referenced file, or
2. Update the link to point to an existing file:

```markdown
See [detailed guide](./references/existing-file.md) for more information.
```

### LK002 - Missing Relative Path Prefix

**Severity**: WARNING
**Auto-fix**: No

**Description**: Internal link does not start with `./` prefix, making it ambiguous.

**Example violation**:

```markdown
See [guide](references/file.md) for details.
```

**Fix**:

```markdown
See [guide](./references/file.md) for details.
```

**Why this matters**: Links without `./` are ambiguous and may not resolve correctly in all contexts.

---

## Progressive Disclosure Info (PD001-PD003)

Validator: `ProgressiveDisclosureValidator`
Auto-fixable: None
**Severity**: INFO (not errors)

These are informational notices about missing progressive disclosure directories. They indicate opportunities to improve skill organization but do not cause validation failures.

### PD001 - No References Directory

**Severity**: INFO
**Auto-fix**: No

**Description**: Skill does not have a `references/` directory for detailed reference material.

**Recommendation**: Create `references/` directory to store:
- Detailed technical documentation
- API references
- Configuration guides
- Long-form explanations

**Example structure**:

```
skill-name/
├── SKILL.md
└── references/
    ├── api-reference.md
    ├── configuration.md
    └── troubleshooting.md
```

### PD002 - No Examples Directory

**Severity**: INFO
**Auto-fix**: No

**Description**: Skill does not have an `examples/` directory for code examples.

**Recommendation**: Create `examples/` directory to store:
- Usage examples
- Common patterns
- Code snippets
- Sample workflows

**Example structure**:

```
skill-name/
├── SKILL.md
└── examples/
    ├── basic-usage.md
    ├── advanced-patterns.md
    └── common-workflows.md
```

### PD003 - No Scripts Directory

**Severity**: INFO
**Auto-fix**: No

**Description**: Skill does not have a `scripts/` directory for companion scripts.

**Recommendation**: Create `scripts/` directory to store:
- Helper scripts
- Automation tools
- Validation scripts
- Data processing utilities

**Example structure**:

```
skill-name/
├── SKILL.md
└── scripts/
    ├── helper.py
    ├── validate.sh
    └── process-data.py
```

---

## Plugin Structure Errors (PL001-PL005)

Validator: `PluginStructureValidator`
Auto-fixable: None
**Integration**: Delegates to `claude plugin validate` CLI when available

### PL001 - Missing plugin.json

**Severity**: ERROR
**Auto-fix**: No

**Description**: Plugin directory does not contain `.claude-plugin/plugin.json` file.

**Fix**: Create plugin.json with minimum required fields:

```json
{
  "name": "plugin-name",
  "version": "1.0.0",
  "description": "Plugin description"
}
```

### PL002 - Invalid JSON Syntax

**Severity**: ERROR
**Auto-fix**: No

**Description**: plugin.json contains invalid JSON syntax.

**Example violation**:

```json
{
  "name": "plugin-name",
  "version": "1.0.0"  # Comment not allowed in JSON
}
```

**Fix**: Ensure valid JSON syntax - no trailing commas, no comments, proper quoting.

**Validation command**:

```bash
python3 -m json.tool .claude-plugin/plugin.json
```

### PL003 - Missing Required Field

**Severity**: ERROR
**Auto-fix**: No

**Description**: plugin.json is missing the required `name` field.

**Example violation**:

```json
{
  "version": "1.0.0",
  "description": "Example plugin"
}
```

**Fix**:

```json
{
  "name": "plugin-name",
  "version": "1.0.0",
  "description": "Example plugin"
}
```

### PL004 - Invalid Component Path

**Severity**: ERROR
**Auto-fix**: No

**Description**: Component path in plugin.json does not start with `./` (must be relative).

**Example violation**:

```json
{
  "name": "plugin-name",
  "agents": ["agents/my-agent.md"]
}
```

**Fix**:

```json
{
  "name": "plugin-name",
  "agents": ["./agents/my-agent.md"]
}
```

### PL005 - Referenced File Does Not Exist

**Severity**: ERROR
**Auto-fix**: No

**Description**: Component file referenced in plugin.json does not exist.

**Example violation**:

```json
{
  "name": "plugin-name",
  "agents": ["./agents/missing-agent.md"]
}
```

**File check**: `./agents/missing-agent.md` does not exist

**Fix**:
1. Create the referenced file, or
2. Remove the reference from plugin.json

---

## Error Code Summary Table

| Code  | Category             | Severity | Auto-fix | Description                             |
|-------|----------------------|----------|----------|-----------------------------------------|
| FM001 | Frontmatter          | ERROR    | No       | Missing required field                  |
| FM002 | Frontmatter          | ERROR    | No       | Invalid YAML syntax                     |
| FM003 | Frontmatter          | ERROR    | No       | Frontmatter not closed                  |
| FM004 | Frontmatter          | ERROR    | Yes      | Forbidden multiline indicator           |
| FM005 | Frontmatter          | ERROR    | No       | Field type mismatch                     |
| FM006 | Frontmatter          | ERROR    | No       | Invalid field value                     |
| FM007 | Frontmatter          | ERROR    | Yes      | Tools field is YAML array               |
| FM008 | Frontmatter          | ERROR    | Yes      | Skills field is YAML array              |
| FM009 | Frontmatter          | ERROR    | Yes      | Unquoted colons in description          |
| FM010 | Frontmatter          | ERROR    | No       | Invalid name pattern                    |
| SK001 | Skill/Agent Name     | ERROR    | No       | Name contains uppercase                 |
| SK002 | Skill/Agent Name     | ERROR    | No       | Name contains underscores               |
| SK003 | Skill/Agent Name     | ERROR    | No       | Name has invalid hyphens                |
| SK004 | Description          | WARNING  | No       | Description too short (<20 chars)       |
| SK005 | Description          | WARNING  | No       | Missing trigger phrases                 |
| SK006 | Complexity           | WARNING  | No       | Token count >4000 (consider splitting)  |
| SK007 | Complexity           | ERROR    | No       | Token count >6400 (must split)          |
| LK001 | Internal Links       | ERROR    | No       | Broken internal link                    |
| LK002 | Internal Links       | WARNING  | No       | Missing ./ prefix                       |
| PD001 | Progressive Disclosure | INFO   | No       | No references/ directory                |
| PD002 | Progressive Disclosure | INFO   | No       | No examples/ directory                  |
| PD003 | Progressive Disclosure | INFO   | No       | No scripts/ directory                   |
| PL001 | Plugin Structure     | ERROR    | No       | Missing plugin.json                     |
| PL002 | Plugin Structure     | ERROR    | No       | Invalid JSON syntax                     |
| PL003 | Plugin Structure     | ERROR    | No       | Missing required field                  |
| PL004 | Plugin Structure     | ERROR    | No       | Invalid component path                  |
| PL005 | Plugin Structure     | ERROR    | No       | Referenced file does not exist          |

---

## Auto-Fix Summary

**4 error codes are auto-fixable** with `--fix` flag:

| Code  | Fix Applied                                     |
|-------|-------------------------------------------------|
| FM004 | Converts multiline YAML to single-line quoted   |
| FM007 | Converts YAML array to comma-separated string   |
| FM008 | Converts YAML array to comma-separated string   |
| FM009 | Adds quotes around description with colons      |

**Usage**:

```bash
uvx skilllint@latest check --fix <path>
```

**Important**: Auto-fix modifies files in-place. Always commit or backup files before running auto-fix.

---

## Severity Levels

| Severity | Meaning | Exit Code Impact |
|----------|---------|------------------|
| **ERROR** | Must be fixed - validation fails | Exit 1 |
| **WARNING** | Should be fixed - validation passes | Exit 0 |
| **INFO** | Informational - validation passes | Exit 0 |

**Exit codes**:
- `0` - Validation passed (no errors, warnings/info allowed)
- `1` - Validation failed (errors found)
- `2` - Usage error (invalid arguments)
- `130` - User interrupted (Ctrl+C)

---

## See Also

- [USAGE.md](./USAGE.md) - CLI usage and workflow examples
- [ARCHITECTURE.md](./ARCHITECTURE.md) - Validator design and implementation
- [skilllint](https://pypi.org/project/skilllint) - Package and source code
