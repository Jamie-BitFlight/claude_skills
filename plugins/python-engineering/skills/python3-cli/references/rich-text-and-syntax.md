# Text and Syntax

Programmatic text building with `Text`, code syntax highlighting with `Syntax`, Markdown rendering, and pretty printing with `pprint` / `Pretty`. Load when formatting code blocks, rendering markdown, or pretty-printing data structures.

## Table of Contents

1. [Text Class](#text-class)
2. [Syntax Highlighting](#syntax-highlighting)
3. [Markdown](#markdown)
4. [Pretty Printing](#pretty-printing)
5. [JSON Renderable](#json-renderable)

---

## Text Class

`Text` is the programmatic API for building styled text — use it when you need to apply styles to specific ranges or combine styled segments.

```python
from rich.text import Text

text = Text("Hello, World!")
text.stylize("bold magenta", 0, 6)  # apply style to range [0:6]
console.print(text)
```

### Constructing Text

```python
# From markup string
text = Text.from_markup("[bold]Hello[/bold] World")

# From ANSI escape sequences
text = Text.from_ansi("\033[1mHello\033[0m World")

# Build by appending
text = Text()
text.append("Hello", style="bold magenta")
text.append(" World")
console.print(text)
```

### Key Text Methods

| Method | Description |
|--------|-------------|
| `text.append(text, style)` | Append a string with an optional style |
| `text.append_text(text)` | Append another `Text` instance |
| `text.stylize(style, start, end)` | Apply style to a character range |
| `text.highlight_regex(re_highlight, style)` | Apply style to all regex matches |
| `text.highlight_words(words, style)` | Apply style to specific words |
| `text.assemble(*parts)` | Class method — build from `(text, style)` tuples |
| `text.copy()` | Return a copy |
| `text.join(lines)` | Join an iterable of Text with this Text as separator |
| `text.wrap(console, width)` | Returns lines wrapped to given width |
| `text.fit(width)` | Returns text truncated to width |
| `text.render(console)` | Yields `Segment` objects for rendering |

### Text Constructor Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `text` | `""` | Initial string |
| `style` | `""` | Base style applied to entire text |
| `justify` | `None` | `"left"`, `"center"`, `"right"`, `"full"` |
| `overflow` | `None` | `"fold"`, `"crop"`, `"ellipsis"`, `"ignore"` |
| `no_wrap` | `False` | Disable wrapping |
| `end` | `"\n"` | String appended after the text when rendering |
| `tab_size` | `None` | Tab size in spaces |
| `spans` | `[]` | Initial list of Span objects |

### assemble() class method

```python
text = Text.assemble(
    ("Hello", "bold magenta"),
    " ",
    ("World", "bold"),
)
console.print(text)
```

---

## Syntax Highlighting

`Syntax` renders source code with syntax highlighting using Pygments.

```python
from rich.console import Console
from rich.syntax import Syntax

console = Console()

# From string — specify lexer
with open("example.py", "rt") as code_file:
    syntax = Syntax(code_file.read(), "python")
console.print(syntax)

# From file — auto-detects language
syntax = Syntax.from_path("example.py")
console.print(syntax)
```

### Syntax Constructor Parameters

| Parameter | Description |
|-----------|-------------|
| `code` | Source code string |
| `lexer` | Language name string (e.g., `"python"`, `"javascript"`) |
| `theme` | Pygments theme name; or `"ansi_dark"` / `"ansi_light"` for terminal colors |
| `line_numbers` | `True` adds a line number column |
| `start_line` | Starting line number (default `1`) |
| `line_range` | `(start, end)` tuple to show a subset of lines |
| `highlight_lines` | Set of line numbers to highlight |
| `code_width` | Explicit width for the code portion |
| `word_wrap` | `True` enables word wrapping |
| `background_color` | Override theme background; `"default"` uses terminal background |
| `indent_guides` | `True` shows indent guide lines |
| `padding` | Padding around code |

### Syntax.from_path()

```python
syntax = Syntax.from_path("example.py", line_numbers=True, theme="monokai")
```

Auto-detects lexer from file extension.

### Line numbers and range

```python
syntax = Syntax.from_path("script.py", line_numbers=True)
syntax = Syntax("...", "python", line_numbers=True, line_range=(10, 30))
```

### CLI

```bash
python -m rich.syntax syntax.py
python -m rich.syntax -h  # see all options
```

---

## Markdown

Renders Markdown text in the terminal.

```python
from rich.console import Console
from rich.markdown import Markdown

console = Console()
with open("README.md") as readme:
    markdown = Markdown(readme.read())
console.print(markdown)
```

`Markdown` supports: headings, paragraphs, inline code, code blocks (with syntax highlighting), blockquotes, lists (ordered and unordered), horizontal rules, and links.

### Markdown Constructor Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `markup` | required | Markdown text string |
| `code_theme` | `"monokai"` | Pygments theme for code blocks |
| `justify` | `None` | Text justification |
| `style` | `"none"` | Base style |
| `hyperlinks` | `True` | Render hyperlinks |
| `inline_code_lexer` | `None` | Lexer for inline code |
| `inline_code_theme` | `None` | Theme for inline code |

---

## Pretty Printing

Rich's `pprint` and `Pretty` class format Python data structures with syntax highlighting, indent guides, and automatic width-fitting.

```python
from rich.pretty import pprint

pprint(locals())
```

### pprint Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `object` | required | Object to pretty print |
| `console` | `None` | Console to use |
| `indent_guides` | `True` | Show indent guide lines |
| `max_length` | `None` | Truncate containers beyond this many elements |
| `max_string` | `None` | Truncate strings beyond this many characters |
| `max_depth` | `None` | Max nesting depth |
| `expand_all` | `False` | `True` fully expands all data structures |

Truncation examples:

```python
pprint(locals(), max_length=2)       # truncate containers > 2 elements
pprint("long string", max_string=21) # truncate strings > 21 chars
pprint(data, expand_all=True)        # always expand everything
```

### Pretty Renderable

`Pretty` wraps any object for display inside other renderables.

```python
from rich import print
from rich.pretty import Pretty
from rich.panel import Panel

pretty = Pretty(locals())
panel = Panel(pretty)
print(panel)
```

### REPL Installation

```python
from rich import pretty
pretty.install()  # auto-pretty-prints all REPL output
```

### Rich Repr Protocol — `__rich_repr__`

Add to any class to control Rich's pretty display:

```python
class Bird:
    def __init__(self, name, eats=None, fly=True, extinct=False):
        self.name = name
        self.eats = list(eats) if eats else []
        self.fly = fly
        self.extinct = extinct

    def __rich_repr__(self):
        yield self.name               # positional argument
        yield "eats", self.eats       # keyword argument
        yield "fly", self.fly, True   # keyword; only shown if not equal to default
        yield "extinct", self.extinct, False

    # Optional: angular bracket style
    __rich_repr__.angular = True
```

Yield tuple rules:

- `yield value` — positional argument
- `yield name, value` — keyword argument
- `yield name, value, default` — keyword argument shown only when `value != default`
- `yield None, value` — positional argument (supports tuple positionals)

### Auto-generated Rich Repr

```python
import rich.repr

@rich.repr.auto
class Bird:
    def __init__(self, name, eats=None, fly=True, extinct=False):
        self.name = name
        self.eats = list(eats) if eats else []
        self.fly = fly
        self.extinct = extinct

# Angular bracket style
@rich.repr.auto(angular=True)
class Bird:
    ...
```

`@rich.repr.auto` requires that `__init__` parameter names match attribute names. Also generates `__repr__`.

Return type annotation: `def __rich_repr__(self) -> rich.repr.Result:`

---

## JSON Renderable

Renders JSON with syntax highlighting.

```python
from rich.json import JSON
from rich.console import Console

console = Console()
console.print(JSON('["foo", "bar"]'))
console.log(JSON('{"key": "value"}'))

# Convenience function
from rich import print_json
print_json('[false, true, null, "foo"]')

# Or via console
console.print_json('[false, true, null, "foo"]')
```

CLI:

```bash
python -m rich.json cats.json
```
