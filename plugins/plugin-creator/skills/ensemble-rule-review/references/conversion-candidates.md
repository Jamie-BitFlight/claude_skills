# Fan-Out Conversion Candidates — Ranked Synthesis

Catalog of in-repo rule-following work suitable for restructuring into the fan-out map-reduce
ensemble (partition ruleset across overlapping cheap parallel sub-agents → fixed-schema findings
→ weight-by-corroboration → drop the tail).

## Table of Contents

- [Weighting Criteria](#weighting-criteria)
- [Tier 0 — Already a Partial Implementation](#tier-0--already-a-partial-implementation-reference--standardize)
- [Tier 1 — Highest Payoff](#tier-1--highest-payoff-large--partition-ready--replicated--single-pass)
  - [C1 Generic Multi-Dimension Code Review](#c1-generic-multi-dimension-code-review--most-replicated-cluster)
  - [C2 Plugin-Creator Audit/Assessor Family](#c2-plugin-creator-auditassessor-family--tier-partitioned-convert-once-cascades)
  - [C3 Holistic-Linting](#c3-holistic-linting--largest-raw-ruleset-user-flagged)
- [Tier 2 — Strong, Mostly Partition-Ready](#tier-2--strong-mostly-partition-ready)
  - [C4 Summarizer Fidelity Rules](#c4-summarizer-fidelity-rules--7-rule-canonical-replicated-5x)
  - [C5 CLI/UI Design Review](#c5-cliui-design-review-python-engineeringdesigning-ui-for-cli--textbook-pre-partition)
  - [C6 Verification / Done Gates](#c6-verification--done-gates--pre-partitioned-single-pass)
  - [C7 Named-Framework Compliance](#c7-named-framework-compliance--partitions-handed-to-you-free-quick-wins)
- [Tier 3 — Solid, Smaller or Needs Enumeration](#tier-3--solid-smaller-or-needs-enumeration)
  - [C8 Language-Specialist Review Agents](#c8-language-specialist-review-agents)
  - [C9 Orchestration / Hallucination Detection](#c9-orchestration--hallucination-detection)
- [Explicit vs Implicit Split](#explicit-vs-implicit-split)
- [Meta-Findings](#meta-findings-observed-act-worthy)
- [Recommended Pilots](#recommended-pilots)
- [Second-Pass Additions](#second-pass-additions)

---

**Method:** 7 territory finders over the 30-plugin tree plus `.claude/`, identical detection
checklist plus fixed schema plus 1-5 fit rubric. (Per-finder reports were written to a
gitignored `.tmp/scratch/` scratch directory during the survey; they are working artifacts, not
committed to the repo.)

**Counts (finder-reported):** a-b 12/6 · c-d 16/8 · e-g 7/5 · h-l 7/4 · m 0/0 ·
n-p 18/12 · q-s 10/8 · t-z 15/10 → ~85 candidates, ~53 at fit≥4.

**Verification caveat:** ruleset-size numbers below are finder estimates relayed from
sub-agents. They are not independently re-read by the orchestrator. Treat as ranking
signal, not ground truth, until the pilot conversion reads the canonical file.

---

## Weighting Criteria

A candidate converts well when it scores on:

1. **Ruleset size** — more independent rules = more to parallelize = bigger speed gain.
2. **Partition-readiness** — named categories/dimensions/principles = the split is free.
   Implicit rubrics ("pythonic", "modernization") must be enumerated first = design cost.
3. **Current cost** — a single Sonnet/Opus pass holding the whole ruleset is the expensive
   baseline the user's journal-review result improved ~35x. Already-parallel = low payoff.
4. **Replication** — the same ruleset recurring across N files means one conversion plus a
   shared template cascades. This is the repo-level corroboration signal.

---

## Tier 0 — Already a Partial Implementation (reference + standardize)

**`development-harness/skills/multi-perspective-review` + `agents/reviewer-{security,quality,performance,accessibility}`**

- This is the user's pattern already running: a 4-worker parallel review fan-out with
  per-worker SOPs and a merge gate. It is the in-repo proof the pattern fits.
- Opportunity: it is the reference implementation to standardize from — extract its structure
  into the shared template, then add the two pieces it lacks vs `/code-review`:
  a fixed candidate schema and an explicit weight-by-corroboration reducer (today it
  merges by any-REJECT, not by corroboration weighting).
- Note: each reviewer agent still applies its own checklist serially — a second-level
  fan-out inside each worker is available if needed.

---

## Tier 1 — Highest Payoff (large + partition-ready + replicated + single-pass)

### C1 Generic Multi-Dimension Code Review — most replicated cluster

Same "review code against N quality dimensions in one pass" ruleset, duplicated:

- `.claude/agents/code-review.md` — ~25-35 criteria, 3 severity tiers (~78 bullets) — fit5
- `development-harness/agents/code-reviewer.md` — 7 universal dims + stack rules — fit5
- `python-engineering/skills/review/SKILL.md` — 9 dimensions, 36 items — fit5
- `.claude/templates/code-review-checklist.md` — 15 items, 4 sections — fit4
- `python3-development/skills/python3-review` — near-duplicate of python-engineering (SKIP: convert the `python-engineering` copy only; see meta-finding 1)

Partition: one worker per dimension (correctness / security / perf / error-handling /
naming / tests / docs), merge by severity plus corroboration.

Why top: biggest replication; the reviewer-* agents above already prove the split works.

### C2 Plugin-Creator Audit/Assessor Family — tier-partitioned, convert-once cascades

- `skills/audit-skill-completeness` — 20+ (5 agentskills checks + 8 scored categories) — fit5
- `skills/assessor` + `references/scoring-criteria.md` — 4 tiers, 15-20 — fit5
- `agents/skill-auditor` — 12-15 — fit5
- `agents/plugin-assessor` — 4 assessment tiers — fit5
- `skills/audit-agent-lifecycle` — 8 dimensions — fit4
- `skills/audit-skill-lifecycle` — 7 dimensions — fit4
- `agents/refactor-validator` — 5 phases, 15+ — fit4

Partition: one worker per tier/dimension; reducer = weighted score. The whole family
shares the tier structure → one template stamps all 7.

### C3 Holistic-Linting — largest raw ruleset; user-flagged

- `agents/post-linting-architecture-reviewer` — 30 items / 7 architectural categories — fit5
- `skills/holistic-linting/SKILL.md` — 12 imperatives + 1000+ backing rules (ruff/bandit/
  mypy across 51 reference files) — fit5
- `agents/linting-root-cause-resolver` — 15+ — fit4
- `skills/holistic-linting-resolver` — 22+ procedural across ruff/mypy/pyright — fit4

Partition: by linter family (ruff / bandit / mypy / pyright) for detection; by the 7
architectural categories for the post-review. Biggest ruleset → biggest raw parallelism.

Caveat: resolution mutates files → the verify gate matters more here than in read-only
reviews; corroboration must run before any write.

---

## Tier 2 — Strong, Mostly Partition-Ready

### C4 Summarizer Fidelity Rules — 7-rule canonical replicated 5x

- `skills/summarizer/references/fidelity-rules.md` — 7 rules (canonical) — fit5
- `skills/agent-result-relay` — 12 — fit5
- `skills/file-summarization` — 20 — fit4
- `skills/multi-source-synthesis` — 17 — fit4
- `skills/url-summarization` — 14 — fit4
- `skills/image-summarization` — 14 — fit4

Nature: the fan-out here is the fidelity check on a produced summary, not the summary
generation — i.e. the verify-gate half of the framework. Strong template for that half.

Convert canonical `fidelity-rules.md` once; the 5 consuming skills inherit it.

### C5 CLI/UI Design Review (`python-engineering/designing-ui-for-cli`) — textbook pre-partition

- `references/critique-checklist.md` — Nielsen's 10 heuristics, each scored 0-4 — fit5
- `references/polish-checklist.md` — 22 items — fit4
- `references/audit-checklist.md` — 5 scored dimensions — fit4

Nielsen 10 = 10 ready-made overlapping jobs. Near-zero partition design cost.

### C6 Verification / Done Gates — pre-partitioned, single-pass

- `agent-orchestration/.../post-completion-validation-protocol.md` — 44 (11 commit types x4) — fit5
- `scientific-method/skills/evidence-first-debugging` — 13 (5 rules + 8 checklist) — fit5
- `development-harness/skills/verify-done` — 8 sections — fit4
- `development-harness/skills/final-verification` — 5 dimensions — fit4
- `verification-gate/skills/verification-gate` — 4 checkpoints, ~25 sub-questions — fit4

### C7 Named-Framework Compliance — partitions handed to you free (quick wins)

- `twelve-factor-app/SKILL.md` — 15 factors — fit5
- `.claude/skills/design-anti-patterns/references/uncodixfy-rules.md` — 50+ rules — fit5
- `gitlab-skill/SKILL.md` — 24 checklist across 3 gates — fit5
- `fastmcp-creator/.../typescript-mcp-server.md` — 12 RULE statements — fit5
- `the-rewrite-room/.../quality-criteria.md` — 40 items / 8 categories — fit5
- `.claude/skills/evaluate-sdlc-layers` — 29 items / 6 sub-checklists — fit5

Each names its own categories → those categories ARE the worker boundaries.

---

## Tier 3 — Solid, Smaller or Needs Enumeration

### C8 Language-Specialist Review Agents

- `bash-development/agents/bash-script-auditor` — 18-22 — fit5
- `.claude/agents/c-systems-programmer` — 26 — fit4
- `.claude/agents/javascript-pro` — 22+ — fit4
- `.claude/agents/typescript-pro` — 14+ — fit4
- `perl-development/agents/perl-script-auditor` — 6 categories, ~20 — fit4

### C9 Orchestration / Hallucination Detection

- `agent-orchestration/.../hallucination-triggers.md` — 4 categories, ~35-40 rules — fit5
- `agent-orchestration/skills/agent-orchestration/SKILL.md` — 6-8 gates — fit4
- `agent-orchestration/skills/how-to-delegate` — 6 pre-flight + 10 step gates — fit4
- `agentskill-kaizen/references/arl-qa-expert-panel.md` — R1-R10 — fit4
- `scientific-method/agents/retrospective-analyst` — 3 artifacts x sub-sections — fit4

---

## Explicit vs Implicit Split

**Partition-ready now (explicit lists):** C2, C5, C6, C7, C4 — categories already named.

**Needs enumeration first (implicit rubrics → make explicit, then partition):**

- `python-engineering/skills/modernpython` "modernization opportunities" → PEP roster
- `python-engineering/skills/snakepolish` + `review` "Modern Patterns" / "pythonic"
- `c-systems-programmer` "Common Pitfalls", `javascript-pro` "Anti-Patterns to Reject"
- `holistic-linting` SKILL "best-practice imperatives"

These carry the higher design cost but also the higher reliability gain (the implicit
list is where a single Sonnet pass silently drops criteria).

---

## Meta-Findings (observed, act-worthy)

1. **`python-engineering` and `python3-development` are near-duplicate plugins** — both
   carry analyze-test-failures, comprehensive-test-review, modernpython, review/python3-review,
   snakepolish, test-failure-mindset, typer, ty, etc. Per repo-owner direction (conversation
   2026-05-30), `python3-development` is being wound down in favour of `python-engineering` and
   kept only so existing users do not break — so convert the `python-engineering` copies and SKIP
   the `python3-development` duplicates. This is owner guidance for this catalog, not a deprecation
   notice published in the plugin's own manifest or README; verify against the plugin before
   relying on it elsewhere.
2. **The framework already exists in-repo** (Tier 0). Standardize from it rather than
   designing from scratch.
3. **Replication is the corroboration signal at repo scale** — code-review (C1), summarizer
   fidelity (C4), and the audit family (C2) each recur; a shared template plus one canonical
   conversion cascades across the cluster.

---

## Recommended Pilots

- **Fastest proof, lowest design cost:** C7 named-framework (12-factor / uncodixfy / gitlab)
  — partitions are free, output is a compliance matrix.
- **Highest cascade:** C2 plugin-creator audit family — tier-partitioned, one template → 7 targets.
- **User-flagged + biggest ruleset:** C3 holistic-linting — partition by linter; verify gate
  guards the file mutations.
- **Standardize the existing pattern:** Tier 0 multi-perspective-review — turn the working
  4-way fan-out into the canonical template (add fixed schema + corroboration-weight reducer).

---

## Second-Pass Additions

A narrow single-plugin re-scan of the four densest plugins (after the first pass overloaded its
wide-territory finders) roughly doubled the fit>=4 set in the overloaded zones and surfaced four
clusters the first pass missed. Marked NEW (missed by pass 1) or CONFIRMED.

### development-harness — skills

- complete-implementation — 5 sequential quality-gate stages — fit5 — NEW
- clear-cove-task-design — CLEAR framework + CoVe — fit5 — NEW
- generate-task — CLEAR ordering + CoVe verification — fit5 — NEW
- add-new-feature — quality vigilance + AC extraction + phase gates — fit5 — NEW
- find-cause — disambiguation + root-cause hypothesis branches (implicit) — fit5 — NEW
- forensic-review — requirement tracing + property checking — fit5 — NEW
- code-review-llm / code-review-nodejs / code-review-architecture — per-domain implicit rubrics — fit5 — NEW
- comprehensive-test-review, evaluate-sdlc-layers, final-verification — fit5 — CONFIRMED
- planner-rt-ica, task-decomposition (9-part CLEAR + 4 atomicity), validation-protocol (7 checks), discovery — fit4 — NEW

### development-harness — agents

- code-reviewer — 13 evals (7 dims + AC + stack + verdict) — fit5 — CONFIRMED
- feature-verifier — 12 verification steps — fit5 — NEW
- impact-analyst — 11 evals (per-system + 7-item ecosystem) — fit5 — NEW
- backlog-item-groomer — 10+ rulesets (RT-ICA, classification, discovery, deps) — fit5 — NEW
- doc-drift-auditor — fit4 — CONFIRMED; dh-context-gathering (9-point), ecosystem-researcher (9), rtica-assessor — fit4 — NEW

### plugin-creator — skills

- lint — 23 ruff/validator error codes (independent per-rule checkers) — fit5 — NEW
- add-doc-updater — 12-15 phase-gated validation checks — fit5 — NEW
- audit-skill-lifecycle (7), audit-skill-completeness (6-8), audit-agent-lifecycle (8) — fit4-5 — CONFIRMED
- optimize-claude-md, plugin-creator, plugin-lifecycle, prompt-optimization, refactor-plugin,
  refactor-skill, skill-creator, subagent-refactoring-methodology — multi-phase gated checklists — fit4 — NEW

### plugin-creator — agents

- refactor-validator (9 criteria x 5 phases), plugin-assessor (9 phases), skill-auditor (11) — fit5 — CONFIRMED
- grader (per-assertion), comparator (per-criterion), ai-doc-optimizer (CoVe 5-6 falsifiable
  questions), skill-sync-source-validator (per-URL), agent-creator (5 fields), hook-creator
  (10 constraints) — textbook per-item fan-out — fit4 — NEW

### python-engineering

- review — 36 items / 9 categories — fit5 — CONFIRMED
- modernpython — 10 PEP-roster principles (implicit→explicit) — fit5 — NEW
- comprehensive-test-review — fit5 — CONFIRMED
- designing-ui-for-cli (Nielsen /40 + 22-item) — fit4 — CONFIRMED
- debug (6-phase), pre-commit (9 stages), lint, code-reviewer agent — fit4 — NEW
- stinkysnake (9-phase workflow), snakepolish (8-step impl phase) — CONVERT PER-PHASE, not
  whole-skill. Verified 2026-05-30: these are sequential workflows, NOT flat single-pass
  rulesets. The whole skill fails the When-to-Use gate; individual rule-bearing phases do not.
  For stinkysnake, the ensemble targets are Phase 2 (type-gap inventory), Phase 3 (modernization
  construct/PEP roster), and Phase 4 (plan review); Phases 6/8/9 are work-partition fan-outs.
  See `composing-in-workflows.md`. (Correction: an earlier pass mis-scored these as flat fit4
  rulesets.)

### python3-development — DO NOT CONVERT (deprecated plugin)

Per repo-owner direction (conversation 2026-05-30), `python3-development` is being wound down in
favour of `python-engineering` and kept only so existing users do not break. Do NOT convert any of
its skills/agents; their live equivalents in `python-engineering` are the conversion targets
instead. (Owner guidance for this catalog — not a deprecation notice in the plugin's own manifest
or README. The candidates below are recorded for completeness only.)

- quality-gate — 5 sequential gates / 15+ criteria — fit5 — NEW — SKIP (use python-engineering)
- type-system-design-patterns — 4-step audit / 12+ per interface — fit5 — NEW — SKIP (use python-engineering)
- code-reviewer (agent) — 18-item / 5 categories — fit5 — NEW — SKIP (use python-engineering)
- python3-standards — 40+ criteria / 8 domains (shared rule hub) — fit5 — NEW — SKIP (use python-engineering)
- architecture-spec-patterns, comprehensive-test-review, stinkysnake, modernpython — fit4 — NEW — SKIP (use python-engineering)

### Net-new clusters pass 1 missed

1. The whole `python3-development` plugin (`python3-standards` 40+ criteria hub, `quality-gate`,
   distinct 18-item `code-reviewer`, `type-system-design-patterns`) — nearly invisible in pass 1.
   NOTE: per owner direction (meta-finding 1) do NOT convert `python3-development`; recorded for completeness only.
2. plugin-creator authoring-workflow cluster (`plugin-creator`, `plugin-lifecycle`,
   `skill-creator`, `refactor-skill`, `prompt-optimization`, `subagent-refactoring-methodology`).
3. plugin-creator CoVe/grading agents (`grader`, `comparator`, `ai-doc-optimizer`,
   `skill-sync-source-validator`) — independent per-item evaluation, ideal fan-out.
4. development-harness CLEAR+CoVe task-design family and the `code-review-{llm,nodejs,architecture}` trio.

The pass-1 vs pass-2 recall gap is itself evidence for this skill's thesis: smaller per-worker
scope raises recall. The overload that hurt the wide pass-1 finders is the overload the
ensemble pattern removes.
