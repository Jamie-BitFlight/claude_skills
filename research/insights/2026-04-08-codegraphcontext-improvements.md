# Improvement Proposals: CodeGraphContext

**Research entry**: ./research/mcp-ecosystem/codegraphcontext.md
**Generated**: 2026-04-08
**Patterns assessed**: 9
**Backlog items created**: 0 (none)
**Deferred (low confidence)**: 3
**Skipped (already covered or tracked)**: 6

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Tree-Sitter for Language-Agnostic Parsing | Low | The gap is real (local `impact-analyst` and `code-reviewer` agents use `Grep`/`Glob`/`Read` for code discovery, not AST parsing). However, adopting tree-sitter requires building a new parsing pipeline and graph database -- not extending any existing system. Prior assessments in `2026-03-19-gitnexus-improvements.md` ("Reimplementing the graph pipeline would require replacing, not extending, local systems"), `2026-04-05-soulforge-improvements.md` ("Requires building new infrastructure -- not an extension of any existing local system"), and `2026-03-23-composure-utilization-assessment.md` confirm this conclusion across three independent research entries. To raise confidence: prototype a tree-sitter-based code indexer as a standalone MCP server and measure whether impact-analyst accuracy improves vs the current grep-based approach. |
| Graph Database for Relationship Queries | Low | Same infrastructure gap as tree-sitter. Local systems (`impact-analyst`, `code-reviewer`, `doc-drift-auditor`) use sequential file reads and grep for relationship discovery. Cypher graph queries would be more expressive for multi-hop traversals (callers-of-callers, transitive dependencies). However, the `impact-analyst` agent already has access to `mcp__git-xray__what_breaks` and `mcp__git-xray__find_symbol` MCP tools, which provide structured code intelligence beyond pure grep. The incremental value of a local graph DB over git-xray has not been measured. To raise confidence: compare git-xray's `what_breaks` output against CGC's `analyze_code_relationships(query_type="callers")` output for the same codebase and measure accuracy/completeness delta. |
| Bundle/Cache Pattern for Offline Analysis | Low | CGC's pre-indexed bundles enable instant analysis of popular repos without indexing. No local system currently pre-computes code analysis results. The DH harness caches per-project artifacts in `~/.dh/projects/{slug}/`, but this is runtime state, not pre-computed analysis bundles. The gap is architecturally interesting but does not map to a specific local system to extend -- it would require a new system for generating, distributing, and loading pre-computed code graphs. To raise confidence: identify a concrete use case where pre-computed analysis saves measurable time in the current workflow (e.g., context-gathering agent spending >N seconds re-analyzing unchanged code). |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| MCP Protocol for Tooling Integration (dual-mode CLI + MCP) | Already covered by `/fastmcp-creator` skill (lines 66-75 of SKILL.md: explicit CLI mode via `fastmcp run` and MCP server mode with transport selection) and `/plugin-creator:mcp-integration` skill (stdio, SSE, HTTP, WebSocket server types). The local system already implements and teaches this pattern. |
| Direct MCP Integration (register CGC as MCP server) | This is a utilization proposal (using CGC as external tool), not a local system improvement. Already covered in `2026-04-08-codegraphcontext-utilization.md` -- Utilization 1 (doc-drift-auditor) and Utilization 2 (context-gathering). |
| Skill Development (create /codegraphcontext skill) | Same as above -- utilization proposal. The pattern is "wrap external tool as skill", which is a standard plugin-creator workflow, not a gap in local system design. |
| Context-Aware Code Search (graph-powered relationship discovery) | Utilization proposal. Already covered in `2026-04-08-codegraphcontext-utilization.md`. The `impact-analyst` agent already has `mcp__git-xray__find_symbol` for structured symbol search. |
| Autonomous Testing Integration (find affected tests via CGC) | Utilization proposal. The `complete-implementation` skill already discovers affected tests via `git diff --name-only` and grep-based test file matching (lines 101-119 of SKILL.md). Adding CGC as a data source is a utilization decision, not a local system gap. |
| Plugin Marketplace (publish CGC wrapper plugin) | Utilization proposal. This is a packaging decision about CGC, not a pattern that improves local systems. |
