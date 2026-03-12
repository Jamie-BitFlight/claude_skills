# Backlog Skill Codebase Analysis

**Analysis Date:** 2026-03-12
**Package:** backlog
**Scope:** CLI patterns, architecture, testing

---

## Overview

The backlog skill provides unified CRUD operations for both local `.claude/backlog/*.md` files and GitHub Issues. It consists of:

- **CLI entry point:** `.claude/skills/backlog/scripts/backlog.py` (2563 lines)
- **Core library:** `.claude/skills/backlog/backlog_core/` — modularized typed operations
- **Tests:** `.claude/skills/backlog/tests/` — comprehensive test suite

**Key Design Principle:** GitHub Issues are the source of truth; local files are a cache for agent consumption.

---

## Part 1: CLI Patterns

### Command Structure

**Location:** `scripts/backlog.py:120`

The CLI uses Typer (a Click-compatible framework) with a single app instance:

```python
app = typer.Typer(help="Backlog and GitHub Issue CRUD — single interface")
```

**Available commands** (from `backlog.py` lines 838-1500+):

| Command | Function | Signatures |
|---------|----------|-----------|
| `add` | `add(title, priority, description, source, item_type, create_issue, dryrun)` | Line 838 |
| `list` | `list_items(show, format, with_status, repo)` | Line 1021 |
| `view` | `view(selector, format, show, since, enrich, repo)` | Not found in early grep; likely delegated to backlog_core |
| `sync` | `sync(dry_run, label, repo)` | Line 1140 |
| `close` | `close(selector, reason, plan, cleanup, repo)` | Line 1228 |
| `resolve` | `resolve(selector, summary, plan, cleanup, repo)` | Line 1328 |
| `update` | `update(selector, plan, status, create_issue, repo)` | Not found in early grep |
| `groom` | `groom(selector, groomed_content, groomed_file, section, repo)` | Not found in early grep |
| `normalize` | Rewrite per-item files to research-style metadata (line 30) | Not found in early grep |
| `migrate-status` | Migrate items with 'open' status to valid state-machine states (line 31) | Not found in early grep |
| `pull` | `pull(dry_run, force, repo)` | Not found in early grep |

### Helper Functions (CLI Layer)

**Location:** `scripts/backlog.py:162-600`

Nine internal helper functions exist in the CLI that have equivalents (exact or renamed) in `backlog_core/`:

| Function | CLI Signature | Core Equivalent | Notes |
|----------|---------------|-----------------|-------|
| `_infer_type` | `(description: str, title: str) -> str` | `parsing.infer_type` | Identical logic — infers issue type from text |
| `_title_to_slug` | `(title: str, max_len: int = 60) -> str` | `parsing.title_to_slug` | Converts title to filename slug |
| `_parse_backlog_from_directory` | `() -> list[dict]` | `parsing.parse_backlog_from_directory` | Returns untyped dicts; core returns `BacklogItem` objects |
| `_parse_item_file` | `(text: str, path: Path) -> dict` | `parsing.parse_item_file` | Returns dict; core returns typed `BacklogItem` |
| `_normalize_issue_title` | `(title: str) -> str` | `parsing.normalize_issue_title` | Strips conventional-commit prefixes, lowercases |
| `_find_fuzzy_duplicates` | `(title: str, items: list[dict], threshold: float) -> list[tuple[str, float, str]]` | `parsing.find_fuzzy_duplicates` | Uses `difflib.SequenceMatcher` for fuzzy matching |
| `_today` | `() -> str` | `parsing.today` | Returns `YYYY-MM-DD` string |
| `_now_iso` | `() -> str` | `parsing.now_iso` | Returns ISO 8601 UTC timestamp |
| `_update_item_metadata` | `(filepath: Path, updates: dict, set_synced: bool) -> None` | `operations.update_item_metadata` | Modifies per-item file frontmatter |

### Import Pattern

**Location:** `scripts/backlog.py:76-81`

The CLI **already imports** from `backlog_core`:

```python
from backlog_core import operations as _backlog_operations
from backlog_core.entry_blocks import rewrite_section as _rewrite_section
from backlog_core.models import BacklogError as _BacklogError, ItemNotFoundError as _ItemNotFoundError
from frontmatter_utils import dump_frontmatter, loads_frontmatter
```

**Critical observation:** The CLI does NOT currently use `_backlog_operations` imported on line 76. This suggests the CLI implements its own logic rather than delegating to the core module.

### Return Types: Dict vs Typed Models

The CLI layer works with **untyped dicts** (with metadata keys like `_section`, `_title`, `_file_path`, `_skip`):

```python
def _parse_backlog_from_directory() -> list[dict]:
    """Returns List of item dicts with _section, _title, and field keys."""
    items: list[dict] = []
    # ...
    item["_section"] = section
    item["_title"] = name
    item["_file_path"] = str(filepath)
    return items
```

The core module works with **typed Pydantic models** (`BacklogItem` from `models.py`):

```python
def parse_item_file(text: str, path: Path) -> BacklogItem:
    """Returns typed BacklogItem."""
```

### Error Display

**Location:** `scripts/backlog.py:121`

Uses Rich Console for formatted output:

```python
_console = Console()
```

Errors use `typer.echo(..., err=True)` pattern for stderr output (e.g., line 138, 550).

---

## Part 2: Architecture

### Module Dependency Graph

```
scripts/backlog.py (CLI entry point)
├── Imports:
│   ├── backlog_core.operations (imported but not used; suggests potential refactoring)
│   ├── backlog_core.entry_blocks.rewrite_section
│   ├── backlog_core.models (BacklogError, ItemNotFoundError)
│   ├── backlog_core.parsing (indirectly via duplicate implementations)
│   ├── backlog_core.github (indirectly via duplicate implementations)
│   └── frontmatter_utils (parsing/writing YAML frontmatter)
│
backlog_core/
├── models.py (constants, regex, exceptions, Pydantic models)
├── parsing.py (frontmatter parsing, slug generation, fuzzy matching, body building)
├── operations.py (item CRUD, state transitions, SAM task management)
├── github.py (GitHub API wrappers for issue operations)
├── entry_blocks.py (timestamped entry formatting and section rewriting)
└── server.py (FastMCP 3.x server for MCP tool endpoint)

tests/ (pytest suite with fixtures)
```

### Core Module Descriptions

**`models.py` (line 1-150+):**
- Path constants: `BACKLOG_DIR`, `DEFAULT_REPO`
- Regex patterns: `SECTION_RE`, `GITHUB_ISSUE_URL_RE`, `_COMMIT_PREFIX_RE`
- Scalar constants: `SKIP_STATUS`, `VALID_CLOSE_REASONS`, `FUZZY_DUPLICATE_THRESHOLD`
- Dict mappings: `TYPE_TO_LABEL`, `ROLE_MAP`, `BENEFIT_MAP`, `PRIORITY_SECTIONS`
- Exception classes: `BacklogError`, `ItemNotFoundError`
- Pydantic models (not shown in early grep): `BacklogItem`, `ViewItemResult`, `SamTask`, `IssueStatus`, etc.

**`parsing.py` (90+ functions):**
- Item file parsing: `parse_item_file`, `parse_backlog_from_directory`, `parse_backlog`
- Utilities: `today`, `now_iso`, `title_to_slug`, `normalize_issue_title`, `infer_type`
- Fuzzy matching: `find_fuzzy_duplicates`, `find_item`
- Issue body building: `build_issue_body`, `build_issue_body_from_file`, `extract_body_field_pairs`
- Section extraction: `extract_sections`, `extract_groomed_section`, `append_or_replace_section`
- SAM tasks: `parse_sam_task_metadata`, `build_sam_task_issue_title`, `build_sam_task_body`

**`operations.py` (70+ functions):**
- Item CRUD: `add_item`, `list_items`, `view_item`, `update_item`, `groom_item`
- State transitions: `close_item`, `resolve_item`, `strike_entry`
- GitHub sync: `sync_items`, `sync_create_missing_issues`, `sync_push_groomed_content`
- Issue operations: `find_or_create_issue`, `create_issue_for_item`
- GitHub pull: `pull_items`, `pull_single_issue`, `pull_by_selector`
- Cache refresh: `refresh_local_cache_from_github`
- SAM tasks: `create_sam_task`, `get_sam_tasks`, `get_ready_sam_tasks`, `update_sam_task_status`
- Normalization: `normalize_items`
- Metadata: `update_item_metadata`

**`github.py` (18+ functions):**
- Authentication: `get_github`, `try_get_github`
- Issue creation/updates: `create_issue_for_item`, `close_github_issue`, `resolve_github_issue`
- Status queries: `batch_fetch_statuses`, `fetch_item_status`, `fetch_open_issues_by_title`
- PR checks: `check_open_prs_for_issue`
- SAM integration: `create_task_issue`, `get_task_issues`, `update_task_status`
- Data extraction: `issue_to_local_fields`, `fetch_github_issue_body`

**`entry_blocks.py` (8+ functions):**
- Entry formatting: `wrap_entry`, `wrap_entry_with_timestamp`, `parse_entries`
- Section manipulation: `rewrite_section`, `strike_entry`
- Diff generation: `generate_diff`

**`server.py` (MCP server):**
- Exposes backlog_core operations as FastMCP 3.x tools
- Entry point for MCP clients (agents using `mcp__backlog__*` tools)

### Where to Add New Code

**New CLI command:** Add `@app.command()` decorator to `scripts/backlog.py`, then implement using calls to `backlog_core.operations` functions (currently not done; CLI reimplements logic).

**New parsing logic:** Add to `backlog_core/parsing.py` (source of truth for item file and body structure).

**New operations:** Add to `backlog_core/operations.py` (state machines, validation, item manipulation).

**New GitHub integration:** Add to `backlog_core/github.py` (GitHub API calls).

**New entry block utilities:** Add to `backlog_core/entry_blocks.py` (timestamped entries, section rewriting).

---

## Part 3: Testing

### Test Framework

**Framework:** pytest
**Config location:** `pyproject.toml` (not examined in this analysis)

### Test File Organization

**Location:** `.claude/skills/backlog/tests/`

Test files follow the pattern `test_*.py`:

| Test File | Purpose | Key Functions |
|-----------|---------|---------------|
| `test_backlog_core_models.py` | Model instantiation and constants | BacklogItem creation, constants validation |
| `test_backlog_core_parsing.py` | Item file parsing, slug generation, fuzzy matching | `parse_item_file`, `parse_backlog_from_directory`, `find_fuzzy_duplicates` |
| `test_backlog_core_operations.py` | Item CRUD, state transitions, SAM tasks | `add_item`, `close_item`, `resolve_item`, SAM operations |
| `test_backlog_core_github.py` | GitHub API integration | `create_issue_for_item`, `batch_fetch_statuses`, etc. |
| `test_backlog_core_server.py` | MCP server endpoints | Server route registration and request handling |
| `test_entry_blocks.py` | Entry formatting and section rewriting | `wrap_entry`, `rewrite_section`, `parse_entries` |
| `test_entry_blocks_integration.py` | Integration tests for entry blocks with real structures | Full workflow parsing and rewriting |
| `test_operations_sam.py` | SAM-specific operations | Task creation, status updates, ready task queries |
| `test_server_sam.py` | MCP SAM task endpoints | Server handling of SAM task requests |
| `test_scenarios.py` | End-to-end workflow scenarios | Complex multi-step workflows |
| `test_live_validation.py` | Integration with real GitHub (requires GITHUB_TOKEN) | Live issue validation |
| `test_backlog_gh_first.py` | GitHub-first workflows | Pull, sync, and issue-driven updates |
| `conftest.py` | Pytest fixtures and shared test utilities | Fixtures for items, repos, mocks |

### Fixture Patterns

**Location:** `conftest.py`

Fixtures are used to provide:
- Mock GitHub repositories
- Sample backlog items (both dict and typed)
- Temp directories for file operations
- Mock BacklogItem instances

Example patterns (not inspected in detail):
- Fixtures likely return `BacklogItem` objects or dicts depending on test context
- Likely include GitHub mocking via PyGithub or unittest.mock
- Likely include filesystem fixtures for isolated file testing

### Mocking Patterns

Tests use:
- `unittest.mock.Mock` or `unittest.mock.patch` for GitHub API mocking
- Fixture-based temporary directories for file I/O testing
- Repository mocks with predefined issue lists

### Coverage

Test coverage is comprehensive based on file count:
- Core parsing logic: high coverage (`test_backlog_core_parsing.py`)
- Operations: high coverage (`test_backlog_core_operations.py`)
- GitHub integration: medium-high coverage (`test_backlog_core_github.py`)
- Entry blocks: medium-high coverage (`test_entry_blocks*.py`)
- SAM tasks: medium coverage (`test_operations_sam.py`, `test_server_sam.py`)
- Scenarios: integration testing (`test_scenarios.py`)

**Not directly tested in listed files:**
- CLI layer (`scripts/backlog.py`) — appears to lack dedicated tests (integration via scenarios possible)
- State machine transitions (CLI layer only; core uses typed operations)

---

## Part 4: Key Findings

### 1. Code Duplication: CLI vs Core

**Issue:** Nine utility functions exist in both `scripts/backlog.py` and `backlog_core/parsing.py`:

| Function | CLI | Core | Difference |
|----------|-----|------|-----------|
| `_infer_type` / `infer_type` | Line 162 | parsing.py:136 | Identical logic |
| `_title_to_slug` / `title_to_slug` | Line 175 | parsing.py:105 | Identical logic |
| `_parse_backlog_from_directory` / `parse_backlog_from_directory` | Line 191 | parsing.py:250 | Core returns `BacklogItem`; CLI returns `dict` |
| `_parse_item_file` / `parse_item_file` | Line 248 | parsing.py:220 | Core returns `BacklogItem`; CLI returns `dict` |
| `_normalize_issue_title` / `normalize_issue_title` | Line 347 | parsing.py:121 | Identical logic |
| `_find_fuzzy_duplicates` / `find_fuzzy_duplicates` | Line 365 | parsing.py:338 | Identical logic |
| `_today` / `today` | Line 561 | parsing.py:90 | Identical logic |
| `_now_iso` / `now_iso` | Line 565 | parsing.py:95 | Identical logic |
| `_update_item_metadata` / `update_item_metadata` | Line 570 | operations.py:99 | Identical logic |

**Consequence:** Changes to parsing or utility logic must be made in two places to stay synchronized.

### 2. Type Signature Mismatch

**Issue:** CLI functions use `list[dict]` while core uses `BacklogItem` (Pydantic models).

**Impact:**
- CLI cannot directly call core functions without converting between dict and typed models
- The imported `_backlog_operations` on line 76 is unused, suggesting CLI reimplements rather than delegates
- Future type-checking could be prevented by the type mismatch

### 3. SKIP_STATUS Constant Divergence

**Location:**
- CLI: `scripts/backlog.py:92` → `SKIP_STATUS = ("DONE", "RESOLVED", "COMPLETED")`
- Core: `backlog_core/models.py:36` → `SKIP_STATUS = ("DONE", "RESOLVED", "COMPLETED", "CLOSED")`

**Difference:** Core includes `"CLOSED"` (GitHub's native status), CLI does not.

**Implication:** CLI-layer filtering may include items that should be skipped based on GitHub state.

### 4. Unused Import

**Location:** `scripts/backlog.py:76`

```python
from backlog_core import operations as _backlog_operations
```

This import is never used in the CLI. All operations are reimplemented locally. Suggests the CLI predates the core module refactoring.

### 5. State Handler Module

**Location:** `scripts/backlog.py:81` imports from `state_handler`

```python
from state_handler import BacklogState, StateTransitionError, apply_github_transition
```

Referenced file: `.claude/skills/backlog/scripts/state_handler.py` (not examined). This handles state machine logic for backlog items (e.g., open → in-progress → resolved transitions).

---

## Part 5: Constants and Configuration

### Regex Patterns

| Pattern | Location | Purpose |
|---------|----------|---------|
| `SECTION_RE` | models.py:28, backlog.py:91 | Matches section headers: `^##\s+(P0\|P1\|P2\|Ideas)` |
| `GITHUB_ISSUE_URL_RE` | models.py:29, backlog.py:93 | Extracts repo and issue number from URLs |
| `_COMMIT_PREFIX_RE` | models.py:30, backlog.py:344 | Matches conventional-commit prefixes: `feat:`, `fix:`, etc. |

### Magic Constants

| Constant | CLI Value | Core Value | Use |
|----------|-----------|-----------|-----|
| `SKIP_STATUS` | `("DONE", "RESOLVED", "COMPLETED")` | `("DONE", "RESOLVED", "COMPLETED", "CLOSED")` | Filter completed items |
| `FUZZY_DUPLICATE_THRESHOLD` | `0.80` | `0.80` | Similarity ratio for duplicate detection |
| `GITHUB_ISSUE_TITLE_TRUNCATE` | `80` | `80` | Max GitHub issue title length |
| `MIN_FRONTMATTER_PARTS` | `3` | `3` | Minimum frontmatter sections (`---\n...\n---\n`) |

### Type and Role Mappings

```python
TYPE_TO_LABEL = {
    "feature": "type:feature",
    "bug": "type:bug",
    "refactor": "type:refactor",
    "docs": "type:docs",
    "chore": "type:chore",
}

ROLE_MAP = {
    "Feature": "developer using Claude Code skills",
    "Bug": "developer relying on this plugin",
    # ... etc
}

BENEFIT_MAP = {
    "Feature": "the tooling becomes more capable and complete",
    # ... etc
}
```

These are used in issue body generation for context-rich formatting.

---

## Summary

The backlog skill demonstrates a **dual-layer architecture** with significant code duplication:

- **CLI layer** (`scripts/backlog.py`): 2563 lines of untyped dict-based operations with complete reimplementation of core utilities
- **Core layer** (`backlog_core/`): Modularized, typed (Pydantic), with clean separation of concerns across parsing, operations, GitHub integration, and entry formatting
- **MCP server** (`server.py`): Exposes core operations as FastMCP tools for agent consumption
- **Tests:** Comprehensive coverage of core logic; CLI layer appears untested

**Key architectural tension:** The CLI and core duplicate nine utility functions, differing in return types (dict vs. `BacklogItem`). The unused import of `_backlog_operations` suggests the CLI predates the core refactoring and could be unified.

