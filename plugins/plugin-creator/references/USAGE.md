# skilllint Usage Guide

Complete usage reference for `skilllint` - the comprehensive validation tool for Claude Code plugins.

---

## Quick Start

**Basic validation**:

```bash
uvx skilllint@latest check <path>
```

**Auto-fix issues**:

```bash
uvx skilllint@latest check --fix <path>
```

**Validate only (no auto-fix)**:

```bash
uvx skilllint@latest check --check <path>
```

---

## Command-Line Interface

### Synopsis

```bash
skilllint [OPTIONS] PATH
```

### Arguments

**PATH** (required)
- File or directory to validate
- Accepts: SKILL.md, agent .md, command .md, plugin directory
- Examples:
  - `plugins/my-plugin/`
  - `plugins/my-plugin/skills/my-skill/SKILL.md`
  - `.claude/agents/my-agent.md`
  - `~/.claude/commands/my-command.md`

### Options

**--check**
- Validate only, do not auto-fix issues
- Useful for CI/CD pipelines
- Exit code 0 = valid, 1 = errors found

**--fix**
- Auto-fix issues where possible (4 error codes)
- Modifies files in-place
- Re-validates after fixing
- Shows what was fixed

**--verbose**
- Show all validation checks, including passed checks
- Useful for debugging and understanding validation process
- Displays detailed information about each validator

**--no-color**
- Disable Rich color output
- Useful for CI/CD or non-TTY environments
- Plain text output only

**--help**
- Show help message and exit
- Displays all options and usage examples

### Exit Codes

| Code | Meaning | Scenario |
|------|---------|----------|
| 0 | Success | All checks passed (warnings/info allowed) |
| 1 | Validation failed | Errors found |
| 2 | Usage error | Invalid arguments or missing path |
| 130 | User interrupted | Ctrl+C during execution |

---

## Usage Examples

### Example 1: Validate Single Skill

```bash
uvx skilllint@latest check \
  plugins/my-plugin/skills/my-skill/SKILL.md
```

**Output**:

```
Validating: plugins/my-plugin/skills/my-skill/SKILL.md

✅ Frontmatter validation passed
⚠️  Description validation warnings:
    - SK005: Description missing trigger phrases (line 3)
      Suggestion: Add trigger phrases: 'use when', 'use this', 'trigger', 'activate'

✅ Complexity validation passed (2847 tokens)
✅ Internal link validation passed
ℹ️  Progressive disclosure info:
    - PD001: No references/ directory
    - PD002: No examples/ directory

Validation: PASSED (0 errors, 1 warning, 2 info)
```

### Example 2: Validate Entire Plugin

```bash
uvx skilllint@latest check plugins/my-plugin
```

**Output**:

```
Validating plugin: plugins/my-plugin

✅ Plugin structure validation passed
✅ Frontmatter validation passed (3 skills, 2 agents, 1 command)
⚠️  Complexity warnings:
    - skills/large-skill/SKILL.md: SK006: 4523 tokens (consider splitting)

✅ Link validation passed
ℹ️  Progressive disclosure opportunities:
    - 2 skills missing references/ directories
    - 1 skill missing examples/ directory

Validation: PASSED (0 errors, 1 warning, 3 info)
```

### Example 3: Auto-Fix Frontmatter Issues

```bash
uvx skilllint@latest check --fix \
  plugins/my-plugin/skills/my-skill/SKILL.md
```

**Output**:

```
Validating: plugins/my-plugin/skills/my-skill/SKILL.md

🔧 Auto-fixing issues...

Fixed (4 changes):
  - FM007: Converted tools YAML array to comma-separated string
  - FM008: Converted skills YAML array to comma-separated string
  - FM009: Quoted description containing colons
  - FM004: Removed multiline indicator from description

Re-validating after fixes...

✅ All checks passed

Validation: PASSED (0 errors, 0 warnings, 0 info)
```

### Example 4: Validate for CI/CD

```bash
# Check-only mode for CI pipeline
uvx skilllint@latest check \
  --check --no-color plugins/my-plugin

# Exit code 0 = pass, 1 = fail
if [ $? -eq 0 ]; then
  echo "Validation passed"
else
  echo "Validation failed"
  exit 1
fi
```

### Example 5: Verbose Output for Debugging

```bash
uvx skilllint@latest check \
  --verbose plugins/my-plugin/skills/my-skill/SKILL.md
```

**Output**:

```
Validating: plugins/my-plugin/skills/my-skill/SKILL.md

Running validators:
  1. FrontmatterValidator
     - Checking YAML syntax... ✅
     - Checking required fields... ✅
     - Checking field types... ✅
     - Checking tools format... ✅
     - Checking name pattern... ✅

  2. NameFormatValidator
     - Checking for uppercase... ✅
     - Checking for underscores... ✅
     - Checking for invalid hyphens... ✅

  3. DescriptionValidator
     - Checking minimum length... ✅ (45 chars)
     - Checking trigger phrases... ⚠️  SK005: Missing trigger phrases

  4. ComplexityValidator
     - Measuring token count... ✅ (2847 tokens)
     - Checking warning threshold... ✅ (<4000)
     - Checking error threshold... ✅ (<6400)

  5. InternalLinkValidator
     - Extracting markdown links... (3 links found)
     - Checking link validity... ✅
     - Checking ./ prefix... ✅

  6. ProgressiveDisclosureValidator
     - Checking references/ directory... ℹ️  PD001: Not found
     - Checking examples/ directory... ℹ️  PD002: Not found
     - Checking scripts/ directory... ✅ (2 scripts)

Validation: PASSED (0 errors, 1 warning, 2 info)
```

### Example 6: Validate Agent File

```bash
uvx skilllint@latest check \
  .claude/agents/my-agent.md
```

**Output**:

```
Validating: .claude/agents/my-agent.md

✅ Frontmatter validation passed
✅ Name format validation passed
⚠️  Description validation warnings:
    - SK004: Description too short (18 chars, minimum 20)

Validation: PASSED (0 errors, 1 warning)
```

### Example 7: Validate Command File

```bash
uvx skilllint@latest check \
  ~/.claude/commands/my-command.md
```

**Output**:

```
Validating: ~/.claude/commands/my-command.md

✅ Frontmatter validation passed
✅ Name format validation passed
✅ Description validation passed

Validation: PASSED (0 errors)
```

---

## Common Workflows

### Workflow 1: Pre-Commit Validation

**Goal**: Validate plugin components before committing to git

**Steps**:

1. Stage changes:

```bash
git add plugins/my-plugin/skills/my-skill/SKILL.md
```

2. Validate changes:

```bash
uvx skilllint@latest check \
  --check plugins/my-plugin/skills/my-skill/SKILL.md
```

3. Fix issues if validation fails:

```bash
uvx skilllint@latest check \
  --fix plugins/my-plugin/skills/my-skill/SKILL.md
```

4. Commit:

```bash
git add plugins/my-plugin/skills/my-skill/SKILL.md
git commit -m "fix(my-skill): correct frontmatter formatting"
```

### Workflow 2: Create New Skill

**Goal**: Create and validate a new skill from scratch

**Steps**:

1. Create skill directory and SKILL.md:

```bash
mkdir -p plugins/my-plugin/skills/new-skill
touch plugins/my-plugin/skills/new-skill/SKILL.md
```

2. Write frontmatter and content (use editor)

3. Validate:

```bash
uvx skilllint@latest check \
  plugins/my-plugin/skills/new-skill/SKILL.md
```

4. Fix issues:

```bash
uvx skilllint@latest check \
  --fix plugins/my-plugin/skills/new-skill/SKILL.md
```

5. Add to plugin.json:

```json
{
  "skills": [
    "./skills/new-skill/"
  ]
}
```

6. Validate entire plugin:

```bash
uvx skilllint@latest check \
  plugins/my-plugin
```

### Workflow 3: Refactor Oversized Skill

**Goal**: Split skill exceeding token thresholds

**Steps**:

1. Check token count:

```bash
uvx skilllint@latest check \
  --verbose plugins/my-plugin/skills/large-skill/SKILL.md
```

**Output shows**: `SK006: 4523 tokens (consider splitting)`

2. Create progressive disclosure structure:

```bash
mkdir -p plugins/my-plugin/skills/large-skill/references
mkdir -p plugins/my-plugin/skills/large-skill/examples
```

3. Move detailed content to references/:

```bash
# Extract detailed sections from SKILL.md into reference files
mv detailed-section.md plugins/my-plugin/skills/large-skill/references/
```

4. Update SKILL.md with links to reference files:

```markdown
For detailed information, see [detailed guide](./references/detailed-section.md).
```

5. Re-validate:

```bash
uvx skilllint@latest check \
  --verbose plugins/my-plugin/skills/large-skill/SKILL.md
```

**Output shows**: `✅ Complexity validation passed (2847 tokens)`

### Workflow 4: Batch Validate All Plugins

**Goal**: Validate all plugins in repository

**Steps**:

1. Create validation script:

```bash
#!/usr/bin/env bash
# validate-all-plugins.sh

set -euo pipefail

failed_plugins=()

for plugin_dir in plugins/*/; do
  echo "Validating $plugin_dir..."
  if ! uvx skilllint@latest check \
    --check --no-color "$plugin_dir"; then
    failed_plugins+=("$plugin_dir")
  fi
done

if [ ${#failed_plugins[@]} -eq 0 ]; then
  echo "✅ All plugins validated successfully"
  exit 0
else
  echo "❌ Validation failed for:"
  printf '  - %s\n' "${failed_plugins[@]}"
  exit 1
fi
```

2. Make executable and run:

```bash
chmod +x validate-all-plugins.sh
./validate-all-plugins.sh
```

### Workflow 5: Fix All Auto-Fixable Issues

**Goal**: Automatically fix all frontmatter formatting issues

**Steps**:

1. Create fix-all script:

```bash
#!/usr/bin/env bash
# fix-all-frontmatter.sh

set -euo pipefail

# Find all SKILL.md, agent, and command files
find plugins -name "SKILL.md" -o -name "*.md" | while read -r file; do
  echo "Fixing $file..."
  uvx skilllint@latest check --fix "$file"
done
```

2. Make executable and run:

```bash
chmod +x fix-all-frontmatter.sh
./fix-all-frontmatter.sh
```

3. Review changes:

```bash
git diff
```

4. Commit if changes look correct:

```bash
git add -A
git commit -m "fix: auto-fix frontmatter formatting across all plugins"
```

---

## Integration Patterns

### Pre-Commit Hook Integration

Add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: skilllint
        name: Validate Plugin Components
        entry: uvx skilllint@latest check
        language: system
        files: '^plugins/.*/.*\.(md|json)$'
        pass_filenames: false
        args: [--check, --no-color]
```

**Usage**:

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run manually
pre-commit run skilllint --all-files
```

### CI/CD Pipeline Integration

**GitHub Actions**:

```yaml
name: Validate Plugins

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Validate plugins
        run: |
          for plugin in plugins/*/; do
            uvx skilllint@latest check \
              --check --no-color "$plugin"
          done
```

**GitLab CI**:

```yaml
validate-plugins:
  image: python:3.11
  script:
    - curl -LsSf https://astral.sh/uv/install.sh | sh
    - export PATH="$HOME/.cargo/bin:$PATH"
    - for plugin in plugins/*/; do
        uvx skilllint@latest check \
          --check --no-color "$plugin";
      done
```

### Pre-Release Validation

Create release checklist script:

```bash
#!/usr/bin/env bash
# release-check.sh

set -euo pipefail

echo "Running pre-release validation..."

# 1. Validate all plugins
echo "✓ Validating plugins..."
for plugin in plugins/*/; do
  uvx skilllint@latest check \
    --check --no-color "$plugin"
done

# 2. Check for oversized skills
echo "✓ Checking skill complexity..."
for skill in plugins/*/skills/*/SKILL.md; do
  if ! uvx skilllint@latest check \
    --check --no-color "$skill" 2>&1 | grep -q "SK007"; then
    continue
  else
    echo "ERROR: Oversized skill detected: $skill"
    exit 1
  fi
done

# 3. Check for broken links
echo "✓ Checking internal links..."
# (skilllint handles this)

# 4. Validate plugin.json files
echo "✓ Validating plugin.json files..."
for plugin_json in plugins/*/.claude-plugin/plugin.json; do
  python3 -m json.tool "$plugin_json" > /dev/null
done

echo "✅ Pre-release validation passed"
```

---

## Troubleshooting

### Issue: "Invalid YAML syntax" but YAML looks correct

**Symptom**: FM002 error but YAML syntax appears valid

**Cause**: Common YAML pitfalls:
- Unquoted strings with colons (`:`)
- Unquoted strings with special characters
- Incorrect indentation (spaces vs tabs)

**Fix**:
1. Quote all strings containing special characters
2. Use spaces, not tabs, for indentation
3. Validate YAML with external tool:

```bash
python3 -c "from ruamel.yaml import YAML; y = YAML(typ='safe'); y.load(open('SKILL.md').read().split('---')[1])"
```

### Issue: "Token count exceeds 6400" but file looks reasonable

**Symptom**: SK007 error but file doesn't seem oversized

**Cause**: Token count measures what Claude processes, not visual line count. Complex markdown, code blocks, and repeated phrases increase token count.

**Fix**:
1. Check actual token count:

```bash
uvx skilllint@latest check \
  --verbose plugins/my-plugin/skills/my-skill/SKILL.md
```

2. Apply progressive disclosure:
   - Move detailed reference material to `./references/`
   - Move code examples to `./examples/`
   - Move implementation scripts to `./scripts/`
   - Keep only high-level guidance in SKILL.md

### Issue: Auto-fix changes content unexpectedly

**Symptom**: `--fix` modifies content in unintended ways

**Cause**: Auto-fix applies specific transformations:
- Converts YAML arrays to CSV strings
- Quotes descriptions with colons
- Removes multiline indicators

**Fix**:
1. Review changes before committing:

```bash
git diff
```

2. Manually adjust if auto-fix produces incorrect result
3. Use `--check` mode first to preview issues:

```bash
uvx skilllint@latest check \
  --check plugins/my-plugin/skills/my-skill/SKILL.md
```

### Issue: Validation passes but `claude plugin validate` fails

**Symptom**: `skilllint` passes but `claude plugin validate` reports errors

**Cause**: Different validation scopes:
- `skilllint` validates component files
- `claude plugin validate` validates plugin.json structure

**Fix**:
1. Run both validators:

```bash
# Component validation
uvx skilllint@latest check plugins/my-plugin

# Structure validation
claude plugin validate plugins/my-plugin
```

2. Fix plugin.json issues reported by Claude CLI

### Issue: Performance is slow on large plugins

**Symptom**: Validation takes >30 seconds

**Cause**: Large plugins with many components, complex token counting

**Optimization**:
1. Validate individual components instead of entire plugin:

```bash
# Fast: validate single file
uvx skilllint@latest check \
  plugins/my-plugin/skills/my-skill/SKILL.md

# Slow: validate entire plugin
uvx skilllint@latest check plugins/my-plugin
```

2. Use `--check` mode to skip auto-fix overhead

3. Profile with verbose output to identify slow validators

---

## See Also

- [ARCHITECTURE.md](./ARCHITECTURE.md) - Validator design and implementation
- [skilllint](https://pypi.org/project/skilllint) - Source code
- [Claude Code Plugin Documentation](https://docs.claude.com/plugins) - Official plugin documentation
