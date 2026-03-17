---
name: agent-orchestration
description: Scientific delegation framework for orchestrators coordinating sub-agents. Provides WHERE-WHAT-WHY context patterns while preserving agent autonomy. Use when delegating tasks, structuring sub-agent prompts, planning multi-agent workflows, or coordinating specialist agents.
---
# Agent Orchestration

## Core Principle

**Provide world-building context (WHERE, WHAT, WHY). Define success criteria. Trust agent expertise for HOW.**

The orchestrator's role:

- Route observations between user and agents — never pre-gather data agents will collect themselves
- Define measurable success criteria
- Enable comprehensive discovery via world-building context
- Trust agent expertise and their 200k context windows

**Reason**: Sub-agents are specialized experts with full tool access. Prescribing implementation limits their ability to discover better solutions.

## Scientific Method Alignment

Structure delegation to enable agents to follow the scientific method:

1. **Observation** — Remove all speculation, state what and when observations, not interpretations or guesses at causality.
2. **Hypothesis** — Let agent form their own hypothesis
3. **Prediction** — Let agent make testable predictions
4. **Experimentation** — Let agent design and execute tests
5. **Verification** — Let agent verify against official sources
6. **Conclusion** — Let agent determine if hypothesis is rejected

**Reason**: Agents apply the scientific method most effectively when given observations and success criteria, not pre-formed conclusions.

## Orchestrator Role Boundaries


```mermaid
flowchart TD
    Start(["Orchestrator receives task"]) --> Classify{"Does this action<br>gather data the agent<br>will collect itself?"}

    Classify -->|"No — orchestrator action"| subDo
    Classify -->|"Yes — pre-gathering"| subNo

    subgraph subDo["DO — orchestrator responsibilities"]
        R1["Route context and observations<br>already in scope to agents"]
        R2["Define measurable success criteria<br>for what DONE looks like"]
        R3["Enable comprehensive agent discovery<br>by providing world-building context"]
    end

    subgraph subNo["DO NOT — prohibited actions"]
        N1["Pre-gather data agents<br>will collect themselves"]
        N2["Prescribe HOW agents<br>should implement"]
    end

    subDo --> Delegate(["Delegate via Agent tool"])
    subNo --> Rewrite(["Rewrite prompt to remove pre-gathering<br>or prescription before delegating"])
```

## Pre-Delegation Verification Checklist

Before delegating any task, verify the delegation includes:

1. Observations without speculation on causality.

Here are different examples of how you can share observations:
- You can say 'When <action>, I observed <observation>.' i.e. `When using the Bash tool with "grep -s 'error' some/output/log.txt" it exited with non-zero.`
- You can provide Raw error messages verbatim (not paraphrased)
- You can provide the url or path to the raw error messages or logs
- You can provide console command outputs already received during your work
- You only use language that describes reality such as — "observed", "measured", "reported"
- You do not use hedging language or speculation such as — "I think", "probably", "likely", "seems"

**Pass-Through vs Pre-Gathering:**

- Pass-through (correct) — data already in your context (user messages, prior agent reports)
- Pre-gathering (incorrect) — DO NOT run commands to collect data for the agent
- Example — DO NOT run `ruff check .` before delegating to linting agents
- **Reason**: Pre-gathering wastes context, duplicates agent work, causes context rot

**Definition of Success or Definition of Done:**

- Specific, measurable outcome
- Acceptance criteria with verification method
- WHAT must work, not HOW to implement it

**World-building context:**

- Problem location (WHERE)
- Identification criteria (WHAT)
- Expected outcomes (WHY)
- Available resources and ecosystem conventions

**Preserved agent autonomy:**

- Describe the ecosystem and available environment — never prescribe which tool to use
- Trust agent's empty context window for comprehensive analysis
- Let agent choose implementation approach

## Task Tool Invocation Rule

**When invoking the Agent tool, construct the `prompt` parameter using the Delegation Template below.**

**Reason**: Agents receive observations and success criteria, enabling them to apply expertise. Prescribing line numbers, exact changes, or tool sequences reduces agents to code-editing tools.

## Delegation Template

Start every Task prompt with:

```text
Your ROLE_TYPE is sub-agent.
```

**Reason**: Keeps the agent aligned with sub-agent role and prevents following orchestration rules from CLAUDE.md.

**Full template:**

```text
Your ROLE_TYPE is sub-agent.

[Task identification]

OBSERVATIONS:
- [Factual observations from your work or other agents]
- [Verbatim error messages if applicable]
- [Observed locations: file:line references if already known]
- [Environment or system state if relevant]

DEFINITION OF SUCCESS:
- [Specific measurable outcome]
- [Acceptance criteria]
- [Verification method]
- Solution follows existing patterns found in [reference locations]
- Solution maintains or reduces complexity

CONTEXT:
- Location: [Where to look]
- Scope: [Boundaries of the task]
- Constraints: [User requirements only]

YOUR TASK:
1. Use the `/am-i-complete` checklist as your working guide throughout this task
2. Perform comprehensive context gathering using:
   - Available functions and MCP tools from the <functions> list
   - Relevant skills from the <available_skills> list
   - Project file exploration and structure analysis
   - External resources (CI/CD logs, API responses, configurations)
   - Official documentation and best practices
   - Known issues, forums, GitHub issues if relevant
3. Form hypothesis based on gathered evidence
4. Design and execute experiments to test hypothesis
5. Verify findings against authoritative sources
6. Implement solution following discovered best practices
7. Verify each `/am-i-complete` checklist item as you complete it
8. Only report completion after all `/am-i-complete` criteria satisfied with evidence

INVESTIGATION REQUIREMENTS:
- Trace the issue through the complete stack before proposing fixes
- Document discoveries at each layer (e.g., UI → Logic → System → Hardware)
- Identify both symptom AND root cause
- Explain why addressing root cause instead of patching symptom
- If proposing workaround, document why root cause cannot be fixed

VERIFICATION REQUIREMENTS:
- `/am-i-complete` is the verification check — run it before claiming done
- Use `/am-i-complete` checklists as working guide, not post-mortem report
- Provide evidence for each checklist item as you complete it
- If checklist reveals missing work, complete that work before proceeding

ECOSYSTEM CONTEXT:
- [Authenticated CLIs available: e.g., "`gh` CLI is pre-authenticated for GitHub operations"]
- [Session-specific access: e.g., "CI logs for PR #42 accessible via MCP GitHub tool"]
- [Non-obvious doc locations: e.g., "linting reports in `.claude/reports/`"]
- [Omit anything already in CLAUDE.md — agents inherit CLAUDE.md and do not need it repeated]
```

## Writing Effective ECOSYSTEM CONTEXT

ECOSYSTEM CONTEXT belongs ONLY in the delegation prompt when it contains information the agent cannot find in CLAUDE.md, the project files it will read, or its own tool descriptions.

**The inheritance rule**: Agents automatically inherit both CLAUDE.md files, MEMORY.md, rules files, git status, and all tool descriptions. Do not repeat any of that in ECOSYSTEM CONTEXT — it is noise that displaces real context.

### What belongs in ECOSYSTEM CONTEXT

Include only session-specific or task-specific facts that exist nowhere the agent can see:

**Authenticated CLIs** — whether a CLI is authenticated varies per session; agents cannot assume it:

```text
- The `gh` CLI is pre-authenticated for GitHub operations (issues, PRs, API queries)
- The `glab` CLI is configured for GitLab access
- AWS CLI is configured with credentials for the staging account
```

**Session-specific access** — CI logs, PR context, external resources relevant to this specific task:

```text
- CI logs for PR #42 are accessible via the MCP GitHub tool
- The staging deployment at staging.example.com is available for testing
```

**Non-obvious document locations** — file locations the agent would not discover without a hint:

```text
- Recent linting reports in `.claude/reports/` document previously resolved issues
- Package validation scripts in `./scripts/` — see README.md for usage
```

**Credentials or runtime state that varies** — anything that depends on the current session environment:

```text
- Docker daemon is running and accessible
- The database seed data is loaded at localhost:5432
```

### What does NOT belong in ECOSYSTEM CONTEXT

These items are inherited from CLAUDE.md or tool descriptions — do not repeat them:

- "Full project context available — explore freely" — agents always have full tool access
- "Check `<functions>` list for MCP tools" — tool descriptions already tell agents this
- "Maximize parallel execution" — CLAUDE.md already instructs this
- "Activate relevant skills for domain expertise" — CLAUDE.md already covers skill activation
- "This Python project uses `uv`" — CLAUDE.md already states the toolchain
- Language/toolchain conventions already in CLAUDE.md (uv, pnpm, cargo, etc.)

**Anti-pattern — parroting inherited context:**

```text
ECOSYSTEM CONTEXT:
- Full project context available — explore freely with all tools
- Check <functions> list for MCP tools — prefer MCP specialists over built-in
- This Python project uses `uv` — activate `uv` skill
- Maximize parallel execution for independent tool calls
```

All four lines are already in CLAUDE.md or tool descriptions. This section adds zero information.

**Correct pattern — session-specific facts only:**

```text
ECOSYSTEM CONTEXT:
- The `gh` CLI is pre-authenticated for GitHub operations (issues, PRs, API queries)
- CI logs for PR #42 accessible via MCP GitHub tool
- Recent linting reports in `.claude/reports/` show resolved issues for reference
```

These three lines are not in any CLAUDE.md and vary per session.

**When there is nothing session-specific to add, omit ECOSYSTEM CONTEXT entirely.** The section only earns its place when it contains information the agent cannot find anywhere else.

See [Ecosystem Context Patterns](./references/ecosystem-context-patterns.md) for detailed examples and the documentation fidelity hierarchy for MCP tool selection.

## Inclusion Rules

### INCLUDE — Factual Observations

- "The command returned exit code 1"
- "File X contains Y at line Z"
- "The error message states: [exact text]"
- "Agent A reported: [their findings]"

**Reason**: Exact observations enable agents to form accurate hypotheses and avoid redundant investigation.

### INCLUDE — User Requirements

- "User specified library X must be used"
- "Must be compatible with version Y"
- "Should follow pattern Z from existing code"

### INCLUDE — Verbatim Errors Already in Context

```text
Error: Module not found
  at line 42 in file.js
  Cannot resolve 'missing-module'
```

Include verbatim errors you already encountered, user-provided errors, and prior agent reports. Do NOT pre-gather errors by running linting/testing commands.

### REPLACE — Assumptions with Observations

- Replace "I think the problem is..." → "Observed symptoms: [list]"
- Replace "This probably happens because..." → "Command X produces output Y"
- Replace "It seems like..." → "File A contains B at line C"
- Replace "The likely cause is..." → "Pattern seen in [locations]"

**Reason**: Assumptions create cascade errors. Observations enable agents to apply scientific method.

### DEFINE — WHAT, Not HOW

- Replace "Use tool X to accomplish this" → Describe the ecosystem, let agent select tools
- Replace "The best approach would be..." → Define success criteria, let agent design approach
- Replace "You should implement it by..." → State required outcome, let agent determine method

**Reason**: Agents have domain expertise and comprehensive tool knowledge. Prescriptions limit discovery.

## Context Calibration Patterns

**Focused task (single file, clear test):**

```text
Fix [specific observation] in [exact file]. Success: [test] passes.
```

**Investigative task (unknown cause):**

```text
[All observations from all agents]
[Complete error traces]
[System state information]
Investigate comprehensively before implementing.
```

**Architectural task (multi-component):**

```text
[Full project structure]
[All related agent findings]
[Historical context]
Design solution considering entire system.
```

## Conditional Delegation Logic

<!-- Converted from prose When/bullets: each condition is now an evaluable diamond with explicit actions -->

```mermaid
flowchart TD
    Start(["Building delegation prompt"]) --> Q1{"Does the current context contain<br>user-provided code or quoted text?"}
    Q1 -->|"Yes"| A1["Include verbatim as<br>'User-provided reference'.<br>User-provided patterns override existing rules."]
    Q1 -->|"No"| Q2
    A1 --> Q2

    Q2{"Did an error occur during<br>orchestrator operations<br>before this delegation?"}
    Q2 -->|"Yes"| A2["Include the exact command that triggered the error<br>and the raw error message verbatim.<br>State as observations, not diagnoses."]
    Q2 -->|"No"| Q3
    A2 --> Q3

    Q3{"Are file:line references<br>to existing patterns<br>already known in context?"}
    Q3 -->|"Yes"| A3["Include as 'Pattern reference: file:line'.<br>Do not prescribe changes —<br>let agent discover all instances."]
    Q3 -->|"No"| Q4
    A3 --> Q4

    Q4{"Did the user explicitly mandate<br>a technical constraint —<br>a library, version, or method?"}
    Q4 -->|"Yes — user-mandated"| A4["Include the constraint exactly as<br>the user stated it.<br>Do not add constraints the user did not specify."]
    Q4 -->|"No — not user-mandated"| Q5
    A4 --> Q5

    Q5{"Are there accumulated observations<br>from other agents or prior<br>orchestrator operations?"}
    Q5 -->|"Yes"| A5["Pass all observations with source attribution.<br>Do not filter — include complete context."]
    Q5 -->|"No"| Q6
    A5 --> Q6

    Q6{"Will the prompt reference<br>one or more file paths?"}
    Q6 -->|"Yes — referencing a file"| A6["Use '@filepath' to include file contents.<br>Use '@dirpath/' for directory listings only.<br>'@filepath' auto-includes CLAUDE.md hierarchy."]
    Q6 -->|"No — no file references needed"| Done
    A6 --> Done(["Delegation prompt complete"])
```

## Orchestrator Workflow Requirements

<!-- Converted from numbered list: added entry gate, evaluable conditions, and explicit terminal states -->

```mermaid
flowchart TD
    Start(["Orchestrator receives user request"]) --> A["Identify every ambiguous term<br>in the user request"]
    A --> Q1{"Does the request contain<br>ambiguous terms or multiple<br>valid interpretations?"}
    Q1 -->|"Yes — ambiguity found"| Clarify["Offer interpretations to user<br>and ask which to proceed with"]
    Clarify --> DefineSuccess
    Q1 -->|"No — request is unambiguous"| DefineSuccess
    DefineSuccess["Define success criteria —<br>specific measurable outcome,<br>acceptance criteria, verification method"]
    DefineSuccess --> Q2{"Has the user confirmed<br>the definition of success?"}
    Q2 -->|"No — not confirmed"| Offer["Present definition of success<br>to user for approval or modification"]
    Offer --> Q2
    Q2 -->|"Yes — confirmed"| Include["Include confirmed definition of success<br>in sub-agent Task prompt"]
    Include --> Delegate(["Delegate task via Agent tool"])
    Delegate --> Q3{"Did sub-agent report<br>all acceptance criteria met<br>with evidence?"}
    Q3 -->|"No — criteria not met"| Follow["Follow up with agent<br>or re-delegate with clarification"]
    Follow --> Q3
    Q3 -->|"Yes — all criteria met with evidence"| Done(["Mark task complete"])
```

### Sub-Agent Context Constraints

Sub-agents inherit limited context:

- Receive the system prompt and CLAUDE.md from their working directory hierarchy
- Do NOT automatically inherit orchestrator conversation history
- Cannot receive follow-up answers after responding (unless using 'resume' feature)

Orchestrator must include all necessary context in the initial Task prompt. Instruct agents to "follow guidelines from @~/.claude/CLAUDE.md" when applicable.

## Specialized Agent Assignments

<!-- Converted from flowchart: replaced \n in labels with <br>, made diamond question evaluable -->

```mermaid
flowchart TD
    Agent(["Task to delegate"]) --> Q1{"What is the primary<br>work domain of the task?"}
    Q1 -->|"Context gathering —<br>research without implementation"| CG["context-gathering agent<br>Preserves orchestrator context window"]
    Q1 -->|"Python code —<br>implementation or refactoring"| PY["python-cli-architect agent<br>All Python implementation"]
    Q1 -->|"Python tests —<br>test authoring or fixing"| PT["python-pytest-architect agent"]
    Q1 -->|"Python review —<br>audit or quality check"| PR["python-code-reviewer agent"]
    Q1 -->|"Bash scripts —<br>shell scripting"| BS["bash-script-developer agent"]
    Q1 -->|"Bash review —<br>shell script audit"| BR["bash-script-auditor agent"]
    Q1 -->|"User-facing docs —<br>NOT for LLM-facing docs"| DD["documentation-expert agent"]
    Q1 -->|"System architecture —<br>design decisions"| SA["system-architect agent"]
    Q1 -->|"Linting issues —<br>root cause resolution"| LR["linting-root-cause-resolver agent"]
```

**Critical Rule**: The orchestrator must task sub-agents with ALL code changes, including the smallest edits, and any context gathering or research.

**Reason**: Sub-agents are optimized for their domains. Orchestrator handling code changes bypasses agent expertise and violates separation of concerns.

## Verification Questions for Orchestrators

<!-- Converted from prose checklist with embedded yes/no labels: each question is now an evaluable diamond -->

```mermaid
flowchart TD
    Start(["Delegation prompt drafted"]) --> Q1{"Does the prompt describe the ecosystem<br>and available environment,<br>or does it name a specific tool to use?"}
    Q1 -->|"Names specific tool — LIMITING"| Fix1["Rewrite — describe ecosystem<br>and available resources instead"]
    Q1 -->|"Describes ecosystem — ENABLING"| Q2
    Fix1 --> Q2

    Q2{"Does the prompt use hedging language<br>— 'probably', 'likely', 'I think', 'seems'?"}
    Q2 -->|"Yes — hedging language present — ASSUMPTION"| Fix2["Rewrite — replace assumptions<br>with observed facts: file:line,<br>exit code, exact error text"]
    Q2 -->|"No — all statements are observations — FACT"| Q3
    Fix2 --> Q3

    Q3{"Does the prompt name a specific implementation<br>method, or does it state a success outcome?"}
    Q3 -->|"Names implementation method — HOW"| Fix3["Rewrite — replace implementation<br>instruction with measurable success criteria"]
    Q3 -->|"States measurable outcome — WHAT"| Q4
    Fix3 --> Q4

    Q4{"Does the prompt prescribe specific changes<br>to make, or report observed locations?"}
    Q4 -->|"Prescribes changes — SOLUTION"| Fix4["Rewrite — state observed problem<br>location; let agent determine change"]
    Q4 -->|"Reports observations — OBSERVATION"| Q5
    Fix4 --> Q5

    Q5{"Does the prompt constrain agent<br>to specific docs, or describe the<br>ecosystem context?"}
    Q5 -->|"Constrains to specific docs — DISTRUST"| Fix5["Rewrite — describe ecosystem context;<br>let agent select which to consult"]
    Q5 -->|"Describes ecosystem context — TRUST"| Send(["Send delegation"])
    Fix5 --> Send
```

## Pattern Expansion — From Single Instance to Systemic Fix

When user identifies a code smell, bug, or anti-pattern at a specific location, treat it as a symptom of a broader pattern that likely exists elsewhere.

**What users say vs what they mean:**

- "Fix walrus operator in `_some_func()`" → "Audit and fix ALL instances of this pattern"
- "Add error handling to this API call" → "Audit all similar operations"
- "This validation is duplicated" → "Find and eliminate all instances systemically"

**Reason**: Users point out single instances as examples. Treating them as systemic saves user effort and improves codebase quality comprehensively.

<!-- Converted from flowchart: diamond now states the evaluable question about observable signal properties -->

```mermaid
flowchart TD
    Signal(["User message received"]) --> Q{"Does the user message name<br>a specific code location<br>and did they say 'only this one'?"}
    Q -->|"Yes — user explicitly scoped to one instance"| Single["Treat as single-instance fix —<br>do not expand scope"]
    Q -->|"No — location named without explicit scope limit"| QType{"What category is the<br>named problem?"}
    QType -->|"Code smell at a specific location"| A1["Delegate — audit entire file/module<br>for all instances of this pattern"]
    QType -->|"Missing error handling on one operation"| A2["Delegate — audit all similar<br>operations in the codebase"]
    QType -->|"Duplicated validation logic"| A3["Delegate — find and eliminate<br>all duplication instances systemically"]
    QType -->|"Inefficient loop or iteration pattern"| A4["Delegate — search codebase<br>for all matching patterns"]
    QType -->|"Missing type hint on one function"| A5["Delegate — audit all<br>function signatures in scope"]
    Single --> Done(["Delegation scoped"])
    A1 & A2 & A3 & A4 & A5 --> Done
```

**Include symptom locations (observational):**

- "Error occurs at server.py:142"
- "User reported issue in yq_wrapper.py:274-327"

**State what agent should discover — do not prescribe changes:**

- Replace "Replace server.py:127-138 with helper function" → "User identified duplication pattern at server.py:127-138. Audit entire file for similar patterns."
- Replace "Change line 42 to use walrus operator" → "User identified assign-then-check pattern at line 42. Audit for all instances."

**Default assumption**: Unless user explicitly says "only this one", treat code smell/bug mentions as representative of a broader pattern requiring systemic remediation.

## Holistic vs Micromanaged Delegation

**Micromanaged delegation (prevents agent understanding):**

```text
OBSERVATIONS:
- Walrus operator opportunity at _some_func():45-47

YOUR TASK:
1. Create helper at line 120
2. Replace lines 127-138 with call
3. Replace lines 180-191 with call
```

Problem: Orchestrator already did investigation. Agent becomes code-editing tool without context.

**Holistic delegation (enables agent understanding):**

```text
OBSERVATIONS:
- User identified assign-then-check pattern at _some_func():45-47
- This suggests developer consistently missed walrus operator opportunities
- Code smell indicates systematic review needed across file/module

DEFINITION OF SUCCESS:
- Pattern eliminated from [file/module] scope
- All assign-then-check conditionals converted to walrus where appropriate

YOUR TASK:
1. Verify acceptance criteria via `/am-i-complete` before claiming done
2. Fix the specific instance user identified
3. Audit entire [file/module] for similar patterns
4. Apply same fix to all discovered instances
5. Document pattern occurrences found and fixed
6. Verify `/am-i-complete` checklist items satisfied with evidence
```

## Anti-Patterns to Avoid

**The Pre-Gathering Anti-Pattern**

Running commands to collect data before delegating wastes context and duplicates agent work.

```text
User: "Address linting issues"
Orchestrator runs: ruff check .
Orchestrator pastes: 244 errors into delegation prompt
Problem: Agent runs linting themselves anyway. Wasted orchestrator context.
```

Replace with: "Run linting against the project. Resolve all issues at root cause. Success: pre-commit passes."

**The Assumption Cascade**

"I think the issue is X, which probably means Y, so likely Z needs fixing" — chain of unverified assumptions.

Replace with: "[Observed symptoms]. Success: [desired behavior]. Investigate comprehensively before implementing."

**The Prescription Trap**

"Fix this by doing A, then B, then C" — prevents agent from discovering better approaches.

Replace with: "Fix [observation]. Success: [outcome]. Available resources: [list]."

**The Discovery Limiter**

"Just read these two files and fix the issue" — prevents comprehensive investigation.

Replace with: "Fix [observation]. Success: [outcome]. Full project context available."

**The Tool Dictation**

"Use the MCP GitHub tool to fetch logs" — agent might find better information source.

Replace with: "Investigate [observation]. Available: MCP GitHub tool, local logs, API access."

**The Paraphrase Problem**

"Something about permissions" instead of "Permission denied: /etc/config" — loses diagnostic information.

Replace with: Include exact error messages verbatim (only those already in your context).

**The Context Withholding**

Not sharing observations from other agents forces redundant discovery work.

Replace with: Include all relevant observations from orchestrator and other agents with source attribution.

**The Micromanagement Pattern**

"Use sed to edit line 42, then grep to verify" — wastes agent expertise.

Replace with: "Fix [issue] in [file]. Success: [tests pass]. Solution follows existing patterns."

**The File:Line Prescription**

"Replace lines 127-138 with helper function" — prescribes exact changes instead of defining problem.

Replace with: "User identified duplication at lines 127-138, 180-191. Eliminate duplication following project patterns."

**The Confidence Mask**

Stating uncertainties as facts propagates errors through agent chain.

Replace with: Mark assumptions explicitly — "Observation: [fact]. Hypothesis to verify: [assumption]."

**The Reductive Tool List**

"AVAILABLE RESOURCES: WebFetch, Read, Bash" when agent has 50+ tools including specialized MCP servers.

Replace with: World-building context describing the ecosystem and guiding tool selection.

**Pre-Gathering Anti-Pattern — Detailed:**

Orchestrators route context, agents do work.

- If data exists in context (user message, prior agent output) → pass it through
- If data does not exist yet → delegate with task + success criteria + available resources
- Let agents gather data, analyze, research, and implement

**Reason**: Pre-gathering causes context rot (source: <https://research.trychroma.com/context-rot>). Orchestrator context should coordinate work, not duplicate specialist tasks.

## Examples — Effective Delegation Patterns

**Linting Task — CORRECT:**

```text
"Run linting against the project. Resolve all issues at root cause.

SUCCESS CRITERIA:
- Code quality checks performed per holistic-linting skill
- All configured linting rules satisfied
- Solutions follow existing project patterns

CONTEXT:
- Python project using uv for dependency management
- Linting configured in pyproject.toml

YOUR TASK:
1. Verify acceptance criteria via `/am-i-complete` before claiming done
2. Activate holistic-linting skill
3. Run linting tools to gather comprehensive data
4. Research root causes for each error category
5. Implement fixes following project conventions
6. Verify all criteria satisfied"
```

**Linting Task — INCORRECT:**

```text
Orchestrator runs: ruff check .
Orchestrator pastes: 244 errors into prompt
Problem: Wasted orchestrator context, duplicated agent work, context rot.
```

**Testing Task — CORRECT:**

```text
"Fix failing tests in test_authentication.py.

SUCCESS CRITERIA:
- All tests in test_authentication.py pass
- No new test failures introduced
- Test coverage maintained or improved

CONTEXT:
- Pytest configured in pyproject.toml
- Test fixtures in ./tests/fixtures/
- Authentication module recently refactored

YOUR TASK:
1. Verify acceptance criteria via `/am-i-complete` before claiming done
2. Run pytest to identify failures
3. Investigate root causes
4. Implement fixes
5. Verify all tests pass and coverage maintained"
```

**Error Delegation:**

"Command X produced error: [exact error]. Success: command completes without error. GitHub Actions logs accessible via MCP."

**Feature Delegation:**

"Implement feature that [user requirement]. Success: [measurable outcome]. Project uses [observed tooling]."

**Investigation Delegation:**

"Investigate why [observation]. Document root cause with evidence. Full project context available."

**Fix Delegation:**

"Fix issue where [observation]. Success: [specific working behavior]. Related systems: [list]."

**Complex System Delegation:**

"System exhibits [observation]. Success: [desired behavior]. Available: Docker MCP, GitHub API, project repository."

## Delegation Formula

**Scientific delegation = Observations + Success Criteria + Available Resources - Assumptions - Prescriptions**

This formula:

- Provides complete factual context (enables accurate hypothesis formation)
- Defines clear success metrics (prevents scope ambiguity)
- Enables full toolkit access (allows optimal tool selection)
- Removes limiting assumptions (prevents cascade errors)
- Trusts agent expertise (leverages specialized domain knowledge)

## Final Verification Before Delegation

<!-- Converted from 4-item numbered list with sub-bullets: each check is now an evaluable diamond in sequence -->

```mermaid
flowchart TD
    Start(["Delegation prompt drafted"]) --> C1{"Does the prompt contain<br>hedging language — 'I think',<br>'probably', 'likely', 'seems',<br>'should work'?"}
    C1 -->|"Yes — hedging language present"| Fix1["Replace each hedging phrase:<br>'I think X' → 'Observed: X'<br>'probably Y' → 'Command Z produces Y'<br>'likely W' → 'Pattern seen at [locations]'<br>'should work' → 'Success criteria: [outcome]'"]
    Fix1 --> C2
    C1 -->|"No — language is observational"| C2

    C2{"Does the prompt include<br>all of: raw observations,<br>success criteria, available resources,<br>file locations, and user constraints only?"}
    C2 -->|"No — one or more missing"| Fix2["Add the missing elements.<br>Remove any constraints not stated by the user."]
    Fix2 --> C3
    C2 -->|"Yes — all present"| C3

    C3{"Does the prompt prescribe a tool,<br>name an implementation method,<br>state a solution, or narrow the agent's scope?"}
    C3 -->|"Yes — prescription present"| Fix3["Rewrite the prescriptive parts:<br>Describe ecosystem instead of naming tool.<br>Define WHAT outcome instead of HOW to implement.<br>State the problem instead of the solution."]
    Fix3 --> C4
    C3 -->|"No — autonomy preserved"| C4

    C4{"Does the prompt transcribe<br>file contents inline instead of<br>referencing the file path?"}
    C4 -->|"Yes — contents transcribed inline"| Fix4["Replace inline content with '@filepath'<br>to include file contents via reference.<br>Use '@dirpath/' for directory listings only."]
    Fix4 --> Send
    C4 -->|"No — using path references"| Send(["Send delegation"])
```

---

## Agent Teams — When Subagents Are Not Enough

Agent teams coordinate multiple Claude Code instances with inter-agent messaging and shared task lists. Use subagents when workers report back independently. Use agent teams when workers must share findings, challenge each other, and coordinate among themselves.

### When Agent Teams Apply vs When Subagents Suffice

<!-- Converted from two prose bullet lists: combined into a single decision flowchart with evaluable gates -->

```mermaid
flowchart TD
    Start(["Workflow with multiple units of work"]) --> Q1{"Are there 3 or more<br>independent units of work?"}
    Q1 -->|"No — fewer than 3 units"| UseSubagents(["Use subagents —<br>coordination overhead not justified"])
    Q1 -->|"Yes — 3 or more units"| Q2

    Q2{"Do the units need to share findings<br>with each other during execution<br>— not just report back to orchestrator?"}
    Q2 -->|"No — units are fully independent"| UseSubagents
    Q2 -->|"Yes — findings from one inform or challenge another"| Q3

    Q3{"Will any two units<br>write to the same file?"}
    Q3 -->|"Yes — shared file mutations"| UseSubagents
    Q3 -->|"No — no shared file mutations"| Q4

    Q4{"Is the final result a synthesis<br>or reconciliation of findings,<br>not just a collection?"}
    Q4 -->|"No — result is concatenation only"| UseSubagents
    Q4 -->|"Yes — value comes from combining findings"| UseTeams(["Use agent teams —<br>all four criteria satisfied"])
```

See [Agent Teams Documentation](./../../../plugin-creator/skills/claude-skills-overview-2026/resources/agent-teams.md) for complete criteria, architecture, and usage patterns.

SOURCE: Lines 10-39 of agent-teams.md (accessed 2026-02-06)
