# Console and Markup

Everything needed to use the `Console` class, print styled output, apply markup tags, define styles, and use color. This is the foundation for all Rich output.

## Table of Contents

1. [Installation](#installation)
2. [Console Class](#console-class)
3. [Console Constructor Parameters](#console-constructor-parameters)
4. [Printing Methods](#printing-methods)
5. [Markup Syntax](#markup-syntax)
6. [Style Definitions](#style-definitions)
7. [Color Formats](#color-formats)
8. [Style Attributes](#style-attributes)
9. [Style Class](#style-class)
10. [Themes](#themes)
11. [Environment Variables](#environment-variables)
12. [Output Capture and Export](#output-capture-and-export)

---

## Installation

```bash
pip install rich
```

For Jupyter support:

```bash
pip install "rich[jupyter]"
```

Verify installation:

```bash
python -m rich
```

Drop-in replacement for `print`:

```python
from rich import print
print("[italic red]Hello[/italic red] World!", locals())
```

---

## Console Class

`Console` is the primary interface for Rich output. Most applications use a single instance.

```python
from rich.console import Console
console = Console()
```

Console auto-detects terminal capabilities and converts colors as needed.

Console attributes:

- `console.size` — current terminal dimensions (updates on resize)
- `console.encoding` — default encoding, typically `"utf-8"`
- `console.is_terminal` — `True` if writing to a terminal
- `console.color_system` — active color system string

---

## Console Constructor Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `color_system` | str or None | `"auto"` | Color system: `None`, `"auto"`, `"standard"`, `"256"`, `"truecolor"`, `"windows"` |
| `style` | str | `None` | Style applied to all output |
| `width` | int | auto-detect | Console width in characters |
| `height` | int | auto-detect | Console height in characters |
| `stderr` | bool | `False` | Write to `sys.stderr` instead of `sys.stdout` |
| `file` | file-like | `sys.stdout` | Output file object |
| `record` | bool | `False` | Record output for export |
| `force_terminal` | bool | `False` | Force terminal mode even when not a TTY |
| `force_interactive` | bool | `None` | Override interactive mode detection |
| `markup` | bool | `True` | Enable markup parsing globally |
| `highlight` | bool | `True` | Enable automatic syntax highlighting |
| `theme` | Theme | None | Custom Theme instance |
| `soft_wrap` | bool | `False` | Disable word wrapping |

```python
# Error console writing to stderr in bold red
error_console = Console(stderr=True, style="bold red")

# File output console
with open("report.txt", "wt") as f:
    console = Console(file=f, width=120)
```

WARNING: Setting `color_system` higher than your terminal supports makes text unreadable.

---

## Printing Methods

### `console.print(*objects, sep, end, style, justify, overflow, no_wrap, emoji, markup, highlight, width, crop, soft_wrap, new_line_start)`

Renders and prints objects. Strings are parsed as markup. Containers are pretty-printed.

```python
console.print([1, 2, 3])
console.print("[blue underline]Looks like a link")
console.print(locals())
console.print("FOO", style="white on blue")
console.print("Rich", style="bold white on blue", justify="center")
```

`justify` accepts: `"default"`, `"left"`, `"right"`, `"center"`, `"full"`

`overflow` accepts: `"fold"` (default), `"crop"`, `"ellipsis"`, `"ignore"`

### `console.log(*objects, log_locals, **kwargs)`

Same as `print` but adds timestamp column (left) and file/line column (right). Useful for debugging.

```python
console.log("Hello, World!")
console.log("Locals:", log_locals=True)  # displays local variable table
```

### `console.out(*objects, style, highlight)`

Low-level output: no markup, no word wrap, no pretty print. Converts all args to strings.

```python
console.out("Locals", locals())
```

### `console.rule(title, align, style, characters)`

Draws a horizontal line with optional title.

```python
console.rule("[bold red]Chapter 2")
console.rule("Section", align="left", style="green")
```

`align` accepts: `"left"`, `"center"` (default), `"right"`

### `console.print_json(json_str)`

Pretty-prints a JSON string with syntax highlighting.

```python
console.print_json('[false, true, null, "foo"]')
```

### `console.print_exception(show_locals, width, extra_lines, max_frames)`

Prints the current exception with Rich formatting.

```python
try:
    do_something()
except Exception:
    console.print_exception(show_locals=True)
```

### `console.status(status, spinner, spinner_style, speed, refresh_per_second)`

Context manager displaying a spinner animation during a block.

```python
with console.status("Working..."):
    do_work()

with console.status("Monkeying around...", spinner="monkey"):
    do_work()
```

Run `python -m rich.spinner` to see available spinner names.

### `console.input(prompt)`

Prompts for input. Prompt accepts Rich markup.

```python
name = console.input("What is [i]your[/i] [bold red]name[/]? :smiley: ")
```

### `console.capture()`

Context manager that captures output as a string instead of printing.

```python
with console.capture() as capture:
    console.print("[bold red]Hello[/] World")
str_output = capture.get()
```

Alternative for unit tests:

```python
from io import StringIO
console = Console(file=StringIO())
console.print("[bold red]Hello[/] World")
str_output = console.file.getvalue()
```

---

## Markup Syntax

Rich markup uses BBCode-style square bracket tags.

```python
from rich import print

# Open and close a style
print("[bold red]alert![/bold red] Something happened")

# Shorthand close — closes the last open tag
print("[bold red]Bold and red[/] not bold or red")

# Unclosed tag applies to end of string
print("[bold italic yellow on red blink]This text is impossible to read")

# Overlapping tags (supported)
print("[bold]Bold[italic] bold and italic [/bold]italic[/italic]")
```

### Links in markup

```python
print("Visit my [link=https://www.willmcgugan.com]blog[/link]!")
```

### Emoji codes

```python
print(":warning:")          # ⚠️
print(":red_heart-emoji:")  # full-color variant
print(":red_heart-text:")   # monochrome variant
```

Run `python -m rich.emoji` to list all emoji codes.

### Escaping markup

```python
from rich.markup import escape

# Backslash escapes a bracket
print(r"foo\[bar]")   # prints: foo[bar]

# Escape user-supplied strings to prevent injection
def greet(name):
    console.print(f"Hello {escape(name)}!")
```

`rich.markup.MarkupError` is raised for mismatched tags like `"[bold]Hello[/red]"`.

### Disabling markup

```python
console.print("[not markup]", markup=False)
console = Console(markup=False)  # disable globally
```

---

## Style Definitions

A style definition is a string containing colors and/or attributes.

```python
console.print("Hello", style="magenta")
console.print("DANGER!", style="red on white")
console.print("Danger, Will Robinson!", style="blink bold red underline on white")
```

Background color uses `on` prefix:

```python
console.print("text", style="white on blue")
console.print("text", style="default on default")  # terminal defaults
```

Negate an attribute with `not`:

```python
console.print("foo [not bold]bar[/not bold] baz", style="bold")
```

---

## Color Formats

| Format | Example | Notes |
|--------|---------|-------|
| Named color | `"magenta"` | See appendix/colors for full list |
| 256-color number | `"color(5)"` | Integer 0–255 |
| Hex RGB | `"#af00ff"` | CSS-style 6-digit hex |
| RGB decimal | `"rgb(175,0,255)"` | Three decimal integers |

```python
console.print("Hello", style="magenta")
console.print("Hello", style="color(5)")
console.print("Hello", style="#af00ff")
console.print("Hello", style="rgb(175,0,255)")
```

NOTE: Some terminals only support 256 colors. Rich picks the closest available color.

---

## Style Attributes

| Attribute | Shorthand | Notes |
|-----------|-----------|-------|
| `bold` | `b` | Bold text |
| `italic` | `i` | Italic (not supported on Windows) |
| `underline` | `u` | Underlined text |
| `strike` | `s` | Strikethrough |
| `reverse` | `r` | Foreground and background reversed |
| `blink` | — | Flashing text (use sparingly) |
| `blink2` | — | Rapid flash (poorly supported) |
| `dim` | — | Dimmed text |
| `conceal` | — | Hidden text (poorly supported) |
| `underline2` | `uu` | Double underline (poorly supported) |
| `overline` | `o` | Overlined text (poorly supported) |
| `frame` | — | Framed text (poorly supported) |
| `encircle` | — | Encircled text (poorly supported) |

Link as attribute:

```python
console.print("Google", style="link https://google.com")
```

---

## Style Class

```python
from rich.style import Style

danger_style = Style(color="red", blink=True, bold=True)
console.print("Danger, Will Robinson!", style=danger_style)

# Combine styles with +
base_style = Style.parse("cyan")
console.print("Hello, World", style=base_style + Style(underline=True))

# Parse from definition string
style = Style.parse("italic magenta on yellow")
```

Rich caches parsed style definitions — first call has a small parsing cost, subsequent calls are free.

---

## Themes

```python
from rich.console import Console
from rich.theme import Theme

custom_theme = Theme({
    "info": "dim cyan",
    "warning": "magenta",
    "danger": "bold red"
})
console = Console(theme=custom_theme)
console.print("This is information", style="info")
console.print("[warning]The pod bay doors are locked[/warning]")
console.print("Something terrible happened!", style="danger")
```

Style names must be lowercase, start with a letter, and contain only letters, `"."`, `"-"`, `"_"`.

Theme overrides default Rich styles when names match. Set `inherit=False` to disable inheritance.

Load from config file:

```python
theme = Theme.read("mytheme.cfg")
```

Config file format:

```text
[styles]
info = dim cyan
warning = magenta
danger = bold red
```

Run `python -m rich.theme` and `python -m rich.default_styles` to see defaults.

---

## Environment Variables

| Variable | Effect |
|----------|--------|
| `TERM=dumb` or `TERM=unknown` | Disables color/style and cursor movement features |
| `FORCE_COLOR=1` | Forces color/style regardless of `TERM` |
| `NO_COLOR` (any non-empty value) | Disables all color (takes precedence over `FORCE_COLOR`) |
| `TTY_COMPATIBLE=1` | Forces Rich to assume terminal escape sequence support |
| `TTY_COMPATIBLE=0` | Forces Rich to assume non-terminal output |
| `TTY_INTERACTIVE=0` | Disables interactive mode (animations) |
| `TTY_INTERACTIVE=1` | Forces interactive mode on |
| `COLUMNS` | Sets console width |
| `LINES` | Sets console height |

NOTE: `NO_COLOR` removes color only — bold, italic, underline etc. are preserved.

For CI/GitHub Actions: set `TTY_COMPATIBLE=1` and `TTY_INTERACTIVE=0`.

---

## Output Capture and Export

```python
# Enable recording
console = Console(record=True)
console.print("Hello!")

# Export as string
text = console.export_text()
html = console.export_html()
svg = console.export_svg()

# Save to disk
console.save_text("output.txt")
console.save_html("output.html")
console.save_svg("output.svg")

# Custom SVG theme
from rich.terminal_theme import MONOKAI
console.save_svg("output.svg", theme=MONOKAI)
```
