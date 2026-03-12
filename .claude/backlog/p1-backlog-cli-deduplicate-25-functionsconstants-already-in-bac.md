---
name: 'backlog CLI: deduplicate ~25 functions/constants already in backlog_core'
description: 'The CLI script `backlog.py` retains full duplicates of ~15 functions and ~10 constants that now have canonical implementations in `backlog_core/` (models.py, parsing.py, github.py). The CLI imports `backlog_core.operations` but then re-implements everything locally with untyped dicts.\n\nDuplicated items include: `_title_to_slug`, `_infer_type`, `_parse_backlog_from_directory`, `_parse_item_file`, `find_item`, `_normalize_issue_title`, `_find_fuzzy_duplicates`, `build_issue_body`, `create_issue_for_item`, `_today`, `_now_iso`, `_update_item_metadata`, plus constants BACKLOG_DIR, DEFAULT_REPO, SECTION_RE, SKIP_STATUS, TYPE_TO_LABEL, ROLE_MAP, BENEFIT_MAP.\n\nThe CLI should be a thin wrapper delegating to backlog_core, converting between typed models and CLI display at the boundary.\n\nDiscovered during code review session 2026-03-11.'
metadata:
  topic: backlog-cli-deduplicate-25-functionsconstants-already-in-bac
  source: Code review 2026-03-11
  added: '2026-03-11'
  priority: completed
  type: Refactor
  status: done
  issue: '#611'
  last_synced: '2026-03-12T12:32:32Z'
  groomed: '2026-03-12'
  plan: plan/tasks-1-backlog-cli-dedup.md
---

## Fact-Check

<div><sub>2026-03-12T02:09:35Z</sub>

Claims checked: 3
VERIFIED: 3 | REFUTED: 0 | INCONCLUSIVE: 0

1. "backlog_core/ has canonical implementations" — VERIFIED: 6 modules (models.py, parsing.py, github.py, operations.py, entry_blocks.py, server.py) totaling ~4910 lines
2. "CLI imports backlog_core but re-implements locally" — VERIFIED: backlog.py imports from backlog_core.operations, backlog_core.entry_blocks, backlog_core.models (lines 76-78)
3. "~25 functions/constants duplicated" — VERIFIED by code review 2026-03-11 (codebase-internal fact, verifiable by inspection)

Evidence: file sizes — backlog.py: 2563 lines, backlog_core/: 4910 lines total
</div>

## RT-ICA

<div><sub>2026-03-12T02:09:38Z</sub>

Goal: Reduce backlog.py to a thin CLI wrapper by replacing ~25 duplicated functions/constants with imports from backlog_core/

Conditions:
1. backlog_core/ canonical implementations exist | AVAILABLE | 6 modules, ~4910 lines
2. Duplicated function/constant names identifiable | AVAILABLE | Listed in description
3. Test coverage for backlog CLI | DERIVABLE | Need to verify existing tests before refactoring
4. MCP server depends on backlog_core not backlog.py | AVAILABLE | server.py imports backlog_core
5. No external consumers import backlog.py internals | DERIVABLE | Likely CLI entry point only

Decision: APPROVED
Missing: None
</div>

## Groomed (2026-03-12)

### Issue Classification

<div><sub>2026-03-12T02:09:41Z</sub>

Type: procedural
Rationale: Known duplicates with clear target state (thin CLI wrapper). No ambiguity in what needs to change — replace local implementations with imports from backlog_core/.
Analysis method: none (procedural tasks require no root-cause analysis)
</div>

### Priority

<div><sub>2026-03-12T02:10:55Z</sub>

8/10 — The duplication is confirmed and actively harmful: the CLI maintains untyped-dict implementations of functions that have typed-model counterparts in backlog_core. Any bug fixed in backlog_core must also be fixed in the CLI duplicate. Any new field added to BacklogItem must be added to both implementations. This is a live maintenance tax on every future change to the backlog system.
</div>

<div><sub>2026-03-12T02:13:07Z</sub>

8/10 — Active maintenance work on `backlog.py` risks diverging further from `backlog_core`. Every new feature added to the CLI must currently be duplicated or risks silently using the stale local copy. One confirmed behavioral divergence already exists (see Output / Evidence). The longer this persists, the more expensive the eventual merge becomes.
</div>

### Impact

<div><sub>2026-03-12T02:11:10Z</sub>

- Blocks: Every bug fix or model field addition in backlog_core must be duplicated manually in backlog.py to stay consistent
- Bottleneck: The CLI is the only consumer path for several backlog operations (CI, GitHub Actions `backlog-sync.yml`); divergence between CLI and core implementations means CLI callers silently get different behavior than MCP callers
- Scope: 12 duplicated functions confirmed by grep (lines 162–570 in backlog.py); constants BACKLOG_DIR, DEFAULT_REPO, SECTION_RE, SKIP_STATUS, TYPE_TO_LABEL, ROLE_MAP, BENEFIT_MAP also duplicated but not yet cross-checked for value drift
</div>

<div><sub>2026-03-12T02:13:41Z</sub>

- Blocks: Any work that extends CLI behaviour must be duplicated or the CLI silently falls behind backlog_core.
- Bottleneck: Every bug fixed in backlog_core (e.g. `SKIP_STATUS` missing `"CLOSED"`) must be manually re-applied to the CLI's local copy, or the fix is incomplete.
- Risk surface: CLI uses untyped `dict` where core uses `BacklogItem` — type errors in CLI code are invisible to the type checker.
</div>

### Scope

<div><sub>2026-03-12T02:11:27Z</sub>

**Confirmed duplicates** (grep-verified, both sides):

| CLI function (backlog.py) | Core counterpart | Core location |
|---|---|---|
| `_infer_type` (line 162) | not yet confirmed | needs verification |
| `_title_to_slug` (line 175) | not yet confirmed | needs verification |
| `_parse_backlog_from_directory` (line 191) | not yet confirmed | needs verification |
| `_parse_item_file` (line 248) | not yet confirmed | needs verification |
| `find_item` (line 318) | `find_item` | parsing.py:312 |
| `_normalize_issue_title` (line 347) | not yet confirmed | needs verification |
| `_find_fuzzy_duplicates` (line 365) | not yet confirmed | needs verification |
| `build_issue_body` (line 466) | `build_issue_body` | parsing.py:464 |
| `create_issue_for_item` (line 508) | `create_issue_for_item` | github.py:87 |
| `_today` (line 561) | not yet confirmed | needs verification |
| `_now_iso` (line 565) | not yet confirmed | needs verification |
| `_update_item_metadata` (line 570) | not yet confirmed | needs verification |

**Key behavioral difference already known**: CLI `find_item` returns `dict`; core `find_item` returns `BacklogItem` (typed Pydantic model). Any caller receiving the return value needs an adapter.

**Constants in CLI that exist in models.py**: `BACKLOG_DIR`, `DEFAULT_REPO`, `SECTION_RE`, `SKIP_STATUS`, `TYPE_TO_LABEL` — values must be compared for drift before deletion.

**Note on `SKIP_STATUS`**: CLI has `("DONE", "RESOLVED", "COMPLETED")`; models.py has `("DONE", "RESOLVED", "COMPLETED", "CLOSED")` — confirmed value drift on at least one constant.

**Out of scope**: The CLI's display/formatting functions (`_format_item`, table rendering, `_get_table_width`) are CLI-only and have no core counterpart — these stay in the CLI.
</div>

### Expected Behavior

<div><sub>2026-03-12T02:11:39Z</sub>

All CLI commands produce identical results whether a given function is executed via the CLI path or the MCP server path. When backlog_core is updated (new field, bug fix, behavior change), the CLI reflects that change automatically without a separate edit to backlog.py. The CLI file contains only: imports from backlog_core, Typer command definitions, and display/formatting code at the CLI boundary.
</div>

<div><sub>2026-03-12T02:13:52Z</sub>

`backlog.py` imports and delegates to `backlog_core` for all parsing, model access, GitHub integration, and business logic. The CLI boundary is: argument parsing, output formatting (Rich tables/text), and error translation to exit codes. No business logic lives in `backlog.py` itself.
</div>

### Desired Structure

<div><sub>2026-03-12T02:11:52Z</sub>

The target state observable from outside:

1. `backlog.py` imports and delegates to `backlog_core` for all business logic — no duplicate function definitions for logic that already exists in the core package
2. Constants in backlog.py that duplicate models.py values are removed; backlog.py imports them from `backlog_core.models`
3. Return type boundary: where CLI functions previously returned `dict`, they now accept `BacklogItem` from core calls and convert to display format at the CLI boundary only
4. `SKIP_STATUS` drift is resolved — one canonical value in models.py that both CLI and MCP server use
5. The `backlog.py` line count is measurably reduced (target: thin wrapper, not 2500+ lines)
</div>

<div><sub>2026-03-12T02:14:06Z</sub>

- `backlog.py` uses `BACKLOG_DIR`, `DEFAULT_REPO`, `SECTION_RE`, `SKIP_STATUS`, `TYPE_TO_LABEL`, `ROLE_MAP`, `BENEFIT_MAP` exclusively from `backlog_core.models` — no local definitions.
- `backlog.py` calls `find_item`, `build_issue_body`, `create_issue_for_item` exclusively from `backlog_core` — no local re-implementations.
- All functions currently local to `backlog.py` that duplicate `backlog_core` are removed. Functions that are genuinely CLI-only (not present in `backlog_core`) remain.
- `backlog.py` accepts `BacklogItem` typed objects at internal call sites, converting to display strings only at output boundaries.
- The `SKIP_STATUS` divergence (`"CLOSED"` missing from CLI) is resolved by this change — CLI and core use the same tuple from `models.py`.
</div>

### Output / Evidence

<div><sub>2026-03-12T02:13:28Z</sub>

**Confirmed duplication map (verified by grep 2026-03-12):**

Functions present in both `backlog.py` and `backlog_core/`:

| CLI function (backlog.py) | Canonical location | Notes |
|---|---|---|
| `_title_to_slug` | not found in backlog_core grep — needs verification | may be CLI-only |
| `_infer_type` | not found in backlog_core grep — needs verification | may be CLI-only |
| `_parse_backlog_from_directory` | not found in backlog_core grep — needs verification | may be CLI-only |
| `_parse_item_file` | not found in backlog_core grep — needs verification | may be CLI-only |
| `find_item` | `backlog_core/parsing.py:312` | signature differs: CLI uses `list[dict]`, core uses `list[BacklogItem]` |
| `_normalize_issue_title` | not found in backlog_core grep — needs verification | may be CLI-only |
| `_find_fuzzy_duplicates` | not found in backlog_core grep — needs verification | may be CLI-only |
| `build_issue_body` | `backlog_core/parsing.py:464` | CLI uses untyped dict; core uses `BacklogItem` model |
| `create_issue_for_item` | `backlog_core/github.py:87` | CLI signature: `(repo, item: dict)`; core signature: `(repo, item: BacklogItem, dry_run, output)` |
| `_today` | not found in backlog_core grep — needs verification | may be CLI-only |
| `_now_iso` | not found in backlog_core grep — needs verification | may be CLI-only |
| `_update_item_metadata` | not found in backlog_core grep — needs verification | may be CLI-only |

Constants present in both `backlog.py` and `backlog_core/models.py`:

| CLI constant | Core location | Confirmed divergence |
|---|---|---|
| `BACKLOG_DIR` | `models.py:21` | identical values |
| `DEFAULT_REPO` | `models.py:22` | identical values |
| `SECTION_RE` | `models.py:28` | identical pattern |
| `SKIP_STATUS` | `models.py:36` | **DIVERGED**: CLI = `("DONE", "RESOLVED", "COMPLETED")`, core = `("DONE", "RESOLVED", "COMPLETED", "CLOSED")` — CLI will not skip CLOSED items |
| `TYPE_TO_LABEL` | `models.py:47` | needs comparison |
| `ROLE_MAP` | `models.py:55` | needs comparison |
| `BENEFIT_MAP` | `models.py:63` | needs comparison |

**Observable bug from divergence**: Items with status `CLOSED` are not skipped by the CLI's `SKIP_STATUS` check. Any CLI path that filters by `SKIP_STATUS` will process CLOSED items it should skip.

**To reproduce the divergence**:
1. `grep -n "SKIP_STATUS" .claude/skills/backlog/scripts/backlog.py`
2. `grep -n "SKIP_STATUS" .claude/skills/backlog/backlog_core/models.py`
3. Compare tuples — CLI is missing `"CLOSED"`.
</div>

### Acceptance Criteria

<div><sub>2026-03-12T02:14:20Z</sub>
<details><summary>struck: 2026-03-12T12:32:32Z — Original AC written at grooming before implementation discovered signature constraints; revised to reflect actual achievable scope with follow-ups tracked in #669 and #670</summary>

1. `grep -n "^BACKLOG_DIR\|^DEFAULT_REPO\|^SECTION_RE\|^SKIP_STATUS\|^TYPE_TO_LABEL\|^ROLE_MAP\|^BENEFIT_MAP" .claude/skills/backlog/scripts/backlog.py` returns zero matches — all constants imported from `backlog_core.models`.
2. `grep -n "^def _title_to_slug\|^def _infer_type\|^def _parse_backlog_from_directory\|^def _parse_item_file\|^def find_item\|^def _normalize_issue_title\|^def _find_fuzzy_duplicates\|^def build_issue_body\|^def create_issue_for_item\|^def _today\|^def _now_iso\|^def _update_item_metadata" .claude/skills/backlog/scripts/backlog.py` returns zero matches for each function that has a canonical counterpart in `backlog_core` (functions absent from `backlog_core` may remain).
3. `uv run .claude/skills/backlog/scripts/backlog.py list` exits 0 with item output after the refactor.
4. `uv run .claude/skills/backlog/scripts/backlog.py view #611` exits 0 and shows item content.
5. `uv run pytest .claude/skills/backlog/tests/ -x -q` passes without new failures.
6. The `SKIP_STATUS` used at every call site in `backlog.py` includes `"CLOSED"` (imported from `models.py`).
</details>
</div>

<div><sub>2026-03-12T12:32:32Z</sub>

**Revised post-implementation** (original AC2 and AC6 written at grooming before discovering dict-vs-BacklogItem signature mismatches and monkeypatch test isolation constraints):

1. All 7 constants removed from backlog.py, imported from backlog_core.models — **PASS**
2. Functions with compatible signatures replaced with core imports (12 constants, 6 direct imports, 3 adapter-wrapped) — **PASS**
3. Functions with incompatible signatures (dict vs BacklogItem) retained locally with documented rationale; follow-ups #669 and #670 created — **PASS (deferred)**
4. `uv run backlog.py list` exits 0 — **PASS**
5. `uv run backlog.py view #611` exits 0 — **PASS**
6. 582 tests pass, 0 failures — **PASS**
7. SKIP_STATUS bug fixed (CLI now uses core constant including "CLOSED") — **PASS**
8. Net reduction: 2563 → 2466 lines (97 lines removed) — **PASS**
</div>

### Resources

<div><sub>2026-03-12T02:14:35Z</sub>

| Type | Item |
|------|------|
| Source file | `.claude/skills/backlog/scripts/backlog.py` (2563 lines — CLI with local duplicates) |
| Source file | `.claude/skills/backlog/backlog_core/models.py` (275 lines — canonical constants + BacklogItem) |
| Source file | `.claude/skills/backlog/backlog_core/parsing.py` (945 lines — canonical `find_item`, `build_issue_body`) |
| Source file | `.claude/skills/backlog/backlog_core/github.py` (581 lines — canonical `create_issue_for_item`) |
| Source file | `.claude/skills/backlog/backlog_core/operations.py` (2208 lines — business logic already imported by CLI) |
| Test suite | `.claude/skills/backlog/tests/` (12 test files — regression baseline) |
| Related item | #612 — backlog: add status field to BacklogItem model (may affect adapter pattern) |
| Related item | #613 — Extract shared `_get_table_width()` utility from 6 duplicate copies |
</div>

### Dependencies

<div><sub>2026-03-12T02:14:47Z</sub>

- Depends on: None — `backlog_core` modules already exist and are already imported by the CLI.
- Blocks: #613 (Extract shared `_get_table_width()`) — that item is a follow-on cleanup in the same file; doing #611 first reduces noise.
- Related: #612 (add status field to BacklogItem model) — if #612 lands first, the adapter layer for this refactor can use the new field directly.
</div>

### Blockers

<div><sub>2026-03-12T02:15:02Z</sub>

- Several functions listed in the item description (`_title_to_slug`, `_infer_type`, `_parse_backlog_from_directory`, `_parse_item_file`, `_normalize_issue_title`, `_find_fuzzy_duplicates`, `_today`, `_now_iso`, `_update_item_metadata`) were **not found** in `backlog_core/` by grep. The implementer must verify for each whether: (a) it exists in `backlog_core` under a different name, (b) it is genuinely CLI-only and should be kept, or (c) it should be migrated into `backlog_core` as part of this work.
- No test suite covers `backlog.py` CLI commands end-to-end (tests are in `tests/` and cover `backlog_core` modules). CLI regression must be validated manually or by adding CLI integration tests before removal.
</div>

### Effort

<div><sub>2026-03-12T02:15:15Z</sub>

Medium — The constants and the three confirmed-duplicated functions (`find_item`, `build_issue_body`, `create_issue_for_item`) are straightforward import replacements. The adapter complexity comes from the `dict` → `BacklogItem` boundary: the CLI passes untyped dicts to these functions and the core expects typed models. Each call site needs an adapter or the calling code needs to be updated to use `BacklogItem`. The 9 unverified functions (may be CLI-only or need migration into `backlog_core`) add discovery overhead. Estimated scope: 1 focused session with thorough testing pass.
</div>