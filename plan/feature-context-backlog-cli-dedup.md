# Feature Context: Backlog CLI Deduplication

## Document Metadata

- **Generated**: 2026-03-12
- **Input Type**: simple_description
- **Source**: GitHub Issue #611 (P1) -- Deduplicate backlog CLI (backlog.py) by replacing local implementations with imports from backlog_core/
- **Status**: DISCOVERY_COMPLETE

---

## Original Request

Deduplicate backlog CLI (backlog.py) by replacing local implementations with imports from backlog_core/. The CLI script retains duplicates of functions and constants that have canonical implementations in backlog_core/. The target state is backlog.py as a thin CLI wrapper delegating to backlog_core, with an adapter layer at the dict/BacklogItem boundary.

---

## Core Intent Analysis

### WHO (Target Users)

Maintainers of the backlog subsystem (CLI + MCP server). Both humans editing the code and agents delegated to modify backlog behavior.

### WHAT (Desired Outcome)

A single source of truth for backlog constants, parsing logic, and GitHub operations. When a constant or function is updated, the change propagates to both CLI and MCP server without requiring parallel edits. The CLI (backlog.py) becomes a thin Typer wrapper that delegates business logic to backlog_core/ modules.

### WHEN (Trigger Conditions)

This is triggered by:

1. A confirmed bug: CLI `SKIP_STATUS` at `backlog.py:92` is `("DONE", "RESOLVED", "COMPLETED")` -- missing `"CLOSED"`. The canonical version in `backlog_core/models.py:36` includes `"CLOSED"`. This divergence causes the CLI to treat CLOSED items differently from the MCP server.
2. Maintenance burden: any change to shared logic (constants, find_item, build_issue_body, create_issue_for_item) requires editing two locations and verifying consistency manually.

### WHY (Problem Being Solved)

Code duplication between `backlog.py` (2563 lines) and `backlog_core/` causes:

- **Behavioral divergence**: The SKIP_STATUS bug is a concrete example -- CLI and MCP server disagree on which statuses to skip.
- **Maintenance cost**: Every change to shared logic requires two edits, two reviews, and risk of drift.
- **Cognitive overhead**: Contributors must know which copy is canonical.

---

## Codebase Research

### Similar Patterns Found

#### Pattern 1: Existing backlog_core imports in backlog.py

- **Location**: `.claude/skills/backlog/scripts/backlog.py:76-78`
- **Relevance**: The CLI already imports from backlog_core in three places (`operations`, `entry_blocks.rewrite_section`, `models.BacklogError/ItemNotFoundError`). This demonstrates the import pathway works and the sys.path setup at line 71 (`sys.path.insert(0, str(_SCRIPT_DIR.parent))`) already exposes backlog_core.
- **Reusable**: The import pattern and path setup are already established. New imports follow the same convention.

#### Pattern 2: Core module architecture with BacklogItem model

- **Location**: `backlog_core/models.py:1-50` (constants), `backlog_core/parsing.py:312` (find_item), `backlog_core/parsing.py:464` (build_issue_body), `backlog_core/github.py:87` (create_issue_for_item)
- **Relevance**: The core modules use `BacklogItem` (Pydantic BaseModel) as their data type, while the CLI uses `dict`. This is the fundamental interface mismatch that requires an adapter layer.
- **Reusable**: All canonical implementations exist and are tested. The dedup work is replacing CLI copies with imports + adapters, not writing new logic.

#### Pattern 3: ARCHITECTURE.md migration mapping

- **Location**: `.claude/skills/backlog/backlog_core/ARCHITECTURE.md:126-175`
- **Relevance**: The architecture doc already defines the intended mapping from CLI private functions to core public functions (e.g., `_title_to_slug()` to `title_to_slug()`, `_parse_item_file()` to `parse_item_file()`). This is an explicit plan that was partially executed.
- **Reusable**: The mapping table serves as a checklist for what was intended to be migrated but was not completed.

#### Pattern 4: DOCUMENTATION_DRIFT_AUDIT findings

- **Location**: `.claude/skills/backlog/backlog_core/DOCUMENTATION_DRIFT_AUDIT.md:275-301`
- **Relevance**: FIND-14 and FIND-15 document that `SKIP_STATUS` and `SECTION_RE` are defined in core models.py but not imported by any core module. This suggests the constants were migrated to core but the consumers (CLI and parsing) were never updated to use them.
- **Reusable**: The audit findings confirm the scope of unused-but-canonical constants.

### Existing Infrastructure

1. **sys.path setup**: `backlog.py:71` already adds `_SCRIPT_DIR.parent` to sys.path, making `from backlog_core import ...` work.
2. **Three existing imports**: `backlog.py:76-78` imports operations, entry_blocks, and model exceptions from backlog_core.
3. **12 test files**: Tests cover both CLI (via `test_backlog_gh_first.py` using importlib) and core modules (via direct imports). Test file `test_backlog_core_parsing.py:691-723` explicitly tests the dict-based `_build_issue_body_from_file` from the CLI script alongside the BacklogItem-based version.

### Code References

- `.claude/skills/backlog/scripts/backlog.py:87-112` -- CLI-local constant definitions (duplicates of core)
- `.claude/skills/backlog/scripts/backlog.py:92` -- SKIP_STATUS missing "CLOSED" (bug)
- `.claude/skills/backlog/scripts/backlog.py:162-248` -- CLI-local utility functions (9 functions not yet in core)
- `.claude/skills/backlog/scripts/backlog.py:318` -- `find_item(items: list[dict], selector: str) -> dict | None`
- `.claude/skills/backlog/scripts/backlog.py:466` -- `build_issue_body(item: dict) -> str`
- `.claude/skills/backlog/scripts/backlog.py:508` -- `create_issue_for_item(repo: Repository, item: dict, dry_run: bool = False) -> int | None`
- `.claude/skills/backlog/backlog_core/models.py:36` -- `SKIP_STATUS = ("DONE", "RESOLVED", "COMPLETED", "CLOSED")`
- `.claude/skills/backlog/backlog_core/parsing.py:312` -- `find_item(items: list[BacklogItem], selector: str) -> BacklogItem | None`
- `.claude/skills/backlog/backlog_core/parsing.py:464` -- `build_issue_body(item: BacklogItem) -> str`
- `.claude/skills/backlog/backlog_core/github.py:87` -- `create_issue_for_item(...)` accepting BacklogItem

---

## Use Scenarios

### Scenario 1: Fixing the SKIP_STATUS bug via dedup

**Actor**: Maintainer
**Trigger**: A backlog item with status "CLOSED" is treated as active by the CLI but skipped by the MCP server.
**Goal**: After dedup, both CLI and MCP server import SKIP_STATUS from `backlog_core/models.py`, eliminating the divergence.
**Expected Outcome**: CLI `list` command skips CLOSED items, matching MCP server behavior.

### Scenario 2: Updating a shared constant

**Actor**: Developer adding a new item type (e.g., "debt")
**Trigger**: Need to add `"debt": "type:debt"` to TYPE_TO_LABEL.
**Goal**: Edit one file (`backlog_core/models.py`) and have both CLI and MCP server pick up the change.
**Expected Outcome**: Single edit, single test run, no risk of forgetting to update the CLI copy.

### Scenario 3: CLI user runs backlog commands

**Actor**: Developer or agent running `backlog.py list`, `backlog.py add`, etc.
**Trigger**: Normal backlog operations via CLI.
**Goal**: CLI output and behavior are identical before and after dedup.
**Expected Outcome**: No behavioral change from the user's perspective (except the SKIP_STATUS bug fix).

### Scenario 4: Running tests after dedup

**Actor**: CI or developer running `uv run pytest .claude/skills/backlog/tests/`
**Trigger**: After dedup changes are made.
**Goal**: All 12 test files pass without modification (or with minimal test adapter changes).
**Expected Outcome**: Tests that import CLI functions directly (e.g., `test_backlog_gh_first.py`, `test_backlog_core_parsing.py:691-723`) still work because the CLI re-exports or adapts from core.

---

## Gap Analysis

### Identified Gaps

| # | Category | Gap Description | Impact |
|---|----------|-----------------|--------|
| 1 | Behavior | CLI functions accept `dict`, core functions accept `BacklogItem`. The adapter layer shape is undefined -- should CLI convert dict-to-BacklogItem before calling core, or should core offer dict-accepting wrappers? | Determines where conversion logic lives and how much CLI code changes |
| 2 | Scope | 9 CLI-only functions (`_title_to_slug`, `_infer_type`, `_parse_backlog_from_directory`, `_parse_item_file`, `_normalize_issue_title`, `_find_fuzzy_duplicates`, `_today`, `_now_iso`, `_update_item_metadata`) exist only in the CLI. ARCHITECTURE.md maps them to core equivalents but some may not exist yet in core. | Must verify which of the 9 already have core equivalents vs. which need to be created first |
| 3 | Behavior | The SKIP_STATUS bug fix (adding "CLOSED") is a behavioral change bundled with a refactoring. Should the bug fix be a separate commit/PR? | Mixing refactoring and behavior changes makes it harder to bisect regressions |
| 4 | Integration | `test_backlog_core_parsing.py:691-723` explicitly imports and tests the dict-based `_build_issue_body_from_file` from `scripts/backlog.py` via importlib. After dedup, this function may no longer exist. | Tests that directly import CLI internals will break if those internals are removed |
| 5 | Scope | The DOCUMENTATION_DRIFT_AUDIT (FIND-14, FIND-15) notes that `SKIP_STATUS` and `SECTION_RE` are unused even within core modules (e.g., `parse_item_file` uses inline set `{"done", "resolved"}` instead of `SKIP_STATUS`). Dedup of CLI is incomplete if core itself has internal inconsistencies. | Core modules may need internal cleanup before they are reliable import targets |
| 6 | Scope | The feature request says "9 functions NOT found in backlog_core" but ARCHITECTURE.md maps all 9 to planned core equivalents. It is unclear how many have been implemented since that mapping was written. | The actual number of functions requiring migration may differ from 9 |

---

## Questions Requiring Resolution

### Q1: Adapter layer placement

- **Category**: Behavior
- **Gap**: CLI uses `dict` for items; core uses `BacklogItem` (Pydantic model)
- **Question**: Should the adapter convert dict-to-BacklogItem at the CLI boundary (CLI constructs BacklogItem before calling core), or should core modules expose dict-accepting convenience wrappers?
- **Options**:
  - A) CLI constructs BacklogItem from dict at the Typer command level, then calls core functions directly
  - B) A thin adapter module (e.g., `backlog_core/compat.py`) provides dict-accepting wrappers around core functions
  - C) CLI keeps its own dict-based find_item/build_issue_body but imports constants and utilities from core
- **Why It Matters**: Option A makes CLI fully dependent on BacklogItem model. Option B adds a new module. Option C leaves some duplication in place.
- **Resolution**: _pending_

### Q2: Bug fix bundling

- **Category**: Scope
- **Gap**: The SKIP_STATUS "CLOSED" fix is a behavioral change mixed with a pure refactoring
- **Question**: Should the SKIP_STATUS bug fix be a separate commit before the dedup refactoring, or is it acceptable as part of the dedup work?
- **Options**:
  - A) Separate commit fixing the bug first, then dedup commit(s)
  - B) Single body of work -- the dedup naturally fixes the bug by importing the correct constant
- **Why It Matters**: Separate commits enable cleaner bisection if regressions appear. Combined is simpler to execute.
- **Resolution**: _pending_

### Q3: Core internal inconsistencies

- **Category**: Scope
- **Gap**: Core's own `parse_item_file` uses inline `{"done", "resolved"}` instead of `SKIP_STATUS`; `SECTION_RE` is unused within core
- **Question**: Should core internal inconsistencies (FIND-14, FIND-15 from the drift audit) be fixed as part of this feature, or deferred to a separate effort?
- **Options**:
  - A) Fix core inconsistencies in this feature (broader scope but cleaner result)
  - B) Defer core cleanup -- only replace CLI duplicates with core imports
- **Why It Matters**: If core's own modules don't use their own constants, importing them into CLI creates a half-fixed state.
- **Resolution**: _pending_

### Q4: CLI-only function migration

- **Category**: Scope
- **Gap**: 9 functions exist only in CLI. ARCHITECTURE.md maps them to planned core equivalents. Unknown how many have been implemented.
- **Question**: For CLI-only functions that do NOT yet have core equivalents, should this feature (a) move them to core, (b) keep them in CLI as private helpers, or (c) defer their migration?
- **Options**:
  - A) Move all 9 to core as part of this feature
  - B) Move only the ones that core modules also need; keep CLI-only helpers in CLI
  - C) Defer all migration -- only dedup what already exists in both places
- **Why It Matters**: Option A is the full "thin CLI wrapper" vision but larger scope. Option C is minimal scope but leaves CLI as a mixed bag.
- **Resolution**: _pending_

### Q5: Test adaptation strategy

- **Category**: Integration
- **Gap**: `test_backlog_core_parsing.py:691-723` imports dict-based CLI internals via importlib
- **Question**: When CLI internals are removed or replaced, should tests be (a) updated to test via core's BacklogItem-based APIs, (b) kept as-is with CLI re-exporting thin wrappers, or (c) removed if the core equivalent is already tested?
- **Options**:
  - A) Update tests to use core APIs
  - B) CLI re-exports wrappers so existing tests keep working
  - C) Remove redundant tests if core equivalents exist
- **Why It Matters**: Determines whether test count stays at 14 files or decreases, and how much test rewriting is needed.
- **Resolution**: _pending_

---

## Goals (Pending Resolution)

_These goals will be finalized after questions are resolved._

1. All shared constants (BACKLOG_DIR, DEFAULT_REPO, SECTION_RE, SKIP_STATUS, TYPE_TO_LABEL, ROLE_MAP, BENEFIT_MAP) are imported from `backlog_core/models.py` -- no CLI-local definitions
2. Duplicated functions (find_item, build_issue_body, create_issue_for_item) are replaced with calls to backlog_core equivalents, with adapter logic for dict/BacklogItem conversion
3. The SKIP_STATUS "CLOSED" bug is fixed (naturally or explicitly)
4. All 12 test files in `.claude/skills/backlog/tests/` pass
5. MCP server behavior is unaffected
6. CLI output is identical for all commands (except the SKIP_STATUS bug fix behavior)
7. backlog.py line count decreases meaningfully (target depends on Q4 resolution)

---

## Next Steps

After questions are resolved:

1. Update "Resolution" fields in Questions section
2. Finalize Goals section
3. Proceed to RT-ICA assessment
4. Then proceed to architecture design

---

## Post-Implementation Annotations

_Added by context-refinement agent on 2026-03-12_

### Design Refinements

1. **`_find_fuzzy_duplicates` mis-classified as having a compatible core equivalent**: The feature context stated the ARCHITECTURE.md migration mapping covers all 9 CLI-only functions. In practice, the core `find_fuzzy_duplicates` accepts `list[BacklogItem]` while the CLI call site passes `list[dict]`. A direct import replacement was not possible without also updating the call site. The function was retained locally as a `list[dict]`-accepting implementation.
   - Original: "9 functions NOT found in backlog_core" (Gap Analysis, Category 6) implied all 9 have confirmed core equivalents
   - Actual: `_find_fuzzy_duplicates` has a core equivalent but with an incompatible signature — retained locally
   - Recorded in: plan/tasks-1-backlog-cli-dedup.md, Discovered During Implementation

2. **Monkeypatch constraint prevents `_parse_backlog_from_directory` from using core import**: The feature context identified `_parse_backlog_from_directory` as a dedup target. The test suite uses `monkeypatch.setattr(mod, "BACKLOG_DIR", ...)` which only affects the `backlog.py` module namespace. Core functions read `backlog_core.models.BACKLOG_DIR` directly and ignore these patches. The function was retained as a local implementation with an explicit comment documenting this constraint.
   - Original: "_parse_backlog_from_directory ... will be replaced with imports + adapters" (implied by dedup scope)
   - Actual: Retained as local implementation; test isolation constraint documented in function docstring
   - Recorded in: plan/tasks-1-backlog-cli-dedup.md, Discovered During Implementation

3. **Scope of constant imports narrower than documented**: The feature context listed 7 constants for replacement. The final import block does not include `SECTION_RE`, `TYPE_TO_LABEL`, `ROLE_MAP`, `BENEFIT_MAP`, and `GITHUB_ISSUE_TITLE_TRUNCATE` — these are not called in the CLI after dedup (clean removal, no dead imports).
   - Original: "All 7 CLI-local constants are replaced with imports from backlog_core.models" (Goals item 1)
   - Actual: 4 constants imported from core; 5 constants removed without import (not referenced in CLI)
   - Recorded in: plan/tasks-1-backlog-cli-dedup.md, Discovered During Implementation

4. **Net line reduction was ~97, not ~335**: The dedup removed fewer lines than the feature context's reduction target implied, primarily because two functions were retained locally and two adapter functions were added.
   - Original: "backlog.py line count decreases meaningfully (target depends on Q4 resolution)" (Goals item 7)
   - Actual: 2563 → 2466 lines (-97 net); 582 tests passing, ruff clean
   - Recorded in: plan/tasks-1-backlog-cli-dedup.md, Discovered During Implementation
