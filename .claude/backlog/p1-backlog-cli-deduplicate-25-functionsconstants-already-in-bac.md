---
name: 'backlog CLI: deduplicate ~25 functions/constants already in backlog_core'
description: 'The CLI script `backlog.py` retains full duplicates of ~15 functions and ~10 constants that now have canonical implementations in `backlog_core/` (models.py, parsing.py, github.py). The CLI imports `backlog_core.operations` but then re-implements everything locally with untyped dicts.\n\nDuplicated items include: `_title_to_slug`, `_infer_type`, `_parse_backlog_from_directory`, `_parse_item_file`, `find_item`, `_normalize_issue_title`, `_find_fuzzy_duplicates`, `build_issue_body`, `create_issue_for_item`, `_today`, `_now_iso`, `_update_item_metadata`, plus constants BACKLOG_DIR, DEFAULT_REPO, SECTION_RE, SKIP_STATUS, TYPE_TO_LABEL, ROLE_MAP, BENEFIT_MAP.\n\nThe CLI should be a thin wrapper delegating to backlog_core, converting between typed models and CLI display at the boundary.\n\nDiscovered during code review session 2026-03-11.'
metadata:
  topic: backlog-cli-deduplicate-25-functionsconstants-already-in-bac
  source: Code review 2026-03-11
  added: '2026-03-11'
  priority: P1
  type: Refactor
  status: open
  issue: '#611'
  last_synced: '2026-03-12T02:11:52Z'
  groomed: '2026-03-12'
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

### Impact

<div><sub>2026-03-12T02:11:10Z</sub>

- Blocks: Every bug fix or model field addition in backlog_core must be duplicated manually in backlog.py to stay consistent
- Bottleneck: The CLI is the only consumer path for several backlog operations (CI, GitHub Actions `backlog-sync.yml`); divergence between CLI and core implementations means CLI callers silently get different behavior than MCP callers
- Scope: 12 duplicated functions confirmed by grep (lines 162–570 in backlog.py); constants BACKLOG_DIR, DEFAULT_REPO, SECTION_RE, SKIP_STATUS, TYPE_TO_LABEL, ROLE_MAP, BENEFIT_MAP also duplicated but not yet cross-checked for value drift
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

### Desired Structure

<div><sub>2026-03-12T02:11:52Z</sub>

The target state observable from outside:

1. `backlog.py` imports and delegates to `backlog_core` for all business logic — no duplicate function definitions for logic that already exists in the core package
2. Constants in backlog.py that duplicate models.py values are removed; backlog.py imports them from `backlog_core.models`
3. Return type boundary: where CLI functions previously returned `dict`, they now accept `BacklogItem` from core calls and convert to display format at the CLI boundary only
4. `SKIP_STATUS` drift is resolved — one canonical value in models.py that both CLI and MCP server use
5. The `backlog.py` line count is measurably reduced (target: thin wrapper, not 2500+ lines)
</div>