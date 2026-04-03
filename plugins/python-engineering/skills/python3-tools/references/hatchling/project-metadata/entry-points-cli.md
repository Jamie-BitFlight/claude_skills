---
category: project-metadata
topics: [entry-points, CLI-scripts, console-commands, command-line-interface]
related: [entry-points-gui, entry-points-plugins]
---

# Entry Points: CLI Scripts

CLI (Command Line Interface) scripts are executable console commands that users can invoke directly from the terminal after package installation.

When Claude helps users create CLI entry points, explain that each entry in `[project.scripts]` defines a command users can run after package installation. The format `command-name = "module.submodule:function"` maps command names to callable Python functions that serve as entry points. Show examples of single and multiple commands with proper naming conventions.

## Configuration

Define CLI scripts in the `[project.scripts]` table:

```toml

[project.scripts]
my-cli = "my_package.cli:main"
another-command = "my_package.commands:execute"

```

## How It Works

When a package with CLI scripts is installed, entry points create executable commands on the user's PATH. Running a CLI script essentially executes:

```python

import sys
from my_package.cli import main

sys.exit(main())

```

## Examples

### Single CLI Command

```toml

[project.scripts]
myapp = "myapp.main:cli"

```

After installation, users can run:

```bash
myapp --help
```

### Multiple Commands

```toml

[project.scripts]
app = "myapp.cli:main"
app-serve = "myapp.server:run"
app-migrate = "myapp.db:migrate"

```

Users can invoke: `app`, `app-serve`, `app-migrate`

### Click Framework

```toml

[project.scripts]
mycli = "mycli.cli:cli"

```

With Click implementation:

```python

import click

@click.group()
def cli():
    pass

@cli.command()
def serve():
    click.echo("Starting server...")

if __name__ == "__main__":
    cli()

```

## Function Requirements

The referenced function should:

1. Accept no required arguments (optional args/kwargs allowed)
2. Return an exit code (integer) or None (exit 0)
3. Handle exceptions appropriately
4. Print output to stdout/stderr

### Valid Function Signatures

```python

def main():
    return 0

def cli():
    print("Hello")
    return None  # Defaults to exit code 0

def run(argv=None):
    return process(argv or sys.argv[1:])

```

## Platform-Specific Behavior

On Windows, console entry points are converted to `.exe` wrapper scripts for seamless execution.

On Unix-like systems, entry points become regular executable files.

## Best Practices

1. Use descriptive command names
2. Use `--help` support in your CLI framework
3. Return meaningful exit codes (0 for success, non-zero for errors)
4. Document available commands in README or help text
5. Use established CLI frameworks (Click, Typer, Argparse)

## Dynamic Entry Points

Entry points can be declared dynamic:

```toml

[project]
dynamic = ["scripts"]

[tool.hatch.metadata.hooks.custom]

```

## Related Configuration

- `entry-points-gui.md`
- `entry-points-plugins.md`
- `dynamic-metadata.md`
