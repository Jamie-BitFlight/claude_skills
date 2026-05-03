# Improvement Proposals: Huashu Design

**Research entry**: ./research/ai-design-tools/huashu-design.md
**Generated**: 2026-05-03
**Patterns assessed**: 7
**Backlog items created**: 2 (issues: #2102, #2103)
**Deferred (low confidence)**: 3
**Skipped (already covered or out of scope)**: 2

---

## Improvement 1: Add proactive WebSearch trigger when prompts mention specific named products/technologies/versions

**Source pattern**: "Fact Verification First (Principle #0)" — README §Fact Verification First (research entry lines 110–112): "when the task mentions a specific product / technology / event (e.g., 'DJI Pocket 4', 'Nano Banana Pro', 'Gemini 3 Pro'), the first action **must** be a `WebSearch` to confirm existence, release status, current version, and specs. No claims from training-corpus memory."
**Local system**: ./.claude/CLAUDE.md (Critical Constraints), ./.claude/skills/fact-check/SKILL.md (reactive verifier)
**Confidence**: High
**Impact**: High
**Backlog**: #2102 created

### Current state

`./.claude/CLAUDE.md` Critical Constraints fires verification only on hedging language emitted by the agent — `"likely"`, `"probably"`, `"I think"` — not on named entities present in the user prompt. The reactive `./.claude/skills/fact-check/SKILL.md` runs after content already exists and requires an `UNVERIFIED` tag or backlog entry to fire. Grep of `./.claude/` for `Fact Verification First`, `WebSearch first`, `named product`, `Principle #0`, or `specific product.*search` returns zero matches. An agent receiving "build a demo using DJI Pocket 4" or "compare against Gemini 3 Pro" can proceed using training-corpus recall and ship work grounded in nonexistent or outdated specs.

### Target state

`./.claude/rules/fact-verification-first.md` exists and is referenced from `./.claude/CLAUDE.md`. The rule defines named-entity trigger patterns (specific product names, version strings like "v1.2.3", release event terms) and mandates that the orchestrator's first tool call be `WebSearch` or `mcp__Ref__ref_search_documentation` before any planning, design, or code-generation tool. A trigger table in the rule lists at least three example trigger phrases and the required verification action.

### Measurable signal

`grep -l "Fact Verification First\|named product\|Principle #0" ./.claude/CLAUDE.md ./.claude/rules/*.md` returns at least one path. The matched file contains a trigger table with at least three example named-entity patterns and a mandatory `WebSearch` action. A test prompt of the form "Make a demo for DJI Pocket 4" causes the orchestrator to run `WebSearch` before any other tool call.

---

## Improvement 2: Add vague-brief fallback to research-curator and skill-research-process — N differentiated alternatives in parallel for user selection

**Source pattern**: "Design Direction Advisor (Fallback Mode)" — SKILL.md §Design Direction Advisor (research entry lines 60–66): "When the brief is too vague to execute. Fallback mode does NOT proceed on generic intuition. Recommends 3 differentiated directions from '5 schools × 20 design philosophies' … Generates 3 visual demos in parallel."
**Local system**: ./.claude/skills/research-curator/SKILL.md, ./.claude/skills/skill-research-process/SKILL.md
**Confidence**: High
**Impact**: High
**Backlog**: #2103 created

### Current state

`./.claude/skills/research-curator/SKILL.md` Mode Routing flowchart branches on flag presence (`--batch`, `--rerun`, `--validate`) and otherwise enters Default Mode with the URL. There is no branch that detects underspecification — homepage URL with no resource identifier, skill name that is a verb phrase rather than a noun, no version or identifier in the prompt. `./.claude/skills/skill-research-process/SKILL.md` Stage 1 launches a single categorization agent without checking whether the input is well-specified. Grep of `./.claude/skills/` for `vague brief`, `fallback mode`, `parallel alternatives`, or `differentiated direction` returns zero matches. Ambiguous prompts produce a single best-guess output; the user discovers misalignment after the work is done, when iteration cost is maximal.

### Target state

`./.claude/skills/research-curator/SKILL.md` Mode Routing flowchart contains a Vague Brief Detector node placed before Default Mode entry. The detector evaluates explicit conditions (URL is a homepage; resource name absent; skill request lacks a noun subject). When ANY condition matches, the skill enters Fallback mode and spawns N parallel `@research-curator` (or `@general-purpose`) agents, each scoped to a distinct interpretation. The orchestrator collects N short summaries, presents them with labeled differentiation axes, and waits for user selection before continuing. `./.claude/skills/skill-research-process/SKILL.md` Stage 1 follows the same pattern.

### Measurable signal

`./.claude/skills/research-curator/SKILL.md` contains a mermaid node labeled "Vague Brief Detector" with at least three explicit branch conditions and one "Fallback — spawn N parallel alternative agents" branch. Running the skill with the input `"research AI tools"` (no URL) causes the orchestrator to spawn N parallel agents and present N differentiated summaries before any entry is written. Trigger conditions are stated explicitly enough that agents evaluate them without subjective judgement.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Core Asset Protocol — 5-step mandatory data-gathering checklist with priority ranking + frozen `brand-spec.md` artifact (research entry lines 76–96) | Medium | Pattern overlaps with `@research-curator` agent's existing Doc-Sufficiency Check (Q1/Q2/Q3) and tier-ordered Phase 1b code analysis. To raise confidence: read all three reference files under `./.claude/skills/research-curator/references/` to confirm whether priority-ranked asset gathering and a frozen-spec artifact are absent in spirit, or merely absent in name. |
| Junior Designer Workflow — single-batch question delivery + assumption/placeholder commits + show-early-iterate-cadence (research entry lines 100–108) | Medium | Pattern is present in spirit across `cove-prompt-design` and `complete-implementation` (assumption-marking, early review), but the specific mechanism of "send the full question set in one batch, wait for all answers before moving" is absent. To raise confidence: read both skills end-to-end and confirm whether any current rule mandates batched questions vs. interactive turn-by-turn elicitation. |
| A/B-tested protocol effectiveness measurement — "v2 reduced stability variance by 5×" with 6-agent runs per arm (research entry line 96) | Low | Research entry states the result but does not describe the measurement protocol (what was measured, how variance was computed, what counted as a stable outcome). Local `agentskill-kaizen` plugin has improvement generators but no formal A/B harness. To raise confidence: original Huashu A/B methodology would need to be sourced from a follow-up reference before a measurable target state can be defined for this repo. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Anti-AI-Slop Rules — explicit avoid/use lists for visual aesthetics (research entry lines 68–74) | Already covered by `./.claude/skills/design-anti-patterns/SKILL.md` ("Absolute Prohibitions" + "Normal Standards" tables) which enforces banned patterns from the Uncodixfy methodology. Adding Huashu's specific items (purple gradients, Inter-as-display, SVG humans) would be additive data-points, not a missing capability. |
| Single-file self-contained deliverable (no external dependencies, runs from `file://`) (research entry line 46) | Out of scope — this repo's primary artifact is skills/agents/markdown, not standalone HTML deliverables. The `file://` constraint that motivates the Huashu pattern does not apply. |
