# Plugin Creator Scripts

Utility scripts for maintaining Claude Code plugins, skills, agents, and commands. All scripts have shebangs and executable permissions — invoke them directly or via `uv run`.

---

## check_agent_auto_discovery.py

Regression guard that detects `plugin.json` files where explicit component path fields silently mask auto-discovered agents or commands.

### Background

Claude Code auto-discovers every `.md` file in a plugin's `agents/` and `commands/` directories only when the corresponding key is **absent** from `plugin.json`. Writing either key overrides that default directory. Custom `skills` paths are additive to the default `skills/` scan and are not checked by this guard.

Two production incidents hit this trap:

- **2026-03-17**: `python3-development` committed two agents in `"agents": [...]` and 17 of 19 agents disappeared silently.
- **2026-04-12**: A buggy pre-commit hook auto-added a 2-entry `agents` array, which would have masked 21 of 23 agents.

### What it checks

Fails when any `plugin.json` under `plugins/` contains an `agents` or `commands` string/array that omits corresponding default-path files, or when the field is empty.

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
