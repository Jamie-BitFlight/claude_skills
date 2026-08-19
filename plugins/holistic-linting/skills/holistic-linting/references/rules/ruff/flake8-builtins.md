# A: flake8-builtins Rules

**Source**: Official Ruff Documentation **Purpose**: Builtin name shadowing detection

This rule family provides specialized checks for Python code quality and specific use cases.

## Overview

Builtin name shadowing detection

## Quick Start

Enable this rule family by adding it to your Ruff configuration:

```toml
[tool.ruff.lint]
extend-select = ["flake8-builtins"]
```

## Rule Categories

For a complete list of all rules in this family, use the Ruff CLI:

```bash
ruff rule --all | grep "^# flake8-builtins.md"
```

## Official Documentation

For detailed information about each rule, including examples and configuration options, visit: [Official Ruff Rules Documentation](https://docs.astral.sh/ruff/rules/)

## Configuration

Most rules in this family support configuration through options in `pyproject.toml` or `ruff.toml`. Refer to the official documentation for family-specific configuration parameters.

## Integration

This rule family works best when combined with core linting rules:

- E, F, W: Core Python style and logical errors
- B: Common bugs and design problems
- I: Import organization
- N: Naming conventions

---

**Last Updated**: 2025-11-04 **Status**: Reference documentation (see `ruff rule --all` for the current rule list)
