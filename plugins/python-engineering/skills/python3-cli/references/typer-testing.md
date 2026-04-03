# Testing

Testing Typer CLI apps with pytest and CliRunner.

## Table of Contents

1. [Setup](#setup)
2. [Basic Test Pattern](#basic-test-pattern)
3. [Checking Results](#checking-results)
4. [Testing Prompts](#testing-prompts)
5. [Testing a Bare Function](#testing-a-bare-function)
6. [Testing Exit Codes](#testing-exit-codes)

---

## Setup

Install test dependencies:

```bash
pip install pytest typer[all]
```

`CliRunner` is the test invoker. Import it from `typer.testing`:

```python
from typer.testing import CliRunner
```

---

## Basic Test Pattern

```python
# app/main.py
import typer

app = typer.Typer()

@app.command()
def main(name: str, city: str = ""):
    typer.echo(f"Hello {name}")
    if city:
        typer.echo(f"Let's have a coffee in {city}")

if __name__ == "__main__":
    app()
```

```python
# app/test_main.py
from typer.testing import CliRunner
from app.main import app

runner = CliRunner()

def test_app():
    result = runner.invoke(app, ["Camila", "--city", "Berlin"])
    assert result.exit_code == 0
    assert "Hello Camila" in result.output
    assert "Let's have a coffee in Berlin" in result.output
```

- `runner.invoke(app, args)` — `args` is a list of strings matching what a user would type
- `result.output` — everything printed to stdout
- `result.exit_code` — `0` for success, non-zero for errors

---

## Checking Results

| Attribute | Type | Content |
|-----------|------|---------|
| `result.exit_code` | `int` | `0` on success |
| `result.output` | `str` | Combined stdout output |
| `result.stdout` | `str` | Standard output only |
| `result.stderr` | `str` | Standard error only (requires `mix_stderr=False` on runner) |
| `result.exception` | `Exception or None` | Unhandled exception if any |

Check help output:

```python
def test_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Usage:" in result.output
```

---

## Testing Prompts

Pass `input` to `runner.invoke()` to simulate terminal input. Newlines (`\n`) simulate pressing Enter:

```python
# main.py
@app.command()
def main(name: str, email: str = typer.Option(..., prompt=True)):
    typer.echo(f"Hello {name}, your email is: {email}")
```

```python
# test_main.py
def test_prompt():
    result = runner.invoke(app, ["Camila"], input="camila@example.com\n")
    assert result.exit_code == 0
    assert "camila@example.com" in result.output
```

Multiple prompts — provide each answer on its own line:

```python
result = runner.invoke(app, ["Camila"], input="camila@example.com\npassword123\npassword123\n")
```

---

## Testing a Bare Function

If a script uses `typer.run()` directly without an explicit app, create one in the test:

```python
# main.py (no explicit app)
import typer

def main(name: str = "World"):
    typer.echo(f"Hello {name}")

if __name__ == "__main__":
    typer.run(main)
```

```python
# test_main.py
import typer
from typer.testing import CliRunner
from app.main import main

runner = CliRunner()

def test_main():
    app = typer.Typer()
    app.command()(main)
    result = runner.invoke(app, ["Camila"])
    assert result.exit_code == 0
    assert "Hello Camila" in result.output
```

---

## Testing Exit Codes

`typer.Exit()` raises an exception that CliRunner captures as an exit code:

```python
# main.py
@app.command()
def main(name: str):
    if not name:
        raise typer.Exit(code=1)
    typer.echo(f"Hello {name}")
```

```python
# test
def test_exit_code():
    result = runner.invoke(app, [""])
    assert result.exit_code == 1
```

`typer.Abort()` produces exit code `1` and prints `Aborted!`:

```python
def test_abort():
    result = runner.invoke(app, ["--confirm"], input="n\n")
    assert result.exit_code == 1
    assert "Aborted" in result.output
```
