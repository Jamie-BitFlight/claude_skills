# Common Widgets

## Display Widgets

### Label / Static

Display static or updatable text:

```python
from textual.widgets import Label, Static

# Label and Static are both display widgets; Label is designed for
# single-line text, Static for general-purpose rendered content.
# Both support .update() with plain text or Rich markup.
# SOURCE: https://textual.textualize.io/widgets/ (accessed 2026-05-07)
label = Label("Hello World")
static = Static("Initial text")

# Update later
static.update("New text")
static.update("[bold]Rich markup[/bold]")
```

### Placeholder

Useful for prototyping layouts:

```python
from textual.widgets import Placeholder

# Shows widget ID and size info
yield Placeholder("Custom label", id="p1")
yield Placeholder(variant="size")  # Shows dimensions
yield Placeholder(variant="text")  # Shows placeholder text
```

## Input Widgets

### Button

```python
from textual.widgets import Button

yield Button("Click Me", id="my-button")
yield Button("Disabled", disabled=True)


# Handle click
def on_button_pressed(self, event: Button.Pressed) -> None:
    button_id = event.button.id
    self.notify(f"{button_id} clicked!")
```

### Input

Single-line text input:

```python
from textual.widgets import Input

yield Input(placeholder="Enter text...", id="name-input")


def on_input_changed(self, event: Input.Changed) -> None:
    self.text_value = event.value


def on_input_submitted(self, event: Input.Submitted) -> None:
    # User pressed Enter
    self.process_input(event.value)
```

### TextArea

Multi-line text editor:

```python
from textual.widgets import TextArea

# Pass text at construction time (preferred)
# SOURCE: https://textual.textualize.io/widgets/text_area/ (accessed 2026-05-07)
text_area = TextArea("Initial content")

# Or set via reactive attribute after construction
text_area.text = "Updated content"

# For code editing with syntax highlighting (requires pip install "textual[syntax]"):
code_editor = TextArea.code_editor("print('hello')", language="python")

# Get content
content = text_area.text
```

### Switch

Toggle switch (like checkbox):

```python
from textual.widgets import Switch

yield Switch(value=True)  # Initially on


def on_switch_changed(self, event: Switch.Changed) -> None:
    is_on = event.value
    self.toggle_feature(is_on)
```

## Data Display

### DataTable

Display tabular data:

```python
from textual.widgets import DataTable

table = DataTable()

# Add columns
table.add_columns("Name", "Age", "Country")

# Add rows
table.add_row("Alice", 30, "USA")
table.add_row("Bob", 25, "UK")

# Add row with custom label
from rich.text import Text

label = Text("1", style="bold cyan")
table.add_row("Charlie", 35, "Canada", label=label)

# Configuration
table.zebra_stripes = True  # Alternating row colors
table.cursor_type = "row"  # "cell", "row", "column", or "none"
table.show_header = True
table.show_row_labels = True


# Handle selection
def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
    row_key = event.row_key
    row_data = table.get_row(row_key)


def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
    value = event.value
    coordinate = event.coordinate
```

## Layout Containers

### Container

Generic container for grouping widgets:

```python
from textual.containers import Container

with Container(id="sidebar"):
    yield Label("Title")
    yield Button("Action")
```

### Vertical / Horizontal / VerticalScroll / HorizontalScroll

Directional containers:

```python
from textual.containers import Vertical, Horizontal, VerticalScroll

with Horizontal():
    yield Button("Left")
    yield Button("Right")

with VerticalScroll():
    for i in range(100):
        yield Label(f"Item {i}")
```

### Grid

Grid layout container:

```python
from textual.containers import Grid

with Grid(id="my-grid"):
    yield Label("A")
    yield Label("B")
    yield Label("C")
    yield Label("D")

# Style in CSS:
# Grid {
#     grid-size: 2 2;  /* 2 columns, 2 rows */
# }
```

## App Widgets

### Header / Footer

Standard app chrome:

```python
from textual.widgets import Header, Footer


def compose(self) -> ComposeResult:
    yield Header()
    # ... content ...
    yield Footer()
```

Footer automatically shows key bindings defined in BINDINGS.

## Custom Widgets

Create reusable components:

```python
from textual.widget import Widget
from textual.widgets import Label, Button


class Card(Widget):
    """A card widget with title and content."""

    DEFAULT_CSS = """
    Card {
        width: 30;
        height: 15;
        border: round white;
        padding: 1;
    }
    """

    def __init__(self, title: str, content: str) -> None:
        super().__init__()
        self.title = title
        self.content = content

    def compose(self) -> ComposeResult:
        yield Label(self.title, classes="card-title")
        yield Label(self.content, classes="card-content")
        yield Button("Select", id=f"select-{self.title}")
```

### Render Method

For simple custom widgets that just render text:

```python
from textual.widget import Widget


class FizzBuzz(Widget):
    def render(self) -> str:
        return "FizzBuzz!"
```
