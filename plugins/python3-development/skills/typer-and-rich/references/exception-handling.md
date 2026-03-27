# Exception Handling in Python CLI Applications with Typer

## The Problem: Exception Chain Explosion

AI-generated code commonly creates a catastrophic anti-pattern where every function catches and re-wraps exceptions, creating massive exception chains (200+ lines of output) for simple errors like "file not found".

**Example of the problem:**

**Full example:** `../assets/nested-typer-exceptions/nested-typer-exception-explosion.py`

```python
# From: nested-typer-exception-explosion.py (simplified - see full file for all 7 layers)
# Layer 1
def read_file(path):
    try:
        return path.read_text()
    except FileNotFoundError as e:
        raise ConfigError(f"File not found: {path}") from e
    except Exception as e:
        raise ConfigError(f"Failed to read: {e}") from e

# Layer 2
def load_config(path):
    try:
        contents = read_file(path)
        return json.loads(contents)
    except ConfigError as e:
        raise ConfigError(f"Config load failed: {e}") from e
    except Exception as e:
        raise ConfigError(f"Unexpected error: {e}") from e

# Layer 3... Layer 4... Layer 5... Layer 6... Layer 7...
# Each layer wraps the exception again
```

**Result:** Single `FileNotFoundError` becomes a 6-layer exception chain with 220 lines of output.

## The Correct Solution: Typer's Exit Pattern

Based on Typer's official documentation and best practices:

### Pattern 1: Custom Exit Exception with typer.echo

**Full example:** `../assets/nested-typer-exceptions/nested-typer-exception-explosion_corrected_typer_echo.py`

Create a custom exception class that handles user-friendly output:

```python
# From: nested-typer-exception-explosion_corrected_typer_echo.py
import typer

class AppExit(typer.Exit):
    """Custom exception for graceful application exits."""

    def __init__(self, code: int | None = None, message: str | None = None):
        self.code = code
        self.message = message
        if message is not None:
            if code is None or code == 0:
                typer.echo(self.message)
            else:
                typer.echo(self.message, err=True)
        super().__init__(code=code)
```

**Usage in helper functions:**

```python
# From: nested-typer-exception-explosion_corrected_typer_echo.py
def load_json_file(file_path: Path) -> dict:
    """Load JSON from file.

    Raises:
        AppExit: If file cannot be loaded or parsed
    """
    contents = file_path.read_text(encoding="utf-8")  # Let FileNotFoundError bubble

    try:
        return json.loads(contents)
    except json.JSONDecodeError as e:
        # Only catch where we can add meaningful context
        raise AppExit(
            code=1,
            message=f"Invalid JSON in {file_path} at line {e.lineno}, column {e.colno}: {e.msg}"
        ) from e
```

**Key principles:**

- Helper functions let exceptions bubble naturally
- Only catch at points where you have enough context for a good error message
- Immediately raise `AppExit` - don't re-wrap multiple times
- Use `from e` to preserve the chain for debugging

### Pattern 2: Custom Exit Exception with Rich Console

**Full example:** `../assets/nested-typer-exceptions/nested-typer-exception-explosion_corrected_rich_console.py`

For applications using Rich for output:

```python
# From: nested-typer-exception-explosion_corrected_rich_console.py
from rich.console import Console
import typer

normal_console = Console()
err_console = Console(stderr=True)

class AppExitRich(typer.Exit):
    """Custom exception using Rich console for consistent formatting."""

    def __init__(
        self,
        code: int | None = None,
        message: str | None = None,
        console: Console = normal_console
    ):
        self.code = code
        self.message = message
        if message is not None:
            console.print(self.message)
        super().__init__(code=code)
```

**Usage:**

```python
# From: nested-typer-exception-explosion_corrected_rich_console.py
def validate_config(data: dict) -> dict:
    """Validate config structure.

    Raises:
        AppExitRich: If validation fails
    """
    if not data:
        raise AppExitRich(code=1, message="Config cannot be empty", console=err_console)
    if not isinstance(data, dict):
        raise AppExitRich(
            code=1,
            message=f"Config must be a JSON object, got {type(data)}",
            console=err_console
        )
    return data
```

## Complete Example: Correct Pattern

**Full example:** `../assets/nested-typer-exceptions/nested-typer-exception-explosion_corrected_typer_echo.py`

```python
# From: nested-typer-exception-explosion_corrected_typer_echo.py
#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["typer>=0.21.2"]
# ///
import json
from pathlib import Path
from typing import Annotated
import typer

app = typer.Typer()

class AppExit(typer.Exit):
    """Custom exception for graceful exits with user-friendly messages."""

    def __init__(self, code: int | None = None, message: str | None = None):
        if message is not None:
            if code is None or code == 0:
                typer.echo(message)
            else:
                typer.echo(message, err=True)
        super().__init__(code=code)

# Helper functions - let exceptions bubble naturally
def read_file_contents(file_path: Path) -> str:
    """Read file contents.

    Raises:
        FileNotFoundError: If file doesn't exist
        PermissionError: If file isn't readable
    """
    return file_path.read_text(encoding="utf-8")

def parse_json_string(content: str) -> dict:
    """Parse JSON string.

    Raises:
        json.JSONDecodeError: If JSON is invalid
    """
    return json.loads(content)

# Only catch where we add meaningful context
def load_json_file(file_path: Path) -> dict:
    """Load and parse JSON file.

    Raises:
        AppExit: If file cannot be loaded or parsed
    """
    contents = read_file_contents(file_path)
    try:
        return parse_json_string(contents)
    except json.JSONDecodeError as e:
        raise AppExit(
            code=1,
            message=f"Invalid JSON in {file_path} at line {e.lineno}, column {e.colno}: {e.msg}"
        ) from e

def validate_config(data: dict, source: str) -> dict:
    """Validate config structure.

    Raises:
        AppExit: If validation fails
    """
    if not data:
        raise AppExit(code=1, message="Config cannot be empty")
    if not isinstance(data, dict):
        raise AppExit(code=1, message=f"Config must be a JSON object, got {type(data)}")
    return data

def load_config(file_path: Path) -> dict:
    """Load and validate configuration.

    Raises:
        AppExit: If config cannot be loaded or is invalid
    """
    try:
        data = load_json_file(file_path)
    except (FileNotFoundError, PermissionError):
        raise AppExit(code=1, message=f"Failed to load config from {file_path}")
    return validate_config(data, str(file_path))

@app.command()
def main(config_file: Annotated[Path, typer.Argument()]) -> None:
    """Load and process configuration file."""
    config = load_config(config_file)
    typer.echo(f"Config loaded successfully: {config}")

if __name__ == "__main__":
    app()
```

## Output Comparison

### Anti-Pattern Output (220 lines)

<eg>
╭───────────────────── Traceback (most recent call last) ──────────────────────╮
│ ... json.loads() ...                                                         │
│ ... 40 lines of traceback ...                                               │
╰──────────────────────────────────────────────────────────────────────────────╯
JSONDecodeError: Expecting value: line 1 column 1 (char 0)

The above exception was the direct cause of the following exception:

╭───────────────────── Traceback (most recent call last) ──────────────────────╮
│ ... parse_json_string() ...                                                  │
│ ... 40 lines of traceback ...                                               │
╰──────────────────────────────────────────────────────────────────────────────╯
ConfigError: Invalid JSON in broken.json at line 1, column 1: Expecting value

The above exception was the direct cause of the following exception:

[... 4 more layers of this ...]
</eg>

### Correct Pattern Output (1 line)

<eg>
Invalid JSON in broken.json at line 1, column 1: Expecting value
</eg>

## Rules for Exception Handling in Typer CLIs

### ✅ DO

1. **Let exceptions propagate in helper functions** - Most functions should not have try/except
2. **Catch only where you add meaningful context** - JSON parsing, validation, etc.
3. **Immediately raise AppExit** - Don't re-wrap multiple times
4. **Use custom exception classes** - Inherit from `typer.Exit` and handle output in `__init__`
5. **Document what exceptions bubble up** - Use docstring "Raises:" sections
6. **Use `from e` when wrapping** - Preserves exception chain for debugging

### ❌ DON'T

1. **NEVER catch and re-wrap at every layer** - This creates exception chain explosion
2. **NEVER use `except Exception as e:` as a safety net** - Too broad, catches things you can't handle
3. **NEVER check `isinstance` to avoid double-wrapping** - This is a symptom you're doing it wrong
4. **NEVER convert exceptions to return values** - Use exceptions, not `{"success": False, "error": "..."}` patterns
5. **NEVER catch exceptions you can't handle** - Let them propagate

## When to Catch Exceptions

**Catch when:**

- You can add meaningful context (filename, line number, etc.)
- You're at a validation boundary and can provide specific feedback
- You need to convert a technical error to user-friendly message

**Don't catch when:**

- You're just going to re-raise it
- You can't add any useful information
- You're in a helper function that just transforms data

## Fail Fast by Default

**What you DON'T want:**

- ❌ Nested try/except that re-raise with redundant messages
- ❌ Bare exception catching (`except Exception:`)
- ❌ Graceful degradation without requirements
- ❌ Failover/fallback logic without explicit need
- ❌ "Defensive" catch-all handlers that mask problems

**What IS fine:**

- ✅ Let exceptions propagate naturally
- ✅ Add try/except only where recovery is actually needed
- ✅ Validation at boundaries (user input, external APIs)
- ✅ Clear, specific exception types

## Environment Variables (Typer 0.20.1+)

- **TYPER_STANDARD_TRACEBACK**: Set to enable standard traceback format instead of Rich (useful for CI/log parsing).
- **TYPER_USE_RICH** (0.23.1+): Set to disable Rich completely when needed.

## Reference: Typer Documentation

Official Typer guidance on exits and exceptions:

- [Terminating](https://typer.tiangolo.com/tutorial/terminating/)
- [Exceptions](https://typer.tiangolo.com/tutorial/exceptions/)
- [Printing](https://typer.tiangolo.com/tutorial/printing/)

## Demonstration Scripts

See `../assets/nested-typer-exceptions/` for complete working examples.

**Quick start:** See `../assets/nested-typer-exceptions/README.md` for script overview and running instructions.

### `../assets/nested-typer-exceptions/nested-typer-exception-explosion.py` - The Anti-Pattern

**What you'll find:**

- Complete executable script demonstrating 7 layers of exception wrapping
- Every function catches exceptions and re-wraps with `from e`
- Creates ConfigError custom exception at each layer
- No isinstance checks - pure exception chain explosion

**What happens when you run it:**

- Single JSON parsing error generates ~220 lines of output
- 7 separate Rich-formatted traceback blocks
- "The above exception was the direct cause of the following exception" repeated 6 times
- Obscures the actual error (invalid JSON) in pages of traceback

**Run it:** `./nested-typer-exception-explosion.py broken.json`

### `../assets/nested-typer-exceptions/nested-typer-exception-explosion_naive_workaround.py` - The isinstance Band-Aid

**What you'll find:**

- Same 7-layer structure as the explosion example
- Each `except Exception as e:` block has `if isinstance(e, ConfigError): raise` checks
- Shows how AI attempts to avoid double-wrapping by checking exception type
- Treats the symptom (double-wrapping) instead of the cause (catching everywhere)

**What happens when you run it:**

- Still shows nested tracebacks but slightly reduced output (~80 lines)
- Demonstrates why isinstance checks appear in AI-generated code
- Shows this is a workaround, not a solution

**Run it:** `./nested-typer-exception-explosion_naive_workaround.py broken.json`

### `../assets/nested-typer-exceptions/nested-typer-exception-explosion_corrected_typer_echo.py` - Correct Pattern with typer.echo

**What you'll find:**

- Custom `AppExit` class extending `typer.Exit` that calls `typer.echo()` in `__init__`
- Helper functions that let exceptions bubble naturally (no try/except)
- Only catches at specific points where meaningful context can be added
- Immediately raises `AppExit` - no re-wrapping through multiple layers
- Complete executable example with PEP 723 metadata

**What happens when you run it:**

- Clean 1-line error message: `Invalid JSON in broken.json at line 1, column 1: Expecting value`
- No traceback explosion
- User-friendly output using typer.echo for stderr

**Run it:** `./nested-typer-exception-explosion_corrected_typer_echo.py broken.json`

### `../assets/nested-typer-exceptions/nested-typer-exception-explosion_corrected_rich_console.py` - Correct Pattern with Rich Console

**What you'll find:**

- Custom `AppExitRich` class extending `typer.Exit` that calls `console.print()` in `__init__`
- Same exception bubbling principles as typer.echo version
- Uses Rich Console for consistent formatting with rest of CLI
- Allows passing different console instances (normal_console vs err_console)

**What happens when you run it:**

- Same clean 1-line output as typer.echo version
- Uses Rich console for output instead of typer.echo
- Demonstrates pattern for apps already using Rich for terminal output

**Run it:** `./nested-typer-exception-explosion_corrected_rich_console.py broken.json`

### Running the Examples

All scripts use PEP 723 inline script metadata and can be run directly:

```bash
# Run any script directly (uv handles dependencies automatically)
./script-name.py broken.json

# Or explicitly with uv
uv run script-name.py broken.json
```

The scripts will create `broken.json` if it doesn't exist.
