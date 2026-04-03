# Improvement Proposals: AgentScope

**Research entry**: ./research/agent-frameworks/agentscope.md
**Generated**: 2026-03-28
**Patterns assessed**: 6
**Backlog items created**: 0
**Deferred (low confidence)**: 2
**Skipped (already covered or tracked)**: 4

---

## Improvement 1: Fine-grained MCP tool extraction from remote servers

**Source pattern**: "AgentScope's MCP support (HttpStatelessClient, fine-grained tool extraction) demonstrates production patterns for MCP tool integration, directly applicable to Claude Code MCP server usage." (Section: Relevance to Claude Code Development, Integration Patterns)
**Local system**: plugins/fastmcp-creator/skills/fastmcp-creator/SKILL.md
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred -- confidence medium: FastMCP v3 Client SDK reference (./references/client-sdk.md) may already cover client-side tool extraction patterns; that file was not fully read to confirm presence or absence

### Current state

The fastmcp-creator SKILL.md focuses on server creation (`@mcp.tool`, `@mcp.resource`, providers, transforms, deployment). The trigger matrix includes a "Write a FastMCP client" row pointing to `./references/client-sdk.md`, but the skill's primary orientation is server-side. AgentScope's pattern of obtaining individual MCP tools as local callable functions (`client.get_callable_function(func_name="maps_geo")`) and composing them into mixed toolkits (MCP tools + native tools in one Toolkit) is a client-side composition pattern that may not be documented in the local skill.

### Target state

The fastmcp-creator skill's client-sdk reference includes a documented pattern for: (a) extracting individual tools from a remote MCP server as local callables, (b) composing extracted remote tools with locally-defined tools into a single tool registry, and (c) wrapping individual MCP functions into composite tools that combine multiple remote calls.

### Measurable signal

The file `plugins/fastmcp-creator/skills/fastmcp-creator/references/client-sdk.md` contains a section titled "Fine-grained Tool Extraction" or equivalent, with a code example showing `Client.get_callable_function()` or equivalent FastMCP v3 API for extracting individual tools. A second example shows mixing remote-extracted tools with local `@mcp.tool` definitions in a single server.

---

## Improvement 2: Composable agent hook registries for pre/post processing

**Source pattern**: "AgentBase supports pre_reply, post_reply, pre_print, post_print, pre_observe, and post_observe hooks as OrderedDict-based class-level hook registries" and "Adapt AgentScope's class-level hook pattern for Claude Code agent preprocessing/postprocessing" (Sections: Key Features > Core Agent Types, Integration Patterns)
**Local system**: plugins/development-harness/skills/start-task/SKILL.md (hooks declaration), plugins/development-harness/skills/implementation-manager/scripts/task_status_hook.py
**Confidence**: Low
**Impact**: Low
**Backlog**: Deferred -- confidence low: The gap is inferred rather than directly observed. Claude Code's hook system (hooks.json, PostToolUse/SubagentStop events declared in SKILL.md frontmatter) is architecturally different from class-level hook registries. AgentScope's pattern assumes a Python class hierarchy where hooks are inherited and composed via OrderedDict; Claude Code hooks are event-driven shell/script invocations declared in YAML. Adopting OrderedDict-style composable registries would require replacing the hook dispatch mechanism, violating the "extend, not replace" gap rule.

### Current state

Hooks are declared per-skill in SKILL.md frontmatter (e.g., `hooks: PostToolUse: - matcher: Write|Edit|Bash`) and executed as external commands. The hook script `task_status_hook.py` handles SubagentStop and PostToolUse events. There is no mechanism for multiple skills to register ordered pre/post hooks on the same event with dependency ordering between them.

### Target state

Multiple skills could register hooks on the same agent lifecycle event with explicit ordering (before/after declarations), allowing composable middleware chains without modifying each skill's hook script.

### Measurable signal

A hooks configuration format supports `priority` or `before`/`after` fields in hook declarations, and the hook runner executes them in declared order. At least two skills register hooks on the same event with explicit ordering.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Fine-grained MCP tool extraction from remote servers | medium | Need to read `plugins/fastmcp-creator/skills/fastmcp-creator/references/client-sdk.md` fully to confirm whether FastMCP v3 Client SDK already documents individual tool extraction and mixed toolkit composition |
| Composable agent hook registries for pre/post processing | low | Claude Code's hook architecture (event-driven external commands) is fundamentally different from AgentScope's class-level Python hook registries; adopting this pattern would require replacing the hook dispatch mechanism rather than extending it |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Tool registry (Toolkit.register_tool_function) | Already covered -- FastMCP creator skill provides equivalent tool registration via `@mcp.tool` decorator and MCP server patterns. AgentScope's Toolkit is a Python runtime registry; Claude Code tools are registered via MCP protocol, which is the correct abstraction for this architecture. |
| Multi-agent coordination (MsgHub message routing) | Already covered -- swarm-operations SKILL.md provides TeamCreate, SendMessage (direct + broadcast), TaskCreate/TaskUpdate with dependency management, shutdown sequences, and inbox-based message routing. Functionally equivalent to MsgHub with managed participants. |
| Model abstraction (ChatModelBase consistent provider interface) | Not applicable -- Claude Code uses Anthropic as its sole model provider. A multi-provider abstraction layer solves a problem that does not exist in this architecture. |
| Memory and session management (JSONSession/RedisSession, memory compression) | Too abstract for actionable gap -- the research entry describes general-purpose session backends (in-memory, file, Redis). The local system uses file-based context (active-task-*.json) for task tracking and CLAUDE.md/rules for persistent configuration. A session abstraction layer would require designing a new subsystem rather than extending an existing one, and the specific benefits (memory compression, Redis backend) address scaling concerns not currently present in Claude Code's single-session execution model. |
