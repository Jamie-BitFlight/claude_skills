# Contributing to Claude Skills Collection

## Adding a New Plugin

### 1. Create the Plugin

Use the plugin-creator plugin to scaffold a new plugin:

```bash
uv run plugins/plugin-creator/scripts/create_plugin.py
```

Or create manually following the structure:

```text
plugins/your-plugin-name/
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   └── your-skill/
│       └── SKILL.md
├── agents/           # Optional
├── commands/         # Optional
└── README.md
```

### 2. Validate the Plugin

Before adding to the marketplace, validate the plugin structure with `skilllint`:

```bash
# Validate and auto-fix a single plugin
uvx skilllint@latest check --fix plugins/your-plugin-name/

# Dry-run to preview fixes before applying
uvx skilllint@latest check --check plugins/your-plugin-name/
```

All validation checks must pass with no errors.

### 3. Update Marketplace

**MANDATORY**: After creating a new plugin, add it to `.claude-plugin/marketplace.json`:

```json
{
  "name": "your-plugin-name",
  "source": "./plugins/your-plugin-name"
}
```

The `name` field is the install name users will use (`/plugin install your-plugin-name@jamie-bitflight-skills`). It can differ from the directory name — for example, `development-harness` installs as `dh` and `the-rewrite-room` installs as `rwr`.

**Note:** The shared `agent-marketplace-versioner` pre-commit hook bumps plugin versions and synchronizes manifest entries for staged plugin changes. Marketplace version repair is proposed after merge in a normal PR. Do not manually edit version fields for the normal local workflow; see [marketplace versioning](docs/marketplace-versioning.md).

#### Validate Marketplace JSON

After editing, validate the JSON syntax:

```bash
python3 -m json.tool .claude-plugin/marketplace.json > /dev/null && echo "Valid" || echo "Invalid"
```

### 4. Test Locally

Test the plugin via the local marketplace:

```bash
# Add local marketplace (if not already added)
/plugin marketplace add ./.claude-plugin/marketplace.json

# Install your plugin
/plugin install your-plugin-name@jamie-bitflight-skills --scope local

# Test functionality
# ... use the plugin ...

# Uninstall when done
/plugin uninstall your-plugin-name@jamie-bitflight-skills --scope local
```

## Removing a Plugin

### 1. Remove Plugin Directory

```bash
rm -rf plugins/your-plugin-name/
```

### 2. Update Marketplace

Remove the plugin entry from `.claude-plugin/marketplace.json`. Find and delete the entire plugin object, including any trailing comma.

### 3. Validate

```bash
python3 -m json.tool .claude-plugin/marketplace.json > /dev/null
```

Version bumping happens automatically on commit via the pre-commit hook.

## Updating an Existing Plugin

Make your changes and commit. The shared `agent-marketplace-versioner` pre-commit hook:

- Bumps the plugin version in `.claude-plugin/plugin.json`
- Syncs the component arrays (skills, agents, commands) in `plugin.json`
- Reconciles local marketplace membership; marketplace version repair is deferred to the post-merge repair PR

You do not need to manually bump any version field.

### Plugin Validation

After making changes to any plugin, validate it before committing:

```bash
# Validate single plugin (auto-fix mode)
uvx skilllint@latest check --fix plugins/your-plugin-name/

# Validate all plugins
uvx skilllint@latest check plugins/
```

The `skilllint` pre-commit hook also runs automatically on commit and applies fixes inline.

## Common Validation Errors

| Error | Cause | Fix |
| --- | --- | --- |
| `name: Plugin name cannot contain spaces` | Plugin name has spaces | Use kebab-case: `my-plugin` not `My Plugin` |
| `agents: Invalid input` | Used `"./agents/"` directory string | Use array: `["./agents/file.md"]` |
| `name: Required` | Missing name field in plugin.json | Add `"name": "plugin-name"` |
| Invalid JSON syntax | Malformed JSON | Run `python3 -m json.tool plugin.json` to find error |

## Marketplace Description Guidelines

The marketplace description should:

- **Identify the target audience** (who this is for)
- **Describe problem domains** (what problems it solves)
- **Avoid listing plugin names** (users can see the plugin list)
- **Avoid stating plugin count** (creates maintenance burden)

**Good:**

> "Professional development workflow extensions for Python engineers, DevOps practitioners, and AI agent developers."

**Bad:**

> "Collection of 26 plugins including python3-development, holistic-linting, plugin-creator..."

## Pull Request Checklist

Before submitting a PR:

- [ ] All plugins validate successfully (`uvx skilllint@latest check plugins/`)
- [ ] `.claude-plugin/marketplace.json` updated (if adding/removing plugins)
- [ ] Marketplace JSON is valid (`python3 -m json.tool`)
- [ ] Tested locally via marketplace installation
- [ ] README.md updated (if adding new plugin to tables — include install name)
- [ ] Plugin has README.md with usage examples

## Code Quality

### Frontmatter Validation

Validate skill and agent frontmatter:

```bash
# Single file
uvx skilllint@latest check path/to/SKILL.md

# Entire plugin directory
uvx skilllint@latest check plugins/your-plugin/

# Auto-fix issues (dry-run first)
uvx skilllint@latest check --check path/to/SKILL.md
uvx skilllint@latest check --fix path/to/SKILL.md
```

### Linting

Run formatters before committing:

```bash
uv run prek run --files path/to/modified/file.md
```

Pre-commit hooks run `ruff`, `ruff-format`, `markdownlint-cli2`, `biome-check`, and `skilllint` automatically on commit. Fix any errors they report before pushing.

## Questions?

Open an issue or check existing plugin implementations for examples.
