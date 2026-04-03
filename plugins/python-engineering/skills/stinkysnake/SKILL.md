---
name: stinkysnake
description: Progressive Python quality improvement through static analysis, type refinement, and modernization. Use when addressing technical debt, eliminating Any types, or applying modern Python patterns across a codebase.
argument-hint: '[file-paths-or-module]'
user-invocable: true
---

# Stinkysnake — Progressive Quality Improvement

## Workflow

1. **Static Analysis**: Run ruff format, ruff check --fix, and type checker
2. **Type Analysis**: Inventory Any types, map dependencies, identify gaps
3. **Plan**: Create modernization plan for type replacements
4. **Review**: Delegate plan to review agent
5. **Refine**: Update plan based on feedback
6. **Implement**: Run tests iteratively until passing
7. **Verify**: Final lint, type check, and test run

## Steps

### Phase 1: Static Analysis

```bash
uv run ruff format $ARGUMENTS
uv run ruff check --fix $ARGUMENTS
uv run ty check $ARGUMENTS
# If project runs mypy: uv run mypy $ARGUMENTS
```

### Phase 2: Type Inventory

```bash
grep -r 'from typing import.*Any\|: Any\|-> Any' $ARGUMENTS
```

### Phase 3: Plan

Create `{plan_dir}/stinkysnake-plan.md` with type replacement strategy.

### Phase 4-5: Review and Refine

Delegate to `code-reviewer` agent.

### Phase 6: Implement

Use `/python-engineering:cleanup` for implementation, or load `python3-tdd` for test-first approach.

### Phase 7: Verify

```bash
uv run ruff check $ARGUMENTS
uv run ty check $ARGUMENTS
uv run pytest -v --cov --cov-report=term-missing
```
