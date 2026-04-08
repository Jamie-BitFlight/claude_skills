# Utilization Proposals: CodeGraphContext

**Research entry**: ./research/mcp-ecosystem/codegraphcontext.md
**Generated**: 2026-04-08
**Integration surfaces found**: 3 (CLI | MCP Server | Python SDK)
**Proposals written**: 2
**Skipped**: 1

---

## Utilization 1: doc-drift-auditor → CodeGraphContext

**Research entry**: ./research/mcp-ecosystem/codegraphcontext.md
**Caller**: ./.claude/agents/doc-drift-auditor.md
**Integration mechanism**: MCP tool call + CLI subprocess
**Replaces or adds**: Enhances code analysis phase with deterministic relationship queries instead of regex-based pattern matching
**Setup cost**: Medium (MCP server setup + cgc index operation on target repo)
**Integration surface**: `find_code(query, fuzzy_search, edit_distance)`, `analyze_code_relationships(query_type, target, context)`, `get_repository_stats(repo_path)` (MCP tools); `cgc analyze callers|callees|tree|dead-code` (CLI commands)

### Why this caller

The doc-drift-auditor agent currently performs static code analysis via grep and heuristics to catalog implemented features and compare them against documentation claims (see `.claude/agents/doc-drift-auditor.md` lines 39-94). This approach relies on pattern matching and file path assumptions, which can miss implicit implementations, lose accuracy on refactored code, and struggle with multi-language codebases. CodeGraphContext's exact AST-based code graph provides deterministic answers: when the auditor wants to know "is authenticate_user actually called anywhere?" or "what functions implement the BaseController interface?", it can query the graph directly instead of scanning files. The `analyze_code_relationships` MCP tool returns exact call relationships with file:line evidence, and `get_repository_stats` provides a ground-truth inventory of functions, classes, and modules. This eliminates false negatives (undocumented code missed) and false positives (documented patterns that don't exist).

### Integration sketch

```python
# Current approach (doc-drift-auditor.md line 38-45):
# Uses grep + manual pattern matching to find code entities
grep -n "^class \|^def " implementation_file.py
# Output: unreliable for multi-file call chains, dynamic code

# New approach with CodeGraphContext:
from codegraphcontext import CodeGraphContextClient

client = CodeGraphContextClient()  # Connects to MCP server

# Index the repository once
client.add_code_to_graph(repo_path="/path/to/codebase")

# Query exact relationships
callers = client.analyze_code_relationships(
    query_type="callers",
    target="authenticate_user"
)
# Returns: [{name: "login_handler", file: "api/auth.py", line: 45}, ...]

# Validate documentation claims
dead_functions = client.find_dead_code(exclude_decorated_with=["@deprecated"])
# Returns: exact list of unused functions with file:line

# Get repository inventory
stats = client.get_repository_stats(repo_path)
# Returns: {classes: N, functions: M, modules: K, dead_code: [list]}

# Compare documented claims vs. actual stats
if documented_function_count != stats["functions"]:
    # Log drift
```

---

## Utilization 2: context-gathering → CodeGraphContext

**Research entry**: ./research/mcp-ecosystem/codegraphcontext.md
**Caller**: ./.claude/agents/context-gathering.md
**Integration mechanism**: MCP tool call
**Replaces or adds**: Extends context manifest with deterministic code relationship discovery and impact analysis
**Setup cost**: Medium (MCP server setup; cgc index runs once, incrementally watches for changes)
**Integration surface**: `analyze_code_relationships(query_type, target, context)`, `find_code(query)`, `find_dead_code()`, `get_repository_stats(repo_path)` (MCP tools)

### Why this caller

The context-gathering agent builds comprehensive context manifests for new tasks by reading existing code paths, tracing flows, and documenting affected services (see `.claude/agents/context-gathering.md` lines 16-127). Currently, this relies on manual file reads and code tracing by the agent, which is token-expensive and can miss cross-cutting concerns like indirect call chains, ripple effects across modules, and dead code that might be incorrectly assumed alive. When a new task modifies a function, the agent must manually trace every caller and callee—a process prone to incompleteness in large codebases. CodeGraphContext's `analyze_code_relationships` MCP tool answers "what calls X?" and "what does X call?" in one query, with guaranteed completeness (AST-based, no false negatives). The agent can enrich context manifests with exact impact radius: "modifying process_payment will affect these 7 functions" (from the graph), reducing human error and improving implementation safety.

### Integration sketch

```python
# Current approach (context-gathering.md lines 38-63):
# Agent manually reads files and traces code paths
# High token cost, incomplete on large codebases

# New approach with CodeGraphContext:
from codegraphcontext import CodeGraphContextClient

client = CodeGraphContextClient()

# Index repo once (can happen at project setup or incrementally via cgc watch)
client.add_code_to_graph(repo_path=task_file["project_path"])

# When task requires modifying a function, get complete impact:
impact = client.analyze_code_relationships(
    query_type="callers",
    target="process_payment"
)
# Returns exact list: [{name: "order_handler", file: "...", line: ...}, ...]

# Get what the function calls (to understand dependencies):
callees = client.analyze_code_relationships(
    query_type="callees",
    target="process_payment"
)

# Include in context manifest:
context_manifest = f"""
## Impact Analysis: Modifying process_payment

This function is called by {len(impact)} other functions:
{format_impact_list(impact)}

It directly calls {len(callees)} functions:
{format_callees_list(callees)}

Tests that exercise process_payment:
{find_tests_for_function(impact, callees)}
"""

# Append to task file
task_file.context_manifest.append(context_manifest)
```

---

## Skipped Systems

| Local System | Reason skipped |
|---|---|
| code-review (`./.claude/agents/code-review.md`) | The code-review agent reviews code changes for security, performance, and pattern adherence (lines 19-90). While CGC's `find_most_complex_functions` and `find_dead_code` could provide supporting metrics, the agent's core review process (identifying LLM slop, checking error handling, tracing logic errors) requires semantic understanding of code intent, not just relationship analysis. CGC provides structural data; code review requires behavioral analysis. Integration would be useful for supplementary metrics (e.g., "this function has 15 callers—be careful with changes") but not for core review logic. This is a "nice to have" enhancement, not a capability gap. Defer as a low-impact future extension. |

---

## Integration Path Forward

CodeGraphContext is an alpha release (v0.4.0, per research entry line 452). Before committing to integration:

1. **Proof of Concept**: Test CGC's MCP server startup, index a real repo, and validate query accuracy against manual code inspection
2. **Setup Protocol**: Document the `cgc mcp setup` and index workflow in `.claude/rules/` for agents to follow
3. **Incremental Integration**: Start with doc-drift-auditor (audits are read-only, lowest risk), then context-gathering
4. **Watch Pattern**: Leverage `cgc watch` for incremental re-indexing during active development to keep the graph fresh

The MCP server mode is the best integration path (vs. CLI subprocess) because it avoids spawning separate processes and provides streaming results.

