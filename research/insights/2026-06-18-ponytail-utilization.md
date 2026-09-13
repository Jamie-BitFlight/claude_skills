---
title: "Utilization Proposals: Ponytail"
---

<!-- removed-skill-citations -->
> **Removed-skill citations:** `swarm-patterns` were removed in PR #3422 (commit `4e1e73bd6`, 2026-09-06) and **retired in favour of** `plugins/agent-orchestration/skills/parallel-work/`, with what delegation guidance survives in `plugins/agent-orchestration/skills/delegate/`. "Retired in favour of" is that PR's own wording, at `plugins/agent-orchestration/skills/delegate/references/harness-notes/claude-code.md` — not a capability-preserving consolidation: `parallel-work/SKILL.md` § "Persistent teams" argues against the long-lived-team model outright, and `TeamCreate` survives in the tree only as a negation. The removal replaced roughly 2080 lines with roughly 330; the line numbers, pattern numbers, and named sections cited below have no surviving equivalent, and grep over `plugins/` and `.claude/` returns zero hits for them (`Handling Crashed Teammates`, `permission_request`, and the rest). Any "already covered" conclusion resting on them is therefore **refuted by the current tree, not merely unverified against it**.

## Utilization 1: research-insight-extractor → Ponytail ruleset

**Research entry**: ./research/agent-frameworks/ponytail.md
**Caller**: ./.claude/agents/research-insight-extractor.md
**Integration mechanism**: Instruction injection (embed AGENTS.md ruleset into agent prompt)
**Replaces or adds**: Adds — enables the agent to generate minimal, non-speculative improvement proposals
**Setup cost**: Low (copy 26-line ruleset into agent prompt)
**Integration surface**: `AGENTS.md` (26-line compact ruleset from ponytail repository)

### Why this caller

The research-insight-extractor agent generates improvement proposals by reading research entries and producing "measurable improvement proposals" (line 10, agent file). Currently, the agent has no instruction enforcing minimalism — it could propose elaborate new features, frameworks, or architectural changes without checking YAGNI or whether stdlib/native features already solve the problem. The ponytail ruleset provides a reflex-level decision ladder (six rungs: YAGNI → stdlib → native → installed deps → one-liner → minimal code) that the agent can apply at proposal-generation time to filter speculative patterns and recommend only the simplest, most necessary improvements. This directly strengthens the agent's output quality by reducing over-engineered proposals.

**Source**:
- Agent file lines 7-9: "produces concrete, measurable improvement proposals"
- Research entry lines 35-46: "The Decision Ladder" with six rungs, applied as reflex not research
- Research entry lines 15-19: "tends toward over-engineering" — exact problem the agent could introduce

### Integration sketch

Inject the ponytail AGENTS.md ruleset into the agent's system prompt before the workflow section:

```markdown
---
name: research-insight-extractor
description: [unchanged]
model: opus
---

# Research Insight Extractor

## Simplicity Ladder (from Ponytail)

Before proposing any improvement, follow this six-rung ladder; stop at the first rung that holds:

1. **Does this improvement need to exist?** If speculative or unnecessary, skip it and note why in one line.
2. **Does the codebase already have this pattern?** Confirm absence before proposing.
3. **Is this a native platform feature?** Prefer database constraints over app-layer checks, project configuration over custom code.
4. **Is this an installed dependency?** Use it. Never propose importing a new dependency for what a few lines can do.
5. **Can it be one line?** If yes, propose the one-liner and move on.
6. **Only then**: The minimum code that actually works.

This is a reflex, not a research project. When in doubt between two rungs that work, take the higher one and move on.

[Rest of agent content unchanged]
```

The agent follows the ladder when assessing gaps (research-insight-extractor.md line 34: "assess the gap"). Each proposal filters through the ladder before being written.

---

## Utilization 2: design-anti-patterns skill → Ponytail companion skill (simplicity-review)

**Research entry**: ./research/agent-frameworks/ponytail.md
**Caller**: ./.claude/skills/design-anti-patterns/SKILL.md
**Integration mechanism**: Skill activation (call `/ponytail-review` from within design-anti-patterns workflow)
**Replaces or adds**: Adds — extends design-anti-patterns beyond banning bad patterns to also detecting over-engineering in generated UI code
**Setup cost**: Medium (reference ponytail-review skill, integrate into pre-flight check workflow)
**Integration surface**: `/ponytail-review` skill from ponytail plugin

### Why this caller

The design-anti-patterns skill enforces UI design constraints through a "Pre-Flight Check" (lines 12-19) that lists styling decisions and cross-references them against banned patterns. This is a local instantiation of constraint enforcement. The ponytail-review companion skill performs diff-level over-engineering detection — it scans generated code for unnecessary complexity and returns a delete-list (research entry lines 60-61). Integrating ponytail-review into the design-anti-patterns workflow would catch over-engineered component structure (excessive nesting, premature abstraction, redundant wrapper divs) in addition to style bans. The two skills are complementary: design-anti-patterns bans specific visual patterns; ponytail-review identifies structural complexity that could be deleted.

**Source**:
- design-anti-patterns SKILL.md lines 12-19: "Pre-Flight Check" structure
- research entry lines 60-61: "ponytail-review: Analyzes the current diff for over-engineering and returns a delete-list"
- research entry lines 48-52: Three intensity levels (lite/full/ultra) that could apply to design review intensity

### Integration sketch

Add ponytail-review as a post-generation step in design-anti-patterns workflow:

```markdown
## Pre-Flight Check + Simplicity Review

After running the pre-flight check against banned patterns:

1. List all styling decisions and cross-reference against Uncodixfy rules (existing step)
2. Generate the component code
3. **NEW STEP**: Run `/ponytail-review` on the generated code:
   - Call the ponytail-review skill with the component code
   - Review findings for over-engineered structure (excess nesting, premature abstraction)
   - Accept the delete-list suggestions
4. Apply deletions and verify the result is still functional

Example command sequence:
\`\`\`
Design component HTML/CSS
Save to temp file
Call: Skill(skill: "ponytail-review", args: "review ./temp-component.html")
Review output: delete-list
Edit component to remove flagged complexity
Verify component still meets requirements
\`\`\`

This ensures generated UI is both visually honest (Uncodixfy) and structurally minimal (ponytail).
```

---

## Skipped Systems

| Local System | Reason skipped |
|---|---|
| .claude/skills/swarm-patterns/SKILL.md | Conceptual documentation only (teaches patterns, does not generate code). Ponytail targets code generation; swarm-patterns documents orchestration templates. No integration surface. |
| .claude/agents/research-curator.md | Research coordination agent. Ponytail applies when generating implementations; research-curator researches and reports. Different lifecycle phase. Already has constraint (high-quality, quoted sources). No simplicity enforcement gap. |
| .claude/skills/cove-prompt-design/SKILL.md | Teaches CoVe (Clear + Verification) methodology for prompt design. Not a code generator. Ponytail enforces simplicity in code, not prompt clarity. Non-overlapping concern. |

---

## Implementation Notes

1. **research-insight-extractor**: Low-effort integration. Copy 26-line ruleset into agent frontmatter, no workflow changes needed. The agent already assesses gaps (line 34) — the ladder becomes a filter applied at that step.

2. **design-anti-patterns**: Requires adding one skill call to the workflow. Moderate effort. The skill already has a structured pre-flight check; adding `/ponytail-review` as a post-generation gate fits naturally into the existing constraint-checking pattern.

3. **Both integrations preserve existing behavior** — they add simplicity constraints without breaking current functionality. Neither requires API changes or removes existing rules.

---

## References

- **Research entry**: ./research/agent-frameworks/ponytail.md (v4.7.0, released 2026-06-17)
- **Ponytail repository**: <https://github.com/DietrichGebert/ponytail>
- **AGENTS.md source**: <https://github.com/DietrichGebert/ponytail/blob/main/AGENTS.md> (accessed via research entry)
- **ponytail-review skill**: documented in research entry lines 60-61, skill definition at ponytail plugin in repo
