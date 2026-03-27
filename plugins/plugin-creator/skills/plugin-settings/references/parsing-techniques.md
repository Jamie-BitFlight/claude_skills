# Settings File Parsing Techniques

Complete guide to parsing `.claude/plugin-name.local.md` files in bash scripts.

## File Structure

Settings files use markdown with YAML frontmatter.

```markdown
---
field1: value1
field2: "value with spaces"
numeric_field: 42
boolean_field: true
list_field: ["item1", "item2", "item3"]
---

# Markdown Content

Body content extracted separately.
Useful for prompts, documentation, or additional context.
```

## Parsing Frontmatter

### Extract Frontmatter Block

```bash
FILE=".claude/my-plugin.local.md"

# Extract everything between --- markers (excluding the markers)
FRONTMATTER=$(sed -n '/^---$/,/^---$/{ /^---$/d; p; }' "$FILE")
```

How it works:

- `sed -n` suppresses automatic printing
- `/^---$/,/^---$/` selects the range from first `---` to second `---`
- `{ /^---$/d; p; }` deletes the `---` lines and prints everything else

### Extract Individual Fields

**String fields:**

```bash
# Simple value
VALUE=$(echo "$FRONTMATTER" | grep '^field_name:' | sed 's/field_name: *//')

# Quoted value (removes surrounding quotes)
VALUE=$(echo "$FRONTMATTER" | grep '^field_name:' | sed 's/field_name: *//' | sed 's/^"\(.*\)"$/\1/')
```

**Boolean fields:**

```bash
ENABLED=$(echo "$FRONTMATTER" | grep '^enabled:' | sed 's/enabled: *//')

if [[ "$ENABLED" == "true" ]]; then
  # Enabled
fi
```

**Numeric fields:**

```bash
MAX=$(echo "$FRONTMATTER" | grep '^max_value:' | sed 's/max_value: *//')

if [[ "$MAX" =~ ^[0-9]+$ ]]; then
  if [[ $MAX -gt 100 ]]; then
    # Too large
  fi
fi
```

**List fields (simple check):**

```bash
# YAML: list: ["item1", "item2", "item3"]
LIST=$(echo "$FRONTMATTER" | grep '^list:' | sed 's/list: *//')

if [[ "$LIST" == *"item1"* ]]; then
  # List contains item1
fi
```

**List fields (proper parsing with yq):**

```bash
# Requires yq installation (brew install yq)
LIST=$(echo "$FRONTMATTER" | yq -o json '.list' 2>/dev/null)

echo "$LIST" | jq -r '.[]' | while read -r item; do
  echo "Processing: $item"
done
```

## Parsing Markdown Body

```bash
FILE=".claude/my-plugin.local.md"

# Extract everything after the closing ---
BODY=$(awk '/^---$/{i++; next} i>=2' "$FILE")
```

How it works:

- `/^---$/` matches `---` lines
- `{i++; next}` increments counter and skips the `---` line
- `i>=2` prints all lines after the second `---`

Handles edge cases — if `---` appears in the markdown body, parsing still works because only the first two `---` at the start are counted.

### Use Body as Prompt

```bash
PROMPT=$(awk '/^---$/{i++; next} i>=2' "$FILE")

# Safe JSON construction with jq
jq -n --arg prompt "$PROMPT" '{
  "decision": "block",
  "reason": $prompt
}'
```

## Common Parsing Patterns

### Field with Default

```bash
VALUE=$(echo "$FRONTMATTER" | grep '^field:' | sed 's/field: *//' | sed 's/^"\(.*\)"$/\1/')

if [[ -z "$VALUE" ]]; then
  VALUE="default_value"
fi
```

### Optional Field

```bash
OPTIONAL=$(echo "$FRONTMATTER" | grep '^optional_field:' | sed 's/optional_field: *//' | sed 's/^"\(.*\)"$/\1/')

if [[ -n "$OPTIONAL" ]] && [[ "$OPTIONAL" != "null" ]]; then
  echo "Optional field: $OPTIONAL"
fi
```

### Multiple Fields at Once

```bash
while IFS=': ' read -r key value; do
  value=$(echo "$value" | sed 's/^"\(.*\)"$/\1/')

  case "$key" in
    enabled)  ENABLED="$value" ;;
    mode)     MODE="$value" ;;
    max_size) MAX_SIZE="$value" ;;
  esac
done <<< "$FRONTMATTER"
```

## Updating Settings Files

### Atomic Single-Field Update

```bash
FILE=".claude/my-plugin.local.md"
CURRENT=$(echo "$FRONTMATTER" | grep '^iteration:' | sed 's/iteration: *//')
NEXT=$((CURRENT + 1))

TEMP_FILE="${FILE}.tmp.$$"
sed "s/^iteration: .*/iteration: $NEXT/" "$FILE" > "$TEMP_FILE"
mv "$TEMP_FILE" "$FILE"
```

### Multi-Field Update

```bash
TEMP_FILE="${FILE}.tmp.$$"

sed -e "s/^iteration: .*/iteration: $NEXT_ITERATION/" \
    -e "s/^pr_number: .*/pr_number: $PR_NUMBER/" \
    -e "s/^status: .*/status: $NEW_STATUS/" \
    "$FILE" > "$TEMP_FILE"

mv "$TEMP_FILE" "$FILE"
```

## Validation Techniques

### File Existence and Readability

```bash
FILE=".claude/my-plugin.local.md"

if [[ ! -f "$FILE" ]]; then
  echo "Settings file not found" >&2
  exit 1
fi

if [[ ! -r "$FILE" ]]; then
  echo "Settings file not readable" >&2
  exit 1
fi
```

### Frontmatter Structure

```bash
MARKER_COUNT=$(grep -c '^---$' "$FILE" 2>/dev/null || echo "0")

if [[ $MARKER_COUNT -lt 2 ]]; then
  echo "Invalid settings file: missing frontmatter markers" >&2
  exit 1
fi
```

### Field Value Validation

```bash
MODE=$(echo "$FRONTMATTER" | grep '^mode:' | sed 's/mode: *//')

case "$MODE" in
  strict|standard|lenient) ;; # Valid
  *)
    echo "Invalid mode: $MODE (must be strict, standard, or lenient)" >&2
    exit 1
    ;;
esac
```

### Numeric Range Validation

```bash
MAX_SIZE=$(echo "$FRONTMATTER" | grep '^max_size:' | sed 's/max_size: *//')

if ! [[ "$MAX_SIZE" =~ ^[0-9]+$ ]]; then
  echo "max_size must be a number" >&2
  exit 1
fi

if [[ $MAX_SIZE -lt 1 ]] || [[ $MAX_SIZE -gt 10000000 ]]; then
  echo "max_size out of range (1-10000000)" >&2
  exit 1
fi
```

## Edge Cases

### Quotes in Values

YAML allows both quoted and unquoted strings. Handle both:

```bash
VALUE=$(echo "$FRONTMATTER" | grep '^field:' | sed 's/field: *//' | sed 's/^"\(.*\)"$/\1/' | sed "s/^'\\(.*\\)'$/\\1/")
```

### Empty Values

```yaml
field1:
field2: ""
field3: null
```

```bash
VALUE=$(echo "$FRONTMATTER" | grep '^field1:' | sed 's/field1: *//')

if [[ -z "$VALUE" ]] || [[ "$VALUE" == "null" ]]; then
  VALUE="default"
fi
```

### Special Characters

Always quote variables when using values that may contain spaces, colons, or special characters:

```bash
MESSAGE=$(echo "$FRONTMATTER" | grep '^message:' | sed 's/message: *//' | sed 's/^"\(.*\)"$/\1/')
echo "Message: $MESSAGE"  # Always quoted
```

## Performance

### Cache Parsed Values

Parse once, extract multiple fields from cached frontmatter.

```bash
FRONTMATTER=$(sed -n '/^---$/,/^---$/{ /^---$/d; p; }' "$FILE")

FIELD1=$(echo "$FRONTMATTER" | grep '^field1:' | sed 's/field1: *//')
FIELD2=$(echo "$FRONTMATTER" | grep '^field2:' | sed 's/field2: *//')
FIELD3=$(echo "$FRONTMATTER" | grep '^field3:' | sed 's/field3: *//')
```

### Lazy Loading

Only parse settings when the hook actually needs them.

```bash
input=$(cat)

# Quick checks first (no file I/O)
tool_name=$(echo "$input" | jq -r '.tool_name')
if [[ "$tool_name" != "Write" ]]; then
  exit 0
fi

# Only now check settings file
if [[ -f ".claude/my-plugin.local.md" ]]; then
  # Parse settings
fi
```

## Alternative — Using yq

For complex YAML, consider `yq`:

```bash
FRONTMATTER=$(sed -n '/^---$/,/^---$/{ /^---$/d; p; }' "$FILE")

ENABLED=$(echo "$FRONTMATTER" | yq '.enabled')
MODE=$(echo "$FRONTMATTER" | yq '.mode')
LIST=$(echo "$FRONTMATTER" | yq -o json '.list_field')

echo "$LIST" | jq -r '.[]' | while read -r item; do
  echo "Item: $item"
done
```

**Trade-off** — yq provides proper YAML parsing and handles complex structures, but requires installation. Use sed/grep for simple fields, yq for complex structures.

## Complete Example

```bash
#!/bin/bash
set -euo pipefail

SETTINGS_FILE=".claude/my-plugin.local.md"

if [[ ! -f "$SETTINGS_FILE" ]]; then
  ENABLED=true
  MODE=standard
  MAX_SIZE=1000000
else
  FRONTMATTER=$(sed -n '/^---$/,/^---$/{ /^---$/d; p; }' "$SETTINGS_FILE")

  ENABLED=$(echo "$FRONTMATTER" | grep '^enabled:' | sed 's/enabled: *//')
  ENABLED=${ENABLED:-true}

  MODE=$(echo "$FRONTMATTER" | grep '^mode:' | sed 's/mode: *//' | sed 's/^"\(.*\)"$/\1/')
  MODE=${MODE:-standard}

  MAX_SIZE=$(echo "$FRONTMATTER" | grep '^max_size:' | sed 's/max_size: *//')
  MAX_SIZE=${MAX_SIZE:-1000000}

  if [[ "$ENABLED" != "true" ]] && [[ "$ENABLED" != "false" ]]; then
    echo "Invalid enabled value, using default" >&2
    ENABLED=true
  fi

  if ! [[ "$MAX_SIZE" =~ ^[0-9]+$ ]]; then
    echo "Invalid max_size, using default" >&2
    MAX_SIZE=1000000
  fi
fi

if [[ "$ENABLED" != "true" ]]; then
  exit 0
fi

echo "Configuration loaded: mode=$MODE, max_size=$MAX_SIZE" >&2

case "$MODE" in
  strict)   ;; # Strict validation
  standard) ;; # Standard validation
  lenient)  ;; # Lenient validation
esac
```

SOURCE: Adapted from Anthropic plugin-dev `skills/plugin-settings/references/parsing-techniques.md`. Accessed 2026-03-24.
