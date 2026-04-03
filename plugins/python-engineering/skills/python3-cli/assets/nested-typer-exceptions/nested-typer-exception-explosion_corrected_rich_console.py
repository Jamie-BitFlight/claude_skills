#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["typer>=0.21.2"]
# ///
"""Demonstration of exception chain explosion anti-pattern corrected using rich console.

This shows how to resolve the issue with nested-typer-exception-explosion.py
by using rich console to print errors consistently with the CLI UX.

Run this to see the problem:
    ./nested-typer-exception-explosion.py broken.json

The 'broken.json' file will be created with invalid JSON content.
"""

# mypy: ignore-errors
from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

try:
    import typer
    from rich.console import Console
except ImportError as e:
    error_message = f"""

    This script needs to be run using a PEP723 compliant executor like uv
    which can handle finding and installing dependencies automatically,
    unlike python or python3 which require you to manually install the dependencies.

    What is inline-metadata? > https://packaging.python.org/en/latest/specifications/inline-script-metadata/#inline-script-metadata
    What is PEP723? > https://peps.python.org/pep-0723/
    How to do this yourself? > https://docs.astral.sh/uv/guides/scripts/

    If you have uv on this system, then this script can be run without prefixing any application.
      example: ./thisscript.py <arguments>

    You can explicitly invoke it with uv:
      example: uv run ./thisscript.py <arguments>

    If you do not have uv installed, then you can install it following the instructions at:
    https://docs.astral.sh/uv/getting-started/installation/

    If that is TL;DR, then you can install it with the following command:
      curl -fsSL https://astral.sh/uv/install.sh | bash

    The longform way to run scripts with inline dependencies is to install the dependencies manually
    and run the script with python or python3.
    example:
        python3 -m venv .venv
        source .venv/bin/activate
        pip install typer
        python3 thisscript.py <arguments>

    ImportException: {e!s}
    """
    raise ImportError(error_message) from None

normal_console = Console()
err_console = Console(stderr=True)
app = typer.Typer()
DEFAULT_CONFIG_FILE = Path("broken.json")


class AppExitRich(typer.Exit):
    """Exception class for application exits using rich console."""

    def __init__(self, code: int | None = None, message: str | None = None, console: Console = normal_console) -> None:
        """Custom exception using console based formatting to keep errors consistent with the CLI UX."""
        self.code = code
        self.message = message
        if message is not None:
            console.print(self.message, crop=False, overflow="ignore")

        super().__init__(code=code if code is not None else 0)


class ConfigError(Exception):
    """Custom exception for errors that will be handled internally."""


# LAYER 1: Low-level file reading
def read_file_contents(file_path: Path) -> str:
    """Read file contents - ANTI-PATTERN: Wraps exceptions unnecessarily.

    Raises:
        FileNotFoundError: If file does not exist
        PermissionError: If file is not readable
    """
    return file_path.read_text(encoding="utf-8")


# LAYER 2: JSON parsing
def parse_json_string(content: str, source: str) -> dict:
    """Parse JSON string - ANTI-PATTERN: Another wrapping layer.

    Bubbles up:
        json.JSONDecodeError: If JSON is not valid
    """
    return json.loads(content)


# LAYER 3: Load JSON from file
def load_json_file(file_path: Path) -> dict:
    """Load JSON from file - ANTI-PATTERN: Yet another wrapping layer.

    Bubbles up:
        FileNotFoundError: If file does not exist
        PermissionError: If file is not readable
        json.JSONDecodeError: If file is not valid JSON
    """
    contents = read_file_contents(file_path)
    try:
        return parse_json_string(contents, str(file_path))
    except json.JSONDecodeError as e:
        raise AppExitRich(
            code=1, message=f"Invalid JSON in {file_path!s} at line {e.lineno}, column {e.colno}: {e.msg}"
        ) from e


# LAYER 4: Validate config structure
def validate_config_structure(data: Any, source: str) -> dict:
    """Validate config structure - ANTI-PATTERN: More wrapping.

    Raises:
        TypeError: If config is not a JSON object
        ValueError: If config is empty
    """
    if not data:
        raise AppExitRich(code=1, message="Config cannot be empty", console=err_console)
    if not isinstance(data, dict):
        raise AppExitRich(code=1, message=f"Config must be a JSON object, got {type(data)}", console=err_console)
    return data


# LAYER 5: Load and validate config (consolidate exception handling)
def load_config(file_path: Path) -> dict:
    """Load and validate config - ANTI-PATTERN: Fifth wrapping layer.

    Raises:
        ConfigError: If config cannot be loaded, invalid structure, or empty
    """
    try:
        data = load_json_file(file_path)
    except (FileNotFoundError, PermissionError) as e:
        raise AppExitRich(code=1, message=f"Failed to load config from {file_path}", console=err_console) from e
    else:
        return validate_config_structure(data, str(file_path))


# LAYER 6: Process config
def process_config(file_path: Path) -> dict:
    """Process configuration - ANTI-PATTERN: Sixth wrapping layer.

    Bubbles up:
        ConfigError: If processing fails (wrapped sixth time)
    """
    config = load_config(file_path)
    normal_console.print("Config successfully loaded")
    return config


# LAYER 7: CLI entry point
@app.command()
def main(config_file: Annotated[Path | None, typer.Argument(help="Path to JSON configuration file")] = None) -> None:
    """Load and process a JSON configuration file.

    This demonstrates the ANTI-PATTERN of exception chain explosion.
    When an error occurs, you'll see a massive exception chain through 7+ layers.

    Example:
        # Create a broken JSON file
        echo "i'm broken" > broken.json

        # Run the script to see exception explosion
        ./nested-typer-exception-explosion.py broken.json
    """
    normal_console.print("Starting script")
    if config_file is None:
        normal_console.print(f"No config file provided, using default: {DEFAULT_CONFIG_FILE!s}")
        config_file = DEFAULT_CONFIG_FILE
    process_config(config_file)


if __name__ == "__main__":
    app()
