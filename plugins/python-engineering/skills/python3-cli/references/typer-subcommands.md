# Subcommands

Composing Typer apps from multiple sub-apps to create nested command hierarchies.

## Table of Contents

1. [Core Pattern](#core-pattern)
2. [Adding a Sub-Typer](#adding-a-sub-typer)
3. [Naming and Help for Sub-Apps](#naming-and-help-for-sub-apps)
4. [Nested Subcommands](#nested-subcommands)
5. [Single-File Subcommands](#single-file-subcommands)
6. [Callback Override](#callback-override)

---

## Core Pattern

Each `typer.Typer()` instance is a self-contained CLI app. Sub-apps are added to a parent with `app.add_typer()`. This enables modular composition without coupling modules.

```python
import typer

# items.py
items_app = typer.Typer()

@items_app.command()
def create(item: str):
    typer.echo(f"Creating item: {item}")

@items_app.command()
def delete(item: str):
    typer.echo(f"Deleting item: {item}")
```

```python
# main.py
import typer
from items import items_app
from users import users_app

app = typer.Typer()
app.add_typer(items_app, name="items")
app.add_typer(users_app, name="users")

if __name__ == "__main__":
    app()
```

Result:

```console
$ python main.py items create Wand
Creating item: Wand

$ python main.py users create Camila
Creating user: Camila
```

---

## Adding a Sub-Typer

`app.add_typer(sub_app, name="command-name")` registers the sub-app under `name`:

```python
app.add_typer(items_app, name="items")
```

The `name` parameter sets the CLI command used to invoke the sub-app. Without `name`, Typer attempts to derive one from the sub-app's callback or raises an error.

---

## Naming and Help for Sub-Apps

Pass `name` and `help` to `app.add_typer()` to control CLI display:

```python
app.add_typer(
    items_app,
    name="items",
    help="Manage items in the system.",
)
```

Or set `name` and `help` on the `typer.Typer()` constructor:

```python
items_app = typer.Typer(name="items", help="Manage items.")
app.add_typer(items_app)
```

---

## Nested Subcommands

Sub-apps can themselves contain sub-apps, creating arbitrary depth:

```python
import typer

app = typer.Typer()
land_app = typer.Typer()
sea_app = typer.Typer()

app.add_typer(land_app, name="land")
app.add_typer(sea_app, name="sea")

@land_app.command("create")
def land_create(item: str):
    typer.echo(f"Creating land item: {item}")

@sea_app.command("create")
def sea_create(item: str):
    typer.echo(f"Creating sea item: {item}")
```

```console
$ python main.py land create Castle
Creating land item: Castle

$ python main.py sea create Ship
Creating sea item: Ship
```

---

## Single-File Subcommands

Sub-apps can live in a single file. Use `add_typer` to group commands logically without separate modules:

```python
import typer

app = typer.Typer()
users_app = typer.Typer()
app.add_typer(users_app, name="users")

@users_app.command("create")
def users_create(username: str):
    typer.echo(f"Creating user: {username}")

@users_app.command("delete")
def users_delete(username: str):
    typer.echo(f"Deleting user: {username}")

if __name__ == "__main__":
    app()
```

---

## Callback Override

Define a callback on a sub-app to run code before any subcommand. Use `invoke_without_command=True` to also run it when no subcommand is given:

```python
import typer
from typing import Optional

app = typer.Typer()
items_app = typer.Typer()
app.add_typer(items_app, name="items")

@items_app.callback()
def items_callback(ctx: typer.Context, verbose: bool = False):
    """Manage items."""
    if verbose:
        typer.echo("Verbose mode enabled")
```

The callback runs before every subcommand of `items_app`. Parameters on the callback become options of the `items` command group.
