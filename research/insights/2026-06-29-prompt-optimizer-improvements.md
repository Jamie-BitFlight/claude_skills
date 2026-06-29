# Improvement Proposals: Prompt Optimizer

**Research entry**: ./research/prompt-engineering/prompt-optimizer.md
**Generated**: 2026-06-29
**Patterns assessed**: 4
**Backlog items created**: 0 (backend offline — see note below)
**Deferred (low confidence)**: 1
**Skipped (already covered or tracked)**: 2

> **Backend note**: At generation time the backlog MCP backend was offline (GitHub
> unavailable, `GITHUB_TOKEN` not set/invalid — serving stale cache of 8 open / 279 total).
> `backlog_add` also requires a `gate_token` supplied only by the `/dh:work-backlog-item` or
> `/dh:create-backlog-item` skill, which is not loadable from this agent context. The single
> high-confidence + actionable proposal below is therefore recorded as **READY TO BACKLOG**
> with the exact title/description/priority/source to file once the backend is reachable and
> the gate token is available. No item was created to avoid silent failure against a stale cache.

---

## Improvement 1: Add a quantified before/after evaluation step to subagent-refactoring methodology

**Source pattern**: Relevance §4 "Evaluation-Driven Development" — "run Prompt Optimizer's structured compare evaluation to quantify the improvement (e.g., 'Before: 60% accuracy on edge cases, After: 85%')"; and §2 "Multi-Model Evaluation" / Key Features §2 "Analysis & Evaluation Pipeline" (analysis → evaluation → compare with structured JSON scoring).
**Local system**: `plugins/plugin-creator/skills/subagent-refactoring-methodology/SKILL.md`
**Confidence**: High
**Impact**: Medium
**Backlog**: READY TO BACKLOG — backend offline at generation (see note); priority P1 per High-confidence × Medium-impact matrix

### Current state

`subagent-refactoring-methodology/SKILL.md` terminates refactoring at a **subjective self-check**.
The "Validation checklist" (lines 150–161) and "Self-Validation Before Delivery" (lines 162–168)
ask the author to confirm structural properties ("Role defined in one sentence", "No vague
qualifiers remain", "Did I remove, not add, unnecessary complexity?"). There is no step that
captures the original prompt's behavior on representative inputs (a baseline), runs the refactored
prompt on the same inputs, and records a quantified before/after delta. The methodology produces a
binary "looks better" verdict with no measurable signal that the refactor actually improved agent
behavior — and no artifact to put in the commit message. This is the exact "AI cannot reliably
self-evaluate" failure mode named in `plugins/plugin-creator/skills/arl/SKILL.md` Universal
Principle 3.

### Target state

`subagent-refactoring-methodology/SKILL.md` gains an evaluation step **between** the "Refactored
agent file" output (line 132) and the validation checklist: capture a baseline run of the original
prompt against a small fixed set of representative inputs drawn from the agent's scope, run the
refactored prompt against the same inputs, and emit a structured comparison block (per-input
result + an explicit verdict of IMPROVED / NO-CHANGE / REGRESSED). The methodology's
"Output Format Specification" lists a fourth artifact: a comparison record with the baseline inputs,
both outputs, and the verdict, so the refactor's improvement is observable rather than asserted.
This is the internal-pattern adoption of Prompt Optimizer's analysis → evaluate → compare pipeline;
it deliberately does NOT require the external Prompt Optimizer tool (that external-dependency
variant is already proposed in `research/insights/2026-06-29-prompt-optimizer-utilization.md`
Utilization 1).

### Measurable signal

Read `plugins/plugin-creator/skills/subagent-refactoring-methodology/SKILL.md`: the
"Output Format Specification" section enumerates a comparison/evaluation artifact (a 4th deliverable)
in addition to the analysis report, refactored file, and validation checklist; and the body
contains a step that names "baseline" capture against representative inputs before the validation
checklist. Verify with: `grep -n -i "baseline\|before/after\|comparison record\|REGRESSED" plugins/plugin-creator/skills/subagent-refactoring-methodology/SKILL.md` returns at least one match in the methodology body (currently returns none).

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Source binding / provenance tracking for prompt assets (Relevance §3; Key Features §5 — "Track prompt origins (manual, template, import) without losing context") | Low | The gap is inferred, not observed. Local skills already carry version history via git, which substantially covers the "version history" half of the pattern. There is no concrete observable target field for "source binding" in a SKILL.md, and no current failure is attributable to its absence. To raise confidence, a specific scenario where an agent makes a wrong decision for lack of instruction provenance would need to be identified. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Evaluation-driven rewrite — "Automatically refine prompts based on evaluation feedback" (Key Features §6) | Already covered. The autonomous refine-on-feedback loop is the explicit research domain of `plugins/plugin-creator/skills/arl/SKILL.md` — see gates R5 (Purpose Anchor), R7 (Convergence Tracking), and the 10-gate table (lines 113–125). Adopting Prompt Optimizer's loop adds nothing the ARL gate model does not already formalize for this repo. |
| Multi-platform deployment / image generation / MCP server / Docker (Key Features §3–8) | Architecturally incompatible with internal pattern adoption. These are deployment surfaces of an external TypeScript product, not patterns expressible as an observable before/after state in a local skill, agent, or workflow file. The one viable external-dependency angle (MCP server for compare evaluation) is already captured in `research/insights/2026-06-29-prompt-optimizer-utilization.md` Utilization 1. |
