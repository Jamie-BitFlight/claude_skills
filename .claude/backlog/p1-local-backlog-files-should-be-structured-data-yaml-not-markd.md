---
name: Local backlog files should be structured data (YAML) not markdown documents
description: Local backlog files (.claude/backlog/*.md) are currently markdown documents. They should be structured data (YAML or JSON) acting as a sync cache for GitHub Issues, not a document format. GitHub is canonical — local files are write caches that push upstream ASAP. The structured format would make parsing reliable, eliminate markdown formatting issues, and align with the principle that local structure mirrors issue structure.
metadata:
  topic: local-backlog-files-should-be-structured-data-yaml-not-markd
  source: 'GitHub Issue #964'
  added: '2026-03-22'
  priority: P1
  type: Refactor
  status: in-progress
  issue: '#964'
  last_synced: '2026-03-22T15:08:49Z'
---

## Story

As a **maintainer of the codebase**, I want to **local backlog files should be structured data (yaml) not markdown documents** so that **the code is cleaner and more maintainable**.

## Description

Local backlog files (.claude/backlog/*.md) are currently markdown documents. They should be structured data (YAML or JSON) acting as a sync cache for GitHub Issues, not a document format. GitHub is canonical — local files are write caches that push upstream ASAP. The structured format would make parsing reliable, eliminate markdown formatting issues, and align with the principle that local structure mirrors issue structure.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: User vision statement 2026-03-21 — divergence #2 from canonical issue lifecycle
- **Priority**: P1
- **Added**: 2026-03-21
- **Research questions**: None

## RT-ICA

<div><sub>2026-03-21T22:33:36Z</sub>

RT-ICA Final: Local backlog files → YAML
Goal: Convert .claude/backlog/*.md from hybrid YAML-frontmatter + markdown-body to pure YAML structured data acting as sync cache for GitHub Issues.
Conditions:
1. Current backlog file format and schema | Snapshot: DERIVABLE → Final: AVAILABLE | Citation: fact-checker verified hybrid format (YAML frontmatter lines 1-15 + markdown body sections)
2. All consumers of backlog files | Snapshot: DERIVABLE → Final: AVAILABLE | Citation: impact-analyst identified 18 file groups by criticality (frontmatter_utils.py, parsing.py, entry_blocks.py, operations.py, github.py, server.py, 24 test files, 12+ doc/skill files)
3. GitHub Issue body sync direction | Snapshot: DERIVABLE → Final: DERIVABLE | Citation: rtica-assessor found function signatures in github.py and operations.py; implementation details deferred to planning agent
4. Target format | Snapshot: MISSING → Final: AVAILABLE | Citation: user confirmed YAML
5. Migration strategy for existing files | Snapshot: DERIVABLE → Final: DERIVABLE | Citation: rtica-assessor identified reference pattern in sam_schema/cli.py _migrate_one; adaptation needed for backlog file structure
6. Markdown prose preservation in YAML | Snapshot: DERIVABLE → Final: AVAILABLE | Citation: rtica-assessor confirmed YAML block scalars (literal |, folded >) handle multiline markdown prose without fidelity loss
Changes from snapshot:
- Condition 1: DERIVABLE → AVAILABLE (resolved by fact-checker)
- Condition 2: DERIVABLE → AVAILABLE (resolved by impact-analyst)
- Condition 4: MISSING → AVAILABLE (user answered: YAML)
- Condition 6: DERIVABLE → AVAILABLE (resolved by rtica-assessor — YAML language feature)
- Conditions 3, 5 remain DERIVABLE — deferred to planning phase agent (not information gaps, design decisions)
Decision: APPROVED
</div>

## RT-ICA

<div><sub>2026-03-21T22:33:36Z</sub>

RT-ICA Final: Local backlog files → YAML
Goal: Convert .claude/backlog/*.md from hybrid YAML-frontmatter + markdown-body to pure YAML structured data acting as sync cache for GitHub Issues.
Conditions:
1. Current backlog file format and schema | Snapshot: DERIVABLE → Final: AVAILABLE | Citation: fact-checker verified hybrid format (YAML frontmatter lines 1-15 + markdown body sections)
2. All consumers of backlog files | Snapshot: DERIVABLE → Final: AVAILABLE | Citation: impact-analyst identified 18 file groups by criticality (frontmatter_utils.py, parsing.py, entry_blocks.py, operations.py, github.py, server.py, 24 test files, 12+ doc/skill files)
3. GitHub Issue body sync direction | Snapshot: DERIVABLE → Final: DERIVABLE | Citation: rtica-assessor found function signatures in github.py and operations.py; implementation details deferred to planning agent
4. Target format | Snapshot: MISSING → Final: AVAILABLE | Citation: user confirmed YAML
5. Migration strategy for existing files | Snapshot: DERIVABLE → Final: DERIVABLE | Citation: rtica-assessor identified reference pattern in sam_schema/cli.py _migrate_one; adaptation needed for backlog file structure
6. Markdown prose preservation in YAML | Snapshot: DERIVABLE → Final: AVAILABLE | Citation: rtica-assessor confirmed YAML block scalars (literal |, folded >) handle multiline markdown prose without fidelity loss
Changes from snapshot:
- Condition 1: DERIVABLE → AVAILABLE (resolved by fact-checker)
- Condition 2: DERIVABLE → AVAILABLE (resolved by impact-analyst)
- Condition 4: MISSING → AVAILABLE (user answered: YAML)
- Condition 6: DERIVABLE → AVAILABLE (resolved by rtica-assessor — YAML language feature)
- Conditions 3, 5 remain DERIVABLE — deferred to planning phase agent (not information gaps, design decisions)
Decision: APPROVED
</div>

## Conditions Assessment

### 1. Current backlog file format and schema
**Status**: ✅ **AVAILABLE**

**Evidence**:
- Fact-Check, CLAIM 1 (REFUTED framing): Files currently use YAML frontmatter (`---` delimited) + markdown body hybrid format
- Frontmatter metadata IS already structured (Pydantic `BacklogItem` model in `models.py` defines 18+ fields)
- Sample file confirmed: `/home/user/repos/claude_skills/.claude/backlog/p0-redesign-work-milestone-from-teamcreate-to-orchestrator-disp.md`
- Metadata fields: `topic`, `source`, `added`, `priority`, `type`, `status`, `issue`, `last_synced`, `groomed`, `plan`
- Body sections (markdown): `## RT-ICA`, `## Fact-Check`, `## Groomed`, `## Impact Radius`, etc.

**Citation**: Fact-Check section, Claim 1 (sample file) + Claim 2 (Pydantic model evidence)

---

### 2. All consumers of backlog files
**Status**: ✅ **AVAILABLE**

**Evidence**:
Impact Radius Phase 1 comprehensively inventoried 18+ files:

**CRITICAL PATH** (must change for pure YAML):
- `backlog_core/frontmatter_utils.py` — loads/dumps hybrid format via `python-frontmatter` library
- `backlog_core/parsing.py` — extracts sections from markdown body; `extract_groomed_section()`, `extract_sections()`, `append_or_replace_section()`, `entry_blocks.py` (250+ lines handling timestamp-delimited entry blocks in markdown)
- All related unit tests: `test_frontmatter_utils.py`, `test_backlog_core_parsing.py`, `test_entry_blocks_integration.py`, `conftest.py` test fixtures

**HIGH IMPACT** (likely changes):
- `backlog_core/operations.py` — save/load entry points; may need adjustment if parsing API changes
- `backlog_core/github.py` — syncs to GitHub issues; may need adjustment for body format change
- Skill documentation: `skills/backlog/SKILL.md`, `groom-backlog-item/SKILL.md`, `work-backlog-item/SKILL.md`, create skill, references

**LOW IMPACT** (may remain stable):
- `backlog_core/models.py` — field definitions, can remain backward-compatible
- `backlog_core/server.py` (code only) — if operations/parsing interfaces stable
- `github_branches.py` — slug generation unchanged
- `sam_schema/` — separate; only affected if task files also migrate

**Citation**: Impact Radius, Phase 1 (18-file inventory) + Phase 2 (impact checklists per module)

---

### 3. GitHub Issue body format and sync direction
**Status**: 🟡 **DERIVABLE** (function names confirm direction; implementation details require agent review)

**Evidence**:
- Impact Radius names sync functions in `github.py`: `sync_to_github()`, `pull_from_github()`
- Function names imply direction: `sync_to_github` = local→GitHub (push), `pull_from_github` = GitHub→local (fetch)
- Fact-Check, CLAIM 3 states this is INCONCLUSIVE and recommends reading `operations.py` and `github.py` to confirm flow
- Unresolved design decision: whether GitHub issue bodies remain in hybrid format (backward compat) or are converted to pure YAML

**Action required**: Agent to read `backlog_core/github.py` and `operations.py` to confirm:
1. Current sync/pull flow direction (likely local→GitHub push)
2. Whether GitHub issue body format will be changed or remain backward-compatible
3. Whether existing issues require migration or can coexist in hybrid format

**Citation**: Impact Radius, Phase 1 (section G: `github.py` 500+ lines) + Fact-Check, CLAIM 3 (INCONCLUSIVE status)

---

### 4. User's target format decision
**Status**: ✅ **AVAILABLE**

**Evidence**:
- User description: "should be structured data (YAML or JSON)"
- Issue context: Divergence #2 from canonical issue lifecycle (2026-03-21)
- User preference: YAML (from issue title: "Local backlog files should be structured data (YAML) not markdown")

**Citation**: Backlog item description + issue title

---

### 5. Migration strategy for existing 100+ backlog files
**Status**: 🟡 **DERIVABLE** (reference pattern exists; details require agent specification)

**Evidence**:
- Impact Radius Phase 1, section G mentions `test_cli_migrate_all.py` in `tests_sam/` — existing reference implementation for task plan file migration (`.md` to `.yaml`)
- `sam_schema/cli.py` (600+ lines) — already handles both `.md` and `.yaml` formats for task plans; provides pattern
- Fact-Check, CLAIM 4 notes markdown body can be migrated to YAML nested fields (one field per section, or `sections` map)

**Two strategic options**:
1. **Bulk migration**: Convert existing 100+ `.md` files to `.yaml` in one operation (read-all, transform, write-all)
2. **Lazy conversion**: Convert files on-read; write in new format on-write (gradual, backward-compatible)

**Action required**: Agent to design migration strategy by:
1. Examining `sam_schema/cli.py` and `test_cli_migrate_all.py` for task plan migration pattern
2. Designing analogous backlog file migration (with entry preservation, timestamp handling)
3. Choosing bulk vs. lazy strategy based on impact to running systems

**Citation**: Impact Radius, Phase 1, sections G (migration scripts) + Fact-Check, CLAIM 4 (markdown body movability)

---

### 6. Whether groomed section content (markdown prose) can be represented in pure YAML
**Status**: ✅ **AVAILABLE**

**Evidence**:
- YAML supports block scalars: `|` (literal, preserves newlines) and `>` (folded, wraps)
- Example:
  ```yaml
  groomed:
    - date: "2026-03-21"
      content: |
        Multi-line markdown prose here.
        Preserves exact formatting:
        - list items
        - with bullets

        And paragraphs separated by blank lines.
  ```
- Markdown prose in entry blocks (currently HTML comments `<div><sub>TIMESTAMP</sub>` delimited) can be stored as YAML list of objects with `content` field
- No loss of fidelity — YAML handles unstructured prose text exactly as markdown does

**Citation**: YAML language spec (block scalars, multiline strings); Fact-Check CLAIM 4 evidence (sample file groomed sections contain prose, timestamps, entry blocks)

---

## Summary Table

| Condition | Status | Evidence | Next Step |
|-----------|--------|----------|-----------|
| **1. Current format & schema** | ✅ Available | Hybrid YAML frontmatter + markdown body; Pydantic models in `models.py` | Proceed with design |
| **2. All consumers** | ✅ Available | 18-file inventory in Impact Radius; categorized by criticality | Proceed with phased implementation plan |
| **3. GitHub sync direction & body format** | 🟡 Derivable | Function names imply local→GitHub push; implementation unread | Agent to read `github.py` + `operations.py` for confirmation |
| **4. Target format decision** | ✅ Available | User specified YAML (confirmed in issue title + description) | Proceed with YAML (not JSON) |
| **5. Migration strategy** | 🟡 Derivable | Reference pattern exists in `sam_schema/cli.py` + `test_cli_migrate_all.py`; two options (bulk vs lazy) | Agent to design strategy based on existing patterns |
| **6. Markdown prose in YAML** | ✅ Available | YAML block scalars preserve multiline text; no fidelity loss | Proceed with confidence; entries can be YAML list of objects |

---

## Decision: APPROVED WITH AGENT FOLLOW-UP

**Approval Gating**:
- ✅ 4 conditions fully available (format, consumers, target format, YAML capability)
- 🟡 2 conditions derivable (GitHub sync details, migration strategy design)

**Recommended Next Step**:
1. Create a follow-up task to resolve Conditions 3 & 5 via agent delegation:
   - **Agent**: `@python3-development:python-cli-architect` (implements migration + format conversion)
   - **Research questions**:
     - Confirm GitHub sync direction and decide on backward-compat strategy for issue bodies
     - Design migration strategy (bulk vs lazy) by adapting `sam_schema` task plan migration pattern
   - **Deliverables**:
     - Design doc: `plan/architect-backlog-yaml-migration.md` (includes GitHub sync strategy + migration algorithm)
     - Migration script: `plugins/development-harness/scripts/migrate_backlog_to_yaml.py`

2. Create implementation task plan via `/add-new-feature` once design is approved.

**Rationale**: Both derivable conditions have clear paths to resolution using existing patterns in the codebase (SAM task plan migration). No blocking unknowns remain. The issue is well-scoped and ready for design phase.

</div>

## Fact-Check

<div><sub>2026-03-21T22:29:43Z</sub>

**FACT-CHECK FINDINGS — Primary Source Evidence**

---

## CLAIM 1: "Local backlog files are currently markdown documents"

**Status:** REFUTED

**Evidence:** Sample file `/home/user/repos/claude_skills/.claude/backlog/p0-redesign-work-milestone-from-teamcreate-to-orchestrator-disp.md` (lines 1-15):
- Contains YAML frontmatter (delimited by `---`)
- Metadata object with structured fields: `topic`, `source`, `added`, `priority`, `type`, `status`, `issue`, `last_synced`, `groomed`, `plan`
- Followed by markdown body sections (lines 16+)

**Finding:** Files use YAML frontmatter + markdown body hybrid format, NOT pure markdown. Metadata IS already structured — it parses into typed fields.

---

## CLAIM 2: "MCP server already treats files as structured data internally"

**Status:** VERIFIED (Partial)

**Evidence:**
- `plugins/development-harness/backlog_core/models.py` (lines 397-427) defines `BacklogItem` Pydantic BaseModel with fields: `title`, `description`, `source`, `added`, `priority`, `item_type`, `issue`, `plan`, `research_first`, `files`, `suggested_location`, `type_`, `topic`, `section`, `file_path`, `skip`, `status`, `groomed`, `last_synced`, `raw_body`
- Models use Pydantic for "natural integration with FastMCP 3.x" (server.py line 4)
- `frontmatter_utils.py` exists in backlog_core (grep result) — indicates frontmatter parsing infrastructure already present

**Finding:** Server parses files into Pydantic models. Frontmatter parsing utilities exist. The gap is not server-side — it's in file format clarity.

---

## CLAIM 3: "GitHub is canonical — local files are write caches"

**Status:** INCONCLUSIVE — Insufficient file content read

**Evidence Needed:** Would need to examine `backlog_sync`, `backlog_pull`, `backlog_update` operations (file:line references from server.py tools). Not examined due to context window discipline.

**Known:** Server provides MCP tools for sync/pull/update (grep found them in server.py). File naming convention uses `.md` (per-item markdown files in `.claude/backlog/`). Requires reading operations.py to confirm flow direction.

---

## CLAIM 4: "Markdown body is legacy"

**Status:** VERIFIED

**Evidence:** Sample file groomed sections (lines 75-197+) show:
- Section structure: `## RT-ICA`, `## Fact-Check`, `## Groomed (2026-03-21)`, `## Impact Radius`, `## Dependencies`, etc.
- All body content is markdown prose + structured HTML comments (e.g., `<div><sub>2026-03-21T21:39:09Z</sub>`) for timestamping
- No YAML fields in body — body content is untyped, freeform markdown

**Finding:** Markdown body contains sections with versioned entry blocks. No YAML in body. Could be migrated to YAML front-matter fields (one field per section, or a `sections` map), but currently stored as markdown.

---

## CLAIM 5: "Parsing is unreliable with markdown format"

**Status:** INCONCLUSIVE — Insufficient code inspection

**Evidence:** Grep found `parsing.py`, `frontmatter_utils.py`, `entry_blocks.py` exist in backlog_core. These modules likely contain parsing logic and format handling. Would need to read implementation to find parsing edge cases, workarounds, or format-related bugs.

**Known Pain Points (from sample file):** Entry blocks use HTML comments with timestamps (`<div><sub>TIMESTAMP</sub>`) for versioning — this is fragile to markdown editors and regex-based parsing because:
- Markdown editors may reformat or escape HTML
- Split/join operations on markdown body could break comment boundaries
- Regex parsing of `<div>` blocks is brittle compared to structured YAML or JSON

Without reading parsing.py, cannot confirm specific bugs, but format does create parsing risk surface.

---

## SUMMARY

| Claim | Status | Finding |
|-------|--------|---------|
| Files are pure markdown | **REFUTED** | Files use YAML frontmatter + markdown body (hybrid format) |
| Server treats as structured data | **VERIFIED** | Pydantic models exist; frontmatter utilities present |
| GitHub is canonical | **INCONCLUSIVE** | Need to read operations.py to confirm flow |
| Markdown body is legacy | **VERIFIED** | Body is untyped markdown; could move to YAML fields |
| Parsing unreliable | **INCONCLUSIVE** | Format contains HTML comment versioning (parsing risk visible); actual bugs not confirmed without reading parsing.py |

---

## NEXT STEPS FOR ISSUE #964

**Recommended validation:** Read `plugins/development-harness/backlog_core/parsing.py` and `entry_blocks.py` to identify specific parsing limitations and validate the "unreliable" claim with concrete examples (regex edge cases, workarounds, format-related issues).

**Scope clarification needed:** Issue title says "should be structured data (YAML) not markdown" — but frontmatter IS already YAML. The issue likely means:
- Move markdown body sections (RT-ICA, Fact-Check, Groomed, etc.) into YAML fields
- Replace HTML comment versioning (`<div><sub>TIMESTAMP</sub>`) with native YAML timestamps and entry block structure
- Result: 100% YAML file format, no markdown body at all
</div>

## Groomed (2026-03-21)


### Impact

<div><sub>2026-03-21T00:00:00Z</sub>

<div><sub>2026-03-21T22:30:09Z</sub>
</div>

<div><sub>2026-03-21T22:32:18Z</sub>

Affects all backlog operations. 18+ file groups: core I/O (`frontmatter_utils.py`, `parsing.py`, `operations.py`), MCP server (`server.py`), entry block handling (`entry_blocks.py`), GitHub sync (`github.py`, `github_branches.py`), models (`models.py`), SAM schema (`sam_schema/cli.py` shares frontmatter), all test files (8+ test modules), skill documentation (4+ skill files), and project-level docs (CLAUDE.md, local-workflow.md). Every backlog read/write operation flows through these modules.
</div>

### Reproducibility

<div><sub>2026-03-21T22:32:05Z</sub>

Open any backlog file in `.claude/backlog/` (e.g., `p0-redesign-work-milestone-from-teamcreate-to-orchestrator-disp.md`). Files contain hybrid YAML frontmatter (`---` delimited metadata) followed by markdown body sections (## RT-ICA, ## Fact-Check, ## Groomed, etc.). Entry timestamps are embedded as HTML comments (`<div><sub>ISO-TIMESTAMP</sub>`), fragile to editor reformatting. Parsing this format requires both frontmatter library AND markdown regex logic — creating parsing complexity and HTML comment fragility.
</div>

### Priority

<div><sub>2026-03-21T22:32:12Z</sub>

**P1 (Critical Infrastructure)** — Affects the entire backlog system. 18+ files in critical and high-impact categories (frontmatter I/O, parsing, MCP server, entry block handling, GitHub sync, tests, skill documentation). Parsing complexity creates ongoing maintenance burden and bug surface. Pure YAML eliminates parsing risk, enables schema validation, and aligns with canonical issue lifecycle (GitHub as source of truth).
</div>

### Benefits

<div><sub>2026-03-21T22:32:25Z</sub>

Pure YAML unlocks: (1) Reliable parsing — replace `frontmatter` library + markdown regex with native `ruamel.yaml` YAML handling; (2) Schema validation — Pydantic models can validate entire file structure (metadata + body sections as typed fields); (3) Cleaner sync — GitHub issue bodies and local files follow same canonical structure, eliminating format divergence; (4) Entry block migration — replace HTML comment timestamps with native YAML list-of-objects or single structured field; (5) Eliminates markdown editor corruption risk — pure data structure survives any text editor formatting.
</div>

### Expected Behavior

<div><sub>2026-03-21T22:32:31Z</sub>

End state: All `.claude/backlog/*.md` files converted to `.claude/backlog/*.yaml` format. Files contain pure YAML — no markdown body. All sections (RT-ICA, Fact-Check, Groomed, Impact Radius, etc.) represented as top-level YAML fields or nested structures (e.g., `sections` map). Entry blocks stored as YAML list of objects with `date` and `content` fields. Metadata and body sections combined in single YAML structure. Pydantic `BacklogItem` model validates entire file. Backward-compatible reader available during migration period.
</div>

### Acceptance Criteria

<div><sub>2026-03-21T22:32:38Z</sub>

1. **Format change**: All 100+ existing `.claude/backlog/*.md` files migrated to `.yaml` format (file extension change confirmed via `ls -la .claude/backlog/`).

2. **YAML validity**: All `.yaml` files parse without error via `ruamel.yaml.YAML().load(file)` (no syntax errors, no parsing exceptions).

3. **Pydantic validation**: All migrated files validate successfully against updated `BacklogItem` Pydantic model (run `BacklogItem.model_validate(yaml_dict)` for each file).

4. **Section preservation**: All sections from markdown body (RT-ICA, Fact-Check, Groomed, Impact Radius, Dependencies, etc.) present as YAML fields with content intact (no text loss).

5. **Entry block structure**: Grooming entry blocks (timestamped records) converted to YAML list-of-objects format, timestamps preserved, content readable (no HTML comment fragility).

6. **Test coverage**: All 8+ test modules (`test_parsing.py`, `test_operations.py`, `test_server.py`, `test_entry_blocks.py`, etc.) pass with pure YAML format — no parse errors, no file I/O failures.

7. **GitHub sync**: Backlog operations (pull, sync, update, groom) work end-to-end with pure YAML files — no failures due to file format mismatch.
</div>

### Files

<div><sub>2026-03-21T22:32:46Z</sub>

**CRITICAL PATH** (must rewrite):
- `plugins/development-harness/backlog_core/frontmatter_utils.py` — rewrite for pure YAML I/O
- `plugins/development-harness/backlog_core/parsing.py` (1000+ lines) — rewrite section extraction/merging logic
- `plugins/development-harness/backlog_core/entry_blocks.py` (250+ lines) — adapt for YAML entry structure
- All test files (8+) — rewrite fixtures and assertions

**HIGH IMPACT** (likely changes):
- `plugins/development-harness/backlog_core/operations.py` — may need API adjustments if parsing changes
- `plugins/development-harness/backlog_core/github.py` — sync logic may adapt
- `plugins/development-harness/skills/backlog/SKILL.md`, `groom-backlog-item/SKILL.md`, `work-backlog-item/SKILL.md`

**LOW IMPACT** (likely stable):
- `plugins/development-harness/backlog_core/models.py` — field definitions expandable, backward-compatible
- `plugins/development-harness/backlog_core/server.py` — if operations API stable
- `plugins/development-harness/sam_schema/cli.py` — if decoupled from backlog migration
</div>

### Resources

<div><sub>2026-03-21T22:32:53Z</sub>

**Reference patterns:**
- Task plan migration: `plugins/development-harness/tests_sam/test_cli_migrate_all.py` — `.md` to `.yaml` conversion pattern for SAM task files (analogous approach)
- SAM schema handling: `plugins/development-harness/sam_schema/cli.py` (600+ lines) — already parses both `.md` and `.yaml` formats; provides dual-format template

**Skills to load:**
- `/python3-development:python-cli-architect` — for migration script + format conversion implementation
- `/python3-development:python-pytest-architect` — for test rewrites (8+ test modules)

**Relevant agents:**
- `@python3-development:python-cli-architect` — design migration strategy, implement format converter
- `@python3-development:python-pytest-architect` — adapt test fixtures and assertions for YAML format
</div>

### Dependencies

<div><sub>2026-03-21T22:33:00Z</sub>

**Depends on:**
- RT-ICA assessment completion (GitHub sync direction clarification) — confirms whether GitHub issue bodies remain hybrid (backward-compat) or convert to pure YAML
- Migration strategy design using SAM task plan migration pattern as template — reduces risk of entry block loss or timestamp corruption

**Unblocks:**
- Schema validation roadmap — enables Pydantic validation of entire backlog file structure (metadata + sections)
- Canonical issue lifecycle implementation — aligns local cache format with GitHub source-of-truth structure
- Parsing reliability improvements — eliminates markdown editor fragility, HTML comment parsing risk
- Future refactoring of duplicated frontmatter parsing code (`plugin-creator/scripts/frontmatter_utils.py` can consolidate after migration)
</div>

### Effort

<div><sub>2026-03-21T22:33:06Z</sub>

**Large** (high scope, moderate complexity). Rationale: 18+ affected files across core I/O, parsing, MCP server, GitHub sync, entry blocks, tests, and documentation. Core modules (`frontmatter_utils.py`, `parsing.py`, `entry_blocks.py`) require substantial rewrites (1000+ lines combined). Migration of 100+ existing backlog files + test fixture rewrites (8+ test modules). However, reference pattern exists (SAM task plan migration), and parsing logic is well-contained. No architectural redesign needed — only format conversion and test adaptation.
</div>


## Impact Radius — Format Migration from Hybrid YAML-Frontmatter+Markdown to Pure YAML

### Current State

Local backlog item files (`.claude/backlog/*.md`) currently use a hybrid format:
- YAML frontmatter metadata block (delimited by `---`)
- Markdown body containing structured sections (grooming notes, entries, etc.)

This format is parsed and written by the `frontmatter` library with a custom `RuamelYAMLHandler` for round-trip YAML preservation.

### Phase 1: Build Systems Inventory

#### A. Core Parsing and I/O (CRITICAL)

**Files that parse/write backlog items:**

1. **`plugins/development-harness/backlog_core/frontmatter_utils.py`** (149 lines)
   - `load_frontmatter()` — reads `.md` files with YAML frontmatter via `frontmatter.load()`
   - `loads_frontmatter()` — parses string containing YAML frontmatter
   - `dump_frontmatter()` — serializes `Post` object to string
   - `dumps_frontmatter()` — writes `Post` object to file
   - `update_field()` — load, update one key, write back
   - Uses `RuamelYAMLHandler` (custom subclass of `YAMLHandler`) for round-trip YAML
   - **Impact**: Every migration path must reimplement this module for pure YAML I/O

2. **`plugins/development-harness/backlog_core/parsing.py`** (1000+ lines)
   - `parse_item_file()` — loads file via `load_frontmatter()`, extracts metadata and body sections
   - `loads_frontmatter()` re-export
   - `dump_frontmatter()` re-export
   - `build_backlog_frontmatter()` — constructs frontmatter dict
   - `build_issue_body()` — converts item to GitHub issue body format
   - `extract_groomed_section()` — parses markdown body for grooming section
   - `extract_sections()` — parses markdown body into sections
   - `merge_sections()` — merges markdown body sections
   - `append_or_replace_section()` — edits markdown body sections
   - `reconstruct_body_from_sections()` — rebuilds markdown body from parsed sections
   - `parse_body_extra_fields()` — extracts fields from markdown body text
   - Dependency: imports from `frontmatter_utils`
   - **Impact**: Must rewrite section extraction/merging logic when body moves to YAML nested structure

3. **`plugins/development-harness/backlog_core/operations.py`** (800+ lines)
   - `load_item()` — calls `parse_item_file()` to load from disk
   - `save_item()` — calls `dumps_frontmatter()` to write to disk
   - `update_item_field()` — calls `frontmatter_utils.update_field()`
   - `sync_item_to_github()` — calls `build_issue_body()` for GitHub sync
   - `parse_item_from_github()` — parses GitHub issue body (separate from file I/O)
   - Dependency: imports from `parsing` module
   - **Impact**: Save/load entry points remain stable; underlying I/O changes

4. **`plugins/development-harness/backlog_core/server.py`** (1200+ lines)
   - MCP tool implementations that call `operations.py` functions
   - `backlog_list()` — calls `parse_backlog_from_directory()`
   - `backlog_view()` — calls `load_item()`
   - `backlog_update()` — calls `save_item()` after modification
   - `backlog_groom()` — calls `append_or_replace_section()` to update body sections
   - `backlog_pull()` — syncs from GitHub issues (calls `build_issue_body()` reverse parse)
   - `backlog_sync()` — pushes to GitHub
   - Dependency: imports from `operations` and `parsing`
   - **Impact**: MCP tool signatures remain stable; underlying parsing changes

#### B. Models and Constants (CRITICAL)

5. **`plugins/development-harness/backlog_core/models.py`** (400+ lines)
   - `BACKLOG_DIR` constant — hardcoded as `.claude/backlog`
   - `BacklogItem` Pydantic model — defines schema for items
   - `SamTask` model — defines GitHub sub-issue task structure
   - `ViewItemResult` model — defines item view response
   - Regex patterns and field enums
   - Dependency: used by all parsing, operations, and server modules
   - **Impact**: Field definitions remain stable; body representation may expand if markdown sections become YAML fields

#### C. Entry Block Management (MAJOR)

6. **`plugins/development-harness/backlog_core/entry_blocks.py`** (250+ lines)
   - Parses and manages "entry" blocks within grooming sections (e.g., timestamp-delimited decision records)
   - Works on markdown body text
   - Functions: `extract_entries()`, `parse_entry()`, `append_entry()`, `strike_entry()`
   - Dependency: used by `parsing.py` and `operations.py`
   - **Impact**: Must adapt entry block extraction if grooming section structure changes (e.g., from markdown code blocks to YAML list)

7. **`plugins/development-harness/backlog_core/github.py`** (500+ lines)
   - Syncs backlog items to GitHub issues
   - `sync_to_github()` — calls `build_issue_body()` to generate GitHub issue body
   - `pull_from_github()` — parses GitHub issue body back to local item
   - Dependency: uses `parsing.py` for body building
   - **Impact**: GitHub issue body format may remain hybrid (for backward compat); local file becomes pure YAML

#### D. GitHub Integration (MAJOR)

8. **`plugins/development-harness/backlog_core/github_branches.py`** (200+ lines)
   - Manages branch names and PR creation for backlog items
   - No direct file I/O; works with item slugs and metadata
   - **Impact**: Low — slug generation unchanged

#### E. SAM Schema (CONDITIONAL)

9. **`plugins/development-harness/sam_schema/cli.py`** (600+ lines)
   - Separate CLI for task plan files (`.md` and `.yaml` formats)
   - Shares frontmatter parsing with backlog (imports `frontmatter_utils`)
   - **Impact**: High — if task plan format migrates to pure YAML simultaneously; Low if decoupled

#### F. Tests (CRITICAL)

10. **Test files that hardcode or parse backlog format:**
    - `plugins/development-harness/tests/test_backlog_core_parsing.py` — unit tests for parsing functions
    - `plugins/development-harness/tests/test_backlog_core_operations.py` — tests for load/save operations
    - `plugins/development-harness/tests/test_backlog_core_server.py` — tests for MCP server
    - `plugins/development-harness/tests/test_entry_blocks_integration.py` — tests for entry block parsing
    - `plugins/development-harness/tests/conftest.py` — test fixtures that create `.md` files
    - `plugins/development-harness/tests/test_scenarios.py` — integration scenarios with `.md` files
    - `plugins/development-harness/tests/test_live_validation.py` — live file validation tests
    - `plugins/plugin-creator/tests/test_frontmatter_utils.py` — unit tests for frontmatter utilities (shared code)
    - **Impact**: All tests must be rewritten to work with pure YAML format

#### G. Legacy and Migration Scripts (INFORMATIONAL)

11. **`plugins/development-harness/tests_sam/test_cli_migrate_all.py`** — tests task file migration from `.md` to YAML
    - Pattern: reads legacy `.md` format, writes new `.yaml` format
    - Provides a reference for backlog migration approach
    - **Impact**: Informational — shows migration pattern to follow

12. **`.claude/scripts/repair_from_original_register.py`** — utility script
    - Mentions backlog operations but is separate maintenance tool
    - **Impact**: May reference old paths/functions; low risk

13. **`scripts/rename_plan_files.py`** — utility for renaming plan files
    - Not directly related to backlog format
    - **Impact**: Low

#### H. Documentation (HIGH)

14. **Backlog Schema Documentation:**
    - `plugins/development-harness/docs/backlog-item-groomed-schema.md` — documents current item schema
    - `plugins/development-harness/skills/backlog/references/item-schema.md` — SKILL.md reference for item format
    - `plugins/development-harness/backlog_core/ARCHITECTURE.md` — internal architecture docs

15. **Process Documentation:**
    - `plugins/development-harness/docs/backlog-lifecycle.draft.md` — describes item lifecycle
    - `plugins/development-harness/docs/process-audit-backlog-lifecycle-2026-03-02.md` — process audit

16. **Backlog Skill Documentation:**
    - `plugins/development-harness/skills/backlog/SKILL.md` — main skill entry point
    - `plugins/development-harness/skills/backlog/README.md` — skill readme
    - `plugins/development-harness/skills/backlog/CLI_TO_MCP_MIGRATION.md` — CLI→MCP migration guide
    - `plugins/development-harness/skills/groom-backlog-item/SKILL.md` — grooming skill
    - `plugins/development-harness/skills/work-backlog-item/SKILL.md` — work-on-item skill
    - `plugins/development-harness/skills/create-backlog-item/SKILL.md` — creation skill
    - Related references in `skills/work-backlog-item/references/` — validation, GitHub integration, step procedures

17. **Project-Level Documentation:**
    - `.claude/CLAUDE.md` — mentions `.claude/backlog/` files and format (lines ~1200)
    - `.claude/rules/local-workflow.md` — SAM workflow, mentions task plan files (separate but related)

#### I. Duplicate Code (SECONDARY)

18. **`plugins/plugin-creator/scripts/frontmatter_utils.py`** (90 lines)
    - Duplicate of `backlog_core/frontmatter_utils.py` with minimal divergence
    - Used by `plugin-creator` plugin only
    - **Impact**: If this is a copy-paste, consolidate after backlog migration

### Phase 2: Impact Checklist per Category

#### Core I/O Layer (`frontmatter_utils.py`)

| Question | Answer | Evidence |
|----------|--------|----------|
| **Will it break without changes?** | YES | Depends on `python-frontmatter` + `RuamelYAMLHandler` which expect hybrid format |
| **Will it become stale?** | YES | Frontmatter handling becomes obsolete when files are pure YAML |
| **Needs code change?** | YES CRITICAL | Must rewrite to use `ruamel.yaml` directly for file I/O |
| **Needs documentation update?** | YES | Docstrings reference "frontmatter"; update to "YAML file" |
| **Test coverage exists?** | YES | `test_frontmatter_utils.py` in both plugins; tests must be rewritten |

#### Parsing Layer (`parsing.py`)

| Question | Answer | Evidence |
|----------|--------|----------|
| **Will it break without changes?** | YES | All functions that call `load/dump_frontmatter()` and manipulate markdown body |
| **Will it become stale?** | YES | Body extraction logic (sections, entries) tied to markdown format |
| **Needs code change?** | YES CRITICAL | Rewrite section extraction/merging to work with YAML nested structure |
| **Needs documentation update?** | YES | Docstrings reference markdown body manipulation; update to YAML field references |
| **Test coverage exists?** | YES | `test_backlog_core_parsing.py` — comprehensive unit tests; all must be rewritten |

#### Operations Layer (`operations.py`)

| Question | Answer | Evidence |
|----------|--------|----------|
| **Will it break without changes?** | MAYBE | Calls to parsing layer may still work if interface is stable (only internal changes) |
| **Will it become stale?** | NO | This layer is an adapter; stability depends on parsing layer changes |
| **Needs code change?** | NO/MAYBE | Only if parsing layer API changes; if purely internal, no changes needed here |
| **Needs documentation update?** | NO | Docstrings are high-level; no markdown-specific references |
| **Test coverage exists?** | YES | `test_backlog_core_operations.py`; tests will fail if parsing layer changes |

#### MCP Server (`server.py`)

| Question | Answer | Evidence |
|----------|--------|----------|
| **Will it break without changes?** | NO | Calls operations layer; no direct I/O |
| **Will it become stale?** | NO | Interface should remain stable |
| **Needs code change?** | NO | None if operations/parsing layers stable |
| **Needs documentation update?** | NO | Tool signatures documented in YAML frontmatter; no change if metadata unchanged |
| **Test coverage exists?** | YES | `test_backlog_core_server.py`; tests may pass if operations stable |

#### Entry Blocks (`entry_blocks.py`)

| Question | Answer | Evidence |
|----------|--------|----------|
| **Will it break without changes?** | YES | Regex/parsing tied to markdown entry format (timestamp delimiters, details blocks) |
| **Will it become stale?** | YES | Entry structure may change if grooming section becomes YAML |
| **Needs code change?** | YES | May need rewrite if entries move to YAML arrays/objects |
| **Needs documentation update?** | YES | Docstrings reference markdown format |
| **Test coverage exists?** | YES | `test_entry_blocks_integration.py` and `test_entry_blocks.py`; must be rewritten |

#### GitHub Integration (`github.py`)

| Question | Answer | Evidence |
|----------|--------|----------|
| **Will it break without changes?** | MAYBE | Depends on whether GitHub issue body format changes (likely backward compat required) |
| **Will it become stale?** | NO | GitHub API unchanged |
| **Needs code change?** | MAYBE | If local→GitHub body building changes; if GitHub format stays hybrid, may be OK |
| **Needs documentation update?** | MAYBE | Only if format differences between local and GitHub are introduced |
| **Test coverage exists?** | YES | `test_backlog_core_github.py`; may pass if GitHub format stable |

#### Tests

| Question | Answer | Evidence |
|----------|--------|----------|
| **Will they break without changes?** | YES | All tests that create or parse `.md` files will fail immediately |
| **Will they become stale?** | N/A | Tests themselves are fixtures, not production code |
| **Needs code change?** | YES CRITICAL | Rewrite all test fixtures to generate `.yaml` instead of `.md`; update assertions |
| **Needs documentation update?** | NO | Test code is not user-facing |
| **Test coverage exists?** | YES | Already comprehensive; rewrite preserves coverage |

#### Documentation

| Question | Answer | Evidence |
|----------|--------|----------|
| **Will it break without changes?** | NO | Docs don't control runtime behavior |
| **Will it become stale?** | YES | References to "markdown body", "YAML frontmatter", "per-item `.md` files" all become outdated |
| **Needs code change?** | NO | Documentation files, not code |
| **Needs documentation update?** | YES | Update all schema docs, lifecycle docs, skill docs to reference pure YAML format |
| **Test coverage exists?** | NO | Docs not tested |

### Scope Summary

**CRITICAL PATH (must change):**
1. `frontmatter_utils.py` — full rewrite for pure YAML I/O
2. `parsing.py` — section/entry extraction logic tied to markdown
3. `entry_blocks.py` — entry parsing tied to markdown format
4. All related unit tests (test_frontmatter, test_parsing, test_entry_blocks)
5. All integration tests using `.md` fixtures

**HIGH IMPACT (likely changes):**
6. `operations.py` — may need adjustment if parsing API changes
7. `github.py` — may need adjustment for backward compat or GitHub format change
8. Skill and documentation files — must be rewritten to describe YAML format

**MODERATE IMPACT (test-only):**
9. `server.py` tests — rewrite fixtures, may not need code changes
10. Integration tests in test_scenarios.py, test_live_validation.py

**LOW IMPACT (may remain stable):**
11. `models.py` — field definitions may grow; backward compat possible
12. `github_branches.py` — slug generation unchanged
13. SAM schema — only affected if task files also migrate to pure YAML

### Critical Divergence Points

1. **Body field representation**: Currently markdown string with `## Section` headers. Migration options:
   - Keep as single YAML string (minimal change, limits structured access)
   - Convert to YAML dict with section keys (breaking change, enables validation)

2. **Entry blocks**: Currently markdown with timestamp delimiters. Options:
   - Keep entry text as markdown within YAML string field
   - Convert to YAML list of objects (breaking change, cleaner structure)

3. **GitHub issue body format**: Local→GitHub sync must decide:
   - Keep GitHub issues as hybrid (backward compat with old issues)
   - Require GitHub→local body parsing to work with both formats
   - Convert all GitHub issue bodies during migration (expensive, risky)

### Recommended Sequencing

1. **Phase 1**: Rewrite `frontmatter_utils.py` for pure YAML I/O only (no behavioral change)
2. **Phase 2**: Update `parsing.py` section handling to work with YAML structure (largest rewrite)
3. **Phase 3**: Update `entry_blocks.py` if entries move to YAML (may be deferred)
4. **Phase 4**: Rewrite all tests with new format
5. **Phase 5**: Update documentation and SKILLs
6. **Phase 6**: Migrate existing `.md` files to `.yaml` (one-way transformation)

### Files Requiring No Changes

- `models.py` — constants and schema can remain stable if forward-compatible
- `github_branches.py` — slug generation independent of file format
- `sam_schema/` — keep separate if task files remain `.md`
- `server.py` (code only) — if operations layer interface stable


</div>