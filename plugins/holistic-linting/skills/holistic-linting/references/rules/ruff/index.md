# Ruff Linting Rules Reference

This directory contains comprehensive documentation for Ruff linting rules organized by rule family. Ruff is an extremely fast Python linter written in Rust, compatible with Flake8, isort, pydocstyle, pyupgrade, and many other linters.

## Rule Structure

Ruff rules follow a standardized naming convention:

- **Prefix**: 1-3 letter code indicating the rule source (e.g., `F` for Pyflakes, `E` for pycodestyle)
- **Number**: Three digits representing the specific rule (e.g., `401`)
- **Full Code**: Combined prefix and number (e.g., `F401`)

Rule counts vary by Ruff version — run `ruff rule --all` for the current, authoritative list across all rule families below.

## Rule Families

### Core Style and Errors

- [E/W: pycodestyle](./pycodestyle-errors-warnings.md) - Python code style conventions
- [F: Pyflakes](./pyflakes.md) - Logical errors and undefined names

### Code Quality and Best Practices

- [B: flake8-bugbear](./flake8-bugbear.md) - Common bugs and design problems
- [C: flake8-comprehensions](./flake8-comprehensions.md) - Comprehension patterns
- [S: flake8-bandit](./flake8-bandit.md) - Security issues
- [U: pyupgrade](./pyupgrade.md) - Python syntax modernization

### Documentation and Naming

- [D: pydocstyle](./pydocstyle.md) - Docstring conventions
- [N: pep8-naming](./pep8-naming.md) - Naming conventions

### Import Management

- [I: isort](./isort.md) - Import sorting and organization
- [ICN: flake8-import-conventions](./import-conventions.md) - Import naming conventions

### Type Checking and Annotations

- [T: Type checking](./type-checking.md) - Type-related rules
  - TC: flake8-type-checking - Type checking imports
  - T20: flake8-print - Print statements
  - T10: flake8-debugger - Debugger statements

### Domain-Specific Rules

- [A: flake8-builtins](./flake8-builtins.md) - Builtin shadowing
- [G: flake8-logging-format](./logging.md) - Logging format issues
- [L: flake8-logging](./logging-rules.md) - Logger configuration
- [Q: flake8-quotes](./quotes.md) - Quote style consistency
- [R: flake8-return](./return-values.md) - Return statement patterns
- [Y: flake8-2020](./version-checks.md) - Python version checks
- [P: pandas-vet](./pandas-rules.md) - Pandas best practices

### Framework-Specific

- [AIR: flake8-airflow](./airflow.md) - Airflow DAG checks
- [FAST: fastapi-rules](./fastapi.md) - FastAPI best practices
- [ERA: eradicate](./era.md) - Commented code detection

### Ruff-Specific

- [RUF: Ruff-specific](./ruff-specific.md) - Rules unique to Ruff

## Quick Configuration Examples

### Minimal Configuration (Recommended Starting Point)

```toml
[tool.ruff.lint]
select = ["E", "F"]
```

### Balanced Configuration

```toml
[tool.ruff.lint]
select = ["E", "F", "B", "I", "UP", "S"]
ignore = ["E501"]  # Line too long (formatter handles this)
```

### Comprehensive Configuration

```toml
[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "F",    # Pyflakes
    "UP",   # pyupgrade
    "B",    # flake8-bugbear
    "S",    # flake8-bandit (security)
    "I",    # isort
    "N",    # pep8-naming
    "D",    # pydocstyle
    "C",    # flake8-comprehensions
    "RUF",  # Ruff-specific
]
ignore = [
    "E501",  # Line too long
    "D100",  # Missing module docstring
    "D104",  # Missing package docstring
]
```

## How Ruff Rules Are Used

To enable a rule family in your configuration:

```toml
[tool.ruff.lint]
# Enable all E (pycodestyle) and F (Pyflakes) rules
select = ["E", "F"]

# Ignore specific rules
ignore = ["E501", "F401"]

# Extend existing selection
extend-select = ["B", "S"]
```

## Understanding Rule Documentation

Each rule family documentation follows this structure:

1. **Rule Code and Name** - The full code (e.g., E501) and human-readable name
2. **Source** - Which linter the rule derives from
3. **What It Prevents** - The design principle or error the rule catches
4. **When This Is a Violation** - Conditions that trigger the rule
5. **When This Is NOT a Violation** - Legitimate exceptions and edge cases
6. **Violating Code Example** - Code that fails the rule
7. **Resolved Code Example** - Fixed version of the code
8. **Configuration** - How to tune the rule (if applicable)
9. **Safe to Auto-Fix** - Whether `ruff check --fix` can automatically resolve it

## Common Patterns

### Ignoring Rules

Ignore on a specific line:

```python
x = 1  # noqa: F841
```

Ignore entire file:

```python
# ruff: noqa
```

Ignore specific rule in file:

```python
# ruff: noqa: F401
```

### Rule Selection Strategies

1. **Start small**: Begin with `["E", "F"]` (style and logic errors)
2. **Add incrementally**: Gradually enable additional rule families
3. **Consider conflicts**: Some rules conflict (e.g., `D203` vs `D211` for docstrings)
4. **Document exceptions**: Use `per-file-ignores` for framework-specific directories

## Referenced Documentation

For official Ruff documentation, visit the [Official Ruff Documentation](https://docs.astral.sh/ruff/).

---

**Last Updated**: 2025-11-04 **Ruff Version**: Latest
