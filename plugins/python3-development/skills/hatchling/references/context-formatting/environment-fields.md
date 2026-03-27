---
category: Context Formatting Fields
topics: [environment-fields, matrix-variables, verbosity, hatch-environments, configuration-interpolation]
related: [README.md, global-fields.md, optional-dependencies.md, configuration-interpolation.md]
---

# Environment-Specific Context Formatting Fields

Reference documentation for context formatting fields specific to Hatch environments. Use this to help users understand environment-specific context fields beyond globally available fields.

## Overview

When assisting users with Hatch environment configuration, explain that environment-specific fields allow scripts, dependencies, and environment variables to reference:

- The environment's own name and type
- Matrix variable values
- Execution verbosity levels
- Dynamic conditional values

## Environment Name and Type Fields

### env_name

- **What it represents**: The name of the current environment
- **Type**: String
- **Modifiers**: None
- **When to use**: When users need scripts to adapt behavior based on which environment they're running in

**Show users these examples:**

```toml
[tool.hatch.envs.test.scripts]
show-env = "echo Running in {env_name}"
```

Output when run in the `test` environment:

```console
Running in test
```

```toml
[tool.hatch.envs.test.scripts]
log = "echo {env_name}: Starting tests >> {root}/logs/{env_name}.log"
```

This creates environment-specific log files: `logs/test.log`, `logs/lint.log`, etc.

### env_type

- **What it represents**: The type of the current environment
- **Type**: String
- **Modifiers**: None
- **Value**: Matches the environment definition type (e.g., "test", "static-analysis", custom defined)
- **When to use**: When users need conditional behavior based on environment category

**Show users these examples:**

```toml
[tool.hatch.envs.test.scripts]
check-type = "echo Environment type: {env_type}"
```

```toml
[tool.hatch.envs.lint.scripts]
setup = "echo Setting up {env_type} environment"
```

## Matrix Variables

### matrix

- **What it does**: Accesses a specific matrix variable value
- **Type**: String (variable identifier after the colon)
- **Modifiers**: Value placeholder followed by default value
- **Syntax**: `{matrix:VARIABLE_NAME}` or `{matrix:VARIABLE_NAME:DEFAULT_VALUE}`
- **Important note**: Provide defaults if the environment is not part of a matrix or was not generated with that variable

**Show users these examples:**

Simple matrix variable reference:

```toml
[[tool.hatch.envs.test.matrix]]
python = ["3.8", "3.9", "3.10", "3.11"]

[tool.hatch.envs.test.scripts]
show-version = "python --version | grep {matrix:python}"
```

When running in the Python 3.10 variant, `{matrix:python}` expands to `3.10`.

With default value (for non-matrix environments):

```toml
[[tool.hatch.envs.test.matrix]]
version = ["1.0", "2.0"]
feature = ["fast", "slow"]

[tool.hatch.envs.test.scripts]
test = "pytest tests/ --version={matrix:version:latest} --feature={matrix:feature:default}"
```

Multiple matrix variables in one command:

```toml
[[tool.hatch.envs.test.matrix]]
python = ["3.9", "3.10"]
django = ["3.2", "4.0"]

[tool.hatch.envs.test.scripts]
test = "pytest -k django_{matrix:django:default} --py{matrix:python:39}"
```

### Matrix Modifiers

#### Matrix Name Format

Control how matrix-generated environment names are formatted using the `matrix-name-format` option:

```toml
[tool.hatch.envs.test]
matrix-name-format = "{variable}_{value}"

[[tool.hatch.envs.test.matrix]]
python = ["3.9", "3.10"]
```

This creates environment names like `test.python_3.9`, `test.python_3.10`.

Placeholders:

- `{variable}` — The matrix variable name (e.g., "python", "version")
- `{value}` — The matrix variable value (e.g., "3.9", "1.0")

## Verbosity Fields

### verbosity

- **What it represents**: The integer verbosity level passed during command execution
- **Type**: Integer
- **Modifiers**: `flag` (optional), integer adjustment (optional)
- **Default**: Usually 0 (normal verbosity)

**Show users these examples:**

Raw verbosity level:

```toml
[tool.hatch.envs.test.scripts]
show-verbosity = "echo Verbosity: {verbosity}"
```

When run with `hatch run test -v`, outputs `Verbosity: 1`.

#### flag Modifier

Converts integer verbosity to CLI-style flags:

```toml
[tool.hatch.envs.test.scripts]
test = "pytest {verbosity:flag}"
```

Conversion rules:

- `-2` → `-qq`
- `-1` → `-q`
- `0` → (no flag)
- `1` → `-v`
- `2` → `-vv`
- `3` → `-vvv`

#### Verbosity Adjustment

Add or subtract from the verbosity level with an integer modifier:

```toml
[tool.hatch.envs.test.scripts]
test = "pytest {verbosity:flag:-1}"
```

This makes the command one level quieter than the user's requested verbosity. If the user passes `-v` (verbosity 1), the effective flag becomes `-q` (verbosity 0).

**Common Pattern:**

```toml
[tool.hatch.envs.test.scripts]
test = "pytest {args} {verbosity:flag}"
```

This allows pytest to receive the verbosity flags based on the user's input to the Hatch command.

## Optional Fields and Fallbacks

### Field Availability

- `env_name` and `env_type` — Always available
- `matrix:VARIABLE_NAME` — Only available if the environment was generated with that matrix variable
- `verbosity` — Only available in script execution context

### Handling Missing Matrix Variables

Always provide defaults for matrix variables you reference, unless the environment is guaranteed to have that variable:

```toml
# DON'T do this (fails if matrix variable doesn't exist):
[tool.hatch.envs.test.scripts]
test = "pytest --version={matrix:python}"

# DO provide a default:
[tool.hatch.envs.test.scripts]
test = "pytest --version={matrix:python:default}"
```

## Configuration Sections with Environment Fields

These configuration sections support environment-specific context fields:

- `[tool.hatch.envs.<ENV_NAME>]` — Environment options
- `[tool.hatch.envs.<ENV_NAME>.scripts]` — Script definitions
- `[tool.hatch.envs.<ENV_NAME>.env-vars]` — Environment variable values
- `[tool.hatch.envs.<ENV_NAME>.dependencies]` — Environment dependencies (with global fields, not env fields)

## Practical Patterns

### Environment-Aware Logging

Create log files specific to the current environment:

```toml
[tool.hatch.envs.test]
dependencies = ["pytest"]

[tool.hatch.envs.test.env-vars]
LOG_FILE = "{root}/logs/{env_name}.log"

[tool.hatch.envs.test.scripts]
test = "pytest --log-file={LOG_FILE} {args}"
```

### Matrix-Based Configuration

Run tests against multiple dependency versions:

```toml
[[tool.hatch.envs.test.matrix]]
django = ["3.2", "4.0", "4.1"]

[tool.hatch.envs.test]
dependencies = [
    "django~={matrix:django}",
]

[tool.hatch.envs.test.scripts]
test = "pytest tests/ -v"
```

### Conditional Verbosity

Scripts that automatically adapt to user verbosity:

```toml
[tool.hatch.envs.test.scripts]
test = "pytest tests/ {verbosity:flag}"
build = "python build.py {verbosity:flag:-1}"
```

The `build` script runs at one level quieter than the user's request.

### Environment-Type Specific Setup

Differentiate behavior by environment:

```toml
[tool.hatch.envs.test.scripts]
setup = "echo Setting up test environment"

[tool.hatch.envs.lint.scripts]
setup = "echo Setting up lint environment"

# Or dynamic:
[tool.hatch.envs.test.scripts]
info = "echo Type: {env_type}, Name: {env_name}"
```

### Multi-Version Testing

Test against multiple Python versions in a single matrix:

```toml
[[tool.hatch.envs.test.matrix]]
python = ["3.8", "3.9", "3.10"]
requests = ["2.27", "2.28"]

[tool.hatch.envs.test.scripts]
test = "pytest --requests={matrix:requests:latest}"
report = "echo Testing Python {matrix:python} with requests {matrix:requests:2.27}"
```

## Combining with Global Fields

Environment-specific fields work seamlessly with global fields in the same placeholder:

```toml
[tool.hatch.envs.test.scripts]
test = "pytest {root}/tests --log={root}/logs/{env_name}-{matrix:python:3.9}.log"
```

This creates logs with both the environment name and matrix variable value.

## Related Topics

- `global-fields.md` — root, home, env fields available everywhere
- `optional-dependencies.md` — Context formatting in optional dependency groups
- `dynamic-configuration.md` — Programmatic metadata and dynamic field resolution
- `configuration-interpolation.md` — Advanced field nesting and patterns
