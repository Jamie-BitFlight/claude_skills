---
name: modernpython
description: Reference guide for Python 3.11+ patterns with PEP citations. Use when reviewing code for modernization opportunities, writing new code to ensure modern patterns, or learning about specific PEPs and features.
argument-hint: '[file-paths-or-topic]'
user-invocable: true
---

# Python Modernization Reference

## Type Hints (PEP 585, 604)

```python
# Legacy (NEVER)
from typing import List, Dict, Optional, Union

# Modern (ALWAYS)
items: list[str]
config: dict[str, int] | None
```

## Walrus Operator (PEP 572)

```python
if data := fetch_data():
    process(data)
```

## Match-Case (PEP 634)

```python
match status_code:
    case 200: return "OK"
    case 404: return "Not Found"
    case _: return "Unknown"
```

## Self Type (PEP 673)

```python
from typing import Self

class Builder:
    def add(self, x: int) -> Self:
        self.value += x
        return self
```

## Exception Notes (PEP 678)

```python
except FileNotFoundError as e:
    e.add_note(f"Attempted path: {path}")
    raise
```

## StrEnum (3.11+)

```python
from enum import StrEnum

class Status(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
```

## Testing Patterns

```python
from pytest_mock import MockerFixture

def test_feature(mocker: MockerFixture) -> None:
    mock_func = mocker.patch('module.function', return_value=42)
```

## CLI Patterns

```python
from typing import Annotated
import typer

@app.command()
def process(
    input_file: Annotated[Path, typer.Argument(help="Input file")],
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
) -> None:
    """Process input file."""
    pass
```
