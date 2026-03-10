---
name: python-cli-architect
description: Reference patterns for Python CLI projects using Typer and Rich — project structure, Rich table rendering, and task completion quality gate. Loaded automatically by the python-cli-architect agent.
---

# Python CLI Architect Reference

## Project Structure

See [./references/project-structure.md](./references/project-structure.md) — `packages/{name}/` layout and Hatchling configuration.

## Rich Tables

See [./references/rich-tables.md](./references/rich-tables.md) — width measurement pattern that prevents wrapping at 80 columns in non-TTY output.

## Task Completion Quality Gate

See [./references/quality-gate.md](./references/quality-gate.md) — mandatory linting, type checking, test, review, and shebang validation steps before reporting done.
