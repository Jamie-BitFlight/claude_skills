# python-engineering Plugin — AI-Facing Documentation

Opinionated Python 3.11+ engineering system. Establishes strong defaults and routes to specialist skills.

---

## Architecture

### One Automatic Router

- `python-engineering:python3-core` — loads on every Python task, establishes defaults, routes to specialists

### Manual Entrypoints (user-invoked only)

- `/python-engineering:orchestrate` — multi-step engineering workflow
- `/python-engineering:review` — code review
- `/python-engineering:lint` — deterministic quality checks
- `/python-engineering:cleanup` — structured cleanup and modernization
- `/python-engineering:debug` — structured debugging

### Specialist Skills (auto-loaded by router when relevant)

- `python-engineering:python3-typing` — typed-boundary and validation policy
- `python-engineering:python3-testing` — TDD, pytest, property-based testing
- `python-engineering:python3-cli` — CLI and script development (Typer/Rich)
- `python-engineering:python3-web` — web and API development
- `python-engineering:python3-data` — data and scientific Python
- `python-engineering:python3-stdlib-only` — constrained/legacy environments
- `python-engineering:python3-tools` — uv, Hatchling, ty, pre-commit, packaging
- `python-engineering:python3-tdd` — TDD workflow entrypoint

### Agents (Python-specific)

- `@python-engineering:python-cli-architect` — implements Python CLI features
- `@python-engineering:python-cli-design-spec` — produces architecture specs for CLIs
- `@python-engineering:python-pytest-architect` — writes pytest test suites
- `@python-engineering:code-reviewer` — general code review with Python awareness
- `@python-engineering:semantic-code-search` — semantic search over Python codebases

### Shared Workflow Agents (development-harness)

Language-agnostic agents use the `@dh:` prefix. Do not duplicate them here.

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

- `skills/python3-core/references/python3-standards.md` — unified standards
- `skills/python3-core/references/typing-matrix.md` — version/dependency typing matrix
- `skills/python3-typing/references/typing-policy.md` — boundary validation policy
- `skills/python3-typing/references/pydantic-boundaries.md` — Pydantic patterns
- `skills/python3-typing/references/hypothesis-boundaries.md` — property-based testing
- `skills/python3-testing/references/testing-standards.md` — testing standards
- `skills/python3-cli/references/typer-patterns.md` — Typer patterns
- `skills/python3-cli/references/rich-patterns.md` — Rich patterns
- `skills/python3-tools/references/tooling-defaults.md` — tooling defaults
- `skills/python3-tools/references/compatibility-lanes.md` — compatibility guidance

---

## Key Design Decisions

1. One automatic router, not multiple overlapping routers
2. Manual entrypoints use `disable-model-invocation: true`
3. Specialist skills use `user-invocable: false` (auto-loaded only)
4. Reference material is one level deep (no nested chains)
5. SKILL.md stays under 500 lines; deep detail in references/
6. Scripts for deterministic checks, not prose
