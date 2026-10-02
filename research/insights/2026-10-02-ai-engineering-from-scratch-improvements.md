# Improvement Proposals: AI Engineering from Scratch

**Research entry**: ./research/ai-research-tools/ai-engineering-from-scratch.md
**Generated**: 2026-10-02
**Patterns assessed**: 9
**Backlog items created**: 0
**Deferred (low confidence)**: 0
**Skipped (already covered or tracked)**: 9

---

No pattern in this entry produced an actionable gap. The resource is a learning curriculum, not a
tool, and every item under "Relevance to Claude Code Development" proposes enriching a local system
with "curriculum-level" material without naming a concrete mechanism the local system lacks. Two
items state `Change: none` themselves. The two concrete mechanisms found outside that section
(evidence capture per lesson run, release evals for skills) already exist locally — see the
Skipped Patterns table for the files and searches.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| (none) | — | — |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Agent Skills path enriching agent creation (Applications, `plugins/plugin-creator/`) | Too abstract: "integration could enrich agent creation guidance with curriculum-level foundational material" names no mechanism. Local file `plugins/plugin-creator/skills/agent-creator/SKILL.md` exists; no observable target state can be derived from the entry. |
| Agent Skills path "release evals" sub-topic (Applications, curriculum route list) | Already covered: `plugins/plugin-creator/skills/skill-creator/scripts/run_eval.py`, `plugins/plugin-creator/skills/skill-creator/references/evaluation-and-optimization.md`, and `plugins/plugin-creator/skills/skill-creator/assets/eval_review.html` implement skill evals (`git grep -il "evals\?/\|evals.json\|eval set" -- plugins/plugin-creator/skills/skill-creator/` -> 5 files). The entry gives no detail of the curriculum's eval mechanism to compare against. |
| MCP Phase 13 / 17-lesson path linked from `docs/MCP-INDEX.md` (Applications) | Not a concrete problem: adding an external learning link closes no failure mode. `docs/MCP-INDEX.md` already indexes an internal 30-minute MCP tutorial (line 47). The 17-lesson figure is also part of the entry's Relevance section, which its own `confidence_map` rates medium. |
| Prompt engineering via Phase 11 (Applications) | Entry states `Change: none`. |
| Layered Skill Learning Path vs SAM pipeline (Patterns Worth Adopting) | Entry states `Change: none` — "already comparable to harness's phase-based progression model". |
| AI Evaluation & Reliability Engineer path → `plugins/development-harness/docs/impact-analysis-principals.md` (Integration Opportunities) | Too abstract: "enrich evaluation frameworks with curriculum-level structured reliability engineering methodology" names no mechanism. The local doc already covers baseline-vs-candidate comparison (line 41), reliability (line 53), and continuous evaluation with cited eval-lifecycle sources (line 180). |
| Swarm coordination / inter-agent communication → `plugins/agent-orchestration/skills/parallel-work/SKILL.md` (Integration Opportunities) | Too abstract and conflicts with a deliberate local decision: `parallel-work/SKILL.md` "Persistent teams" section (lines 42-44) states teams with messaging "add instruction and communication overhead that agents follow inconsistently, and they are not portable across harnesses". The entry names no specific swarm mechanism that would answer that objection. |
| Swarm task distribution → `.claude/agents/research-curator.md` (Integration Opportunities) | Too abstract: "standardized swarm-coordination and multi-agent task distribution patterns from curriculum phases 15-17" names no mechanism; the entry documents no content of phases 15-17 beyond their titles. |
| Standard Lesson Workflow step 4 "Keep evidence: command, working directory, exit code, output, artifacts produced" (Installation & Usage) | Already covered: `plugins/development-harness/skills/verify-done/SKILL.md` lines 34 and 49 require terminal output of a successful run as completion evidence and state "exit code 0 is NOT enough". |
