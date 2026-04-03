# Parameter Types

Type annotations Typer understands natively, including enums, paths, files, numbers with constraints, dates, UUIDs, and custom types.

## Table of Contents

1. [Built-in Types](#built-in-types)
2. [Enum and Literal Choices](#enum-and-literal-choices)
3. [Number Constraints](#number-constraints)
4. [Path and File Types](#path-and-file-types)
5. [DateTime](#datetime)
6. [UUID](#uuid)
7. [Custom Types](#custom-types)

---

## Built-in Types

Typer maps Python built-in types to CLI display types:

| Python type | CLI display | Behavior |
|-------------|-------------|----------|
| `str` | `TEXT` | No conversion |
| `int` | `INTEGER` | Validated integer |
| `float` | `FLOAT` | Validated float |
| `bool` | flag pair | `--flag` / `--no-flag` |

Type conversion happens at parse time. Invalid input exits with an error before reaching the function body.

---

## Enum and Literal Choices

Restrict input to a predefined set of values using `enum.Enum`:

```python
import typer
import enum
from typing import Annotated

class NeuralNetwork(str, enum.Enum):
    simple = "simple"
    conv = "conv"
    lstm = "lstm"

@app.command()
def train(
    network: Annotated[NeuralNetwork, typer.Option()] = NeuralNetwork.simple,
):
    typer.echo(f"Training neural network of type: {network.value}")
```

The parameter value arrives as an `Enum` instance. Use `.value` to get the string.

Enum choices are case-sensitive by default:

```console
$ python main.py --network CONV
Error: Invalid value for '--network': 'CONV' is not one of 'simple', 'conv', 'lstm'.
```

Make case-insensitive with `case_sensitive=False`:

```python
network: Annotated[NeuralNetwork, typer.Option(case_sensitive=False)] = NeuralNetwork.simple
```

Use `Literal` for choices without defining a class:

```python
from typing import Annotated, Literal

@app.command()
def train(
    network: Annotated[Literal["simple", "conv", "lstm"], typer.Option()] = "simple",
):
    typer.echo(f"Training: {network}")
```

Invalid value error message:

```text
Error: Invalid value for '--network': 'capsule' is not one of 'simple', 'conv', 'lstm'.
```

---

## Number Constraints

Use `typer.Option()` or `typer.Argument()` with `min` and `max` to constrain numeric ranges:

```python
import typer
from typing import Annotated

@app.command()
def main(
    percent: Annotated[float, typer.Option(min=0, max=100)] = 40.0,
    rank: Annotated[int, typer.Option(min=0)] = 0,
):
    typer.echo(f"Percent: {percent}, Rank: {rank}")
```

`clamp=True` silently clamps values to the range instead of erroring:

```python
percent: Annotated[float, typer.Option(min=0, max=100, clamp=True)] = 40.0
```

---

## Path and File Types

Use `pathlib.Path` for filesystem paths. Typer validates existence and type when constraints are set:

```python
import typer
from pathlib import Path
from typing import Annotated

@app.command()
def main(
    config: Annotated[Path, typer.Option(
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    )],
):
    typer.echo(f"Config: {config}")
```

`exists=True` — path must exist; `file_okay` / `dir_okay` — constrain to file or directory; `readable` / `writable` — constrain access mode.

For file objects (opened handles), use `typer.FileText` or `typer.FileBinaryRead`:

```python
from typing import Annotated
import typer

@app.command()
def main(
    config: Annotated[typer.FileText, typer.Option()] = ...,
):
    text = config.read()
    typer.echo(text)
```

---

## DateTime

Use `datetime.datetime` for automatic date/time parsing:

```python
import typer
from datetime import datetime
from typing import Annotated

@app.command()
def main(
    launch: Annotated[datetime, typer.Option()] = datetime(2023, 1, 1),
):
    typer.echo(f"Launch date: {launch}")
```

Accepted formats include ISO 8601 (`2023-01-15`) and variants. Invalid values produce an error at parse time.

---

## UUID

Use `uuid.UUID` for automatic UUID parsing and validation:

```python
import typer
import uuid
from typing import Annotated

@app.command()
def main(
    user_id: Annotated[uuid.UUID, typer.Argument()],
):
    typer.echo(f"User ID: {user_id}")
```

Input is validated as a well-formed UUID. Invalid UUIDs produce a parse error before the function runs.

---

## Custom Types

Implement a custom Click `ParamType` subclass to handle types Typer doesn't natively support:

```python
import click
import typer
from typing import Annotated

class EmailType(click.ParamType):
    name = "email"

    def convert(self, value, param, ctx):
        if "@" not in value:
            self.fail(f"{value!r} is not a valid email address", param, ctx)
        return value

@app.command()
def main(
    email: Annotated[str, typer.Option(click_type=EmailType())],
):
    typer.echo(f"Email: {email}")
```

`self.fail()` triggers the standard Click error display with the message provided.
