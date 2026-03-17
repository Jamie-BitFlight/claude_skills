# Backlog State Reconciliation: Architecture & Patterns

**Analysis Date:** 2026-03-14
**Focus:** State machine patterns, local cache management, GitHub synchronization, error handling
**Key Files Analyzed:**
- `.claude/skills/backlog/scripts/backlog.py` (CLI tool, 2100+ lines)
- `.claude/skills/backlog/scripts/state_handler.py` (state machine, 180 lines)
- `.claude/skills/backlog/backlog_core/operations.py` (high-level operations)
- `.claude/skills/backlog/backlog_core/github.py` (GitHub API wrapper)
- `.claude/skills/backlog/references/state-machine.md` (state machine spec)
- Test infrastructure (16 test files)

---

## 1. State Machine Implementation

### 1.1 State Definitions

**Location:** `state_handler.py:39-49`

```python
class BacklogState(StrEnum):
    NEEDS_GROOMING = "needs-grooming"
    GROOMED = "groomed"
    BLOCKED = "blocked"
    IN_MILESTONE = "in-milestone"
    IN_PROGRESS = "in-progress"
    DONE = "done"
    RESOLVED = "resolved"
    CLOSED = "closed"
```

Eight canonical states form a directed acyclic graph (DAG). Terminal state: `CLOSED`.

### 1.2 Transition Validation DAG

**Location:** `state_handler.py:54-63`

Valid transitions are statically defined as a dict[BacklogState, frozenset[BacklogState]]:

```python
VALID_TRANSITIONS = {
    BacklogState.NEEDS_GROOMING: frozenset({BacklogState.GROOMED, BacklogState.BLOCKED, BacklogState.RESOLVED}),
    BacklogState.GROOMED: frozenset({BacklogState.IN_MILESTONE, BacklogState.RESOLVED}),
    BacklogState.BLOCKED: frozenset({BacklogState.NEEDS_GROOMING, BacklogState.RESOLVED}),
    BacklogState.IN_MILESTONE: frozenset({BacklogState.IN_PROGRESS, BacklogState.GROOMED, BacklogState.RESOLVED}),
    BacklogState.IN_PROGRESS: frozenset({BacklogState.DONE, BacklogState.RESOLVED, BacklogState.BLOCKED}),
    BacklogState.DONE: frozenset({BacklogState.CLOSED}),
    BacklogState.RESOLVED: frozenset({BacklogState.CLOSED}),
    BacklogState.CLOSED: frozenset(),  # terminal
}
```

**Function:** `state_handler.py:83-116` — `validate_transition(from_state, to_state)`
- Pure function (no I/O)
- Raises `StateTransitionError` if invalid
- Called by higher-level operations before applying transitions

### 1.3 State Persistence Dimension

**Dimension 1: Local Frontmatter**
- Location: `.claude/backlog/*.md` files, `metadata.status` field
- Persisted by: `_update_item_metadata(filepath, {"metadata": {"status": new_state}})` — `backlog.py:91`
- Format: YAML frontmatter string, e.g., `status: in-progress`

**Dimension 2: GitHub Labels**
- Location: GitHub Issue labels, prefix `status:`
- Format: `status:needs-grooming`, `status:groomed`, etc.
- Created automatically by `_ensure_label_exists()` — `state_handler.py:119-135`
- Color palette defined at `state_handler.py:67-76` (used when auto-creating missing labels)

**Dimension 3: GitHub Native Issue State**
- Location: GitHub API `Issue.state` field (not managed by state_handler.py)
- Values: `open` or `closed` (GitHub native, orthogonal to backlog status)
- Mutated separately from state machine transitions (see Section 2.6)

---

## 2. State Transition Implementation Patterns

### 2.1 The Central Transition Function

**Location:** `state_handler.py:138-177` — `apply_github_transition(repo, issue, from_state, to_state)`

This function is the **canonical way to apply state transitions to GitHub issues.**

**Behavior:**
1. **Remove old label:** If `from_state` is None, removes ALL `status:*` labels. Otherwise, removes `status:{from_state}` (if present).
2. **Add new label:** Creates the `status:{to_state}` label if it doesn't exist, then adds it to the issue.
3. **Atomic:** Both operations complete in a single call.

**Error Handling:**
- Catches `GithubException` and re-raises as `StateTransitionError` with context.

**Callers:**
- `_apply_status_in_progress()` — `backlog.py:1624-1633`
- `_close_github_issue()` — `backlog.py:1074-1077`
- `_resolve_github_issue()` — `backlog.py:1306`

### 2.2 Pattern: GitHub First with Local Fallback

**Location:** `backlog.py:129-154` — `_get_github()` vs. `_try_get_github()`

**Two paths to GitHub:**

1. **`_get_github(repo)` — fails hard**
   - Requires `GITHUB_TOKEN` environment variable
   - Raises `typer.Exit(1)` if token missing
   - Used for operations that cannot proceed offline

2. **`_try_get_github(repo)` — soft failure**
   - Returns `None` if token missing or GitHub API unavailable
   - Timeout: 10 seconds (prevents blocking async MCP event loop)
   - Used for optional/enrichment operations (fetching status labels, checking for PRs)

**Pattern Impact:**
- State-changing operations use `_get_github()` (must succeed)
- State-reading operations use `_try_get_github()` (can fall back to local)

### 2.3 Pattern: Update Local Frontmatter Via `_update_item_metadata()`

**Location:** `backlog_core/operations.py:100-134` — `update_item_metadata(filepath, updates, set_synced)`

Unified function for all local frontmatter updates:

```python
def update_item_metadata(
    filepath: Path,
    updates: dict[str, str | dict[str, str]],
    set_synced: bool = False,
    output: Output | None = None
) -> dict:
    """Update per-item file frontmatter. Supports nested metadata.plan, metadata.issue, etc.

    When set_synced=True, also sets metadata.last_synced to current UTC time.
    """
    post = loads_frontmatter(filepath.read_text(encoding="utf-8"))
    meta = post.metadata or {}
    for key, value in updates.items():
        if key == "metadata" and isinstance(value, dict):
            # Merge nested dict
            nested_dict = {...}
            nested_dict.update(value)
            if set_synced:
                nested_dict["last_synced"] = now_iso()
            meta["metadata"] = nested_dict
        else:
            meta[key] = value
    post.metadata = meta
    filepath.write_text(dump_frontmatter(post), encoding="utf-8")
    return {"filepath": str(filepath), "updated": True, **out.to_dict()}
```

**Key Callers:**
- `backlog.py:479` — Update issue ref after GitHub issue creation
- `backlog.py:532-545` — Update priority, type, status after pulling from GitHub
- `backlog.py:1058` — Update local status to `closed` when dismissing
- `backlog.py:1163` — Update status during resolve
- `backlog.py:1651` — Update plan field during work-backlog-item

**Pattern:**
- All calls pass `metadata: {...}` dict with one or more fields
- `set_synced=True` added when operation succeeds and should record synchronization time

### 2.4 Pattern: Atomic Transition = GitHub Label + Local Frontmatter

**Correctly Implemented (Last 4 Transitions):**

1. **`in-milestone` → `in-progress`** — `backlog.py:1624-1633`
   ```python
   def _apply_status_in_progress(item: dict, repo: str) -> None:
       repository = _get_github(repo)
       issue = repository.get_issue(int(num))
       current_status = next(...)  # Get existing status label
       apply_github_transition(repository, issue, current_status, BacklogState.IN_PROGRESS.value)
       # TODO: verify local frontmatter update
   ```

2. **`in-progress` → `done`** — `backlog.py:1188-1208`
   ```python
   apply_github_transition(repository, issue, current_status, BacklogState.DONE.value)
   _update_item_metadata(filepath, {"metadata": {"status": BacklogState.DONE.value}})
   ```

3. **`in-progress` → `resolved`** — `backlog.py:1306-1310`
   ```python
   apply_github_transition(repository, issue, current_status, BacklogState.RESOLVED.value)
   _update_item_metadata(filepath, {"metadata": {"status": BacklogState.RESOLVED.value}})
   ```

4. **`done`/`resolved` → `closed`** — `backlog.py:1074-1077`
   ```python
   apply_github_transition(repository, issue, current_status, BacklogState.CLOSED.value)
   ```

**Broken Transitions (Early Stages):**

1. **Creation** — `backlog.py:683-684`
   - Sets local `status: open` (NOT in state machine)
   - GitHub issue created with label `status:needs-grooming`
   - **Mismatch:** Local says `open`, GitHub says `needs-grooming`

2. **`needs-grooming` → `groomed`** — `backlog.py:1746-1747`
   - Removes `status:needs-grooming` label
   - **MISSING:** Does NOT add `status:groomed` label
   - **MISSING:** Does NOT update local frontmatter `status` field
   - Result: Item enters "stateless void"

---

## 3. Local Cache Management

### 3.1 Parsing Local Cache

**Location:** `backlog.py:234-298`

```python
def parse_backlog() -> list[dict]:
    """Parse backlog items from .claude/backlog/ per-item files."""
    return _parse_backlog_from_directory()

def _parse_backlog_from_directory() -> list[dict]:
    """Parse and enrich items from local cache files."""
    if not BACKLOG_DIR.exists():
        return []

    prefix_to_section = {
        "p0-": "P0",
        "p1-": "P1",
        "p2-": "P2",
        "idea-": "Ideas",
        # ...
    }
    items = []
    for filepath in sorted(BACKLOG_DIR.glob("*.md")):
        name = filepath.stem
        # Infer section from filename prefix
        section = ""
        for prefix, sec in prefix_to_section.items():
            if name.startswith(prefix):
                section = sec
                break
        # Parse file → BacklogItem
        item = _parse_item_file_core(item_text, filepath)
        # Override section if metadata.priority is set
        meta_priority = item.priority
        if meta_priority and meta_priority.upper() in {"P0", "P1", "P2"}:
            section = meta_priority.upper()
        # Convert to display dict
        items.append(backlog_item_to_display_dict(item))
    return items
```

**Key Adapter:** `backlog_item_to_display_dict(item: BacklogItem) -> dict`
- **Location:** `backlog.py:190-231`
- Converts typed `BacklogItem` from `backlog_core` to dict with underscore-prefixed keys
- Maps: `item.status` → `d["_status"]` (conditional — only present if non-empty)
- Maps: Bold metadata keys → `d["**Description**"]`, `d["**Priority**"]`, etc.

**Inverse Adapter:** `_dict_to_backlog_item_fields(d: dict) -> dict`
- **Location:** `backlog.py:156-187`
- Converts CLI display dict back to BacklogItem field kwargs
- Used when CLI operations need to call core functions

### 3.2 GitHub-First Refresh Pattern

**Location:** `backlog.py:860-886` — `_refresh_local_cache_from_github(repo, label=None)`

**Two-step process:**

1. **Fetch from GitHub**
   ```python
   issues = repo_obj.get_issues(state="open", labels=label_objs or GithubObject.NotSet)
   ```
   **Critical limitation:** Only fetches `state="open"` issues. Closed issues are ignored.

2. **Update or Create Local Files**
   ```python
   for issue in issues:
       if issue.pull_request is not None:
           continue
       _pull_single_issue(repo_obj, issue.number)  # Write/update cache file
   ```

   Each call to `_pull_single_issue()` — `backlog.py:504-563`:
   - Fetches GitHub issue via PyGithub
   - Extracts fields: title, body, priority, type, status, milestone
   - **If file exists:** Updates description, status, last_synced timestamp, body sections
   - **If file missing:** Creates new cache file with frontmatter + body

**Pattern Impact:**
- Closed issues are **never refreshed** when `--from-github` is used
- Local cache files persist even after GitHub issues are closed
- Next time `backlog list` is called, stale closed items appear in the list

### 3.3 Staleness Detection Pattern

**Location:** `backlog.py:601-622` — `_check_item_staleness(item, repo) -> bool`

Compare `_last_synced` timestamp in local frontmatter against `Issue.updated_at` on GitHub:

```python
def _check_item_staleness(item: dict, repo: str) -> bool:
    issue_ref = item.get("_issue", "")
    last_synced = item.get("_last_synced", "")
    if not last_synced:
        return True  # No timestamp = always stale

    gh_issue = repository.get_issue(int(num))
    gh_updated = issue.updated_at.strftime("%Y-%m-%dT%H:%M:%SZ")
    return gh_updated > last_synced
```

**Used by:** View enrichment to warn users if local cache is stale relative to GitHub.

---

## 4. Status Fetching Patterns

### 4.1 Batch Fetch (Multi-Item)

**Location:** `backlog.py:755-783` — `_batch_fetch_statuses(items, repo) -> dict[int, dict[str, str]]`

Single API call to fetch status and milestone for all items:

```python
def _batch_fetch_statuses(items: list[dict], repo: str) -> dict[int, dict[str, str]]:
    repo_obj = _try_get_github(repo)
    if repo_obj is None:
        return {}  # Graceful fallback if GitHub unavailable

    # Single call: get all open issues (again, only state="open")
    all_issues = {
        issue.number: issue
        for issue in repo_obj.get_issues(state="open")
        if issue.pull_request is None
    }

    result = {}
    for item in items:
        num = int(item.get("_issue", "").lstrip("#"))
        if num in all_issues:
            gh_issue = all_issues[num]
            status_labels = [lbl.name for lbl in gh_issue.labels if lbl.name.startswith("status:")]
            result[num] = {
                "status": status_labels[0] if status_labels else "",
                "milestone": gh_issue.milestone.title if gh_issue.milestone else ""
            }
    return result  # Closed issues = missing keys in result
```

**Called by:**
- `_list_items_json()` — `backlog.py:806-830` (when `--with-status` flag)
- `_list_items_table()` — `backlog.py:833-857` (when `--with-status` flag)

**Pattern Impact:**
- If an issue is closed, it does NOT appear in `repo_obj.get_issues(state="open")`
- Result dict will not have a key for that issue number
- Callers get an empty status: `info = status_map.get(num, {"status": "", "milestone": ""})`

### 4.2 Single-Item Fetch (Fallback)

**Location:** `backlog.py:786-803` — `_fetch_item_status(item, repo) -> str`

For individual item operations:

```python
def _fetch_item_status(item: dict, repo: str) -> str:
    if not item.get("_issue"):
        return ""
    try:
        gh_issue = repository.get_issue(int(num))
        labels = [lb.name for lb in gh_issue.labels if lb.name.startswith("status:")]
        return labels[0] if labels else ""
    except GithubException:
        return ""
```

Used sparingly; `_batch_fetch_statuses()` preferred for multiple items.

---

## 5. GitHub API Pattern: Create Issues

### 5.1 GH-First Creation Flow

**Location:** `backlog.py:640-701` — `_add_item_index_format()`

New items created with GitHub issue **before** writing local file:

```python
def _add_item_index_format(..., create_issue: bool, repo: str) -> None:
    # Step 1: Try to create GitHub issue FIRST
    issue_num = None
    if create_issue:
        item = {...}  # Build item dict for core function
        repository = _try_get_github(repo)
        if repository is not None:
            try:
                issue_num = create_issue_for_item(repository, item, dry_run=False)
            except GithubException as e:
                typer.echo(f"WARNING: Issue creation failed: {e}")
        else:
            typer.echo("WARNING: GitHub unavailable — creating local-only item")

    # Step 2: Build frontmatter with issue number already included
    issue_ref = f"#{issue_num}" if issue_num else ""
    fm_str = _build_backlog_frontmatter(
        title, description, source, today, priority, type_,
        "open",      # ← Status set to "open" (NOT in state machine)
        issue_ref, "", ""
    )

    # Step 3: Write local cache file (single write)
    filepath.write_text(fm_str.rstrip() + "\n\n" + body, encoding="utf-8")
    if issue_num:
        _update_item_metadata(filepath, {}, set_synced=True)
```

**Key Pattern:** Fails gracefully if GitHub unavailable (local-only item created).

**Issue Created With:**
- Labels: `status:needs-grooming`, `priority:{P0|P1|P2}`, `type:{Feature|Bug|...}`
- State: GitHub native `open`
- Body: Built from item description and metadata

### 5.2 Deduplication on Sync

**Location:** `backlog.py:929-967` — `_sync_create_missing_issues()`

Pass 1 of `backlog sync` command:

```python
def _sync_create_missing_issues(items: list[dict], repo: str, dry_run: bool) -> None:
    needed = items_needing_issues(items)  # Items without _issue field
    if not needed:
        return

    repository = _get_github(repo)

    # Fetch all open issues to prevent duplicate creation
    existing_issues = _fetch_open_issues_by_title(repository)
    # Result: {normalized_title: issue_number}

    for item in needed:
        title = item.get("_title", "")
        normalized = _normalize_issue_title(title)
        if normalized in existing_issues:
            # Link to existing issue
            existing_num = existing_issues[normalized]
            _update_item_metadata(filepath, {"metadata": {"issue": f"#{existing_num}"}})
        else:
            # Create new issue
            issue_num = create_issue_for_item(repository, item, dry_run=False)
            existing_issues[normalized] = issue_num  # Track for intra-batch dedup
            _update_item_metadata(filepath, {"metadata": {"issue": f"#{issue_num}"}})
```

**Pattern:** Normalize titles (strip conventional-commit prefixes) before comparing.

---

## 6. Test Infrastructure Patterns

### 6.1 Fixture: Backlog Directory Isolation

**Location:** `test_backlog_core_operations.py:79-94`

Autouse fixture in all tests:

```python
@pytest.fixture(autouse=True)
def _isolate_backlog_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Redirect BACKLOG_DIR in every module that uses it to tmp_path."""
    fake_dir = tmp_path / "backlog"
    fake_dir.mkdir(parents=True, exist_ok=True)

    import backlog_core.models as models
    monkeypatch.setattr(models, "BACKLOG_DIR", fake_dir)
    monkeypatch.setattr(parsing, "BACKLOG_DIR", fake_dir)
    monkeypatch.setattr(ops, "BACKLOG_DIR", fake_dir)
```

**Key:** Monkeypatches `BACKLOG_DIR` in all modules that import it.

**Why:** Prevents tests from reading/writing the real `.claude/backlog/` directory.

### 6.2 Minimal Test Item Helper

**Location:** `test_backlog_core_operations.py:34-71` — `_write_item()`

Helper to create test backlog files:

```python
_MINIMAL_FRONTMATTER = """\
---
name: {title}
description: A test item
metadata:
  priority: {priority}
  status: open
  source: test
  added: '2026-01-01'
  type: Feature
  topic: {topic}
  issue: '{issue}'
---
"""

def _write_item(
    backlog_dir: Path,
    *,
    title: str = "Test Item",
    priority: str = "P1",
    topic: str = "test-item",
    issue: str = "",
    skip: bool = False,
    extra_body: str = "",
) -> Path:
    slug = topic
    filename = f"{priority.lower()}-{slug}.md"
    filepath = backlog_dir / filename
    status = "done" if skip else "open"
    content = _MINIMAL_FRONTMATTER.format(...)
    filepath.write_text(content, encoding="utf-8")
    return filepath
```

**Pattern:** Default `status: open` (matches current creation behavior).

### 6.3 Test Coverage

**16 test files, organized by module:**
- `test_backlog_core_operations.py` — Operations API (add, list, view, close, resolve)
- `test_backlog_core_models.py` — Data models
- `test_backlog_core_parsing.py` — YAML/markdown parsing
- `test_backlog_display_dict_roundtrip.py` — CLI adapter dict conversion
- `test_operations_sam.py` — SAM task-specific operations
- `test_live_validation.py` — End-to-end lifecycle tests (16 test cases)
- `test_backlog_core_server.py` — MCP server integration

**Key Test Pattern:** Each test uses the isolated BACKLOG_DIR fixture automatically.

---

## 7. Error Handling Patterns

### 7.1 GitHub API Errors

**Caught at:** All GitHub API call sites
- Pattern: `try: ... except GithubException as e: ...`
- **Hard fail:** Operations that require GitHub (state transitions, issue creation)
- **Soft fail:** Optional operations (enrichment, fetching status)

**Specific Handlers:**

1. **Connection errors** — `try_get_github()` returns `None` instead of raising
2. **Issue not found** — `typer.echo(f"WARNING: Could not fetch issue #{issue_num}: {e}", err=True)`
3. **Label not found** — `typer.echo(f"WARNING: label '{name}' not found")`
4. **State transition errors** — Caught in `apply_github_transition()`, re-raised as `StateTransitionError`

### 7.2 File I/O Errors

**Pattern:** Defensive reads, fail silently for missing optional data

- `filepath.read_text(encoding="utf-8")` wrapped in try/except for individual items in batch operations
- Missing `_last_synced` timestamp treated as "always stale" (no exception)
- Missing `_issue` field treated as "no GitHub issue" (gracefully skips that item)

### 7.3 Validation Errors

**Custom Exceptions:**
- `StateTransitionError` — Invalid state transition attempted
- `BacklogError` — Generic backlog operation failure
- `ItemNotFoundError` — Item not found by selector
- `DuplicateItemError` — Fuzzy duplicate check hit threshold

---

## 8. Key Conventions to Follow

### 8.1 Naming & Paths

**Local cache directory:** `.claude/backlog/` (from `BACKLOG_DIR` constant)

**File naming:** `{priority_prefix}-{slug}.md`
- Examples: `p0-auth-system.md`, `p1-backlog-state-patterns.md`, `idea-future-feature.md`
- Prefix maps to section in list output

**Metadata field names** (in frontmatter):
- Core: `name`, `description`
- Metadata nested dict: `priority`, `status`, `source`, `added`, `type`, `topic`, `issue`, `plan`, `groomed`, `last_synced`

### 8.2 State Transition Protocol

**Always use `state_handler.apply_github_transition()`** for GitHub label changes.

Never:
- Call `issue.remove_from_labels()` directly without also calling `issue.add_to_labels()`
- Update local `status` field without also updating GitHub label
- Set `status:*` label without validating it's in `VALID_TRANSITIONS` DAG

**Always use `update_item_metadata()`** for frontmatter changes.

Never:
- Directly edit the YAML file
- Manually construct frontmatter strings
- Call `loads_frontmatter()` / `dump_frontmatter()` in command code (use the wrapper)

### 8.3 GitHub API Patterns

**Two-step for state changes:**
1. Call `apply_github_transition()` to update labels (atomic)
2. Call `update_item_metadata()` to update local status
3. Call `issue.edit(state="closed")` SEPARATELY if closing issue (GitHub native state, orthogonal to backlog status)

**Example (correct):**
```python
apply_github_transition(repo, issue, current_status, BacklogState.DONE.value)
_update_item_metadata(filepath, {"metadata": {"status": BacklogState.DONE.value}})
issue.edit(state="closed")  # Optional: close GitHub issue
```

**Example (incorrect):**
```python
issue.remove_from_labels("status:in-progress")  # Missing: add new label
# Missing: update local status
# Missing: this leaves the item in "stateless void"
```

### 8.4 CLI Adapter Pattern

**Convert between types at command boundaries:**

- CLI commands work with `dict` (underscore-prefixed keys, bold metadata keys)
- Core operations work with `BacklogItem` (typed, validated model)
- Use `backlog_item_to_display_dict()` to convert model → dict
- Use `_dict_to_backlog_item_fields()` to convert dict → model

**Why:** CLI layer historically used dicts; core refactored to use typed models. Adapters bridge both.

### 8.5 Output Reporting Pattern

**All state-changing operations must report what changed:**

```python
typer.echo(f"Updated item status to {new_status}")
typer.echo(f"Created #{issue_num}: {title[:60]}")
typer.echo(f"Removed local file {filepath.name}")
```

**Why:** Users need to know if the operation succeeded (silent success is confusing).

---

## 9. Known Conventions & Invariants

### 9.1 Invariants (Must Always Be True)

1. **GitHub as source of truth for state labels** — If a `status:*` label exists on GitHub, it reflects the current state. Local frontmatter should match (but may lag).

2. **Local file existence = item is in backlog** — If `.claude/backlog/{slug}.md` exists, the item is active. Closed/deleted items should have their file removed.

3. **Issue number stability** — Once assigned via `metadata.issue: #N`, the issue number never changes (never update it to a different number).

4. **Terminal states are exclusive** — `CLOSED` is a sink state. No transitions out. `DONE` and `RESOLVED` are both "final" (transition only to `CLOSED`).

### 9.2 Current State (Bug Observations)

**These are NOT invariants but current behavior:**

1. **New items created with `status: open`** — Not a valid state in the machine, but used as a placeholder until grooming transitions them to `needs-grooming` or `groomed`.

2. **Grooming removes label without adding replacement** — After grooming, GitHub label is removed (`status:needs-grooming` gone) but new label (`status:groomed`) is not added. Item is "stateless."

3. **Closed issues remain in local cache** — `--from-github` refresh only fetches `state="open"` issues. Closed issues are never updated locally and appear as "open" on next list.

---

## 10. Architecture Specification Conventions

When designing new state machine operations, follow these patterns:

### Pattern: Atomic State Transition

```python
def transition_state(item: dict, from_state: str, to_state: str, repo: str) -> None:
    # Step 1: Validate transition (pure, no I/O)
    try:
        validate_transition(from_state, to_state)
    except StateTransitionError as e:
        typer.echo(f"ERROR: {e}", err=True)
        raise typer.Exit(1)

    # Step 2: Update GitHub (or fail hard)
    repository = _get_github(repo)
    issue = repository.get_issue(int(num))
    apply_github_transition(repository, issue, from_state, to_state)

    # Step 3: Update local cache
    _update_item_metadata(
        Path(filepath),
        {"metadata": {"status": to_state}},
        set_synced=True  # Record sync time on success
    )

    # Step 4: Report result
    typer.echo(f"Transitioned {title} from {from_state} to {to_state}")
```

### Pattern: Graceful Degradation for Optional Enrichment

```python
def enrich_item_from_github(item: dict, repo: str) -> dict:
    # Optional: GitHub unavailable = use local data as fallback
    repository = _try_get_github(repo)
    if repository is None:
        typer.echo("  GitHub unavailable — using cached status", err=True)
        return item  # Use local cache

    # GitHub available: enrich with live data
    issue = repository.get_issue(int(item.get("_issue", "").lstrip("#")))
    item["status"] = ...
    return item
```

---

**End of Analysis**

---

## Quick Reference: Which File For What?

| Need | File | Pattern |
|------|------|---------|
| Validate state transition | `state_handler.py:83-116` | `validate_transition(from, to)` |
| Apply GitHub label change | `state_handler.py:138-177` | `apply_github_transition(repo, issue, from, to)` |
| Update local frontmatter | `backlog_core/operations.py:100-134` | `update_item_metadata(filepath, updates)` |
| Parse local cache | `backlog.py:234-298` | `parse_backlog()` |
| Fetch status from GitHub | `backlog.py:755-783` | `_batch_fetch_statuses(items, repo)` |
| Refresh local from GitHub | `backlog.py:860-886` | `_refresh_local_cache_from_github(repo)` |
| Create GitHub issue | `backlog_core/github.py:95-127` | `create_issue_for_item(repo, item)` |
| Sync local → GitHub | `backlog.py:969-1005` | `_sync_push_groomed_content(items, repo)` |
| Dedup existing issues | `backlog.py:929-967` | `_sync_create_missing_issues(items, repo)` |

