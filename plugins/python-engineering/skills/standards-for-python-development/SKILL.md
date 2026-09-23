---
name: standards-for-python-development
description: "Shared Python 3.11+ development rules — type safety and the boundary policy for `Any` (ty, native generics, Protocol, TypeIs, Pydantic), layered architecture and SOLID, error handling, security, performance, identifier naming, PEP 723 script dependencies, Rich/Typer output, tooling defaults (uv, ruff, ty, hatchling, pytest), and testing requirements (80% coverage, TDD). Activates when any Python skill or agent needs the shared rules for implementation, code review, refactoring, or test authoring."
user-invocable: false
---

# Python 3 Development Standards

This document holds the rules. `python-engineering:python3-core` routes a task to the specialist
skill that applies them and carries this plugin's reference files; the bare filenames cited below
are indexed in its References table.

## 1. Shared Development Standards

### 1.1 Type Safety & Modern Patterns
- **Native Types**: Use Python 3.11+ native type hints (`list[str]`, `dict[str, int]`, `str | None`) instead of legacy `typing` imports (`List`, `Dict`, `Optional`, `Union`).
- **`Any` Boundary Policy**: `Any`, broad `object`, and unchecked `cast()` belong only in dedicated validator, parser, adapter, or boundary modules, where unknown-shape external data enters. Those modules validate and convert raw input into strongly typed internal objects immediately, so the typed core never receives an unvalidated payload. Everywhere else, replace `Any` with a specific type, `TypeVar`, `Generic`, or `Protocol`. A narrow lint exception for `Any` belongs to a boundary module or nowhere.
- **Data Structures**: Prefer a Pydantic `BaseModel` for structured data — CLI output, tool payloads, parsed file records. `TypedDict` (with `NotRequired`) and `dataclasses` (with `slots=True, frozen=True`) are the right shape in a confirmed stdlib-only context. Typing lane selection follows what a file already imports, so an existing `@dataclass` is never reconsidered on its own — choose the shape when adding or touching it.
- **Duck Typing**: Use `typing.Protocol` for structural subtyping instead of ABCs where appropriate.
- **Narrowing**: Use `TypeIs` (PEP 742, Python 3.13+) for bidirectional type narrowing. Use `TypeGuard` only when targeting Python < 3.13 without `typing_extensions`.
- **Modern Operators**: Utilize the walrus operator (`:=`) and `match-case` statements where they improve readability.
- **Type Checking**: Use **ty** (Astral) as the default checker — `uv run ty check` (paths per project). Detect the active checker from `.pre-commit-config.yaml`, then CI, never from a config table alone: repos keep `[tool.mypy]`, `[tool.basedpyright]`, or `pyrightconfig.json` as IDE stubs while hooks run ty. When hooks or CI actually run mypy, basedpyright, or pyright, follow that project's configuration rather than forcing a migration. When migrating to ty, silence those stub tables (`exclude = [".*"]`, `typeCheckingMode = "off"`) instead of deleting them, so built-in IDE checkers stop duplicating ty. See the `python-engineering:ty` skill.
- **Parsing**: Use `tomlkit` to read and write TOML (it preserves formatting and comments); `tomllib` (stdlib) only for stdlib-only scripts. Parse markdown through the `marko` AST, never a regex parser — add it with `uv add marko` when the project does not already depend on it.
- **Type Safety Reference**: For Generics, Protocols, TypedDict, Type Narrowing, and the attrs/dataclasses/pydantic comparison, see `type-safety-mypy.md` in the `python-engineering:python3-typing` skill. (Filename references mypy docs; patterns apply to ty and other checkers unless a rule is mypy-specific.)
- **Version-Specific Features**: Check the project's `requires-python` floor against the per-version supplements, `python311-features.md` through `python314-features.md`.
- **Version Lifecycle** (SOURCE: <https://devguide.python.org/versions>, accessed 2026-03-23): 3.10 EOL 2026-10, 3.11 security-only until 2027-10, 3.12 security-only until 2028-10, 3.13 bugfix until 2029-10, 3.14 bugfix until 2030-10. When choosing a `requires-python` floor, prefer versions still in bugfix status.

### 1.2 Architecture & Design
- **Layered Architecture**: Separate concerns into clear boundaries: CLI → Core Logic → Services → Display/UI.
- **Shared Models**: Define data models, constants, and exceptions in a `shared/` or `models/` directory.
- **Dependency Injection**: Use `Protocol` classes to define expected interfaces for external services, allowing easy mocking.
- **SOLID**: Apply SOLID as active design guidance while writing, not as a checklist run afterwards.
- **Factory Patterns**: Use a factory for complex object construction rather than a long constructor.
- **Module Hygiene**: Keep functions under 50 lines, avoid deep nesting (>3 levels), prevent circular imports, and define `__all__` in public modules.
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
- **O(1) Lookups**: Use `set` for membership testing instead of `list`.
- **I/O**: Use async patterns (`asyncio`, `httpx`) for I/O-bound operations. Avoid synchronous I/O in async contexts.
- **Caching**: Cache repeated expensive function calls.
- **String Building**: Avoid string concatenation in loops; use `.join()` or list comprehensions.

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
- **Public by Default**: Name new functions, modules, variables, and import aliases without a
  leading underscore. Add privacy once a caller needs it.
- **An Existing Underscore Is a Finding**: Establish what it defends against before keeping it.
  Bind the bare name instead and see whether the module already binds it; if nothing collides,
  the prefix is habit — drop it. A dotted import needs an alias because `import a.b` binds only
  `a`, so prefer `import a.b as ab` over `import a.b as _ab`.
- **Fix the Collision, Not the Name**: Where a collision is real, two shapes recur — a wrapper
  that shadows the function it delegates to, and a local name that shadows a third-party one.
  The collision is the defect; the alias is the symptom. A per-file `private-member-access` lint
  exemption is the same signal at file scale.

### 1.6 Script Dependencies
Default to Typer + Rich declared in a PEP 723 inline block: less code to write, better output, and
a single-file executable that `uv` resolves at launch. The cost is network access on first run.

Choose stdlib-only — manual `argparse`, manual formatting, plainer output — for a confirmed
deployment restriction such as an air-gapped or locked-down environment, never as a default
posture.

For inline-block syntax, shebang form, and how a script that outgrows one file imports its own
modules, see `PEP723.md`.

### 1.7 UI & CLI (Rich / Typer)
- **Rich Emoji Usage**: In Rich console output, always use Rich emoji tokens (e.g., `:white_check_mark:`) instead of literal Unicode emojis. This ensures cross-platform compatibility, consistent rendering, and markdown-safe alignment.
- **Width Handling**: For Rich table and panel width patterns, use `Measurement.get(console, console.options, renderable)`. See `typer-rich-non-tty-patterns.md` in the `python3-cli` skill for examples.

### 1.8 Testing & Documentation
- **Test-First (TDD)**: Write failing tests against defined interfaces before implementing logic.
- **Framework**: Use `pytest` with `pytest-mock` (avoid `unittest.mock`).
- **Coverage**: Maintain a minimum of 80% test coverage, ensuring edge cases are handled. Critical paths require 95%+ coverage and mutation testing.
- **Test Quality**:
  - Follow the AAA (Arrange-Act-Assert) pattern.
  - Test names must describe behavior, not implementation (e.g., `test_process_payment_when_insufficient_funds_returns_declined`).
  - Tests must be isolated and independent.
- **Test Failure Mindset**: Treat every test failure as a potential bug discovery, not an annoyance. Use a dual-hypothesis approach (Test is wrong vs. Implementation is wrong). Never automatically change a test to match the implementation.
- **Docstrings**: Use Google-style docstrings (Args/Returns/Raises) for all public functions and classes.
- **Sync Docs**: Ensure `CLAUDE.md` and architecture documents are updated when adding new commands or modules.

### 1.9 Tooling Defaults
`uv` for dependency management, `ruff` for linting and formatting, `ty` for type checking,
`pytest` for tests, `hatchling` as the build backend. Keep a checker or build backend the project
already runs in its hooks or CI.

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
