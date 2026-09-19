---
name: feedback-typer-echo-vs-logging-capture
description: "typer.echo() output reaches CliRunner's result.output; a logging.StreamHandler created before the test run writes elsewhere"
metadata:
  type: feedback
---

`typer.echo()` looks up `sys.stdout` again on each call, so `CliRunner` captures it. A `logging.StreamHandler` binds the stream when it is created, so `CliRunner`'s `result.output` omits the logged lines. In `CliRunner` tests, assert only on text the command emits with `typer.echo()`.
