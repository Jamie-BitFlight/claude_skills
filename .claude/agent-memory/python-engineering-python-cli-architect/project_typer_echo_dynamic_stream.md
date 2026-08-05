---
name: project-typer-echo-dynamic-stream
description: "why typer.echo()/print() — not a bound logging.StreamHandler — is the correct Rich Console replacement for CLI output that must stay CliRunner-testable"
metadata:
  type: project
---

`click.testing.CliRunner.invoke()` (which `typer.testing.CliRunner` wraps) reassigns the
`sys.stdout`/`sys.stderr` module attributes for the duration of an invocation so it can capture
output into `result.output` — see `click/testing.py`, `isolation()`, lines ~314-341 (swap) and
~420-421 (restore).

`rich.console.Console` (constructed with the default `file=None`) survives this because
`Console.file` is a **property** that resolves `sys.stdout`/`sys.stderr` fresh on every access
(`rich/console.py`): `file = self._file or (sys.stderr if self.stderr else sys.stdout)`. It never
binds a stream reference at construction time.

`click.echo()` (= `typer.echo()`) does the same thing: when `file=None` it resolves via
`_default_text_stdout()`/`_default_text_stderr()` on every call — see
`click/utils.py::echo()`. This is why `typer.echo()` is the correct, already-tested,
zero-extra-code replacement for `console.print()`/`console.print(..., err=True)` in a Typer app.

**Why this matters**: `logging.StreamHandler(stream)` binds `self.stream` once, at handler
construction (typically at module-import time, before any test has run `invoke()`). A logger
built that way keeps writing to the *pre-swap* stream, and none of its output shows up in
`result.output` — tests silently see empty output instead of failing loudly, which is a nasty
failure mode to debug. Building a workaround subclass that overrides `emit()` to re-resolve
`sys.stdout`/`sys.stderr` on every call is *possible* (verified working) but unnecessary — it's
solving a problem `typer.echo()` doesn't have in the first place. Prefer `typer.echo()` outright;
don't reach for `logging` + a custom dynamic-stream handler when the content is primary CLI
output. See [[feedback_cli_output_not_logging]] for the broader logging-vs-output distinction.

**Verified**: `plugins/development-harness/scripts/*.py` Rich-removal task, 2026-08-05 — traced
through `click/testing.py`, `click/utils.py::echo()`, and `rich/console.py::Console.file` source
directly (not from memory) before committing to the `typer.echo()` design.
