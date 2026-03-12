---
description: "Deduplicate backlog CLI by replacing local implementations with imports from backlog_core/"
version: "1.0"
feature_slug: backlog-cli-dedup
github_issue: 611
architecture_spec: plan/architect-backlog-cli-dedup.md
feature_context: plan/feature-context-backlog-cli-dedup.md
codebase_analysis: plan/codebase/backlog-patterns.md
task_exports:
  enabled: false
  directory: "TASK"
tasks:
  - T1: Replace CLI constant definitions with imports from backlog_core/models.py
  - T2: Replace confirmed-duplicate utility functions with imports from backlog_core
  - T3: Replace dict-accepting duplicate functions with core calls plus adapters
  - T4: Migrate CLI-only functions to core imports
  - T5: Decouple test_backlog_core_parsing.py importlib imports and add CLI re-export wrapper
  - T6: Final cleanup, dead code removal, and full verification
---

## Context Manifest

| Artifact | Path | Role |
|----------|------|------|
| Feature context | `plan/feature-context-backlog-cli-dedup.md` | Problem definition, gap analysis, resolved questions |
| Codebase analysis | `plan/codebase/backlog-patterns.md` | CLI patterns, architecture, duplication inventory |
| Architecture spec | `plan/architect-backlog-cli-dedup.md` | ADRs, adapter pattern, rollout sequence |
| CLI script | `.claude/skills/backlog/scripts/backlog.py` | Target file for dedup edits (2563 lines) |
| Core models | `.claude/skills/backlog/backlog_core/models.py` | Canonical constants source |
| Core parsing | `.claude/skills/backlog/backlog_core/parsing.py` | Canonical function implementations |
| Core operations | `.claude/skills/backlog/backlog_core/operations.py` | Canonical CRUD and metadata operations |
| Core github | `.claude/skills/backlog/backlog_core/github.py` | Canonical GitHub operations |
| Test directory | `.claude/skills/backlog/tests/` | 12 test files that must pass after each task |
| Architecture doc | `.claude/skills/backlog/backlog_core/ARCHITECTURE.md` | Migration mapping table |
| Drift audit | `.claude/skills/backlog/backlog_core/DOCUMENTATION_DRIFT_AUDIT.md` | FIND-14/15 on unused constants in core |

## Dependency Graph

```text
T1 (constants)
 |
 +---> T2 (identical-logic utility functions)
 |      |
 |      +---> T3 (dict/BacklogItem adapter functions)
 |             |
 |             +---> T4 (CLI-only function migration)
 |                    |
 |                    +---> T5 (test decoupling)
 |                           |
 |                           +---> T6 (final cleanup + verification)
```

All tasks are sequential because they modify the same file (`.claude/skills/backlog/scripts/backlog.py`). Each task independently testable -- all 12 test files must pass after each task completes.

---

---
task: T1
title: Replace CLI constant definitions with imports from backlog_core/models.py
status: not-started
agent: python3-development:python-cli-architect
dependencies: []
priority: 1
complexity: low
accuracy-risk: medium
skills: ["python3-development"]
parallelize-with: []
reason: "Sequential -- modifies backlog.py which all subsequent tasks also modify"
handoff: "Summary of constants replaced, diff of import block changes, test results"
---

## Task T1: Replace CLI constant definitions with imports from backlog_core/models.py

### Context

This task is the first step in deduplicating `.claude/skills/backlog/scripts/backlog.py`. The CLI script defines 7 constants locally (lines 87-118) that have canonical equivalents in `.claude/skills/backlog/backlog_core/models.py`. One of these -- `SKIP_STATUS` -- has a confirmed bug: the CLI version at line 92 is `("DONE", "RESOLVED", "COMPLETED")` while the canonical version at `models.py:36` is `("DONE", "RESOLVED", "COMPLETED", "CLOSED")`. Replacing the local definition with the import fixes the bug.

The CLI already has `sys.path` setup at line 71 and existing imports from `backlog_core` at lines 76-78, so the import pathway is established.

Read the architecture spec at `plan/architect-backlog-cli-dedup.md` and codebase analysis at `plan/codebase/backlog-patterns.md` for full context.

### Objective

Replace all 7 locally defined constants in `backlog.py` (lines 87-118) with imports from `backlog_core.models`, fixing the SKIP_STATUS bug as a natural consequence.

### Inputs

- `.claude/skills/backlog/scripts/backlog.py` -- target file, lines 87-118 for constant definitions, lines 76-78 for existing import block
- `.claude/skills/backlog/backlog_core/models.py` -- canonical constant definitions (lines 17-60+)
- `.claude/skills/backlog/backlog_core/DOCUMENTATION_DRIFT_AUDIT.md` -- FIND-14/15 confirm `SKIP_STATUS` and `SECTION_RE` are defined in core but unused by core modules

### Requirements

1. Add imports to the existing `backlog_core` import block (around lines 76-78) for: `BACKLOG_DIR`, `DEFAULT_REPO`, `SECTION_RE`, `SKIP_STATUS`, `GITHUB_ISSUE_URL_RE`, `GITHUB_ISSUE_TITLE_TRUNCATE`, `MIN_FRONTMATTER_PARTS`, `TYPE_TO_LABEL`, `ROLE_MAP`, `BENEFIT_MAP`
2. Remove the local constant definitions from `backlog.py` (lines 87-118 region: `BACKLOG_DIR`, `DEFAULT_REPO`, `SECTION_RE`, `SKIP_STATUS`, `GITHUB_ISSUE_URL_RE`, `GITHUB_ISSUE_TITLE_TRUNCATE`, `MIN_FRONTMATTER_PARTS`, `TYPE_TO_LABEL`, `ROLE_MAP`, `BENEFIT_MAP`)
3. Keep `FUZZY_DUPLICATE_THRESHOLD` if it exists locally -- verify whether it is defined locally or only in core; if duplicated, import it too
4. Keep `_COMMIT_PREFIX_RE` handling correct -- verify whether `backlog.py` defines this locally (around line 344) and whether `models.py` exports it; if both exist, import from core
5. Preserve the underscore-prefixed import aliases pattern used by the existing imports (e.g., `from backlog_core.models import BACKLOG_DIR as _BACKLOG_DIR`) only if the CLI uses the constant with an underscore prefix; otherwise import directly
6. Verify every usage site in `backlog.py` that references the old local constant still resolves correctly after the replacement

### Constraints

- Do NOT modify any file in `backlog_core/` in this task
- Do NOT modify any test files
- Do NOT change any CLI command behavior (except the natural SKIP_STATUS bug fix)
- Do NOT remove any functions -- only constants
- Commit message must reference `Fixes #611`

### Expected Outputs

- Modified `.claude/skills/backlog/scripts/backlog.py` with constants imported instead of locally defined

### Acceptance Criteria

1. Zero locally defined constants in `backlog.py` that duplicate `backlog_core/models.py` definitions
2. `SKIP_STATUS` in `backlog.py` resolves to `("DONE", "RESOLVED", "COMPLETED", "CLOSED")` -- the canonical value from `models.py:36`
3. All 12 test files pass: `uv run pytest .claude/skills/backlog/tests/ -x -q`
4. `backlog.py` runs without import errors: `uv run python -c "import importlib.util; s=importlib.util.spec_from_file_location('b', '.claude/skills/backlog/scripts/backlog.py'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); print('OK')"`
5. No references to removed local constants remain as undefined names (grep for each constant name and verify all references resolve to the imported version)

### Verification Steps

1. Run full test suite: `uv run pytest .claude/skills/backlog/tests/ -x -q` -- expect all 12 files pass
2. Verify SKIP_STATUS value: `uv run python -c "import sys; sys.path.insert(0, '.claude/skills/backlog/scripts'); import importlib.util; s=importlib.util.spec_from_file_location('b', '.claude/skills/backlog/scripts/backlog.py'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); assert 'CLOSED' in m.SKIP_STATUS, f'SKIP_STATUS={m.SKIP_STATUS}'; print('SKIP_STATUS OK:', m.SKIP_STATUS)"`
3. Grep for orphaned constant definitions: `grep -n "^BACKLOG_DIR\|^DEFAULT_REPO\|^SECTION_RE\|^SKIP_STATUS\|^GITHUB_ISSUE_URL_RE\|^TYPE_TO_LABEL\|^ROLE_MAP\|^BENEFIT_MAP" .claude/skills/backlog/scripts/backlog.py` -- expect zero matches (all definitions removed)
4. Verify import block is clean: `uv run python -c "import ast, sys; tree=ast.parse(open('.claude/skills/backlog/scripts/backlog.py').read()); imports=[n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom)) and getattr(n, 'module', '') and 'backlog_core' in getattr(n, 'module', '')]; print(f'{len(imports)} backlog_core imports found'); assert len(imports) >= 2"`

### CoVe Checks

- Key claims to verify:
  - `SKIP_STATUS` in `models.py` includes `"CLOSED"` (line 36)
  - The CLI `sys.path.insert` at line 71 makes `backlog_core` importable
  - All 7 constants exist in `models.py` with matching names
- Verification questions:
  1. Does `backlog_core/models.py` export `BACKLOG_DIR`, `DEFAULT_REPO`, `SECTION_RE`, `SKIP_STATUS`, `GITHUB_ISSUE_URL_RE`, `GITHUB_ISSUE_TITLE_TRUNCATE`, `MIN_FRONTMATTER_PARTS`, `TYPE_TO_LABEL`, `ROLE_MAP`, `BENEFIT_MAP`?
  2. Are there any constants in `backlog.py` lines 87-118 that do NOT have a counterpart in `models.py`?
  3. Does any code in `backlog.py` reference these constants with a module prefix (e.g., `models.SKIP_STATUS`) that would break if imported directly?
- Evidence to collect:
  - Read `models.py` lines 1-80 to confirm all constant names and values
  - Read `backlog.py` lines 85-120 to confirm all local constant definitions
  - Grep `backlog.py` for each constant name to find all usage sites
- Revision rule:
  - If any constant exists locally but NOT in `models.py`, do not remove it -- leave it in place and note it in the handoff summary.

### Handoff

Return:
- List of constants replaced (name, old value, new import source)
- Whether SKIP_STATUS bug is confirmed fixed (value comparison)
- Any constants that could NOT be replaced and why
- Full test suite output (pass/fail count)
- Diff summary of import block changes

---
task: T2
title: Fix core internal SKIP_STATUS and SECTION_RE inconsistencies (FIND-14/FIND-15)
status: not-started
agent: python3-development:python-cli-architect
dependencies: [T1]
priority: 1
complexity: low
accuracy-risk: medium
skills: ["python3-development"]
parallelize-with: []
reason: "Sequential -- T1 must complete first so constants are imported; this task modifies backlog_core/ files"
handoff: "Summary of core internal fixes, diff of parsing.py changes, test results"
---

## Task T2: Fix core internal SKIP_STATUS and SECTION_RE inconsistencies (FIND-14/FIND-15)

### Context

This task is merged from two planned changes to `backlog_core/parsing.py` to avoid edit conflicts. It addresses FIND-14 and FIND-15 from `.claude/skills/backlog/backlog_core/DOCUMENTATION_DRIFT_AUDIT.md`.

**FIND-14**: `parsing.py:parse_item_file` uses an inline set `{"done", "resolved"}` instead of importing and using `SKIP_STATUS` from `models.py`. This means core's own parsing does not respect the canonical constant.

**FIND-15**: `SECTION_RE` is defined in `models.py` but not imported by any core module that needs it.

These inconsistencies must be resolved before later tasks import more functions from core into the CLI -- the CLI must import from a self-consistent core.

Read the architecture spec Section 5.7 at `plan/architect-backlog-cli-dedup.md` for the design decision.

### Objective

Make `backlog_core/parsing.py` use `SKIP_STATUS` and `SECTION_RE` from `backlog_core/models.py` instead of inline definitions, ensuring core is internally consistent.

### Inputs

- `.claude/skills/backlog/backlog_core/parsing.py` -- target file for edits
- `.claude/skills/backlog/backlog_core/models.py` -- source of canonical constants
- `.claude/skills/backlog/backlog_core/DOCUMENTATION_DRIFT_AUDIT.md` -- FIND-14 and FIND-15 descriptions

### Requirements

#### SKIP_STATUS usage in core

1. In `parsing.py`, find where item status filtering uses an inline set (e.g., `{"done", "resolved"}` or similar hardcoded values) instead of `SKIP_STATUS`
2. Replace the inline set with a reference to `SKIP_STATUS` imported from `.models`
3. Ensure case handling is correct: `SKIP_STATUS` contains uppercase strings `("DONE", "RESOLVED", "COMPLETED", "CLOSED")`; if the inline code compares lowercase, normalize via `.upper()` before comparison

#### SECTION_RE usage in core

4. Search `parsing.py` for any inline regex that duplicates `SECTION_RE` pattern (`r"^##\s+(P0|P1|P2|Ideas)"`)
5. If found, replace with import of `SECTION_RE` from `.models`
6. If `SECTION_RE` is not used inline in `parsing.py`, no change needed -- document this in handoff

### Constraints

- Do NOT modify `backlog.py` (CLI script) in this task
- Do NOT modify any test files
- Do NOT change the semantic behavior of any function -- only replace inline values with the canonical constant
- Ensure the status comparison handles case correctly (uppercase constant vs potentially lowercase input)

### Expected Outputs

- Modified `.claude/skills/backlog/backlog_core/parsing.py` with `SKIP_STATUS` imported from `.models` and used where applicable

### Acceptance Criteria

1. No inline hardcoded status sets (e.g., `{"done", "resolved"}`) remain in `parsing.py` that duplicate `SKIP_STATUS` semantics
2. `SKIP_STATUS` appears in `parsing.py`'s import block from `.models`
3. All 12 test files pass: `uv run pytest .claude/skills/backlog/tests/ -x -q`
4. The `parse_item_file` function in `parsing.py` uses `SKIP_STATUS` for status filtering (if it performs status filtering)

### Verification Steps

1. Run full test suite: `uv run pytest .claude/skills/backlog/tests/ -x -q`
2. Grep for inline status sets: `grep -n "done.*resolved\|DONE.*RESOLVED" .claude/skills/backlog/backlog_core/parsing.py` -- expect only references to `SKIP_STATUS`, not inline sets
3. Verify import exists: `grep -n "SKIP_STATUS" .claude/skills/backlog/backlog_core/parsing.py` -- expect at least one import line and one usage line
4. CLI smoke test still works: `uv run .claude/skills/backlog/scripts/backlog.py list --format text 2>&1 | head -5`

### CoVe Checks

- Key claims to verify:
  - `parsing.py` currently contains an inline set for status filtering (FIND-14 claim)
  - The inline set uses lowercase strings while `SKIP_STATUS` uses uppercase
- Verification questions:
  1. What exact inline status values does `parsing.py` use, and on which line(s)?
  2. Does the comparison context use `.lower()`, `.upper()`, or direct comparison?
  3. Does `parse_item_file` actually filter by status, or does a different function do it?
- Evidence to collect:
  - Read `parsing.py` and grep for status-related filtering logic
  - Read FIND-14 description in `DOCUMENTATION_DRIFT_AUDIT.md` for exact line references
- Revision rule:
  - If FIND-14's inline set does not exist (already fixed), skip that part and document in handoff. If the case conversion differs, adapt the replacement to preserve behavior.

### Handoff

Return:
- Which inline values were replaced and on which lines
- Whether SECTION_RE was also addressed or was not needed
- Case handling approach used (uppercase normalization vs other)
- Full test suite output (pass/fail count)

<!-- PENDING: T3 -->

<!-- PENDING: T4 -->

<!-- PENDING: T5 -->

<!-- PENDING: T6 -->

<!-- PENDING: SYNC_CHECKPOINTS -->
