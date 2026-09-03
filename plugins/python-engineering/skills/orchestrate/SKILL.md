---
name: orchestrate
description: "Use when implementing a Python feature, adding CLI commands, writing pytest suites, reviewing Python code, debugging, or refactoring. The primary Python engineering workflow orchestrator — classifies the task and delegates through this plugin's own specialist agents (architect → implement → test → review), sized to the task. Delegates to python-cli-architect (implementation), python-pytest-architect (tests), code-reviewer (review), python-cli-design-spec (architecture). Triggers on any Python task requiring specialist agent coordination or multi-agent execution."
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

## Step 2 — Classify the task

1. Classify the task: feature, refactor, review, debug, packaging, migration, or cleanup
2. Identify project lane: CLI, web, data, library, service, or legacy
3. Identify typing lane from repository constraints and dependencies
4. Choose the minimum set of specialist skills needed

State aloud before the first Agent tool call:

```text
Task: <one sentence>
Workflow pattern: <TDD | Feature Addition | Refactoring | Debugging | Code Review>
Agent chain: <AGENT1> → <AGENT2> → ...
```

If you cannot fill in workflow pattern and agent chain from the guide read in Step 1, go back and read it.

## Step 3 — Execute

1. Produce a concise execution plan
2. Execute or delegate in the smallest coherent units
3. Run deterministic checks before declaring completion

Agent routing — delegate rather than implement:

- Python code → subagent_type="python-engineering:python-cli-architect"
- Tests → subagent_type="python-engineering:python-pytest-architect"
- Code review → subagent_type="python-engineering:code-reviewer"
- Architecture design → subagent_type="python-engineering:python-cli-design-spec"
- Stdlib-only script → Skill(skill: "python-engineering:python3-stdlib-only")
- CLI/TUI UI design, shape brief, critique, audit, or polish → Skill(skill: "python-engineering:designing-ui-for-cli")
- Pre-implementation challenge → subagent_type="python-engineering:adversarial-solution-design"

Before delegating any non-trivial implementation to `python-cli-architect`, route through `adversarial-solution-design` first. Skip only for one-line fixes where the correct change is unambiguous (typo, wrong variable name, trivial rename).

Each delegation must include:

- Outcomes: what must be true when the agent is done
- Constraints: user requirements, compatibility, scope boundaries
- Known issues: error messages already in context (pass-through, not pre-gathered)
- File paths: where to start looking — not what you found there

### Delegation Hard Rules

These apply to all delegations:

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
