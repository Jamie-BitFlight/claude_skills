---
name: feedback-cli-output-not-logging
description: "CLI result output (status, data, errors the caller acts on) goes through typer.echo()/print() or JSON; logging carries only debug traces behind --verbose/--debug"
metadata:
  type: feedback
---

A CLI tool's result is anything the caller reads and acts on: status lines, data, and errors. Emit it with `typer.echo()` (`err=True` for stderr) or `print()`, and use JSON when the data is structured. Keep `logging` for debug traces, gated behind a `--verbose`/`--debug` flag. If a tool has no such flag, it gets no `logging`.

When you replace Rich `Console` calls, map each one to echo or JSON. `logging`'s levels and stdout/stderr split look like a fit but are the wrong tool. The repo owner corrected this once already.

`typer.echo()` looks up `sys.stdout` again on each call, so `CliRunner` captures it. A `logging.StreamHandler` binds the stream when it is created, so `CliRunner` misses its output and `result.output` is silently empty.
