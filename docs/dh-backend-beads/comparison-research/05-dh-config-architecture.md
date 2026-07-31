---
title: DH Configuration Architecture and Beads Config Detection — Research for Backend-Switching Design
date: 2026-05-14
scope: |
  Documents how DH resolves project identity, where it stores state, and what
  configuration mechanisms exist — with focus on the existing backend config concept
  and where a "backend: beads" option could be added. Also documents how beads detects
  its project root and stores config. Concludes with the detection precedence rules
  and pseudocode for a thin CLI wrapper that routes between backends.
sources:
  - plugins/development-harness/dh_paths.py
  - plugins/development-harness/backlog_core/backend_protocol.py
  - plugins/development-harness/backlog_core/backends/__init__.py
  - plugins/development-harness/CLAUDE.md
  - plugins/development-harness/docs/backend-providers.md
  - ~/.dh/projects/ (live directory listing)
  - /home/user/repos/beads/internal/beads/beads.go (FindBeadsDir, FindDatabasePath)
  - /home/user/repos/beads/internal/config/config.go (Initialize, config precedence)
  - /home/user/repos/beads/internal/config/yaml_config.go (YamlOnlyKeys, SetYamlConfig)
  - /home/user/repos/beads/cmd/bd/config.go (configCmd, configSetCmd)
  - /home/user/repos/beads/cmd/bd/init.go (initCmd flags)
---

## Summary

DH has a fully-developed, two-level backend configuration system already in production:
`BACKLOG_BACKEND` env var or `backend.toml` selects among `github`, `sqlite`, and `memory`
for the backlog MCP; `TASKBACKEND` env var or `taskbackend.toml` selects among `local`,
`github`, and `memory` for the SAM MCP. Adding `beads` as a fourth backend name requires
adding one new case to each factory function and implementing the corresponding `BacklogBackend`
and `TaskBackend` Protocol classes. No new config file format is needed; `backend.toml` already
supports the `[backend] name` key.

Beads detects its project root by walking up from `cwd` looking for a `.beads/` directory
containing project files (a Dolt database), mirroring DH's `git rev-parse --git-common-dir`
walk. Both systems key on the same directory (the git repo root). A shared project identity
is available without any additional convention: whichever directory contains both `.git/` and
`.beads/` is the project root for both tools.

---

## Part 1 — DH State and Config Architecture

### 1.1 Three-Tier Layout

DH organises state into three tiers, all resolved through `dh_paths.py`:

```text
Tier 1 — In-repo project config (committed, shared across developers):
  {project_root}/.dh/
    .gitkeep              (created by ensure_dirs(); keeps dir in VCS)
    backend.toml          (OPTIONAL — selects backlog backend; not created by default)
    taskbackend.toml      (OPTIONAL — selects SAM backend; not created by default)

Tier 2 — Persistent per-project state (outside repo, machine-local):
  ~/.dh/projects/{slug}/
    backlog/              (per-item .yaml + .md files; local cache of GitHub Issues)
    plan/                 (SAM task plan YAML files: P{id}-{slug}.yaml, T0-baseline-*.yaml)
    milestones/
    research/

Tier 3 — Ephemeral per-session state:
  ~/.dh/projects/{slug}/
    context/              (active-task-{session-id}.json)
    reports/
```

The `dispatch-state.db` SQLite file (used by `dispatch_state.DispatchStateManager`) is at:

```text
~/.dh/projects/{slug}/dispatch-state.db
```

### 1.2 Slug Computation

Source: `dh_paths.py:compute_slug()` (lines 260–278).

Algorithm: replace every `/` in the absolute path string with `-`.

```text
/home/user/repos/claude_skills
  → -home-user-repos-claude_skills
```

The leading `-` is intentional — it distinguishes slugs from ordinary directory names and
prevents collision with numeric IDs. The live directory confirms this:

```text
~/.dh/projects/-home-user-repos-claude_skills/
```

### 1.3 DH_STATE_HOME Override

Source: `dh_paths.py:_dh_user_root()` (lines 305–317).

```python
def _dh_user_root() -> Path:
    env_override = os.environ.get("DH_STATE_HOME", "")
    if env_override:
        return Path(env_override).expanduser()
    return Path.home() / ".dh"
```

Default: `~/.dh/`
Override: `DH_STATE_HOME=/tmp/test-dh uv run ...`

### 1.4 Project Root Resolution

Source: `dh_paths.py:infer_project_root()` (lines 181–231).

Resolution order (first match wins):

1. `DH_PROJECT_ROOT` env var — explicit override for any host
2. `WORKSPACE_FOLDER_PATHS` — JSON array (VS Code / Cursor); first entry resolving as a git repo
3. `CURSOR_PROJECT_ROOT` env var — Cursor-specific
4. `CLAUDE_PROJECT_DIR` env var — Claude Code host
5. Walk upward from `cwd` looking for a `.git` entry, then `git rev-parse --git-common-dir`
6. `git rev-parse` from `cwd` directly

The git root discovery uses `--git-common-dir` (not `--show-toplevel`) to correctly handle
linked worktrees — the common dir's parent is the main worktree root even when invoked from
a linked worktree.

### 1.5 What Files Exist in `~/.dh/projects/{slug}/`

Observed from live filesystem at `~/.dh/projects/-home-user-repos-claude_skills/`:

```text
backlog/          ← per-item YAML + MD files (GitHub Issues local cache)
context/          ← ephemeral session context (active-task-*.json)
kage-bunshin/     ← kage-bunshin session state (not documented in dh_paths.py)
plan/             ← SAM task plan files
reports/          ← agent investigation reports
```

No per-project config file (e.g. `project.toml`) exists in the slug directory. All
per-project config is in `{project_root}/.dh/` (Tier 1) or env vars.

---

## Part 2 — Existing Backend Configuration System

### 2.1 Backlog Backend Selection

Source: `backlog_core/backend_protocol.py:create_backend()` (lines 1003–1044).

Resolution order (first non-empty value wins):

1. `BACKLOG_BACKEND` environment variable
2. `[backend] name` in `backend.toml` (searched: `{project_root}/backend.toml` then `~/.dh/backend.toml`)
3. Default: `"github"`

Valid backend names: `"github"`, `"sqlite"`, `"memory"`.

`backend.toml` format (TOML):

```toml
[backend]
name = "sqlite"
```

The search logic in `_load_backend_toml_name()` (lines 969–1000) calls `dh_paths.git_project_root()`
to locate the project root, then checks `{project_root}/backend.toml` before `~/.dh/backend.toml`.
A missing file is silently ignored. A present file without the `backend.name` key is also ignored.

The singleton pattern: `get_config()` caches the result in `_active_config`. Tests call
`reset_config()` to clear the cache between test runs.

### 2.2 SAM (TaskBackend) Selection

Source: `plugins/development-harness/docs/backend-providers.md` lines 200–221.

Resolution order:

1. `TASKBACKEND` environment variable
2. `[backend] name` in `taskbackend.toml` (searched: `{project_root}/taskbackend.toml` then `~/.dh/taskbackend.toml`)
3. Default: `"local"`

Valid backend names: `"local"`, `"github"`, `"memory"`.

`taskbackend.toml` format:

```toml
[backend]
name = "local"
```

### 2.3 The BacklogBackend Protocol

Source: `backlog_core/backend_protocol.py` (full file).

`BacklogBackend` is a `@runtime_checkable` `Protocol` with synchronous methods. The MCP layer
wraps calls in `asyncio.to_thread()` when needed. `BacklogConfig` is a dataclass wrapping the
active backend instance. `operations.py` and `server.py` receive `BacklogConfig` via dependency
injection.

Three implementations exist:

| Name | Class | Module |
|---|---|---|
| `github` | `GitHubBackend` | `backlog_core/backends/github_backend.py` |
| `sqlite` | `SQLiteBackend` | `backlog_core/backends/sqlite_backend.py` |
| `memory` | `InMemoryBackend` | `backlog_core/backends/memory_backend.py` |

All three are in `backlog_core/backends/`. Imports are deferred inside `create_backend()` to
avoid circular imports (backends import TypedDicts from `backend_protocol.py`).

### 2.4 How to Add `backend: beads`

Adding `beads` as a recognised backend name requires:

**In `backlog_core/backend_protocol.py`:**

```python
_VALID_BACKENDS: tuple[str, ...] = ("beads", "github", "memory", "sqlite")  # add "beads"


def create_backend(name: str | None = None) -> BacklogBackend:
    ...
    if resolved == "beads":
        from backlog_core.backends.beads_backend import BeadsBackend  # noqa: PLC0415

        return cast("BacklogBackend", BeadsBackend())
    ...
```

**New file `backlog_core/backends/beads_backend.py`:**

A class `BeadsBackend` that implements the `BacklogBackend` Protocol by delegating to the
beads CLI (`bd`) or its internal Go library via subprocess. The class routes every method call
to the equivalent `bd` subcommand.

This is the only required code change to wire the new backend into the existing config system.

---

## Part 3 — Beads Config and Detection Architecture

### 3.1 Beads Project Root Detection

Source: `internal/beads/beads.go:FindBeadsDir()` and `FindBeadsDirFrom()`.

Beads detects its project root by finding the `.beads/` directory that contains project files
(a Dolt database). Resolution order (first match wins):

1. `BEADS_DIR` environment variable — explicit override; must contain a valid `.beads/` with project files
2. Walk upward from `cwd` through ancestor directories, checking each for `.beads/` with project files
3. Worktree fallback: if the walk reaches the git worktree root and finds `.beads/` metadata
   without a database, check the shared worktree `.beads/` via `worktreeFallbackBeadsDirForRepo`

The walk uses `hasBeadsProjectFiles()` to distinguish a `.beads/` directory that actually
holds a Dolt database from one that only holds committed metadata (hooks, config).

A `.beads/redirect` file may redirect to a different `.beads/` directory path, enabling shared
databases across multiple git worktrees.

### 3.2 Beads Config File Locations

Source: `internal/config/config.go:Initialize()` (lines 1–368).

Config is layered (lowest priority first, each layer merged on top):

```text
Priority 1 (lowest):  ~/.beads/config.yaml          (legacy user config)
Priority 2:           ~/.config/bd/config.yaml       (XDG user config)
Priority 3:           Walk up from cwd to find {dir}/.beads/config.yaml  (project config)
Priority 4 (highest): $BEADS_DIR/config.yaml          (explicit override)

Local override (merged on top of project config, not committed):
              {project_dir}/.beads/config.local.yaml
```

Environment variables via `BD_*` prefix take precedence over all config files. Example:
`BD_JSON=true` maps to the `json` key.

### 3.3 Beads Config Namespaces

Source: `internal/config/config.go` defaults block (lines 168–263) and `cmd/bd/config.go` help text.

Key namespaces relevant to backend switching:

```text
export.*          Auto-export settings (stored in config.yaml, not DB)
jira.*            Jira integration
linear.*          Linear integration
github.*          GitHub integration
routing.*         Issue routing (maintainer vs contributor mode)
dolt.*            Dolt storage settings (auto-commit, remotes)
sync.*            Remote sync settings (sync.remote URL)
```

Notable startup keys (must be in `config.yaml`, read before DB opens):
- `no-db`, `json`, `db`, `actor`, `identity`, `routing.*`, `sync.*`, `git.*`

### 3.4 What `.beads/` Contains

From `internal/beads/beads.go` and `cmd/bd/init.go`:

```text
{project_root}/.beads/
  config.yaml           ← project-level config (committed; no secrets)
  config.local.yaml     ← machine-local overrides (gitignored)
  redirect              ← optional redirect to a different .beads/ path
  issues.jsonl          ← auto-export file (the beads issue database in JSONL)
  {prefix}*.db or dolt/ ← Dolt embedded database (gitignored)
  hooks/                ← bd hook scripts
  formulas/             ← workflow formula definitions (.formula.toml files)
```

The beads `.beads/` in the beads repo itself contains only `formulas/` (the beads-release
formula). The Dolt database and `issues.jsonl` are gitignored.

### 3.5 `bd config` Commands

Source: `cmd/bd/config.go`.

```bash
bd config set <key> <value>   # Set a config value (DB or config.yaml for startup keys)
bd config get <key>           # Get a config value
bd config list                # List all config values
bd config unset <key>         # Remove a config value
```

Config is stored in SQLite (the Dolt DB) for most keys. Startup keys (listed in `YamlOnlyKeys`)
are stored in `config.yaml` so they are available before the DB is opened.

---

## Part 4 — Shared Project Identity

Both DH and beads identify a project by its directory on the filesystem. Both walk up from
`cwd` to find their respective markers:

| System | Marker | Walk terminator |
|---|---|---|
| DH | `.git/` entry → `git rev-parse --git-common-dir` | Filesystem root |
| beads | `.beads/` directory with project files | Filesystem root (with git worktree boundary awareness) |

For any repo that has both `bd init` and DH initialised, the git root directory is identical
for both systems. DH computes `slug = path.replace("/", "-")`; beads uses the path directly
via `BEADS_DIR` or the walk-up discovery.

There is no existing shared identity token. The shared ground truth is: the same absolute
path to the git repo root identifies the project in both systems.

---

## Part 5 — Where the CLI Wrapper Would Live

The thin CLI wrapper that reads the backend config and routes `dh backlog *` commands to either
GitHub (DH native) or beads (`bd`) should live at:

```text
plugins/development-harness/scripts/dh_backlog_router.py
```

This follows the repository convention: all companion scripts are Python PEP 723 scripts in
`plugins/{plugin-name}/scripts/`. The router is invoked by the backlog MCP server as a
subprocess, or used as the CLI entry point for direct invocation.

Alternatively, routing can be implemented entirely inside the `BeadsBackend` class at
`backlog_core/backends/beads_backend.py` — the MCP server instantiates whichever backend
`create_backend()` returns, so the routing is transparent to the server.

The CLI wrapper pattern (rather than in-process routing) is appropriate if the beads
integration must survive the MCP server's Python process and interact with the Dolt embedded
engine through the `bd` binary.

---

## Part 6 — Backend Routing Logic Pseudocode

### Detection Precedence Rules

```text
For the backlog backend:

  1. BACKLOG_BACKEND env var (explicit, highest priority)
     └─ value: "github" | "sqlite" | "memory" | "beads"

  2. backend.toml [backend] name
     └─ search: {git_project_root}/backend.toml → ~/.dh/backend.toml
     └─ value: "github" | "sqlite" | "memory" | "beads"

  3. Auto-detect: beads
     └─ condition: .beads/ directory with project files exists at or above cwd
     └─ activates only if user opts in via a config flag (see below)

  4. Default: "github"
```

Auto-detect (#3) is not implemented in the current codebase. It would be a new feature that
checks for `.beads/` existence before falling through to the default. Given that beads is a
user-initiated tool (`bd init`), auto-detection is safe: if `.beads/` is present, the user
chose beads. The check is: `any(p.is_dir() for p in walk_up(cwd, ".beads"))`.

### Factory Extension Pseudocode

```python
# In backlog_core/backend_protocol.py:create_backend()


def create_backend(name: str | None = None) -> BacklogBackend:
    resolved = (
        name
        or os.environ.get("BACKLOG_BACKEND")
        or _load_backend_toml_name()
        or _auto_detect_beads()  # NEW: returns "beads" if .beads/ found, else None
        or "github"
    )

    if resolved == "beads":
        from backlog_core.backends.beads_backend import BeadsBackend

        return cast("BacklogBackend", BeadsBackend())

    if resolved == "github":
        ...
    if resolved == "sqlite":
        ...
    if resolved == "memory":
        ...

    msg = f"Unknown backend {resolved!r}. Valid options: {', '.join(sorted(_VALID_BACKENDS))}"
    raise ValueError(msg)


def _auto_detect_beads() -> str | None:
    """Return "beads" if a .beads/ directory with project files exists at or above cwd."""
    try:
        project_root = git_project_root()
    except (FileNotFoundError, RuntimeError):
        return None
    # Walk from project_root upward (typically just the project root itself)
    for candidate in (project_root, *project_root.parents):
        beads_dir = candidate / ".beads"
        if beads_dir.is_dir() and _has_beads_project_files(beads_dir):
            return "beads"
        if candidate == project_root:
            # Do not walk above the project root for auto-detection
            break
    return None


def _has_beads_project_files(beads_dir: Path) -> bool:
    """Return True if the .beads/ directory contains a Dolt database or issues.jsonl."""
    # Mirrors beads' hasBeadsProjectFiles logic (Go: beads.go)
    if (beads_dir / "issues.jsonl").exists():
        return True
    # Dolt embedded: .beads/dolt/ or .beads/*.db
    if (beads_dir / "dolt").is_dir():
        return True
    return any(beads_dir.glob("*.db"))
```

### BeadsBackend Routing Pseudocode

```python
# backlog_core/backends/beads_backend.py

import subprocess
import json
from pathlib import Path


class BeadsBackend:
    """BacklogBackend implementation that delegates to the bd CLI."""

    def _bd(self, *args: str, input_data: str | None = None) -> dict:
        """Run a bd subcommand and return parsed JSON output."""
        cmd = ["bd", "--json", *args]
        result = subprocess.run(cmd, capture_output=True, text=True, input=input_data, check=True)
        return json.loads(result.stdout)

    def create_issue_for_item(self, repo, item, dry_run=False, output=None):
        if dry_run:
            return None
        result = self._bd("create", "--title", item.title, "--description", item.description or "")
        return result.get("id")

    def close_github_issue(self, issue_ref, reason, *, reference="", comment="", repo="", output=None):
        self._bd("close", str(issue_ref), "--reason", reason)

    def fetch_item_status(self, item, repo="", output=None) -> str:
        result = self._bd("show", str(item.issue_number), "--format", "json")
        return result.get("status", "open")

    # ... remaining Protocol methods delegate to bd subcommands ...
```

---

## Part 7 — Detection Precedence Rules (Summary)

```text
Backend selection for DH backlog operations:

  explicit config > beads auto-detect > GitHub default

Expanded:

  Priority 1: BACKLOG_BACKEND env var = "beads"
              (user or CI explicitly requests beads backend)

  Priority 2: backend.toml [backend] name = "beads"
              (project or user has committed a persistent preference;
               file location: {project_root}/backend.toml or ~/.dh/backend.toml)

  Priority 3: .beads/ auto-detection
              (no explicit config; .beads/ with project files found at git root;
               user ran `bd init` in this repo — treat as opt-in)

  Priority 4: default = "github"
              (no beads installation; existing behavior unchanged)
```

Auto-detection (Priority 3) is the only addition not already in the codebase. Priorities 1
and 2 use the existing `BACKLOG_BACKEND` / `backend.toml` mechanism unchanged.

---

## What Was Found

- `dh_paths.compute_slug()` (line 278): `str(project_root).replace("/", "-")` — leading `-` is intentional
- `DH_STATE_HOME` default is `~/.dh/`; override via env var; re-evaluated on each call (monkeypatch-safe for tests)
- DH has two config files: `backend.toml` (backlog backend) and `taskbackend.toml` (SAM backend); neither is created by default
- `backend.toml` search order: `{project_root}/backend.toml` first, then `~/.dh/backend.toml`
- `_VALID_BACKENDS = ("github", "memory", "sqlite")` — no `beads` entry yet
- `_active_config` is a module-level singleton; `reset_config()` clears it for tests
- Beads walks up from cwd checking for `.beads/` with `hasBeadsProjectFiles()` (Dolt DB presence)
- Beads config precedence: `BEADS_DIR/config.yaml` > project `.beads/config.yaml` > `~/.config/bd/config.yaml` > `~/.beads/config.yaml`
- Beads `config.yaml` holds startup keys (routing, sync, identity); non-startup keys go to the Dolt DB
- The `kage-bunshin/` directory exists in the live DH project state but is not defined in `dh_paths.py` — it is created by the kage-bunshin workflow outside the standard path functions
- `dispatch-state.db` lives at `~/.dh/projects/{slug}/dispatch-state.db`; created by `dispatch_state.DispatchStateManager`

## What Was NOT Found

- No existing `beads` backend name or any mention of beads in DH source code
- No `backend.toml` or `taskbackend.toml` files in the live claude_skills repo or in `~/.dh/`
- No per-project config file at `~/.dh/projects/{slug}/` level (config is in `{project_root}/.dh/` or env vars)
- No existing auto-detection logic for alternative backends in `create_backend()`
- No shared ID token or registry that both DH and beads consult to establish a common project identity
- No `bd config set backend.*` or equivalent in beads that would tell beads to integrate with DH

## Uncertain

- `_has_beads_project_files()` Python equivalent: the Go implementation checks for a Dolt
  database directory or `.db` file. The exact file layout may vary by beads version. The
  pseudocode above uses `issues.jsonl` and `dolt/` as heuristics — verification against the
  installed beads version is needed before relying on these names.
- The `kage-bunshin/` directory at `~/.dh/projects/{slug}/kage-bunshin/` is observed in the
  live filesystem but not in `dh_paths.py`. Its creation path and whether it needs to be
  declared in `ensure_dirs()` is unclear without reading the kage-bunshin workflow code.
- The beads `BeadsBackend` method implementations would require mapping every `BacklogBackend`
  Protocol method to a `bd` CLI subcommand. Some methods (e.g. `_graphql_request`,
  `_resolve_labels_graphql`) are GitHub-specific internals that have no beads equivalent —
  these would need to return stubs or raise `NotImplementedError` with a clear message.

---

## Sources

- `plugins/development-harness/dh_paths.py` — read 2026-05-14 (485 lines, complete)
- `plugins/development-harness/backlog_core/backend_protocol.py` — read 2026-05-14 (1045 lines, complete)
- `plugins/development-harness/CLAUDE.md` — read 2026-05-14 (full system prompt injection)
- `plugins/development-harness/docs/backend-providers.md` — read 2026-05-14 (partial; backend config sections)
- `/home/user/repos/beads/internal/beads/beads.go` — read 2026-05-14 (FindBeadsDir, FindDatabasePath, FindBeadsDirFrom excerpts)
- `/home/user/repos/beads/internal/config/config.go` — read 2026-05-14 (Initialize, 369 lines complete)
- `/home/user/repos/beads/internal/config/yaml_config.go` — read 2026-05-14 (YamlOnlyKeys section)
- `/home/user/repos/beads/cmd/bd/config.go` — read 2026-05-14 (configCmd, configSetCmd excerpts)
- `~/.dh/projects/` live directory listing — observed 2026-05-14
- `~/.dh/projects/-home-user-repos-claude_skills/` live directory listing — observed 2026-05-14
