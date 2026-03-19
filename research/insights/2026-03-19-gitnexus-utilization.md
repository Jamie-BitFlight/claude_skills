# Utilization Proposals: GitNexus

**Research entry**: ./research/mcp-ecosystem/gitnexus.md
**Generated**: 2026-03-19
**Integration surfaces found**: 2 (MCP server CLI | Agent skills generation | PreToolUse/PostToolUse hooks)
**Proposals written**: 2
**Skipped**: 3 — (python3-development plugin uses Grep/Glob for exploration instead of graph queries; no existing impact-analysis agent in this repo; context-gathering already has codebase reading capability but doesn't perform impact analysis)

---

## Utilization 1: python3-development plugin → GitNexus MCP impact analysis

**Research entry**: ./research/mcp-ecosystem/gitnexus.md
**Caller**: ./plugins/python3-development (agents: code-reviewer, context-refinement, feature-verifier)
**Integration mechanism**: MCP tool call (`gitnexus_impact`, `gitnexus_detect_changes`)
**Replaces or adds**: Replaces manual blast-radius estimation with precomputed graph-based impact analysis
**Setup cost**: Low (MCP server setup one-time; tools accessed via existing MCP client in Claude Code)
**Integration surface**: MCP tools `impact` (line 133) and `detect_changes` (line 134) from research entry

### Why this caller

The python3-development plugin contains multiple agents that review code and assess impact (code-reviewer, context-refinement, feature-verifier agents documented in local-workflow.md). Currently, these agents rely on:
- Manual symbol tracing through grep/Glob searches (line 36 in research entry notes Grep is used for exploration)
- Unstructured codebase exploration to find dependents
- Heuristic-based risk estimation

GitNexus's `impact` tool (documented at line 133-143 in research entry) provides:
- Precomputed depth-grouped dependency analysis (Depth 1 = WILL BREAK, Depth 2 = LIKELY AFFECTED, Depth 3 = transitive)
- Confidence scoring for impact assessment
- Process-grouped results showing which execution flows are affected

This directly enables:
1. **code-reviewer agent**: Pre-change impact verification before recommending edits
2. **context-refinement agent**: Confidence-grounded scope assessment for plan artifact updates
3. **feature-verifier agent**: Structural verification of whether changes introduced unintended side effects

The `detect_changes` tool (line 134-144 in research entry) maps git diffs to affected symbols and execution flows—enabling the agents to understand blast radius of actual committed changes, not just proposed ones.

### Integration sketch

**For code-review impact assessment**:
```python
# Pseudo-code showing tool call pattern from research entry line 133-143
impact_result = gitnexus_impact({
    "target": "function_or_class_name",
    "direction": "upstream"  # Find all callers
})

# Returns depth-grouped results:
# {
#   "depth_1": [{"symbol": "directCaller", "process": "auth_flow"}],
#   "depth_2": [{"symbol": "indirectCaller", "process": "http_handler"}],
#   "confidence": "HIGH"
# }

# Agent reports to user:
# "Impact of modifying X: WILL BREAK 3 direct callers (HIGH confidence),
#  LIKELY AFFECTED 7 indirect dependents in payment_processing flow"
```

**For post-commit verification**:
```python
# From research entry line 144, detect_changes maps diffs to execution flows
changed_impact = gitnexus_detect_changes({
    "scope": "staged",
    "repo": repo_name
})

# Returns: {
#   "changed_symbols": ["validateUser", "authCache.clear"],
#   "affected_processes": ["auth_flow", "session_cleanup"],
#   "risk_level": "MEDIUM"
# }
```

**Hooks integration** (from research entry lines 375-377):
- PreToolUse hook enriches searches (already in .worktrees/GitNexus integration)
- PostToolUse hook auto-reindexes after commits (ensures agents see fresh graph)

---

## Utilization 2: development-harness plugin → GitNexus wiki generation + agent skills

**Research entry**: ./research/mcp-ecosystem/gitnexus.md
**Caller**: ./plugins/development-harness (service-docs-maintainer agent)
**Integration mechanism**: CLI command (`npx gitnexus wiki`, `npx gitnexus analyze --skills`)
**Replaces or adds**: Adds capability to auto-generate architecture documentation and repo-specific skills from knowledge graph
**Setup cost**: Low (CLI installed globally; OpenAI key required for wiki generation, but optional)
**Integration surface**: CLI commands `wiki` (line 220, 228-235) and `analyze --skills` (line 210, 190-194) from research entry

### Why this caller

The development-harness plugin contains `service-docs-maintainer` agent (referenced in local-workflow.md Phase 3), which runs when documentation drift is detected. Currently it:
- Manually reviews doc/code divergence
- Edits documentation files
- Lacks automated architectural view from code structure

GitNexus provides two complementary CLI features:

1. **Wiki Generation** (line 220-235 in research entry):
   - Reads indexed graph structure
   - Groups files into modules via LLM
   - Generates per-module documentation with cross-references
   - Works with custom LLM models (default: gpt-4o-mini)

2. **Repo-Specific Skills** (line 190-194 in research entry):
   - Detects functional areas via Leiden community detection
   - Generates SKILL.md file for each community under `.claude/skills/generated/`
   - Describes entry points, execution flows, cross-area connections
   - Regenerated on each analyze run to stay current

This enables:
- **service-docs-maintainer agent**: Bootstrap architecture docs from code structure instead of manual authoring
- **workflow context**: Generated skills populate `.claude/skills/generated/`, which can be referenced in task files
- **architecture documentation**: Mermaid diagrams and execution flow documentation auto-generated from the knowledge graph

### Integration sketch

**Wiki generation** (from research entry line 220, 228-235):
```bash
# Pre-commit or post-merge hook:
npx gitnexus wiki --model gpt-4o-mini

# Produces markdown documentation in .gitnexus/wiki/:
# - overview.md (architecture summary with cross-references)
# - module-auth.md (authentication module docs)
# - module-payment.md (payment processing module docs)
# - etc. per detected community

# service-docs-maintainer can then:
# 1. Copy/merge wiki output into repository docs/
# 2. Add custom sections (e.g., deployment guide, API reference)
# 3. Commit updated docs
```

**Skills generation** (from research entry line 210, 190-194):
```bash
# After indexing:
npx gitnexus analyze --skills

# Generates per-community skill files:
# .claude/skills/generated/auth-module.md
# .claude/skills/generated/payment-processing.md
# etc.

# Each skill includes:
# - Key files and entry points
# - Execution flows (from line 5: "157 execution flows" in GitNexus index)
# - Cross-area connections
# - Community-specific patterns

# Tasks can then reference: "skills: ['generated/auth-module']"
```

**Hook integration** (from research entry line 375-377):
- PostToolUse hook auto-reindexes after commits
- Enables wiki/skills to be regenerated automatically to stay current

---

## Skipped Systems

| Local System | Reason skipped |
|---|---|
| context-gathering agent | Already reads codebase via Grep/Glob for symbol discovery. GitNexus would enhance but not replace—integration would be additive complexity without displacing existing capability. Deferring to Phase 2 once impact tool adoption proven. |
| generic refactoring agents | No local refactoring agent found that matches GitNexus's `rename` tool scope. Skipped pending discovery of dedicated refactoring task workflow. |
| doc-drift-auditor agent | Reads-only code comparison for drift detection. GitNexus integration would be for structural analysis, not drift audit itself. Architecture better served by service-docs-maintainer integration. |

---

## Integration Priority and Dependencies

1. **Utilization 1** (python3-development impact analysis): **HIGH PRIORITY**
   - Unblocks better risk assessment in code-review phase
   - Reduces false-positive estimates in feature-verifier
   - Feeds into context-refinement confidence scoring

2. **Utilization 2** (development-harness wiki generation): **MEDIUM PRIORITY**
   - Unblocks architecture documentation generation
   - Reduces manual burden on service-docs-maintainer
   - Depends on Utilization 1 infrastructure (MCP client setup)

Both proposals assume `.worktrees/GitNexus/gitnexus-claude-plugin/` is available and registered as an MCP server.

---

## Next Steps

1. **Verify MCP server registration**: Check that `gitnexus mcp` is available to Claude Code as an MCP tool (likely already configured in `.worktrees/GitNexus`)
2. **Add impact-analysis calls to code-reviewer**: Integrate `gitnexus_impact()` calls before code change recommendations
3. **Test detect_changes integration**: Verify PostToolUse hook properly invokes `gitnexus_detect_changes()` for staged commits
4. **Enable wiki generation in service-docs-maintainer**: Add CLI invocation for `npx gitnexus wiki` with LLM model configuration
5. **Validate skills generation**: Confirm `.claude/skills/generated/` skills are discoverable by task file skill: field

