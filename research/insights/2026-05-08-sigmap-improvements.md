# Improvement Proposals: SigMap

**Research entry**: ./research/developer-tools/sigmap.md
**Generated**: 2026-05-08
**Patterns assessed**: 8
**Backlog items created**: 0
**Deferred (low confidence)**: 3
**Skipped (already covered or tracked)**: 5

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Groundedness scoring as a programmatic verification gate (`sigmap judge --response --context`) | Low | The `verify` skill (.claude/skills/verify/SKILL.md) is a self-assessment checklist with rationalization-prevention prompts, not a programmatic scorer. SigMap's `judge` command scores an answer's groundedness against retrieved context numerically, returning a quantitative score. The gap is real — verify produces qualitative PASS/FAIL evidence, not a groundedness number. However, implementing a scorer requires building (a) a context-extraction step that captures what the agent saw, (b) a response-extraction step that captures what the agent claimed, and (c) a scoring engine that compares the two. This is a new subsystem rather than an extension of `verify`. To raise confidence: prototype a minimal `verify --score` command that reads the last agent transcript, extracts cited file paths, and counts how many response claims are traceable to those paths; measure whether the score correlates with downstream bug rates. |
| Session memory with intent-aware file-rank boost (4-hour TTL, +0.2 boost for top-5 from previous query) | Low | No local system tracks per-query session memory of which files were retrieved. The `context-gathering` agent (.claude/agents/context-gathering.md) writes a single Context Manifest into the task file but does not boost or re-rank files based on prior queries within the same session. The DH harness (`~/.dh/projects/{slug}/`) caches per-project artifacts but does not implement query-session memory with TTL-based decay. The pattern requires a new ranking engine to begin with — there is no existing TF-IDF or scored retrieval engine in this repo to extend. ccc (cocoindex-code) does semantic search but does not expose a re-rankable score that session memory could boost. To raise confidence: identify a concrete workflow where the same agent issues N>1 retrieval queries within a session and measure whether intent-aware boosts would change which files were read. |
| Hub suppression for high-fanout files in code search ranking (suppress utils/, helpers/, common/, index, files used by >20% of codebase) | Low | This pattern requires an underlying ranking engine to suppress within. ccc (.claude/skills/ccc/SKILL.md) wraps cocoindex-code's semantic search and does not surface or weight individual file scores in a way that supports score-modifying boosts or suppressions. The Glob/Grep tools used by context-gathering return matches without ranking. The gap (high-fanout utility files dominating naive ranking) is well-known but not actionable here because there is no local system whose ranking the agent controls. To raise confidence: instrument ccc query results across N real searches and measure how often top-5 results contain `utils/`, `helpers/`, or `common/` paths that the agent ultimately ignored. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Layered context injection (always-injected signature baseline + on-demand MCP fetches) | Already covered architecturally by Claude Code's runtime: CLAUDE.md auto-loads as baseline context, and skills load on-demand via Skill tool. The repo's `context-gathering` agent writes a Context Manifest to task files (always-injected per task), and ccc/MCP tools cover on-demand fetches. Adopting SigMap's specific layering would require generating signature manifests, which requires building signature extraction first — that is a utilization proposal (use SigMap), not a local-system extension. |
| Deterministic ranking over embeddings (TF-IDF reproducibility) | The `ccc` skill (.claude/skills/ccc/SKILL.md) wraps cocoindex-code's semantic search (embedding-based). Replacing this with TF-IDF is an architectural alternative that would require building a new search engine, not extending ccc. SigMap's ranking is a property of an external tool — adopting it is a utilization decision (potentially the subject of a sigmap-utilization.md file), not a local-system improvement. |
| Impact analysis before changes (`sigmap plan` — rank files by change likelihood, compute impact radius) | Already covered by existing impact-radius infrastructure and codegraphcontext deferred proposals (./research/insights/2026-04-08-codegraphcontext-improvements.md). The repo has impact-radius coverage in plan-validator and impact-radius-findings backlog entries (e.g., `p1-impact-radius-findings-must-become-plan-tasks-or-documented-.md`). The CodeGraphContext insight already documented that adopting graph-based impact analysis requires replacing rather than extending local systems and was deferred. The same conclusion applies to SigMap's `plan` command. |
| Incremental signature caching by mtime | Requires the existence of a signature-extraction subsystem to cache. No such subsystem exists locally, and ccc handles its own indexing internally (`ccc index` / `ccc search --refresh`). Adopting mtime-keyed caching is a utilization proposal (use SigMap), not a local-system extension. |
| Multi-adapter context output (single run generates CLAUDE.md, .cursorrules, .windsurfrules, AGENTS.md, etc.) | Out of scope. This repository is a Claude Code Marketplace Plugin — the target ecosystem is Claude Code (with secondary OpenCode support via the `mcp:` frontmatter convention documented in .claude/rules/frontmatter-requirements.md). Generating output for Cursor, Windsurf, and Copilot is a cross-tool publishing concern, not a gap in any local system. The repo's `external-pattern-integrator` skill already covers the inverse direction (integrating external patterns into local skills). |

---

## Notes on Utilization vs Improvement

The bulk of SigMap's actionable value to this repo lies in **utilization** (using SigMap as an external context-generation tool), not in patterns that extend existing local systems. The "Integration Opportunities" section of the research entry — "Agent-generated SAM task plans could use `sigmap plan`", "Skill context pre-generation via `sigmap`", "MCP server for Claude Code" — are all utilization proposals to be assessed by `@research-utilization-assessor` in a separate output file (`2026-05-08-sigmap-utilization.md`), not local-system improvements.

Three patterns in the entry's "Patterns Worth Adopting" section (groundedness scoring, session memory with intent boost, hub suppression) describe genuine capability gaps in local systems but require building new ranking/scoring infrastructure rather than extending existing files. They are recorded as deferred above with concrete confidence-raising experiments. The remaining patterns are either already covered, already deferred in prior insights (CodeGraphContext), or are utilization concerns.
