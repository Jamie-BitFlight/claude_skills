---
name: claude-plugins-reference-2026
description: Claude Code plugin and marketplace reference. Use when creating plugins, configuring component paths, validating plugin roots, or distributing local, Git, and archive sources.
user-invocable: true
---

# Claude Code Plugins and Marketplaces Reference

Plugins extend Claude Code with skills, agents, hooks, MCP servers, and LSP servers. This reference covers verified plugin and marketplace boundaries.

---

## Plugin Components Overview

Plugins can include any combination of:

- **Skills**: SKILL.md directories that Claude can invoke automatically
- **Commands**: Markdown files creating `/name` shortcuts (legacy; use skills instead)
- **Agents**: Specialized subagents for specific tasks
- **Hooks**: Event handlers responding to Claude Code events
- **MCP Servers**: Model Context Protocol servers for external tool integration
- **LSP Servers**: Language Server Protocol servers for code intelligence

---

## plugin.json Schema

The optional `plugin.json` file in `.claude-plugin/` defines Claude Code-specific plugin metadata
and configuration. Claude Code can load a plugin without it when components use default locations;
add it when the plugin needs a stable name, metadata, or custom component paths.

### Complete Schema Example

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
  "agents": "./custom/agents/security-reviewer.md",
  "skills": "./custom/skills/",
  "hooks": "./config/hooks.json",
  "mcpServers": "./mcp-config.json",
  "outputStyles": "./styles/",
  "lspServers": "./.lsp.json"
}
```

### Required Fields

| Field  | Type   | Description                               | Example              |
| ------ | ------ | ----------------------------------------- | -------------------- |
| `name` | string | Unique identifier (kebab-case, no spaces) | `"deployment-tools"` |

### Metadata Fields

| Field         | Type   | Description                         | Example                                            |
| ------------- | ------ | ----------------------------------- | -------------------------------------------------- |
| `version`     | string | Semantic version                    | `"2.1.0"`                                          |
| `description` | string | Brief explanation of plugin purpose | `"Deployment automation tools"`                    |
| `author`      | object | Author information                  | `{"name": "Dev Team", "email": "dev@company.com"}` |
| `homepage`    | string | Documentation URL                   | `"https://docs.example.com"`                       |
| `repository`  | string | Source code URL                     | `"https://github.com/user/plugin"`                 |
| `license`     | string | License identifier                  | `"MIT"`, `"Apache-2.0"`                            |
| `keywords`    | array  | Discovery tags                      | `["deployment", "ci-cd"]`                          |

### Component Path Fields

| Field          | Type           | Description                                                                    | Example                                |
| -------------- | -------------- | ------------------------------------------------------------------------------ | -------------------------------------- |
| `commands`     | string\|array  | Command files/directories — replaces the default `commands/`                   | `"./custom/cmd.md"` or `["./cmd1.md"]` |
| `agents`       | string\|array  | Agent file path(s) — replaces the default `agents/` scan | `"./custom/reviewer.md"` or `["./custom/reviewer.md"]` |
| `skills`       | string\|array  | Additional skill directories — loaded alongside the default `skills/`          | `"./custom/skills/"`                   |
| `hooks`        | string\|object | Hook config path or inline config                                              | `"./hooks.json"`                       |
| `mcpServers`   | string\|object | MCP config path or inline config                                               | `"./mcp-config.json"`                  |
| `outputStyles` | string\|array  | Output style files/directories — replaces the default `output-styles/`         | `"./styles/"`                          |
| `lspServers`   | string\|object | Language Server Protocol config for code intelligence (go to definition, etc.) | `"./.lsp.json"`                        |
| `monitors`     | string\|array  | Background monitor configurations — path to monitors.json or inline array      | `"./monitors/monitors.json"`           |
| `userConfig`   | object         | User-configurable values prompted at enable time; stored in keychain or settings | See [User Config Reference](./references/user-config.md) |
| `channels`     | array          | Message channel declarations bound to MCP servers with per-channel user config | See [User Config Reference](./references/user-config.md) |

**Path behavior rules:**

Whether a custom path replaces or extends the plugin's default directory depends on the field:

- **Replaces the default**: `commands`, `agents`, `workflows`, `outputStyles`, `experimental.themes`, `experimental.monitors`. Declaring the key stops the matching default directory being scanned. To keep the default and add more, list it explicitly: `"commands": ["./commands/", "./extras/"]`
- **Adds to the default**: `skills`. The default `skills/` directory is always scanned, and directories listed in `skills` load alongside it. Exception: for a marketplace entry whose `source` resolves to the marketplace root, declaring specific subdirectories replaces the default `skills/` scan
- All paths must be relative to plugin root and start with `./`
- Multiple paths can be specified as arrays
- `agents` accepts one path as a string or multiple paths as an array. Declaring it replaces the default `agents/` scan, so include default-path files when retaining them.

SOURCE: [Plugins reference — Component path fields](https://code.claude.com/docs/en/plugins-reference#component-path-fields) (accessed 2026-09-24)

**Common validation errors**:

```json
// CORRECT agents fields
"agents": "./custom/security-reviewer.md"
"agents": ["./agents/security-reviewer.md", "./agents/code-formatter.md"]
```

---

## Plugin Directory Structure

### Standard Layout

```
enterprise-plugin/
├── .claude-plugin/           # Metadata directory
│   └── plugin.json          # Optional host manifest for identity/custom paths
├── commands/                 # Default command location
│   ├── status.md
│   └── logs.md
├── agents/                   # Default agent location
│   ├── security-reviewer.md
│   ├── performance-tester.md
│   └── compliance-checker.md
├── skills/                   # Agent Skills
│   ├── code-reviewer/
│   │   └── SKILL.md
│   └── pdf-processor/
│       ├── SKILL.md
│       └── scripts/
├── hooks/                    # Hook configurations
│   ├── hooks.json           # Main hook config
│   └── security-hooks.json  # Additional hooks
├── .mcp.json                # MCP server definitions
├── .lsp.json                # LSP server configurations
├── scripts/                 # Hook and utility scripts
│   ├── security-scan.sh
│   ├── format-code.py
│   └── deploy.js
├── LICENSE                  # License file
└── CHANGELOG.md             # Version history
```

**Critical**: The `.claude-plugin/` directory contains ONLY the `plugin.json` file. All other directories (commands/, agents/, skills/, hooks/) must be at the plugin root, not inside `.claude-plugin/`.

### File Locations Reference

| Component       | Default Location             | Purpose                                    |
| --------------- | ---------------------------- | ------------------------------------------ |
| **Manifest**    | `.claude-plugin/plugin.json` | Optional host metadata/configuration file  |
| **Commands**    | `commands/`                  | Skill Markdown files (legacy; use skills/) |
| **Agents**      | `agents/`                    | Subagent Markdown files                    |
| **Skills**      | `skills/`                    | Skills with `<name>/SKILL.md` structure    |
| **Hooks**       | `hooks/hooks.json`           | Hook configuration                         |
| **MCP servers** | `.mcp.json`                  | MCP server definitions                     |
| **LSP servers** | `.lsp.json`                  | Language server configurations             |

---

## Plugin Components Reference

### Skills

Plugins add skills to Claude Code, creating `/name` shortcuts that you or Claude can invoke.

**Location**: `skills/` in the plugin root. `commands/` is the legacy flat-file form.

**Skill structure**:

```
skills/
├── pdf-processor/
│   ├── SKILL.md
│   ├── reference.md (optional)
│   └── scripts/ (optional)
└── code-reviewer/
    └── SKILL.md
```

**Integration behavior:**

- Skills and commands are automatically discovered when the plugin is installed
- Claude can invoke them automatically based on task context
- Skills can include supporting files alongside SKILL.md
- Plugin skills invoke as `/plugin-name:skill-name`, so they do not collide with standalone
  `/skill-name` entries. The skill frontmatter `name` supplies the suffix; when omitted, Claude uses
  the skill directory basename.
- A plugin containing exactly one skill may place `SKILL.md` at the plugin root. Claude uses its
  frontmatter `name` as the invocation suffix.

[Skill subdirectory warning](../../docs/skill-subdirectory-warning.md) — nested skill directories silently fail to register, with a wrong/right example; read before organizing related skills into grouping subdirectories.

### Agents

Plugins can provide specialized subagents for specific tasks that Claude can invoke automatically when appropriate.

**Location**: `agents/` directory in plugin root

**File format**: Markdown files with YAML frontmatter describing agent capabilities

**Integration points:**

- Agents appear in the `/agents` interface
- Claude can invoke agents automatically based on task context
- Agents can be invoked manually by users
- Plugin agents work alongside built-in Claude agents
- Agent files in subdirectories of `agents/` load recursively; subfolder names become parts of the
  scoped agent name.
- A missing frontmatter `name` falls back to the file path. Frontmatter that does not parse falls
  back to the file path plus a generic plugin description and ignores the invalid fields. Provide
  valid `name` and `description` fields for stable names and accurate automatic routing.

### Plugin Agent Security Restrictions

For security reasons, certain frontmatter fields are silently ignored when present in plugin-shipped agents. These restrictions apply **only** to agents bundled inside a plugin (in `agents/` or declared in `plugin.json`). They do **not** apply to directly-installed agents in `~/.claude/agents/` or `.claude/agents/`.

| Field | Status in plugin agents |
| ----- | ----------------------- |
| `hooks` | Valid agent field; silently ignored for plugin agents |
| `mcpServers` | Valid agent field; ignored for plugin agents |
| `permissionMode` | Valid agent field; ignored for plugin agents |
| `isolation` | Supported — valid value: `"worktree"` (provides isolated worktree environment for agent execution) |

SOURCE: [Plugins Reference — Agents](https://code.claude.com/docs/en/plugins-reference#agents) (accessed 2026-09-24)

**`isolation` field example:**

```yaml
---
name: my-isolated-agent
description: Agent that runs in an isolated worktree
isolation: worktree
---
```

Setting `isolation: "worktree"` causes the agent to execute in a fresh worktree, preventing it from affecting the main working tree directly.

SOURCE: [Plugins Reference](https://code.claude.com/docs/en/plugins-reference.md) line 183 (accessed 2026-04-23)

### Hooks

Plugins can provide event handlers that respond to Claude Code events automatically.

**Location**: `hooks/hooks.json` in plugin root, or inline in plugin.json

**Format**: JSON configuration with event matchers and actions

Claude auto-discovers plugin-wide hooks from `hooks/hooks.json`. These hooks are active whenever
the plugin is enabled. Skill-frontmatter hooks use the same format as settings hooks, support all
hook events in Claude Code, and are added for the rest of the session after the skill is invoked.
Matching handlers run in parallel, so one handler cannot prevent another matching handler from
starting.
Hook commands run with the user's system permissions; review plugin hook code before enabling it.

**Hook configuration**:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/format-code.sh"
          }
        ]
      }
    ]
  }
}
```

**Available events** (representative examples — see the full list of hook events in the complete reference):

- `PreToolUse`: Before Claude uses any tool
- `PostToolUse`: After Claude successfully uses any tool
- `UserPromptSubmit`: When user submits a prompt
- `SessionStart`: At the beginning of sessions

SOURCE: [Hooks guide](https://code.claude.com/docs/en/hooks-guide.md) and
[Hooks reference](https://code.claude.com/docs/en/hooks.md) (accessed 2026-09-24)

For the complete hook event catalog (all events, matchers, input schemas, exit code behavior), see [hook events reference](./references/hook-events.md).

For hook types (`command`, `prompt`, `agent`, `http`) and their configuration options, see [hook events reference](./references/hook-events.md).

### MCP Servers

Plugins can bundle Model Context Protocol (MCP) servers to connect Claude Code with external tools and services.

**Location**: `.mcp.json` in plugin root, or inline in plugin.json

**Format**: Standard MCP server configuration

**MCP server configuration**:

```json
{
  "mcpServers": {
    "plugin-database": {
      "command": "${CLAUDE_PLUGIN_ROOT}/servers/db-server",
      "args": ["--config", "${CLAUDE_PLUGIN_ROOT}/config.json"],
      "env": {
        "DB_PATH": "${CLAUDE_PLUGIN_ROOT}/data"
      }
    },
    "plugin-api-client": {
      "command": "npx",
      "args": ["@company/mcp-server", "--plugin-mode"],
      "cwd": "${CLAUDE_PLUGIN_ROOT}"
    }
  }
}
```

**Integration behavior:**

- Plugin MCP servers start automatically when the plugin is enabled
- Servers appear as standard MCP tools in Claude's toolkit
- Server capabilities integrate seamlessly with Claude's existing tools
- Plugin servers can be configured independently of user MCP servers

### LSP Servers

Plugins can provide Language Server Protocol (LSP) servers to give Claude real-time code intelligence while working on your codebase.

LSP integration provides:

- **Instant diagnostics**: Claude sees errors and warnings immediately after each edit
- **Code navigation**: go to definition, find references, and hover information
- **Language awareness**: type information and documentation for code symbols

**Location**: `.lsp.json` in plugin root, or inline in `plugin.json`

**Format**: JSON configuration mapping language server names to their configurations

**`.lsp.json` file format**:

```json
{
  "go": {
    "command": "gopls",
    "args": ["serve"],
    "extensionToLanguage": {
      ".go": "go"
    }
  }
}
```

**Inline in `plugin.json`**:

```json
{
  "name": "my-plugin",
  "lspServers": {
    "go": {
      "command": "gopls",
      "args": ["serve"],
      "extensionToLanguage": {
        ".go": "go"
      }
    }
  }
}
```

**Required fields:**

| Field                 | Description                                  |
| --------------------- | -------------------------------------------- |
| `command`             | The LSP binary to execute (must be in PATH)  |
| `extensionToLanguage` | Maps file extensions to language identifiers |

**Optional fields:**

| Field                   | Description                                               |
| ----------------------- | --------------------------------------------------------- |
| `args`                  | Command-line arguments for the LSP server                 |
| `transport`             | Communication transport: `stdio` (default) or `socket`    |
| `env`                   | Environment variables to set when starting the server     |
| `initializationOptions` | Options passed to the server during initialization        |
| `settings`              | Settings passed via `workspace/didChangeConfiguration`    |
| `workspaceFolder`       | Workspace folder path for the server                      |
| `startupTimeout`        | Max time to wait for server startup (milliseconds)        |
| `shutdownTimeout`       | Max time to wait for graceful shutdown (milliseconds)     |
| `restartOnCrash`        | Whether to automatically restart the server if it crashes |
| `maxRestarts`           | Maximum number of restart attempts before giving up       |

**Important**: You must install the language server binary separately. LSP plugins configure how Claude Code connects to a language server, but they don't include the server itself.

### Monitors

Plugins can declare background monitor processes that run for the lifetime of a Claude Code session. Each line written to a monitor's stdout is delivered as a notification to Claude. Monitors require Claude Code v2.1.105 or later, run only in interactive CLI sessions, and execute unsandboxed at the same trust level as hooks.

For the complete monitors specification (schema, `when` field, variable substitution, constraints), see [monitors reference](./references/monitors.md).

SOURCE: [Plugins Reference](https://code.claude.com/docs/en/plugins-reference.md) lines 1087-1132 (accessed 2026-04-23)

**Available LSP plugins:**

| Plugin           | Language server            | Install command                                                                            |
| ---------------- | -------------------------- | ------------------------------------------------------------------------------------------ |
| `pyright-lsp`    | Pyright (Python)           | `pip install pyright` or `npm install -g pyright`                                          |
| `typescript-lsp` | TypeScript Language Server | `npm install -g typescript-language-server typescript`                                     |
| `rust-lsp`       | rust-analyzer              | [See rust-analyzer installation](https://rust-analyzer.github.io/manual.html#installation) |

---

## Plugin Caching and File Resolution

Plugin-contained paths must remain within the plugin boundary. Marketplace sources are copied to cache unless the source loads in place; `--plugin-dir`, marketplace command link mode, and local-directory sources load in place, while `--plugin-url` fetches an archive for the session.

### How Plugin Caching Works

When you install a plugin, Claude Code copies the plugin files to a cache directory:

- **For marketplace plugins with relative paths**: The path specified in the `source` field is copied recursively. For example, if your marketplace entry specifies `"source": "./plugins/my-plugin"`, the entire `./plugins` directory is copied.
- **For plugins with `.claude-plugin/plugin.json`**: The implicit root directory (the directory containing `.claude-plugin/plugin.json`) is copied recursively.

### Path Traversal Limitations

Plugins cannot use component paths that escape the plugin root, regardless of whether that source is cached or loaded in place.

### Working with External Dependencies

If your plugin needs to access files outside its directory, you have two options:

**Repository portability policy:** keep dependencies physically within the plugin boundary rather than relying on symlinks. Claude Code handles symlinks explicitly, but checkout behavior differs across platforms.

**Option 2: Restructure your marketplace**

Set the plugin path to a parent directory that contains all required files, then provide the rest of the plugin manifest directly in the marketplace entry:

```json
{
  "name": "my-plugin",
  "source": "./",
  "description": "Plugin that needs root-level access",
  "commands": ["./plugins/my-plugin/commands/"],
  "agents": ["./plugins/my-plugin/agents/security-reviewer.md", "./plugins/my-plugin/agents/compliance-checker.md"],
  "strict": false
}
```

This approach copies the entire marketplace root, giving your plugin access to sibling directories.

SOURCE: [Create plugins](https://code.claude.com/docs/en/plugins) and [Plugin marketplaces](https://code.claude.com/docs/en/plugin-marketplaces) (accessed 2026-09-24)

---

## Plugin Installation Scopes

When you install a plugin, you choose a **scope** that determines where the plugin is available and who else can use it:

| Scope     | Settings file                 | Use case                                                 |
| --------- | ----------------------------- | -------------------------------------------------------- |
| `user`    | `~/.claude/settings.json`     | Personal plugins available across all projects (default) |
| `project` | `.claude/settings.json`       | Team plugins shared via version control                  |
| `local`   | `.claude/settings.local.json` | Project-specific plugins, gitignored                     |
| `managed` | `managed-settings.json`       | Managed plugins (read-only, update only)                 |

---

## Environment Variables

**`${CLAUDE_PLUGIN_ROOT}`**: Contains the absolute path to your plugin directory. Use this in hooks, MCP servers, and scripts to ensure correct paths regardless of installation location.

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/process.sh"
          }
        ]
      }
    ]
  }
}
```

**`${CLAUDE_PROJECT_DIR}`**: Project root directory (where Claude Code was started).

**`${CLAUDE_PLUGIN_DATA}`**: Persistent plugin data directory that survives plugin updates. Path: `~/.claude/plugins/data/{id}/` where `{id}` is the plugin name with non-alphanumeric characters replaced by hyphens. Use for installed dependencies (node_modules, virtualenvs), generated code, and caches. Recommended pattern: store a manifest hash in this directory, check it on startup, and reinstall dependencies only when the manifest changes.

```json
{
  "mcpServers": {
    "my-server": {
      "command": "node",
      "args": ["${CLAUDE_PLUGIN_DATA}/node_modules/.bin/my-server"]
    }
  }
}
```

SOURCE: [Plugins Reference](https://code.claude.com/docs/en/plugins-reference.md) lines 1275-1318 (accessed 2026-04-23)

---

## Plugin Marketplaces

### Marketplace Schema

Create `.claude-plugin/marketplace.json` in your repository root:

```json
{
  "name": "company-tools",
  "owner": {
    "name": "DevTools Team",
    "email": "devtools@example.com"
  },
  "plugins": [
    {
      "name": "code-formatter",
      "source": "./plugins/formatter",
      "description": "Automatic code formatting on save",
      "version": "2.1.0",
      "author": {
        "name": "DevTools Team"
      }
    },
    {
      "name": "deployment-tools",
      "source": {
        "source": "github",
        "repo": "company/deploy-plugin"
      },
      "description": "Deployment automation tools"
    }
  ]
}
```

### Required Marketplace Fields

| Field     | Type   | Description                         | Example        |
| --------- | ------ | ----------------------------------- | -------------- |
| `name`    | string | Marketplace identifier (kebab-case) | `"acme-tools"` |
| `owner`   | object | Marketplace maintainer information  |                |
| `plugins` | array  | List of available plugins           |                |

**Reserved names**: `claude-code-marketplace`, `claude-code-plugins`, `claude-plugins-official`, `anthropic-marketplace`, `anthropic-plugins`, `agent-skills`, `life-sciences` are reserved for official Anthropic use.

### Plugin Sources

#### Relative paths

For plugins in the same repository:

```json
{
  "name": "my-plugin",
  "source": "./plugins/my-plugin"
}
```

**Note**: Relative paths only work when users add your marketplace via Git (GitHub, GitLab, or git URL). If users add your marketplace via a direct URL to the `marketplace.json` file, relative paths will not resolve correctly.

#### GitHub repositories

```json
{
  "name": "github-plugin",
  "source": {
    "source": "github",
    "repo": "owner/plugin-repo"
  }
}
```

You can pin to a specific branch, tag, or commit:

```json
{
  "name": "github-plugin",
  "source": {
    "source": "github",
    "repo": "owner/plugin-repo",
    "ref": "v2.0.0",
    "sha": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"
  }
}
```

| Field  | Type   | Description                                                           |
| ------ | ------ | --------------------------------------------------------------------- |
| `repo` | string | Required. GitHub repository in `owner/repo` format                    |
| `ref`  | string | Optional. Git branch or tag (defaults to repository default branch)   |
| `sha`  | string | Optional. Full 40-character git commit SHA to pin to an exact version |

#### Git repositories

```json
{
  "name": "git-plugin",
  "source": {
    "source": "url",
    "url": "https://gitlab.com/team/plugin.git"
  }
}
```

You can pin to a specific branch, tag, or commit:

```json
{
  "name": "git-plugin",
  "source": {
    "source": "url",
    "url": "https://gitlab.com/team/plugin.git",
    "ref": "main",
    "sha": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"
  }
}
```

| Field | Type   | Description                                                           |
| ----- | ------ | --------------------------------------------------------------------- |
| `url` | string | Required. Full git repository URL (`https://` or `git@`); `.git` suffix is optional |
| `ref` | string | Optional. Git branch or tag (defaults to repository default branch)   |
| `sha` | string | Optional. Full 40-character git commit SHA to pin to an exact version |

#### Zip archives

- Archive URLs must use HTTPS. HTTP, loopback, link-local, and cloud-metadata hosts are rejected.
- Archives larger than 256 MiB are refused.
- `.claude-plugin/` must be at the archive root or beneath one top-level folder.
- Optional `sha256` is verified when supplied.
- Marketplace-relative sources must remain below the marketplace root, use forward slashes, and cannot contain `../`.

SOURCE: [Plugin marketplaces](https://code.claude.com/docs/en/plugin-marketplaces) (accessed 2026-09-24)

---

## CLI Commands Reference

Claude Code provides CLI commands for non-interactive plugin management, useful for scripting and automation.

### plugin install

Install a plugin from available marketplaces.

```bash
claude plugin install <plugin> [options]
```

**Arguments:**

- `<plugin>`: Plugin name or `plugin-name@marketplace-name` for a specific marketplace

**Options:**

| Option                | Description                                       | Default |
| --------------------- | ------------------------------------------------- | ------- |
| `-s, --scope <scope>` | Installation scope: `user`, `project`, or `local` | `user`  |
| `-h, --help`          | Display help for command                          |         |

**Examples:**

```bash
# Install to user scope (default)
claude plugin install formatter@my-marketplace

# Install to project scope (shared with team)
claude plugin install formatter@my-marketplace --scope project

# Install to local scope (gitignored)
claude plugin install formatter@my-marketplace --scope local
```

### plugin uninstall

Remove an installed plugin.

```bash
claude plugin uninstall <plugin> [options]
```

**Arguments:**

- `<plugin>`: Plugin name or `plugin-name@marketplace-name`

**Options:**

| Option                | Description                                         | Default |
| --------------------- | --------------------------------------------------- | ------- |
| `-s, --scope <scope>` | Uninstall from scope: `user`, `project`, or `local` | `user`  |
| `-h, --help`          | Display help for command                            |         |

**Aliases:** `remove`, `rm`

### plugin enable

Enable a disabled plugin.

```bash
claude plugin enable <plugin> [options]
```

**Arguments:**

- `<plugin>`: Plugin name or `plugin-name@marketplace-name`

**Options:**

| Option                | Description                                    | Default |
| --------------------- | ---------------------------------------------- | ------- |
| `-s, --scope <scope>` | Scope to enable: `user`, `project`, or `local` | `user`  |
| `-h, --help`          | Display help for command                       |         |

### plugin disable

Disable a plugin without uninstalling it.

```bash
claude plugin disable <plugin> [options]
```

**Arguments:**

- `<plugin>`: Plugin name or `plugin-name@marketplace-name`

**Options:**

| Option                | Description                                     | Default |
| --------------------- | ----------------------------------------------- | ------- |
| `-s, --scope <scope>` | Scope to disable: `user`, `project`, or `local` | `user`  |
| `-h, --help`          | Display help for command                        |         |

### plugin list

List installed plugins.

```bash
claude plugin list [options]
```

**Options:**

| Option          | Description                                              |
| --------------- | -------------------------------------------------------- |
| `--json`        | Output as JSON                                           |
| `--available`   | Include available (not yet installed) plugins (requires `--json`) |
| `-h, --help`    | Display help for command                                 |

**Examples:**

```bash
# List installed plugins
claude plugin list

# JSON output (for scripting)
claude plugin list --json

# Include available plugins in JSON output
claude plugin list --json --available
```

SOURCE: [Plugins Reference](https://code.claude.com/docs/en/plugins-reference.md) lines 974-980 (accessed 2026-04-23)

### plugin update

Update a plugin to the latest version.

```bash
claude plugin update <plugin> [options]
```

**Arguments:**

- `<plugin>`: Plugin name or `plugin-name@marketplace-name`

**Options:**

| Option                | Description                                               | Default |
| --------------------- | --------------------------------------------------------- | ------- |
| `-s, --scope <scope>` | Scope to update: `user`, `project`, `local`, or `managed` | `user`  |
| `-h, --help`          | Display help for command                                  |         |

---

## Debugging and Development Tools

### Debugging Commands

Use `claude --debug` to see plugin loading details:

```bash
claude --debug
```

This shows:

- Which plugins are being loaded
- Any errors in plugin manifests
- Command, agent, and hook registration
- MCP server initialization

### Common Issues

| Issue                               | Cause                                  | Solution                                                                 |
| ----------------------------------- | -------------------------------------- | ------------------------------------------------------------------------ |
| Plugin not loading                  | Invalid `plugin.json`                  | Validate JSON syntax with `claude plugin validate` or `/plugin validate` |
| Default agents disappear           | Declared replacement `agents` paths without default files | Include retained default agent files or remove `agents` |
| Commands not appearing              | Wrong directory structure              | Ensure `commands/` at root, not in `.claude-plugin/`                     |
| Hooks not firing                    | Script not executable                  | Run `chmod +x script.sh`                                                 |
| MCP server fails                    | Missing `${CLAUDE_PLUGIN_ROOT}`        | Use variable for all plugin paths                                        |
| Path errors                         | Absolute paths used                    | All paths must be relative and start with `./`                           |
| LSP `Executable not found in $PATH` | Language server not installed          | Install the binary (e.g., `npm install -g typescript-language-server`)   |

### Validation Commands

```bash
# CLI (from terminal)
claude plugin validate .
claude plugin validate ./path/to/plugin

# In Claude Code session
/plugin validate .
/plugin validate ./path/to/plugin
```

### Testing Without Installation

```bash
# Load plugin for current session only
claude --plugin-dir ./my-plugin

# Load multiple plugins
claude --plugin-dir ./plugin-one --plugin-dir ./plugin-two
```

**Override precedence**: When a `--plugin-dir` plugin has the same name as an installed marketplace plugin, the local copy takes precedence for that session. Exception: marketplace plugins force-enabled by managed settings cannot be overridden by `--plugin-dir`.

SOURCE: [Create Plugins](https://code.claude.com/docs/en/plugins.md) line 807 (accessed 2026-04-23)

---

## Enterprise Features

### Required Marketplaces for Teams

Configure your repository so team members are automatically prompted to install your marketplace when they trust the project folder. Add your marketplace to `.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "company-tools": {
      "source": {
        "source": "github",
        "repo": "your-org/claude-plugins"
      }
    }
  }
}
```

You can also specify which plugins should be enabled by default:

```json
{
  "enabledPlugins": {
    "code-formatter@company-tools": true,
    "deployment-tools@company-tools": true
  }
}
```

### Managed Marketplace Restrictions

For organizations requiring strict control over plugin sources, administrators can restrict which plugin marketplaces users are allowed to add using the `strictKnownMarketplaces` setting in managed settings.

When `strictKnownMarketplaces` is configured in managed settings, the restriction behavior depends on the value:

| Value               | Behavior                                                         |
| ------------------- | ---------------------------------------------------------------- |
| Undefined (default) | No restrictions. Users can add any marketplace                   |
| Empty array `[]`    | Complete lockdown. Users cannot add any new marketplaces         |
| List of sources     | Users can only add marketplaces that match the allowlist exactly |

**Common configurations:**

Disable all marketplace additions:

```json
{
  "strictKnownMarketplaces": []
}
```

Allow specific marketplaces only:

```json
{
  "strictKnownMarketplaces": [
    {
      "source": "github",
      "repo": "acme-corp/approved-plugins"
    },
    {
      "source": "github",
      "repo": "acme-corp/security-tools",
      "ref": "v2.0"
    },
    {
      "source": "url",
      "url": "https://plugins.example.com/marketplace.json"
    }
  ]
}
```

Allow all marketplaces from an internal git server using regex pattern matching:

```json
{
  "strictKnownMarketplaces": [
    {
      "source": "hostPattern",
      "hostPattern": "^github\\.example\\.com$"
    }
  ]
}
```

**How restrictions work:**

Restrictions are validated early in the plugin installation process, before any network requests or filesystem operations occur. This prevents unauthorized marketplace access attempts.

The allowlist uses exact matching for most source types. For a marketplace to be allowed, all specified fields must match exactly:

- For GitHub sources: `repo` is required, and `ref` or `path` must also match if specified in the allowlist
- For URL sources: the full URL must match exactly
- For `hostPattern` sources: the marketplace host is matched against the regex pattern

Because `strictKnownMarketplaces` is set in managed settings, individual users and project configurations cannot override these restrictions.

---

## Private Repository Authentication

| Provider  | Environment variables        | Notes                                     |
| --------- | ---------------------------- | ----------------------------------------- |
| GitHub    | `GITHUB_TOKEN` or `GH_TOKEN` | Personal access token or GitHub App token |
| GitLab    | `GITLAB_TOKEN` or `GL_TOKEN` | Personal access token or project token    |
| Bitbucket | `BITBUCKET_TOKEN`            | App password or repository access token   |

Set the token in your shell configuration (e.g., `.bashrc`, `.zshrc`) or pass it when running Claude Code:

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
```

**For manual installation and updates:** Claude Code uses your existing git credential helpers. If `git clone` works for a private repository in your terminal, it works in Claude Code too.

**For background auto-updates:** Set the appropriate authentication token in your environment. GitHub Actions automatically provides `GITHUB_TOKEN` for repositories in the same organization.

---

## Distribution and Versioning

### Version Management

Follow semantic versioning for plugin releases:

```json
{
  "name": "my-plugin",
  "version": "2.1.0"
}
```

**Version format**: `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes (incompatible API changes)
- **MINOR**: New features (backward-compatible additions)
- **PATCH**: Bug fixes (backward-compatible fixes)

**Best practices:**

- Start at `1.0.0` for your first stable release
- Update the version in `plugin.json` before distributing changes
- Document changes in a `CHANGELOG.md` file
- Use pre-release versions like `2.0.0-beta.1` for testing

---

## Constraints and Limitations

- Marketplace plugins are cached unless their source mode loads in place; `--plugin-dir` loads directly
- Cannot reference files outside plugin directory (`../` fails)
- LSP servers require separate binary installation
- All paths must be relative, start with `./`
- Path traversal (`..`) not allowed
- Scripts must be executable (`chmod +x`)
- Reserved marketplace names: `claude-code-marketplace`, `claude-code-plugins`, `claude-plugins-official`, `anthropic-marketplace`, `anthropic-plugins`, `agent-skills`, `life-sciences`

---

## Plugin Cache Lifecycle

When a copied plugin version is updated, the old version is not deleted immediately. It is marked
orphaned and removed by a background sweep roughly 14 days later. This grace period allows
concurrent sessions using the old version to finish without errors. The sweep runs only while at
least one plugin is installed.

Claude's `Glob` and `Grep` tools skip orphaned version directories during file searches, so file results do not include outdated plugin code.

SOURCE: [Plugins Reference — Plugin caching and file resolution](https://code.claude.com/docs/en/plugins-reference.md#plugin-caching-and-file-resolution) (accessed 2026-09-24)

---

## Sources

- [Plugins Reference](https://code.claude.com/docs/en/plugins-reference.md) (accessed 2026-09-24)
- [Create Plugins](https://code.claude.com/docs/en/plugins.md) (accessed 2026-09-24)
- [Plugin Marketplaces](https://code.claude.com/docs/en/plugin-marketplaces) (accessed 2026-09-24)
- [Skills Reference](https://code.claude.com/docs/en/skills.md) (accessed 2026-09-24)
- [Hooks Guide](https://code.claude.com/docs/en/hooks-guide.md) (accessed 2026-09-24)
- [Hooks Reference](https://code.claude.com/docs/en/hooks.md) (accessed 2026-09-24)
- [MCP Reference](https://code.claude.com/docs/en/mcp.md)
