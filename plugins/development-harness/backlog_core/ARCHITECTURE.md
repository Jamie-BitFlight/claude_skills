# Backlog MCP Package — Architecture Spec

## Overview

Extract all business logic from `.claude/skills/backlog/scripts/backlog.py` into a clean Python package at `.claude/skills/backlog/backlog_core/`. The package exposes the same functionality through two thin wrappers:

1. **CLI wrapper** (`backlog.py`) — Typer CLI, calls operations module
2. **MCP server** (`server.py`) — FastMCP 3.x, calls operations module

## Source File

All logic originates from: `.claude/skills/backlog/scripts/backlog.py`

Each agent MUST read the full source file and extract ONLY the functions assigned to their module.

## I/O Modules (post-YAML migration)

Local file I/O is handled by two dedicated modules:

- `yaml_io.py` — pure-YAML read/write for backlog items (`.yaml` format). Primary path for all
  new items. Uses `ruamel.yaml` directly; no `python-frontmatter` dependency.
- `github_sync.py` — bidirectional GitHub issue body conversion. `render_issue_body` serialises a
  `BacklogItem` to GitHub markdown; `parse_issue_body` reconstructs a `BacklogItem` from issue
  body text; `merge_item` merges local and remote items with conflict resolution rules. Uses
  `entry_blocks.py` for timestamped div block handling.

**Bulk migration**: `scripts/migrate_backlog_to_yaml.py` converts an existing backlog directory
from `.md` frontmatter files to `.yaml` format in-place. It uses `yaml_io.load_item` and
`yaml_io.save_item` and deletes the source `.md` file after a successful write.

## Module Dependency Graph

```text
models.py             ← standalone, no imports from other mcp modules
parsing.py            ← imports from models; provides loads_frontmatter/dump_frontmatter (ruamel.yaml-based)
entry_blocks.py       ← timestamped entry block parse/render/rewrite; imports from models, parsing
yaml_io.py            ← pure-YAML read/write for .yaml backlog items; imports from models, parsing
github_sync.py        ← GitHub issue body conversion (render/parse/merge); imports from models, parsing, entry_blocks
gh_client.py          ← imports from models, parsing
rendering.py          ← shared rendering utilities (section_display_title, render_groomed_section); imported by backend implementations
backend_protocol.py   ← BacklogBackend Protocol, BacklogConfig, create_backend; imports from models (type hints only)
backends/             ← GitHubBackend, SQLiteBackend, InMemoryBackend; each implements BacklogBackend Protocol
operations.py         ← imports from models, parsing, backend_protocol, yaml_io
dispatch_state.py     ← imports from models (DispatchItemRecord, DispatchWaveRecord); no MCP awareness
server.py             ← imports from models, operations, dispatch_state, backend_protocol
backlog.py            ← imports from operations (thin CLI wrapper)
```

## Output Pattern

Functions that previously used `typer.echo()` for status/progress messages must instead use an `Output` object (defined in models.py). Each function that needs to communicate status takes an optional `output: Output | None = None` parameter.

```python
# In models.py — ALL models use Pydantic BaseModel
from pydantic import BaseModel, Field

class Entry(BaseModel):
    """Timestamped addressable content entry within a section."""
    id: str                        # ISO timestamp used as primary key
    content: str
    struck: bool = False
    struck_at: str = ""
    struck_reason: str = ""

class Section(BaseModel):
    """A section containing a list of timestamped entries."""
    entries: list[Entry] = Field(default_factory=list)

class GroomedData(BaseModel):
    """Structured groomed section with a date and named subsections."""
    date: str = ""
    subsections: dict[str, str] = Field(default_factory=dict)

class BacklogItem(BaseModel):
    """Parsed backlog item — replaces untyped dict."""
    title: str = ""
    description: str = ""
    source: str = "Not specified"
    added: str = ""
    priority: str = ""
    status: str = ""
    item_type: str = "Feature"
    issue: str = ""
    plan: str = ""
    section: str = ""
    file_path: str = ""
    skip: bool = False
    last_synced: str = ""
    sections: dict[str, Section | GroomedData] = Field(default_factory=dict)

# Notes:
# - `file_path` and `skip` are excluded from YAML serialisation (yaml_io.save_item).
# - `sections` holds Entry-bearing sections ("fact_check", "rt_ica", "issue_classification")
#   plus a "groomed" key (GroomedData). Populated by github_sync.parse_issue_body.

class Output(BaseModel):
    messages: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    def info(self, msg: str) -> None: ...
    def warn(self, msg: str) -> None: ...
    def error(self, msg: str) -> None: ...

# Also: IssueStatus, PullRequestRef, ViewItemResult, IssueLocalFields
```

**CRITICAL**: No `Any` type anywhere. Use `BacklogItem` instead of `dict` for items.
Use `IssueStatus` instead of `dict[str, str]` for status results.
Use `PullRequestRef` instead of `dict[str, Any]` for PR references.
Use `ViewItemResult` instead of `dict[str, Any]` for view results.

Replace `typer.echo(msg)` → `output.info(msg)`
Replace `typer.echo(msg, err=True)` → `output.warn(msg)`
Replace `typer.Exit(1)` → raise appropriate exception from models.py

## Error Handling Pattern

Functions that previously raised `typer.Exit(1)` must instead raise one of:

- `BacklogError` — general errors
- `ItemNotFoundError(selector)` — item not found
- `DuplicateItemError(duplicates)` — fuzzy duplicate detected
- `GitHubUnavailableError` — GITHUB_TOKEN missing or API unreachable
- `ValidationError` — input validation failure

---

## Module: models.py

**Responsibility**: Constants, regex patterns, type maps, exceptions, Output handler.

**Functions/data extracted from backlog.py** (line references are approximate):

- Constants: `BACKLOG_DIR`, `DEFAULT_REPO`, `SECTION_RE`, `SKIP_STATUS`, `GITHUB_ISSUE_URL_RE`, `GITHUB_ISSUE_TITLE_TRUNCATE`, `MIN_FRONTMATTER_PARTS`, `TYPE_TO_LABEL`, `ROLE_MAP`, `BENEFIT_MAP`, `FUZZY_DUPLICATE_THRESHOLD`, `_COMMIT_PREFIX_RE`, `_FIELD_TO_INDEX`
- Add new: `PRIORITY_SECTIONS` dict mapping priority strings to section headings (from the `add` command)
- Exception classes: `BacklogError`, `ItemNotFoundError`, `DuplicateItemError`, `GitHubUnavailableError`, `ValidationError`
- Pydantic models: `Entry`, `Section`, `GroomedData`, `BacklogItem`, `Output`, `IssueStatus`, `PullRequestRef`, `ViewItemResult`, `IssueLocalFields`

**Exports** (public API):
All constants, all exception classes, all Pydantic models.

**Imports from other modules**: None.

---

## Module: parsing.py

**Responsibility**: File parsing, item search, slug generation, body section utilities, view helpers, normalize helpers.

**Current active functions** (post-YAML migration):

- Date helpers: `today()`, `now_iso()`
- Slug/title: `title_to_slug()`, `normalize_issue_title()`, `infer_type()`
- Selector: `parse_issue_selector()`
- Item parsing: `parse_item_file()` (legacy `.md` path — deprecated, kept for migration tooling),
  `parse_backlog_from_directory()`, `parse_backlog()`
- Item search: `find_item()`, `find_fuzzy_duplicates()`
- Item filtering: `items_needing_issues()`, `items_with_issues()`
- Issue body: `build_issue_body()`, `build_issue_body_from_file()`
- Body utilities: `extract_groomed_section()`, `build_body_extra_only()`, `merge_sections()`
- Section extraction (used by `github_sync.py`): `extract_sections()`, `extract_groomed_section()`
- View helper: `view_result_from_local_item()`
- Normalize helper: `extract_normalize_metadata()`

**Exports**: All functions above (without leading underscores).

**Imports from other modules**: `from .models import ...`, `from ruamel.yaml import YAML, YAMLError`.

---

## Module: entry_blocks.py

**Responsibility**: Parse, render, rewrite, and diff timestamped HTML div entry blocks embedded in
GitHub issue section bodies. Each entry is identified by an ISO timestamp used as a primary key.

**Public functions**:

- Wrap: `wrap_entry(content)` — wraps content in a new timestamped `<div><sub>…</sub></div>` block
- Wrap with specific timestamp: `wrap_entry_with_timestamp(content, timestamp)` — for legacy migration and overwrites
- Parse: `parse_entries(section_body, show, since, added_date)` — parses all entry blocks from a section body string; `show` accepts `"all"`, `"last"`, `"first"`, `"struck"`, positive/negative int
- Strike: `strike_entry(entry_raw, reason)` — wraps entry content in a `<details>` struck block
- Rewrite: `rewrite_section(existing_body, new_content, entry_id, replace, reason, added_date)` — orchestrates append, targeted-entry replace, or full-replace-and-strike operations
- Diff: `generate_diff(local, remote)` — git-diff-style comparison of entry blocks between two section bodies

**Imports from other modules**: `from .models import Entry`, `from .parsing import now_iso`

---

## Module: yaml_io.py

**Responsibility**: Pure-YAML read/write for `.yaml` backlog item files. Primary I/O path for all
new items. Provides a format-detecting reader that falls back to the legacy `.md` parser during
transition.

**Public API** (`__all__`): `detect_format`, `load_item`, `load_item_text`, `save_item`

- `detect_format(path)` — returns `"yaml"` or `"legacy_md"` based on file suffix; raises `ValueError` for unsupported extensions
- `load_item(path)` — reads `BacklogItem` from `.yaml` or `.md` file; `.md` emits `DeprecationWarning`
- `load_item_text(text, path)` — parses `BacklogItem` from in-memory string; format determined by `path` suffix; file need not exist on disk
- `save_item(item, path)` — serialises `BacklogItem` to YAML; excludes `file_path` and `skip`; line-wrapping disabled

**Key behaviours**:
- Uses `ruamel.yaml` (typ="safe" for reads, typ="rt" for writes); no `python-frontmatter` dependency
- `.md` load path delegates to `parsing.parse_item_file()` and emits `DeprecationWarning`

**Imports from other modules**: `from .models import BacklogItem`, `from .parsing import parse_item_file`

---

## Module: github_sync.py

**Responsibility**: Bidirectional conversion between `BacklogItem` and GitHub issue body markdown.
Operations layer never writes raw markdown body strings directly — they go through this adapter.

**Public API** (`__all__`): `render_issue_body`, `parse_issue_body`, `merge_item`, `SECTION_HEADING`, `heading_to_section_key`, `heading_to_unknown_key`, `unknown_key_to_heading`

- `render_issue_body(item)` — serialises `BacklogItem` to GitHub markdown; embeds metadata in an
  invisible `<!-- backlog-metadata: -->` HTML comment; renders description, entry-bearing sections,
  and groomed section in canonical order
- `parse_issue_body(body, existing)` — reconstructs `BacklogItem` from issue body text; extracts
  metadata comment for priority/type/status/added; maps `## Section` headings to typed section
  models; non-body fields are carried over from `existing` when provided
- `merge_item(local, remote)` — merges remote into local; local metadata is authoritative; sections
  are merged per-entry (struck state wins over active; longer content wins on tie; unique entries
  from either side are preserved)
- `SECTION_HEADING` — dict mapping section storage keys to GitHub markdown heading text (e.g. `"fact_check"` → `"Fact-Check"`)
- `heading_to_section_key(heading_text)` — maps a `## Heading` text to its section storage key; returns `None` for unknown headings
- `heading_to_unknown_key(heading_text)` — converts an unknown heading to an `"unknown__"` prefixed storage key
- `unknown_key_to_heading(key)` — reverses `heading_to_unknown_key`; strips prefix, title-cases result

**Known section keys** (BacklogItem.sections):
- `"fact_check"` → `## Fact-Check`
- `"rt_ica"` → `## RT-ICA`
- `"issue_classification"` → `## Issue Classification`
- `"groomed"` → `## Groomed (date)` (GroomedData type, not Section)

**Dependency direction**: `models ← parsing ← entry_blocks ← github_sync` (must remain acyclic;
do not import from `gh_client.py`, `operations.py`, or `server.py`)

**Imports from other modules**: `from .entry_blocks import parse_entries`,
`from .models import BacklogItem, Entry, GroomedData, Section`,
`from .parsing import extract_sections`

---

## Module: rendering.py

**Responsibility**: Backend-neutral shared rendering utilities for backlog sections. Extracts rendering logic from `github_sync` into a location all three `BacklogBackend` implementations (GitHub, SQLite, memory) can import, ensuring identical section rendering across backends.

**Dependency direction**: `models ← rendering` (must remain acyclic; do not import from `github_sync`, `operations`, `gh_client`, or `server`)

**Public API** (`__all__`): `GROOMED_SUBSECTION_ORDER`, `SECTION_HEADING`, `render_groomed_section`, `section_display_title`, `unknown_key_to_heading`

- `SECTION_HEADING` — dict mapping known section storage keys to display heading text (e.g. `"fact_check"` → `"Fact-Check"`); shared constant used by all backends
- `GROOMED_SUBSECTION_ORDER` — canonical render order for `GroomedData` subsections (heading text as stored)
- `render_groomed_section(groomed)` — renders a `GroomedData` as `## Groomed ({date})` with `### subsection` children in canonical order; extras appended alphabetically
- `section_display_title(key, groomed_date)` — returns the human-readable title for a section storage key; handles known keys via `SECTION_HEADING`, `"unknown__"` prefix via `unknown_key_to_heading`, and the special `"groomed"` key with optional date
- `unknown_key_to_heading(key)` — strips `"unknown__"` prefix, replaces underscores with spaces, and title-cases the result

**Imports from other modules**: `from .models import GroomedData` (type annotation only, under `TYPE_CHECKING`)

---

## Module: gh_client.py

**Responsibility**: GitHub API connection, issue CRUD, status/label management, view enrichment.

**Functions extracted from backlog.py**:

- Connection: `_get_github()` → `get_github()`, `_try_get_github()` → `try_get_github()`
- Issue CRUD: `create_issue_for_item()`, `_close_github_issue()` → `close_github_issue()`, `_resolve_github_issue()` → `resolve_github_issue()`
- PR check: `_check_open_prs_for_issue()` → `check_open_prs_for_issue()`
- Status: `_batch_fetch_statuses()` → `batch_fetch_statuses()`, `_fetch_item_status()` → `fetch_item_status()`, `_apply_status_in_progress()` → `apply_status_in_progress()`
- Issue queries: `_fetch_open_issues_by_title()` → `fetch_open_issues_by_title()`
- View enrichment: `_view_enrich_from_github()` → `view_enrich_from_github()`
- Issue data: `_issue_to_local_fields()` → `issue_to_local_fields()`
- Groomed sync: `_sync_groomed_to_github_issue()` → `sync_groomed_to_github_issue()`
- Fetch: `_fetch_github_issue_body()` → `fetch_github_issue_body()`

**Exports**: All functions listed above.

**Imports from other modules**:
- `from .models import ...` (constants, Output, exceptions)
- `from .parsing import ...` (build_issue_body, infer_type, normalize_issue_title, etc.)

---

## Module: backend_protocol.py

**Responsibility**: Defines the `BacklogBackend` Protocol and `BacklogConfig` dataclass. Provides `create_backend()` factory and `get_config()` / `set_config()` / `reset_config()` module-level accessors. Decouples all operations and server code from any specific storage platform.

**Public API** (`__all__`): `BacklogBackend`, `BacklogConfig`, `IssueCommentNode`, `IssueNode`, `MilestoneFullNode`, `create_backend`, `get_config`, `reset_config`

- `BacklogBackend` — `@runtime_checkable` Protocol defining the full backend contract. Method groups: repository access, GraphQL utilities, issue CRUD, issue comments, status mutations, milestones/projects, task issues, sync/serialisation (including rendering methods), and integration branches.
- `BacklogConfig` — dataclass wrapping the active `BacklogBackend` instance; passed by dependency injection to `operations.py` and `server.py`.
- `create_backend(name)` — factory that instantiates the backend by name (`"github"`, `"sqlite"`, `"memory"`). Resolution order: explicit name → `BACKLOG_BACKEND` env var → `[backend] name` in `backend.toml` → default `"github"`.
- `get_config()` — returns the module-level `BacklogConfig` singleton, auto-initialising on first call.

**Rendering utilities via protocol dispatch**: Rendering methods (`section_heading`, `render_groomed_section`, `section_display_title`) are part of the `BacklogBackend` Protocol surface. Callers access rendering through the active backend rather than importing directly from `github_sync`. Shared rendering logic lives in `rendering.py` and is used by all backend implementations.

**Imports from other modules**: `from .models import ...` (type annotations only, under `TYPE_CHECKING`). Does NOT import from `gh_client`, `github_sync`, or `github_branches` — those are implementation details of the GitHub backend.

---

## Backends: backends/

**Responsibility**: Platform-specific implementations of `BacklogBackend`.

- `backends/github_backend.py` — `GitHubBackend`: delegates to `gh_client.py`, `github_sync.py`, `github_branches.py`. Requires `GITHUB_TOKEN`. Default backend.
- `backends/sqlite_backend.py` — `SQLiteBackend`: local 6-table SQLite schema, WAL mode. No external credentials.
- `backends/memory_backend.py` — `InMemoryBackend`: in-memory test double. No persistence.

Each backend imports from `backend_protocol` (for TypedDicts and config) and `models`. Backend selection is resolved at startup via `create_backend()`; consumers access the active backend through `get_config().backend`.

---

## Module: operations.py

**Responsibility**: High-level CRUD operations that combine parsing, GitHub, and file I/O. Each public function returns a dict or list and takes an optional `output: Output` parameter.

**Functions extracted/refactored from backlog.py**:

- File metadata: `_update_item_metadata()` → `update_item_metadata()`
- ADD: `_add_item_index_format()` → part of `add_item()`; duplicate check logic from `add` command
- LIST: logic from `list_items` command → `list_items()`; `_refresh_local_cache_from_github()` → `refresh_local_cache_from_github()`
- VIEW: logic from `view` command → `view_item()`
- SYNC: `_sync_create_missing_issues()` → `sync_create_missing_issues()`, `_sync_push_groomed_content()` → `sync_push_groomed_content()`, combined `sync_items()`; `_find_or_create_issue()` → `find_or_create_issue()`
- CLOSE: `_close_item_index()`, `_close_cleanup()` → part of `close_item()`
- RESOLVE: `_resolve_item_index()` → part of `resolve_item()`
- UPDATE: refactored `update` command → `update_item()`; `_apply_plan_to_item()`, `_create_issue_and_update_item()`, `_handle_update_groomed()`, `_ensure_github_issue()`, `_write_groomed_to_github()`, `_write_groomed_to_item_file()`, `_resolve_groomed_content()`
- GROOM: `groom` command → `groom_item()`
- NORMALIZE: `normalize` command → `normalize_items()`; `_build_normalized_content()`, `_normalize_item_file()`
- PULL: `pull` command → `pull_items()`; `_pull_single_issue()` → `pull_single_issue()`, `_pull_item()`, `_pull_item_create_new()`, `_pull_item_update_existing()`, `_overwrite_body_from_github()`

**Exports**: `add_item`, `list_items`, `view_item`, `sync_items`, `close_item`, `resolve_item`, `update_item`, `groom_item`, `normalize_items`, `pull_items`, `update_item_metadata`, `pull_single_issue`, `refresh_local_cache_from_github`, `sync_create_missing_issues`, `sync_push_groomed_content`

**Imports from other modules**:
- `from .models import ...`
- `from .parsing import ...`
- `from .gh_client import ...`
- `from .yaml_io import ...`

---

## Module: server.py

**Responsibility**: FastMCP 3.x server exposing all operations as MCP tools.

**Pattern**: Each CLI subcommand becomes a `@mcp.tool()` decorated function that calls the corresponding operation and returns a dict.

**Tools** (14 total):

*Backlog management (10):*

1. `backlog_add` — calls `operations.add_item()`
2. `backlog_list` — calls `operations.list_items()`
3. `backlog_view` — calls `operations.view_item()`
4. `backlog_sync` — calls `operations.sync_items()`
5. `backlog_close` — calls `operations.close_item()`
6. `backlog_resolve` — calls `operations.resolve_item()`
7. `backlog_update` — calls `operations.update_item()`
8. `backlog_groom` — calls `operations.groom_item()`
9. `backlog_normalize` — calls `operations.normalize_items()`
10. `backlog_pull` — calls `operations.pull_items()`

*Dispatch orchestration (4):*

11. `dispatch_wave_start(milestone, wave_num, items)` — creates a wave entry with item records; initialises all items with `status=pending`; returns error if wave already exists
12. `dispatch_item_status(milestone, issue, status, result, error, cost)` — records completion or failure of a single dispatch item; looks up item by milestone+issue across all waves; valid status values: `complete`, `failed`, `skipped`
13. `dispatch_wave_status(milestone, wave_num)` — queries current wave status with per-item detail; checks stale PIDs (marks dead processes failed) before returning
14. `dispatch_spawn(milestone, wave_num, ...)` — background task (`@mcp.tool(task=True)`) that spawns parallel kage-bunshin sessions for a wave; calls `dispatch_wave_start` then launches one `claude -p` process per item

**Key patterns**:
- Use `Annotated[type, Field(...)]` for parameter validation
- Catch `BacklogError` subclasses and convert to structured error responses
- Return dicts with result data + output messages
- Dispatch tools wrap `dispatch_state.DispatchStateManager` via `asyncio.to_thread()`
- Use `if __name__ == "__main__": mcp.run()` for STDIO transport

**Imports**: `from fastmcp import FastMCP`, `from .models import ...`, `from .operations import ...`, `from .dispatch_state import DispatchStateManager`

---

## Module: dispatch_state.py

**Responsibility**: SQLite-backed state persistence for dispatch orchestration. Standalone — no MCP or FastMCP imports.

**Class**: `DispatchStateManager(db_path)`

- `ensure_schema()` — creates `waves` and `items` tables if absent; idempotent
- `create_wave(milestone, wave_num, items)` → `DispatchWaveRecord` — inserts wave row and all item rows; raises `sqlite3.IntegrityError` if wave already exists
- `get_wave(milestone, wave_num)` → `DispatchWaveRecord | None`
- `get_all_waves(milestone)` → `list[DispatchWaveRecord]`
- `set_item_in_progress(milestone, wave_num, issue, pid)` — marks item in-progress, records PID
- `set_item_complete(milestone, wave_num, issue, result, cost)` — marks item complete; triggers wave completion check
- `set_item_failed(milestone, wave_num, issue, error)` — marks item failed; triggers wave completion check
- `get_item(milestone, wave_num, issue)` → `DispatchItemRecord | None`
- `get_wave_items(milestone, wave_num)` → `list[DispatchItemRecord]`
- `check_stale_pids()` → `list[DispatchItemRecord]` — probes each in-progress PID with `os.kill(pid, 0)`; marks dead items failed; returns newly failed items

**Storage**: SQLite at `~/.dh/projects/{project-slug}/dispatch-state.db`. `server.py` initialises the path; `dispatch_state.py` does not resolve it.

**Imports from other modules**: `from .models import DispatchItemRecord, DispatchWaveRecord`

---

## Lifespan Bootstrap

At server startup, `server.py` auto-bootstraps the [beads](https://github.com/beads-dev/beads) toolchain so every user gets the `bd` binary, `.beads/` project database, and Claude PreCompact/SessionStart hooks without manual setup.

### How It Wires In

The FastMCP constructor receives a `lifespan=_beads_lifespan` parameter (see `server.py`, `FastMCP(...)` call). FastMCP invokes this hook once per server startup (or once per `Client(mcp)` context manager entry in tests). The hook runs `_bootstrap_beads()` in a thread executor before yielding to accept tool calls:

```text
FastMCP startup → _beads_lifespan → asyncio.run_in_executor(_bootstrap_beads) → yield → tools available
```

The `@lifespan` decorator is imported from `fastmcp.server.lifespan`.

### Sentinel Pattern

A module-level `_beads_bootstrapped: bool = False` sentinel prevents repeated execution. The sentinel is checked at the top of `_bootstrap_beads()` and set to `True` on every exit path (including degradation paths). This matters because tests open multiple `Client(mcp)` connections — without the sentinel, bootstrap would run on every connection.

Tests reset the sentinel via `monkeypatch.setattr("backlog_core.server._beads_bootstrapped", False)`.

### Bootstrap Decision Tree

```mermaid
flowchart TD
    Start([_bootstrap_beads called]) --> S{_beads_bootstrapped?}
    S -->|True| Skip([return immediately])
    S -->|False| BD{shutil.which bd?}
    BD -->|found| HasBeads{.beads/ exists?}
    HasBeads -->|No| InitHappy[bd init --stealth --quiet]
    HasBeads -->|Yes| Setup
    InitHappy --> Setup[bd setup claude --project --stealth]
    Setup --> SetTrue1([_beads_bootstrapped = True])
    BD -->|not found| NPM{shutil.which npm?}
    NPM -->|not found| WarnNPM[log warning: npm not available]
    WarnNPM --> SetTrue2([_beads_bootstrapped = True])
    NPM -->|found| Install[npm install -g @beads/bd]
    Install --> BDAgain{shutil.which bd?}
    BDAgain -->|not found| WarnFail[log warning: npm install failed silently]
    WarnFail --> SetTrue3([_beads_bootstrapped = True])
    BDAgain -->|found| InitInstall[bd init --stealth --quiet]
    InitInstall --> SetupInstall[bd setup claude --project --stealth]
    SetupInstall --> SetTrue4([_beads_bootstrapped = True])
```

### Execution Paths

| Path | Condition | Actions |
|------|-----------|---------|
| Happy (bd present, `.beads/` exists) | `bd` on PATH, `.beads/` directory exists | `bd setup claude --project --stealth` |
| Happy (bd present, no `.beads/`) | `bd` on PATH, `.beads/` missing | `bd init --stealth --quiet`, then `bd setup claude --project --stealth` |
| Install | `bd` absent, `npm` present | `npm install -g @beads/bd`, `bd init`, `bd setup` |
| Degraded — npm absent | `bd` absent, `npm` absent | Warning logged, returns |
| Degraded — install failed | `bd` absent, `npm` present but install silent-failed | Warning logged, returns |

### Subprocess Call Contracts

All subprocess calls in `_bootstrap_beads()` follow these rules:

- `check=False` — non-zero exits do not raise exceptions; the next `shutil.which()` check determines outcome
- `capture_output=True` — suppresses stdout/stderr from subprocess; prevents MCP transport pollution
- `cwd=project_dir` — set on all `bd` commands; absent on `npm install` (npm installs globally)
- Command as list (never `shell=True`) — prevents shell injection

### Project Directory Source

Bootstrap receives the project root from `models.get_repo_root()`, which returns the path set during `_init_models()` at module import time. The sequence is: `sys.argv` → `_parse_args()` → `_init_models(project_dir)` → `models._REPO_ROOT` → `models.get_repo_root()` → `_bootstrap_beads(project_dir)`.

---

## CLI wrapper: backlog.py (rewritten)

**Responsibility**: Thin Typer CLI that imports from `operations` module.

**Pattern**: Each `@app.command()` function:
1. Creates `Output()` instance
2. Calls the corresponding `operations.*()` function
3. Prints `output.messages` and `output.warnings`
4. Catches exceptions and converts to `typer.Exit(1)`

**Keeps**: Rich table formatting for `list` command, text formatting for `view` command.
These are CLI-specific display concerns that don't belong in core logic.

**Imports**: `from .operations import ...`, `from .models import ...`
