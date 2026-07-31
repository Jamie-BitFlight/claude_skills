---
name: python3-cli
description: Use when building CLI applications with Typer and Rich — creating commands with Annotated parameter syntax, defining arguments and options, composing subcommands, async concurrent CLI tasks with semaphores, testing with CliRunner, PEP 723 shebang scripts, progress bars, Rich terminal output, or non-TTY display width handling.
user-invocable: false
---

# CLI Development (Typer + Rich)

Consult `python3-core` for standing defaults. Load `python3-testing` for test patterns.

## Standards

- `Annotated[Type, typer.Option(...)]` syntax for all CLI params
- `rich_help_panel` to group options
- Rich emoji tokens (`:white_check_mark:`) not Unicode literals
- Architecture: CLI (Typer) → Business Logic → Services → Display (Rich)
- `uv run <script>` over `python3 <script>`
- Factory pattern for dependency injection

## App Structure

```python
import typer
from rich.console import Console

app = typer.Typer()
console = Console()


@app.command()
def process(
    input_file: Annotated[Path, typer.Argument(help="Input file")],
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
) -> None:
    """Process input file."""
    ...
```

## Rich Width Handling

```python
from rich.console import Console
from rich.table import Table
from rich.measure import Measurement


def get_table_width(table: Table) -> int:
    temp = Console(width=9999)
    m = Measurement.get(temp, temp.options, table)
    return int(m.maximum)
```

## Testing

```python
from typer.testing import CliRunner

runner = CliRunner()


def test_app_runs() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
```

## Async Patterns

Use semaphores for I/O-bound CLI tasks:

```python
import asyncio
import typer
from typing import Annotated


@app.command()
def fetch(urls: Annotated[list[str], typer.Argument()], max_concurrent: Annotated[int, typer.Option()] = 10) -> None:
    """Fetch multiple URLs concurrently."""
    results = asyncio.run(_fetch_all(urls, max_concurrent))
    for result in results:
        console.print(result)


async def _fetch_all(urls: list[str], limit: int) -> list[str]:
    sem = asyncio.Semaphore(limit)
    async with httpx.AsyncClient() as client:
        tasks = [_fetch_one(client, u, sem) for u in urls]
        return await asyncio.gather(*tasks)
```

## PEP 723 Shebang

```python
#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["typer>=0.21", "rich>=13.0"]
# ///
```

## References

- `references/typer-app-and-commands.md`, `references/typer-parameters.md`, `references/typer-parameter-types.md`, `references/typer-advanced-patterns.md`, `references/typer-subcommands.md`, `references/typer-testing.md` — Typer commands, arguments, parameters, subcommands
- `references/rich-console-and-markup.md`, `references/rich-renderables.md`, `references/rich-text-and-syntax.md`, `references/rich-advanced-patterns.md`, `references/rich-progress-and-live.md`, `references/rich-logging-and-tracebacks.md` — Rich tables, panels, progress, live displays
- `references/typer-rich-non-tty-patterns.md`, `references/typer-rich-tables.md`, `references/typer-rich-exception-handling.md`, `references/typer-rich-testing-patterns.md` — Typer+Rich integration, non-TTY, width, testing

## Related Skills

Load `python-engineering:textual` when the task involves Textual TUI widgets, screen stack, CSS styling, reactive attributes, Pilot testing, or background workers.

Load `python-engineering:typer` when the task is focused on Typer commands, parameter configuration, subcommand composition, or Typer-specific documentation.

Load `python-engineering:typer-and-rich` when the task involves Rich table rendering in non-TTY contexts, Typer/Rich integration pitfalls, or correctness review of CLI output handling.

## Assets

- `assets/python-cli-demo.py` — complete working example
- `assets/typer_examples/index.md` — working scripts demonstrating non-TTY display solutions (Panel/Table width, wrapping, cropping)
- `assets/nested-typer-exceptions/` — runnable demos of Typer nested exception anti-patterns and fixes
