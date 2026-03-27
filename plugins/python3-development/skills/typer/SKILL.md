---
name: typer
description: Use when building CLI applications with Typer — creating commands, defining arguments and options, composing subcommands, testing with CliRunner, or using advanced features like callbacks and autocompletion. Covers app creation, parameter types, subcommand composition, testing patterns, and output utilities.
user-invocable: false
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# Typer Knowledge

Build CLI applications with Typer by annotating Python functions. Typer converts type annotations into validated CLI parameters with auto-generated help text.

**Typer version:**
!`python -c "import typer; print(typer.__version__)" 2>/dev/null || echo "not found in PATH"`

## Scope

Consult `../python3-development/references/python3-standards.md` when applying shared architecture, typing, testing, or CLI rules; full standards, graphs, and amendment process are documented there.

TRIGGER: Activate when the user asks about building CLIs with Typer, defining CLI arguments or options, composing subcommands, testing CLI apps, or using Typer features like prompts, enums, progress bars, or autocompletion.

COVERS:
- App creation with `typer.Typer()` and `typer.run()`
- CLI arguments (`typer.Argument()`) and options (`typer.Option()`)
- Parameter types — enums, paths, numbers, dates, UUIDs, custom
- Subcommand composition with `app.add_typer()`
- Testing with `typer.testing.CliRunner`
- Output, colors, progress bars, callbacks, and autocompletion

DOES NOT COVER:
- Click internals beyond what Typer exposes
- Rich library beyond `typer.echo` / `typer.style`
- FastAPI or other web frameworks

## Workflow

```mermaid
flowchart TD
    Start([Task received]) --> Q1{Task type?}
    Q1 -->|Create app or add commands| AppCmd[Load reference — app-and-commands.md]
    Q1 -->|Define arguments or options| Params[Load reference — parameters.md]
    Q1 -->|Use enum, path, date, UUID| Types[Load reference — parameter-types.md]
    Q1 -->|Add subcommands or sub-apps| Sub[Load reference — subcommands.md]
    Q1 -->|Write tests| Test[Load reference — testing.md]
    Q1 -->|Callbacks, output, progress, packaging| Adv[Load reference — advanced-patterns.md]
```

## Reference Files

### App and Commands

Core patterns for creating Typer apps, registering commands with `@app.command()`, configuring multi-command apps, and controlling command naming and help text.
Load when creating a new app, adding commands, or configuring app-level behavior.

`references/app-and-commands.md`

### Parameters

Complete reference for CLI arguments and CLI options — `typer.Argument()`, `typer.Option()`, defaults, required vs optional, help text, prompts, password input, option names, environment variable bindings, multiple values, bool flags, and version options.
Load when defining any CLI parameter or controlling how input is received.

`references/parameters.md`

### Parameter Types

Type annotations Typer understands — `str`, `int`, `float`, `bool`, `enum.Enum`, `Literal`, `pathlib.Path`, file objects, `datetime`, `UUID`, and custom Click `ParamType` subclasses.
Load when restricting parameter values to a set, validating paths, parsing dates, or implementing custom types.

`references/parameter-types.md`

### Subcommands

Composing multiple `typer.Typer()` instances with `app.add_typer()` to create nested command hierarchies. Covers single-file and multi-file patterns, naming, help text, and callback overrides.
Load when adding sub-apps, creating command groups, or building git-style multi-level command trees.

`references/subcommands.md`

### Testing

Testing Typer apps with pytest and `typer.testing.CliRunner`. Covers invoking the app in tests, checking exit codes and output, simulating prompt input, and testing bare functions.
Load when writing tests for any Typer CLI.

`references/testing.md`

### Advanced Patterns

Context (`typer.Context`), eager callbacks, `typer.echo`/`typer.secho`/`typer.style`, progress bars, `typer.Exit`/`typer.Abort`, `typer.confirm`, autocompletion setup, packaging with `pyproject.toml`, and `typer.launch`.
Load when implementing version flags, colored output, progress reporting, shell completion, or packaging a CLI as a distributable tool.

`references/advanced-patterns.md`

## Quick Reference

```python
import typer
from typing import Annotated

app = typer.Typer()

@app.command()
def main(
    name: str,                                          # required argument
    count: Annotated[int, typer.Option()] = 1,          # optional option
    formal: bool = False,                               # --formal / --no-formal
):
    """Greet NAME."""
    for _ in range(count):
        greeting = f"Good day, {name}." if formal else f"Hello {name}"
        typer.echo(greeting)

if __name__ == "__main__":
    app()
```

```console
$ python main.py Alice --count 2 --formal
Good day, Alice.
Good day, Alice.
```
