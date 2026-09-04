# ARL Expert Panel — Q&A Record

**Date Started:** 2026-02-13
**Phase:** 4 (Validation and Rigor Review)
**Status:** In Progress — Phase 1 complete, Phase 2 complete, Phase 3 complete

---

## Session State

- **Question Groups Discussed:** 5/5 (Phase 1 COMPLETE)
- **R-Requirements Addressed:** R1, R2, R3, R4, R5, R6, R7, R8, R9, R10 (all 10 addressed; R9 primary in Q5)
- **Experts Spawned:** bmad-expert, gastown-expert, gsd-expert, octocode-expert, ralph-expert, sam-expert

---

## Question Group 1: Human Gating and Judgment

**Status:** DISCUSSED (all 6 experts responded)

**Questions:**
1. When working with AI, why does a human stop the AI from doing an action? (5 whys)
2. What does the human need to know to be sure about what the AI is doing, and what it will do next?
3. At what points is judgment needed? Which of those could be eliminated, front-loaded, or reduced?
4. What processes need more judgment than others? How do we know?
5. How do systems and processes get evaluated as needing closer human attention? What criteria or heuristics do frameworks use?

**R-Requirements touched:** R1, R3, R4, R5, R8

---

## Question Group 2: Interaction Points and Front-Loading

**Status:** DISCUSSED (all 6 experts responded)

**Questions:**
1. What are the interaction points in these frameworks? Where does the human touch the system?
2. How does each framework assess what is needed by the human at each of those points?
3. How do they front-load human-based work so it can be done all at once — allowing the agent to continue without the human until the task is done?
4. What must be captured upfront for that to work? What fails when it isn't captured?

**R-Requirements touched:** R1, R4, R5

---

## Question Group 3: Framework Design Rationale and Conditions

**Status:** DISCUSSED (all 6 experts responded)

**Questions:**
1. Why has your framework chosen that way of doing it? What problem was it solving?
2. Is that way the only way, or is it conditional? Under what conditions does the framework do X vs Y?
3. How are those conditions detected? What triggers the framework to take one path vs another?
4. What makes a project, feature, or task hit these complexity or bounded/unbounded checkpoints? How does the framework decide that something is "simple" vs "complex," or "bounded" vs "unbounded"?

**R-Requirements touched:** R2, R7, R8, R10

---

## Question Group 4: Alignment, Drift, and Definition of Done

**Status:** DISCUSSED (all 6 experts responded)

**Questions:**
1. How is alignment between human intent and agent behavior tracked?
2. How is drift detected? What constitutes drift vs acceptable evolution?
3. How is the definition of done validated? Who validates it? What makes it machine-checkable vs judgment-dependent?
4. When definition of done is ambiguous, how do frameworks handle it?

**R-Requirements touched:** R5, R6, R7

---

## Question Group 5: Agent Teams and Orchestration

**Status:** DISCUSSED (all 6 experts responded)

**Questions:**
1. Given tools like agent teams, how could this be utilized within a system to assist with orchestration and human-gating?
2. Where could parallel teammates replace sequential human checks?
3. Where could cross-examination between teammates surface issues before they reach a human?
4. How could a lead agent synthesize escalation so the human gets compressed context instead of raw logs?

**R-Requirements touched:** R2, R3, R4, R9

---

## Responses

### Question Group 1 Responses

#### Q1: Why does a human stop the AI from doing an action? (5 Whys)

**Cross-Framework Root Causes Identified:**

All 6 frameworks converge on the same fundamental insight through different paths:

| Framework | Root Cause | Key Citation |
|---|---|---|
| **BMAD** | The system has no external ground truth to validate its own findings. The human IS the ground truth. | adversarial-review.md:35 "You decide what's real" |
| **SAM** | LLMs optimize fluent continuation, not truth evaluation. Hallucination is structural, not behavioral. The fix must be structural (pipeline stages) not instructional. | stateless-software-engineering-framework.md:1051, :108 |
| **GSD** | The human holds intent authority and sensory access. The AI is scoped to a single plan, not the whole project. | discuss-phase.md:26, checkpoints.md:9, gsd-executor.md:118-126 |
| **Ralph** | Evaluating "is this approach viable?" requires domain judgment the system doesn't encode. Quality thresholds exist but "is this the right thing to build?" does not. | hatless_ralph.rs:21-23, preflight.rs:384-399 |
| **Octocode** | The AI lacks the ability to evaluate whether its own reasoning is correct. If Verifier = Generator, they share blind spots. | MANIFEST.md:117-123 |
| **Gastown** | Trust is not yet established, or the operation is outside the system's competence boundary. "Daemon can't reason." | watchdog-chain.md:28-29, :34-35 |

**Convergence pattern:** All frameworks identify that the AI cannot reliably self-evaluate. The divergence is in their response:
- SAM/BMAD → structural pipeline with human gates at boundaries
- GSD → front-load decisions, checkpoint for sensory/visual verification
- Ralph → count-based thrashing detection + human escalation
- Octocode → GAN-inspired adversarial review + explicit confidence levels
- Gastown → three-tier escalation chain with time-based severity auto-bump

**Disagreement:** SAM argues behavioral instructions "cannot override architectural limitations" (stateless-software-engineering-framework.md:108). Octocode's approach (STOP gates, verbalization requirements) IS behavioral instruction-based. This is a tension: does Octocode's approach work because of the phase-gate structure (structural) or because of the explicit STOP instructions (behavioral)?

---

#### Q2: What does the human need to know?

**Cross-Framework Information Categories:**

| Category | BMAD | SAM | GSD | Ralph | Octocode | Gastown |
|---|---|---|---|---|---|---|
| **Current state/progress** | template-output display (workflow.xml:71-74) | Artifact files, not conversation (README.md:149) | Checkpoint return format with progress (gsd-executor.md:183-214) | Hat/event routing, task state (task.rs) | Verbalized self-assessment (research:193-196) | MoleculeStatusInfo with progress % (molecule_status.go:99-126) |
| **What comes next** | Menu options [a/c/p/y] (workflow.xml:75-90) | Stage-specific artifacts with defined schemas | Task <verify> and <done> fields (gsd-planner.md:128-149) | Deterministic event topology (ralph.yml:13-119) | Numbered plan steps with tools (research:293-306) | NextAction field (molecule_status.go) |
| **Confidence/quality** | Completeness scores, DoD scores (step-v-12, checklist.md:72) | RT-ICA AVAILABLE/DERIVABLE/MISSING table (ssf:374-378) | Verifier Observable Truths pass/fail/uncertain (gsd-verifier.md:316-401) | BackpressureEvidence metrics (event_parser.rs:95-128), Confessor confidence 0-100 | Explicit HIGH/MED/LOW confidence (plan:68-75) | Severity levels CRITICAL/HIGH/MEDIUM (escalation.md:18-22) |
| **Why stopped** | HALT conditions with reasons (correct-course/checklist.md:36) | BLOCKED with specific blockers (ssf:630) | Checkpoint details + Awaiting section | escalate.human with verified issue (ralph.yml:107-108) | "Blocked >2 attempts" summaries (plan:300) | Structured escalation: Question/Options/Context (escalation.md:87-97) |
| **Audit trail** | Coverage matrices, checklist scores | Forensic review evidence tables (ssf:675-707) | VERIFICATION.md with scored results | Confessor memories, JSONL planning files | file:line evidence requirements (research:535) | DetachAuditEntry with timestamps (audit.go:12-20) |

**Key insight:** SAM is unique in surfacing information as files, not conversation. All other frameworks use a mix of structured output within the conversation flow. Gastown's MoleculeStatusInfo is the most machine-readable (Go struct). Ralph's event bus makes the next action deterministic from the current state.

---

#### Q3: Human Decision Points — Eliminable / Front-Loadable / Irreducible

**Cross-Framework Decision Point Classification:**

**ELIMINABLE (machine-verifiable conditions can replace human):**
- File/schema existence checks (BMAD step-01:49-58, GSD auth gates, Gastown polecat safety checks)
- FR-to-epic coverage matrices (BMAD step-03:87-105)
- Deterministic validation — tests/linters/build (SAM README.md:153, Ralph backpressure, GSD auto-fix Rules 1-3)
- Content structural inventory comparison (SAM human-out-of-loop:129)
- Merge failure triage for recoverable types (Gastown types.go:231-239)
- Finding count tracking across iterations (SAM human-out-of-loop:130)
- Fast-path bypass for simple tasks (Octocode research:237-259)

**FRONT-LOADABLE (captured once, used throughout):**
- Goal/intent/scope definition (SAM RT-ICA, GSD discuss-phase/CONTEXT.md, Octocode Phase 0, BMAD product brief→PRD)
- Complexity/scope classification (SAM process_realignment:43-47, GSD discovery levels, Octocode Quick/Full mode)
- Downstream dependency mapping (SAM context integration, GSD planner file manifests)
- Convergence exit criteria — max iterations, severity floor (SAM human-out-of-loop:144, GSD verify-work:480-490)
- Purpose invariant (SAM human-out-of-loop:145)
- Escalation routing rules (Gastown escalation.md:28-36 — categories pre-mapped to tiers)
- Molecule step decomposition (Gastown molecule.go:55-66 — DAG validated at authoring time)
- Artifact creation permissions (Octocode — if blanket permission granted at start)

**IRREDUCIBLE (requires continuous human judgment):**
- Adversarial review false-positive filtering (BMAD adversarial-review.md:33-35)
- Proportionality — is the fix worth its blast radius (BMAD correct-course/checklist.md:135-180, GSD executor Rule 4)
- Purpose drift beyond automated threshold (SAM human-out-of-loop:157)
- Split justification — is the new entity independently viable (SAM human-out-of-loop:153)
- Visual/sensory verification (GSD checkpoints.md:20-26 — "Users ONLY visit URLs, click UI")
- Architectural/design decisions (Gastown escalation.md:260, Ralph planning_session.rs)
- AI stuck / blocked (Octocode plan:300, Ralph human.interact, Gastown polecat escalation)
- Root cause after thrashing (Ralph mod.rs:447-448 — system detects failure count, not cause)
- Setting the objective (Ralph hatless_ralph.rs:21-23 — "no mechanism to auto-generate objectives")

**Cross-examination note:** Octocode classifies plan approval as "REDUCIBLE but not eliminable" — if plan quality were self-certifiable with evidence-backed traceability (plan:207-208), approval could be auto-granted. No other framework claims this is reducible. This is a tension point: can machine-verified plan quality substitute for human plan approval?

---

#### Q4: What processes need more judgment? How do frameworks distinguish?

**Cross-Framework Complexity Classification:**

| Framework | Mechanism | Tiers | Citation |
|---|---|---|---|
| **BMAD** | Quick Flow vs Full Path; module.yaml scale-domain-adaptive; change scope Minor/Moderate/Major | 3 tiers: quick flow (3 commands) → full path (6+ workflows) → correct-course | README.md:53, module.yaml:13-44, correct-course/instructions.md:161-164 |
| **SAM** | Scope-Dependent Complexity (High/Medium/Low clarity); Artifact Selection Matrix mapping complexity→required artifacts | 4 tiers: Simple→Moderate→Complex→Firmware/Embedded | process_realignment.md:43-47, :143-149, human-out-of-loop:252-256 |
| **GSD** | Discovery levels (0-3); Deviation rules (1-4); Checkpoint type distribution (90% verify, 9% decision, 1% action); Context budget thresholds | 4 tiers: Level 0 skip → Level 1 quick → Level 2 standard → Level 3 deep dive | gsd-planner.md:97-126, gsd-executor.md:88-139, checkpoints.md:766-768 |
| **Ralph** | Hat routing through event topology; confidence threshold (80); thrashing counters | 4 tiers: clean path → confessor issues → escalate.human → thrashing termination | ralph.yml:22-117, ralph.yml:76-78, mod.rs:447-448 |
| **Octocode** | Fast-Path vs Full-Path (4 binary criteria); Quick vs Full review mode; Confidence→action mapping | Binary (fast/full) with confidence overlay (HIGH/MED/LOW) | research:237-259, PR:46-53, plan:68-75 |
| **Gastown** | Tier hints on molecule steps (haiku/sonnet/opus); Severity-based routing (CRITICAL→HIGH→MEDIUM); Failure type classification (recoverable vs not) | 3 severity tiers + model tier hints | molecule.go:18, escalation.md:18-22, types.go:231-239 |

**Convergence:** All frameworks use some form of binary or multi-tier classification to route tasks to appropriate authority levels. The classification happens at different points (upfront in SAM/GSD, runtime in Ralph/Gastown).

**Novel finding:** Gastown's molecule tier hints (haiku/sonnet/opus) directly tie complexity to model capability — more complex steps get more capable models. No other framework makes this explicit at the step level.

---

#### Q5: Escalation Triggers and Heuristics

**Cross-Framework Escalation Trigger Taxonomy:**

| Trigger Type | Frameworks Using It | Examples |
|---|---|---|
| **Count-based failure** | Ralph (3 blocks→abandon, 3 abandons→terminate), GSD (3 planner loops→max iterations), Octocode (2-3 attempts→ask user), Gastown (2-3 test failures→escalate) | Ralph mod.rs:1917, GSD verify-work:480-490, Octocode plan:300, polecat.md.tmpl:453 |
| **Confidence threshold** | Ralph (Confessor ≥80), Octocode (HIGH/MED/LOW), BMAD (completeness scores) | Ralph ralph.yml:76-78, Octocode plan:68-75 |
| **Quality metric failure** | Ralph (coverage ≥80%, mutation ≥70%, complexity ≤10), GSD (verifier Observable Truths), SAM (deterministic backpressure) | Ralph event_parser.rs:161-163, GSD gsd-verifier.md:107, SAM README.md:153 |
| **Scope exceeded** | GSD (5+ tasks/plan = blocker), Octocode (>2 repos→STOP, >500 lines→split), Gastown (cross-rig→Mayor) | GSD gsd-plan-checker.md:196-208, Octocode plan:149, polecat.md.tmpl:476-479 |
| **Category-based routing** | Gastown (7 categories→3 tiers), BMAD (scope Minor/Moderate/Major→authority level) | Gastown escalation.md:28-36, BMAD correct-course/instructions.md:161-164 |
| **Time-based auto-escalation** | Gastown (stale 4h→auto-bump severity), Ralph (MaxRuntime) | Gastown escalation-system.md:67-68, Ralph mod.rs:429-439 |
| **Prerequisite missing** | SAM (RT-ICA MISSING→BLOCK), BMAD (prerequisite validation), GSD (locked decision violated) | SAM ssf:377, BMAD step-01:67-73, GSD gsd-plan-checker.md:264-280 |
| **Security-sensitive** | Octocode (hardcoded secrets→immediate), Gastown (security→emergency category) | Octocode roast:359, Gastown escalation.md:254 |
| **Cannot verify programmatically** | GSD (UNCERTAIN status for visual/UX), BMAD (adversarial review false positives) | GSD gsd-verifier.md:264-268, BMAD adversarial-review.md:33 |
| **Zero findings (suspicious)** | BMAD (soft halt — "suspicious, re-analyze") | BMAD review-adversarial-general.xml:44 |

**Unique contribution — Gastown time-based auto-escalation:** No other framework implements automatic severity escalation over time. Gastown's stale_threshold (4h) with max_reescalations (2) means unacknowledged issues automatically become more urgent. This addresses the "forgotten escalation" failure mode.

**Unique contribution — SAM "detect insufficiency":** SAM explicitly states the ability to detect "I don't have enough information to decide" is itself a critical capability (human-out-of-loop:331). A loop that guesses when uncertain is worse than one that asks. No other framework articulates this as a design principle, though GSD's UNCERTAIN status and Octocode's LOW confidence→ask user are implementations of the same idea.

---

#### Cross-Examination Records

- **bmad-expert → gastown-expert:** Asked about validity filtering, escalation mechanisms, and convergence tracking.
- **sam-expert → ralph-expert:** Challenged Ralph on backpressure mechanism and whether count-based heuristics are sufficient.
- **octocode-expert → gsd-expert:** Cross-examined GSD on autonomous gate bypassing.

---

### Question Group 2 Responses

#### Q1: What are the interaction points? Where does the human touch the system?

**Cross-Framework Interaction Point Inventory:**

| Framework | Interaction Points | Key Citations |
|---|---|---|
| **BMAD** | 8 workflow steps with human gates: product brief→PRD→architecture→story-drafting→dev-kickoff→checklist→correct-course→adversarial-review. Each step has explicit menu options [a/c/p/y] for human routing. | workflow.xml:71-90, README.md:53 |
| **SAM** | 4 pipeline stages with boundaries: Discovery→Planning→Context Integration→Execution. Human touches at stage transitions, RT-ICA assessment, and process realignment triggers. Artifacts (files) are the handoff mechanism, not conversation. | README.md:149, stateless-software-engineering-framework.md:374-378 |
| **GSD** | 11 interaction points: project init, milestone definition, discuss-phase, plan approval, checkpoint responses (verify/decision/action), deviation escalation, phase completion, verify-work UAT, milestone audit, todo capture. 90% are verify-type (confirm/deny). | discuss-phase.md:26, checkpoints.md:9-26, gsd-executor.md:118-126, gsd-planner.md:97-126 |
| **Ralph** | 4 interaction points: objective setting (hatless_ralph.rs:21-23), planning session approval (planning_session.rs), human.interact escalation (ralph.yml:107-108), thrashing termination acknowledgment (mod.rs:447-448). Event topology makes routing deterministic. | ralph.yml:13-119, hatless_ralph.rs:21-23 |
| **Octocode** | 5 interaction points: Phase 0 context setup, plan approval (plan:207-208), STOP gates during review (research:193-196), blocked escalation (plan:300), artifact creation permission. Fast-path can skip plan approval for simple tasks. | research:237-259, plan:68-75, MANIFEST.md:117-123 |
| **Gastown** | 5 structural interaction types: molecule authoring (Mayor), formula definition (Mayor), delegation terms (crew→polecat), escalation responses (3-tier), detach/reattach audit review. Role taxonomy encodes who can interact. | molecule.go:55-66, escalation.md:28-36, polecat.md.tmpl:453-479 |

**Convergence:** All frameworks have interaction points at task initiation and escalation. The divergence is in density — BMAD has the most gates (8 sequential), Ralph has the fewest (4 with deterministic routing between them).

---

#### Q2: How does each framework assess what is needed by the human at each point?

**Cross-Framework Assessment Mechanisms:**

| Framework | Assessment Mechanism | Key Insight |
|---|---|---|
| **BMAD** | Sequential artifact chain — each step produces a template that the next step requires. Missing template = cannot proceed. Completeness scores on checklists quantify readiness. | The artifact IS the assessment — if it doesn't exist or score is below threshold, the human is needed. |
| **SAM** | RT-ICA (Reverse Thinking - Information Completeness Assessment) — works backward from the goal through the prerequisite chain, classifying each information need as AVAILABLE, DERIVABLE, or MISSING. MISSING items block progression. Dynamic, not fixed checklist — adapts to the goal. | The assessment adapts to what's being built. A CLI tool and a firmware project generate different MISSING lists. |
| **GSD** | Three mechanisms: (1) explicit code classification in discuss-phase tags, (2) workflow toggles (skip_research, preferences), (3) implicit workflow design where checkpoint type distribution (90/9/1) pre-determines human load. | GSD front-loads the WHAT in discuss-phase, so execution checkpoints are mostly verify-type (low-judgment). |
| **Ralph** | Event topology — the YAML event graph deterministically routes to human based on state transitions. Confidence threshold (≥80) on Confessor determines whether finding is auto-accepted or escalated. BackpressureEvidence metrics quantify quality. | The topology IS the assessment — no runtime analysis needed, the graph encodes when humans are needed. |
| **Octocode** | Fast-path criteria (4 binary checks: single repo, <500 lines, no cross-cutting, clear scope). If all pass → skip human. Confidence levels (HIGH/MED/LOW) on findings determine escalation. | Binary gate first, then confidence overlay on findings. Two-layer assessment. |
| **Gastown** | Role taxonomy — Polecats (AI workers) NEVER ask humans, Crew (human-facing) ALWAYS can. Molecule tier hints (haiku/sonnet/opus) assess step complexity. Escalation category routing (7 categories→3 tiers) pre-maps what needs human. | Structural role encoding replaces runtime assessment. The ROLE determines human contact, not the situation. |

---

#### Q3: How do frameworks front-load human work?

**Cross-Framework Front-Loading Spectrum:**

| Framework | Front-Loading Depth | What's Captured | Key Citation |
|---|---|---|---|
| **SAM** | Deepest — 4 stages before execution (Discovery→Planning→Context Integration→Task Decomposition). RT-ICA runs iteratively until MISSING count = 0 or accepted. | Goal, scope, complexity classification, information completeness, artifact selection, downstream dependencies, convergence criteria, purpose invariant. | stateless-software-engineering-framework.md:374-378, human-out-of-loop:144-145 |
| **BMAD** | Deep — sequential artifact chain (product brief→PRD→architecture→stories). "Create-story" is explicitly designed as a "context engine" to prevent dev agent failures. | Business requirements, functional requirements, architecture decisions, epic/story breakdown, acceptance criteria, DoD definitions. | README.md:53, workflow.xml:71-90 |
| **GSD** | 3-scale front-loading: (1) project-level via PROJECT.md, (2) phase-level via discuss-phase, (3) task-level via planner must_haves/preferences. | At project level: goals, milestones, success criteria. At phase level: context, requirements, preferences. At task level: file manifests, verify/done conditions. | discuss-phase.md:26, gsd-planner.md:128-149 |
| **Ralph** | Medium — objective + specs + event topology. Planning session captures objective and specifications; topology is pre-built, not per-task. | Objective (human-set invariant), specifications (Confessor captures), event routing (fixed topology). | hatless_ralph.rs:21-23, ralph.yml:13-119 |
| **Octocode** | Light-medium — Phase 0 context.md + hints system. Hints persist across sessions. Context.md captures project state, hints encode learned preferences. | Project context, repository structure, learned hints, PR scope limits, review preferences. | research:237-259, plan:207-208 |
| **Gastown** | Structural — molecules define step DAGs at authoring time, formulas define repeatable patterns, delegation terms set autonomy boundaries at creation. | Step decomposition, dependency graph, tier hints, escalation routing, role permissions. All encoded in Go structs. | molecule.go:55-66, escalation.md:28-36 |

**Key finding — SAM front-loading gap:** SAM has no mechanism to route back to discovery from execution when front-loading proves insufficient. If execution reveals the RT-ICA assessment was incomplete, the framework has no structured "return to discovery" path.

**Key finding — GSD auth gate gap:** GSD does not front-load authentication requirements. These are discovered at runtime when agents hit permission boundaries, causing checkpoint escalation rather than planned handling.

---

#### Q4: What must be captured upfront? What fails when it isn't?

**Cross-Framework Failure Modes from Insufficient Front-Loading:**

| Framework | What Must Be Captured | What Fails Without It | Citation |
|---|---|---|---|
| **BMAD** | Product brief with business context, FR list, architecture decisions | Dev agent produces code that doesn't align with business goals; create-story was explicitly designed to prevent this failure mode | README.md:53, workflow.xml:71-74 |
| **SAM** | RT-ICA AVAILABLE/DERIVABLE/MISSING assessment, scope classification, purpose invariant | Agent proceeds with MISSING information and hallucinate fills the gap; produces fluent but wrong artifacts | stateless-software-engineering-framework.md:108, :1051, human-out-of-loop:145 |
| **GSD** | discuss-phase context (goals, requirements, preferences), planner must_haves | Skipping discuss-phase: planner generates plans without requirements context, producing technically valid but wrong-direction work. Skipping must_haves: implementation satisfies tests but misses user intent. Skipping preferences: technically correct but user-hostile output. | discuss-phase.md:26, gsd-planner.md:128-149 |
| **Ralph** | Objective (human-set), specifications (Confessor-captured) | No mechanism to auto-generate objectives — without human-set objective, the entire topology has no purpose anchor. Confessor without specs cannot evaluate quality. | hatless_ralph.rs:21-23, preflight.rs:384-399 |
| **Octocode** | context.md with repo structure, PR scope, cross-cutting concerns | Without context: reviews miss architectural patterns. Without scope limits: reviews expand to unbounded scope (>500 lines→split rule exists because this happened). | research:237-259, plan:149 |
| **Gastown** | Molecule step definitions, delegation terms, escalation routing | Without molecule: no DAG, no progress tracking, no tier hints. Without delegation terms: polecats default to maximum autonomy (unsafe). Without escalation routing: issues go unhandled → stale_threshold auto-bumps severity. | molecule.go:55-66, escalation.md:28-36, escalation-system.md:67-68 |

**Unique pattern — Gastown role taxonomy:** Gastown structurally encodes autonomy boundaries through roles (polecats never ask humans, crew always human-facing). This prevents the "ask/don't-ask" decision from being a runtime judgment — it's baked into the role assignment.

**Unique pattern — BMAD "context engine":** BMAD's create-story step is explicitly described as a "context engine" — its purpose is to generate enough context that the dev agent cannot fail due to missing information. This is front-loading as explicit design goal, not implicit workflow benefit.

---

### Question Group 3 Responses

#### Q1: Why has your framework chosen that way of doing it? What problem was it solving?

**Cross-Framework Design Motivation Mapping:**

| Framework | Core Problem Solved | Design Response | Key Citation |
|---|---|---|---|
| **BMAD** | Multi-agent consistency — agents make conflicting technical decisions without shared architectural guidance | 4-phase sequential pipeline (Analysis→Planning→Solutioning→Implementation) with progressive document chain; facilitator pattern (agents guide, not generate) | why-solutioning-matters.md:11-17, step-01-init.md:23 |
| **SAM** | 6 documented LLM failure modes — long-context degradation, training data staleness, miscalibrated confidence, completion optimization, unreliable uncertainty, goal displacement | Stateless agents + externalized memory + RT-ICA gate + deterministic backpressure + embedded methodology + independent forensic review. "Behavioral instructions cannot override architectural limitations" | stateless-software-engineering-framework.md:43-51, :108 |
| **GSD** | AI quality degradation under context pressure — quality drops sharply above 50% context utilization | Plans-as-prompts with 2-3 tasks/plan limit, fresh 200k context per subagent; wave-based parallel execution; 4-tier deviation rules for auto-fix; goal-backward verification | gsd-planner.md:74-83, gsd-executor.md:83-139 |
| **Ralph** | Context pollution in long-running loops + brittleness of prescriptive workflows + infinite loops on impossible tasks | Fresh context per iteration (Tenet #1); backpressure over prescription (Tenet #2); hat-based adversarial topology; hardcoded thrashing thresholds (3 blocks = abandon) | AGENTS.md:73-85, mod.rs:447, :1917 |
| **Octocode** | Guess-driven development + shared blind spots in single-model self-review + latency-quality tradeoff | Research-Driven Development (RDD); GAN-inspired adversarial flow (Generator vs Discriminator); Fast-Path/Deep-Research split; Triple Lock enforcement (STATE+FORBIDDEN+REQUIRED) | MANIFEST.md:16, :39-40, :42-48 |
| **Gastown** | Daemon can't reason (Go code following ZFC) + context debt from long sessions + agents skip steps/hallucinate completion | Three-tier watchdog chain (Daemon→Boot→Deacon); ZFC (Zero Decisions in Code); molecule DAG with per-step closure; ephemeral polecats with persistent identity via beads | watchdog-chain.md:26-35, stuck.go:17, witness.md.tmpl:236-237 |

**Convergence pattern — "structural over behavioral":** SAM states it explicitly ("behavioral instructions cannot override architectural limitations"), but all 6 frameworks converge on this principle through their designs. BMAD enforces via document chain. GSD enforces via context budget. Ralph enforces via backpressure gates. Octocode enforces via adversarial flow. Gastown enforces via ZFC (Go code never decides, AI agents decide). The shared insight: telling the AI "please do X" is unreliable; structuring the pipeline so X is the only possible path is reliable.

**Unique contribution — SAM Assumptions & Evidence Ledger:** SAM includes Appendix D (stateless-software-engineering-framework.md:976-1012) with 26 entries classifying each claim as EMPIRICAL/DESIGN CHOICE/TERMINOLOGY and rating evidence quality YES/NO/PARTIAL. No other framework self-audits its own claims.

**Unique contribution — GSD context budget as engineering constraint:** GSD is the only framework that treats context window utilization as a measurable, threshold-gated resource (peak quality at 0-30%, degrading at 50-70%, poor at 70%+). All other frameworks manage context implicitly.

---

#### Q2: Is that way the only way, or is it conditional? Under what conditions does the framework do X vs Y?

**Cross-Framework Branching Point Inventory:**

| Framework | Branching Points | Key Conditional | Most Distinctive Branch |
|---|---|---|---|
| **BMAD** | 7 branches | Quick Flow vs BMad Method vs Enterprise (story count heuristic) | YOLO mode — user can skip all confirmations (workflow.xml:107-109) |
| **SAM** | 5 branches | RT-ICA APPROVED vs BLOCKED (any MISSING = block) | Pipeline is predominantly linear — complexity affects artifact depth, not structure |
| **GSD** | 9 branches | Discovery level 0-3, TDD vs Standard plans, workflow toggles | Context budget as hard splitting criterion (5+ tasks/plan = blocker) |
| **Ralph** | 6 branches | Solo vs Multi-hat (registry.is_empty()), backpressure pass/reject | Persistent mode — completion suppressed, loop runs indefinitely (mod.rs:484-504) |
| **Octocode** | 8 branches | Fast-Path 4 criteria (all must pass), confidence HIGH/MED/LOW | Writer scaling by question count (<20/20-99/100+) |
| **Gastown** | 7 branches | Boot Decision Matrix (5-way: session state × heartbeat × mail × activity) | Staleness re-escalation with max cap (escalate_impl.go:326-349) |

**Total branching points across all frameworks: 42.**

**Pattern — pipeline fixity vs routing flexibility:** SAM and BMAD have fixed pipelines (same stages for every task, varying only in depth). GSD and Ralph have configurable pipelines (toggles, presets, modes). Octocode has conditional density (fast-path skips stages entirely). Gastown has structural routing (formula type determines execution topology). These represent a spectrum from "always the same pipeline" to "the pipeline itself is selected."

---

#### Q3: How are those conditions detected? What triggers the framework to take one path vs another?

**Cross-Framework Detection Mechanism Taxonomy:**

| Detection Type | Definition | Frameworks Using It | Examples |
|---|---|---|---|
| **Numeric threshold** | Comparison against hardcoded or configured number | GSD (tasks/plan ≤3, context ≤50%), Ralph (coverage ≥80%, thrashing ≥3), Octocode (files ≤5, lines >500) | gsd-plan-checker.md:196-207, event_parser.rs:161-163, PR-reviewer:46-50 |
| **Config/flag-based** | Boolean or enum set before execution | Ralph (persistent, robot.enabled), GSD (workflow toggles), Gastown (formula type from TOML structure) | config.rs:603, settings.md:56-74, parser.go:37-53 |
| **File/structure existence** | Presence of file, field, or section | GSD (checkpoint grep), Gastown (TOML section presence, bead label parsing), BMAD (tech-spec file path) | gsd-executor.md:52-54, parser.go:38-53, step-01-mode-detection.md:47-52 |
| **AI semantic judgment** | LLM classifies based on instructions | Octocode (6/8 branches), BMAD (escalation signals, scope classification), SAM (RT-ICA, complexity), GSD (discovery level, deviation rules) | research/SKILL.md:242-247, step-01-mode-detection.md:67-81, ssf:373-378, gsd-planner.md:120-124 |
| **Human declaration** | Human explicitly states choice | BMAD (track selection, YOLO), Ralph (preset selection), Octocode (interactive vs auto), Gastown (formula selection, escalation severity) | module.yaml:17-29, workflow.xml:89, plan/SKILL.md:137, escalation.md:42-73 |
| **Binary outcome** | Did the action succeed or fail? | SAM (execution COMPLETE vs BLOCKED), Ralph (backpressure evidence parsing) | ssf:610, mod.rs:1785-1892 |
| **Time-based** | Duration exceeds threshold | Gastown (heartbeat age, staleness threshold 4h, shutdown dance timeouts 60→120→240s) | watchdog-chain.md:95-105, escalation-system.md:66-69, dog-pool-architecture.md:262-266 |
| **Content-based parsing** | Structured field extraction from agent output | Ralph (BackpressureEvidence fields, Confessor confidence 0-100), Gastown (polecat exit status string enum) | event_parser.rs:95-128, handlers.go:56 |

**Key finding — AI judgment dominance:** Across all 42 branching points, the majority rely on AI semantic judgment rather than machine-verifiable conditions. Octocode: 6/8 branches use AI judgment. BMAD: 4/7. SAM: 3/5. GSD: 3/9 (GSD has the highest ratio of machine-verifiable branches due to numeric thresholds on context budget and task counts). Ralph: 1/6 (most branches are config or threshold-based). Gastown: 1/7 (most are structural/time-based).

**Implication for ARL:** If the ARL aims to replace human gates with machine-verifiable conditions, the existing frameworks show that most current "conditional" logic is actually AI judgment disguised as conditions. Converting these to machine-verifiable conditions is the core challenge.

---

#### Q4: What makes a task hit complexity or bounded/unbounded checkpoints?

**Cross-Framework Complexity Classification Comparison:**

| Framework | Has Formal Classification? | Dimensions | Thresholds | Effect on Pipeline |
|---|---|---|---|---|
| **BMAD** | No — advisory only | Story count (1-15/10-50/30+), escalation signals (5 indicators), change scope (Minor/Moderate/Major) | 2+ signals → escalation; story counts are "guidance, not definitions" | Routes to track (Quick/BMad/Enterprise) but no hard gate |
| **SAM** | Partial — in research docs only | Scope clarity (High/Med/Low), goal measurability, data enumeration, module count, interface type | None formalized — agent classifies | Affects artifact depth, not pipeline structure |
| **GSD** | Yes — numeric thresholds | Tasks/plan (2-3 target), files/plan (5-8 target), context budget (50% target), task duration (15-60 min) | 5+ tasks = blocker, 15+ files = blocker, 80%+ context = blocker | Hard gate — plans exceeding thresholds are rejected by plan-checker |
| **Ralph** | No — uniform treatment | None | Uniform: 50 iterations, 3600s, coverage ≥80%, mutation ≥70%, complexity ≤10 for ALL tasks | No variation — preset selection is human-driven |
| **Octocode** | Partial — multi-system | 5 classification systems: research (4 binary), plan (3-level), PR (file count + risk), prompt (4 dimensions), doc scaling (question count) | File count ≤5, lines >500, questions <20/20-99/100+ | Routes to fast-path vs full-path; affects review depth |
| **Gastown** | No — human decides | None | Tier hints (haiku/sonnet/opus) are advisory, not gating | Formula selection is human-driven; ZFC principle delegates classification to AI/human |

**What NO framework has:**

- **R2 (Loop detection):** Only Ralph has thrashing detection (count-based, 3 blocks = abandon). No framework detects output-similarity loops (fix A breaks B, fix B breaks A). GSD has bounded planning iterations (max 3) but unbounded gap closure.
- **R7 (Convergence tracking):** No framework tracks finding-count-per-iteration as a convergence metric. GSD's re-verification tracks score delta (previous_score → score) but doesn't classify convergence/oscillation/stall. Ralph's fresh-context-per-iteration design explicitly trades away convergence tracking.
- **R8 (Proportionality):** No framework compares finding severity against proposed change scope. GSD's scope sanity thresholds (tasks/plan, files/plan) are the closest — but they measure plan size, not proportionality relative to the finding. BMAD's change scope classification (Minor/Moderate/Major) routes to different teams, not to proportionality assessment.
- **R10 (Split justification):** No framework validates that a split produces independently viable units. GSD splits plans by context budget and file ownership. Octocode flags PRs >500 lines for splitting. BMAD decomposes into epics/stories. But none check whether the resulting pieces are independently useful.

**The gap is universal:** All 6 frameworks lack the four R-requirements (R2, R7, R8, R10) that would enable autonomous loop operation without human judgment on these dimensions. This is the core finding of Question Group 3.

---

#### Q3 Cross-Examination Records

- **octocode-expert → gsd-expert:** Cross-examined on detection mechanisms, loop detection triggers, convergence measurement.
- **sam-expert → ralph-expert:** Cross-examined on event topology rationale and complexity thresholds.
- **ralph-expert → gastown-expert:** Cross-examined on complexity classification and ZFC implications.
- **gsd-expert → octocode-expert:** Cross-examined on conditional branching and detection mechanisms.
- **bmad-expert → gastown-expert:** Cross-examined on intent alignment, drift detection, molecule step completion.
- **gastown-expert → bmad-expert:** Cross-examined on proportionality, independent viability, verifiability.

---

### Question Group 4 Responses

#### Q1: How is alignment between human intent and agent behavior tracked?

**Cross-Framework Intent Tracking Comparison:**

| Framework | Intent Capture | Intent Storage | Alignment Checking | Gap |
|---|---|---|---|---|
| **BMAD** | 4-stage progressive chain: Product Brief → PRD FRs → Story ACs → Implementation | Documents at each stage | Local only — each stage checks against previous stage, never against original brief | No global alignment check (story becomes sole authority, disconnected from product brief) |
| **SAM** | Stage 1 Discovery artifact: problem, goals, anti-goals, FRs, NFRs | Discovery artifact file | Stage 7 Final Verification compares against Discovery; Stage 6 Forensic Review compares against task-level criteria only | 5 transformation stages between capture and final check with no intermediate alignment verification |
| **GSD** | 4-layer chain: PROJECT.md → ROADMAP.md phase goals → CONTEXT.md locked decisions → must_haves | Files at each layer | Plan-checker context compliance (pre-execution), goal-backward verification (post-execution), milestone audit (post-milestone) | No comparison between iteration 0 intent and iteration N state; no continuous monitoring |
| **Ralph** | Single capture: objective stored verbatim | Injected into every iteration prompt (bookend pattern) | None — objective is broadcast but no mechanism checks work relevance | Backpressure validates quality (tests pass) but not relevance (right thing built) |
| **Octocode** | mainResearchGoal parameter + context.md + plan approval gate | mainResearchGoal in every tool call; context.md file | Plan approval gate (human checkpoint); self-check "On track?" after each tool call | No continuous alignment metric; "On track?" is AI self-assessment with no criteria |
| **Gastown** | Issue bead + DelegationTerms (AcceptanceCriteria field) + molecule step sequence | Bead in Dolt (persistent); DelegationTerms as JSON slot | Self-review step checks file scope via git diff; molecule forces verification steps structurally | AcceptanceCriteria field is optional; self-review checks file scope, not semantic scope |

**Universal finding:** No framework tracks alignment as a computed metric. All rely on either human observation at checkpoints or LLM self-assessment. The gap between "intent was captured" and "work matches intent" is bridged by trust, not measurement.

---

#### Q2: How is drift detected? What constitutes drift vs acceptable evolution?

**Cross-Framework Drift Detection:**

| Framework | Drift Detection Mechanism | Drift vs Evolution Distinction | Citation |
|---|---|---|---|
| **BMAD** | Scope creep conversational challenges during planning; quick-dev escalation signals during execution; correct-course workflow for formal change management | No formal distinction — all changes flow through correct-course which classifies CAUSE (technical limitation, new requirement, etc.) but not DESIRABILITY | step-03-success.md:122, step-01-mode-detection.md:67-81, correct-course/instructions.md:14-15 |
| **SAM** | None implemented. Research docs acknowledge drift as known failure mode. Single-task scoping is structural prevention. | No distinction. Research doc notes "successive rewrites can shift a skill away from original intent without any single change being obviously wrong" | ssf:92, human-out-of-loop:110, :329 |
| **GSD** | Plan-checker context compliance (detects contradiction with locked decisions); deviation rules during execution (Rules 1-3 = acceptable, Rule 4 = stop) | Yes — explicit at execution level: Rules 1-3 = acceptable evolution (bugs, security, blocking), Rule 4 = unacceptable drift (architectural) | gsd-plan-checker.md:251-293, gsd-executor.md:83-139 |
| **Ralph** | None. Backpressure validates quality, not relevance. Agent could refactor entire build system while objective says "fix typo." | No distinction. Scratchpad captures evolving interpretation but no boundary between "refining approach" and "drifting from objective." | mod.rs:1785-1892 |
| **Octocode** | mainResearchGoal reference in hints provides drift prevention (not detection). Plan-step enforcement prevents improvisation during execution. | No distinction. No formal definition of drift exists in the codebase. | research/SKILL.md:628-629, plan/SKILL.md:256 |
| **Gastown** | Self-review file-scope check (git diff); "discovered work" pattern files new beads for out-of-scope items. | Procedural distinction: discovered work → new bead (evolution); undiscovered drift in same files → undetected. No "this issue evolved" path — only "done" and "new issue." | mol-polecat-work.formula.toml:226-232, :271-277 |

**Universal finding:** Drift detection is universally absent as a programmatic capability. GSD comes closest with its 4-tier deviation rules that explicitly distinguish acceptable (Rules 1-3) from unacceptable (Rule 4) changes — but only at execution time, not across iterations. No framework detects gradual semantic drift where small individually-acceptable changes cumulatively shift purpose.

---

#### Q3: How is definition of done validated?

**Cross-Framework Definition of Done — Machine-Checkable vs Judgment-Dependent:**

| Framework | Machine-Checkable | Judgment-Dependent | Who Validates | Key Gap |
|---|---|---|---|---|
| **BMAD** | 8/21 checklist items: task completion flags, test coverage %, linter pass, HALT conditions, story/sprint status | 10/21 items: architecture compliance, AC satisfaction, ambiguity, edge cases, integration tests, documentation quality | Self-assessment by dev agent + adversarial code review (independent evaluator) | Adversarial review creates second evaluation but both are LLM-assessed |
| **SAM** | Task self-verification (if deterministic backpressure items), all-tasks-complete status, all-reviews-pass status | Quality scoring (1-5 per dimension), goal achievement judgment, CERTIFIED/NOT_CERTIFIED verdict | Execution Agent (self-verify) → Forensic Review (independent) → Final Verification (independent) | No formula for CERTIFIED — agent judgment determines final verdict |
| **GSD** | 3-level artifact checks (exists/substantive/wired), anti-pattern grep, test pass/fail | Visual appearance, UX flows, real-time behavior, complex wiring, edge cases → UNCERTAIN status | gsd-executor (self-check) → gsd-verifier (independent automated) → human (for UNCERTAIN items) | UNCERTAIN status handles "clear but uncheckable" but not "ambiguous criteria" |
| **Ralph** | Completion promise token (string match), task store query, backpressure gates per-iteration (coverage ≥80%, mutation ≥70%, complexity ≤10) | Confessor confidence (0-100 self-reported), objective satisfaction (agent decides to emit promise) | Agent self-validates → Confessor (independent but same-model) → human (via robot check-ins, if enabled) | Task completeness check is informational, not blocking — agent can emit promise with tasks open |
| **Octocode** | ~8 items: build/test/lint pass, file:line presence, count checks | ~12 items: goal achieved, confidence level, no duplicates, intent preserved, quality score (0-100 by AI QA) | Skill-specific: plan has human gate, research has 4 completion triggers, PR review has confidence self-assessment | Documentation QA score is numeric but AI-produced — judgment disguised as metric |
| **Gastown** | Tests pass, branch merges cleanly, workspace clean, commit on main verified | "Did this solve the issue?" — not validated by any automated pipeline stage | Polecat (self-review) → Witness (lifecycle validation) → Refinery (merge validation) → human (semantic validation) | Nobody in the automated pipeline validates semantic correctness |

**Universal finding:** All frameworks have machine-checkable gates for code quality (tests, lint, build) but none have machine-checkable gates for semantic correctness (did we build the right thing?). The "right thing" judgment is always deferred to humans or LLM self-assessment.

---

#### Q4: When definition of done is ambiguous, how do frameworks handle it?

**Cross-Framework Ambiguity Handling:**

| Framework | Proactive (before work) | Reactive (during work) | Ambiguity Detection | Key Pattern |
|---|---|---|---|---|
| **BMAD** | SMART validation scores ambiguity 1-5 per dimension; PRD polish checks for contradictions; story checklist flags vague instructions | HALT on unclear requirements during implementation; correct-course for discovered issues | LLM-evaluated — agent assigns SMART scores, no machine verification of score accuracy | Multi-phase forced clarification (most proactive of all frameworks) |
| **SAM** | RT-ICA blocks on MISSING prerequisites | No reactive mechanism — no AMBIGUOUS status in vocabulary (only AVAILABLE/DERIVABLE/MISSING) | None — ambiguous-but-present criteria classified as AVAILABLE | Front-loads but can't detect "present but unclear" |
| **GSD** | discuss-phase gray area resolution; plan-checker flags vague tasks ("implement auth" rejected) | UNCERTAIN verification status routes to human | Plan-checker detects vague PLANS but not vague GOALS | Catches ambiguous plans, misses ambiguous objectives |
| **Ralph** | None — objective stored verbatim without validation; preflight checks spec completeness but not objective clarity | human.interact (agent-initiated, agent must realize ambiguity) | Confessor low confidence as indirect signal (but doesn't distinguish ambiguity from incorrectness) | Propagates ambiguity silently; agent fills gaps via interpretation |
| **Octocode** | STOP-and-ask for unknowns; assumptions-with-consequences documentation | [INCOMPLETE] marker for stuck research; "Did I change any original intent?" self-check | AI self-assessment — agent must recognize ambiguity | Distinguishes assumptions (proceed) from unknowns (block) |
| **Gastown** | None at creation time — issue bead stored as-is | Polecat escalates "unclear requirements" to Witness; Witness auto-escalates to Mayor via substring match; ESCALATED exit status | Programmatic: `strings.Contains(problem, "unclear")` in witness/protocol.go:397-403 | ZFC principle: ambiguity is a judgment call → route upward (Polecat→Witness→Mayor→Human) |

**Spectrum of ambiguity handling:** BMAD (most proactive — multi-phase scoring and forced clarification) → GSD (proactive for plans, reactive for goals) → Octocode (assumptions vs unknowns distinction) → SAM (blocks on MISSING but can't detect "present but unclear") → Gastown (escalates when detected but doesn't proactively detect) → Ralph (propagates silently).

**Universal gap — content-loss detection (R6):** No framework implements content-loss detection. BMAD's code review checks AC implementation status (IMPLEMENTED/PARTIAL/MISSING) but not whether content was removed during refactoring. GSD's verifier checks "does the goal hold?" not "was anything removed." Octocode's prompt optimizer checks "Did I change any original intent?" but via AI self-assessment. This is the least-addressed R-requirement across all frameworks.

---

#### Q4 Cross-Examination Records

- **octocode-expert → bmad-expert:** Cross-examined on content-loss, drift vs evolution, definition of done.
- **sam-expert → gsd-expert:** Cross-examined on incremental vs deferred alignment checking; 6 intent layers with no cross-checking.
- **ralph-expert → sam-expert:** Cross-examined on stateless alignment, pipeline done-ness, RT-ICA ambiguity.
- **gsd-expert → ralph-expert:** Cross-examined on definition of done ambiguity handling.
- **bmad-expert → gastown-expert:** Cross-examined on intent alignment, drift detection, molecule step completion.
- **gastown-expert → sam-expert:** Cross-examined on proportionality, convergence detection, split justification.

---

### Question Group 5 Responses

#### Q1: Multi-agent patterns and human oversight

**Cross-Framework Multi-Agent Pattern Inventory:**

| Framework | Pattern Type | Agent Count | Parallelism | Human Oversight Effect | Key Citation |
|---|---|---|---|---|---|
| **BMAD** | Persona switching (party mode) + sequential workflow binding | 8+ personas, single LLM | None — single context | INCREASES human involvement (party mode is collaborative discussion WITH human) | workflow.md:90-97, dev.agent.yaml:32-38 |
| **SAM** | Sequential specialist pipeline + documented swarm patterns | 7 pipeline roles + parallel specialists (documented) | Documented but not primary (EXEC:SEQUENTIAL/PARALLEL/WAVE tokens) | Front-loads human to single Discovery gate; pipeline runs autonomously after | ssf:249-278, :1128-1155, :184 |
| **GSD** | Pipeline + wave-parallel execution + parallel diagnostic swarm | Orchestrator + N specialist agents per wave | True parallelism within waves; parallel debug agents | Human sees compressed wave summaries; diagnosis runs fully autonomous | execute-phase.md:74-75, diagnose-issues.md:87-88 |
| **Ralph** | Hat-based persona switching + worktree parallelism | 3 hats (single LLM) + N parallel loops (separate processes) | Hat system sequential; worktree loops truly parallel | Merge queue introduces human gate for parallel loop outputs | ralph.yml:13-118, worktree.rs:1-80, loop_registry.rs:1-80 |
| **Octocode** | GAN adversarial flow + parallel domain agents + parallel research/roast | Generator+Discriminator pairs + 1-8 parallel writers + parallel per-domain agents | True parallelism for writers and domain agents | Adversarial flow reduces human checkpoints; parallel output merged before human sees it | MANIFEST.md:39-40, doc-writer:50-56, plan:311-328 |
| **Gastown** | Role-based hierarchy + watchdog chain + convoy parallelism + aspect weaving | 6 role types (Mayor/Deacon/Witness/Refinery/Polecat/Crew) | Convoy formula spawns parallel polecats; redundant convoy observers | Compresses human oversight to strategic decisions (Mayor) and escalation resolution | architecture.md:62-80, watchdog-chain.md:7, design.formula.toml:1-5 |

**Convergence pattern — persona switching vs true multi-agent:** BMAD and Ralph use persona switching (single LLM, different prompts). GSD, Octocode, and Gastown use true multi-agent (separate processes/contexts). SAM documents both but primarily uses sequential pipeline. The distinction matters for ARL: persona switching shares blind spots (same model weights); true multi-agent provides independence but requires coordination infrastructure.

**Convergence pattern — orchestrator compression:** All frameworks with true multi-agent patterns (GSD, Octocode, Gastown) compress parallel agent outputs before presenting to human. GSD's orchestrator reads SUMMARY.md files and presents one-liners. Octocode's merge step combines parallel outputs. Gastown's patrol digest aggregates cycles into daily summaries. The orchestrator IS the compression layer.

---

#### Q2: Where could parallel teammates replace sequential human checks?

**Cross-Framework Parallelization Opportunity Inventory:**

| Framework | Sequential Gate | Current Bottleneck | Parallel Alternative | Independence Basis |
|---|---|---|---|---|
| **BMAD** | PRD validation (13 steps) | Single agent checks 12 dimensions sequentially | Parallel agents check independent dimensions (density, measurability, traceability, SMART, etc.) simultaneously | Each dimension checks different aspect of same document — no interdependency |
| **BMAD** | Implementation readiness (6 steps) | Steps 02, 04, 05 run sequentially despite independence | Steps 02 (PRD analysis), 04 (UX alignment), 05 (epic quality) run in parallel | Different document sources, different evaluation criteria |
| **SAM** | Forensic Review (per-task sequential) | Execute Task 1 → Review 1 → Execute Task 2 → Review 2 | Parallel review agents review completed tasks simultaneously | Each review takes independent inputs (execution artifact + task spec) |
| **SAM** | Final Verification (monolithic) | Single agent checks goals + ACs + DoD in one pass | Parallel specialists (goal checker, AC verifier, integration verifier, doc verifier) | Each checks different dimension against different source |
| **GSD** | Post-execution verification | One verifier per phase, sequential | One verification agent per plan within a phase | Each plan's SUMMARY.md lists specific files — independent verification scopes |
| **GSD** | Plan-checking | Single checker evaluates all dimensions of all plans | Per-plan checkers for Dimensions 1-5 + cross-plan checker for Dimensions 4,7 | Dimensions 1-2 (coverage, completeness) and 5 (scope) are per-plan |
| **Ralph** | Builder → Confessor → Handler | Sequential LLM audit chain; entire loop blocks on human.interact | Parallel quality dimension agents (tests, lint, security, architecture) | Each dimension uses independent tool output |
| **Octocode** | Plan approval | Human reads plan → approves/rejects | Multiple verifier agents check feasibility, evidence, scope simultaneously; human gets pre-digested signals | Different evaluation criteria, same input document |
| **Octocode** | PR review checkpoint | Human must review TL;DR before deep analysis begins | Begin parallel domain analysis while human reviews TL;DR; deprioritize non-focus areas after human responds | Domain analyses are independent of human focus decision |
| **Gastown** | Self-review → run-tests | Sequential despite both being read-only on same git state | Parallel: one agent reviews diff, another runs tests | Both read same git state, neither modifies it; types.go:96 supports Parallel flag |
| **Gastown** | Escalation acknowledgment chain | Polecat → Deacon → Mayor → Overseer, 4h stale threshold per tier | Parallel triage: historical pattern check + resource availability check + auto-resolution check simultaneously | Each check queries different data source |
| **Gastown** | Refinery sequential merge queue | One MR at a time, conflict resolution serialized | Parallel verification for non-conflicting MRs (different file sets) | Non-conflicting MRs touch different files — independent verification |

**Universal pattern:** All frameworks have sequential gates where the serialization is an artifact of single-agent execution, not logical dependency. The independence basis in each case is that the checks operate on different dimensions or different data sources with no interdependency.

**Key finding for ARL:** The most common parallelizable gate type is "multiple independent quality dimensions checked sequentially by one agent." This maps directly to the parallel specialist swarm pattern (SAM ssf:1134): spawn N focused reviewers, each produces bounded artifact, leader synthesizes.

---

#### Q3: Cross-examination and adversarial patterns between agents

**Cross-Framework Adversarial Pattern Comparison:**

| Framework | Pattern | Adversarial Strength | Direction | What It Catches | What It Misses | Key Citation |
|---|---|---|---|---|---|---|
| **Octocode** | Generator-Discriminator (GAN-inspired) | Strong — Verifier explicitly tries to find flaws; "zero-sum game" framing | Bidirectional across iterations (Generator revises based on Discriminator feedback) | Structural gaps, evidence gaps, plan-code inconsistency | Shared blind spots when same model (mitigated by cross-model validation design) | MANIFEST.md:117-120, :122-125 |
| **BMAD** | Adversarial code review | Strong — "Find 3-10 specific issues minimum"; halt on zero findings (suspicious) | Unidirectional (reviewer → dev agent work) | Story claims vs git reality; false completion claims; missing implementations | Same-model evaluation; no dispute mechanism for false positives from reviewer | code-review/instructions.xml:7-14, review-adversarial-general.xml:38,44 |
| **Ralph** | Confessor + Handler chain | Medium — Confessor instructed "rewarded for surfacing problems"; Handler spot-checks Confessor | Two-layer unidirectional (Builder → Confessor → Handler) | Builder shortcuts/uncertainties; Confessor fabrications (Handler escalates if Confessor untrustworthy) | All same model; Handler trusts own spot-check without external verification | ralph.yml:61-63, :100-112 |
| **GSD** | Plan-checker validates planner; Verifier validates executor | Medium — explicit skepticism instructions ("DO NOT trust SUMMARY claims") | Unidirectional (downstream validates upstream) | Vague tasks, scope violations, false completion claims | No dispute mechanism — planner accepts all checker findings; no validity filtering of checker output | gsd-plan-checker.md:56-61, gsd-verifier.md:440 |
| **SAM** | Forensic Review (independent verifier) | Weak-medium — independent but not adversarial (checks correctness, doesn't hunt problems) | Unidirectional (Forensic Review → Execution Agent) | Incorrect claims, missing criteria | Not incentivized to find problems; no adversarial mandate; SAM warns multi-agent "amplifies coordination complexity" | ssf:640-709, :856, :1070 |
| **Gastown** | Witness zombie detection; HandleMerged commit verification | Structural — cross-references agent claims against independent truth source | Unidirectional (Witness → Polecat state, Witness → Refinery claims) | Dead agents claiming alive; false merge signals | Only checks liveness and lifecycle, not semantic correctness | mol-witness-patrol, witness/handlers.go:282-296 |

**Key finding — no framework implements bidirectional cross-examination:** All adversarial patterns are unidirectional (reviewer validates producer). No framework supports the producer disputing a reviewer finding. This means false positives from reviewers propagate unchallenged. Octocode's revision loop is the closest — the Generator revises based on Discriminator feedback — but the Generator revises rather than disputes.

**Key finding — adversarial strength spectrum:** From weakest to strongest: SAM (independent but not adversarial) → Gastown (structural cross-reference against truth source) → GSD (skepticism-instructed, no dispute) → Ralph (inverted reward framing, two-layer) → BMAD (forced minimum findings, halt on zero) → Octocode (GAN-inspired zero-sum, cross-model design). The spectrum ranges from "check if correct" to "actively try to break."

**Implication for R3 (Validity filtering):** Cross-examination between parallel teammates could address the universal gap: a reviewer agent's findings could be challenged by a second agent before being acted upon. Currently, no framework filters the reviewer's own false positives.

---

#### Q4: Lead agent escalation and context compression for humans

**Cross-Framework Escalation Compression Comparison:**

| Framework | Compression Layers | Quick-Scan Signal | Detail Layer | Action Layer | Cross-Source Aggregation | Key Citation |
|---|---|---|---|---|---|---|
| **GSD** | 5 patterns | Wave completion table; plan-checker severity counts; verification score (N/M); diagnosis table; milestone YAML scores | SUMMARY.md per plan; VERIFICATION.md per phase; debug session per gap | Next command to run; fix hints per issue; gap-closure routing | Yes — milestone audit aggregates phase verifications + integration checker | execute-phase.md:206-226, plan-checker.md:550-579, diagnose-issues.md:165-186 |
| **Octocode** | 5 patterns | TL;DR (few sentences); [INCOMPLETE] marker; risk level (HIGH/MED/LOW); damage report (2 CAPITAL, 3 FELONIES...); QA score (0-100) | Full analysis with evidence; per-finding breakdown; QA-SUMMARY.md | "Next Step" (required question); redemption options; focus request | No — each skill compresses independently; no cross-skill aggregation | research:568-575, roast:134, doc-writer:492-494 |
| **Gastown** | 5 layers | HasAlerts boolean; severity routing (low→bead only, critical→SMS); patrol digest counts | EscalationFields struct (14 fields); decision pattern with options table | Resolution instructions; severity-routed channels | Partial — patrol digest aggregates cycles into daily summary; dashboard aggregates system state | beads_escalation.go:13-30, escalation.md:138-159, cmd/patrol.go:31-55, web/handler.go:254-309 |
| **SAM** | 2 patterns | Verdict (COMPLETE/NEEDS_WORK); Status (CERTIFIED/NOT_CERTIFIED) | Completion/Quality/Fact-Check tables with evidence; Goal/AC/DoD tables | Issues Found numbered list; Follow-up Tasks checklist | No — each artifact self-contained; no cross-review aggregation; acknowledges gap (references Gastown wisps) | ssf:675-707, :772-797, :1109 |
| **BMAD** | 2 tiers | Code review severity counts; retrospective metrics (velocity, quality, business) | Per-story review findings with categories; cross-story pattern synthesis (retrospective only) | Fix options (auto-fix/action items/details); retrospective action items with owners | Only at retrospective (epic boundary) — no mid-epic cross-story aggregation | code-review/instructions.xml:112-147, retrospective/instructions.md:445-533 |
| **Ralph** | 3 channels | Check-in: 4 scalars (iteration, time, hat, cost); handoff: structured sections | human.interact: raw agent text (no compression); handoff.md: git context + tasks + key files | Continuation prompt (handoff only) | No — Confessor reasoning not compressed for human; escalate.human sends raw text | mod.rs:1407-1431, :1958-2050, handoff.rs:87-114 |

**Compression depth spectrum:** GSD (deepest — 5 patterns with cross-source aggregation, orchestrator compression by design) → Gastown (5 layers with severity routing and dashboard aggregation) → Octocode (5 patterns but no cross-skill aggregation) → BMAD (2 tiers, retrospective-only aggregation) → SAM (2 patterns, self-contained artifacts) → Ralph (3 channels, no compression on escalation path).

**Key finding — orchestrator as compression forcing function:** GSD's orchestrator operates at 10-15% context (execute-phase.md:322), which FORCES compression — it cannot hold raw agent outputs. This is compression by architectural constraint, not by instruction. Gastown's dashboard (web/handler.go) similarly compresses by design — it renders a fixed struct, not variable-length output. Frameworks without context pressure (BMAD single-context, Ralph single-agent) have less compression because there's no architectural need for it.

**Key finding — escalation compression gap:** All frameworks compress SUCCESS paths well (structured reports, scores, tables). FAILURE paths are less compressed: Ralph sends raw text on escalate.human; SAM has no severity classification; BMAD has no mid-epic pattern detection. The human gets the most information when things go WRONG — which is when they most need compression.

**Implication for R9 (Downstream impact):** A lead agent synthesis pattern — reading multiple parallel agents' outputs and producing a single compressed escalation — exists only partially in GSD (milestone audit) and Gastown (patrol digest). No framework has real-time cross-source escalation synthesis.

---

#### Q5 Cross-Examination Records

- **sam-expert → bmad-expert:** Cross-examined on transformation chain alignment (5 transforms BMAD vs 4 SAM).
- **sam-expert → gastown-expert:** Cross-examined on convoy verification scope and escalation format.
- **octocode-expert → ralph-expert:** Cross-examined on adversarial vs confirmatory validation, cross-agent flow, escalation compression.
- **gastown-expert → ralph-expert:** Cross-examined on multi-agent coordination and escalation compression.
- **gastown-expert → sam-expert:** Cross-examined on convoy scope, escalation format, sequential dependencies.
- **gsd-expert → bmad-expert:** Cross-examined on drift handling and DoD failure mode conflation.
- **gsd-expert → octocode-expert:** Cross-examined on bidirectional agent validation and dispute mechanisms.

---

### Phase 1 Summary

**Phase 1 Discussion complete.** All 5 question groups discussed by all 6 experts. All 10 R-requirements addressed across the question groups:

| R-Requirement | Primary Question Groups | Key Finding |
|---|---|---|
| R1 (RT-ICA / front-loading) | Q1, Q2 | SAM deepest (4 stages); all frameworks front-load but none detect when front-loading proves insufficient at runtime |
| R2 (Loop detection) | Q3, Q5 | Only Ralph has thrashing detection (count-based). No framework detects output-similarity loops. Multi-agent monitoring could address this. |
| R3 (Validity filtering) | Q1, Q5 | No framework filters reviewer false positives. Cross-examination between parallel agents could address. Adversarial strength varies from "check correctness" (SAM) to "actively break" (Octocode GAN). |
| R4 (Plan quality gates) | Q1, Q5 | GSD plan-checker is the most structured. Parallel quality dimension checking could replace sequential single-agent review. |
| R5 (Purpose anchor) | Q1, Q2, Q4 | No framework tracks alignment as computed metric. All rely on human observation or LLM self-assessment. |
| R6 (Content-loss detection) | Q4 | Least-addressed requirement. No framework diffs before/after to detect silent removal. |
| R7 (Convergence tracking) | Q3 | No framework tracks finding-count-per-iteration. GSD's re-verification tracks score delta but doesn't classify convergence/oscillation/stall. |
| R8 (Proportionality) | Q3 | No framework compares finding severity against proposed change scope. GSD scope thresholds are closest but measure plan size, not proportionality. |
| R9 (Downstream impact) | Q5 | GSD milestone audit and Gastown patrol digest are closest to cross-source synthesis. No framework has real-time cross-source escalation synthesis. |
| R10 (Split justification) | Q3 | No framework validates that splits produce independently viable units. |

**Transition to Phase 2: R1-R10 Mapping.**

---

## Phase 2: R1–R10 Mapping

Each mapping entry synthesizes Phase 1 evidence for one ARL requirement. For each: which frameworks address it, which don't, where they disagree, and what must be designed from scratch.

---

### R1 — RT-ICA / Front-Loading as Gate Pattern

**What the ARL needs:** Before iterative refinement begins, capture enough context that the loop can operate without returning to the human for missing information. This is the "information completeness" gate.

**Which frameworks address it:**

- **SAM** (strongest): RT-ICA classifies each prerequisite as AVAILABLE/DERIVABLE/MISSING. Any MISSING item blocks progression. Dynamic — adapts to what's being built, not a fixed checklist. 4 stages before execution (Discovery→Planning→Context Integration→Task Decomposition). [Q2-Q3: ssf:374-378, human-out-of-loop:144-145]
- **GSD**: 3-scale front-loading: project-level (PROJECT.md), phase-level (discuss-phase), task-level (planner must_haves/preferences). Workflow toggles allow skipping research. [Q2-Q4: discuss-phase.md:26, gsd-planner.md:128-149]
- **BMAD**: Sequential artifact chain (product brief→PRD→architecture→stories). "Create-story" explicitly described as a "context engine." [Q2: README.md:53, workflow.xml:71-90]
- **Ralph**: Medium front-loading — objective + specs + event topology. Planning session captures objective; topology is pre-built. [Q2: hatless_ralph.rs:21-23, ralph.yml:13-119]
- **Octocode**: Light-medium — Phase 0 context.md + hints system. Fast-path criteria (4 binary checks) determine whether deep front-loading needed. [Q2: research:237-259]
- **Gastown**: Structural front-loading — molecules define step DAGs at authoring time, delegation terms set autonomy boundaries at creation. [Q2: molecule.go:55-66, escalation.md:28-36]

**Which frameworks DON'T address it:**

All frameworks front-load to some degree. The gap is in detecting when front-loading proves INSUFFICIENT at runtime. SAM has no structured "return to discovery" path from execution. GSD does not front-load authentication requirements. [Q2-Q4: identified by sam-expert and gsd-expert]

**Where frameworks disagree:**

SAM treats front-loading as the PRIMARY gate (block until complete). GSD treats it as configurable (skip_research toggle). Octocode treats it as conditional (fast-path can skip). Ralph treats it as minimal (objective only, rest discovered at runtime). The disagreement is about how much front-loading is enough — SAM says "everything the agent will need," Ralph says "just the objective."

**What must be designed:**

The ARL's RT-ICA equivalent must handle a case none of the frameworks address: re-triggering discovery from within an iterative loop. SAM's front-loading is one-shot (no return path). The ARL loops — which means iteration N may discover that the front-loading from iteration 0 was insufficient. The logical process needs a "return to front-loading" decision point within the loop.

**Research questions informed:** Primary (under what conditions can human judgment be replaced) — front-loading is the primary mechanism for eliminating runtime human gates.

---

### R2 — Loop Detection (Output-Similarity or Task-Based Thrashing)

**What the ARL needs:** Detect when the loop is oscillating (fix A breaks B, fix B breaks A) or producing the same findings repeatedly (stall), and stop or escalate rather than continuing indefinitely.

**Which frameworks address it:**

- **Ralph** (only implemented): Task-based thrashing detection with hardcoded thresholds: 3 blocks = abandon task, 3 abandons = terminate loop. [Q3: mod.rs:447, :1917] Also: MaxRuntime cutoff (mod.rs:429-439) and max_activations per hat (config.rs:1200-1265). [Q1]
- **GSD** (partial): Bounded planning iterations (max 3 planner↔checker loops). But unbounded gap closure — verification→diagnosis→gap-closure can repeat without limit. [Q3: plan-phase.md:314-318, verify-work:480-490]

**Which frameworks DON'T address it:**

- **SAM**: No loop detection. Single-task scoping is structural prevention (each task is bounded), but when used in an iterative context, no mechanism prevents oscillation across tasks. [Q3]
- **BMAD**: No loop detection. No iteration concept beyond correct-course (which is human-triggered, not loop-triggered). [Q3]
- **Octocode**: No iteration-level loop detection. The adversarial flow (Generator↔Discriminator) prevents some stalls within a single pass but doesn't detect cross-iteration oscillation. [Q3, Q5]
- **Gastown**: No loop detection or convergence tracking. Phase-based progression only. [Q3, prior correction table]

**Where frameworks disagree:**

Ralph uses count-based heuristics (3 failures = escalate). GSD uses bounded iteration counts (max 3). The disagreement is whether to count FAILURES (Ralph) or ITERATIONS (GSD). Failure counting detects thrashing but not stalls. Iteration counting prevents infinite loops but doesn't distinguish progress from oscillation.

**What must be designed from scratch:**

Output-similarity loop detection — detecting that iteration N's findings resemble iteration N-2's findings (oscillation pattern). No framework implements this. Ralph detects task-level thrashing (same task fails repeatedly) but not finding-level oscillation (fix A breaks B, fix B breaks A). The logical process needs both: task-level thrashing detection (Ralph's pattern) AND finding-level oscillation detection (novel).

**Multi-agent monitoring opportunity (from Q5):** A dedicated loop-monitoring agent could track findings across iterations independently of the working agents. This agent would not participate in refinement — it would observe and classify the loop state (converging/stalling/oscillating).

**Research questions informed:** Primary + Secondary #1 (patterns for autonomous loop control).

---

### R3 — Validity Filtering / False Positive Handling

**What the ARL needs:** Distinguish genuine findings from false positives before acting on them. A finding without verifiable evidence should not trigger changes.

**Which frameworks address it:**

- **Octocode** (strongest adversarial): GAN-inspired flow where Verifier explicitly tries to find flaws in Generator output. Cross-model validation design eliminates shared blind spots. PR finalization classifies findings as UNCHANGED/UPDATED/INCORRECT — INCORRECT findings are deleted. [Q1, Q5: MANIFEST.md:117-125, PR-reviewer:546-550]
- **BMAD**: Adversarial code review with forced minimum findings (3-10 per review). Halt on zero findings (suspicious). Git reality check cross-references claims against actual git state. [Q5: code-review/instructions.xml:7-14, review-adversarial-general.xml:38,44]
- **Ralph**: Confessor + Handler two-layer adversarial chain. Handler spot-checks Confessor — if Confessor fabricated issues, Handler escalates. Backpressure validates machine-verifiable evidence (tests pass/fail, coverage%). [Q5: ralph.yml:61-63, :100-112, event_parser.rs:320-365]
- **GSD**: Plan-checker skepticism instructions ("DO NOT trust SUMMARY claims"). Verifier independently checks codebase. [Q5: gsd-plan-checker.md:56-61, gsd-verifier.md:440]
- **SAM**: Forensic Review as independent verifier — checks correctness, not adversarially hunting problems. Structural separation of execution and review. [Q5: ssf:640-709, :856]
- **Gastown**: Witness zombie detection cross-references agent state claims against tmux reality. HandleMerged commit verification cross-references merge claims against git state. Both are structural truth-source checks, not semantic validity filtering. [Q5: mol-witness-patrol, witness/handlers.go:282-296]

**Which frameworks DON'T address it:**

All frameworks have some validation, but NO framework filters the REVIEWER's own false positives. The adversarial patterns are unidirectional — reviewer validates producer, but nobody validates the reviewer. [Q5 synthesis]

**Where frameworks disagree:**

Adversarial strength spectrum: SAM (check correctness) → Gastown (structural truth-source) → GSD (skepticism instructions) → Ralph (inverted reward framing) → BMAD (forced minimum findings) → Octocode (GAN zero-sum). The disagreement is whether validation should be "confirm correctness" (SAM) or "actively try to break" (Octocode). Stronger adversarial mandates catch more real issues but also produce more false positives.

**What must be designed:**

Meta-validity filtering — filtering the filter's own false positives. No framework has a dispute mechanism where the producer can challenge a reviewer finding with counter-evidence. The ARL's cross-examination between parallel agents (Q5 finding) could address this: a finding challenged by a second independent agent is more likely valid than one accepted without challenge.

**Research questions informed:** Secondary #2 (minimum set of logical conditions per gate).

---

### R4 — Plan Quality Gates

**What the ARL needs:** Validate plans before execution. A plan that is internally inconsistent, addresses the wrong findings, or proposes disproportionate changes should not proceed.

**Which frameworks address it:**

- **GSD** (strongest): Plan-checker evaluates 7 dimensions: requirement coverage, task completeness, file organization, dependency correctness, scope sanity, testability, context compliance. Explicit thresholds (5+ tasks = blocker, 15+ files = blocker). Max 3 revision iterations. [Q3, Q5: gsd-plan-checker.md:55-293, plan-phase.md:269-318]
- **Octocode**: Verify Plan step in GAN flow — adversarial review and fact check against initial research. Plan approval gate (human checkpoint). [Q5: MANIFEST.md:91-94, plan:202-205]
- **BMAD**: Implementation readiness check (6 steps) validates PRD/architecture/stories before development. Completeness scores quantify readiness. [Q5: check-implementation-readiness steps 01-06]
- **SAM**: RT-ICA at planning stage blocks if prerequisites MISSING. But validates information completeness, not plan quality. [Q2: ssf:374-378]
- **Ralph**: No plan quality gate. Planning session captures objective and specifications but does not validate the resulting plan against quality criteria. [Q4]
- **Gastown**: No plan quality gate. Molecule step definitions are validated structurally (DAG validation) but not for quality or proportionality. [Q3]

**Where frameworks disagree:**

GSD and Octocode validate plans through adversarial checking (checker/verifier finds problems). BMAD validates through completeness scoring (all pieces present?). SAM validates through information assessment (all prerequisites met?). The disagreement is whether plan quality means "no problems found" (adversarial) or "all components present" (completeness).

**What must be designed:**

The ARL's plan quality gate must check something none of the frameworks check: whether the plan is proportional to the findings it addresses (R8 overlap). A plan that proposes rewriting 500 lines to fix a typo is structurally sound but disproportionate. GSD's scope thresholds catch large plans but don't compare plan scope against finding severity.

**Parallel quality checking opportunity (from Q5):** Multiple independent agents could check different plan dimensions simultaneously — one for feasibility, one for evidence backing, one for scope proportionality — then synthesize.

**Research questions informed:** Secondary #2 (minimum conditions per gate).

---

### R5 — Purpose Anchor (Record Intent at Iteration 0, Check Drift)

**What the ARL needs:** Record the skill's stated purpose before any changes begin. At each iteration, check whether changes have drifted from that purpose. Detect gradual semantic drift where individually-acceptable changes cumulatively shift purpose.

**Which frameworks address it:**

- **GSD** (closest): 4-layer intent chain (PROJECT.md → ROADMAP.md → CONTEXT.md → must_haves). Plan-checker context compliance (pre-execution). Deviation rules distinguish acceptable (Rules 1-3: bugs, security, blocking) from unacceptable (Rule 4: architectural). Goal-backward verification (post-execution). [Q4: gsd-plan-checker.md:251-293, gsd-executor.md:83-139]
- **SAM**: Discovery artifact captures problem, goals, anti-goals, FRs, NFRs. Stage 7 Final Verification compares against Discovery. But 5 transformation stages between capture and final check with no intermediate alignment verification. [Q4: ssf:300-359, :757-793]
- **BMAD**: 4-stage progressive chain (Product Brief → PRD FRs → Story ACs → Implementation). But local checking only — each stage checks against previous stage, never against original brief. [Q4: step-03-success.md:122]
- **Ralph**: Objective injected into every iteration prompt (bookend pattern). But no mechanism checks work RELEVANCE — backpressure validates quality (tests pass) not direction (right thing built). [Q4: hatless_ralph.rs:21-23]
- **Octocode**: mainResearchGoal in every tool call provides drift prevention (not detection). "On track?" self-check has no criteria. [Q4: research:628-629]
- **Gastown**: Issue bead + DelegationTerms (AcceptanceCriteria field) + molecule step sequence. Self-review checks file scope via git diff, not semantic scope. [Q4: mol-polecat-work:226-232]

**Which frameworks DON'T address it:**

No framework tracks alignment as a computed metric. All rely on human observation or LLM self-assessment. The gap between "intent was captured" and "work matches intent" is bridged by trust, not measurement. [Q4 universal finding]

No framework detects gradual semantic drift where small individually-acceptable changes cumulatively shift purpose. [Q4: sam-expert citing ssf:92, human-out-of-loop:329]

**What must be designed from scratch:**

A purpose anchor that persists across iterations and is checked programmatically (not by LLM self-assessment). The anchor must be captured at iteration 0 and compared at each subsequent iteration. The comparison must detect cumulative drift, not just single-step deviation. GSD's deviation rules are the closest pattern (distinguishing acceptable from unacceptable changes) but operate within a single execution, not across loop iterations.

**Research questions informed:** Primary (conditions for replacing human judgment) — purpose drift is one of the hardest human judgments to replace.

---

### R6 — Content-Loss Detection (Before/After Diff)

**What the ARL needs:** Detect whether semantic units (sections, headings, behavioral blocks, examples) present before changes are still present after. Reorganization is acceptable; silent deletion is not.

**Which frameworks address it:**

- **None directly.** This is the least-addressed R-requirement across all 6 frameworks. [Q4 universal finding]

**Partial approaches:**

- **BMAD**: Code review checks AC implementation status (IMPLEMENTED/PARTIAL/MISSING) — detects missing implementations but not content removed during refactoring. [Q4: code-review/instructions.xml]
- **GSD**: Verifier checks "does the goal hold?" with artifact existence checks (exists/substantive/wired). But checks goal achievement, not structural preservation. [Q4: gsd-verifier.md:107]
- **Octocode**: Prompt optimizer self-check "Did I change any original intent?" — via AI self-assessment, not structural diff. [Q4: prompt-optimizer]
- **SAM**: Content structural inventory comparison listed as ELIMINABLE in human-out-of-loop analysis. But not implemented — only identified as a category of machine-verifiable check. [Q1: human-out-of-loop:129]

**What must be designed from scratch:**

Content-loss detection is entirely novel. No framework diffs before/after to verify structural preservation. The logical process needs: (1) capture a structural inventory before changes (sections, headings, behavioral blocks, examples), (2) capture a structural inventory after changes, (3) compare inventories, (4) flag missing units. Reorganization (unit moved) vs deletion (unit absent) must be distinguished.

SAM's human-out-of-loop research (line 129) identifies "Content structural inventory comparison" as a category of machine-verifiable check, providing the conceptual foundation. But no implementation exists in any framework.

**Research questions informed:** Secondary #2 (minimum conditions per gate) — R6 has the least existing evidence and requires the most novel design.

---

### R7 — Convergence Tracking (Finding Count per Iteration)

**What the ARL needs:** Track whether the loop is producing fewer findings per iteration (converging), the same findings (stalled), or alternating between states (oscillating). Determine when remaining findings are not worth fixing (diminishing returns).

**Which frameworks address it:**

- **GSD** (closest but not equivalent): Re-verification tracks score delta (previous_score → score). But doesn't classify convergence/oscillation/stall — only reports whether score improved. [Q3: gsd-verifier.md, verify-work:480-490]
- **Ralph**: Fresh-context-per-iteration design explicitly trades away convergence tracking. Each iteration starts without knowledge of prior iterations. Thrashing detection (R2) is count-based, not convergence-based. [Q3: AGENTS.md:73-85]

**Which frameworks DON'T address it:**

- **SAM**: No state maintained across iterations. Each invocation is stateless. [Q3, research doc gap #3]
- **BMAD**: No iteration concept. Sequential pipeline runs once. [Q3]
- **Octocode**: No iteration-level tracking. Single-pass pipeline. [Q3]
- **Gastown**: Does not track convergence. Prior session incorrectly attributed this. [Q3, prior correction table]

**What must be designed from scratch:**

Convergence tracking is entirely novel as a cross-iteration capability. The logical process needs: (1) count and characterize findings at each iteration, (2) compare against previous iterations, (3) classify loop state (converging if count decreasing, stalling if count stable, oscillating if alternating). (4) Apply diminishing returns threshold — when the cost of fixing remaining findings exceeds the value of fixing them, the loop stops.

GSD's score delta provides a partial pattern (tracking improvement across verification runs), but it operates within a single phase, not across ARL iterations.

**Research questions informed:** Primary + Secondary #1 (patterns for autonomous loop control).

---

### R8 — Proportionality Check (Severity vs Blast Radius)

**What the ARL needs:** Evaluate whether the scope of proposed changes is proportional to the severity of findings. Flag when blast radius exceeds what the finding warrants. Low-severity findings should not trigger high-scope changes.

**Which frameworks address it:**

- **GSD** (closest): Scope sanity thresholds (tasks/plan ≤3, files/plan 5-8 target, context budget 50%). These catch oversized plans but measure plan SIZE, not proportionality relative to finding severity. [Q3: gsd-plan-checker.md:196-208]
- **BMAD**: Change scope classification (Minor/Moderate/Major) routes to different authority levels. But routes to TEAMS, not to proportionality assessment. [Q3: correct-course/instructions.md:161-164]
- **Octocode**: File count and line count thresholds (>500 lines → split). But measures absolute size, not proportionality. [Q3: plan:149]

**Which frameworks DON'T address it:**

- **SAM**: No proportionality concept. [Q3]
- **Ralph**: Uniform treatment — same thresholds for all tasks regardless of finding severity. [Q3: mod.rs:429-439]
- **Gastown**: Tier hints are advisory, not gating. No proportionality assessment. [Q3]

**What must be designed from scratch:**

Proportionality checking is novel. No framework compares finding severity against proposed change scope. The logical process needs: (1) classify finding severity (what's the impact of NOT fixing this?), (2) estimate change scope (how many files/lines/sections affected?), (3) compare — if scope >> severity, flag for review. GSD's scope thresholds provide a useful pattern for measuring scope, but the severity-to-scope comparison is new.

**Research questions informed:** Secondary #2 (minimum conditions per gate).

---

### R9 — Downstream Impact Analysis

**What the ARL needs:** Identify all inbound references to modified components. After changes, verify those references still resolve and contracts still hold. A change that breaks a downstream consumer should be detected.

**Which frameworks address it:**

- **GSD** (partial): Plan-checker validates file ownership (no two plans modify same file). Milestone integration checker verifies cross-phase wiring and E2E flows. But operates at plan/phase level, not at reference/contract level. [Q5: gsd-plan-checker.md, audit-milestone.md:55-71]
- **Octocode**: PR reviewer Flow Impact Analysis traces downstream effects of code changes. Only skill with explicit downstream impact analysis for code changes. [Q5: PR-reviewer:491-501]
- **Gastown**: Convoy observers (Witness + Refinery) both watch issue lifecycle. Redundant monitoring catches missed signals. But monitors issue state, not code references. [Q5: convoy/observer.go:14-67]
- **SAM**: Context Integration Agent (Stage 3) validates dependencies between tasks. But operates pre-execution, not post-change. [Q2: ssf:432-505]

**Which frameworks DON'T address it:**

- **BMAD**: No downstream impact analysis. Epic/story structure doesn't track cross-story dependencies. [Q5]
- **Ralph**: No downstream impact tracking. Backpressure validates local quality, not downstream effects. [Q5]

**Where frameworks disagree:**

GSD checks downstream at the plan/phase boundary (coarse-grained). Octocode checks at the code change level (fine-grained). The ARL modifies skills (markdown files with references), so downstream impact means checking that all files referencing the modified skill still resolve correctly. This is closer to Octocode's fine-grained approach.

**What must be designed:**

Post-change reference verification — after the ARL modifies a skill, scan all inbound references (from other skills, agents, CLAUDE.md, plugin.json) and verify they still resolve. The existing assessor lifecycle audits (bidirectional coherence) detect broken references, but they run BEFORE implementation, not AFTER. The logical process needs a post-implementation reference re-verification step.

**Multi-agent opportunity (from Q5):** Parallel dependency checkers could verify different reference types simultaneously (markdown links, skill activation references, plugin.json paths, CLAUDE.md references).

**Research questions informed:** Secondary #2 (minimum conditions per gate).

---

### R10 — Split Justification (When to Extract a New Skill)

**What the ARL needs:** When the refinement loop determines that content belongs in a separate skill, verify that the split produces independently viable units. A new skill created by splitting must be invocable in multiple distinct contexts, not only from its parent.

**Which frameworks address it:**

- **GSD** (partial): Splits plans by context budget and file ownership. But measures split necessity by resource constraints, not independent viability. [Q3: gsd-plan-checker.md:196-208]
- **Octocode**: Flags PRs >500 lines for splitting. But measures absolute size, not whether resulting pieces are independently useful. [Q3: plan:149]
- **BMAD**: Decomposes into epics/stories. But decomposition follows business domain boundaries, not independent viability checks. [Q3]

**Which frameworks DON'T address it:**

- **SAM**: No split concept in the pipeline. [Q3]
- **Ralph**: No split mechanism. [Q3]
- **Gastown**: Formula types encode topology but no split justification gate. [Q3]

**What must be designed from scratch:**

Split justification is entirely novel as a gate. No framework validates that a split produces independently viable units. The logical process needs: (1) before splitting, define what "independently viable" means (invocable from multiple contexts, not just parent), (2) after splitting, verify the new skill meets that criterion, (3) if the new skill is only useful as a reference file from its parent, classify it as a reference file rather than a skill.

The existing `/refactor-skill` workflow in plugin-creator splits based on line count and domain boundaries but has no independent viability gate. This is the specific gap the ARL would close.

**Research questions informed:** Secondary #2 (minimum conditions per gate).

---

### Phase 2 Summary

**Coverage by category:**

| Category | Requirements | Status |
|---|---|---|
| Import from frameworks (pattern exists, adapt for ARL) | R1, R3, R4 | Multiple framework patterns available; adaptation needed for iterative loop context |
| Partial coverage (closest analogue exists, significant extension needed) | R2, R5, R9 | Ralph thrashing (R2), GSD deviation rules (R5), Octocode flow analysis (R9) provide starting points |
| Build from scratch (no framework covers it) | R6, R7, R8, R10 | Content-loss detection, convergence tracking, proportionality, split justification are all novel |

**Cross-cutting finding:** The 4 build-from-scratch requirements (R6, R7, R8, R10) are all requirements that emerge specifically from ITERATIVE refinement. The surveyed frameworks are predominantly single-pass pipelines (SAM, BMAD, Octocode) or bounded iterations (GSD, Ralph). The ARL's distinguishing characteristic — recursive refinement until convergence — creates requirements that single-pass frameworks never encounter.

**Transition to Phase 3: Synthesis Writing.**

---

## Phase 3: Synthesis

**Status:** COMPLETE

Two synthesis documents written:

1. [synthesis-general-theory.md](./synthesis-general-theory.md) — 7 universal principles + decision tree + 4 unresolved tensions
2. [synthesis-arl-applicable.md](./synthesis-arl-applicable.md) — R1-R10 mapped to framework mechanisms with loop structure diagram

Both documents draw exclusively from Phase 1 Q&A and Phase 2 mapping. Scope check passed — all sections describe what/when/why, not how to build.

---

## Phase 4: Validation and Rigor Review

### 4a. Traceability Audit

For each major claim in the synthesis documents, trace backwards: synthesis section → Phase 2 mapping → Phase 1 Q&A → source code citation.

| Synthesis Claim | Phase 2 Entry | Phase 1 Q&A | Source Code Citations | Chain Complete? |
|---|---|---|---|---|
| Structure over instruction (General Theory P1) | Cross-cutting across R1-R10 | Q1 convergence pattern, Q3 branching analysis | SAM ssf:108, GSD execute-phase.md:322, Ralph AGENTS.md:73-85, Octocode MANIFEST.md:117-120, Gastown watchdog-chain.md:26-35 | Yes |
| Front-loading reduces runtime gates (General Theory P2) | R1 mapping | Q2 front-loading spectrum table | SAM ssf:374-378, GSD discuss-phase.md:26, BMAD workflow.xml:71-90, Ralph hatless_ralph.rs:21-23, Octocode research:237-259, Gastown molecule.go:55-66 | Yes |
| AI cannot reliably self-evaluate (General Theory P3) | R3 mapping | Q1 root cause analysis, Q5 adversarial patterns | SAM ssf:856, Octocode MANIFEST.md:122-125, Ralph ralph.yml:61-63, BMAD code-review/instructions.xml:26-31, Gastown witness/handlers.go:282-296 | Yes |
| Compression is architectural (General Theory P4) | R9 mapping, Q5 synthesis | Q5 escalation compression | GSD execute-phase.md:322, Gastown web/handler.go:254-309, Ralph mod.rs:1407-1431 | Yes |
| Iteration-aware state required (General Theory P5) | R2, R7 mapping | Q3 universal gap analysis | Ralph mod.rs:447, GSD verify-work:480-490 | Yes |
| Parallelism enables independent verification (General Theory P6) | Q5 synthesis | Q5 multi-agent inventory, parallelization | SAM ssf:1134, GSD diagnose-issues.md:87-88, Octocode doc-writer:50-56, Gastown design.formula.toml:26-29 | Yes |
| Failure paths need more compression (General Theory P7) | Q5 synthesis | Q5 escalation comparison | Ralph mod.rs:1958-2050, GSD execute-phase.md:265-284, Gastown escalation-system.md:83-113 | Yes |
| R6 is least-addressed requirement (ARL Applicable) | R6 mapping | Q4 universal finding | SAM human-out-of-loop:129, BMAD code-review/instructions.xml, GSD gsd-verifier.md:107 | Yes (conceptual foundation only — no implementation citations because none exist) |
| R2/R7/R8/R10 absent from all frameworks (ARL Applicable) | Phase 2 summary | Q3 "what no framework has" section | Ralph mod.rs:447 (R2 partial only), GSD verify-work:480-490 (R7 partial only) | Yes (absence claims verified by exhaustive Q3 analysis across all 6 frameworks) |
| No bidirectional cross-examination exists (ARL Applicable R3) | R3 mapping | Q5 adversarial pattern comparison | All 6 frameworks examined — patterns found are unidirectional in each | Yes (absence claim) |
| ARL loop structure sequence (ARL Applicable cross-cutting) | All R1-R10 mappings | Gate timing derived from when-activates fields in each mapping | N/A — logical process design, not source code claim | Yes (derived from Phase 2, not from source code) |

**Unsupported claims found:** None. All synthesis claims trace to Phase 1 Q&A evidence.

**Note on absence claims:** Several claims assert that no framework implements a capability (R6, R7, R8, R10). These are supported by the exhaustive Q3 analysis where all 6 experts were asked about these capabilities and none reported implementation. Absence claims are limited by the expert panel's coverage — a capability not reported is not the same as a capability that doesn't exist (see 4c Limitations).

---

### 4b. Research Question Coverage

| Research Question | Coverage | Synthesis Sections | Evidence Quality |
|---|---|---|---|
| **Primary:** Under what conditions can human judgment be replaced by machine-verifiable conditions, and what are the failure modes when conditions are insufficient? | **Full answer.** Decision tree in General Theory identifies 4 conditions (external truth source, single dimension, domain-knowledge-free, bounded scope). Failure modes documented per-requirement in ARL Applicable. | General Theory: Decision Tree; ARL Applicable: each R-requirement's "what failure looks like" | Strong — 6 frameworks × 5 question groups = 30 expert responses informing this |
| **Secondary #1:** What patterns for autonomous loop control exist, and which are implemented? | **Full answer.** Ralph thrashing detection and GSD bounded iterations are the only implemented patterns. All others are absent. | ARL Applicable: R2, R7; General Theory: P5 | Strong for what exists; strong for what's absent (exhaustive survey) |
| **Secondary #2:** For each R1-R10, what is the minimum set of logical conditions? | **Full answer.** Each R-requirement mapping in Phase 2 specifies what the gate must achieve and what success/failure look like. ARL Applicable provides per-requirement logical conditions. | ARL Applicable: all 10 R-requirement sections | Moderate — conditions are logically derived from framework patterns, not empirically validated |
| **Secondary #3:** Where do frameworks disagree, and what explains disagreements? | **Full answer.** Each Phase 2 mapping includes "where frameworks disagree" section. General Theory unresolved tensions document 4 cross-cutting disagreements. | Phase 2 mappings; General Theory: Unresolved Tensions | Strong — disagreements documented with specific framework positions and citations |
| **Secondary #4:** What does no framework address, and what does absence reveal? | **Full answer.** Phase 2 summary categorizes requirements as import/adapt/build-from-scratch. General Theory P5 explains why the gap exists (single-pass frameworks don't encounter iterative requirements). | Phase 2 summary; General Theory: P5; ARL Applicable: R6, R7, R8, R10 | Strong — exhaustive survey across 6 frameworks, with explanation of structural cause |
| **Secondary #5:** What general principles emerge beyond the ARL? | **Full answer.** 7 principles identified in General Theory, each with cross-framework evidence. | General Theory: P1-P7 | Strong — each principle supported by evidence from multiple frameworks |

**All research questions answered.** No unanswered questions remain.

---

### 4c. Limitations and Threats to Validity

**1. Single-source risk:** Each framework has exactly one expert. If an expert missed a capability or misinterpreted source code, the finding is unverified. Mitigation: cross-examination between experts challenged claims; prior corrections table from previous sessions corrected known errors.

**2. Inference risk:** The synthesis derives principles from patterns across 6 frameworks. These are empirical observations, not proven theorems. A 7th framework could contradict any principle. Mitigation: principles are stated with their evidence basis; exceptions or counter-evidence can be incorporated.

**3. Absence ≠ nonexistence:** When all 6 experts report "my framework does not implement X," this means X was not found in the surveyed code. It does not mean X cannot exist or has never been implemented anywhere. The survey covers 6 specific repositories.

**4. Temporal boundary:** All source code citations reflect repository state as of 2026-02-13. Frameworks evolve. Features may be added or removed after this date.

**5. Sample boundary:** The 6 frameworks share a context: they are all AI development orchestration frameworks. The general theory principles (P1-P7) may not generalize to non-AI-orchestration domains.

**6. Scope limitation of "machine-verifiable":** The synthesis uses "machine-verifiable" to mean "determinable without LLM semantic judgment." Some conditions classified as machine-verifiable (e.g., structural inventory comparison for R6) have not been implemented anywhere and may prove harder than expected.

**7. Cross-examination coverage:** Not all experts cross-examined all other experts on all questions. Coverage was partial — most experts cross-examined 1-2 others per question group. Systematic pairwise cross-examination across all 15 expert pairs was not achieved.

**8. Orchestrator synthesis bias:** The orchestrator (not the experts) wrote the synthesis. The orchestrator's framing, categorization, and emphasis choices introduce interpretation that was not directly validated by the experts. The Phase 2 mapping and Phase 3 synthesis are the orchestrator's analytical work product, informed by but not authored by the experts.

---

### 4d. Contribution Statement

**What this process discovered that was not previously documented in any single framework:**

1. **The "structural over behavioral" convergence.** All 6 frameworks independently converge on the principle that pipeline structure, not behavioral instructions, produces reliable AI behavior. No single framework documents this as a cross-framework pattern — each describes its own structural approach without referencing the universal principle.

2. **The iterative gap.** The 4 build-from-scratch requirements (R6, R7, R8, R10) all emerge specifically from iterative refinement. This explains WHY the surveyed frameworks don't address them — they are predominantly single-pass. This structural explanation for the gap was not documented anywhere.

3. **The adversarial strength spectrum.** The ranking from "check correctness" (SAM) to "actively try to break" (Octocode) with specific positions for each framework provides a comparative analysis that no single framework documents. Each framework describes its own approach without positioning it on a spectrum.

4. **The universal absence of bidirectional cross-examination.** No framework allows a producer to dispute a reviewer's finding. This gap — meta-validity filtering — was not identified as a category in any framework's documentation or research.

5. **The compression-by-constraint pattern.** GSD's 10-15% context orchestrator forces compression architecturally. This observation — that the most effective compression is caused by constraint, not instruction — emerged from comparing GSD's forced compression against frameworks with voluntary compression.

6. **The decision tree for gate replacement.** The 4 conditions under which human gates can be replaced (external truth source, single dimension, domain-knowledge-free, bounded scope) are synthesized from cross-framework evidence. No single framework articulates these conditions.

7. **The ARL loop structure with gate timing.** The sequence of R1-R10 gates within a single ARL iteration, with specific timing (before assessment, after assessment, after planning, after implementation), is a novel logical process design derived from the expert panel evidence.

---

### 4e. Reproducibility

**To reproduce these findings:**

1. Read the 6 framework repositories at the commit SHAs current on 2026-02-13
2. Pose the 5 question groups from the Q&A file to experts with access to each repository
3. Cross-examine expert responses
4. Map findings to R1-R10 requirements
5. Synthesize cross-framework patterns

The Q&A file preserves the full discussion record with source code citations. Any claim can be independently verified by reading the cited source files at the cited line numbers.

---

## Process Complete

**Phase 1:** 5/5 question groups discussed by all 6 experts. Cross-examination conducted.
**Phase 2:** R1-R10 mapped to framework evidence. 3 importable, 3 partial, 4 build-from-scratch.
**Phase 3:** Two synthesis documents written — general theory (7 principles) and ARL-applicable (10 requirements with loop structure).
**Phase 4:** Traceability audit (all claims traced), research question coverage (all 5+5 answered), limitations (8 documented), contribution statement (7 novel findings), reproducibility documented.
