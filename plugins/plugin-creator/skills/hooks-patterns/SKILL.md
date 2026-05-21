---
name: hooks-patterns
description: Hook recipes and working examples — plugin hooks, frontmatter hooks in skills/agents/commands, prompt-based LLM hooks, and complete code examples in Python and Node.js. Use when building hook scripts, integrating hooks into plugins, implementing prompt-based hooks, or looking for hook configuration patterns.
user-invocable: true
---

# Claude Code Hooks — Patterns & Examples (May 2026)

Working examples and recipes for building hooks. For hook system fundamentals, activate `Skill(skill: "plugin-creator:hooks-core-reference")`. For JSON I/O schemas, activate `Skill(skill: "plugin-creator:hooks-io-api")`.

---

## Plugin Hooks

Plugins can provide hooks that integrate with user and project hooks. For complete plugin documentation including plugin.json schema, directory structure, and component integration, see `Skill(skill: "plugin-creator:claude-plugins-reference-2026")`.

### How Plugin Hooks Work

- Plugin hooks defined in `hooks/hooks.json` or custom path via `hooks` field in plugin.json
- When plugin enabled, its hooks merge with user and project hooks
- Multiple hooks from different sources can respond to same event
- Plugin hooks run alongside custom hooks in parallel

### Plugin Hook Configuration

Hooks can be configured in `hooks/hooks.json` or inline in `plugin.json`:

```json
{
  "description": "Automatic code formatting",
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/format.sh",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

Reference in plugin.json:

```json
{
  "name": "my-plugin",
  "hooks": "./hooks/hooks.json"
}
```

Or define inline:

```json
{
  "name": "my-plugin",
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/format.sh"
          }
        ]
      }
    ]
  }
}
```

### Plugin Environment Variables

- `${CLAUDE_PLUGIN_ROOT}`: Absolute path to the plugin directory
- `${CLAUDE_PROJECT_DIR}`: Project root directory
- All standard environment variables available

---

## Hooks in Skills, Agents, and Slash Commands

Hooks can be defined in frontmatter. These are scoped to the component's lifecycle. For complete skill documentation, see `Skill(skill: "plugin-creator:claude-skills-overview-2026")`.

**Supported events**: All hook events are supported in skill and agent frontmatter. The most common for subagents are `PreToolUse`, `PostToolUse`, and `Stop` (which is automatically converted to `SubagentStop` in agent context).

### Skill Example

```yaml
---
description: Perform operations with security checks
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/security-check.sh"
---
```

### Agent Example

```yaml
---
description: Review code changes
hooks:
  PostToolUse:
    - matcher: "Edit|Write"
      hooks:
        - type: command
          command: "./scripts/run-linter.sh"
---
```

### `once` Option

Set `once: true` to run hook only once per session. After first successful execution, hook is removed.

```yaml
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/one-time-setup.sh"
          once: true
```

**Note**: Only supported for skills and slash commands, not agents.

---

## Prompt-Based Hooks

LLM-evaluated decisions using a fast model (Haiku). Also known as "agent hooks" for complex verification tasks.

### How Prompt-Based Hooks Work

1. Send the hook input and your prompt to Haiku
2. The LLM responds with structured JSON containing a decision
3. Claude Code processes the decision automatically

### Configuration

```json
{
  "type": "prompt",
  "prompt": "Evaluate if Claude should stop: <USER_ARGUMENTS>. Check if all tasks are complete.",
  "timeout": 30
}
```

> **Note:** `<USER_ARGUMENTS>` above represents the `` `$ARGUMENTS` `` placeholder — replace it with the literal token `$ARGUMENTS` in your actual hook configuration. The placeholder is used here because skill files undergo argument substitution at load time.

Alternatively, use `"type": "agent"` for complex verification tasks that require tool access.

| Field             | Required | Description |
| ----------------- | -------- | ----------- |
| `type`            | Yes      | `"prompt"` for LLM evaluation, `"agent"` for multi-turn tool access |
| `prompt`          | Yes      | Prompt text sent to LLM. Use `$ARGUMENTS` placeholder for hook input JSON |
| `model`           | No       | Model to use. Defaults to a fast model (Haiku) |
| `timeout`         | No       | Seconds (default: 30 for prompt, 60 for agent) |
| `continueOnBlock` | No       | When `ok: false`, feed `reason` back to Claude and continue the turn instead of ending it. Default: `false`. Valid for `PostToolUse`, `TeammateIdle` |

### Response Schema

The LLM must respond with JSON:

```json
{
  "ok": true,
  "reason": "Explanation for the decision"
}
```

| Field    | Type    | Description                                    |
| -------- | ------- | ---------------------------------------------- |
| `ok`     | boolean | `true` allows the action, `false` prevents it  |
| `reason` | string  | Required when `ok` is `false`. Shown to Claude |

### The ARGUMENTS Placeholder

Use `` `$ARGUMENTS` `` in prompt to include hook input JSON. If omitted, input is appended to the prompt.

### Example: Intelligent Stop Hook

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "prompt",
            "prompt": "You are evaluating whether Claude should stop working. Context: <USER_ARGUMENTS>\n\nAnalyze the conversation and determine if:\n1. All user-requested tasks are complete\n2. Any errors need to be addressed\n3. Follow-up work is needed\n\nRespond with JSON: {\"ok\": true} to allow stopping, or {\"ok\": false, \"reason\": \"your explanation\"} to continue working.",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

### Example: SubagentStop Validation

> **Note:** `<USER_ARGUMENTS>` above represents the `` `$ARGUMENTS` `` placeholder — replace it with the literal token `$ARGUMENTS` in your actual hook configuration. The placeholder is used here because skill files undergo argument substitution at load time.

```json
{
  "hooks": {
    "SubagentStop": [
      {
        "hooks": [
          {
            "type": "prompt",
            "prompt": "Evaluate if this subagent should stop. Input: <USER_ARGUMENTS>\n\nCheck if:\n- The subagent completed its assigned task\n- Any errors occurred that need fixing\n- Additional context gathering is needed\n\nReturn: {\"ok\": true} to allow stopping, or {\"ok\": false, \"reason\": \"explanation\"} to continue."
          }
        ]
      }
    ]
  }
}
```

### Best Use Cases

| Event               | Use Case                              |
| ------------------- | ------------------------------------- |
| `Stop`              | Intelligent task completion detection |
| `SubagentStop`      | Verify subagent completed task        |
| `UserPromptSubmit`  | Context-aware prompt validation       |
| `PreToolUse`        | Complex permission decisions          |
| `PermissionRequest` | Intelligent allow/deny dialogs        |
| `PostToolUse`       | Validate tool output quality (use `continueOnBlock: true` to continue on fail) |
| `TeammateIdle`      | Quality gate before teammate goes idle (use `continueOnBlock: true`) |
| `TaskCreated`       | Enforce task naming conventions       |
| `TaskCompleted`     | Verify completion criteria (tests pass, artifacts exist) |

### Comparison with Command Hooks

| Feature           | Command Hooks         | Prompt Hooks                   |
| ----------------- | --------------------- | ------------------------------ |
| Execution         | Runs bash script      | Queries LLM                    |
| Decision logic    | You implement in code | LLM evaluates context          |
| Setup complexity  | Requires script file  | Configure prompt only          |
| Context awareness | Limited to script     | Natural language understanding |
| Performance       | Fast (local)          | Slower (API call)              |
| Use case          | Deterministic rules   | Context-aware decisions        |

### Best Practices for Prompt Hooks

1. **Be specific in prompts** - Clearly state what you want the LLM to evaluate
2. **Include decision criteria** - List the factors the LLM should consider
3. **Test your prompts** - Verify the LLM makes correct decisions for your use cases
4. **Set appropriate timeouts** - Default is 30 seconds, adjust if needed
5. **Use for complex decisions** - Bash hooks are better for simple, deterministic rules

---

## Code Examples

### Python: Bash Command Validation (Exit Code)

```python
#!/usr/bin/env python3
import json
import re
import sys

# Define validation rules as (regex pattern, message) tuples
VALIDATION_RULES = [
    (
        r"\bgrep\b(?!.*\|)",
        "Use 'rg' (ripgrep) instead of 'grep' for better performance",
    ),
    (
        r"\bfind\s+\S+\s+-name\b",
        "Use 'rg --files -g pattern' instead of 'find -name'",
    ),
]

def validate_command(command: str) -> list[str]:
    issues = []
    for pattern, message in VALIDATION_RULES:
        if re.search(pattern, command):
            issues.append(message)
    return issues

try:
    input_data = json.load(sys.stdin)
except json.JSONDecodeError as e:
    print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
    sys.exit(1)

tool_name = input_data.get("tool_name", "")
tool_input = input_data.get("tool_input", {})
command = tool_input.get("command", "")

if tool_name != "Bash" or not command:
    sys.exit(0)

issues = validate_command(command)

if issues:
    for message in issues:
        print(f"\u2022 {message}", file=sys.stderr)
    # Exit code 2 blocks tool call and shows stderr to Claude
    sys.exit(2)
```

### Python: UserPromptSubmit Context and Validation (JSON Output)

```python
#!/usr/bin/env python3
import json
import sys
import re
import datetime

try:
    input_data = json.load(sys.stdin)
except json.JSONDecodeError as e:
    print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
    sys.exit(1)

prompt = input_data.get("prompt", "")

# Check for sensitive patterns
sensitive_patterns = [
    (r"(?i)\b(password|secret|key|token)\s*[:=]", "Prompt contains potential secrets"),
]

for pattern, message in sensitive_patterns:
    if re.search(pattern, prompt):
        # Use JSON output to block with a specific reason
        output = {
            "decision": "block",
            "reason": f"Security policy violation: {message}. Please rephrase without sensitive information."
        }
        print(json.dumps(output))
        sys.exit(0)

# Add current time to context
context = f"Current time: {datetime.datetime.now()}"
print(context)

# Equivalent JSON approach:
# print(json.dumps({
#   "hookSpecificOutput": {
#     "hookEventName": "UserPromptSubmit",
#     "additionalContext": context,
#   },
# }))

sys.exit(0)
```

### Python: UserPromptSubmit Conditional Skill Invocation (Two-Layer Pattern)

The two-layer pattern separates evaluation from execution: the hook script wraps the prompt
with lightweight evaluation instructions and emits them as `additionalContext`. Claude then
evaluates the prompt inline — proceeding immediately for clear prompts, or invoking a skill
only when the prompt is vague. This keeps skill-load overhead off the common (clear) path.

> **Token overhead:** Clear prompts — ~189 tokens (evaluation wrapper only).
> Vague prompts — 189 tokens + skill load. ~31% reduction vs. embedding evaluation
> logic in the hook directly (prompt-improver v0.4.0, 2026-02-14).

```python
#!/usr/bin/env python3
import json
import sys

input_data = json.load(sys.stdin)
original_prompt = input_data.get("prompt", "")

# bypass: strip * prefix and skip evaluation
if original_prompt.startswith("*"):
    print(original_prompt[1:].lstrip())
    sys.exit(0)

# bypass: slash commands and memorize pass through unchanged
if original_prompt.startswith("/") or original_prompt.startswith("#"):
    print(original_prompt)
    sys.exit(0)

# ~189 tokens; instructs Claude to evaluate clarity,
#  invoke skill only when vague
evaluation_context = (
    f"Evaluate the following prompt for clarity and specificity.\n"
    f"...\n"
    f"PROCEED IMMEDIATELY if the prompt is clear and specific.\n"
    f"If vague: use Skill(skill='your-plugin:your-skill') to clarify before proceeding.\n"
    f"\nUser prompt: {original_prompt}"
)

output = {
    "hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": evaluation_context,
    }
}
print(json.dumps(output))
sys.exit(0)
```

Hook configuration (`hooks.json`):

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 /path/to/your-hook.py"
          }
        ]
      }
    ]
  }
}
```

**Skill contract:** The skill invoked via `Skill(skill='your-plugin:your-skill')` must assume
the hook has already evaluated the prompt for clarity. The skill must not re-evaluate whether
the prompt is vague — that decision has already been made by the hook. The skill should
proceed directly to its task (research, clarifying questions, enrichment, or any other
domain-specific work). Re-evaluating clarity in the skill defeats the two-layer separation
and doubles the token overhead for vague prompts.

### Python: PreToolUse Auto-Approval (JSON Output)

```python
#!/usr/bin/env python3
import json
import sys

try:
    input_data = json.load(sys.stdin)
except json.JSONDecodeError as e:
    print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
    sys.exit(1)

tool_name = input_data.get("tool_name", "")
tool_input = input_data.get("tool_input", {})

# Auto-approve file reads for documentation files
if tool_name == "Read":
    file_path = tool_input.get("file_path", "")
    if file_path.endswith((".md", ".mdx", ".txt", ".json")):
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": "Documentation file auto-approved"
            },
            "suppressOutput": True
        }
        print(json.dumps(output))
        sys.exit(0)

# Let normal permission flow proceed
sys.exit(0)
```

### Node.js: SessionStart Context Injection

```javascript
#!/usr/bin/env node

const output = {
  hookSpecificOutput: {
    hookEventName: "SessionStart",
    additionalContext: `<project-context>
Environment: ${process.env.NODE_ENV || "development"}
Node version: ${process.version}
Working directory: ${process.cwd()}
</project-context>`,
  },
};

console.log(JSON.stringify(output));
```

---

## Configuration Snippet Examples

### Code Formatting (PostToolUse)

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "prettier --write \"$CLAUDE_PROJECT_DIR\"/**/*.{js,ts,json}"
          }
        ]
      }
    ]
  }
}
```

### File Protection (PreToolUse)

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "./scripts/check-protected-files.sh"
          }
        ]
      }
    ]
  }
}
```

### Custom Notifications

**`notification_type` / matcher values**: `permission_prompt`, `idle_prompt`, `auth_success`, `elicitation_dialog`, `elicitation_complete`, `elicitation_response`

```json
{
  "hooks": {
    "Notification": [
      {
        "matcher": "permission_prompt",
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/permission-alert.sh"
          }
        ]
      },
      {
        "matcher": "idle_prompt",
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/idle-notification.sh"
          }
        ]
      }
    ]
  }
}
```

### Task Verification (Stop)

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "prompt",
            "prompt": "Verify task completion. Check edge cases. Return {\"ok\": true} or {\"ok\": false, \"reason\": \"...\"}."
          }
        ]
      }
    ]
  }
}
```

---

## Sources

- [Hooks Reference](https://docs.anthropic.com/en/docs/claude-code/hooks.md) (accessed 2026-05-21)
- [Hooks Guide](https://docs.anthropic.com/en/docs/claude-code/hooks-guide.md) (accessed 2026-05-21)
- [Settings Reference](https://docs.anthropic.com/en/docs/claude-code/settings.md)
- [Plugin Components Reference](https://docs.anthropic.com/en/docs/claude-code/plugins-reference.md#hooks)
