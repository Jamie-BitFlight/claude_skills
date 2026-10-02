# Improvement Proposals: GitHub Agentic Workflows (gh-aw)

**Research entry**: ./research/developer-tools/gh-aw.md
**Generated**: 2026-10-02
**Patterns assessed**: 4
**Backlog items created**: 0
**Deferred (low confidence)**: 2
**Skipped (already covered or tracked)**: 2

No proposal reached high confidence, so this file holds no numbered improvements. The entry's
Relevance section states each change as "could inform" or "none" and names no concrete mechanism
whose absence can be observed in a local file.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| MCP safe-inputs validation, tool mapping, server lifecycle (Relevance > Integration Opportunities; Key Features > MCP Server Integration: "Safe-inputs framework validates tool inputs before agent use") | low | The entry describes safe-inputs in one sentence and does not say what is validated, against what schema, or where the check runs. Its Integration Opportunities line contradicts itself: it says "nothing" matches, then cites `git grep --full-name -il "MCP" ...` returning 572 matches. `plugins/fastmcp-creator/skills/fastmcp-creator/SKILL.md` covers per-tool auth (`require_scopes`, line 94). FastMCP derives input schemas from type annotations, so a gap can't be stated without the gh-aw safe-inputs specification. To raise confidence, fetch the gh-aw safe-inputs docs and list the checks that FastMCP's annotation-derived schema validation lacks. |
| Safe-outputs: the agent emits structured JSON and a separately permissioned job validates it against declared permissions before writing (Key Features > Security & Sandboxing; Technical Architecture > Safe-Outputs Framework) | low | The Relevance section does not name this pattern. I inferred it from Key Features myself, so it is not grounded in a Relevance passage. The nearest local analog is the dh backlog MCP server (`plugins/development-harness/backlog_core/`), the only path agents use to write to the backlog. I did not examine whether it splits proposal from validated execution. To raise confidence, have the research entry name a concrete local target, and read the backlog write path to check whether a validate-then-execute split is absent. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Multi-engine registry with validation before compile (Relevance > Applications, mapped to `plugins/agent-orchestration/`) | Already covered. `scripts/generate_harness_compatibility.py` keeps a `HARNESSES` registry and rejects unknown harness and plugin names with an explicit error (lines 124-131). `plugins/agent-orchestration/README.md` line 14 sets up per-harness notes under `delegate/references/harness-notes/`. The entry's "Change" field ("could inform how this repo scales multi-engine support") gives no target state beyond that. |
| Markdown + YAML frontmatter declarative definitions (Relevance > Applications, mapped to `.claude/agents/research-curator.md`) | The entry's own Change field says "none". Local agents and skills already use YAML frontmatter, and skilllint validates it on commit. |

---

## Research Entry Defects Observed (for the research-curator, not backlog proposals)

- Limitations & Caveats says that versions ">= 0.83.3 and < 0.85.4" were retired and that users
  should "upgrade to v0.40.1 or later". v0.40.1 is lower than the affected range, so the claim
  contradicts itself. One of the version numbers is wrong.
- Integration Opportunities says "nothing" matches and then cites 572 `git grep` matches.
- The Cross-References link `../../agent-frameworks/agent-orchestration.md` resolves outside
  `research/`. Neither `research/agent-frameworks/agent-orchestration.md` nor a top-level
  `agent-frameworks/` exists.
