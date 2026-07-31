# Typer UI Patterns — Output, Help, Colour, Progress, and Errors

Typer-specific patterns for CLI UI design: where to send output, how to design help text,
how to control colour and non-TTY behaviour, progress bars, error display, and command
discovery UX.

For non-TTY table width and data-loss-safe table printing, see
[./render-patterns.md](./render-patterns.md) and the authoritative local source at
`plugins/python-engineering/skills/python3-cli/references/typer-rich-tables.md`.

SOURCE: <https://typer.tiangolo.com/tutorial/printing/> (accessed 2026-05-07)
SOURCE: <https://typer.tiangolo.com/tutorial/exceptions/> (accessed 2026-05-07)
SOURCE: <https://typer.tiangolo.com/tutorial/terminating/> (accessed 2026-05-07)
SOURCE: <https://typer.tiangolo.com/tutorial/progressbar/> (accessed 2026-05-07)
SOURCE: <https://typer.tiangolo.com/tutorial/options/help/> (accessed 2026-05-07)
SOURCE: <https://typer.tiangolo.com/tutorial/commands/help/> (accessed 2026-05-07)
SOURCE: `plugins/python-engineering/skills/python3-cli/references/typer-rich-non-tty-patterns.md`
SOURCE: `plugins/python-engineering/skills/python3-cli/references/typer-rich-exception-handling.md`

---

## Output Tool Hierarchy

Official Typer docs establish a priority order for output. Use the highest-appropriate tool:

1. **`console.print()`** — full control; use for any formatted output in a well-structured CLI
2. **`rich.print()`** (or `from rich import print`) — quick Rich output in simple scripts
3. **`print()`** — acceptable for plain text with no formatting needs
4. **`typer.echo()`** — fallback only; use for binary data edge cases or when Rich is unavailable

`typer.echo()` is not deprecated but is not recommended for display work. Its value is handling
`bytes`-to-str conversion and stderr routing (`err=True`). For styled output, `console.print()`
or `rich.print()` is always the better choice.

SOURCE: <https://typer.tiangolo.com/tutorial/printing/> (accessed 2026-05-07)

---

## Output Channels — Where to Send What

Typer CLIs have three output channels:

| Channel | Mechanism | Use when |
|---|---|---|
| stdout | `console.print()`, `rich.print()`, `typer.echo()` | Data output — pipeable, machine-readable |
| stderr | `Console(stderr=True).print()`, `typer.echo(err=True)` | Diagnostics, progress, status messages |
| help system | Docstring + `help=` params | Parameter and command documentation |

**The decisive rule**: if the output might be piped to `jq`, `awk`, another script, or read by an
AI agent, it belongs on stdout as clean data (JSON, CSV, plain text). Human-readable diagnostics
and progress belong on stderr so they do not corrupt piped output.

```python
import typer
from rich.console import Console

app = typer.Typer()
err = Console(stderr=True)


@app.command()
def export(format: str = "json") -> None:
    err.print("[dim]Exporting...[/dim]")  # stderr: shown to human, invisible to pipes
    typer.echo(build_output(format))  # stdout: data (pipeable)
```

SOURCE: `plugins/python-engineering/skills/python3-cli/references/typer-rich-non-tty-patterns.md`
SOURCE: <https://typer.tiangolo.com/tutorial/printing/#standard-error> (accessed 2026-05-07)

---

## Help Text Design

### Markup Mode Selection

Set `rich_markup_mode` on `typer.Typer()`:

```python
# Rich markup — supports colour, bold, italic, emoji
app = typer.Typer(rich_markup_mode="rich")

# Markdown — supports structure, lists, links (NO colour)
app = typer.Typer(rich_markup_mode="markdown")

# Plain text — safe for all terminals, zero dependency on Rich rendering
app = typer.Typer(rich_markup_mode=None)
```

Default is `"rich"` when Rich is installed. In `"rich"` mode, any `[tag]` in docstrings or
`help=` strings is parsed as Rich markup — escape literal square brackets with `\[`.

### Markup in Docstrings and Help Params

```python
@app.command()
def create(username: Annotated[str, typer.Argument(help="The username to be [green]created[/green]")]) -> None:
    """
    [bold green]Create[/bold green] a new [italic]shiny[/italic] user. :sparkles:

    This requires a [underline]username[/underline].
    """
    ...
```

### Grouping Parameters into Named Panels

`rich_help_panel` groups options and arguments into separate sections in `--help` output:

```python
@app.command()
def deploy(
    env: str,
    dry_run: Annotated[bool, typer.Option(help="Simulate only")] = False,
    timeout: Annotated[int, typer.Option(help="Max seconds", rich_help_panel="Advanced")] = 60,
    retries: Annotated[int, typer.Option(help="Retry count", rich_help_panel="Advanced")] = 3,
) -> None: ...
```

This produces a default `Options` panel for `dry_run` and a separate `Advanced` panel for
`timeout` and `retries`. The same parameter works on `@app.command()` to group commands on the
main help page.

SOURCE: <https://typer.tiangolo.com/tutorial/commands/help/> (accessed 2026-05-07)

### Epilog — Footer Text in Help

```python
@app.command(epilog="Made with [bold]uv[/bold]. See https://example.com for docs.")
def build(...) -> None:
    ...
```

### Hiding or Customising Default Values in Help

```python
# Hide default entirely
fullname: Annotated[str, typer.Option(show_default=False)] = "Wade Wilson"

# Replace raw value with a human-readable description
fullname: Annotated[str, typer.Option(show_default="user's registered name")] = "Wade Wilson"
```

SOURCE: <https://typer.tiangolo.com/tutorial/options/help/#hide-default-from-help> (accessed 2026-05-07)

### Marking Commands as Deprecated

```python
@app.command(deprecated=True)
def old_export(path: str) -> None:
    """Export data. Use `new-export` instead."""
    ...
```

This prints `[deprecated]` in help listings and on the command's own `--help`. The command still
executes normally — no backward compatibility is broken.

SOURCE: <https://typer.tiangolo.com/tutorial/commands/help/#deprecate-a-command> (accessed 2026-05-07)

---

## Colour Output and Non-TTY Behaviour

### The Fundamental Rule

When stdout is not a TTY (CI, pipes, agent Bash tool), Rich strips ANSI codes and defaults to
width 80. Designing output that works in both contexts requires explicit decisions at each output
site.

### TTY Detection

```python
import sys

is_tty = sys.stdout.isatty()
```

### Colour Control Environment Variables

Rich and Typer respect these automatically — no code change needed:

| Variable | Effect |
|---|---|
| `NO_COLOR` (any non-empty value) | Disables all colour output |
| `FORCE_COLOR` (any non-empty value) | Enables colour even without a TTY |
| `TYPER_USE_RICH=0` | Disables Rich entirely in Typer |
| `TYPER_STANDARD_TRACEBACK=1` | Switches to plain Python traceback format |

`rich_markup_mode` and `NO_COLOR`: Typer inherits `NO_COLOR` from the environment via Click.
No extra code needed — set `NO_COLOR=1` and all Rich help formatting is suppressed automatically.

### `force_terminal` vs `width` — Separate Concerns

```python
# Emit ANSI codes to a non-TTY (e.g., output going to a pager with colour support)
Console(force_terminal=True)

# Control wrapping width, independent of colour
Console(width=120)

# Both: emit colour AND control width
Console(force_terminal=True, width=120)
```

SOURCE: `plugins/python-engineering/skills/python3-cli/references/typer-rich-non-tty-patterns.md`

---

## Progress Bars and Spinners

### Preferred: `rich.progress.track()`

Official Typer docs recommend `rich.progress.track()` as the preferred progress API.
`typer.progressbar()` is a fallback for when Rich is unavailable or disabled.

```python
from rich.progress import track

for item in track(items, description="Processing..."):
    process(item)
```

`track()` handles non-TTY automatically — it emits no control sequences when stdout is not a TTY.

### TTY Guard for Explicit Progress Context

`transient=True` does NOT suppress non-TTY garbage. Use `disable=not sys.stdout.isatty()`:

```python
import sys
from rich.progress import Progress

with Progress(disable=not sys.stdout.isatty()) as progress:
    task = progress.add_task("Processing...", total=len(items))
    for item in items:
        process(item)
        progress.update(task, advance=1)
```

### Spinner for Indeterminate Duration

```python
from rich.progress import Progress, SpinnerColumn, TextColumn

with Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    transient=True,
    disable=not sys.stdout.isatty(),
) as progress:
    progress.add_task(description="Loading...", total=None)
    do_long_work()
```

### Rich Progress vs typer.progressbar

- Use `rich.progress.track()` in all cases where Rich is available
- Use `typer.progressbar()` only when Rich is disabled or unavailable

SOURCE: <https://typer.tiangolo.com/tutorial/progressbar/> (accessed 2026-05-07)
SOURCE: `plugins/python-engineering/skills/python3-cli/references/typer-rich-non-tty-patterns.md`

---

## Exception Display Controls

### Knobs on `typer.Typer()`

```python
app = typer.Typer(
    pretty_exceptions_enable=True,  # default: True — Rich formats exceptions
    pretty_exceptions_short=True,  # default: True — hides Typer internals
    pretty_exceptions_show_locals=False,  # default: False since 0.23.0 — security: hides locals
)
```

**Security**: `pretty_exceptions_show_locals=True` exposes the values of all local variables in
the traceback. In CI environments that capture logs, this can leak passwords, API keys, and
tokens. Enable only when debugging locally.

SOURCE: <https://typer.tiangolo.com/tutorial/exceptions/> (accessed 2026-05-07)

### AppExit Pattern — User-Facing Errors

Avoid catching and re-wrapping exceptions at every layer. A single `FileNotFoundError` wrapped
seven times produces 220 lines of traceback output. The correct pattern is to catch once, at
the layer that has meaningful context, and raise a typed exit immediately:

```python
import typer
from pathlib import Path


class AppExit(typer.Exit):
    """Graceful exit with a user-facing message. Output in __init__, raise once."""

    def __init__(self, code: int | None = None, message: str | None = None) -> None:
        if message is not None:
            if code is None or code == 0:
                typer.echo(message)
            else:
                typer.echo(message, err=True)  # errors go to stderr
        super().__init__(code=code)
```

With Rich:

```python
from rich.console import Console
import typer

err_console = Console(stderr=True)


class AppExitRich(typer.Exit):
    def __init__(self, code: int | None = None, message: str | None = None, console: Console = err_console) -> None:
        if message is not None:
            console.print(message)
        super().__init__(code=code)
```

Usage — let exceptions propagate through helper functions, catch only at the layer that has
meaningful context (filename, line number, validation detail):

```python
def load_config(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        raise AppExit(code=1, message=f"Config not found: {path}")
    except json.JSONDecodeError as e:
        raise AppExit(code=1, message=f"Invalid JSON in {path} at line {e.lineno}: {e.msg}") from e
```

### Exit Codes

```python
raise typer.Exit()  # code 0 — success
raise typer.Exit(code=1)  # non-zero — error
raise typer.Abort()  # prints "Aborted!", code 1 — user cancellation
```

Always use `typer.Exit`, not `sys.exit()`. `CliRunner` captures `typer.Exit`; `sys.exit()`
raises `SystemExit` and may abort the test runner.

SOURCE: `plugins/python-engineering/skills/python3-cli/references/typer-rich-exception-handling.md`
SOURCE: <https://typer.tiangolo.com/tutorial/terminating/> (accessed 2026-05-07)

---

## Command Discovery UX

### `no_args_is_help=True`

Running `myapp` with no arguments shows help instead of a confusing "Missing command" error:

```python
app = typer.Typer(no_args_is_help=True)
```

### `suggest_commands=True` (default since Typer 0.20.0)

When a user mistypes a command name, Typer suggests close matches using
`difflib.get_close_matches()`. This is on by default — no code required. Disable with
`suggest_commands=False` only when the typo-suggestion behaviour is unwanted.

SOURCE: <https://typer.tiangolo.com/tutorial/commands/help/#suggest-commands> (accessed 2026-05-07)

---

## UX Gotchas

### Gotcha 1: Rich Progress Redirects stdout/stderr by Default

`Progress` captures stdout and stderr to route them through its live display. This breaks:

- `typer.echo()` inside a progress context (output may disappear or corrupt the bar)
- `subprocess.run()` inside a progress context (subprocess output captured, not shown)
- pytest output capture (CliRunner may conflict)

Fix:

```python
with Progress(redirect_stdout=False, redirect_stderr=False, disable=True) as progress:
    ...
```

SOURCE: `plugins/python-engineering/skills/python3-cli/references/typer-rich-non-tty-patterns.md`

### Gotcha 2: `transient=True` Does Not Suppress Non-TTY Progress Output

`transient=True` erases the progress bar from an interactive terminal on completion. In non-TTY
contexts (CI logs, piped output), `disable=True` is required. Many developers use `transient=True`
and expect CI logs to be clean — they are not.

SOURCE: `plugins/python-engineering/skills/python3-cli/references/typer-rich-non-tty-patterns.md`

### Gotcha 3: `rich_markup_mode="rich"` Is the Default — Docstrings Render Markup

With `rich_markup_mode="rich"` (current default when Rich is installed), any `[tag]` in
docstrings and `help=` strings is parsed as Rich markup. Literal square brackets in help text
need escaping: write `\[` to display `[`.

### Gotcha 4: `rich.print()` Creates a New Console on Every Call

`from rich import print` creates a temporary console per call. For consistent width, style, and
stderr routing across a CLI, use a shared `Console` instance constructed once at module level.
`rich.print()` is fine for quick scripts; not for structured CLI output.

### Gotcha 5: `CliRunner` Captures stdout But Not Module-Level `Console(stderr=True)`

`CliRunner` redirects `sys.stdout`. A `Console(stderr=True)` writes to `sys.stderr`. To capture
stderr in tests, use `mix_stderr=False`:

```python
from typer.testing import CliRunner

runner = CliRunner(mix_stderr=False)
result = runner.invoke(app, ["report"])
assert result.exit_code == 0
assert "error detail" in result.stderr
```

SOURCE: `plugins/python-engineering/skills/python3-cli/references/typer-rich-non-tty-patterns.md`

### Gotcha 6: Box-Drawing Characters Suppressed Without `force_terminal=True` in Tests

When asserting on `╭`, `│`, `╰` box characters in help output, the test console must set
`force_terminal=True`. Without it, Rich detects a non-TTY and omits box-drawing characters.
Tests pass locally (real terminal) and fail in CI.

SOURCE: `plugins/python-engineering/skills/python3-cli/references/typer-rich-non-tty-patterns.md`
