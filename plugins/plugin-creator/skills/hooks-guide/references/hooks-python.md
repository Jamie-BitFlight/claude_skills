# Python Hook Authoring Guide

## Table of Contents

- [When to use Python vs CJS](#when-to-use-python-vs-cjs)
- [Shebang](#shebang)
- [Read stdin](#read-stdin)
- [Exit codes](#exit-codes)
- [Write to stdout](#write-to-stdout)
- [Write to stderr](#write-to-stderr)
- [Subprocess calls](#subprocess-calls)
- [Templates](#templates)
  - [Blocking hook](#blocking-hook)
  - [Permission decision](#permission-decision)
  - [Context injection](#context-injection)
  - [Task verification](#task-verification)
- [Anti-patterns](#anti-patterns)

---

## When to use Python vs CJS

Use Python when the hook integrates with Python tooling or requires file parsing or regex.

```text
Python:  integrating with ruff, mypy, pytest; parsing Python ASTs; regex matching on file content
CJS:     default for plugin hooks — avoids Python env dependency, runs with Node.js only
```

Python hooks require `python3` on `PATH` and the project virtualenv active if they import third-party packages. CJS hooks have no such dependency. Choose Python only when the tooling benefit outweighs the environment constraint.

---

## Shebang

Add this as the first line of every Python hook script.

```python
#!/usr/bin/env python3
```

---

## Read stdin

Claude Code delivers hook input as a JSON object on stdin. Read it with `sys.stdin.read()` and parse with `json.loads()`. Guard the parse with `try/except` and exit 0 on failure so a malformed payload does not block Claude.

```python
#!/usr/bin/env python3
import json
import sys

try:
    payload = json.loads(sys.stdin.read())
except json.JSONDecodeError:
    sys.exit(0)
```

Common fields present in every hook event:

```json
{
  "session_id": "abc123",
  "transcript_path": "/home/user/.claude/projects/.../transcript.jsonl",
  "cwd": "/home/user/my-project",
  "permission_mode": "default",
  "hook_event_name": "PreToolUse"
}
```

Event-specific fields — for example, a `PreToolUse` Bash hook also receives:

```json
{
  "tool_name": "Bash",
  "tool_input": {
    "command": "npm test"
  }
}
```

---

## Exit codes

Exit code is the primary signal Claude Code reads from a hook.

| Exit code | Meaning | What Claude Code does |
|-----------|---------|----------------------|
| `0` | Success | Parses stdout for JSON output fields; action proceeds |
| `2` | Blocking error | Ignores stdout; feeds stderr text to Claude as error message; blocks the action (for blockable events) |
| Any other | Non-blocking error | Shows stderr in verbose mode; execution continues |

Exit code 2 behavior depends on the event. Blockable events include `PreToolUse`, `Stop`, `SubagentStop`, `UserPromptSubmit`, and `TeammateIdle`. Non-blockable events like `PostToolUse` and `SessionStart` show stderr to Claude or the user but cannot prevent the action.

SOURCE: [Hooks reference — Exit code output](https://code.claude.com/docs/en/hooks-reference.md) (accessed 2026-03-01)

---

## Write to stdout

Write only `json.dumps()` output to stdout when returning structured hook decisions. Plain text on stdout is shown to the user in the transcript. Structured JSON output must be the only content on stdout.

```python
import json
import sys

output = {"decision": "block", "reason": "Tests must pass before stopping"}
sys.stdout.write(json.dumps(output))
sys.exit(0)
```

Use `sys.stdout.write()` rather than `print()`. `print()` appends a newline, which is harmless for JSON parsing, but it can cause problems when your shell profile also prints text — Claude Code cannot parse stdout that contains mixed text and JSON. Using `sys.stdout.write()` is explicit intent that this is structured output.

---

## Write to stderr

Write human-readable error messages to stderr. On exit 2, Claude Code feeds stderr text back to Claude as the blocking reason. On non-blocking exit codes, stderr appears in verbose mode.

```python
import sys

sys.stderr.write("Ruff lint failed — fix errors before proceeding\n")
sys.exit(2)
```

---

## Subprocess calls

Use `subprocess.run()` with `capture_output=True` and a `timeout`. Always handle `subprocess.TimeoutExpired` so a slow tool does not hang Claude.

```python
import subprocess
import sys

try:
    result = subprocess.run(["ruff", "check", "--select", "E,W", "."], capture_output=True, text=True, timeout=3)
except subprocess.TimeoutExpired:
    sys.stderr.write("Lint check timed out\n")
    sys.exit(1)

if result.returncode != 0:
    sys.stderr.write(result.stdout)
    sys.exit(2)

sys.exit(0)
```

---

## Templates

### Blocking hook

Use for `PreToolUse` when you need to block a tool call based on its input. Exit 2 with a message on stderr.

```python
#!/usr/bin/env python3
"""PreToolUse hook — block dangerous shell patterns."""

import json
import sys

BLOCKED_PATTERNS = ["rm -rf /", "git push --force"]

try:
    payload = json.loads(sys.stdin.read())
except json.JSONDecodeError:
    sys.exit(0)

command = payload.get("tool_input", {}).get("command", "")

for pattern in BLOCKED_PATTERNS:
    if pattern in command:
        sys.stderr.write(f"Blocked: pattern '{pattern}' is not allowed\n")
        sys.exit(2)

sys.exit(0)
```

### Permission decision

Use for `PreToolUse` when you want fine-grained control — allow, deny, or ask. Return JSON via stdout with exit 0. The decision lives inside `hookSpecificOutput`.

```python
#!/usr/bin/env python3
"""PreToolUse hook — deny write operations to production config."""

import json
import sys

try:
    payload = json.loads(sys.stdin.read())
except json.JSONDecodeError:
    sys.exit(0)

tool_input = payload.get("tool_input", {})
file_path = tool_input.get("file_path", "")

if "production" in file_path:
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "Direct edits to production config are not allowed",
        }
    }
    sys.stdout.write(json.dumps(output))
    sys.exit(0)

output = {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow"}}
sys.stdout.write(json.dumps(output))
sys.exit(0)
```

The three values for `permissionDecision`:

| Value | Effect |
|-------|--------|
| `"allow"` | Bypasses the permission system; shown to user |
| `"deny"` | Prevents the tool call; reason shown to Claude |
| `"ask"` | Prompts the user to confirm; reason shown to user |

SOURCE: [Hooks reference — PreToolUse decision control](https://code.claude.com/docs/en/hooks-reference.md) (accessed 2026-03-01)

### Context injection

Use for `SessionStart` to inject dynamic context into Claude's session. Return JSON with `additionalContext` via stdout with exit 0.

```python
#!/usr/bin/env python3
"""SessionStart hook — inject current git branch and open issues count."""

import json
import subprocess
import sys

try:
    payload = json.loads(sys.stdin.read())
except json.JSONDecodeError:
    sys.exit(0)

context_parts = []

try:
    branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, timeout=3)
    if branch.returncode == 0:
        context_parts.append(f"Current git branch: {branch.stdout.strip()}")
except subprocess.TimeoutExpired:
    pass

context = "\n".join(context_parts)

output = {"hookEventName": "SessionStart", "additionalContext": context}
sys.stdout.write(json.dumps(output))
sys.exit(0)
```

For `SessionStart`, plain text on stdout is also added as visible context, but the `additionalContext` JSON field is added more discretely.

SOURCE: [Hooks reference — SessionStart decision control](https://code.claude.com/docs/en/hooks-reference.md) (accessed 2026-03-01)

### Task verification

Use for `Stop` to force Claude to continue if a quality gate fails. Exit 2 with a message on stderr to prevent Claude from stopping.

```python
#!/usr/bin/env python3
"""Stop hook — require passing tests before Claude finishes."""

import json
import subprocess
import sys

try:
    payload = json.loads(sys.stdin.read())
except json.JSONDecodeError:
    sys.exit(0)

# Avoid infinite loop — check if stop hook already fired this turn
if payload.get("stop_hook_active"):
    sys.exit(0)

try:
    result = subprocess.run(["python", "-m", "pytest", "--tb=no", "-q"], capture_output=True, text=True, timeout=30)
except subprocess.TimeoutExpired:
    sys.stderr.write("Test run timed out — skipping gate\n")
    sys.exit(0)

if result.returncode != 0:
    sys.stderr.write("Tests are failing. Fix the failing tests before finishing.\n" + result.stdout[-500:])
    sys.exit(2)

sys.exit(0)
```

Check `stop_hook_active` before applying the gate. When Claude Code continues as a result of a stop hook, it sets `stop_hook_active: true` on the next `Stop` event. Without this check, the hook creates an infinite loop.

SOURCE: [Hooks reference — Stop input](https://code.claude.com/docs/en/hooks-reference.md) (accessed 2026-03-01)

---

## Anti-patterns

### Using print() for hook output

`print()` appends a newline and activates any shell profile output. Use `sys.stdout.write(json.dumps(output))` for structured JSON responses.

```python
# Wrong
print(json.dumps(output))

# Correct
sys.stdout.write(json.dumps(output))
sys.exit(0)
```

### Not catching JSON parse errors

Unparseable stdin causes an unhandled exception, which exits with code 1 — a non-blocking error that shows in verbose mode. Protect every hook with a try/except that exits 0 on parse failure so Claude is not blocked by a malformed payload.

```python
# Wrong
payload = json.loads(sys.stdin.read())  # raises on malformed input

# Correct
try:
    payload = json.loads(sys.stdin.read())
except json.JSONDecodeError:
    sys.exit(0)
```

### Mixing JSON and non-JSON on stdout

Any non-JSON text on stdout causes JSON validation to fail. If your script imports a library that prints on import, or if your shell profile prints a greeting, Claude Code cannot parse the hook response.

```python
# Wrong — prints debugging text before JSON
print("debug: checking payload")
sys.stdout.write(json.dumps(output))

# Correct — use stderr for diagnostic output
sys.stderr.write("debug: checking payload\n")
sys.stdout.write(json.dumps(output))
sys.exit(0)
```
