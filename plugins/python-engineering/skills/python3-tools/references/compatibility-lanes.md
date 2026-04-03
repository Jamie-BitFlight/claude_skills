# Compatibility Lanes

## Python Version Lifecycle

- 3.10: EOL 2026-10
- 3.11: security-only until 2027-10
- 3.12: security-only until 2028-10
- 3.13: bugfix until 2029-10
- 3.14: bugfix until 2030-10

Prefer versions still in bugfix status for new projects.

## Constrained Environment Detection

A project is "constrained" when any of:

- `requires-python = ">=3.10,<3.11"` (no modern typing features)
- No third-party dependencies allowed by policy
- Airgapped / no network access
- Enterprise-restricted environment

## Lane Selection Rules

1. Check `requires-python` in `pyproject.toml`
2. Check for Pydantic / Hypothesis in dependencies
3. Check for network access capability
4. Choose the strongest valid typing lane

## Tool Restrictions by Lane

| Tool | Standard | Constrained |
|---|---|---|
| uv | Yes | Not available |
| ruff | Yes | Not available |
| ty/mypy | Yes | Not available |
| pytest | Yes | `unittest` fallback |
| Pydantic | Yes | Not available |
| Hypothesis | Yes | Not available |

## Stdlib-Only Patterns

When dependencies are unavailable:

- argparse for CLI
- logging for structured output
- json/tomllib/configparser for config
- dataclasses for structured data
- TypedDict for dict shapes
- Protocol for duck typing
