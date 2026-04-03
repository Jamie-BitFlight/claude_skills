# App and Commands

Core patterns for creating Typer applications, registering commands, and structuring multi-command CLIs.

## Table of Contents

1. [App Creation](#app-creation)
2. [Single-Command Apps](#single-command-apps)
3. [Multi-Command Apps](#multi-command-apps)
4. [Command Registration](#command-registration)
5. [App Behavior Options](#app-behavior-options)
6. [Command Naming](#command-naming)
7. [Command Help Text](#command-help-text)

---

## App Creation

```python
import typer

app = typer.Typer()
```

`typer.Typer()` creates the CLI application object. All commands are registered on this object.

For a single-function script with no explicit app:

```python
import typer

def main(name: str):
    typer.echo(f"Hello {name}")

if __name__ == "__main__":
    typer.run(main)
```

`typer.run()` implicitly creates a `Typer` app with the function as the single command.

---

## Single-Command Apps

A function decorated with `@app.command()` becomes the CLI entry point:

```python
import typer

app = typer.Typer()

@app.command()
def main(name: str, lastname: str = ""):
    """Say hi to NAME, optionally with a --lastname."""
    typer.echo(f"Hello {name} {lastname}")

if __name__ == "__main__":
    app()
```

The function docstring becomes the command's help text shown under `--help`.

---

## Multi-Command Apps

When the app has multiple commands, each decorated function becomes a subcommand:

```python
import typer

app = typer.Typer()

@app.command()
def create(username: str):
    typer.echo(f"Creating user: {username}")

@app.command()
def delete(username: str):
    typer.echo(f"Deleting user: {username}")

if __name__ == "__main__":
    app()
```

Usage:

```console
$ python main.py create Camila
Creating user: Camila

$ python main.py delete Camila
Deleting user: Camila
```

Commands appear in `--help` in declaration order — the order in the Python file determines display order.

---

## Command Registration

`@app.command()` registers the function without modifying it. The original function remains callable as a plain Python function. This means the same function can be used as both a Typer command and a FastAPI endpoint.

Equivalent to calling `app.command()(func)` programmatically:

```python
def main(name: str = "World"):
    typer.echo(f"Hello {name}")

app.command()(main)
```

---

## App Behavior Options

`typer.Typer()` accepts configuration kwargs:

```python
app = typer.Typer(
    no_args_is_help=True,   # Show help when called with no arguments
    invoke_without_command=True,  # Run callback even when subcommand is given
)
```

`no_args_is_help=True` is useful for multi-command apps — displays help instead of an error when no subcommand is given:

```console
$ python main.py
# Shows help text without requiring --help flag
```

---

## Command Naming

By default the command name is derived from the function name, with underscores replaced by hyphens:

```python
@app.command()
def delete_user(username: str):  # → CLI name: delete-user
    ...
```

Override with an explicit name:

```python
@app.command("rm")
def delete_user(username: str):  # → CLI name: rm
    ...
```

---

## Command Help Text

The function docstring becomes the command help text:

```python
@app.command()
def create(username: str):
    """
    Create a new user.

    USERNAME is the name for the new user.
    """
    typer.echo(f"Creating user: {username}")
```

For the top-level app help, pass `help` to `typer.Typer()`:

```python
app = typer.Typer(help="Manage users in the system.")
```
