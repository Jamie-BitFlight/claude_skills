---
name: standards-for-python-development
description: "Shared Python 3.11+ development rules — type safety and the boundary policy for `Any` (ty, native generics, Protocol, TypeIs, Pydantic), layered architecture and SOLID, error handling, security, performance, identifier naming, PEP 723 script dependencies, Rich/Typer output, tooling defaults (uv, ruff, ty, hatchling, pytest), and testing requirements (behavioral coverage, TDD). Activates when any Python skill or agent needs the shared rules for implementation, code review, refactoring, or test authoring."
user-invocable: false
---

# Python 3 Development Standards

This document holds the rules. `python-engineering:python3-core` routes a task to the specialist
skill that applies them and carries this plugin's reference files; the bare filenames cited below
are indexed in its References table.

## 1. Shared Development Standards

### 1.0 Applicability and precedence

These are strong defaults for new Python work, not a mandate to redesign a coherent existing project.

Apply constraints in this order:

1. Explicit user requirements and safety/security constraints.
2. The target repository's supported Python versions, public contracts, architecture, dependencies, CI, formatter/linter/type-checker configuration, and established local conventions.
3. Framework/library ecosystem conventions.
4. These plugin defaults.

Do not introduce a dependency, abstraction, architectural layer, compatibility change, or broad modernization solely to satisfy a default below. When existing project practice is coherent and safe, preserve it. When it conflicts with correctness, security, an explicit requirement, or its own declared contract, surface the conflict and make the smallest justified change.

For every change, preserve unrelated behavior and APIs. Trace the demonstrated change surface, then modify only what the requirement and affected contracts need; do not opportunistically modernize adjacent code.


### 1.1 Type Safety & Modern Patterns
- **Native Types**: Use Python 3.11+ native type hints (`list[str]`, `dict[str, int]`, `str | None`) instead of legacy `typing` imports (`List`, `Dict`, `Optional`, `Union`).
- **`Any` Boundary Policy**: Prefer precise types. Contain `Any`, broad `object`, and unchecked `cast()` at explicit dynamic or external boundaries and convert to stronger internal types as soon as practical. A narrowly justified `Any` is preferable to dishonest or excessively complex typing when a third-party API, plugin protocol, decorator, or deliberately dynamic interface cannot be expressed accurately. **Localize policy exceptions by file**: put the ingest/parser/adapter methods or classes that genuinely require the exception in a dedicated boundary module and configure the linter/type checker exception for that file. Do not scatter inline suppressions through otherwise strongly typed modules. The exception file is an architectural boundary and should expose typed outputs to the rest of the system.
- **Data Structures**: Prefer Pydantic `BaseModel` when runtime validation/serialization materially benefits a boundary or agent-facing JSON contract. Prefer dataclasses for typed internal value objects and `TypedDict` for typed mapping shapes when runtime validation is unnecessary. Preserve a coherent existing choice rather than migrating shapes without a demonstrated benefit.
- **Duck Typing**: Use `typing.Protocol` for structural subtyping instead of ABCs where appropriate.
- **Narrowing**: Use `TypeIs` (PEP 742, Python 3.13+) for bidirectional type narrowing. Use `TypeGuard` only when targeting Python < 3.13 without `typing_extensions`.
- **Modern Operators**: Utilize the walrus operator (`:=`) and `match-case` statements where they improve readability.
- **Type Checking**: Use **ty** (Astral) as the default checker — `uv run ty check` (paths per project). Detect the active checker from `.pre-commit-config.yaml`, then CI, never from a config table alone: repos keep `[tool.mypy]`, `[tool.basedpyright]`, or `pyrightconfig.json` as IDE stubs while hooks run ty. When hooks or CI actually run mypy, basedpyright, or pyright, follow that project's configuration rather than forcing a migration. When migrating to ty, silence those stub tables (`exclude = [".*"]`, `typeCheckingMode = "off"`) instead of deleting them, so built-in IDE checkers stop duplicating ty. See the `python-engineering:ty` skill.
- **Parsing**: Use `tomlkit` to read and write TOML (it preserves formatting and comments); `tomllib` (stdlib) only for stdlib-only scripts. Parse markdown through the `marko` AST, never a regex parser — add it with `uv add marko` when the project does not already depend on it.
- **Type Safety Reference**: For Generics, Protocols, TypedDict, Type Narrowing, and the attrs/dataclasses/pydantic comparison, see `type-safety-mypy.md` in the `python-engineering:python3-typing` skill. (Filename references mypy docs; patterns apply to ty and other checkers unless a rule is mypy-specific.)
- **Version-Specific Features**: Check the project's `requires-python` floor against the per-version supplements, `python311-features.md` through `python314-features.md`.
- **Version Lifecycle** (SOURCE: <https://devguide.python.org/versions>, accessed 2026-03-23): 3.10 EOL 2026-10, 3.11 security-only until 2027-10, 3.12 security-only until 2028-10, 3.13 bugfix until 2029-10, 3.14 bugfix until 2030-10. When choosing a `requires-python` floor, prefer versions still in bugfix status.

### 1.2 Architecture & Design
- **Boundaries**: Separate concerns where they change for different reasons. For CLI applications, a useful default is CLI → Core Logic → Services → Output boundary; do not manufacture layers that contain no independent responsibility.
- **Models**: Keep shared domain models/constants/exceptions in an obvious stable module when multiple consumers need them; do not create a `shared/` directory merely to satisfy the pattern.
- **Dependency Injection**: Use direct parameters first. Introduce `Protocol` boundaries when multiple implementations, external services, testing seams, or architectural isolation justify them.
- **SOLID**: Use SOLID as design pressure toward cohesive responsibilities, explicit dependencies, substitutable contracts, and small interfaces. Do not add indirection merely to demonstrate a principle.
- **Construction**: Prefer direct construction while it remains clear. Introduce factories/builders when construction policy is complex, repeated, conditional, or needs isolation.
- **Module Hygiene**: Keep functions and modules small enough that their behavior and dependencies remain understandable. Long functions, deep nesting, large files, circular imports, and sprawling public surfaces are investigation triggers, not numeric failures. Split by responsibility when doing so improves cohesion or comprehension.
- **Code Smells**: Treat a smell as a design signal to investigate and follow back to the design that produced it, not as noise to suppress.

### 1.3 Error Handling & Security
- **Fail-Fast**: Catch an exception only where you have a specific recovery action or context to add. Let everything else propagate to the caller. Never use bare `except:` or swallow exceptions silently.
  ```python
  def get_user(user_id):
      try:
          return db.query(User, user_id)
      except ConnectionError:
          logger.warning("DB unavailable, using cache")
          return cache.get(f"user:{user_id}")  # Specific recovery action
  ```
- **Contextualize**: Use `e.add_note()` or `raise ... from e` to add context to re-raised exceptions.
- **Security**:
  - Prevent SQL injection (use parameterized queries).
  - Prevent command injection (never use `shell=True` with user input).
  - Validate all external inputs.
  - Never hardcode secrets.

### 1.4 Performance
- **Data structures**: Choose structures for semantics first and complexity second; use sets for repeated membership checks when ordering/duplicates are irrelevant.
- **I/O**: Use async/concurrency when the workload and surrounding architecture benefit from overlapping I/O; do not convert synchronous code merely because the work is I/O-bound. Never block an existing async event loop with avoidable synchronous I/O.
- **Caching**: Cache only demonstrated repeated expensive work when invalidation, memory, and concurrency semantics are understood.
- **Performance**: Prefer clear idiomatic code until measurement identifies a material bottleneck; optimize the measured path and retain a benchmark when performance is a contract.

### 1.5 Identifier Naming

- **Expand Acronyms**: Expand acronyms in public function names, method names, and class
  names. `gcd()` is opaque; `greatest_common_divisor()` is self-documenting.
  SOURCE: TheAlgorithms/Python `CONTRIBUTING.md` (accessed 2026-04-27) — "Expand acronyms
  because `gcd()` is hard to understand but `greatest_common_divisor()` is not."
- **Contrast Example**: Prefer `greatest_common_divisor(a, b)` over `gcd(a, b)` for any
  public API.
- **Domain Acronym Exceptions**: Established domain acronyms that are the standard term
  in their field may remain abbreviated. Per PEP 8, they appear lowercase in `snake_case`
  identifiers: `url`, `api`, `sql`, `http`, `json`, `xml`.
  Example: `parse_url()`, `fetch_api_response()`, `run_sql_query()`.
- **Local Variable Scope**: Short names are acceptable for local variables with a lifetime
  under 5 lines (loop indices, comprehension variables, short closures). Expand acronyms
  when the variable is referenced beyond 5 lines of its definition.
- **No Cargo-Cult Privacy**: A leading underscore is an architectural claim that an identifier is intentionally non-public. Do not add one merely because a helper, local function, module constant, import alias, or implementation detail "looks private." Treat speculative privacy like premature optimization and YAGNI: require a concrete boundary or collision it protects.
- **Public by Default**: Name new functions, modules, variables, and import aliases without a leading underscore. Introduce an underscore only when an established API boundary, framework convention, name-mangling requirement, or concrete collision makes privacy meaningful.
- **An Existing Underscore Is a Finding**: Establish what it defends against before keeping it.
  Bind the bare name instead and see whether the module already binds it; if nothing collides,
  the prefix is habit — drop it. A dotted import needs an alias because `import a.b` binds only
  `a`, so prefer `import a.b as ab` over `import a.b as _ab`.
- **Fix the Collision, Not the Name**: Where a collision is real, two shapes recur — a wrapper
  that shadows the function it delegates to, and a local name that shadows a third-party one.
  The collision is the defect; the alias is the symptom. A per-file `private-member-access` lint
  exemption is the same signal at file scale.

### 1.6 Script Dependencies
For a new human-facing CLI where third-party dependencies are acceptable, Typer + Rich are the preferred defaults. For a CLI shipped inside an Agent Skill or plugin, prefer a stable compact JSON contract and do not add Rich for command output. For existing projects, preserve their coherent CLI framework and dependency policy.

Before adding any dependency, establish that it materially reduces complexity or strengthens the required contract enough to justify installation, compatibility, supply-chain, and maintenance cost. Use stdlib when it already solves the problem clearly; choose stdlib-only when deployment constraints require it.

For inline-block syntax, shebang form, and how a script that outgrows one file imports its own
modules, see `PEP723.md`.

### 1.7 UI & CLI (Rich / Typer)
- **Rich Emoji Usage**: In Rich console output, always use Rich emoji tokens (e.g., `:white_check_mark:`) instead of literal Unicode emojis. This ensures cross-platform compatibility, consistent rendering, and markdown-safe alignment.
- **Width Handling**: For Rich table and panel width patterns, use `Measurement.get(console, console.options, renderable)`. See `typer-rich-non-tty-patterns.md` in the `python3-cli` skill for examples.

### 1.8 Testing & Documentation
- **Test-First (TDD)**: Write failing tests against defined interfaces before implementing logic.
- **Framework**: Prefer `pytest` for new projects. Preserve an existing coherent test framework. Prefer fakes, dependency injection, `monkeypatch`, or `pytest-mock` according to the test seam; do not add `pytest-mock` solely to replace working `unittest.mock` usage.
- **Coverage**: Cover changed behavior, public contracts, boundaries, regressions, and meaningful failure paths. Respect an existing repository coverage gate; do not invent a percentage target when none exists. Inspect uncovered changed branches for risk. Use mutation testing for critical logic when it materially strengthens confidence.
- **Test Quality**:
  - Follow the AAA (Arrange-Act-Assert) pattern.
  - Test names must describe behavior, not implementation (e.g., `test_process_payment_when_insufficient_funds_returns_declined`).
  - Tests must be isolated and independent.
- **Test Failure Mindset**: Treat every test failure as a potential bug discovery, not an annoyance. Use a dual-hypothesis approach (Test is wrong vs. Implementation is wrong). Never automatically change a test to match the implementation.
- **Docstrings**: For new public APIs, prefer concise Google-style docstrings when the signature and name do not already communicate the contract or when behavior, errors, units, side effects, or invariants need explanation. Follow an established project documentation style.
- **Sync Docs**: Update documentation, examples, architecture records, changelog/release notes, and generated artifacts when the changed contract has consumers there; follow the repository's established documentation and release conventions.

### 1.9 Tooling Defaults
`uv` for dependency management, `ruff` for linting and formatting, `ty` for type checking, `pytest` for tests, and `hatchling` as the build backend are defaults for new projects. Existing project tooling is authoritative when it is coherent and supported; use the commands and configuration actually enforced by hooks/CI rather than adding parallel tooling.

---

## 2. Reviewing and Amending Standards

These standards are a living artifact. When you discover a new best practice, a missing ecosystem
tool, or a rule here that contradicts official Python documentation, update this document.

1. **Identify the gap**: The trigger is a recurring failure mode an agent hits, a new tool entering
   the ecosystem, or an explicit request for a standard update. State it.
2. **Verify against a primary source**: Check the proposed rule against Python PEPs or official
   library documentation (`docs.python.org`, `docs.pytest.org`, `docs.astral.sh`) before writing
   it. A measured sweep of real code is also a primary source — record the command and the commit
   that reproduce it.
3. **Compare**: Weigh the verified practice against Section 1. A gap exists when the concept is
   missing or the existing rule is the anti-pattern.
4. **Write it**: Add or modify bullets in the Section 1 subsection the rule belongs to. Keep the
   rule concise, imperative, and free of counts or repository-specific paths — this document ships
   to other repositories.
5. **Validate**: Confirm the new rule contradicts nothing else in this document.
