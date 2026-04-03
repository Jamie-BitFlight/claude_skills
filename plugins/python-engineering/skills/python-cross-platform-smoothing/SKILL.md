---
name: python-cross-platform-smoothing
description: 'Knowledge base of cross-platform compatibility tips, tricks, and helper patterns for Python scripts targeting Windows, Linux, macOS, CLI, TUI (Rich/Textual), and GUI environments. Use when writing Python scripts that must run on multiple platforms, when Rich or Typer output breaks on Windows, when dealing with Unicode/encoding issues, terminal detection, path separators, or console color support. Covers: stdout/stderr encoding guards, ANSI escape handling, Windows console quirks, terminal capability detection, and portable I/O patterns.'
---

# Python Cross-Platform Smoothing

Verified patterns for writing Python scripts that behave correctly on Windows, Linux, and macOS across CLI, TUI, and GUI contexts.

## Unicode Output on Windows (Rich / Typer / any stdout)

**Problem:** Windows defaults stdout/stderr to a legacy code page (cp1252, cp437). Rich and Typer use Unicode characters (box-drawing, spinners, emoji) that these encodings cannot represent, causing `UnicodeEncodeError` at runtime.

**Solution:** Reconfigure streams before importing Rich or Typer.

```python
import sys
from io import TextIOWrapper

# Ensure UTF-8 output on Windows (cp1252 default cannot encode emoji/spinner chars).
# reconfigure() is available on Python 3.7+ when stdout is a TextIOWrapper.
if isinstance(sys.stdout, TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if isinstance(sys.stderr, TextIOWrapper):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Rich/Typer imports come AFTER the reconfigure block
import typer
from rich.console import Console
```

**Placement rule:** Immediately after stdlib imports, before any third-party imports. Rich inspects stdout encoding at import time.

**`errors="replace"`** substitutes unencodable characters with `?` instead of raising. Prefer this over `errors="strict"` for CLI tools where a crash is worse than a degraded character.

**`isinstance` guard** skips reconfigure when stdout is not a `TextIOWrapper` (e.g. redirected to `BytesIO` in tests, or already a custom wrapper). Safe to include unconditionally.

**Rich Console variant:** When targeting legacy Windows consoles (cmd.exe without Windows Terminal), also pass `legacy_windows=False` to force ANSI escape sequences instead of the Windows Console API:

```python
console = Console(legacy_windows=False)
```

**Why not env vars?** `PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8` require the caller to set them before the process starts — not self-contained in the script. The `reconfigure()` pattern is fully portable with no external configuration required.

**Also applies to:** `pathlib.Path.write_text()`, `open()`, and any file I/O that inherits the default encoding. Always pass `encoding="utf-8"` explicitly to file write calls on Windows:

```python
path.write_text(content, encoding="utf-8")
open(path, "w", encoding="utf-8")
```
