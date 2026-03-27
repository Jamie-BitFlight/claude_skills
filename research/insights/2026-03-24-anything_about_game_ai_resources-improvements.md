# Improvement Proposals: Anything About Game AI Resources

**Research entry**: ./research/developer-tools/anything_about_game_ai_resources.md
**Generated**: 2026-03-24
**Patterns assessed**: 9
**Backlog items created**: 0
**Deferred (low confidence)**: 2
**Skipped (already covered or tracked)**: 7

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Emphasis on system prompts as a research focus | Low | The research entry suggests dedicating sections to leaked system prompts and prompt configuration. The local `prompt-engineering` research category exists and could host such entries, but the pattern describes a content curation strategy rather than a concrete mechanism absent from local systems. To raise confidence: verify whether any existing research entries in `prompt-engineering/` analyze actual system prompt configurations, and whether the research-curator entry template has a field for "configuration analysis" distinct from general feature documentation. |
| Agent framework comparison matrix as a research output format | Low | The research entry suggests building a comparison matrix of orchestrators (crewAI, Agno, etc.) by features. The research-curator currently produces individual entries per resource with no cross-resource comparison output. However, the research entry does not describe a concrete mechanism for comparison -- it names a deliverable type. To raise confidence: identify a specific comparison format from the source repository that goes beyond a link list, and verify that the research-curator entry template cannot already accommodate comparative analysis within its existing sections (e.g., Cross-References, Relevance). |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Taxonomy-first curation (organizing by problem domain) | Already covered: research-curator SKILL.md has 23 categories organized by function/domain in `<categories>` section, and entry-template.md has a category selection flowchart. |
| Cross-reference linking between AI domains | Already covered: `@research-cross-referencer` agent (`.claude/agents/research-cross-referencer.md`) actively adds cross-references to research entries. The research-curator orchestrator spawns it after every entry creation. |
| Dual-language maintenance (English + Chinese) | Incompatible with repo architecture: this repository serves Claude Code plugins which operate in English. Adding dual-language support would require restructuring every skill, agent, and reference file -- a fundamental architecture change, not an extension. |
| Distinction between frameworks and integrations (MCP layers) | Already covered: the entry-template category list separates `mcp-ecosystem` (servers/integrations) from `agent-frameworks` (SDKs) from `api-frameworks`. The fastmcp-creator SKILL.md trigger matrix further distinguishes server creation, composition, proxying, and integration patterns. |
| MCP Server Catalog with entry-level templates | Already covered: the `mcp__plugin_fastmcp-creator_fastmcp-reference__scaffold_server` MCP tool scaffolds new FastMCP servers. The fastmcp-creator skill (`plugins/fastmcp-creator/skills/fastmcp-creator/SKILL.md`) provides a trigger matrix mapping user intents to specific reference files for server creation, composition, proxying, authentication, and deployment. |
| Unity Integration Deepdive (focused research entries) | Too abstract: this is a content suggestion ("create more research entries on Unity MCP implementations") rather than a structural improvement to any local system. Any user can invoke `/research-curator` with a Unity MCP URL to create such entries. |
| Context Engineering linked to context-window optimization | Already covered: CLAUDE.md and `.claude/rules/` contain extensive context management guidance including investigation escalation, delegation path rules, skill content optimization rules, and the "No Invented Limits" policy. The `context-management` research category exists for hosting context engineering research entries. |
