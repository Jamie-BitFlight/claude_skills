<p align="center">
  <img src="./assets/hero.png" alt="XDG Base Directory" width="800" />
</p>

# XDG Base Directory

Teaches Claude the XDG Base Directory Specification — the Linux standard for where applications store configuration, data, cache, state, and runtime files. Claude applies these conventions automatically when writing code that touches the filesystem.

## What It Does

Without this plugin, Claude writes code that scatters files across the home directory (`~/.myapp`, `~/.myapp-config`, `~/.myapp.lock`). With it, Claude follows the specification precisely: correct directories, correct environment variable handling, correct validation rules (absolute paths only), and correct separation of config vs data vs cache vs state.

## What Changes

With this plugin installed, Claude will:

- Use `~/.config/appname/` for configuration (not `~/.appname`)
- Use `~/.local/share/appname/` for persistent data
- Use `~/.cache/appname/` for regenerable cache files
- Use `~/.local/state/appname/` for logs, history, and undo buffers
- Use `/run/user/$UID/appname/` for runtime files (sockets, pipes, locks)
- Respect all five `$XDG_*` environment variables when set
- Validate that XDG paths are absolute before using them (per spec rule)
- Handle cross-platform storage correctly when using the `platformdirs` library

## XDG Environment Variables

| Variable | Default | Use For |
|----------|---------|---------|
| `$XDG_CONFIG_HOME` | `$HOME/.config` | Settings, preferences |
| `$XDG_DATA_HOME` | `$HOME/.local/share` | Databases, generated content |
| `$XDG_CACHE_HOME` | `$HOME/.cache` | Temporary, regenerable data |
| `$XDG_STATE_HOME` | `$HOME/.local/state` | Logs, history, recent files |
| `$XDG_RUNTIME_DIR` | `/run/user/$UID` | Sockets, pipes, lock files |

## Installation

```bash
/plugin marketplace add Jamie-BitFlight/claude_skills
/plugin install xdg-base-directory@jamie-bitflight-skills
```

## Usage

Install and ask Claude to write code that stores files. The skill activates automatically:

```text
"Create a CLI tool that saves user configuration"
"Build a Python app that caches downloaded data"
"Write a script that logs command history"
"Make this app respect XDG environment variables"
"Where should this app store its database file?"
```

### Example

Without this plugin:

```python
config_file = Path.home() / ".myapp" / "config.toml"  # pollutes home dir
```

With this plugin:

```python
def get_config_dir() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg and Path(xdg).is_absolute() else Path.home() / ".config"
    return base / "myapp"


config_file = get_config_dir() / "config.toml"
```

Clean home directory. Respects user customization. Compliant with the specification.

## When to Use

- Writing Python CLI tools or applications that store files
- Reviewing code that hardcodes `~/.appname` paths
- Building Linux-native applications that need proper file organization
- Writing cross-platform code with `platformdirs` that falls back correctly on Linux
- Testing XDG compliance by overriding `$XDG_*` variables in test environments

## Requirements

- Claude Code v2.0+
- Primarily for Linux/Unix development; also covers cross-platform apps (macOS, Windows) via `platformdirs`
