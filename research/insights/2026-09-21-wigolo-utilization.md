# Utilization Proposals: wigolo

**Research entry**: ./research/mcp-ecosystem/wigolo.md
**Generated**: 2026-09-21
**Integration surfaces found**: 2 (MCP server stdio, Python SDK, CLI, Docker)
**Proposals written**: 2
**Skipped**: 0

---

## Utilization 1: research-curator agent → wigolo

**Research entry**: ./research/mcp-ecosystem/wigolo.md
**Caller**: `.claude/agents/research-curator.md`
**Integration mechanism**: MCP server (stdio)
**Replaces or adds**: Replaces current mcp__Ref__ and mcp__exa__ MCP tools with wigolo's local-first web intelligence; adds capabilities (crawl, extract with ML scoring, vector search, page monitoring)
**Setup cost**: Medium (auth + schema — npm install, 1.5 GB disk for models/engine, .mcp.json configuration)
**Integration surface**: wigolo MCP server stdio with tools: search, fetch, crawl, extract, cache, find_similar, research, agent

### Why this caller

The research-curator agent currently gathers information about tools and libraries using `mcp__Ref__ref_search_documentation` and `mcp__exa__web_search_exa` MCP tools (documented at lines 87-94 of `.claude/agents/research-curator.md`). These tools require external API access and depend on third-party search services. Wigolo's local-first MCP server offers the same web research capabilities (search, fetch, extract) plus advanced features (crawl for multi-page research, ML-scored structured extraction, vector similarity search) without external APIs, billing, or cloud dependencies. This directly addresses the research entry's stated problem: "Agent web research requires external APIs and per-query billing" and "Extracting structured data from web pages requires manual parsing or expensive cloud extraction APIs" (line 29-31).

The agent's Phase 1 extraction workflow (line 42-54 of the agent file) involves fetching URLs and extracting passages. Wigolo's `fetch` tool with tiered escalation (HTTP → headless browser on signal detection) and `extract` tool with schema-based field extraction would streamline this phase, especially for JavaScript-heavy sites or pages behind anti-bot systems. The `research` tool could consolidate multi-step queries into a single coordinated call, reducing the number of agent iterations needed.

### Integration sketch

**Step 1: Add wigolo to plugin MCP configuration**

Create or update `.mcp.json` at the plugin root (or inline in `plugin.json` if single-server):

```json
{
  "wigolo": {
    "command": "npx",
    "args": ["wigolo"],
    "env": {
      "WIGOLO_DATA_DIR": "${CLAUDE_PROJECT_DIR}/.wigolo"
    }
  }
}
```

Environment setup (one-time):

```bash
npx wigolo init
```

This downloads ~1.5 GB of models and browser engine to the configured `WIGOLO_DATA_DIR`.

**Step 2: Update research-curator agent to use wigolo tools**

In the "Available Research Tools" section of `.claude/agents/research-curator.md` (after line 126), add:

```markdown
**Local-first web intelligence** (if wigolo MCP is configured):

- `mcp__plugin_wigolo_wigolo__search` -- query 18 search engines with ML reranking and result merging
- `mcp__plugin_wigolo_wigolo__fetch` -- retrieve single URLs with tiered escalation (HTTP → headless browser)
- `mcp__plugin_wigolo_wigolo__crawl` -- follow links across a site for multi-page research
- `mcp__plugin_wigolo_wigolo__extract` -- pull structured data with ML-scored direct citations, schema support
- `mcp__plugin_wigolo_wigolo__find_similar` -- vector similarity search against cached pages
- `mcp__plugin_wigolo_wigolo__research` -- multi-step synthesis: decompose question, plan parallel calls, optionally synthesize results
```

**Step 3: Routing logic in agent flow (conditional on wigolo availability)**

Add a branch in the agent's "Identify" flowchart step (around line 34-40):

```mermaid
Identify -->|"Wigolo MCP available<br>(check tool availability at start)"| UseWigolo[Use wigolo search/fetch/crawl/extract<br>for all web research steps]
Identify -->|"Wigolo not available<br>fall back to defaults"| Fallback[Use mcp__Ref__ and mcp__exa__ tools<br>as documented]
```

**Step 4: Concrete method signatures (grounded in wigolo research entry)**

Replace manual WebFetch loops with tool calls following the research entry's documented parameters (lines 41-60):

```python
# Before (multiple tool calls per URL):
fetch_url(url)
extract_text(page)
search_for_related(query)

# After (single wigolo call):
wigolo_extract(
    url=url,
    mode="structured",  # supports tables, JSON-LD, key-value pairs
    schema={
        "type": "object",
        "properties": {
            "feature_name": {"type": "string"},
            "description": {"type": "string"},
            "example": {"type": "string"},
        },
    },
)

# For multi-page research (crawl):
wigolo_crawl(url=start_url, max_depth=2, max_pages=10, include_domains=["docs.example.com"])

# For finding related documentation (vector search):
wigolo_find_similar(query="authentication middleware", max_results=5)
```

**Fallback**: If wigolo is not installed or the MCP server fails to start, the agent continues using the documented mcp__Ref__ and mcp__exa__ tools. The tool availability check is already part of the agent's startup (line 84: "Check the `<functions>` list in your system prompt for current MCP tool availability").

---

## Utilization 2: fact-check skill → wigolo

**Research entry**: ./research/mcp-ecosystem/wigolo.md
**Caller**: `.claude/skills/fact-check/SKILL.md` (spawns `@fact-checker` agents)
**Integration mechanism**: MCP server (stdio)
**Replaces or adds**: Replaces WebFetch and WebSearch tool calls in verification agents with wigolo's search and fetch tools; adds structured data extraction and page change detection
**Setup cost**: Medium (auth + schema — shared with research-curator if both use wigolo, one-time 1.5 GB disk, .mcp.json configuration)
**Integration surface**: wigolo MCP server stdio with tools: search, fetch, extract, diff

### Why this caller

The fact-check skill currently spawns `@fact-checker` agents that verify claims using "WebFetch output, WebSearch result, command output, repository source code, or MCP tool output" (lines 35-41 of `.claude/skills/fact-check/SKILL.md`). Each verification wave requires multiple tool calls to find a source URL, fetch its content, and extract the relevant passage. Wigolo's MCP server consolidates these steps: the `search` tool with configurable categories (lines 41-42 of the research entry) finds authoritative sources by category (e.g., "docs" for official documentation), the `fetch` tool with tiered escalation handles challenging URLs (behind Cloudflare, JavaScript-dependent pages), and the `extract` tool with schema support pulls structured fields directly. The `diff` tool (line 58 of research entry) adds a new capability: detecting when an official source has changed, which flags stale claims in the KB.

The skill's "Evidence Rules" (lines 29-51 of fact-check SKILL.md) require WebFetch or command output as primary evidence. Wigolo's `fetch` tool satisfies this requirement (documented as supporting MCP and command-line invocation at line 44 of wigolo research entry), and its `extract` tool with ML-scored direct citations provides verifiable passages matching the skill's "WebFetch output" standard.

### Integration sketch

**Step 1: Shared MCP configuration (if not already from research-curator integration)**

Add wigolo to `.mcp.json` as in Utilization 1, Step 1. (If already done, skip this.)

**Step 2: Update fact-checker agent spawning parameters**

In the fact-check skill's "Verification Agent Spawning" section (around line 85-95), expand the agent parameters:

```text
CLAIM: {exact claim text}
SOURCE_FILE: {file containing the claim, with line numbers}
PRIMARY_SOURCE: {URL or command to check against}
VERIFICATION_METHOD: WebFetch | WebSearch | CLI command | gh API | wigolo_fetch | wigolo_search
WIGOLO_CATEGORY: general | news | code | docs | papers (optional, hints search strategy)
FALSIFICATION_CRITERIA: {what would disprove this}
```

**Step 3: Fact-checker agent implementation (conditional on wigolo availability)**

In the spawned `@fact-checker` agent, add conditional routing:

```mermaid
Start([Receive claim and primary source]) --> CheckWigolo{Wigolo MCP<br>available?}
CheckWigolo -->|Yes| SearchWigolo[Use wigolo_search with<br>category=docs for official docs<br>or category=general for web]
CheckWigolo -->|No| FallbackFetch[Use WebFetch / WebSearch<br>as currently implemented]
SearchWigolo --> FetchWigolo[Use wigolo_fetch on<br>top-ranked result]
FetchWigolo --> ExtractWigolo[Use wigolo_extract with<br>schema for claim-specific fields]
FallbackFetch --> CurrentLogic[Proceed with existing<br>WebFetch/WebSearch flow]
ExtractWigolo --> Verify[Extract passage matches claim?]
CurrentLogic --> Verify
Verify -->|Match| VERIFIED
Verify -->|Mismatch| REFUTED
Verify -->|Inconclusive| INCONCLUSIVE
```

**Step 4: Concrete method signatures (grounded in wigolo research entry)**

Replace multiple tool calls with single wigolo calls:

```python
# Before (3+ tool calls per claim):
search_results = WebSearch(claim + " official documentation")
fetch_result = WebFetch(search_results[0]["url"])
extracted_text = extract_passages(fetch_result.content)

# After (1-2 wigolo calls):
search_results = wigolo_search(
    query=claim,
    category="docs",  # prioritize official documentation
    max_results=3,
    format="highlights",  # ML-scored highlights speed review
)

fetch_result = wigolo_fetch(
    url=search_results[0]["url"]
    # Tiered escalation handles JS-heavy sites, Cloudflare, etc.
)

extracted = wigolo_extract(
    url=search_results[0]["url"],  # or use cached fetch_result
    mode="structured",
    schema={"type": "object", "properties": {"claim_field": {"type": "string"}, "context": {"type": "string"}}},
)
# vigolo_extract returns ml_scored direct citations, matching Evidence Rule 1
```

**Step 5: New capability — detecting stale claims via page diff**

Add a check for KB entries that may have gone stale:

```python
# Optional: monitor when official sources change
if claim_is_old(entry.last_verified):
    diff_result = wigolo_diff(
        url=official_source_url
        # Second URL can be a cached version or omitted to compare against history
    )
    if diff_result.has_changes:
        mark_entry_as_stale(entry_path, diff_result.changes_summary)
```

This addresses the fact-check skill's stated problem: verifying claims without relying on training data recall. Wigolo's `diff` tool enables proactive staleness detection, not just reactive verification.

**Fallback**: If wigolo is not available, the skill falls back to the current WebFetch/WebSearch implementation. Tool availability is checked at agent startup.

---

## Skipped Systems

| Local System | Reason skipped |
|---|---|
| (None) | All identified callers (research-curator agent, fact-check skill) have concrete integration opportunities grounded in wigolo's documented APIs. No systems skipped. |

---

## Integration Readiness Summary

Both proposals are ready for implementation without architectural changes:

- **research-curator agent**: Wigolo enhances Phase 1 extraction (lines 42-54) and reduces iteration count for multi-page research
- **fact-check skill**: Wigolo improves verification speed, adds structured extraction, and enables staleness detection via diff

**Shared infrastructure**: Both use the same `.mcp.json` configuration and benefit from the 1.5 GB one-time model download. Running both agents sequentially reduces redundant engine initialization.

**Zero-key guarantee preserved**: Wigolo's design (research entry, line 4) requires no API keys for core tools (search, fetch, crawl, extract), aligning with this repo's preference for tools that don't require external credentials or billing.
