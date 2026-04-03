#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["typer>=0.21.2"]
# ///
# ruff: noqa: TRY300, TRY301
# mypy: ignore-errors
"""Demonstration of exception chain explosion anti-pattern.

This script demonstrates how catching and re-wrapping exceptions at every
layer creates massive traceback output (8+ pages) for simple errors.

Based on real AI-generated code patterns that destroy terminal UI.

Run this to see the problem:
    ./nested-typer-exception-explosion.py broken.json

The 'broken.json' file will be created with invalid JSON content.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer()


class ConfigError(Exception):
    """Custom exception for configuration errors."""


# LAYER 1: Low-level file reading
def read_file_contents(file_path: Path) -> str:
    """Read file contents - ANTI-PATTERN: Wraps exceptions unnecessarily.

    Raises:
        ConfigError: If file cannot be read (wrapped)
    """
    try:
        return file_path.read_text(encoding="utf-8")
    except FileNotFoundError as e:
        raise ConfigError(f"File not found: {file_path}") from e
    except PermissionError as e:
        raise ConfigError(f"Permission denied: {file_path}") from e
    except Exception as e:
        # ANTI-PATTERN: Safety net catches the ConfigError we just raised!
        raise ConfigError(f"Failed to read {file_path}: {e}") from e


# LAYER 2: JSON parsing
def parse_json_string(content: str, source: str) -> dict:
    """Parse JSON string - ANTI-PATTERN: Another wrapping layer.

    Raises:
        ConfigError: If JSON cannot be parsed (wrapped again)
    """
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        raise ConfigError(f"Invalid JSON in {source} at line {e.lineno}, column {e.colno}: {e.msg}") from e
    except Exception as e:
        # ANTI-PATTERN: Safety net catches ConfigError we just raised
        raise ConfigError(f"JSON parse error in {source}: {e}") from e


# LAYER 3: Load JSON from file
def load_json_file(file_path: Path) -> dict:
    """Load JSON from file - ANTI-PATTERN: Yet another wrapping layer.

    Raises:
        ConfigError: If file cannot be loaded (wrapped third time)
    """
    try:
        contents = read_file_contents(file_path)
        return parse_json_string(contents, str(file_path))
    except ConfigError as e:
        # ANTI-PATTERN: Wrap the already-wrapped exception AGAIN
        raise ConfigError(f"Failed to load JSON from {file_path}: {e}") from e
    except Exception as e:
        # ANTI-PATTERN: Safety net catches ConfigError we just raised
        raise ConfigError(f"Unexpected error loading {file_path}: {e}") from e


# LAYER 4: Validate config structure
def validate_config_structure(data: object, source: str) -> dict:
    """Validate config structure - ANTI-PATTERN: More wrapping.

    Raises:
        ConfigError: If validation fails (wrapped fourth time)
    """
    try:
        if not isinstance(data, dict):
            raise TypeError("Config must be a JSON object")
        if not data:
            raise ValueError("Config cannot be empty")
        return data
    except (TypeError, ValueError) as e:
        raise ConfigError(f"Invalid config structure in {source}: {e}") from e
    except Exception as e:
        # ANTI-PATTERN: Safety net catches ConfigError we just raised
        raise ConfigError(f"Config validation error in {source}: {e}") from e


# LAYER 5: Load and validate config
def load_config(file_path: Path) -> dict:
    """Load and validate config - ANTI-PATTERN: Fifth wrapping layer.

    Raises:
        ConfigError: If config cannot be loaded (wrapped fifth time)
    """
    try:
        data = load_json_file(file_path)
        return validate_config_structure(data, str(file_path))
    except ConfigError as e:
        # ANTI-PATTERN: Wrap the already-quadruple-wrapped exception
        raise ConfigError(f"Configuration loading failed: {e}") from e
    except Exception as e:
        # ANTI-PATTERN: Safety net catches ConfigError we just raised
        raise ConfigError(f"Unexpected configuration error: {e}") from e


# LAYER 6: Process config
def process_config(file_path: Path) -> None:
    """Process configuration - ANTI-PATTERN: Sixth wrapping layer.

    Raises:
        ConfigError: If processing fails (wrapped sixth time)
    """
    try:
        config = load_config(file_path)
        typer.echo(f"Successfully loaded config: {config}")
    except ConfigError as e:
        # ANTI-PATTERN: Wrap the already-quintuple-wrapped exception
        raise ConfigError(f"Failed to process configuration: {e}") from e
    except Exception as e:
        # ANTI-PATTERN: Safety net catches ConfigError we just raised
        raise ConfigError(f"Processing error: {e}") from e


# LAYER 7: CLI entry point
@app.command()
def main(
    config_file: Annotated[Path, typer.Argument(help="Path to JSON configuration file")] = Path("broken.json"),
) -> None:
    """Load and process a JSON configuration file.

    This demonstrates the ANTI-PATTERN of exception chain explosion.
    When an error occurs, you'll see a massive exception chain through 7+ layers.

    Example:
        # Create a broken JSON file
        echo "i'm broken" > broken.json

        # Run the script to see exception explosion
        ./nested-typer-exception-explosion.py broken.json
    """
    # DON'T catch here - let the exception chain explode through all layers
    # This shows the full horror of the nested wrapping pattern
    process_config(config_file)


@app.command()
def create_test_file() -> None:
    """Create a broken JSON file for testing the exception explosion."""
    broken_file = Path("broken.json")
    broken_file.write_text("i'm broken", encoding="utf-8")
    typer.echo(f"Created {broken_file} with invalid JSON content")


if __name__ == "__main__":
    # Auto-create broken.json if it doesn't exist and is being used
    if len(sys.argv) > 1:
        arg = sys.argv[-1]
        if arg == "broken.json" or (not arg.startswith("-") and Path(arg).name == "broken.json"):
            broken_file = Path("broken.json")
            if not broken_file.exists():
                typer.echo("Creating broken.json for demonstration...")
                broken_file.write_text("i'm broken", encoding="utf-8")
                typer.echo()

    app()
