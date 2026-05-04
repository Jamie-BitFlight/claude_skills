# Human-Out-of-Loop Prerequisites

Research analysis identifying what must be known, measured, and verified before autonomous refinement loops can operate without human review gates.

**Date:** 2026-02-13
**Status:** Research Analysis — Logical Process Design
**Purpose:** Define the conditions, decision trees, and failure modes for autonomous skill refinement

This document describes what must be true for human gates to be removed, when removal is feasible, and why certain gates resist automation. It does not prescribe how to build the mechanisms — no schemas, thresholds, file layouts, or tool selections. See `ARL-agent-instructions.md` Section 0 for scope boundary rationale.

**Relationship to other ARL documents:**

- [Autonomous Refinement Loop Research](./autonomous-refinement-loop-research.md) → defines the problem (what the human does, what's missing)
- This document → analyzes the conditions under which human gates can be removed
- `ARL-agent-instructions.md` → governs the expert panel process that produces the logical process design

---

## Research Questions This Document Addresses

This document primarily advances these research questions (from `ARL-agent-instructions.md` Section 1a):

- **Primary:** Under what conditions can human judgment at iterative refinement loop gates be replaced by machine-verifiable conditions, and what are the failure modes when those conditions are insufficient?
- **Secondary #2:** For each ARL requirement (R1–R10), what is the minimum set of logical conditions that must hold for the gate to operate without human intervention?
- **Secondary #3:** Where do the surveyed frameworks disagree on approach, and what contextual factors explain those disagreements?

---

## 1. Universalities Across Documents

### Common Patterns: Where Human Judgment Is Required

All documents identify these recurring human decision points:

**1. Goal Alignment Verification**

- **SAM/SSE Framework:** "Planning stage BLOCKS if prerequisites missing" — human must verify completeness before proceeding (stateless-software-engineering-framework.md, lines 90-91)
- **Process Realignment:** "Review and restate the goal and intent to the user until user approves" (process_realignment.md, line 32)
- **Autonomous Refinement Research:** "Does the plan address the actual intent of the skill, or is it optimizing for metrics that don't matter?" (autonomous-refinement-loop-research.md)

**Pattern:** All methodologies require explicit goal confirmation before execution. Without human input, systems optimize for wrong objectives. This maps to R5 (Purpose anchor) and R1 (RT-ICA / front-loading).

**2. Proportionality Judgment**

- **SAM Framework:** No explicit proportionality check exists
- **Autonomous Refinement Research:** "Are the proposed changes proportional to the issues found, or is it over-engineering?"
- **Process Realignment:** Complexity assessment determines artifact granularity — "Simple: Single-module, no external interfaces" vs "Complex: Cross-system, infrastructure, hardware" (lines 43-47)

**Pattern:** Change scope must match problem severity. Systems lack intuition for "is this fix worth its blast radius?" This maps to R8 (Proportionality check).

**3. Downstream Impact Assessment**

- **SAM Framework:** "Verification at boundaries — Every stage validates previous stage's output" (README.md, line 152)
- **Autonomous Refinement Research:** "Will the changes break something downstream that the assessor didn't account for?"
- **Process Realignment:** Interface control documents track external system integration, hardware-software boundaries (lines 95-98)

**Pattern:** All frameworks recognize cascading dependencies exist. None solve cross-system impact prediction without human review. This maps to R9 (Downstream impact).

**4. Convergence vs Oscillation Detection**

- **SAM Framework:** Fresh context per phase eliminates error accumulation, but no convergence tracking across iterations
- **Autonomous Refinement Research:** "Is the loop converging or oscillating (fix A breaks B, fix B breaks A)?"

**Pattern:** Recursive refinement can spiral. Detecting productive vs degenerative iterations requires state tracking absent from stateless architectures. This maps to R2 (Loop detection) and R7 (Convergence tracking).

### Common Patterns: Where Machine-Verifiable Conditions Successfully Replace Human Review

**1. Deterministic Backpressure**

- **SAM Framework:** "Always run deterministic checks (tests/linters/static analysis/checklists) and treat failures as ground truth" (README.md, line 153)
- **Plugin-Creator:** Error codes E001-E023 provide deterministic validation without human judgment (plugin-creator/CLAUDE.md, ERROR_CODES.md)
- **Autonomous Refinement Research:** "Cross-reference each finding against the source file with line evidence. False positives have no line evidence."

**Success Factor:** When outcomes are binary (pass/fail) with objective evidence (test output, linter errors, file:line references), machines eliminate human review need. This is the strongest category of gate replacement.

**2. Schema Validation**

- **SAM Framework:** Artifact templates enforce structure
- **Plugin-Creator:** Frontmatter schema validation catches structural errors before execution (uvx skilllint@latest check)
- **Autonomous Refinement Research:** "Every acceptance criterion in the task file gets a pass/fail."

**Success Factor:** Predefined schemas allow automated verification. Human review only needed when schema is ambiguous or incomplete.

**3. Content-Loss Detection**

- **SAM Framework:** Message passing via artifacts creates audit trail (README.md, line 151)
- **Autonomous Refinement Research:** "Every heading and code fence in the original must appear somewhere in the result."

**Success Factor:** Structural preservation can be verified mechanically. Inventories of structural elements (headings, code fences, sections) are machine-checkable invariants. This maps to R6 (Content-loss detection).

### What Makes Autonomous Operation Possible vs Impossible

**Possible When:**

| Condition | Evidence from Documents |
|-----------|------------------------|
| **Complete context provided upfront** | SAM: "Task files contain all answers needed for the task" (README.md, line 155) |
| **Binary pass/fail criteria exist** | SAM: "Deterministic backpressure" (README.md, line 153); Plugin-Creator: ERROR_CODES.md |
| **Scope is constrained** | Process Realignment: "Simple: Single-module, no external interfaces" (line 44) |
| **Verification is structural** | Autonomous Refinement: "Every heading must appear" |
| **Dependencies are explicit** | SAM: Artifact interdependency chains |

**Impossible When:**

| Condition | Evidence from Documents |
|-----------|------------------------|
| **Goal is ambiguous** | Open-ended goals like "best-in-class" require defining every evaluative term |
| **Proportionality requires context** | Severity weights depend on domain knowledge not capturable as fixed rules |
| **Downstream impact unknown** | Cross-system effects require knowledge beyond what's in scope |
| **Purpose can drift** | Successive rewrites can shift a skill away from its original intent without any single change being obviously wrong |
| **Convergence criteria subjective** | "Are remaining findings worth fixing?" is a value judgment |

**Critical Insight:** SAM architecture eliminates many failure modes through structure (stateless agents, externalized memory, verification at boundaries), but the framework presupposes human-provided complete task files. The autonomous refinement loop question is: **Can we generate those complete task files automatically?**

---

## 2. Human-Out-of-Loop vs Human-at-End-of-Loop

Classification of all human interaction points identified across documents:

### Eliminable: Replaced by Machine-Verifiable Conditions

These are gates where the human check can be fully replaced by an automated condition, provided certain prerequisites are met.

| Human Check | What the Replacement Must Achieve | Prerequisites for Elimination |
|-------------|----------------------------------|-------------------------------|
| **Are findings real?** | Distinguish genuine issues from false positives. A finding without verifiable evidence should not trigger changes. | Findings must include file:line citations. Source files must be readable. Evidence must be exact matches, not inferred. |
| **Did implementation match plan?** | Compare what was planned against what was produced. Every acceptance criterion checkable as pass/fail. | Plan must include binary acceptance criteria. Outputs must be verifiable artifacts. |
| **No content loss?** | Detect whether structural elements present before changes are still present after. | Content inventory taken before changes. Structural elements (headings, code fences, sections) enumerable. |
| **Is the loop converging?** | Track whether finding count decreases across iterations. | State maintained across iterations. Finding counts quantifiable. Stopping condition defined. |
| **Frontmatter valid?** | Schema validation against defined models. Deterministic error codes. | Schema definitions exist. Validation runs automatically. |
| **Plugin structure valid?** | Structure checks against defined schema. Required fields, file references, syntax. | Schema defined. All component paths resolvable. Exit codes deterministic. |

### Front-Loadable: Captured Once at Start, Used Throughout

These are gates where the human's judgment can be captured before the loop begins, then referenced throughout execution without further human input.

| Human Check | What Must Be Captured Upfront | Why Front-Loading Works |
|-------------|------------------------------|------------------------|
| **Goal alignment** | Desired outcome, component objectives, testable acceptance criteria | If the goal is clear and measurable at the start, every iteration can check alignment against the recorded goal without asking the human again. |
| **Proportionality boundaries** | What severity levels exist. What constitutes "disproportionate" change scope for each level. | Proportionality judgment is contextual, but the context can often be captured as rules before execution begins. |
| **Complexity classification** | Whether this task is simple/bounded or complex/unbounded. What design depth is appropriate. | Complexity determines how much autonomy is safe. A simple bounded task needs fewer gates than a complex unbounded one. |
| **Downstream dependencies** | What other components reference the target. What contracts must be preserved. | The dependency graph can be mapped before changes begin. Re-verification after changes uses this map. |
| **Convergence exit criteria** | Maximum iteration count. Minimum improvement per iteration to justify continuing. Severity floor below which remaining findings are not worth fixing. | These are value judgments, but they can be made once at the start rather than at every iteration. |
| **Purpose invariant** | The skill's stated intent at iteration 0. Used as anchor to detect drift. | Purpose drift is detected by comparison, and comparison requires a baseline. Capture the baseline once. |

### Irreducible: Requires Continuous Human Judgment

These are gates where the human's judgment cannot be fully captured upfront or replaced by automated conditions. The reasons vary.

| Human Check | Why It Resists Automation | Mitigation Strategy |
|-------------|--------------------------|---------------------|
| **Is the split justified?** | Determining whether a new skill is independently viable requires understanding user mental models and workflow contexts. Use cases emerge over time, not from static analysis. | Post-hoc validation: track invocation patterns after splitting. If a skill is only ever called from its parent after a reasonable observation period, it was not a viable independent skill. |
| **Will users find the new skill?** | Discoverability depends on naming intuitiveness, documentation clarity, and user familiarity — all context-dependent and not measurable at split time. | Generate invocation examples during split. Include cross-references from parent skill. Monitor usage patterns. |
| **Does purpose serve end users?** | End-user benefit is contextual and cannot be algorithmically determined without user feedback. A skill can pass all validators and still be useless. | Capture user benefit statements during front-loading. Re-validate against those statements after each iteration. Flag if changes don't map to stated benefits. |
| **Are changes proportional to blast radius?** | Severity is contextual. A typo in user-facing documentation is critical; same typo in internal comment is trivial. The same finding has different severity in different contexts. | Pre-define severity for known issue types during front-loading. Flag unknown issue types for human classification. |
| **Purpose drift beyond threshold** | Automated comparison can detect that a description changed, but cannot reliably distinguish "rewording for clarity" (not drift) from "expanding scope" (drift). | Use comparison as a heuristic trigger for human review, not as a final determination. When comparison flags a change, present the before/after to the human rather than deciding autonomously. |

---

## 3. Prerequisites for Human-Out-of-Loop

What must be **KNOWN** and **MEASURED** before autonomous refinement can operate without human gates.

### Starting State Requirements

#### What Data Must Be Available

Before the loop begins, these categories of information must be present. Without any one of them, specific gates cannot operate and the loop falls back to human intervention at those points.

| Data Category | Why It's Required | What Happens Without It |
|---------------|-------------------|------------------------|
| **Source files (complete, not excerpts)** | Every finding must be traceable to a specific location in the source. Line-level evidence separates real findings from false positives. | Validity filtering (R3) cannot operate. Findings cannot be verified. |
| **Dependency graph** | Downstream impact analysis requires knowing what references the target. | Downstream impact (R9) cannot operate. Changes may break consumers silently. |
| **Historical context** | Previous iterations, known failure modes, lessons learned from similar skills. Prevents repeating past mistakes. | Loop detection (R2) weakened. Same failures can recur across sessions. |
| **Quality baselines** | Structural inventory before changes: headings, code fences, sections, validation status. | Content-loss detection (R6) cannot operate. No basis for before/after comparison. |
| **Reference standards** | What "good" looks like for this type of skill. Official documentation, community patterns, authoritative examples. | Plan quality (R4) has no standard to evaluate against. Plans cannot be judged as sound or unsound. |

#### Goal Specification Precision

The desired outcome must answer:

- **End state definition:** What does the completed skill look like? What measurable attributes define success?
- **Success criteria:** What tests or checks prove each objective is met? Are they binary (pass/fail) or scored?
- **Non-goals:** What improvements are explicitly out of scope? What constraints must not change?

**Why precision matters:** Every point of ambiguity in the goal is a point where the loop will either guess (risking wrong direction) or stall (requiring human input). The more precise the goal, the more gates can operate autonomously.

#### Expected vs Acceptable Outcomes

Three questions that must be answered upfront:

1. **Ideal outcome vs minimum viable outcome?** — Determines stopping criteria. The loop stops when "acceptable" is reached, not when "perfect" is reached.
2. **What failures are blocking vs advisory?** — Some conditions must pass (the loop cannot continue without them). Others can fail with warnings (the loop notes them and continues).
3. **When to escalate vs retry?** — If the same check fails in consecutive iterations, does the loop retry with a different approach or escalate to the human?

#### Guardrails and Safety Constraints

Constraints that prevent destructive changes:

| Constraint Category | What It Prevents | When It Activates |
|--------------------|------------------|-------------------|
| **Immutability constraints** | Fields that must not change (purpose anchor, skill identity). | Before committing any change. If a protected field changed, block the change. |
| **Dependency preservation** | All inbound references must remain valid after changes. | After implementation, before accepting the result. |
| **Content preservation** | Structural elements from iteration 0 must appear in iteration N (possibly reorganized, not deleted). | After implementation, during content-loss detection. |
| **Scope boundaries** | Changes limited to specific files/directories. Cannot modify files outside the target scope. | During implementation. Any edit outside scope is blocked. |

### Scope-Dependent Complexity

**Critical insight:** Scope ambiguity determines feasibility of removing human gates.

#### Constrained Scope Example: "Cross Platform Usage Guide for Astral's uv Tool"

**Characteristics:**

- Subject matter: Single, well-defined tool with official documentation
- Expected outcome: Practical guide for cross-platform usage patterns
- Data sources: Identifiable and enumerable (uv docs, GitHub examples, pyproject.toml specs)
- Success measurement: Binary (user can install, create project, manage dependencies on target platforms)
- Unknowns: Limited (platform-specific edge cases)

**Human gates eliminable here because:**

1. Complete dataset enumerable — documentation URLs known, official examples exist
2. Goal objectively verifiable — guide either covers core workflows or doesn't
3. No subjective quality judgment — "comprehensive" means coverage of known commands, measurable via checklist
4. Proportionality calculable — finding severity determinable from user impact

**Autonomous loop feasible:** Yes, provided validators can test examples (deterministic pass/fail) and content completeness is measured against a known inventory.

#### Open-Ended Scope Example: "Meta-Skill that Assesses Any Skill to Best-in-Class"

**Characteristics:**

- Subject matter: "Meta-skill" undefined. Self-referential (skill that improves skills, including itself)
- Expected outcome: "Best-in-class" undefined. "Self-improving" implies no stopping criteria
- Data sources: Unknowable — what is the reference dataset for "best skill design"?
- Success measurement: Subjective — "best-in-class" varies by use case, user expertise, domain
- Unknowns: Vast — what makes a skill "best"?

**Human gates irreducible here because:**

1. **Goal definition infinite regress** — "Best-in-class" requires defining evaluation criteria. Criteria depend on user priorities. User priorities emerge from usage, not specification.
2. **No objective stopping criteria** — "Recursive self-improving loop" has no natural end state. Every iteration can find new "improvements" by changing evaluation weights.
3. **Purpose drift inevitable** — Each iteration changes the skill based on assessment findings. After N iterations, the skill may optimize for assessor metrics rather than user utility.
4. **Self-reference paradox** — If the meta-skill assesses itself and finds improvements, does it rewrite its own assessment logic? How to prevent assessment bias drift?

**Why front-loading fails here:** Even with pre-defined rubrics, thresholds, and stopping criteria, the core problem remains — rubric weights are unknown (depends on context), user satisfaction is unknowable without deployment, and goal alignment is unverifiable (high rubric scores do not equal useful skill).

#### The Scope-Feasibility Relationship

| Scope Clarity | Goal Measurability | Data Enumeration | Human Gates Eliminable? |
|--------------|-------------------|------------------|-------------------------|
| **High** (specific tool, platform, use case) | **High** (binary pass/fail, checklist) | **High** (official docs, known examples) | **Yes** — Autonomous loop feasible |
| **Medium** (domain-specific best practices) | **Medium** (scoring with weights) | **Medium** (reference examples, community patterns) | **Partial** — Autonomous with periodic human checkpoints |
| **Low** (general improvement, meta-goals) | **Low** (subjective, emergent criteria) | **Low** (unknown what "complete" means) | **No** — Requires human at each decision point |

**Design implication for the logical process:** The ARL must either:

1. **Constrain scope** — Only operate on bounded problems with clear success criteria
2. **Front-load extensively** — Spend the discovery phase collapsing ambiguity until scope reaches "High" clarity
3. **Accept hybrid model** — Autonomous execution within iteration, human review between iterations

---

## 4. The Front-Loading Pattern

If the design goal is "every point where a human would pivot, decide, review, or quality-check gets asked and clarified at the start," what does that front-loading session need to accomplish?

### What Must Be Captured

The front-loading session must produce answers to these categories of questions. The expert panel (governed by `ARL-agent-instructions.md`) will determine the logical process for how these answers are gathered and validated.

#### Goal Definition

- What does "done" look like? (End state description)
- How will success be measured? (Observable outcomes)
- What value does completion deliver to users? (Benefit statement)
- What are the component objectives? Are they independently measurable?
- What is explicitly out of scope?
- What trade-offs are acceptable?

#### Quality Boundaries

- Which checks are blocking (must pass to continue) vs advisory (noted but not blocking)?
- What constitutes "good enough" vs "ideal"?
- What failures trigger escalation to the human?
- At what point does the loop stop (maximum iterations, minimum improvement, severity floor)?

#### Invariants and Constraints

- What must not change? (Purpose anchor, skill identity, protected fields)
- If those things must change, what approval process applies?
- Must all structural elements from the original be preserved?
- What is the scope boundary — which files/directories can the loop modify?

#### Context and Dependencies

- What other components reference the target?
- What does the target invoke?
- Has this been refactored before? What issues arose?
- What reference standards define "good" for this type of skill?
- What is the blast radius if changes go wrong?

#### Execution Environment

- What validators will run? In what order?
- How is complexity measured?
- What agents handle what task types?
- Can tasks run in parallel or must they be sequential?
- What happens when a task fails?

### When Front-Loading Is Sufficient vs Insufficient

**Sufficient when:**

1. All decision points captured — every question that would cause a human to pause during execution has been answered
2. Criteria are binary or scored with defined thresholds — no fuzzy "looks good" judgments
3. Scope is constrained — problem space is bounded, complete dataset enumerable
4. Guardrails prevent drift — immutability constraints block unintended changes
5. Escalation triggers defined — clear criteria for when the loop must stop and request human input

**Insufficient when:**

1. Goal evolves during execution — user discovers the original goal was wrong
2. Unknowns emerge — findings reveal dependencies not captured during discovery
3. Proportionality requires runtime context — change scope vs severity depends on information only available during implementation
4. Subjective quality judgment required — "is this wording clearer?" cannot be pre-captured
5. Purpose drift undetectable by comparison — subtle scope expansion passes automated checks

**What happens when front-loading is insufficient:** The loop must detect that it has encountered a decision point not covered by front-loading, and STOP rather than guess. The ability to detect insufficiency and escalate is itself a requirement — a loop that guesses when uncertain is worse than a loop that asks.

---

## 5. What the AI Reviewer Must Know

If an AI actor replaces the human reviewer, that AI must be "hard hitting, insightful, well researched, purpose driven, runtime environment and contextually aware, knowing how and why end users benefit from having the skill."

This section analyzes what **categories of information and evaluation approaches** would give an AI reviewer those qualities.

### "Hard Hitting" — Finds Real Issues, Not False Positives

**What the reviewer needs:**

| Input Category | Why It Enables Hard-Hitting Critique |
|----------------|-------------------------------------|
| **Source file with line numbers** | Enables file:line citations. Specific, verifiable findings rather than vague observations. |
| **Baseline metrics** | Enables delta detection. "This iteration added significant content but fixed only one finding" is measurable comparison. |
| **Dependency graph** | Enables impact assessment. "Changing this breaks N callers" is concrete blast radius. |
| **Validation error logs** | Enables root cause analysis. Specific error codes with line references point to specific fixes. |
| **Historical failure patterns** | Enables pattern recognition. "Previous iteration tried this approach, it caused these problems" prevents repetition. |

**What hard-hitting means in practice:**
- Finding cites specific file:line evidence
- Finding can be verified objectively (test, validator, grep)
- Finding is actionable (clear fix vs vague suggestion)
- False positive prevention: cited line still exists, finding still applies after recent changes, finding is not duplicate

### "Insightful" — Identifies Non-Obvious Issues and Opportunities

**What the reviewer needs:**

| Input Category | Why It Enables Insight |
|----------------|----------------------|
| **Cross-reference analysis** | Enables usage pattern insight. Which skills reference this one? Are references balanced or over-coupled? |
| **Semantic similarity** | Enables redundancy detection. Is this skill's description substantially similar to an existing skill? |
| **Architectural patterns** | Enables structural insight. Is the skill at the right abstraction layer? |
| **User workflow traces** | Enables user experience insight. What do users do before and after invoking this skill? Where do they get stuck? |
| **Optimization opportunities** | Enables efficiency insight. Which sections consume the most tokens relative to their reference frequency? |

**What insightful means in practice:**
- Recognizes recurring issues across multiple skills (systemic, not local)
- Identifies architectural coherence issues (coupling, abstraction boundaries)
- Surfaces user experience friction that isn't captured by validators

### "Well Researched" — Grounded in Authoritative Sources

**What the reviewer needs:**

| Input Category | Why It Enables Research Depth |
|----------------|------------------------------|
| **Official documentation** | Enables citation against authoritative sources. Claims can be verified. |
| **Community best practices** | Enables benchmarking against what others do. |
| **Historical context** | Enables version awareness. Is the skill using current patterns or deprecated ones? |
| **Domain-specific references** | Enables domain correctness. PEP standards for Python skills, testing patterns for test skills. |

**What well-researched means in practice:**
- Claims cited with specific sources (URL, document, line)
- Sources are authoritative (official docs weighted over community forums)
- Sources are current (publication/access date noted)
- If novel approach, rationale explained and counter-examples considered

### "Purpose Driven" — Optimizes for User Value, Not Metrics

**What the reviewer needs:**

| Input Category | Why It Enables Purpose Focus |
|----------------|----------------------------|
| **User benefit statements** | Enables value validation. Does this change serve stated user benefit, or just improve a metric? |
| **Purpose anchor** | Enables drift detection. Has the skill's purpose shifted from iteration 0? |
| **Usage analytics** | Enables prioritization. Is this optimizing a rarely-used feature vs a common workflow? |
| **User pain points** | Enables problem-solution fit. Does the change address what users actually struggle with? |

**What purpose-driven means in practice:**
- Change serves stated user benefit (not just rubric scores)
- If purpose changed, it was intentional (approved) not drift
- Metric improvements that reduce usability are flagged, not celebrated
- Changes that don't map to user stories are questioned

### "Runtime Environment and Contextually Aware"

**What the reviewer needs:**

| Input Category | Why It Enables Context Awareness |
|----------------|----------------------------------|
| **System architecture** | Understands how skills load, how agents delegate, how tools interact |
| **Tool availability** | Knows what tools/permissions are available vs blocked |
| **Model capabilities** | Knows target model's context window, tool use patterns, limitations |
| **Dependency availability** | Knows what external dependencies exist, are installed, what versions |
| **User environment** | Knows project type, directory structure, git state |

**What context-aware means in practice:**
- Catches assumptions about execution environment ("skill assumes synchronous but delegates to async service")
- Validates tool permissions are sufficient for operations
- Validates model capabilities match task requirements
- Catches missing dependencies before runtime failure

### Integration: What Makes a Complete Reviewer

An AI reviewer with all these input categories can find real issues (source evidence), provide insights (cross-references and patterns), ground recommendations (authoritative sources), optimize for users (benefit statements and purpose anchor), and validate runtime feasibility (environment and dependencies).

**Without these inputs:** The reviewer becomes shallow — produces generic advice without evidence, misses context, optimizes for wrong goals.

**Design implication for the logical process:** The front-loading phase must gather all reviewer input categories and make them available to the review gate. The quality of autonomous review is bounded by the completeness of the information provided to the reviewer.

---

## 6. Summary: From Research to Logical Process Design

### What Enables Human-Out-of-Loop

**Necessary Conditions (all must be true):**

1. **Constrained scope** — Problem bounded, complete dataset enumerable, success criteria objective
2. **Binary verification** — Pass/fail checks with deterministic outcomes (tests, validators, diffs)
3. **Complete front-loading** — All decision points captured upfront, no runtime ambiguity
4. **Structural preservation** — Guardrails prevent destructive changes, content loss detection active
5. **Escalation triggers** — Clear criteria for when autonomous loop must stop and request human input

### What Forces Human-in-Loop

**Irreducible Judgment Requirements:**

1. **Goal ambiguity** — Open-ended objectives require continuous refinement of success criteria
2. **Proportionality context** — Change scope vs severity depends on domain knowledge not capturable as fixed rules
3. **Purpose drift** — Automated metrics can optimize away from original user value without semantic understanding
4. **Downstream impact prediction** — Cross-system effects require knowledge graphs beyond current scope
5. **Diminishing returns** — When to stop refining is a subjective trade-off between effort and value

### Design Implications for the Logical Process

1. **Accept hybrid model** — Human-at-end-of-loop (review after iteration) is more feasible than human-out-of-loop (no review ever). The logical process should support both modes.
2. **Invest in front-loading** — The more that can be captured before the loop begins, the more gates can operate autonomously. Front-loading is the highest-leverage phase.
3. **Detect insufficiency** — If a runtime decision point arises that wasn't covered in front-loading, STOP rather than guess. The ability to detect "I don't have enough information to decide" is itself a critical capability.
4. **Build feedback loops** — Track "questions that arose during execution" and feed them into the next front-loading phase. The system improves over time as front-loading becomes more complete.
5. **Scope determines autonomy** — Narrow problems (fix validation errors) are autonomizable. Broad problems (make skill best-in-class) require continuous human guidance. The logical process must classify scope before selecting autonomy level.

### What This Document Provides for the Expert Panel

- **Section 1:** Patterns of where human judgment is currently required vs successfully replaced, with source citations
- **Section 2:** Classification of every human check into eliminable / front-loadable / irreducible, with reasoning
- **Section 3:** Categories of starting state information required for autonomous operation
- **Section 4:** What the front-loading phase must capture, and when front-loading is sufficient vs insufficient
- **Section 5:** Categories of information an AI reviewer needs to match human review quality

**What remains for the expert panel to determine:** The logical process design — decision trees for each gate, activation conditions for each check, expected outcomes at each stage, and which framework patterns inform each element. This document provides the requirements; the expert panel produces the design.
