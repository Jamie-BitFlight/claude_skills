---
name: stinkysnake
description: Progressive Python quality improvement with static analysis, type refinement, modernization planning, plan review, and test-driven implementation. Use when addressing technical debt, eliminating Any types, applying modern Python patterns, or refactoring for better design.
argument-hint: '[file-paths-or-module]'
user-invocable: true
---

<file_paths>$ARGUMENTS</file_paths>

# Python Quality Improvement System

Systematic Python code quality improvement through static analysis, type refinement, modernization planning with review, and test-driven implementation.

## Arguments

<file_paths/>

## Workflow Overview

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                         STINKYSNAKE WORKFLOW                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Phase 1: STATIC ANALYSIS                                                   │
│  ├── Run formatters (ruff format)                                           │
│  ├── Run linters (ruff check --fix)                                         │
│  ├── Run type checkers (ty default; mypy/pyright if project configures)    │
│  └── Auto-fix all resolvable issues                                         │
│           │                                                                 │
│           ▼                                                                 │
│  Phase 2: TYPE ANALYSIS                                                     │
│  ├── Determine minimum Python version                                       │
│  ├── Inventory all `Any` types                                              │
│  ├── Map type dependencies                                                  │
│  └── Identify typing gaps                                                   │
│           │                                                                 │
│           ▼                                                                 │
│  Phase 3: MODERNIZATION PLANNING                                            │
│  ├── Plan Protocol usage for duck typing                                    │
│  ├── Plan Generic type parameters                                           │
│  ├── Plan TypeGuard narrowing                                               │
│  ├── Plan TypeAlias definitions                                             │
│  ├── Plan TypedDict for dict shapes                                         │
│  ├── Plan dataclass/Pydantic models                                         │
│  └── Plan library modernization (httpx, orjson, etc.)                       │
│           │                                                                 │
│           ▼                                                                 │
│  Phase 4: PLAN REVIEW (context: fork)                                       │
│  ├── Review against pythonic best practices                                 │
│  ├── Verify against online references                                       │
│  ├── Check feasibility                                                      │
│  ├── Identify breaking changes                                              │
│  └── Produce review report                                                  │
│           │                                                                 │
│           ▼                                                                 │
│  Phase 5: PLAN REFINEMENT                                                   │
│  └── Update plan based on review feedback                                   │
│           │                                                                 │
│           ▼                                                                 │
│  Phase 6: DOCUMENTATION DISCOVERY                                           │
│  ├── Find docs requiring updates                                            │
│  └── Note what changes are needed                                           │
│           │                                                                 │
│           ▼                                                                 │
│  Phase 7: INTERFACE DESIGN                                                  │
│  └── Create interfaces/protocols first                                      │
│           │                                                                 │
│           ▼                                                                 │
│  Phase 8: TEST-FIRST (context: fork, python-pytest-architect)               │
│  ├── Write failing tests against interfaces                                 │
│  └── Stop after tests written                                               │
│           │                                                                 │
│           ▼                                                                 │
│  Phase 9: IMPLEMENTATION (/python3-development:snakepolish)                                     │
│  ├── context: fork with python-cli-architect                                │
│  ├── Follow plans and implement functions                                   │
│  └── Run tests until passing                                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Companion Plugins

This skill integrates with plugins in the same marketplace:

### holistic-linting Plugin

**Activation**: `Skill(skill: "holistic-linting:holistic-linting")`

Provides: Linting rules knowledge base, `linting-root-cause-resolver` agent, automatic linter detection.

### pre-commit Plugin

**Activation**: `Skill(skill: "python3-development:pre-commit")`

Provides: Git hook automation for quality gates.

---

## Phase 1: Static Analysis

Run automated tools to fix all resolvable issues before manual work begins.

### Step 1.1: Format Code

```bash
# Format all Python files
uv run ruff format $ARGUMENTS

# Verify formatting
uv run ruff format --check $ARGUMENTS
```

### Step 1.2: Auto-Fix Linting Issues

```bash
# Fix all auto-fixable issues
uv run ruff check --fix $ARGUMENTS

# Fix unsafe fixes if appropriate
uv run ruff check --fix --unsafe-fixes $ARGUMENTS
```

### Step 1.3: Run Type Checkers

Inspect `.pre-commit-config.yaml` (then CI) first, then `pyproject.toml`. **Default for new work:** **ty**. **If hooks or CI invoke mypy:** run **mypy** and do not rip it out. **Do not** switch to mypy only because `[tool.mypy]` exists — many repos keep that section while **ty** is the real gate.

```bash
# Default (ty) — when hooks run ty, [tool.ty] is active, or no mypy invocation in hooks/CI
uv run ty check $ARGUMENTS

# Project that actually runs mypy in hooks/CI — respect mypy.ini / [tool.mypy]
uv run mypy $ARGUMENTS

# Project standardizes on pyright / basedpyright
uv run pyright $ARGUMENTS
# uv run basedpyright $ARGUMENTS
```

### Step 1.4: Document Remaining Issues

Create inventory of issues that cannot be auto-fixed:

```text
## Static Analysis Results

### Auto-Fixed
- [X] Formatting issues: N fixed
- [X] Import sorting: N fixed
- [X] Safe linting fixes: N fixed

### Requires Manual Resolution
| File:Line | Rule | Issue | Complexity |
|-----------|------|-------|------------|
| src/api.py:45 | ANN001 | Missing type annotation | Low |
| src/models.py:120 | B006 | Mutable default | Medium |
```

---

## Phase 2: Type Analysis

Determine Python compatibility and inventory typing gaps.

### Step 2.1: Determine Minimum Python Version

Check project configuration:

```bash
# Check pyproject.toml
grep -E "requires-python|python_requires" pyproject.toml

# Check setup.py if exists
grep -E "python_requires" setup.py
```

**Document the constraint**:

```text
## Python Version Constraint

Minimum Version: Python 3.11
Reason: [from pyproject.toml requires-python = ">=3.11"]

Available Language Features:
- Native generics (list[str], dict[str, int])
- Union syntax (str | None)
- Pattern matching (match/case)
- Exception groups
- Self type
- TypeVarTuple
- Required/NotRequired in TypedDict
```

### Step 2.2: Inventory All `Any` Types

Search for explicit and implicit `Any` usage:

```bash
# Find explicit Any imports and usage
uv run rg "from typing import.*Any|: Any|-> Any" $ARGUMENTS

# Implicit Any / strict diagnostics — use the same checker the project uses
uv run ty check $ARGUMENTS 2>&1 | grep -iE "Any|implicit" || true
# If project uses mypy instead:
# uv run mypy --strict $ARGUMENTS 2>&1 | grep -E "has type.*Any|Implicit.*Any"
```

**Create inventory**:

```text
## Any Type Inventory

### Explicit Any Usage
| Location | Variable | Current Type | Proposed Type |
|----------|----------|--------------|---------------|
| api.py:23 | response | Any | dict[str, JSONValue] |
| utils.py:45 | callback | Any | Callable[[str], None] |

### Implicit Any (from untyped libraries)
| Location | Source | Mitigation |
|----------|--------|------------|
| client.py:12 | third_party.get() | Add type stub or cast |
```

### Step 2.3: Map Type Dependencies

Understand how types flow through the codebase:

```text
## Type Dependency Map

Entry Points (public API):
- cli.main() -> int
- api.fetch_data(url: str) -> ???  # Needs typing

Internal Flow:
fetch_data() -> parse_response() -> validate() -> Model

Type Gaps:
- parse_response returns Any
- validate accepts Any
```

---

## Phase 3: Modernization Planning

Plan how to apply modern Python features to eliminate type gaps and improve design.

### Step 3.1: Load modernpython Skill

```text
Skill(skill: "python3-development:modernpython")
```

### Step 3.2: Plan Type System Improvements

For each `Any` in the inventory, plan the replacement using appropriate constructs:

Select the appropriate type construct for each `Any` replacement:

- **Protocol** — duck-typed objects sharing behavior without inheritance
- **Generic** — containers/functions preserving type info across multiple types
- **TypeGuard** — runtime checks that should narrow types for the checker
- **TypeAlias** — repeated complex types needing a name
- **TypedDict** — dicts with known keys and specific value types
- **Dataclass/Pydantic** — structured data with optional validation

See `references/type-patterns.md` for before/after code samples and library modernization reference table.

### Step 3.3: Plan Library Modernization

See the library modernization reference table in `references/type-patterns.md#library-modernization-reference`.

### Step 3.4: Create Modernization Plan Document

Resolve the plan directory at runtime: `uv run python -c 'from dh_paths import plan_dir; print(plan_dir())'` (typically `~/.dh/projects/{slug}/plan/`). Create the plan at `{plan_dir}/stinkysnake-plan.md` using the template in `references/plan-templates.md#modernization-plan-template-phase-3-output`.

---

## Phase 4: Plan Review

Delegate to a review agent with context fork to critique the plan.

### Step 4.1: Launch Plan Review Agent

Delegate to `code-reviewer` using the prompt in `references/agent-prompts.md#phase-4-plan-review`.

### Step 4.2: Review Report Structure

The reviewer produces a report following the template in `references/plan-templates.md#plan-review-report-template-phase-4-output`.

---

## Phase 5: Plan Refinement

Update the plan based on review feedback.

### Step 5.1: Address Blocking Issues

For each blocking issue:

1. Understand the concern
2. Research alternatives
3. Update the plan
4. Document the change

### Step 5.2: Acknowledge Warnings

For each warning:

1. Add mitigation to the plan
2. Or accept risk with justification

### Step 5.3: Consider Suggestions

For each suggestion:

1. Evaluate effort vs benefit
2. Include if beneficial, defer if not

### Step 5.4: Update Plan Document

Update `{plan_dir}/stinkysnake-plan.md` (resolve `plan_dir` as in Step 3.4) using the revised plan format in `references/plan-templates.md#revised-plan-template-phase-5-output`.

---

## Phase 6: Documentation Discovery

Find documentation that needs updating after code changes.

### Step 6.1: Inventory Documentation

```bash
# Find all documentation files
fd -e md -e rst -e txt . docs/ README.md CHANGELOG.md

# Find docstrings in affected files
uv run rg "^\s+\"\"\"" $ARGUMENTS
```

### Step 6.2: Map Code to Docs

Create documentation update plan using the template in `references/plan-templates.md#documentation-update-plan-template-phase-6-output`.

---

## Phase 7: Interface Design

Create interfaces and protocols before implementation.

### Step 7.1: Define Type Aliases

```python
# src/types.py
from typing import TypeAlias

JSONValue: TypeAlias = str | int | float | bool | None | list["JSONValue"] | dict[str, "JSONValue"]
APIResponse: TypeAlias = dict[str, JSONValue]
```

### Step 7.2: Define Protocols

```python
# src/protocols.py
from typing import Protocol

class Handler(Protocol):
    def handle(self, data: bytes) -> None: ...

class Serializable(Protocol):
    def to_dict(self) -> dict[str, Any]: ...
```

### Step 7.3: Define TypedDicts

```python
# src/schemas.py
from typing import TypedDict, NotRequired

class UserData(TypedDict):
    name: str
    email: str
    age: NotRequired[int]
```

### Step 7.4: Define Data Classes

```python
# src/models.py
from dataclasses import dataclass

@dataclass
class User:
    name: str
    email: str
    age: int | None = None
```

---

## Phase 8: Test-First Implementation

Delegate to python-pytest-architect to write failing tests against the interfaces.

### Step 8.1: Launch Test Writing Agent

Delegate to `python-pytest-architect` using the prompt in `references/agent-prompts.md#phase-8-test-writing-agent`.

### Step 8.2: Verify Tests Fail

```bash
# Run tests - they should fail
uv run pytest tests/ -v

# Expected output: X failed, 0 passed
```

---

## Phase 9: Implementation

Use the `/python3-development:snakepolish` skill to implement until tests pass.

### Step 9.1: Launch Implementation Skill

```text
/python3-development:snakepolish $ARGUMENTS
```

This skill:

- Has `context: fork` to work in isolation
- Uses `agent: python-cli-architect` for implementation
- Follows the refined plan
- Runs tests after each change
- Continues until all tests pass

### Step 9.2: Verify All Tests Pass

```bash
# Final verification
uv run pytest tests/ -v
uv run ty check $ARGUMENTS
# If project uses mypy: uv run mypy $ARGUMENTS
uv run ruff check $ARGUMENTS
```

---

## Output Artifacts

The complete workflow produces:

| Artifact                | Location                                  | Purpose             |
| ----------------------- | ----------------------------------------- | ------------------- |
| Static Analysis Results | `.claude/reports/static-analysis-{ts}.md` | Auto-fix summary    |
| Type Inventory          | `.claude/reports/type-inventory-{ts}.md`  | Any types found     |
| Modernization Plan      | `{plan_dir}/stinkysnake-plan.md`          | Implementation plan |
| Plan Review             | `.claude/reports/plan-review-{ts}.md`     | Review feedback     |
| Revised Plan            | `{plan_dir}/stinkysnake-plan.md`          | Updated plan        |
| Doc Update Plan         | `.claude/reports/doc-updates-{ts}.md`     | Docs to change      |
| Test Files              | `tests/test_*.py`                         | Failing tests       |
| Implementation          | `src/`                                    | Passing code        |

---

## Quick Reference

### Skill Activations

```text
Skill(skill: "holistic-linting:holistic-linting")     # Linting workflows
Skill(skill: "python3-development:pre-commit")       # Git hooks
Skill(skill: "python3-development:modernpython")     # Python 3.11+ patterns
Skill(skill: "python3-development:python3-development")  # Core patterns
```

### Agent Delegations

```text
Agent(subagent_type="holistic-linting:linting-root-cause-resolver", ...)  # Phase 1 linting
Agent(subagent_type="python3-development:code-reviewer", ...)     # Phase 4 review
Agent(subagent_type="python3-development:python-pytest-architect", ...)  # Phase 8 tests
```

### Related Skills

```text
/python3-development:snakepolish  # Phase 9 implementation (context: fork)
```

---

---

## Agent Team Alternative for Phase 4

When Phase 4 (quality improvement implementation) involves 3+ independent improvement areas where findings from one area inform or challenge another, consider agent teams instead of sequential subagents.

### When Agent Teams Apply

A quality improvement workflow is a candidate for agent teams when ALL of these are true:

1. 3+ independent improvement areas (enough parallelism to justify coordination overhead)
2. Areas benefit from cross-communication (findings from one area inform or challenge another)
3. No shared file mutations (each teammate owns different files)
4. Result is a synthesis, not a concatenation (value comes from combining, deduplicating, or reconciling findings across areas)

### When Subagents Suffice

A quality improvement workflow is NOT a candidate for agent teams when:

- Only 1-2 improvement areas (subagent overhead is lower)
- Areas are fully independent with no cross-communication need (subagents suffice)
- Result is just collecting N outputs (no synthesis step)
- Work is sequential (each step depends on the previous)

### Reference

See `../../../plugin-creator/skills/claude-skills-overview-2026/resources/agent-teams.md` for complete criteria, architecture, and usage patterns.

SOURCE: Lines 27-39 of agent-teams.md (accessed 2026-02-06)

## References

### Skill Reference Files

- `../python3-development/references/python3-standards.md` — Shared development standards, knowledge graph, and process graph
- `references/plan-templates.md` — document formats for modernization plan, review report, revised plan, and documentation update plan
- `references/agent-prompts.md` — pre-built delegation prompts for Phase 4 review agent and Phase 8 test writing agent

### External Documentation

- [Typing Module](https://docs.python.org/3/library/typing.html)
- [PEP 544 - Protocols](https://peps.python.org/pep-0544/)
- [PEP 589 - TypedDict](https://peps.python.org/pep-0589/)
- [PEP 647 - TypeGuard](https://peps.python.org/pep-0647/)
- [ty documentation](https://docs.astral.sh/ty/) (default type checker)
- [mypy Cheat Sheet](https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html) (when project uses mypy)

### Companion Plugins

- **holistic-linting** - Linting rules knowledge base
- **pre-commit** - Git hook automation
