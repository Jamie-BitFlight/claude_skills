---
name: RT-ICA process conflates implementation deliverables with information gaps
description: "The RT-ICA process has two distinct bugs:\n\n1. CATEGORIZATION BUG: RT-ICA agents list implementation deliverables as MISSING conditions. Observed on #719: \"sam create CLI command exists\" was listed as MISSING — but we know exactly what it needs to do. The information is complete; the code doesn't exist yet. Five of six MISSING items were things to build, not things we don't know. MISSING means \"we lack information that prevents planning.\" Deliverables belong in acceptance criteria, not RT-ICA conditions.\n\n2. INTERACTION BUG: When RT-ICA returns BLOCKED with genuine MISSING conditions, work-backlog-item Step 4 dumps all missing conditions as a text block and says \"wait for user response.\" No structured questions, no one-at-a-time flow, no multiple choice options, no research-before-asking, no loop until resolved.\n\nThe brainstorming skill (at /home/ubuntulinuxqa2/repos/superpowers/skills/brainstorming/) demonstrates the correct pattern: (a) research the project state first using tools, (b) ask one question at a time, (c) prefer multiple choice with options derived from research, (d) wait for response before next question, (e) loop until all gaps resolved. This reduces user burden and produces higher quality answers.\n\nThe ARL human-probing design doc (.claude/docs/sdlc-layers/arl-human-probing-design.md) identifies the right trigger points (RT-ICA BLOCKED, grooming gaps) and mentions multi-choice with open-ended opportunities, but has no implementation, no research-before-asking principle, and no interaction loop.\n\nWhat success looks like: When RT-ICA encounters a genuine MISSING condition (design decision, unknown constraint), the orchestrator (a) uses tools to research available options and trade-offs, (b) presents one question at a time with informed multiple-choice options, (c) waits for the user's answer, (d) updates the RT-ICA condition, (e) checks if any conditions remain MISSING, (f) loops until all resolved or user defers. Implementation deliverables are never listed as MISSING.\n\nHow you'll know it's working: RT-ICA on a well-understood item produces zero false MISSING conditions. When a genuine MISSING condition exists (e.g., naming convention decision), the user receives a single question with researched options (e.g., \"P{N}-{slug}.yaml where N=issue number\" vs \"tasks-{N}-{slug}.yaml with sequence counter\" — with trade-offs for each), not a text dump saying \"provide these inputs.\"\n\nFiles that need updating:\n- .claude/skills/work-backlog-item/SKILL.md Step 4 (RT-ICA Checkpoint) — add structured questioning loop\n- .claude/skills/groom-backlog-item/SKILL.md Step 8.5 (RT-ICA Final Pass) — add structured questioning for new MISSING\n- .claude/skills/groom-backlog-item/references/ — rtica-assessor agent prompt needs categorization rules\n- .claude/docs/sdlc-layers/arl-human-probing-design.md — implement the design with research-first principle\n- Any agent that performs RT-ICA assessment needs the deliverable vs information gap distinction"
metadata:
  topic: rt-ica-process-conflates-implementation-deliverables-with-in
  source: 'Session observation — RT-ICA on #719 listed 5 deliverables as MISSING information (2026-03-15)'
  added: '2026-03-15'
  priority: completed
  type: Bug
  status: done
  issue: '#720'
  last_synced: '2026-03-15T07:32:04Z'
  groomed: '2026-03-15'
---

## Groomed (2026-03-15)



### Decision

<div><sub>2026-03-15T07:23:41Z</sub>
<details><summary>struck: 2026-03-15T07:28:45Z — Simplified to single resolution pass; added training data asymmetry (generate questions: ok, answer questions: banned)</summary>

**ARL principle (from user, 2026-03-15)**:

ARL reduces human effort. It does not increase probing. The AI exhausts every autonomous option before involving the human. The self-probing loop is:

1. **Can I answer this with a tool?** (grep, web search, doc fetch, code analysis) → YES: research, resolve to AVAILABLE, continue. Do not ask the human.
2. **Can I answer this with an experiment?** (run a command, test a hypothesis, prototype) → YES: run it, resolve to AVAILABLE, continue. Do not ask the human.
3. **Can I find a resource that answers this?** (docs, prior decisions, ADRs, git history, research entries) → YES: read it, resolve to AVAILABLE, continue. Do not ask the human.
4. **This requires a human decision.** What kind?
   - Is it an opinion/preference? → What factors influence this choice?
   - Is it a constraint? → What are the boundaries?
   - Is it a trade-off? → What are the options?
5. **For each option**: derive impact, risk, effort, reversibility using tools and analysis.
6. **Present to human**: "Here are N options. Here's what each costs and risks. Which do you prefer?" — with multiple choice via AskUserQuestion. One question at a time. Not a gap report.

The human receives a fully researched decision brief, not a missing-information dump. The burden on the human is minimal: choose between well-researched options with trade-offs, not "provide these inputs."

**Interaction pattern** (from brainstorming skill at /home/ubuntulinuxqa2/repos/superpowers/skills/brainstorming/):
- One question at a time — not a batch
- Multiple choice preferred — with options derived from research
- Wait for response before next question
- Loop until all gaps resolved
- Research project state first using tools before asking anything

**What changes in RT-ICA**:
- Steps 1-3 of the ARL loop run BEFORE any condition is marked MISSING
- A condition is only MISSING after tools, experiments, and resources have been exhausted
- When a condition remains MISSING after autonomous resolution attempts, the presentation is a researched decision brief with options — not "provide this input"
- Implementation deliverables are never conditions — they are acceptance criteria
</details>
</div>

<div><sub>2026-03-15T07:26:30Z</sub>
<details><summary>struck: 2026-03-15T07:28:45Z — Simplified to single resolution pass; added training data asymmetry (generate questions: ok, answer questions: banned)</summary>

**ARL principle (from user, 2026-03-15, corrected)**:

ARL is **asynchronous introspection with batched human touchpoints** — not an interactive questioning loop. The AI works independently, building and resolving a question stack. The human is interrupted minimally with batched questions, not probed one at a time.

**The self-resolution loop:**

1. Build a question stack from all MISSING and DERIVABLE conditions
2. For each question on the stack, attempt resolution autonomously:
   - Try tools (grep, web search, doc fetch, code analysis) → resolved? remove from stack
   - Try experiments (run a command, test a hypothesis) → resolved? remove from stack
   - Try resources (docs, ADRs, git history, research entries) → resolved? remove from stack
   - Try deriving from other already-resolved answers → resolved? remove from stack
3. Repeat for N iterations or until a time threshold
4. If questions remain after threshold → batch them to the human
   - Present all remaining questions at once (not one at a time)
   - For each question: include the options researched, trade-offs derived, and what the AI tried
   - Human answers what they can, skips what they can't
5. Take whatever answers arrived → return to self-resolution loop
   - New answers unlock further derivation of remaining questions
6. Loop until stack is empty or AI is stuck again (another batch to human)

**Key distinction from brainstorming-style interaction:**
- Brainstorming = interactive design session, one question at a time, synchronous
- ARL = autonomous work with minimal interruption, batched questions, asynchronous

**What this means for RT-ICA BLOCKED handling:**
- The orchestrator does NOT immediately present MISSING conditions to the human
- The orchestrator first runs the self-resolution loop (tools, experiments, resources, derivation)
- Only conditions that survive the loop get batched to the human
- The batch includes what was tried and what options exist — not bare gap names
- Implementation deliverables are never on the question stack — they are acceptance criteria

**Threshold parameters (to be determined during implementation):**
- Loop iteration limit before batching to human
- Time limit before batching to human
- Whether partial human answers trigger immediate re-loop or accumulate
</details>
</div>

<div><sub>2026-03-15T07:28:45Z</sub>

**ARL principle (from user, 2026-03-15, final)**:

ARL is **asynchronous introspection with batched human touchpoints**. A single resolution pass filters out questions the AI can answer with tools before presenting the remainder to the human.

**The asymmetry:**
- **Generating questions from training data**: welcomed — "what are the common trade-offs for X?" is a valid question to put on the stack
- **Answering questions from training data**: banned — answers must come from tools, experiments, resources, or the human. Training data recall is a hallucination source for project-specific gaps.

**Single resolution pass:**

1. Build question stack from MISSING and DERIVABLE conditions
2. For each question on the stack:
   - Can I answer this with a tool right now? (file read, grep, web fetch, command output) → answer must cite the tool result. Remove from stack.
   - Can I answer this only from training data? → question stays on stack. Do not answer it.
   - Can I not answer it at all? → question stays on stack. Note what was tried.
3. Present remaining stack to human as a batch
   - For each question: what was tried, what options were found (from tool results), what trade-offs were derived (from tool results)
   - Human answers what they can, skips what they can't
4. Take answers received → resolved conditions unlock further derivation of remaining questions
5. Continue with whatever was resolved

**What this prevents:**
1. Asking the human questions the AI can look up (wasted human attention)
2. Answering project-specific questions from training data (hallucination)
3. Treating implementation deliverables as information gaps (wrong category)

**What this means for RT-ICA:**
- Before marking any condition MISSING, run one resolution pass with tools
- Every resolution must cite a tool result — not training data
- Conditions that survive the pass get batched to the human with researched options
- Implementation deliverables are never on the question stack — they are acceptance criteria

**Interaction model:**
- NOT one-at-a-time interactive probing (that's brainstorming-style, for design sessions)
- Batched presentation of remaining questions after autonomous resolution
- Human answers partially → AI continues with what it got
</div>

### Research

<div><sub>2026-03-15T07:32:04Z</sub>

**ARL Canonical Sources (verified 2026-03-15)**:

Primary reference (in this repo):
- `plugins/agentskill-kaizen/references/arl.md` — 187-line knowledge reference covering HOOTL, three-layer architecture, 10 gates (R1-R10), interaction spectrum, scope-feasibility matrix, 7 universal principles

Primary research (SAM repo):
- `/home/ubuntulinuxqa2/repos/stateless-agent-methodology/research/arl/README.md` — 51KB canonical ARL definition
- `/home/ubuntulinuxqa2/repos/stateless-agent-methodology/research/arl/PROVENANCE.md` — provenance of HOOTL, ARL, agentskill-kaizen concepts
- `/home/ubuntulinuxqa2/repos/stateless-agent-methodology/research/arl/references/human-out-of-loop-prerequisites.md` — 482 lines: eliminable/front-loadable/irreducible classification of human checks, front-loading pattern
- `/home/ubuntulinuxqa2/repos/stateless-agent-methodology/research/arl/references/autonomous-refinement-loop-research.md` — 147 lines: 9 infrastructure gaps for replacing the human
- `/home/ubuntulinuxqa2/repos/stateless-agent-methodology/research/arl/references/synthesis-arl-applicable.md` — R1-R10 mapped to logical process design with gate timing
- `/home/ubuntulinuxqa2/repos/stateless-agent-methodology/research/arl/references/synthesis-general-theory.md` — 7 universal principles with cross-framework evidence
- `/home/ubuntulinuxqa2/repos/stateless-agent-methodology/autonomous-loop-principles.md` — 7 principles extracted from 6 frameworks

Design doc (in this repo, stub):
- `.claude/docs/sdlc-layers/arl-human-probing-design.md` — 72-line stub, status: "Design (to be implemented)"

**Key ARL concepts that govern RT-ICA BLOCKED handling:**

1. **R1 = RT-ICA** — Information Completeness gate. Failure mode: "Loop proceeds with gaps, agent hallucinate-fills missing information." This is the gate #720 fixes.

2. **Interaction Spectrum** — 4 levels, goal is level 4:
   - Level 1: Question with no context (current RT-ICA BLOCKED)
   - Level 2: Question with context
   - Level 3: Statement requesting confirmation
   - Level 4: Completed work with async follow-up (HOOTL goal)

3. **Layer 2 Execution Model** — Three mechanisms:
   - AI user representatives: triage questions before they reach the human
   - Question-to-action-item conversion: exhaust resources, surface completed work + action item
   - Async feedback queue: DAG visibility showing what each question blocks/unblocks

4. **Scope-Feasibility Matrix** — Determines if HOOTL is feasible for a given question:
   - High scope clarity + high measurability + high data enumeration = autonomous
   - Low on any dimension = human required at that decision point

5. **Decision Tree** — 4 conditions ALL must hold to replace human gate:
   - External truth source exists
   - Operates on single dimension
   - Pass/fail determinable without domain knowledge
   - Scope is bounded

6. **Front-Loading Principle** — "More context captured upfront = fewer human interventions during execution. Every point of ambiguity in the goal is a point where the loop will either guess or stall."
</div>