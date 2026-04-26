# Utilization Proposals: Tolaria

**Research entry**: ./research/developer-tools/tolaria.md
**Generated**: 2026-04-26
**Integration surfaces found**: 1 (MCP server with 14 tools)
**Proposals written**: 2
**Skipped**: 3 — (knowledge-explorer already covers KB scope; backlog-tools insufficient integration justification; doc-drift-auditor not applicable)

---

## Utilization 1: research-context-agent → Tolaria MCP Server

**Research entry**: ./research/developer-tools/tolaria.md
**Caller**: ./.claude/agents/research-context-agent.md
**Integration mechanism**: MCP server (stdio or WebSocket bridge to tolaria)
**Replaces or adds**: Adds structured vault-backed note linking and relationship navigation during research integration analysis
**Setup cost**: Medium (tolaria installation, vault creation, MCP registration, then MCP tool calls in agent prompt)
**Integration surface**: Tolaria MCP server (14 tools: `search_notes`, `create_note`, `link_notes`, `edit_note_frontmatter`, `list_notes`, `vault_context`)

### Why this caller

The research-context-agent currently discovers integration opportunities by searching the repo codebase (skills, agents, plugins, commands) and validates claims against primary sources. It searches for existing skill/agent/hook/command coverage, then proposes new capabilities.

Tolaria's vault system would provide a **persistent knowledge graph** where research context (tool capabilities, patterns, design decisions) can be stored as typed entities with relationships. Instead of re-analyzing each research file against the codebase in isolation, the agent could:

1. Query tolaria for prior research on related tools (via `search_notes`)
2. Navigate relationship chains to find patterns adopted across multiple research entries
3. Create a note for each research entry linking it to skills/agents that implement its patterns (via `link_notes`)
4. Store Integration Opportunities as structured metadata (type: `opportunity`, belongs_to: research entry, related_to: skill/agent/plugin)

This moves research-context-agent from a transactional search-and-match workflow (per-file) to a **knowledge graph navigation workflow** where discovered patterns and prior integrations inform future discoveries.

**Current Implementation**: Lines 26–70 of research-context-agent.md describe the three-phase process (absorb, search & match, write opportunities). Search happens via Grep, Glob, WebSearch on the live codebase — no memory of prior discoveries persists between runs.

**Tolaria Advantage**: The MCP server (via `vault_context` and `search_notes`) exposes vault-structured knowledge. A vault storing research findings as typed entities (type: tool, type: pattern, type: integration-opportunity) with relationships (belongs_to, related_to, has) would allow the agent to build on prior discoveries instead of rediscovering patterns each time a research file is analyzed.

### Integration sketch

```python
# Pseudo-code: research-context-agent enhanced with tolaria MCP

def phase_1_absorb(research_file_path):
    research_content = read_file(research_file_path)

    # NEW: Query tolaria for prior research on the same tool/library
    prior_notes = mcp_call("search_notes", query=extract_tool_name(research_content))
    if prior_notes:
        research_content += "\n## Prior Research Notes\n"
        for note in prior_notes:
            research_content += f"- [[{note['title']}]] (type: {note['isA']}, status: {note['status']})\n"

    return research_content

def phase_2_search_and_match(research_content):
    opportunities = find_integration_opportunities_in_repo()  # existing: Grep/Glob search

    # NEW: Also search tolaria vault for patterns and prior integrations
    vault_context = mcp_call("vault_context")
    for opportunity in opportunities:
        related_notes = mcp_call("search_notes", query=opportunity['skill_name'])
        if related_notes:
            opportunity['vault_references'] = related_notes  # link to vault

    return opportunities

def write_integration_opportunities_section(opportunities):
    # NEW: Before writing to research file, create/update tolaria notes
    for opportunity in opportunities:
        note_data = {
            "type": "opportunity",
            "belongs_to": extract_tool_name(research_file_path),
            "related_to": opportunity['skill_name'],
            "status": "proposed",
            "links": opportunity.get('vault_references', [])
        }

        # Register the opportunity as a note in tolaria vault
        mcp_call("create_note",
                 title=f"Integration: {opportunity['skill_name']} + {tool_name}",
                 frontmatter=note_data,
                 content=opportunity['description'])

        # Link the research entry to the opportunity
        mcp_call("link_notes",
                 from_note="research.md",
                 to_note=f"opportunity-{opportunity['id']}",
                 relationship="has")
```

**Grounding in Research**: Lines 82-88 of tolaria.md document the MCP server's 14 tools. Lines 22-30 of tolaria.md describe the Semantic Field Names (type, status, belongs_to, related_to) that enable relationships. Lines 287-304 of ARCHITECTURE.md in tolaria repo specify tool names and signatures. Lines 419-435 of tolaria.md sketch "Integration Opportunities" including "AI Skill Development: Use Tolaria as a test environment for multi-agent orchestration. Store agent specifications as Type documents, log agent interactions as activity records, use the MCP server to coordinate agent handoffs."

---

## Utilization 2: context-gathering → Tolaria MCP Server

**Research entry**: ./research/developer-tools/tolaria.md
**Caller**: ./.claude/agents/context-gathering.md
**Integration mechanism**: MCP server (stdio connection to tolaria, async MCP tool calls)
**Replaces or adds**: Adds persistent task context storage and retrieval from a structured vault, accessible across sessions
**Setup cost**: Medium (tolaria installation, MCP registration, then reading from tolaria vault in context-gathering workflow)
**Integration surface**: Tolaria MCP server (tools: `vault_context`, `search_notes`, `list_notes`, `read_note`)

### Why this caller

The context-gathering agent assembles comprehensive context for a new task (lines 17–40 of context-gathering.md). It reads the task file, then hunts down:

- Every feature/service/module involved
- Components that communicate with those modules
- Configuration files and environment variables
- Database models and data access patterns
- Caching systems, auth flows, error handling patterns
- Existing similar implementations

This context is written as a "Context Manifest" section back into the task file (line 15 of context-gathering.md). **The problem**: the context manifest is task-specific and stored only in that task's file. If another task needs the same underlying knowledge (e.g., understanding how auth flows work, or what caching patterns the codebase uses), context-gathering re-researches those same components from scratch.

Tolaria's vault would store **reusable context components** as typed entities:

- type: `module` — describes a codebase module with its dependencies, interfaces, and common patterns
- type: `pattern` — describes a recurring architectural pattern (auth, caching, error handling) with examples
- type: `config` — documents environment variables, settings, and their relationships

A tolaria vault preloaded with these reusable components would allow context-gathering to:

1. Search for existing notes on modules/patterns the new task will touch
2. Link task context to those reusable notes instead of re-transcribing the same information
3. Resolve relationships (a service depends on auth pattern X, which uses config Y) via wikilinks

**Current Implementation**: Lines 36–85 of context-gathering.md describe researching "everything tangentially relevant." This research happens dynamically for each task, with no persistent knowledge graph connecting related findings across tasks.

**Tolaria Advantage**: A pre-populated vault (or one that grows over time with manually curated modules and patterns) becomes a **context cache**. Instead of hunting through the codebase on every task, context-gathering queries tolaria first: "What do we know about this module?" If a note exists (type: module, name matches), the agent can include a summary and link to it, reducing redundant research.

### Integration sketch

```python
# Pseudo-code: context-gathering enhanced with tolaria MCP

def step_1_understand_task(task_file_path):
    task = read_file(task_file_path)
    modules_involved = extract_modules_from_task(task)

    return task, modules_involved

def step_2_research_everything_with_vault(task, modules_involved):
    context = {}

    for module in modules_involved:
        # NEW: Query tolaria vault first
        vault_note = mcp_call("search_notes", query=module)

        if vault_note:
            # Context already documented in vault; link to it
            context[module] = {
                "source": "tolaria_vault",
                "note_title": vault_note['title'],
                "note_status": vault_note['status'],
                "snippet": vault_note['snippet'],
                "wikilink": f"[[{vault_note['filename']}]]"
            }
        else:
            # Context not in vault; research from codebase (existing behavior)
            context[module] = research_module_in_codebase(module)

            # NEW: After researching, store in tolaria vault for future reuse
            mcp_call("create_note",
                     title=f"Module: {module}",
                     frontmatter={"type": "module", "status": "documented"},
                     content=context[module]['full_description'])

    return context

def step_3_write_context_manifest(context_manifest):
    # Include vault references in the manifest
    manifest_section = "## Context Manifest\n\n"
    manifest_section += "### Modules and Dependencies\n"

    for module, info in context.items():
        if info.get('source') == 'tolaria_vault':
            manifest_section += f"- {module}: [[{info['note_title']}]] (cached in vault)\n"
        else:
            manifest_section += f"- {module}: (researched from codebase; consider archiving to vault)\n"

    # Append manifest to task file
    append_section_to_file(task_file_path, manifest_section)
```

**Grounding in Research**: Lines 74–80 of tolaria.md describe the VaultEntry data model with fields (title, type/isA, status, snippet, modifiedAt). Lines 219–230 define semantic field names including type and status. Lines 420–435 of tolaria.md note applications including "Vault as a Development Workspace: Store project specifications, architectural decisions, design patterns, and implementation notes as a structured git-backed knowledge graph."

---

## Skipped Systems

| Local System | Reason skipped |
|---|---|
| knowledge-explorer | Already manages research KB (research/) with equivalent scope to tolaria's vault. Tolaria would be a redundant parallel system, not a replacement. No clear advantage for knowledge-explorer to call tolaria instead of managing research/ directly. |
| backlog-tools (backlog.py, backlog-tools-administrator) | Integration surface exists (could store task metadata in tolaria vault), but Claude Code backlog system (GitHub Issues as source of truth, local .md cache) is architectural standard. Tolaria vault would fragment task state across two systems. No integration justification. |
| doc-drift-auditor | Audits documentation drift; doesn't manage knowledge or read/write persistent structures. No integration surface applicable. |

---
