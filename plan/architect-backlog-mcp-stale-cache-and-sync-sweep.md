> **SUPERSEDED — DO NOT IMPLEMENT THIS DESIGN.** Current authority: [`backlog_core/ARCHITECTURE.md`](../plugins/development-harness/backlog_core/ARCHITECTURE.md) and [`architect-backlog-snapshot-reconciliation.md`](./architect-backlog-snapshot-reconciliation.md). Invalid assumption: **universal YAML** is the storage authority.

# Architecture Spec: Backlog MCP Cache Coherence and Sync Contract Fix

**Item:** #2452
**Status:** ARCHITECTURE_COMPLETE
**Agent:** python-engineering:python-cli-design-spec
**Date:** 2026-05-24

---

## 1. Executive Summary

Two observable failures caused by a single root-cause class: the local YAML cache is treated as
the source of truth for section content even when a live backend connection is available.

**Failure 1 (stale sections_index):** `view_item` seeds `result.sections` and `sections_index`
from the local YAML cache (`parse_backlog`), then enriches only `result.body` from GitHub.
`_assemble_view_content` builds `sections_index` from `item.sections` (local), ignoring the
freshly-fetched live body. After concurrent `backlog_groom` writes (which each write to GitHub
correctly but race on the local YAML via read-modify-write), subsequent `backlog_view` calls see
only whichever agent's local YAML write landed last.

**Failure 2 (phantom `flush_only` parameter):** `finally.md` instructs callers to invoke
`backlog_sync(flush_only=true)`. This parameter does not exist in the MCP tool schema.
The MCP server drops unknown kwargs silently, resolving to `backlog_sync()` with no arguments,
which runs a full bidirectional sweep of all 321 issues. The documented operation ("export
current state to JSONL") has never existed as code. `groom_item` already syncs every write
to GitHub at write time, so the finalization step's stated purpose is redundant.

**Fix strategy:**

- **Failure 1:** Extend `_assemble_view_content` in `operations.py` so that when
  `view_enrich_from_github` succeeded and populated `result.body` from the live backend,
  sections and `sections_index` are derived from the live body rather than from `item.sections`.
  This is a single-file change in `operations.py`. No backend protocol extension required.

- **Failure 2:** Update `finally.md` to remove the phantom `backlog_sync(flush_only=true)`
  call and replace it with the correct finalization pattern. Since `groom_item` already pushes
  each write to GitHub synchronously, no separate flush is needed. The replacement is
  `backlog_pull(selector=<item_ref>)` to refresh local cache, or no-op if the agent can confirm
  all writes succeeded. Document the JSONL claim as aspirational-never-implemented.

---

## 2. Architecture Overview

### C4 Context Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Claude Code Session                       │
│                                                             │
│  Orchestrator Agent ──────► backlog_view (MCP tool)         │
│       │                          │                          │
│  Subagent Groomers ──────► backlog_groom (MCP tool)         │
│                                  │                          │
└──────────────────────────────────┼─────────────────────────┘
                                   │
                    ┌──────────────▼────────────────┐
                    │    backlog_core MCP Server     │
                    │    (server.py)                 │
                    │                                │
                    │  ┌────────────┐  ┌──────────┐ │
                    │  │operations  │  │BacklogBknd│ │
                    │  │  .py       │  │Protocol   │ │
                    │  └─────┬──────┘  └────┬─────┘ │
                    └────────┼──────────────┼────────┘
                             │              │
              ┌──────────────▼──┐    ┌──────▼───────┐
              │ Local YAML Cache │    │ GitHub Issues │
              │ ~/.dh/projects/  │    │ (authoritative│
              │  {slug}/backlog/ │    │  source)      │
              └──────────────────┘    └───────────────┘
```

### Container Diagram — Affected Components

```
operations.py
├── view_item()                    ← MODIFIED: sections source logic
│   ├── find_item(parse_backlog()) ← reads local YAML (unchanged)
│   ├── view_enrich_from_github()  ← fetches live body (unchanged)
│   └── _assemble_view_content()   ← MODIFIED: prefer live body for sections
│
gh_client.py
└── view_enrich_from_github()      ← unchanged; already sets result.body
    (github backend calls this)

skills/work-backlog-item/references/workflows/groom/finally.md
└── MODIFIED: remove phantom flush_only call, document correct pattern
```

### Data Flow — Before Fix (Failure 1)

```
view_item(selector="#2452")
  1. parse_backlog() → item with item.sections = {last-writer's sections only}
  2. view_enrich_from_github() → result.body = <full live body from GitHub>
  3. _assemble_view_content():
       if item and item.sections:          ← TRUE (uses local YAML)
           sections_index = _render_section_index(item)  ← STALE
       # result.body (live) is used for entry content, but sections_index
       # is built from item.sections (local YAML) — MISMATCH
```

### Data Flow — After Fix (Failure 1)

```
view_item(selector="#2452")
  1. parse_backlog() → item (local YAML, potentially stale)
  2. view_enrich_from_github() → result.body = <full live body from GitHub>
                                  enriched = True
  3. _assemble_view_content(enriched=True):
       if result.body:                      ← TRUE (live body)
           sections derived from live body  ← CURRENT (all sections)
           sections_index built from body   ← CONSISTENT with body
       # item.sections used only as fallback when backend unreachable
```

---

## 3. Technology Stack

No new dependencies. All changes operate within the existing stack:

| Component | Technology | Justification |
|---|---|---|
| Section parsing | Existing `_build_sections_compact` / `_build_sections_metadata` in `operations.py` | Already parses sections from raw body string; no new code needed |
| Backend dispatch | Existing `BacklogBackend` Protocol via `get_config().backend` | No Protocol extension required — fix is in `operations.py` |
| Workflow docs | Markdown | `finally.md` is corrected in place |

---

## 4. Component Design

### 4.1 `_assemble_view_content` — Modified

**Location:** `plugins/development-harness/backlog_core/operations.py`

**Current signature (unchanged):**

```python
def _assemble_view_content(
    result: ViewItemResult,
    item: BacklogItem | None,
    *,
    include_content: bool,
    section: str | None,
    show: str | int | None,
    since: str | None,
    offset: int,
    limit: int,
) -> None:
```

**Problem:** When `result.body` is populated from live GitHub (enrichment succeeded), the function
still builds `sections_index` from `item.sections` (local YAML). These two sources are
inconsistent after concurrent writes.

**Fix — logic change (not signature change):**

The function must check whether `result.body` is populated (indicating live enrichment succeeded)
before falling back to `item.sections`. The rule:

> When `result.body` is non-empty, derive all section information from `result.body`.
> Fall back to `item.sections` only when `result.body` is empty (offline / no issue number).

Concretely, in the `not include_content` (summary mode) branch:

```python
# BEFORE (schematic):
if body:
    result.sections_metadata = [... from _build_sections_compact(body) ...]
elif item and item.sections:
    _populate_yaml_item_compact(result, item)
if item and item.sections:
    index = _render_section_index(item)  # ← BUG: always uses local YAML
    if index:
        result.sections_index = index

# AFTER (schematic):
if body:
    result.sections_metadata = [... from _build_sections_compact(body) ...]
    index = _build_sections_index_from_body(body)  # NEW helper
    if index:
        result.sections_index = index
elif item and item.sections:
    _populate_yaml_item_compact(result, item)
    index = _render_section_index(item)
    if index:
        result.sections_index = index
```

In the `include_content` branch (analogous fix):

```python
# BEFORE (schematic):
if body:
    result.sections = _build_sections_metadata(body, show, since)
    if item and item.sections:               # ← BUG: unconditional local prepend
        index = _render_section_index(item)
        if index:
            result.body = index + "\n" + body

# AFTER (schematic):
if body:
    result.sections = _build_sections_metadata(body, show, since)
    index = _build_sections_index_from_body(body)  # NEW helper
    if index:
        result.body = index + "\n" + body
    # item.sections no longer used when body is available
elif item and item.sections:
    _populate_yaml_item_content(result, item, section)
```

### 4.2 `_build_sections_index_from_body` — New Private Helper

**Location:** `plugins/development-harness/backlog_core/operations.py`

**Purpose:** Build the `sections_index` string from a raw issue body string. Replaces the
`_render_section_index(item)` call when live body is available.

**Signature:**

```python
def _build_sections_index_from_body(body: str) -> str:
    """Build a sections_index string from a raw GitHub issue body.

    Parses the body for section headers and entry counts using the existing
    _build_sections_compact primitive. Returns the formatted index string
    in the same format as _render_section_index(item).

    Args:
        body: Raw issue body string (from GitHub or backend).

    Returns:
        Formatted section index string, e.g.:
        "[0] Acceptance Criteria (3 entries)\\n[1] Risk Summary (1 entry)\\n"
        Returns empty string when body has no recognizable sections.
    """
```

**Contract:**
- Input: raw body string (may be empty)
- Output: formatted `sections_index` string matching the format of `_render_section_index`
- Delegates to `_build_sections_compact(body)` for section detection
- Returns `""` for empty body or no sections found
- Must not raise; returns `""` on any parse failure

**Implementation notes for the implementor:**
- Call `_build_sections_compact(body)` — already tested and handles all section formats
- Format each section as `[N] {name} ({count} entries)` to match existing `_render_section_index` output
- Singular "entry" vs plural "entries" must match existing format

### 4.3 `view_item` — Unchanged Signature

`view_item` signature is NOT changed. The fix is entirely within `_assemble_view_content` and
the new `_build_sections_index_from_body` helper. No callers change.

### 4.4 `finally.md` — Documentation Fix

**Location:**
`plugins/development-harness/skills/work-backlog-item/references/workflows/groom/finally.md`

**Current Step 1 (REMOVE):**

```markdown
1. **Sync state**: call `mcp__plugin_dh_backlog__backlog_sync(flush_only=true)` to export
   current state to JSONL. This ensures any status changes (blocked, groomed) are persisted
   regardless of how the workflow exited.
```

**Replacement Step 1:**

```markdown
1. **Confirm state is persisted**: `backlog_groom` writes each section to GitHub synchronously
   at write time — no separate flush is needed. If the workflow wrote any sections, they are
   already on GitHub. To refresh the local cache to match GitHub (e.g., after a multi-agent
   groom session), call `mcp__plugin_dh_backlog__backlog_pull(selector=<item_ref>)`.
   Do NOT call `backlog_sync()` — that runs a full sweep of all issues and is expensive.
```

**ADR note to include in doc:** The `flush_only` parameter and "JSONL export" operation
referenced in the previous version of this step were aspirational and never implemented.
They were removed in the fix for #2452.

### 4.5 `backlog_sync` MCP Tool — Unknown Kwarg Rejection

**Location:** `plugins/development-harness/backlog_core/server.py`

**Current behavior:** Unknown kwargs passed to `backlog_sync` are silently dropped by the
MCP/pydantic schema layer, masking the misdocumented call as a silent no-op substitute.

**Prescribed behavior:** The MCP framework (FastMCP + pydantic) should reject unknown parameters
with a schema validation error rather than silently dropping them. This is a **separate concern**
from the doc fix — addressed via a follow-up backlog item, not this spec. The immediate fix
(correcting `finally.md`) eliminates the symptom. Schema hardening prevents recurrence.

**Out of scope for this spec.** File a follow-up item: "MCP server: enable strict kwargs
validation to reject unknown parameters at the tool schema boundary."

---

## 5. Data Architecture

### 5.1 No New Data Models

No new models, no schema changes. `ViewItemResult` fields are unchanged:

```python
# Existing fields (operations.py / models.py) — unchanged
@dataclass
class ViewItemResult:
    item: BacklogItem | None = None
    issue_number: int | None = None
    title: str = ""
    priority: str = ""
    status: str = ""
    groomed: str = ""
    sections_index: str = ""      # ← populated from live body when available
    body: str = ""                # ← populated by view_enrich_from_github (live)
    sections: dict[str, Section] = field(default_factory=dict)
    sections_metadata: list[SectionMeta] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
```

### 5.2 Section Data Flow — Source Priority

After the fix, the source priority for section information is:

| `result.body` state | `sections_index` source | `sections` / `sections_metadata` source |
|---|---|---|
| Non-empty (live enrichment succeeded) | Parsed from `result.body` via new helper | Parsed from `result.body` |
| Empty (backend unreachable / no issue) | Built from `item.sections` (local YAML) | From `item.sections` (local YAML) |
| Empty (item has no sections at all) | `""` | `{}` |

### 5.3 Staleness Warning Contract

When `result.body` is empty because the backend is unreachable and the server used local YAML
as fallback, `result.warnings` must include a staleness marker:

```
"backend unreachable — sections_index reflects local cache, may be stale"
```

This allows downstream agents to detect and react to the degraded read.

**Where to add the warning:** In `view_item`, after `view_enrich_from_github` returns `False`
AND `item` is not None (offline fallback path). This is a new warning insertion at the existing
call site.

---

## 6. Type System Design

### 6.1 No New Types Required

The fix operates entirely within existing types. No new `NewType`, `Protocol` extension, or
`TypedDict` is needed.

### 6.2 Domain Identifier Audit — Affected Types

| Identifier | Type | Validation Boundary | Notes |
|---|---|---|---|
| `body: str` on `ViewItemResult` | `str` | Set by `view_enrich_from_github` (live) or empty | No change — already typed |
| `sections_index: str` | `str` | Set in `_assemble_view_content` | Fix changes the source, not the type |
| Section headers parsed from body | `str` | Inside `_build_sections_compact` | Existing parser handles all formats |

### 6.3 Return Type — `_build_sections_index_from_body`

```python
def _build_sections_index_from_body(body: str) -> str: ...
```

Pure function. `str` → `str`. No `Any`, no `object`, no `cast()`.

### 6.4 Weak Type Audit

No `Any`, `cast()`, or unchecked conversions introduced by this fix. The helper function
accepts and returns `str`. The enrichment result is already typed as `ViewItemResult`.

---

## 7. Security Architecture

This fix does not change authentication, authorization, or credential management.
Existing security properties are retained:

- GitHub credentials accessed via `try_get_github` / `get_github` (unchanged)
- No new network endpoints
- No new file paths written
- `finally.md` doc fix removes a call that was triggering unintended side effects
  (full issue sweep), which is a reduction in unintended write surface

---

## 8. Testing Architecture

### 8.1 Strategy

Three new test files. All follow the existing fixture and naming conventions documented in the
codebase analysis. All tests are **unit-level** — they use `mocker.patch` / `mock_github` to
simulate backend state without network calls.

The concurrent-write scenario is simulated by manually writing conflicting local YAML state
then asserting the live-body path corrects it. True concurrency tests are impractical in
a unit suite and not needed: the fix is in the read path (live body takes precedence), not
in locking.

### 8.2 Required Test Files

#### `backlog_core/tests/test_view_live_sections.py` — Failure 1 regression

**Test class:** `TestViewItemSectionsCoherence`

| Test name | What it verifies |
|---|---|
| `test_view_returns_sections_from_live_body_when_enrichment_succeeds` | When `view_enrich_from_github` returns a body with N sections, `sections_index` contains all N sections (not local YAML subset) |
| `test_view_returns_local_sections_when_backend_unreachable` | When `view_enrich_from_github` returns `False`, `sections_index` reflects local YAML and `warnings` contains the staleness message |
| `test_view_sections_index_matches_body_content` | `sections_index` and body section headers are consistent — no heading in `sections_index` absent from `body` |
| `test_concurrent_writes_do_not_cause_stale_sections_index` | Simulates two agents writing different sections to local YAML (last-writer race); live body has all sections; `sections_index` reflects live body |

**Required fixture overrides:**

```python
# Override mock_github default to simulate live enrichment
mock_github["view_enrich_from_github"].return_value = True

# Also mock the actual body that enrichment puts on result
# (requires patching at operations.py boundary, not gh_client)
```

**Key observation (Concern 1 from codebase-analysis):** The `mock_github` fixture defaults
`view_enrich_from_github` to `return_value=False` (no enrichment). All new tests exercising
the live-body path MUST explicitly set `return_value=True` AND also configure what body content
`view_enrich_from_github` writes to `result`. This requires a custom `side_effect` that mutates
the `result` argument.

**Side effect pattern:**

```python
def _enrich_with_live_body(result, issue_num, repo=""):
    result.body = LIVE_BODY_WITH_ALL_SECTIONS
    result.number = 2452
    return True

mock_github["view_enrich_from_github"].side_effect = _enrich_with_live_body
```

#### `backlog_core/tests/test_sync_scope.py` — Failure 2 regression

**Test class:** `TestFinallyWorkflowFinalization`

| Test name | What it verifies |
|---|---|
| `test_backlog_sync_has_no_flush_only_parameter` | `backlog_sync` MCP tool schema does not expose `flush_only` parameter (schema introspection test) |
| `test_sync_items_always_sweeps_all_items` | `sync_items()` with no arguments calls `sync_create_missing_issues` and `sync_push_groomed_content` on all items — confirms the sweep behavior that finally.md was inadvertently triggering |
| `test_finally_md_does_not_reference_flush_only` | File content check: `finally.md` does not contain `flush_only` string after the doc fix |
| `test_backlog_pull_selector_refreshes_single_item` | `backlog_pull` with a selector only fetches the targeted item (validates the replacement instruction in updated finally.md) |

#### `backlog_core/tests/test_concurrent_writes.py` — Integration scenario

**Test class:** `TestConcurrentGroomWriteRace`

| Test name | What it verifies |
|---|---|
| `test_second_groom_write_does_not_clobber_first_sections_on_view` | Arrange: write section A to local YAML; arrange: write only section B to local YAML (simulating race where second writer did not see first's write); arrange: live body has both A and B; act: `view_item`; assert: `sections_index` has both A and B |
| `test_offline_fallback_emits_staleness_warning` | When backend unreachable and local YAML has partial sections, `view_item` returns `warnings` containing the staleness string |

### 8.3 Fixture Reuse

All new tests use existing fixtures from `tests/conftest.py`:

| Fixture | Purpose |
|---|---|
| `backlog_dir` | Isolate YAML state to tmp dir |
| `write_test_item` | Create pre-populated YAML items |
| `mock_github` | Patch all GitHub operations at `backlog_core.operations` boundary |
| `mocker` (pytest-mock) | `side_effect` for enrichment simulation |

### 8.4 Coverage Targets

| Module | Target |
|---|---|
| `operations.py` — `_assemble_view_content` | 90% branch (existing + new live-body branches) |
| `operations.py` — `_build_sections_index_from_body` | 95% (pure function, all branches exercised) |
| `finally.md` doc correctness | 100% (file content assertion) |

---

## 9. Distribution Architecture

No distribution changes. This fix is internal to `backlog_core`. The MCP server is deployed
as a PEP 723 script (`run_backlog_server.py`) — existing deployment unchanged. No new
dependencies, no new entry points, no packaging changes.

---

## 10. Architectural Decisions (ADRs)

### ADR-001: Failure 1 — Extend `_assemble_view_content` (not `view_enrich_from_github`)

**Context:** The stale `sections_index` bug has three candidate fix paths:
- A. Extend `view_enrich_from_github` to refresh `sections`/`sections_index` in all 4 backend implementations
- B. Call `pull_by_selector` inline in `view_item` before building `sections_index`
- C. Serialize concurrent write path (fix race at write time rather than read time)

**Decision:** Path A — extend `_assemble_view_content` to prefer `result.body` over
`item.sections` when body is non-empty. This is a single change in `operations.py`.

**Rejection of Path B (`pull_by_selector`):**
`pull_by_selector` always makes a network call and writes the fetched content to the local
YAML file (via `_pull_item` → `_pull_item_update_existing`). Calling it from inside `view_item`
would:
1. Add a full network round-trip + file write to every `backlog_view` call
2. Introduce re-entrant side effects (file writes) inside a read operation
3. Double the network cost: `pull_by_selector` fetches the body, then `view_enrich_from_github`
   also fetches the body — two GraphQL calls per view
`pull_by_selector` is designed as an explicit user-invoked operation, not an implicit read helper.

**Rejection of Path C (write serialization):**
Serializing writes at the `backlog_groom` level would require a file lock or merge-on-write
mechanism. This addresses the race condition's mechanism but not the immediate symptom: even
with fully serialized writes, a stale local YAML from a previous session would still be
preferred over the live body. The read path must be fixed regardless.

**Consequence:** The approach modifies `_assemble_view_content` and adds one private helper
(`_build_sections_index_from_body`). No backend protocol change. No new network calls.
The live body (already fetched by `view_enrich_from_github`) is parsed for sections — no
additional API cost.

**Q1 resolution (read coherence model):** When the backend is reachable and enrichment
succeeds, `result.body` is populated. `_assemble_view_content` uses `result.body` as the
authoritative section source. This gives "always-refresh for items with issue numbers when
connected" semantics without any extra network call, because `view_enrich_from_github`
already performs the fetch. Items without issue numbers (YAML-only items) are unaffected.

---

### ADR-002: Failure 1 — Offline Fallback Uses Local Cache with Explicit Warning

**Context:** Q2 — when the backend is unreachable, should `view_item` fail hard, degrade
silently, or degrade with an explicit warning?

**Decision:** Degrade gracefully with an explicit machine-detectable warning in `result.warnings`.

**Rationale:** Hard failure breaks offline workflows. Silent fallback recreates the bug class
(agents can't tell they're reading stale data). An explicit warning in the standard `warnings`
field allows downstream agents to inspect `warnings` and adapt their routing decisions.

**Warning text:** `"backend unreachable — sections_index reflects local cache, may be stale"`

**Q2 resolution:** Cache fallback with `warnings` entry — Option B from the feature-context.

---

### ADR-003: Failure 1 — Scope Limited to `view_item` / `backlog_view`

**Context:** Q3 — should the coherence fix apply to all read paths (`backlog_list`, etc.)?

**Decision:** This spec scopes the fix to `_assemble_view_content` (called only by `view_item` /
`backlog_view`). `backlog_list` uses a separate code path and is out of scope.

**Rationale:** The bug was observed specifically on `backlog_view(summary=True)`. Extending the
fix to all read paths increases blast radius and testing surface without confirmed evidence of
the same failure on `list`. A follow-up backlog item should audit `backlog_list` coherence.

**Q3 resolution:** Scoped to `view_item`. File follow-up: "audit backlog_list for same
cache-vs-live coherence gap."

---

### ADR-004: Failure 1 — Write Path Not Fixed in This Spec

**Context:** Q4 — should the write path (`backlog_groom`) be made atomic with the local cache?

**Decision:** Write path race is out of scope for this spec.

**Rationale:** The observed symptom (stale `sections_index`) is fully resolved by the read-path
fix — when `result.body` is live, local YAML staleness is irrelevant to the returned
`sections_index`. Write-path atomicity is a separate concern that would require file locking
or merge-on-write. The risk of that complexity exceeds the benefit given the read-path fix
provides correct behavior for all connected reads.

**Q4 resolution:** Read-path-only fix. File follow-up: "backlog_groom: consider atomic
local-YAML update with merge semantics to prevent last-writer-wins race in offline mode."

---

### ADR-005: Failure 2 — Update `finally.md` (Path B), Not Implement `flush_only`

**Context:** Q5 — implement `flush_only` parameter or correct the documentation?

**Decision:** Path B — update `finally.md` only. No code change to `backlog_sync` or
`sync_items`.

**Rationale:**
1. `groom_item` already calls `_write_groomed_to_github` → `sync_groomed_to_github_issue`
   synchronously on every write. Each section written by each agent is already on GitHub
   before the agent returns. No separate "flush" is needed.
2. The "export to JSONL" operation mentioned in the original `finally.md` has never existed
   as code. Adding `flush_only` would implement a novel operation to match an aspirational doc.
3. Implementing `flush_only` on `backlog_sync` requires deciding what "pending items" means
   without a dirty bit — either a diff against GitHub (expensive) or a heuristic (unreliable).
   Neither option is justified when the problem is a documentation error.
4. Path B has zero code risk: one markdown file changes, existing behavior is unchanged.

**Consequence for the silent-kwarg-drop concern:** The immediate symptom (expensive sync on
finalization) is resolved by removing the bad call from `finally.md`. The systemic risk
(MCP server silently drops unknown kwargs) remains. A follow-up item is filed:
"MCP server: enable strict parameter validation to reject unknown kwargs at schema boundary."

**Q5 resolution:** Path B (doc-only fix) with a follow-up item for schema hardening.

---

### ADR-006: Failure 2 — JSONL Export Aspirational, Not Implemented

**Context:** Q6 — what did "export current state to JSONL" mean?

**Decision:** The operation was aspirational and never implemented. The doc is corrected to
remove the claim. No JSONL export mechanism is added in this spec.

**Q6 resolution:** Aspirational claim removed from documentation.

---

### ADR-007: Local YAML Cache Retains Its Role as a Derivative Cache

**Context:** Q7 — is the local YAML an authoritative artifact or a transient cache?

**Decision:** Local YAML remains a derivative cache, not a primary artifact. GitHub Issues
is the authoritative source. The local YAML exists for offline workflows, performance, and
local tooling (`parse_backlog`). After this fix, connected reads always prefer GitHub body
for section data, but local YAML remains the seed for items without issue numbers.

**Q7 resolution:** Local YAML is a cache; GitHub is authoritative when reachable.

---

## 11. Scalability Strategy

This fix has no scalability implications beyond the specific improvement it makes:

- **Before:** Every `finally.md` groom finalization triggered a 321-issue full sweep.
- **After:** No sweep occurs at finalization. Per-view API cost is zero additional calls
  (live body was already fetched by `view_enrich_from_github`; sections are parsed from
  the in-memory body string — no extra network call).
- **Async patterns:** Unchanged. `view_item` remains synchronous; `backlog_view` MCP tool
  wraps it in `asyncio.to_thread` as before.
- **API rate limiting:** Reduced pressure — finalization no longer triggers bulk sweeps.
  Per-view cost remains one GraphQL call (already paid).

---

## Appendix A: Files to Modify

| File | Change type | Change scope |
|---|---|---|
| `plugins/development-harness/backlog_core/operations.py` | Logic fix | `_assemble_view_content` and new `_build_sections_index_from_body` helper |
| `plugins/development-harness/skills/work-backlog-item/references/workflows/groom/finally.md` | Doc fix | Step 1 text replacement |

## Appendix B: New Test Files

| File | Test class | Failure covered |
|---|---|---|
| `plugins/development-harness/backlog_core/tests/test_view_live_sections.py` | `TestViewItemSectionsCoherence` | Failure 1 |
| `plugins/development-harness/backlog_core/tests/test_sync_scope.py` | `TestFinallyWorkflowFinalization` | Failure 2 |
| `plugins/development-harness/backlog_core/tests/test_concurrent_writes.py` | `TestConcurrentGroomWriteRace` | Failure 1 (race scenario) |

## Appendix C: Follow-Up Items to File

1. **MCP strict kwargs validation:** Enable schema-level rejection of unknown parameters in
   `backlog_sync` and other MCP tools to prevent silent kwarg drops masking documentation errors.
2. **`backlog_list` coherence audit:** Verify whether `backlog_list` has the same
   cache-vs-live coherence gap as `backlog_view`.
3. **`backlog_groom` write-path merge:** Investigate atomic local YAML update with merge
   semantics to fix the last-writer-wins race in offline/degraded mode.

## Appendix D: Concerns (Quality Vigilance)

**Concern 1 — `_render_section_index` format consistency:**
The new `_build_sections_index_from_body` helper must produce output in exactly the same
format as `_render_section_index(item)`. If the formats diverge, callers that parse
`sections_index` (e.g., orchestrators reading `[N] Title (count)` lines) will break.
The implementor must verify the format against `_render_section_index` output before shipping.

**Concern 2 — `mock_github` fixture masks the bug by default:**
The existing `mock_github` fixture defaults `view_enrich_from_github` to `return_value=False`.
This means all existing tests that call `view_item` exercise the offline/local-cache path only.
New tests for the live-body path MUST use `side_effect` to both return `True` and mutate
`result.body`. A `mock_github_live` convenience fixture should be considered for the conftest
to document this pattern clearly.

**Concern 3 — No citation for "JSONL export" claim in original `finally.md`:**
The original `finally.md` referenced exporting to JSONL with no corresponding implementation.
This is a documentation-vs-code drift instance. The corrected doc should include an inline
note: "The `flush_only=true` reference and JSONL export claim were removed in #2452 — they
referenced a capability that was never implemented."

**Concern 4 — `include_content=True` branch in `_assemble_view_content` needs the same fix:**
The fix described above covers both the `not include_content` (summary mode) and
`include_content=True` branches. The implementor must address both branches, not just the
summary mode branch where the bug was observed. Missing the full-content branch would leave
a partial fix.
