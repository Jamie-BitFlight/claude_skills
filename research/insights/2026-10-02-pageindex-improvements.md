# Improvement Proposals: PageIndex

**Research entry**: ./research/context-management/pageindex.md
**Generated**: 2026-10-02
**Patterns assessed**: 5
**Backlog items created**: 0
**Deferred (low confidence)**: 1
**Skipped (already covered or tracked)**: 4

The duplicate check against the backlog could not run: `backlog_list` with a search filter
returned `GraphQL is unavailable in this environment` (backend GitHub, reachable, 826 open
items). No proposal reached high confidence, so no item would have been created either way.
Re-run the duplicate check before promoting the deferred proposal below.

---

## Improvement 1: PDF-capable tree-index retrieval behind the existing progressive markdown engine

**Source pattern**: the Integration Opportunities item "PageIndex SDK as MCP tools (`index_document`, `query_index`) for PDF sources" (Relevance to Claude Code Development > Integration Opportunities, `docs/MCP-INDEX.md`); mechanism described under Technical Architecture > Retrieval Flow ("Only the nodes the model reached are fetched") and Citation Handling (`{document, page, [block_id]}`).
**Local system**: `plugins/development-harness/progressive_markdown/navigator.py`, `plugins/development-harness/docs/agent-markdown-consumption-contract.md`, `plugins/summarizer/skills/file-summarization/SKILL.md`
**Absence evidence**: `git grep -il "pageindex" -- . ':!research/'` -> 0 matches (outside `research/`, no file mentions PageIndex; inside `research/`, `git grep -il "pageindex" -- . ':!research/context-management/pageindex.md'` -> 7 files, all under `research/`: the five entries `research/ai-research-tools/samuraizer.md`, `research/context-management/jina-ai.md`, `research/context-management/sourcesyncai.md`, `research/data-infrastructure/chroma.md` and `research/mcp-ecosystem/docs-mcp-server.md`, plus the two insight files for this entry). `git grep -il "pdf" -- plugins/ .claude/skills/ .claude/agents/` (excluding images/HTML) -> 42 files; the reading-related hits are `plugins/summarizer/skills/file-summarization/SKILL.md:47` ("Use a host-provided or available format-aware reader") and `plugins/summarizer/README.md:56` ("no bundled parser"), plus `.claude/skills/agent-browser/SKILL.md:236-240` (open a local PDF in a browser). None builds a navigable tree over a PDF.
**Confidence**: Medium
**Impact**: Low
**Backlog**: Deferred — confidence Medium: the tree-map-then-read-only-what-you-need pattern already exists for Markdown, and no observed failure shows agents in this repo need PDF retrieval

### Current state

The PageIndex retrieval pattern (build a hierarchical index, let the model read the map, fetch
only the nodes it selects) already exists for Markdown. `ProgressiveMarkdownNavigator` in
`plugins/development-harness/progressive_markdown/navigator.py` exposes `map()` (line 194, a
paginated document map), `view_section(ref)` (line 236) and `view_code()`, each bounded by a
token budget. The navigator is served to agents through the `backlog_view` disclosure path
(`plugins/development-harness/backlog_core/server.py:2452-2465`). R1 of
`agent-markdown-consumption-contract.md` requires "A single markdown engine serves every markdown
consumption path ... No component may hand-build a table of contents". A new standalone PageIndex
MCP server would be a second engine, which R1 calls a defect.

What is missing is non-Markdown input. For PDFs, `file-summarization` defers to whatever reader
the host provides, and nothing produces a section tree or page-cited results for a PDF.

### Target state

A provider for PDF sources feeds the existing progressive markdown engine, so a PDF reaches agents
through the same `map()` / `view_section()` contract and does not get a parallel MCP server.
`plugins/development-harness/progressive_markdown/providers.py` is where that provider would go
(the file exists; its PDF support was not evaluated). Results carry page provenance, matching
PageIndex's `{document, page}` citation shape. Choosing between PageIndex Flash (layout
statistics, no LLM) and a plain parser is a dependency decision for
`research-utilization-assessor`, not part of this proposal.

### Measurable signal

A PDF path passed to the navigator returns a `NavigationKind.document_map` result whose entries
include page numbers, and `view_section` on one entry returns that section's text with its page
range. Before promoting this to the backlog, find at least one agent workflow in this repo that
failed or overflowed context while reading a PDF.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| PageIndex MCP server for long-document retrieval (Improvement 1) | medium | Markdown tree navigation already exists (`progressive_markdown`, contract R1). To raise confidence, show that agents here really need to read PDFs, and confirm whether `progressive_markdown/providers.py` can take a non-Markdown source. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Long document analysis in `research-utilization-assessor` | Research entries are Markdown (`research/context-management/pageindex.md` is 247 lines), and PageIndex targets PDFs. Wiring an external SDK into an agent is a dependency integration, which falls under `.claude/agents/research-utilization-assessor.md` itself and not under gap extraction. No observable gap. |
| Document-based agent tools (formerly anchored to `AGENTS.md` in the entry) | Too abstract: it named no mechanism or target state, and the quoted "Today" text ("When the user says \"can you\" ...") described delegation, not document handling. The item was removed from the entry's Relevance section; nothing remains to implement. |
| Multi-document synthesis in `research-insight-extractor` | Inputs are Markdown research entries and local files, which the agent reads directly. The claim that cross-entry pattern finding "would be expensive or impossible" is not backed by any observed failure. The entry's Limitations section records whether cross-document relationships are modeled structurally as "not mentioned in documentation"; that is not the same as PageIndex not doing it. |
| Hierarchical information organization (formerly anchored to `plugins/development-harness/dh_core/ledger_spec.py` in the entry) | The entry's claim that `ledger_spec.py` "already models tasks as structured hierarchies" was not supported: `git grep -c -i "hierarch" -- :/plugins/development-harness/dh_core/ledger_spec.py` matches 0 lines. The item was removed from the entry. |
| (Integration Opportunity, standalone MCP server form) | Folded into Improvement 1. A standalone server would break R1 of `agent-markdown-consumption-contract.md` (one markdown engine), so the only compatible form extends the existing engine. |
