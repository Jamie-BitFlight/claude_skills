---
name: typer-and-rich
description: Use when building Typer/Rich CLI applications or reviewing existing CLI code for correctness. Activates on requests involving Rich table rendering, console output handling, testing Rich-formatted output, or Typer command wiring. Prevents common AI mistakes — Rich table wrapping in non-TTY contexts, incorrect stderr/stdout separation, and integration pitfalls. Load alongside the typer and rich API reference skills.
argument-hint: <test_file_or_test_name>
user-invocable: true
---

# Typer and Rich Best Practices

<user_input>$ARGUMENTS</user_input>
If <user_input/> contains a directory or file then that is what should be examines against this guide specifically. Start immediately. If its empty, then use this as a reference for existing tasks.

Correctness patterns for building CLI applications with Typer and Rich, focused on non-TTY environments and common failure modes. For API reference, load the dedicated skills:

- `Skill(skill="python3-development:typer")` — Typer CLI framework API reference
- `Skill(skill="python3-development:rich")` — Rich terminal UI API reference

## Non-TTY and Programmatic Usage

Consult `../python3-development/references/python3-standards.md` when applying shared architecture, typing, testing, or CLI rules; full standards, graphs, and amendment process are documented there.

See `references/non-tty-patterns.md` — Console behavior without TTY, width defaults, force_terminal vs width, Progress/Live in non-interactive contexts, environment variables.

## Rich Table Width Measurement

See `references/rich-tables.md` — width measurement pattern that prevents wrapping at 80 columns in non-TTY output.

## Testing Patterns

See `references/testing-patterns.md` — capturing Rich output in pytest, CliRunner with Rich, snapshot testing, common assertion mistakes.

## Exception Chain Prevention

See `references/exception-handling.md` — Typer exception chain prevention with `AppExit` and `AppExitRich` patterns. Read when implementing error handling in Typer CLI applications.

## Working Script Examples

See `assets/typer_examples/index.md` — working scripts demonstrating non-TTY display solutions. Read when troubleshooting display and layout of terminal applications.

See `assets/python-cli-demo.py` — complete working CLI demo with all patterns (PEP 723 shebang, Typer + Rich integration, modern Python 3.11+, async processing). Read when creating a new CLI tool as a reference implementation.
