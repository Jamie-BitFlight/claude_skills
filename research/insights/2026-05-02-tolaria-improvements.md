# Improvement Proposals: Tolaria (ai-design-tools entry)

**Research entry**: ./research/ai-design-tools/tolaria.md
**Generated**: 2026-05-02
**Patterns assessed**: 4
**Backlog items created**: 0 (all actionable gaps already tracked from earlier entry)
**Deferred (low confidence)**: 1
**Skipped (already covered or tracked)**: 4

> Note: A second Tolaria research entry exists at `./research/developer-tools/tolaria.md` (created 2026-04-26) with a more detailed "Patterns Worth Adopting" section. The 4 actionable improvements from that entry were captured in `./research/insights/2026-04-26-tolaria-improvements.md` and produced backlog items #1949, #1951, #1952, #1953. The current `ai-design-tools/tolaria.md` entry has only a "Relevance to Claude Code Development" section — its 4 sub-items are higher-level framings of patterns already extracted, plus one item about AGENTS.md that is already a foundational repo design choice.

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Structured Context for AI Agents — YAML frontmatter + WikiLinks + MCP tooling for vault legibility | Fully covered by existing items: MCP exposure of `./research/` is tracked under #1952 (research-curator MCP server with 6+ tools); cross-reference graph integrity (the wikilinks/backlinks aspect) is tracked under #1953 (automatic backlink detection in research-cross-referencer). YAML frontmatter is already required and validated by `validate_research.py`. No additional gap remains. |
| Plain-Text Knowledge Base Compatibility — markdown + git for diff/version-control friendliness | Already a foundational design choice across the entire repo: skills, agents, research entries, backlog items, SAM plans are all plain markdown / YAML stored in git. No actionable gap. |
| Offline-First, Portable Knowledge Graph — no cloud dependency, works air-gapped | Already a foundational design choice: research entries, backlog cache, SAM plans, and skill definitions are all local files. The backlog system's GitHub Issues source-of-truth is the only cloud dependency, and that is already mitigated by the `~/.dh/projects/{slug}/backlog/` cache that allows offline reads. No actionable gap. |
| Convention-Based Agent Guidance — single AGENTS.md drives Claude Code, Codex, Gemini uniformly | Already implemented: `/home/user/claude_skills/AGENTS.md` (292 lines) exists at repo root and serves as the multi-tool guide. Tolaria's promise is that a single file unifies guidance across multiple AI CLIs — this repo already follows that convention. |

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| AGENTS.md ↔ CLAUDE.md drift detection | Low | Repo has both `AGENTS.md` (292 lines) and `.claude/CLAUDE.md` (571 lines) covering overlapping topics, but the research entry does not call out drift detection between two parallel agent-instruction files as an explicit pattern — Tolaria's design has only one such file (AGENTS.md). Whether divergence between AGENTS.md and CLAUDE.md is actually causing observable problems in this repo would require comparison of section coverage, not just line counts. The `doc-drift-auditor` agent exists but does not specifically target this pair. Raising confidence would require reading both files in full and identifying concrete contradictory guidance — not warranted from this research entry alone. |

---

## Notes for Future Extraction

When Tolaria reaches v1.0 or publishes a documented MCP tool catalog (currently noted as a limitation: "MCP Server Scope Not Fully Documented"), re-run extraction against the updated entry. The specific MCP tool surface — tool names, parameters, transports — would inform the design of the research-curator MCP server tracked in #1952 and may surface additional gaps not visible in the current 0.1.0 alpha documentation.
