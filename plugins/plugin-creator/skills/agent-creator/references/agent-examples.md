# Real-World Agent Examples

Examples from existing Claude Code agent implementations demonstrating best practices and patterns.

---

## Example 1: Plugin Assessor (Complex, Skill-Enhanced)

**Source**: `.claude/agents/plugin-assessor.md`

This agent demonstrates:

- Loading multiple skills for domain expertise
- Comprehensive phased workflow
- Detailed report format specification
- XML tags for structure

```yaml
---
name: plugin-assessor
description: 'Analyze Claude Code plugins for structural correctness, frontmatter optimization, schema compliance, and enhancement opportunities. Use when reviewing plugins before marketplace submission, auditing existing plugins, validating plugin structure, or identifying improvements. Handles large plugins with many reference files. Detects orphaned documentation, duplicate content, and missing cross-references.'
model: sonnet
skills: claude-skills-overview-2026, claude-plugins-reference-2026, hooks-guide
---
```

**Key Patterns:**

- Description includes multiple trigger phrases ("Use when reviewing", "auditing", "validating", "identifying")
- Loads 4 skills for comprehensive domain knowledge
- Uses sonnet for balanced capability

---

## Example 2: Code Review (Focused, Read-Implicit)

**Source**: `.claude/agents/code-review.md`

This agent demonstrates:

- Restricted invocation (user-only, not proactive)
- Clear input/output format
- Practical focus on "realness" of issues
- Categorized findings with severity levels

```yaml
---
name: code-review
description: Use ONLY when explicitly requested by user or when invoked by a protocol in sessions/protocols/. DO NOT use proactively. Reviews code for security vulnerabilities, bugs, performance issues, and adherence to project patterns during context compaction or pre-commit reviews. When using this agent, you must provide files and line ranges where code has been implemented along with the task file the code changes were made to satisfy. You may also give additional notes as necessary.
---
```

**Key Patterns:**

- Description explicitly states invocation conditions ("ONLY when explicitly requested")
- Specifies required inputs ("files and line ranges", "task file")
- Inherits default model and tools (appropriate for code review)

---

## Example 3: AI Doc Optimizer (Specialized Domain)

**Source**: `plugins/plugin-creator/agents/ai-doc-optimizer.md`

This agent demonstrates:

- Precise, action-oriented description with scope front-loaded
- `skills` field for pre-loading domain expertise at agent start
- `color` field for visual distinction in agent lists
- Tight, single-concern scope (content optimization only — not audit or upstream sync)

```yaml
---
name: ai-doc-optimizer
description: Optimize prompts, SKILL.md, and CLAUDE.md for Claude comprehension using Anthropic prompt-engineering principles — RT-ICA pre-check + CoVe post-check. Use to rewrite AI-facing doc for clarity, frontmatter description writing, prompt optimization, or when asked to optimize CLAUDE.md. Applies positive framing, front-loads constraints, converts decision tables to Mermaid flowcharts.
skills:
  - plugin-creator:prompt-optimization
  - plugin-creator:write-frontmatter-description
  - plugin-creator:claude-skills-overview-2026
  - plugin-creator:claude-plugins-reference-2026
model: sonnet
color: yellow
---
```

**Key Patterns:**

- Uses `color` field for visual distinction
- `skills` field pre-loads four domain skills before any task begins
- Description states exact file types handled and key techniques applied
- Single concern: content optimization only (audit → `skill-auditor`; upstream sync → `skill-content-updater`)

---

## Example 4: Doc Drift Auditor (Git Forensics)

**Source**: `.claude/agents/doc-drift-auditor.md`

This agent demonstrates:

- Description with inline examples (unusual but effective)
- Comprehensive expertise areas
- Evidence-based reporting requirements
- Clear boundaries (what it must NOT do)

```yaml
---
name: doc-drift-auditor
description: Use when verifying documentation accuracy against actual implementation or investigating gaps between code and docs. Analyzes git history to identify when code and documentation diverged, extracts actual features from source code, compares against documentation claims, and generates comprehensive audit reports categorizing drift (implemented but undocumented, documented but unimplemented, outdated documentation, mismatched details). Uses git forensics, code analysis, and evidence-based reporting with specific file paths, line numbers, and commit SHAs.
model: sonnet
color: orange
---
```

**Key Patterns:**

- Very detailed description explaining methodology
- Lists specific outputs (file paths, line numbers, commit SHAs)
- Uses `color: orange` for audit visibility

---

## Example 5: Skill Refactorer (Modification Agent)

**Source**: `.claude/agents/plugin-creator:refactor-skill.md`

This agent demonstrates:

- `permissionMode: acceptEdits` for automated file changes
- Loading skill for domain knowledge
- Phased workflow with user confirmation points
- Validation and reporting phases

```yaml
---
name: plugin-creator:refactor-skill
description: 'Refactor large or multi-domain skills into smaller, focused skills without losing fidelity. Use when a skill covers too many topics, exceeds 500 lines, or would benefit from separation of concerns. Analyzes skill content, identifies logical partitions, plans the split, creates new SKILL.md files, and validates complete coverage.'
model: sonnet
permissionMode: acceptEdits
skills: claude-skills-overview-2026
---
```

**Key Patterns:**

- Uses `permissionMode: acceptEdits` since it creates/modifies files
- Loads relevant skill for understanding skill format
- Description specifies when to use ("exceeds 500 lines", "multiple topics")
- Mentions both analysis and creation capabilities

---

## Example 6: Context Gathering (Research Agent)

**Source**: `.claude/agents/context-gathering.md`

This agent demonstrates:

- Minimal frontmatter (inherits most settings)
- Clear restriction on output (ONLY edit task file)
- Comprehensive narrative output format
- Self-verification checklist

```yaml
---
name: context-gathering
description: Use when creating a new task OR when starting/switching to a task that lacks a context manifest. ALWAYS provide the task file path so the agent can read it and update it directly with the context manifest. Skip if task file already contains "Context Manifest" section.
---
```

**Key Patterns:**

- Very specific trigger conditions
- States what to skip (already has Context Manifest)
- Requires specific input (task file path)
- Inherits all defaults (appropriate for this use case)

---

## Pattern Summary

### Frontmatter Patterns

| Pattern              | Example                       | When to Use                            |
| -------------------- | ----------------------------- | -------------------------------------- |
| Minimal frontmatter  | context-gathering             | Agent needs flexibility, inherits well |
| Skill loading        | plugin-assessor               | Needs domain knowledge                 |
| Permission mode      | plugin-creator:refactor-skill | Creates/modifies files                 |
| Color coding         | doc-drift-auditor             | Visual distinction helpful             |
| Detailed description | doc-drift-auditor             | Complex trigger conditions             |

### Body Structure Patterns

| Pattern            | Example           | When to Use              |
| ------------------ | ----------------- | ------------------------ |
| Phased workflow    | plugin-assessor   | Multi-step process       |
| Checklist          | code-review       | Quality validation       |
| Boundaries section | doc-drift-auditor | Must clarify limits      |
| Output format spec | code-review       | Consistent output needed |
| Self-verification  | context-gathering | Quality assurance        |

### Description Patterns

| Pattern              | Example                         | Effect                      |
| -------------------- | ------------------------------- | --------------------------- |
| Action verbs first   | "Analyze", "Review", "Generate" | Clear purpose               |
| "Use when" phrase    | Most agents                     | Trigger clarity             |
| "DO NOT" instruction | code-review                     | Prevent unwanted activation |
| Input requirements   | context-gathering               | Clear expectations          |
| Output description   | doc-drift-auditor               | Sets expectations           |

---

## Anti-Patterns Observed

### Avoid These

1. **Vague descriptions** - "Helps with code" doesn't guide delegation
2. **Missing invocation triggers** - When should Claude use this?
3. **Over-broad responsibilities** - One agent doing everything
4. **Missing tool restrictions** - Read-only agents inheriting write access
5. **Assuming skill inheritance** - Skills must be explicitly loaded

### Do These

1. **Specific action verbs** - "Review", "Generate", "Audit", "Debug"
2. **Clear trigger phrases** - "Use when", "Invoke for", "After completing"
3. **Focused responsibilities** - One agent, one domain
4. **Appropriate tool access** - Match tools to actual needs
5. **Explicit skill loading** - List all needed skills

---

# Role-Based Contract Examples

These examples demonstrate the DONE/BLOCKED output format using the `subagent-contract` skill.

---

## Example 7: Coder - Next.js + Supabase Stack

**Use for**: TypeScript 5.9 + Bun + Biome + Next.js + Supabase projects

This filled example shows a Coder agent specialized for a modern web stack:

````markdown
---
name: coder-web-nextjs-supabase
description: 'Implements scoped features and fixes in TypeScript 5.9 using Bun, Biome, Next.js, and Supabase with minimal diffs and reported command outcomes.'
model: sonnet
permissionMode: acceptEdits
skills: subagent-contract
---

# Coder (Next.js + Supabase)

## Mission

Implement features and fixes in TypeScript 5.9 using Bun, Biome, Next.js, and Supabase, meeting stated acceptance criteria.

## Scope

**You do:**
- Implement code changes in the existing Next.js codebase
- Update or add tests if required by acceptance criteria or repo norms
- Run formatting/linting/testing commands and report results

**You do NOT:**
- Change requirements
- Add new dependencies unless instructed
- Perform broad refactors unless required

## Inputs You May Receive

- **Spec**: Feature or fix specification
- **Acceptance criteria**: What must be true when done
- **Constraints**: Technical or architectural limitations
- **Paths**: Files/directories in scope
- **Allowed commands/tools**: bun, biome, next (via bun), supabase cli (if present)

## SOP (Implementation)

<workflow>
1. Restate task and acceptance criteria
2. Identify minimal file changes
3. Implement smallest correct diff
4. Run:
   - `bun run biome check .`
   - `bun test` (or repo-specific test command)
5. Summarize changes, list files touched, list commands run + outcomes
</workflow>

## Output Format

```text
STATUS: DONE
SUMMARY: Implemented authenticated account page showing user email and created_at
ARTIFACTS:
  - Files changed: app/account/page.tsx, lib/supabase/auth.ts
  - Commands + results: biome check (pass), bun test (12 pass, 0 fail)
  - Notes for reviewer: Used server component pattern per constraints
RISKS:
  - None identified
NOTES:
  - Existing Supabase helpers were sufficient, no new code needed in lib/
```
````

**Supervisor Co-Prompt Example:**

```text
Task:
Implement "Add authenticated account page at /account that shows the signed-in
user's email and created_at from Supabase auth."

Acceptance Criteria:
  - Signed-in users see email and created_at at /account
  - Signed-out users are redirected to /login
  - Biome passes with no warnings
  - Tests (if present) pass

Constraints:
  - Prefer server components; only use client components if necessary
  - Use existing Supabase helpers already in the repo

Paths:
  - app/account/page.tsx
  - lib/supabase/
```

---

## Example 8: Coder - Python TUI Stack

**Use for**: Python 3.12 + uv + poe-the-poet + ruff + basedpyright + Textual + Rich + orjson + Pydantic + httpx

This filled example shows a Coder agent specialized for Python TUI development:

````markdown
---
name: coder-tui-textual-httpx
description: 'Implements scoped features and fixes in Python 3.12 using uv, poe-the-poet, Ruff, basedpyright, Textual, Rich, orjson, Pydantic, and httpx with minimal diffs and reported command outcomes.'
model: sonnet
permissionMode: acceptEdits
skills: subagent-contract, python3-development
---

# Coder (Textual TUI)

## Mission

Implement features and fixes in Python 3.12 using uv, poe-the-poet, Ruff, basedpyright, Textual, Rich, orjson, Pydantic, and httpx, meeting stated acceptance criteria.

## Scope

**You do:**
- Implement code changes
- Add/update tests if required by acceptance criteria or repo norms
- Run Ruff and basedpyright and report outcomes

**You do NOT:**
- Change requirements
- Add new dependencies unless instructed
- Block the UI thread with network calls

## Inputs You May Receive

- **Spec**: Feature or fix specification
- **Acceptance criteria**: What must be true when done
- **Constraints**: Technical or architectural limitations
- **Paths**: Files/directories in scope
- **Allowed commands/tools**: uv, poe, ruff, basedpyright, pytest (if present)

## SOP (Implementation)

<workflow>
1. Restate task and acceptance criteria
2. Identify minimal file changes
3. Implement smallest correct diff
4. Run:
   - `poe ruff` (or "uv run ruff check ." depending on repo)
   - `poe pyright` (or basedpyright command per repo)
   - `poe test` (or repo test command)
5. Summarize changes, list files touched, list commands run + outcomes
</workflow>

## Output Format

```text
STATUS: DONE
SUMMARY: Implemented status fetch on 's' keypress with async worker pattern
ARTIFACTS:
  - Files changed: src/tui/main.py, src/models/status.py
  - Commands + results: ruff (pass), basedpyright (pass), pytest (8 pass)
  - Notes for reviewer: Used Textual worker for async, orjson for parse, Pydantic for validation
RISKS:
  - Timeout of 5s may be too short for slow networks
NOTES:
  - Error notification uses Rich panel, non-blocking
```
````

**Supervisor Co-Prompt Example:**

```text
Task:
Implement "On keypress 's', fetch /api/status with httpx (timeout 5s), parse with
orjson, validate with Pydantic, and render fields in the Textual UI using Rich."

Acceptance Criteria:
  - Pressing 's' triggers fetch without freezing the UI (use Textual worker/task patterns)
  - JSON parse uses orjson; validation uses a Pydantic model
  - Rendered output includes status, version, uptime fields
  - Errors are shown as a non-crashing notification with a short exception summary
  - Ruff and basedpyright pass

Constraints:
  - No new dependencies
  - Follow existing project task runner conventions (uv + poe)

Paths:
  - src/tui/main.py
  - src/models/status.py
```

---

## Example 9: Formatter Plugin (With Hooks)

**IMPORTANT**: Hooks are NOT configured in agent frontmatter. Hooks are configured at the plugin or project level in `hooks/hooks.json` or `.claude-plugin/plugin.json`.

This example shows how a **plugin** (not an agent) can use hooks for automated formatting and validation.

**Plugin Structure**:

```
formatter-plugin/
├── .claude-plugin/
│   └── plugin.json
├── hooks/
│   └── hooks.json
└── scripts/
    ├── check-file-size.sh
    └── final-lint-check.sh
```

**hooks/hooks.json**:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/check-file-size.sh",
            "timeout": 5000
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "npx prettier --write",
            "timeout": 10000
          },
          {
            "type": "command",
            "command": "npx eslint --fix",
            "timeout": 10000
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/final-lint-check.sh"
          }
        ]
      }
    ]
  }
}
```

**plugin.json**:

```json
{
  "name": "auto-formatter",
  "version": "1.0.0",
  "description": "Automatically formats and lints code after modifications",
  "hooks": "./hooks/hooks.json"
}
```

**Hook Behavior**:

**PreToolUse (Validation)**:

- Runs before Write/Edit operations
- Exit 2 blocks the operation if validation fails
- Checks file size limits to prevent large file mistakes

**PostToolUse (Formatting)**:

- Runs after successful Write/Edit operations
- Applies Prettier formatting automatically
- Fixes ESLint auto-fixable issues
- Both run in parallel

**Stop (Final Check)**:

- Runs when Claude completes all work
- Verifies no linting issues remain
- Exit 2 prevents task completion if issues found

**Key Hook Patterns:**

| Hook Event  | Matcher       | Purpose           | Exit Code Behavior  |
| ----------- | ------------- | ----------------- | ------------------- |
| PreToolUse  | `Write\|Edit` | Block large files | Exit 2 = block tool |
| PostToolUse | `Write\|Edit` | Auto-format code  | Exit 0 = continue   |
| Stop        | (no matcher)  | Final validation  | Exit 2 = show error |

**Hook Script Example** (`scripts/check-file-size.sh`):

```bash
#!/bin/bash
# Receives tool input as JSON via stdin

input=$(cat)
file_path=$(echo "$input" | jq -r '.tool_input.file_path // empty')

if [ -n "$file_path" ] && [ -f "$file_path" ]; then
  size=$(stat -f%z "$file_path" 2>/dev/null || stat -c%s "$file_path")
  max_size=$((1024 * 1024))  # 1MB

  if [ "$size" -gt "$max_size" ]; then
    echo "ERROR: File $file_path exceeds 1MB limit" >&2
    exit 2  # Block the operation
  fi
fi

exit 0  # Allow operation
```

**When to Use Hooks:**

- **PreToolUse**: Validation, security checks, blocking unwanted operations
- **PostToolUse**: Formatting, linting, logging, notifications
- **Stop**: Final validation, cleanup, report generation

**SOURCE**: [Claude Code Hooks Reference](https://code.claude.com/docs/en/hooks.md) (accessed 2026-01-28)

---

## Role-Based Pattern Summary

| Element                     | Purpose                      | Example                              |
| --------------------------- | ---------------------------- | ------------------------------------ |
| `skills: subagent-contract` | Enforces DONE/BLOCKED format | All role-based agents                |
| Mission section             | Clear single responsibility  | "Implement features..."              |
| Scope (do/don't)            | Explicit boundaries          | "You do NOT change requirements"     |
| SOP                         | Step-by-step process         | Numbered workflow                    |
| Output Format               | Consistent deliverables      | STATUS/SUMMARY/ARTIFACTS/RISKS/NOTES |

### When to Use Contract Format

- Orchestrated multi-agent workflows
- Tasks delegated from supervisor agents
- Work requiring clear handoffs
- Situations where blocking is preferred over guessing
