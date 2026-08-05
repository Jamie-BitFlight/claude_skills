---
name: feedback-cli-output-not-logging
description: "primary CLI output (status/results/errors an agent reads) must go through typer.echo()/print(), never through the logging module — logging is reserved for genuine debug/forensic output"
metadata:
  type: feedback
---

When replacing `rich.console.Console` output in a CLI tool, do not default to routing the
replacement through Python's `logging` module just because it has levels and a stdout/stderr
split. `logging` and `print` are not interchangeable: `logging` is for debugging/forensics
(diagnostic records a developer inspects later), `print`/`typer.echo()` is for the tool's
primary output — the thing the calling process (human or agent) actually reads and acts on.

**Why**: Corrected explicitly by the repo owner during a Rich-removal task
(`plugins/development-harness/scripts/*.py`, 2026-08-05) after I initially wrapped every
`console.print()` replacement in `logger.info()`/`logger.error()` calls via a custom
`configure_cli_logger()` helper. None of the content being replaced was diagnostic — it was
status messages, tables, and results meant to be read directly. Using `logging` for it was
solving a problem (levels, stdout/stderr split) that didn't need solving with that tool.

**How to apply**:
- Ask first: is this content the tool's *result* (status, data, error the caller acts on) or a
  *debug trace* (something only useful when troubleshooting the tool itself)? Results → `typer.echo()`
  (or `print()`)/JSON. Debug traces → `logging`, gated behind a `--verbose`/`--debug` flag.
- If a CLI script has zero `--verbose`/`--debug` flag and its Rich `Console` calls are *all*
  user/agent-facing status or error messages, there is no legitimate use for `logging` at all in
  that file — don't introduce it.
- See [[project_typer_echo_dynamic_stream]] for why `typer.echo()` (not `logging.StreamHandler`)
  is also the mechanically correct choice for CliRunner test compatibility.
- See [[project_dh_scripts_agent_only_json]] for the further step this repo took: once you're on
  `typer.echo()`, decide whether the content is tabular/structured (→ JSON) or a simple line (→
  plain `typer.echo()`).
