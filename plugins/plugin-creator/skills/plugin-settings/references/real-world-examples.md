# Real-World Plugin Settings Examples

Production plugins using the `.claude/plugin-name.local.md` pattern.

## multi-agent-swarm Plugin

### Settings File

**.claude/multi-agent-swarm.local.md:**

```markdown
---
agent_name: auth-implementation
task_number: 3.5
pr_number: 1234
coordinator_session: team-leader
enabled: true
dependencies: ["Task 3.4"]
additional_instructions: "Use JWT tokens, not sessions"
---

# Task: Implement Authentication

Build JWT-based authentication for the REST API.

## Requirements

- JWT token generation and validation
- Refresh token flow
- Secure password hashing

## Success Criteria

- Auth endpoints implemented
- Tests passing
- PR created and CI green
```

### Hook Usage — agent-stop-notification.sh

Sends notifications to coordinator when agent becomes idle.

```bash
#!/bin/bash
set -euo pipefail

SWARM_STATE_FILE=".claude/multi-agent-swarm.local.md"

# Quick exit if no swarm active
if [[ ! -f "$SWARM_STATE_FILE" ]]; then
  exit 0
fi

# Parse frontmatter
FRONTMATTER=$(sed -n '/^---$/,/^---$/{ /^---$/d; p; }' "$SWARM_STATE_FILE")

# Extract configuration
COORDINATOR_SESSION=$(echo "$FRONTMATTER" | grep '^coordinator_session:' | sed 's/coordinator_session: *//' | sed 's/^"\(.*\)"$/\1/')
AGENT_NAME=$(echo "$FRONTMATTER" | grep '^agent_name:' | sed 's/agent_name: *//' | sed 's/^"\(.*\)"$/\1/')
TASK_NUMBER=$(echo "$FRONTMATTER" | grep '^task_number:' | sed 's/task_number: *//' | sed 's/^"\(.*\)"$/\1/')
PR_NUMBER=$(echo "$FRONTMATTER" | grep '^pr_number:' | sed 's/pr_number: *//' | sed 's/^"\(.*\)"$/\1/')
ENABLED=$(echo "$FRONTMATTER" | grep '^enabled:' | sed 's/enabled: *//')

if [[ "$ENABLED" != "true" ]]; then
  exit 0
fi

NOTIFICATION="Agent ${AGENT_NAME} (Task ${TASK_NUMBER}, PR #${PR_NUMBER}) is idle."

if tmux has-session -t "$COORDINATOR_SESSION" 2>/dev/null; then
  tmux send-keys -t "$COORDINATOR_SESSION" "$NOTIFICATION" Enter
fi

exit 0
```

Key patterns:

1. **Quick exit** — returns immediately if file does not exist
2. **Field extraction** — parses each frontmatter field individually
3. **Enabled check** — respects the enabled flag
4. **Action from settings** — uses coordinator_session to send tmux notification

### Creation

Settings files are created during swarm launch.

```bash
cat > "$WORKTREE_PATH/.claude/multi-agent-swarm.local.md" <<EOF
---
agent_name: $AGENT_NAME
task_number: $TASK_ID
pr_number: TBD
coordinator_session: $COORDINATOR_SESSION
enabled: true
dependencies: [$DEPENDENCIES]
additional_instructions: "$EXTRA_INSTRUCTIONS"
---

# Task: $TASK_DESCRIPTION

$TASK_DETAILS
EOF
```

### Updates

PR number updated after PR creation.

```bash
TEMP_FILE=".claude/multi-agent-swarm.local.md.tmp.$$"
sed "s/^pr_number: .*/pr_number: $PR_NUM/" \
  ".claude/multi-agent-swarm.local.md" > "$TEMP_FILE"
mv "$TEMP_FILE" ".claude/multi-agent-swarm.local.md"
```

## ralph-loop Plugin

### Settings File

**.claude/ralph-loop.local.md:**

```markdown
---
iteration: 1
max_iterations: 10
completion_promise: "All tests passing and build successful"
started_at: "2025-01-15T14:30:00Z"
---

Fix all the linting errors in the project.
Make sure tests pass after each fix.
Document any changes needed in CLAUDE.md.
```

### Hook Usage — stop-hook.sh

Prevents session exit and loops Claude's output back as input.

```bash
#!/bin/bash
set -euo pipefail

RALPH_STATE_FILE=".claude/ralph-loop.local.md"

# Quick exit if no active loop
if [[ ! -f "$RALPH_STATE_FILE" ]]; then
  exit 0
fi

FRONTMATTER=$(sed -n '/^---$/,/^---$/{ /^---$/d; p; }' "$RALPH_STATE_FILE")

ITERATION=$(echo "$FRONTMATTER" | grep '^iteration:' | sed 's/iteration: *//')
MAX_ITERATIONS=$(echo "$FRONTMATTER" | grep '^max_iterations:' | sed 's/max_iterations: *//')
COMPLETION_PROMISE=$(echo "$FRONTMATTER" | grep '^completion_promise:' | sed 's/completion_promise: *//' | sed 's/^"\(.*\)"$/\1/')

# Check max iterations
if [[ $MAX_ITERATIONS -gt 0 ]] && [[ $ITERATION -ge $MAX_ITERATIONS ]]; then
  echo "Ralph loop: Max iterations ($MAX_ITERATIONS) reached."
  rm "$RALPH_STATE_FILE"
  exit 0
fi

# Continue loop — increment iteration
NEXT_ITERATION=$((ITERATION + 1))

# Extract prompt from markdown body
PROMPT_TEXT=$(awk '/^---$/{i++; next} i>=2' "$RALPH_STATE_FILE")

# Atomic update of iteration counter
TEMP_FILE="${RALPH_STATE_FILE}.tmp.$$"
sed "s/^iteration: .*/iteration: $NEXT_ITERATION/" "$RALPH_STATE_FILE" > "$TEMP_FILE"
mv "$TEMP_FILE" "$RALPH_STATE_FILE"

# Block exit and feed prompt back
jq -n \
  --arg prompt "$PROMPT_TEXT" \
  --arg msg "Ralph iteration $NEXT_ITERATION" \
  '{
    "decision": "block",
    "reason": $prompt,
    "systemMessage": $msg
  }'

exit 0
```

Key patterns:

1. **Quick exit** — skip if not active
2. **Iteration tracking** — count and enforce max iterations
3. **Prompt extraction** — read markdown body as next prompt
4. **Atomic state update** — increment iteration via temp file + mv
5. **Loop continuation** — block exit and feed prompt back via JSON output

### Creation

```bash
cat > ".claude/ralph-loop.local.md" <<EOF
---
iteration: 1
max_iterations: $MAX_ITERATIONS
completion_promise: "$COMPLETION_PROMISE"
started_at: "$(date -Iseconds)"
---

$PROMPT
EOF
```

## Common Patterns Across Production Plugins

**Quick exit** — both plugins check file existence first. Avoids errors when plugin is not configured.

```bash
if [[ ! -f "$STATE_FILE" ]]; then
  exit 0
fi
```

**Enabled flag** — explicit control via `enabled: true/false`. Allows temporary deactivation without deleting the file.

**Atomic updates** — temp file + atomic move prevents corruption if process is interrupted.

```bash
TEMP_FILE="${FILE}.tmp.$$"
sed "s/^field: .*/field: $NEW_VALUE/" "$FILE" > "$TEMP_FILE"
mv "$TEMP_FILE" "$FILE"
```

**Quote handling** — strip surrounding quotes from YAML values because YAML allows both `field: value` and `field: "value"`.

```bash
sed 's/^"\(.*\)"$/\1/'
```

## Anti-Patterns

**Hardcoded paths** — use relative `.claude/plugin-name.local.md`, not absolute `/Users/alice/.claude/...`.

**Unquoted variables** — always quote `"$VALUE"` to handle values with spaces or special characters.

**Non-atomic updates** — `sed -i` can corrupt the file if interrupted. Always use temp file + mv.

**Missing defaults** — always provide fallback values when a field is missing.

```bash
MAX=${MAX:-10}
```

SOURCE: Adapted from Anthropic plugin-dev `skills/plugin-settings/references/real-world-examples.md`. Accessed 2026-03-24.
