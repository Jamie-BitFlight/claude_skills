# Context-Fit Complexity: Adoption Conditions

Companion to [complexity-fit-and-economics-of-agents.md](./complexity-fit-and-economics-of-agents.md).

That document asks: are these claims true? This document asks: given what I can observe right now, should I apply this concept here?

Each section maps one concept to four observable criteria. No claim about universal applicability is made — each criterion references a condition you can check before committing to the approach.

---

## Concept 1: Measure complexity as context-fit, not implementation difficulty

**Apply when:**
- An agent is failing tasks that a human would call "easy" (small LOC, clear logic)
- Task failure rate does not correlate with algorithm complexity — simple CRUD operations fail as often as complex transformations
- Post-mortems on failed agent tasks consistently show the agent had the right approach but wrong project-specific details

**Skip when:**
- Tasks are failing due to tool errors, API unavailability, or flaky test infrastructure — context-fit is not the variable in those failures
- All tasks involve pure algorithmic work with no project-specific context (e.g., a standalone math library with no external dependencies)

**Evidence it is working:**
- You can predict task success rate from context load count (files read before first edit) better than from LOC changed
- Reducing the knowledge payload for a task (by making upstream outputs more complete) raises success rate without changing the implementation

**Evidence it is not working:**
- Success rate tracks LOC changed or cyclomatic complexity regardless of context load
- Agents fail on tasks where all required context was explicitly provided in the prompt

---

## Concept 2: Use the three-term equation (knowledge + uncertainty + overhead)

**Apply when:**
- You need a scoring system to decide whether to split a task or keep it whole
- You want to prioritize which backlog items need knowledge prep before execution
- Task estimates are consistently wrong and you suspect the missing variable is context acquisition time

**Skip when:**
- Tool reliability is the primary failure mode — flaky MCP servers, rate limits, or network errors dominate your failure logs. The three-term equation does not model tool infrastructure.
- Instruction ambiguity is the primary failure mode — agents produce correct work but on the wrong interpretation of the task. The equation does not model prompt clarity.

**Evidence it is working:**
- Tasks scored high on the equation take longer, require more retries, or produce more hallucinated claims than low-scored tasks
- Interventions that reduce a specific term (e.g., resolving unknowns before execution reduces the uncertainty term) produce measurable improvement

**Evidence it is not working:**
- High-scored tasks succeed on the first attempt without special handling
- Low-scored tasks fail repeatedly despite minimal equation cost
- If this happens, check whether tool reliability or instruction ambiguity is the actual driver before discarding the equation

---

## Concept 3: Decompose at knowledge boundaries, not code boundaries

**Apply when:**
- A task requires reading documentation for Module A before editing Module B, and the two modules have no shared callers
- Two steps that touch the same file require completely different reference material (e.g., one step needs the API schema, the other needs the deployment config)
- An agent is context-exhausted mid-task even though the individual code changes are small

**Skip when:**
- The codebase is tightly coupled — knowledge boundaries and code boundaries are the same thing in most places
- Tasks are small enough that a single agent can load all required knowledge with capacity to spare
- The task has ordering constraints that override knowledge grouping (e.g., Step 2 must read Step 1's output even if they share no knowledge payload)

**Evidence it is working:**
- Agents assigned to knowledge-bounded tasks reach their first edit faster (fewer read tool calls before the first write)
- Fewer "I need to check X first" mid-task pivots that consume context before any implementation starts

**Evidence it is not working:**
- Knowledge-bounded tasks produce more coordination overhead than they save (agents need each other's outputs before they can proceed, creating sequential dependencies that cancel the benefit)
- The knowledge boundary split creates tasks so narrow that each one requires a full context reload for a trivial change

---

## Concept 4: Hardcode stable constraints; discover volatile constraints dynamically

**Apply when:**
- A constraint in a SKILL.md, CLAUDE.md, or agent prompt has been edited more than twice in the past three months (check: `git log --follow -p <file>`)
- An agent recently produced incorrect output because a hardcoded value was stale (pricing tier, API version, team convention that changed)
- You are writing a new constraint and the thing it references changes on a per-project or per-environment basis

**Skip when:**
- The constraint references something that has not changed since the file was created
- Discovery at runtime is expensive (requires a network call, a file read of a large document, or a slow tool) and the constraint is correct 95%+ of the time

**Evidence it is working:**
- Agents stop producing stale-constraint errors after volatile constraints are moved to dynamic lookup
- The constraint source file (where the dynamic lookup reads from) is updated in one place and immediately reflected in all tasks that use it

**Evidence it is not working:**
- Dynamic lookup adds latency or failure modes that the hardcoded version did not have
- The constraint source changes so frequently that even dynamic lookup is stale within a single task execution

---

## Concept 5: Progressive disclosure — load minimum context per step

**Apply when:**
- A task has 3+ sequential steps where each step's required knowledge is mostly disjoint from the others
- Agents are losing earlier instructions by the time they reach later steps (observable: the agent re-reads files it already read, or ignores constraints stated early in the prompt)
- Context window is routinely near-full before the last step executes

**Skip when:**
- Steps have cross-cutting concerns — Step 3 needs to know about a constraint introduced in Step 1's reference material
- The task has only 2 steps — the overhead of progressive loading adds complexity that does not pay off at that scale
- The agent needs to make architectural decisions early that depend on knowledge from later steps (lookahead requirement)

**Evidence it is working:**
- Later steps follow earlier constraints more reliably when those constraints are not competing with 50,000 tokens of earlier reference material
- Total tokens per task decreases because unused knowledge for later steps is never loaded during earlier steps

**Evidence it is not working:**
- Agents miss cross-step dependencies and produce inconsistent implementations across steps
- The orchestrator spending overhead (routing knowledge to the right step at the right time) consumes more tokens than the savings from not preloading

---

## Concept 6: Context garbage collection — retire consumed intermediate artifacts

**Apply when:**
- A session is accumulating tool output that will not be referenced again (raw search results that have been summarized, failed attempt transcripts, verbose build logs)
- An agent in a long session starts referencing conclusions from early failed attempts as if they were valid findings
- Context is near-full but the remaining work is small

**Skip when:**
- The session is short (under 10 tool calls) — the overhead of tracking and removing artifacts exceeds the benefit
- All intermediate output is still potentially relevant (e.g., the agent is debugging and earlier failed attempts contain relevant evidence)

**Evidence it is working:**
- Agents in compacted sessions make fewer references to resolved or superseded conclusions
- Sessions reach task completion with more context headroom remaining

**Evidence it is not working:**
- Compaction removes context the agent later needed (observable: the agent asks for information it had earlier, or re-reads files it had already summarized)
- The compaction step itself (summarizing, deciding what to keep) consumes more tokens than the stale context would have

---

## Concept 7: Turn unknown unknowns into known unknowns through structured enumeration

**Apply when:**
- A previous attempt at a similar task failed at a point that was not anticipated during planning
- The task touches an area of the codebase with no recent test coverage or documentation
- The implementation plan has steps labeled "investigate X" without specifying what a successful investigation looks like

**Skip when:**
- The task is identical to one that was completed successfully recently — the unknowns are already known from that prior run
- The domain is fully documented and the agent has successfully executed in it before without surprises
- Time pressure makes upfront enumeration impractical — in that case, accept the higher failure-during-execution rate as a known tradeoff

**Evidence it is working:**
- The enumeration step surfaces at least one blocking unknown that would have caused a mid-execution failure
- Agents that enumerate prerequisites before starting produce fewer "I cannot proceed because X is unclear" mid-task stops

**Evidence it is not working:**
- Enumeration consistently produces empty or trivially satisfied prerequisite lists — the domain is well-understood and enumeration adds overhead without discovery
- Unknowns surface during execution regardless (the enumeration does not help because the blocking unknowns are not the kind that can be found by reading files or running checks upfront)

---

## Concept 8: Persistent sessions amortize context loading cost

**Apply when:**
- You have 3+ related subtasks that all require reading the same large set of reference files before executing
- The shared context is stable across all subtasks (it does not change between task 1 and task 5)
- Output per subtask is modest — the session does not grow primarily from output tokens

**Skip when:**
- Subtasks are independent with minimal shared context — the cache amortization benefit does not apply when each task needs a different knowledge payload
- Subtask outputs are large (e.g., each subtask generates 2,000+ tokens of output) — output token cost dominates regardless of input cache savings
- Cross-task contamination risk is high — prior task conclusions could incorrectly anchor later tasks

**Evidence it is working:**
- Token cost for N related subtasks in one session is lower than N × cost-per-isolated-session
- Agents in the persistent session do not re-read shared reference files between subtasks

**Evidence it is not working:**
- Session cost grows faster than isolated sessions because output accumulation exceeds cache savings
- Later subtasks in the session show quality degradation — earlier conclusions are anchoring incorrect assumptions in later work

---

## Concept 9: Context bloat degrades persistent session quality

**Apply when (i.e., when to apply compaction to a persistent session):**
- A persistent session has completed 2+ subtasks and the context is growing with accumulated intermediate output
- An agent references a conclusion from an earlier subtask that has since been superseded
- The running context size is above 60% of the model's effective context window

**Skip compaction when:**
- The session is still on its first subtask — bloat has not accumulated yet
- All prior context is still directly relevant to the current subtask
- The compaction step would remove evidence needed for debugging a current failure

**Evidence bloat is the problem (not other factors):**
- Quality degradation onset correlates with context size growth, not with task number or time elapsed
- Compacting the session and re-running the current subtask produces better output than continuing in the bloated session

**Evidence bloat is not the problem:**
- Quality is consistent across subtask 1 through subtask 5 even with accumulated context
- Degradation tracks task complexity, not session length

---

## Concept 10: Classify tasks by context-fit spectrum before choosing strategy

**Apply when:**
- You are deciding whether to use a single agent or split across multiple parallel agents
- A single-agent task is failing with context exhaustion errors or quality degradation in later steps
- You want to predict whether a new task needs a parallel agent team before committing to implementation

**The three regions and their signals:**

**Zero-overhead execution** — all required inputs are already present in the prompt in directly usable form:
- Observable signal: the agent's first tool call is a write or create, not a read
- Correct strategy: single agent, no special handling
- Wrong strategy: splitting this into parallel agents adds coordination overhead with no benefit

**Single-agent loading zone** — task fits in one agent after some context acquisition:
- Observable signal: the agent reads 2–8 files before the first write, then executes without re-reading
- Correct strategy: single agent with progressive disclosure if steps are sequential
- Wrong strategy: splitting this wastes parallel coordination overhead

**Knowledge-boundary scale-out** — task requires multiple distinct knowledge domains that do not fit comfortably together:
- Observable signal: the agent reads 10+ files, re-reads earlier files mid-task, or shows quality degradation after a certain point in execution
- Correct strategy: split at knowledge boundaries into parallel agents, each with a narrow context
- Wrong strategy: forcing this into a single agent produces context exhaustion or knowledge-gap failures

**Evidence of misclassification:**
- You classified a task as loading-zone and the agent exhausted context — reclassify as scale-out
- You classified a task as scale-out and the parallel agents spent more tokens coordinating than executing — reclassify as loading-zone

---

## Concept 11: Iterative knowledge discovery via speculation detection

**Apply when:**
- You are building a SKILL.md or agent prompt for a new domain and do not know what the minimum viable knowledge set is
- A skill or agent is producing speculative claims (outputs that assert project-specific facts not present in its loaded context)
- You want to build reusable agent knowledge for a domain without loading comprehensive documentation every time

**Skip when:**
- The domain is already well-covered by an existing skill — load that skill instead of re-discovering the knowledge set
- The task is a one-off — the cost of running the discovery loop exceeds the benefit of having a reusable knowledge set
- The domain has no stable invariants — if the facts change on every project, a seeded skill will not transfer

**Evidence it is working:**
- Each iteration reduces the speculative claim count in the agent's output
- The final seeded knowledge set is smaller than the full documentation set (it achieved coverage selectivity)
- A different agent loaded with the discovered seed produces equivalent output to an agent loaded with the full documentation

**Evidence it is not working:**
- Speculative claim count does not decrease across iterations — the auditor is not identifying the right missing knowledge units
- The converged seed is nearly as large as the full documentation (no selectivity was achieved)
- The agent produces correct output only when the full documentation is loaded, not when the seed is loaded

---

## Adoption Sequence

If you are applying these concepts to a project for the first time, this order reduces wasted effort:

1. **C4 first** (volatile vs stable constraints) — git log audit, no agent runs, immediate payoff if stale constraints are present
2. **C7** (unknown enumeration) — add a prerequisite checklist to the next task you run; observe whether it surfaces a blocker before execution
3. **C10** (spectrum classification) — classify the next 5 tasks you assign before assigning them; check whether your classification matches what actually happens
4. **C1/C2** (complexity equation) — score the next 10 tasks on the three terms; check whether score correlates with outcome
5. **C3** (knowledge-boundary decomposition) — apply to the next multi-step task that fails or shows context strain
6. **C5/C6** (progressive disclosure + garbage collection) — apply together to the next long session
7. **C8/C9** (session economics) — apply when you have a batch of related subtasks; instrument token cost to verify the savings claim
8. **C11** (iterative discovery) — apply when you are creating a new SKILL.md for an unfamiliar domain

---

## Cross-Reference

- Claim definitions and experiment designs: [complexity-fit-and-economics-of-agents.md](./complexity-fit-and-economics-of-agents.md)
- Codified model: [sdlc-layers/layer-0/context-fit-complexity.md](./sdlc-layers/layer-0/context-fit-complexity.md)
- RT-ICA (uncertainty resolution in practice): `/dh:planner-rt-ica`
- Orchestrator discipline (context window management): `.claude/rules/orchestrator-discipline`
