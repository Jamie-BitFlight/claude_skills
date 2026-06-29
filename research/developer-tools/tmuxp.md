---
title: "tmuxp"
research_date: "2026-03-01"
source_url: "https://tmuxp.git-pull.com/"
github_url: "https://github.com/tmux-python/tmuxp"
version_at_research: "1.64.0"
license: "MIT"
last_verified: "2026-03-01"
version_at_verification: "v1.64.0"
next_review: "2026-06-01"
---

## Overview

tmuxp is a Python-based session manager for tmux that lets users declaratively define tmux
sessions as YAML or JSON configuration files and restore them programmatically. Built on top of
[libtmux](https://github.com/tmux-python/libtmux), it exposes a clean Python API
(`WorkspaceBuilder`, `ConfigReader`, `TmuxpPlugin`) for creating, loading, freezing, and
importing tmux sessions without manual shell scripting. A single config file captures an entire
multi-window, multi-pane development environment and can be replayed identically via one CLI
command. The project is maintained by the tmux-python organization and has been in active
development since 2013, with 265 PyPI releases as of March 2026.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Recreating complex multi-pane tmux layouts (editors, test watchers, servers, logs) after a reboot or disconnection requires manual repetition | A YAML config with `session_name`, `windows`, `panes`, `layout`, and `shell_command` keys rebuilds the entire workspace via `tmuxp load` |
| Sessions created by scripts using raw tmux commands are not reproducible across machines | Declarative configs are version-controllable and portable; configs live in `~/.config/tmuxp/` or per-project `.tmuxp.yaml` files |
| Capturing the current state of a running tmux session for later reuse requires manual documentation | `tmuxp freeze <session>` snapshots a live session into a YAML workspace config automatically |
| Programmatically orchestrating multiple tmux sessions requires writing raw libtmux calls | `WorkspaceBuilder(session_config=config, server=server).build()` creates fully configured sessions in Python with one call |
| Configs written for tmuxinator or teamocil are not compatible with tmuxp | `tmuxp import tmuxinator` and `tmuxp import teamocil` convert foreign config formats |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 4,434 | 2026-03-01 |
| GitHub Forks | 236 | 2026-03-01 |
| Contributors | 68 | 2026-03-01 |
| Open Issues | 113 | 2026-03-01 |
| Latest Release | v1.64.0 | 2026-03-01 |
| Release Date | 2026-01-24 | 2026-03-01 |
| Total PyPI Releases | 265 | 2026-03-01 |
| Repository Created | 2013-08-27 | 2026-03-01 |
| Primary Language | Python | 2026-03-01 |
| Python Requirement | >=3.10,<4.0 | 2026-03-01 |

SOURCE: [GitHub API — tmux-python/tmuxp](https://api.github.com/repos/tmux-python/tmuxp) (accessed 2026-03-01)
SOURCE: [PyPI — tmuxp JSON API](https://pypi.org/pypi/tmuxp/json) (accessed 2026-03-01)

---

## Key Features

### Declarative Session Configuration (YAML and JSON)

Configs are plain dicts with well-defined keys. The minimal structure:

```yaml
session_name: my-project
windows:
  - window_name: editor
    layout: main-vertical
    panes:
      - vim .
      - pytest -x
  - window_name: logs
    panes:
      - tail -f /var/log/app.log
```

Full config schema supports:

- `session_name` — tmux session name (required)
- `start_directory` — default working directory for all windows/panes
- `before_script` — shell script or command executed before the session is built
- `shell_command_before` — list of commands run before each pane's `shell_command`
- `suppress_history` — suppress pane commands from shell history (session, window, or pane level)
- `environment` — environment variables injected at session, window, or pane scope
- `options` — tmux window options (e.g., `main-pane-height: 67%`, `synchronize-panes: on`)
- `focus` — mark the window or pane to receive initial focus on load
- `plugins` — list of Python class paths for tmuxp plugin hooks
- Layout values: `even-horizontal`, `even-vertical`, `main-horizontal`, `main-vertical`, `tiled`

### Session Loading Modes

```text
tmuxp load ./mysession.yaml          # Load a config file
tmuxp load -s name ./mysession.yaml  # Override session name on load
tmuxp load -d mysession              # Load detached (no auto-attach)
tmuxp load -a myproject              # Append windows to current session
tmuxp load mysession another         # Load multiple sessions; attach to last
tmuxp load -y dev staging            # Answer yes to all prompts; load multiple
tmuxp load -L other-socket myproject # Target a specific tmux socket
```

Configs stored in `$TMUXP_CONFIGDIR`, `$XDG_CONFIG_HOME/tmuxp/` (`~/.config/tmuxp/`), or
`~/.tmuxp/` are loadable by name without a path. Projects with `.tmuxp.yaml` or `.tmuxp.json`
in their root directory load via `tmuxp load path/to/project/`.

### Session Freezing (Snapshot to Config)

```text
tmuxp freeze                 # Freeze current session
tmuxp freeze my-session      # Freeze a named session
tmuxp freeze -o ./out.yaml   # Write to file instead of stdout
```

The `freeze` command walks all windows and panes of the target session using libtmux, capturing
`window_name`, `layout`, `start_directory` (shared across panes), and `pane_current_command`.
It produces a valid tmuxp YAML that can be reloaded. Interpreter-only processes (python, ruby,
node) and shell processes are filtered from `shell_command` since they are not safely replayable.

### Python Programmatic API

The `WorkspaceBuilder` class is the core API for programmatic session creation:

```python
import yaml
import libtmux
from tmuxp._internal import config_reader
from tmuxp.workspace import loader
from tmuxp.workspace.builder import WorkspaceBuilder

# Load config from file
session_config = config_reader.ConfigReader._from_file(
    pathlib.Path("./mysession.yaml")
)

# Or from a dict directly
session_config = {
    "session_name": "orchestrator",
    "windows": [
        {"window_name": "agent-1", "panes": ["bash"]},
        {"window_name": "agent-2", "panes": ["bash"]},
    ],
}

# Build the session
server = libtmux.Server()
builder = WorkspaceBuilder(session_config=session_config, server=server)
builder.build()

# Access the created session object
session = builder.session
print(session.name)         # "orchestrator"
print(session.windows)      # list of libtmux.Window objects
```

`WorkspaceBuilder.build()` accepts optional parameters:

- `session` — build into an existing `libtmux.Session` instead of creating a new one
- `append` — append windows to the current active session without creating a new session

The builder checks if a session with the configured `session_name` already exists and attaches
to it rather than creating a duplicate.

### Plugin System

Plugins hook into the session lifecycle via a base class with four extension points:

```python
from tmuxp.plugin import TmuxpPlugin

class MyPlugin(TmuxpPlugin):
    def before_workspace_builder(self, session):
        """Called after session creation, before any windows/panes are built."""

    def on_window_create(self, window):
        """Called before panes are created in a window."""

    def after_window_finished(self, window):
        """Called after all panes and options are set on a window."""

    def before_script(self, session):
        """Called after the full workspace is built; augments before_script."""

    def reattach(self, session):
        """Called before re-attaching to an existing session."""
```

Plugins are declared in YAML:

```yaml
session_name: my-session
plugins:
  - "mypackage.tmuxp_plugins.MyPlugin"
windows:
  - window_name: main
    panes:
      - bash
```

The plugin constructor accepts version constraints (`tmux_min_version`, `libtmux_min_version`,
`tmuxp_min_version`, `tmux_version_incompatible`, etc.) to enforce compatibility at load time.

### Config Import (tmuxinator and teamocil)

```text
tmuxp import tmuxinator ./.tmuxinator.yml
tmuxp import teamocil ./teamocil.yml
```

Converts foreign session manager configs to tmuxp YAML format. Output is written to stdout or a
file.

### Interactive Shell with libtmux Objects

```text
tmuxp shell               # Drop into PDB REPL pre-loaded with server, session, window, pane
tmuxp shell -c 'expr'     # Evaluate expression and print result; no interactive prompt
```

The shell binds `server`, `session`, `window`, and `pane` as locals in a Python REPL.
Supports `PYTHONBREAKPOINT` (PEP 553). Useful for live inspection and programmatic manipulation.

```bash
tmuxp shell -c 'print(session.name)'
tmuxp shell -c 'window.split()'
tmuxp shell -c 'pane.send_keys("echo hello", enter=True)'
```

### Additional CLI Commands

```text
tmuxp ls                  # List tmuxp config files in known config dirs
tmuxp search <keyword>    # Search config file names
tmuxp edit <config>       # Open a config in $EDITOR
tmuxp convert <file>      # Convert between JSON and YAML formats
tmuxp debug-info          # Print environment info for bug reports
```

---

## Technical Architecture

tmuxp is a thin orchestration layer on top of libtmux (the Python binding to the tmux control
protocol). The dependency chain is:

```text
tmuxp CLI (argparse subcommands)
    |
    v
tmuxp.workspace.builder.WorkspaceBuilder
    |
    +-- tmuxp._internal.config_reader.ConfigReader     (YAML/JSON parsing)
    +-- tmuxp.workspace.loader.expand / trickle        (config normalization)
    +-- tmuxp.workspace.validation.validate_schema     (schema checking)
    +-- tmuxp.workspace.finders.find_workspace_file    (config discovery)
    |
    v
libtmux.Server / .Session / .Window / .Pane
    |
    v
tmux process (via control mode: tmux -C)
```

Key modules:

- `tmuxp._internal.config_reader.ConfigReader` — parses YAML (PyYAML SafeLoader) and JSON; provides `_from_file(path)` and `_load(fmt, content)` classmethods; supports `dump("yaml")` and `dump("json")` for serialization
- `tmuxp.workspace.loader` — `expand()` normalizes shorthand syntax (string panes to dict form, single-element lists to scalars); `trickle()` propagates `start_directory` and `shell_command_before` from session to windows to panes
- `tmuxp.workspace.builder.WorkspaceBuilder` — iterates windows and panes from `session_config`, calls `server.new_session()`, then `session.new_window()` and `window.split()` or `window.panes[0]` with `send_keys()` for each configured pane command; fires plugin hooks at each stage
- `tmuxp.workspace.freezer.freeze(session)` — reverse operation; walks live libtmux objects to produce a workspace dict
- `tmuxp.plugin.TmuxpPlugin` — base class with version compatibility validation built into `__init__`; subclasses override lifecycle hooks
- `tmuxp.shell` — launches a Python REPL (PDB or standard) with libtmux objects pre-bound

Runtime environment variables:

- `TMUXP_CONFIGDIR` — override config search directory
- `TMUXP_DEFAULT_COLUMNS` / `TMUXP_DEFAULT_ROWS` — override terminal size detection for new sessions
- `TMUXP_DETECT_TERMINAL_SIZE` — set to `"0"` to disable `shutil.get_terminal_size()` calls (useful in headless/CI contexts)
- `PYTHONBREAKPOINT` — controls debugger in `tmuxp shell`

Dependencies (runtime only):

- `libtmux~=0.53.0` — tmux Python binding; provides `Server`, `Session`, `Window`, `Pane`
- `PyYAML>=6.0` — config file parsing
- `colorama>=0.3.9` — cross-platform terminal color output

tmux version requirements: minimum 3.2 (set in `tmuxp.plugin.TMUX_MIN_VERSION`).

---

## Installation & Usage

```bash
# pip
pip install --user tmuxp

# uv
uv add tmuxp

# Run without installing (ephemeral)
uvx tmuxp

# Homebrew (macOS / Linux)
brew install tmuxp

# Debian / Ubuntu
sudo apt install tmuxp
```

```yaml
# Example: .tmuxp.yaml for a multi-agent workspace
session_name: claude-agents
start_directory: ~/projects/myapp
before_script: ./scripts/start-services.sh
environment:
  ANTHROPIC_API_KEY: "${ANTHROPIC_API_KEY}"
windows:
  - window_name: orchestrator
    layout: main-horizontal
    options:
      main-pane-height: 70%
    panes:
      - focus: true
        shell_command: python orchestrator.py
      - shell_command: tail -f logs/orchestrator.log
  - window_name: agent-workers
    layout: tiled
    panes:
      - python worker.py --id 1
      - python worker.py --id 2
      - python worker.py --id 3
      - python worker.py --id 4
  - window_name: monitoring
    panes:
      - htop
      - watch -n2 ./scripts/check-agents.sh
```

```bash
# Load the session
tmuxp load .

# Load detached (no terminal attachment)
tmuxp load -d .

# Freeze current session to a new config
tmuxp freeze claude-agents > ~/.config/tmuxp/claude-agents.yaml

# Programmatic load from Python
python -c "
import pathlib
import libtmux
from tmuxp._internal import config_reader
from tmuxp.workspace.builder import WorkspaceBuilder

cfg = config_reader.ConfigReader._from_file(pathlib.Path('.tmuxp.yaml'))
server = libtmux.Server()
builder = WorkspaceBuilder(session_config=cfg, server=server)
builder.build()
print(builder.session.id)
"
```

```bash
# Inspect a live session's objects via the shell
tmuxp shell -c 'print([w.name for w in session.windows])'
tmuxp shell -c 'session.windows[1].panes[0].send_keys("git status", enter=True)'
```

---

## Relevance to Claude Code Development

### Applications

tmuxp is a direct enabler for structured multi-agent tmux session management in Claude Code
orchestration workflows. The existing research entry
[using-tmux-with-claude-code.md](./using-tmux-with-claude-code.md) documents the pattern of
running Claude Code agents in named tmux windows and capturing output via `tmuxp capture-pane`.
tmuxp makes this pattern declarative and reproducible.

Concrete applications:

- Define a multi-agent workspace as a `.tmuxp.yaml` checked into the repository; any developer
  or CI environment can restore the full agent topology with `tmuxp load .`
- The `WorkspaceBuilder` Python API can be called directly from an orchestration script to
  programmatically spawn agent sessions, assign named windows per agent role, and pre-populate
  each pane with the correct startup command — no shell string interpolation required
- `tmuxp freeze` captures the exact pane layout and running commands of a complex agent session
  for post-mortem analysis or sharing
- `TMUXP_DETECT_TERMINAL_SIZE=0` makes `WorkspaceBuilder.build()` safe to call from headless
  CI or subagent contexts where no terminal is attached
- `tmuxp shell -c 'pane.send_keys(...)'` provides a one-liner mechanism to inject commands into
  any named tmux pane from a script, without tmux key-binding complexity

### Patterns Worth Adopting

- The `WorkspaceBuilder` lifecycle with plugin hooks (`before_workspace_builder`,
  `on_window_create`, `after_window_finished`) is a clean extension pattern for any tool that
  needs ordered initialization steps with shared context — equivalent to Claude Code's hook
  system but for terminal infrastructure
- The `trickle()` function in `tmuxp.workspace.loader` that propagates `start_directory` and
  `shell_command_before` from session to window to pane is a useful cascade pattern for
  hierarchical config objects — avoids repetition at lower levels
- Config search path resolution (`TMUXP_CONFIGDIR`, `XDG_CONFIG_HOME`, `~/.tmuxp/`) with
  name-based loading (just the filename stem, without path or extension) is a clean CLI UX
  pattern for tools that manage collections of named configs
- The `freeze → edit → load` workflow round-trips between live state and declarative config,
  enabling a "capture once, replay many times" workflow that would apply to agent session
  topology management

### Integration Opportunities

- A tmuxp plugin class (`TmuxpPlugin` subclass) could register Claude Code agents into each
  window after it is created (`after_window_finished` hook), passing session context via
  environment variables or a shared file
- The `before_workspace_builder` hook fires after session creation but before any windows are
  built — a natural point to configure the tmux server's global options or start shared
  infrastructure processes
- `tmuxp freeze` output could be piped into `tmuxp load` to snapshot and restore agent
  topologies across CI runs; combine with `session_name` override (`-s`) to avoid collisions
- The `tmuxp shell` Python REPL provides an interactive escape hatch for debugging agent pane
  state: `tmuxp shell -c 'session.windows.get(window_name="agent-1").panes[0].capture_pane()'`
- Since tmuxp uses libtmux under the hood, any pane objects returned by `WorkspaceBuilder` are
  full libtmux `Pane` instances with `send_keys()`, `capture_pane()`, and `resize()` methods —
  enabling rich programmatic control after the workspace is built

---

## References

- [GitHub — tmux-python/tmuxp](https://github.com/tmux-python/tmuxp) (accessed 2026-03-01)
- [GitHub — README.md](https://github.com/tmux-python/tmuxp/blob/master/README.md) (accessed 2026-03-01)
- [GitHub — Release v1.64.0 Notes](https://github.com/tmux-python/tmuxp/releases/tag/v1.64.0) (accessed 2026-03-01)
- [GitHub — workspace/builder.py — WorkspaceBuilder API](https://github.com/tmux-python/tmuxp/blob/master/src/tmuxp/workspace/builder.py) (accessed 2026-03-01)
- [GitHub — workspace/freezer.py — freeze() API](https://github.com/tmux-python/tmuxp/blob/master/src/tmuxp/workspace/freezer.py) (accessed 2026-03-01)
- [GitHub — workspace/loader.py — expand/trickle normalization](https://github.com/tmux-python/tmuxp/blob/master/src/tmuxp/workspace/loader.py) (accessed 2026-03-01)
- [GitHub — plugin.py — TmuxpPlugin base class](https://github.com/tmux-python/tmuxp/blob/master/src/tmuxp/plugin.py) (accessed 2026-03-01)
- [GitHub — _internal/config_reader.py — ConfigReader API](https://github.com/tmux-python/tmuxp/blob/master/src/tmuxp/_internal/config_reader.py) (accessed 2026-03-01)
- [GitHub — examples/ — config examples](https://github.com/tmux-python/tmuxp/tree/master/examples) (accessed 2026-03-01)
- [GitHub — pyproject.toml — dependencies and entry points](https://github.com/tmux-python/tmuxp/blob/master/pyproject.toml) (accessed 2026-03-01)
- [PyPI — tmuxp package page](https://pypi.org/project/tmuxp/) (accessed 2026-03-01)
- [GitHub API — Repository Metadata](https://api.github.com/repos/tmux-python/tmuxp) (accessed 2026-03-01)

---
