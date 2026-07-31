# Non-TTY and Programmatic Usage Patterns

Patterns for using Rich and Typer correctly when stdout/stderr is not a terminal — piped output,
CI environments, subprocess capture, testing, and Claude Code's Bash tool.

---

## 1. Non-TTY Console Behavior

### What Rich detects and changes without a TTY

When `Console.is_terminal` is `False` (piped, redirected, or no TTY), Rich:

- Strips ANSI escape codes (color, bold, etc.) by default
- Falls back to width `80` when `os.get_terminal_size()` fails
- Still renders markup and highlights syntax unless explicitly disabled

Source: `.claude/worktrees/rich/rich/console.py` — `size` property and `is_terminal` property.

Width fallback chain (source: `console.py`, `size` property):

```python
# 1. Try os.get_terminal_size() on each std stream file descriptor
# 2. Fall back to COLUMNS environment variable
# 3. Fall back to 80 if all else fails
width = width or 80
```

### `force_terminal=True` vs `width=N`

Use `force_terminal=True` when you want Rich to emit ANSI codes to a non-TTY (e.g., output that
will be interpreted by another tool or rendered in a pager with color support):

```python
from rich.console import Console

# Emit color codes even when stdout is piped
console = Console(force_terminal=True)
console.print("[bold green]OK[/bold green] Build passed")
```

Use `width=N` when you know the display width and want to control wrapping, independent of
whether ANSI codes are emitted:

```python
from rich.console import Console

# Fixed 120-column layout, no color (piped output)
console = Console(width=120)
console.print(some_table)
```

Combining both: emit color AND control width:

```python
from rich.console import Console

console = Console(force_terminal=True, width=120)
```

Source: `.claude/worktrees/rich/rich/console.py`, `Console.__init__` docstring lines 593–601.

### `Console(stderr=True)` — separate data from display

Use `stderr=True` to send Rich output (progress, status, diagnostics) to stderr while keeping
stdout clean for machine-readable data:

```python
from rich.console import Console
import json

err_console = Console(stderr=True)
out_console = Console()  # stdout, no color when piped


def process(items: list[dict]) -> None:
    with err_console.status("Processing..."):
        result = [transform(item) for item in items]
    # stdout receives only the data — safe to pipe to jq, etc.
    out_console.print_json(json.dumps(result))
```

Source: `.claude/worktrees/rich/rich/console.py`, `Console.__init__` `stderr` parameter.

### `Console(file=StringIO())` — capture in tests

```python
from io import StringIO
from rich.console import Console


def test_output_contains_warning():
    buf = StringIO()
    console = Console(file=buf, width=80)
    console.print("[yellow]Warning:[/yellow] disk low")
    output = buf.getvalue()
    assert "Warning:" in output  # markup stripped; plain text remains
```

Note: `file=StringIO()` produces no ANSI codes because `StringIO.isatty()` returns `False`.
Use `force_terminal=True` alongside `file=StringIO()` only when testing ANSI output itself.

---

## 2. Environment Variables

Rich reads these environment variables (source: `.claude/worktrees/rich/rich/console.py`,
`is_terminal` property and `__init__`):

| Variable | Effect |
|---|---|
| `NO_COLOR` | Any non-empty value disables all color output |
| `FORCE_COLOR` | Any non-empty value enables color even without a TTY |
| `TERM=dumb` | Detected as dumb terminal; width defaults to 80, no color |
| `COLUMNS` | Overrides width detection when no TTY (integer value) |
| `LINES` | Overrides height detection |
| `TTY_COMPATIBLE` | Rich-specific: treated as a TTY for color/control purposes |

Detection order for color (source: `console.py` `is_terminal` property, line ~956–970):

```python
# 1. force_terminal parameter (highest precedence)
# 2. Jupyter detection
# 3. TTY_COMPATIBLE env var
# 4. FORCE_COLOR env var
# 5. file.isatty() (lowest precedence)
```

Inject `NO_COLOR=1` to disable all Rich color in CI without code changes:

```bash
NO_COLOR=1 python my_cli.py report
```

### `COLUMNS` is not a width cap for diagnostic tools

`COLUMNS=N` pins Rich's non-TTY width at `N`. Use it **only** when you have a known,
fixed display surface that your output must fit into (e.g., a 120-col dashboard pane,
an email with a monospace column limit, a printout). That is not the situation for
CLI diagnostics, test reports, environment checks, or any tool whose output is
consumed by CI logs, grep/awk pipelines, or AI agents.

For diagnostic tooling, pinning `COLUMNS=200` (or any other integer) causes the exact
data-loss modes described in `typer-rich-tables.md` "The Goal: Zero Data Loss":

1. Cells longer than `N` wrap — continuation lines lose their row label, timestamp,
   and severity. A `grep ERROR` pipeline then matches only line 1 of each wrapped row.
2. URLs, file paths, and identifiers split mid-token across line boundaries.
   `grep /path/to/environment.py` returns nothing because the path no longer exists
   as a contiguous string in the output.
3. Truncation with `…` destroys the tail of values needed for analysis.

For diagnostic tools: do not pin `COLUMNS`. Use the `Measurement.get` pattern below
to render at the renderable's natural width, and let the consumer (terminal pager,
log viewer, `less -S`, agent) handle width however it wants.

---

## 3. Width and Wrapping Problems

### The 80-column default

Without a TTY, Rich defaults to width 80. Tables and panels that look correct
interactively will wrap or truncate in CI. For diagnostic tooling, do not replace
the 80-column default with another fixed integer — any cap causes data loss on
content longer than the cap. Measure the renderable's natural width and render
at that width instead.

```python
from rich.console import Console
from rich.measure import Measurement
from rich.table import Table

# BAD: Console() defaults to 80 in CI, wraps and truncates
console = Console()

# ALSO BAD: fixed cap loses everything past column 200
console = Console(width=200)


# GOOD: measure natural width on a 9999-col temp console, render at that width
def get_rendered_width(renderable) -> int:
    temp = Console(width=999999)
    return int(Measurement.get(temp, temp.options, renderable).maximum)


table = Table("Name", "Value", "Description")
table.add_row("item", "value", "long description...")
table.width = get_rendered_width(table)

console = Console()
console.print(table, crop=False, overflow="ignore", soft_wrap=True, no_wrap=True)
```

Use a fixed `Console(width=N)` **only** when you have a known fixed display surface
your output must fit into (a 120-col pane, a printable report, an email column). That
is not the case for CLI diagnostics, test reports, or any tool consumed by CI logs,
grep pipelines, or AI agents — those consumers handle width themselves and need every
character preserved. See `typer-rich-tables.md` "The Goal: Zero Data Loss".

### `soft_wrap=True` — prevent hard-wrapping long lines

`soft_wrap=True` on `Console` (or per `print` call) tells Rich not to word-wrap output.
Use this for log lines or structured output where wrapping corrupts the content:

```python
from rich.console import Console

console = Console(soft_wrap=True)  # applies to all print calls
console.print("very long line that must not wrap: " + "x" * 200)

# Or per call:
console = Console()
console.print("very long line", soft_wrap=True)
```

### `overflow` and `crop` on `console.print`

`crop=False` prevents Rich from truncating rendered output to console width:

```python
from rich.console import Console

console = Console(width=80)
# Without crop=False: content beyond 80 chars is silently dropped
console.print(wide_panel, crop=False)
```

`overflow` controls what happens when a renderable exceeds its container:

```python
from rich.console import Console
from rich.text import Text

console = Console(width=40)
text = Text("a" * 100)
console.print(text, overflow="ignore")  # extend past boundary
console.print(text, overflow="fold")  # wrap at character boundary
console.print(text, overflow="ellipsis")  # truncate with …
console.print(text, overflow="crop")  # hard cut at width
```

Source: `.claude/worktrees/rich/rich/console.py` — `OverflowMethod` literal type, line 76.

### `no_wrap=True` on Table columns

Prevent a specific column from wrapping even when the table is constrained:

```python
from rich.console import Console
from rich.table import Table

console = Console(width=80)
table = Table()
table.add_column("ID", no_wrap=True, min_width=8)  # never wraps
table.add_column("Description", ratio=1)  # flexible
table.add_column("Status", no_wrap=True, min_width=10)  # never wraps
```

Source: `.claude/worktrees/rich/rich/table.py`, `Column.no_wrap` field line 105.

### Measuring natural width of a renderable

Use `Measurement.get` to find the minimum and maximum width a renderable requires before
committing to a console width:

```python
from rich.console import Console
from rich.measure import Measurement
from rich.table import Table

console = Console()
table = Table("Col A", "Col B")
table.add_row("short", "also short")

measurement = Measurement.get(console, console.options, table)
print(measurement.minimum)  # narrowest width without data loss
print(measurement.maximum)  # widest natural layout
```

Source: `.claude/worktrees/rich/rich/measure.py`, `Measurement` class.

---

## 4. Progress and Live in Non-TTY

### Progress bars produce garbage without a TTY

Without a TTY, `Progress` emits control sequences (carriage returns, cursor moves) that appear
as garbage in captured output or CI logs. Always disable `Progress` in non-interactive contexts.

```python
import os
import sys
from rich.progress import Progress

is_interactive = sys.stdout.isatty()

with Progress(disable=not is_interactive) as progress:
    task = progress.add_task("Processing...", total=100)
    for i in range(100):
        do_work(i)
        progress.update(task, advance=1)
```

Source: `.claude/worktrees/rich/rich/progress.py`, `Progress.__init__` `disable` parameter line 1088.

### `transient=True` implications

`transient=True` clears the progress bar from the terminal on exit. In non-TTY contexts where
`disable=True`, `transient` has no effect. Do not rely on `transient` to suppress output in CI —
use `disable=True`.

```python
from rich.progress import Progress

# transient=True: visually clean in terminal (erases bar on completion)
# but does NOT suppress output in non-TTY — use disable for that
with Progress(transient=True, disable=not sys.stdout.isatty()) as progress:
    ...
```

Source: `.claude/worktrees/rich/rich/progress.py` line 1069, `.claude/worktrees/rich/rich/live.py` line 50.

### `redirect_stdout` and `redirect_stderr` in Progress

`Progress` redirects stdout and stderr through its live display by default. In non-TTY or
testing contexts this can interfere with output capture:

```python
from rich.progress import Progress

# Disable redirection when output capture matters (e.g., pytest)
with Progress(redirect_stdout=False, redirect_stderr=False, disable=True) as progress:
    ...
```

Source: `.claude/worktrees/rich/rich/progress.py`, `Progress.__init__` lines 1085–1087.

### Live display without a terminal

`Live` checks `console.is_terminal` before emitting control sequences (source:
`.claude/worktrees/rich/rich/live.py` lines 171, 197, 269). When no TTY is present, Live
degrades to sequential prints without cursor control. This is safe but produces verbose output.
Use `Console(quiet=True)` or suppress via `disable` if output must be clean:

```python
from rich.live import Live
from rich.console import Console

# Suppress all Live output in non-interactive contexts
console = Console(quiet=not sys.stdout.isatty())
with Live(console=console, refresh_per_second=4):
    ...
```

---

## 5. Typer-Specific Patterns

### `typer.echo()` vs `rich.print()` vs `console.print()`

| Function | Stdout | Strips markup | Use when |
|---|---|---|---|
| `typer.echo()` | yes (default) | yes (plain text only) | Simple text, exit messages |
| `typer.echo(err=True)` | no (stderr) | yes | Error messages without Rich |
| `rich.print()` | yes | no (renders markup) | Quick Rich output, scripts |
| `console.print()` | configurable | no (renders markup) | Full control of output target/width |

For CLIs that produce data on stdout (piped to `jq`, `awk`, etc.) and diagnostics on stderr:

```python
import sys
import typer
from rich.console import Console

app = typer.Typer()
err = Console(stderr=True)


@app.command()
def export(format: str = "json") -> None:
    err.print("[dim]Exporting...[/dim]")  # stderr: diagnostics
    typer.echo(build_output(format))  # stdout: data (pipeable)
```

### Typer `rich_markup_mode` and `no_color`

Typer passes `rich_markup_mode` to its help formatter. Set it on the `Typer()` instance:

```python
import typer

# "rich" — Rich markup in docstrings and help text
# "markdown" — Markdown in docstrings and help text
# None — plain text (safe for all terminals)
app = typer.Typer(rich_markup_mode="rich")
```

Source: `.claude/worktrees/typer/typer/main.py` lines 410–519.

Typer inherits `NO_COLOR` from the environment via Click's terminal detection. No extra code
needed — set `NO_COLOR=1` and all Rich help formatting is suppressed automatically.

### Exit codes

Always use `raise typer.Exit(code=N)` rather than `sys.exit(N)`. `typer.Exit` is caught by
`CliRunner` in tests; `sys.exit` raises `SystemExit` and may abort the test runner.

```python
import typer

app = typer.Typer()


@app.command()
def check() -> None:
    if not run_check():
        raise typer.Exit(code=1)
```

---

## 6. Testing Patterns

### `CliRunner` — capturing Typer app output

Typer's `CliRunner` wraps Click's `CliRunner`. Use it to invoke commands in-process and
capture stdout/stderr without a TTY:

```python
from typer.testing import CliRunner
from myapp.cli import app

runner = CliRunner()


def test_output():
    result = runner.invoke(app, ["--format", "json"])
    assert result.exit_code == 0
    assert '"status"' in result.output
```

Source: `.claude/worktrees/typer/typer/testing.py`.

`color=False` (default) strips ANSI codes from captured output. Set `color=True` only when
testing ANSI escape sequences explicitly:

```python
result = runner.invoke(app, ["report"], color=False)  # default: plain text
result_with_color = runner.invoke(app, ["report"], color=True)  # includes ANSI
```

### Injecting environment variables in tests

```python
from typer.testing import CliRunner
from myapp.cli import app

runner = CliRunner()


def test_no_color_env():
    result = runner.invoke(app, ["report"], env={"NO_COLOR": "1"})
    assert "\033[" not in result.output  # no ANSI escape sequences
```

### Capturing Rich output with `Console(record=True)`

Use `record=True` when you need Rich's full rendering (tables, panels, markup) but want to
capture the result as a string rather than write to a file:

```python
from rich.console import Console


def test_table_output():
    console = Console(record=True, width=80)
    render_my_table(console)
    text = console.export_text()  # plain text, no ANSI
    assert "Alice" in text
    assert "Bob" in text
```

`export_text()` clears the record buffer by default (`clear=True`). Call with `clear=False` to
preserve the buffer for multiple exports.

Source: `.claude/worktrees/rich/rich/console.py`, `export_text` method line 2177.

### `begin_capture` / `end_capture` — lightweight capture

For capturing a specific block without setting `record=True` on construction:

```python
from rich.console import Console

console = Console()
console.begin_capture()
console.print("[bold]hello[/bold]")
output = console.end_capture()  # returns plain text string
assert "hello" in output
```

Source: `.claude/worktrees/rich/rich/console.py`, `begin_capture` line 872, `end_capture` line 876.

### Asserting styled vs unstyled output

To compare styled content, export with `styles=True` from a `record=True` console:

```python
from rich.console import Console


def test_warning_is_yellow():
    console = Console(record=True, force_terminal=True, width=80)
    console.print("[yellow]Warning[/yellow]: disk low")
    # export_text(styles=True) includes ANSI sequences
    styled = console.export_text(styles=True)
    assert "\x1b[33m" in styled  # yellow ANSI code
    # export_text(styles=False) strips all ANSI
    plain = console.export_text(styles=False, clear=False)
    assert "Warning" in plain
```

---

## 7. Patterns for CI Logs and AI Agent Consumption (Claude Code Bash Tool)

The Bash tool has no TTY. So do GitLab/GitHub CI runners, Docker containers, any
`subprocess.run(..., capture_output=True)` invocation, and most agent harnesses.
Rich output in these contexts will, by default:

- Have no color (unless `FORCE_COLOR=1` is set in the command)
- Default to width 80 — wrapping cells and truncating content
- Show `Progress` control sequences as garbage characters

The consumer of this output is either an AI agent reading a transcript, a CI log
reader, or a `grep`/`awk` pipeline. All three need every character of every row
preserved on one physical line. Wrapping orphans labels; truncation destroys data.
See `typer-rich-tables.md` "The Goal: Zero Data Loss" for the full argument.

### Do not pin `COLUMNS`

Earlier versions of this guide recommended `NO_COLOR=1 COLUMNS=200 python my_cli.py`.
That is wrong for diagnostic tools. Pinning `COLUMNS=200` means any row with content
longer than 200 columns is silently wrapped or truncated — the exact failure mode
the tool exists to prevent. Use `COLUMNS=N` only when you have an actual fixed
display surface to fit into (a 120-col dashboard pane, a printed report).

### The correct pattern: measure-and-render at natural width

From within the tool, build every Table / Panel with explicit `no_wrap=True` on
every column, measure natural width via `Measurement.get` on a 9999-col temp console,
set `table.width = measured_width`, and print with `crop=False, overflow="ignore",
soft_wrap=True, no_wrap=True`. No environment variable is required.

```python
from rich.console import Console
from rich.measure import Measurement
from rich.table import Table


def get_rendered_width(renderable) -> int:
    temp = Console(width=999999)
    return int(Measurement.get(temp, temp.options, renderable).maximum)


console = Console()  # no explicit width — consumer handles it

table = Table()
table.add_column("Check", no_wrap=True)
table.add_column("Value", no_wrap=True)
table.add_column("Note", no_wrap=True)
table.add_row("jlink", "000683056102", "full nrfjprog --ids output preserved")
table.width = get_rendered_width(table)

console.print(table, crop=False, overflow="ignore", soft_wrap=True, no_wrap=True)
```

This renders the table at whatever natural width the content requires — 80, 200,
500, 1200 columns. The CI log, agent transcript, or `less -S` handles horizontal
scrolling. No character is lost.

### Disabling color for CI / agent capture

If you need color stripped (to avoid ANSI noise in captured output), set `NO_COLOR=1`
in the environment — this does not affect width:

```bash
NO_COLOR=1 python my_cli.py report
```

Or from code: `Console(no_color=True)`. Both are compatible with the measure-and-render
pattern.

### Oversized cell content

If a single cell value is genuinely too large to be useful inline (multi-KB stderr
dumps, full log files), truncate it **at the data source** with an explicit length
and a visible sentinel (`…` or `[truncated, N more chars]`) before it reaches the
cell. Never hide the truncation by capping column width — the truncation must be
visible in the captured output so downstream readers know data was dropped.

```python
_NOTE_MAX = 200
note_raw = subprocess.run(...).stderr
note = note_raw[:_NOTE_MAX] + "…" if len(note_raw) > _NOTE_MAX else note_raw
table.add_row("jlink", serial, note)  # sentinel is part of the cell value
```

### Structured output for programmatic consumption

For data intended for a downstream parser (`jq`, `awk`, another script), bypass Rich
entirely and emit plain JSON / NDJSON / CSV on stdout. Send human-readable Rich
output to stderr via `Console(stderr=True)`:

```python
import json
import sys
from rich.console import Console

err = Console(stderr=True)


def export(result: dict) -> None:
    err.print("[dim]Exporting...[/dim]")  # stderr: diagnostics, color OK
    print(json.dumps(result), file=sys.stdout)  # stdout: data (pipeable)
```

---

## 8. Verifying a CLI Tool is Data-Loss-Safe

Before shipping a CLI tool that will run in CI or be consumed by an AI agent, verify
that no content is lost when output is captured without a TTY. A tool is
data-loss-safe when **every character of every value** appears contiguously
(no wrap splits, no truncation, no ellipsis) in the captured output.

### Verification steps

1. **Construct a pathological payload** — a row or panel whose content is longer
   than any fixed integer a human might default to (200+ columns). Examples:
   - A URL with query parameters: `https://example.com/...?a=1&b=2&...` 300 chars long
   - A file path in a deeply nested monorepo: `/very/long/path/to/a/real/file.py`
   - A full `subprocess.run(...).stderr` block with multiple lines
2. **Capture the output with no TTY** (one of):
   ```bash
   # Pipe to cat — removes the TTY, default width 80 applies
   uv run mytool 2>&1 | cat

   # Force the 80-col failure case explicitly
   COLUMNS=80 uv run mytool 2>&1 | cat

   # Redirect to a file
   uv run mytool > /tmp/out.txt 2>&1
   ```
3. **Assert every expected token is contiguous in the capture**:
   ```bash
   # The full URL must appear as one substring
   grep -F 'https://example.com/very/long/url?param=value&other=thing' /tmp/out.txt

   # The full file path must be greppable
   grep -F '/very/long/path/to/a/real/file.py' /tmp/out.txt

   # Row labels must appear on the same line as their values
   grep -E '^.*jlink.*000683056102' /tmp/out.txt
   ```
   If any of these `grep`s return nothing, the tool is wrapping, truncating, or
   splitting mid-token — not data-loss-safe.
4. **Look for ellipsis sentinels** (`…`, `...`). If they appear in captured output
   where you did not explicitly add them at the data source, a column or console
   is capping width and destroying content:
   ```bash
   grep -c '…' /tmp/out.txt  # should be 0 unless added deliberately as a sentinel
   ```
5. **Confirm widths are content-driven, not fixed** — inspect the widest row and
   confirm the horizontal border length equals `max(content_width) + padding`,
   not a fixed 80 / 120 / 200.

### Pytest assertion pattern

Integrate the check into your test suite so regressions are caught automatically:

```python
import subprocess


def test_env_check_preserves_long_paths(tmp_path, monkeypatch):
    long_path = "/this/is/a/very/long/tool/path/that/exceeds/200/characters/" + "x" * 200
    monkeypatch.setenv("DCF_TOOL", long_path)

    result = subprocess.run(
        ["uv", "run", "robotTests/tools/zigbee_env_check.py"],
        capture_output=True,
        text=True,
        env={"COLUMNS": "80", **os.environ},
    )

    # The full path must be contiguous in the captured output
    assert long_path in result.stdout, (
        f"Long path was wrapped, truncated, or ellipsized. Captured output: {result.stdout!r}"
    )
    # No stray ellipsis
    assert "…" not in result.stdout
```

### Failure modes this test catches

- Console default-80 wrapping (missing `no_wrap` + measurement)
- Column `overflow="fold"` or `overflow="ellipsis"` with constrained `max_width`
- Fixed `Console(width=N)` or `table.width = N` caps
- `min(measured, N)` caps on measured widths
- Cell values that exceed `max_width` and get silently folded

A tool that passes this test is safe to run in CI and have its output read by an
AI agent without hallucination risk from truncated identifiers.
