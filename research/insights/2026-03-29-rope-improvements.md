# Improvement Proposals: Rope

**Research entry**: ./research/code-auditing/rope.md
**Generated**: 2026-03-29
**Patterns assessed**: 5
**Backlog items created**: 0
**Deferred (low confidence)**: 1
**Skipped (already covered or tracked)**: 4

---

## Improvement 1: AST-Based Static Analysis in Code Review Quality Gates

**Source pattern**: "Leverage rope's AST analysis and scope tracking to build custom code auditing or linting tools" (Relevance to Claude Code Development, Use Case 3)
**Local system**: plugins/python3-development/agents/code-reviewer.md
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred -- confidence medium: the research entry describes this as an aspirational use case ("Leverage... to build"), not a concrete mechanism with specific inputs/outputs. The local code-reviewer agent operates via LLM judgment with linting tool integration (ruff, mypy, pyright). Rope's AST scope analysis could supplement this by detecting unreferenced symbols, import conflicts, or scope violations programmatically. However, the research entry does not describe a specific auditing pattern that maps to a gap -- it suggests a category of tools that could be built.

### Current state

The code-reviewer agent (plugins/python3-development/agents/code-reviewer.md) performs code review entirely via LLM reading and judgment, supplemented by linting tools (ruff, mypy, pyright) loaded via the holistic-linting skill. There is no programmatic AST-based analysis for scope-aware symbol detection, occurrence counting, or import conflict identification. The agent reviews code by reading files and applying learned patterns.

### Target state

A supplementary MCP tool or script wrapping rope's AST analysis provides programmatic verification of Python symbol usage: unused imports, unreferenced variables, scope conflicts, and cross-module symbol resolution. The code-reviewer agent invokes this tool as a pre-check before LLM-based review, producing a structured report of AST-verified findings alongside its judgment-based review.

### Measurable signal

An MCP tool or script exists that accepts a Python file path and returns a JSON report of AST-detected issues (unused imports, unreferenced symbols, scope conflicts). The code-reviewer agent's workflow includes a step invoking this tool. Running the tool on a Python file with known unused imports produces a report listing them.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| AST-based static analysis in code review | Medium | Research entry describes aspirational use case, not a concrete mechanism. Would need to verify that rope's specific analysis capabilities (occurrence detection, scope tracking) produce findings that ruff/mypy/pyright do not already cover, to confirm the gap is real. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| IDE Refactoring Integration | Too abstract -- describes using Rope as a library in editors. Local repo builds Claude Code skills/plugins, not IDE refactoring extensions. No local system maps to this pattern. |
| Automated Code Transformation | Architecture incompatible -- local refactoring system (implement-refactor skill) targets markdown/YAML skill documentation via agent delegation, not Python source code via AST transformation. |
| Test Generation via Extract | Too abstract -- research entry says "can be used to generate isolated test cases" without describing a concrete mechanism. Local test generation uses pytest-architect agent. No specific gap identifiable. |
| Interactive Refactoring Tools | Too abstract -- describes a potential future plugin offering AST-based refactoring suggestions. No existing local system to compare against; this is a new feature idea, not a gap in a current system. |
