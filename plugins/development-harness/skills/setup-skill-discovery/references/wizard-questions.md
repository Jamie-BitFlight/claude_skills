# Wizard Questions Reference

Questions presented in Step 5 of the `setup-skill-discovery` wizard. Each question surfaces
a project convention that repo scanning (Step 1) cannot infer from file presence alone.

**Total questions**: 12, across 6 categories.
**Questions shown per run**: 4–7 (filtered by stack trigger).
**Presentation order**: Categories 1–5 first, then Domain questions (Category 6) for detected
signals only.

> **Constraint**: Do NOT ask questions answerable by repo scanning. Step 1 already infers
> primary language, frameworks, dependency lists, and tooling presence. These questions
> capture team conventions, strictness levels, and intended usage patterns.

---

## Category 1: Testing Conventions

### Q1: Test-Driven Development

**Question**: "Does your team follow TDD — writing tests before implementation?"

**Why it matters**: TDD practitioners need different skill guidance. The `python3-tdd` skill
provides TDD-specific workflows (red/green/refactor loop). Without it, agents default to
post-implementation test writing, which contradicts the team's process.

**Default if skipped**: No

**Stack trigger**: Python detected (pyproject.toml or setup.py present)

**→ `skill_rules` mapping**:

```yaml
- when: "feature involves new functionality and the team follows test-driven development"
  use:
    - python-engineering:python3-tdd
```

---

### Q2: Property-Based Testing

**Question**: "Do you use property-based testing (e.g., Hypothesis) for complex logic like
algorithms, parsers, or data transformations?"

**Why it matters**: Property-based tests require different authoring patterns than example-based
tests. Loading `python3-testing` ensures the agent knows how to write `@given` strategies and
understand shrinking behavior.

**Default if skipped**: No

**Stack trigger**: Python detected AND (Hypothesis present in pyproject.toml OR tests/ directory
exists with substantial existing test files)

**→ `skill_rules` mapping**:

```yaml
- when: "feature involves algorithms, validators, parsers, or data transformations requiring
  property-based tests"
  use:
    - python-engineering:python3-testing
```

---

## Category 2: Linting and Formatting

### Q3: Linting as Hard CI Gate

**Question**: "Are linting violations treated as hard failures that block merges — not just
warnings?"

**Why it matters**: Blocking-lint projects need root-cause resolution skills (fixing the
underlying code issue, not adding `# noqa` suppressions). Non-blocking projects can tolerate
lighter guidance.

**Default if skipped**: No

**Stack trigger**: Linter config detected (ruff.toml, .ruff.toml, pyproject.toml [tool.ruff],
.eslintrc*, eslint.config.*)

**→ `skill_rules` mapping**:

```yaml
- when: "code changes touch linted modules or linting errors are reported in scope"
  use:
    - holistic-linting:linting-root-cause-resolver
```

---

## Category 3: Type Checking

### Q4: Type Checking Strictness

**Question**: "How strictly is type checking enforced in this project?
(A) Strict — all type errors must be fixed before merging
(B) Standard — major type errors only, warnings tolerated
(C) Advisory — type errors are informational, not blocking"

**Why it matters**: Strict type-checked projects need the linting resolver skill to fix type
errors to root cause. Advisory projects benefit from typing guidance but not blocking workflows.

**Default if skipped**: C — Advisory

**Stack trigger**: Python detected AND type checker config present in pyproject.toml
([tool.mypy], [tool.pyright], [tool.ty])

**→ `skill_rules` mapping** (for answers A or B):

```yaml
- when: "Python code changes involve typed modules, require new type annotations, or produce
  type checker errors"
  use:
    - holistic-linting:linting-root-cause-resolver
```

---

## Category 4: CI/CD Quality Gates

### Q5: Quality Gate Enforcement

**Question**: "Does your CI pipeline block merges when lint, typecheck, or test jobs fail?"

**Why it matters**: Gate-enforced projects need skills that understand the full sequential
quality-gate workflow (format → lint → typecheck → test). Without this context, agents fix
one gate in isolation and break another.

**Default if skipped**: No

**Stack trigger**: CI config file detected (.github/workflows/*.yml, .gitlab-ci.yml,
Jenkinsfile, .circleci/config.yml)

**→ `skill_rules` mapping**:

```yaml
- when: "feature changes must pass the full quality gate (format + lint + typecheck + test)
  before shipping"
  use:
    - holistic-linting:holistic-linting
```

---

## Category 5: Documentation

### Q6: Public API Documentation Required

**Question**: "Does this project require docstrings, JSDoc, or similar inline documentation
for all public functions, classes, and API endpoints?"

**Why it matters**: Documentation-required projects need the documentation skill loaded
alongside implementation skills so docs are written in the same pass, not as a follow-up task.

**Default if skipped**: No

**Stack trigger**: Always ask (universal — applies to any stack)

**→ `skill_rules` mapping**:

```yaml
- when: "adding or modifying public functions, classes, modules, or API endpoints"
  use:
    - documentation-expert
```

---

## Category 6: Domain-Specific

> These questions are only asked when the corresponding stack signal is detected in Step 1.

---

### Q7: Claude Code Plugin / Skill / Agent Development

**Question**: "Does this project actively develop Claude Code skills, agents, or plugins
— not just use them as consumers?"

**Why it matters**: Plugin development requires specialized plugin-creator knowledge:
SKILL.md frontmatter format, agent frontmatter schema, plugin.json structure, and
invocation control. Without it, agents produce structurally incorrect definitions.

**Default if skipped**: No

**Stack trigger**: .claude-plugin/ directory present OR agents/*.md files present OR
AGENTS.md at repo root

**→ `skill_rules` mapping**:

```yaml
- when: "working on SKILL.md files, agent definitions, plugin.json, hooks.json, or
  plugin structure"
  use:
    - plugin-creator:plugin-creator
    - plugin-creator:claude-skills-overview-2026
```

---

### Q8: MCP Server Development

**Question**: "Does this project define or extend MCP (Model Context Protocol) servers?"

**Why it matters**: MCP server development requires FastMCP-specific patterns: tool
registration, resource handlers, server lifecycle, and tool naming conventions. General
Python skills produce code that compiles but fails at MCP protocol level.

**Default if skipped**: No

**Stack trigger**: fastmcp in pyproject.toml dependencies OR mcp_*.py file pattern present
OR FastMCP import detected in*.py files

**→ `skill_rules` mapping**:

```yaml
- when: "implementing or modifying MCP tools, resources, prompts, or FastMCP server code"
  use:
    - fastmcp-creator:fastmcp-creator
```

---

### Q9: Claude Code Hook Automation

**Question**: "Does this project define Claude Code hooks for workflow automation
(PreToolUse, PostToolUse, Stop events)?"

**Why it matters**: Hook scripts have strict structural requirements: CJS format (.cjs
extension), hookSpecificOutput schema, exit-code semantics, and execFileSync usage.
Without the hooks-guide skill, agents produce structurally invalid hook scripts that
silently fail or error.

**Default if skipped**: No

**Stack trigger**: .claude/hooks/ directory present OR hooks.json present at repo root
or plugin directory

**→ `skill_rules` mapping**:

```yaml
- when: "creating, modifying, or debugging Claude Code hooks (PreToolUse, PostToolUse,
  Stop, SessionStart)"
  use:
    - plugin-creator:hooks-guide
    - plugin-creator:hook-creator
```

---

### Q10: Database Schema Migrations or Complex SQL

**Question**: "Does this project perform schema migrations or write complex SQL queries
(joins, aggregations, window functions)?"

**Why it matters**: Evolving schemas require migration patterns (PRAGMA user_version,
_MIGRATIONS dict, schema versioning). Performance-sensitive queries need index awareness
and EXPLAIN QUERY PLAN analysis. Standard Python skills do not cover these.

**Default if skipped**: No

**Stack trigger**: *.db files present in repo OR sqlite3/aiosqlite/databases import
detected in*.py files

**→ `skill_rules` mapping**:

```yaml
- when: "adding database tables, modifying schema, writing SQL queries, or implementing
  schema migrations"
  use:
    - sqlite-database-expert
    - sql-optimization
```

---

### Q11: Frontend Component Library

**Question**: "Does the frontend use a specific component library?
(A) shadcn/ui
(B) Radix UI primitives (without shadcn)
(C) Material UI / Ant Design / Chakra
(D) None / fully custom"

**Why it matters**: Component library choice determines which design-system skills to
inject. The wrong library's patterns produce structurally incompatible components (e.g.,
shadcn variants vs MUI sx props are not interchangeable).

**Default if skipped**: D — None / custom

**Stack trigger**: react, vue, or svelte detected in package.json dependencies

**→ `skill_rules` mapping** (for answer A):

```yaml
- when: "implementing React UI components, dashboard layouts, or interactive controls"
  use:
    - frontend-design
    - shadcn
```

*(For answer B: replace `shadcn` with `radix-ui-design-system` if available in your
installed skills. For C: use `frontend-design` alone.)*

---

### Q12: Robot Framework / Hardware-in-the-Loop Testing

**Question**: "Does this project use Robot Framework for integration, end-to-end, or
hardware-in-the-loop (HiL) testing?"

**Why it matters**: Robot Framework test files (.robot) use keyword-driven syntax that
standard pytest skills do not cover. Authoring .robot tests requires different patterns
for resource files, variable definitions, and keyword libraries.

**Default if skipped**: No

**Stack trigger**: *.robot files present in repo OR robotframework in pyproject.toml
test dependencies

**→ `skill_rules` mapping**:

```yaml
- when: "feature requires Robot Framework test cases, .robot file modifications, or
  keyword library extensions"
  use:
    - python-engineering:python3-testing
```

---

## Skip Logic Summary

| Question | Category             | Stack Trigger                                          |
|----------|----------------------|--------------------------------------------------------|
| Q1       | Testing              | Python (pyproject.toml or setup.py)                    |
| Q2       | Testing              | Python + Hypothesis or existing tests/ dir             |
| Q3       | Linting              | Any linter config file                                 |
| Q4       | Type Checking        | Python + mypy/pyright/ty in pyproject.toml             |
| Q5       | CI/CD                | CI config file (.github/, .gitlab-ci.yml, etc.)        |
| Q6       | Documentation        | Always — universal                                     |
| Q7       | Domain — Plugin      | .claude-plugin/ or agents/*.md or AGENTS.md            |
| Q8       | Domain — MCP         | fastmcp dependency or mcp_*.py files                   |
| Q9       | Domain — Hooks       | .claude/hooks/ or hooks.json                           |
| Q10      | Domain — Database    | *.db files or sqlite/aiosqlite imports                 |
| Q11      | Domain — Frontend    | react/vue/svelte in package.json                       |
| Q12      | Domain — Robot       | *.robot files or robotframework in test deps           |

**Expected question count per project type**:

- Pure Python CLI project: Q1, Q2, Q3, Q4, Q5, Q6 → 6 questions
- Claude Code plugin project: Q1, Q3, Q4, Q5, Q6, Q7, Q8, Q9 → 8 questions (likely filtered further)
- Full-stack web app with database: Q3, Q5, Q6, Q10, Q11 → 5 questions
- Embedded/QA project with Robot Framework: Q1, Q3, Q5, Q6, Q12 → 5 questions
