# Run Scripts With uv run — Stop and Ask When uv Is Unavailable

`uv run` resolves whatever environment a script needs at launch — from its own PEP 723
`# /// script` block when it has one (see `rules/python-development.md`), or from the project
environment otherwise. No manual `pip install` or `venv activate` is required.

## If `uv run` fails with "uv not found" or "command not found"

**Preferred fix — install uv (resolves this for all future sessions):**

Ask the user:

```text
uv is not installed. It handles virtual environments and dependency installation
automatically. Would you like me to install it now?
```

If yes, install:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then re-run the original command with `uv run`.

**If uv installation is not an option:**

Stop and tell the user which command needed `uv`.
