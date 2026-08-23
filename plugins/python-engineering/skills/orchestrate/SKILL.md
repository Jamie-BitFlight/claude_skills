---
name: orchestrate
description: "Use when implementing a Python feature, adding CLI commands, writing pytest suites, reviewing Python code, debugging, or refactoring. The primary Python engineering workflow orchestrator — routes to SAM track (multi-step feature additions, work spanning 2+ agents or files, durable progress tracking) or Direct track (single-focused tasks: bug fix, tests for one file, one-shot refactor, code review). Delegates to python-cli-architect (implementation), python-pytest-architect (tests), code-reviewer (review), python-cli-design-spec (architecture). Triggers on any Python task requiring specialist agent coordination or multi-agent execution."
argument-hint: '[task description]'
---

# Orchestrate

Multi-step engineering workflow command.

## Input

Task: $ARGUMENTS

If no argument is supplied, derive the task from the active conversation.

## Step 1 — Load the orchestration guide (MANDATORY)

Load and follow the guide in `/python-engineering:orchestrating-python-development`.

Do not proceed to Step 2 until this skill has been loaded. It contains agent selection criteria, workflow patterns, quality gates, and multi-agent chaining patterns needed for Step 2.

## Step 2 — Route to track

```mermaid
flowchart TD
    Q{"Does the task meet ANY of:<br>- user said 'add a feature', 'plan', or 'track'<br>- requires 2+ agents in sequence<br>- spans multiple files or modules<br>- needs durable progress tracking across turns"}
    Q -->|"Yes"| SAM["SAM Track — Step 3A"]
    Q -->|"No — single focused task:<br>fix a bug, write tests for one file,<br>review code, one-shot refactor"| Direct["Direct Track — Step 3B"]
```

Then state aloud before the first Agent tool call:

```text
Task: <one sentence>
Track: SAM | Direct
Workflow pattern: <TDD | Feature Addition | Refactoring | Debugging | Code Review>
Agent chain: <AGENT1> → <AGENT2> → ...
```

If you cannot fill in workflow pattern and agent chain from the guide read in Step 1, go back and read it.

## Step 3A — SAM Track

```mermaid
flowchart TD
    P1["Phase 1 — Plan<br>Skill: /dh:add-new-feature<br>Args: task description<br>Produces: ~/.dh/projects/{slug}/plan/P{NNN}-{slug}.yaml"]
    P1 --> P1Q{"add-new-feature result?"}
    P1Q -->|"BLOCKED — plan-validator gate failed"| P1Blocked["Surface blocker to user<br>Await clarification<br>STOP"]
    P1Q -->|"PASS — task file produced"| P2
    P2["Phase 2 — Execute<br>Skill: /dh:implement-feature<br>Args: path to task file<br>Loop: sam ready → start-task → SubagentStop hook marks COMPLETE<br>Repeat until no tasks remain"]
    P2 --> P3["Phase 3 — Quality gates<br>Auto-invoked by implement-feature<br>Skill: /dh:complete-implementation<br>Runs: code review → feature verification → integration check<br>→ doc drift → doc update → context refinement → commit"]
    P3 --> Done(["DONE — changes committed"])
```

### SAM task creation format (when creating tasks directly)

When `mcp__plugin_dh_sam__sam_create` is called directly (e.g., from `create-feature-task`):

```yaml
title: "<short imperative title>"
description: |
  <what must be true when this task is done>
acceptance_criteria:
  - Given <context>, when <action>, then <observable result>
phases:
  - name: <phase name>
    tasks:
      - <concrete subtask>
```

Update task status with `mcp__plugin_dh_sam__sam_update` as phases complete.

## Step 3B — Direct Track

Classify the task then delegate:

1. Classify the task: feature, refactor, review, debug, packaging, migration, or cleanup
2. Identify project lane: CLI, web, data, library, service, or legacy
3. Identify typing lane from repository constraints and dependencies
4. Choose the minimum set of specialist skills needed
5. Produce a concise execution plan
6. Execute or delegate in the smallest coherent units
7. Run deterministic checks before declaring completion

Agent routing — delegate rather than implement:

- Python code → subagent_type="python-engineering:python-cli-architect"
- Tests → subagent_type="python-engineering:python-pytest-architect"
- Code review → subagent_type="python-engineering:code-reviewer"
- Architecture design → subagent_type="python-engineering:python-cli-design-spec" — requires a resolved `item_id` (see below)
- Task breakdown → subagent_type="dh:swarm-task-planner"
- Stdlib-only script → Skill(skill: "python-engineering:python3-stdlib-only")
- CLI/TUI UI design, shape brief, critique, audit, or polish → Skill(skill: "python-engineering:designing-ui-for-cli")
- Pre-implementation challenge → subagent_type="python-engineering:adversarial-solution-design"

Before delegating any non-trivial implementation to `python-cli-architect`, route through `adversarial-solution-design` first. Skip only for one-line fixes where the correct change is unambiguous (typo, wrong variable name, trivial rename).

#### Resolving `item_id` for `python-cli-design-spec`

`python-cli-design-spec` registers its spec as an artifact against a backlog item — it has no
file-write fallback, so every dispatch, Direct Track included, must resolve an `item_id` first:

1. Task already names a tracked item (`#N` GitHub issue or a Beads ID) → use it as `item_id`.
2. Otherwise call `mcp__plugin_dh_backlog__backlog_add(title=<task title>, priority=<P0|P1|P2|Ideas>, description=<task description>)` and capture the returned issue number (or backend-native identifier) as `item_id`. Treat an `error` key in the response as a hard stop — report it, do not fall back to a file write.

Pass the resolved `item_id` in the delegation context alongside Outcomes/Constraints/Known
issues/File paths below.

Each delegation must include:

- Outcomes: what must be true when the agent is done
- Constraints: user requirements, compatibility, scope boundaries
- Known issues: error messages already in context (pass-through, not pre-gathered)
- File paths: where to start looking — not what you found there
- `item_id`: required for `python-cli-design-spec` dispatches — resolved per the previous section

### Delegation Hard Rules

These apply to all delegations — SAM and Direct:

| Prohibited | Instead |
|---|---|
| Read files, grep, or run tools to gather context before delegating | See Pre-Gathering Alternatives below |
| Hedging: "I think", "probably", "likely", "seems" | State observed facts: file path, exit code, exact error text |
| Name a specific tool: "use Bash to…" | Describe the ecosystem; agent selects tools |
| Invent constraints the user did not state | Include only user-specified constraints |
| Fix one bug/smell instance | Treat as systemic — audit scope for all instances unless user said "only this one" |

#### Pre-Gathering Alternatives

Reading files then describing what you found to an agent (a) consumes orchestrator context on raw reads, (b) loses fidelity through paraphrase, (c) hands the agent your filtered interpretation rather than the source. When context is needed before work can proceed, choose one of:

**1. Spawn an information-gathering agent** — sole job is exhaustive discovery across files, docs, and tooling:

```text
Find all occurrences of [X] in [codebase] and [docs/tooling locations].
Return: file paths, line numbers, key observations.
```

The gathering agent reads more broadly than a few orchestrator greps can reach. You receive a structured report and synthesize from that — without having read anything yourself.

**2. Embed discovery as the implementing agent's first steps** — pass the research actions as instructions, not keyword searches:

```text
Start by tracing [X] through the codebase: find all call sites, read how [Y] is used in
[related files], consult the [module] docs/source at [URL or package repo], then implement [task].
```

"Finding" here means tracing — following call chains, reading usage patterns, consulting the module's documentation, its source on GitHub, its changelog, related RFCs or issues — not a grep for a keyword. The implementing agent does this with full task context, so it understands why it is looking and what to do with what it discovers. Research done in context of the implementation task produces higher-quality results than pre-filtered findings handed over from the orchestrator.

Load `/agent-orchestration:agent-orchestration` for the full framework: delegation template, verification checklists, anti-patterns, and parallel dispatch patterns.

### Delegation Routing Rules

- Use specialist skills for guidance
- Use subagents only when the task has separable parallelizable work or needs isolated analysis
- Do not duplicate routing already handled by `python3-core`
- Do not preload unrelated specialists

## Quality Gate

Before reporting done:

1. `uv run prek run --files <modified_files>` — runs linting, formatting, and type checking
   Fallback: `uv run ruff format` and `uv run ruff check --fix` only when no `.pre-commit-config.yaml`
2. `uv run pytest` — all pass, coverage ≥80%
3. Shebang validated on any scripts
