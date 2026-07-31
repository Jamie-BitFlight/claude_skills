
## Progress Bars

### Simple Progress

```python
from rich.progress import track
import time

for item in track(range(100), description="Processing..."):
    time.sleep(0.01)
```

### Multiple Tasks

```python
from rich.progress import Progress

with Progress() as progress:
    task1 = progress.add_task("[red]Downloading...", total=100)
    task2 = progress.add_task("[green]Processing...", total=100)

    while not progress.finished:
        progress.update(task1, advance=0.9)
        progress.update(task2, advance=0.6)
        time.sleep(0.02)
```

## Syntax Highlighting

```python
from rich.console import Console
from rich.syntax import Syntax

console = Console()

code = """
def hello():
    print("Hello, World!")
"""

syntax = Syntax(code, "python", theme="monokai", line_numbers=True)
console.print(syntax)
```

## Tree Displays

```python
from rich.console import Console
from rich.tree import Tree

console = Console()

tree = Tree("[bold blue]MyProject/[/]")
src = tree.add("[bold]src/[/]")
src.add("main.py")
src.add("config.py")

tests = tree.add("[bold]tests/[/]")
tests.add("test_main.py")

console.print(tree)
```
