# Rich Gaps — Patterns Not Covered in render-patterns.md and rich-extras.md

Advanced and safety-critical Rich patterns identified as missing from the existing
designing-ui-for-cli reference files. All code verified against official Rich docs
and local authoritative sources.

SOURCE: <https://rich.readthedocs.io/en/stable/console.html> (accessed 2026-05-07)
SOURCE: <https://rich.readthedocs.io/en/stable/tables.html> (accessed 2026-05-07)
SOURCE: <https://rich.readthedocs.io/en/stable/progress.html> (accessed 2026-05-07)
SOURCE: <https://rich.readthedocs.io/en/stable/panel.html> (accessed 2026-05-07)
SOURCE: <https://rich.readthedocs.io/en/stable/tree.html> (accessed 2026-05-07)
SOURCE: <https://rich.readthedocs.io/en/stable/syntax.html> (accessed 2026-05-07)
SOURCE: <https://rich.readthedocs.io/en/stable/markup.html> (accessed 2026-05-07)
SOURCE: `plugins/python-engineering/skills/python3-cli/references/typer-rich-non-tty-patterns.md`

---

## Non-TTY and Pipe Safety

### Terminal Detection

Rich auto-detects terminal capability. `console.is_terminal` is `False` when stdout is piped,
redirected, or not a TTY. When `is_terminal` is `False`, Rich strips ANSI escape codes from
output automatically — no code needed to get clean pipe output.

```python
from rich.console import Console

console = Console()

# Gate interactive features on TTY detection
if console.is_terminal:
    with console.status("Working..."):
        do_work()
else:
    print("Working...")  # plain output for pipes/logs
```

### `force_terminal=True` — Preserve Colour in CI

Use when the output destination supports colour (e.g., GitHub Actions, terminal pager) but
Rich detects no TTY:

```python
# Force ANSI codes even when stdout is piped
console = Console(force_terminal=True)
```

Do not use for output that will be stored as plain text (log files, database fields).

### `width` Parameter — Control Wrapping Without Affecting Colour

```python
# Explicit width prevents wrapping based on the caller's terminal width
console = Console(width=120)

# Both: emit colour AND fix wrapping width
console = Console(force_terminal=True, width=120)
```

Width and colour emission are independent. Setting `width` does not enable or disable colour.

SOURCE: <https://rich.readthedocs.io/en/stable/console.html> — "Terminal detection" section
(accessed 2026-05-07)

---

## Markup Injection — `escape()` for User-Controlled Content

Rich markup is parsed by default in every `console.print()` call. If user-supplied data
contains square brackets (e.g., a task title `[URGENT] Deploy`), it is parsed as markup and
can produce garbled output or silently drop the bracketed text.

**Always escape user-controlled strings before passing to `console.print()`:**

```python
from rich.markup import escape

# Safe — escape() converts [ to \[ so Rich renders it literally
console.print(f"Task: {escape(task_title)}")

# In table rows — escape any column that holds user data
from rich.table import Table

table = Table()
table.add_column("Title")
table.add_column("Notes")

for task in tasks:
    table.add_row(
        escape(task["title"]),  # user-supplied — must escape
        escape(task["notes"]),  # user-supplied — must escape
    )
```

Alternatively, use `Text` objects which do not parse markup:

```python
from rich.text import Text

table.add_row(Text(task["title"]))  # no markup parsing
```

SOURCE: <https://rich.readthedocs.io/en/stable/markup.html> — "Escaping" section (accessed 2026-05-07)

---

## `console.pager()` — Long Output Pagination

`console.pager()` sends output to the system pager (`less`, `more`) when content is long.
Use for task lists, logs, or any output that may not fit in one screen.

```python
def show_all_tasks(tasks: list) -> None:
    """Display a potentially long task list with paging."""
    table = render_task_table(tasks)
    with console.pager(styles=True):
        console.print(table)
```

`styles=True` passes ANSI codes to the pager (supported by `less -R`). Without it, the pager
receives plain text.

SOURCE: <https://rich.readthedocs.io/en/stable/console.html> — "Paging" section (accessed 2026-05-07)

---

## `console.rule()` — Lightweight Section Separator

`console.rule(title, style, align)` draws a horizontal line with an optional centred title.
Lighter-weight than a `Panel` for separating sequential output sections.

```python
console.rule("[bold cyan]Results", style="cyan")
console.print(table)
console.rule()  # plain divider — no title
```

`align` accepts `"left"`, `"center"` (default), or `"right"`.

SOURCE: <https://rich.readthedocs.io/en/stable/console.html> — "Rules" section (accessed 2026-05-07)

---

## `console.screen()` — Alternate Screen for Dashboard Display

`console.screen()` switches the terminal to alternate screen mode (the same mechanism used by
`vim` and `less`). Output is displayed full-screen and the shell history is left clean on exit.

```python
import time

with console.screen():
    console.print(build_dashboard_layout())
    time.sleep(5)
# Terminal returns to normal state here — no scroll pollution
```

Marked experimental in official docs. Use `rich.Live` for continuously-updating dashboards;
use `console.screen()` for static full-screen display.

SOURCE: <https://rich.readthedocs.io/en/stable/console.html> — "Alternate screen" section
(accessed 2026-05-07)

---

## `Table.grid()` — Borderless Two-Column Layout

`Table.grid()` creates a borderless, headerless table for aligning content without visible
borders. The standard pattern for status lines, key-value pairs, and label-with-value layouts.

```python
from rich.table import Table


def render_status_line(label: str, value: str, value_style: str = "bold") -> None:
    """Render a label-value pair: label on left, value on right."""
    grid = Table.grid(expand=True)
    grid.add_column()
    grid.add_column(justify="right")
    grid.add_row(label, f"[{value_style}]{value}[/]")
    console.print(grid)


render_status_line("Tasks completed", "12 of 50", value_style="bold green")
render_status_line("Last synced", "2 minutes ago", value_style="dim")
```

`expand=True` stretches the grid to full console width, pushing the right column to the right
edge. Without `expand=True`, the grid collapses to its content width.

SOURCE: <https://rich.readthedocs.io/en/stable/tables.html> — "Grids" section (accessed 2026-05-07)

---

## `MofNCompleteColumn` — Integer Progress Display

`MofNCompleteColumn` displays progress as "M/N" (e.g., "12/50") rather than a percentage.
Best when completed and total are integers and the user cares about counts, not fractions.

```python
from rich.progress import Progress, BarColumn, TextColumn, MofNCompleteColumn


def process_files(items: list, description: str = "Processing") -> None:
    with Progress(
        TextColumn("[bold blue]{task.description}"), BarColumn(), MofNCompleteColumn(), transient=True
    ) as progress:
        task = progress.add_task(description, total=len(items))
        for item in items:
            process(item)
            progress.update(task, advance=1)
```

SOURCE: <https://rich.readthedocs.io/en/stable/progress.html> — column objects list, MofNCompleteColumn
(accessed 2026-05-07)

---

## `Progress.get_default_columns()` — Extension Pattern

Use `get_default_columns()` to extend the default progress bar column set rather than
replacing it from scratch. Avoids losing the standard percentage/bar/ETA display when adding
a spinner or elapsed time column.

```python
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn

progress = Progress(
    SpinnerColumn(),
    *Progress.get_default_columns(),  # bar + percentage + time remaining
    TimeElapsedColumn(),
)
```

SOURCE: <https://rich.readthedocs.io/en/stable/progress.html> — "Columns" section (accessed 2026-05-07)

---

## Panel `subtitle` Parameter

`Panel` accepts a `subtitle` argument that draws text on the bottom border. Use for footer
hints, timestamps, or keyboard shortcut reminders without an extra `console.print()` call.

```python
from rich.panel import Panel

Panel(
    content,
    title="[bold]Task #42[/bold]",
    subtitle="[dim]Press Enter to continue[/dim]",
    border_style="bright_blue",
    padding=(1, 2),
)
```

`subtitle` accepts the same markup strings as `title`.

SOURCE: <https://rich.readthedocs.io/en/stable/panel.html> (accessed 2026-05-07)

---

## `Tree` `guide_style` — Visual Hierarchy

`Tree(label, guide_style=...)` controls the weight of the guide lines connecting tree branches.
Thicker or doubled lines communicate depth hierarchy more clearly.

```python
from rich.tree import Tree

# Bold (thick) guide lines — good for deep trees
tree = Tree("[bold blue]MyProject/[/]", guide_style="bold")

# Double lines
tree = Tree("[bold blue]MyProject/[/]", guide_style="underline2")
```

SOURCE: <https://rich.readthedocs.io/en/stable/tree.html> — "Tree Styles" section (accessed 2026-05-07)

---

## `Syntax` `highlight_lines` — Point to Error Lines

`highlight_lines` accepts a set of line numbers to visually highlight. Use when displaying
config files or scripts with errors — highlights the problem line so the user does not scan
the entire file.

```python
from rich.syntax import Syntax

syntax = Syntax(
    code,
    "python",
    line_numbers=True,
    highlight_lines={12, 13},  # visually emphasise these lines
    theme="monokai",
)
console.print(syntax)
```

SOURCE: <https://rich.readthedocs.io/en/stable/syntax.html> — "Line numbers" section (accessed 2026-05-07)

---

## `Table` `row_styles` — Zebra Striping

`Table(row_styles=["dim", ""])` alternates row styling automatically. An alternative to
`show_lines=True` that improves scannability without border clutter.

```python
from rich.table import Table
from rich.box import ROUNDED

table = Table(
    box=ROUNDED,
    row_styles=["dim", ""],  # alternating dim/normal rows
    show_lines=False,  # no per-row borders needed with zebra
)
```

SOURCE: <https://rich.readthedocs.io/en/stable/tables.html> — Table Options, `row_styles`
(accessed 2026-05-07)

---

## PyFiglet Patterns

Patterns for the `pyfiglet` library. Verified against pyfiglet 1.0.4 via runtime inspection
(2026-05-07).

SOURCE: <https://pypi.org/project/pyfiglet/> (accessed 2026-05-07)
SOURCE: <https://github.com/pwaller/pyfiglet> (accessed 2026-05-07)
SOURCE: Runtime inspection of pyfiglet 1.0.4 `__init__.py` (2026-05-07)

### Exception Hierarchy — Always Catch Specifically

Never use bare `except:` with pyfiglet. The exception hierarchy:

```
Exception
  FigletError
    FontNotFound    — font name not found in bundled or custom font paths
    FontError       — font file parse failure
    CharNotPrinted  — terminal width too narrow to render a character
    InvalidColor    — invalid color specification to print_figlet
```

Always catch the specific exception:

```python
def generate_banner(text: str, font: str = "slant") -> str:
    """Generate ASCII banner with fallback to 'standard' font."""
    try:
        return pyfiglet.figlet_format(text, font=font)
    except pyfiglet.FontNotFound:
        return pyfiglet.figlet_format(text, font="standard")
```

A bare `except:` catches `KeyboardInterrupt` and `SystemExit`, preventing clean program exit.

### Font Name Case Sensitivity

Font names are case-sensitive on case-sensitive filesystems. `banner3-D` requires capital `D`:

```python
pyfiglet.figlet_format("Hello", font="banner3-D")  # correct
pyfiglet.figlet_format("Hello", font="banner3-d")  # raises FontNotFound
```

Use `pyfiglet.FigletFont.getFonts()` to get the authoritative list of bundled font names.
pyfiglet 1.0.4 ships 571 bundled fonts.

```python
# List all bundled fonts
all_fonts = pyfiglet.FigletFont.getFonts()

# Filter by substring
cyber_fonts = [f for f in all_fonts if "cyber" in f]
# ['cyberlarge', 'cybermedium', 'cybersmall']
```

Note: `pyfiglet.get_fonts()` does not exist. Use `pyfiglet.FigletFont.getFonts()` (class method)
or `pyfiglet.Figlet().getFonts()` (instance method). Both return the same list.

### `Figlet` Class for Repeated Rendering

Use the `Figlet` class when rendering multiple strings with the same font. `figlet_format()`
re-parses the font file on every call; `Figlet` parses once and reuses:

```python
import pyfiglet
import shutil

terminal_width = shutil.get_terminal_size().columns
f = pyfiglet.Figlet(font="slant", width=terminal_width, justify="center")

header = f.renderText("Welcome")
footer = f.renderText("Done")

# Change font in place — no new instance needed
f.setFont(font="doom")
error_banner = f.renderText("Error")
```

`Figlet.__init__` signature: `(font='standard', direction='auto', justify='auto', width=80)`

### `width` Parameter with `shutil.get_terminal_size()`

The `width` parameter controls line wrapping. Default is 80. Set to the actual terminal width
to avoid premature wrapping:

```python
import shutil
import pyfiglet

terminal_width = shutil.get_terminal_size().columns
banner = pyfiglet.figlet_format("Hello", font="slant", width=terminal_width)
```

### `justify` Parameter

Valid values: `'auto'` (default, follows font direction), `'left'`, `'center'`, `'right'`.

```python
pyfiglet.figlet_format("Hello", font="slant", justify="center")
```

### `direction` Parameter

Valid values: `'auto'` (default), `'left-to-right'`, `'right-to-left'`.

```python
pyfiglet.figlet_format("Hello", font="slant", direction="left-to-right")
```

### `pyfiglet.print_figlet()` — Native ANSI Colour

`print_figlet()` outputs coloured ASCII art to `sys.stdout` using ANSI escape codes directly.
The `colors` parameter uses `"FOREGROUND:BACKGROUND"` format:

```python
import pyfiglet

pyfiglet.print_figlet("Hello", font="slant", colors="CYAN:")  # cyan foreground
pyfiglet.print_figlet("Error", font="doom", colors="RED:BLACK")  # red on black
pyfiglet.print_figlet("Hello", font="slant", colors="255;128;0:")  # RGB orange foreground
```

Named colour values (case-insensitive after normalisation):
`BLACK`, `RED`, `GREEN`, `YELLOW`, `BLUE`, `MAGENTA`, `CYAN`, `WHITE`, `LIGHT_GRAY`,
`DARK_GRAY`, `LIGHT_RED`, `LIGHT_GREEN`, `LIGHT_YELLOW`, `LIGHT_BLUE`, `LIGHT_MAGENTA`,
`LIGHT_CYAN`, `DEFAULT`, `RESET`

**Rich integration caveat**: `print_figlet()` writes to `sys.stdout` directly and bypasses
Rich's `Console` markup system. When using Rich as the rendering layer, use `figlet_format()`
to get the string and apply colour via Rich:

```python
from rich.text import Text

logo_text = pyfiglet.figlet_format("MyApp", font="slant")
styled = Text(logo_text, style="bold cyan")
console.print(styled)
```

SOURCE: `inspect.getsource(pyfiglet.print_figlet)` + `pyfiglet.COLOR_CODES` dict — pyfiglet
1.0.4 (accessed 2026-05-07)

### Gotcha: `time.sleep()` Blocks Async Event Loops

`time.sleep()` is synchronous. In Textual (asyncio-based) apps or any async context, calling
`time.sleep()` blocks the entire event loop — no messages are processed, no widgets update,
and the terminal appears frozen.

**Plain CLI script (no async):** `time.sleep()` is correct.

**Textual async method — use `asyncio.sleep`:**

```python
import asyncio


async def on_mount(self) -> None:
    await asyncio.sleep(2.0)  # yields control to event loop
```

**Textual animation loop — use `@work` with `asyncio.sleep`:**

```python
from textual.worker import work


@work
async def animate_welcome(self) -> None:
    frames = ["🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘"]
    for _ in range(2):
        for frame in frames:
            self.query_one("#status").update(f"{frame} Loading...")
            await asyncio.sleep(0.1)
```

**Blocking code in thread worker (for synchronous libraries):**

```python
from textual.worker import work


@work(thread=True)
def heavy_sync_work(self) -> None:
    time.sleep(2)  # safe — runs in a thread, not the event loop
    result = compute_something()
    self.call_from_thread(self.update_result, result)
```

SOURCE: <https://textual.textualize.io/guide/workers/> (accessed 2026-05-07) — "blocking
operations in message handlers prevent UI responsiveness."
