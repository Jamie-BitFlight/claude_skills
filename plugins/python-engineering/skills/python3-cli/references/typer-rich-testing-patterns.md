# Testing Patterns for Typer and Rich Applications

SOURCE: `.claude/worktrees/typer/typer/testing.py`, `.claude/worktrees/typer/tests/`,
`.claude/worktrees/rich/rich/console.py`, `.claude/worktrees/rich/tests/test_console.py`

---

## 1. Capturing Rich Output in pytest

### Console(file=StringIO()) — Inline capture

Redirect console output to an in-memory buffer. Use this when you construct the console in
your test and pass it into the function under test.

```python
import io
from rich.console import Console


def render_summary(console: Console, items: list[str]) -> None:
    for item in items:
        console.print(f"[bold]{item}[/bold]")


def test_render_summary():
    console = Console(file=io.StringIO(), width=80)
    render_summary(console, ["alpha", "beta"])
    output = console.file.getvalue()
    assert "alpha" in output
    assert "beta" in output
```

Always set `width` explicitly. Without it, `Console` queries the terminal width, which varies
between CI and local environments and causes line-wrap differences that break assertions.

SOURCE: `.claude/worktrees/rich/tests/test_console.py` line 49 — `Console(file=io.StringIO(), width=20)`

### Console.capture() — Context manager

Use `capture()` when you cannot inject the console via dependency injection and need to
intercept output from a shared console instance.

```python
from rich.console import Console

console = Console()


def greet(name: str) -> None:
    console.print(f"[bold magenta]Hello {name}[/]")


def test_greet_output():
    with console.capture() as capture:
        greet("World")
    text = capture.get()
    assert "Hello World" in text
```

`capture.get()` raises `CaptureError` if called inside the `with` block before the block exits.
Call it only after the context manager closes.

SOURCE: `.claude/worktrees/rich/rich/console.py` line 1102 — `def capture()`;
`.claude/worktrees/rich/tests/test_console.py` line 377 — `test_capture()`

### console.export_text() — Recording mode

Enable `record=True` in the constructor. `export_text()` returns all output since the last
export (or since construction if no prior export). By default it strips ANSI codes; pass
`styles=True` to include them.

```python
from rich.console import Console


def test_export_text_strips_markup():
    console = Console(record=True, width=100)
    console.print("[b]Important[/b] message")
    text = console.export_text()
    # Rich markup is rendered then stripped — raw tag strings do not appear
    assert text == "Important message\n"
    assert "[b]" not in text


def test_export_text_with_styles():
    console = Console(record=True, width=100)
    console.print("[b]Bold[/b]")
    styled = console.export_text(styles=True)
    # ANSI escape codes are present when styles=True
    assert "\x1b[" in styled
```

`export_text(clear=True)` (the default) resets the buffer after each call. Set `clear=False`
to keep accumulating across multiple exports.

SOURCE: `.claude/worktrees/rich/rich/console.py` lines 2177–2214 — `def export_text()`;
`.claude/worktrees/rich/tests/test_console.py` lines 505–547 — `test_export_text()`

### Styled vs unstyled assertions

Assert on plain text content, not markup strings or ANSI codes, unless you are explicitly
testing style output.

```python
from rich.console import Console


def test_content_not_markup():
    console = Console(record=True, width=80)
    console.print("[bold red]Error:[/bold red] file not found")
    text = console.export_text()
    # Correct: assert on rendered text
    assert "Error: file not found" in text
    # Wrong: this will never match — markup is consumed by the renderer
    assert "[bold red]Error:[/bold red]" not in text  # always true, misleading as assertion intent
```

When you need to verify that styling was applied, use `export_html()` or `export_text(styles=True)`
and check for the relevant CSS class or ANSI sequence.

```python
def test_bold_applied():
    console = Console(record=True, width=80)
    console.print("[b]critical[/b]")
    html = console.export_html()
    assert "font-weight: bold" in html or "r1" in html  # HTML output includes style class
```

SOURCE: `.claude/worktrees/rich/tests/test_console.py` — `test_export_html()` at line 513

---

## 2. Typer CliRunner with Rich

### typer.testing.CliRunner vs click.testing.CliRunner

`typer.testing.CliRunner` is a thin subclass of `click.testing.CliRunner`. The only difference
is that its `invoke()` accepts a `typer.Typer` instance directly instead of a Click command.
Internally it calls `typer.main.get_command(app)` to convert the Typer app before passing it
to Click's runner.

```python
from typer.testing import CliRunner
import typer

app = typer.Typer()

@app.command()
def hello(name: str) -> None:
    typer.echo(f"Hello {name}")

runner = CliRunner()


def test_hello():
    result = runner.invoke(app, ["World"])
    assert result.exit_code == 0
    assert "Hello World" in result.output
```

Do not use `click.testing.CliRunner` directly with a `typer.Typer` instance — pass the app
to `typer.testing.CliRunner` and let it convert.

SOURCE: `.claude/worktrees/typer/typer/testing.py` — full file

### Capturing Rich-formatted output from Typer commands

`CliRunner` captures whatever the command writes to stdout. Rich output goes through its own
console, which by default targets stdout. The runner intercepts that. The captured text in
`result.output` is the rendered (markup-stripped) text.

```python
from typer.testing import CliRunner
import typer
from rich import print as rprint

app = typer.Typer()

@app.command()
def status() -> None:
    rprint("[bold green]OK[/bold green]")

runner = CliRunner()


def test_status_output():
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    # Output is the rendered text — markup tags are gone
    assert "OK" in result.output
```

When a command uses a module-level `console = Console(...)`, the runner still captures output
because it redirects `sys.stdout`. However, if the console is constructed with
`file=sys.stderr` or `stderr=True`, output goes to `result.stderr` (only available when
`mix_stderr=False` on the runner).

### Testing commands that use rich.print vs console.print

`rich.print` is a module-level convenience function that creates a temporary console on each
call. `console.print` uses a shared instance. Both write to `sys.stdout` by default and both
are captured by `CliRunner`.

```python
from typer.testing import CliRunner
import typer
from rich.console import Console

# Shared console — constructed at module level
console = Console()

app = typer.Typer()

@app.command()
def run() -> None:
    console.print("[italic]running[/italic]")

runner = CliRunner()


def test_run_captured():
    result = runner.invoke(app, [])
    assert "running" in result.output
```

The only behavioral difference in tests: a module-level console may retain state between
invocations (e.g., if `record=True`). Construct the console inside the command function or
inject it as a parameter when test isolation matters.

### Rich markup mode and help output

`typer.Typer(rich_markup_mode="rich")` enables Rich-rendered help panels with box-drawing
characters. Assert on those characters to verify the mode is active.

```python
from typer.testing import CliRunner
import typer

rounded = ["╭", "─", "┬", "╮", "│", "├", "┼", "┤", "╰", "┴", "╯"]

runner = CliRunner()


def test_rich_help_panels():
    app = typer.Typer(rich_markup_mode="rich")

    @app.command()
    def main(arg: str) -> None:
        """Main function"""

    result = runner.invoke(app, ["--help"])
    assert any(c in result.stdout for c in rounded)


def test_plain_help_no_panels():
    app = typer.Typer(rich_markup_mode=None)

    @app.command()
    def main(arg: str) -> None:
        """Main function"""

    result = runner.invoke(app, ["--help"])
    assert all(c not in result.stdout for c in rounded)
```

SOURCE: `.claude/worktrees/typer/tests/test_rich_markup_mode.py` — `test_rich_markup_mode_rich()`,
`test_rich_markup_mode_none()`

### Prompt simulation

Pass the `input` parameter to `runner.invoke()` to simulate user input to prompts. For
multiple prompts, separate responses with `\n`.

```python
from typer.testing import CliRunner
import typer

app = typer.Typer()

@app.command()
def greet(
    name: str,
    lastname: str = typer.Option(..., prompt=True),
) -> None:
    typer.echo(f"Hello {name} {lastname}")

runner = CliRunner()


def test_prompt_response():
    result = runner.invoke(app, ["Camila"], input="Gutiérrez")
    assert result.exit_code == 0
    assert "Lastname: " in result.output
    assert "Hello Camila Gutiérrez" in result.output


def test_multiple_prompts():
    result = runner.invoke(app, [], input="Alice\nSmith\n")
    assert result.exit_code == 0
```

SOURCE: `.claude/worktrees/typer/tests/test_tutorial/test_options/test_prompt/test_tutorial001.py`
— `test_option_lastname_prompt()`

---

## 3. Snapshot Testing

### Golden file tests with Console(record=True)

Record console output to a string and compare against a stored golden file. Use this for
complex rendered output (tables, panels, progress) where inline expected strings become
unmanageable.

```python
import pathlib
from rich.console import Console


GOLDEN_DIR = pathlib.Path(__file__).parent / "golden"


def render_report(console: Console, data: dict) -> None:
    from rich.table import Table
    table = Table(title="Report")
    table.add_column("Key")
    table.add_column("Value")
    for k, v in data.items():
        table.add_row(k, str(v))
    console.print(table)


def test_report_golden(request):
    console = Console(record=True, width=80, force_terminal=True)
    render_report(console, {"status": "ok", "count": 42})
    output = console.export_text()

    golden_path = GOLDEN_DIR / "report.txt"
    if not golden_path.exists():
        # First run: write golden file
        GOLDEN_DIR.mkdir(exist_ok=True)
        golden_path.write_text(output)
        return

    expected = golden_path.read_text()
    assert output == expected, (
        f"Output differs from golden file {golden_path}. "
        "Delete the golden file and re-run to update."
    )
```

Set `width` and `force_terminal=True` in the recording console so that box-drawing characters
and layout are deterministic. Without `force_terminal=True`, Rich may detect a non-terminal
environment and suppress box characters.

### Updating golden files

Add a pytest flag to allow updating golden files without manual deletion:

```python
def pytest_addoption(parser):
    parser.addoption("--update-golden", action="store_true", default=False)


def test_report_golden(request):
    update = request.config.getoption("--update-golden")
    console = Console(record=True, width=80, force_terminal=True)
    render_report(console, {"status": "ok", "count": 42})
    output = console.export_text()

    golden_path = pathlib.Path(__file__).parent / "golden" / "report.txt"
    if update or not golden_path.exists():
        golden_path.parent.mkdir(exist_ok=True)
        golden_path.write_text(output)
        return

    assert output == golden_path.read_text()
```

Run with `pytest --update-golden` to regenerate all golden files after intentional output
changes.

---

## 4. Common Testing Mistakes

### Mistake: asserting on Rich markup strings

Rich markup is consumed by the renderer. The string `[bold]foo[/bold]` never appears in
rendered output.

```python
# Wrong — this assertion always fails
assert "[bold]foo[/bold]" in result.output

# Correct — assert on rendered plain text
assert "foo" in result.output
```

### Mistake: inconsistent console width between test and production

A console with no explicit `width` queries the terminal. In CI there is no terminal, so Rich
falls back to a default (typically 80 or 0 characters). Locally you may have a 200-column
terminal. This causes layout differences that make snapshot tests flaky.

```python
# Wrong — width is environment-dependent
console = Console(file=io.StringIO())

# Correct — width is fixed
console = Console(file=io.StringIO(), width=80)
```

Apply the same fixed width in both the test console and any golden file generation.

SOURCE: `.claude/worktrees/rich/tests/test_console.py` — consistent `width=20` or `width=40`
on every test console

### Mistake: ANSI codes in assertion strings

Asserting on strings containing raw ANSI escape codes is brittle. Use `export_text()` (which
strips codes by default) or `capture.get()` for plain text assertions, and `export_text(styles=True)`
or `export_html()` only when you specifically need to verify styling.

```python
# Wrong — hard to read and breaks when color codes change
assert "\x1b[1mfoo\x1b[0m" in output

# Correct — assert on content, not rendering codes
console = Console(record=True, width=80)
console.print("[b]foo[/b]")
assert "foo" in console.export_text()

# Correct — assert on style via HTML when required
html = console.export_html()
assert "font-weight: bold" in html
```

### Mistake: not setting force_terminal when testing box-drawing output

When `file` is not a real TTY, Rich disables box-drawing characters unless `force_terminal=True`.
Tests that assert on `╭`, `│`, or `╰` will fail in CI without this flag.

```python
# Wrong — box characters suppressed in non-TTY environment
console = Console(file=io.StringIO(), width=80)

# Correct — force terminal mode for layout-sensitive tests
console = Console(file=io.StringIO(), width=80, force_terminal=True)
```

SOURCE: `.claude/worktrees/rich/tests/test_console.py` line 324 —
`Console(file=io.StringIO(), force_terminal=True, legacy_windows=False, _environ={})`

### Mistake: module-level console accumulates state across tests

A `Console(record=True)` instance at module level accumulates all output from every test.
`export_text()` clears the buffer by default, but if any test reads the buffer mid-stream or
sets `clear=False`, subsequent tests see stale data.

```python
# Wrong — shared recording console, state leaks between tests
console = Console(record=True, width=80)

def test_a():
    console.print("A")
    assert "A" in console.export_text(clear=False)  # buffer not cleared

def test_b():
    console.print("B")
    assert console.export_text() == "B\n"  # fails — "A\n" still in buffer

# Correct — construct a fresh console per test
def test_a():
    console = Console(record=True, width=80)
    console.print("A")
    assert "A" in console.export_text()

def test_b():
    console = Console(record=True, width=80)
    console.print("B")
    assert console.export_text() == "B\n"
```
