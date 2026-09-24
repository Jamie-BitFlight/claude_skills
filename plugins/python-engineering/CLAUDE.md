# python-engineering Plugin — AI-Facing Documentation

Opinionated Python 3.11+ engineering system. Establishes strong defaults and routes to specialist skills.

---

## Architecture

### One Automatic Router

- `python-engineering:python3-core` — loads on every Python task, establishes defaults, routes to specialists

### Entrypoints (user and model invocable)

- `/python-engineering:orchestrate` — multi-step engineering workflow
- `/python-engineering:review` — code review
- `/python-engineering:lint` — deterministic quality checks
- `/python-engineering:cleanup` — structured cleanup and modernization
- `/python-engineering:debug` — structured debugging

### Specialist Skills (auto-loaded by router when relevant)

The Domain Routing table in `skills/python3-core/SKILL.md` names every specialist and the task
that selects it. Read it there; this file does not restate the list.

### Agents (Python-specific)

- `@python-engineering:python-cli-architect` — implements Python CLI features
- `@python-engineering:python-cli-design-spec` — produces architecture specs for CLIs
- `@python-engineering:python-pytest-architect` — writes pytest test suites
- `@python-engineering:code-reviewer` — general code review with Python awareness
- `@python-engineering:semantic-code-search` — pattern and structure search over Python codebases

---

## Typing Policy

Universal rules (all lanes):
- `Any`, broad `object`, and unchecked `cast()` are forbidden in internal code
- Allowed only at explicit system boundaries
- Boundary code must validate immediately and return typed objects
- Boundary modules may be the only place with narrow lint exceptions for `Any`

Strategy auto-detected from Python version and dependencies. See `python3-core` for routing to `python3-typing`.

---

## References

All detailed reference material lives in `references/` subdirectories of specialist skills. One level deep from SKILL.md — no nested reference chains.

- `skills/standards-for-python-development/SKILL.md` — the shared rules every other skill applies
- `skills/python3-core/references/typing-matrix.md` — version/dependency typing matrix
- `skills/python3-typing/references/typing-policy.md` — boundary validation policy
- `skills/python3-typing/references/pydantic-boundaries.md` — Pydantic patterns
- `skills/python3-typing/references/hypothesis-boundaries.md` — property-based testing
- `skills/python3-testing/references/testing-standards.md` — testing standards
- `skills/python3-cli/references/typer-*.md` — Typer app, parameters, subcommands, testing, advanced patterns
- `skills/python3-cli/references/rich-*.md` — Rich console, renderables, progress, logging, text, advanced patterns
- `skills/python3-cli/references/typer-rich-*.md` — tables, non-TTY width, exception handling, testing patterns
- `skills/python3-tools/references/tooling-defaults.md` — tooling defaults
- `skills/python3-tools/references/compatibility-lanes.md` — compatibility guidance

---

## Key Design Decisions

1. One automatic router, not multiple overlapping routers
2. Entrypoints are invocable by both user and model; `orchestrate` removed `disable-model-invocation`
3. Specialist skills use `user-invocable: false` (auto-loaded only)
4. Reference material is one level deep (no nested chains)
5. SKILL.md stays under 500 lines; deep detail in references/
6. Scripts for deterministic checks, not prose
