# Utilization Proposals: zvec-grep

**Research entry**: ./research/ai-research-tools/zvec-grep.md
**Generated**: 2026-09-11
**Integration surfaces found**: 3 (npm package | CLI | MCP server)
**Proposals written**: 3
**Skipped**: 1

---

## Utilization 1: context-gathering agent → zvec-grep

**Research entry**: ./research/ai-research-tools/zvec-grep.md
**Caller**: ./.claude/agents/context-gathering.md
**Integration mechanism**: MCP (Model Context Protocol)
**Replaces or adds**: Augments the agent's current file-reading workflow with semantic search for discovering architectural context
**Setup cost**: Low (npm install + MCP server registration)
**Integration surface**: MCP tool `zvec_grep_search`; CLI `zg --vector "<query>"`

### Why this caller

The context-gathering agent reads files and traces call paths to build comprehensive context manifests for tasks. Its current workflow relies on manual Grep and file-reading to locate related code, database models, authentication patterns, and service boundaries. zvec-grep's semantic search (`--vector`) would accelerate discovery of these "tangentially relevant" systems — especially for architectural questions that span multiple files and modules. The agent explicitly notes "Include ANYTHING tangentially relevant" and "Spare no tokens" — vector search directly addresses this goal by ranking relevance across the codebase without requiring exact keywords.

Reference: `./.claude/agents/context-gathering.md` lines 27-39 (research step and artifact gathering) would benefit from `zg --vector "where is authentication checked for this feature"` rather than manually reading auth files.

### Integration sketch

```python
# Pseudo-code integration pattern
from zvec_grep_client import ZvecGrepMCP


async def gather_architectural_context(task_domain: str) -> List[RelevantFile]:
    """Use zvec-grep to find related components across the codebase."""

    client = ZvecGrepMCP()

    # Semantic search for related systems
    results = await client.zvec_grep_search(query=f"where is {task_domain} implemented", limit=10)

    # Results include file paths, line numbers, relevance scores
    # Agent reads returned files to build context manifest
    for result in results:
        if result.confidence > 0.7:  # High relevance threshold
            context.add_file(result.file_path, result.snippet)
```

**MCP invocation** (once installed):

```text
Agent calls MCP tool: zvec_grep_search
Input: { query: "where authentication is validated in this codebase", limit: 10 }
Output: Ranked results with file paths, line numbers, code snippets
```

**CLI fallback** (for testing or standalone use):

```bash
zg --vector "authentication validation" --modified-after "1 month ago" --limit 10
```

---

## Utilization 2: find-cause skill → zvec-grep

**Research entry**: ./research/ai-research-tools/zvec-grep.md
**Caller**: ./.claude/skills/find-cause/SKILL.md
**Integration mechanism**: CLI subprocess + result parsing
**Replaces or adds**: Improves evidence gathering by replacing keyword-only Grep with hybrid search (BM25 + vector + ripgrep)
**Setup cost**: Low (npm install)
**Integration surface**: CLI `zg <query>`, `zg --fts "<query>"`, `zg --rg -i -C 2 -g "*.ts" "<pattern>"`

### Why this caller

The find-cause skill's Step 2 and Step 3 investigate root causes by reading source files and searching for evidence. The current evidence chain relies on Grep and manual file reading, which requires exact keywords or regex patterns to locate relevant code. zvec-grep's multi-mode search would strengthen the investigation by:

1. **BM25 lexical search** (`--fts`) — ranked keyword matching when the exact term is unknown
2. **Vector search** (`--vector`) — semantic queries like "where is this error handled?" without knowing the exact variable/function name
3. **Ripgrep integration** (`--rg`) — exact matches and regex patterns when patterns are known

Reference: `./.claude/skills/find-cause/SKILL.md` lines 100-107 list the evidence verification paths. zvec-grep's multi-format indexing (source code symbols, structured data, plain text) directly maps to this requirement: "can you observe it directly by running the system, or must you read source/docs?"

### Integration sketch

```bash
#!/bin/bash
# Pseudo-code: find-cause skill using zvec-grep to gather evidence

# Step 1: Semantic search for the problem area
zg --vector "where is the timeout error handled" --limit 5

# Step 2: If semantic search returns candidates, confirm with exact match
zg --rg -i -C 3 "TIMEOUT_ERROR\|timeout.*error" src/

# Step 3: Fallback to BM25 if exact match fails
zg --fts "timeout handling retry logic" --limit 10

# All results are ranked and include file:line citations
# Agent parses output and adds to evidence chain
```

**Invoke via subprocess**:

```python
import subprocess
import json

result = subprocess.run(["zg", "--vector", "error handling pattern", "--limit", "10"], capture_output=True, text=True)

# Parse JSON output (zg supports --json flag)
evidence = json.loads(result.stdout)
for item in evidence:
    print(f"Evidence: {item['file']}:{item['line']} - {item['snippet']}")
```

---

## Utilization 3: codebase-analyzer agent → zvec-grep

**Research entry**: ./research/ai-research-tools/zvec-grep.md
**Caller**: ./plugins/development-harness/agents/codebase-analyzer.md
**Integration mechanism**: MCP (Model Context Protocol) or CLI
**Replaces or adds**: Accelerates pattern discovery and symbol-aware retrieval when analyzing CLI commands, testing patterns, and module structure
**Setup cost**: Medium (npm install + MCP registration in development-harness plugin configuration)
**Integration surface**: MCP tool `zvec_grep_search` with `prefer_symbol` flag; CLI `zg --prefer-symbol --type function "pattern"`

### Why this caller

The codebase-analyzer agent explores codebases to extract CLI patterns, architecture, testing patterns, and conventions. Its current workflow relies on Grep and Read to trace patterns across files. zvec-grep's **symbol-aware retrieval** (`--prefer-symbol`) would directly accelerate this:

1. **CLI command patterns** — Find all CLI subcommands and their implementations: `zg --prefer-symbol --type function "handleCommand" --limit 20`
2. **Testing fixtures** — Locate test utilities and fixtures: `zg --vector "test fixture for mocking" --prefer-symbol --type function`
3. **Module structure** — Understand dependencies and boundaries: `zg --prefer-symbol --type module "exports from auth"`

Reference: `./plugins/development-harness/agents/codebase-analyzer.md` lines 40-54 (philosophy and prescriptive approach) emphasize accurate file paths and concrete patterns. zvec-grep's symbol extraction and line-number accuracy directly support this requirement.

### Integration sketch

```typescript
// Pseudo-code: codebase-analyzer using zvec-grep MCP

async function discoverCliPatterns(): Promise<CliPattern[]> {
  const client = createMCPClient('zvec-grep');

  // Query 1: Find all CLI command handlers
  const results = await client.zvec_grep_search({
    query: 'function that handles CLI commands',
    prefer_symbol: true,
    type_filter: ['function'],
    limit: 50
  });

  // Query 2: Find test utilities
  const testUtils = await client.zvec_grep_search({
    query: 'test fixture mock setup',
    prefer_symbol: true,
    modified_after: '1 week ago'
  });

  // Results include symbol names, file paths, line ranges
  // Enables registration of artifact with concrete references
  return extractPatterns(results);
}
```

**CLI alternative** (for development/validation):

```bash
zg --prefer-symbol --type function "pattern discovery" --limit 20
zg --vector "testing fixture boilerplate" --prefer-symbol --limit 10
zg --rg -i -g "test*.ts" "beforeEach\|setUp" --modified-after "1 month ago"
```

---

## Skipped Systems

| Local System | Reason skipped |
|---|---|
| `research-context-agent` (`./.claude/agents/research-context-agent.md`) | Already specialized in searching the research knowledge base itself, not codebases. Integration would add search across general code, which is outside its scope. No overlap with zvec-grep's use case (code/codebase search, not research KB). |

---

## Integration Notes

### Prerequisites

1. **Node.js 22+** — zvec-grep requires Node.js 22 or newer
2. **npm install** — `npm install -g @zvec/zvec-grep` or as a project dependency
3. **Workspace indexing** — First run `zg --index --embedding local/potion-retrieval-32m` to build the search index
4. **MCP server registration** — Add to `.mcp.json` or agent tool configuration:

   ```json
   {
     "mcpServers": {
       "zvec-grep": {
         "command": "zg",
         "args": ["--server"]
       }
     }
   }
   ```

### Cost Breakdown

- **Setup cost**: Low for CLI, Medium for MCP (requires .mcp.json registration)
- **First run**: ~2-5 minutes to index a large codebase (embedding model download + indexing)
- **Search latency**: <500ms for cached queries; <2s for initial vector embeddings
- **Storage**: 100MB–1GB per indexed workspace depending on code volume and embedding model

### Recommended Adoption Order

1. **Phase 1** (Quick win): Integrate with `find-cause` skill via CLI. No MCP setup required.
2. **Phase 2** (Agent benefit): Register MCP server and integrate `codebase-analyzer` agent for pattern discovery.
3. **Phase 3** (Context acceleration): Integrate `context-gathering` agent with MCP for architectural queries.

All three proposals are independent and can be implemented in parallel or sequentially.
