---
name: typer-and-rich
description: Use when building or debugging Typer/Rich CLI applications. Activates on Rich table rendering, console output in non-TTY environments, CliRunner testing with Rich output, snapshot testing, Typer command wiring, exception chain prevention with AppExit/AppExitRich patterns, table width at 80-column wrapping, Progress/Live in non-interactive contexts, stderr/stdout separation, or force_terminal vs width configuration. Grounds AI-generated CLI code in verified correctness patterns and prevents known Typer/Rich integration mistakes.
argument-hint: <test_file_or_test_name>
user-invocable: true
---

# Typer and Rich Best Practices

<user_input>$ARGUMENTS</user_input>

If `<user_input/>` contains a directory or file then that is what should be examined against this guide specifically. Start immediately. If it is empty, then use this as a reference for existing tasks.

Correctness patterns for building CLI applications with Typer and Rich, focused on non-TTY environments and common failure modes. For API reference, load the dedicated skills:

- `Skill(skill="python-engineering:typer")` — Typer CLI framework API reference
- For Rich API reference, see `../python3-cli/references/rich-console-and-markup.md` and related Rich references

## Non-TTY and Programmatic Usage

Consult `python-engineering:standards-for-python-development` for the shared rules (architecture, typing, testing, CLI rules).

See `../python3-cli/references/typer-rich-non-tty-patterns.md` — Console behavior without TTY, width defaults, force_terminal vs width, Progress/Live in non-interactive contexts, environment variables.

## Rich Table Width Measurement

See `../python3-cli/references/typer-rich-tables.md` — width measurement pattern that prevents wrapping at 80 columns in non-TTY output.

## Testing Patterns

See `../python3-cli/references/typer-rich-testing-patterns.md` — capturing Rich output in pytest, CliRunner with Rich, snapshot testing, common assertion mistakes.

## Exception Chain Prevention

See `../python3-cli/references/typer-rich-exception-handling.md` — Typer exception chain prevention with `AppExit` and `AppExitRich` patterns. Read when implementing error handling in Typer CLI applications.

## Working Script Examples

See `../python3-cli/assets/typer_examples/index.md` — working scripts demonstrating non-TTY display solutions. Read when troubleshooting display and layout of terminal applications.

See `../python3-cli/assets/python-cli-demo.py` — complete working CLI demo with all patterns (PEP 723 shebang, Typer + Rich integration, modern Python 3.11+, async processing). Read when creating a new CLI tool as a reference implementation.
