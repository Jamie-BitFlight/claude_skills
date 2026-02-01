# Plugin Creator & Refactoring Toolkit

Complete plugin development toolkit for creating, refactoring, and validating Claude Code plugins. Combines plugin creation, systematic refactoring workflows, and comprehensive validation tools.

## Overview

This plugin provides end-to-end capabilities for plugin development:

**Plugin Creation:**

- Step-by-step guidance for creating new plugins
- Frontmatter validation and auto-fixing
- Structure scaffolding and template generation

**Plugin Refactoring:**

- Analyze plugin structure and identify issues
- Create detailed refactoring plans
- Execute tasks via specialized agents
- Validate refactoring completeness

**Validation Tools:**

- Comprehensive frontmatter schema validation
- Skill structure and quality checks
- Internal link validation
- Line count enforcement

## ⚠️ Critical Bug Discovery: Skill Name Field (Plugin Skills Only)

**Discovered:** 2026-01-29
**Claude Code Version:** v2.1.23
**Scope:** **Only affects plugin skills** - does NOT affect `.claude/skills/` directories

### The Bug

**Plugin skills** with an explicit `name:` field in their frontmatter **DO NOT appear as slash commands**, even when `user-invocable: true` is set.

**Important:** This bug only affects skills distributed via plugins. Skills in `.claude/skills/` (personal/project) work fine with or without the `name:` field.

**Symptoms (Plugin Skills Only):**

- Skill in plugin's `skills` array
- Skill has `user-invocable: true`
- Skill has `name: skill-name` in frontmatter
- **Result:** `/plugin-name:skill-name` does NOT appear in autocomplete

**Not Affected:**

- Skills in `~/.claude/skills/` (user-level) ✓
- Skills in `.claude/skills/` (project-level) ✓
- These work fine with `name:` field

**Workaround (For Plugin Skills):**

```yaml
# ❌ BROKEN - skill won't appear as slash command
---
name: my-skill
description: Does something useful
user-invocable: true
---

# ✅ WORKS - skill appears as slash command
---
description: Does something useful
user-invocable: true
---
```

Claude Code automatically uses the directory name, so omitting `name:` allows proper slash command registration.

### Automatic Fix

The `validate_frontmatter.py` script now automatically removes `name:` fields from SKILL.md files:

```bash
uv run ./scripts/validate_frontmatter.py fix ./skills/my-skill/SKILL.md
```

Output:

```
✓ Removed 'name' field (Claude Code bug: skills with 'name' field don't appear as slash commands)
```

## When to Use

Use this plugin when:

- Creating new plugins, skills, commands, or agents
- Validating frontmatter in SKILL.md or agent files
- A skill exceeds 500 lines and needs splitting
- Skills cover multiple distinct domains
- Agent descriptions have weak triggers
- Plugin structure needs reorganization
- Systematically improving plugin quality

## Quick Start

### Creating Plugins

```bash
# Generate new plugin structure
uv run ./scripts/create_plugin.py

# Validate frontmatter
uv run ./scripts/validate_frontmatter.py validate ./skills/my-skill/SKILL.md

# Auto-fix common frontmatter issues
uv run ./scripts/validate_frontmatter.py fix ./skills/my-skill/SKILL.md
```

### Refactoring Plugins

```bash
# Quick check of skill line counts
/plugin-creator:count-lines ./plugins/my-plugin

# Validate skill structure
./scripts/validate-skill-structure.sh ./skills/my-skill
```

## Commands

| Command                       | Purpose                | Example                                           |
| ----------------------------- | ---------------------- | ------------------------------------------------- |
| `/plugin-creator:count-lines` | Quick line count check | `/plugin-creator:count-lines ./plugins/my-plugin` |

## Skills

### Creation Skills

| Skill                           | Purpose                                                                                        |
| ------------------------------- | ---------------------------------------------------------------------------------------------- |
| `plugin-creator`                | Step-by-step guidance for creating Claude Code plugins                                         |
| `skill-creator`                 | Official Anthropic guide for creating effective skills (modified from upstream)                |
| `agent-creator`                 | Create high-quality Claude Code agents from scratch or by adapting existing agents             |
| `write-frontmatter-description` | Write or rewrite frontmatter description fields for skills and agents following best practices |

### Reference Skills

| Skill                           | Purpose                                                          |
| ------------------------------- | ---------------------------------------------------------------- |
| `claude-skills-overview-2026`   | Complete reference for Claude Code skills system (January 2026)  |
| `claude-plugins-reference-2026` | Complete reference for Claude Code plugins system (January 2026) |
| `claude-hooks-reference-2026`   | Complete reference for Claude Code hooks system (January 2026)   |

### Refactoring Skills

| Skill                 | Purpose                                                   |
| --------------------- | --------------------------------------------------------- |
| `assessor`            | Analyze plugin and create refactoring task files          |
| `implement-refactor`  | Execute refactoring tasks with parallel orchestration     |
| `ensure-complete`     | Validate refactoring and create follow-up tasks if needed |
| `refactor-plugin`     | Complete plugin refactoring workflow                      |
| `refactor-skill`      | Split oversized skills into smaller focused skills        |
| `start-refactor-task` | Execute individual refactoring tasks                      |
| `feature-discovery`   | Research feature requests and identify gaps               |

## Agents

| Agent                | Purpose                                       | Triggers                                                |
| -------------------- | --------------------------------------------- | ------------------------------------------------------- |
| `refactor-planner`   | Analyze plugins and create refactoring plans  | "plan a refactoring", "analyze plugin for refactoring"  |
| `refactor-executor`  | Execute refactoring tasks from plans          | "execute refactoring tasks", "run the refactoring plan" |
| `refactor-validator` | Validate refactoring completeness and quality | "validate refactoring", "verify refactoring complete"   |

## Scripts

### Validation Scripts

| Script                        | Purpose                                       | Usage                                              |
| ----------------------------- | --------------------------------------------- | -------------------------------------------------- |
| `validate_frontmatter.py`     | Comprehensive schema validation with auto-fix | `uv run validate_frontmatter.py validate SKILL.md` |
| `validate-skill-structure.sh` | Skill structure and quality validation        | `./validate-skill-structure.sh ./skills/my-skill`  |
| `validate-task-file.sh`       | Validate refactoring task file format         | `./validate-task-file.sh tasks.md`                 |

### Utility Scripts

| Script                 | Purpose                                   | Usage                                        |
| ---------------------- | ----------------------------------------- | -------------------------------------------- |
| `create_plugin.py`     | Interactive plugin scaffolding            | `uv run create_plugin.py`                    |
| `count-skill-lines.sh` | Count lines and identify oversized skills | `./count-skill-lines.sh ./plugins/my-plugin` |
| `fix-tool-formats.py`  | Fix tool field formatting issues          | `uv run fix-tool-formats.py`                 |

### Script Usage Examples

```bash
# Validate frontmatter (comprehensive)
uv run ./scripts/validate_frontmatter.py validate ./skills/my-skill/SKILL.md

# Validate all frontmatter in a directory
uv run ./scripts/validate_frontmatter.py batch ./plugins/my-plugin

# Auto-fix frontmatter issues
uv run ./scripts/validate_frontmatter.py fix ./skills/my-skill/SKILL.md --dry-run
uv run ./scripts/validate_frontmatter.py fix ./skills/my-skill/SKILL.md

# Batch fix all frontmatter
uv run ./scripts/validate_frontmatter.py fix-batch ./plugins/my-plugin

# Validate skill structure (line counts, links, directories)
./scripts/validate-skill-structure.sh ./skills/my-skill

# Count skill lines
./scripts/count-skill-lines.sh ./plugins/my-plugin
```

## Validation Capabilities

### Frontmatter Validation (`validate_frontmatter.py`)

**Checks:**

- YAML syntax validity
- No forbidden multiline indicators (`>-`, `|-`)
- Required fields present (`name`, `description` for agents)
- Field types match schema (string, bool, object)
- Field values within constraints (length, pattern, valid values)
- Enumeration validation (model, permissionMode)

**Auto-fixes:**

- YAML arrays → comma-separated strings (tools, skills, etc.)
- Multiline descriptions → single-line quoted strings
- Unquoted descriptions with colons

**Supports:**

- Skills (SKILL.md)
- Agents (.md in agents/ directories)
- Commands (.md in commands/ directories)

### Skill Structure Validation (`validate-skill-structure.sh`)

**Checks:**

- SKILL.md presence and frontmatter structure
- Name and description fields
- Name format (lowercase, hyphens)
- Description length (minimum 20 characters)
- Description trigger phrases
- Line count limits (warns >500, errors >800)
- Progressive disclosure structure (references/, examples/, scripts/)
- Internal markdown link validity

## Refactoring Workflow

```text
┌─────────────────────────────────────────────────────────────────┐
│                    REFACTORING WORKFLOW                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Invoke @"plugin-creator:refactor-planner (agent)"              │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │ Phase 1:        │                                            │
│  │ Assessment      │──▶ Plugin Assessment Report                │
│  └────────┬────────┘                                            │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │ Phase 2:        │                                            │
│  │ Design          │──▶ refactor-design-{slug}.md               │
│  └────────┬────────┘                                            │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │ Phase 3:        │                                            │
│  │ Task Planning   │──▶ tasks-refactor-{slug}.md                │
│  └────────┬────────┘                                            │
│           │                                                      │
│           ▼                                                      │
│  Invoke @"plugin-creator:refactor-executor (agent)"             │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │ Phase 4:        │                                            │
│  │ Execution       │──▶ Parallel agent execution                │
│  └────────┬────────┘                                            │
│           │                                                      │
│           ▼                                                      │
│  Invoke @"plugin-creator:refactor-validator (agent)"            │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │ Phase 5:        │                                            │
│  │ Validation      │──▶ Validation Report                       │
│  └────────┬────────┘                                            │
│           │                                                      │
│     ┌─────┴─────┐                                               │
│     │           │                                               │
│     ▼           ▼                                               │
│  [Issues]    [No Issues]                                        │
│     │           │                                               │
│     ▼           ▼                                               │
│  Follow-up   COMPLETE                                           │
│  Tasks                                                          │
│     │                                                           │
│     └─────────▶ Recurse                                         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Quality Standards

### Skill Size Limits

- **Recommended**: <500 lines (body content)
- **Warning**: 500-800 lines - consider splitting
- **Critical**: >800 lines - must split

### Skill Split Requirements

When splitting skills:

- No content loss (100% migration)
- Cross-references between new skills
- Original skill becomes facade/meta-skill
- Backwards compatibility maintained

### Frontmatter Requirements

**Skills:**

- `name`: Optional (uses directory name if omitted)
- `description`: Optional (uses first paragraph if omitted)
- Valid tool/model values if specified

**Agents:**

- `name`: Required (lowercase, hyphens)
- `description`: Required (trigger keywords)
- `model`: One of sonnet/opus/haiku/inherit
- `tools`: Comma-separated string (not array)

## Plugin System Fundamentals

### Plugin Caching and File Resolution

Claude Code copies plugins to a cache directory rather than using them in-place for security and verification.

**How it works:**

- Marketplace plugins: The `source` path is copied recursively
- Plugins with `.claude-plugin/plugin.json`: The directory containing `.claude-plugin/` is copied recursively

**Path traversal limitations:**

- Plugins cannot reference files outside their directory (`../shared-utils` will fail)
- External files are not copied to the cache

**Solutions for external dependencies:**

1. **Use symlinks:** Create symlinks within your plugin directory (symlinks are followed during copy)

   ```bash
   ln -s /path/to/shared-utils ./shared-utils
   ```

2. **Restructure marketplace:** Set source to parent directory that contains all required files

### Installation Scopes

When installing a plugin, choose a scope that determines availability:

| Scope     | Settings file                 | Use case                                                 |
| --------- | ----------------------------- | -------------------------------------------------------- |
| `user`    | `~/.claude/settings.json`     | Personal plugins available across all projects (default) |
| `project` | `.claude/settings.json`       | Team plugins shared via version control                  |
| `local`   | `.claude/settings.local.json` | Project-specific plugins, gitignored                     |
| `managed` | `managed-settings.json`       | Managed plugins (read-only, update only)                 |

**Examples:**

```bash
# Install to user scope (default)
claude plugin install plugin-creator@jamie-bitflight-skills

# Install to project scope (shared with team)
claude plugin install plugin-creator@jamie-bitflight-skills --scope project

# Install to local scope (gitignored)
claude plugin install plugin-creator@jamie-bitflight-skills --scope local
```

### Environment Variables

**`${CLAUDE_PLUGIN_ROOT}`:** Absolute path to your plugin directory. Use in hooks, MCP servers, and scripts.

**`${CLAUDE_PROJECT_DIR}`:** Project root directory (where Claude Code was started).

**Example:**

```json
{
  "hooks": {
    "PostToolUse": [{
      "hooks": [{
        "type": "command",
        "command": "${CLAUDE_PLUGIN_ROOT}/scripts/process.sh"
      }]
    }]
  }
}
```

### CLI Commands Reference

**Install plugin:**

```bash
claude plugin install <plugin> [--scope user|project|local]
```

**Uninstall plugin:**

```bash
claude plugin uninstall <plugin> [--scope user|project|local]
# Aliases: remove, rm
```

**Enable/disable plugin:**

```bash
claude plugin enable <plugin> [--scope user|project|local]
claude plugin disable <plugin> [--scope user|project|local]
```

**Update plugin:**

```bash
claude plugin update <plugin> [--scope user|project|local|managed]
```

**Validate plugin:**

```bash
claude plugin validate <plugin-directory>
/plugin validate <plugin-directory>  # In session
```

### Testing Without Installation

```bash
# Load plugin for current session only
claude --plugin-dir ./plugins/plugin-creator

# Load multiple plugins
claude --plugin-dir ./plugin-one --plugin-dir ./plugin-two
```

## Installation

```bash
# From marketplace (user scope - default)
/plugin install plugin-creator@jamie-bitflight-skills

# Install to project scope (shared with team)
claude plugin install plugin-creator@jamie-bitflight-skills --scope project

# For development (session only)
claude --plugin-dir ./plugins/plugin-creator
```

## Example Sessions

### Creating a New Plugin

```bash
# Generate plugin structure interactively
uv run ./scripts/create_plugin.py

# Validate the generated frontmatter
uv run ./scripts/validate_frontmatter.py batch ./my-new-plugin

# Validate plugin manifest
claude plugin validate ./my-new-plugin
```

### Refactoring an Existing Plugin

```bash
# 1. Check skill sizes
/plugin-creator:count-lines ./plugins/python3-development

# Output shows skills over 500 lines

# 2. Validate skill structures
./scripts/validate-skill-structure.sh ./plugins/python3-development/skills/python3

# 3. Invoke @"plugin-creator:refactor-planner (agent)"
Use @"plugin-creator:refactor-planner (agent)" to analyze ./plugins/python3-development

# Assessment runs, creates plan files

# 4. Review plan at .claude/plan/refactor-design-python3-development.md

# 5. Invoke @"plugin-creator:refactor-executor (agent)" when ready
Use @"plugin-creator:refactor-executor (agent)" to execute the python3-development refactoring plan

# Tasks execute in parallel where possible

# 6. Invoke @"plugin-creator:refactor-validator (agent)"
Use @"plugin-creator:refactor-validator (agent)" to validate the python3-development refactoring

# If issues found, follow-up tasks created and cycle repeats
```

### Validating and Fixing Frontmatter

```bash
# Check a single file
uv run ./scripts/validate_frontmatter.py validate ./skills/my-skill/SKILL.md

# Validate all skills in a plugin
uv run ./scripts/validate_frontmatter.py batch ./plugins/my-plugin

# Auto-fix issues (dry-run first)
uv run ./scripts/validate_frontmatter.py fix ./skills/my-skill/SKILL.md --dry-run

# Apply fixes
uv run ./scripts/validate_frontmatter.py fix ./skills/my-skill/SKILL.md

# Batch fix entire plugin
uv run ./scripts/validate_frontmatter.py fix-batch ./plugins/my-plugin
```

## Plugin Component Reference

### plugin.json Component Fields

| Field          | Type           | Description                                         | Example                                  |
| -------------- | -------------- | --------------------------------------------------- | ---------------------------------------- |
| `commands`     | string\|array  | Additional command files/directories                | `"./custom/cmd.md"` or `["./cmd1.md"]`   |
| `agents`       | string\|array  | Additional agent files or directories               | `"./custom/agents/"` or `["./agent.md"]` |
| `skills`       | string\|array  | Additional skill directories                        | `"./custom/skills/"`                     |
| `hooks`        | string\|object | Hook config path or inline config                   | `"./hooks.json"`                         |
| `mcpServers`   | string\|object | MCP config path or inline config                    | `"./mcp-config.json"`                    |
| `outputStyles` | string\|array  | Additional output style files/directories           | `"./styles/"`                            |
| `lspServers`   | string\|object | Language Server Protocol config (code intelligence) | `"./.lsp.json"`                          |

**Path behavior:**

- Custom paths supplement default directories (don't replace them)
- All paths must be relative and start with `./`
- Multiple paths can be specified as arrays

### LSP Servers

Plugins can provide Language Server Protocol (LSP) servers for real-time code intelligence:

- **Instant diagnostics:** Claude sees errors and warnings immediately after edits
- **Code navigation:** go to definition, find references, hover information
- **Language awareness:** type information and documentation for code symbols

**Configuration format:**

```json
{
  "lspServers": {
    "python": {
      "command": "pyright-langserver",
      "args": ["--stdio"],
      "extensionToLanguage": {
        ".py": "python"
      }
    }
  }
}
```

**Note:** LSP servers require separate binary installation. LSP plugins configure Claude Code's connection to a language server but don't include the server itself.

**Available LSP plugins:**

| Plugin           | Language server  | Install command                                                                            |
| ---------------- | ---------------- | ------------------------------------------------------------------------------------------ |
| `pyright-lsp`    | Pyright (Python) | `pip install pyright` or `npm install -g pyright`                                          |
| `typescript-lsp` | TypeScript LS    | `npm install -g typescript-language-server typescript`                                     |
| `rust-lsp`       | rust-analyzer    | See [rust-analyzer installation](https://rust-analyzer.github.io/manual.html#installation) |

## Related Plugins

- **holistic-linting** - Code quality and linting workflows
- **prompt-optimization-claude-45** - Optimize AI-facing documentation
- **python3-development** - Python development best practices

## Version

2.5.0 - Added official Anthropic skill-creator skill (modified from upstream)

## Author

Jamie Nelson (<https://github.com/bitflight-devops>)

## Attributions

- **skill-creator skill**: Modified version of the official Anthropic skill-creator from [anthropics/skills](https://github.com/anthropics/skills/tree/69c0b1a0674149f27b61b2635f935524b6add202/skills/skill-creator). Licensed under Apache License 2.0 (see `skills/skill-creator/LICENSE.txt`).

## License

MIT License (excluding skill-creator which retains Apache License 2.0)
