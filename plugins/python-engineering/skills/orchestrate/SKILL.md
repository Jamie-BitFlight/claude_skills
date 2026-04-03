---
name: orchestrate
description: Use when orchestrating a multi-step Python engineering workflow from a user-supplied task description. Invoke to coordinate planning, implementation, testing, and validation across skills.
disable-model-invocation: true
argument-hint: '[task description]'
---

# Orchestrate

Multi-step engineering workflow command.

## Input

Task: $ARGUMENTS

If no argument is supplied, derive the task from the active conversation.

## Workflow

1. Classify the task: feature, refactor, review, debug, packaging, migration, or cleanup
2. Identify project lane: CLI, web, data, library, service, or legacy
3. Identify typing lane from repository constraints and dependencies
4. Choose the minimum set of specialist skills needed
5. Produce a concise execution plan
6. Execute or delegate in the smallest coherent units
7. Run deterministic checks before declaring completion

## Delegation Rules

- Use specialist skills for guidance
- Use subagents only when the task has separable parallelizable work or needs isolated analysis
- Do not duplicate routing already handled by `python3-core`
- Do not preload unrelated specialists

## Quality Gate

Before reporting done:

1. `uv run ruff check` and `uv run ruff format --check`
2. Project type checker (detected from hooks/CI)
3. `uv run pytest` — all pass, coverage ≥80%
4. Shebang validated on any scripts
