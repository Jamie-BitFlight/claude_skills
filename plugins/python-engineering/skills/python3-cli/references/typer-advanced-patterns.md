# Advanced Patterns

Context, callbacks, output, progress bars, autocompletion, packaging, and error handling.

## Table of Contents

1. [Context](#context)
2. [Callbacks and Eager Options](#callbacks-and-eager-options)
3. [Output and Colors](#output-and-colors)
4. [Progress Bars](#progress-bars)
5. [Error Handling and Exit](#error-handling-and-exit)
6. [Autocompletion](#autocompletion)
7. [Packaging](#packaging)
8. [Launching Applications](#launching-applications)

---

## Context

`typer.Context` provides access to the Click context — useful for sharing state across commands and controlling behavior:

```python
import typer

app = typer.Typer()

@app.callback()
def main(ctx: typer.Context, verbose: bool = False):
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose

@app.command()
def process(ctx: typer.Context):
    if ctx.obj["verbose"]:
        typer.echo("Verbose mode: processing...")
    typer.echo("Done")
```

Pass `ctx.obj` to share data between a callback and its commands. `ctx.ensure_object(dict)` initializes `ctx.obj` if not already set.

Access the current context without passing it explicitly:

```python
ctx = typer.get_current_context()
```

---

## Callbacks and Eager Options

A callback on `typer.Option()` runs when the value is set. `is_eager=True` processes it before other parameters:

```python
import typer
from typing import Annotated, Optional

__version__ = "1.0.0"

def version_callback(value: bool):
    if value:
        typer.echo(f"Version: {__version__}")
        raise typer.Exit()

@app.command()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option("--version", callback=version_callback, is_eager=True),
    ] = None,
    name: str = "World",
):
    typer.echo(f"Hello {name}")
```

`raise typer.Exit()` in a callback exits cleanly. Without `is_eager=True`, `--version` would wait for all parameters to be processed first.

---

## Output and Colors

`typer.echo()` prints to stdout by default. Pass `err=True` to print to stderr:

```python
typer.echo("Normal output")          # stdout
typer.echo("Error message", err=True)  # stderr
```

Use `typer.style()` for colored output (requires `colorama` on Windows):

```python
success = typer.style("Done!", fg=typer.colors.GREEN, bold=True)
typer.echo(success)

warning = typer.style("Warning:", fg=typer.colors.YELLOW)
typer.echo(warning)
```

Available colors: `typer.colors.BLACK`, `RED`, `GREEN`, `YELLOW`, `BLUE`, `MAGENTA`, `CYAN`, `WHITE`, `BRIGHT_BLACK`, `BRIGHT_RED`, `BRIGHT_GREEN`, `BRIGHT_YELLOW`, `BRIGHT_BLUE`, `BRIGHT_MAGENTA`, `BRIGHT_CYAN`, `BRIGHT_WHITE`.

`typer.secho()` combines `style()` and `echo()`:

```python
typer.secho("Done!", fg=typer.colors.GREEN, bold=True)
```

---

## Progress Bars

`typer.progressbar()` renders a terminal progress bar. Use as a context manager:

```python
import typer
import time

@app.command()
def process(total: int = 100):
    with typer.progressbar(range(total), label="Processing") as progress:
        for item in progress:
            time.sleep(0.01)  # simulate work
    typer.echo("Done processing")
```

For an iterable with known length:

```python
items = ["a", "b", "c", "d"]
with typer.progressbar(items, length=len(items)) as progress:
    for item in progress:
        process_item(item)
```

---

## Error Handling and Exit

Exit normally with `raise typer.Exit()` (exit code 0) or `raise typer.Exit(code=N)`:

```python
@app.command()
def deploy(env: str):
    if env not in ("staging", "production"):
        typer.echo(f"Unknown env: {env}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"Deploying to {env}")
```

Abort with user-visible message using `raise typer.Abort()` (prints `Aborted!`, exit code 1):

```python
confirmed = typer.confirm("Are you sure?")
if not confirmed:
    raise typer.Abort()
```

`typer.confirm()` prompts for yes/no. Returns `True` on yes. Pass `default=True` to make Enter accept:

```python
if not typer.confirm("Delete all?", default=False):
    raise typer.Abort()
```

`typer.prompt()` asks for arbitrary input:

```python
name = typer.prompt("What is your name?")
```

Handle exceptions with `app(standalone_mode=False)` to catch `SystemExit` in scripts:

```python
if __name__ == "__main__":
    app(standalone_mode=False)
```

---

## Autocompletion

Autocompletion is installed per-shell with built-in commands:

```console
$ python main.py --install-completion
zsh completion installed in /home/user/.zshrc
Completion will take effect once you restart the terminal
```

`--install-completion` and `--show-completion` are added automatically when the app has a single command or when `add_completion=True` (the default) on `typer.Typer()`.

Disable autocompletion options:

```python
app = typer.Typer(add_completion=False)
```

Add custom autocompletion for a parameter using a `complete` callback:

```python
def complete_name(ctx, param, incomplete):
    names = ["Alice", "Bob", "Camila"]
    return [n for n in names if n.startswith(incomplete)]

@app.command()
def main(
    name: Annotated[str, typer.Argument(autocompletion=complete_name)],
):
    typer.echo(f"Hello {name}")
```

Run with the `typer` CLI command for ad-hoc autocompletion without installing:

```console
typer main.py run --name [TAB]
```

---

## Packaging

To create a distributable package with a proper CLI entry point, configure `pyproject.toml`:

```toml
[project.scripts]
myapp = "mypackage.main:app"
```

After installation, users run `myapp` directly:

```console
myapp --help
```

For a package with a single-function entry point:

```toml
[project.scripts]
myapp = "mypackage.main:main"
```

Where `main` is the function passed to `typer.run()`. Typer wraps it automatically when invoked as a script entry point.

---

## Launching Applications

`typer.launch()` opens a URL or file in the default application:

```python
@app.command()
def open_docs():
    typer.launch("https://typer.tiangolo.com")
```

Open the current directory in the file manager:

```python
typer.launch(".", locate=True)
```

`locate=True` reveals the item in the file manager instead of opening it.
