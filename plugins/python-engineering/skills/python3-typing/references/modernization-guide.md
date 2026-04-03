# Complete Python Modernization Guide

A comprehensive reference for writing modern Python 3.11+ code with best practices, type safety, and framework integration.

---

## Official PEP References

### Type System & Generics

| PEP                                          | Feature               | Python Version |
| -------------------------------------------- | --------------------- | -------------- |
| [PEP 585](https://peps.python.org/pep-0585/) | Builtin Generics      | 3.9+           |
| [PEP 604](https://peps.python.org/pep-0604/) | Union Pipe Syntax     | 3.10+          |
| [PEP 646](https://peps.python.org/pep-0646/) | TypeVarTuple          | 3.11           |
| [PEP 655](https://peps.python.org/pep-0655/) | Required/NotRequired  | 3.11           |
| [PEP 673](https://peps.python.org/pep-0673/) | Self Type             | 3.11           |
| [PEP 675](https://peps.python.org/pep-0675/) | LiteralString         | 3.11           |
| [PEP 695](https://peps.python.org/pep-0695/) | Type Parameter Syntax | 3.12           |
| [PEP 696](https://peps.python.org/pep-0696/) | TypeVar Defaults      | 3.13           |

### Runtime Features

| PEP                                          | Feature                 | Python Version |
| -------------------------------------------- | ----------------------- | -------------- |
| [PEP 654](https://peps.python.org/pep-0654/) | Exception Groups        | 3.11           |
| [PEP 657](https://peps.python.org/pep-0657/) | Fine-Grained Tracebacks | 3.11           |
| [PEP 678](https://peps.python.org/pep-0678/) | Exception Notes         | 3.11           |
| [PEP 680](https://peps.python.org/pep-0680/) | tomllib                 | 3.11           |
| [PEP 684](https://peps.python.org/pep-0684/) | Per-Interpreter GIL     | 3.13           |
| [PEP 701](https://peps.python.org/pep-0701/) | Enhanced F-Strings      | 3.12           |

---

## Legacy Patterns to Avoid

### Typing Module Legacy Imports

**FORBIDDEN:**

```python
from typing import List, Dict, Optional, Union, Tuple, Set

def process_items(items: List[str]) -> Dict[str, int]:
    result: Optional[str] = None
    values: Union[int, str] = 0
    return {}
```

**REQUIRED:**

```python
def process_items(items: list[str]) -> dict[str, int]:
    result: str | None = None
    values: int | str = 0
    return {}
```

### Manual Implementations Duplicating Stdlib

**FORBIDDEN:**

```python
def has_command(cmd: str) -> bool:
    result = subprocess.run(['which', cmd], capture_output=True)
    return result.returncode == 0
```

**REQUIRED:**

```python
from shutil import which

if sudo_path := which("sudo"):
    # Command exists
    pass
```

### Assignment Before Truthiness Check

**LEGACY:**

```python
result = expensive_function()
if result:
    process(result)

match = re.search(pattern, text)
if match:
    return match.group(1)
```

**MODERN:**

```python
if result := expensive_function():
    process(result)

if match := re.search(pattern, text):
    return match.group(1)
```

### unittest.mock in Tests

**FORBIDDEN:**

```python
from unittest.mock import Mock, patch

@patch('module.function')
def test_something(mock_func):
    mock_func.return_value = 42
```

**REQUIRED:**

```python
from pytest_mock import MockerFixture

def test_something(mocker: MockerFixture) -> None:
    mock_func = mocker.patch('module.function', return_value=42)
```

---

## Match-Case vs If/Elif

**Rule:**

- Any elif → Use match-case
- Inequalities (`<`, `>`, `<=`, `>=`) → Use if/elif
- Boolean operators (`and`, `or`, `not`, `in`) → Use if/elif
- Simple if or if/else → Use if/else
- Existing match-case → Never refactor away

**Example - Any elif (use match-case):**

```python
# Modern
match status_code:
    case 200: return "OK"
    case 404: return "Not Found"
    case 500: return "Server Error"
    case _: return "Unknown"

# Legacy (avoid)
if status_code == 200:
    return "OK"
elif status_code == 404:
    return "Not Found"
elif status_code == 500:
    return "Server Error"
else:
    return "Unknown"
```

**Example - Inequalities (use if/elif):**

```python
if score >= 90:
    grade = "A"
elif score >= 80:
    grade = "B"
elif score >= 70:
    grade = "C"
else:
    grade = "F"
```

**Example - Structural patterns:**

```python
match command.split():
    case ["go", direction]:
        move(direction)
    case ["get", item]:
        pickup(item)
    case ["put", item, "in", container]:
        place(item, container)
```

---

## Python 3.11 Baseline Features

### Built-in Generics

```python
items: list[str]
mapping: dict[str, int]
unique: set[int]
coords: tuple[float, float]
frozen: frozenset[str]

# Nested generics
matrix: list[list[int]]
lookup: dict[str, list[tuple[str, int]]]

# Abstract types
from collections.abc import Iterable, Sequence, Mapping

def process(items: Iterable[str]) -> Sequence[int]:
    data: Mapping[str, int] = {}
    return []
```

### Union Types with Pipe

```python
value: int | str
result: dict[str, int] | None
data: int | float | str | None

def get_config(path: str | None = None) -> dict[str, str] | None:
    pass

# Type aliases
JsonValue = str | int | float | bool | None | dict[str, "JsonValue"] | list["JsonValue"]
```

### Exception Groups

```python
def process_batch(items: list[Any]) -> None:
    errors: list[Exception] = []
    for item in items:
        try:
            process(item)
        except ValueError as e:
            errors.append(e)
    if errors:
        raise ExceptionGroup("Processing failed", errors)

# Handling
try:
    process_batch(items)
except* ValueError as eg:
    for exc in eg.exceptions:
        log.error(f"Validation error: {exc}")
except* RuntimeError as eg:
    for exc in eg.exceptions:
        log.error(f"Runtime error: {exc}")
```

### TOML Support

```python
import tomllib
from pathlib import Path

def load_config(path: Path) -> dict[str, Any]:
    with path.open('rb') as f:
        return tomllib.load(f)

config = load_config(Path("pyproject.toml"))
```

### StrEnum

```python
from enum import StrEnum

class Status(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

def set_status(status: Status) -> None:
    match status:
        case Status.PENDING:
            print("Waiting to start")
        case Status.RUNNING:
            print("In progress")
```

### Self Type

```python
from typing import Self

class Builder:
    def __init__(self) -> None:
        self.value = 0

    def add(self, x: int) -> Self:
        self.value += x
        return self

    def multiply(self, x: int) -> Self:
        self.value *= x
        return self

    def build(self) -> int:
        return self.value

result = Builder().add(5).multiply(3).build()
```

### TypeVarTuple for Variadic Generics

```python
from typing import TypeVarTuple, Generic

Ts = TypeVarTuple('Ts')

class Tuple(Generic[*Ts]):
    def __init__(self, *items: *Ts) -> None:
        self.items = items

t1 = Tuple(1, "hello")  # Tuple[int, str]
```

### Required/NotRequired for TypedDict

```python
from typing import TypedDict, Required, NotRequired

class User(TypedDict):
    name: Required[str]
    email: Required[str]
    phone: NotRequired[str]
    address: NotRequired[str]

user: User = {"name": "Alice", "email": "alice@example.com"}
```

### Exception Notes

```python
def process_file(path: str) -> None:
    try:
        with open(path) as f:
            data = json.load(f)
    except FileNotFoundError as e:
        e.add_note(f"Attempted to read from: {path}")
        e.add_note("Check that the file exists and path is correct")
        raise
    except json.JSONDecodeError as e:
        e.add_note(f"File {path} contains invalid JSON")
        raise
```

---

## Python 3.12+ Features

### PEP 695 Generic Syntax

```python
# 3.11 style
from typing import TypeVar, Generic

T = TypeVar('T')

class Container(Generic[T]):
    def __init__(self, value: T) -> None:
        self.value = value

# 3.12+ style
class Container[T]:
    def __init__(self, value: T) -> None:
        self.value = value

def first[T](items: list[T]) -> T | None:
    return items[0] if items else None

type Point[T] = tuple[T, T]
```

### Enhanced F-Strings

```python
# Nested f-strings
name = "World"
message = f"Hello, {f'{name.upper()}'}"

# Multi-line with proper indentation
query = f"""
    SELECT *
    FROM {table_name}
    WHERE id = {user_id}
"""

# f-strings in comprehensions
results = [f"{x=}" for x in range(5)]
```

---

## Python 3.13+ Features

### TypeVar Defaults

```python
from typing import TypeVar

T = TypeVar('T', default=str)

class Container[T = str]:
    def __init__(self, value: T) -> None:
        self.value = value

Container()  # Container[str] inferred
Container(42)  # Container[int] inferred
```

### Free-Threaded Mode

```python
# Run with: python --disable-gil script.py
import threading

def worker(thread_id: int) -> None:
    print(f"Thread {thread_id} running without GIL contention")

threads = []
for i in range(4):
    t = threading.Thread(target=worker, args=(i,))
    threads.append(t)
    t.start()

for t in threads:
    t.join()
```

### Removed Modules (Python 3.13)

These modules were removed. Use alternatives:

| Removed   | Alternative                 |
| --------- | --------------------------- |
| cgi       | urllib.parse or frameworks  |
| cgitb     | logging + error tracking    |
| crypt     | bcrypt or argon2-cffi       |
| imghdr    | PIL/Pillow                  |
| telnetlib | paramiko or fabric          |
| pipes     | subprocess with shell=False |
| uu        | base64.a2b_uu               |

---

## Type System Best Practices

### Protocol for Structural Typing

```python
from typing import Protocol

class Drawable(Protocol):
    def draw(self) -> None: ...

def render(obj: Drawable) -> None:
    obj.draw()

class Circle:
    def draw(self) -> None:
        print("Drawing circle")

render(Circle())  # Works without inheritance
```

### TypeGuard for Type Narrowing

```python
from typing import TypeGuard

def is_string_list(value: list[object]) -> TypeGuard[list[str]]:
    return all(isinstance(item, str) for item in value)

def process_strings(items: list[object]) -> None:
    if is_string_list(items):
        for item in items:
            print(item.upper())  # Type checker knows items is list[str]
```

### Annotated for Metadata

```python
from typing import Annotated
from typer import Option

def main(
    name: Annotated[str, Option(help="User name")],
    age: Annotated[int, Option(min=0, max=150)],
) -> None:
    pass
```

### Never for Unreachable Code

```python
from typing import Never

def raise_error(message: str) -> Never:
    raise RuntimeError(message)
```

### LiteralString for SQL Safety

```python
from typing import LiteralString

def execute_query(query: LiteralString, *args: object) -> list[dict[str, object]]:
    pass

execute_query("SELECT * FROM users WHERE id = ?", 123)  # OK
execute_query(f"SELECT * FROM {user_input}")  # Type error!
```

### ParamSpec for Callable Forwarding

```python
from typing import ParamSpec, TypeVar, Callable
from functools import wraps

P = ParamSpec('P')
R = TypeVar('R')

def log_call(func: Callable[P, R]) -> Callable[P, R]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        print(f"Calling {func.__name__}")
        return func(*args, **kwargs)
    return wrapper
```

### Type Aliases

```python
from pathlib import Path

PathLike = str | Path
Command = list[str]
CommandOutput = tuple[str, str, int]  # stdout, stderr, returncode
JsonPrimitive = str | int | float | bool | None
JsonValue = JsonPrimitive | dict[str, "JsonValue"] | list["JsonValue"]
```

---

## Framework Patterns

### Typer CLI

```python
import typer
from typing import Annotated
from pathlib import Path

app = typer.Typer(
    name="myapp",
    help="My application description",
    add_completion=False,
)

@app.command()
def process(
    input_file: Annotated[Path, typer.Argument(help="Input file to process")],
    output_file: Annotated[Path | None, typer.Option(help="Output file path")] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
    threads: Annotated[int, typer.Option(min=1, max=32)] = 4,
) -> None:
    """Process input file and generate output."""
    if verbose:
        typer.echo(f"Processing {input_file}")
    result_path = output_file or input_file.with_suffix('.out')
    typer.echo(f"Output written to {result_path}")

@app.command(rich_help_panel="Configuration")
def configure(
    config_file: Annotated[Path, typer.Argument(help="Configuration file")],
) -> None:
    """Configure application settings."""
    pass

if __name__ == "__main__":
    app()
```

### Rich Terminal Output

```python
from rich import box
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.measure import Measurement

console = Console()

# Markup output
console.print("[bold green]Success:[/bold green] Operation completed")
console.print("[bold red]Error:[/bold red] Something went wrong", err=True)

# Panels
console.print(Panel(
    "Important information here",
    title="Notice",
    border_style="yellow"
))

# Progress bars
with Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    console=console,
) as progress:
    task = progress.add_task("Processing...", total=100)
    for i in range(100):
        progress.update(task, advance=1)

# Table width control (required for production CLIs)
def _get_table_width(table: Table) -> int:
    temp_console = Console(width=9999)
    measurement = Measurement.get(temp_console, temp_console.options, table)
    return int(measurement.maximum)

def display_results(results: list[dict[str, str]]) -> None:
    table = Table(title="Results", box=box.MINIMAL_DOUBLE_HEAD)
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Status", style="magenta")

    for result in results:
        table.add_row(result["name"], result["status"])

    table.width = _get_table_width(table)
    console.print(table, crop=False, overflow="ignore", no_wrap=True, soft_wrap=True)
```

### pytest Testing

```python
from pathlib import Path
from typing import Generator
import pytest
from pytest_mock import MockerFixture

@pytest.fixture
def temp_config(tmp_path: Path) -> Path:
    config_file = tmp_path / "config.json"
    config_file.write_text('{"key": "value"}')
    return config_file

@pytest.fixture
def database_connection() -> Generator[Connection, None, None]:
    conn = connect_to_database()
    yield conn
    conn.close()

def test_process_file(temp_config: Path, mocker: MockerFixture) -> None:
    """Test file processing with valid configuration."""
    # Arrange
    mock_api = mocker.patch('module.external_api')
    mock_api.return_value = {"status": "ok"}

    # Act
    result = process_file(temp_config)

    # Assert
    assert result.success
    mock_api.assert_called_once()

def test_invalid_config_raises_error() -> None:
    with pytest.raises(ValueError, match="Invalid configuration format"):
        load_config({"invalid": "data"})

@pytest.mark.parametrize("input_value,expected", [
    ("hello", "HELLO"),
    ("world", "WORLD"),
    ("", ""),
])
def test_uppercase(input_value: str, expected: str) -> None:
    assert to_uppercase(input_value) == expected

@pytest.mark.asyncio
async def test_async_operation(mocker: MockerFixture) -> None:
    mock_fetch = mocker.patch('module.fetch_data', new_callable=mocker.AsyncMock)
    mock_fetch.return_value = {"data": "value"}

    result = await process_async()

    assert result.success
    mock_fetch.assert_awaited_once()
```

---

## Concrete Transformations

### Loop Transformations

```python
# Legacy
for i in range(len(items)):
    print(f"{i}: {items[i]}")

# Modern
for i, item in enumerate(items):
    print(f"{i}: {item}")

# Legacy
result = ""
for item in items:
    result += str(item) + ", "

# Modern
result = ", ".join(str(item) for item in items)
```

### Collection Membership

```python
# Legacy (O(n) lookup)
valid_codes = [200, 201, 204, 301, 302]

# Modern (O(1) lookup)
VALID_CODES = {200, 201, 204, 301, 302}
```

### Exception Handling

```python
# Legacy (too broad)
try:
    return risky_operation()
except Exception:
    return None

# Modern (specific exceptions)
try:
    return risky_operation()
except (ValueError, KeyError) as e:
    raise ProcessingError("Failed to process data") from e
```

### Context Managers

```python
# Legacy
file = open("data.txt")
try:
    data = file.read()
finally:
    file.close()

# Modern
with open("data.txt") as file:
    data = file.read()

# Multiple managers
with lock1, lock2:
    # critical section
    pass
```

### Path Handling

```python
# Legacy
import os
config_path = os.path.join(home_dir, ".config", "app", "config.json")

# Modern
from pathlib import Path
config_path = Path.home() / ".config" / "app" / "config.json"
data = config_path.read_text()
```

### Subprocess

```python
# Legacy (dangerous)
subprocess.run(f"ls -la {directory}", shell=True)

# Modern (safer)
from shutil import which

if ls_path := which("ls"):
    subprocess.run([ls_path, "-la", directory], capture_output=True, text=True, check=True)
```

---

## Summary Principles

1. Python 3.11+ minimum baseline
2. Built-in generics (PEP 585) and pipe unions (PEP 604) exclusively
3. Walrus operator to reduce line count
4. Match-case for elif patterns
5. Comprehensive type hints with Protocol, TypeVar, TypeGuard
6. Self type (PEP 673) for fluent APIs
7. Typer patterns with Annotated syntax
8. Rich for terminal output with proper width handling
9. pytest with pytest-mock and AAA pattern
10. Clean architecture with dependency injection
11. Prefer stdlib over manual implementations
12. Specific exceptions with fail-fast error handling
13. Exception notes (PEP 678) for richer error context
14. Validation with ruff, ty check (or project mypy if already configured), pytest
15. 80%+ test coverage
