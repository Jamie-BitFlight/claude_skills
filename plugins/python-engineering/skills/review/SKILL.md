---
name: review
description: Reviews Python code across type safety, error handling, security, performance, modern patterns, design clarity, typed-boundary compliance, test quality, and documentation. Use when performing code review, PR review, pre-merge quality checks, or assessing Python for security vulnerabilities, bare except clauses, Any usage outside boundaries, or missing input validation at system boundaries.
argument-hint: '[path or scope]'
---

# Review

Use this skill for a bounded conventional code review of the requested Python scope.

For a broad audit asking how the code could be more Pythonic, smaller, lower-maintenance, modernized, replaced by ecosystem libraries, or aligned with large-project practices, use `python-engineering:python-quality-audit` instead. That entryway fans out StinkySnake, SnakePolish, ecosystem, project-practice, and removal/debt research and synthesizes an actionable report.

Review the requested Python scope with these priorities.

## Input

Scope: $ARGUMENTS

## Instructions

1. Read target files from arguments
2. Check each dimension listed below
3. Report findings with severity and location
4. Suggest fixes with code examples

---

## Shared policy

Load `python-engineering:standards-for-python-development` before judging the target. Its precedence and contextual defaults are authoritative; this entrypoint must not invent stricter framework migrations or numeric heuristics.

Review for correctness, security, boundary safety, design/cohesion, tests, typing, performance where demonstrated, and documentation affected by the change. Prefer the plugin's defaults for new work, but do not flag coherent existing `unittest.mock`, absence of Hypothesis without a useful invariant/input space, direct construction, or existing architecture merely because another preferred option exists.

For each finding report severity, file:line, evidence, consequence, suggested correction, and verification. Treat ~500 physical LOC as the default module boundary and inspect/decompose unless evidence shows splitting would worsen cohesion/API boundaries.

Do not edit the reviewed code.
