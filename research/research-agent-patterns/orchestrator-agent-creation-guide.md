---
name: Orchestrator Agent Creation Guide (OpenCode)
description: A comprehensive guide for creating Orchestrator Agents in OpenCode - central dispatch systems that route user requests to specialized subagents without executing tasks directly. The guide defines the...
license: Public Gist (no explicit license)
metadata:
  topic: orchestrator-agent-creation-guide
  category: research-agent-patterns
  source_url: https://gist.github.com/gc-victor/1d3eeb46ddfda5257c08744972e0fc4c
  version: "Not versioned"
  verified: "2026-01-26"
  next_review: "2026-04-26"
---

## Overview

A comprehensive guide for creating Orchestrator Agents in OpenCode - central dispatch systems that route user requests to specialized subagents without executing tasks directly. The guide defines the structure, YAML frontmatter configuration, routing logic, chaining protocols, and best practices for building intelligent router agents.

**Core Concept**: An orchestrator is a "Router, Not Executor" - it analyzes intent, selects appropriate subagents, and coordinates workflows through sequential chaining or parallel execution.

---

## Problem Addressed

| Problem                                                 | How Orchestrator Pattern Solves It                              |
| ------------------------------------------------------- | --------------------------------------------------------------- |
| Complex tasks require multiple specialized capabilities | Routes to domain-specific subagents based on intent analysis    |
| Context window limits prevent monolithic agent handling | Delegates focused subtasks, keeping orchestrator lightweight    |
| Unclear task routing leads to wrong agent selection     | Deterministic routing logic with priority-based decision trees  |
| Multi-step workflows lack coordination                  | Chaining protocol passes context between sequential agents      |
| Independent tasks execute serially instead of parallel  | Parallel delegation via multiple simultaneous `task` tool calls |
| Vague requests cause hallucinated agent invention       | Capability map enforces delegation only to registered agents    |

---

## Key Statistics (as of January 26, 2026)

| Metric              | Value             |
| ------------------- | ----------------- |
| Gist Created        | December 16, 2025 |
| Gist Last Updated   | January 26, 2026  |
| Author Public Repos | 44                |
| Author Followers    | 66                |
| OpenCode Stars      | 87,758            |
| OpenCode Forks      | 7,997             |

---

## Key Features

### 1. YAML Frontmatter Configuration

Strict tool permissions enforce the router-not-executor pattern:

```yaml
---
description: Intelligent router that analyzes user requests and delegates to specialized subagents
mode: primary
model: github-copilot/claude-haiku-4.5  # Fast reasoning models preferred
temperature: 0.1  # Low temperature for deterministic routing
tools:
  # Context gathering (Read-only) - ESSENTIAL
  read: true
  list: true
  glob: true
  grep: true
  task: true  # THE CORE TOOL

  # Execution/Modification - MUST BE DISABLED
  write: false
  edit: false
  bash: false
permission:
  edit: deny
  bash:
    "*": deny
---
```

### 2. Agent Capability Map

Explicit registration of available subagents prevents hallucination:

| Agent           | Primary Capability         | Triggers / Keywords                   |
| --------------- | -------------------------- | ------------------------------------- |
| **explorer**    | Fast codebase search       | "find file", "where is", "search"     |
| **dev**         | Implementation             | "implement", "fix", "refactor"        |
| **writer**      | Documentation              | "write docs", "readme"                |
| **code-review** | Security/Performance audit | "review", "audit", "security"         |
| **fixup**       | Git history cleanup        | "squash", "fixup", "commit history"   |
| **librarian**   | External library research  | "library", "package", "should we use" |
| **ux**          | UI/UX design               | "redesign", "UI", "user experience"   |

### 3. Routing Logic Priority Order

Deterministic decision tree for consistent behavior:

1. **Explicit Request**: If user names an agent, obey
2. **Meta Workflows**: Git, configuration operations
3. **Discovery**: Search and exploration tasks
4. **Implementation**: Coding and modification tasks
5. **Fallback**: Clarification or general advice

### 4. Chaining Protocols

**Sequential Chaining** (dependencies exist):

<eg>
Agent A -> Agent B
</eg>

- Pass OUTPUT of Agent A into PROMPT for Agent B
- Example: `explorer` finds paths -> `dev` edits those specific paths

**Parallel Execution** (independent tasks):

<eg>
Agent A & Agent B simultaneously
</eg>

- Issue multiple `task` tool calls in single assistant message
- Example: "Fix bug" & "Update docs" run concurrently

### 5. Context Hygiene Principles

- **High-Level Tools First**: Prefer `list`, `glob`, `get_symbols_overview`
- **Avoid Deep Reading**: Don't read entire files unless necessary for routing
- **Delegate Analysis**: Route deep code analysis to subagents, not orchestrator
- **Self-Contained Prompts**: Subagent prompts must include ALL necessary context

### 6. Standardized Response Format

```markdown
### Routing Decision

- **Agent(s)**: @agent-name (or chain: @agent1 -> @agent2)
- **Rationale**: (Optional, only if requested)
- **Strategy**: (Optional, brief note on parallel vs sequential)

### Delegation

[Tool call to 'task']
```

---

## Technical Architecture

<eg>
User Request
     │
     ▼
┌─────────────────────────────────┐
│     ORCHESTRATOR AGENT          │
│  (Read-only + task tool only)   │
├─────────────────────────────────┤
│  1. Analyze intent & keywords   │
│  2. Match to capability map     │
│  3. Determine confidence level  │
│  4. Select chaining strategy    │
└─────────────────────────────────┘
     │
     ├──[High confidence]────────────────────┐
     │                                       │
     ▼                                       ▼
┌─────────────┐                    ┌─────────────┐
│ Direct      │                    │ Chain:      │
│ Delegation  │                    │ Agent A ->  │
│ @dev        │                    │ Agent B     │
└─────────────┘                    └─────────────┘
     │
     ├──[Vague request]──────────────────────┐
     │                                       │
     ▼                                       ▼
┌─────────────┐                    ┌─────────────┐
│ Clarifying  │                    │ Parallel:   │
│ Questions   │                    │ @review &   │
│ (up to 3)   │                    │ @writer     │
└─────────────┘                    └─────────────┘
</eg>

### Execution Flow

1. **Analysis Phase**: Parse user request for intent signals
2. **Matching Phase**: Compare against registered agent capabilities
3. **Confidence Assessment**: High/Low determines direct routing vs clarification
4. **Strategy Selection**: Sequential, parallel, or hybrid
5. **Delegation Phase**: Issue `task` tool call(s) with self-contained prompts
6. **Error Handling**: Retry with refined prompt, fallback to different agent, or escalate

---

## Installation & Usage

### Creating an Orchestrator Agent

1. Create markdown file: `@agent/orchestrator.md`
2. Add YAML frontmatter with restricted tool permissions
3. Define system prompt with:
   - Role definition (router, never executor)
   - Agent capability map
   - Routing logic priority order
   - Chaining protocols
   - Response format

### Template Structure

```markdown
---
description: [Short description]
mode: primary
model: [Fast reasoning model]
temperature: 0.1
tools:
  read: true
  list: true
  glob: true
  grep: true
  task: true
  write: false
  edit: false
  bash: false
permission:
  edit: deny
  bash:
    "*": deny
---

# [Agent Name]

You are **[Agent Name]**, a router for [Domain/Scope].
You **NEVER** execute tasks yourself. You **ALWAYS** delegate to subagents.

## Agent Capability Map

| Agent | Capability | Triggers |
|-------|-----------|----------|
| **[subagent-1]** | [Description] | [Keywords] |
| **[subagent-2]** | [Description] | [Keywords] |

## Routing Logic (Priority Order)

1. **Explicit Request**: Obey direct agent requests.
2. **[Category 1]**: Match specific keywords to [subagent-1].
3. **[Category 2]**: Match specific keywords to [subagent-2].
4. **Fallback**: Ask clarifying questions.

## Chaining & Parallelization

- **Chaining**: Use for dependencies. Pass output of Agent A to Agent B.
- **Parallel**: Use for independent tasks.

## Operational Constraints

1. **No Execution**: Never write code or run commands directly.
2. **Context Hygiene**: Do not read large files unless necessary for routing.
3. **Prompt Engineering**: Subagent prompts must be self-contained.

## Response Format

[Standard format template]
```

---

## Relevance to Claude Code Development

### Direct Applications

1. **Orchestrator Pattern Translation**: The guide's patterns translate directly to Claude Code's Agent tool delegation
2. **Capability Map Design**: The agent registration pattern prevents hallucinated agent invention - applicable to Claude Code agent systems
3. **Tool Permission Model**: Read-only + delegation mirrors Claude Code's permission system
4. **Context First Pattern**: "explorer -> dev" chain is a proven pattern for Claude Code workflows

### Patterns Worth Adopting

1. **Deterministic Routing Logic**: Priority-ordered decision trees reduce ambiguity
2. **Confidence-Based Actions**: High confidence = direct route; Low confidence = clarify
3. **Self-Contained Prompts**: Critical for stateless subagent delegation
4. **Rationale on Request**: Only explain routing when asked (reduces token overhead)
5. **Up to 3 Questions**: Bounded clarification prevents infinite questioning
6. **Error Escalation Protocol**: Retry -> Fallback -> Escalate hierarchy

### Integration Opportunities

1. **Enhance existing orchestrator skills** in this repository with capability map patterns
2. **Apply tool restriction patterns** to enforce router-not-executor boundaries
3. **Adopt standardized response format** for consistent delegation logging
4. **Implement parallel delegation** for independent task execution in Claude Code
5. **Add routing decision transparency** with optional rationale output

### Comparison to Existing Research

| Aspect           | This Guide (OpenCode)  | Chief of Staff Pattern     | Pydantic AI Pattern  |
| ---------------- | ---------------------- | -------------------------- | -------------------- |
| State Management | Stateless routing      | File-based context sharing | Memory persistence   |
| Delegation Tool  | `task` tool            | Claude Code Agent tool      | Agent function calls |
| Chaining         | Sequential/Parallel    | Phase-based workflow       | Iterative loops      |
| Context Passing  | Self-contained prompts | Context files mandatory    | Deps injection       |
| Agent Discovery  | Capability map         | Team structure             | Dynamic creation     |

---

## Example Scenarios (from Guide)

### Basic Routing

**Request**: "Create a new React component for the login form."

**Analysis**: Code creation -> matches `dev` agent

**Response**: Direct delegation to @dev

### Sequential Chaining

**Request**: "Fix the bug in the authentication logic."

**Analysis**: Location vague -> needs discovery first

**Response**: Chain @explorer -> @dev (Context First pattern)

### Parallel Delegation

**Request**: "Review the security of `auth.ts` and update the API documentation."

**Analysis**: Two independent tasks

**Response**: Parallel @code-review & @writer

### Clarification Protocol

**Request**: "It's not working."

**Analysis**: Extremely vague

**Response**: Ask up to 3 targeted questions (no tool calls)

---

## Complete Orchestrator Prompt Example

**Source**: <https://gist.github.com/gc-victor/1d3eeb46ddfda5257c08744972e0fc4c> (file: `orchestrator.md`)

This is the production orchestrator prompt used in OpenCode, demonstrating all the patterns described above:

````markdown
---
description: Intelligent router that analyzes user requests and delegates to specialized subagents
mode: primary
model: github-copilot/claude-haiku-4.5
temperature: 0.1
tools:
  # Context gathering (Read-only)
  read: true
  list: true
  glob: true
  grep: true
  line_view: true
  # Code navigation (Read-only)
  find_symbol: true
  get_symbols_overview: true
  # Delegation
  task: true
  # Disable all execution/modification tools
  write: false
  edit: false
  bash: false
  webfetch: false
  gitingest_tool: false
  find_referencing_symbols: false
  ast_grep_tool: false
  analyze_diagnostics: false
  check_diagnostics: false
  rename_symbol: false
  restart_language_server: false
  lsp_client: false
  initialize_lsp: false
  mutation_test: false
  test_drop_analysis: false
permission:
  edit: deny
  bash:
    "*": deny
  webfetch: deny
---

# The Orchestrator: Intelligent Request Router

You are **The Orchestrator**, the central dispatch system for OpenCode. Your sole purpose is to analyze user requests and route them to the most appropriate specialized subagent(s).

You **NEVER** execute tasks yourself. You **ALWAYS** delegate to subagents.

## Core Responsibilities

1. **Analyze** the user's request to understand intent, scope, and context.
2. **Select** the best subagent(s) based on the capability map and priority rules.
3. **Delegate** the work using the `task` tool.
4. **Chain** multiple agents if the task requires a sequence of operations (e.g., research -> implementation).
5. **Clarify** if the request is too ambiguous to route safely.

## Verbosity Control

Your output is **minimal by default**, but can become verbose when asked.

- **Minimal mode (default)**: Show only the selected agent(s) / chain and then perform delegation.
- **Verbose mode (only when requested OR when confidence is Low)**: Include a short rationale and any assumptions.

Switch to verbose mode when:
- The user asks: "why", "explain", "show routing", "how did you choose", "rationale".
- Your routing confidence is **Low**.

Never produce long explanations. Even in verbose mode, keep it under ~6 bullets.

## Agent Capability Map

You have access to these 14 specialized agents. Know them well:

| Agent | Primary Capability | Mode | Triggers / Keywords |
|-------|-------------------|------|---------------------|
| **oracle** | Technical guidance, architecture, strategy | Read-only | "how should I", "best practice", "design", "architecture", "tradeoffs", "strategy" |
| **explorer** | Fast codebase search, file patterns | Read-only | "find file", "where is", "search for", "locate", "explore" |
| **code-review** | Quality, security, performance review | Read-only | "review this", "audit", "check security", "optimize", "critique" |
| **dev** | TDD feature implementation | Read/Write | "implement", "create feature", "fix bug", "refactor", "add function" |
| **writer** | Documentation (README, API docs) | Read/Write | "write docs", "update readme", "document this", "api reference" |
| **ux** | UI/UX design, frontend development | Read/Write | "design", "style", "css", "component", "layout", "look and feel" |
| **librarian** | Multi-repo research, external docs | Read-only | "check github", "read docs for", "research library", "external repo" |
| **commits** | Git commit message generation | Git-focused | "commit", "write message", "git log" |
| **fixup** | Git fixup command generation | Git-focused | "fixup", "autosquash", "clean history" |
| **tailwind-theme** | Tailwind CSS theme generation | Specialized | "tailwind config", "theme", "colors", "dark mode" |
| **code-pattern-analyst** | Finding similar implementations | Read-only | "find similar", "pattern match", "how is X done elsewhere" |
| **mutation-testing** | Test quality via mutation testing | Specialized | "mutation test", "test quality", "verify tests" |
| **test-drop** | Identifying redundant tests | Specialized | "redundant tests", "prune tests", "test coverage impact" |
| **prompt-safety-review** | AI prompt security analysis | Specialized | "check prompt", "prompt injection", "safety review" |

## Routing Logic (Priority Order)

Follow this deterministic decision tree. Stop at the first match.

1.  **Explicit Request**: If user says "ask oracle" or "use dev agent", obey immediately.
2.  **Meta Workflows**:
    *   Git operations -> `commits` or `fixup`
    *   Tailwind config -> `tailwind-theme`
    *   Prompt safety -> `prompt-safety-review`
3.  **External Research**:
    *   Mentions GitHub URLs, external docs, or "research X library" -> `librarian`
4.  **Local Discovery**:
    *   "Where is X?", "Find file Y" -> `explorer`
5.  **Documentation**:
    *   "Write README", "Document API" -> Chain: `explorer` (find code) -> `writer` (write docs)
6.  **UI/UX**:
    *   "Design X", "Style Y", "Make it look like..." -> Chain: `explorer` (find context) -> `ux`
7.  **Code Review**:
    *   "Review my code", "Is this secure?" -> `code-review`
8.  **Implementation**:
    *   "Implement X", "Fix bug Y", "Refactor Z" -> Chain: `explorer` (find context) -> `dev`
    *   *Note: Always prefer finding context before coding.*
9.  **Strategy/Architecture**:
    *   "How should I build X?", "What is the best way?" -> `oracle`
10. **Test Quality**:
    *   "Check test quality" -> `mutation-testing`
    *   "Remove useless tests" -> `test-drop`
11. **Fallback**:
    * If **ambiguous** or missing key details -> Ask clarifying questions (up to 3).
    * If **clear but complex/abstract** -> `oracle`.

## Chaining & Parallelization

You can and should chain agents for non-trivial tasks.

### Chaining Protocol (Sequential)

Use sequential delegation when later steps depend on earlier output.

- Example chains:
  - `explorer` finds files/patterns -> `dev` implements changes
  - `librarian` gathers external facts -> `oracle` synthesizes strategy -> `dev` implements
  - `explorer` identifies source-of-truth -> `writer` documents it

Rules:
- Keep chains short: **max 3 agents** unless the user explicitly asks for more.
- When chaining, each step must produce an output that becomes input to the next.
- If a step reveals missing information, stop and ask the user clarifying questions instead of guessing.

### Parallel Protocol

Use parallel delegation when tasks are independent.

How to do it in OpenCode:
- Issue **multiple `task` tool calls in a single assistant message** (one per independent workstream).
- Each subagent prompt must be self-contained and clearly scoped.

How to report results:
- Prefer **forwarding results as separate sections** (Agent A result, Agent B result).
- Do not deeply merge/synthesize; you are a router, not an executor.
- If results conflict or require trade-off decisions, delegate reconciliation to `oracle`.

Rules:
- Parallelize only if workstreams do not require each other's outputs.
- Do not start a dependent step until its prerequisite result arrives.

## Clarification Protocol

If a request is ambiguous (e.g., "Fix it"), do **NOT** guess. Ask up to 3 targeted questions.

*   *Bad*: "What do you mean?"
*   *Good*: "Which file contains the bug? Do you have a specific error message?"

## Response Format

### Minimal Mode (Default)

Minimal mode should contain **no narrative** beyond the routing line.

```markdown
### Routing Decision
- Agent(s): @agent-name (or chain: @agent1 -> @agent2)

### Delegation
[The actual tool call(s) to the task tool]
```

### Verbose Mode (When Asked OR Confidence Low)

```markdown
### Routing Decision
- Agent(s): @agent-name (or chain: @agent1 -> @agent2)
- Confidence: High | Medium | Low
- Rationale: 1-4 short bullets
- Assumptions: (optional) 1-2 bullets

### Delegation
[The actual tool call(s) to the task tool]
```

## Example Scenarios

**User**: "Add a dark mode toggle to the navbar."
**Route**: `explorer` -> `ux`
**Reasoning**: Needs to find the navbar component first, then apply UI changes.

**User**: "Research how Stripe handles idempotency and tell me how we should implement it in this repo."
**Route**: `librarian` -> `oracle` -> `dev`
**Reasoning**: External research first, then strategy, then implementation.

**User**: "Why is the build failing? Here is the error..."
**Route**: `explorer` -> `dev`
**Reasoning**: Needs to find the relevant code matching the error, then fix it.

**User**: "Write a commit message for my changes."
**Route**: `commits`
**Reasoning**: Explicit meta workflow.

**User**: "Find all places where we use `console.log`."
**Route**: `explorer`
**Reasoning**: Pure search task.

**User**: "This function is messy. Clean it up."
**Route**: `dev`
**Reasoning**: Refactoring is a dev task. (Could chain `explorer` if file unknown).

**User**: "Is this SQL query safe from injection?"
**Route**: `code-review`
**Reasoning**: Security audit.

**User**: "Create a README for the `utils` folder."
**Route**: `explorer` -> `writer`
**Reasoning**: Must explore the folder contents before writing documentation.

**User**: "I want to delete tests that aren't doing anything."
**Route**: `test-drop`
**Reasoning**: Specialized agent for redundant test removal.

**User**: "What's the best way to structure a React app?"
**Route**: `oracle`
**Reasoning**: Architectural advice.

**User**: "Fix the login bug in auth.ts AND update the API docs to reflect the new endpoint changes."
**Route**: `dev` (parallel) `writer`
**Reasoning**: Two independent tasks - bug fix and documentation update can run simultaneously.

**User**: "Review the payment processing code for security issues and also check if our tests are actually meaningful."
**Route**: `code-review` (parallel) `mutation-testing`
**Reasoning**: Security audit and test quality analysis are independent concerns.

## Final Instruction

You are the router. Be decisive. Be fast. Delegate.

If you can route confidently, delegate immediately.
If you cannot route safely, ask up to 3 clarifying questions and stop.
````

### Key Observations from Production Prompt

1. **Explicit Tool Denial**: Every non-essential tool is explicitly set to `false` - not just omitted
2. **Permission Layer**: Additional `permission` block with `deny` rules as defense-in-depth
3. **14 Specialized Agents**: Granular specialization (separate agents for `commits` vs `fixup`)
4. **Trigger Keywords**: Each agent has documented activation keywords for routing
5. **Verbosity Toggle**: Minimal by default, verbose only when asked or low confidence
6. **Concrete Examples**: 12 routing scenarios with reasoning documented
7. **3-Agent Chain Limit**: Explicit constraint on chain length

---

## References

1. **Primary Source**: <https://gist.github.com/gc-victor/1d3eeb46ddfda5257c08744972e0fc4c> (accessed 2026-01-26)
2. **OpenCode Repository**: <https://github.com/anomalyco/opencode> (accessed 2026-01-26)
3. **OpenCode Homepage**: <https://opencode.ai> (accessed 2026-01-26)
4. **OpenCode Agent System Docs**: <https://deepwiki.com/sst/opencode/3.2-agent-system> (accessed 2026-01-26)
5. **Related Article**: "Long-horizon agents: OpenCode + GPT-5.2 Codex Experiment" by Maxim Saplin, Dev.to (2026-01-22)
6. **Related Article**: "OpenCode Agents: Another Path to Self-Healing Documentation Pipelines" by Rick Hightower, Medium (2025-09-17)
7. **GitHub Issue**: "[feat] True Async/Background Sub-Agent Delegation #5887" - anomalyco/opencode (2025-12-20)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Claude Code Harness](../agent-frameworks/claude-code-harness.md) | agent-frameworks | referenced by Claude Code Harness (agent-frameworks) |
