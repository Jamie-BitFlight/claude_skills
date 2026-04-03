# Renderables

Constructor signatures, parameters, and usage patterns for all Rich renderable types: Panel, Table, Tree, Columns, Group, Padding, Rule, Align. These objects can be passed to `console.print()` or nested inside each other.

## Table of Contents

1. [Panel](#panel)
2. [Table](#table)
3. [Table Constructor Options](#table-constructor-options)
4. [Column Options](#column-options)
5. [Table Grid Layout](#table-grid-layout)
6. [Tree](#tree)
7. [Columns](#columns)
8. [Padding](#padding)
9. [Rule](#rule)
10. [Align](#align)
11. [Box Styles](#box-styles)

---

## Panel

Draws a border around any renderable.

```python
from rich import print
from rich.panel import Panel

# Basic panel — expands to full terminal width
print(Panel("Hello, [red]World!"))

# Fit to content size
print(Panel.fit("Hello, [red]World!"))
print(Panel("Hello, [red]World!", expand=False))

# With title and subtitle
print(Panel("Hello, [red]World!", title="Welcome", subtitle="Thank you"))
```

Key Panel constructor parameters:

| Parameter | Description |
|-----------|-------------|
| `renderable` | Content to display inside the panel |
| `box` | Box style (import from `rich.box`); default is `box.ROUNDED` |
| `title` | Text drawn on top border |
| `subtitle` | Text drawn on bottom border |
| `title_align` | `"left"`, `"center"` (default), `"right"` |
| `subtitle_align` | `"left"`, `"center"`, `"right"` |
| `style` | Style applied to panel border |
| `expand` | `True` (default) expands to full width; `False` fits content |
| `padding` | Padding inside the panel |
| `width` | Explicit width |
| `height` | Explicit height |

---

## Table

```python
from rich.console import Console
from rich.table import Table

table = Table(title="Star Wars Movies")

table.add_column("Released", justify="right", style="cyan", no_wrap=True)
table.add_column("Title", style="magenta")
table.add_column("Box Office", justify="right", style="green")

table.add_row("Dec 20, 2019", "Star Wars: The Rise of Skywalker", "$952,110,690")
table.add_row("May 25, 2018", "Solo: A Star Wars Story", "$393,151,347")

console = Console()
console.print(table)
```

Rich auto-calculates optimal column widths and wraps text to fit terminal width.

`add_row` accepts any Rich renderable — not just strings.

Short form — column names as positional args:

```python
table = Table("Released", "Title", "Box Office", title="Star Wars Movies")
```

Column with custom options via `Column` class:

```python
from rich.table import Column, Table

table = Table(
    "Released",
    "Title",
    Column(header="Box Office", justify="right"),
    title="Star Wars Movies"
)
```

Row with section break:

```python
table.add_row("value1", "value2", end_section=True)
# or
table.add_section()
```

Check before printing empty table:

```python
if table.columns:
    console.print(table)
else:
    console.print("[i]No data...[/i]")
```

---

## Table Constructor Options

| Parameter | Description |
|-----------|-------------|
| `title` | Text shown above the table |
| `caption` | Text shown below the table |
| `width` | Fixed width (disables auto-calculation) |
| `min_width` | Minimum table width |
| `box` | Box style from `rich.box`; `None` removes borders |
| `safe_box` | `True` forces ASCII characters instead of unicode |
| `padding` | int or tuple (1, 2, or 4 values) for cell padding |
| `collapse_padding` | `True` merges padding of neighboring cells |
| `pad_edge` | `False` removes padding around table edges |
| `expand` | `True` expands table to full available width |
| `show_header` | `True` (default) shows header row |
| `show_footer` | `True` shows footer row |
| `show_edge` | `False` removes outer border |
| `show_lines` | `True` shows lines between all rows |
| `leading` | Additional space between rows |
| `style` | Style applied to entire table |
| `row_styles` | List of styles for alternating rows, e.g. `["dim", ""]` for zebra stripes |
| `header_style` | Default style for header row |
| `footer_style` | Default style for footer row |
| `border_style` | Style for border characters |
| `title_style` | Style for the title |
| `caption_style` | Style for the caption |
| `title_justify` | `"left"`, `"right"`, `"center"` (default), `"full"` |
| `caption_justify` | `"left"`, `"right"`, `"center"`, `"full"` |
| `highlight` | `True` enables automatic cell content highlighting |

---

## Column Options

Passed to `table.add_column()` or `Column()` constructor:

| Parameter | Description |
|-----------|-------------|
| `header` | Column header text |
| `header_style` | Style for the header cell |
| `footer` | Footer text for this column |
| `footer_style` | Style for the footer cell |
| `style` | Style applied to all column cells |
| `justify` | `"left"`, `"center"`, `"right"`, `"full"` |
| `vertical` | `"top"`, `"middle"`, `"bottom"` — vertical cell alignment |
| `width` | Fixed character width (disables auto-calculation) |
| `min_width` | Minimum character width |
| `max_width` | Maximum character width |
| `ratio` | Proportional width; e.g. `ratio=2` in a total of 6 gives 1/3 of space |
| `no_wrap` | `True` prevents text wrapping in this column |
| `highlight` | `True` enables automatic content highlighting |

Vertical alignment per cell using `Align`:

```python
from rich.align import Align
table.add_row(Align("Title", vertical="middle"))
```

---

## Table Grid Layout

`Table.grid()` creates a borderless, headerless table for layout purposes.

```python
from rich import print
from rich.table import Table

grid = Table.grid(expand=True)
grid.add_column()
grid.add_column(justify="right")
grid.add_row("Raising shields", "[bold magenta]COMPLETED [green]:heavy_check_mark:")
print(grid)
```

---

## Tree

```python
from rich.tree import Tree
from rich import print

tree = Tree("Rich Tree")
tree.add("foo")
tree.add("bar")

# Nested branches — add() returns a new Tree instance
baz_tree = tree.add("baz")
baz_tree.add("[red]Red").add("[green]Green").add("[blue]Blue")

print(tree)
```

`Tree.add(label, style, guide_style, highlight)` returns a new `Tree` instance for the added branch.

Tree style parameters:

| Parameter | Description |
|-----------|-------------|
| `label` | Branch label — string or any renderable |
| `style` | Style for the entire branch (inherited by sub-trees) |
| `guide_style` | Style for guide lines (inherited); `bold` uses thicker unicode lines; `underline2` uses double-line unicode |
| `highlight` | `True` enables automatic label highlighting |

---

## Columns

Displays renderables in a grid of columns, similar to `ls` terminal output.

```python
from rich.columns import Columns
from rich import print

data = ["one", "two", "three", "four", "five", "six"]
print(Columns(data))
```

Key Columns constructor parameters:

| Parameter | Description |
|-----------|-------------|
| `renderables` | Iterable of renderables to display |
| `padding` | Padding around each item (default `(0, 1)`) |
| `expand` | `True` expands to full terminal width |
| `equal` | `True` forces all columns to equal width |
| `column_first` | `True` fills columns top-to-bottom instead of left-to-right |
| `right_to_left` | `True` reverses column order |
| `align` | `"left"`, `"center"`, `"right"` — alignment within each cell |
| `title` | Optional title above the columns |

---

## Padding

Adds whitespace padding around a renderable.

```python
from rich.padding import Padding
from rich import print

print(Padding("Hello", (1, 2)))          # 1 top/bottom, 2 left/right
print(Padding("Hello", (1, 2, 3, 4)))   # top, right, bottom, left (CSS order)
print(Padding("Hello", 1))              # 1 on all sides
```

`Padding(renderable, pad)` where `pad` is:

- `int` — same padding on all sides
- 2-tuple `(top_bottom, left_right)`
- 4-tuple `(top, right, bottom, left)` in CSS order

---

## Rule

Draws a horizontal rule (dividing line) with optional title. Also available as `console.rule()`.

```python
from rich.rule import Rule
from rich import print

print(Rule("Section Title"))
print(Rule(style="red"))
print(Rule("Title", align="left"))
```

| Parameter | Description |
|-----------|-------------|
| `title` | Optional title text in the center of the rule |
| `characters` | Characters to use for the line (default `"─"`) |
| `style` | Style for the line |
| `align` | `"left"`, `"center"` (default), `"right"` |

---

## Align

Wraps a renderable to align it within its available space.

```python
from rich.align import Align
from rich import print

print(Align("Hello, World!", align="center"))
print(Align("Hello, World!", align="right"))
print(Align("Hello", vertical="middle"))
```

| Parameter | Description |
|-----------|-------------|
| `renderable` | Renderable to align |
| `align` | `"left"`, `"center"`, `"right"` — horizontal alignment |
| `vertical` | `"top"`, `"middle"`, `"bottom"` — vertical alignment |
| `style` | Style applied to padding space |
| `pad` | `True` (default) pads to fill available width |
| `width` | Explicit width |
| `height` | Explicit height |

Class methods:

```python
Align.center(renderable, vertical="middle")
Align.left(renderable)
Align.right(renderable)
```

---

## Box Styles

Import box styles from `rich.box`:

```python
from rich import box
from rich.table import Table

table = Table(box=box.MINIMAL_DOUBLE_HEAD)
table = Table(box=box.SIMPLE)
table = Table(box=None)  # no borders
```

Common box constants (from `rich.box`):

```text
ASCII           ASCII2          ASCII_DOUBLE_HEAD
SQUARE          SQUARE_DOUBLE_HEAD  MINIMAL
MINIMAL_HEAVY_HEAD  MINIMAL_DOUBLE_HEAD  SIMPLE
SIMPLE_HEAD     SIMPLE_HEAVY    HORIZONTALS
ROUNDED         HEAVY           HEAVY_EDGE
HEAVY_HEAD      DOUBLE          DOUBLE_EDGE
MARKDOWN
```

Run `python -m rich.box` to see all box styles rendered.
