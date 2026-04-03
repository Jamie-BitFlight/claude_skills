# Progress and Live

Progress bars, task tracking, and live-updating displays. Covers `track()`, `Progress`, `Live`, and `Status`.

## Table of Contents

1. [Basic Progress — track()](#basic-progress--track)
2. [Progress Class](#progress-class)
3. [Task Management](#task-management)
4. [Progress Columns](#progress-columns)
5. [Progress Constructor Options](#progress-constructor-options)
6. [Reading Files with Progress](#reading-files-with-progress)
7. [Nesting Progress Bars](#nesting-progress-bars)
8. [Live Display](#live-display)
9. [Live Constructor Options](#live-constructor-options)
10. [Status Spinner](#status-spinner)

---

## Basic Progress — track()

`track()` is the simplest way to add a progress bar to a loop.

```python
import time
from rich.progress import track

for i in track(range(20), description="Processing..."):
    time.sleep(1)  # work being done
```

`track(sequence, description, total, auto_refresh, console, transient, get_time, refresh_per_second, style, complete_style, finished_style, pulse_style, update_period, disable)` — yields values from `sequence` and updates the progress bar on each iteration.

NOTE: In Jupyter notebooks, auto-refresh is disabled. Use `refresh=True` when calling `update()`, or use `track()` which refreshes automatically.

---

## Progress Class

Use `Progress` directly when you need multiple tasks or custom columns.

```python
import time
from rich.progress import Progress

with Progress() as progress:
    task1 = progress.add_task("[red]Downloading...", total=1000)
    task2 = progress.add_task("[green]Processing...", total=1000)
    task3 = progress.add_task("[cyan]Cooking...", total=1000)

    while not progress.finished:
        progress.update(task1, advance=0.5)
        progress.update(task2, advance=0.3)
        progress.update(task3, advance=0.9)
        time.sleep(0.02)
```

`Progress` is a context manager. It starts and stops the display automatically.

Without context manager (use try/finally to guarantee `stop()`):

```python
progress = Progress()
progress.start()
try:
    task1 = progress.add_task("[red]Downloading...", total=1000)
    while not progress.finished:
        progress.update(task1, advance=0.5)
        time.sleep(0.02)
finally:
    progress.stop()
```

Print above the progress bar:

```python
with Progress() as progress:
    task = progress.add_task("twiddling thumbs", total=10)
    for job in range(10):
        progress.console.print(f"Working on job #{job}")
        run_job(job)
        progress.advance(task)
```

Pass an existing Console:

```python
with Progress(console=my_console) as progress:
    my_console.print("[bold blue]Starting work!")
    do_work(progress)
```

---

## Task Management

### `progress.add_task(description, start, total, completed, visible, **fields) -> TaskID`

Returns a `TaskID` integer used in subsequent `update()` calls.

| Parameter | Description |
|-----------|-------------|
| `description` | Text displayed in the description column (supports markup) |
| `start` | `True` (default) starts the timer immediately; `False` for indeterminate start |
| `total` | Number of steps for 100%; `None` for indeterminate (pulsing animation) |
| `completed` | Initial completed count (default `0`) |
| `visible` | `True` (default); `False` hides the task |

### `progress.update(task_id, total, completed, advance, description, visible, refresh, **fields)`

| Parameter | Description |
|-----------|-------------|
| `advance` | Add to current `completed` value |
| `completed` | Set `completed` directly |
| `total` | Update total steps |
| `description` | Update the task description |
| `visible` | Show or hide the task |
| `refresh` | `True` forces immediate refresh |
| `**fields` | Extra data stored in `task.fields`; accessible in column format strings |

### Indeterminate progress

```python
# Start with unknown total — shows pulsing animation
task = progress.add_task("Connecting...", start=False, total=None)
# Later, when total is known:
progress.start_task(task)
progress.update(task, total=100)
```

### Custom field in format string

```python
progress.update(task, extra="custom value")
# In column: "{task.fields[extra]}"
```

---

## Progress Columns

Default columns:

```python
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn

progress = Progress(
    TextColumn("[progress.description]{task.description}"),
    BarColumn(),
    TaskProgressColumn(),
    TimeRemainingColumn(),
)
```

Extend defaults with additional columns:

```python
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn

progress = Progress(
    SpinnerColumn(),
    *Progress.get_default_columns(),
    TimeElapsedColumn(),
)
```

Available column classes:

| Class | Description |
|-------|-------------|
| `BarColumn` | Progress bar graphic |
| `TextColumn` | Text using format string with `{task.*}` |
| `TimeElapsedColumn` | Time elapsed since task start |
| `TimeRemainingColumn` | Estimated time remaining |
| `TaskProgressColumn` | Percentage complete |
| `MofNCompleteColumn` | `"M/N"` completed/total (integers) |
| `FileSizeColumn` | Progress as file size (steps = bytes) |
| `TotalFileSizeColumn` | Total file size (steps = bytes) |
| `DownloadColumn` | Download progress (steps = bytes) |
| `TransferSpeedColumn` | Transfer speed (steps = bytes) |
| `SpinnerColumn` | Spinner animation |
| `RenderableColumn` | Any Rich renderable |

Custom column layout with ratio:

```python
from rich.table import Column
from rich.progress import Progress, BarColumn, TextColumn

text_column = TextColumn("{task.description}", table_column=Column(ratio=1))
bar_column = BarColumn(bar_width=None, table_column=Column(ratio=2))
progress = Progress(text_column, bar_column, expand=True)
```

Implement a custom column by extending `ProgressColumn`.

---

## Progress Constructor Options

| Parameter | Description |
|-----------|-------------|
| `*columns` | Column objects or format strings (positional args) |
| `console` | Use an existing Console instead of creating one |
| `auto_refresh` | `True` (default, 10 Hz) — set `False` to call `refresh()` manually |
| `refresh_per_second` | Refresh rate; default 10 |
| `transient` | `True` removes progress display on exit |
| `expand` | `True` stretches to full terminal width |
| `redirect_stdout` | `True` (default) redirects stdout to avoid breaking display |
| `redirect_stderr` | `True` (default) redirects stderr |

Transient progress:

```python
with Progress(transient=True) as progress:
    task = progress.add_task("Working", total=100)
    do_work(task)
```

Expand to full width:

```python
with Progress(expand=True) as progress:
    task = progress.add_task("Loading...", total=100)
```

---

## Reading Files with Progress

```python
import json
import rich.progress

# Open a file with automatic progress bar
with rich.progress.open("data.json", "rb") as file:
    data = json.load(file)

# Wrap an existing file object
from rich.progress import wrap_file
from urllib.request import urlopen

response = urlopen("https://example.com/file")
size = int(response.headers["Content-Length"])

with wrap_file(response, size) as file:
    for line in file:
        process(line)
```

---

## Nesting Progress Bars

Creating a `Progress` or using `track()` inside an existing progress context displays inner bars below the outer bar.

```python
from rich.progress import track
from time import sleep

for count in track(range(10)):
    for letter in track("ABCDEF", transient=True):
        print(f"Stage {count}{letter}")
        sleep(0.1)
    sleep(0.1)
```

Inner bar's refresh rate follows `refresh_per_second` of the outer bar.

Multiple Progress instances with different columns require a `Live` context. See `live_progress.py` example in the Rich repository.

---

## Live Display

`Live` enables continuously updating any renderable — not just progress bars.

```python
import time
from rich.live import Live
from rich.table import Table

table = Table()
table.add_column("Row ID")
table.add_column("Description")
table.add_column("Level")

with Live(table, refresh_per_second=4):
    for row in range(12):
        time.sleep(0.4)
        table.add_row(f"{row}", f"description {row}", "[red]ERROR")
```

Update the renderable on the fly:

```python
with Live(generate_table(), refresh_per_second=4) as live:
    for _ in range(40):
        time.sleep(0.4)
        live.update(generate_table())
```

Print above the live display:

```python
with Live(table, refresh_per_second=4) as live:
    for row in range(12):
        live.console.print(f"Working on row #{row}")
        time.sleep(0.4)
        table.add_row(...)
```

`vertical_overflow` options:

- `"ellipsis"` (default) — shows `...` when content exceeds terminal height
- `"crop"` — hides content beyond terminal height
- `"visible"` — allows full content (cannot be properly cleared)

---

## Live Constructor Options

| Parameter | Description |
|-----------|-------------|
| `renderable` | Initial renderable to display |
| `console` | Use an existing Console |
| `auto_refresh` | `True` (default, 4 Hz) |
| `refresh_per_second` | Refresh rate; default 4 |
| `transient` | `True` removes display on exit |
| `redirect_stdout` | `True` (default) redirects stdout |
| `redirect_stderr` | `True` (default) redirects stderr |
| `screen` | `True` uses alternate screen (full-screen mode) |
| `vertical_overflow` | `"ellipsis"` (default), `"crop"`, `"visible"` |

If `auto_refresh=False`, call `live.refresh()` manually or `live.update(renderable, refresh=True)`.

---

## Status Spinner

`console.status()` is a convenience wrapper around `Live` that shows a spinner.

```python
from rich.console import Console

console = Console()

with console.status("Working..."):
    do_work()

with console.status("Monkeying around...", spinner="monkey"):
    do_work()
```

Run `python -m rich.status` to see a demo. Run `python -m rich.spinner` to see all spinner names.
