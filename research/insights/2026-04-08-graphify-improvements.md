# Improvement Proposals: graphify

**Research entry**: ./research/skill-generation-tools/graphify.md
**Generated**: 2026-04-08
**Patterns assessed**: 8
**Backlog items created**: 0
**Deferred (low confidence)**: 3
**Skipped (already covered or tracked)**: 5

---

## Improvement 1: Add claim-level provenance tags to research entries

**Source pattern**: "Relationship classification: Every edge is tagged with confidence level: EXTRACTED -- relationship found directly in source; INFERRED -- reasonable deduction with confidence score (0.0-1.0) assigned by Claude; AMBIGUOUS -- uncertain relationships flagged for human review in the report" (Key Features section, lines 41-44)
**Local system**: .claude/agents/research-curator.md
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred -- confidence Medium: the research-curator already requires "every factual claim in that section traces to at least one extracted passage" (line 232) and tags Phase 1b code extracts with `Confidence: code-read` (line 226). Section-level confidence is recorded in Freshness Tracking. The gap is whether adding per-claim EXTRACTED/INFERRED/AMBIGUOUS tags would provide materially different value beyond the existing claim-tracing rule. Verification would require analyzing existing research entries to determine whether claims of different provenance types are distinguishable or whether the existing methodology already prevents untagged inferences from entering entries.

### Current state

The research-curator agent (`.claude/agents/research-curator.md`, lines 119-232) uses a two-phase extractive methodology. Each extracted passage records its source (`Source: {URL or tool + section}`) and relevance (`Relevance: {section name}`). Phase 1b code extracts add `Confidence: code-read`. The final entry includes section-level confidence in the Freshness Tracking table (high/medium). Individual claims within a section are not tagged with provenance type. All claims must trace to an extract, but the entry file does not preserve whether a claim was directly extracted vs. reasoned from an extract.

### Target state

Each factual claim in a research entry includes an inline provenance tag: `[EXTRACTED]` for verbatim quotes, `[INFERRED]` for reasonable deductions from sources, `[AMBIGUOUS]` for uncertain claims requiring review. The Freshness Tracking table includes a per-section count of EXTRACTED vs INFERRED claims. The entry template in `./references/entry-template.md` documents the tagging syntax.

### Measurable signal

Read any research entry produced after the change. Each non-trivial factual claim (version numbers, statistics, architectural assertions, capability claims) includes one of `[EXTRACTED]`, `[INFERRED]`, or `[AMBIGUOUS]` inline. The Freshness Tracking table row for each section includes a column showing the provenance breakdown (e.g., "8 extracted, 2 inferred, 0 ambiguous").

---

## Improvement 2: Add content-hash skip logic to research-curator rerun mode

**Source pattern**: "SHA256 cache ensures unchanged files are never re-processed" and "Incremental updates (--update): Re-extracts only changed files, merges with existing graph, regenerates wiki if present. SHA256 cache ensures unchanged files are never re-processed." (Key Features section, lines 52, 86)
**Local system**: .claude/skills/research-curator/SKILL.md (Rerun Mode, lines 209-271)
**Confidence**: Low
**Impact**: Low
**Backlog**: Deferred -- confidence Low: the cost structure is fundamentally different between the two systems. graphify processes local files (re-reading unchanged code is wasted compute). The research-curator re-gathers data from remote sources -- the whole purpose of `--rerun` is to check whether remote data has changed. A content hash of the local entry file would not help because the question is whether the remote source has new information, not whether the local file changed. The pattern would only be useful if the research-curator cached remote source responses by hash, which would require a different caching architecture (response cache, not content cache).

### Current state

The research-curator rerun mode (`.claude/skills/research-curator/SKILL.md`, lines 242-248) re-processes an entire entry: the `@research-curator` agent reads the existing entry, re-gathers fresh data from primary sources, re-extracts passages, and updates content. No mechanism exists to detect "nothing has changed at the source" and skip re-processing. Every rerun incurs the full cost of source access and LLM-based extraction, regardless of whether the source material has actually changed.

### Target state

The rerun workflow computes a SHA256 hash of the primary source content (README, docs) at the time of initial research. On rerun, the workflow fetches the source, computes the hash, and skips re-extraction if the hash matches the stored value. The stored hash is written to the entry's frontmatter or a sidecar cache file. When the hash differs, the workflow proceeds with full re-extraction and updates the stored hash.

### Measurable signal

Run `--rerun` on an entry whose source has not changed. The agent reports "Source unchanged (hash match) -- skipping re-extraction" and completes in under 10 seconds (vs. 60+ seconds for full re-processing). The entry frontmatter or `./research/.cache/` directory contains SHA256 hashes keyed by entry filename.

---

## Improvement 3: Separate deterministic metadata extraction from LLM-dependent analysis in research-curator

**Source pattern**: "Two-pass extraction pipeline: Pass 1 -- Deterministic AST extraction (no LLM cost): tree-sitter parses code files, walks AST nodes, extracts classes/functions/imports with their source locations, builds a call graph. Pass 2 -- Parallel semantic extraction: Claude subagents process docs, papers, and images in parallel batches." (Technical Architecture section, lines 92-97)
**Local system**: .claude/agents/research-curator.md
**Confidence**: Low
**Impact**: Low
**Backlog**: Deferred -- confidence Low: the research-curator already has a two-phase approach (Phase 1: extract passages from sources; Phase 1b: conditional code analysis; Phase 2: write from extracts). Phase 1 is not purely deterministic -- it uses MCP tools and web search which involve network I/O -- but the separation of "gather data" from "synthesize entry" is architecturally similar to graphify's two-pass model. Whether explicitly labeling these as "deterministic" vs "semantic" would change agent behavior is unclear without testing. The local system already gets the cost-saving benefit of conditional Phase 1b (skip code analysis when docs are sufficient).

### Current state

The research-curator agent (`.claude/agents/research-curator.md`, lines 22-66) runs Phase 1 (extract passages from primary sources), an optional Phase 1b (code analysis triggered by doc-sufficiency check), Phase 2 (write from extracts), Phase 4 (assign confidence), and Phase 5 (verify claims). All phases run in a single agent session. Phase 1 involves both deterministic operations (reading files from shallow clone) and LLM-dependent operations (using MCP search tools, interpreting results). There is no explicit cost boundary separating "free" operations from "LLM-cost" operations.

### Target state

The research-curator agent explicitly separates Phase 1 into two sub-phases: Phase 1a (deterministic -- `Read`, `Glob`, `Grep` on cloned repo, `gh api` metadata calls, no LLM inference) and Phase 1b (semantic -- MCP search, web search, content interpretation). Phase 1a always runs. Phase 1b runs only when Phase 1a extracts are insufficient per the doc-sufficiency check. This makes the cost boundary explicit and enables future optimization (e.g., running Phase 1a in a haiku agent while reserving sonnet/opus for Phase 1b).

### Measurable signal

The research-curator agent file contains explicit Phase 1a and Phase 1b labels in its workflow diagram. Phase 1a includes only deterministic tool calls (Read, Glob, Grep, gh api). Phase 1b includes LLM-dependent tool calls (mcp__Ref, mcp__exa, web search). The agent workflow diagram shows this separation with a decision node between them.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Claim-level provenance tags (EXTRACTED/INFERRED/AMBIGUOUS) | Medium | Existing claim-tracing rule may already prevent untagged inferences. Would need analysis of existing entries to verify whether provenance types are distinguishable in practice. |
| SHA256 content-hash skip for rerun mode | Low | Research-curator re-gathers from remote sources; content hash of local entry does not help determine if remote has changed. Pattern requires a response cache architecture, not a content cache. |
| Explicit deterministic vs. semantic phase separation | Low | Research-curator already has Phase 1 (gather) and Phase 1b (conditional code analysis) separation. Adding explicit labels for deterministic vs. semantic may not change agent behavior. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Knowledge graph as persistent skill context | Requires reimplementing graphify's full extraction pipeline (tree-sitter AST + NetworkX graph + Leiden clustering). This is not extending a local system -- it is replacing codebase navigation with a different product. Already assessed in `2026-03-19-gitnexus-improvements.md` as non-transferable: "Reimplementing the graph pipeline would require replacing, not extending, local systems." |
| PreToolUse hook for graph summary | The hook mechanism is already used locally (`.claude/settings.json` Setup hooks; `task_status_hook.py` PostToolUse). PreToolUse hooks for enriching search with graph context require an indexed knowledge graph to query. Already assessed in `2026-03-19-gitnexus-improvements.md`: "The hook *mechanism* is already used locally; the hook *content* (graph queries) requires [graph] infrastructure." |
| Agent-crawlable wiki (--wiki output with index.md) | The local `research/` directory already has `README.md` as a navigable index with per-category tables linking to individual entries. Each entry is already a standalone `.md` file agents can read. The wiki format (per-community articles with Wikipedia-style structure) is graphify's export format, not a transferable workflow pattern. |
| Multi-platform skill format | Already covered locally via multi-ecosystem frontmatter preservation (`.claude/rules/frontmatter-requirements.md`, "Multi-Ecosystem Frontmatter Preservation" section). The `mcp:` field for OpenCode and the ecosystem registry at `plugins/plugin-creator/scripts/ecosystem_registry.py` implement cross-platform skill targeting. |
| LanguageConfig dataclass pattern | Generic code quality pattern (configuration dataclass to reduce per-variant code duplication). Not a workflow improvement specific to any local system. Applicable to any codebase with multi-variant handling -- too abstract to produce a concrete before/after state in a specific local file. |
