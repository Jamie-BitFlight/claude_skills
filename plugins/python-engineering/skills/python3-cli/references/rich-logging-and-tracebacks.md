# Logging and Tracebacks

`RichHandler` for integrating Rich with Python's stdlib `logging`, and Rich traceback installation for styled exception output with syntax highlighting and local variable display.

## Table of Contents

1. [RichHandler Setup](#richhandler-setup)
2. [RichHandler Parameters](#richhandler-parameters)
3. [Per-Message Overrides](#per-message-overrides)
4. [Rich Tracebacks in Log Output](#rich-tracebacks-in-log-output)
5. [Suppressing Framework Frames](#suppressing-framework-frames)
6. [Traceback Installation](#traceback-installation)
7. [Printing Tracebacks Manually](#printing-tracebacks-manually)
8. [Max Frames Limit](#max-frames-limit)

---

## RichHandler Setup

```python
import logging
from rich.logging import RichHandler

FORMAT = "%(message)s"
logging.basicConfig(
    level="NOTSET",
    format=FORMAT,
    datefmt="[%X]",
    handlers=[RichHandler()]
)

log = logging.getLogger("rich")
log.info("Hello, World!")
```

Rich log output adds:
- Timestamp column on the left (formatted via `datefmt`)
- File and line number column on the right
- Syntax highlighting for log messages

---

## RichHandler Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `level` | `NOTSET` | Minimum log level |
| `console` | `None` | Custom Console instance; creates one internally if not provided |
| `show_time` | `True` | Show timestamp column |
| `omit_repeated_times` | `True` | Suppress duplicate timestamps in successive log lines |
| `show_level` | `True` | Show log level column |
| `show_path` | `True` | Show file path and line number |
| `enable_link_path` | `True` | Make file path clickable in supported terminals |
| `highlighter` | `ReprHighlighter()` | Highlighter applied to log message |
| `markup` | `False` | Enable Rich markup in log messages (off by default — see warning below) |
| `rich_tracebacks` | `False` | Use Rich Traceback for exceptions |
| `tracebacks_width` | `None` | Width for traceback output |
| `tracebacks_extra_lines` | `3` | Extra lines of context around each frame |
| `tracebacks_theme` | `None` | Pygments theme for traceback code |
| `tracebacks_word_wrap` | `True` | Word wrap traceback code |
| `tracebacks_show_locals` | `False` | Show local variables in tracebacks |
| `tracebacks_suppress` | `()` | List of modules or paths to suppress from tracebacks |
| `locals_max_length` | `10` | Max items in local variable containers |
| `locals_max_string` | `80` | Max string length for local variables |
| `log_time_format` | `"[%x %X]"` | Format for timestamp when not using `datefmt` |
| `keywords` | `None` | List of words to highlight in log output |

WARNING: `markup=False` is the default because most libraries don't escape square brackets. Enable only for your own log messages that you control.

---

## Per-Message Overrides

Override handler settings for individual log calls using the `extra` dict:

```python
# Enable markup for this specific message
log.error("[bold red blink]Server is shutting down![/]", extra={"markup": True})

# Disable highlighter for this message
log.error("123 will not be highlighted", extra={"highlighter": None})
```

---

## Rich Tracebacks in Log Output

```python
import logging
from rich.logging import RichHandler

logging.basicConfig(
    level="NOTSET",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)

log = logging.getLogger("rich")
try:
    print(1 / 0)
except Exception:
    log.exception("unable print!")
```

---

## Suppressing Framework Frames

Use `tracebacks_suppress` to hide framework code (click, django, etc.) from traceback output. Suppressed frames show file/line only, no code.

```python
import click
import logging
from rich.logging import RichHandler

logging.basicConfig(
    level="NOTSET",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, tracebacks_suppress=[click])]
)
```

Pass a list of module objects or string paths.

---

## Traceback Installation

Install Rich as the global exception handler so all uncaught exceptions render with Rich formatting.

```python
from rich.traceback import install
install(show_locals=True)
```

`install()` parameters:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `console` | `None` | Custom Console to use |
| `width` | `100` | Width of traceback output |
| `extra_lines` | `3` | Extra context lines around each frame |
| `theme` | `None` | Pygments theme for code |
| `show_locals` | `False` | Display local variables for each frame |
| `locals_max_length` | `10` | Max items in local variable containers |
| `locals_max_string` | `80` | Max string length for local variables |
| `locals_hide_dunder` | `True` | Hide dunder variables from locals |
| `locals_hide_sunder` | `False` | Hide sunder variables from locals |
| `suppress` | `()` | List of modules or paths to suppress |
| `max_frames` | `100` | Max frames shown; 0 disables limit |

NOTE: For shared code, add `install()` in the main entry point module rather than in `sitecustomize.py`.

Automatic installation via `sitecustomize.py` (affects entire virtualenv):

```bash
touch .venv/lib/python3.9/site-packages/sitecustomize.py
```

```python
# .venv/lib/python3.9/site-packages/sitecustomize.py
from rich.traceback import install
install(show_locals=True)
```

---

## Printing Tracebacks Manually

```python
from rich.console import Console

console = Console()

try:
    do_something()
except Exception:
    console.print_exception(show_locals=True)
```

`console.print_exception()` parameters:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `show_locals` | `False` | Display local variables per frame |
| `width` | `88` | Width for traceback output |
| `extra_lines` | `3` | Extra context lines per frame |
| `theme` | `None` | Pygments theme |
| `word_wrap` | `False` | Word wrap source code lines |
| `suppress` | `()` | Modules or paths to suppress |
| `max_frames` | `100` | Max frames shown |

Suppress framework frames:

```python
import click
try:
    run_app()
except Exception:
    console.print_exception(suppress=[click])
```

---

## Max Frames Limit

Recursion errors produce very large tracebacks. `max_frames` (default 100) shows only the first 50 and last 50 frames when exceeded.

```python
try:
    foo(1)
except Exception:
    console.print_exception(max_frames=20)
```

Set `max_frames=0` to disable the limit entirely.
