---
name: code-review-cli
description: Reviews CLI application code for correctness and quality. Use when reviewing tools that use argparse, click, typer, commander.js, or similar argument parsers — covers exit codes, help flags, stdin/stdout/stderr separation, non-interactive operation, signal handling, argument validation, ANSI color safety, and dry-run support for destructive operations.
user-invocable: false
---

# CLI Application Code Review Patterns

Stack-specific rules loaded by `dh:code-reviewer` when CLI entrypoints are detected (argparse, click, typer, commander.js, or similar argument parsing libraries).

Read [Review principles](../../docs/review-principles.md) before applying these checks; it defines
authority, applicability, evidence, and blocking criteria. Establish the command's supported
platforms and human/machine output contracts before prescribing an exact flag or exit code.

## Exit Codes

- Verify exit status distinguishes success from failure under the documented command contract, including partial-success or best-effort modes where supported.
- Report success status after a required operation failed when callers cannot detect that failure; distinguish an overall failure from a documented recoverable warning.
- Common conventions: `1` for general errors, `2` for usage/argument errors, `3+` for application-specific codes documented in `--help`
- Verify fatal paths reach a non-zero exit through the framework or explicit exit handling; printing to stderr alone is not a failure signal for a caller that checks exit status.

```python
# WRONG: exits 0 even on error
def main():
    try:
        run()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
    # implicit exit 0


# RIGHT: non-zero on error
def main():
    try:
        run()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
```

## Help and Version Flags

- Check that supported help/version interfaces are discoverable and usable by their intended callers; use `--help` and `--version` as conventions for new human-facing commands.
- Verify help describes the actual options and examples, and version output agrees with the installed/distributed package's version source.
- Help text must be consistent with actual behavior — stale help text is a blocking finding
- Supported help and version requests must report success when they complete successfully.

## stdin / stdout / stderr Separation

- Progress indicators, status messages, and diagnostic output go to `stderr`
- Data output (results to be piped or redirected) goes to `stdout`
- Mixing diagnostic messages into `stdout` breaks pipe usage — this is a blocking finding for tools that produce structured output
- Error messages go to `stderr` with a non-zero exit code

## Non-Interactive Operation

- For supported CI/script use, provide explicit inputs for interactive choices or a clear non-interactive failure; identify any prompt that makes the documented automation path unusable.
- Interactive prompts that block in non-TTY environments (piped input, CI) are a blocking finding
- Detect non-TTY input with `sys.stdin.isatty()` or equivalent. Do not interpret an unavailable prompt as consent to a consequential operation.

## Signal Handling

- Check interruption behavior for the supported platform/signals: required cleanup, an observable interrupted result, and preservation of valid durable state. Use conventional signal exit codes where that platform and command contract apply.
- For long-running commands, trace termination through resource ownership and partial operations; report abandoned resources or corrupt writes rather than requiring a particular handler API.
- Temporary resources need cleanup on relevant normal/error/interruption paths; a registered callback alone does not prove those paths are covered.

## Argument Validation

- Validate all arguments before beginning any work — do not fail halfway through a destructive operation due to a missing flag
- Report actionable validation errors; aggregate independent errors when that helps the caller without executing partial work.
- Check path preconditions before consequential work and handle failures at the operation boundary; a preflight existence/permission check does not guarantee the later operation succeeds.

## ANSI Color Codes

- ANSI escape codes must not be emitted when `NO_COLOR` environment variable is set (any non-empty value)
- Keep piped/redirected output free of unintended ANSI sequences by default; respect documented explicit color controls and the machine-output contract.
- Check TTY with `sys.stdout.isatty()` or equivalent before colorizing output

## Dry Run for Destructive Operations

- For commands that delete or overwrite durable data, verify how the caller can inspect and authorize the intended effects before execution. Report missing safeguards with the unintended effect they permit.
- Where the command promises `--dry-run`, verify it previews the relevant effects without performing them and clearly identifies affected resources. Do not require a specific flag name when the supported interface supplies equivalent protection.

## Anti-Patterns

```python
# Missing preview in a command whose contract requires --dry-run.
@app.command()
def delete_records(pattern: str):
    records = find_records(pattern)
    for r in records:
        r.delete()
    print(f"Deleted {len(records)} records")


# RIGHT: dry-run support
@app.command()
def delete_records(pattern: str, dry_run: bool = typer.Option(False, "--dry-run")):
    records = find_records(pattern)
    if dry_run:
        for r in records:
            print(f"Would delete: {r.id}")
        print(f"Would delete {len(records)} records (dry run)")
        return
    for r in records:
        r.delete()
    print(f"Deleted {len(records)} records")


# WRONG: ANSI always on
print(f"\033[32mSuccess\033[0m")

# RIGHT: conditional color
import os
import sys

USE_COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
success = "\033[32mSuccess\033[0m" if USE_COLOR else "Success"
print(success)
```
