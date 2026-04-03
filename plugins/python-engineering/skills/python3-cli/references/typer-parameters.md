# Parameters — Arguments and Options

Complete reference for CLI arguments (`typer.Argument()`) and CLI options (`typer.Option()`), including types, defaults, help text, prompts, and validation.

## Table of Contents

1. [Arguments vs Options](#arguments-vs-options)
2. [CLI Arguments](#cli-arguments)
3. [CLI Options](#cli-options)
4. [Type Annotations and Conversion](#type-annotations-and-conversion)
5. [Required and Optional](#required-and-optional)
6. [Default Values](#default-values)
7. [Help Text](#help-text)
8. [Prompts](#prompts)
9. [Password Input](#password-input)
10. [Option Names](#option-names)
11. [Environment Variables](#environment-variables)
12. [Multiple Values](#multiple-values)
13. [Bool Flags](#bool-flags)
14. [Version Option](#version-option)

---

## Arguments vs Options

| Feature | CLI Argument | CLI Option |
|---------|-------------|------------|
| Syntax | positional (no `--`) | `--name value` |
| Default | required | optional |
| Order-dependent | yes | no |
| Python type | `typer.Argument()` or bare annotation | `typer.Option()` or default value |

A parameter without a default value becomes a required CLI argument. A parameter with a default value becomes an optional CLI option.

---

## CLI Arguments

Declared by using `typer.Argument()` or by having no default value:

```python
import typer

app = typer.Typer()

@app.command()
def main(name: str):
    typer.echo(f"Hello {name}")
```

With explicit `typer.Argument()` to add metadata:

```python
import typer
from typing import Annotated

app = typer.Typer()

@app.command()
def main(name: Annotated[str, typer.Argument(help="The name to greet")]):
    typer.echo(f"Hello {name}")
```

Optional argument with a default:

```python
import typer
from typing import Annotated, Optional

@app.command()
def main(name: Annotated[Optional[str], typer.Argument()] = None):
    if name:
        typer.echo(f"Hello {name}")
    else:
        typer.echo("Hello World")
```

Multiple positional arguments are filled in declaration order — order matters:

```python
@app.command()
def main(name: str, lastname: str):
    typer.echo(f"Hello {name} {lastname}")
```

---

## CLI Options

Declared by using `typer.Option()` or by providing a default value:

```python
import typer
from typing import Annotated

@app.command()
def main(
    name: str,
    lastname: Annotated[str, typer.Option(help="Last name")] = "",
):
    typer.echo(f"Hello {name} {lastname}")
```

A parameter with a default value `= ""` automatically becomes an optional CLI option named `--lastname`.

---

## Type Annotations and Conversion

Typer converts CLI string input to the annotated Python type:

```python
@app.command()
def main(
    name: str,           # TEXT
    age: int = 0,        # INTEGER — validated at CLI
    height: float = 0.0, # FLOAT — validated at CLI
    active: bool = True, # FLAG — --active / --no-active
):
    ...
```

Invalid type input produces a CLI error:

```console
$ python main.py --age 15.3
Error: Invalid value for '--age': '15.3' is not a valid integer
```

---

## Required and Optional

A parameter is required when it has no default. Optional when it has a default (including `None`):

```python
import typer
from typing import Annotated, Optional

@app.command()
def main(
    name: str,                                             # required argument
    lastname: Annotated[Optional[str], typer.Option()] = None,  # optional option
):
    ...
```

Force a CLI option to be required by using `typer.Option()` with `...` (Ellipsis) as default:

```python
from typing import Annotated

@app.command()
def main(
    name: Annotated[str, typer.Option()],  # required option
):
    ...
```

---

## Default Values

Set defaults directly in the function signature or via `typer.Argument()`/`typer.Option()`:

```python
import typer
from typing import Annotated

@app.command()
def main(
    name: str = "World",
    count: Annotated[int, typer.Option()] = 1,
):
    for _ in range(count):
        typer.echo(f"Hello {name}")
```

---

## Help Text

Add help text via `typer.Argument(help=...)` or `typer.Option(help=...)`:

```python
import typer
from typing import Annotated

@app.command()
def main(
    name: Annotated[str, typer.Argument(help="The person to greet")],
    count: Annotated[int, typer.Option(help="Number of greetings")] = 1,
):
    """Greet NAME a number of times."""
    for _ in range(count):
        typer.echo(f"Hello {name}")
```

---

## Prompts

Add `prompt=True` to `typer.Option()` to ask the user for input when the option is not provided:

```python
import typer
from typing import Annotated

@app.command()
def main(
    name: str,
    email: Annotated[str, typer.Option(prompt=True)],
):
    typer.echo(f"Hello {name}, your email is: {email}")
```

Custom prompt text:

```python
email: Annotated[str, typer.Option(prompt="Your email address")]
```

---

## Password Input

`hide_input=True` hides typed characters. Use with `confirmation_prompt=True` to require confirmation:

```python
import typer
from typing import Annotated

@app.command()
def create(
    username: str,
    password: Annotated[str, typer.Option(prompt=True, hide_input=True, confirmation_prompt=True)],
):
    typer.echo(f"Creating {username}")
```

---

## Option Names

Override CLI option names with a list of strings:

```python
import typer
from typing import Annotated

@app.command()
def main(
    name: Annotated[str, typer.Option("--name", "-n", help="Your name")],
):
    typer.echo(f"Hello {name}")
```

Usage: `--name Camila` or `-n Camila`

---

## Environment Variables

Bind a CLI option to an environment variable with `envvar`:

```python
import typer
from typing import Annotated

@app.command()
def main(
    name: Annotated[str, typer.Option(envvar="APP_NAME")],
):
    typer.echo(f"Hello {name}")
```

The CLI option takes precedence over the environment variable. The environment variable takes precedence over the default.

Also works for CLI arguments:

```python
name: Annotated[str, typer.Argument(envvar="APP_NAME")]
```

---

## Multiple Values

Accept multiple values for a single option using `List`:

```python
import typer
from typing import Annotated, List

@app.command()
def main(
    names: Annotated[List[str], typer.Option()] = [],
):
    for name in names:
        typer.echo(f"Hello {name}")
```

Usage: `--names Alice --names Bob`

---

## Bool Flags

A `bool` parameter automatically creates paired `--flag` / `--no-flag` options:

```python
@app.command()
def main(
    name: str,
    formal: bool = False,   # creates --formal / --no-formal
):
    if formal:
        typer.echo(f"Good day, {name}.")
    else:
        typer.echo(f"Hello {name}")
```

The default shows in help as `[default: no-formal]` or `[default: formal]`.

---

## Version Option

Use `typer.Option()` with a callback to implement `--version`:

```python
import typer
from typing import Annotated, Optional

__version__ = "0.1.0"

def version_callback(value: bool):
    if value:
        typer.echo(f"My App version: {__version__}")
        raise typer.Exit()

@app.command()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option("--version", callback=version_callback, is_eager=True),
    ] = None,
):
    typer.echo("Running app")
```

`is_eager=True` ensures `--version` is processed before other parameters so it can exit cleanly.
