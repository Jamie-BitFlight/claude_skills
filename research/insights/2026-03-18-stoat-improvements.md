# Improvement Proposals: Stoat

**Research entry**: ./research/developer-tools/stoat.md
**Generated**: 2026-03-18
**Patterns assessed**: 7
**Backlog items created**: 0
**Deferred (low confidence)**: 0
**Skipped (already covered or tracked)**: 7

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Confirmation workflows for destructive operations | Already covered. CLAUDE.md contains a Deletion Safety Protocol requiring verification before file deletion. Backlog item #470 ("Add elicitation to backlog_close and backlog_resolve for confirmation of destructive operations") and #473 ("Add MCP prompts and guided elicitation tools to backlog_core") already track adding structured confirmation to destructive MCP operations. |
| Read-only mode enforcement (dual-layer) | Too abstract for this repo. Stoat's dual-layer pattern (database connection flag + UI flag) is specific to database client tooling. The repo already implements analogous read-only enforcement via subagent tool restrictions (denying Write/Edit tools to read-only agents) and plan mode in the Agent SDK. No concrete gap exists that could be expressed as a file or command change. |
| Theme-aware syntax highlighting | Not applicable. This repo has no TUI rendering system. Stoat's per-theme color definitions for syntax highlighting apply to Bubbletea-based terminal applications, not to a Claude Code plugin marketplace that operates through markdown-based skill files and CLI scripts. |
| Configuration via structured YAML | Already covered. The repo uses structured YAML extensively: SAM task files with YAML frontmatter (documented in .claude/docs/TASK_FILE_FORMAT.md), plugin.json for plugin metadata, .pre-commit-config.yaml for hooks, and ~/.stoat-style config patterns already exist in MCP server configurations (.mcp.json). No gap. |
| Agent context injection for database introspection | Not applicable. The pattern suggests agents loading database connection configs to introspect databases during task execution. This repo has no database inspection workflow and no database-backed agent tasks. The pattern would require introducing an entirely new system rather than extending an existing one. |
| Query snippet library (shared queries across teams) | Not applicable. The repo has no SQL query execution context. While the concept of shared snippet libraries could abstractly map to skill templates, the repo already has a skill-creator workflow and plugin-creator scaffolding that serve the equivalent purpose for its domain. |
| Extensible database support (modular driver architecture) | Already covered in spirit. Stoat's modular driver pattern (adding database types without core changes) is architecturally equivalent to this repo's plugin system, where new skills and agents are added as modular plugins without modifying core infrastructure. No concrete gap. |
