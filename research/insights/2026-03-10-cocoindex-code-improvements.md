# Improvement Proposals: CocoIndex Code

**Research entry**: ./research/mcp-ecosystem/cocoindex-code.md
**Generated**: 2026-03-10
**Patterns assessed**: 8
**Backlog items created**: 0
**Deferred (low confidence)**: 2
**Skipped (already covered or tracked)**: 6

---

## Improvement 1: Add zero-configuration MCP server pattern guidance to fastmcp-creator skill

**Source pattern**: "Zero-configuration MCP servers: CocoIndex Code's approach to automatic root discovery and environment-based configuration (no YAML config files) minimizes setup friction for users" (Patterns Worth Adopting section)
**Local system**: plugins/fastmcp-creator/skills/fastmcp-creator/SKILL.md
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred -- confidence medium: the fastmcp-creator skill covers server instantiation, deployment, and `.mcp.json` configuration but does not explicitly document the zero-config pattern (auto-discovering project root via `.git/` markers, using only environment variables instead of config files). However, the existing `claude-code-mcp-integration.md` reference may partially address this via `.mcp.json` env passthrough. A full read of that reference file would be needed to confirm absence.

### Current state

The fastmcp-creator SKILL.md trigger matrix includes server creation, deployment, and Claude Code integration. The `claude-code-mcp-integration.md` reference covers `.mcp.json` configuration. Neither the SKILL.md nor the visible portions of reference files contain explicit guidance on implementing automatic project root discovery (scanning parent directories for `.git/`, marker files) or designing servers that require zero YAML/JSON configuration files by relying solely on environment variables.

### Target state

The fastmcp-creator skill includes a "Zero-Configuration Server Pattern" section or reference entry documenting: (1) automatic project root discovery via marker files (`.git/`, custom markers), (2) environment-variable-only configuration as a design goal, (3) sensible defaults that eliminate required configuration. This pattern would appear in either `server-core.md` or a new `patterns.md` reference.

### Measurable signal

The fastmcp-creator references directory contains a section or file with the heading "Zero-Configuration" or "Auto-Discovery" that documents the marker-file root discovery pattern and environment-variable-only configuration approach. Searchable via `grep -r "zero.config\|auto.*discover\|marker.*file" plugins/fastmcp-creator/`.

---

## Improvement 2: Create a semantic code search skill wrapping cocoindex-code MCP server

**Source pattern**: "A skill wrapping cocoindex-code's search tool could provide higher-level abstractions (e.g., 'find all error handlers', 'locate database queries') atop the raw semantic search" (Integration Opportunities section)
**Local system**: No existing skill for semantic code search. Closest: `.claude/skills/fastmcp-creator/SKILL.md` (for MCP server creation pattern)
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred -- confidence medium: while the research entry clearly describes this as an integration opportunity, creating a new skill wrapping an external MCP tool requires validating that cocoindex-code is stable enough for production use (v0.1.0, 337 stars), that the skill would provide value beyond what agents already get from the raw MCP tool, and that the skill's higher-level abstractions are well-defined. The research entry does not provide evidence that the raw MCP tool is insufficient for agent use.

### Current state

No skill in `.claude/skills/` or `plugins/` provides semantic code search capability. Agents rely on `Grep` (text-based regex search) and `Glob` (filename pattern matching) for code discovery. These tools cannot search by meaning, description, or conceptual similarity.

### Target state

A skill at `.claude/skills/semantic-code-search/SKILL.md` (or equivalent plugin path) exists that: (1) documents cocoindex-code MCP server installation and registration, (2) provides higher-level search patterns (e.g., "find all error handlers", "locate database connection setup"), (3) includes guidance on when to use semantic search vs. Grep/Glob.

### Measurable signal

A SKILL.md file exists under a `semantic-code-search` directory that references cocoindex-code as the underlying MCP tool and includes at least three higher-level search pattern examples with expected usage scenarios.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Zero-configuration MCP server pattern guidance | Medium | Need to fully read `claude-code-mcp-integration.md` reference to confirm this pattern is not already partially documented; the fastmcp-creator skill may cover env-based config via `.mcp.json` passthrough |
| Semantic code search skill wrapping cocoindex-code | Medium | cocoindex-code is v0.1.0 with 337 stars; need to validate stability and confirm the raw MCP tool is insufficient without a skill wrapper before committing to creation |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Incremental indexing with change detection | Specific to code indexing/embedding tools; no local system performs code indexing. Pattern is incompatible with repo architecture -- this repo builds skills and agents, not code analysis engines |
| Flexible embedding models via environment variable | Specific to ML/embedding tooling; no local system manages embedding models. Incompatible with repo architecture |
| Structured return types (Pydantic models for tool outputs) | Already covered in `plugins/fastmcp-creator/skills/fastmcp-creator/references/advanced.md` lines 280-312 which document Pydantic BaseModel structured responses for FastMCP tools |
| Context-aware code embedding across sessions | Too abstract for current architecture; would require building embedding infrastructure and session-persistent storage not present in any local system |
| MCP tool composition (combining semantic + text search) | Already covered by fastmcp-creator skill via `mount()`, provider composition, and multi-server patterns documented in `providers.md` and `real-world-patterns.md` references |
| Agent skill library for semantic search | Equivalent to the "semantic code search skill" proposal above; deduplicated to avoid redundant assessment |
