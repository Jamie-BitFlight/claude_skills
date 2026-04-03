# Python CLI Architecture Spec Patterns

Reference for the `python-cli-design-spec` agent. Contains the project-level technology
decisions, component templates, and integration patterns that go into `architect-{slug}.md`.

---

## Standard Technology Stack

### Core Framework

- **CLI Framework**: Typer 0.21.2+ (includes Rich for terminal output)
- **Type System**: Python 3.11+ native type hints (no `Optional`, `List`, `Dict`)
- **Configuration**: `tomlkit` for TOML read/write (preserves formatting, comments); `tomllib` only for stdlib-only scripts. `pydantic-settings` for validation
- **Package Manager**: uv for dependency management and execution

### CLI Components

- **Command Parsing**: Typer with `Annotated` syntax
- **Output Formatting**: Rich (tables, panels, progress bars, syntax highlighting)
- **Input Validation**: Pydantic models with type coercion
- **Error Handling**: Custom exception hierarchy with Rich-formatted messages

### Development Tools

- **Testing**: pytest 8+ with coverage, pytest-mock (never `unittest.mock` directly)
- **Type Checking**: ty (Astral's type checker, primary); basedpyright/pyright as alternative
- **Linting/Formatting**: ruff
- **Pre-commit**: prek or pre-commit (detect from `.git/hooks/pre-commit`)

### Distribution Strategies

**Strategy 1 — PEP 723 Standalone Script** (single-file tools, <500 lines, 1-5 deps):

- Shebang: `#!/usr/bin/env -S uv --quiet run --active --script`
- PEP 723 metadata block with `requires-python` and `dependencies`
- Executable permissions required
- Reference: activate `python3-development:shebangpython` for compliance

**Strategy 2 — Python Package** (multi-file tools, complex logic):

```text
packages/{package_name}/    # hyphens in project name → underscores
├── __init__.py
├── cli.py                  # Typer commands only
├── core/                   # Business logic (pure Python, no I/O)
├── services/               # External I/O, APIs, filesystem
└── utils/                  # Shared helpers
tests/                      # Mirror source structure
pyproject.toml
```

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatchling.build.targets.wheel]
packages = ["packages/{package_name}"]
```

---

## Component Design Templates

### CLI Layer (cli.py)

- Purpose: command parsing, validation, user interaction — no business logic
- Technology: Typer with `Annotated[Path, typer.Argument(exists=True)]` syntax
- `rich_help_panel` for command grouping
- Delegates all processing to core layer

### Core Layer (core/)

- Purpose: business logic, orchestration, data processing — pure Python, no I/O
- Input: type-safe data models
- Output: result objects with `is_valid: bool`, `errors: list[str]`, `warnings: list[str]`
- No exceptions for expected failures (return result objects); exceptions for bugs

### Service Layer (services/)

- Purpose: external integrations, file I/O, API calls
- Async where beneficial, sync for simple operations
- Typed requests and typed responses or exceptions
- NEVER `shell=True` in subprocess calls

### Utils (utils/)

- Path utilities using `shutil.which(command)` for external command location
- Rich table builders
- Formatting helpers

---

## Error Handling Architecture

### Exception Hierarchy

```text
ToolError (base)
├── ConfigurationError   — invalid config, missing required settings
├── ValidationError      — invalid input data
├── ProcessingError      — business logic failures
├── ExternalServiceError — API, network, subprocess failures
└── ResourceError        — file not found, permissions, disk
```

- `raise SpecificError("message") from original_exc` — preserve stack traces
- `__init__` stores message and `**context` kwargs as attributes
- No stack traces in user-facing output (unless `--verbose`)

### Exit Codes

- `0`: Success
- `1`: General error (validation, processing, configuration)
- `2`: Command-line usage error
- `130`: Interrupted (Ctrl+C)

### Rich Error Display

- `Rich Panel` with red border, `:cross_mark:` in title
- All errors shown at once (never fail-on-first for validation)
- Error messages are actionable: what is wrong + how to fix

---

## Security Architecture

- Configuration storage: `XDG_CONFIG_HOME` or `~/.config/tool/`
- Secret handling: environment variables or keyring (never in config files or logs)
- Secure file permissions: `0600` for credential files
- Subprocess: NEVER `shell=True`; pass command+args as list
- Input validation checklist for specs:
  - [ ] Path traversal prevention
  - [ ] Command injection prevention
  - [ ] Secure temp file handling
  - [ ] Rate limiting for API calls
  - [ ] Certificate validation for HTTPS

---

## Scalability and Resource Management

- Async I/O for concurrent operations; semaphores to cap concurrency
- Memory-efficient file processing (streaming for large files)
- Context managers for resource lifecycle
- Graceful shutdown on SIGINT/SIGTERM
- Lazy loading of expensive resources
- Progress bars for operations >2 seconds or multiple items

---

## Monitoring and Observability

### Logging Configuration

```python
# RichHandler for console; FileHandler for persistent logs
logging.basicConfig(
    level=log_level.upper(),
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True, markup=True)]
)
```

### Progress Bar Components

- `SpinnerColumn` + `TextColumn` + `BarColumn` + `TaskProgressColumn` + `TimeRemainingColumn`
- `with Progress(...) as progress:` — automatic cleanup
- Use for: multi-item operations, known-count operations, operations >2 seconds

---

## Architectural Patterns

### Factory Pattern for Dependency Injection

- Protocol classes define dependency contracts (structural typing via `Protocol`)
- Factory creates configured instances for production vs. testing
- Enables mock injection in tests without changing client code

### Strategy Pattern for Command Processing

- `Protocol` with `process()` method signature
- Processor holds strategy reference and delegates
- Use when: multiple algorithms for same task, runtime algorithm selection

### Validation with match-case

- `StrEnum` for valid types/categories (IDE autocomplete, exhaustiveness checking)
- `match value:` with `case _:` wildcard that raises `ValueError`
- More readable than `if/elif` chains; mypy warns on missing cases

---

## Integration Patterns

### External Command Verification

```python
# Use shutil.which — raise FileNotFoundError with actionable message if missing
if not (cmd := shutil.which("docker")):
    raise FileNotFoundError("docker not found — install from https://docker.com")
```

Collect ALL missing commands before failing — display them all in one error.

### Safe Subprocess

```python
subprocess.run(
    [str(cmd_path), *args],  # list, never string
    capture_output=True,
    text=True,
    check=True,
    cwd=working_dir,
)
```

### Configuration Loading

Search order: explicit path → `.mytool.toml` → `~/.config/mytool/config.toml` → `/etc/mytool/config.toml`

- TOML: preferred for human-editable config. Use `tomlkit` for read and write (preserves formatting, comments). Use `tomllib` (stdlib) only when the script must remain stdlib-only.
- JSON: programmatic config
- YAML: use `ruamel.yaml` (not `pyyaml`) when YAML is required
- Validate with Pydantic; support env var overrides

---

## Architectural Decisions (Default ADRs)

Include these ADRs in every architecture spec unless the requirements justify deviation:

| ADR | Decision | Rationale |
|-----|----------|-----------|
| ADR-001 | Typer for CLI framework | Type safety, automatic help, Rich included |
| ADR-002 | PEP 723 for standalone tools | Zero-setup execution, single-file distribution |
| ADR-003 | ty for type checking | Astral's ty is the primary type checker; catches bugs at development time, fast iteration |

Add project-specific ADRs for non-standard decisions.

---

## Review Compliance Requirements

Architecture specs MUST prescribe patterns that pass the project's review pipeline on first
assessment. The review pipeline consists of three stages:

### Stage 1: Code Smell and Modernization Analysis (`stinkysnake` + `modernpython`)

The spec must prescribe:

- Python 3.11+ builtin generics (`list[str]`, `dict[str, int]`) — never `typing.List`, `typing.Dict`
- Pipe union syntax (`X | None`) — never `Optional[X]`
- `StrEnum` for all finite string value sets (status codes, categories, modes)
- `match-case` for branching on discrete values — never `if/elif` chains on the same variable
- `Self` type (PEP 673) for fluent builder APIs and method chaining
- Exception notes (PEP 678) via `e.add_note()` for enriching re-raised exceptions
- `tomlkit` for TOML read and write (preserves formatting, comments); `tomllib` only for stdlib-only scripts
- `ruamel.yaml` for YAML (not `pyyaml`)
- Typer with `Annotated` syntax for all CLI parameters
- Rich tables with explicit width measurement pattern
- `pytest-mock` (`MockerFixture`) — never `unittest.mock` directly

### Stage 2: Shebang and Distribution Validation (`shebangpython`)

The spec's Distribution Architecture section must prescribe:

- **Standalone scripts with external deps**: shebang `#!/usr/bin/env -S uv --quiet run --active --script` + PEP 723 metadata block
- **Stdlib-only scripts**: shebang `#!/usr/bin/env python3` — no PEP 723 block
- **Package modules**: no shebang (not directly executable)
- **Transitive deps**: typer bundles rich and shellingham — never list them separately in PEP 723
- **Execute bit**: all files with shebangs must have `chmod +x`

### Stage 3: Code Review (`code-reviewer`)

The spec must prescribe architecture that satisfies:

- Layered architecture: CLI → Core (pure logic, no I/O) → Services (external I/O) → Display
- Data models in `shared/` using Pydantic v2, dataclasses, or StrEnum
- Constants and exceptions in `shared/`
- Protocol classes for dependency injection at service boundaries
- Fail-fast error handling (catch only with specific recovery action)
- `from __future__ import annotations` at top of every file
- 80% minimum test coverage target
