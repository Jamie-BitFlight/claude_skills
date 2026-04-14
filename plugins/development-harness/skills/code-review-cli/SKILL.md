---
name: code-review-cli
description: Reviews CLI application code for correctness and quality. Use when reviewing tools that use argparse, click, typer, commander.js, or similar argument parsers — covers exit codes, help flags, stdin/stdout/stderr separation, non-interactive operation, signal handling, argument validation, ANSI color safety, and dry-run support for destructive operations.
user-invocable: false
---

# CLI Application Code Review Patterns

Stack-specific rules loaded by `dh:code-reviewer` when CLI entrypoints are detected (argparse, click, typer, commander.js, or similar argument parsing libraries).

## Exit Codes

- Exit code `0` must be returned only on success — any error condition must produce a non-zero exit code
- Returning exit code `0` after printing an error message is a blocking finding — tools in pipelines cannot detect the failure
- Common conventions: `1` for general errors, `2` for usage/argument errors, `3+` for application-specific codes documented in `--help`
- `sys.exit(1)` or `process.exit(1)` must be called on fatal errors, not just printing to stderr

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

- `--help` must be present and print usage information, option descriptions, and examples — the auto-generated help from argparse/click/typer is acceptable as a minimum
- `--version` must be present and print the version string matching `pyproject.toml` or `package.json`
- Help text must be consistent with actual behavior — stale help text is a blocking finding
- `--help` must exit `0`; `--version` must exit `0`

## stdin / stdout / stderr Separation

- Progress indicators, status messages, and diagnostic output go to `stderr`
- Data output (results to be piped or redirected) goes to `stdout`
- Mixing diagnostic messages into `stdout` breaks pipe usage — this is a blocking finding for tools that produce structured output
- Error messages go to `stderr` with a non-zero exit code

## Non-Interactive Operation

- Every interactive prompt (`input()`, `readline`, `inquirer`) must have a corresponding flag alternative (`--flag value`) for use in CI and scripts
- Interactive prompts that block in non-TTY environments (piped input, CI) are a blocking finding
- Detect TTY with `sys.stdin.isatty()` or equivalent and skip interactive prompts in non-TTY mode

## Signal Handling

- SIGINT (Ctrl+C) must produce a clean exit — no stack traces, no partial file writes, exit code `130` by default
- SIGTERM must be handled in long-running processes — clean up resources and exit gracefully
- Temporary files created during execution must be cleaned up in signal handlers or `atexit` callbacks

## Argument Validation

- Validate all arguments before beginning any work — do not fail halfway through a destructive operation due to a missing flag
- Report all validation errors at once rather than stopping at the first error
- File path arguments must be validated for existence and permissions before the operation begins, not after

## ANSI Color Codes

- ANSI escape codes must not be emitted when `NO_COLOR` environment variable is set (any non-empty value)
- ANSI escape codes must not be emitted when stdout is not a TTY (piped output, file redirection)
- Check TTY with `sys.stdout.isatty()` or equivalent before colorizing output

## Dry Run for Destructive Operations

- Any operation that deletes, modifies, or overwrites data must have a `--dry-run` flag that shows what would happen without doing it
- `--dry-run` output must clearly distinguish what would be changed and what would remain untouched

## Anti-Patterns

```python
# WRONG: no --dry-run for destructive command
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
import sys
USE_COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
success = "\033[32mSuccess\033[0m" if USE_COLOR else "Success"
print(success)
```
