# Advanced Patterns

Custom renderables via the `__rich_console__` and `__rich__` protocols, `Layout` for multi-pane terminal UIs, `RegexHighlighter` for custom syntax highlighting, and `Theme` management. Load when writing custom renderables, multi-pane layouts, or custom highlighting rules.

## Table of Contents

1. [__rich__ Protocol — Simple Customization](#__rich__-protocol--simple-customization)
2. [__rich_console__ Protocol — Full Control](#__rich_console__-protocol--full-control)
3. [Low-Level Segment Rendering](#low-level-segment-rendering)
4. [Measuring Renderables](#measuring-renderables)
5. [Layout Class](#layout-class)
6. [RegexHighlighter](#regexhighlighter)
7. [Highlighter Usage](#highlighter-usage)
8. [Inspect Function](#inspect-function)
9. [Rich in the REPL](#rich-in-the-repl)

---

## `__rich__` Protocol — Simple Customization

The simplest way to customize how an object is rendered. Return any Rich-renderable or a markup string.

```python
class MyObject:
    def __rich__(self) -> str:
        return "[bold cyan]MyObject()"
```

Returning a string renders it as Rich markup. Return a `Text`, `Table`, or other renderable for more complex output.

---

## `__rich_console__` Protocol — Full Control

For multi-renderable output, implement `__rich_console__`. It must accept `Console` and `ConsoleOptions` and return an iterable of renderables (typically a generator using `yield`).

```python
from dataclasses import dataclass
from rich.console import Console, ConsoleOptions, RenderResult
from rich.table import Table

@dataclass
class Student:
    id: int
    name: str
    age: int

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        yield f"[b]Student:[/b] #{self.id}"
        my_table = Table("Attribute", "Value")
        my_table.add_row("name", self.name)
        my_table.add_row("age", str(self.age))
        yield my_table
```

Rules for `__rich_console__`:

- First positional param: `console: Console`
- Second positional param: `options: ConsoleOptions`
- Return type: `RenderResult` (iterable of renderables)
- Use `yield` to make it a generator
- Can yield strings (rendered as markup), `Text`, `Table`, or any other renderable
- Can yield `Segment` objects for lowest-level control

---

## Low-Level Segment Rendering

Yield `Segment` objects for complete character-level control. Each `Segment` is a `(text, style)` pair.

```python
from rich.console import Console, ConsoleOptions, RenderResult
from rich.segment import Segment
from rich.style import Style

class MyObject:
    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        yield Segment("My", Style(color="magenta"))
        yield Segment("Object", Style(color="green"))
        yield Segment("()", Style(color="cyan"))
```

---

## Measuring Renderables

When Rich needs to know the character width of a custom renderable (e.g., for table column sizing), implement `__rich_measure__`.

```python
from rich.console import Console, ConsoleOptions
from rich.measure import Measurement

class ChessBoard:
    def __rich_measure__(self, console: Console, options: ConsoleOptions) -> Measurement:
        return Measurement(8, options.max_width)
```

`Measurement(minimum, maximum)`:

- `minimum` — fewest characters the renderable can use without breaking
- `maximum` — preferred or maximum characters; use `options.max_width` for unconstrained max

---

## Layout Class

`Layout` divides the terminal into resizable panels for full-screen TUI-style applications. Combine with `Live` for live updates.

```python
from rich.layout import Layout
from rich.console import Console

console = Console()
layout = Layout()

# Split into named panes vertically (top to bottom)
layout.split_column(
    Layout(name="header", size=3),
    Layout(name="body"),
    Layout(name="footer", size=3),
)

# Split body horizontally (left to right)
layout["body"].split_row(
    Layout(name="left"),
    Layout(name="right"),
)

# Update content in a pane
layout["header"].update("[bold]My App")
layout["left"].update(Panel("Left content"))

console.print(layout)
```

### Layout methods

| Method | Description |
|--------|-------------|
| `layout.split_column(*layouts)` | Split into vertical sections (top-to-bottom) |
| `layout.split_row(*layouts)` | Split into horizontal sections (left-to-right) |
| `layout.split(*layouts, direction)` | Split with explicit direction |
| `layout["name"]` | Access a named child layout |
| `layout.update(renderable)` | Set the content of this pane |
| `layout.visible` | Set to `False` to hide the pane |

### Layout constructor parameters

| Parameter | Description |
|-----------|-------------|
| `renderable` | Initial content |
| `name` | Name for accessing this pane via `layout["name"]` |
| `size` | Fixed character size (rows for column split, chars for row split) |
| `minimum_size` | Minimum size (default 1) |
| `ratio` | Proportional size (default 1) |
| `visible` | `True` (default) |

Use with `Live` for live-updating layouts:

```python
from rich.live import Live

with Live(layout, screen=True, refresh_per_second=4) as live:
    while True:
        layout["left"].update(generate_left_panel())
        layout["right"].update(generate_right_panel())
        sleep(0.25)
```

---

## RegexHighlighter

Apply styles to text that matches regex patterns. Used to create custom syntax highlighters.

```python
from rich.highlighter import RegexHighlighter
from rich.theme import Theme
from rich.console import Console

class EmailHighlighter(RegexHighlighter):
    """Highlights email addresses."""
    base_style = "example."
    highlights = [r"(?P<email>[\w-]+@([\w-]+\.)+[\w-]+)"]

theme = Theme({"example.email": "bold magenta"})
console = Console(highlighter=EmailHighlighter(), theme=theme)
console.print("Send an email to hello@example.org to get started")
```

`RegexHighlighter` subclass rules:

- `base_style` — prefix for all named groups; must end with `"."`
- `highlights` — list of regex pattern strings; named groups become style names
- Named group `(?P<name>...)` in a pattern maps to style `{base_style}{name}`
- Patterns are applied in order; later patterns can override earlier ones

Built-in highlighters in `rich.highlighter`:

- `ReprHighlighter` — highlights Python repr output (default for console)
- `NullHighlighter` — disables all highlighting
- `ISO8601Highlighter` — highlights ISO 8601 dates

---

## Highlighter Usage

Apply a custom highlighter to a Console:

```python
console = Console(highlighter=EmailHighlighter())
```

Apply to a specific `print` call:

```python
console.print(text, highlight=False)   # disable for this call
console.print(text, highlighter=EmailHighlighter())  # custom for this call
```

Apply a highlighter to a `Text` object directly:

```python
from rich.highlighter import ReprHighlighter

highlighter = ReprHighlighter()
text = Text("Hello 1.0 World (1,2,3)")
highlighter.highlight(text)
console.print(text)
```

---

## Inspect Function

`inspect()` generates a formatted report on any Python object — useful for debugging.

```python
from rich import inspect
from rich.color import Color

color = Color.parse("red")
inspect(color, methods=True)
```

`inspect(object, console, title, help, methods, docs, private, dunder, sort, all, value)` parameters:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `methods` | `False` | Include method signatures |
| `docs` | `True` | Include docstrings |
| `private` | `False` | Include private attributes (`_name`) |
| `dunder` | `False` | Include dunder attributes (`__name__`) |
| `sort` | `True` | Sort attributes alphabetically |
| `all` | `False` | Include everything (private + dunder) |
| `value` | `True` | Show the object's value/repr |

---

## Rich in the REPL

Install pretty printing and tracebacks for the interactive REPL:

```python
from rich import pretty
pretty.install()
```

After `pretty.install()`, all REPL output is automatically pretty-printed with syntax highlighting.

IPython extension (loads pretty + tracebacks):

```python
%load_ext rich
```

To load by default, add `"rich"` to `c.InteractiveShellApp.extension` in IPython config.
