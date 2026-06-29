---
title: "Improvement Proposals: Research Mode"
---

## Improvement 1: Add source lookup cascade with cost tiers to research-curator agent

**Source pattern**: "The plugin enforces an ordered cascade to minimize token cost while prioritizing reliability: Level 1 — Local files (zero cost) [...] Level 2 — WebSearch snippets (low cost) [...] Level 3 — WebFetch for direct quotes (high cost, used sparingly) [...] Level 4 — Scholar Gateway (for academic claims)" (Section: Source Lookup Cascade, lines 56-68)
**Local system**: .claude/agents/research-curator.md
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred -- confidence medium: the research-curator agent lists available tools in its `<research_tools>` section (lines 73-113) but does not prescribe an ordering or cost hierarchy. However, the agent's Phase 1 workflow already implicitly prefers local reads (shallow clone first, then web sources). The gap exists in that no explicit cascade ordering or cost tier labels are documented, but the practical impact is uncertain -- the agent may already follow a reasonable order due to the workflow structure (shallow clone precedes web lookups in the flowchart). Verifying whether agents actually follow the implicit ordering vs. using tools in arbitrary order would require observing multiple research sessions.

### Current state

The research-curator agent at `.claude/agents/research-curator.md` lists tools in a `<research_tools>` section (lines 73-113) without ordering them by cost or reliability. The tools are grouped by type (documentation sites, code/API research, repository clone, GitHub metadata, fallback) but no cascade or priority ordering is enforced. There are no limits on how many WebSearch or WebFetch calls the agent makes per research question -- the agent decides freely.

### Target state

The `<research_tools>` section in `.claude/agents/research-curator.md` includes an explicit source lookup cascade with four cost tiers (local files first, WebSearch snippets second, WebFetch full pages third, Scholar/specialized fourth). Each tier has a stated condition for escalating to the next tier. Hard limits are defined: maximum N WebSearch calls and maximum M WebFetch calls per entry, with instructions to summarize findings and note what remains unverified when limits are reached.

### Measurable signal

The `<research_tools>` section in `.claude/agents/research-curator.md` contains subsections labeled "Level 1", "Level 2", "Level 3", "Level 4" (or equivalent cascade ordering) with explicit escalation conditions. A Grep for "maximum.*WebSearch" or "maximum.*WebFetch" in the agent file returns at least one match.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Source lookup cascade with cost tiers | medium | The research-curator workflow implicitly orders local reads before web lookups via its flowchart structure. Confirming the gap requires observing whether agents deviate from this implicit order in practice. The research entry describes the mechanism clearly but the local system requires interpretation to confirm absence vs. implicit coverage. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Competitive Intelligence (citation discipline for GTM work) | Too abstract -- describes a use case domain, not a concrete mechanism. No observable file-level gap to address. |
| Skill and Plugin Documentation (quote-based extraction for accuracy) | Already covered in `.claude/agents/research-curator.md` Phase 1 extractive methodology (lines 119-248) and Fidelity Rules (lines 253-301). The research-curator already requires extract-before-write and verbatim quote grounding. |
| Multi-Agent Orchestration (research constraints adoptable locally) | Already covered -- the `/fact-check` skill (`.claude/skills/fact-check/SKILL.md`) and the hallucination-triggers reference (`plugins/agent-orchestration/skills/agent-orchestration/hallucination-triggers.md`) provide constraint mechanisms agents can invoke within workflows. The research-curator itself is already invocable as a subtask via `@research-curator` agent delegation. |
| Governance and Compliance (citation trails and uncertainty) | Already covered in `.claude/agents/research-curator.md` Fidelity Rule 3 (distinguish absence from nonexistence, lines 276-284) and Rule 4 (state confidence explicitly, lines 286-299). Also covered in `.claude/rules/skill-documentation-verification.md` (uncertainty markers) and `.claude/CLAUDE.md` citation requirements section. |
