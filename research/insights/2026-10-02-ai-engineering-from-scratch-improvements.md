# Improvement Proposals: AI Engineering from Scratch

**Research entry**: ./research/ai-research-tools/ai-engineering-from-scratch.md
**Generated**: 2026-10-02
**Patterns assessed**: 7
**Backlog items created**: 0
**Deferred (low confidence)**: 0
**Skipped (already covered or tracked)**: 7

---

No pattern in this entry produced an actionable gap. The resource is a learning curriculum, not a
tool, and all 7 items under "Relevance to Claude Code Development" carry `Change: none` with a
specific reason: four state that the local file already covers the topic (Agent Skills, prompt
engineering, evaluation practice, parallel work), and three state the topic is out of scope (MCP
Phase 13 learner route, the Layered Skill Learning Path, the single-entry research-curator worker).
Two further mechanisms found outside that section (release evals for skills, evidence capture per
lesson run) already exist locally; they are listed after the seven items in the Skipped Patterns
table with the files and searches.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| (none) | — | — |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Agent Skills and SDK Integration -> `plugins/plugin-creator/skills/agentskills/SKILL.md` (Applications) | Entry states `Change: none` — "`plugins/plugin-creator/skills/agentskills/` already covers the curriculum's Agent Skills path topics". Its `references/` holds `specification.md`, `integration.md` and `best-practices.md`. |
| Model Context Protocol Implementation -> `docs/MCP-INDEX.md` (Applications) | Entry states `Change: none` — "out of scope (`docs/MCP-INDEX.md` indexes how to build MCP servers inside this repository's plugins; the curriculum's Phase 13 and `/learn-mcp` route teach the protocol to learners, a different audience)". `docs/MCP-INDEX.md` also already indexes an internal 30-minute MCP tutorial (line 47). |
| LLM Engineering and Prompt Engineering -> `plugins/plugin-creator/skills/prompt-optimization/SKILL.md` (Applications) | Entry states `Change: none` — "already applies prompt-engineering practice to this repository's artifacts; the curriculum's Phase 11 is learner-facing background, not a gap here". |
| Layered Skill Learning Path (Patterns Worth Adopting) | Entry states `Change: none` — "out of scope (the development harness sequences work items through the SAM pipeline for contributors; it ships no learner routes, so the curriculum's 12 career-route manifests have no counterpart to compare against)". The entry's `git grep` for `learning-path` and `curriculum` over the local plugin, skill, agent, rules and docs paths returned 0 matches. |
| AI Evaluation and Reliability Engineering Practices -> `plugins/development-harness/docs/impact-analysis-principals.md` (Integration Opportunities) | Entry states `Change: none` — "already states the evaluation practice the `ai-evaluation-reliability-engineer` route teaches (evals, observability, canaries, rollback); the route is a learner syllabus, not a source of new harness requirements". The local doc covers baseline-vs-candidate comparison (line 41), reliability (line 53), and continuous evaluation with cited eval-lifecycle sources (line 180). |
| Multi-Agent Orchestration and Parallel Work Patterns -> `plugins/agent-orchestration/skills/parallel-work/SKILL.md` (Integration Opportunities) | Entry states `Change: none` — "already covers the fan-out shape and deliberately declines persistent teams with shared messaging". `parallel-work/SKILL.md` "Persistent teams" section (lines 42-44) states teams with messaging "add instruction and communication overhead that agents follow inconsistently, and they are not portable across harnesses". |
| Agent Orchestration and Research Workflows -> `.claude/agents/research-curator.md` (Integration Opportunities) | Entry states `Change: none` — "out of scope (`.claude/agents/research-curator.md` is a single-entry worker whose Boundaries section assigns batch coordination to the `/research-curator` skill; Phase 16's supervisor-orchestrator pattern describes a runtime this worker does not implement)". |
| Outside the Relevance section: Agent Skills path "release evals" sub-topic (curriculum route list) | Already covered: `plugins/plugin-creator/skills/skill-creator/scripts/run_eval.py`, `plugins/plugin-creator/skills/skill-creator/references/evaluation-and-optimization.md`, and `plugins/plugin-creator/skills/skill-creator/assets/eval_review.html` implement skill evals (`git grep -il "evals\?/\|evals.json\|eval set" -- plugins/plugin-creator/skills/skill-creator/` -> 5 files). The entry gives no detail of the curriculum's eval mechanism to compare against. |
| Standard Lesson Workflow step 4 "Keep evidence: command, working directory, exit code, output, artifacts produced" (Installation & Usage) | Already covered: `plugins/development-harness/skills/verify-done/SKILL.md` lines 34 and 49 require terminal output of a successful run as completion evidence and state "exit code 0 is NOT enough". |
