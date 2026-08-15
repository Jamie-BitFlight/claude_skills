---
name: libtmux - Typed Python API for tmux
description: libtmux is a typed, object-oriented Python library that wraps the tmux terminal multiplexer. It exposes Server, Session, Window, and Pane as live Python objects with full CRUD control — creating sessions, splitting panes, sending keystrokes, and capturing output — without shelling out to parse raw tmux CLI output. Powers tmuxp in production.
license: MIT
metadata:
  topic: libtmux
  category: developer-tools
  source_url: https://github.com/tmux-python/libtmux
  github: tmux-python/libtmux
  version: "0.53.1"
  verified: "2026-03-01"
  next_review: "2026-06-01"
---

## Overview

libtmux is a typed Python library that provides an ORM-like wrapper over the tmux terminal multiplexer. Rather than invoking tmux CLI commands and parsing text output, developers interact with four live Python objects — `Server`, `Session`, `Window`, and `Pane` — each backed by tmux's format strings and real process state. The same library powers tmuxp (the declarative tmux workspace manager), ensuring the API is battle-tested in production workloads.

The library's primary value is eliminating the subprocess-plus-string-parsing pattern when scripting tmux: create sessions in background, split windows, send keystrokes, and capture pane output all through typed Python method calls. As of v0.53.1, it ships a `Framework :: Pytest` entry point with fixtures for isolated tmux test servers.

---

## Problem Addressed

| Problem | libtmux Solution |
|---------|-----------------|
| `subprocess.run(["tmux", "list-sessions"])` returns text that must be parsed | `server.sessions` returns a typed `QueryList[Session]` of live objects |
| No way to filter tmux objects without grep/awk | Django-ORM-style filtering: `sessions.filter(session_name__startswith="dev")` |
| Pane output requires `tmux capture-pane` subprocess call and parsing | `pane.capture_pane()` returns `list[str]`, with optional start/end line control |
| Sending keys requires building a subprocess command string | `pane.send_keys("echo hello", enter=True)` — typed, no quoting issues |
| Tmux socket/server isolation is manual to configure | `Server(socket_name="test")` isolates test runs from user sessions |
| Writing tests for tmux-scripting tools is brittle | Built-in pytest fixtures (`server`, `session`, `window`, `pane`) with automatic cleanup |
| Context manager support requires manual try/finally cleanup | `with server.new_session() as session:` handles kill on exit |
| Options and hooks require raw `tmux set-option` subprocess calls | `OptionsMixin` and `HooksMixin` on every object for typed get/set |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 1,146 | 2026-03-01 |
| GitHub Forks | 115 | 2026-03-01 |
| Open Issues | 97 | 2026-03-01 |
| Subscribers (watchers) | 16 | 2026-03-01 |
| Contributors | 42 | 2026-03-01 |
| Repository Created | 2016-05-22 | - |
| Latest Release | v0.53.1 (2026-02-19) | 2026-03-01 |
| Python Support | >=3.10, <4.0 (CPython + PyPy) | 2026-03-01 |
| tmux Requirement | >=3.2a | 2026-03-01 |
| License | MIT | 2026-03-01 |
| PyPI Package | `libtmux` | 2026-03-01 |
| Runtime Dependencies | None (zero required) | 2026-03-01 |
| Development Status | Production/Stable (classifier 5) | 2026-03-01 |

SOURCE: [GitHub API - tmux-python/libtmux](https://api.github.com/repos/tmux-python/libtmux) (accessed 2026-03-01); [PyPI libtmux JSON](https://pypi.org/pypi/libtmux/json) (accessed 2026-03-01)

---

## Key Features

### Four Core Objects: Server, Session, Window, Pane

The tmux hierarchy maps exactly to Python classes, each a dataclass with live state:

```python
import libtmux

server = libtmux.Server()  # connects to default tmux socket
server = libtmux.Server(socket_name="my-server")  # isolated socket

session: libtmux.Session = server.new_session(
    session_name="dev",
    start_directory="/home/user/project",
    attach=False,  # background, no attach
    x=220,
    y=50,  # explicit dimensions for headless
)
window: libtmux.Window = session.new_window(window_name="editor", attach=False)
pane: libtmux.Pane = window.split(direction=libtmux.PaneDirection.Below, shell="bash")
```

Each object maps to a tmux ID type: `Session` uses `$N`, `Window` uses `@N`, `Pane` uses `%N`.

SOURCE: [libtmux README](https://raw.githubusercontent.com/tmux-python/libtmux/master/README.md) (accessed 2026-03-01); [src/libtmux/server.py](https://raw.githubusercontent.com/tmux-python/libtmux/master/src/libtmux/server.py) (accessed 2026-03-01)

### Pane.send_keys — Keystroke Injection

```python
pane.send_keys("echo 'hello world'")  # sends text + Enter
pane.send_keys("echo hey", enter=False)  # sends text without Enter
pane.send_keys("q", literal=True)  # sends literal key, not tmux key binding
pane.enter()  # sends Enter alone
pane.clear()  # sends Ctrl-L (clear screen)
pane.reset()  # sends 'reset' command
```

`suppress_history=True` prepends a space to avoid writing to shell history (default: False since v0.14).

SOURCE: [src/libtmux/pane.py send_keys](https://raw.githubusercontent.com/tmux-python/libtmux/master/src/libtmux/pane.py) (accessed 2026-03-01)

### Pane.capture_pane — Output Capture

```python
# Current visible pane contents
lines: list[str] = pane.capture_pane()

# Last 50 lines of scrollback history
lines = pane.capture_pane(start=-50, end="-")

# Full history from beginning
lines = pane.capture_pane(start="-", end="-")

# Include ANSI escape sequences for color information
lines = pane.capture_pane(escape_sequences=True)

# Escape non-printable chars as \xxx octal
lines = pane.capture_pane(escape_non_printable=True)
```

Parameters `start` and `end` accept integers (negative = scrollback, 0 = first visible line, positive = visible lines), or `"-"` literal for history start/end.

SOURCE: [src/libtmux/pane.py capture_pane](https://raw.githubusercontent.com/tmux-python/libtmux/master/src/libtmux/pane.py) (accessed 2026-03-01)

### Pane.split — Dynamic Pane Creation

```python
# Split below (default)
new_pane = window.split()

# Split with direction
from libtmux.constants import PaneDirection

right_pane = window.split(direction=PaneDirection.Right)

# Split with specific size (percentage or cells)
pane = window.split(size="30%")
pane = window.split(size=20)

# Split and run a command (pane closes when command exits)
pane = window.split(shell="python3 -m http.server 8080")

# Split with working directory and environment
pane = window.split(start_directory="/home/user/project", environment={"VIRTUAL_ENV": "/home/user/.venv"})
```

SOURCE: [src/libtmux/pane.py split](https://raw.githubusercontent.com/tmux-python/libtmux/master/src/libtmux/pane.py) (accessed 2026-03-01)

### QueryList Filtering — ORM-Style Object Queries

All collections (`server.sessions`, `session.windows`, `window.panes`) return `QueryList` objects with Django-inspired field lookups:

```python
# Exact match
session = server.sessions.get(session_name="dev")

# Prefix filter
windows = session.windows.filter(window_name__startswith="api")

# Contains filter
panes = window.panes.filter(pane_current_path__contains="/project")

# Get active/attached state
active_pane = window.active_pane
active_window = session.active_window

# Traverse hierarchy bidirectionally
pane.window  # Window containing this pane
pane.session  # Session containing this pane
window.session  # Session containing this window
```

Supported lookup operators: exact (default), `__startswith`, `__endswith`, `__contains`, `__regex`, `__icontains`, `__in`.

SOURCE: [src/libtmux/_internal/query_list.py](https://raw.githubusercontent.com/tmux-python/libtmux/master/src/libtmux/_internal/query_list.py) (accessed 2026-03-01)

### Context Managers — Automatic Cleanup

Every object supports `with` statement for deterministic teardown:

```python
# Server as context manager (kills server on exit)
with libtmux.Server(socket_name="test-server") as server:
    session = server.new_session("workspace")
    # server.kill() called automatically

# Pane as context manager (kills pane on exit)
with window.split(shell="bash") as pane:
    pane.send_keys("npm test")
    output = pane.capture_pane()
    # pane.kill() called automatically
```

SOURCE: [src/libtmux/server.py __exit__](https://raw.githubusercontent.com/tmux-python/libtmux/master/src/libtmux/server.py) (accessed 2026-03-01)

### Raw Escape Hatch — `.cmd()`

Every object exposes `.cmd()` for direct tmux commands not yet wrapped:

```python
# On Server
server.cmd("display-message", "hello world")
server.cmd("new-session", "-d", "-P", "-F#{session_id}")

# On Session
session.cmd("send-keys", "-t", f"{session.name}:0", "ls", "Enter")

# On Pane
result = pane.cmd("capture-pane", "-p")
print(result.stdout)  # list[str]
print(result.stderr)  # list[str]
```

`.cmd()` properly passes the socket name/path so commands always target the correct tmux server.

SOURCE: [libtmux README](https://raw.githubusercontent.com/tmux-python/libtmux/master/README.md) (accessed 2026-03-01)

### Options and Hooks Mixins

All four objects inherit `OptionsMixin` and `HooksMixin`:

```python
# Read/write tmux options
server.set_option("default-terminal", "tmux-256color", g=True)
session.set_option("base-index", "1")
window.set_window_option("synchronize-panes", "on")

# Hook management (tmux hooks)
session.set_hook("after-new-window", "run-shell 'notify window created'")
```

SOURCE: [src/libtmux/options.py](https://raw.githubusercontent.com/tmux-python/libtmux/master/src/libtmux/options.py) (accessed 2026-03-01)

### Pytest Plugin — Isolated Test Fixtures

Register by installing libtmux; fixtures are auto-discovered via the `Framework :: Pytest` entry point:

```python
# conftest.py — no setup needed, fixtures provided automatically
from libtmux.server import Server
from libtmux.session import Session


def test_tool_creates_windows(session: Session) -> None:
    """Receives a fresh, isolated tmux session."""
    window = session.new_window(window_name="test-window")
    pane = window.active_pane
    pane.send_keys("echo 'test output'", enter=True)

    lines = pane.capture_pane()
    assert any("test output" in line for line in lines)
    # Cleanup is automatic — session and server torn down after test


def test_multi_server(server: Server) -> None:
    """Receives a fresh tmux server on an isolated socket."""
    s1 = server.new_session("session-a")
    s2 = server.new_session("session-b")
    assert len(server.sessions) == 2
```

Available fixtures: `home_path`, `user_path`, `config_file`, `server`, `session`, `window`, `pane`. Each creates isolated resources on temporary sockets, preventing interference with the user's running tmux.

SOURCE: [src/libtmux/pytest_plugin.py](https://raw.githubusercontent.com/tmux-python/libtmux/master/src/libtmux/pytest_plugin.py) (accessed 2026-03-01)

### Pane Position Introspection

```python
pane.at_top  # bool — pane is at top edge of window
pane.at_bottom  # bool — pane is at bottom edge of window
pane.at_left  # bool — pane is at left edge of window
pane.at_right  # bool — pane is at right edge of window
pane.height  # str — height in rows
pane.width  # str — columns
pane.index  # str — pane index within window
```

SOURCE: [src/libtmux/pane.py properties](https://raw.githubusercontent.com/tmux-python/libtmux/master/src/libtmux/pane.py) (accessed 2026-03-01)

---

## Technical Architecture

### Package Structure

```text
src/libtmux/
├── __init__.py          # Public API: Server, Session, Window, Pane
├── server.py            # Server class — entry point, owns sessions
├── session.py           # Session class — owns windows
├── window.py            # Window class — owns panes
├── pane.py              # Pane class — terminal interaction surface
├── common.py            # EnvironmentMixin, tmux_cmd, version helpers
├── constants.py         # PaneDirection, OptionScope, ResizeAdjustmentDirection
├── exc.py               # Exception hierarchy (17 typed exceptions)
├── formats.py           # FORMAT_SEPARATOR, tmux format strings
├── hooks.py             # HooksMixin for all objects
├── neo.py               # Obj base class, fetch_obj, fetch_objs, parse_output
├── options.py           # OptionsMixin for all objects
├── pytest_plugin.py     # Pytest fixtures: server, session, window, pane
└── _internal/
    └── query_list.py    # QueryList with ORM-style filtering operators
```

### Execution Model

Every public method (e.g., `pane.send_keys()`, `session.new_window()`) ultimately calls `tmux_cmd()` in `common.py`, which invokes tmux as a subprocess. Return data uses tmux format strings (`-F`) to get structured output. The `neo.py` module (`fetch_obj`, `fetch_objs`, `parse_output`) handles list-parsing: libtmux runs `list-sessions`/`list-windows`/`list-panes` with a custom `FORMAT_SEPARATOR`-delimited format string and splits the result into typed dicts (`SessionDict`, `WindowDict`, `PaneDict`).

v0.53.1 eliminated one extra subprocess call in `new_session()` by expanding the `-F` format string to include all session fields and parsing the `new-session -P` output directly, fixing a race condition in Docker/PyInstaller environments.

### Type System

All four classes are Python dataclasses inheriting from `Obj` (defined in `neo.py`). `Obj` provides `refresh()`, `cmd()`, and dict-style attribute access (`pane["pane_current_path"]`). `QueryList` is generic (`QueryList[T]`) and uses `keygetter()` for nested key traversal with `__dunder` lookup operators.

### Exception Hierarchy

```text
LibTmuxException
├── DeprecatedError
├── TmuxSessionExists
├── TmuxCommandNotFound
├── TmuxObjectDoesNotExist (extends ObjectDoesNotExist)
├── VersionTooLow
├── BadSessionName
├── OptionError
│   ├── UnknownOption
│   │   └── UnknownColorOption
│   ├── InvalidOption
│   └── AmbiguousOption
├── WaitTimeout
├── VariableUnpackingError
├── PaneError
│   └── PaneNotFound
└── WindowError
    ├── MultipleActiveWindows
    ├── NoActiveWindow
    └── NoWindowsExist
```

SOURCE: [src/libtmux/exc.py](https://raw.githubusercontent.com/tmux-python/libtmux/master/src/libtmux/exc.py) (accessed 2026-03-01)

### Version and Socket Utilities

```python
from libtmux.common import get_version, has_version, has_gt_version

get_version()  # LooseVersion of running tmux binary
has_version("3.2")  # bool — exact match
has_gt_version("3.0")  # bool — strictly greater
has_gte_version("3.2a")  # bool — greater or equal
```

---

## Installation and Usage

```bash
# pip
pip install libtmux

# uv
uv add libtmux

# pipx (for scripting contexts)
pipx install libtmux

# pin for pre-1.0 stability (recommended by upstream)
# requirements.txt
libtmux==0.53.*
# pyproject.toml
# libtmux = "0.53.*"

# bleeding edge
pip install 'git+https://github.com/tmux-python/libtmux.git'
```

**Runtime requirement**: tmux >= 3.2a must be installed and on PATH.

### Full Workflow: Create Workspace, Run Commands, Capture Output

```python
import libtmux
from libtmux.constants import PaneDirection

# Connect to (or create) a named isolated server
server = libtmux.Server(socket_name="claude-agent")

# Create a session with explicit dimensions (needed in headless/TTY-less environments)
session = server.new_session(session_name="workspace", start_directory="/home/user/project", attach=False, x=220, y=50)

# Get the initial window and pane
window = session.active_window
main_pane = window.active_pane

# Split to create a second pane for output monitoring
monitor_pane = window.split(direction=PaneDirection.Below, size="20%")

# Send commands to the main pane
main_pane.send_keys("source .venv/bin/activate")
main_pane.send_keys("python run_agent.py --task build")

# Capture output from monitor pane
import time

time.sleep(2)  # wait for command to produce output
output_lines = monitor_pane.capture_pane(start=-100, end="-")
errors = [line for line in output_lines if "ERROR" in line]

# Kill specific pane
monitor_pane.kill()

# Kill entire session when done
session.kill()
```

### Headless Usage Without a TTY

libtmux works in environments without an attached terminal (CI, Docker, Claude Code sessions) by using `x` and `y` dimensions in `new_session()` and the `attach=False` flag:

```python
server = libtmux.Server(socket_name="headless-test")
session = server.new_session(
    session_name="ci-run",
    attach=False,
    x=200,  # explicit width required without TTY
    y=50,  # explicit height required without TTY
)
```

Without `x`/`y`, tmux in headless mode may default to 80x24 or fail to start. The `socket_name` parameter isolates the server from user sessions.

### Environment Variable Injection

```python
# Pass environment variables to new sessions/panes
session = server.new_session(session_name="env-test", attach=False, environment={"API_KEY": "secret", "DEBUG": "1"})
pane = window.split(environment={"NODE_ENV": "test"})
```

---

## Relevance to Claude Code Development

### Direct Application: PTY Management Without TTY

Claude Code sessions run without an attached TTY (no terminal). The existing interactive terminal workaround protocol uses `tmux` for providing a PTY. libtmux enables this to be scripted cleanly from Python without shelling out:

```python
# Current approach (subprocess + string parsing)
subprocess.run(["tmux", "new-session", "-d", "-s", "mysession", "-x", "160", "-y", "50", "command"])
subprocess.run(["tmux", "capture-pane", "-t", "mysession", "-p"])

# libtmux equivalent (typed, no parsing)
import libtmux

server = libtmux.Server(socket_name="claude-pty")
with server.new_session("tool-run", attach=False, x=160, y=50) as session:
    pane = session.active_window.active_pane
    pane.send_keys("command here")
    output = pane.capture_pane()
```

### Application: Multi-Pane Agent Workspaces

Agent workflows that need concurrent terminal processes (e.g., running a dev server while tests execute) can use libtmux to create structured pane layouts:

```python
def create_dev_workspace(project_path: str) -> dict:
    """Create a tmux workspace for development with server + test runner."""
    server = libtmux.Server(socket_name="dev-workspace")
    session = server.new_session("dev", start_directory=project_path, attach=False, x=220, y=50)

    window = session.active_window
    window.rename_window("main")

    # Server pane (top, 70% height)
    server_pane = window.active_pane
    server_pane.send_keys("uv run uvicorn app:main --reload")

    # Test pane (bottom, 30% height)
    test_pane = window.split(direction=libtmux.PaneDirection.Below, size="30%")

    return {"session": session, "server_pane": server_pane, "test_pane": test_pane}
```

### Application: Output Polling for Long-Running Processes

Agents running shell commands need to monitor output. libtmux's `capture_pane()` replaces fragile subprocess pipe polling:

```python
import time


def wait_for_output(pane: libtmux.Pane, pattern: str, timeout: float = 30.0) -> list[str]:
    """Poll pane output until pattern appears or timeout."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        lines = pane.capture_pane(start=-50)
        if any(pattern in line for line in lines):
            return lines
        time.sleep(0.5)
    raise TimeoutError(f"Pattern '{pattern}' not seen in pane output within {timeout}s")
```

### Application: Test Fixture Isolation

Skills and scripts that test tmux interactions can use the pytest plugin for fully isolated, auto-cleaned fixtures:

```python
def test_agent_creates_session(server: libtmux.Server) -> None:
    """Fixture server is on a temp socket, independent of user's tmux."""
    result = my_agent_function(server)
    assert len(server.sessions) == 1
    assert server.sessions[0].name == "expected-name"
```

### Limitation: Pre-1.0 API Stability

libtmux self-describes as pre-1.0. Upstream recommends pinning to a minor version (e.g., `0.53.*`) to avoid breaking changes between releases. The CHANGES file records breaking changes per release; migration guides are published at `https://libtmux.git-pull.com/migration.html`.

---

## Integration Opportunities

### Enhances Existing

| Target | Type | How |
|--------|------|-----|
| `.claude/rules/interactive-terminal-workarounds.md` | rule | Add libtmux as a named Python option under "PTY Providers" — `Server(socket_name=...) + new_session(attach=False, x=160, y=50)` replaces the `tmux new-session -d` shell invocation pattern, providing typed output from `capture_pane()` instead of `tmux capture-pane -p` shell call |
| `plugins/python3-development/` | plugin | Add libtmux to the modern-modules reference as the recommended library for any Python script needing to create, control, or monitor tmux sessions — with the note to pin `libtmux==0.53.*` |
| `research/developer-tools/psmux.md` | research | Cross-reference — psmux is a minimal tmux scripting alternative; libtmux is the full-featured ORM approach with pytest integration |
| `research/developer-tools/using-tmux-with-claude-code.md` | research | Cross-reference libtmux as the Python programmatic control layer on top of the tmux patterns documented there |

### Cross-References

- Related research: `research/developer-tools/psmux.md` — psmux is a lighter-weight tmux scripting library; libtmux is the more comprehensive ORM-style alternative with full type annotations and pytest integration.
- Related research: `research/developer-tools/byobu.md` — byobu wraps tmux/screen for interactive sessions; libtmux targets programmatic control from Python scripts rather than interactive session management.
- Related research: `research/developer-tools/shpool.md` — shpool provides session persistence without tmux; libtmux specifically targets tmux as the session backend.
- Related research: `research/developer-tools/dtach.md` — dtach provides minimal detach/reattach; libtmux provides full structured access to tmux's complete feature set.

---

## References

1. **libtmux GitHub Repository** - <https://github.com/tmux-python/libtmux> (accessed 2026-03-01)
2. **libtmux Documentation** - <https://libtmux.git-pull.com> (accessed 2026-03-01)
3. **libtmux README** - <https://raw.githubusercontent.com/tmux-python/libtmux/master/README.md> (accessed 2026-03-01, via research agent)
4. **GitHub API - Repository Metadata** - <https://api.github.com/repos/tmux-python/libtmux> (accessed 2026-03-01): stars=1146, forks=115, subscribers=16, license=MIT, created=2016-05-22
5. **GitHub API - Latest Release** - <https://api.github.com/repos/tmux-python/libtmux/releases/latest> (accessed 2026-03-01): v0.53.1 (2026-02-19), bug fix for race condition in new_session()
6. **GitHub API - Contributors** - <https://api.github.com/repos/tmux-python/libtmux/contributors?per_page=1> (accessed 2026-03-01): 42 total contributors (from Link header last page)
7. **PyPI libtmux JSON** - <https://pypi.org/pypi/libtmux/json> (accessed 2026-03-01): version=0.53.1, requires-python=>=3.10,<4.0, no runtime dependencies
8. **pyproject.toml** - <https://raw.githubusercontent.com/tmux-python/libtmux/master/pyproject.toml> (accessed 2026-03-01): classifiers, keywords, dependency-groups
9. **src/libtmux/server.py** - <https://raw.githubusercontent.com/tmux-python/libtmux/master/src/libtmux/server.py> (accessed 2026-03-01): Server class, new_session(), sessions/windows/panes QueryList properties
10. **src/libtmux/pane.py** - <https://raw.githubusercontent.com/tmux-python/libtmux/master/src/libtmux/pane.py> (accessed 2026-03-01): send_keys(), capture_pane(), split(), position properties
11. **src/libtmux/session.py** - <https://raw.githubusercontent.com/tmux-python/libtmux/master/src/libtmux/session.py> (accessed 2026-03-01): Session class method signatures
12. **src/libtmux/window.py** - <https://raw.githubusercontent.com/tmux-python/libtmux/master/src/libtmux/window.py> (accessed 2026-03-01): Window class method signatures
13. **src/libtmux/exc.py** - <https://raw.githubusercontent.com/tmux-python/libtmux/master/src/libtmux/exc.py> (accessed 2026-03-01): full exception hierarchy
14. **src/libtmux/__init__.py** - <https://raw.githubusercontent.com/tmux-python/libtmux/master/src/libtmux/__init__.py> (accessed 2026-03-01): public API surface: Server, Session, Window, Pane
15. **src/libtmux/pytest_plugin.py** - <https://raw.githubusercontent.com/tmux-python/libtmux/master/src/libtmux/pytest_plugin.py> (accessed 2026-03-01): server, session, window, pane fixtures
16. **CHANGES (Changelog)** - <https://raw.githubusercontent.com/tmux-python/libtmux/master/CHANGES> (accessed 2026-03-01): v0.53.1 race condition fix, v0.53.0 breaking change in Session.attach()
