# Schema Research: Claude Code Plugin, Agent, and Skill Formats

Sources:
- <https://code.claude.com/docs/en/plugins-reference.md> (fetched 2026-02-19)
- <https://code.claude.com/docs/en/skills.md> (fetched 2026-02-19)
- <https://code.claude.com/docs/en/sub-agents.md> (fetched 2026-02-19)
- Real agent files in `/home/user/repos/claude_skills/plugins/`

---

## 1. Agent Frontmatter — Complete Schema

### Required Fields

| Field | Type | Constraint |
|-------|------|-----------|
| `name` | string | Lowercase letters and hyphens only, max 64 characters |
| `description` | string | When Claude should delegate to this agent; max 1024 characters |

### Optional Fields

| Field | Type | Values / Format | Notes |
|-------|------|-----------------|-------|
| `tools` | string | Comma-separated tool names | Allowlist. Inherits all tools if omitted. |
| `disallowedTools` | string | Comma-separated tool names | Denylist. Removed from inherited or specified list. |
| `model` | string | `sonnet`, `opus`, `haiku`, `inherit` | Defaults to `inherit` if omitted. |
| `permissionMode` | string | `default`, `acceptEdits`, `dontAsk`, `bypassPermissions`, `plan` | Controls permission prompt behavior. |
| `maxTurns` | integer | Any positive integer | Maximum agentic turns before agent stops. |
| `skills` | string | Comma-separated skill names | Full skill content injected at startup (not inherited from parent). |
| `mcpServers` | string or object | Server name or inline config | MCP servers available to this agent. |
| `hooks` | object | Hook configuration object | Lifecycle hooks scoped to this agent. |
| `memory` | string | `user`, `project`, `local` | Enables persistent cross-session memory. |
| `color` | string | Color name e.g. `cyan`, `pink`, `green`, `yellow` | Terminal output color for agent messages. |

### Critical Formatting Constraint

`tools`, `disallowedTools`, and `skills` MUST be comma-separated strings, NOT YAML arrays.

```yaml
# CORRECT
tools: Read, Grep, Glob, Bash
skills: python3-development, uv

# WRONG — will fail validation
tools:
  - Read
  - Grep
```

### Complete Example Agent File

```markdown
---
name: dasel-operator
description: Executes dasel queries and transformations on YAML, TOML, JSON, and JSONC files. Use when querying structured config files, applying path-based updates, or converting between config formats.
tools: Read, Bash, Write, Edit, Grep, Glob
model: sonnet
color: cyan
---

Agent system prompt body goes here in Markdown.
```

---

## 2. Model Field — Exact Values

The `model` field accepts aliases only (not full model IDs):

| Alias | Resolves to |
|-------|-------------|
| `haiku` | claude-haiku-4-5 (fast, low-latency, Explore agent default) |
| `sonnet` | claude-sonnet-4-6 (balanced capability and speed) |
| `opus` | claude-opus-4-6 (maximum intelligence) |
| `inherit` | Same model as the parent conversation |

`inherit` is the default when `model` is omitted.

**In agent frontmatter:**

```yaml
model: haiku    # Fast, use for retrieval-only agents
model: sonnet   # Default for most specialist agents
model: opus     # Use for complex reasoning (e.g., refactor-skill)
model: inherit  # Explicitly inherit from orchestrator
```

**In SKILL.md frontmatter** — same aliases apply:

```yaml
model: sonnet
```

---

## 3. SKILL.md Frontmatter — Complete Schema

### Fields

| Field | Required | Type | Notes |
|-------|----------|------|-------|
| `name` | No | string | Display name. Uses directory name if omitted. **BUG: causes slash command registration failure in plugin skills — omit for plugin skills.** |
| `description` | Recommended | string | What the skill does and when to use it. Used by Claude for auto-invocation. |
| `argument-hint` | No | string | Shown in autocomplete. Example: `[issue-number]` or `[filename] [format]` |
| `disable-model-invocation` | No | boolean | `true` prevents Claude from auto-loading; user must invoke with `/name`. Default: `false` |
| `user-invocable` | No | boolean | `false` hides from `/` menu (Claude-only). Default: `true` |
| `allowed-tools` | No | string | Comma-separated tool names Claude can use without asking when skill is active. |
| `model` | No | string | `sonnet`, `opus`, `haiku`, or `inherit`. |
| `context` | No | string | `fork` — runs skill in an isolated subagent context. |
| `agent` | No | string | Which subagent to use when `context: fork` is set. Built-ins: `Explore`, `Plan`, `general-purpose`. Or any custom agent name. |
| `hooks` | No | object | Hooks scoped to this skill's lifecycle. |

### Bug: `name` Field in Plugin Skills

Confirmed Claude Code v2.1.23 bug: plugin skills with an explicit `name:` field in frontmatter do NOT appear as slash commands. Affects ONLY plugin skills (`plugins/*/skills/*/SKILL.md`). Skills in `~/.claude/skills/` and `.claude/skills/` work correctly.

**Workaround:** Omit the `name:` field in plugin SKILL.md files. Claude Code uses the directory name instead.

### Complete SKILL.md Example

```yaml
---
description: Runs dasel queries against structured config files. Use when reading or updating YAML, TOML, JSON fields by path selector.
disable-model-invocation: false
allowed-tools: Bash, Read, Write
model: sonnet
---

Skill body in Markdown.
```

### SKILL.md with Subagent Fork

```yaml
---
description: Deep research on dasel selectors and expressions
context: fork
agent: Explore
allowed-tools: Bash(dasel *)
---

Research $ARGUMENTS thoroughly using dasel documentation...
```

---

## 4. plugin.json — Complete Schema

Location: `<plugin-root>/.claude-plugin/plugin.json`

The manifest is optional. `name` is the only required field if the manifest exists.

### Complete Schema

```json
{
  "name": "plugin-name",
  "version": "1.2.0",
  "description": "Brief plugin description",
  "author": {
    "name": "Author Name",
    "email": "author@example.com",
    "url": "https://github.com/author"
  },
  "homepage": "https://docs.example.com/plugin",
  "repository": "https://github.com/author/plugin",
  "license": "MIT",
  "keywords": ["keyword1", "keyword2"],
  "commands": ["./custom/commands/special.md"],
  "agents": ["./agents/agent-one.md", "./agents/agent-two.md"],
  "skills": "./custom/skills/",
  "hooks": "./config/hooks.json",
  "mcpServers": "./mcp-config.json",
  "outputStyles": "./styles/",
  "lspServers": "./.lsp.json"
}
```

### Field Reference

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `name` | Yes (if manifest exists) | string | Kebab-case, no spaces. Used for component namespacing. |
| `version` | No | string | Semver e.g. `"1.2.0"`. If set in both plugin.json and marketplace entry, plugin.json takes priority. |
| `description` | No | string | Brief plugin purpose. |
| `author` | No | object | `name`, `email`, `url` fields. |
| `homepage` | No | string | Documentation URL. |
| `repository` | No | string | Source code URL. |
| `license` | No | string | e.g. `"MIT"`, `"Apache-2.0"` |
| `keywords` | No | array of strings | Discovery tags. |
| `commands` | No | string or array | Additional command files/directories. |
| `agents` | No | string or array | MUST be array of individual file paths, NOT a directory string. e.g. `["./agents/my-agent.md"]` |
| `skills` | No | string or array | Skill directories. |
| `hooks` | No | string, array, or object | Hook config paths or inline config. |
| `mcpServers` | No | string, array, or object | MCP config paths or inline config. |
| `outputStyles` | No | string or array | Output style files/directories. |
| `lspServers` | No | string, array, or object | Language Server Protocol config. |

### Critical: `agents` Field Format

The `agents` field must be an array of individual file paths, not a directory string.

```json
// CORRECT
"agents": ["./agents/dasel-operator.md", "./agents/config-researcher.md"]

// WRONG — causes "agents: Invalid input" validation error
"agents": "./agents/"
```

### Path Rules

- All paths must be relative to plugin root
- All paths must start with `./`
- Custom paths supplement default directories (they don't replace them)

### Environment Variable

`${CLAUDE_PLUGIN_ROOT}` — absolute path to the plugin directory at runtime. Use in hooks and MCP server configs:

```json
{
  "hooks": {
    "PostToolUse": [{
      "hooks": [{
        "type": "command",
        "command": "${CLAUDE_PLUGIN_ROOT}/scripts/validate.py"
      }]
    }]
  }
}
```

---

## 5. How Skills Reference Agents

Two mechanisms exist:

### Mechanism 1: Skill Forks into an Agent (`context: fork`)

A skill runs inside a named subagent. The skill content becomes the task/prompt for that agent.

```yaml
---
description: Research dasel selectors thoroughly
context: fork
agent: Explore
---

Research $ARGUMENTS using dasel documentation...
```

The `agent` field can be:
- Built-in: `Explore`, `Plan`, `general-purpose`
- Custom agent name (must exist in `.claude/agents/` or a plugin's `agents/` directory)
- Omitted: defaults to `general-purpose`

### Mechanism 2: Agent Preloads Skills (`skills` field in agent frontmatter)

An agent declares skills to inject at startup. Full skill content is loaded into the agent's context.

```yaml
---
name: dasel-operator
description: Expert dasel operator
skills: dasel-reference, yaml-patterns
---
```

The agent does not inherit skills from the parent conversation — skills must be listed explicitly.

---

## 6. Agent File — Location and Naming Rules

### Location Priority (highest to lowest)

| Location | Scope |
|----------|-------|
| `--agents` CLI flag | Current session only (JSON, not persisted) |
| `.claude/agents/<name>.md` | Current project |
| `~/.claude/agents/<name>.md` | All projects (user-level) |
| `plugins/<plugin>/agents/<name>.md` | Where plugin is installed |

### Naming

- Filename: `<agent-name>.md` (kebab-case)
- `name` field in frontmatter must match kebab-case, lowercase letters and hyphens only, max 64 characters
- Namespaced in UI as `plugin-name:agent-name` when from a plugin

### File Structure

```markdown
---
name: agent-name
description: When Claude should delegate here
tools: Read, Grep, Glob
model: sonnet
color: cyan
---

System prompt body in Markdown. This is what the agent receives
as its system prompt. It does NOT receive the full Claude Code
system prompt — only this body plus basic environment details
(working directory, etc.).
```

---

## 7. Validation Rules Summary

Run validation:

```bash
# Validate single agent or skill file
uv run plugins/plugin-creator/scripts/plugin_validator.py <path>

# Validate entire plugin
uv run plugins/plugin-creator/scripts/plugin_validator.py plugins/my-plugin

# Validate plugin structure (Claude Code built-in)
claude plugin validate plugins/my-plugin
```

### Agent Validation Rules

- `name`: required, kebab-case, max 64 chars
- `description`: required, max 1024 chars, no colons except in URLs (use em dash `—` instead)
- `model`: must be `sonnet`, `opus`, `haiku`, or `inherit` if specified
- `tools`: must be comma-separated string (not YAML array, not JSON array)
- `disallowedTools`: must be comma-separated string
- `skills`: must be comma-separated string

### Skill Validation Rules

- `name`: optional (omit for plugin skills due to bug)
- `description`: optional but recommended
- `allowed-tools`: must be comma-separated string (not YAML array)
- `model`: must be valid alias if specified

### plugin.json Validation Rules

- `name`: required, kebab-case
- `agents`: must be array of individual file paths (not a directory path string)
- All path values must start with `./`
- JSON must be syntactically valid

---

## 8. Real Examples from This Repository

### Agent with All Common Fields

From `plugins/python3-development/agents/python-cli-architect.md`:

```yaml
---
name: python-cli-architect
description: Creates, enhances, and reviews Python CLI code using modern patterns with Typer and Rich. Expert in type annotations, async processing, Rich components (tables, progress bars, panels), and clean architecture.
color: pink
permissionMode: bypassPermissions
---
```

From `plugins/agentskill-kaizen/agents/transcript-analyst.md`:

```yaml
---
name: transcript-analyst
description: "Deep-dive into Claude Code session transcripts using DuckDB SQL and process mining tools — spawned by analyze and explore commands to query JSONL data, detect anti-patterns, extract frustration signals, and mine workflow patterns across sessions"
model: sonnet
color: cyan
skills: transcript-analysis
---
```

### Agent with All Fields (Example/Reference File)

From `plugins/plugin-creator/examples/agents/example-agent.md`:

```yaml
---
name: example-agent
description: "Demonstrates all available agent frontmatter fields. Use when you need a reference for agent configuration or when learning about agent capabilities. Handles example tasks, demonstration requests, and tutorial scenarios."
tools: Read, Grep, Glob, WebFetch, WebSearch
disallowedTools: Bash, Write, Edit
model: sonnet
permissionMode: default
skills: python3-development, claude-skills-overview-2026
hooks:
  PreToolUse:
    - matcher: "Read"
      hooks:
        - type: command
          command: "echo 'About to read a file'"
          timeout: 5
color: cyan
---
```

### Minimal Agent (No Optional Fields)

From `plugins/summarizer/agents/image-summarizer.md`:

```yaml
---
name: image-summarizer
description: Autonomous image and screenshot summarization agent. Use when user requests description of images, screenshots, diagrams, or visual content and does not need to discuss it interactively.
---
```

---

## 9. Hooks Configuration Format (in Agent/Skill Frontmatter)

```yaml
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/validate.sh"
          timeout: 30
  PostToolUse:
    - matcher: "Write|Edit"
      hooks:
        - type: command
          command: "${CLAUDE_PLUGIN_ROOT}/scripts/lint.py"
  Stop:
    - hooks:
        - type: prompt
          prompt: "Summarize what was accomplished."
```

Hook types: `command`, `prompt`, `agent`

`Stop` hooks in agent frontmatter are automatically converted to `SubagentStop` at runtime.

---

## 10. Standard Plugin Directory Layout

```
my-plugin/
├── .claude-plugin/
│   └── plugin.json          # manifest (optional)
├── agents/                  # agent .md files
│   └── my-agent.md
├── skills/                  # skill directories
│   └── my-skill/
│       └── SKILL.md
├── commands/                # legacy (use skills/ for new work)
├── hooks/
│   └── hooks.json
├── scripts/                 # helper scripts
├── .mcp.json                # MCP server definitions
└── .lsp.json                # LSP server configs
```

Components (agents/, skills/, hooks/) must be at the plugin root, NOT inside `.claude-plugin/`. Only `plugin.json` belongs in `.claude-plugin/`.
