---
name: snakepolish
description: Implementation phase for stinkysnake workflow. Use when tests are written and plan is ready. Implements functions following the modernization plan, runs tests until passing.
argument-hint: '[file-paths-or-module]'
context: fork
agent: python-cli-architect
user-invocable: true
---

# Snake Polish — Implementation Phase

Execute the implementation plan from `/python-engineering:stinkysnake`.

## Prerequisites

1. `/python-engineering:stinkysnake` phases 1-5 completed
2. Modernization plan reviewed and refined
3. Failing tests written

## Implementation Order

1. Type definitions (TypeAlias, TypedDict, Protocol)
2. Data structures (dataclass, Pydantic models)
3. Utility functions
4. Core business logic
5. Integration points
6. Entry points

## Iterative Loop

```bash
# After each batch
uv run pytest -v --tb=short

# Final verification
uv run ruff check $ARGUMENTS
uv run ty check $ARGUMENTS
uv run pytest -v --cov --cov-report=term-missing
```

## Completion

When all tests pass and static analysis is clean:

1. Report implementation summary
2. List any deferred items
3. Reference documentation updates needed
