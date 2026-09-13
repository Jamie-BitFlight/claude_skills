# Plugin Creator Scripts

Utility scripts for maintaining Claude Code plugins, skills, agents, and commands. All scripts have shebangs and executable permissions — invoke them directly or via `uv run`.

---

## check_agent_auto_discovery.py

Regression guard that detects `plugin.json` files where explicit component arrays silently mask auto-discovered agents, skills, or commands.

### Background

Claude Code auto-discovers every `.md` file in a plugin's `agents/`, `commands/`, and `skills/` directories — but only when the corresponding key is **absent** from `plugin.json`. Writing the key with even a single entry overrides auto-discovery: the declared list becomes the complete list and every unlisted file becomes invisible.

Two production incidents hit this trap:

- **2026-03-17**: `python3-development` committed two agents in `"agents": [...]` and 17 of 19 agents disappeared silently.
- **2026-04-12**: A buggy pre-commit hook auto-added a 2-entry `agents` array, which would have masked 21 of 23 agents.

### What it checks

Fails when any `plugin.json` under `plugins/` contains an `agents`, `commands`, or `skills` key that is a strict subset of the corresponding files on disk, or when the key is an empty list.

### Usage

```bash
# Check all plugins for auto-discovery violations
./plugins/plugin-creator/scripts/check_agent_auto_discovery.py
```

The script exits non-zero on violations and explains the fix: remove the key entirely to restore auto-discovery, or list every file explicitly.

---

## create_plugin.py

Interactive plugin scaffolding tool. Prompts for plugin details and creates a new plugin with proper structure and a validated `plugin.json`.

### What it creates

- `.claude-plugin/` directory with `plugin.json`
- Optional `skills/`, `agents/`, `commands/` directories
- Self-validates with `claude plugin validate` before reporting success

### Subcommands

| Subcommand | Description |
|---|---|
| `create` | Interactive wizard — prompts for name, description, author, and which directories to create |
| `validate` | Validate an existing plugin directory structure |

### Usage

```bash
# Create a new plugin interactively
./plugins/plugin-creator/scripts/create_plugin.py create

# Validate an existing plugin
./plugins/plugin-creator/scripts/create_plugin.py validate <plugin-path>
```

---

## fix_tool_formats.py

Scans Claude Code frontmatter files and converts invalid tool field formats to the required comma-separated string format.

### What it fixes

Claude Code requires tool specifications in frontmatter to use comma-separated string format:

```yaml
tools: Read, Grep, Glob, Bash
```

The script converts two invalid formats:

**YAML list format:**

```yaml
# Before (invalid)
allowed-tools:
  - Read
  - Glob
  - Bash

# After (valid)
allowed-tools: Read, Glob, Bash
```

**JSON array format:**

```yaml
# Before (invalid)
tools: ["Read", "Grep", "Glob", "Write"]

# After (valid)
tools: Read, Grep, Glob, Write
```

### Why this matters

Invalid formats written by Claude in earlier sessions become "evidence" in future searches, creating a feedback loop where the AI learns incorrect patterns from its own prior output.

### Usage

```bash
# Fix all .claude directories in the home directory
./plugins/plugin-creator/scripts/fix_tool_formats.py

# Also scan ~/repos/** directories
./plugins/plugin-creator/scripts/fix_tool_formats.py --scan-repos

# Preview changes without writing
./plugins/plugin-creator/scripts/fix_tool_formats.py --dry-run
```

### Arguments

| Flag | Description |
|---|---|
| `--scan-repos` | Also scan `~/repos/**` directories (default: off) |
| `--no-scan-repos` | Scan only `~/.claude/**` (default) |
| `--dry-run` | Show what would be changed without modifying files |

### Scan locations

By default, scans:

- `~/.claude/agents/**/*.md`
- `~/.claude/commands/**/*.md`
- `~/.claude/skills/**/SKILL.md`

With `--scan-repos`, additionally scans all `.claude` directories under `~/repos/`.

---

## normalize_frontmatter.py

Round-trips every markdown file with YAML frontmatter through `ruamel.yaml` to strip unnecessary quotes. Only the frontmatter block is affected; the body of each file is preserved verbatim.

### What it normalizes

Removes over-quoting introduced by editors or other tools — e.g., `description: "my skill"` becomes `description: my skill`. Quotes required for YAML correctness (such as values containing `:`) are preserved.

### Usage

```bash
# Apply normalization in-place
./plugins/plugin-creator/scripts/normalize_frontmatter.py

# Preview changes without writing
./plugins/plugin-creator/scripts/normalize_frontmatter.py --dry-run

# Specify a different repository root
./plugins/plugin-creator/scripts/normalize_frontmatter.py --root /path/to/repo
```

### Arguments

| Flag | Description |
|---|---|
| `--dry-run` | Report diffs without writing files |
| `--root DIRECTORY` | Repository root to search from (default: `.`) |

### Files discovered

- `plugins/**/*.md`
- `.claude/**/*.md`

Excludes `node_modules/`, `.venv/`, and `*.lock` files.

---

## validate-task-file.sh

Validates refactoring task file format and structure. Used during plugin refactoring workflows to ensure task files created by the planner agent are correctly formatted before execution begins.

### Usage

```bash
./plugins/plugin-creator/scripts/validate-task-file.sh <path/to/tasks-refactor-*.md>
```

### What it validates

- Task structure and required fields
- Status field format (`❌ NOT STARTED`, `🔄 IN PROGRESS`, `✅ COMPLETE`)
- Dependency references — all referenced task IDs exist in the same file
- Acceptance criteria are present for each task
- Agent assignments are specified

Exits 0 on pass, non-zero on failure. Prints a summary of errors and warnings.

---

## Library Modules

These modules are not standalone scripts. They are imported by the scripts above.

| Module | Purpose |
|---|---|
| `frontmatter_core.py` | Pydantic models and validation logic for SKILL.md, agent, and command frontmatter. Shared by `normalize_frontmatter.py` and the `skilllint` validators. |
| `frontmatter_utils.py` | Load/dump helpers for YAML frontmatter using `ruamel.yaml` round-trip mode. Preserves formatting and only adds quotes where YAML syntax requires them. |

---

## Pre-Commit Integration

The shared versioner and one local guard run automatically via `.pre-commit-config.yaml`:

| Hook ID | Script | Trigger pattern | Purpose |
|---|---|---|---|
| `agent-marketplace-versioner` | [agent-marketplace-versioner](https://github.com/Jamie-BitFlight/agent-marketplace-versioner) (external) | all conventional manifests | Plugin versioning and marketplace membership reconciliation |
| `check-agent-auto-discovery` | `check_agent_auto_discovery.py` | `^plugins/.*plugin\.json$` | Guard against silent component masking |

---

## Requirements

All Python scripts require Python 3.11+ and `uv`. The scripts use PEP 723 inline metadata to declare their own dependencies — `uv` installs them automatically.

Bash scripts require Bash 5.1+ and standard POSIX utilities.
