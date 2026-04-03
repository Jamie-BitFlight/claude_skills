#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "typer>=0.21.2",     # Typer includes Rich - do NOT add Rich separately
# ]
# ///
"""Working demonstration of all Python CLI patterns from the enhanced guide.

This file shows proper Typer + Rich integration with modern Python features.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from itertools import starmap
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, Generic, Protocol, TypeVar

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

# Console setup
console = Console()
error_console = Console(stderr=True, style="bold red")


# Logging setup - must occur early in module lifecycle
def setup_logging() -> Path:
    """Configure file-based logging with RichHandler.

    Creates log directory following pattern:
    ~/.local/logs/cli-demo/<date>/<pid>.json

    Returns:
        Path to the log file

    Raises:
        OSError: If log directory creation fails
    """
    # Build log path with date and PID
    home = Path.home()
    date_str = datetime.now(UTC).strftime("%Y-%m-%d")
    pid = os.getpid()
    log_dir = home / ".local" / "logs" / "cli-demo" / date_str
    log_file = log_dir / f"{pid}.txt"  # Using .txt for simplicity in demo

    # Create directory with parents
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        msg = f"Failed to create log directory {log_dir}: {e}"
        raise OSError(msg) from e

    # Configure logging with RichHandler for terminal + file handler for persistence
    # Set level to DEBUG to capture all log levels in demo (info, debug, warning, error)
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(message)s",
        handlers=[
            RichHandler(console=console, rich_tracebacks=True, tracebacks_show_locals=True),
            logging.FileHandler(log_file, mode="a", encoding="utf-8"),
        ],
    )

    return log_file


# Initialize logging and get log file path
LOG_FILE = setup_logging()
logger = logging.getLogger(__name__)

# Type definitions
T = TypeVar("T")


class OutputFormat(StrEnum):
    """Supported output formats."""

    JSON = "json"
    CSV = "csv"
    YAML = "yaml"
    XML = "xml"


class Processor(Protocol):
    """Protocol for file processors."""

    def process(self, file: Path) -> dict[str, Any]:
        """Process a file and return result dictionary.

        Args:
            file: Path to file to process

        Returns:
            Dictionary containing processing results
        """
        ...


@dataclass
class ProcessingResult(Generic[T]):
    """Generic processing result."""

    success: bool
    data: T | None
    error: str | None
    duration: float


# CLI application setup
app = typer.Typer(
    name="cli-demo", help="Demonstration of modern Python CLI patterns with Typer and Rich", rich_markup_mode="rich"
)

# Subcommand groups
process_app = typer.Typer(help="File processing commands")
app.add_typer(process_app, name="process")


# Validation functions
def validate_input_file(value: Path) -> Path:
    """Validate input file exists and is readable.

    Args:
        value: Path to validate

    Returns:
        Validated Path object

    Raises:
        typer.BadParameter: If file doesn't exist, isn't a file, or is empty
    """
    match True:
        case _ if not value.exists():
            msg = f"File does not exist: {value}"
            raise typer.BadParameter(msg)
        case _ if not value.is_file():
            msg = f"Path is not a file: {value}"
            raise typer.BadParameter(msg)
        case _ if not value.stat().st_size > 0:
            msg = f"File is empty: {value}"
            raise typer.BadParameter(msg)
        case _:
            return value


def handle_cli_error(operation: str, error: Exception) -> None:
    """Handle CLI errors with rich formatting.

    Args:
        operation: Name of the operation that failed
        error: The exception that was raised

    Raises:
        typer.Exit: With appropriate exit code based on error type
    """
    error_panel = Panel(
        f"[bold red]Error in {operation}:[/bold red]\n{error!s}",
        title=":cross_mark: Operation Failed",
        border_style="red",
    )
    error_console.print(error_panel)

    match error:
        case FileNotFoundError() | PermissionError():
            raise typer.Exit(2) from error
        case ValueError():
            raise typer.Exit(3) from error
        case _:
            raise typer.Exit(1) from error


# Rich display functions
def display_results(results: list[dict[str, Any]]) -> None:
    """Display results in a formatted table.

    Args:
        results: List of processing results to display
    """
    table = Table(title="Processing Results")
    table.add_column("File", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Size", justify="right", style="yellow")

    for result in results:
        status = "[green]:white_check_mark:[/green]" if result["success"] else "[red]:cross_mark:[/red]"
        table.add_row(result["filename"], status, str(result["size"]))

    console.print(table)


def show_progress_demo() -> None:
    """Show progress for demonstration.

    Demonstrates Rich progress bars with spinner and text updates.
    """
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        task = progress.add_task("Processing files...", total=None)
        time.sleep(2)  # Simulate work
        progress.update(task, description="[green]Complete!")


# Mock processors for demonstration
class GenericProcessor:
    """Generic file processor for demonstration.

    This class demonstrates the DRY principle by consolidating duplicate
    processor implementations into a single configurable class.

    Args:
        processor_type: Type identifier for this processor (json, csv, xml)
        config: Configuration dictionary for processor
    """

    def __init__(self, processor_type: str, config: dict[str, Any]) -> None:
        """Initialize generic processor with type and configuration.

        Args:
            processor_type: Type identifier for this processor
            config: Configuration dictionary
        """
        self.processor_type = processor_type
        self.config = config

    def process(self, file: Path) -> dict[str, Any]:
        """Process a file.

        Args:
            file: Path to file to process

        Returns:
            Processing result dictionary with type, file path, and size
        """
        return {"type": self.processor_type, "file": str(file), "size": file.stat().st_size}


def create_processor(processor_type: str, config: dict[str, Any] | None = None) -> Processor:
    """Factory function for processors.

    Args:
        processor_type: Type of processor to create (json, csv, xml)
        config: Optional configuration dictionary

    Returns:
        Processor instance for the specified type

    Raises:
        ValueError: If processor_type is not supported
    """
    valid_types = {"json", "csv", "xml"}

    match processor_type:
        case _ if processor_type in valid_types:
            return GenericProcessor(processor_type, config or {})
        case _:
            msg = f"Unknown processor type: {processor_type}. Valid types: {valid_types}"
            raise ValueError(msg)


# Async processing functions
async def process_files_async(
    files: list[tuple[Path, int]], max_workers: int = 4
) -> AsyncIterator[ProcessingResult[dict[str, Any]]]:
    """Process files asynchronously.

    Args:
        files: List of tuples containing (file_path, file_size)
        max_workers: Maximum number of concurrent workers

    Yields:
        ProcessingResult for each completed file
    """
    semaphore = asyncio.Semaphore(max_workers)

    async def process_single(file: Path, size: int) -> ProcessingResult[dict[str, Any]]:
        """Process a single file.

        Args:
            file: Path to file to process
            size: Size of the file in bytes

        Returns:
            ProcessingResult with success/failure information
        """
        async with semaphore:
            try:
                # Simulate async processing
                await asyncio.sleep(0.1)
                data = {"file": str(file), "size": size}
                return ProcessingResult(success=True, data=data, error=None, duration=0.1)
            except OSError as e:
                return ProcessingResult(success=False, data=None, error=str(e), duration=0.0)

    tasks = list(starmap(process_single, files))

    for coro in asyncio.as_completed(tasks):
        yield await coro


# CLI Commands
@app.command()
def hello(
    name: Annotated[str, typer.Option("--name", "-n", help="Your name")] = "World",
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Verbose output")] = False,
) -> None:
    """Say hello with style.

    Demonstrates logger vs console separation:
    - logger.debug/info: Operational/diagnostic messages
    - console.print: User-facing UI output
    """
    logger.info("Hello command invoked", extra={"user_name": name, "verbose_mode": verbose})

    if verbose:
        logger.debug("Verbose mode enabled")
        console.print(f"[bold blue]Greeting:[/bold blue] Preparing to say hello to {name}")

    console.print(f"[bold green]Hello, {name}![/bold green] :wave:")
    logger.info("Hello command completed successfully")


@app.command()
def demo_markup() -> None:
    """Demonstrate Rich markup patterns."""
    console.print("[bold blue]Rich Markup Demonstration[/bold blue]")
    console.print()

    # Status messages
    console.print("[bold green]:white_check_mark: Operation completed successfully[/]")
    console.print("[bold red]:cross_mark: Operation failed[/]")
    console.print()

    # Progress indication
    console.print("[bold yellow]Processing... :hourglass:[/]")
    console.print()

    # Hyperlinks
    console.print("Visit [link=https://rich.readthedocs.io]Rich documentation[/link]")
    console.print()

    # Code highlighting
    command = "python -m rich.emoji"
    console.print(f"[bold cyan]Command:[/bold cyan] [code]{command}[/code]")


@app.command()
def demo_table() -> None:
    """Demonstrate Rich table formatting."""
    sample_results = [
        {"filename": "data1.json", "success": True, "size": 1024},
        {"filename": "data2.csv", "success": True, "size": 2048},
        {"filename": "data3.xml", "success": False, "size": 0},
    ]

    display_results(sample_results)


@app.command()
def demo_progress() -> None:
    """Demonstrate Rich progress display."""
    show_progress_demo()


@process_app.command("files")
def process_files_command(
    directory: Annotated[Path, typer.Option("--dir", "-d", help="Directory to process")] = Path(),
    pattern: Annotated[str, typer.Option("--pattern", "-p", help="File pattern to match")] = "*.py",
    format_type: Annotated[OutputFormat, typer.Option("--format", "-f", help="Output format")] = OutputFormat.JSON,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Verbose output")] = False,
) -> None:
    """Process files matching pattern.

    Demonstrates logging for operational events:
    - File discovery and processing steps
    - Error conditions with context
    - Success/failure tracking
    """
    logger.info(
        "Starting file processing", extra={"directory": str(directory), "pattern": pattern, "format": format_type.value}
    )

    try:
        files = list(directory.glob(pattern))
        logger.info(f"Found {len(files)} files matching pattern", extra={"count": len(files)})

        if verbose:
            console.print(f"[bold blue]Found {len(files)} files matching pattern:[/bold blue] {pattern}")

        processor = create_processor(format_type.value)
        results = []

        for file in files[:3]:  # Limit for demo
            try:
                logger.debug(f"Processing file: {file.name}")
                result = processor.process(file)
                results.append({"filename": file.name, "success": True, "size": result["size"]})
                console.print(f"[bold green]:white_check_mark:[/bold green] Processed {file.name}")
            except OSError as e:
                logger.exception(f"Failed to process {file.name}", extra={"file": str(file)})
                results.append({"filename": file.name, "success": False, "size": 0})
                console.print(f"[bold red]:cross_mark:[/bold red] Failed {file.name}: {e}")

        if results:
            console.print()
            display_results(results)

        logger.info("File processing completed", extra={"total_processed": len(results)})

    except OSError as e:
        logger.exception("File processing failed")
        handle_cli_error("file processing", e)


@process_app.command("async")
def async_process_command(
    directory: Annotated[Path, typer.Option("--dir", "-d", help="Directory to process")] = Path(),
    workers: Annotated[int, typer.Option("--workers", "-w", help="Max workers")] = 4,
) -> None:
    """Process files asynchronously.

    Demonstrates logging in async contexts with concurrent operations.
    """
    logger.info("Starting async file processing", extra={"directory": str(directory), "workers": workers})

    if not (files := list(directory.glob("*.py"))[:5]):  # Limit for demo
        logger.warning("No Python files found in directory", extra={"directory": str(directory)})
        console.print("[yellow]No Python files found in directory[/yellow]")
        return

    # Gather file stats before async processing (avoids blocking I/O in async context)
    files_with_stats = [(f, f.stat().st_size) for f in files]

    logger.info(f"Processing {len(files_with_stats)} files asynchronously", extra={"file_count": len(files_with_stats)})
    console.print(f"[bold blue]Processing {len(files_with_stats)} files with {workers} workers...[/bold blue]")

    with Progress(console=console) as progress:
        task = progress.add_task("Processing files...", total=len(files_with_stats))

        async def run_processing() -> None:
            success_count = 0
            error_count = 0

            async for result in process_files_async(files_with_stats, workers):
                if result.success and result.data:
                    success_count += 1
                    logger.debug(f"Async processing succeeded: {result.data['file']}")
                    console.print(f"[green]:white_check_mark:[/green] {result.data['file']}")
                else:
                    error_count += 1
                    logger.error(f"Async processing failed: {result.error}")
                    console.print(f"[red]:cross_mark:[/red] Error: {result.error}")
                progress.advance(task)

            logger.info("Async processing completed", extra={"success": success_count, "errors": error_count})

        asyncio.run(run_processing())


@app.command()
def advanced_example(
    *,
    # Input/Output Options
    input_file: Annotated[
        Path | None, typer.Option("--input", "-i", help="Input file path", rich_help_panel="Input/Output Options")
    ] = None,
    output_dir: Annotated[
        Path, typer.Option("--output", "-o", help="Output directory", rich_help_panel="Input/Output Options")
    ] = Path(),
    # Processing Options
    workers: Annotated[
        int, typer.Option("--workers", "-w", help="Number of worker threads", rich_help_panel="Processing Options")
    ] = 4,
    timeout: Annotated[
        int, typer.Option("--timeout", "-t", help="Operation timeout in seconds", rich_help_panel="Processing Options")
    ] = 300,
    # Debug Options
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose output", rich_help_panel="Debug Options")
    ] = False,
    debug: Annotated[bool, typer.Option("--debug", help="Enable debug mode", rich_help_panel="Debug Options")] = False,
) -> None:
    """Advanced command demonstrating help panels and complex options."""
    config_panel = Panel(
        f"Input: {input_file or 'None'}\n"
        f"Output: {output_dir}\n"
        f"Workers: {workers}\n"
        f"Timeout: {timeout}s\n"
        f"Verbose: {verbose}\n"
        f"Debug: {debug}",
        title="Configuration",
        border_style="blue",
    )
    console.print(config_panel)


def main() -> None:
    """Main entry point with startup logging."""
    # Display log file location on startup
    console.print(f"[dim]Log file: {LOG_FILE}[/dim]")
    logger.info("CLI application started", extra={"pid": os.getpid()})

    app()


if __name__ == "__main__":
    main()
