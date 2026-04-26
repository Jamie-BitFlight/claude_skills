# Improvement Proposals: Tolaria

**Research entry**: ./research/developer-tools/tolaria.md
**Generated**: 2026-04-26
**Patterns assessed**: 8
**Backlog items created**: 4 (issues: #1949, #1951, #1952, #1953)
**Deferred (low confidence)**: 1
**Skipped (already covered or tracked)**: 3

---

## Improvement 1: Transactional staging for research-curator file rewrites

**Source pattern**: Patterns Worth Adopting #3 — "Crash-Safe File Operations: Use transactional staging directories (`.tolaria-rename-txn/`) and recovery helpers to ensure file operations complete or roll back cleanly. Protects data integrity when operations fail mid-way."
**Local system**: `.claude/skills/research-curator/SKILL.md` (post-actions, lines 354-388); `.claude/skills/research-curator/scripts/validate_research.py`
**Confidence**: High
**Impact**: Medium
**Backlog**: #1949 created (P1)

### Current state

The research-curator skill rewrites entries (`--rerun`, `--validate --fix`, default mode) and updates `./research/README.md` via direct `Write`/`Edit` calls. There is no transactional staging directory, no atomic-rename mechanism, and no recovery helper. If a rewrite fails partway (process crash, disk-full, OOM kill, network drop while a sub-agent holds the file open), the entry on disk is left in a partial state. Grep of `.claude/skills/research-curator/` for `txn`, `staging`, `rollback`, or `transactional` returns zero matches.

### Target state

Rewrites stage to `./research/.research-curator-txn/<uuid>/` first, then atomic-rename onto the target on success. On startup or `--validate` invocation, the orchestrator scans for orphaned `.research-curator-txn/*` directories and either completes or rolls back each. Field `staging_dir` exposed as `./research/.research-curator-txn/` in SKILL.md. Validator script gains `--recover` subcommand.

### Measurable signal

Run `uv run .claude/skills/research-curator/scripts/validate_research.py --recover ./research/`. Output lists zero orphans on a clean tree. Inject a partial transaction (`mkdir ./research/.research-curator-txn/test-uuid; echo partial > ./research/.research-curator-txn/test-uuid/cocoindex-code.md`) — the same command reports the orphan and recovers or removes it. Grep returns at least one `staging_dir`/`txn` match in SKILL.md and one in `validate_research.py`.

---

## Improvement 2: Git-based incremental cache for research validation

**Source pattern**: Vault Caching and Performance — "Same commit → re-parse only uncommitted changes via `git status --porcelain`. Different commit → `git diff` to find changed files → selective re-parse. No cache → full walkdir scan."
**Local system**: `.claude/skills/research-curator/scripts/validate_research.py`
**Confidence**: High
**Impact**: Low
**Backlog**: #1951 created (P2)

### Current state

`validate_research.py` and the `--rerun all` path always re-process every entry from scratch. There is no cache of last-validated commit per entry, no `git status --porcelain` shortcut to find changed files, no `git diff` to identify changed entries since the last run. The `./research/` directory contains 30+ category subdirectories with hundreds of entries. Every `--validate all` performs a full walk and re-validates entries that have not changed.

### Target state

`validate_research.py` writes a cache at `~/.cache/research-curator/<repo-hash>.json` recording per-entry `last_validated_commit_sha`, `last_validated_at`, `last_validation_result_hash`. On invocation: same commit → `git status --porcelain` to find uncommitted changes only; different commit → `git diff --name-only <cached_sha> HEAD` to enumerate changed entries; no cache → full scan. Flags `--no-cache` (force rescan) and `--invalidate-cache` (delete cache, matching Tolaria's "Reload Vault" disposability).

### Measurable signal

Run `validate_research.py --json ./research/` twice on an unchanged tree. Second run completes in measurably less wall-clock time and JSON output includes `cache_hit_count` near total entry count. Touch one entry — third run reports `cache_hit_count` = (total - 1) and `revalidated: ['./research/developer-tools/tolaria.md']`. Cache file present at `~/.cache/research-curator/<hash>.json` with `last_validated_commit_sha`.

---

## Improvement 3: MCP server exposing research-curator vault operations

**Source pattern**: MCP Server Architecture — "14 built-in tools for vault operations: `open_note`, `create_note`, `search_notes`, `edit_note_frontmatter`, `delete_note`, `link_notes`, `list_notes`, `vault_context`, `ui_*` controls. Multiple transports: stdio for Claude Code/Cursor."
**Local system**: `.claude/skills/research-curator/scripts/` (no MCP server present)
**Confidence**: High
**Impact**: Medium
**Backlog**: #1952 created (P1)

### Current state

The research-curator skill produces a structured knowledge base at `./research/` (300+ entries across 30+ categories) but exposes no MCP interface. Only humans and the in-session agent can query it. Other plugins, sub-agents in fresh-context windows, and external Claude Code sessions cannot search by content/category, read structured fields (Freshness Tracking, Cross-References, Patterns Worth Adopting), list by freshness/layer, append cross-reference rows, or get a vault_context snapshot. `.claude/skills/research-curator/scripts/` contains `validate_research.py` only. Grep of the skill for `fastmcp` or `mcp:` in frontmatter returns zero matches. Distinct from #436 (NotebookLM external integration) — this exposes the local `./research/` directory itself.

### Target state

A FastMCP server at `.claude/skills/research-curator/scripts/research_mcp_server.py` exposing at minimum: `research_list`, `research_view`, `research_search`, `research_view_section` (progressive disclosure), `research_freshness_summary`, `research_add_cross_reference`. Server registered via `mcp:` frontmatter block in research-curator SKILL.md per `.claude/rules/frontmatter-requirements.md` ecosystem rules. Validation via `/fastmcp-creator:fastmcp-client-cli`.

### Measurable signal

Run `uv run fastmcp list --command "uv run --script .claude/skills/research-curator/scripts/research_mcp_server.py"` — output enumerates at least 6 tools matching the names above. Run `uv run fastmcp call --command "..." research_search '{"query": "tolaria", "mode": "title"}'` — output JSON contains an entry with `path: "./research/developer-tools/tolaria.md"`. Frontmatter of `.claude/skills/research-curator/SKILL.md` contains an `mcp:` top-level key referencing the server.

---

## Improvement 4: Automatic backlink / inverse cross-reference detection

**Source pattern**: Relationship Navigation — "Backlink detection: Scans vault for notes referencing the current note via wikilinks. Neighborhood mode: explore outgoing relationships (grouped by type), inverse relationships, backlinks, and all connected notes in a single scrollable view."
**Local system**: `.claude/agents/research-cross-referencer.md`; `.claude/skills/research-curator/scripts/validate_research.py`
**Confidence**: High
**Impact**: Low
**Backlog**: #1953 created (P2)

### Current state

`research-cross-referencer` appends a Cross-References table to a target entry, but there is no inverse-link enforcement. When entry A is updated to cross-reference entry B, entry B does NOT automatically receive a corresponding back-reference to A. The cross-reference graph is therefore directional and lossy. No script in `.claude/skills/research-curator/scripts/` performs a vault-wide backlink scan; `validate_research.py` does not check for asymmetric cross-references.

### Target state

`validate_research.py --check-backlinks` walks every entry, parses Cross-References tables (entries already use `[Name](../category/file.md)` paths, equivalent to wikilinks), builds a directed graph, and reports edges A→B with no reverse B→A. With `--fix`, auto-appends the reverse row to B's Cross-References table. A future `research_backlinks(path)` MCP tool (depends on #1952) returns entries that reference a given path.

### Measurable signal

Run `validate_research.py --check-backlinks ./research/`. Output JSON includes `asymmetric_cross_references: N` count and a list of pairs. Run with `--check-backlinks --fix` — second invocation reports `asymmetric_cross_references: 0`. Any entry that was the target of a cross-reference now has a row pointing back at the source.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Convention-driven semantic field names with built-in UI behavior (`type:`, `status:`, `belongs_to:` with default rendering) | Medium | Research entries already follow a strict template (Freshness Tracking, Cross-References, Patterns Worth Adopting). Whether adopting Tolaria-style semantic frontmatter fields would meaningfully improve agent comprehension over the existing section-based structure cannot be determined without testing both formats against a representative agent task. The pattern is sound but the gap and target state both require interpretation rather than direct observation. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Three-Representation Architecture (filesystem → cache → memory with disposable cache) | Already implemented in the backlog system: GitHub Issues are the source of truth, `~/.dh/projects/{slug}/backlog/*.md` is a disposable cache rebuilt by `backlog_pull` (per .claude/CLAUDE.md backlog_operations block). Cache in research-curator is covered by Improvement 2 above. |
| Files-first / portable plain-markdown architecture | Already a foundational design choice across the entire repo: skills, agents, research entries, backlog items, SAM plans are all plain markdown / YAML. No actionable gap. |
| Convention over Configuration / standard field names with default behavior | Already tracked under #1162 (SectionType for stage-based routing in BacklogItem.sections) and #1161 (agents using sections for progressive disclosure). The relevant gap in Claude Code domain — typed sections — is already in the backlog. |
| Token-budgeted context builder (60% of 180k = 108k cap) | Already tracked under #1855 (token_budget on Task/Plan models) and #1092 (teammate context headroom signal). No additional gap from this research. |
