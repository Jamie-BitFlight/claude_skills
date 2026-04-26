# Improvement Proposals: TheAlgorithms-Python

**Research entry**: /home/user/claude_skills/research/learning-resources/TheAlgorithms-Python.md
**Generated**: 2026-04-26
**Patterns assessed**: 6
**Backlog items created**: 1 (issues: #1958)
**Deferred (low confidence)**: 0
**Skipped (already covered or tracked)**: 5

---

## Improvement 1: Add "expand acronyms" naming convention rule to Python coding standards

**Source pattern**: From "Naming Conventions" section of TheAlgorithms-Python.md, citing the project's CONTRIBUTING.md: "Expand acronyms because `gcd()` is hard to understand but `greatest_common_divisor()` is not."
**Local system**: /home/user/claude_skills/plugins/python3-development/skills/python3-development/references/python3-standards.md (and the parallel file in python-engineering)
**Confidence**: High
**Impact**: Medium
**Backlog**: #1958 created

### Current state

`python3-standards.md` covers type safety, architecture, error handling, performance, and testing. It contains zero guidance on identifier naming beyond mentioning that test names should be behavioral. There is no rule against single-letter or acronym function names. `grep -rn "expand acron\|gcd()\|abbreviat" plugins/python3-development/ plugins/python-engineering/` returns no matches in any SKILL.md or reference file. As a result, agents writing Python code may produce identifiers like `gcd()`, `lcm()`, `bfs()`, `dfs()` without prompting expansion to `greatest_common_divisor()`, `breadth_first_search()`, etc., reducing readability of generated code for downstream consumers.

### Target state

`python3-standards.md` Section 1.1 (or a new Section 1.X "Identifier Naming") includes an "Expand Acronyms in Public APIs" subsection with:

1. The rule statement: "Expand acronyms in function names, class names, and module names. `gcd()` is opaque; `greatest_common_divisor()` is self-documenting."
2. Two contrast examples — one acronym-named function and the same function with the acronym expanded
3. A scoped exception: established three-letter acronyms accepted as words (URL, API, SQL, HTTP, JSON, XML) may remain abbreviated when they are the standard term in the domain
4. A pointer to apply the same rule to local variables when the variable's lifetime exceeds 5 lines

The same content is added to `plugins/python-engineering/skills/python3-core/SKILL.md` Naming Defaults section, or `python3-core` references the python3-development standard if that file is the canonical source.

### Measurable signal

Run: `grep -n "expand acron\|greatest_common_divisor" plugins/python3-development/skills/python3-development/references/python3-standards.md` returns at least one match in a section heading or rule statement. The file contains the literal contrast example pair `gcd()` and `greatest_common_divisor()`. Cross-reference: `grep -n "expand acron" plugins/python-engineering/skills/python3-core/SKILL.md` returns either the rule or an explicit pointer to the python3-development source.

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Doctest as validated test cases (`pytest --doctest-modules`) | Already tracked as #1956 — same source pattern, same target plugin scope, same measurable signal |
| Type hints on every function signature | Already covered in python3-standards.md Section 1.1 ("Native Types: Use Python 3.11+ native type hints"); modernpython SKILL.md has dedicated Type Hints section with PEP 585/604 guidance |
| Multiple implementation strategies side-by-side (iterative vs recursive) | Pattern is educational/pedagogical — TheAlgorithms ships both variants for learner comparison. This is incompatible with this repo's architecture which produces production code, not pedagogical examples. Agents should choose one implementation matching the use case, not generate variants |
| Pre-commit + ruff enforcement | Already covered — repo runs `prek` (Rust pre-commit replacement) per CLAUDE.md "Local Formatting and Linting" section; pre-commit skill exists at plugins/python3-development/skills/pre-commit/ |
| Comprehensive ruff rule sets (40+ categories from TheAlgorithms pyproject.toml) | Out of scope for skill documentation — this is project-level tooling configuration, not skill guidance. If the repo's ruff config is missing rule categories, that is a separate `pyproject.toml` concern |
