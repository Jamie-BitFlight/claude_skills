# Documentation Drift Audit Report

**Generated**: 2026-03-01
**Repository**: `/home/user/claude_skills`
**Spec**: `.claude/skills/backlog/backlog_core/ARCHITECTURE.md`

> **Note (2026-03-30)**: This audit was generated before the YAML migration (P964). Several
> findings are superseded:
> - FIND-21: `raw_body` field removed from `BacklogItem` in P964 — ARCHITECTURE.md updated in T4.
> - FIND-12: `build_backlog_frontmatter` (which used `import frontmatter`) is now deprecated;
>   retained only for test coverage. The `frontmatter` package dependency noted here is legacy.
> - New modules added in P964 (`yaml_io.py`, `github_sync.py`, `entry_blocks.py`) and new models
>   (`Entry`, `Section`, `GroomedData`) are documented in ARCHITECTURE.md as of T5.
>
> All other findings remain valid unless explicitly addressed in a subsequent audit.

**Analyzed Files**:

- Implementation: `backlog_core/__init__.py`, `backlog_core/models.py`, `backlog_core/parsing.py`, `backlog_core/gh_client.py`, `backlog_core/operations.py`, `backlog_core/server.py`
- Documentation: `.claude/skills/backlog/backlog_core/ARCHITECTURE.md`

**Git Timeline**:

- `89ab8b2` (2026-03-01) — initial implementation commit: created all six modules and updated ARCHITECTURE.md simultaneously
- `d79372b` (2026-03-01) — lint-fix commit: refactored `add_item` into private helpers in `operations.py`, minor `parsing.py` fix

The ARCHITECTURE.md spec was last touched in `89ab8b2`, the same commit that created the implementation. The `d79372b` commit added new private helper functions to `operations.py` without updating the spec. All drift originates from this second commit plus implementation deviations made during the initial commit.

---

## Executive Summary

- **Total Drift Items**: 24
- **Critical Mismatches**: 3
- **Implemented but Undocumented**: 12
- **Documented but Unimplemented**: 3
- **Outdated / Mismatched Details**: 9

---

## Findings by Category

---

### 1. Implemented but Undocumented

Features present in the code with no mention in ARCHITECTURE.md.

---

**FIND-1** — `Output.to_dict()` method not listed in spec

- **Priority**: Medium
- **Evidence**: `models.py:179-181`

```python
def to_dict(self) -> dict[str, list[str]]:
    """Return all collected messages as a dict (alias for model_dump)."""
    return self.model_dump()
```

- **Documentation Claim**: The spec shows the `Output` class with `info()`, `warn()`, `error()` methods only (`ARCHITECTURE.md:74-77`). The `to_dict()` method is not mentioned.
- **Code Reality**: `to_dict()` is defined and is a central part of how every public operation function merges output into its return dict: `return {**result, **out.to_dict()}`. This pattern appears in every public function in `operations.py` and every tool wrapper in `server.py`.
- **Recommendation**: Add `to_dict() -> dict[str, list[str]]` to the `Output` model description in the spec.

---

**FIND-2** — `ViewItemResult` has a `body_truncated`, `body_remaining_lines`, `body_total_lines` dynamic key pattern not in spec

- **Priority**: Medium
- **Evidence**: `operations.py:825-832`

```python
if remaining > 0:
    data["body_truncated"] = True
    data["body_remaining_lines"] = remaining
    data["body_total_lines"] = total
```

- **Documentation Claim**: `ViewItemResult` fields are listed in `ARCHITECTURE.md:199-216` (by inference from the Pydantic model snippet). No pagination metadata fields are mentioned in the spec or in the model definition.
- **Code Reality**: `view_item()` adds three ad-hoc keys to the returned dict when body content is paginated. These are not `ViewItemResult` model fields — they are injected post-`model_dump()`.
- **Recommendation**: Document the pagination metadata keys in the spec for `view_item()`.

---

**FIND-3** — Five private helper functions added to `operations.py` by `d79372b` have no mention in spec

- **Priority**: Low
- **Evidence**: `operations.py:532-628`, commit `d79372b`

Functions: `_check_for_duplicates`, `_resolve_filepath`, `_try_create_github_issue`, `_build_item_body`, `_write_local_item`.

- **Documentation Claim**: The spec (`ARCHITECTURE.md:175-186`) describes the private helpers as `_add_item_index_format()` → `part of add_item()` and `duplicate check logic from add command`. No decomposed private helpers are listed.
- **Code Reality**: `add_item()` was decomposed into five distinct private helpers during the lint-fix commit. The spec lists the old monolithic framing.
- **Recommendation**: Update the spec's operations.py private helper list to name these five functions.

---

**FIND-4** — `_resolve_groomed_content` helper not in spec

- **Priority**: Low
- **Evidence**: `operations.py:174-190`

```python
def _resolve_groomed_content(
    section: str | None, content: str | None, groomed_content: str | None, groomed_file: str | None
) -> tuple[str, str | None]:
```

- **Documentation Claim**: The spec (`ARCHITECTURE.md:182`) mentions `_resolve_groomed_content()` by name as a private helper under UPDATE. This is partially addressed, but the return type `tuple[str, str | None]` and `groomed_file` stdin fallback behavior are not described.
- **Code Reality**: The function has a stdin fallback (`sys.stdin.read()`) when all four arguments are `None`. This is a significant undocumented behavior — `sys.stdin` is imported for this case (`operations.py:11`).
- **Recommendation**: Add stdin fallback note to spec; document the `groomed_file` parameter path.

---

**FIND-5** — `_ensure_github_issue` helper not in spec

- **Priority**: Low
- **Evidence**: `operations.py:235-259`

- **Documentation Claim**: Not listed anywhere in the spec's private helper enumeration for UPDATE.
- **Code Reality**: Exists as a distinct function that creates a GitHub issue for items lacking one, used in `_handle_update_groomed`.
- **Recommendation**: Add to spec's private helper list for operations.py UPDATE section.

---

**FIND-6** — `_write_groomed_to_github` helper not in spec

- **Priority**: Low
- **Evidence**: `operations.py:261-288`

- **Documentation Claim**: Not listed anywhere in the spec.
- **Code Reality**: Exists as a distinct private function with graceful GitHub fallback behavior, used in `_handle_update_groomed`.
- **Recommendation**: Add to spec's private helper list for operations.py UPDATE section.

---

**FIND-7** — `_write_groomed_to_item_file` and `_handle_update_groomed` listed but return types/behavior not described

- **Priority**: Low
- **Evidence**: `operations.py:191-320`

- **Documentation Claim**: Spec (`ARCHITECTURE.md:182`) lists `_handle_update_groomed()` and `_write_groomed_to_item_file()` by name.
- **Code Reality**: `_handle_update_groomed` implements a GitHub-first write order (GitHub canonical, local file is cache) with four documented steps. `_write_groomed_to_item_file` handles both section-level incremental updates and full Groomed block replacement. Neither behavior is described in the spec.
- **Recommendation**: Add write-order contract and section vs full-block distinction to spec.

---

**FIND-8** — `_pull_item`, `_pull_item_create_new`, `_pull_item_update_existing` have no spec equivalent

- **Priority**: Low
- **Evidence**: `operations.py:414-530`

- **Documentation Claim**: Spec (`ARCHITECTURE.md:185`) lists `_pull_single_issue()` → `pull_single_issue()` and `_pull_item()`, `_pull_item_create_new()`, `_pull_item_update_existing()`. The create/update/overwrite helpers are mentioned by name without any behavioral description.
- **Code Reality**: These exist and implement full create-vs-update logic including force-overwrite and section merge. The `_overwrite_body_from_github` helper is also present (`operations.py:321-335`) but not listed in the spec.
- **Recommendation**: Add `_overwrite_body_from_github` to the spec's private helper list; add behavioral notes.

---

**FIND-9** — `find_or_create_issue` in operations.py is public but not in spec's Exports list

- **Priority**: Medium
- **Evidence**: `operations.py:841` (public function, no leading underscore)

- **Documentation Claim**: Spec Exports (`ARCHITECTURE.md:187`):

```text
add_item, list_items, view_item, sync_items, close_item, resolve_item, update_item,
groom_item, normalize_items, pull_items, update_item_metadata, pull_single_issue,
refresh_local_cache_from_github, sync_create_missing_issues, sync_push_groomed_content
```

- **Code Reality**: `find_or_create_issue` is defined as a public function and is present in operations.py. It is not listed in the spec's Exports.
- **Recommendation**: Add `find_or_create_issue` to the spec's Exports list for operations.py.

---

**FIND-10** — `update_item` has `groomed_file` and `groomed: bool` parameters not in spec

- **Priority**: High
- **Evidence**: `operations.py:1105-1161`

```python
def update_item(
    selector: str,
    plan: str | None = None,
    status: str | None = None,
    create_issue: bool = False,
    groomed_file: str | None = None,
    groomed_content: str | None = None,
    section: str | None = None,
    content: str | None = None,
    groomed: bool = False,
    repo: str = DEFAULT_REPO,
    output: Output | None = None,
) -> dict[str, str | int | bool | list[str]]:
```

- **Documentation Claim**: The spec describes `update_item()` (`ARCHITECTURE.md:181-182`) but lists no signature. The server wrapper (`server.py:182-231`) exposes only `groomed_content`, `section`, `content` — not `groomed_file` or `groomed: bool`.
- **Code Reality**: Two additional parameters exist in `update_item()` that the server layer does not expose: `groomed_file` (reads from filesystem path) and `groomed: bool` (triggers stdin read when True and no other groomed input is provided). These are reachable only via the CLI wrapper, not via MCP tools.
- **Recommendation**: Document the `groomed_file` and `groomed` parameters in the spec; note they are CLI-only and not exposed through MCP server.

---

**FIND-11** — `groom_item` has a `groomed_file` parameter not in spec

- **Priority**: Medium
- **Evidence**: `operations.py:1164-1198`

```python
def groom_item(
    selector: str,
    groomed_file: str | None = None,
    groomed_content: str | None = None,
    section: str | None = None,
    content: str | None = None,
    repo: str = DEFAULT_REPO,
    output: Output | None = None,
) -> dict[str, str | int | bool | list[str]]:
```

- **Documentation Claim**: Spec only states `groom` command → `groom_item()` (`ARCHITECTURE.md:183`). No parameter signature is described.
- **Code Reality**: `groom_item` accepts `groomed_file` for reading groomed content from a file path. The server wrapper `backlog_groom` does not expose this parameter — it is CLI-only.
- **Recommendation**: Add `groomed_file` to spec notes; flag as CLI-only parameter not exposed via MCP.

---

**FIND-12** — `parsing.py` imports `import frontmatter` (python-frontmatter package) in addition to `frontmatter_utils`

- **Priority**: High
- **Evidence**: `parsing.py:15`

```python
import frontmatter
```

Used at `parsing.py:423`:

```python
post = frontmatter.Post(
    "", name=name.replace('"', "'"), description=(description or "").replace('"', "'"), metadata=meta
)
```

- **Documentation Claim**: The spec (`ARCHITECTURE.md:16-28`) specifies exactly how to import `frontmatter_utils`:

```python
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT / "plugins" / "plugin-creator" / "scripts"))
from frontmatter_utils import dump_frontmatter, loads_frontmatter
```

No mention is made of importing the `frontmatter` package directly.

- **Code Reality**: `parsing.py` imports both `frontmatter_utils` (via the specified path manipulation) AND the `frontmatter` Python package directly. `frontmatter.Post(...)` is used to construct frontmatter objects in `build_backlog_frontmatter`. This dependency on the `frontmatter` package is not described in the spec.
- **Recommendation**: Add the `frontmatter` package as an explicit dependency in the spec.

---

### 2. Documented but Unimplemented

Features or items the spec describes that are absent from the code.

---

**FIND-13** — `Output` class methods shown as stubs with `...` body in spec — IMPLEMENTATION EXISTS but spec shows wrong syntax

- **Priority**: Medium (documentation clarity issue, not a missing feature)
- **Evidence**: `ARCHITECTURE.md:74-77`

```python
def info(self, msg: str) -> None: ...
def warn(self, msg: str) -> None: ...
def error(self, msg: str) -> None: ...
```

- **Code Reality**: All three methods are fully implemented in `models.py:167-177`. The spec's stub syntax `...` is a simplified pseudo-code representation that could be mistaken for `Protocol` or abstract method declarations.
- **Recommendation**: Replace `...` stubs with the actual implementation signatures, or explicitly note "method bodies omitted for brevity."

---

**FIND-14** — `SKIP_STATUS` constant is defined but never imported or used outside `models.py`

- **Priority**: Low
- **Evidence**: `models.py:36`, confirmed by grep returning no matches in other modules

```python
SKIP_STATUS = ("DONE", "RESOLVED", "COMPLETED")
```

- **Documentation Claim**: Spec lists `SKIP_STATUS` as a constant in models.py (`ARCHITECTURE.md:108`).
- **Code Reality**: `SKIP_STATUS` is defined in `models.py` but imported by no other module. The skip logic in `parse_item_file` (`parsing.py:236`) uses an inline set `{"done", "resolved"}` rather than `SKIP_STATUS`.
- **Recommendation**: Either use `SKIP_STATUS` in `parse_item_file` to avoid logic duplication, or remove it from the spec's constants list if it is intentionally unused.

---

**FIND-15** — `SECTION_RE` constant is defined but never imported or used outside `models.py`

- **Priority**: Low
- **Evidence**: `models.py:28`, confirmed by grep returning no matches in other modules

```python
SECTION_RE = re.compile(r"^##\s+(P0|P1|P2|Ideas)")
```

- **Documentation Claim**: Spec lists `SECTION_RE` as a constant in models.py (`ARCHITECTURE.md:108`).
- **Code Reality**: `SECTION_RE` is defined but imported nowhere. Section detection in `parse_backlog_from_directory` uses filename prefix matching (`parsing.py:255-270`), not this regex.
- **Recommendation**: Either use `SECTION_RE` in parsing logic to eliminate the duplicate pattern, or remove it from the spec's constants list.

---

### 3. Outdated Documentation

Spec describes an implementation that has since been superseded.

---

**FIND-16** — Spec says `backlog.py` imports from `.mcp.operations` and `.mcp.models` — wrong path

- **Priority**: Critical
- **Evidence**: `ARCHITECTURE.md:237`

```text
**Imports**: `from .mcp.operations import ...`, `from .mcp.models import ...`
```

- **Code Reality**: The package was renamed from `mcp/` to `backlog_core/` during implementation to avoid namespace collision with the installed `mcp` Python SDK (noted in commit `89ab8b2`). The CLI wrapper (`backlog.py`) would import from `backlog_core`, not `.mcp`. The spec still uses the old `mcp` subpath.
- **Recommendation**: Update CLI wrapper imports section to reflect `from .backlog_core.operations import ...` and `from .backlog_core.models import ...`.

---

**FIND-17** — Spec says module directory is named `mcp/` — wrong, it is `backlog_core/`

- **Priority**: Critical
- **Evidence**: `ARCHITECTURE.md:5`

```text
Extract all business logic from `.claude/skills/backlog/scripts/backlog.py` into a clean
Python package at `.claude/skills/backlog/backlog_core/`. The package exposes...
```

The body of the spec correctly says `backlog_core/`. However, the CLI wrapper section (`ARCHITECTURE.md:224-238`) contradicts this by still using `.mcp.operations` import paths. The package was renamed from `mcp/` during implementation.

- **Code Reality**: All modules exist at `.claude/skills/backlog/backlog_core/`. The `.mcp` import references in the CLI section are stale.
- **Recommendation**: Remove all `.mcp` references from the CLI wrapper section.

---

**FIND-18** — Spec Exports list for `operations.py` omits `find_or_create_issue` and uses old private helper name `_add_item_index_format`

- **Priority**: Medium
- **Evidence**: `ARCHITECTURE.md:177, 187`

Spec lists: `_add_item_index_format()` → `part of add_item()`

Spec Exports include: `add_item, list_items, view_item, sync_items, close_item, resolve_item, update_item, groom_item, normalize_items, pull_items, update_item_metadata, pull_single_issue, refresh_local_cache_from_github, sync_create_missing_issues, sync_push_groomed_content`

- **Code Reality**: `_add_item_index_format` does not exist. It was replaced by five private helpers in `d79372b`. `find_or_create_issue` is public but absent from the Exports list.
- **Recommendation**: Remove `_add_item_index_format` reference; add `find_or_create_issue` to the Exports list.

---

**FIND-19** — Spec description of `parsing.py` private vs public function naming implies leading-underscore pattern was retained

- **Priority**: Low
- **Evidence**: `ARCHITECTURE.md:126-136`

Spec uses the pattern `_foo()` → `foo()` to mean "renamed to public":

```text
Date helpers: `_today()` → `today()`, `_now_iso()` → `now_iso()`
```

Several functions the spec marks as private with leading underscore are now fully public without underscore in the code:

- `_extract_body_field_pairs()` → `extract_body_field_pairs` (public, in `__all__`)
- `_apply_field_to_result()` → `apply_field_to_result` (public, in `__all__`)
- `_merge_field_into_result()` → `merge_field_into_result` (public, in `__all__`)
- `_parse_body_extra_fields()` → `parse_body_extra_fields` (public, in `__all__`)
- `_extract_groomed_section()` → `extract_groomed_section` (public, in `__all__`)
- `_build_body_extra_only()` → `build_body_extra_only` (public, in `__all__`)
- `_append_or_replace_section()` → `append_or_replace_section` (public, in `__all__`)
- `_extract_description_from_issue_body()` → `extract_description_from_issue_body` (public, in `__all__`)
- `_extract_sections()` → `extract_sections` (public, in `__all__`)
- `_reconstruct_body_from_sections()` → `reconstruct_body_from_sections` (public, in `__all__`)
- `_merge_sections()` → `merge_sections` (public, in `__all__`)

The spec format using `_old()` → `new()` implies these were renamed to public, which is accurate — but the spec retains the old underscore names, making it ambiguous whether they remain private.

- **Code Reality**: All are public (no leading underscore) and included in `parsing.py`'s `__all__`.
- **Recommendation**: Update spec to list only the final public names without the `_old() → new()` migration notation, since the migration is complete.

---

**FIND-20** — `gh_client.py` spec lists private names `_get_github()`, `_try_get_github()`, etc. — all are now public

- **Priority**: Low
- **Evidence**: `ARCHITECTURE.md:151-158`

Spec uses the same `_old()` → `new()` migration notation for every function in `gh_client.py`. All were made public. Same issue as FIND-19, specific to `gh_client.py`.

- **Code Reality**: `get_github`, `try_get_github`, `create_issue_for_item`, `close_github_issue`, `resolve_github_issue`, `check_open_prs_for_issue`, `batch_fetch_statuses`, `fetch_item_status`, `apply_status_in_progress`, `fetch_open_issues_by_title`, `view_enrich_from_github`, `issue_to_local_fields`, `sync_groomed_to_github_issue`, `fetch_github_issue_body` — all public, all in `gh_client.py`.
- **Recommendation**: Update spec to list only final public names.

---

### 4. Mismatched Details

Spec says X, code does Y.

---

**FIND-21** — Spec says `BacklogItem` has an `item_type` field but `parse_item_file` never populates it

- **Priority**: High
- **Evidence**: `models.py:140`, `parsing.py:213-240`

Spec (`ARCHITECTURE.md:56`):

```python
item_type: str = "Feature"
```

`parse_item_file` return (`parsing.py:228-240`):

```python
return BacklogItem(
    title=...,
    description=...,
    source=...,
    added=...,
    priority=...,
    issue=...,
    plan=...,
    skip=...,
    groomed=...,
    last_synced=...,
)
```

- **Code Reality**: `item_type` is a field on `BacklogItem` (default `"Feature"`) but `parse_item_file` never reads `type` from the frontmatter or sets this field. Items parsed from disk always have `item_type = "Feature"` regardless of what their frontmatter `type:` field contains. The `extract_normalize_metadata` function (`parsing.py:849`) does read `type_val` from frontmatter, but this is only used during normalize operations, not regular parsing. The `raw_body` field was removed in the YAML migration (P964).
- **Recommendation**: Fix `parse_item_file` to read `item_type` from frontmatter `type` key, or document the known gap in the spec.

---

**FIND-22** — Spec says `operations.py` imports come from `from .models import ...` but operations.py also imports `_COMMIT_PREFIX_RE` (a private name) from models

- **Priority**: Low
- **Evidence**: `operations.py:33`

```python
from .models import (
    _COMMIT_PREFIX_RE,
    ...
)
```

- **Documentation Claim**: Spec (`ARCHITECTURE.md:189-192`) says operations imports constants, exceptions, and models from `.models`. No mention of importing a private constant (`_COMMIT_PREFIX_RE`).
- **Code Reality**: `_COMMIT_PREFIX_RE` is imported directly into `operations.py` despite being a private constant (leading underscore). It is used in `pull_single_issue` to strip conventional-commit prefixes from issue titles.
- **Recommendation**: Either rename `_COMMIT_PREFIX_RE` to `COMMIT_PREFIX_RE` (public) or document this import in the spec.

---

**FIND-23** — Spec says server.py imports `from .models import ...` — code imports only `BacklogError, Output` from models

- **Priority**: Low
- **Evidence**: `server.py:11`

```python
from .models import BacklogError, Output
```

- **Documentation Claim**: `ARCHITECTURE.md:220`: `**Imports**: from fastmcp import FastMCP, from .models import ..., from .operations import ...`
- **Code Reality**: `server.py` imports from operations as a module (`from . import operations`) rather than individual functions. Only `BacklogError` and `Output` are imported from models — not the full model set. The server does not import individual operation functions by name.
- **Recommendation**: Update spec to show accurate import pattern: `from . import operations` (module-level) rather than `from .operations import ...` (individual functions).

---

**FIND-24** — Spec says `output: Output | None = None` pattern applies to ALL operation functions — `groom_item` parameter order differs from spec implied signature

- **Priority**: Low
- **Evidence**: `operations.py:1164-1198`, `ARCHITECTURE.md:43`

- **Documentation Claim**: The spec states: "Each function that needs to communicate status takes an optional `output: Output | None = None` parameter."
- **Code Reality**: All public operation functions do follow this pattern. However, `groom_item` delegates entirely to `update_item` and does not independently check for empty input — it passes `groomed=not has_input` which triggers stdin reading when nothing else is provided. This implicit stdin fallback is an undocumented behavior that violates the principle of explicit parameter passing described in the spec.
- **Recommendation**: Document the stdin fallback in `groom_item` and `update_item`; note this is a CLI-specific concern that does not affect the MCP server path (the MCP server always provides explicit parameter values).

---

## Recommendations (Prioritized)

### Critical (fix spec accuracy immediately)

1. **FIND-17 / FIND-16**: Remove all `.mcp.operations` / `.mcp.models` import references from the CLI wrapper section of the spec. Replace with `backlog_core`. The package was renamed and the spec still uses the old name.

2. **FIND-21**: Document or fix the gap in `parse_item_file`: `item_type` from frontmatter `type:` key is never populated during parsing. Items always use the `"Feature"` default. This is a functional issue: `create_issue_for_item` uses `item.item_type` to derive issue labels and prefix — if parsing never sets it from disk, the value is always wrong for Bug/Refactor/etc. items loaded from local files.

3. **FIND-12**: Add `frontmatter` (python-frontmatter package) as an explicit dependency in the spec's dependency section. Its use in `build_backlog_frontmatter` is not mentioned anywhere, and anyone implementing from spec would miss this package requirement.

### High (spec correctness)

4. **FIND-10**: Document `update_item`'s `groomed_file` and `groomed: bool` parameters in the spec. Flag as CLI-only (not exposed through MCP).

5. **FIND-9**: Add `find_or_create_issue` to the operations.py Exports list.

6. **FIND-18**: Remove `_add_item_index_format` reference (function does not exist) from the spec.

### Medium (completeness)

7. **FIND-1**: Add `Output.to_dict()` to the spec's model description.

8. **FIND-2**: Document the pagination metadata keys (`body_truncated`, `body_remaining_lines`, `body_total_lines`) added by `view_item()`.

9. **FIND-11**: Document `groom_item`'s `groomed_file` parameter.

10. **FIND-13**: Replace `Output` stub methods (`...`) with actual implementation signature notes.

11. **FIND-23**: Fix server.py imports description: `from . import operations` (not individual functions).

### Low (spec hygiene)

12. **FIND-3**: Update the operations.py ADD private helpers list to name the five refactored helpers.

13. **FIND-4 through FIND-8**: Add behavioral notes to private helpers that have complex contracts (stdin fallback, GitHub-first write order, force-overwrite vs section-merge paths).

14. **FIND-14 / FIND-15**: Resolve unused `SKIP_STATUS` and `SECTION_RE` constants: either wire them into parsing logic or remove them from the spec's constants list.

15. **FIND-19 / FIND-20**: Replace `_old() → new()` migration notation in `parsing.py` and `gh_client.py` sections with final public names only.

16. **FIND-22**: Rename `_COMMIT_PREFIX_RE` to `COMMIT_PREFIX_RE` (remove private prefix since it is imported across module boundaries) or document the cross-module private import.

17. **FIND-24**: Add a note on stdin fallback behavior in `groom_item` and `update_item`.
